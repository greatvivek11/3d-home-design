import layout from '../../house-spec/layout-study.json'
import { findRoom, roomLabelAnchor } from './model'
import type { FloorId, Position } from './model'
import { TOUR_FPS, tourFormats, tourMetadata } from './tour'
import type { TourAspect, TourCamera } from './tour'

export const DETAILED_SECONDS = 210
export const DETAILED_FRAMES = DETAILED_SECONDS * TOUR_FPS
type Point = { target: Position; distance: number; yaw: number; elevation: number }
type Stop = {
  start: number; end: number; floor: FloorId; title: string; text: string
  rooms: string[]; at: Point; to: Point
}
const point = (target: Position, distance = 13, yaw = 80, elevation = 58): Point => ({ target, distance, yaw, elevation })
function room(floorId: FloorId, roomId: string, distance = 13, dx = 0, dz = 0, yaw = 80): Point {
  const source = findRoom({ floorId, roomId })
  if (!source) throw new Error(`Detailed tour room is missing: ${floorId}/${roomId}`)
  const [x, , z] = roomLabelAnchor(source)
  return point([x + dx, 0.45, z + dz], distance, yaw)
}
function outside(id: string, distance: number, dx = 0, dz = 0, yaw = 80): Point {
  const source = layout.outdoor.find((item) => item.id === id)
  if (!source) throw new Error(`Detailed tour garden feature is missing: ${id}`)
  const [x, z, width, depth] = source.rect
  return point([(x + width / 2) * 0.3048 + dx, 0.1, -(z + depth / 2) * 0.3048 + dz], distance, yaw, 52)
}
const rearBalcony = layout.balconies.find((item) => item.id === 'rear_balcony')
if (!rearBalcony) throw new Error('Detailed tour rear balcony is missing')
const [bx, by, bw, bd] = rearBalcony.rect
const groundEnvelope = layout.floors.find((floor) => floor.id === 'ground')?.envelope
if (!groundEnvelope) throw new Error('Detailed tour ground envelope is missing')
const [gx, gy, gw, gd] = groundEnvelope

const stops: Stop[] = [
  { start: 0, end: 12, floor: 'ground', title: 'Arriving through the front garden',
    text: 'Welcome home. The front garden and tea veranda lead to one controlled entrance.',
    rooms: [], at: outside('front_lawn', 19, -2, 0.4, 100), to: outside('entry_path', 13, 0, -1.6, 80) },
  { start: 12, end: 19, floor: 'ground', title: 'Entrance Gallery',
    text: 'The four-foot Entrance Gallery welcomes visitors without opening directly into family spaces.',
    rooms: ['entrance_gallery'], at: room('ground', 'entrance_gallery', 10, 0, 1.5), to: room('ground', 'entrance_gallery', 10, 0, -1.5, 92) },
  { start: 19, end: 27, floor: 'ground', title: 'Drawing room',
    text: 'A generous front drawing room gives guests their own place to sit, with garden-facing light.',
    rooms: ['receiving'], at: room('ground', 'receiving', 13, -0.6, 0.6, 100), to: room('ground', 'receiving', 12, 0.5, -0.6, 85) },
  { start: 27, end: 35, floor: 'ground', title: 'Guest bedroom & private ensuite',
    text: 'Across the entrance: a guest bedroom with bedside tables, large glazing and its own shower ensuite.',
    rooms: ['guest_bedroom', 'guest_bathroom'], at: room('ground', 'guest_bedroom', 11, 0, 0.7), to: room('ground', 'guest_bathroom', 10, -0.4, 0.6, 100) },
  { start: 35, end: 43, floor: 'ground', title: 'House Gallery',
    text: 'The House Gallery screens family life behind a privacy wall, with a shared WC and utility cupboard at opposite ends.',
    rooms: ['cross_passage', 'family_toilet', 'utility_store'], at: room('ground', 'utility_store', 11, -0.5), to: room('ground', 'family_toilet', 12, 1.2, 0, 95) },
  { start: 43, end: 54, floor: 'ground', title: 'The private master suite',
    text: 'The master opens from the family zone, with its bed on the west wall under a high sliding window. The private dressing leads to a daylight bathroom.',
    rooms: ['master_bedroom', 'master_wardrobe', 'master_bathroom'],
    at: room('ground', 'master_bedroom', 16, 0.4, -0.5, 98), to: room('ground', 'master_wardrobe', 11, -0.6, -0.4, 85) },
  { start: 54, end: 61, floor: 'ground', title: 'Family dining',
    text: 'Eight seats around a table running along the privacy wall bring everyone together, open to living yet screened from arriving visitors.',
    rooms: ['dining'], at: room('ground', 'dining', 11, -0.3, 0.4), to: room('ground', 'dining', 10, 0.4, -0.4, 100) },
  { start: 61, end: 70, floor: 'ground', title: 'Garden kitchen & pantry',
    text: 'A wide kitchen with an island, a free-standing fridge, a 6 by 10 foot walk-in pantry and windows wrapping the whole counter into the backyard.',
    rooms: ['kitchen', 'pantry'], at: room('ground', 'kitchen', 12, -0.3, 0.3, 98), to: room('ground', 'pantry', 10, -0.5, 0.3, 75) },
  { start: 70, end: 78, floor: 'ground', title: 'Open family living',
    text: 'A larger west-side lounge faces a TV on a wooden cabinet from a comfortable distance, with a large ten-foot garden slider to the rear lawn.',
    rooms: ['family_living'], at: room('ground', 'family_living', 13, 0.2, -1.4, 100), to: room('ground', 'family_living', 12, -0.1, 1.2, 82) },
  { start: 78, end: 84, floor: 'ground', title: 'A quiet prayer corner',
    text: 'The prayer alcove sits in the north-east corner of the east wall, with a high window behind it, away from the garden doorway and the shared WC.',
    rooms: ['prayer_alcove'], at: room('ground', 'prayer_alcove', 10, -0.5, -0.3), to: room('ground', 'prayer_alcove', 9, 0.2, 0.4, 95) },
  { start: 84, end: 90, floor: 'ground', title: 'Rear veranda & family lawn',
    text: 'Step outside to the rear veranda, swing and play lawn, backed by a planting and tree reserve.',
    rooms: [], at: outside('back_veranda', 17, 3.5, 0, 100), to: outside('play_lawn', 17, 1.8, -0.7, 95) },
  { start: 90, end: 96, floor: 'ground', title: 'The backyard pool',
    text: 'An eight-by-sixteen-foot family pool sits beside the lawn, within its own controlled enclosure.',
    rooms: [], at: outside('pool', 15, -1.2, 0.5, 100), to: outside('pool', 13, 0, -0.6, 80) },
  { start: 96, end: 102, floor: 'ground', title: 'Stairs & front-lawn lift',
    text: 'Internal stairs and the proposed front-lawn lift connect the levels without taking living-room space.',
    rooms: ['stairs', 'lift', 'lift_lobby'], at: room('ground', 'stairs', 14, 0, -1), to: room('ground', 'lift', 13, -0.4, 0.3, 100) },
  { start: 102, end: 110, floor: 'first', title: 'Upstairs office',
    text: 'The separate front-right office makes space for focused work and piano, with daylight from its front balcony slider.',
    rooms: ['office'], at: room('first', 'office', 12, -0.3, 0.7, 100), to: room('first', 'office', 11, 0.3, -0.7, 85) },
  { start: 110, end: 120, floor: 'first', title: 'Child 1 suite & front balcony',
    text: 'The front bedroom has 272 square feet of sleeping space, private dressing and bath, plus shared balcony access.',
    rooms: ['child_bedroom_1', 'child_wardrobe_1', 'child_bathroom_1'],
    at: room('first', 'child_wardrobe_1', 14, 0.7, 0.5, 100), to: room('first', 'child_bedroom_1', 13, 0, 2.6, 80) },
  { start: 120, end: 132, floor: 'first', title: 'One generous family lounge',
    text: "A unified 653-square-foot lounge leaves the central floor open for family time and children's recreation.",
    rooms: ['upstairs_lounge'], at: room('first', 'upstairs_lounge', 13, -4.6, 0, 100), to: room('first', 'upstairs_lounge', 13, 4.6, 0, 85) },
  { start: 132, end: 141, floor: 'first', title: 'Child 2 rear suite',
    text: 'The second equal-size bedroom faces the rear garden, with its own dressing and shower bathroom.',
    rooms: ['child_bedroom_2', 'child_wardrobe_2', 'child_bathroom_2'],
    at: room('first', 'child_bedroom_2', 13, 0.1, -0.5, 98), to: room('first', 'child_bathroom_2', 11, 0.4, -0.4, 80) },
  { start: 141, end: 150, floor: 'first', title: 'Child 3 rear suite',
    text: 'The third bedroom keeps the same 272-square-foot sleeping area and its own private suite facilities.',
    rooms: ['child_bedroom_3', 'child_wardrobe_3', 'child_bathroom_3'],
    at: room('first', 'child_bedroom_3', 13, -0.1, -0.5, 100), to: room('first', 'child_bathroom_3', 11, -0.4, -0.4, 82) },
  { start: 150, end: 155, floor: 'first', title: 'Shared rear balcony',
    text: 'A common rear route reaches the shared balcony overlooking the backyard.',
    rooms: ['rear_gallery'], at: room('first', 'rear_gallery', 12, 0, -0.5, 95), to: point([(bx + bw / 2) * 0.3048, 0.4, -(by + bd / 2) * 0.3048], 15, 80) },
  { start: 155, end: 160, floor: 'first', title: 'The shared stair-side WC',
    text: 'The compact six-by-five-and-a-half-foot common WC stays beside the stairs, away from the play area.',
    rooms: ['first_common_toilet', 'core_lobby', 'stairs', 'lift'],
    at: room('first', 'first_common_toilet', 11, -0.4, 0, 95), to: room('first', 'lift', 14, -0.3, -0.5, 82) },
  { start: 160, end: 168, floor: 'basement', title: 'Driveway & three-SUV garage',
    text: 'The curved ramp reaches a rear turning reserve. Three SUVs park within the garage bays.',
    rooms: ['drive_aisle', 'vehicle_parking', 'two_wheelers'],
    at: room('basement', 'drive_aisle', 23, 7.8, 0, 100), to: room('basement', 'vehicle_parking', 20, 0, 0.3, 80) },
  { start: 168, end: 174, floor: 'basement', title: 'Protected access & household stores',
    text: 'A two-door garage airlock leads to the clean gallery, with separate general and food stores.',
    rooms: ['garage_airlock', 'clean_lobby', 'clean_spine', 'general_storage', 'food_storage', 'stairs', 'lift'],
    at: room('basement', 'garage_airlock', 14, -1.2, 0.2, 95), to: room('basement', 'food_storage', 14, -1.5, 0, 80) },
  { start: 174, end: 181, floor: 'basement', title: 'The home gym',
    text: 'The gym gets the same net floor area as gaming: 387.75 square feet for movement and training.',
    rooms: ['gym', 'front_passage'], at: room('basement', 'gym', 13, -0.5, -0.4, 18), to: room('basement', 'gym', 12, 0.6, 0.4, 0) },
  { start: 181, end: 188, floor: 'basement', title: 'Gaming & recreation',
    text: 'An equally generous recreation room gives gaming and shared hobbies their own place downstairs.',
    rooms: ['tech_cave'], at: room('basement', 'tech_cave', 14, -1, 0.4, 12), to: room('basement', 'tech_cave', 13, 1, -0.4, -5) },
  { start: 188, end: 194, floor: 'basement', title: 'Laundry on the quiet service level',
    text: 'Laundry and a basement WC stay on the clean side, keeping noisy utility work off the ground floor.',
    rooms: ['laundry', 'basement_toilet'], at: room('basement', 'basement_toilet', 14, -0.6, 0, 95), to: room('basement', 'laundry', 15, -1, 0, 80) },
  { start: 194, end: 202, floor: 'roof', title: 'Open-sky family terrace',
    text: 'On the roof: a family gathering terrace and shaded seating, reached by sheltered stairs and the proposed lift.',
    rooms: ['roof_gathering', 'roof_shade', 'stairs', 'lift', 'lift_lobby'],
    at: room('roof', 'lift_lobby', 18, 2.5, 0, 100), to: room('roof', 'roof_shade', 18, 0.5, 0, 85) },
  { start: 202, end: 210, floor: 'roof', title: 'Room to grow, together',
    text: 'Planters and a solar reserve complete the concept. A home for private retreats and shared family life.',
    rooms: ['roof_planters', 'roof_solar'],
    at: room('roof', 'roof_planters', 19, -0.7, 0, 100), to: point([(gx + gw / 2) * 0.3048, 0.4, -(gy + gd / 2) * 0.3048], 36, 84, 60) },
]
export const detailedShots = stops.map((stop) => ({ ...stop, mode: 'single' as const, site: stop.floor === 'ground' }))
export const detailedCaptions = detailedShots.map(({ start, end, text }) => ({ start, end, text }))
const travelDistance = (a: Point, b: Point) => Math.hypot(...a.target.map((value, i) => value - b.target[i]))
export const detailedCuts = detailedShots.map((shot, i) => i > 0
  && (shot.floor !== detailedShots[i - 1].floor || travelDistance(detailedShots[i - 1].to, shot.at) > 6))

function mix(a: Point, b: Point, amount: number): Point {
  const t = Math.max(0, Math.min(1, amount))
  const smooth = t * t * (3 - 2 * t)
  const lerp = (x: number, y: number) => x + (y - x) * smooth
  return {
    target: [lerp(a.target[0], b.target[0]), lerp(a.target[1], b.target[1]), lerp(a.target[2], b.target[2])],
    distance: lerp(a.distance, b.distance), yaw: lerp(a.yaw, b.yaw), elevation: lerp(a.elevation, b.elevation),
  }
}
export function detailedFrame(frame: number, aspect: TourAspect = 'portrait') {
  if (!Number.isInteger(frame) || frame < 0 || frame >= DETAILED_FRAMES) throw new Error(`Detailed tour frame must be an integer from 0 to ${DETAILED_FRAMES - 1}`)
  const time = frame / TOUR_FPS
  const index = detailedShots.findIndex((shot) => time >= shot.start && time < shot.end)
  const shot = detailedShots[index]
  if (!shot) throw new Error(`Detailed tour timeline is incomplete at frame ${frame}`)
  const previous = detailedShots[index - 1]
  const enteringCut = !previous || detailedCuts[index]
  const leavingCut = detailedCuts[index + 1]
  const progress = (time - shot.start) / (shot.end - shot.start)
  const travel = previous ? travelDistance(previous.to, shot.at) : 0
  const transition = Math.min(0.45, Math.max(1.2, travel * 0.5) / (shot.end - shot.start))
  const position = !enteringCut && progress < transition
    ? mix(previous.to, shot.at, progress / transition)
    : mix(shot.at, shot.to, enteringCut ? progress : (progress - transition) / (1 - transition))
  const camera: TourCamera = { yaw: position.yaw * Math.PI / 180, elevation: position.elevation * Math.PI / 180,
    scale: 1, focus: { target: position.target, distance: position.distance, offsetY: aspect === 'landscape' ? 0.06 : 0 } }
  return {
    index, shot, time, caption: detailedCaptions[index], camera,
    visible: { basement: true, ground: true, first: true, roof: true, site: shot.site },
    opacity: Math.min(enteringCut && index > 0 ? Math.min(1, (time - shot.start) / 0.25) : 1,
      leavingCut ? Math.min(1, (shot.end - time) / 0.25) : 1),
  }
}
const stamp = (time: number) => `${String(Math.floor(time / 3600)).padStart(2, '0')}:${String(Math.floor(time / 60) % 60).padStart(2, '0')}:${String(time % 60).padStart(2, '0')},000`
export const detailedMetadata = {
  ...tourMetadata, variant: 'detailed', frames: DETAILED_FRAMES, seconds: DETAILED_SECONDS,
  shots: detailedShots, captions: detailedCaptions,
  subtitles: detailedCaptions.map((cue, i) => `${i + 1}\n${stamp(cue.start)} --> ${stamp(cue.end)}\n${cue.text}\n`).join('\n'),
  musicCredit: { title: 'Flying High - FREDJI', soundcloud: 'https://soundcloud.com/fredjimusic', facebook: 'https://www.facebook.com/fredjimusic/' },
}
export const detailedLandscapeMetadata = {
  ...detailedMetadata, ...tourFormats.landscape, aspect: 'landscape', cameraVerticalOffset: 0.06,
}
