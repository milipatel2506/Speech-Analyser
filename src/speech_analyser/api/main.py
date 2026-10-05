"""FastAPI backend for the dashboard.

Run:  uv run uvicorn speech_analyser.api.main:app --port 8000
"""

from __future__ import annotations

import json
import uuid
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from ..audio_io import SAMPLE_RATE, decode_any, load_audio, save_audio
from ..pipeline import Analysed, analyse, analyse_recording, report

ROOT = Path(__file__).resolve().parents[3]
DS = ROOT / "dataset"
UPLOADS = ROOT / "backend_uploads"
FRONTEND = ROOT / "frontend" / "dist"
MAX_UPLOAD_S = 300

app = FastAPI(title="Speech Delivery Analyser", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_methods=["*"], allow_headers=["*"])


# --------------------------------------------------------------------------- dataset access


def _baseline_meta(sid: str) -> dict:
    p = DS / "labels" / sid / "baseline.json"
    if not p.exists():
        raise HTTPException(404, f"unknown baseline {sid}")
    return json.loads(p.read_text(encoding="utf-8"))


def _clip_label(clip_id: str) -> dict:
    sid = clip_id.split("__")[0]
    p = DS / "labels" / sid / f"{clip_id}.json"
    if not p.exists():
        raise HTTPException(404, f"unknown clip {clip_id}")
    return json.loads(p.read_text(encoding="utf-8"))


@lru_cache(maxsize=16)
def _baseline(sid: str) -> Analysed:
    meta = _baseline_meta(sid)
    return analyse_recording(load_audio(DS / meta["audio"], normalize=False), meta["transcript"], meta["words"])


@lru_cache(maxsize=256)
def _clip_report(clip_id: str) -> dict:
    lab = _clip_label(clip_id)
    # reuse the forced alignment cached at build time when present (deterministic, ~20 s faster)
    part = analyse_recording(load_audio(DS / lab["audio"], normalize=False), lab["transcript"], lab.get("aligned_words"))
    return report(_baseline(lab["baseline_id"]), part)


# --------------------------------------------------------------------------- routes


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.get("/api/baselines")
def baselines() -> list[dict]:
    out = []
    for p in sorted((DS / "labels").glob("*/baseline.json")):
        m = json.loads(p.read_text(encoding="utf-8"))
        out.append({k: m[k] for k in ("id", "speaker", "sex", "title", "year", "duration", "transcript", "license", "source_url")})
    return out


@app.get("/api/baselines/{sid}/audio")
def baseline_audio(sid: str):
    return FileResponse(DS / _baseline_meta(sid)["audio"], media_type="audio/wav")


@app.get("/api/clips")
def clips(baseline_id: str | None = None) -> list[dict]:
    out = []
    for p in sorted((DS / "labels").glob(f"{baseline_id or '*'}/*.json")):
        if p.name == "baseline.json":
            continue
        lab = json.loads(p.read_text(encoding="utf-8"))
        out.append(
            {
                "clip_id": lab["clip_id"],
                "baseline_id": lab["baseline_id"],
                "kind": lab["kind"],
                "level": lab["level"],
                "duration": lab["duration"],
                "speaker": lab.get("speaker"),
                "take": lab.get("take"),
                "flaws": [{k: f[k] for k in ("type", "label", "severity", "start", "end")} for f in lab["flaws"]],
            }
        )
    return out


@app.get("/api/clips/{clip_id}/audio")
def clip_audio(clip_id: str):
    return FileResponse(DS / _clip_label(clip_id)["audio"], media_type="audio/wav")


@app.post("/api/clips/{clip_id}/analyze")
async def analyze_clip(clip_id: str) -> dict:
    lab = _clip_label(clip_id)
    rep = await run_in_threadpool(_clip_report, clip_id)
    return {
        **rep,
        "baseline_id": lab["baseline_id"],
        "participant_audio_url": f"/api/clips/{clip_id}/audio",
        "baseline_audio_url": f"/api/baselines/{lab['baseline_id']}/audio",
        "ground_truth": lab["flaws"],
    }


@app.post("/api/analyze")
async def analyze_upload(
    audio: UploadFile = File(...),
    baseline_id: str | None = Form(None),
    transcript: str | None = Form(None),
    baseline_audio: UploadFile | None = File(None),
    baseline_transcript: str | None = Form(None),
) -> dict:
    """Analyse an uploaded delivery against a dataset baseline or an uploaded reference."""
    UPLOADS.mkdir(exist_ok=True)

    async def store(upload: UploadFile, tag: str) -> tuple[str, Path]:
        uid = f"{uuid.uuid4().hex}_{tag}"
        raw = UPLOADS / f"{uid}{Path(upload.filename or '').suffix or '.bin'}"
        raw.write_bytes(await upload.read())
        try:
            y = await run_in_threadpool(decode_any, raw)
        except Exception as e:
            raise HTTPException(400, f"could not decode {upload.filename}: {e}") from e
        finally:
            raw.unlink(missing_ok=True)
        if len(y) / SAMPLE_RATE > MAX_UPLOAD_S:
            raise HTTPException(413, f"recordings are limited to {MAX_UPLOAD_S} s")
        wav = UPLOADS / f"{uid}.wav"
        save_audio(wav, y)
        return uid, wav

    if baseline_audio is not None:
        if not (baseline_transcript or transcript):
            raise HTTPException(400, "a transcript is required with an uploaded reference")
        b_uid, b_wav = await store(baseline_audio, "ref")
        b_text = baseline_transcript or transcript
        base = await run_in_threadpool(analyse_recording, load_audio(b_wav), b_text)
        baseline_url = f"/api/uploads/{b_uid}"
    elif baseline_id:
        base = await run_in_threadpool(_baseline, baseline_id)
        b_text = _baseline_meta(baseline_id)["transcript"]
        baseline_url = f"/api/baselines/{baseline_id}/audio"
    else:
        raise HTTPException(400, "choose a dataset baseline or upload a reference recording")

    uid, wav = await store(audio, "participant")
    y = load_audio(wav, normalize=False)
    rep = await run_in_threadpool(analyse, y, transcript or b_text, base)
    return {**rep, "baseline_id": baseline_id, "participant_audio_url": f"/api/uploads/{uid}", "baseline_audio_url": baseline_url, "ground_truth": None}


@app.get("/api/evaluation")
def evaluation() -> dict:
    p = ROOT / "docs" / "results" / "evaluation.json"
    if not p.exists():
        raise HTTPException(404, "evaluation not run yet")
    res = json.loads(p.read_text(encoding="utf-8"))
    res["false_positives"].pop("items", None)
    return res


@app.get("/api/uploads/{uid}")
def uploaded_audio(uid: str):
    p = UPLOADS / f"{Path(uid).name}.wav"
    if not p.exists():
        raise HTTPException(404)
    return FileResponse(p, media_type="audio/wav")


if FRONTEND.exists():  # production: serve the built dashboard from the same origin
    app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")
