# Technical Architecture

## Guiding principle

Keep the house specification independent of Blender. The user-approved JSON brief is the source of truth for requirements, targets and unresolved inputs, not an approved layout. The Python pipeline validates the brief and candidate, creates the Blender scene and exports web assets.

## Data flow

1. house-spec/house.json version 2 defines the approved five-bedroom program, basement requirements, outdoor/roof uses, comfort goals, budget aspirations and explicit unknowns. There is no approved site rectangle or room-size schedule.
2. Python loads the JSON, validates it and reports unresolved inputs. Convert linear feet to metres once at the geometry boundary; areas explicitly marked sq ft need squared conversion, money remains INR and fractions remain dimensionless. Null dimensions mean unresolved, not zero or a fallback size.
3. Layout logic proposes a labeled illustrative site and furniture-led dimensions, explicit rooms/zones, walls, openings and circulation. Candidate dimensions belong to separate layout data; do not write guesses back as approved brief values or silently reduce required functions.
4. Geometry checks run before 3D generation: envelope bounds, overlaps, host-wall relationships, furniture/equipment clearances and connectivity. Review basement, ground, first, roof and outdoor plans together before architectural modeling.
5. Blender's bpy API generates an editable .blend scene with stable object names and meaningful collections.
6. Blender renders preview images and exports an optimized .glb asset.
7. The [web app](../web/) uses React, TypeScript, Vite, Three.js through React Three Fiber and Drei to load the GLB, select rooms and inspect levels.
8. The static frontend can later be deployed via Vercel from GitHub; no backend is needed. Deployment and integration into another website are deferred.

## Browser inspection implementation

[export_web.py](../blender/export_web.py) requires a generated Blender study and matching candidate snapshot. Five canonical `floor_*` roots contain `architecture_*` groups from `SITE`, `BASEMENT`, `GROUND`, `FIRST` and `ROOF`, plus separate `structure_*` groups from each floor's `STRUCTURE` collection. Text, lights, cameras and presentation instances are excluded. Floor/room/fixture and structural-intent properties survive as glTF extras.

Floor roots use local zero-elevation metres; **site uses road-relative heights**, including driveway and raised rear deck/entry. Blender +Y becomes Three.js -Z. The [manifest](../web/src/generated/house.json), schema 2, supplies physical elevations, actual plates/area, room bounds/net footprints, hashes, stair profiles, driveway/weather metadata and structural review. Study 010 subtracts ensuite from guest, pantry only from living and shaft intersection from gaming; open prayer is shared, not deducted. The 4 x 2 ft cupboard is a separate gallery-end footprint, never a child of living. SVGs reuse the shared generator. Export does not modify the native file.

Study 010 excludes the smaller 6 x 5.5 ft stair-side WC from its parent unified lounge (686 gross, 653 sq ft net). Removed east/west galleries are absent from all room menus, labels and geometry. Child 1's wet/dressing strip sits in the front band reclaimed from office. Master has a closed 3 ft entrance route, then private bedroom/dressing/bath access; ground galleries and retained upper shared routes are 4 ft. Shared inside-door approach geometry checks both child dressing entries and the common WC's fixture-free 3 ft strip.

[Finish generation](../blender/finishes.py) creates deterministic 512px PBR maps, packed natively and embedded in GLB. Physical UV scale distinguishes floors/joinery. Study 010 retains 113 checked furniture placements and eight derived dining-chair footprints. Bed rotations preserve actual solid-wall headboards; ten bedside lamps remain. Floor tiles carry `room_floor`; lift reserves are true upper slab voids, with one display-only parked platform in basement.

Export evaluates modifiers before batching compatible complete extras/finish identities. Room tiles, guards, glazing, partitions, doors, stair treads/landings and structural proxies retain separate roles. Mesh counts and exact file sizes are recorded in the generation result and manifest. The [Node compression step](../web/scripts/optimize-model.mjs) uses lossless Meshopt, not quantization/simplification, and verifies decoded attributes/topology/transforms/extras before publishing the GLB. Hosting-layer HTTP compression remains future work.

The full-height garage barrier intent is cut away in brown. The basement retains clean-front/garage-rear order, a connected barrier chain, two self-closing airlock doors, protected laundry/stores/recreation and front-of-compartment SUV bays. Footprint/core alignment widens the basement to 50 ft and leaves a 16.83 ft deep rear arrival aisle. Shared [driveway geometry](../scripts/driveway.py) integrates eased grades and samples body/overhang sweep against paving, parked fixtures, portal and overhead/underbody assumptions. Independent stalls, fire/airflow, drainage, services and engineering remain unresolved.

Private bath/dressing suites retain full-width soft-divider openings, parked purple curtains and enclosed-shower intent panels. Shared balconies retain deck/guard identities without internal screens. Study 004 swaps office/Child 1, mirrors Child 2's room entry, makes the first-floor WC common and retains suite privacy. Access, dressing aisles and common rear-balcony routes are checked independently of markers. Removing the second master WC gives eight toilets, derived from the brief.

The four 7 x 7 ft lift reserves align beside the stair core. Only shared clean-side landing doors are permitted. No cab/product, pit, roof overrun, structural support, fire protection, accessible manoeuvring or emergency evacuation provision is certified. Geometry generation cuts the upper slabs and preserves the separate stairs.

Study 010 retains the front-lawn shaft ahead of **internal stairs**, with a direct **internal shared-gallery** door on every full-floor landing. No external stair-link room, annex or roof is generated. Shared `stair_profile` defines front/back orientation of the 9 x 17 ft U-stair, 4 ft flights/landings, nine 12 in goings per flight and twenty risers. Front orientation reflects native treads/landings/guards and complete slab openings together. Headroom, fire and accessibility remain unverified.

The 50 x 50 ft ground/first plates restore the transverse House Gallery and upstairs lounge arrangement. Local front-room/suite changes accommodate a 4 ft internal stair gallery without sacrificing guest front glazing. The restored pool is outside the basement and sampled driveway. Rear fill and terrain have real pool/driveway openings; fill excludes basement volume, where a separate deck proxy remains. Pool water/shell/barrier share the raised garden reference. Fill, retaining, pool excavation, deck circulation and loads remain non-engineered.

The sole front door enters a labelled Entrance Gallery; drawing/guest have internal side doors and front windows instead of direct entrances. The wider House Gallery serves the left-end WC and recessed utility cupboard. The latter has separately identified cutaway sliding-front panels and handles inside the wall line, not the passage; hardware/operation and ventilation are unverified. `opening_meets_room` validates the private guest ensuite's interior parent-child connection without allowing a fake parent door at the exterior boundary.

`structural_members` in [layout](../scripts/layout.py) generates **display-only** perimeter/core columns/beams, not engineering sizes. Separate scenes 11-15 and web structural mode carry persistent warnings. Proxy footprints avoid requested living/parking zones; roughly **49.5 ft spans** and all load paths, headroom, foundations, retaining/seismic/soil/garden loads and cost are unproven. An engineer may require internal supports or plan changes.

The viewer clones hierarchies while sharing GPU resources. [Presentation helpers](../web/src/model.ts) apply comparison/physical/focused transforms. Site is available only assembled or focused-ground; focused ground translates road-relative site by **-ground elevation**, while assembled site stays at road zero. The basement-only driveway clone uses **-basement elevation** locally, cancelling its physical transform when assembled. This keeps raised entry/deck and curved ramp aligned without different geometry.

Only displayed floor groups have pointer handlers. A visible surface stops click propagation, and site terrain blocks clicks into rooms beneath it. This prevents hidden floors or underlying rooms from winning a room-selection raycast.

Orthographic perspective/plan views fit visible layers or a room, with mouse/touch orbit and zoom up to 800. Demand-driven DPR 1-2, AgX/sRGB, up to 16x anisotropy and local PMREM lighting remain. Studio mode uses a half-float composer, multisampling, 70%-resolution GTAO and fitted 4096px shadows; balanced mode omits AO and uses 2048px shadows. Small screens use balanced rendering. Shadow targets reallocate on quality changes; transparent glazing avoids opaque shadows. Separate weather collections/mesh flags support the cover toggle.

Floor/room HTML labels and SVG dimension lines use normal DOM overlays, not nested R3F roots. Room anchors use their largest net footprint, avoiding shaft/pantry holes. Collision/viewport culling and explicit projected-size thresholds reveal smaller labels while zooming; selecting a room prioritizes its tag and adds feet/metre dimension lines. Names and inline feet sizes toggle independently. Assembled mode annotates only the uppermost visible floor rather than hidden rooms. Labels are pointer-transparent; no geometry or net area changes. No remote environments, fonts or decoders are fetched.

Loading/error/retry, all-hidden recovery and SVGs expose failures. The 40 frontend tests cover hashes/bundle, GLB/PBR, all 113 fixture vertices, unified lounge/WC net geometry, front-suite placement, restored areas/no link, site bounds/raised entry/deck/pool, labels/dimensions, lift/glazing, structure, treads/landings and ray-tested holes/portals/ramp/terrain. Node inflates PNGs; Chromium verifies real rendering/controls. The lazy viewer is about 289 KB gzip and exceeds Vite's advisory chunk threshold.

The Vite base is relative for future static/subpath hosting. Public assets and the manifest must ship together; Git LFS binaries must be materialized before building/deploying. No Vercel, iframe or microfrontend integration is configured.

## Blender organization

Use collections or stable naming prefixes for site, basement, ground, first, roof, rooms/zones, walls, slabs, doors, windows, stairs, furniture and lighting. The building has two above-ground storeys plus one basement; the accessible roof terrace is not another enclosed storey. Room/floor identity must survive export sufficiently for visibility toggles and navigation. Use metres inside geometry code and convert for presentation only.

Required brief rooms have no approved widths/depths. Office and laundry are required assigned spaces: first-floor office and basement-only laundry, each placed exactly once. Private/shared bathrooms, lift/stairs, balconies, verandas, pool, gardens, ramp and unresolved services remain explicit. Floor LABELS and DIMENSIONS child collections separate annotations from editable geometry.

The roof terrace needs its own inspection layer in addition to removable roof/slab geometry. Keep layer visibility distinct from collision/navigation so hiding an object does not accidentally create unsafe movement or strand the camera.

## Animated cutaway preview

[create_tour.py](../blender/create_tour.py) writes a separate animation under `output/`. Preserved films/current shots depict Study 003, not Study 010; all shots need reframing before a revised film. Three copied scenes use baked 102-frame cameras and quintic easing; reopening checks poses. No source geometry is transformed. Labels/dimensions are hidden only in the presentation copy.

Blender renders 1920 x 1080 PNGs at 24 fps using Cycles with 48 samples, denoising, a fixed seed and persistent render data. Blender also renders transparent title graphics using its built-in font; there are no font downloads. FFmpeg joins the three shots with nine-frame dissolves into exactly 12 seconds/288 frames, adds endpoint fades and encodes a silent H.264/yuv420p fast-start MP4. `ffprobe` verifies the actual output shape/timing, and FFmpeg decodes every frame before atomic publication.

The tour report binds the animation to source model/brief/layout/script hashes and render settings. Resume checks those identities and the prepared `.blend` hash, rejects incomplete/wrong-sized PNGs and skips reusable frames. The source study is never overwritten. The animated `.blend`, PNG frames, contact sheet, MP4 and verification report are local generated artifacts; this does not add a video to the web bundle or deploy anything.

The default renderer is still Cycles. An explicit `--engine EEVEE` selects Blender 5.2's Eevee GPU renderer, with screen-space ray tracing and fast global illumination; `--samples` controls its temporal render samples rather than Cycles path samples. Renderer choice participates in the resume signature, so caches cannot cross renderer/settings boundaries. Each comparison keeps the same geometry, camera animation, resolution and encoding. Reports include first/warmed still-frame timings, per-shot wall times, actual rendered-frame counts and the actual GPU backend; original outputs remain unchanged.

## Requirement and feasibility boundaries

Record approved requirements separately from flexible targets, illustrative assumptions and professional-review items. The brief approval does not approve a floor plan. The complete finished visualization includes first-floor furnishing even if a real build defers it.

Latest approval restores approximately **7,000 sq ft**, the spacious ground/first room pattern, larger gardens and pool. Local internal-access/suite and basement/roof alignment changes are permitted; external links and unapproved plot growth are not. Yard fractions include access, not green area alone. Basement is function-led, not a coverage percentage; independent vehicle use still needs proof. Gardens, raised soil, pool and retaining/excavation require specialist review.

Budget aspirations are metadata, not a cost model. A successful layout/render does not establish affordability, passive thermal performance, basement flood resistance, safe garage air, pool safety, code compliance or structural adequacy. Fuel/LPG, generator/battery equipment and occupied basement separation require appropriate professional review; never assume general basement storage is suitable.

## Rendering vs real-time web

Blender is the authoring source. Use Eevee for quick iteration and Cycles for final still renders. Do not assume Blender lighting/shader settings transfer identically to the browser. For the web, use compatible materials, conservative texture sizes, optimized geometry and a loading state.

## First-person walkthrough

The current browser app implements orbit/plan inspection, not first-person movement. Future walkthrough work belongs in the browser: keyboard/pointer input, collision checks and navigation in addition to the existing room/floor UI. GLB is a model delivery format, not a walkthrough engine. Collision geometry can be simpler than visual geometry. Test internal stairs between basement, ground, first and roof, external garden/basement access, balconies and pool boundaries before enabling walking; walkthrough collision is not a real-world safety certification.

## Initial non-goals

No backend, database, user accounts, generative AI runtime, structural analysis or construction-document production is needed for the initial visualization project.
