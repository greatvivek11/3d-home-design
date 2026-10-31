/* global window, document, innerWidth, innerHeight */
import { chromium } from 'playwright'
import { createHash } from 'node:crypto'
import { execFileSync, spawn } from 'node:child_process'
import { once } from 'node:events'
import { existsSync, mkdirSync, readFileSync, renameSync, writeFileSync } from 'node:fs'
import { resolve, join } from 'node:path'
import process from 'node:process'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { parseArgs } from 'node:util'

const root = fileURLToPath(new URL('../..', import.meta.url))
const { values } = parseArgs({ options: {
  url: { type: 'string', default: 'http://localhost:5173/' },
  output: { type: 'string' },
  browser: { type: 'string' },
  tour: { type: 'string', default: 'overview' },
  aspect: { type: 'string', default: 'portrait' },
  frames: { type: 'string' },
  'start-frame': { type: 'string', default: '0' },
  'stills-only': { type: 'boolean', default: false },
} })
const sourceFiles = ['web/public/models/house.glb', 'web/src/generated/house.json', 'web/src/HouseViewer.tsx',
  'web/src/tour.ts', 'web/src/detailedTour.ts', 'house-spec/layout-study.json',
  'web/src/CinematicTour.tsx', 'web/src/tour.css', 'web/scripts/export-tour.mjs']
const fingerprints = () => Object.fromEntries(sourceFiles.map((name) =>
  [name, createHash('sha256').update(readFileSync(join(root, name))).digest('hex')]))
const integer = (value, name) => {
  const result = Number(value)
  if (!Number.isSafeInteger(result) || result < 0) throw new Error(`${name} must be a nonnegative integer`)
  return result
}

async function main() {
  if (!['overview', 'detailed'].includes(values.tour)) throw new Error('--tour must be overview or detailed')
  if (!['portrait', 'landscape'].includes(values.aspect)) throw new Error('--aspect must be portrait or landscape')
  if (values.aspect === 'landscape' && values.tour !== 'detailed') throw new Error('Landscape currently requires --tour detailed')
  const landscape = values.aspect === 'landscape'
  const dimensions = landscape ? { width: 1920, height: 1080 } : { width: 1080, height: 1920 }
  execFileSync('ffmpeg', ['-version'], { stdio: 'ignore' })
  execFileSync('ffprobe', ['-version'], { stdio: 'ignore' })
  const output = resolve(root, values.output ?? (values.tour === 'detailed' ? `output/study-010-detailed-tour${landscape ? '-landscape' : ''}` : 'output/study-010-web-tour'))
  const basename = values.tour === 'detailed' ? `dream-home-detailed-${values.aspect}` : 'dream-home-portrait'
  const movie = join(output, `${basename}.mp4`)
  for (const existing of [movie, join(output, 'tour-result.json')]) {
    if (existsSync(existing)) throw new Error(`Refusing to overwrite ${existing}; choose a new --output directory`)
  }
  mkdirSync(output, { recursive: true })
  const before = fingerprints()
  const wallStart = performance.now()
  const browser = await chromium.launch({
    executablePath: values.browser,
    headless: true,
    args: process.platform === 'darwin' ? ['--use-angle=metal'] : [],
  })
  let encoder
  try {
    const errors = []
    const page = await browser.newPage({ viewport: dimensions, deviceScaleFactor: 1, colorScheme: 'light' })
    page.on('pageerror', (error) => errors.push(error.message))
    page.on('console', (message) => { if (message.type() === 'error') errors.push(message.text()) })
    page.on('requestfailed', (request) => errors.push(`${request.url()}: ${request.failure()?.errorText}`))
    page.on('response', (response) => { if (response.status() >= 400) errors.push(`HTTP ${response.status()} ${response.url()}`) })
    const url = new URL(values.url)
    url.searchParams.set('tour', values.tour === 'detailed' ? 'detailed' : '1')
    url.searchParams.set('export', '1')
    url.searchParams.set('aspect', values.aspect)
    await page.goto(url.href, { waitUntil: 'networkidle', timeout: 60000 })
    await page.getByText('3D house model loaded', { exact: true }).waitFor({ state: 'attached', timeout: 60000 })
    await page.waitForFunction(() => !!window.houseTour)
    const session = await page.context().newCDPSession(page)
    let captureScale = 1
    const capture = async (path) => {
      const screenshot = async () => {
        const image = await session.send('Page.captureScreenshot', { format: 'png', fromSurface: true,
          captureBeyondViewport: false, optimizeForSpeed: true,
          clip: { x: 0, y: 0, ...dimensions, scale: captureScale } })
        return Buffer.from(image.data, 'base64')
      }
      let buffer = await screenshot()
      const width = buffer.readUInt32BE(16), height = buffer.readUInt32BE(20)
      if (width !== dimensions.width && width / dimensions.width === height / dimensions.height) {
        captureScale *= dimensions.width / width
        console.log(`Normalizing native screenshot scale ${width}x${height} to ${dimensions.width}x${dimensions.height}`)
        buffer = await screenshot()
      }
      if (buffer.readUInt32BE(16) !== dimensions.width || buffer.readUInt32BE(20) !== dimensions.height) throw new Error('Screenshot dimensions do not match the requested export')
      if (path) writeFileSync(path, buffer)
      return buffer
    }
    const metadata = await page.evaluate(() => window.houseTour.metadata)
    const expectedSeconds = values.tour === 'detailed' ? 210 : 60
    if (metadata.seconds !== expectedSeconds || metadata.frames !== expectedSeconds * 30
        || metadata.width !== dimensions.width || metadata.height !== dimensions.height || metadata.aspect !== values.aspect
        || (values.tour === 'detailed' && metadata.variant !== 'detailed')) {
      throw new Error('Served timeline does not match the requested tour; rebuild/restart the server')
    }
    const manifest = JSON.parse(readFileSync(join(root, 'web/src/generated/house.json'), 'utf8'))
    if (metadata.studyId !== manifest.study_id || metadata.layoutSha256 !== manifest.layout_sha256) {
      throw new Error('Served tour does not match the local canonical model; rebuild/restart the server')
    }
    const gpu = await page.evaluate(() => {
      const canvas = document.querySelector('canvas')
      const gl = canvas?.getContext('webgl2')
      if (!gl) throw new Error('WebGL2 is unavailable')
      const debug = gl.getExtension('WEBGL_debug_renderer_info')
      return { renderer: debug ? gl.getParameter(debug.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER),
        canvas: [canvas.width, canvas.height], viewport: [innerWidth, innerHeight] }
    })
    if (/swiftshader|llvmpipe|software/i.test(gpu.renderer)) throw new Error(`Hardware GPU rendering required, got ${gpu.renderer}`)
    if (gpu.canvas[0] !== metadata.width || gpu.canvas[1] !== metadata.height) throw new Error('Unexpected render resolution')
    const start = integer(values['start-frame'], 'start-frame')
    const count = values.frames === undefined ? metadata.frames - start : integer(values.frames, 'frames')
    if (count < 1 || start + count > metadata.frames) throw new Error('Requested frame range is outside the tour')
    const setFrame = (frame) => page.evaluate(async (next) => {
      if (!window.houseTour) throw new Error('Tour controller disappeared')
      await window.houseTour.setFrame(next)
    }, frame)
    const assertBrowser = () => { if (errors.length) throw new Error(`Browser export errors:\n${errors.join('\n')}`) }
    await setFrame(start)
    await capture()
    assertBrowser()
    if (values['stills-only']) {
      const frames = values.tour === 'detailed' ? metadata.shots.map((shot) => Math.round((shot.start + shot.end) / 2 * metadata.fps)) : [75, 240, 510, 930, 1260, 1530, 1725]
      for (const frame of frames) {
        await setFrame(frame)
        await capture(join(output, `frame-${String(frame).padStart(4, '0')}.png`))
        assertBrowser()
      }
      if (JSON.stringify(before) !== JSON.stringify(fingerprints())) throw new Error('Source assets changed while rendering framing stills')
      writeFileSync(join(output, 'stills.json'), JSON.stringify({ status: 'PASS', metadata, gpu, frames, source_hashes: before }, null, 2))
      console.log(`${frames.length} framing stills: ${output}`)
      return
    }
    const pending = join(output, `${basename}.pending.mp4`)
    let stderr = '', encoderError
    encoder = spawn('ffmpeg', ['-hide_banner', '-loglevel', 'error', '-y',
      '-f', 'image2pipe', '-framerate', String(metadata.fps), '-vcodec', 'png', '-i', 'pipe:0',
      '-an', '-c:v', 'libx264', '-preset', 'fast', '-crf', '17', '-pix_fmt', 'yuv420p',
      '-movflags', '+faststart', pending], { stdio: ['pipe', 'ignore', 'pipe'] })
    encoder.stderr.on('data', (data) => { stderr = (stderr + data).slice(-16000) })
    encoder.stdin.on('error', (error) => { encoderError = error })
    const finished = new Promise((resolve, reject) => {
      encoder.once('error', reject)
      encoder.once('exit', (code, signal) => code === 0 ? resolve() : reject(new Error(`FFmpeg exited ${code ?? signal}: ${stderr}`)))
    }).catch((error) => { encoderError = error })
    const renderStart = performance.now()
    for (let frame = start; frame < start + count; frame++) {
      if (encoderError) throw encoderError
      await setFrame(frame)
      const image = await capture()
      assertBrowser()
      if (encoderError) throw encoderError
      if (!encoder.stdin.write(image)) await once(encoder.stdin, 'drain')
      if ((frame - start + 1) % 150 === 0) console.log(`${frame - start + 1}/${count} frames (${((performance.now() - renderStart) / 1000).toFixed(1)}s)`)
    }
    encoder.stdin.end()
    await finished
    if (encoderError) throw encoderError
    const renderSeconds = (performance.now() - renderStart) / 1000
    const probe = JSON.parse(execFileSync('ffprobe', ['-v', 'error', '-count_frames', '-show_streams', '-show_format', '-of', 'json', pending], { encoding: 'utf8' }))
    const videos = probe.streams.filter((stream) => stream.codec_type === 'video')
    const video = videos[0]
    if (videos.length !== 1 || probe.streams.some((stream) => stream.codec_type === 'audio')
        || video.codec_name !== 'h264' || video.pix_fmt !== 'yuv420p'
        || video.width !== metadata.width || video.height !== metadata.height
        || video.avg_frame_rate !== `${metadata.fps}/1`
        || Number(video.nb_read_frames) !== count
        || Math.abs(Number(probe.format.duration) - count / metadata.fps) > 0.001) {
      throw new Error(`Unexpected video contract: ${JSON.stringify(probe)}`)
    }
    execFileSync('ffmpeg', ['-v', 'error', '-xerror', '-i', pending, '-f', 'null', '-'], { stdio: ['ignore', 'ignore', 'pipe'] })
    if (JSON.stringify(before) !== JSON.stringify(fingerprints())) throw new Error('Source assets changed during export; refusing to publish mixed frames')
    assertBrowser()
    if (start === 0 && count === metadata.frames) writeFileSync(join(output, `${basename}.srt`), metadata.subtitles)
    renameSync(pending, movie)
    const report = {
      status: 'PASS', source_hashes: before, gpu, metadata, first_frame: start, captured_frames: count,
      video_seconds: count / metadata.fps, render_and_encode_seconds: renderSeconds,
      wall_seconds: (performance.now() - wallStart) / 1000, video_bytes: Number(probe.format.size),
      complete_decode: true, capture: { format: 'lossless PNG', optimizeForSpeed: true, nativeScale: captureScale }, browser_errors: errors, probe,
    }
    writeFileSync(join(output, 'tour-result.json'), JSON.stringify(report, null, 2))
    console.log(JSON.stringify({ movie: pathToFileURL(movie).href, frames: count, seconds: report.video_seconds,
      render_and_encode_seconds: renderSeconds, video_bytes: report.video_bytes, gpu: gpu.renderer }, null, 2))
  } finally {
    if (encoder && encoder.exitCode === null && !encoder.killed) encoder.kill('SIGTERM')
    await browser.close()
  }
}
main().catch((error) => { console.error(error); process.exitCode = 1 })
