import { describe, expect, it } from 'vitest'
import { DETAILED_FRAMES, detailedCaptions, detailedCuts, detailedFrame, detailedLandscapeMetadata, detailedMetadata, detailedShots } from './detailedTour'
import { findRoom, floors } from './model'
import { tourMetadata } from './tour'
import { PerspectiveCamera, Vector3 } from 'three'
import { roomLabelAnchor } from './model'
import { tourFormats } from './tour'

describe('the detailed phone-first camera tour', () => {
  it('preserves the short film and provides exactly three and a half minutes', () => {
    expect(tourMetadata.frames).toBe(1800)
    expect([detailedMetadata.width, detailedMetadata.height, detailedMetadata.fps, DETAILED_FRAMES]).toEqual([1080, 1920, 30, 6300])
    expect(detailedMetadata.seconds).toBe(210)
    expect(detailedMetadata.audio).toBe('silent')
  })
  it('covers every frame with a finite close-up camera and caption', () => {
    for (let frame = 0; frame < DETAILED_FRAMES; frame++) {
      const state = detailedFrame(frame)
      const focus = state.camera.focus!
      expect([...focus.target, focus.distance, state.camera.yaw, state.camera.elevation].every(Number.isFinite)).toBe(true)
      expect(focus.distance).toBeGreaterThanOrEqual(9)
      expect(focus.distance).toBeLessThanOrEqual(36)
      expect(state.opacity).toBeGreaterThanOrEqual(0)
      expect(state.opacity).toBeLessThanOrEqual(1)
      expect(state.caption.text).not.toMatch(/undefined|NaN/)
      expect(state.shot.mode).toBe('single')
    }
  })
  it('visits every canonical room and both gardens, lawn, pool and balconies', () => {
    for (const floor of floors) {
      const covered = new Set(detailedShots.filter((shot) => shot.floor === floor.id).flatMap((shot) => shot.rooms))
      for (const room of floor.rooms) expect(covered.has(room.id), `${floor.id}/${room.id}`).toBe(true)
    }
    for (const shot of detailedShots) for (const roomId of shot.rooms) expect(findRoom({ floorId: shot.floor, roomId })).toBeDefined()
    expect(detailedShots.some((shot) => /front garden/i.test(shot.title))).toBe(true)
    expect(detailedShots.some((shot) => /family lawn/i.test(shot.title))).toBe(true)
    expect(detailedShots.some((shot) => /pool/i.test(shot.title))).toBe(true)
    expect(detailedShots.filter((shot) => /balcony/i.test(shot.title))).toHaveLength(2)
  })
  it('keeps nearby camera paths continuous and dissolves distant relocations instead of whip-panning', () => {
    for (let i = 1; i < detailedShots.length; i++) {
      const shot = detailedShots[i], previous = detailedShots[i - 1]
      const next = detailedFrame(shot.start * 30)
      if (!detailedCuts[i]) {
        expect(next.camera.focus?.target).toEqual(previous.to.target)
        expect(next.camera.focus?.distance).toBe(previous.to.distance)
        expect(next.opacity).toBe(1)
      } else expect(next.opacity).toBe(0)
    }
    expect(detailedFrame(0).camera.focus?.target).not.toEqual(detailedFrame(300).camera.focus?.target)
  })
  it('exports contiguous matching subtitles, full credits and valid bounds', () => {
    expect(detailedMetadata.subtitles).toContain('00:03:22,000 --> 00:03:30,000')
    expect(detailedCaptions[0].start).toBe(0)
    for (let i = 1; i < detailedCaptions.length; i++) expect(detailedCaptions[i].start).toBe(detailedCaptions[i - 1].end)
    expect(detailedMetadata.musicCredit.soundcloud).toBe('https://soundcloud.com/fredjimusic')
    expect(detailedMetadata.musicCredit.facebook).toBe('https://www.facebook.com/fredjimusic/')
    for (const frame of [-1, DETAILED_FRAMES, 1.2, Infinity, NaN]) expect(() => detailedFrame(frame)).toThrow()
  })
  it.each(['portrait', 'landscape'] as const)('actually frames every room centre in the %s safe area, not just in the itinerary', (aspect) => {
    const seen = new Set<string>()
    const { width, height } = tourFormats[aspect]
    const camera = new PerspectiveCamera(45, width / height, 0.1, 800)
    if (aspect === 'landscape') camera.setViewOffset(width, height, 0, height * detailedLandscapeMetadata.cameraVerticalOffset, width, height)
    for (let frame = 0; frame < DETAILED_FRAMES; frame += 15) {
      const state = detailedFrame(frame, aspect)
      if (state.opacity < 0.9) continue
      const focus = state.camera.focus!
      const target = new Vector3(...focus.target)
      const { yaw, elevation } = state.camera
      camera.position.copy(target).addScaledVector(new Vector3(Math.cos(yaw) * Math.cos(elevation), Math.sin(elevation), Math.sin(yaw) * Math.cos(elevation)), focus.distance)
      camera.lookAt(target)
      camera.updateMatrixWorld()
      for (const source of floors.find((floor) => floor.id === state.shot.floor)!.rooms) {
        const projected = new Vector3(...roomLabelAnchor(source)).project(camera)
        if (Math.abs(projected.x) < 0.9 && projected.y > (aspect === 'landscape' ? -0.48 : -0.62) && projected.y < 0.68 && Math.abs(projected.z) < 1) seen.add(`${state.shot.floor}/${source.id}`)
      }
    }
    const missing = floors.flatMap((floor) => floor.rooms.filter((room) => !seen.has(`${floor.id}/${room.id}`)).map((room) => `${floor.id}/${room.id}`))
    expect(missing).toEqual([])
  })
  it('keeps landscape timing, subjects and subtitles identical while adjusting native camera framing', () => {
    expect([detailedLandscapeMetadata.width, detailedLandscapeMetadata.height, detailedLandscapeMetadata.frames]).toEqual([1920, 1080, 6300])
    expect(detailedLandscapeMetadata.subtitles).toBe(detailedMetadata.subtitles)
    expect(detailedLandscapeMetadata.shots).toBe(detailedMetadata.shots)
    for (let frame = 0; frame < DETAILED_FRAMES; frame++) {
      const portrait = detailedFrame(frame), landscape = detailedFrame(frame, 'landscape')
      expect(landscape.camera.focus?.target).toEqual(portrait.camera.focus?.target)
      expect(landscape.camera.focus?.distance).toBe(portrait.camera.focus?.distance)
      expect(landscape.camera.focus?.offsetY).toBe(detailedLandscapeMetadata.cameraVerticalOffset)
      expect(landscape.opacity).toBe(portrait.opacity)
      expect(landscape.caption).toBe(portrait.caption)
    }
  })
})
