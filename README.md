# Dream Home - Blender + Python

A code-driven visualization of a private, nature-connected family retreat: basement, ground floor, first floor and accessible roof terrace. Blender/Python is the editable authoring pipeline; a React/Three.js website provides interactive inspection of the same geometry.

## Current status

**Spacious Study 010 restores the user's preferred 7,000 sq ft direction.** The candidate plot returns to **70 x 100 ft**, with **50 x 50 ft main plates**. Front drawing/guest rooms flank Entrance Gallery; the transverse House Gallery separates them from rear master/family spaces, with WC left and utility cupboard right. Upstairs, front office/Child 1 and two rear child rooms are separated by a transverse lounge. Larger gardens and an **8 x 16 ft pool** return. The front-lawn lift retains direct internal stair access, with **no external link or extra side strip**. Basement/roof functions and later furnishing/privacy/weather improvements remain, with necessary footprint/core alignment. This restores the pattern with local room/suite adjustments, not every old dimension. The editable cutaway retains 113 placements, 20 packed maps and fifteen scenes. Site, dimensions, cost, safety and engineering remain unapproved.

Study 010 corrects [Study 009](assets/models/study-009/dream-home-study.blend): the user-approved **4 x 2 ft cupboard** faces left at the right terminal end of House Gallery, entirely outside living. Living regains **12 sq ft**, reaching **343.5 sq ft net**. The shared upstairs WC shrinks to **6 x 5.5 ft**, enlarging the unified lounge to **653 sq ft net**. Galleries retain their 4 ft through-route and the private master entry remains 3 ft. All other rooms, basement, roof, plot, gardens, pool and ramp are unchanged from Study 009.

Blender 5.2.2 LTS is accessible on macOS through `/Applications/Blender.app/Contents/MacOS/Blender`. The saved study uses portable Cycles CPU settings and is reopened after saving; the separate render utility also supports this Mac's Metal GPU. The browser loads the matching GLB; its current size is displayed in the website footer. This is an inspection viewer, not a collision-aware first-person walkthrough.

### Refined presentation retained in the revised layout

- Physical-scale oak flooring, separate continuous-grain joinery, walnut, limestone, concrete and woven sage/linen finishes. Maps are generated locally and packed into Blender and GLB; no downloaded models, texture services or HDR files are needed.
- Rounded upholstery, layered beds and pillows, real table/chair legs, cabinet fronts and shelving, workstation keys/screen, piano keys, hollow basins/toilets/tub, fittings, kitchen appliances, vehicles, gym equipment and solar cells.
- Clean wall caps/skirting and framed glazing; shared balconies retain their original uninterrupted decks and perimeter guards.
- Cycles/AgX in Blender; real-time GTAO ambient depth, fitted 4096px studio shadows, up to 16x anisotropic filtering and 2x pixel ratio on the web. Small screens use balanced rendering.
- Geometry checks cover all 113 placements and eight dining-chair footprints. Layout/brief hashes bind native/web assets to their sources. Earlier studies and their videos remain unchanged.

## Explore in the browser

### Checked-in assets and Git LFS

Install Git LFS, then run `git lfs install` and `git lfs pull` after cloning. The required binary assets are versioned with LFS:

- [Editable Study 010](assets/models/study-010/dream-home-study.blend), with packed finishes, [layout snapshot](assets/models/study-010/layout-snapshot.json), [brief snapshot](assets/models/study-010/brief-snapshot.json) and [portable generation metadata](assets/models/study-010/generation-result.json).
- Preserved [compact Study 007](assets/models/study-007/dream-home-study.blend), [Study 006](assets/models/study-006/dream-home-study.blend), [Study 005](assets/models/study-005/dream-home-study.blend), [Study 004](assets/models/study-004/dream-home-study.blend), [Study 003](assets/models/study-003/dream-home-study.blend) and its [animated tour](assets/models/study-003/dream-home-tour.blend). These are earlier layouts, not Study 010; the compact direction and Study 006's larger site/side link are superseded.
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
- Toggle **3D view / Floor plan**, **Labels**, **Dimensions**, and **Reset view**. Room names and inline room sizes appear when there is enough screen space; zoom/focus to reveal smaller rooms. Tags are collision-culled rather than piled on top of each other. Selecting a room adds dimension lines in feet/metres; inline sizes are in feet and net area remains separate. In assembled view, tags annotate only the highest visible floor, not rooms hidden beneath slabs.
- Switch **Furnished / Structural intent** to inspect a separate perimeter/core support-and-beam diagram in any presentation mode. Teal supports and ochre beams are display proxies, **not member sizes or an engineered load path**. Pale areas show requested clear-span living/parking footprints; feasibility, structural system and possible internal supports need an engineer. The warning stays visible and site terrain is omitted in this mode.
- **Garden & site** is available in assembled and ground-floor views. Other views omit terrain so it cannot conceal their plan sheets.
- **Weather covers** reveals the roof stair/lift enclosure and driveway canopy; covers start hidden for cutaway inspection. **Studio quality** toggles ambient occlusion and higher-contrast/sharper studio lighting on larger screens.
- The room section links to dimensioned plans, also usable if the model cannot load. **Concept 010** explains the study's limitations.
- Parent-room cards show outer extents separately from usable area, excluding enclosed pantry/shaft/ensuite/cupboard footprints where applicable; selection overlays follow the actual net floor.

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

The 40 frontend tests cover presentation/annotations/units, source and portable-bundle fingerprints, every room footprint and all 113 furniture placements, PBR PNGs, private suites, side glazing, wall-backed headboards and ten lamps, front lift doors, separate structural groups, guards/showers, Meshopt and all five plans. Decoded geometry verifies the unified lounge/WC subtraction, front-band suite, restored areas/site bounds, no stair-link meshes, raised entrance/rear deck, tread/landing positions, complete slab holes, the sole front portal, real ramp elevations, pool level and actual terrain openings beneath pool/ramp. Node validates PNGs; Chromium exercises actual rendering and controls.

### Regenerate browser assets after changing the house

First regenerate the Blender study from the candidate using the commands below, then export that saved file. Run `npm --prefix web ci` first: export uses the local Node compression helper.

```bash
/Applications/Blender.app/Contents/MacOS/Blender \
  --background --factory-startup --python-exit-code 1 \
  --python blender/export_web.py -- \
  --blend assets/models/study-010/dream-home-study.blend
```

Replace the example path with the newly generated study when applicable. The exporter requires its matching layout snapshot; it refuses a stale/mismatched study. It evaluates bevels/normals, batches only compatible same-finish/identity pieces and preserves individually identified safety-intent panels and room tiles. Presentation stages, dimensions, text, cameras, lights and collection instances stay out of the GLB.

The [local compression helper](web/scripts/optimize-model.mjs) applies Meshopt without quantization, filters or simplification, then decodes and fingerprints the result to verify exact attributes, triangle topology, transforms and picking identities. Export writes matching GLB, manifest/source fingerprints and SVGs without overwriting Blender. Exact compressed/uncompressed sizes are recorded in the manifest; the footer shows the current model size. HTTP gzip/Brotli can reduce transfer further when hosting is configured; deployment compression is not configured yet.

Unlike local `output/`, the public browser model/plans and generated metadata are deliberate versioned deliverables. The repository assigns GLB files to Git LFS: a fresh checkout or future hosting build must fetch the actual binary, not an LFS pointer. The asset tests detect missing/pointer/mismatched GLBs. Deployment configuration is not included yet.

## Open the latest study

Current local artifacts are in [output/study-010/](output/study-010/). Previous [Study 007](output/study-007/), [Study 006](output/study-006/), [Study 005](output/study-005/), [Study 004](output/study-004/), [refined Study 003](output/study-003-refined/), [Study 003 blockout](output/study-003-upstairs/), [Study 002](output/study-002-revised/) and [Study 001](output/study-001-side-by-side/) are preserved.

- [Editable Blender file - opens with all four levels side by side](output/study-010/dream-home-study.blend)
- [Ground](output/study-010/ground.png), [basement](output/study-010/basement.png), [first floor](output/study-010/first.png), [roof](output/study-010/roof.png) and [garden overview](output/study-010/overview.png) previews
- [Structural-intent stack - not engineered](output/study-010/structural-stack.png)
- Dimensioned [site](output/study-010/site.svg), [ground](output/study-010/ground.svg), [basement](output/study-010/basement.svg), [first](output/study-010/first.svg) and [roof](output/study-010/roof.svg) plans
- [Checks and review limitations](output/study-010/review-report.json), plus brief/layout snapshots and [generation/render settings](output/study-010/generation-result.json)

The file opens in `07 - All four plans side by side`, with headings for basement, ground, first and roof. Scroll to zoom, middle-mouse to orbit, Shift + middle-mouse to pan, and Numpad 0 to toggle camera view (or use View > Cameras > Active Camera).

Use the **scene selector at the top-right of Blender's main window**, not the Outliner collection list: `01` garden/ground, `02` ground, `03` basement, `04` first, `05` roof, `06` physical stack, `07` side-by-side, `08`-`10` close-ups, or **`11`-`15` structural intent** (stack and individual floors, explicitly not engineered). Presentations reference canonical floor collections. The file opens in Material Preview; saved Cycles cameras support finished stills. Each floor's **LABELS** and **DIMENSIONS** child collections toggle its vector annotations. Structural collections are separate from furnished geometry.

The internal `START HERE - Study notes` text explains the study. Walls remain intentionally cut to 3 ft; furnishings are detailed parametric concept assets, not manufacturer/construction specifications. Per-floor plans use local zero elevation; physical levels are now **-8.5, +1.5, +12.5 and +23.5 ft relative to road**. Site placement compensates for local ground views; the basement ramp context compensates for local basement views.

### Animated video preview

These preserved movies and the current tour camera sequence depict **Study 003**, not the current Study 010. No new tour is rendered as part of this layout revision; reframe every shot before filming the restored layout.

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

#### Faster-render experiments

The default remains **Cycles / 48 samples**. Opt into `--engine EEVEE --samples 32` to use Eevee's screen-space ray tracing and fast global illumination, or `--engine CYCLES --samples 16 --device METAL` to test fewer Cycles samples. Always choose a **new** `--output` directory for each renderer/sample combination; the original movie and saved assets are not overwritten.

For example:

```bash
/Applications/Blender.app/Contents/MacOS/Blender \
  --background --factory-startup --python-exit-code 1 \
  --python blender/create_tour.py -- \
  --blend assets/models/study-003/dream-home-study.blend \
  --output output/a-new-eevee-tour --engine EEVEE --samples 32 --stills
```

Review its contact sheet and rerun with `--resume` instead of `--stills` to encode the same 12-second sequence. Eevee always uses Blender's configured GPU backend (Metal on this Mac); `--device` only selects the Cycles device. Identical camera paths, resolution, frame rate, lighting, materials, titles and transitions make the results comparable, but Eevee approximates lighting/reflections and can show more noise on glass/shadows.

Stills reports record individual frame timings, including the first-frame setup cost; compare warmed frames separately. Full runs record per-shot wall time and how many frames were actually rendered versus reused. Sample counts are engine-specific, not equivalent quality settings. Local [benchmark results](output/study-003-tour-speed-comparison/benchmark.json) and a [same-frame visual comparison](output/study-003-tour-speed-comparison/quality-comparison.png) accompany the [Eevee movie](output/study-003-tour-eevee32/dream-home-preview.mp4); the original Cycles movie remains in its original directory.

On the M4 Pro/Metal Mac, the full Eevee 32 run took **339.47 seconds (5m39s)** versus the original Cycles 48 run's **1,179.02 seconds (19m39s)**: about **3.47× faster**. Both rendered 297 fresh frames, reused nine reviewed frames and included encoding/verification; initial scene/title preparation and the sample-render runs are separate. Nine-frame benchmarks measured warmed means of **2.424 s/frame for Cycles 16** and **1.313 s/frame for Eevee 32**; only Eevee received a complete new movie. Linear extrapolation suggests roughly **57–85 minutes for 2–3 minutes** of similarly complex Eevee footage, not a guarantee for a new walkthrough or a sustained longer render.

### Important proposal, not a new approved requirement

Study 010 supersedes the compact Study 007 direction and returns to **70 x 100 ft = 7,000 sq ft**, without reviving Study 006's 8,856 sq ft plot or external link. The user approved restoring the old ground/first-floor room pattern, allowing local internal-access/suite changes and necessary basement/roof footprint/core alignment. This is not an approved legal plot or minimum-size proof.

Main ground/first plates are **50 x 50 ft = 2,500 sq ft**, plus a **60 sq ft front-lawn shaft annex** each. Basement is **4,016.7 sq ft**, excluding driveway. The three levels total approximately **9,136.7 sq ft** before detailed deductions/balconies/roof enclosure: this is accumulated floor area, **not plot growth beyond 7,000 sq ft**. Budget feasibility is unverified.

**Basement retained/aligned:** recreation stays in front, clean stores/laundry and protected circulation in the middle, garage behind. Gym/gaming are **387.75 sq ft net each**, stores **88.5 each**, laundry **117.5**. Three SUVs remain at the **front of the garage compartment**. Core alignment shifts the garage back, reducing rear aisle depth from 20.83 to **16.83 ft**, with greater width; the sampled route still clears actual parked fixtures. Independent stall manoeuvres, simultaneous equipment use, storage capacity and air/fire/egress performance remain unproven.

**Entry and galleries:** one 4 ft front opening enters the **4 ft Entrance Gallery**, between drawing/guest rooms. The transverse **38 x 4 ft House Gallery** has its **8 x 5 ft WC left** and approved **4 ft long x 2 ft deep cupboard at the right terminal end**, facing left between stairs and living. The cupboard is outside living and does not narrow the through-route: the gallery ends at its sliding front. A **4 ft internal stair gallery** preserves front-landing access without an external link. The private master entry is the approved **3 ft exception**. Ordinary room/bath/stair/lift openings are 3 ft, family archway 6.5 ft; modeled widths are not finished clear widths after frames. Drawing/guest have no direct outside doors; garden/required escape remain.

**Local ground adjustments:** drawing is **314.5 sq ft**. Narrowing Entrance Gallery gives guest **11.5 x 17 ft gross minus 5.5 x 7 ft ensuite = 157 sq ft net**, retaining front glazing, queen, reading seat and wardrobe. All five beds retain solid-wall headboards and two bedside tables/lamps; drawing/living/office retain side windows.

**Family spaces:** public-boundary screens and a **6.5 ft doorless entry** protect sampled Entrance Gallery sightlines. Living is **391.5 gross - 48 pantry = 343.5 sq ft net**, including open prayer/circulation; no cupboard is deducted. Dining is **150 sq ft** with eight chair footprints; kitchen **168 sq ft**, pantry **6 x 8 ft** with fridge. Living/dining/kitchen remain internally open. A **7 ft living-room garden slider**, with a clear approach, reaches the rear veranda without crossing master/prayer. Service/pull-back comfort and all-position privacy remain unverified.

**Master:** sleeping **21.5 x 17 ft = 365.5 sq ft**, dressing **9 x 9.5 ft = 85.5**, left bathroom **8.5 x 8.5 ft = 72.25 sq ft**. Route: House Gallery -> **3 x 9.5 ft private entry** -> bedroom -> dressing -> bath. No dressing/bath door opens to House Gallery. Dressing remains larger than bath; retain **one wall-backed WC, one compact basin**, a **5.5 ft tub**, separate shower and private garden glazing. The bathroom loses 1 ft depth to retain the ground WC and recovered bedroom depth. The house retains **eight toilets**.

Kitchen windows do not replace ducted source extraction. **Neither kitchen nor garage exhaust outlets are located yet:** they must avoid the rear play lawn, pool/veranda, windows, neighbours and fresh-air intakes. No duct sizes, airflow rates or safety performance are established.

**First floor refined:** front-left office and front-right Child 1; rear-left Child 3 and rear-right Child 2. All child sleeping rooms are **16 x 17 ft = 272 sq ft**. Child 1 bath/dressing occupy a **6 ft wide front suite strip**, reclaimed from office width, not lounge; each is **6 x 8.25 ft**. Private suite entries and clear dressing-door approaches are checked.

Office is **12 x 17 ft = 204 sq ft**, retaining workstation, shared table, reduced shelving and piano. The **49 x 14 ft unified lounge** is **686 gross - 33 shared WC = 653 sq ft net**, versus 634 in Study 009. There are no east/west gallery rooms or separating walls. The **6 x 5.5 ft common WC** opens only to lounge at the right stair end. Repositioned toilet/basin retain a clear 3 ft inside doorway approach and 2.5 ft toilet-frontal space; door operation/accessibility remain unverified. Front stair and rear balcony routes remain **4 ft**, meeting lounge openly; furniture use and recreational operating space still need detailed review.

Balconies remain uninterrupted shared decks with perimeter guards: front **40 x 6 ft**, rear **50 x 6 ft**. Office, Child 1 and the internal gallery have front access; rear children and the common route reach the rear deck. Soft bath/dressing dividers and enclosed showers remain concept geometry, not wet-area engineering.

**Front-lawn core:** aligned **7 x 7 ft lift reserves** meet the front full-floor landing of the **9 x 17 ft internal U-stair**. Shared galleries connect directly inside the main plate on all levels. **No stair-link room, external link annex or link roof exists.** Flights/landings remain 4 ft, with twelve-inch goings and twenty risers. Product/pit/overrun, headroom, fire, accessibility and setbacks remain unverified; lift is not emergency egress. Roughly **49.5 ft structural proxies** are not member sizes or proven clear spans.

**Driveway and weather:** **12 ft straight width**, flared **15 ft bend**, **19 ft rear-axle radius**, **24 ft portal** and **96.35 ft path**. Maximum candidate grades remain 14% straight/10% curved. The sampled **5.25 x 2.25 x 2.2 m SUV** plus 0.3 m buffer clears paving/portal/parked fixtures; minimum assumed roof/underside margins are **0.36/0.13 m**. Ground **+1.5 ft** and basement **-8.5 ft** retain a 10 ft rise. Three front steps and a raised rear garden deck are modeled; accessible arrival and garden loads need design. Roof stair/lift covers and open-sided ramp canopy remain; no flood/dust guarantee is implied.

**Outdoor restoration:** front/back bands return to **20% / 30%**; the play lawn is **48 x 15 ft**. The **8 x 16 ft pool** and its enclosure are outside the basement and sampled vehicle route. Rear grade/pool edges align at +1.5 ft; terrain/fill has real openings for driveway/pool and excludes the basement volume. The deck above basement and raised soil outside it remain non-engineered intentions, not deep-soil/retaining/load/drainage approval. Pool enclosure/deck circulation and child safety need specialist design. Fishpond and double height remain deferred.

## Reproduce and validate

No system Python packages need installing. Layout tests use the standard library; finish generation uses NumPy bundled with Blender. Run from the repository root:

```bash
python3 -m unittest discover -s tests -v
python3 scripts/layout.py
/Applications/Blender.app/Contents/MacOS/Blender \
  --background --factory-startup --python-exit-code 1 \
  --python blender/create_layout.py
```

The Blender command creates a new timestamped directory under `output/`, writes plans/reports/snapshots, renders fourteen Cycles/AgX stills at up to 96 samples and saves/reopens the `.blend`. Standard plans/overview are 2400 x 2600, comparison 5200 x 2400, living detail 2400 x 1800, and office/bedroom details 2400 x 2100. The opening scene, four floor instances and all 113 furniture footprints are checked. Use `-- --output output/a-new-study-directory` for an explicit path, adding `--skip-render` for model/plan-only generation. Existing directories are refused.

To render saved cameras separately, without changing the editable file:

```bash
/Applications/Blender.app/Contents/MacOS/Blender \
  --background --python-exit-code 1 --python blender/render_study.py -- \
  --blend assets/models/study-010/dream-home-study.blend --device METAL
```

Use `--device CPU` on other systems. Optional `--scenes office-detail living-detail`, `--samples 32` and `--resolution 1440` support focused previews. Missing requested GPU support fails explicitly rather than silently switching devices. Render settings/results are recorded alongside the study.

For plans/reports without Blender:

```bash
python3 scripts/layout.py --output output/a-new-plan-directory
```

`FAIL` produces a nonzero exit status. `NEEDS REVIEW` is the expected successful result for an unapproved concept. The 114 layout tests cover the 7,000 sq ft cap, restored spacious pattern, private master entry, unified lounge/front suite/stair-side WC, cupboard outside living and clear compact-WC approach, preserved basement/roof/outdoors, pool/barrier separation and required presence, no external link, direct internal landings, actual doors/private suites, 3 ft dressing-door approaches, common-WC space, raised-ground driveway assumptions, equal recreation, privacy/open connections, beds/lamps, pantry/fridge, galleries/airlock and non-engineered structure. Thirteen driveway tests check body/overhang sweep, flaring/portal, grade integration, roof/underbody margins and invalid cases; this is not independent parking certification.

Eight additional tour tests cover the exact dissolve timeline, moving camera paths, orbit radius/height, easing, invalid frame ranges and renderer-specific settings/validation. Blender round-trip pose checks and full MP4 probing/decoding complement those pure-Python tests.

Generated output is Git-ignored and local, not included in a fresh checkout. Regenerate it using these commands. Edit [layout-study.json](house-spec/layout-study.json) for candidate placement/dimensions; do not write proposals into the approved brief as confirmed facts.

## Approved direction

- Quiet, cooler, nature-connected setting near mountains, potentially around Dehradun; no plot purchased.
- Latest direction restores approximately **7,000 sq ft**, spacious front/rear ground and first-floor room patterns, larger gardens and pool. Keep the front-lawn lift/no external link and newer improvements; allow local internal access and basement/roof alignment. Further growth needs approval; no actual plot is purchased or approved.
- Roughly 20% front yard and 30% backyard, including associated paths, driveway/ramp and other uses; side connections between yards. These targets do not establish a building footprint.
- Five bedrooms: master/guest downstairs and three equal upstairs sleeping rooms with private connected bathroom/dressing suites. Quiet front-left office; common first-floor WC. Shared front/rear balconies without internal dividers; large operable bedroom glazing.
- Basement-only laundry, equal gym/gaming areas, four-level lift reserve, prayer away from garden exit/WCs, wider drawing/smaller furnished guest and a larger master closet with one WC in the reduced bath.
- One controlled front entrance, labelled internal galleries and offset family privacy; private guest ensuite, left-end WC, right-gallery cupboard and **front-lawn lift with direct internal full-floor stair landing access, no external side link**. Retain garden/required escape. Wall-backed beds have two bedside lamps; pantry houses the fridge; master has one basin.
- Connected family living, open kitchen with island, pantry and eight-seat dining; front receiving area without direct views into family space. Covered verandas, garden openings and backyard swing.
- Independently accessible basement parking for three SUVs, two motorbikes, one scooter and children's bicycles, plus EV charging, basic gym, gaming/recreation, storage and toilet. Use the smallest workable basement, not a fixed plot-coverage percentage.
- Larger play lawn, planting/tree reserve, private outdoor seating and family pool with controlled barrier. Roof retains planters, shade, gatherings and solar; pool/garden structure and safety remain unverified.
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

Review the restored spacious plans and explicit local adjustments before approving the candidate. Detailed [M2 shell work](docs/tasks/02-blender-architecture.md) and final visualization remain gated on that review. The utility validates a hand-authored candidate with a sampled arrival sweep; it is not an automatic optimizer, full schema, independent-bay planner or traffic-engineering solver.
