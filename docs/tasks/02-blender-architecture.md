# Codex Task M2 — Blender Architectural Shell

Implement M2 only after a candidate floor plan has been reviewed. If no layout has been explicitly approved, use a clearly labeled provisional study model for technical testing only.

## Read first

Read the house specification, reviewed layout data, docs/architecture.md, docs/validation-rules.md and the M0/M1 task files.

## Goal

Generate an editable two-storey architectural shell with geometry derived from the layout data, not hand-positioned independent cubes.

## Requirements

1. Implement modular bpy helpers for slabs, walls, openings, doors, windows, stairs, roof and optional balcony.
2. Use a consistent world origin, metres for geometry, documented floor elevations and explicit floor-to-floor height.
3. Generate wall segments around openings so that doors and windows are actual gaps in wall geometry, not decals over a solid wall.
4. Keep room boundaries, shared walls and opening positions tied to the layout model. Avoid duplicate overlapping walls at shared room boundaries where feasible.
5. Organize objects into named collections and stable names/IDs, including floor and room identity. This identity should be preserved as far as practical in the later GLB export.
6. Support floor isolation, roof visibility and cutaway inspection in Blender.
7. Add checks for non-finite coordinates, unintended zero-sized geometry, floor-level alignment, openings that exceed host walls and out-of-envelope objects.
8. Save to a new generated output path. Never overwrite the last known-good .blend if generation fails.
9. Add a background-mode smoke test if the installed Blender version supports the required commands.
10. Keep geometry parametric and reproducible from the JSON specification plus layout data. Do not make manual edits in Blender the only source of truth.

## Acceptance criteria

- A two-storey .blend can be regenerated from source data.
- Wall, slab, opening and floor identities are inspectable and documented.
- Doors, windows and stairs align with the reviewed floor plan.
- Geometry diagnostics are emitted and tests pass where feasible.
- Visual polish and furniture placement remain out of scope until M3.

## Report back

Provide exact generation/render commands, output paths, geometry checks and any unresolved layout problems. Do not move to M3 automatically.
