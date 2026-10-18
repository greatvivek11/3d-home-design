# Validation Rules

Validation must distinguish PASS, FAIL and NEEDS REVIEW. A passing geometry test is not evidence of building-code or structural compliance.

## Specification checks

- Required fields exist and have the correct types.
- Approved targets, unresolved values and candidate dimensions are distinguished. Null site width/depth, floor heights and wall thicknesses are valid unresolved brief inputs, not zero, silently defaulted geometry or approved dimensions.
- Specified dimensions are finite positive numbers; candidate geometry cannot proceed without the dimensions it uses. Report NEEDS REVIEW for missing inputs and identify any explicitly proposed study values.
- Unit system is explicit; convert linear feet to metres and sq ft to sq metres correctly at the geometry boundary. INR amounts, counts and fractions must not undergo length conversion.
- IDs are unique within their defined scope.
- Setbacks, orientation and jurisdiction may remain unresolved, but unresolved site constraints must block any claim that the layout fits the legally buildable envelope.
- Verify five required bedrooms: master and guest on ground, three equal-size children's rooms on first. A required office is additional, not a bedroom substitute.
- Verify two above-ground storeys plus one basement; roof terrace is accessible but not an additional enclosed storey.
- Office and laundry must each be assigned exactly once: first-floor office, basement-only laundry. Required bathroom/wardrobe references and private guest-ensuite access must resolve.
- Preserve one master WC backed to the actual wall, one basin, tub and separate shower; private guest bath, gallery WCs, three children's ensuites and basement WC: eight toilets.
- Budget ranges are unverified aspirations; neither schema validity nor geometry PASS establishes cost feasibility.

## Layout geometry checks

- Every room rectangle lies inside the main plate or explicit attached annexes. Enforce both the **7,000 sq ft area cap** and candidate dimension caps. The only above-ground annex is the front-lawn shaft, not a side link. Floor area sums actual non-overlapping plates, not their bounding rectangle.
- Rooms intended to be separate must not overlap beyond a documented tolerance.
- Shared boundaries and wall centerlines/thicknesses are consistent.
- Doors/windows lie on a valid host wall and their plan spans actually meet both named connected rooms. A nested excluded child's doorway may connect to its containing parent only on the child's genuinely internal boundary, not a shared exterior edge. Door heights/swings remain a separate design check.
- The candidate U-stair reserves 4 ft flights/landings, at least 12 in goings and twenty 6-7 in risers on rising levels. Reject a too-short reserve rather than silently steepening it. Doors meet the full-depth landing; native/decoded meshes clear the complete turn/flights above. These checks do not certify headroom, guarding, fire or accessibility.
- Exactly one non-window front exterior opening enters the labelled Entrance Gallery, with internal-only drawing/guest access. Preserve garden/required escape routes. Entrance/House Galleries are 4 ft; WC, recessed cupboard, lift and stairs are shared-route reachable without private rooms or outside shortcuts. The approved private-master exception is 3 ft. Widths are modeled zones/openings, not certified finished clearances.
- Master access must be House Gallery -> private entry -> bedroom -> dressing -> bathroom, never a public route through dressing. Preserve a furniture-free entrance and direct private bath/dressing connection.
- First-floor east/west galleries are removed in favor of a unified open lounge. Child 1 bath/dressing stay in the reclaimed front-office band, not lounge; the shared WC is recessed beside stairs and deducted from lounge area.
- Parking target rectangle does not intersect required access/circulation.
- Test three SUV bays plus manoeuvring/ramp swept paths and independent exit without moving another vehicle; include two motorbikes, scooter, bicycles and EV access.
- Include gym equipment operating areas, movable recreation-table play/storage states and safe circulation, not furniture bounds alone.
- Account for front/back yard targets using total plot area and include paths/ramp as intended. Do not double-count side access, assume a fixed house footprint or count all outdoor area as planted/play space.
- Flag basement/garden overlap for soil depth, tree-root, structural, waterproofing and drainage review; do not treat the basement roof as unrestricted natural ground.
- Sample entrance-gallery positions to occupied family-furniture corners against opaque full-height public-boundary/return intent. Preserve a clear wide doorless family entry and open living/dining/kitchen connections. This is not all-position, acoustic or security simulation.
- Verify furniture-led bedroom/office clearances, eight-seat dining, kitchen island, covered verandas and practical laundry/drying routes.
- Deduct guest ensuite from guest, pantry only from living and shaft intersection from gaming. The approved 4 x 2 ft cupboard terminates House Gallery outside living, faces into the gallery and cannot overlap its 4 ft through-route. Keep fridge in pantry and five beds against solid walls with two flanking bedside tables each. Fixture operation/ventilation and wet/chemical storage need review.
- Check complete clean/buffer/garage classification, a connected side-to-side chain of intended full-height barrier segments including core returns, two self-closing airlock doors and clean-side reachability of laundry/lift without the garage or airlock. Open-zone adjacency cannot jump declared partitions. These are topology/design-intent checks, not airflow/fire tests.
- Compute usable L-shaped floor area by subtracting enclosed child-room footprints, without subtracting shared open prayer space. Keep tiles, displayed area and selection overlays consistent; parent furniture cannot occupy excluded child floors or their surrounding wall allowance.
- Include all eight generated dining-chair footprints in bounds checks; do not assume a fitting tabletop means eight seats fit.
- Verify bedroom-to-private-dressing and dressing-to-bathroom direct connections, with no common-space or other-suite access to a child's bath/dressing. Check real wardrobe footprints leave at least a 3 x 5 ft dressing aisle; this does not resolve all operating/accessible clearances.
- Check enclosed-shower intent beside soft bath/dressing dividers. Curtains alone are not wet-area separation or proof of humidity control.
- First-floor common WC opens only to unified lounge beside stairs; ground common WC terminates the left House Gallery with gallery-only access, not living/prayer. Both must remain reachable without private rooms or an outside shortcut.
- Prayer cannot adjoin bathrooms. Preserve the shared living-room garden slider without crossing a private bedroom/prayer; its approach stays clear of furnishings.
- Gym and gaming usable areas must be equal; keep all existing equipment roles, but still review simultaneous play/operation.
- All five bedrooms need at least one large outward-facing operable glazing opening. The current candidate check uses at least 9 ft width and 7 ft intended height, not a code/daylight/ventilation criterion.
- Export shared front/rear decks without internal privacy screens, retaining perimeter guards. First-floor SVGs must show the balconies and soft divider openings.
- Geometry outside the plot or approved candidate envelope is reported.
- Floor levels and vertical openings align across floors.
- Aligned lift reserves are **in front of internal stairs in the front lawn**, not the driveway. Each gate meets a full-floor front landing with a direct **internal shared-gallery door**. Reject any external stair-link room/annex. Mirrored stairs, complete turn/run voids and front landing slabs/gates must agree. Below ground only, explicit shaft boundary cutouts may trim gaming; subtract actual intersections and retain equal net recreation. Product/pit/overrun, headroom, fire and accessibility remain unverified.
- Use actual road-relative levels in ramp headroom assumptions: ground +1.5 ft, slab underside +1 ft, basement -8.5 ft. Model three entry steps and the raised rear garden deck; test site alignment in focused-ground and assembled views. These are not an accessible-arrival or planting-load certification.
- The restored brief requires a modeled pool; reject a missing pool even if an obsolete compact deferral is added. Require an enclosing barrier reserve and no pool/barrier overlap with basement, sampled convex driveway sections or buffered vehicle footprints. This is plan separation, not excavation, deck-clearance or child-safety certification.
- Regression tests retain the spacious front drawing/guest and rear master/family split, transverse House Gallery, front office/Child 1 and rear children around the lounge, equal 272 sq ft child rooms and larger gardens. Record local guest/master/suite/lounge and basement-aisle changes rather than claiming an exact historical copy.
- Keep actual common-WC space in front of its wall-backed toilet; the current first-floor reserve is 6 x 5.5 ft with 2.5 ft frontal space and a furniture-free 3 ft inside doorway approach. The targeted two-foot minimum is a concept regression, not an accessibility/code certificate.
- All three child bedroom-to-dressing doorways need a furniture-free strip covering the opening width and extending 3 ft inside the dressing room, in addition to a 3 x 5 ft dressing aisle. This is a targeted furniture check, not general accessibility or bathroom-clearance certification.
- Sample the full large-SUV body, front/rear overhangs and 0.3 m clearance, not just its centreline. Check flared paving, portal, clear arrival aisle, eased elevation integration, roof and underside margins. Independent bay manoeuvres, street approach, dynamics/traction, drainage and legal grades remain specialist checks.
- Weather covers are explicit geometry with an inspection toggle, not flood-proofing or windblown-dust exclusion. Drain markers do not establish hydraulic capacity, sump/pump backup or waterproofing.
- Structural diagram must state non-engineered status and use display-only proxies. Check proxy-column footprints against actual net living/parking clear-span zones; absence of proxies there does not establish feasibility, load paths, sizes or safety.
- Model pool barriers, balcony/roof guarding and appropriate opening protection; insect screens, nets, shallow pool depth and covers are not sufficient substitutes.

## 3D checks

- Mesh dimensions and floor elevations are consistent with the specification.
- Openings are actually represented in wall geometry, not merely drawn over solid walls.
- Object names/collections are stable and unique.
- No non-finite coordinates or unintended degenerate geometry.
- GLB export completes, references available textures and can be loaded by a test viewer.
- Bind generated assets to actual layout/brief fingerprints. Visual-only changes must preserve fingerprints; user-approved layout revisions update them deliberately. Check saved Blender geometry, source furniture/derived chairs and decoded export, not just unchanged JSON.
- Validate embedded PNG payloads and PBR assignments; exercise actual texture rendering and dimensions in a real high-DPI browser. The Node image adapter used for geometry tests is not a substitute for browser rendering.
- Batching/compression must preserve picking extras and separately identified guard, partition, closing-door, shower and soft-divider intent. Verify decoded position/normal/UV attributes and triangle topology; do not silently quantize a locked layout.
- Room annotations derive from current bounds, anchor inside net footprints, distinguish outer extents, stay sharp and remain noninteractive. Test collision/zoom thresholds, offscreen culling, independent names/sizes toggles and selected-room feet/metre lines. In assembled view, do not annotate rooms through higher slabs.
- Architecture and structural groups must be separately switchable without reloading/changing room geometry. Structural warning remains visible, site stays hidden and decoded column proxies must not intrude into requested net clear-span footprints.
- Site, basement, ground, first and roof identities remain inspectable. Roof-terrace access and layer visibility must not break walkthrough navigation.
- Visualization includes finished first-floor spaces even if future construction furnishing is phased.

## Limitations

Automated checks are geometric heuristics. They do not verify affordability, structural/seismic adequacy, fire safety, egress compliance, accessibility, local code compliance, garage exhaust separation, ventilation adequacy, thermal/daylight performance, waterproofing/flooding, roof/soil loads, tree viability, pool safety or construction feasibility. LPG, generator/diesel, battery/electrical and water-storage locations require specialist review; no spare vehicle fuel is required. Flag these for a qualified local architect/engineer and relevant specialists/authority.
