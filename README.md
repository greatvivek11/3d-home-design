# Dream Home - Blender + Python

A code-driven visualization of a private, nature-connected family retreat: basement, ground floor, first floor and accessible roof terrace. Blender/Python is the editable authoring pipeline; a React/Three.js website provides interactive inspection of the same geometry.

## Current status

**User-approved design brief and visually refined Study 003, 17 October 2026.** The user approved rear parking/front recreation and the garden kitchen/larger living direction, then larger equal children's rooms, private interconnected bath/dressing suites, an office swap with private indoor WC and seamless shared balconies. The resulting floor plan, dimensions and site remain proposals. The latest pass improves presentation only: the layout and brief are byte-for-byte unchanged. The editable cutaway model has detailed parametric furniture, 20 packed finish maps, ten inspection scenes, dimensioned plans and nine render cameras. This is not construction documentation, a cost estimate or evidence of code compliance.

Blender 5.2.2 LTS is accessible on macOS through `/Applications/Blender.app/Contents/MacOS/Blender`. The saved study uses portable Cycles CPU settings and is reopened after saving; the separate render utility also supports this Mac's Metal GPU. The browser loads the matching GLB; its current size is displayed in the website footer. This is an inspection viewer, not a collision-aware first-person walkthrough.

### Visual refinement, not a layout revision

- Physical-scale oak flooring, separate continuous-grain joinery, walnut, limestone, concrete and woven sage/linen finishes. Maps are generated locally and packed into Blender and GLB; no downloaded models, texture services or HDR files are needed.
- Rounded upholstery, layered beds and pillows, real table/chair legs, cabinet fronts and shelving, workstation keys/screen, piano keys, hollow basins/toilets/tub, fittings, kitchen appliances, vehicles, gym equipment and solar cells.
- Clean wall caps/skirting and framed glazing; shared balconies retain their original uninterrupted decks and perimeter guards.
- Cycles/AgX studio presentation in Blender; local environment lighting, fitted soft shadows, anisotropic texture filtering and up to 2x pixel ratio on the web.
- Geometry checks retain all 99 source furniture placements, including the eight dining-chair footprints. Source hashes and every exported room footprint are regression-tested. No rooms, openings, stairs, balconies or site dimensions moved.

## Explore in the browser

### Checked-in assets and Git LFS

Install Git LFS, then run `git lfs install` and `git lfs pull` after cloning. The required binary assets are versioned with LFS:

- [Editable refined Blender study](assets/models/study-003/dream-home-study.blend), with its packed finishes, [layout snapshot](assets/models/study-003/layout-snapshot.json) and [portable generation metadata](assets/models/study-003/generation-result.json).
- [Editable animated Blender tour](assets/models/study-003/dream-home-tour.blend), including the three animated camera scenes.
- [Browser GLB](web/public/models/house.glb), with embedded finishes; matching metadata and SVG plans are committed alongside the app.

The Blender assets are copies of the validated local deliverables, not replacements for them. All screenshots, rendered images, MP4s, intermediate frames and render logs remain local/ignored. Links under `output/` below refer to those local previews, not files included in a clone. Use the checked-in study for rendering/exporting without first regenerating it; use a new output directory when generating new artifacts.

Use Node.js 22.12+ and npm. From the repository root:

```bash
npm --prefix web ci
npm --prefix web run dev
```

Open **http://localhost:5173/** (or the URL Vite prints if that port is busy). Blender does not need to be running: the website uses the included [GLB](web/public/models/house.glb), [metadata](web/src/generated/house.json) and [dimensioned SVG plans](web/public/plans/).

- **Side by side** compares all four levels; narrow canvases use a two-by-two arrangement.
- **Assembled** uses proposed physical floor elevations; hide upper floors to see below them.
- **Separated** adds vertical space between levels.
- Click a floor name to focus it, or use the eye controls to hide/show floors.
- Select a room from the menu or click its floor/furniture for proposed dimensions and a closer view. Stair zones remain available through the menu.
- Toggle **3D view / Floor plan**, **Labels**, **Dimensions**, and **Reset view**. Dimension lines show the floor plate, or the selected room's outer extents, in feet and metres; net area remains separate. Drag to orbit, scroll to zoom, right-drag to pan; touch uses one finger to orbit and two fingers to pan/zoom.
- **Garden & site** is available in assembled and ground-floor views. Other views omit terrain so it cannot conceal their plan sheets.
- The room section links to dimensioned plans, also usable if the model cannot load. **Concept 003** explains the study's limitations.
- Living is L-shaped: its card shows outer extents separately from usable area, excluding the enclosed pantry; the selection overlay follows that actual footprint.

The interface is responsive and uses local assets/system fonts, with loading, explicit failure/retry, and all-hidden recovery states. First-person movement, hosting on Vercel and iframe/microfrontend integration are deferred.

### Build and test the website

```bash
npm --prefix web run typecheck
npm --prefix web run lint
npm --prefix web test
npm --prefix web run build
npm --prefix web run preview
```

Serve the generated [web/dist/](web/dist/) through HTTP, not by opening its HTML as a local file. Vite uses relative asset paths for future static/subpath hosting. The lazy-loaded Three.js viewer chunk is about 1 MB uncompressed (275 KB gzip), triggering Vite's advisory 500 KB chunk warning; the GLB is a separate download.

The 23 frontend tests cover presentation/visibility rules, dimension lines/units, immutable source hashes, every exported room footprint and all 99 furniture placements, embedded PBR PNGs, private-suite metadata, guards/dividers/shower enclosures, lossless Meshopt delivery and all five plan assets. Node geometry tests validate/inflate the embedded PNGs; real texture rendering is exercised in Chromium. Browser checks additionally cover high-DPI close-ups, room picking, controls and mobile overflow.

### Regenerate browser assets after changing the house

First regenerate the Blender study from the candidate using the commands below, then export that saved file. Run `npm --prefix web ci` first: export uses the local Node compression helper.

```bash
/Applications/Blender.app/Contents/MacOS/Blender \
  --background --factory-startup --python-exit-code 1 \
  --python blender/export_web.py -- \
  --blend assets/models/study-003/dream-home-study.blend
```

Replace the example path with the newly generated study when applicable. The exporter requires its matching layout snapshot; it refuses a stale/mismatched study. It evaluates bevels/normals, batches only compatible same-finish/identity pieces and preserves individually identified safety-intent panels and room tiles. Presentation stages, dimensions, text, cameras, lights and collection instances stay out of the GLB.

The [local compression helper](web/scripts/optimize-model.mjs) applies Meshopt without quantization, filters or simplification, then decodes and fingerprints the result to verify exact attributes, triangle topology, transforms and picking identities. Export writes the matching GLB, manifest/hash/source fingerprint and SVGs without overwriting Blender. The detailed model is approximately **20.6 MB**, reduced from 30.1 MB; it is deliberately larger than the old blockout. HTTP gzip/Brotli can reduce transfer further when hosting is configured; deployment compression is not configured yet.

Unlike local `output/`, the public browser model/plans and generated metadata are deliberate versioned deliverables. The repository assigns GLB files to Git LFS: a fresh checkout or future hosting build must fetch the actual binary, not an LFS pointer. The asset tests detect missing/pointer/mismatched GLBs. Deployment configuration is not included yet.

## Open the latest study

Current local artifacts are in [output/study-003-refined/](output/study-003-refined/). Previous [Study 003 blockout](output/study-003-upstairs/), [Study 002](output/study-002-revised/) and [Study 001](output/study-001-side-by-side/) are preserved.

- [Editable Blender file - opens with all four levels side by side](output/study-003-refined/dream-home-study.blend)
- [All four levels together](output/study-003-refined/all-floors.png) - labeled 5200 x 2400 overview
- [Garden/ground overview](output/study-003-refined/overview.png)
- [Ground](output/study-003-refined/ground.png), [basement](output/study-003-refined/basement.png), [first floor](output/study-003-refined/first.png) and [roof](output/study-003-refined/roof.png) previews
- Close-ups: [living/kitchen](output/study-003-refined/living-detail.png), [office](output/study-003-refined/office-detail.png), [bedroom/suite](output/study-003-refined/bedroom-detail.png)
- Web evidence: [before/after comparison](output/study-003-refined/quality-comparison.png), [deep-zoom detail](output/study-003-refined/web-keyboard-detail.png) and [mobile floor plan](output/study-003-refined/web-mobile.png)
- Dimensioned [site](output/study-003-refined/site.svg), [ground](output/study-003-refined/ground.svg), [basement](output/study-003-refined/basement.svg), [first](output/study-003-refined/first.svg) and [roof](output/study-003-refined/roof.svg) plans
- [Checks and review limitations](output/study-003-refined/review-report.json), plus brief/layout snapshots and [generation/render settings](output/study-003-refined/generation-result.json)

The file opens in `07 - All four plans side by side`, with headings for basement, ground, first and roof. Scroll to zoom, middle-mouse to orbit, Shift + middle-mouse to pan, and Numpad 0 to toggle camera view (or use View > Cameras > Active Camera).

Use the **scene selector at the top-right of Blender's main window**, not the Outliner collection list, to switch scenes: `01` garden/ground overview, `02` ground, `03` basement, `04` first, `05` roof, `06` physical stack, `07` side-by-side plans, or `08`-`10` living/office/bedroom close-ups. The presentations reference the original floor collections; switch to an individual floor scene to edit its rooms. The file opens in Material Preview; use the saved Cycles cameras for finished stills. Toggle each floor's **DIMENSIONS** child collection in the Outliner to hide its vector annotations.

The internal `START HERE - Study notes` text explains the study. Walls remain intentionally cut to 3 ft; furnishings are detailed parametric concept assets, not manufacturer/construction specifications. Per-floor plans use local zero elevation; the physical stack uses the unchanged proposed elevations -10, 0, 11 and 22 ft.

### Animated video preview

- [12-second MP4](output/study-003-tour-preview/dream-home-preview.mp4) - 1920 x 1080, 24 fps, H.264/yuv420p with fast-start playback; silent, suitable for sharing.
- [Animated Blender copy](output/study-003-tour-preview/dream-home-tour.blend) - select `TOUR 01-overview`, `TOUR 02-living` or `TOUR 03-suite` and play frames 1-102.
- [Framing contact sheet](output/study-003-tour-preview/preview-contact-sheet.png), [render/verification report](output/study-003-tour-preview/tour-result.json) and [native Mac playback check](output/study-003-tour-preview/native-video-verification.json).

The preview uses real camera orbits and gentle push-ins, not a slideshow: all-floor overview, ground-floor living/garden kitchen, then one child's bedroom/dressing/bath suite. Nine-frame dissolves join three 102-frame shots into exactly 288 output frames. Room labels and dimension overlays are hidden for the film; the architecture, furniture placements, source study and layout/brief remain unchanged. No music or narration is included in this style preview.

Open the MP4 in QuickTime or another H.264-capable player and send the file directly to family. The preview is approximately 3.3 MB. Native macOS checks verify real playback, seeking and all 288 decoded frames. It is a local deliverable, not an added route on the React website.

The [tour utility](blender/create_tour.py) uses Blender for animation/rendering and the locally installed `ffmpeg`/`ffprobe` for titles, transitions, H.264 encoding and full-file decode verification. No DaVinci Resolve, remote assets or additional Python packages are required. To reproduce, first render representative frames into a **new** output directory:

```bash
/Applications/Blender.app/Contents/MacOS/Blender \
  --background --factory-startup --python-exit-code 1 \
  --python blender/create_tour.py -- \
  --blend assets/models/study-003/dream-home-study.blend \
  --output output/a-new-tour --device METAL --stills
```

Review its contact sheet, then repeat the command replacing `--stills` with `--resume` to render all frames and encode the MP4. Omit both flags to create a complete preview in one pass. `--device CPU` is available without Metal; `--samples` defaults to 48 and must stay the same when resuming. Rendering animation is significantly more expensive than a still image.

The utility refuses mismatched source hashes, edited prepared animations or changed script/settings on resume. It checks actual camera poses after reopening the animation, reuses only complete correctly sized PNG frames, verifies codec/resolution/fps/duration/frame count and decodes the entire MP4 before publishing it. Source and generated-animation hashes are recorded. PNG frames are retained for resuming/re-encoding; all tour outputs remain local under ignored `output/`.

### Important proposal, not a new approved requirement

Study 003 retains **70 x 100 ft = 7,000 sq ft**, 40% above the initial 5,000 sq ft upper target. The 50 x 50 ft above-ground footprint, ramp and front/back bands remain unchanged. This is one generous candidate, not proof of a minimum or optimal plot.

The proposed basement is now **50 x 88 ft = 4,400 sq ft**, excluding ramp: 400 sq ft / 10% more than Study 001, extended 8 ft toward the front. This retains the 16 x 15 ft gym, 32.5 x 15 ft gaming room, aligned stairs, three SUV bays and 25.5 ft manoeuvring aisle while adding protected access and an airlock. It extends under more of the front yard; soil, waterproofing, structure, setbacks and cost require review. The two above-ground plates remain 2,500 sq ft each: approximately 9,400 sq ft total before detailed deductions, ramp and balconies. This is not evidence that the brief fits INR 50-70 lakh.

**Basement zoning:** front gym/gaming; clean-side storage, WC and stair circulation; a two-door garage airlock; rear parking and motorbike/scooter storage by the ramp landing. The brown barrier represents intended full-height sealed construction, shown at the same 3-ft cutaway height as the study walls. Green door panels indicate self-closing intent. Independent garage exhaust/makeup air, pressure control, clean-area ventilation, monitoring and fire/egress design are not engineered or certified. Garage plant reserve has access only from the garage and does not approve fuel/LPG/battery placement.

**Family spaces:** backyard kitchen 12 x 14 ft with a 6 x 3 ft island, indicative hob/hood and sink window; directly adjacent 5 x 6 ft pantry. Dining reduces from 201.5 to 162 sq ft, retaining an eight-seat 4 x 7.5 ft table with at least 3 ft nominal table-edge clearance within its zone. Living is L-shaped: 14.5 x 21.5 ft outer extents minus the 30 sq ft pantry = **281.75 sq ft**, up from 209.25 sq ft (about **35% larger**). The shared prayer alcove is not subtracted as an enclosed room. The garden slider remains accessible.

Kitchen windows do not replace ducted source extraction. **Neither kitchen nor garage exhaust outlets are located yet:** they must avoid the rear play lawn, pool/veranda, windows, neighbours and fresh-air intakes. No duct sizes, airflow rates or safety performance are established.

**First-floor revision:** office moves to the former front Child 2 location; Child 2 moves beside Child 3 at the rear. All three sleeping rooms grow equally from 256 to **272 sq ft (16 x 17 ft, +6.25%)**, without enlarging the plate. Each has bedroom -> private walk-in dressing <-> shower bathroom access. Child 1 has a 6.5 x 8 ft dressing room and 6.5 x 8.5 ft bath; each rear child has a 5.5 x 7 ft dressing room and 5.5 x 9.5 ft bath. Sleeping sizes are equal, not all suite components. Single-sided wardrobes leave at least 3.5 ft clear width.

The 16 x 16 ft front office retains its workstation, shared table, bookshelf and piano; a private **8 x 5 ft indoor WC** opens only from it, increasing the total to **nine toilets**. The **49 x 9.5 ft seamless lounge/gallery** includes common movement, not only seating. A 4 ft central path between the rear suites preserves shared rear-balcony access without entering a bedroom.

Front and rear balconies are each uninterrupted shared decks; internal privacy screens are removed, outer guards retained. The front is entered from Child 1 or office; the rear also has lounge access. They are not joined as a wraparound balcony. Purple parked curtains represent soft bathroom/dressing dividers. Enclosed shower intent is modeled; extraction, moisture protection, waterproofing, plumbing and privacy still require design.

Laundry stays downstairs; master bedroom and pool are unchanged. All dimensions are **proposed**, not approved. Vehicle swept paths, actual operating/accessible clearances, acoustics, services, structure, drainage, pool safety and regulations remain under review. Fishpond and double-height atrium are deferred.

## Reproduce and validate

No system Python packages need installing. Layout tests use the standard library; finish generation uses NumPy bundled with Blender. Run from the repository root:

```bash
python3 -m unittest discover -s tests -v
python3 scripts/layout.py
/Applications/Blender.app/Contents/MacOS/Blender \
  --background --factory-startup --python-exit-code 1 \
  --python blender/create_layout.py
```

The Blender command creates a new timestamped directory under `output/`, writes plans/reports/snapshots, renders nine Cycles/AgX stills at up to 96 samples and saves/reopens the `.blend`. Standard plans/overview are 2400 x 2600, comparison 5200 x 2400, living detail 2400 x 1800, and office/bedroom details 2400 x 2100. The opening scene, four floor instances and all 99 furniture footprints are checked. Use `-- --output output/a-new-study-directory` for an explicit path, adding `--skip-render` for model/plan-only generation. Existing directories are refused.

To render saved cameras separately, without changing the editable file:

```bash
/Applications/Blender.app/Contents/MacOS/Blender \
  --background --python-exit-code 1 --python blender/render_study.py -- \
  --blend assets/models/study-003/dream-home-study.blend --device METAL
```

Use `--device CPU` on other systems. Optional `--scenes office-detail living-detail`, `--samples 32` and `--resolution 1440` support focused previews. Missing requested GPU support fails explicitly rather than silently switching devices. Render settings/results are recorded alongside the study.

For plans/reports without Blender:

```bash
python3 scripts/layout.py --output output/a-new-plan-directory
```

`FAIL` produces a nonzero exit status. `NEEDS REVIEW` is the expected successful result for an unapproved concept. The 55 standard-library tests cover geometry/program checks, actual opening connections, clean-route/airlock topology, partition intent, eight dining chairs, net living area, equal bedroom enlargement, private interconnected bath/dressing suites, clear dressing aisles, enclosed shower intent, office-only WC access and the shared rear-balcony route.

Five additional tour tests cover the exact dissolve timeline, moving camera paths, orbit radius/height, easing and invalid frame ranges. Blender round-trip pose checks and full MP4 probing/decoding complement those pure-Python tests.

Generated output is Git-ignored and local, not included in a fresh checkout. Regenerate it using these commands. Edit [layout-study.json](house-spec/layout-study.json) for candidate placement/dimensions; do not write proposals into the approved brief as confirmed facts.

## Approved direction

- Quiet, cooler, nature-connected setting near mountains, potentially around Dehradun; no plot purchased.
- Initial plot search target: 4,000-5,000 sq ft, flexible upward. The 500 sq yd reference equals 4,500 sq ft; exact width/depth are unknown.
- Roughly 20% front yard and 30% backyard, including associated paths, driveway/ramp and other uses; side connections between yards. These targets do not establish a building footprint.
- Five bedrooms: master suite and guest room downstairs, three larger equal sleeping rooms upstairs, each with a private connected bathroom/walk-in dressing suite. A separate quiet front-garden-facing office is upstairs, with its own indoor WC. Front and rear balconies are shared without internal dividers.
- Connected family living, open kitchen with island, pantry and eight-seat dining; front receiving area without direct views into family space. Covered verandas, garden openings and backyard swing.
- Independently accessible basement parking for three SUVs, two motorbikes, one scooter and children's bicycles, plus EV charging, basic gym, gaming/recreation, storage and toilet. Use the smallest workable basement, not a fixed plot-coverage percentage.
- Play lawn, trees/mini-forest edge, private outdoor seating and small recreational pool; fishpond optional. Roof terrace with planters, shaded seating, gatherings and solar.
- Warm white, wood/oak tones, light stone and restrained dark accents. Daylight, privacy and year-round thermal comfort take precedence over excessive glass or premium finishes.

Room sizes will be derived from furniture, storage, seating and clear movement, then reviewed. The previous fixed room sizes are not requirements.

## Budget and phasing

Land starts around INR 50 lakh as a flexible target. The build aspiration is INR 50-70 lakh, preferably below INR 1 crore, **not cost-validated**. A large basement and the complete program present significant feasibility/cost questions. Construction quality, five bedrooms, gardens and basement parking are protected priorities; double height and premium finishes can go first.

The visualization includes all finished spaces. In a real build, the structure could be completed together and first-floor furnishing deferred. The construction-duration aspiration is 1-2 years from construction start, not from land purchase; no start date is set.

## Planned workflow

1. Establish specification validation and the reproducible Python/Blender foundation.
2. Propose clearly labeled site assumptions, furniture-led room sizes and dimensioned layouts for basement, ground, first, roof and outdoor areas.
3. Review space, access, privacy and feasibility conflicts before approving a layout.
4. Generate the architectural shell in Blender, then furnish, light and render the complete visualization.
5. Regenerate GLB and the React + TypeScript + Vite + React Three Fiber/Drei inspection viewer as the model evolves; implement first-person movement separately.
6. Publish through GitHub and Vercel after local validation.

## Repository map

- [House specification](house-spec/house.json) - structured source-of-truth brief, explicit targets and unknowns.
- [Candidate layout](house-spec/layout-study.json) - unapproved study geometry, furniture placement and review items.
- [Plan/validation utility](scripts/layout.py), [Blender generator](blender/create_layout.py), [packed finishes](blender/finishes.py) and [saved-camera renderer](blender/render_study.py) - reproducible study tooling.
- [Web exporter](blender/export_web.py) and [React website](web/) - canonical GLB/metadata/plan delivery and interactive inspection.
- [Design decisions](docs/design-decisions.md) - approved requirements, trade-offs and unresolved questions.
- [Room schedule](docs/room-schedule.md) - furniture-led program and room relationships.
- [Architecture](docs/architecture.md) - technical architecture and data flow.
- [Validation rules](docs/validation-rules.md) - geometric checks and professional-review boundaries.
- [Implementation plan](docs/implementation-plan.md) - milestones and review gates.
- [Task index](docs/tasks/README.md) - copy-ready milestone prompts.

## Important boundaries

The flat, standalone, front-road site is only an illustrative assumption. Orientation, neighbouring context, setbacks, permitted coverage/FAR, basement permissions, ground conditions and legally buildable envelope remain unresolved. Do not treat the whole plot as buildable or claim the brief fits its budget.

Basement structure, flooding protection, vehicle exhaust separation, fuel/LPG and battery locations, fire/egress, pool barriers, fall protection and roof loads need qualified local review for any real build. Attractive renders and passing geometry checks cannot establish safety, passive comfort or construction feasibility.

## Next step

Review the study plans and trade-offs before approving or revising the candidate layout. Detailed [M2 shell work](docs/tasks/02-blender-architecture.md) and final visualization remain gated on that review. The current utility validates a specific hand-authored candidate; it is not an automatic layout optimizer, a complete general-purpose schema or a vehicle swept-path solver.
