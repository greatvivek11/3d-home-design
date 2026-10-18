import { lazy, Suspense, useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import Icon from './Icon'
import type { IconName } from './Icon'
import {
  defaultVisibility, displayedFloors, findRoom, floorColors, floors, formatArea, formatFeet, modes, siteAllowed, study,
} from './model'
import type { CameraView, FloorId, Inspection, Selection, ViewMode, Visibility } from './model'

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
  const [inspection, setInspection] = useState<Inspection>('furnished')
  const [showLabels, setShowLabels] = useState(true)
  const [showDimensions, setShowDimensions] = useState(true)
  const [showCovers, setShowCovers] = useState(false)
  const [studioQuality, setStudioQuality] = useState(true)
  const [smallScreen, setSmallScreen] = useState(() => !window.matchMedia('(min-width: 1024px)').matches)
  const [selection, setSelection] = useState<Selection | null>(null)
  const [resetKey, setResetKey] = useState(0)
  const [attempt, setAttempt] = useState(0)
  const [showNotes, setShowNotes] = useState(false)
  const active = displayedFloors(mode, visible, single)
  const room = findRoom(selection)
  const currentFloor = floors.find((floor) => floor.id === single)
  const planFloor = selection?.floorId ?? single
  useEffect(() => {
    const query = window.matchMedia('(min-width: 1024px)')
    const update = () => setSmallScreen(!query.matches)
    query.addEventListener('change', update)
    return () => query.removeEventListener('change', update)
  }, [])

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
          <div className="inspection-switch" aria-label="Inspection layer">
            <button aria-pressed={inspection === 'furnished'} className={inspection === 'furnished' ? 'is-active' : ''}
              onClick={() => setInspection('furnished')}>Furnished</button>
            <button aria-pressed={inspection === 'structure'} className={inspection === 'structure' ? 'is-active' : ''}
              onClick={() => setInspection('structure')}>Structural intent</button>
          </div>
          {inspection === 'structure' && <p className="setting-hint">Teal: support proxies. Ochre: beam proxies. Pale zones: requested clear spans, not proven feasible.</p>}
          <label className={`setting-row ${inspection === 'structure' ? 'is-muted' : ''}`}>
            <span>Weather covers</span>
            <input type="checkbox" checked={showCovers && inspection === 'furnished'} disabled={inspection === 'structure'}
              onChange={(event) => setShowCovers(event.target.checked)} />
          </label>
          <label className={`setting-row ${smallScreen || inspection === 'structure' ? 'is-muted' : ''}`}>
            <span>Studio quality</span>
            <input type="checkbox" checked={studioQuality && !smallScreen && inspection === 'furnished'} disabled={smallScreen || inspection === 'structure'}
              onChange={(event) => setStudioQuality(event.target.checked)} />
          </label>
          <p className="setting-hint">{smallScreen ? 'Balanced rendering on small screens. ' : 'Studio adds ambient depth and sharper contact shadows. '}Covers start hidden for cutaway inspection.</p>
        </section>

        <section className="control-section">
          <h2><span>02</span> Find your level <small>CLICK TO FOCUS</small></h2>
          <div className="floor-list">
            {floors.map((floor) => {
              const shown = active.includes(floor.id)
              return <div className={`floor-row ${mode === 'single' && single === floor.id ? 'is-selected' : ''}`} key={floor.id}>
                <button className="floor-focus" onClick={() => focusFloor(floor.id)} aria-label={`Focus ${floor.title}`}>
                  <span className="floor-swatch" style={{ backgroundColor: floorColors[floor.id] }} />
                  <span><strong>{floor.title}</strong><small>{floor.id === 'roof' ? 'Planters, sunshine & slow mornings' : `${formatArea(floor.area_sq_ft)} sq ft · Level ${floor.elevation_ft > 0 ? '+' : ''}${floor.elevation_ft} ft`}</small></span>
                </button>
                <button className={`icon-button visibility-button ${shown ? '' : 'is-muted'}`} aria-label={`${shown ? 'Hide' : 'Show'} ${floor.title}`}
                  aria-pressed={shown} disabled={mode === 'single' && single !== floor.id}
                  onClick={() => { setVisible((value) => ({ ...value, [floor.id]: !value[floor.id] })); setSelection(null) }}>
                  <Icon name={shown ? 'eye' : 'eyeOff'} size={17} />
                </button>
              </div>
            })}
          </div>
          <label className={`setting-row ${siteAllowed(mode, single) && inspection === 'furnished' ? '' : 'is-muted'}`}>
            <span><Icon name="sun" size={17} /> Garden & site</span>
            <input type="checkbox" checked={visible.site && siteAllowed(mode, single) && inspection === 'furnished'} disabled={!siteAllowed(mode, single) || inspection === 'structure'}
              onChange={(event) => setVisible((value) => ({ ...value, site: event.target.checked }))} />
          </label>
          {(!siteAllowed(mode, single) || inspection === 'structure') && <p className="setting-hint">Available in furnished assembled or ground-floor view.</p>}
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
            <div className="room-dimensions"><strong>{formatFeet(room.width_ft)} <span>×</span> {formatFeet(room.depth_ft)}<small>{room.footprints.length > 1 ? ' FT EXTENTS' : ' FEET'}</small></strong><span>{formatArea(room.area_sq_ft)} sq ft</span></div>
            <p>{room.footprints.length > 1 ? 'Net area excludes enclosed rooms and shafts; dimensions are outer extents.' : 'Candidate dimensions, not approved construction sizes.'}</p>
          </div> : <p className="room-hint">Room names and sizes appear as you zoom in. Pick a room here, or click its floor/furniture, for dimension lines.</p>}
          <a className="plan-link" href={`${import.meta.env.BASE_URL}plans/${planFloor}.svg`} target="_blank" rel="noreferrer">Open dimensioned {floors.find((floor) => floor.id === planFloor)?.title.toLowerCase()} plan <Icon name="arrow" size={16} /></a>
        </section>

        <div className="sidebar-foot"><span className="eyebrow">THE IDEA</span><p>A family retreat, designed around light, greenery and everyday life.</p><button className="text-button" onClick={() => setShowNotes(true)}>About this study <Icon name="arrow" size={15} /></button></div>
      </aside>

      <main className="viewer-panel" aria-label="Interactive 3D house viewer">
        <div className="viewer-heading">
          <div><span className="eyebrow">LIVE MODEL / {study.study_id.toUpperCase()}</span><h2>{inspection === 'structure' ? `${mode === 'single' ? currentFloor?.title : 'The house'} / conceptual frame` : mode === 'single' ? currentFloor?.title : mode === 'side-by-side' ? 'Every level. One vision.' : mode === 'stacked' ? 'The house, together.' : 'A little breathing room.'}</h2></div>
          <span className="model-status"><span className="status-dot" /> BLENDER → THREE.JS</span>
        </div>
        <div className="canvas-shell">
          <Suspense fallback={<div className="viewer-message" role="status"><h3>Preparing the 3D viewer…</h3></div>}>
            <HouseViewer mode={mode} visible={visible} single={single} cameraView={cameraView} inspection={inspection} showLabels={showLabels} showDimensions={showDimensions} showCovers={showCovers} studioQuality={studioQuality && !smallScreen}
              selection={selection} resetKey={resetKey} onSelect={selectRoom} attempt={attempt} onRetry={() => setAttempt((value) => value + 1)} />
          </Suspense>
          {inspection === 'structure' && <div className="structural-warning" role="note">
            <strong>STRUCTURAL INTENT ONLY — NOT ENGINEERED</strong>
            <span>Display proxies, not member sizes. Column-free living/parking is unverified; an engineer may require internal supports or transfer structure.</span>
          </div>}
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
        <p>This is {study.study_id.replace('study-', 'Study ')}: the restored spacious 7,000 sq ft direction. Drawing and guest rooms sit in front, divided by Entrance Gallery; House Gallery separates them from the rear master and family spaces, with common WC left and utility cupboard right. Upstairs, front office/Child 1 and two rear child bedrooms are divided by a transverse lounge. Larger gardens and an 8 × 16 ft pool return. The front-lawn lift retains internal stair access, with no external link or extra side strip. Basement and roof functions remain, with aligned footprints. The browser uses the same Blender geometry with real-time studio lighting and ambient occlusion.</p>
        <p>Entrance and House Galleries remain 4 ft; the wider guest room is 157 sq ft net. The approved 4 × 2 ft cupboard faces left at the gallery’s terminal right end, outside living; living regains its floor and is now 343.5 sq ft net. A separate 3 ft master passage leads into the bedroom, then private dressing and bathroom. All three child sleeping rooms remain 272 sq ft. The office is 204 sq ft, placing Child 1’s suite in the front band. The unified lounge is now 653 sq ft net after its smaller 6 × 5.5 ft shared WC beside stairs, with no east/west galleries. Dimensions are modeled zones/openings, not certified finished clearances. Ground is proposed 1.5 ft above road; raised rear grade, pool enclosure/deck, drainage, structure, independent parking and accessibility remain unverified. Stair/lift dimensions are reserves, not approved headroom or fire/escape design. A single controlled front entrance does not mean a single emergency exit. Enclosed child-room areas are deducted from their parent rooms, not counted twice.</p>
        <p>Labels and room sizes appear when there is enough screen space; zoom or focus a floor to see smaller rooms. Select a room for dimension lines in feet/metres. Net areas exclude enclosed rooms/shafts. In assembled view, room tags annotate only the uppermost visible floor so hidden rooms are not labelled through slabs.</p>
        <p><strong>Structural intent is not an engineered design.</strong> Teal supports and ochre beams are display proxies, not proposed sections or a proven load path. Pale areas show the requested clear-span living/parking zones. Long spans may need transfer systems, greater depth, internal columns or layout changes; professional structural/seismic review is essential.</p>
        <p>The driveway has a flared curved entry into the rear turning aisle; cars are at the front of the garage compartment, not the recreation area. Its sampled large-SUV body/overhang and vertical-clearance checks are concepts, not traffic engineering. Independent parking manoeuvres and the street approach remain unverified.</p>
        <p>Use Weather covers to inspect the roof stair enclosure and open-sided driveway canopy. A roof does not make the basement flood-proof or exclude windblown dust; drainage, pumping, ventilation and weather/structural design need specialists.</p>
        <p><strong>The proposed {formatArea(study.site.area_sq_ft)} sq ft plot is larger than the initial target.</strong> It stays within the permitted study allowance, not an approved site, budget or building plan. Floor areas include the external lift annex rather than the empty corners of a bounding rectangle.</p>
        <p>Orbit inspection is available. First-person walking is not enabled: collision, stairs and safety boundaries need a separate implementation and review.</p>
        <details><summary>All feasibility and design notes</summary><ul>{study.review_items.map((item) => <li key={item}>{item}</li>)}</ul></details>
        <button className="primary-button" onClick={() => setShowNotes(false)}>Back to exploring <Icon name="arrow" size={16} /></button>
    </NotesDialog>}
  </div>
}
