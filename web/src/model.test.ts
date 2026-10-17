import { describe, expect, it, vi } from 'vitest'
import { createHash } from 'node:crypto'
import { readFileSync } from 'node:fs'
import { inflateSync } from 'node:zlib'
import { Box3, Mesh, Vector3 } from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { MeshoptDecoder } from 'meshoptimizer/decoder'
import {
  defaultVisibility, dimensionLines, displayedFloors, findRoom, floorPosition, floors, formatArea, formatLength, siteAllowed, study,
} from './model'

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
    expect(document.nodes.filter((node) => node.extras?.self_closing_intent === true)).toHaveLength(3)
    for (const floor of floors) {
      for (const room of floor.rooms.filter((room) => !['stairs', 'circulation'].includes(room.kind))) {
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
      expect(svg).toContain(`${study.site.width_ft} x ${study.site.depth_ft} ft`)
    }
  })

  it('retains the four floors and explicit concept status', () => {
    expect(floors.map((floor) => floor.id)).toEqual(['basement', 'ground', 'first', 'roof'])
    expect(study.status).toBe('unapproved_concept')
    expect(study.site.area_sq_ft).toBe(7000)
    expect(Object.values(study.mesh_counts).every((count) => count > 0)).toBe(true)
  })

  it('locks the source layout and brief byte-for-byte during visual refinement', () => {
    const layout = readFileSync(new URL('../../house-spec/layout-study.json', import.meta.url))
    const brief = readFileSync(new URL('../../house-spec/house.json', import.meta.url))
    expect(createHash('sha256').update(layout).digest('hex')).toBe('784ae6fe54e51c9d338fd7c2275b38cdc8e5f7ae961ff85c4815026e12f3f098')
    expect(createHash('sha256').update(brief).digest('hex')).toBe('40257587e167234d247ab185b8ce549c0329220c789706f1e1039e425d1993b3')
    expect(study.layout_sha256).toBe(createHash('sha256').update(layout).digest('hex'))
    expect(study.visual_quality).toBe('refined-01')
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

  it('preserves every rendered room footprint and all 99 source furniture placements', async () => {
    const layout: { floors: { id: string; furniture: { id: string; kind: string; rect: number[] }[] }[] } =
      JSON.parse(readFileSync(new URL('../../house-spec/layout-study.json', import.meta.url), 'utf8'))
    const gltf = await model()
    gltf.scene.updateMatrixWorld(true)
    const meshes: Mesh[] = []
    gltf.scene.traverse((node) => { if (node instanceof Mesh) meshes.push(node) })
    for (const floor of floors) {
      for (const room of floor.rooms.filter((room) => !['stairs', 'circulation'].includes(room.kind))) {
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
    expect(checked).toBe(99)
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

  it('retains the revised basement, garden kitchen and actual net L-shaped floor geometry', async () => {
    const living = findRoom({ floorId: 'ground', roomId: 'family_living' })
    const kitchen = findRoom({ floorId: 'ground', roomId: 'kitchen' })
    const pantry = findRoom({ floorId: 'ground', roomId: 'pantry' })
    expect(study.study_id).toBe('study-003')
    expect(floors[0].bounds.depth / 0.3048).toBeCloseTo(88)
    expect(living?.area_sq_ft).toBe(281.75)
    expect(living?.footprints.length).toBeGreaterThan(1)
    expect(kitchen?.bounds.z).toBeCloseTo(-69.5 * 0.3048)
    expect(pantry?.bounds.x).toBeCloseTo((26.5 + 12 + 0.5) * 0.3048)
    const gltf = await model()
    gltf.scene.updateMatrixWorld(true)
    const tiles: Mesh[] = []
    gltf.scene.traverse((node) => {
      if (node instanceof Mesh && node.userData.floor_id === 'ground' && !('fixture_id' in node.userData)) tiles.push(node)
    })
    const pantryTile = tiles.find((node) => node.userData.room_id === 'pantry')
    if (!pantryTile) throw new Error('GLB is missing the enclosed pantry tile')
    const pantryBox = new Box3().setFromObject(pantryTile)
    const livingBoxes = tiles.filter((node) => node.userData.room_id === 'family_living').map((node) => new Box3().setFromObject(node))
    expect(livingBoxes).toHaveLength(3)
    const area = livingBoxes.reduce((total, box) => total + (box.max.x - box.min.x) * (box.max.z - box.min.z), 0)
    expect(area / 0.09290304).toBeCloseTo(281.75, 3)
    for (const box of livingBoxes) {
      const overlapX = Math.max(0, Math.min(box.max.x, pantryBox.max.x) - Math.max(box.min.x, pantryBox.min.x))
      const overlapZ = Math.max(0, Math.min(box.max.z, pantryBox.max.z) - Math.max(box.min.z, pantryBox.min.z))
      expect(overlapX * overlapZ).toBeLessThan(0.00001)
    }
  })

  it('exports larger equal child bedrooms, private walk-ins and the front office WC', async () => {
    const gltf = await model()
    gltf.scene.updateMatrixWorld(true)
    for (let i = 1; i <= 3; i++) {
      const roomId = `child_bedroom_${i}`
      expect(findRoom({ floorId: 'first', roomId })?.area_sq_ft).toBe(272)
      const tiles: Mesh[] = []
      gltf.scene.traverse((node) => {
        if (node instanceof Mesh && node.userData.floor_id === 'first' && node.userData.room_id === roomId && !('fixture_id' in node.userData)) tiles.push(node)
      })
      expect(tiles).toHaveLength(1)
      const box = new Box3().setFromObject(tiles[0])
      expect((box.max.x - box.min.x) * (box.max.z - box.min.z) / 0.09290304).toBeCloseTo(272, 3)
      expect(findRoom({ floorId: 'first', roomId: `child_wardrobe_${i}` })?.area_sq_ft).toBeGreaterThanOrEqual(38.5)
    }
    expect(findRoom({ floorId: 'first', roomId: 'office' })?.bounds.x).toBeCloseTo(28 * 0.3048)
    expect(findRoom({ floorId: 'first', roomId: 'office_toilet' })?.area_sq_ft).toBe(40)
    const toiletIds = new Set(document.nodes.map((node) => node.extras?.fixture_id).filter((id) =>
      typeof id === 'string' && /^(basement_wc|guest_wc|family_wc|master_wc_[12]|child[123]_wc|office_wc)$/.test(id)))
    expect(toiletIds.size).toBe(9)
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
    expect(enclosures).toHaveLength(12)
    expect(enclosures.filter((node) => node.extras?.entry_door === true)).toHaveLength(3)
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
    expect(floorPosition('basement', 'stacked', false)[1]).toBeCloseTo(-3.048)
    expect(floorPosition('first', 'stacked', false)[1]).toBeCloseTo(3.3528)
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
    expect(room.area_sq_ft).toBe(281.75)
  })
})
