import { Suspense, useEffect, useMemo, useRef } from 'react'
import type { ComponentRef } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { OrbitControls, useGLTF } from '@react-three/drei'
import {
  AgXToneMapping, Color, DirectionalLight, Fog, Mesh, MeshStandardMaterial, Object3D, PCFShadowMap, PMREMGenerator, PerspectiveCamera,
  Scene, SRGBColorSpace, Vector3,
} from 'three'
import { Sky } from 'three/addons/objects/Sky.js'
import { LoadingModel, StudioEffects, ViewerBoundary } from './HouseViewer'
import { cameraAzimuth, exterior, exteriorViews, floors, study, verticalFov } from './model'
import type { ExteriorView } from './model'

type Props = {
  viewId: string
  autoOrbit: boolean
  studioQuality: boolean
  resetKey: number
  attempt: number
  onRetry: () => void
  onUserMove: () => void
}

const base = import.meta.env.BASE_URL
// A retry changes the query so a cached failed request cannot be reused.
const houseUrl = (attempt: number) => `${base}models/house.glb?v=${study.revision}&attempt=${attempt}`
const exteriorUrl = (attempt: number) => `${base}${exterior.model}?v=${exterior.revision}&attempt=${attempt}`
const groundBounds = floors[1].bounds
const HOUSE_CENTER = new Vector3(groundBounds.x + groundBounds.width / 2, 4.2, groundBounds.z + groundBounds.depth / 2)
const SUN_ELEVATION = 0.74
const SUN_OFFSET = 0.85
const TRANSITION_MS = 1700

function ease(t: number) {
  return t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2
}

function prepare(root: Object3D, anisotropy: number) {
  root.traverse((node) => {
    if (!(node instanceof Mesh)) return
    const materials = Array.isArray(node.material) ? node.material : [node.material]
    node.castShadow = !materials.every((material) => material.transparent && material.opacity < 0.5)
    node.receiveShadow = true
    if (node.userData.cutaway_planting) node.visible = false
    for (const material of materials) {
      if (!(material instanceof MeshStandardMaterial)) continue
      for (const texture of [material.map, material.normalMap, material.roughnessMap, material.metalnessMap]) {
        if (texture) {
          texture.anisotropy = anisotropy
          texture.needsUpdate = true
        }
      }
    }
  })
}

function Atmosphere() {
  const { gl, scene, invalidate } = useThree()
  useEffect(() => {
    const sky = new Sky()
    sky.scale.setScalar(6000)
    const uniforms = sky.material.uniforms
    uniforms.turbidity.value = 3.2
    uniforms.rayleigh.value = 1.35
    uniforms.mieCoefficient.value = 0.004
    uniforms.mieDirectionalG.value = 0.82
    uniforms.sunPosition.value.set(-0.35, 0.62, 0.7).normalize()
    scene.add(sky)
    const generator = new PMREMGenerator(gl)
    const envScene = new Scene()
    envScene.add(sky.clone())
    const environment = generator.fromScene(envScene, 0.02)
    const previous = { environment: scene.environment, fog: scene.fog, background: scene.background, intensity: scene.environmentIntensity }
    scene.environment = environment.texture
    scene.environmentIntensity = 0.34
    scene.fog = new Fog(new Color('#c3d3d3'), 140, 1250)
    scene.background = new Color('#c3d3d3')
    gl.toneMappingExposure = 0.58
    invalidate()
    return () => {
      scene.remove(sky)
      sky.geometry.dispose()
      sky.material.dispose()
      environment.dispose()
      generator.dispose()
      scene.environment = previous.environment
      scene.environmentIntensity = previous.intensity
      scene.fog = previous.fog
      scene.background = previous.background
    }
  }, [gl, scene, invalidate])
  return null
}

function ExteriorModel({ studio, sun, attempt }: { studio: boolean; sun: { current: DirectionalLight | null }; attempt: number }) {
  const house = useGLTF(houseUrl(attempt))
  const shell = useGLTF(exteriorUrl(attempt))
  const { gl, invalidate } = useThree()
  const roofElevation = floors.find((floor) => floor.id === 'roof')?.elevation_m
  if (roofElevation === undefined) throw new Error('The manifest is missing the roof level')
  const objects = useMemo(() => {
    const anisotropy = Math.min(16, gl.capabilities.getMaxAnisotropy())
    const layers = ['site', 'roof'].map((id) => {
      const source = house.scene.getObjectByName(`floor_${id}`)
      if (!source) throw new Error(`The house model is missing floor_${id}. Regenerate its GLB.`)
      const root = source.clone(true)
      const structure = root.getObjectByName(`structure_${id}`)
      if (structure) structure.visible = false
      prepare(root, anisotropy)
      return root
    })
    const outside = shell.scene.clone(true)
    prepare(outside, anisotropy)
    return { site: layers[0], roof: layers[1], outside }
  }, [house.scene, shell.scene, gl])
  useEffect(() => {
    if (sun.current) {
      sun.current.shadow.needsUpdate = true
    }
    invalidate()
  }, [objects, sun, invalidate, studio])
  return <>
    <primitive object={objects.site} />
    <group position={[0, roofElevation, 0]}><primitive object={objects.roof} /></group>
    <primitive object={objects.outside} />
  </>
}

function Lighting({ sun, studio }: { sun: { current: DirectionalLight | null }; studio: boolean }) {
  const target = useMemo(() => new Object3D(), [])
  const { invalidate } = useThree()
  useEffect(() => {
    target.position.copy(HOUSE_CENTER)
    target.updateMatrixWorld()
    const light = sun.current
    if (!light) return
    const camera = light.shadow.camera
    camera.left = camera.bottom = -26
    camera.right = camera.top = 26
    camera.near = 1
    camera.far = 220
    camera.updateProjectionMatrix()
    light.shadow.needsUpdate = true
    invalidate()
  }, [target, sun, studio, invalidate])
  const size = studio ? 4096 : 2048
  return <>
    <primitive object={target} />
    <hemisphereLight args={['#d6e6ff', '#6f8456', 0.4]} />
    <directionalLight key={size} ref={sun} target={target} castShadow intensity={studio ? 4.6 : 4.2} color="#ffeccc"
      position={[-30, 55, 60]} shadow-mapSize={[size, size]} shadow-bias={-0.00004} shadow-normalBias={0.02} shadow-autoUpdate={false} />
  </>
}

function CameraRig({ view, resetKey, autoOrbit, controls, sun, onUserMove }: {
  view: ExteriorView
  resetKey: number
  autoOrbit: boolean
  controls: { current: ComponentRef<typeof OrbitControls> | null }
  sun: { current: DirectionalLight | null }
  onUserMove: () => void
}) {
  const { camera, invalidate } = useThree()
  const animation = useRef<null | { start: number; position: Vector3; target: Vector3; fov: number; azimuth: number }>(null)
  const azimuth = useRef<number | null>(null)
  const place = (azimuthValue: number) => {
    const light = sun.current
    if (!light) return
    const angle = azimuthValue + SUN_OFFSET
    light.position.set(HOUSE_CENTER.x + Math.sin(angle) * Math.cos(SUN_ELEVATION) * 70, HOUSE_CENTER.y + Math.sin(SUN_ELEVATION) * 70,
      HOUSE_CENTER.z + Math.cos(angle) * Math.cos(SUN_ELEVATION) * 70)
    light.shadow.needsUpdate = true
  }
  useEffect(() => {
    const orbit = controls.current
    if (!orbit || !(camera instanceof PerspectiveCamera)) return
    const goal = {
      position: new Vector3(...view.position), target: new Vector3(...view.target), fov: verticalFov(view.lens_mm),
      azimuth: cameraAzimuth(view.position, view.target),
    }
    if (azimuth.current === null) {
      camera.position.copy(goal.position)
      orbit.target.copy(goal.target)
      camera.fov = goal.fov
      camera.updateProjectionMatrix()
      orbit.update()
      azimuth.current = goal.azimuth
      place(goal.azimuth)
    } else {
      animation.current = { start: performance.now(), position: camera.position.clone(), target: orbit.target.clone(), fov: camera.fov, azimuth: azimuth.current }
      // Take the short way round when the sun follows the new camera direction.
      while (goal.azimuth - animation.current.azimuth > Math.PI) animation.current.azimuth += 2 * Math.PI
      while (goal.azimuth - animation.current.azimuth < -Math.PI) animation.current.azimuth -= 2 * Math.PI
      azimuth.current = goal.azimuth
    }
    invalidate()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view, resetKey])
  useEffect(() => {
    const orbit = controls.current
    if (!orbit) return
    const stop = () => onUserMove()
    orbit.addEventListener('start', stop)
    return () => orbit.removeEventListener('start', stop)
  }, [controls, onUserMove])
  useFrame(() => {
    const orbit = controls.current
    if (!orbit || !(camera instanceof PerspectiveCamera)) return
    const move = animation.current
    if (move && azimuth.current !== null) {
      const t = Math.min(1, (performance.now() - move.start) / TRANSITION_MS)
      const e = ease(t)
      camera.position.lerpVectors(move.position, new Vector3(...view.position), e)
      orbit.target.lerpVectors(move.target, new Vector3(...view.target), e)
      camera.fov = move.fov + (verticalFov(view.lens_mm) - move.fov) * e
      camera.updateProjectionMatrix()
      orbit.update()
      place(move.azimuth + (azimuth.current - move.azimuth) * e)
      if (t >= 1) animation.current = null
      invalidate()
    } else if (autoOrbit) {
      invalidate()
    }
  })
  return null
}

function Scene3D({ view, autoOrbit, studio, resetKey, onUserMove, attempt }: Pick<Props, 'autoOrbit' | 'resetKey' | 'onUserMove' | 'attempt'> & { view: ExteriorView; studio: boolean }) {
  const controls = useRef<ComponentRef<typeof OrbitControls>>(null)
  const sun = useRef<DirectionalLight>(null)
  return <>
    <OrbitControls ref={controls} makeDefault enableDamping dampingFactor={0.1} minDistance={4} maxDistance={260}
      maxPolarAngle={Math.PI / 2 - 0.02} autoRotate={autoOrbit} autoRotateSpeed={0.9} />
    <Atmosphere />
    <Lighting sun={sun} studio={studio} />
    <Suspense fallback={null}><ExteriorModel studio={studio} sun={sun} attempt={attempt} /></Suspense>
    <CameraRig view={view} resetKey={resetKey} autoOrbit={autoOrbit} controls={controls} sun={sun} onUserMove={onUserMove} />
    <StudioEffects enabled={studio} />
  </>
}

export default function ExteriorViewer({ viewId, autoOrbit, studioQuality, resetKey, attempt, onRetry, onUserMove }: Props) {
  const view = exteriorViews.find((item) => item.id === viewId) ?? exteriorViews[0]
  const first = exteriorViews.find((item) => item.id === 'aerial-front') ?? exteriorViews[0]
  return <ViewerBoundary onRetry={onRetry} key={`${study.revision}:${exterior.revision}:${attempt}`}>
    <Canvas camera={{ position: first.position, fov: verticalFov(first.lens_mm), near: 0.3, far: 9000 }} frameloop="demand"
      onCreated={({ gl }) => { gl.toneMapping = AgXToneMapping; gl.outputColorSpace = SRGBColorSpace }}
      shadows={{ type: PCFShadowMap }} dpr={[1, 2]} gl={{ antialias: true, alpha: false }}
      fallback={<div className="viewer-message" role="alert"><h3>Your browser cannot start WebGL.</h3><p>Try hardware acceleration or another browser.</p></div>}>
      <Scene3D view={view} autoOrbit={autoOrbit} studio={studioQuality} resetKey={resetKey} onUserMove={onUserMove} attempt={attempt} />
    </Canvas>
    <ExteriorStatus attempt={attempt} />
  </ViewerBoundary>
}

function ExteriorStatus({ attempt }: { attempt: number }) {
  return <Suspense fallback={<LoadingModel />}><Ready attempt={attempt} /></Suspense>
}

function Ready({ attempt }: { attempt: number }) {
  useGLTF(houseUrl(attempt))
  useGLTF(exteriorUrl(attempt))
  return <span className="sr-only" role="status">3D exterior loaded</span>
}
