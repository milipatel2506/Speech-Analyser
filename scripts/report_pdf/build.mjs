// Usage: npm i && npm run build   (uses the system Microsoft Edge; set CHANNEL=chrome for Chrome)
import { readFileSync } from 'node:fs'
import { marked } from 'marked'
import { chromium } from 'playwright-core'

const [, , src, out] = process.argv
const css = `
body { font-family: "Segoe UI", system-ui, sans-serif; font-size: 9.6pt; line-height: 1.38; color: #111; }
h1 { font-size: 16pt; margin: 0 0 2pt; } h1 + p { margin-top: 0; color: #444; }
h2 { font-size: 12pt; margin: 11pt 0 3pt; border-bottom: 1px solid #ccc; padding-bottom: 2pt; }
h3 { font-size: 10.5pt; margin: 8pt 0 2pt; }
p, li { margin: 3pt 0; } ul { padding-left: 16pt; margin: 3pt 0; }
table { border-collapse: collapse; width: 100%; margin: 4pt 0; font-size: 8.4pt; page-break-inside: avoid; }
th, td { border: 1px solid #d0d0d0; padding: 2pt 4pt; text-align: left; vertical-align: top; }
th { background: #f2f2f2; }
code { font-family: Consolas, monospace; font-size: 8.6pt; background: #f4f4f4; padding: 0 2pt; }
blockquote { margin: 4pt 0; padding: 3pt 8pt; border-left: 3px solid #2a78d6; background: #f6f9fd; }`
const html = `<!doctype html><html><head><meta charset="utf-8"><style>${css}</style></head><body>${marked.parse(readFileSync(src, 'utf8'))}</body></html>`
const browser = await chromium.launch({ channel: process.env.CHANNEL ?? 'msedge' })
const page = await browser.newPage()
await page.setContent(html, { waitUntil: 'load' })
await page.pdf({
  path: out, format: 'A4', printBackground: true,
  margin: { top: '15mm', bottom: '15mm', left: '15mm', right: '15mm' },
  displayHeaderFooter: true, headerTemplate: '<span></span>',
  footerTemplate: '<div style="font-size:8px;width:100%;text-align:center;color:#888">Cadence · Track C · page <span class="pageNumber"></span> / <span class="totalPages"></span></div>',
})
await browser.close()
console.log(`wrote ${out}`)
