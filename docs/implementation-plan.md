# Implementation Plan and Acceptance Criteria

The copy-ready Codex prompts live in [tasks/README.md](tasks/README.md). Execute one milestone at a time and review its artifacts before continuing.

## Approved scope and current state

The requirements brief was approved on 17 October 2026; no layout or dimensions were approved. The complete visualization includes five bedrooms, separate office, three-SUV basement with recreation/storage, front/back gardens, covered verandas, pool, balconies and accessible roof terrace. See [design decisions](design-decisions.md) and [room schedule](room-schedule.md).

A temporary Blender probe established headless access. Reusable [validation/plan tooling](../scripts/layout.py) and the [Blender generator](../blender/create_layout.py) produce revised [Study 003](../house-spec/layout-study.json), with 55 Python tests, a saved/reopened .blend and dimensioned plans. The visual-only refinement adds packed PBR finishes, detailed footprint-contained furniture, ten inspection scenes and nine high-resolution render cameras, without changing the layout/brief bytes. It opens with all four levels side by side; individual, stacked and three close-up scenes remain available. See the [README](../README.md). This remains a concept review artifact, not completion of the final shell/interiors or all feasibility checks.

Study 002 retains the 70 x 100 ft plot (7,000 sq ft, 40% above the initial upper target) and 2,500 sq ft above-ground plates. The basement increases from 4,000 to 4,400 sq ft excluding ramp, to retain front recreation, clean access, an airlock and rear ramp-side parking. Kitchen/pantry move to the backyard, dining retains eight seats in 162 sq ft, and net L-shaped living grows to 281.75 sq ft. The user approved these directions and permits basement expansion; exact dimensions remain unapproved. Vehicle swept paths, actual exhaust/fire/egress performance, services, cost and local/site/engineering constraints remain unresolved.

Study 003 preserves that work and revises the first floor: all sleeping rooms grow to equal 16 x 17 ft, each has a connected private bathroom/walk-in dressing suite, office swaps with Child 2 and gets an indoor office-only WC (nine toilets total), and balcony privacy screens disappear while perimeter guards remain. The shared rear approach and seamless lounge/gallery are retained without enlarging the plate. Soft dividers/enclosed-shower intent are blockouts, not wet-area or ventilation engineering.

## M0 — Environment and repository foundation ([Codex task](tasks/00-foundation.md))

- Inspect macOS, Blender, Python, Git, Node.js and npm versions before installing anything.
- Document reproducible setup and commands.
- Load/validate the JSON design brief and convert feet to internal metres at the boundary.
- Preserve unresolved null dimensions; validate brief readiness separately from geometry readiness rather than defaulting to old starter sizes.
- Generate a minimal editable Blender scene and preview render.
- Add tests for schema validation and unit conversion.

**Exit criteria:** clean setup docs, passing tests, a saved .blend, and a preview render or a documented environment blocker.

## M1 — 2D layout solver and review ([Codex task](tasks/01-floorplan-layout.md))

- Confirm site inputs or explicitly leave them unresolved.
- Propose explicitly labeled site assumptions, furniture-led room sizes and coordinate system.
- Generate dimensioned plans for basement, ground, first, roof and outdoor/access areas together.
- Test room overlaps, envelope bounds, wall connectivity, openings, stairs and circulation.
- Test three-SUV independent access/ramp geometry, full required space program, garden allocation, privacy and furniture/equipment use. Flag professional-review and cost risks.
- Produce a readable report with PASS/FAIL/NEEDS REVIEW.

**Exit criteria:** floor-plan study and conflict report are reviewable before detailed 3D work. Do not call it code-compliant.

## M2 — Architectural shell ([Codex task](tasks/02-blender-architecture.md))

- Generate basement, above-ground shell, slabs, true openings, windows, doors, internal/external access, required balconies/verandas, roof terrace and representative site/pool boundaries.
- Use stable identifiers and named collections for floors and rooms.
- Support hide/isolate operations for floors and walls.

**Exit criteria:** aligned, editable basement + ground + first + roof/site .blend with geometry checks and unresolved professional-review items clearly reported.

## M3 — Materials, furniture and rendering ([Codex task](tasks/03-visualization-rendering.md))

**Concept-level refinement implemented:** deterministic local oak/joinery/stone/textile PBR maps, detailed parametric furnishings/fixtures, clean cutaway trims/framed glazing, shared glass guards and studio lighting. Saved cameras use Cycles/AgX at up to 96 samples and 5200px comparison width. The separate renderer supports CPU or explicitly requested Metal, recording results without modifying the source file. This does not complete a construction-ready shell or photorealistic final exterior.

- Add reusable minimalist materials and furniture/fixture assets.
- Furnish all five bedrooms and office, shared spaces, basement gym/gaming and outdoor/roof seating; do not omit upstairs furnishing based on real-world phasing.
- Use Eevee for previews and Cycles for final stills.
- Produce exterior, interior and cutaway renders.
- Check furniture clearances and camera composition.

**Exit criteria:** coherent visual render set and reproducible render command.

## M4 — GLB export and web walkthrough ([Codex task](tasks/04-web-walkthrough.md))

**Inspection subset implemented:** canonical GLB/metadata/SVG export and a responsive React/TypeScript/Vite/React Three Fiber/Drei website. It provides side-by-side, assembled, separated and focused-floor views, visibility/site toggles, room selection, projected vector dimensions, orbit/top-down cameras, labels, reset, loading/error/retry and plan fallbacks. Local PBR environment lighting, fitted shadows and high-DPI rendering improve close inspection. Identity-safe batching and verified lossless Meshopt reduce delivery overhead. Twenty-three frontend tests check helpers and actual geometry/metadata; 55 Python tests check the layout. L-shaped highlights/net areas exclude the pantry. Browser inspection is separate from layout approval.

**Still pending:** first-person movement, collision geometry and the navigation acceptance tests below. The inspection website does not complete all of M4. Vercel and integration into the user's existing website are explicitly deferred.

- Export a compact GLB with usable object/floor/room identity.
- Add React + TypeScript + Vite + React Three Fiber + Drei frontend.
- Implement model loading, orbit controls, site/basement/ground/first/roof visibility, room selection and first-person movement.
- Use separate simplified collision geometry where practical.
- Add loading/error states, reset control, responsive layout and a fallback for devices with weaker graphics.

**Exit criteria:** browser model loads; basement-to-roof and garden navigation avoids obvious wall penetration, falls through modeled boundaries and stair traps. UI distinguishes visualization from approved construction/cost documentation.

## M5 — GitHub and Vercel publication ([Codex task](tasks/05-deploy-portfolio.md))

- Keep source/spec/docs in Git; avoid committing transient renders and caches.
- Consider Git LFS for large .blend files and assets.
- Deploy the static frontend through Vercel's Git integration.
- Test deployment URL on desktop/mobile and optimize initial GLB load.

**Exit criteria:** reproducible build and public portfolio project page.

## Scope boundary

This is a visualization and design exploration project. Construction documents, structure, code compliance and permits require qualified local professionals.
