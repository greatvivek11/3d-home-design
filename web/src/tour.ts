import { findRoom, floors, formatArea, study } from './model'
import type { FloorId, Position, ViewMode, Visibility } from './model'

export const TOUR_FPS = 30
export const TOUR_SECONDS = 60
export const TOUR_FRAMES = TOUR_FPS * TOUR_SECONDS
export const tourFormats = { portrait: { width: 1080, height: 1920 }, landscape: { width: 1920, height: 1080 } } as const
export type TourAspect = keyof typeof tourFormats
export type TourCamera = { yaw: number; elevation: number; scale: number; focus?: { target: Position; distance: number; offsetY?: number } }
type Shot = {
  start: number; end: number; mode: ViewMode; floor: FloorId; site: boolean
  kicker: string; title: string; detail: string; yaw: number; elevation: number
}
export const tourShots: Shot[] = [
  { start: 0, end: 6, mode: 'exploded', floor: 'ground', site: false,
    kicker: 'THE BIG PICTURE', title: 'A place to\ncall home.', detail: '5 bedrooms / 4 connected levels', yaw: 72, elevation: 27 },
  { start: 6, end: 14, mode: 'single', floor: 'ground', site: true,
    kicker: 'SPACE TO BREATHE', title: 'Closer to\nnature.', detail: `${formatArea(study.site.area_sq_ft)} sq ft plot / gardens + pool`, yaw: 88, elevation: 65 },
  { start: 14, end: 26, mode: 'single', floor: 'ground', site: false,
    kicker: 'GROUND FLOOR', title: 'Room for\nfamily life.', detail: 'Drawing / guest suite / master / open family spaces', yaw: 78, elevation: 65 },
  { start: 26, end: 38, mode: 'single', floor: 'first', site: false,
    kicker: 'FIRST FLOOR', title: 'A world of\ntheir own.', detail: '3 equal bedrooms / family lounge / office', yaw: 85, elevation: 66 },
  { start: 38, end: 48, mode: 'single', floor: 'basement', site: false,
    kicker: 'BASEMENT', title: 'Play. Move.\nMake room.', detail: '3 SUVs / gym / gaming / laundry / storage', yaw: 88, elevation: 67 },
  { start: 48, end: 55, mode: 'single', floor: 'roof', site: false,
    kicker: 'ROOF TERRACE', title: 'Life under\nan open sky.', detail: 'Gathering / shaded seating / planting / solar reserve', yaw: 76, elevation: 63 },
  { start: 55, end: 60, mode: 'exploded', floor: 'ground', site: false,
    kicker: 'OUR DREAM HOME', title: 'Designed for\nlife together.', detail: 'Space for today. Possibilities for tomorrow.', yaw: 90, elevation: 28 },
]

function area(floorId: FloorId, roomId: string) {
  const room = findRoom({ floorId, roomId })
  if (!room) throw new Error(`Tour room is missing: ${floorId}/${roomId}`)
  return formatArea(room.area_sq_ft)
}
export const tourCaptions = [
  { start: 0, end: 6, text: 'A nature-connected family home, imagined across basement, ground, first floor and roof.' },
  { start: 6, end: 10, text: `A ${study.site.width_ft} by ${study.site.depth_ft} ft plot gives the house space to breathe.` },
  { start: 10, end: 14, text: 'Front gardens, a rear play lawn and an 8 by 16 ft pool bring family life outdoors.' },
  { start: 14, end: 20, text: 'One controlled front entrance leads to the drawing room and a guest bedroom with its own ensuite.' },
  { start: 20, end: 26, text: 'Beyond the House Gallery: open living and dining, a garden kitchen, pantry and a private master suite.' },
  { start: 26, end: 32, text: `Three equal ${area('first', 'child_bedroom_1')} sq ft bedrooms each have private dressing and bathroom spaces.` },
  { start: 32, end: 38, text: `A ${area('first', 'upstairs_lounge')} sq ft shared lounge makes room for play, beside a separate office and common WC.` },
  { start: 38, end: 43, text: 'Three SUVs park within the garage, served by a curved driveway and a protected two-door airlock.' },
  { start: 43, end: 48, text: 'Equal-sized gym and gaming spaces, quiet-side laundry and household stores keep daily life organised.' },
  { start: 48, end: 52, text: 'A family terrace with shaded seating and planters creates another place to unwind.' },
  { start: 52, end: 55, text: 'Solar space is reserved. Internal stairs and a proposed lift connect all four levels.' },
  { start: 55, end: 60, text: 'Five bedrooms. Shared moments. Private retreats. A home designed around the way we want to live.' },
]
const allVisible: Visibility = { basement: true, ground: true, first: true, roof: true, site: false }

export function tourFrame(frame: number) {
  if (!Number.isInteger(frame) || frame < 0 || frame >= TOUR_FRAMES) throw new Error('Tour frame must be an integer from 0 to 1799')
  const time = frame / TOUR_FPS
  const index = tourShots.findIndex((shot) => time >= shot.start && time < shot.end)
  const shot = tourShots[index]
  const caption = tourCaptions.find((cue) => time >= cue.start && time < cue.end)
  if (!shot || !caption) throw new Error(`Tour timeline is incomplete at frame ${frame}`)
  const progress = (time - shot.start) / (shot.end - shot.start)
  const smooth = progress * progress * (3 - 2 * progress)
  const fadeIn = index === 0 ? 1 : Math.min(1, (time - shot.start) / 0.3)
  const fadeOut = index === tourShots.length - 1 ? 1 : Math.min(1, (shot.end - time) / 0.3)
  return {
    index, shot, caption, time, opacity: Math.min(fadeIn, fadeOut),
    visible: shot.site ? { ...allVisible, site: true } : allVisible,
    camera: { yaw: (shot.yaw - 7 + 14 * smooth) * Math.PI / 180, elevation: shot.elevation * Math.PI / 180, scale: 0.96 + smooth * 0.04 },
  }
}

export function tourSubtitles() {
  const timestamp = (time: number) => {
    const ms = Math.round(time * 1000)
    return `${String(Math.floor(ms / 3600000)).padStart(2, '0')}:${String(Math.floor(ms / 60000) % 60).padStart(2, '0')}:${String(Math.floor(ms / 1000) % 60).padStart(2, '0')},${String(ms % 1000).padStart(3, '0')}`
  }
  return tourCaptions.map((cue, index) => `${index + 1}\n${timestamp(cue.start)} --> ${timestamp(cue.end)}\n${cue.text}\n`).join('\n')
}

export const tourMetadata = {
  studyId: study.study_id, revision: study.revision, layoutSha256: study.layout_sha256,
  ...tourFormats.portrait, aspect: 'portrait', fps: TOUR_FPS, frames: TOUR_FRAMES, seconds: TOUR_SECONDS,
  audio: 'silent', shots: tourShots, captions: tourCaptions, subtitles: tourSubtitles(),
  bedrooms: floors.flatMap((floor) => floor.rooms).filter((room) => room.kind === 'bedroom').length,
}
