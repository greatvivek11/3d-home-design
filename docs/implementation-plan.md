# Implementation Plan and Acceptance Criteria

The copy-ready Codex prompts live in [tasks/README.md](tasks/README.md). Execute one milestone at a time and review its artifacts before continuing.

## M0 — Environment and repository foundation ([Codex task](tasks/00-foundation.md))

- Inspect macOS, Blender, Python, Git, Node.js and npm versions before installing anything.
- Document reproducible setup and commands.
- Load/validate the JSON design brief and convert feet to internal metres at the boundary.
- Generate a minimal editable Blender scene and preview render.
- Add tests for schema validation and unit conversion.

**Exit criteria:** clean setup docs, passing tests, a saved .blend, and a preview render or a documented environment blocker.

## M1 — 2D layout solver and review ([Codex task](tasks/01-floorplan-layout.md))

- Confirm site inputs or explicitly leave them unresolved.
- Create explicit room rectangles and coordinate system.
- Generate dimensioned floor-plan previews for both floors.
- Test room overlaps, envelope bounds, wall connectivity, openings, stairs and circulation.
- Produce a readable report with PASS/FAIL/NEEDS REVIEW.

**Exit criteria:** floor-plan study and conflict report are reviewable before detailed 3D work. Do not call it code-compliant.

## M2 — Architectural shell ([Codex task](tasks/02-blender-architecture.md))

- Generate slabs, walls, true openings, windows, doors, stairs, roof and optional balcony.
- Use stable identifiers and named collections for floors and rooms.
- Support hide/isolate operations for floors and walls.

**Exit criteria:** aligned, editable two-floor .blend with geometry checks.

## M3 — Materials, furniture and rendering ([Codex task](tasks/03-visualization-rendering.md))

- Add reusable minimalist materials and furniture/fixture assets.
- Use Eevee for previews and Cycles for final stills.
- Produce exterior, interior and cutaway renders.
- Check furniture clearances and camera composition.

**Exit criteria:** coherent visual render set and reproducible render command.

## M4 — GLB export and web walkthrough ([Codex task](tasks/04-web-walkthrough.md))

- Export a compact GLB with usable object/floor/room identity.
- Add React + TypeScript + Vite + React Three Fiber + Drei frontend.
- Implement model loading, orbit controls, floor visibility, roof visibility, room selection and first-person movement.
- Use separate simplified collision geometry where practical.
- Add loading/error states, reset control, responsive layout and a fallback for devices with weaker graphics.

**Exit criteria:** browser model loads and first-person movement avoids obvious wall penetration and stair traps.

## M5 — GitHub and Vercel publication ([Codex task](tasks/05-deploy-portfolio.md))

- Keep source/spec/docs in Git; avoid committing transient renders and caches.
- Consider Git LFS for large .blend files and assets.
- Deploy the static frontend through Vercel's Git integration.
- Test deployment URL on desktop/mobile and optimize initial GLB load.

**Exit criteria:** reproducible build and public portfolio project page.

## Scope boundary

This is a visualization and design exploration project. Construction documents, structure, code compliance and permits require qualified local professionals.
