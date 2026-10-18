# Implementation Plan and Acceptance Criteria

The copy-ready Codex prompts live in [tasks/README.md](tasks/README.md). Execute one milestone at a time and review its artifacts before continuing.

## Approved scope and current state

The brief was approved on 17 October 2026; particular layout/dimensions remain unapproved. Latest approval supersedes the compact direction: restore the spacious 7,000 sq ft ground/first pattern, larger gardens and pool, retaining the front-lawn lift/no external link and basement/roof functions with necessary alignment. Local internal-access/suite changes are permitted. See [design decisions](design-decisions.md) and [room schedule](room-schedule.md).

A temporary Blender probe established headless access. [Validation tooling](../scripts/layout.py), [driveway checks](../scripts/driveway.py) and [Blender generation](../blender/create_layout.py) now produce spacious [Study 010](../house-spec/layout-study.json), with saved/reopened model, 113 placements and dimensioned plans. Fifteen scenes include comparisons, plans, close-ups and non-engineered structure. See [README](../README.md); this is not feasibility certification.

Study 002 retains the 70 x 100 ft plot (7,000 sq ft, 40% above the initial upper target) and 2,500 sq ft above-ground plates. The basement increases from 4,000 to 4,400 sq ft excluding ramp, to retain front recreation, clean access, an airlock and rear ramp-side parking. Kitchen/pantry move to the backyard, dining retains eight seats in 162 sq ft, and net L-shaped living grows to 281.75 sq ft. The user approved these directions and permits basement expansion; exact dimensions remain unapproved. Vehicle swept paths, actual exhaust/fire/egress performance, services, cost and local/site/engineering constraints remain unresolved.

Study 003 preserves that work and revises the first floor: all sleeping rooms grow to equal 16 x 17 ft, each has a connected private bathroom/walk-in dressing suite, office swaps with Child 2 and gets an indoor office-only WC (nine toilets total), and balcony privacy screens disappear while perimeter guards remain. The shared rear approach and seamless lounge/gallery are retained without enlarging the plate. Soft dividers/enclosed-shower intent are blockouts, not wet-area or ventilation engineering.

Study 004 supersedes that office/WC arrangement: office front-left, Child 1 front-right, shared first-floor WC and corrected Child 2 entrance, retaining equal private child suites. Basement-only laundry, equal gym/gaming, four-stop lift reserve, relocated prayer/front family WC, larger living/drawing/master closet and large bedroom glazing follow the 18 October user decisions. The new lift/airlock core leaves a 22 ft main aisle; SUV turning needs rechecking. Structural proxies show clear-span intent only; engineering may require internal columns or transfer structure. React room names/sizes now appear while zooming, independently of selected-room dimension lines, and a separate structural mode carries a persistent warning.

Study 005 replaces the front wet core with the sole controlled front-entry gallery and internal drawing/guest doors. A 5 ft House Gallery has a left-end common WC and recessed 6 x 2 ft household cupboard; the guest gets a private 6 x 7.5 ft corner ensuite. Their areas are deducted from drawing/guest, not added. The lift moves to the right perimeter beside a candidate 9 x 17 ft U-stair and 4 ft landing; the basement airlock uses the old shaft position. Master/kitchen/upstairs suites, gardens/balconies and parking/ramp rectangles remain unchanged, as does 312.5 sq ft net living. Gallery access, stair/slab geometry and enclosure wall allowances are tested, not certified for construction.

Study 006 moved the lift into the front lawn but added a covered side link on an 8,856 sq ft site. The user subsequently **rejected the link and plot growth**. Its bundle is preserved for history, not the current accepted direction. It introduced privacy/bedside/side-glazing/weather details, sampled driveway checks and optional GTAO studio lighting.

Study 007 fits **5,000 sq ft**, with **1,944 sq ft main plates + 60 sq ft front shaft only**, internal front-gallery landing access and **no external side link**. Basement is 3,253.5 sq ft. Explicit reductions retain equal 210 sq ft child rooms, equal 229 sq ft recreation, five bedrooms/office, three SUV bays, eight toilets, eight-seat dining and basement laundry. Pool is explicitly deferred. Road-relative levels are -8.5/+1.5/+12.5/+23.5 ft; actual parked-fixture arrival and assumed ramp margins pass. Independent bay operations, accessible arrival, gardens over basement, costs and engineering remain unresolved.

Study 008 supersedes that compact direction at **70 x 100 ft / 7,000 sq ft**. Restore front drawing/guest separated by Entrance Gallery, transverse House Gallery with left WC/right cupboard, and rear master/family spaces. Upstairs restores front office/Child 1, two rear children and transverse lounge; child sleeping rooms return to **272 sq ft**. Larger gardens and an outboard **8 x 16 ft pool** return. A 4 ft internal stair gallery requires local guest/suite/lounge changes, not an exact old-plan copy. Basement remains clean-front/garage-rear, with aligned wider footprint and **16.83 ft rear aisle**; roof keeps solar/gathering/shade/planters. No external link or further plot growth. Pool/barrier separation, actual native/decoded geometry, portable re-export and browser behavior are checked; engineering/safety remain unresolved.

Study 009 refines only ground/first circulation and suites: 4 ft Entrance/House Galleries, an approved 3 ft private master entry, wider guest/master/living, smaller front office to house Child 1's suite, and a unified 634 sq ft net lounge with shared WC beside stairs. No east/west galleries remain. Basement/roof and outdoor functions are preserved; front path realigns with the narrower entry.

Study 010 moves the approved 4 x 2 ft cupboard to the gallery's right terminal end outside living, preserving its 4 ft through-route, and shrinks the stair-side shared WC to 6 x 5.5 ft with repositioned fixtures/clear doorway approach. Living/lounge net areas become 343.5/653 sq ft; the rest of Study 009 is preserved.

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

**Inspection subset implemented:** canonical GLB/metadata/SVG export and a responsive React/TypeScript/Vite/React Three Fiber/Drei website. It provides side-by-side, assembled, separated and focused-floor views, visibility/site toggles, room selection, projected vector dimensions, orbit/top-down cameras, labels, reset, loading/error/retry and plan fallbacks. Local PBR environment lighting, fitted shadows and high-DPI rendering improve close inspection. Identity-safe batching and verified lossless Meshopt reduce delivery overhead. Thirty-three frontend tests check helpers and actual geometry/metadata; 86 Python tests check the layout, plus eight tour tests. L-shaped highlights/net areas exclude enclosed pantry, shaft, ensuite and cupboard footprints. Browser inspection is separate from layout approval.

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
