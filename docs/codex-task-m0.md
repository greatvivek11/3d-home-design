# Codex Task M0 — Project Foundation

Implement M0 and the initial portion of M1 for this Dream Home project.

## Context

Read house-spec/house.json and the project documentation first. The concept is a two-storey modern minimalist independent home on a provisional 30 ft × 50 ft plot, with one-car parking and an initial four-bedroom family-home target. Plot dimensions and room targets are unconfirmed. Setbacks, orientation, road width and jurisdiction remain unresolved.

## Requirements

1. Inspect macOS and installed development tools before changing the environment.
2. Create a modular Python/Blender project structure.
3. Validate the JSON specification, report missing/unresolved fields, and add unit tests.
4. Convert input dimensions from feet to internal metres exactly once at the configuration boundary. Keep unit metadata explicit.
5. Keep all room sizes and site inputs provisional. Do not invent a legal buildable envelope.
6. Define a minimal sample arrangement with explicit provisional room rectangles only for visualization/testing; label it as unapproved.
7. Generate dimensioned 2D floor-plan previews before detailed 3D geometry.
8. Detect invalid dimensions, overlaps, out-of-envelope geometry, openings that do not fit host walls and obvious circulation/stair connectivity issues where feasible.
9. Save a minimal editable .blend scene and a preview render.
10. Add Git ignore rules for Python caches, Blender backup files, local virtual environments and temporary render output.
11. Document exact setup, test, generate, render and export commands.
12. Preserve compatibility with future GLB export and a React Three Fiber viewer through stable object names and floor/room grouping.

## Acceptance criteria

- A fresh checkout has documented setup steps.
- Valid input passes tests; invalid geometry produces actionable diagnostics.
- The 2D preview labels rooms and target dimensions.
- Blender generates and saves a scene without manual UI steps where practical.
- The report distinguishes PASS, FAIL and NEEDS REVIEW.
- No web frontend or unnecessary backend is introduced yet.
- No structural or regulatory compliance is claimed.

Start with a short plan, then implement the smallest working version, run the available tests and report generated artifacts and remaining limitations. Do not overwrite the last known-good output if a generation fails.
