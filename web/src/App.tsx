import { lazy, Suspense, useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import Icon from './Icon'
import type { IconName } from './Icon'
import {
  defaultVisibility, displayedFloors, findRoom, floorColors, floors, formatArea, modes, siteAllowed, study,
} from './model'
import type { CameraView, FloorId, Selection, ViewMode, Visibility } from './model'

const HouseViewer = lazy(() => import('./HouseViewer'))
const modeIcons: Record<string, IconName> = { 'side-by-side': 'grid', stacked: 'layers', exploded: 'spread' }

function NotesDialog({ children, onClose }: { children: ReactNode; onClose: () => void }) {
  const ref = useRef<HTMLDialogElement>(null)
  useEffect(() => {
    const dialog = ref.current
    if (!dialog) return
    dialog.showModal()
    return () => dialog.close()
  }, [])
  return <dialog ref={ref} className="study-dialog" aria-labelledby="study-title" onCancel={onClose}
    onKeyDown={(event) => {
      if (event.key === 'Escape') { event.preventDefault(); onClose() }
    }}
    onClick={(event) => {
      if (event.target !== event.currentTarget) return
      const rect = event.currentTarget.getBoundingClientRect()
      if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) onClose()
    }}>{children}</dialog>
}

export default function App() {
  const [mode, setMode] = useState<ViewMode>('side-by-side')
  const [visible, setVisible] = useState<Visibility>(defaultVisibility)
  const [single, setSingle] = useState<FloorId>('ground')
  const [cameraView, setCameraView] = useState<CameraView>('perspective')
  const [showLabels, setShowLabels] = useState(true)
  const [showDimensions, setShowDimensions] = useState(true)
  const [selection, setSelection] = useState<Selection | null>(null)
  const [resetKey, setResetKey] = useState(0)
  const [attempt, setAttempt] = useState(0)
  const [showNotes, setShowNotes] = useState(false)
  const active = displayedFloors(mode, visible, single)
  const room = findRoom(selection)
  const currentFloor = floors.find((floor) => floor.id === single)
  const planFloor = selection?.floorId ?? single

  function changeMode(next: ViewMode) {
    setMode(next)
    setSelection(null)
  }

  function focusFloor(id: FloorId) {
    setSingle(id)
    setVisible((value) => ({ ...value, [id]: true }))
    setMode('single')
    setSelection(null)
  }

  function selectRoom(value: Selection) {
    setSelection(value)
    setSingle(value.floorId)
    setVisible((current) => ({ ...current, [value.floorId]: true }))
    setMode('single')
  }

  return <div className="app-shell">
    <header className="app-header">
      <a className="brand" href={import.meta.env.BASE_URL} aria-label="Dream Home, home">
        <span className="brand-mark"><Icon name="home" size={23} /></span>
        <span>dream<span className="brand-light">home</span><small>A PLACE TO BELONG</small></span>
      </a>
      <div className="header-middle"><span className="header-line" /> THE SPATIAL STUDY <span className="header-line" /></div>
      <button className="study-badge" onClick={() => setShowNotes(true)}><span className="status-dot" /> {study.study_id.replace('study-', 'Concept ')} <Icon name="info" size={15} /></button>
    </header>

    <div className="workspace">
      <aside className="sidebar" aria-label="House viewer controls">
        <div className="intro">
          <span className="eyebrow">A HOME, REIMAGINED</span>
          <h1>Room to<br /><em>imagine.</em></h1>
          <p>Open spaces. Quiet corners. A little closer to nature.</p>
        </div>

        <section className="control-section">
          <h2><span>01</span> Explore the house</h2>
          <div className="mode-buttons" aria-label="Presentation mode">
            {modes.map((item) => <button key={item.id} className={`mode-button ${mode === item.id ? 'is-active' : ''}`}
              onClick={() => changeMode(item.id)} aria-pressed={mode === item.id} title={item.description}>
              <Icon name={modeIcons[item.id]} size={19} /><span>{item.label}</span>
            </button>)}
          </div>
        </section>

        <section className="control-section">
          <h2><span>02</span> Find your level <small>CLICK TO FOCUS</small></h2>
          <div className="floor-list">
            {floors.map((floor) => {
              const shown = active.includes(floor.id)
              return <div className={`floor-row ${mode === 'single' && single === floor.id ? 'is-selected' : ''}`} key={floor.id}>
                <button className="floor-focus" onClick={() => focusFloor(floor.id)} aria-label={`Focus ${floor.title}`}>
                  <span className="floor-swatch" style={{ backgroundColor: floorColors[floor.id] }} />
                  <span><strong>{floor.title}</strong><small>{floor.id === 'roof' ? 'Planters, sunshine & slow mornings' : `${formatArea(floor.bounds.width * floor.bounds.depth / 0.09290304)} sq ft · Level ${floor.elevation_ft > 0 ? '+' : ''}${floor.elevation_ft} ft`}</small></span>
                </button>
                <button className={`icon-button visibility-button ${shown ? '' : 'is-muted'}`} aria-label={`${shown ? 'Hide' : 'Show'} ${floor.title}`}
                  aria-pressed={shown} disabled={mode === 'single' && single !== floor.id}
                  onClick={() => { setVisible((value) => ({ ...value, [floor.id]: !value[floor.id] })); setSelection(null) }}>
                  <Icon name={shown ? 'eye' : 'eyeOff'} size={17} />
                </button>
              </div>
            })}
          </div>
          <label className={`setting-row ${siteAllowed(mode, single) ? '' : 'is-muted'}`}>
            <span><Icon name="sun" size={17} /> Garden & site</span>
            <input type="checkbox" checked={visible.site && siteAllowed(mode, single)} disabled={!siteAllowed(mode, single)}
              onChange={(event) => setVisible((value) => ({ ...value, site: event.target.checked }))} />
          </label>
          {!siteAllowed(mode, single) && <p className="setting-hint">Available in assembled or ground-floor view.</p>}
        </section>

        <section className="control-section room-section">
          <h2><span>03</span> A closer look</h2>
          <label className="sr-only" htmlFor="room-select">Explore a room</label>
          <select id="room-select" value={selection ? `${selection.floorId}/${selection.roomId}` : ''} onChange={(event) => {
            if (!event.target.value) { setSelection(null); return }
            for (const floor of floors) {
              const selected = floor.rooms.find((item) => `${floor.id}/${item.id}` === event.target.value)
              if (selected) { selectRoom({ floorId: floor.id, roomId: selected.id }); return }
            }
          }}>
            <option value="">Choose a room to explore</option>
            {floors.map((floor) => <optgroup key={floor.id} label={floor.title}>{floor.rooms.map((item) =>
              <option key={item.id} value={`${floor.id}/${item.id}`}>{item.name}</option>)}</optgroup>)}
          </select>
          {room ? <div className="room-card" aria-live="polite">
            <div className="room-card-heading"><span className="eyebrow">PROPOSED SPACE</span><button className="icon-button" aria-label="Clear room selection" onClick={() => setSelection(null)}><Icon name="close" size={15} /></button></div>
            <h3>{room.name}</h3>
            <div className="room-dimensions"><strong>{room.width_ft} <span>×</span> {room.depth_ft}<small>{room.footprints.length > 1 ? ' FT EXTENTS' : ' FEET'}</small></strong><span>{formatArea(room.area_sq_ft)} sq ft</span></div>
            <p>{room.footprints.length > 1 ? 'Usable L-shaped area excludes the enclosed pantry; dimensions are outer extents.' : 'Candidate dimensions, not approved construction sizes.'}</p>
          </div> : <p className="room-hint">Pick a room here, or click its floor or furniture in the model.</p>}
          <a className="plan-link" href={`${import.meta.env.BASE_URL}plans/${planFloor}.svg`} target="_blank" rel="noreferrer">Open dimensioned {floors.find((floor) => floor.id === planFloor)?.title.toLowerCase()} plan <Icon name="arrow" size={16} /></a>
        </section>

        <div className="sidebar-foot"><span className="eyebrow">THE IDEA</span><p>A family retreat, designed around light, greenery and everyday life.</p><button className="text-button" onClick={() => setShowNotes(true)}>About this study <Icon name="arrow" size={15} /></button></div>
      </aside>

      <main className="viewer-panel" aria-label="Interactive 3D house viewer">
        <div className="viewer-heading">
          <div><span className="eyebrow">LIVE MODEL / {study.study_id.toUpperCase()}</span><h2>{mode === 'single' ? currentFloor?.title : mode === 'side-by-side' ? 'Every level. One vision.' : mode === 'stacked' ? 'The house, together.' : 'A little breathing room.'}</h2></div>
          <span className="model-status"><span className="status-dot" /> BLENDER → THREE.JS</span>
        </div>
        <div className="canvas-shell">
          <Suspense fallback={<div className="viewer-message" role="status"><h3>Preparing the 3D viewer…</h3></div>}>
            <HouseViewer mode={mode} visible={visible} single={single} cameraView={cameraView} showLabels={showLabels} showDimensions={showDimensions}
              selection={selection} resetKey={resetKey} onSelect={selectRoom} attempt={attempt} onRetry={() => setAttempt((value) => value + 1)} />
          </Suspense>
          {active.length === 0 && <div className="viewer-message empty-view"><h3>A blank canvas, for now.</h3><p>All floors are hidden.</p><button className="primary-button" onClick={() => setVisible(defaultVisibility())}>Show floors</button></div>}
        </div>
        <div className="viewer-toolbar" aria-label="Camera controls">
          <div className="camera-switch">
            <button className={cameraView === 'perspective' ? 'is-active' : ''} aria-pressed={cameraView === 'perspective'} onClick={() => setCameraView('perspective')}>3D view</button>
            <button className={cameraView === 'plan' ? 'is-active' : ''} aria-pressed={cameraView === 'plan'} onClick={() => setCameraView('plan')}>Floor plan</button>
          </div>
          <span className="toolbar-divider" />
          <button className={`toolbar-button ${showLabels ? 'is-active' : ''}`} aria-pressed={showLabels} onClick={() => setShowLabels((value) => !value)}>Labels</button>
          <button className={`toolbar-button ${showDimensions ? 'is-active' : ''}`} aria-pressed={showDimensions} onClick={() => setShowDimensions((value) => !value)}>Dimensions</button>
          <span className="toolbar-divider" />
          <button className="toolbar-button reset-button" onClick={() => { setSelection(null); setResetKey((value) => value + 1) }}><Icon name="reset" size={16} /><span>Reset view</span></button>
        </div>
        <div className="viewer-caption"><span><span className="north-marker">↑</span> BACK / GARDEN <small>Orientation illustrative</small></span><p>Drag to orbit <i /> Scroll to zoom <i /> Right-drag to pan<br /><small>Touch: one finger to orbit · pinch / two fingers to zoom and pan</small></p></div>
      </main>
    </div>
    <footer className="app-footer"><span><span className="status-dot" /> A LIVING DESIGN STUDY <span className="footer-separator">/</span> NOT AN APPROVED BUILDING PLAN</span><span>{study.site.width_ft} × {study.site.depth_ft} FT STUDY PLOT <span className="footer-separator">·</span> {(study.model_bytes / 1_000_000).toFixed(2)} MB MODEL</span></footer>
    {showNotes && <NotesDialog onClose={() => setShowNotes(false)}>
        <button className="icon-button dialog-close" aria-label="Close study notes" onClick={() => setShowNotes(false)} autoFocus><Icon name="close" /></button>
        <span className="eyebrow">DREAM HOME / {study.study_id.replace('study-', 'Concept ').toUpperCase()}</span><h2 id="study-title">An idea, not a blueprint.</h2>
        <p>This is the refined Blender cutaway study, with detailed furniture and local PBR finishes. The browser uses the same geometry, with presentation transforms for each view—not a different house. The Study 003 layout is unchanged.</p>
        <p>Dimensions shows candidate floor-plate sizes, or the selected room’s outer extents, in feet and metres. Net areas exclude enclosed child spaces where indicated. These are design-study annotations, not surveyed or construction dimensions.</p>
        <p><strong>The proposed 7,000 sq ft plot is 40% above the initial upper target.</strong> Dimensions, engineering, cost and the layout itself still need review.</p>
        <p>Orbit inspection is available. First-person walking is not enabled: collision, stairs and safety boundaries need a separate implementation and review.</p>
        <details><summary>All feasibility and design notes</summary><ul>{study.review_items.map((item) => <li key={item}>{item}</li>)}</ul></details>
        <button className="primary-button" onClick={() => setShowNotes(false)}>Back to exploring <Icon name="arrow" size={16} /></button>
    </NotesDialog>}
  </div>
}
