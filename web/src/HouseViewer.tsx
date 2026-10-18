import { Component, Suspense, useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import type { ComponentRef, ErrorInfo, ReactNode, RefObject } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import type { ThreeEvent } from '@react-three/fiber'
import { OrbitControls, useGLTF, useProgress } from '@react-three/drei'
import { AgXToneMapping, Box3, DirectionalLight, HalfFloatType, Mesh, MeshStandardMaterial, Object3D, OrthographicCamera, PCFShadowMap, PMREMGenerator, SRGBColorSpace, Vector3, WebGLRenderTarget } from 'three'
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js'
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js'
import { GTAOPass } from 'three/addons/postprocessing/GTAOPass.js'
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js'
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js'
import {
  annotationFloors, dimensionLines, displayedFloors, findRoom, floorPosition, floors, formatFeet, roomLabelAnchor, siteAllowed, sitePosition, study, visibleRoomAnnotations,
} from './model'
import type { CameraView, DimensionLine, FloorId, Inspection, LayerId, RoomAnnotation, Selection, ViewMode, Visibility } from './model'

type Measurement = DimensionLine & { key: string; floorId: FloorId }
const roomMarkers = floors.flatMap((floor) => floor.rooms.map((room) => ({
  key: `${floor.id}/${room.id}`, floorId: floor.id, room, anchor: roomLabelAnchor(room),
})))

type Props = {
  mode: ViewMode
  visible: Visibility
  single: FloorId
  cameraView: CameraView
  inspection: Inspection
  showLabels: boolean
  showDimensions: boolean
  showCovers: boolean
  studioQuality: boolean
  selection: Selection | null
  resetKey: number
  onSelect: (selection: Selection) => void
}

function StudioLighting({ controls, sceneKey, studio }: {
  controls: RefObject<ComponentRef<typeof OrbitControls> | null>
  sceneKey: string
  studio: boolean
}) {
  const { gl, scene, invalidate } = useThree()
  const sun = useRef<DirectionalLight>(null)
  const target = useMemo(() => new Object3D(), [])
  const offset = useMemo(() => new Vector3(-0.55, 1, 0.65).normalize().multiplyScalar(100), [])
  const previous = useRef({ span: 0, target: new Vector3(Infinity, Infinity, Infinity) })
  useEffect(() => {
    const generator = new PMREMGenerator(gl)
    const room = new RoomEnvironment()
    const environment = generator.fromScene(room, 0.04)
    const original = scene.environment
    scene.environment = environment.texture
    scene.environmentIntensity = 0.5
    invalidate()
    return () => {
      scene.environment = original
      environment.dispose()
      generator.dispose()
      room.dispose()
    }
  }, [gl, scene, invalidate])
  useEffect(() => {
    scene.environmentIntensity = studio ? 0.6 : 0.5
    gl.toneMappingExposure = studio ? 0.9 : 1
    invalidate()
  }, [studio, gl, scene, invalidate])
  useLayoutEffect(() => {
    if (sun.current) {
      const shadow = sun.current.shadow
      if (shadow.map && shadow.map.width !== shadow.mapSize.x) {
        shadow.map.dispose()
        shadow.map = null
      }
      shadow.needsUpdate = true
    }
    invalidate()
  }, [sceneKey, invalidate])
  useFrame(({ camera }) => {
    const light = sun.current
    const focus = controls.current?.target
    if (!light || !focus || !(camera instanceof OrthographicCamera)) return
    const span = Math.max(camera.right - camera.left, camera.top - camera.bottom) / camera.zoom * 0.72 + 3
    if (Math.abs(previous.current.span - span) < 0.005 && previous.current.target.distanceToSquared(focus) < 0.000025) return
    previous.current.span = span
    previous.current.target.copy(focus)
    target.position.copy(focus)
    target.updateMatrixWorld()
    light.position.copy(focus).add(offset)
    const shadow = light.shadow.camera
    shadow.left = shadow.bottom = -span
    shadow.right = shadow.top = span
    shadow.near = 1
    shadow.far = 240
    shadow.updateProjectionMatrix()
    light.shadow.needsUpdate = true
  })
  return <>
    <primitive object={target} />
    <hemisphereLight args={['#fff7ea', '#9ba79b', studio ? 0.28 : 0.5]} />
    <directionalLight ref={sun} target={target} castShadow intensity={studio ? 3 : 2.6} color="#fff1da"
      shadow-mapSize={[studio ? 4096 : 2048, studio ? 4096 : 2048]} shadow-bias={-0.00003} shadow-normalBias={0.003} shadow-autoUpdate={false} />
    <directionalLight position={[25, 40, -40]} intensity={studio ? 0.35 : 0.7} color="#e4edff" />
  </>
}

function StudioEffects({ enabled }: { enabled: boolean }) {
  const { gl, scene, camera, size, invalidate, viewport } = useThree()
  const pipeline = useRef<{ composer: EffectComposer; ao: GTAOPass } | null>(null)
  useEffect(() => {
    if (!enabled) return
    const target = new WebGLRenderTarget(1, 1, { type: HalfFloatType })
    target.samples = Math.min(4, gl.capabilities.maxSamples)
    const composer = new EffectComposer(gl, target)
    const render = new RenderPass(scene, camera)
    const ao = new GTAOPass(scene, camera)
    ao.updateGtaoMaterial({ radius: 0.5, thickness: 1, distanceFallOff: 0.6, scale: 1, samples: 8, screenSpaceRadius: false })
    ao.updatePdMaterial({ radius: 5, samples: 8, rings: 2 })
    ao.blendIntensity = 1
    const output = new OutputPass()
    composer.addPass(render)
    composer.addPass(ao)
    composer.addPass(output)
    pipeline.current = { composer, ao }
    invalidate()
    return () => {
      pipeline.current = null
      render.dispose()
      ao.dispose()
      output.dispose()
      composer.dispose()
    }
  }, [enabled, gl, scene, camera, invalidate])
  useEffect(() => {
    const current = pipeline.current
    if (!current) return
    current.composer.setSize(size.width, size.height)
    const ratio = gl.getPixelRatio() * 0.7
    current.ao.setSize(Math.max(1, Math.ceil(size.width * ratio)), Math.max(1, Math.ceil(size.height * ratio)))
    invalidate()
  }, [size.width, size.height, viewport.dpr, gl, enabled, invalidate])
  useFrame((state, delta) => {
    if (enabled && pipeline.current) pipeline.current.composer.render(delta)
    else state.gl.render(state.scene, state.camera)
  }, 1)
  return null
}

class ViewerBoundary extends Component<{ children: ReactNode; onRetry: () => void }, { error: Error | null }> {
  state: { error: Error | null } = { error: null }
  static getDerivedStateFromError(error: Error) { return { error } }
  componentDidCatch(error: Error, info: ErrorInfo) { console.error('House viewer failed:', error, info.componentStack) }
  render() {
    if (this.state.error) {
      return <div className="viewer-message" role="alert">
        <span className="message-symbol">!</span>
        <h3>The 3D model could not be opened.</h3>
        <p>Check your connection and WebGL support, then try again. Dimensioned plans are still available below the room selector.</p>
        <details><summary>Error details</summary><p>{this.state.error.message}</p></details>
        <button className="primary-button" onClick={this.props.onRetry}>Try again</button>
      </div>
    }
    return this.props.children
  }
}

function LoadingModel() {
  const { progress } = useProgress()
  return <div className="loading-card" role="status">
    <div className="loading-line"><span style={{ width: `${Math.max(4, progress)}%` }} /></div>
    <strong>Bringing your home into view</strong>
    <span>Loading the Blender study · {Math.round(progress)}%</span>
  </div>
}

function Model(props: Props & {
  attempt: number
  labelRefs: RefObject<Partial<Record<FloorId, HTMLDivElement | null>>>
  roomRefs: RefObject<Map<string, HTMLDivElement>>
  dimensionRefs: RefObject<Map<string, SVGGElement>>
  measurements: Measurement[]
  onReady: () => void
}) {
  const { mode, visible, single, cameraView, inspection, showLabels, showDimensions, showCovers, studioQuality, selection, resetKey, onSelect, attempt, labelRefs, roomRefs, dimensionRefs, measurements, onReady } = props
  const gltf = useGLTF(`${import.meta.env.BASE_URL}models/house.glb?v=${study.revision}&attempt=${attempt}`)
  const { size, camera, invalidate, gl } = useThree()
  const compact = size.width < 700
  const studio = studioQuality && !compact && inspection === 'furnished'
  const controls = useRef<ComponentRef<typeof OrbitControls>>(null)
  const labelPoint = useMemo(() => new Vector3(), [])
  const roots = useMemo(() => {
    const result = new Map<LayerId, { object: Object3D; architecture: Object3D; structure: Object3D | undefined; bounds: Box3; frameBounds: Box3 }>()
    for (const id of ['site', ...floors.map((floor) => floor.id)] as const) {
      const source = gltf.scene.getObjectByName(`floor_${id}`)
      if (!source) throw new Error(`The exported model is missing floor_${id}. Regenerate its GLB.`)
      const object = source.clone(true)
      object.updateWorldMatrix(true, true)
      const architecture = object.getObjectByName(`architecture_${id}`)
      const structure = object.getObjectByName(`structure_${id}`)
      if (!architecture || (id !== 'site' && !structure)) throw new Error(`The exported ${id} layer is missing an inspection group. Regenerate its GLB.`)
      const bounds = new Box3().setFromObject(architecture)
      const frameBounds = structure ? new Box3().setFromObject(structure) : bounds
      if (bounds.isEmpty()) throw new Error(`The exported ${id} layer is empty`)
      object.traverse((node) => {
        if (node instanceof Mesh) {
          const materials = Array.isArray(node.material) ? node.material : [node.material]
          node.castShadow = !materials.every((material) => material.transparent && material.opacity < 0.5)
          node.receiveShadow = true
          for (const material of materials) {
            if (!(material instanceof MeshStandardMaterial)) continue
            for (const texture of [material.map, material.normalMap, material.roughnessMap, material.metalnessMap]) {
              if (texture) {
                texture.anisotropy = Math.min(16, gl.capabilities.getMaxAnisotropy())
                texture.needsUpdate = true
              }
            }
          }
        }
      })
      result.set(id, { object, architecture, structure, bounds, frameBounds })
    }
    return result
  }, [gltf.scene, gl])
  const active = useMemo(() => displayedFloors(mode, visible, single), [mode, visible, single])
  const includeSite = inspection === 'furnished' && visible.site && siteAllowed(mode, single)
  const selectedRoom = findRoom(selection)
  const site = roots.get('site')
  if (!site) throw new Error('Missing garden/site geometry')
  const driveway = useMemo(() => {
    const source = roots.get('site')
    if (!source) throw new Error('Missing driveway source')
    const context = source.object.clone(true)
    context.name = 'basement_driveway_context'
    const basement = floors.find((floor) => floor.id === 'basement')
    if (!basement) throw new Error('Missing basement level')
    context.position.y -= basement.elevation_m
    context.traverse((node) => {
      if (node instanceof Mesh) node.visible = node.userData.context_group === 'driveway'
    })
    context.updateWorldMatrix(true, true)
    return context
  }, [roots])
  const showDriveway = inspection === 'furnished' && active.includes('basement')
    && ((mode === 'single' && single === 'basement') || (mode === 'stacked' && !includeSite))

  useEffect(onReady, [onReady])
  useLayoutEffect(() => {
    for (const root of roots.values()) {
      root.architecture.visible = inspection === 'furnished'
      if (root.structure) root.structure.visible = inspection === 'structure'
      root.object.traverse((node) => {
        if (node instanceof Mesh && node.userData.weather_cover) node.visible = showCovers
      })
    }
    driveway.traverse((node) => {
      if (node instanceof Mesh && node.userData.weather_cover) node.visible = showCovers
    })
    invalidate()
  }, [roots, driveway, inspection, showLabels, showDimensions, showCovers, invalidate])
  useFrame(({ camera, size }) => {
    for (const floor of floors) {
      const element = labelRefs.current[floor.id]
      if (!element) continue
      const [x, y, z] = floorPosition(floor.id, mode, compact)
      labelPoint.set(floor.bounds.x + floor.bounds.width / 2 + x, 1.7 + y, floor.bounds.z - 1.5 + z).project(camera)
      element.hidden = !showLabels || !active.includes(floor.id) || labelPoint.z < -1 || labelPoint.z > 1
      element.style.transform = `translate3d(${(labelPoint.x + 1) * size.width / 2}px, ${(1 - labelPoint.y) * size.height / 2}px, 0) translate(-50%, -50%)`
    }
    const annotated = annotationFloors(mode, active)
    const candidates: RoomAnnotation[] = []
    for (const marker of roomMarkers) {
      const element = roomRefs.current.get(marker.key)
      if (!element) continue
      element.hidden = true
      if ((!showLabels && !showDimensions) || !annotated.includes(marker.floorId)) continue
      if (inspection === 'structure' && !['lift', 'stairs'].includes(marker.room.kind)
          && !study.structure.clear_span_zones.some((zone) => zone.floor_id === marker.floorId && zone.room_id === marker.room.id)) continue
      const offset = new Vector3(...floorPosition(marker.floorId, mode, compact))
      labelPoint.set(...marker.anchor).add(offset).project(camera)
      if (Math.abs(labelPoint.z) > 1) continue
      const x = (labelPoint.x + 1) * size.width / 2, y = (1 - labelPoint.y) * size.height / 2
      const b = marker.room.bounds
      const corners = [[b.x, b.z], [b.x + b.width, b.z], [b.x, b.z + b.depth]].map(([px, pz]) => {
        labelPoint.set(px, marker.anchor[1], pz).add(offset).project(camera)
        return [(labelPoint.x + 1) * size.width / 2, (1 - labelPoint.y) * size.height / 2]
      })
      const projectedWidth = Math.hypot(corners[1][0] - corners[0][0], corners[1][1] - corners[0][1])
      const projectedHeight = Math.hypot(corners[2][0] - corners[0][0], corners[2][1] - corners[0][1])
      const sizeText = `${formatFeet(marker.room.width_ft)} × ${formatFeet(marker.room.depth_ft)} ft${marker.room.footprints.length > 1 ? ' ext.' : ''}`
      const contentWidth = Math.max(showLabels ? marker.room.label.length * 5.2 + 12 : 0, showDimensions ? sizeText.length * 4.8 + 12 : 0)
      const width = Math.min(150, contentWidth, Math.max(48, projectedWidth - 4))
      const lines = showLabels ? Math.min(2, Math.ceil(marker.room.label.length * 5.2 / (width - 12))) : 0
      const height = 8 + lines * 12 + (showDimensions ? 12 : 0)
      const selected = selection?.floorId === marker.floorId && selection.roomId === marker.room.id
      const primary = ['bedroom', 'living', 'office', 'recreation', 'kitchen'].includes(marker.room.kind)
      candidates.push({ key: marker.key, x, y, width, height, projectedWidth, projectedHeight, priority: selected ? 100 : primary ? 20 : 10 })
      element.style.width = `${width}px`
      element.style.transform = `translate3d(${x}px, ${y}px, 0) translate(-50%, -50%)`
    }
    for (const key of visibleRoomAnnotations(candidates, size.width, size.height, inspection === 'structure' ? (size.width < 700 ? 105 : 65) : 0)) {
      const element = roomRefs.current.get(key)
      if (element) element.hidden = false
    }
    for (const dimension of measurements) {
      const element = dimensionRefs.current.get(dimension.key)
      if (!element) continue
      const offset = new Vector3(...floorPosition(dimension.floorId, mode, compact))
      const points = [dimension.start, dimension.end, dimension.from, dimension.to].map((position) => {
        labelPoint.set(...position).add(offset).project(camera)
        return { x: (labelPoint.x + 1) * size.width / 2, y: (1 - labelPoint.y) * size.height / 2, z: labelPoint.z }
      })
      const [a, b, from, to] = points
      const dx = b.x - a.x, dy = b.y - a.y
      const length = Math.hypot(dx, dy)
      const shown = showDimensions && active.includes(dimension.floorId) && points.every((point) => Math.abs(point.z) <= 1) && length >= 70
      element.setAttribute('visibility', shown ? 'visible' : 'hidden')
      if (!shown) continue
      element.ownerSVGElement?.setAttribute('viewBox', `0 0 ${size.width} ${size.height}`)
      const tx = (dx - dy) / length * 3, ty = (dy + dx) / length * 3
      element.querySelector('path')?.setAttribute('d',
        `M${from.x},${from.y} L${a.x},${a.y} L${b.x},${b.y} L${to.x},${to.y} M${a.x - tx},${a.y - ty} l${tx * 2},${ty * 2} M${b.x - tx},${b.y - ty} l${tx * 2},${ty * 2}`)
      let angle = Math.atan2(dy, dx) * 180 / Math.PI
      if (angle > 90) angle -= 180
      if (angle < -90) angle += 180
      const side = dimension.id === 'width' ? 1 : -1
      element.querySelector('text')?.setAttribute('transform',
        `translate(${(a.x + b.x) / 2 - dy / length * 13 * side},${(a.y + b.y) / 2 + dx / length * 13 * side}) rotate(${angle})`)
    }
  })

  useLayoutEffect(() => {
    const orbit = controls.current
    if (!(camera instanceof OrthographicCamera) || !orbit) return
    const bounds = new Box3()
    if (selection && selectedRoom && active.includes(selection.floorId)) {
      const b = selectedRoom.bounds
      const position = new Vector3(...floorPosition(selection.floorId, mode, compact))
      const root = roots.get(selection.floorId)
      if (!root) throw new Error(`Missing selected floor: ${selection.floorId}`)
      const tall = selectedRoom.kind === 'stairs' || (showCovers && selectedRoom.kind === 'lift') || inspection === 'structure'
      bounds.set(new Vector3(b.x, 0, b.z), new Vector3(b.x + b.width, tall ? Math.max(3.5, root.bounds.max.y) : 2.2, b.z + b.depth)).translate(position)
    } else {
      for (const id of active) {
        const source = roots.get(id)
        if (source) bounds.union((inspection === 'structure' ? source.frameBounds : source.bounds).clone().translate(new Vector3(...floorPosition(id, mode, compact))))
      }
      if (includeSite) {
        const site = roots.get('site')
        if (site) bounds.union(site.bounds.clone().translate(new Vector3(...sitePosition(mode))))
      }
      if (showDriveway) {
        driveway.updateWorldMatrix(true, true)
        const contextBounds = new Box3()
        driveway.traverse((node) => {
          if (node instanceof Mesh && node.visible) contextBounds.expandByObject(node)
        })
        bounds.union(contextBounds.translate(new Vector3(...floorPosition('basement', mode, compact))))
      }
    }
    if (bounds.isEmpty()) return
    const target = bounds.getCenter(new Vector3())
    const direction = cameraView === 'plan' ? new Vector3(0, 1, 0.0001) : new Vector3(0.26, 1, 0.72).normalize()
    camera.position.copy(target).addScaledVector(direction, 180)
    orbit.target.copy(target)
    camera.lookAt(target)
    camera.updateMatrixWorld()
    const projected = new Box3()
    for (const x of [bounds.min.x, bounds.max.x]) {
      for (const y of [bounds.min.y, bounds.max.y]) {
        for (const z of [bounds.min.z, bounds.max.z]) {
          projected.expandByPoint(new Vector3(x, y, z).applyMatrix4(camera.matrixWorldInverse))
        }
      }
    }
    const extent = projected.getSize(new Vector3())
    camera.zoom = Math.max(1, Math.min(size.width / Math.max(extent.x, 1), size.height / Math.max(extent.y, 1)) * 0.79)
    camera.updateProjectionMatrix()
    orbit.update()
    invalidate()
  }, [mode, visible, single, cameraView, inspection, selection, selectedRoom, resetKey, size.width, size.height, compact, camera, invalidate, roots, includeSite, active, driveway, showDriveway, showCovers])

  function pick(event: ThreeEvent<MouseEvent>, floorId: FloorId) {
    if (!active.includes(floorId) || event.delta > 5) return
    event.stopPropagation()
    const roomId: unknown = event.object.userData.room_id
    if (typeof roomId === 'string' && floors.find((floor) => floor.id === floorId)?.rooms.some((room) => room.id === roomId)) {
      onSelect({ floorId, roomId })
    }
  }

  return <>
    <OrbitControls ref={controls} makeDefault enableDamping dampingFactor={0.12} minZoom={1} maxZoom={800} maxPolarAngle={Math.PI / 2.02} />
    <StudioLighting controls={controls} sceneKey={`${mode}:${inspection}:${active.join(',')}:${includeSite}:${showCovers}:${studio}`} studio={studio} />
    <StudioEffects enabled={studio} />
    {floors.map((floor) => {
      const root = roots.get(floor.id)
      if (!root) throw new Error(`Missing ${floor.id} geometry`)
      const shown = active.includes(floor.id)
      return <group key={floor.id} position={floorPosition(floor.id, mode, compact)} visible={shown}
        onClick={shown ? (event) => pick(event, floor.id) : undefined} dispose={null}>
        <primitive object={root.object} />
        {floor.id === 'basement' && <group visible={showDriveway}><primitive object={driveway} /></group>}
        {selection?.floorId === floor.id && selectedRoom && selectedRoom.footprints.map((part, index) => <mesh key={index}
          position={[part.x + part.width / 2, 0.11, part.z + part.depth / 2]}
          rotation={[-Math.PI / 2, 0, 0]} raycast={() => undefined}>
          <planeGeometry args={[part.width, part.depth]} />
          <meshBasicMaterial color="#c18a42" transparent opacity={0.06} depthWrite={false} />
        </mesh>)}
      </group>
    })}
    <group position={sitePosition(mode)} visible={includeSite} onClick={includeSite ? (event) => event.stopPropagation() : undefined} dispose={null}><primitive object={site.object} /></group>
  </>
}

function ViewerScene(props: Props & { attempt: number }) {
  const [loaded, setLoaded] = useState(false)
  const [started, setStarted] = useState(false)
  const labelRefs = useRef<Partial<Record<FloorId, HTMLDivElement | null>>>({})
  const roomRefs = useRef(new Map<string, HTMLDivElement>())
  const dimensionRefs = useRef(new Map<string, SVGGElement>())
  const active = displayedFloors(props.mode, props.visible, props.single)
  const room = findRoom(props.selection)
  const sources = props.selection && room && active.includes(props.selection.floorId)
    ? [{ floorId: props.selection.floorId, bounds: room.bounds, width: room.width_ft, depth: room.depth_ft, offset: 0.3 }]
    : floors.filter((floor) => active.includes(floor.id)).map((floor) => ({
      floorId: floor.id, bounds: floor.bounds, width: floor.bounds.width / 0.3048, depth: floor.bounds.depth / 0.3048, offset: floor.id === 'first' ? 2.4 : 0.6,
    }))
  const measurements = sources.flatMap((source) => dimensionLines(source.bounds, source.width, source.depth, source.offset)
    .map((line) => ({ ...line, key: `${source.floorId}-${line.id}`, floorId: source.floorId })))
  const onReady = useCallback(() => setLoaded(true), [])
  return <>
    <Canvas orthographic camera={{ position: [40, 70, 40], zoom: 12, near: 0.1, far: 800 }} frameloop="demand"
      onCreated={({ gl }) => { gl.toneMapping = AgXToneMapping; gl.outputColorSpace = SRGBColorSpace; setStarted(true) }}
      shadows={{ type: PCFShadowMap }} dpr={[1, 2]} gl={{ antialias: true, alpha: true }}
      fallback={<div className="viewer-message" role="alert"><h3>Your browser cannot start WebGL.</h3><p>Try hardware acceleration or another browser. You can still open the dimensioned plans from the sidebar.</p></div>}>
      <Suspense fallback={null}><Model {...props} labelRefs={labelRefs} roomRefs={roomRefs} dimensionRefs={dimensionRefs} measurements={measurements} onReady={onReady} /></Suspense>
    </Canvas>
    {loaded ? <span className="sr-only" role="status">3D house model loaded</span> : started && <LoadingModel />}
    <div className="floor-labels" aria-hidden="true">
      {floors.map((floor, index) => <div key={floor.id} className="floor-tag" hidden
        ref={(element) => { labelRefs.current[floor.id] = element }}>
        <span>{String(index + 1).padStart(2, '0')}</span>{floor.title}
      </div>)}
    </div>
    <div className="room-labels" aria-hidden="true">
      {roomMarkers.map((marker) => <div key={marker.key} className={`room-tag ${props.selection?.floorId === marker.floorId && props.selection.roomId === marker.room.id ? 'is-selected' : ''}`} hidden
        data-room-label={marker.key} title={`${marker.room.name}: ${formatFeet(marker.room.width_ft)} × ${formatFeet(marker.room.depth_ft)} ft (outer extents)`}
        ref={(element) => { if (element) roomRefs.current.set(marker.key, element); else roomRefs.current.delete(marker.key) }}>
        <strong hidden={!props.showLabels}>{marker.room.label}</strong>
        <span hidden={!props.showDimensions} data-room-size>{formatFeet(marker.room.width_ft)} × {formatFeet(marker.room.depth_ft)} ft{marker.room.footprints.length > 1 ? ' ext.' : ''}</span>
      </div>)}
    </div>
    <svg className="dimension-overlay" role="img" aria-label="Candidate dimensions in feet and metres">
      {measurements.map((dimension) => <g key={dimension.key} visibility="hidden" data-dimension={dimension.key}
        ref={(element) => { if (element) dimensionRefs.current.set(dimension.key, element); else dimensionRefs.current.delete(dimension.key) }}>
        <path /><text>{dimension.label}</text>
      </g>)}
    </svg>
  </>
}

export default function HouseViewer(props: Props & { attempt: number; onRetry: () => void }) {
  return <ViewerBoundary key={`${study.revision}:${props.attempt}`} onRetry={props.onRetry}>
    <ViewerScene {...props} />
  </ViewerBoundary>
}
