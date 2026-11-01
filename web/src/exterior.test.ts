import { describe, expect, it, vi } from 'vitest'
import { createHash } from 'node:crypto'
import { readFileSync } from 'node:fs'
import { Box3, Mesh, Raycaster, Vector3 } from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { MeshoptDecoder } from 'meshoptimizer/decoder'
import { cameraAzimuth, exterior, exteriorViews, floors, study, verticalFov } from './model'

// Node has no ImageBitmap: report the PNG's real header so decoding can proceed.
vi.stubGlobal('self', globalThis)
vi.stubGlobal('createImageBitmap', async (blob: Blob) => {
  const png = Buffer.from(await blob.arrayBuffer())
  expect(png.subarray(0, 8).toString('hex')).toBe('89504e470d0a1a0a')
  return { width: png.readUInt32BE(16), height: png.readUInt32BE(20), close() {} }
})

const layout = JSON.parse(readFileSync(new URL('../../house-spec/layout-study.json', import.meta.url), 'utf8'))
const bytes = readFileSync(new URL('../public/models/exterior.glb', import.meta.url))
const load = () => new GLTFLoader().setMeshoptDecoder(MeshoptDecoder).parseAsync(new Uint8Array(bytes).buffer, '')
const FT = 0.3048

describe('the 360 degree exterior', () => {
  it('ships a lossless-compressed, hash-matched exterior model for this exact study', () => {
    expect(exterior.model).toBe('models/exterior.glb')
    expect(exterior.model_bytes).toBe(bytes.byteLength)
    expect(exterior.revision).toBe(createHash('sha256').update(bytes).digest('hex').slice(0, 12))
    expect(exterior.uncompressed_model_bytes).toBeGreaterThan(exterior.model_bytes)
    expect(bytes.byteLength).toBeLessThan(8_000_000)
    expect(study.layout_sha256).toBe(createHash('sha256').update(readFileSync(new URL('../../house-spec/layout-study.json', import.meta.url))).digest('hex'))
    expect(exterior.status).toMatch(/not designed or approved/i)
  })

  it('has the nine named presentation cameras with valid, in-plot, above-ground positions', () => {
    expect(exteriorViews.map((view) => view.id).sort()).toEqual(
      ['aerial-front', 'aerial-rear', 'entrance', 'front', 'garden-pool', 'left', 'orbit', 'rear', 'right'])
    for (const view of exteriorViews) {
      expect([...view.position, ...view.target, view.lens_mm].every(Number.isFinite)).toBe(true)
      expect(view.position[1]).toBeGreaterThan(0.6)
      expect(verticalFov(view.lens_mm)).toBeGreaterThan(20)
      expect(verticalFov(view.lens_mm)).toBeLessThan(60)
    }
    // Blender +Y becomes Three.js -Z: the road is at z ~ 0 and the rear garden is at negative z.
    expect(exteriorViews.find((view) => view.id === 'front')?.position[2]).toBeGreaterThan(0)
    expect(exteriorViews.find((view) => view.id === 'rear')?.position[2]).toBeLessThan(-40)
    expect(() => verticalFov(0)).toThrow('positive finite')
    expect(() => verticalFov(NaN)).toThrow('positive finite')
  })

  it('keeps the sun relative to the camera, taking the shortest way round the house', () => {
    const front = exteriorViews.find((view) => view.id === 'front')!
    const rear = exteriorViews.find((view) => view.id === 'rear')!
    expect(Math.abs(cameraAzimuth(front.position, front.target))).toBeLessThan(0.4)
    expect(Math.abs(Math.abs(cameraAzimuth(rear.position, rear.target)) - Math.PI)).toBeLessThan(0.4)
  })

  it('decodes finished full-height storeys, the lift tower, gates and varied planting', async () => {
    const gltf = await load()
    gltf.scene.updateMatrixWorld(true)
    const root = gltf.scene.getObjectByName('exterior_root')
    expect(root?.userData.presentation_only).toBe(true)
    const meshes: Mesh[] = []
    gltf.scene.traverse((node) => { if (node instanceof Mesh) meshes.push(node) })
    expect(meshes.length).toBeGreaterThan(15)
    const ground = layout.floors.find((floor: { id: string }) => floor.id === 'ground')
    const first = layout.floors.find((floor: { id: string }) => floor.id === 'first')
    const roof = layout.floors.find((floor: { id: string }) => floor.id === 'roof')
    const byMaterial = (prefix: string) => {
      const found = new Box3()
      for (const mesh of meshes) {
        if ((Array.isArray(mesh.material) ? mesh.material : [mesh.material]).some((m) => m.name.startsWith(prefix))) found.expandByObject(mesh)
      }
      return found
    }
    const plaster = byMaterial('plaster')
    expect(plaster.isEmpty()).toBe(false)
    // Plaster walls and fascia run from the ground slab to the roof edge: two full 11 ft storeys.
    expect(plaster.min.y).toBeLessThanOrEqual((ground.elevation + layout.exterior.plinth_height) * FT + 1e-6)
    expect(plaster.max.y).toBeGreaterThanOrEqual((roof.elevation - 0.5) * FT)
    expect(plaster.max.y).toBeLessThanOrEqual((roof.elevation + 1) * FT)
    expect(first.elevation - ground.elevation).toBe(layout.exterior.storey_height)
    expect(roof.elevation - first.elevation).toBe(layout.exterior.storey_height)
    // The lift tower rises above the roof so its slot and head sit on the same road-side facade.
    const stone = byMaterial('facade_stone')
    expect(stone.max.y).toBeGreaterThanOrEqual(roof.elevation * FT - 1e-4)
    const materialNames = new Set(meshes.flatMap((mesh) => (Array.isArray(mesh.material) ? mesh.material : [mesh.material]).map((m) => m.name)))
    for (const name of ['plaster', 'facade_stone', 'frame', 'facade_glass', 'timber', 'boundary_stone', 'leaf_a', 'pine_a']) {
      expect([...materialNames].some((value) => value.startsWith(name)), name).toBe(true)
    }
  })

  it('keeps the exterior inside the road-to-rear envelope and leaves the entry and driveway open', async () => {
    const gltf = await load()
    gltf.scene.updateMatrixWorld(true)
    const site = layout.site
    const gates = layout.exterior.boundary.gaps
    const path = layout.outdoor.find((item: { id: string }) => item.id === 'entry_path').rect
    const gate = gates.find((item: { id: string }) => item.id === 'pedestrian_gate')
    expect(gate.start).toBeLessThanOrEqual(path[0])
    expect(gate.end).toBeGreaterThanOrEqual(path[0] + path[2])
    // Anything modeled as boundary wall must not cross the pedestrian or driveway gates.
    const stone: Mesh[] = []
    gltf.scene.traverse((node) => {
      if (node instanceof Mesh && (Array.isArray(node.material) ? node.material : [node.material]).some((m) => m.name.startsWith('boundary_stone'))) stone.push(node)
    })
    expect(stone.length).toBeGreaterThan(0)
    // Fire rays from the road toward the house at 0.6 m height: walls must be hit, gate openings must not.
    const blocked = (xFt: number) => {
      const caster = new Raycaster(new Vector3(xFt * FT, 0.6, 6 * FT), new Vector3(0, 0, -1), 0, 14 * FT)
      return caster.intersectObjects(stone, false).some((hit) => hit.point.z > -1.5 * FT)
    }
    expect(blocked(gate.start / 2)).toBe(true)
    expect(blocked((gates[1].end + site.width) / 2)).toBe(true)
    for (const gap of gates) {
      for (const fraction of [0.1, 0.5, 0.9]) expect(blocked(gap.start + (gap.end - gap.start) * fraction), `${gap.id} @ ${fraction}`).toBe(false)
    }
    expect(blocked((gates[0].end + gates[1].start) / 2)).toBe(true)
    expect(site.width).toBe(70)
  })

  it('decodes every added or centred window at its real exterior height, width and section count', async () => {
    const gltf = await load()
    gltf.scene.updateMatrixWorld(true)
    const panes: Mesh[] = []
    gltf.scene.traverse((node) => { if (node instanceof Mesh && node.userData.role === 'exterior_glazing') panes.push(node) })
    const ids = ['ground_wc_window', 'master_bath_window', 'master_side_window', 'living_side_window',
      'child1_side_window', 'lounge_west_window', 'lounge_east_window']
    for (const id of ids) {
      const floor = layout.floors.find((f: { openings: { id?: string }[] }) => f.openings.some((o) => o.id === id))
      const opening = floor.openings.find((o: { id?: string }) => o.id === id)
      const matches = panes.filter((node) => node.userData.opening_id === id)
      expect(matches, id).toHaveLength(1)
      const pane = matches[0]
      const bounds = new Box3().setFromObject(pane)
      const frame = layout.exterior.frame_ft
      expect(bounds.min.z).toBeCloseTo(-(opening.start + opening.width - frame) * FT, 4)
      expect(bounds.max.z).toBeCloseTo(-(opening.start + frame) * FT, 4)
      expect(bounds.min.y).toBeCloseTo((floor.elevation + opening.sill + frame) * FT, 4)
      expect(bounds.max.y).toBeCloseTo((floor.elevation + opening.sill + opening.height - frame) * FT, 4)
      expect(pane.userData.sections).toBe(opening.sections)
      expect(pane.userData.operable_intent).toBe(true)
      const left = opening.at < layout.site.width / 2
      const fromX = left ? 3 : 55
      for (let k = 1; k < opening.sections; k++) {
        const divider = opening.start + opening.width * k / opening.sections
        const ray = new Raycaster(new Vector3(fromX * FT, (floor.elevation + opening.sill + opening.height / 2) * FT, -divider * FT),
          new Vector3(left ? 1 : -1, 0, 0), 0, 3 * FT)
        const hit = ray.intersectObject(gltf.scene, true).find((h) => h.object instanceof Mesh)
        expect(hit, `${id} divider ${k}`).toBeDefined()
        const mesh = hit!.object as Mesh
        const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material]
        expect(materials.every((m) => m.name === 'frame')).toBe(true)
      }
      if (opening.privacy_glass) {
        const materials = Array.isArray(pane.material) ? pane.material : [pane.material]
        expect(materials.every((m) => m.name === 'privacy_glass' && m.opacity === 1)).toBe(true)
        expect(pane.userData.privacy_glass).toBe(true)
      } else expect(pane.userData.operation).toBe('horizontal_sliding_intent')
    }
  })

  it('marks cutaway trees so the exterior never mixes low-poly cutaway planting into the outside view', async () => {
    const gltf = await new GLTFLoader().setMeshoptDecoder(MeshoptDecoder).parseAsync(
      new Uint8Array(readFileSync(new URL('../public/models/house.glb', import.meta.url))).buffer, '')
    const flagged: Mesh[] = []
    gltf.scene.traverse((node) => { if (node instanceof Mesh && node.userData.cutaway_planting) flagged.push(node) })
    expect(flagged.length).toBeGreaterThan(0)
    expect(floors.find((floor) => floor.id === 'roof')?.elevation_m).toBeCloseTo(23.5 * FT, 6)
  })
})
