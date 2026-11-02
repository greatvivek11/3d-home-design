import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { surfaceKinds } from './realism'

const materialNames = (file: string): string[] => {
  const bytes = readFileSync(new URL(`../public/models/${file}`, import.meta.url))
  const json: { materials: { name: string }[] } = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)).toString('utf8'))
  return json.materials.map((material) => material.name)
}

describe('runtime surface realism', () => {
  const exterior = new Set(materialNames('exterior.glb'))
  const house = new Set(materialNames('house.glb'))

  it('only targets materials that exist in the shipped models', () => {
    for (const name of Object.keys(surfaceKinds)) expect(exterior.has(name) || house.has(name), name).toBe(true)
  })

  it('covers the large exterior surfaces that previously rendered flat', () => {
    for (const name of ['context', 'plaster', 'facade_stone', 'boundary_stone', 'road', 'ridge_near', 'leaf_a', 'pine_a']) {
      expect(surfaceKinds[name], name).toBeDefined()
    }
  })

  it('never touches glass, metal or emissive materials', () => {
    for (const name of ['glass', 'facade_glass', 'metal', 'brass', 'chrome', 'lamp_glow', 'frame']) expect(surfaceKinds[name], name).toBeUndefined()
  })
})
