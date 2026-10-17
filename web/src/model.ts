import manifest from './generated/house.json'

export const FLOOR_IDS = ['basement', 'ground', 'first', 'roof'] as const
export type FloorId = typeof FLOOR_IDS[number]
export type LayerId = FloorId | 'site'
export type ViewMode = 'side-by-side' | 'stacked' | 'exploded' | 'single'
export type CameraView = 'perspective' | 'plan'
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

export function findRoom(selection: Selection | null): Room | undefined {
  return selection ? floors.find((floor) => floor.id === selection.floorId)?.rooms.find((room) => room.id === selection.roomId) : undefined
}

export function formatArea(area: number): string {
  return new Intl.NumberFormat('en-IN', { maximumFractionDigits: 1 }).format(area)
}

export function formatLength(valueFt: number): string {
  if (!Number.isFinite(valueFt) || valueFt <= 0) throw new Error('A dimension must be a positive finite length')
  return `${new Intl.NumberFormat('en-IN', { maximumFractionDigits: 2 }).format(valueFt)} ft / ${(valueFt * 0.3048).toFixed(2)} m`
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
