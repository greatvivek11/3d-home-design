import { useCallback, useEffect, useRef, useState } from 'react'
import { flushSync } from 'react-dom'
import HouseViewer from './HouseViewer'
import { study } from './model'
import { TOUR_FPS, tourFrame, tourMetadata } from './tour'
import { detailedFrame, detailedLandscapeMetadata, detailedMetadata } from './detailedTour'
import './tour.css'

declare global {
  interface Window {
    houseTour?: {
      metadata: typeof tourMetadata | typeof detailedMetadata | typeof detailedLandscapeMetadata
      setFrame: (frame: number) => Promise<void>
    }
  }
}

export default function CinematicTour() {
  const detailed = new URLSearchParams(location.search).get('tour') === 'detailed'
  const landscape = detailed && new URLSearchParams(location.search).get('aspect') === 'landscape'
  const metadata = detailed ? landscape ? detailedLandscapeMetadata : detailedMetadata : tourMetadata
  const frameState = useCallback((next: number) => detailed
    ? detailedFrame(next, landscape ? 'landscape' : 'portrait') : tourFrame(next), [detailed, landscape])
  const total = metadata.frames
  const [frame, setFrame] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [attempt, setAttempt] = useState(0)
  const current = useRef(frame)
  useEffect(() => { current.current = frame }, [frame])
  const state = frameState(frame)
  const exporting = new URLSearchParams(location.search).has('export')
  useEffect(() => {
    window.houseTour = {
      metadata,
      setFrame: async (next) => {
        frameState(next)
        flushSync(() => { setPlaying(false); setFrame(next) })
        await document.fonts.ready
        await new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve())))
      },
    }
    return () => { delete window.houseTour }
  }, [metadata, frameState])
  useEffect(() => {
    if (!playing) return
    const first = current.current === total - 1 ? 0 : current.current
    const start = performance.now()
    let request = 0
    const tick = (now: number) => {
      const next = Math.min(total - 1, first + Math.floor((now - start) * TOUR_FPS / 1000))
      setFrame(next)
      if (next === total - 1) setPlaying(false)
      else request = requestAnimationFrame(tick)
    }
    request = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(request)
  }, [playing, total])
  return <main className={`tour-page${detailed ? ' tour-detailed' : ''}${landscape ? ' tour-landscape' : ''}`} data-tour-frame={frame} aria-label="Dream home cinematic tour">
    <div className="tour-geometry" style={{ opacity: state.opacity }}>
      <HouseViewer mode={state.shot.mode} visible={state.visible} single={state.shot.floor} cameraView="perspective"
        inspection="furnished" showLabels={false} showDimensions={false} showCovers={detailed && state.shot.floor !== 'basement'} studioQuality
        selection={null} resetKey={0} onSelect={() => {}} tourCamera={state.camera}
        attempt={attempt} onRetry={() => setAttempt((value) => value + 1)} />
    </div>
    {detailed ? <header className="tour-location">
      <span>{state.shot.floor === 'first' ? 'FIRST FLOOR' : state.shot.floor === 'roof' ? 'ROOF TERRACE' : `${state.shot.floor.toUpperCase()} FLOOR`}</span>
      <h1>{state.shot.title}</h1>
    </header> : <header className="tour-header">
      <div className="tour-brand"><span className="tour-brand-mark">H</span> OUR DREAM HOME <span className="tour-number">{String(state.index + 1).padStart(2, '0')} / 07</span></div>
      <p className="tour-kicker">{tourFrame(frame).shot.kicker}</p>
      <h1>{state.shot.title}</h1>
      <p className="tour-detail">{tourFrame(frame).shot.detail}</p>
    </header>}
    <section className="tour-caption" aria-label="Video captions">
      {!detailed && <div className="tour-caption-label"><span /> THE WAY WE WANT TO LIVE</div>}
      <p>{state.caption.text}</p>
    </section>
    {detailed && state.time >= metadata.seconds - 8 ? <footer className="tour-music-credit">
      <strong>Music: {detailedMetadata.musicCredit.title}</strong>
      <span>{detailedMetadata.musicCredit.soundcloud}</span><span>{detailedMetadata.musicCredit.facebook}</span>
    </footer> : <footer className="tour-footer">
      <span>{study.study_id.replace('-', ' ').toUpperCase()} / CONCEPT DESIGN</span><span>DIMENSIONS &amp; ENGINEERING SUBJECT TO REVIEW</span>
    </footer>}
    <div className="tour-progress"><span style={{ width: `${(frame + 1) / total * 100}%` }} /></div>
    {!exporting && <nav className="tour-controls" aria-label="Tour preview controls">
      <a href={location.pathname}>Back to explorer</a>
      <button onClick={() => setPlaying((value) => !value)}>{playing ? 'Pause' : detailed ? 'Play detailed tour' : 'Play 60-second tour'}</button>
      <input aria-label="Tour frame" type="range" min={0} max={total - 1} value={frame}
        onChange={(event) => { setPlaying(false); setFrame(Number(event.target.value)) }} />
    </nav>}
  </main>
}
