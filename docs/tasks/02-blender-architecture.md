# Codex Task M2 — Blender Architectural Shell

Implement M2 only after a candidate floor plan has been reviewed. If no layout has been explicitly approved, use a clearly labeled provisional study model for technical testing only.

## Read first

Read the house specification, reviewed layout data, docs/architecture.md, docs/validation-rules.md and the M0/M1 task files.

## Goal

Generate an editable basement + two-storey architectural shell, accessible roof terrace and representative site geometry from reviewed layout data, not hand-positioned independent cubes.

## Requirements

1. Implement modular bpy helpers for slabs, walls, openings, doors, windows, internal/external stairs/access, basement/ramp, required balconies/covered verandas, roof terrace and representative garden/pool/barrier geometry.
2. Use a consistent world origin, metres for geometry, documented floor elevations and explicit floor-to-floor height.
3. Generate wall segments around openings so that doors and windows are actual gaps in wall geometry, not decals over a solid wall.
4. Keep room boundaries, shared walls and opening positions tied to the layout model. Avoid duplicate overlapping walls at shared room boundaries where feasible.
5. Organize objects into named collections and stable IDs for site, basement, ground, first, roof and rooms/zones. Preserve identity as far as practical in later GLB export.
6. Support floor isolation, roof visibility and cutaway inspection in Blender.
7. Add checks for non-finite coordinates, unintended zero-sized geometry, floor-level alignment, openings that exceed host walls and out-of-envelope objects.
8. Save to a new generated output path. Never overwrite the last known-good .blend if generation fails.
9. Add a background-mode smoke test if the installed Blender version supports the required commands.
10. Keep geometry parametric and reproducible from the JSON specification plus layout data. Do not make manual edits in Blender the only source of truth.
11. Do not replace null brief dimensions with silent defaults. Use reviewed candidate dimensions/flexible-space assignments and preserve budget, site and professional-review warnings.

## Acceptance criteria

- A basement + ground + first + roof/site .blend can be regenerated from source data.
- Wall, slab, opening and floor identities are inspectable and documented.
- Doors, windows and stairs align with the reviewed floor plan.
- Required balconies/verandas, garden access, basement connection, pool/fall boundaries and roof stair access are inspectable; geometry does not establish safety/engineering compliance.
- Geometry diagnostics are emitted and tests pass where feasible.
- Visual polish and furniture placement remain out of scope until M3.

## Report back

Provide exact generation/render commands, output paths, geometry checks and any unresolved layout problems. Do not move to M3 automatically.
