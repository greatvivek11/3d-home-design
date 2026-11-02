import { Mesh, MeshStandardMaterial } from 'three'
import type { Object3D, WebGLProgramParametersWithUniforms } from 'three'

// Runtime surface detail for the GLB's flat or low-frequency materials. Everything is a function of
// world position, so it needs no UVs, adds no textures and leaves the Blender pipeline untouched.
// High octaves fade out with screen-space derivatives to avoid shimmer at distance.

export type SurfaceKind = 'grass' | 'stucco' | 'stone' | 'foliage' | 'asphalt' | 'gravel' | 'forest'

export const realismEnabled = () => typeof location === 'undefined' || new URLSearchParams(location.search).get('realism') !== '0'

export const surfaceKinds: Record<string, SurfaceKind> = {
  context: 'grass', garden: 'grass', soil: 'gravel',
  plaster: 'stucco', plaster_trim: 'stucco',
  facade_stone: 'stone', boundary_stone: 'stone',
  leaf_a: 'foliage', leaf_b: 'foliage', leaf_c: 'foliage', pine_a: 'foliage', pine_b: 'foliage', pine_c: 'foliage', hedge: 'foliage', foliage: 'foliage', foliage_light: 'foliage',
  road: 'asphalt', path_context: 'gravel', path: 'gravel',
  ridge_far: 'forest', ridge_near: 'forest',
}

const NOISE = /* glsl */ `
float rHash(vec3 p) {
  p = fract(p * 0.3183099 + vec3(0.71, 0.113, 0.419));
  p *= 17.0;
  return fract(p.x * p.y * p.z * (p.x + p.y + p.z));
}
float rNoise(vec3 x) {
  vec3 i = floor(x), f = fract(x);
  f = f * f * (3.0 - 2.0 * f);
  return mix(mix(mix(rHash(i), rHash(i + vec3(1, 0, 0)), f.x), mix(rHash(i + vec3(0, 1, 0)), rHash(i + vec3(1, 1, 0)), f.x), f.y),
             mix(mix(rHash(i + vec3(0, 0, 1)), rHash(i + vec3(1, 0, 1)), f.x), mix(rHash(i + vec3(0, 1, 1)), rHash(i + vec3(1, 1, 1)), f.x), f.y), f.z);
}
// Band-limited noise: an octave contributes only while its feature is larger than ~2 pixels.
float rBand(vec3 p, float freq, float px) {
  float fade = 1.0 - smoothstep(0.22, 0.7, px * freq);
  return (rNoise(p * freq) - 0.5) * fade;
}
float rFbm(vec3 p, float freq, float px) {
  return rBand(p, freq, px) + 0.5 * rBand(p, freq * 2.07, px) + 0.25 * rBand(p, freq * 4.13, px);
}
`

const SNIPPETS: Record<SurfaceKind, { albedo: string; height: string; rough: string }> = {
  grass: {
    albedo: /* glsl */ `
      float clump = rFbm(p, 0.35, px) * 2.0, mid = rFbm(p, 2.2, px) * 1.4, blade = rFbm(p, 26.0, px);
      float stripe = sin(p.x * 2.6 + rFbm(p, 0.2, px) * 6.0) * 0.5 + 0.5;
      vec3 dry = vec3(1.14, 1.04, 0.62), lush = vec3(0.8, 1.12, 0.78);
      c *= mix(dry, lush, clamp(0.5 + clump * 1.1, 0.0, 1.0)) * (1.0 + mid * 0.38 + blade * 0.5) * (0.95 + 0.07 * stripe * step(0.7, n.y));
    `,
    height: 'rFbm(p, 30.0, px) * 1.0 + rFbm(p, 9.0, px) * 0.8',
    rough: '0.96',
  },
  stucco: {
    albedo: /* glsl */ `
      float blotch = rFbm(p, 0.9, px) * 2.0, grain = rFbm(p, 70.0, px);
      float streak = rFbm(p * vec3(7.0, 0.55, 7.0), 1.0, px) * 2.0;
      float grime = mix(0.84, 1.0, smoothstep(0.35, 1.5, p.y)) * (1.0 - 0.08 * smoothstep(0.55, 1.0, 1.0 - n.y) * 0.0);
      c *= (1.0 + blotch * 0.11 + grain * 0.12 - max(streak, 0.0) * 0.12) * grime;
    `,
    height: 'rFbm(p, 90.0, px) * 0.9 + rFbm(p, 24.0, px) * 0.6',
    rough: '0.9',
  },
  stone: {
    albedo: /* glsl */ `
      float mottle = rFbm(p, 5.0, px) * 2.0, fine = rFbm(p, 60.0, px);
      c *= 1.0 + mottle * 0.22 + fine * 0.16;
    `,
    height: 'rFbm(p, 40.0, px) * 1.1 + rFbm(p, 11.0, px) * 0.7',
    rough: '0.93',
  },
  foliage: {
    albedo: /* glsl */ `
      float dapple = rFbm(p, 7.0, px) * 2.0, fine = rFbm(p, 28.0, px);
      float lit = mix(0.8, 1.22, clamp(n.y * 0.5 + 0.5, 0.0, 1.0));
      c *= (1.0 + dapple * 0.34 + fine * 0.28) * lit * vec3(1.04, 1.0, 0.9);
    `,
    height: 'rFbm(p, 20.0, px) * 1.0',
    rough: '0.82',
  },
  asphalt: {
    albedo: 'c *= 1.0 + rFbm(p, 55.0, px) * 0.45 + rFbm(p, 3.0, px) * 0.25;',
    height: 'rFbm(p, 70.0, px) * 1.2',
    rough: '0.9',
  },
  gravel: {
    albedo: 'c *= 1.0 + rFbm(p, 45.0, px) * 0.5 + rFbm(p, 4.0, px) * 0.2;',
    height: 'rFbm(p, 50.0, px) * 1.2 + rFbm(p, 16.0, px) * 0.6',
    rough: '0.95',
  },
  forest: {
    albedo: 'c *= vec3(0.86, 0.98, 0.8) * (0.9 + rFbm(p, 0.045, px) * 0.9 + rFbm(p, 0.35, px) * 0.35);',
    height: '0.0',
    rough: '0.97',
  },
}

// Vertex displacement: world-space noise roughens canopy silhouettes (shadow maps keep the smooth hull).
const DISPLACE: Partial<Record<SurfaceKind, string>> = {
  foliage: `{
    vec3 wp = vRWorld;
    float lump = rNoise(wp * 2.3) * 0.7 + rNoise(wp * 5.1) * 0.3;
    float push = (lump - 0.5) * 0.9;
    transformed += normalize(objectNormal) * push;
    vRWorld = (modelMatrix * vec4(transformed, 1.0)).xyz;
  }`,
}

const patched = new WeakSet<object>()

function patch(material: MeshStandardMaterial, kind: SurfaceKind) {
  if (patched.has(material)) return
  patched.add(material)
  const snippet = SNIPPETS[kind]
  const previous = material.onBeforeCompile
  material.onBeforeCompile = (shader: WebGLProgramParametersWithUniforms, renderer) => {
    previous?.call(material, shader, renderer)
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', `#include <common>\nvarying vec3 vRWorld;\nvarying vec3 vRNormal;\n${NOISE}`)
      .replace('#include <begin_vertex>', `#include <begin_vertex>
        vec4 rWorld = vec4(transformed, 1.0);
        #ifdef USE_INSTANCING
          rWorld = instanceMatrix * rWorld;
        #endif
        vRWorld = (modelMatrix * rWorld).xyz;
        vRNormal = normalize(mat3(modelMatrix) * objectNormal);
        ${DISPLACE[kind] ?? ''}`)
    shader.fragmentShader = shader.fragmentShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vRWorld;\nvarying vec3 vRNormal;')
      .replace('#include <common>', `#include <common>\n${NOISE}`)
      .replace('#include <color_fragment>', `#include <color_fragment>
        {
          vec3 p = vRWorld, n = normalize(vRNormal);
          float px = length(fwidth(p));
          vec3 c = vec3(1.0);
          ${snippet.albedo}
          diffuseColor.rgb *= clamp(c, 0.0, 2.0);
        }`)
      .replace('#include <roughnessmap_fragment>', `#include <roughnessmap_fragment>
        roughnessFactor = max(roughnessFactor, ${snippet.rough});`)
      .replace('#include <normal_fragment_maps>', `#include <normal_fragment_maps>
        {
          vec3 p = vRWorld;
          float px = length(fwidth(p));
          float h = ${snippet.height};
          vec2 dH = vec2(dFdx(h), dFdy(h)) * 0.45;
          vec3 sx = normalize(dFdx(-vViewPosition)), sy = normalize(dFdy(-vViewPosition));
          vec3 r1 = cross(sy, normal), r2 = cross(normal, sx);
          float det = dot(sx, r1) * faceDirection;
          normal = normalize(abs(det) * normal - sign(det) * (dH.x * r1 + dH.y * r2));
        }`)
  }
  material.customProgramCacheKey = () => `realism-${kind}`
  material.needsUpdate = true
}

export function enhanceRealism(root: Object3D) {
  if (!realismEnabled()) return
  root.traverse((node) => {
    if (!(node instanceof Mesh)) return
    const materials = Array.isArray(node.material) ? node.material : [node.material]
    for (const material of materials) {
      const kind = surfaceKinds[material.name]
      if (kind && material instanceof MeshStandardMaterial) patch(material, kind)
    }
  })
}
