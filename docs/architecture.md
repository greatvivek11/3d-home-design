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

[export_web.py](../blender/export_web.py) requires a generated Blender study and its matching candidate snapshot. It exports only meshes from `SITE`, `BASEMENT`, `GROUND`, `FIRST` and `ROOF`, under five canonical `floor_*` roots. Text, lights, cameras and side-by-side/stacked collection instances are excluded. Custom floor/room/fixture properties survive as glTF extras.

All exported floor geometry is in local zero-elevation metre coordinates. Blender's positive Y becomes Three.js negative Z. The generated [manifest](../web/src/generated/house.json), schema version 2, supplies floor elevations, room outer bounds, usable areas, rectangular footprint parts, unresolved review notes, mesh counts and a GLB-hash revision. Enclosed nested rooms are subtracted from parent areas/tiles/highlights; shared open prayer space is not. Dimensioned SVGs reuse the existing plan generator. Exports do not change the source `.blend`.

The visual-only refinement retains the exact Study 003 layout/brief bytes. [Finish generation](../blender/finishes.py) creates deterministic 512px color, normal and roughness maps, packed into the editable file and embedded in GLB. UVs use physical feet-based scale; oak floorboards and continuous-grain joinery are separate finishes. Furniture details stay within the original 99 source rectangles, plus the established dining-chair footprints. Floor surfaces carry `role: room_floor` for independent geometric checks.

Export evaluates modifiers before joining compatible geometry by complete extras and finish. Room tiles, guard-role objects, partitions, closing doors and shower/soft-divider panels retain their separate identities. This reduces 3,508 editable meshes (including presentation stages) to 522 canonical web meshes. The [Node compression step](../web/scripts/optimize-model.mjs) uses lossless Meshopt, not quantization or simplification, and verifies a decoded fingerprint of attributes/topology/transforms/extras before publishing. The approximately 20.6 MB GLB trades a larger payload for editable high-detail source fidelity; hosting-layer HTTP compression remains future work.

Study 002 adds a proposed full-height basement garage partition rendered as a brown cutaway wall and three indicative closing-door panels (two at the airlock, one at the garage-only plant reserve). Their design-intent metadata survives GLB export. The adjacency validator respects explicit partitions, verifies door spans against named rooms and checks clean-side reachability without traversing the garage/airlock. It cannot establish ventilation, leakage, fire resistance, safe exhaust discharge or egress compliance.

Study 003 retains those layers and revises the first floor. Bathroom/dressing links use full-width `soft_divider` openings with purple parked curtain panels; enclosed shower intent uses cutaway panels with an identified entry side. Their custom metadata survives export. Shared balcony decks and perimeter guards have explicit role/identity extras; hard-coded internal balcony privacy screens are removed. Suite topology, office-only WC access, dressing-aisle rectangles and the common rear-balcony route are checked independently of the rendered markers. Toilet count is derived from the revised brief (nine).

The viewer clones object hierarchies once per floor while sharing geometry/materials with the loaded asset. [Presentation helpers](../web/src/model.ts) apply side-by-side, assembled, vertically separated or focused-floor transforms; they do not regenerate a different house. Site terrain is available only in assembled and ground-floor views. Metadata drives room selection and dimension display; no candidate dimensions become approved requirements.

Only displayed floor groups have pointer handlers. A visible surface stops click propagation, and site terrain blocks clicks into rooms beneath it. This prevents hidden floors or underlying rooms from winning a room-selection raycast.

An orthographic camera supports oblique inspection and top-down plans, fitting visible layers or a selected room. Orbit controls support mouse/touch, close inspection up to zoom 800 and reset. Rendering is demand-driven at DPR 1-2 with AgX/sRGB output, up to 8x anisotropic filtering and a locally generated PMREM studio environment. A 2048px directional shadow map fits the current orbit target/zoom, updates on view/visibility changes and is reused between otherwise static frames. Transparent guards/glazing do not cast opaque rectangular shadows.

HTML floor labels and SVG dimension lines are projected into normal React DOM overlays, not nested roots inside the 3D renderer. Dimensions annotate existing floor-plate or selected-room outer bounds in feet/metres; they never modify geometry or substitute a bounding rectangle for net L-shaped area. No remote environments, fonts or decoders are fetched.

Loading and error/retry states, explicit WebGL guidance, all-hidden recovery and separately accessible SVGs keep failures visible. The 23 frontend tests cover immutable source hashes, binary/header/hash, canonical layers, PBR images, all room-floor footprints and every vertex of the 99 source furniture placements, plus safety-intent identities and plan files. Node validates/inflates embedded PNGs for geometry parsing; Chromium separately verifies real texture rendering and projected dimensions. The lazy-loaded viewer is about 278 KB gzip and still exceeds Vite's advisory chunk threshold.

The Vite base is relative for future static/subpath hosting. Public assets and the manifest must ship together; Git LFS binaries must be materialized before building/deploying. No Vercel, iframe or microfrontend integration is configured.

## Blender organization

Use collections or stable naming prefixes for site, basement, ground, first, roof, rooms/zones, walls, slabs, doors, windows, stairs, furniture and lighting. The building has two above-ground storeys plus one basement; the accessible roof terrace is not another enclosed storey. Room/floor identity must survive export sufficiently for visibility toggles and navigation. Use metres inside geometry code and convert for presentation only.

Required rooms in the JSON have no invented widths/depths. Office and laundry are required flexible spaces with an unresolved floor assignment; candidates must place each exactly once on an allowed floor. Private and shared bathrooms, balconies, verandas, pool, gardens, ramp and service zones must be represented, not hidden inside a bedroom count.

The roof terrace needs its own inspection layer in addition to removable roof/slab geometry. Keep layer visibility distinct from collision/navigation so hiding an object does not accidentally create unsafe movement or strand the camera.

## Animated cutaway preview

[create_tour.py](../blender/create_tour.py) reads the saved refined study and writes a separate animation under `output/`. Three copied scenes reference the existing geometry, with independent cameras and camera data. Each camera has a baked 102-frame orbit/push-in with quintic easing. Copied scenes receive persistent users so Blender does not discard them during saving; the file is reopened and actual camera positions/scales are checked before rendering. No architecture or furniture is transformed. Room labels/dimensions are hidden only in the presentation copy.

Blender renders 1920 x 1080 PNGs at 24 fps using Cycles with 48 samples, denoising, a fixed seed and persistent render data. Blender also renders transparent title graphics using its built-in font; there are no font downloads. FFmpeg joins the three shots with nine-frame dissolves into exactly 12 seconds/288 frames, adds endpoint fades and encodes a silent H.264/yuv420p fast-start MP4. `ffprobe` verifies the actual output shape/timing, and FFmpeg decodes every frame before atomic publication.

The tour report binds the animation to source model/brief/layout/script hashes and render settings. Resume checks those identities and the prepared `.blend` hash, rejects incomplete/wrong-sized PNGs and skips reusable frames. The source study is never overwritten. The animated `.blend`, PNG frames, contact sheet, MP4 and verification report are local generated artifacts; this does not add a video to the web bundle or deploy anything.

## Requirement and feasibility boundaries

Record approved requirements separately from flexible targets, illustrative assumptions and professional-review items. The brief approval does not approve a floor plan. The complete finished visualization includes first-floor furnishing even if a real build defers it.

The initial plot area is flexible upward; front/back yard fractions include associated access, not just green area. Basement size must be derived from independently accessible three-SUV parking, two motorbikes, scooter, bicycles, gym/recreation, storage and circulation, not a fixed percentage. Do not infer garden tree viability above a basement without soil/load/drainage review.

Budget aspirations are metadata, not a cost model. A successful layout/render does not establish affordability, passive thermal performance, basement flood resistance, safe garage air, pool safety, code compliance or structural adequacy. Fuel/LPG, generator/battery equipment and occupied basement separation require appropriate professional review; never assume general basement storage is suitable.

## Rendering vs real-time web

Blender is the authoring source. Use Eevee for quick iteration and Cycles for final still renders. Do not assume Blender lighting/shader settings transfer identically to the browser. For the web, use compatible materials, conservative texture sizes, optimized geometry and a loading state.

## First-person walkthrough

The current browser app implements orbit/plan inspection, not first-person movement. Future walkthrough work belongs in the browser: keyboard/pointer input, collision checks and navigation in addition to the existing room/floor UI. GLB is a model delivery format, not a walkthrough engine. Collision geometry can be simpler than visual geometry. Test internal stairs between basement, ground, first and roof, external garden/basement access, balconies and pool boundaries before enabling walking; walkthrough collision is not a real-world safety certification.

## Initial non-goals

No backend, database, user accounts, generative AI runtime, structural analysis or construction-document production is needed for the initial visualization project.
