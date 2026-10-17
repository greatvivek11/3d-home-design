import { Component, Suspense, useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import type { ComponentRef, ErrorInfo, ReactNode, RefObject } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import type { ThreeEvent } from '@react-three/fiber'
import { OrbitControls, useGLTF, useProgress } from '@react-three/drei'
import { AgXToneMapping, Box3, DirectionalLight, Mesh, MeshStandardMaterial, Object3D, OrthographicCamera, PCFSoftShadowMap, PMREMGenerator, SRGBColorSpace, Vector3 } from 'three'
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js'
import {
  dimensionLines, displayedFloors, findRoom, floorPosition, floors, siteAllowed, study,
} from './model'
import type { CameraView, DimensionLine, FloorId, LayerId, Selection, ViewMode, Visibility } from './model'

type Measurement = DimensionLine & { key: string; floorId: FloorId }

type Props = {
  mode: ViewMode
  visible: Visibility
  single: FloorId
  cameraView: CameraView
  showLabels: boolean
  showDimensions: boolean
  selection: Selection | null
  resetKey: number
  onSelect: (selection: Selection) => void
}

function StudioLighting({ controls, sceneKey }: {
  controls: RefObject<ComponentRef<typeof OrbitControls> | null>
  sceneKey: string
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
  useLayoutEffect(() => {
    if (sun.current) sun.current.shadow.needsUpdate = true
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
    <hemisphereLight args={['#fff7ea', '#9ba79b', 0.5]} />
    <directionalLight ref={sun} target={target} castShadow intensity={2.6} color="#fff1da"
      shadow-mapSize={[2048, 2048]} shadow-bias={-0.00008} shadow-normalBias={0.009} shadow-autoUpdate={false} />
    <directionalLight position={[25, 40, -40]} intensity={0.7} color="#e4edff" />
  </>
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
  dimensionRefs: RefObject<Map<string, SVGGElement>>
  measurements: Measurement[]
  onReady: () => void
}) {
  const { mode, visible, single, cameraView, showLabels, showDimensions, selection, resetKey, onSelect, attempt, labelRefs, dimensionRefs, measurements, onReady } = props
  const gltf = useGLTF(`${import.meta.env.BASE_URL}models/house.glb?v=${study.revision}&attempt=${attempt}`)
  const { size, camera, invalidate, gl } = useThree()
  const compact = size.width < 700
  const controls = useRef<ComponentRef<typeof OrbitControls>>(null)
  const labelPoint = useMemo(() => new Vector3(), [])
  const roots = useMemo(() => {
    const result = new Map<LayerId, { object: Object3D; bounds: Box3 }>()
    for (const id of ['site', ...floors.map((floor) => floor.id)] as const) {
      const source = gltf.scene.getObjectByName(`floor_${id}`)
      if (!source) throw new Error(`The exported model is missing floor_${id}. Regenerate its GLB.`)
      const object = source.clone(true)
      object.updateWorldMatrix(true, true)
      const bounds = new Box3().setFromObject(object)
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
                texture.anisotropy = Math.min(8, gl.capabilities.getMaxAnisotropy())
                texture.needsUpdate = true
              }
            }
          }
        }
      })
      result.set(id, { object, bounds })
    }
    return result
  }, [gltf.scene, gl])
  const active = useMemo(() => displayedFloors(mode, visible, single), [mode, visible, single])
  const includeSite = visible.site && siteAllowed(mode, single)
  const selectedRoom = findRoom(selection)
  const site = roots.get('site')
  if (!site) throw new Error('Missing garden/site geometry')

  useEffect(onReady, [onReady])
  useFrame(({ camera, size }) => {
    for (const floor of floors) {
      const element = labelRefs.current[floor.id]
      if (!element) continue
      const [x, y, z] = floorPosition(floor.id, mode, compact)
      labelPoint.set(floor.bounds.x + floor.bounds.width / 2 + x, 1.7 + y, floor.bounds.z - 1.5 + z).project(camera)
      element.hidden = !showLabels || !active.includes(floor.id) || labelPoint.z < -1 || labelPoint.z > 1
      element.style.transform = `translate3d(${(labelPoint.x + 1) * size.width / 2}px, ${(1 - labelPoint.y) * size.height / 2}px, 0) translate(-50%, -50%)`
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
      bounds.set(new Vector3(b.x, 0, b.z), new Vector3(b.x + b.width, 3.5, b.z + b.depth)).translate(position)
    } else {
      for (const id of active) {
        const source = roots.get(id)
        if (source) bounds.union(source.bounds.clone().translate(new Vector3(...floorPosition(id, mode, compact))))
      }
      if (includeSite) {
        const site = roots.get('site')
        if (site) bounds.union(site.bounds)
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
  }, [mode, visible, single, cameraView, selection, selectedRoom, resetKey, size.width, size.height, compact, camera, invalidate, roots, includeSite, active])

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
    <StudioLighting controls={controls} sceneKey={`${mode}:${active.join(',')}:${includeSite}`} />
    {floors.map((floor) => {
      const root = roots.get(floor.id)
      if (!root) throw new Error(`Missing ${floor.id} geometry`)
      const shown = active.includes(floor.id)
      return <group key={floor.id} position={floorPosition(floor.id, mode, compact)} visible={shown}
        onClick={shown ? (event) => pick(event, floor.id) : undefined} dispose={null}>
        <primitive object={root.object} />
        {!includeSite && mode !== 'stacked' && <mesh
          position={[(root.bounds.min.x + root.bounds.max.x) / 2, root.bounds.min.y - 0.025, (root.bounds.min.z + root.bounds.max.z) / 2]}
          rotation={[-Math.PI / 2, 0, 0]} receiveShadow raycast={() => undefined}>
          <planeGeometry args={[root.bounds.max.x - root.bounds.min.x + 0.6, root.bounds.max.z - root.bounds.min.z + 0.6]} />
          <meshStandardMaterial color="#f6f4ec" roughness={1} />
        </mesh>}
        {selection?.floorId === floor.id && selectedRoom && selectedRoom.footprints.map((part, index) => <mesh key={index}
          position={[part.x + part.width / 2, 0.11, part.z + part.depth / 2]}
          rotation={[-Math.PI / 2, 0, 0]} raycast={() => undefined}>
          <planeGeometry args={[part.width, part.depth]} />
          <meshBasicMaterial color="#c18a42" transparent opacity={0.06} depthWrite={false} />
        </mesh>)}
      </group>
    })}
    <group visible={includeSite} onClick={includeSite ? (event) => event.stopPropagation() : undefined} dispose={null}><primitive object={site.object} /></group>
  </>
}

function ViewerScene(props: Props & { attempt: number }) {
  const [loaded, setLoaded] = useState(false)
  const [started, setStarted] = useState(false)
  const labelRefs = useRef<Partial<Record<FloorId, HTMLDivElement | null>>>({})
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
      shadows={{ type: PCFSoftShadowMap }} dpr={[1, 2]} gl={{ antialias: true, alpha: true }}
      fallback={<div className="viewer-message" role="alert"><h3>Your browser cannot start WebGL.</h3><p>Try hardware acceleration or another browser. You can still open the dimensioned plans from the sidebar.</p></div>}>
      <Suspense fallback={null}><Model {...props} labelRefs={labelRefs} dimensionRefs={dimensionRefs} measurements={measurements} onReady={onReady} /></Suspense>
    </Canvas>
    {loaded ? <span className="sr-only" role="status">3D house model loaded</span> : started && <LoadingModel />}
    <div className="floor-labels" aria-hidden="true">
      {floors.map((floor, index) => <div key={floor.id} className="floor-tag" hidden
        ref={(element) => { labelRefs.current[floor.id] = element }}>
        <span>{String(index + 1).padStart(2, '0')}</span>{floor.title}
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
