import manifest from './generated/house.json'

export const FLOOR_IDS = ['basement', 'ground', 'first', 'roof'] as const
export type FloorId = typeof FLOOR_IDS[number]
export type LayerId = FloorId | 'site'
export type ViewMode = 'side-by-side' | 'stacked' | 'exploded' | 'single'
export type CameraView = 'perspective' | 'plan'
export type Inspection = 'furnished' | 'structure'
export type Visibility = Record<LayerId, boolean>
export type Selection = { floorId: FloorId; roomId: string }
export type Position = [number, number, number]
export type DimensionLine = {
  id: 'width' | 'depth'
  label: string
  start: Position
  end: Position
  from: Position
  to: Position
}

export const study = manifest
export const floors = FLOOR_IDS.map((id) => {
  const floor = manifest.floors.find((item) => item.id === id)
  if (!floor) throw new Error(`Model manifest is missing the ${id} floor`)
  return { ...floor, id }
})
export type Floor = typeof floors[number]
export type Room = Floor['rooms'][number]
export type RoomAnnotation = {
  key: string
  x: number
  y: number
  width: number
  height: number
  projectedWidth: number
  projectedHeight: number
  priority: number
}

export const floorColors: Record<FloorId, string> = {
  basement: '#a18564', ground: '#6f8b72', first: '#7d91a5', roof: '#b49966',
}

export const modes: { id: Exclude<ViewMode, 'single'>; label: string; description: string }[] = [
  { id: 'side-by-side', label: 'Side by side', description: 'Compare every level' },
  { id: 'stacked', label: 'Assembled', description: 'Actual floor elevations' },
  { id: 'exploded', label: 'Separated', description: 'See between levels' },
]

export function defaultVisibility(): Visibility {
  return { basement: true, ground: true, first: true, roof: true, site: false }
}

export function displayedFloors(mode: ViewMode, visible: Visibility, single: FloorId): FloorId[] {
  return FLOOR_IDS.filter((id) => visible[id] && (mode !== 'single' || id === single))
}

export function floorPosition(id: FloorId, mode: ViewMode, compact: boolean): Position {
  const index = FLOOR_IDS.indexOf(id)
  const floor = floors[index]
  if (mode === 'side-by-side') {
    return compact ? [(index % 2) * 22, 0, Math.floor(index / 2) * 37] : [index * 22, 0, 0]
  }
  if (mode === 'stacked') return [0, floor.elevation_m, 0]
  if (mode === 'exploded') return [0, floor.elevation_m + index * 5, 0]
  return [0, 0, 0]
}

export function siteAllowed(mode: ViewMode, single: FloorId): boolean {
  return mode === 'stacked' || (mode === 'single' && single === 'ground')
}

export function sitePosition(mode: ViewMode): Position {
  return [0, mode === 'single' ? -floors[1].elevation_m : 0, 0]
}

export function findRoom(selection: Selection | null): Room | undefined {
  return selection ? floors.find((floor) => floor.id === selection.floorId)?.rooms.find((room) => room.id === selection.roomId) : undefined
}

export function annotationFloors(mode: ViewMode, active: FloorId[]): FloorId[] {
  if (mode !== 'stacked') return active
  return floors.filter((floor) => active.includes(floor.id)).sort((a, b) => b.elevation_m - a.elevation_m).slice(0, 1).map((floor) => floor.id)
}

export function roomLabelAnchor(room: Room): Position {
  const part = room.footprints.reduce((largest, next) => next.width * next.depth > largest.width * largest.depth ? next : largest)
  return [part.x + part.width / 2, 1.04, part.z + part.depth / 2]
}

export function visibleRoomAnnotations(candidates: RoomAnnotation[], width: number, height: number, topInset = 0): Set<string> {
  const visible = new Set<string>()
  const occupied: { left: number; top: number; right: number; bottom: number }[] = []
  for (const item of [...candidates].sort((a, b) => b.priority - a.priority || b.projectedWidth * b.projectedHeight - a.projectedWidth * a.projectedHeight)) {
    if (item.projectedWidth < 52 || item.projectedHeight < 28) continue
    const rect = { left: item.x - item.width / 2, top: item.y - item.height / 2, right: item.x + item.width / 2, bottom: item.y + item.height / 2 }
    if (rect.left < 2 || rect.right > width - 2 || rect.top < topInset + 2 || rect.bottom > height - 2) continue
    if (occupied.some((other) => rect.left < other.right + 3 && rect.right > other.left - 3 && rect.top < other.bottom + 3 && rect.bottom > other.top - 3)) continue
    occupied.push(rect)
    visible.add(item.key)
  }
  return visible
}

export function formatArea(area: number): string {
  return new Intl.NumberFormat('en-IN', { maximumFractionDigits: 1 }).format(area)
}

export function formatFeet(valueFt: number): string {
  if (!Number.isFinite(valueFt) || valueFt <= 0) throw new Error('A dimension must be a positive finite length')
  return new Intl.NumberFormat('en-IN', { maximumFractionDigits: 2 }).format(valueFt)
}

export function formatLength(valueFt: number): string {
  return `${formatFeet(valueFt)} ft / ${(valueFt * 0.3048).toFixed(2)} m`
}

export function dimensionLines(bounds: Room['bounds'], widthFt: number, depthFt: number, offset = 0.6): DimensionLine[] {
  const { x, z, width, depth } = bounds
  const y = 0.08
  return [
    { id: 'width', label: formatLength(widthFt), start: [x, y, z + depth + offset], end: [x + width, y, z + depth + offset],
      from: [x, y, z + depth], to: [x + width, y, z + depth] },
    { id: 'depth', label: formatLength(depthFt), start: [x + width + offset, y, z], end: [x + width + offset, y, z + depth],
      from: [x + width, y, z], to: [x + width, y, z + depth] },
  ]
}
