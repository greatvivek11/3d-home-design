# POC: 3DCodeVerse-style loop for a more realistic web model

Branch `poc/3dcodeverse-visual-quality`. Goal: see how far the web viewer's visual quality can be pushed without changing the house geometry or the Blender pipeline.

## What 3DCodeVerse is, and what was actually used

[3DCodeVerse](https://github.com/gaoypeng/3dcodeverse) (arXiv 2610.22341) generates 3D scenes as code with an LLM planner and sub-agents. Each round it collects three kinds of feedback: **execution** (build/runtime logs), **measurement** (numeric checks) and **vision** (a rubric-guided VLM judge on multi-view renders). The score is computed in code, **measurements veto visual claims**, and the best-scoring round is kept.

**Not used:** the repository's harness, its LLM planner/fix agents, its VLM judge or its datasets (the datasets are CC-BY-NC-SA, non-commercial; no data was used). No code was copied.

**Adopted:** the feedback-loop pattern only, in [web/scripts/visual-harness.mjs](../../web/scripts/visual-harness.mjs):

| 3DCodeVerse stage | Here |
|---|---|
| Execution | Playwright captures console and page errors; any error caps the round score. It caught a real bug in round 1 (`patch` is a reserved GLSL word). |
| Measurement | Per-view luminance, contrast, clipping, crushing, edge density and colourfulness, plus median and p95 frame time (a slow viewer is penalised). |
| Vision | A weighted rubric file filled by a reviewer. Here the reviewer was me, looking at the captured sheets. **This is not an independent VLM judgement.** |

Nine views are captured per round (five exterior presets, ground plan, living, kitchen, master).

## What changed (visual only)

- [web/src/realism.ts](../../web/src/realism.ts): world-space procedural surface detail patched into the GLB's materials at load time (no UVs, no new textures, no Blender changes). Grass, stucco, stone, foliage, asphalt, gravel and far hills get albedo variation, roughness and micro-normal detail. Octaves fade by screen-space derivatives to avoid shimmer. Foliage vertices are displaced so canopies lose their smooth-balloon silhouette.
- A display-referred finishing pass (mild saturation, S-curve, soft vignette) in the studio post-process.
- Exterior sky, fog, exposure and sun colour retuned for more depth.
- Opt out with `?realism=0` for A/B comparison. The interior viewer geometry and materials are untouched.
- [web/src/realism.test.ts](../../web/src/realism.test.ts) checks that every mapped material exists in the shipped GLBs and that glass, metal and emissive materials are never touched.

## Results

Before/after captures in this folder: [rear](outside-rear-before.png) / [after](outside-rear-after.png), [garden](outside-garden-pool-before.png) / [after](outside-garden-pool-after.png), [front](outside-front-before.png) / [after](outside-front-after.png).

| Round | Change | Measurement score |
|---|---|---|
| r0 | baseline | 0.588 |
| r1 | procedural materials | 0.573 |
| r2 | lighting, atmosphere, grade | 0.563 |
| r3 | foliage displacement | 0.543 |
| r4 | final, with vision rubric | measurement 0.543, vision 0.563 (baseline 0.425), total 0.555 |

Frame time is unchanged (p95 about 9 ms on this Mac).

**The pixel metric disagreed with the images.** It fell every round while the renders clearly improved: surfaces read as materials, the lawn and hills have variation, trees are no longer smooth balloons. The metric rewards raw edge density and fixed luminance bands, and it is penalised by the very softening and colour work that makes the scene look natural. Treat the measurement score as a regression and error detector, not a quality target. The vision score (0.425 to 0.563) is subjective and reviewer-dependent.

## What this POC cannot fix

The remaining realism gap is mostly **geometry and asset quality**, not shading:
- Trees are still low-poly primitives with bare branches and no leaf cards or instanced foliage.
- Walls are flat extrusions with no mouldings, window reveals, frames with depth or roof overhang detail.
- No grass blades, ground-cover meshes, water caustics or real reflections.
- Interiors still use the Blender-baked finishes; nothing here changes them.
- Realism comes with a runtime shader cost on low-end GPUs; measure before shipping widely.

## Next steps worth trying

1. Replace tree primitives with instanced, leaf-card or authored models (Blender side).
2. Add real window reveals, frames with depth and roof detail in `blender/create_layout.py`.
3. Use a real VLM judge (separate from the author of the change) against the same rubric, so the vision score is independent.
4. Extend the same patching to the interior viewer for flooring and wall finishes.
5. Re-render the exterior stills and tour videos once the look is approved; existing videos are unchanged.
