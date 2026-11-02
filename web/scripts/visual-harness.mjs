/* global document, Image, requestAnimationFrame */
// Render -> measure -> score loop for the web viewer, adapted from the
// execution / measurement / vision feedback pattern of 3DCodeVerse.
// Execution: console and page errors. Measurement: per-view image statistics and frame time.
// Vision: an optional rubric file filled in by a reviewer (human or VLM) who has looked at the sheet.
import { chromium } from 'playwright'
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { join, resolve } from 'node:path'
import process from 'node:process'
import { fileURLToPath } from 'node:url'
import { parseArgs } from 'node:util'

const root = fileURLToPath(new URL('../..', import.meta.url))
const { values } = parseArgs({ options: {
  url: { type: 'string', default: 'http://127.0.0.1:5173/' },
  round: { type: 'string' },
  out: { type: 'string', default: 'output/poc-visual' },
  vision: { type: 'string' },
  browser: { type: 'string' },
  width: { type: 'string', default: '1600' },
  height: { type: 'string', default: '1000' },
} })
if (!values.round) throw new Error('--round <name> is required, e.g. --round r0-baseline')
const outDir = resolve(root, values.out, values.round)
if (existsSync(join(outDir, 'result.json'))) throw new Error(`Refusing to overwrite ${outDir}; choose a new --round`)
mkdirSync(outDir, { recursive: true })

const exterior = (shot) => ({ id: `outside-${shot}`, url: `?view=outside&shot=${shot}`, settle: 3200 })
const views = [
  exterior('front'), exterior('entrance'), exterior('rear'), exterior('aerial-rear'), exterior('garden-pool'),
  { id: 'inside-ground-plan', url: '', plan: true, floor: 'ground', settle: 2500 },
  { id: 'inside-living', url: '', room: 'ground/family_living', settle: 3200 },
  { id: 'inside-kitchen', url: '', room: 'ground/kitchen', settle: 3200 },
  { id: 'inside-master', url: '', room: 'ground/master_bedroom', settle: 3200 },
]

// Targets are proxies for "reads as a lit, material-rich photograph", not ground truth.
const targets = {
  luma: [0.38, 0.62], contrast: [0.17, 0.3], clipped: [0, 0.01], crushed: [0, 0.06],
  detail: [0.035, 0.11], colourful: [0.05, 0.22],
}
const inRange = (value, [low, high], softness = 0.5) => {
  if (value >= low && value <= high) return 1
  const span = (high - low) * softness
  const distance = value < low ? low - value : value - high
  return Math.max(0, 1 - distance / span)
}

async function measure(page, base64) {
  return page.evaluate(async (data) => {
    const image = new Image()
    image.src = `data:image/png;base64,${data}`
    await image.decode()
    const w = 400, h = Math.round(400 * image.height / image.width)
    const canvas = document.createElement('canvas')
    canvas.width = w; canvas.height = h
    const context = canvas.getContext('2d')
    context.drawImage(image, 0, 0, w, h)
    const { data: px } = context.getImageData(0, 0, w, h)
    const luma = new Float32Array(w * h)
    let sum = 0, clipped = 0, crushed = 0, chroma = 0, counted = 0
    for (let i = 0; i < w * h; i++) {
      const r = px[i * 4] / 255, g = px[i * 4 + 1] / 255, b = px[i * 4 + 2] / 255
      const y = 0.2126 * r + 0.7152 * g + 0.0722 * b
      luma[i] = y
      sum += y
      if (y > 0.985) clipped++
      if (y < 0.04) crushed++
      chroma += Math.max(r, g, b) - Math.min(r, g, b)
      counted++
    }
    const mean = sum / luma.length
    let variance = 0, edges = 0
    for (let y = 1; y < h - 1; y++) {
      for (let x = 1; x < w - 1; x++) {
        const i = y * w + x
        variance += (luma[i] - mean) ** 2
        const gx = luma[i + 1] - luma[i - 1], gy = luma[i + w] - luma[i - w]
        if (Math.hypot(gx, gy) > 0.05) edges++
      }
    }
    const pixels = (w - 2) * (h - 2)
    return { luma: mean, contrast: Math.sqrt(variance / pixels), clipped: clipped / luma.length,
      crushed: crushed / luma.length, detail: edges / pixels, colourful: chroma / counted }
  }, base64)
}

async function frameTime(page, ms = 1500) {
  return page.evaluate((duration) => new Promise((resolveTime) => {
    const stamps = []
    const tick = (now) => {
      stamps.push(now)
      if (now - stamps[0] < duration) requestAnimationFrame(tick)
      else {
        const deltas = stamps.slice(1).map((t, i) => t - stamps[i]).sort((a, b) => a - b)
        resolveTime({ frames: deltas.length, medianMs: deltas[Math.floor(deltas.length / 2)] ?? 0, p95Ms: deltas[Math.floor(deltas.length * 0.95)] ?? 0 })
      }
    }
    requestAnimationFrame(tick)
  }), ms)
}

const errors = []
const browser = await chromium.launch({ executablePath: values.browser, headless: true, args: process.platform === 'darwin' ? ['--use-angle=metal'] : [] })
const results = []
try {
  const page = await browser.newPage({ viewport: { width: Number(values.width), height: Number(values.height) }, deviceScaleFactor: 1, colorScheme: 'light' })
  page.on('pageerror', (error) => errors.push(`pageerror: ${error.message}`))
  page.on('console', (message) => { if (message.type() === 'error') errors.push(`console: ${message.text()}`) })
  for (const view of views) {
    await page.goto(new URL(view.url, values.url).toString(), { waitUntil: 'load' })
    await page.waitForSelector('canvas', { timeout: 60000 })
    await page.waitForFunction(() => !document.body.innerText.toLowerCase().includes('loading'), null, { timeout: 90000 }).catch(() => {})
    if (view.plan) {
      await page.getByRole('button', { name: 'Floor plan' }).click()
      await page.getByRole('button', { name: 'Focus Ground' }).first().click().catch(() => {})
    }
    if (view.room) await page.selectOption('#room-select', view.room)
    await page.waitForTimeout(view.settle)
    const shot = await page.locator('main.viewer-panel').screenshot({ type: 'png' })
    writeFileSync(join(outDir, `${view.id}.png`), shot)
    const stats = await measure(page, shot.toString('base64'))
    const timing = await frameTime(page)
    const parts = Object.fromEntries(Object.entries(targets).map(([key, range]) => [key, inRange(stats[key], range)]))
    const score = Object.values(parts).reduce((a, b) => a + b, 0) / Object.values(parts).length
    results.push({ id: view.id, stats, timing, parts, score })
    console.log(view.id.padEnd(20), `score ${score.toFixed(2)}`, `luma ${stats.luma.toFixed(2)} contrast ${stats.contrast.toFixed(2)} detail ${stats.detail.toFixed(3)} clip ${stats.clipped.toFixed(3)}`, `${timing.medianMs.toFixed(1)}ms p95 ${timing.p95Ms.toFixed(1)}ms`)
  }
} finally {
  await browser.close()
}

const measurement = results.reduce((a, r) => a + r.score, 0) / results.length
const slowest = Math.max(...results.map((r) => r.timing.p95Ms))
// Measurements veto visual claims: errors cap the round and a slow viewer is penalised.
let total = measurement
const vetoes = []
if (errors.length) { total = Math.min(total, 0.5); vetoes.push(`${errors.length} runtime error(s)`) }
if (slowest > 60) { total -= Math.min(0.15, (slowest - 60) / 400); vetoes.push(`p95 frame ${slowest.toFixed(0)} ms`) }
let vision = null
if (values.vision) {
  vision = JSON.parse(readFileSync(resolve(root, values.vision), 'utf8'))
  const weights = vision.weights ?? {}
  const scores = vision.scores ?? {}
  const weightSum = Object.values(weights).reduce((a, b) => a + b, 0)
  vision.total = weightSum ? Object.entries(weights).reduce((a, [key, weight]) => a + weight * (scores[key] ?? 0), 0) / weightSum / 10 : null
  if (vision.total !== null) total = 0.4 * total + 0.6 * vision.total
}
const report = { round: values.round, measurement, vision, total, vetoes, errors: errors.slice(0, 20), results }
writeFileSync(join(outDir, 'result.json'), `${JSON.stringify(report, null, 2)}\n`)
console.log(`\nROUND ${values.round}: measurement ${measurement.toFixed(3)}${vision ? ` vision ${vision.total?.toFixed(3)}` : ''} total ${total.toFixed(3)}${vetoes.length ? ` vetoes: ${vetoes.join(', ')}` : ''}`)
if (errors.length) console.log(errors.slice(0, 5).join('\n'))
