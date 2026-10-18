import { describe, expect, it, vi } from 'vitest'
import { createHash } from 'node:crypto'
import { readFileSync } from 'node:fs'
import { inflateSync } from 'node:zlib'
import { Box3, Mesh, Raycaster, Vector3 } from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { MeshoptDecoder } from 'meshoptimizer/decoder'
import {
  annotationFloors, defaultVisibility, dimensionLines, displayedFloors, findRoom, floorPosition, floors, formatArea, formatFeet, formatLength, roomLabelAnchor, siteAllowed, sitePosition, study, visibleRoomAnnotations,
} from './model'
import type { RoomAnnotation } from './model'

// Node has no ImageBitmap. Validate and inflate real PNGs for geometry tests;
// the production browser check exercises their actual pixel rendering.
vi.stubGlobal('self', globalThis)
vi.stubGlobal('createImageBitmap', async (blob: Blob) => {
  const png = Buffer.from(await blob.arrayBuffer())
  expect(png.subarray(0, 8).toString('hex')).toBe('89504e470d0a1a0a')
  const width = png.readUInt32BE(16), height = png.readUInt32BE(20)
  expect(width).toBe(512)
  expect(height).toBe(512)
  expect(png[24]).toBe(8)
  expect([2, 6]).toContain(png[25])
  expect(png[28]).toBe(0)
  const chunks: Buffer[] = []
  for (let offset = 8; offset < png.length;) {
    const length = png.readUInt32BE(offset)
    expect(offset + length + 12).toBeLessThanOrEqual(png.length)
    if (png.toString('ascii', offset + 4, offset + 8) === 'IDAT') chunks.push(png.subarray(offset + 8, offset + 8 + length))
    offset += length + 12
  }
  const pixels = inflateSync(Buffer.concat(chunks))
  const channels = png[25] === 6 ? 4 : 3
  expect(pixels.length).toBe((width * channels + 1) * height)
  return { width, height, close() {} }
})

describe('the exported study contract', () => {
  const bytes = readFileSync(new URL('../public/models/house.glb', import.meta.url))
  const document: {
    asset: { version: string }
    scenes: { nodes: number[] }[]
    nodes: { name?: string; mesh?: number; extras?: Record<string, unknown> }[]
    images: { mimeType: string; bufferView?: number; uri?: string }[]
    materials: { normalTexture?: unknown; pbrMetallicRoughness?: { baseColorTexture?: unknown; metallicRoughnessTexture?: unknown } }[]
    extensionsRequired?: string[]
  } = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)).toString('utf8'))
  const model = () => new GLTFLoader().setMeshoptDecoder(MeshoptDecoder).parseAsync(new Uint8Array(bytes).buffer, '')

  it('ships an actual GLB 2.0 matching its manifest, not a Git LFS pointer', () => {
    expect(bytes.toString('utf8', 0, 4)).toBe('glTF')
    expect(bytes.readUInt32LE(4)).toBe(2)
    expect(bytes.readUInt32LE(8)).toBe(bytes.length)
    expect(bytes.readUInt32LE(16)).toBe(0x4e4f534a)
    expect(bytes.length).toBe(study.model_bytes)
    expect(createHash('sha256').update(bytes).digest('hex').slice(0, 12)).toBe(study.revision)
    expect(document.asset.version).toBe('2.0')
    expect(study.schema_version).toBe(2)
  })

  it('exports exactly five canonical layers with room floor/furniture identities', () => {
    const ids = ['site', ...floors.map((floor) => floor.id)]
    expect(document.scenes).toHaveLength(1)
    expect(document.scenes[0].nodes.map((index) => document.nodes[index].name).sort()).toEqual(ids.map((id) => `floor_${id}`).sort())
    for (const [id, count] of Object.entries(study.mesh_counts)) {
      expect(document.nodes.filter((node) => node.mesh !== undefined && node.extras?.floor_id === id)).toHaveLength(count)
    }
    const barrier = document.nodes.filter((node) => node.extras?.partition_id === 'garage_barrier')
    expect(barrier.length).toBeGreaterThan(0)
    expect(barrier.every((node) => node.extras?.intended_height_ft === 10 && node.extras.cutaway === true)).toBe(true)
    expect(document.nodes.filter((node) => node.extras?.self_closing_intent === true)).toHaveLength(2)
    for (const floor of floors) {
      for (const room of floor.rooms.filter((room) => !['stairs', 'circulation', 'lift'].includes(room.kind))) {
        expect(document.nodes.some((node) => node.mesh !== undefined && node.extras?.floor_id === floor.id && node.extras.room_id === room.id)).toBe(true)
      }
    }
  })

  it('ships a dimensioned SVG fallback for every level and the site', () => {
    for (const id of ['site', ...floors.map((floor) => floor.id)]) {
      const svg = readFileSync(new URL(`../public/plans/${id}.svg`, import.meta.url), 'utf8')
      expect(svg).toContain('<svg xmlns="http://www.w3.org/2000/svg"')
      expect(svg).toContain(`DREAM HOME / ${id.toUpperCase()} / ${study.study_id.replace('-', ' ').toUpperCase()}`)
      expect(svg).toContain('UNAPPROVED CONCEPT')
      expect(svg).toContain(`${study.site.width_ft} x ${Number(study.site.depth_ft.toPrecision(6))} ft`)
    }
  })

  it('retains the four floors and explicit concept status', () => {
    expect(floors.map((floor) => floor.id)).toEqual(['basement', 'ground', 'first', 'roof'])
    expect(study.status).toBe('unapproved_concept')
    expect(study.site.area_sq_ft).toBe(7000)
    expect(Object.values(study.mesh_counts).every((count) => count > 0)).toBe(true)
  })

  it('binds the revised study to the actual layout and brief fingerprints', () => {
    const layout = readFileSync(new URL('../../house-spec/layout-study.json', import.meta.url))
    const brief = readFileSync(new URL('../../house-spec/house.json', import.meta.url))
    expect(study.layout_sha256).toBe(createHash('sha256').update(layout).digest('hex'))
    expect(study.brief_sha256).toBe(createHash('sha256').update(brief).digest('hex'))
    expect(study.visual_quality).toBe('refined-01')
  })

  it('ships a portable editable Blender bundle matching the current web source', () => {
    const base = new URL(`../../assets/models/${study.study_id}/`, import.meta.url)
    const result = JSON.parse(readFileSync(new URL('generation-result.json', base), 'utf8'))
    expect(result.blend).toBe('dream-home-study.blend')
    expect(result.layout_sha256).toBe(study.layout_sha256)
    expect(result.brief_sha256).toBe(study.brief_sha256)
    expect(result.structural_status).toBe('illustrative_only_not_engineered')
    expect(result.renders).toEqual([])
    expect(result.locked_fixtures_checked).toBe(113)
    expect(JSON.parse(readFileSync(new URL('layout-snapshot.json', base), 'utf8'))).toEqual(
      JSON.parse(readFileSync(new URL('../../house-spec/layout-study.json', import.meta.url), 'utf8')))
    expect(JSON.parse(readFileSync(new URL('brief-snapshot.json', base), 'utf8'))).toEqual(
      JSON.parse(readFileSync(new URL('../../house-spec/house.json', import.meta.url), 'utf8')))
    expect(readFileSync(new URL(result.blend, base)).byteLength).toBeGreaterThan(1_000_000)
  })

  it('embeds real PBR maps without remote texture dependencies', () => {
    expect(document.images.length).toBeGreaterThanOrEqual(17)
    expect(document.images.every((image) => image.mimeType === 'image/png' && image.bufferView !== undefined && !image.uri)).toBe(true)
    expect(document.materials.filter((material) => material.pbrMetallicRoughness?.baseColorTexture).length).toBeGreaterThanOrEqual(12)
    expect(document.materials.filter((material) => material.normalTexture).length).toBeGreaterThanOrEqual(10)
    expect(document.materials.filter((material) => material.pbrMetallicRoughness?.metallicRoughnessTexture).length).toBeGreaterThanOrEqual(10)
    expect(document.extensionsRequired).toContain('EXT_meshopt_compression')
    expect(study.compression).toBe('lossless_meshopt')
    expect(study.model_bytes).toBeLessThan(study.uncompressed_model_bytes * 0.75)
  })

  it('preserves every rendered room footprint and all 113 revised source furniture placements', async () => {
    const layout: { floors: { id: string; furniture: { id: string; kind: string; rect: number[] }[] }[] } =
      JSON.parse(readFileSync(new URL('../../house-spec/layout-study.json', import.meta.url), 'utf8'))
    const gltf = await model()
    gltf.scene.updateMatrixWorld(true)
    const meshes: Mesh[] = []
    gltf.scene.traverse((node) => { if (node instanceof Mesh) meshes.push(node) })
    for (const floor of floors) {
      for (const room of floor.rooms.filter((room) => !['stairs', 'circulation', 'lift'].includes(room.kind))) {
        const tiles = meshes.filter((mesh) => mesh.userData.floor_id === floor.id && mesh.userData.room_id === room.id && mesh.userData.role === 'room_floor')
        expect(tiles).toHaveLength(room.footprints.length)
        const boxes = tiles.map((mesh) => new Box3().setFromObject(mesh))
        for (const part of room.footprints) {
          expect(boxes.some((box) => Math.abs(box.min.x - part.x) < 0.00001 && Math.abs(box.min.z - part.z) < 0.00001
            && Math.abs(box.max.x - part.x - part.width) < 0.00001 && Math.abs(box.max.z - part.z - part.depth) < 0.00001)).toBe(true)
        }
      }
    }
    const violations: string[] = []
    const point = new Vector3()
    let checked = 0
    for (const floor of layout.floors) {
      for (const item of floor.furniture) {
        const [x, y, w, d] = item.rect
        const allowed = [item.rect]
        if (item.kind === 'dining_table') {
          for (const t of [0, 0.5, 1]) allowed.push([x - 1.8, y + (d - 1.5) * t, 1.5, 1.5], [x + w + 0.3, y + (d - 1.5) * t, 1.5, 1.5])
          allowed.push([x + w / 2 - 0.75, y - 1.8, 1.5, 1.5], [x + w / 2 - 0.75, y + d + 0.3, 1.5, 1.5])
        }
        const parts = meshes.filter((mesh) => mesh.userData.floor_id === floor.id && mesh.userData.fixture_id === item.id)
        expect(parts.length).toBeGreaterThan(0)
        for (const mesh of parts) {
          const position = mesh.geometry.getAttribute('position')
          for (let i = 0; i < position.count; i++) {
            point.fromBufferAttribute(position, i).applyMatrix4(mesh.matrixWorld)
            const px = point.x / 0.3048, py = -point.z / 0.3048
            if (!allowed.some(([rx, ry, rw, rd]) => px >= rx - 0.002 && px <= rx + rw + 0.002 && py >= ry - 0.002 && py <= ry + rd + 0.002)) {
              violations.push(mesh.name)
              break
            }
          }
        }
        checked++
      }
    }
    expect(checked).toBe(113)
    expect(violations).toEqual([])
  })

  it('has unique room IDs per floor and positive metre bounds', () => {
    for (const floor of floors) {
      expect(new Set(floor.rooms.map((room) => room.id)).size).toBe(floor.rooms.length)
      for (const room of floor.rooms) {
        expect(room.bounds.width).toBeGreaterThan(0)
        expect(room.bounds.depth).toBeGreaterThan(0)
        expect(room.bounds.width).toBeCloseTo(room.width_ft * 0.3048)
        expect(room.bounds.depth).toBeCloseTo(room.depth_ft * 0.3048)
        expect(room.footprints.reduce((area, part) => area + part.width * part.depth, 0) / 0.09290304).toBeCloseTo(room.area_sq_ft)
      }
    }
  })

  it('retains basement functions and actual net living floor around its pantry and cupboard', async () => {
    const living = findRoom({ floorId: 'ground', roomId: 'family_living' })
    const kitchen = findRoom({ floorId: 'ground', roomId: 'kitchen' })
    const pantry = findRoom({ floorId: 'ground', roomId: 'pantry' })
    expect(study.study_id).toBe('study-010')
    expect(floors[0].bounds.depth / 0.3048).toBeCloseTo(80.33333333333333)
    expect(living?.area_sq_ft).toBe(343.5)
    expect(kitchen?.area_sq_ft).toBe(168)
    expect(living?.footprints.length).toBeGreaterThan(1)
    expect(kitchen?.bounds.z).toBeCloseTo(-69.5 * 0.3048)
    expect(pantry?.bounds.x).toBeCloseTo(39 * 0.3048)
    const gltf = await model()
    gltf.scene.updateMatrixWorld(true)
    const tiles: Mesh[] = []
    gltf.scene.traverse((node) => {
      if (node instanceof Mesh && node.userData.floor_id === 'ground' && node.userData.role === 'room_floor') tiles.push(node)
    })
    const pantryTile = tiles.find((node) => node.userData.room_id === 'pantry')
    if (!pantryTile) throw new Error('GLB is missing the enclosed pantry tile')
    const pantryBox = new Box3().setFromObject(pantryTile)
    const livingBoxes = tiles.filter((node) => node.userData.room_id === 'family_living').map((node) => new Box3().setFromObject(node))
    expect(livingBoxes.length).toBeGreaterThan(1)
    const area = livingBoxes.reduce((total, box) => total + (box.max.x - box.min.x) * (box.max.z - box.min.z), 0)
    expect(area / 0.09290304).toBeCloseTo(343.5, 3)
    for (const box of livingBoxes) {
      const overlapX = Math.max(0, Math.min(box.max.x, pantryBox.max.x) - Math.max(box.min.x, pantryBox.min.x))
      const overlapZ = Math.max(0, Math.min(box.max.z, pantryBox.max.z) - Math.max(box.min.z, pantryBox.min.z))
      expect(overlapX * overlapZ).toBeLessThan(0.00001)
    }
  })

  it('exports equal child suites, the office swap and a common first-floor WC', async () => {
    const gltf = await model()
    gltf.scene.updateMatrixWorld(true)
    for (let i = 1; i <= 3; i++) {
      const roomId = `child_bedroom_${i}`
      expect(findRoom({ floorId: 'first', roomId })?.area_sq_ft).toBe(272)
      const tiles: Mesh[] = []
      gltf.scene.traverse((node) => {
        if (node instanceof Mesh && node.userData.floor_id === 'first' && node.userData.room_id === roomId && node.userData.role === 'room_floor') tiles.push(node)
      })
      expect(tiles).toHaveLength(1)
      const box = new Box3().setFromObject(tiles[0])
      expect((box.max.x - box.min.x) * (box.max.z - box.min.z) / 0.09290304).toBeCloseTo(272, 3)
      expect(findRoom({ floorId: 'first', roomId: `child_wardrobe_${i}` })?.area_sq_ft).toBeGreaterThanOrEqual(30.25)
    }
    expect(findRoom({ floorId: 'first', roomId: 'office' })?.bounds.x).toBeCloseTo(4.5 * 0.3048)
    expect(findRoom({ floorId: 'first', roomId: 'child_bedroom_1' })?.bounds.x).toBeCloseTo(23.5 * 0.3048)
    expect(findRoom({ floorId: 'first', roomId: 'first_common_toilet' })?.area_sq_ft).toBe(33)
    expect(findRoom({ floorId: 'first', roomId: 'office_toilet' })).toBeUndefined()
    const toiletIds = new Set(document.nodes.map((node) => node.extras?.fixture_id).filter((id) =>
      typeof id === 'string' && /^(basement_wc|guest_wc|family_wc|master_wc_1|child[123]_wc|first_common_wc)$/.test(id)))
    expect(toiletIds.size).toBe(8)
  })

  it('keeps architecture and non-engineered frame groups separate on every floor', async () => {
    const gltf = await model()
    gltf.scene.updateMatrixWorld(true)
    expect(study.structure.status).toBe('illustrative_only_not_engineered')
    expect(study.structure.disclaimer).toContain('NOT ENGINEERED')
    for (const floor of floors) {
      const root = gltf.scene.getObjectByName(`floor_${floor.id}`)
      expect(root?.children.map((node) => node.name).sort()).toEqual([`architecture_${floor.id}`, `structure_${floor.id}`].sort())
      const frame = gltf.scene.getObjectByName(`structure_${floor.id}`)
      if (!frame) throw new Error('Missing conceptual frame')
      const columns: Mesh[] = []
      frame.traverse((node) => {
        if (node instanceof Mesh && node.userData.structural_role === 'column_proxy') columns.push(node)
      })
      const zones = study.structure.clear_span_zones.filter((zone) => zone.floor_id === floor.id)
      for (const column of columns) {
        expect(column.userData.engineering_status).toBe('not_engineered')
        const box = new Box3().setFromObject(column)
        for (const zone of zones) {
          for (const part of zone.footprints) {
            const overlapX = Math.max(0, Math.min(box.max.x, part.x + part.width) - Math.max(box.min.x, part.x))
            const overlapZ = Math.max(0, Math.min(box.max.z, part.z + part.depth) - Math.max(box.min.z, part.z))
            expect(overlapX * overlapZ).toBeLessThan(0.000001)
          }
        }
      }
    }
  })

  it('exports four lift landings, one parked placeholder and large operable bedroom glazing', () => {
    const doors = document.nodes.filter((node) => node.extras?.role === 'lift_landing_door')
    expect(doors).toHaveLength(8)
    for (const floor of floors) expect(doors.filter((node) => node.extras?.floor_id === floor.id)).toHaveLength(2)
    const cars = document.nodes.filter((node) => node.extras?.role === 'lift_car_placeholder')
    expect(cars).toHaveLength(1)
    expect(cars[0].extras?.floor_id).toBe('basement')
    for (const floor of floors) {
      for (const room of floor.rooms.filter((room) => room.kind === 'bedroom')) {
        expect(document.nodes.some((node) => node.extras?.floor_id === floor.id && node.extras?.room_id === room.id
          && node.extras.role === 'facade_glazing' && node.extras.operable_intent === true && Number(node.extras.opening_width_ft) >= 9)).toBe(true)
      }
    }
  })

  it('exports labelled galleries, the corner core and honest guest/drawing net areas', async () => {
    expect(findRoom({ floorId: 'ground', roomId: 'entrance_gallery' })?.width_ft).toBe(4)
    expect(findRoom({ floorId: 'ground', roomId: 'cross_passage' })?.depth_ft).toBe(4)
    for (const [floorId, roomId] of [
      ['ground', 'entrance_gallery'], ['ground', 'cross_passage'], ['ground', 'lift_lobby'],
      ['first', 'core_lobby'], ['first', 'rear_gallery'], ['roof', 'lift_lobby'],
    ] as const) {
      expect(findRoom({ floorId, roomId })?.name).toMatch(/gallery|lobby|route/i)
    }
    expect(findRoom({ floorId: 'ground', roomId: 'guest_shared_bathroom' })).toBeUndefined()
    expect(findRoom({ floorId: 'ground', roomId: 'guest_bathroom' })?.area_sq_ft).toBe(38.5)
    expect(findRoom({ floorId: 'ground', roomId: 'guest_bedroom' })?.area_sq_ft).toBe(157)
    expect(findRoom({ floorId: 'ground', roomId: 'receiving' })?.area_sq_ft).toBe(314.5)
    expect(findRoom({ floorId: 'ground', roomId: 'utility_store' })?.area_sq_ft).toBe(8)
    expect(findRoom({ floorId: 'ground', roomId: 'utility_store' })?.bounds.x).toBeCloseTo(51.5 * .3048)
    expect(findRoom({ floorId: 'ground', roomId: 'family_toilet' })?.area_sq_ft).toBe(40)
    const cupboard = document.nodes.filter(node => node.extras?.role === 'utility_cupboard_door')
    expect(cupboard).toHaveLength(2)
    expect(cupboard.every(node => node.extras?.sliding_intent === true && node.extras?.room_id === 'utility_store')).toBe(true)
    const gltf = await model()
    gltf.scene.updateMatrixWorld(true)
    let decodedDoors = 0
    gltf.scene.traverse(node => {
      if (!(node instanceof Mesh) || node.userData.role !== 'utility_cupboard_door') return
      const box = new Box3().setFromObject(node)
      expect(box.max.x - box.min.x).toBeLessThan(.1)
      expect(box.max.z - box.min.z).toBeGreaterThan(.3048)
      expect((box.min.x + box.max.x) / 2 / .3048).toBeCloseTo(51.25, 1)
      decodedDoors++
    })
    expect(decodedDoors).toBe(2)
    for (const floor of floors) {
      expect(findRoom({ floorId: floor.id, roomId: 'lift' })?.bounds.x).toBeCloseTo(46.5 * .3048)
    }
  })

  it('decodes the aligned stair treads and full-height landings from the actual GLB', async () => {
    const gltf = await model()
    gltf.scene.updateMatrixWorld(true)
    for (const floor of floors) {
      const profile = floor.stair
      expect(profile.units).toBe('ft')
      expect(profile.status).toBe('unapproved_concept')
      expect(profile.flight_width).toBe(4)
      expect(profile.landing_depth).toBe(4)
      expect(profile.going).toBe(1)
      expect(profile.risers_per_flight).toBe(10)
      expect(profile.entry_edge).toBe('front')
      const steps: Mesh[] = []
      const landings: Mesh[] = []
      gltf.scene.traverse(node => {
        if (!(node instanceof Mesh) || node.userData.floor_id !== floor.id) return
        if (node.userData.role === 'stair_tread') steps.push(node)
        if (node.userData.role === 'stair_landing') landings.push(node)
      })
      expect(steps).toHaveLength(floor.id === 'roof' ? 0 : 18)
      expect(landings).toHaveLength(floor.id === 'roof' ? 0 : 2)
      for (const step of steps) {
        const index = Number(step.userData.riser_index)
        expect([1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 14, 15, 16, 17, 18, 19]).toContain(index)
        const box = new Box3().setFromObject(step)
        expect(box.max.y).toBeCloseTo(index * profile.riser_height * .3048, 5)
        expect(box.max.x - box.min.x).toBeCloseTo(4 * .3048, 5)
        expect(box.max.z - box.min.z).toBeCloseTo(.3048, 5)
        const i = index < 10 ? index : index - 10
        const py = index < 10 ? profile.rect[1] + profile.landing_depth + (i - 1) * profile.going
          : profile.rect[1] + profile.rect[3] - profile.landing_depth - i * profile.going
        expect(box.max.z).toBeCloseTo(-py * .3048, 4)
      }
      for (const landing of landings) {
        const box = new Box3().setFromObject(landing)
        expect(box.max.y).toBeCloseTo(Number(landing.userData.riser_index) * profile.riser_height * .3048, 5)
        expect(box.max.z - box.min.z).toBeCloseTo(4 * .3048, 5)
        const py = Number(landing.userData.riser_index) === 10 ? profile.turn[1] : profile.landing[1]
        expect(box.max.z).toBeCloseTo(-py * .3048, 4)
      }
    }
  })

  it('cuts real slab holes over the complete stair turn/flights and the moved lift', async () => {
    const gltf = await model()
    gltf.scene.updateMatrixWorld(true)
    for (const floor of floors.filter(item => item.id !== 'basement')) {
      const slabs: Mesh[] = []
      gltf.scene.traverse(node => {
        if (!(node instanceof Mesh) || node.userData.floor_id !== floor.id) return
        const materials = Array.isArray(node.material) ? node.material : [node.material]
        if (materials.some(material => material.name === 'slab')) slabs.push(node)
      })
      expect(slabs.length).toBeGreaterThan(0)
      const ray = new Raycaster()
      for (const [x, y] of [[49, 35.5], [46.5, 29], [51.5, 29], [50, 16.5]]) {
        ray.set(new Vector3(x * .3048, .01, -y * .3048), new Vector3(0, -1, 0))
        expect(ray.intersectObjects(slabs, false)).toHaveLength(0)
      }
      ray.set(new Vector3(49 * .3048, .01, -22.5 * .3048), new Vector3(0, -1, 0))
      expect(ray.intersectObjects(slabs, false).length).toBeGreaterThan(0)
    }
  })

  it('renders one clear front portal and solid window sills instead of front-room doorways', async () => {
    const gltf = await model()
    gltf.scene.updateMatrixWorld(true)
    const architecture = gltf.scene.getObjectByName('architecture_ground')
    if (!architecture) throw new Error('Missing ground-floor architecture')
    const ray = new Raycaster()
    ray.far = 2.6 * .3048
    for (const [x, entrance] of [[26.5, true], [8, false], [33, false]] as const) {
      ray.set(new Vector3(x * .3048, .3048, -18 * .3048), new Vector3(0, 0, -1))
      const hits = ray.intersectObject(architecture, true)
      expect(hits.length === 0).toBe(entrance)
    }
  })

  it('exports two uninterrupted balconies with guards and three soft bath/dressing dividers', () => {
    const decks = document.nodes.filter((node) => node.extras?.role === 'shared_balcony_deck')
    expect(decks.map((node) => node.extras?.balcony_id).sort()).toEqual(['front_balcony', 'rear_balcony'])
    expect(document.nodes.filter((node) => node.extras?.role === 'perimeter_guard')).toHaveLength(6)
    expect(document.nodes.some((node) => node.name?.includes('privacy_screen'))).toBe(false)
    const panels = document.nodes.filter((node) => node.extras?.soft_partition_intent === true)
    expect(panels).toHaveLength(6)
    expect(new Set(panels.map((node) => node.extras?.divider_id)).size).toBe(3)
    const enclosures = document.nodes.filter((node) => node.extras?.shower_enclosure_intent === true)
    expect(enclosures).toHaveLength(16)
    expect(enclosures.filter((node) => node.extras?.entry_door === true)).toHaveLength(4)
  })

  it('counts the actual annex floor area, not the empty corners of its bounding rectangle', () => {
    for (const floor of floors) {
      expect(floor.area_sq_ft).toBeCloseTo(floor.id === 'basement' ? 50 * 80.33333333333333 : 2560)
      expect(floor.footprints.reduce((sum, part) => sum + part.width * part.depth / .09290304, 0)).toBeCloseTo(floor.area_sq_ft)
      if (floor.id === 'basement') expect(floor.bounds.width * floor.bounds.depth / .09290304).toBeCloseTo(floor.area_sq_ft)
      else expect(floor.bounds.width * floor.bounds.depth / .09290304).toBeGreaterThan(floor.area_sq_ft)
    }
    expect(findRoom({ floorId: 'first', roomId: 'upstairs_lounge' })?.area_sq_ft).toBe(653)
    expect(document.nodes.some(node => node.extras?.room_id === 'stair_link' || node.name?.includes('stair_link'))).toBe(false)
  })

  it('decodes the enlarged unified lounge without counting its stair-side WC twice', async () => {
    expect(findRoom({ floorId: 'first', roomId: 'front_landing' })).toBeUndefined()
    expect(findRoom({ floorId: 'first', roomId: 'east_gallery' })).toBeUndefined()
    expect(findRoom({ floorId: 'first', roomId: 'office' })?.area_sq_ft).toBe(204)
    expect(findRoom({ floorId: 'ground', roomId: 'master_entry' })?.width_ft).toBe(3)
    expect(findRoom({ floorId: 'ground', roomId: 'master_bedroom' })?.area_sq_ft).toBe(365.5)
    const gltf = await model()
    gltf.scene.updateMatrixWorld(true)
    const tiles: Mesh[] = []
    gltf.scene.traverse(node => {
      if (node instanceof Mesh && node.userData.floor_id === 'first' && node.userData.role === 'room_floor') tiles.push(node)
    })
    const wc = tiles.find(node => node.userData.room_id === 'first_common_toilet')
    if (!wc) throw new Error('Missing stair-side common WC floor')
    const wcBox = new Box3().setFromObject(wc)
    expect(wcBox.min.x / .3048).toBeCloseTo(47.5)
    expect((wcBox.max.x - wcBox.min.x) / .3048).toBeCloseTo(6)
    expect((wcBox.max.z - wcBox.min.z) / .3048).toBeCloseTo(5.5)
    const boxes = tiles.filter(node => node.userData.room_id === 'upstairs_lounge').map(node => new Box3().setFromObject(node))
    expect(boxes.length).toBeGreaterThan(1)
    expect(boxes.reduce((area, box) => area + (box.max.x - box.min.x) * (box.max.z - box.min.z), 0) / .09290304).toBeCloseTo(653, 3)
    for (const box of boxes) {
      const dx = Math.max(0, Math.min(box.max.x, wcBox.max.x) - Math.max(box.min.x, wcBox.min.x))
      const dz = Math.max(0, Math.min(box.max.z, wcBox.max.z) - Math.max(box.min.z, wcBox.min.z))
      expect(dx * dz).toBeLessThan(.00001)
    }
    for (const roomId of ['child_bathroom_1', 'child_wardrobe_1']) {
      const tile = tiles.find(node => node.userData.room_id === roomId)
      if (!tile) throw new Error(`Missing front-suite floor ${roomId}`)
      expect(new Box3().setFromObject(tile).min.z / -.3048).toBeLessThanOrEqual(37.5001)
    }
  })

  it('decodes wall-backed headboards, ten bedside lamps and front-landing lift doors', async () => {
    const gltf = await model()
    gltf.scene.updateMatrixWorld(true)
    const heads: Mesh[] = []
    const lamps: Mesh[] = []
    const doors: Mesh[] = []
    gltf.scene.traverse(node => {
      if (!(node instanceof Mesh)) return
      if (node.userData.role === 'bed_headboard') heads.push(node)
      if (node.userData.role === 'bedside_lamp') lamps.push(node)
      if (node.userData.role === 'lift_landing_door') doors.push(node)
    })
    expect(heads).toHaveLength(5)
    expect(lamps).toHaveLength(10)
    for (const floor of floors) {
      for (const room of floor.rooms.filter(item => item.kind === 'bedroom')) {
        const head = heads.find(item => item.userData.floor_id === floor.id && item.userData.room_id === room.id)
        if (!head) throw new Error(`Missing headboard ${room.id}`)
        const box = new Box3().setFromObject(head)
        expect(Math.min(Math.abs(box.min.x - room.bounds.x), Math.abs(box.max.x - room.bounds.x - room.bounds.width),
          Math.abs(box.min.z - room.bounds.z), Math.abs(box.max.z - room.bounds.z - room.bounds.depth))).toBeLessThan(.025)
      }
    }
    for (const door of doors) {
      const box = new Box3().setFromObject(door)
      expect(box.min.z).toBeCloseTo(-20.3 * .3048, 4)
      expect(box.max.z).toBeCloseTo(-20.2 * .3048, 4)
    }
  })

  it('exports real side windows, weather covers and a graded curved driveway with terrain cut away', async () => {
    const gltf = await model()
    gltf.scene.updateMatrixWorld(true)
    const meshes: Mesh[] = []
    gltf.scene.traverse(node => { if (node instanceof Mesh) meshes.push(node) })
    for (const [floorId, roomId] of [['ground', 'receiving'], ['ground', 'family_living'], ['first', 'office']]) {
      const windows = meshes.filter(node => node.userData.floor_id === floorId && node.userData.room_id === roomId && node.userData.role === 'facade_glazing')
      expect(windows.some(node => {
        const box = new Box3().setFromObject(node)
        return node.userData.operable_intent && box.max.x - box.min.x < .03 && box.max.z - box.min.z >= 6 * .3048 - .0001
      })).toBe(true)
    }
    expect(meshes.some(node => node.userData.floor_id === 'roof' && node.userData.weather_cover === true)).toBe(true)
    expect(meshes.some(node => node.userData.floor_id === 'site' && node.userData.weather_cover === true)).toBe(true)
    const road = meshes.find(node => node.userData.role === 'driveway_surface')
    if (!road) throw new Error('Missing actual driveway mesh')
    const box = new Box3().setFromObject(road)
    expect(box.min.y).toBeCloseTo((-8.5 + .035) * .3048, 5)
    expect(box.max.y).toBeCloseTo(.035 * .3048, 5)
    expect(box.max.x).toBeCloseTo(69.5 * .3048, 4)
    const garden = meshes.filter(node => node.userData.floor_id === 'site' && (Array.isArray(node.material) ? node.material : [node.material]).some(material => material.name === 'garden'))
    const ray = new Raycaster()
    ray.set(new Vector3(60.5 * .3048, 2, -40 * .3048), new Vector3(0, -1, 0))
    expect(ray.intersectObjects(garden, false)).toHaveLength(0)
    expect(ray.intersectObject(road, false)[0].point.y).toBeCloseTo(-4.445 * .3048, 4)
    expect(study.driveway.minimum_roof_clearance_m).toBeGreaterThanOrEqual(.3)
    expect(study.driveway.minimum_underbody_clearance_m).toBeGreaterThanOrEqual(.1)
  })

  it('keeps site geometry within 7,000 sq ft and models the raised entrance and rear deck', async () => {
    const gltf = await model()
    gltf.scene.updateMatrixWorld(true)
    const site = gltf.scene.getObjectByName('floor_site')
    if (!site) throw new Error('Missing spacious site')
    const bounds = new Box3().setFromObject(site)
    expect(bounds.min.x).toBeGreaterThanOrEqual(-.0001)
    expect(bounds.max.x).toBeLessThanOrEqual(70 * .3048 + .0001)
    expect(bounds.min.z).toBeGreaterThanOrEqual(-study.site.depth_ft * .3048 - .0001)
    expect(bounds.max.z).toBeLessThanOrEqual(.0001)
    const steps: Mesh[] = []
    site.traverse(node => { if (node instanceof Mesh && node.userData.role === 'entry_step') steps.push(node) })
    expect(steps).toHaveLength(3)
    expect(steps.map(step => new Box3().setFromObject(step).max.y / .3048).sort()).toEqual(
      expect.arrayContaining([expect.closeTo(.5, 4), expect.closeTo(1, 4), expect.closeTo(1.5, 4)]))
    let deck: Mesh | undefined
    site.traverse(node => { if (node instanceof Mesh && node.name.includes('rear_garden') && node.name.includes('structural_deck_intent')) deck = node })
    if (!deck) throw new Error('Missing raised rear garden structure intent')
    expect(new Box3().setFromObject(deck).min.y).toBeCloseTo(.3048, 5)
    expect(document.nodes.some(node => node.name?.startsWith('web.site.pool.'))).toBe(true)
  })

  it('restores the outboard pool at rear-garden level without earth blocking the pool or ramp', async () => {
    const gltf = await model()
    gltf.scene.updateMatrixWorld(true)
    const meshes: Mesh[] = []
    gltf.scene.traverse(node => { if (node instanceof Mesh && node.userData.floor_id === 'site') meshes.push(node) })
    const water = meshes.find(node => (Array.isArray(node.material) ? node.material : [node.material])
      .some(material => material.name === 'water'))
    if (!water) throw new Error('Missing restored pool water')
    const pool = new Box3().setFromObject(water)
    expect(pool.min.x).toBeCloseTo(57 * .3048, 4)
    expect(pool.max.x).toBeCloseTo(65 * .3048, 4)
    expect(pool.min.z).toBeCloseTo(-98 * .3048, 4)
    expect(pool.max.z).toBeCloseTo(-82 * .3048, 4)
    expect(pool.min.y).toBeCloseTo((1.5 - .35) * .3048, 4)
    const garden = meshes.filter(node => (Array.isArray(node.material) ? node.material : [node.material])
      .some(material => material.name === 'garden'))
    const ray = new Raycaster()
    for (const [x, y] of [[61, 90], [55.5, 77]]) {
      ray.set(new Vector3(x * .3048, 3, -y * .3048), new Vector3(0, -1, 0))
      expect(ray.intersectObjects(garden, false)).toHaveLength(0)
    }
    ray.set(new Vector3(40 * .3048, 3, -90 * .3048), new Vector3(0, -1, 0))
    expect(ray.intersectObjects(garden, false)[0].point.y).toBeGreaterThanOrEqual(1.5 * .3048 - .0001)
  })
})

describe('presentation without duplicating house geometry', () => {
  it('defaults to all four floors with the site off', () => {
    expect(displayedFloors('side-by-side', defaultVisibility(), 'ground')).toHaveLength(4)
    expect(defaultVisibility().site).toBe(false)
  })

  it('positions wide side-by-side floors at equal spacing', () => {
    expect(floorPosition('basement', 'side-by-side', false)).toEqual([0, 0, 0])
    expect(floorPosition('roof', 'side-by-side', false)).toEqual([66, 0, 0])
  })

  it('uses two rows when the canvas is narrow', () => {
    expect(floorPosition('first', 'side-by-side', true)).toEqual([0, 0, 37])
    expect(floorPosition('roof', 'side-by-side', true)).toEqual([22, 0, 37])
  })

  it('uses proposed physical elevations only in assembled mode', () => {
    expect(floorPosition('basement', 'stacked', false)[1]).toBeCloseTo(-2.5908)
    expect(floorPosition('ground', 'stacked', false)[1]).toBeCloseTo(.4572)
    expect(floorPosition('first', 'stacked', false)[1]).toBeCloseTo(3.81)
    expect(floorPosition('first', 'single', false)).toEqual([0, 0, 0])
  })

  it('separates levels vertically without changing geometry', () => {
    expect(floorPosition('roof', 'exploded', false)[1]).toBeGreaterThan(floorPosition('roof', 'stacked', false)[1])
  })

  it('respects floor visibility, including all-hidden', () => {
    const visible = defaultVisibility()
    visible.roof = false
    expect(displayedFloors('stacked', visible, 'ground')).not.toContain('roof')
    visible.basement = visible.ground = visible.first = false
    expect(displayedFloors('stacked', visible, 'ground')).toEqual([])
  })

  it('shows only the focused floor in single mode', () => {
    expect(displayedFloors('single', defaultVisibility(), 'first')).toEqual(['first'])
  })

  it('does not mix site terrain with floating or underground plan sheets', () => {
    expect(siteAllowed('side-by-side', 'ground')).toBe(false)
    expect(siteAllowed('exploded', 'ground')).toBe(false)
    expect(siteAllowed('single', 'basement')).toBe(false)
    expect(siteAllowed('single', 'ground')).toBe(true)
    expect(siteAllowed('stacked', 'first')).toBe(true)
    expect(sitePosition('single')).toEqual([0, -floors[1].elevation_m, 0])
    expect(sitePosition('stacked')).toEqual([0, 0, 0])
  })

  it('formats fractional room dimensions without losing useful precision', () => {
    expect(formatFeet(17.615384615384617)).toBe('17.62')
    expect(formatFeet(6)).toBe('6')
    for (const value of [0, -1, NaN, Infinity]) expect(() => formatFeet(value)).toThrow('positive finite')
  })

  it('resolves room details without substituting a default room', () => {
    expect(findRoom({ floorId: 'ground', roomId: 'master_bedroom' })?.width_ft).toBe(21.5)
    expect(findRoom({ floorId: 'first', roomId: 'office' })?.name).toContain('office')
    expect(findRoom({ floorId: 'first', roomId: 'missing' })).toBeUndefined()
    expect(findRoom(null)).toBeUndefined()
  })

  it('formats areas without implying whole-plot buildability', () => {
    expect(formatArea(7000)).toBe('7,000')
    expect(formatArea(21.5 * 17.5)).toBe('376.3')
  })

  it('formats proposed lengths honestly in feet and metres', () => {
    expect(formatLength(16)).toBe('16 ft / 4.88 m')
    expect(formatLength(50)).toBe('50 ft / 15.24 m')
    expect(formatLength(6.5)).toBe('6.5 ft / 1.98 m')
    expect(formatLength(22.828125)).toBe('22.83 ft / 6.96 m')
    expect(() => formatLength(0)).toThrow()
    expect(() => formatLength(NaN)).toThrow()
  })

  it('annotates existing bounds without changing their position, extents or net area', () => {
    const room = findRoom({ floorId: 'ground', roomId: 'family_living' })
    if (!room) throw new Error('Missing family living room')
    const before = structuredClone(room)
    const lines = dimensionLines(room.bounds, room.width_ft, room.depth_ft)
    expect(lines).toHaveLength(2)
    expect(lines[0].end[0] - lines[0].start[0]).toBeCloseTo(room.bounds.width)
    expect(lines[1].end[2] - lines[1].start[2]).toBeCloseTo(room.bounds.depth)
    expect(room).toEqual(before)
    expect(room.area_sq_ft).toBe(343.5)
  })

  it('places room label anchors inside actual net footprints, never inside a pantry or shaft hole', () => {
    for (const floor of floors) {
      for (const room of floor.rooms) {
        const [x, y, z] = roomLabelAnchor(room)
        expect(y).toBeGreaterThan(0.9144)
        expect(room.footprints.some((part) => x > part.x && x < part.x + part.width && z > part.z && z < part.z + part.depth)).toBe(true)
        expect(room.label.length).toBeGreaterThan(0)
      }
    }
  })

  it('does not label hidden rooms through assembled slabs', () => {
    expect(annotationFloors('stacked', ['basement', 'ground', 'first', 'roof'])).toEqual(['roof'])
    expect(annotationFloors('stacked', ['basement', 'ground'])).toEqual(['ground'])
    expect(annotationFloors('stacked', [])).toEqual([])
    expect(annotationFloors('side-by-side', ['basement', 'ground'])).toEqual(['basement', 'ground'])
  })

  it('culls annotation collisions, tiny rooms and offscreen tags while prioritising the selection', () => {
    const candidate = (key: string, changes: Partial<RoomAnnotation> = {}): RoomAnnotation => ({
      key, x: 100, y: 100, width: 80, height: 32, projectedWidth: 100, projectedHeight: 60, priority: 10, ...changes,
    })
    const tags = [
      candidate('normal'), candidate('selected', { priority: 100 }), candidate('separate', { x: 250 }),
      candidate('tiny-width', { x: 350, projectedWidth: 51.99 }), candidate('tiny-depth', { x: 350, projectedHeight: 27.99 }),
      candidate('offscreen', { x: 5 }), candidate('under-warning', { y: 30 }),
    ]
    expect([...visibleRoomAnnotations(tags, 500, 300, 50)]).toEqual(['selected', 'separate'])
    expect([...visibleRoomAnnotations([candidate('threshold', { projectedWidth: 52, projectedHeight: 28 })], 500, 300)]).toEqual(['threshold'])
  })
})
