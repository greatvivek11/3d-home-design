import { describe, expect, it } from 'vitest'
import { TOUR_FRAMES, tourCaptions, tourFrame, tourMetadata, tourShots, tourSubtitles } from './tour'
import { study } from './model'

describe('the portrait family film', () => {
  it('uses the current canonical study, portrait HD and exactly one minute', () => {
    expect(tourMetadata.studyId).toBe(study.study_id)
    expect(tourMetadata.layoutSha256).toBe(study.layout_sha256)
    expect([tourMetadata.width, tourMetadata.height, tourMetadata.fps, tourMetadata.frames]).toEqual([1080, 1920, 30, 1800])
    expect(tourMetadata.bedrooms).toBe(5)
    expect(tourMetadata.audio).toBe('silent')
  })
  it('covers every frame with a camera, chapter and readable caption', () => {
    for (let frame = 0; frame < TOUR_FRAMES; frame++) {
      const value = tourFrame(frame)
      expect(value.caption.text).not.toMatch(/undefined|NaN/)
      expect(value.opacity).toBeGreaterThanOrEqual(0)
      expect(value.opacity).toBeLessThanOrEqual(1)
      expect(Object.values(value.camera).every(Number.isFinite)).toBe(true)
      expect(tourShots.filter((shot) => value.time >= shot.start && value.time < shot.end)).toHaveLength(1)
      expect(tourCaptions.filter((cue) => value.time >= cue.start && value.time < cue.end)).toHaveLength(1)
    }
  })
  it('rejects invalid frames instead of exporting a misleading timeline', () => {
    for (const frame of [-1, 1800, 1.5, NaN, Infinity]) expect(() => tourFrame(frame)).toThrow()
  })
  it('moves the camera without changing model geometry and covers all four floors', () => {
    expect(tourFrame(420).camera.yaw).not.toBe(tourFrame(779).camera.yaw)
    expect(new Set(tourShots.filter((shot) => shot.mode === 'single').map((shot) => shot.floor))).toEqual(new Set(['ground', 'first', 'basement', 'roof']))
    expect(tourFrame(200).visible.site).toBe(true)
    expect(tourFrame(500).visible.site).toBe(false)
  })
  it('exports matching, contiguous subtitle timing and current room areas', () => {
    const srt = tourSubtitles()
    expect(srt).toContain('00:00:00,000 --> 00:00:06,000')
    expect(srt).toContain('00:00:55,000 --> 00:01:00,000')
    expect(srt).toContain('272 sq ft')
    expect(srt).toContain('653 sq ft')
    for (let i = 1; i < tourCaptions.length; i++) expect(tourCaptions[i].start).toBe(tourCaptions[i - 1].end)
  })
})
