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
- Office and laundry candidates must each be assigned exactly once to an allowed floor and respect an explicit assignment. Office is now assigned first. Required bathroom/wardrobe references and dual guest/receiving bathroom access must resolve.
- Preserve the master suite's two separate toilets and two basins, guest/receiving shared bathroom, family toilet, three children's ensuites and basement toilet, plus the new office-only WC: nine toilets, derived from the brief rather than a fixed old count.
- Budget ranges are unverified aspirations; neither schema validity nor geometry PASS establishes cost feasibility.

## Layout geometry checks

- Every room rectangle has positive width/depth and lies inside the candidate envelope.
- Rooms intended to be separate must not overlap beyond a documented tolerance.
- Shared boundaries and wall centerlines/thicknesses are consistent.
- Doors/windows lie on a valid host wall and their plan spans actually meet both named connected rooms. Door heights/swings remain a separate design check.
- Stair openings, landings and travel paths connect the floors without geometric contradictions.
- Required paths from entrance to common spaces and stairs remain clear in the model.
- Parking target rectangle does not intersect required access/circulation.
- Test three SUV bays plus manoeuvring/ramp swept paths and independent exit without moving another vehicle; include two motorbikes, scooter, bicycles and EV access.
- Include gym equipment operating areas, movable recreation-table play/storage states and safe circulation, not furniture bounds alone.
- Account for front/back yard targets using total plot area and include paths/ramp as intended. Do not double-count side access, assume a fixed house footprint or count all outdoor area as planted/play space.
- Flag basement/garden overlap for soil depth, tree-root, structural, waterproofing and drainage review; do not treat the basement roof as unrestricted natural ground.
- Check front receiving sightlines do not directly expose family living/kitchen; backyard routes must not cross master bedroom or office.
- Verify furniture-led bedroom/office clearances, eight-seat dining, kitchen island, covered verandas and practical laundry/drying routes.
- Check dual bathroom door swings and flag the privacy/locking solution for review. Food/chemical storage and garage/occupied-air separation require explicit attention.
- Check a complete clean/buffer/garage room classification, an intended full-height garage barrier, two self-closing airlock doors and internal clean-side reachability without traversing garage rooms. Open-zone adjacency must not jump across a declared partition. These are topology/design-intent checks, not airflow or fire-performance tests.
- Compute usable L-shaped floor area by subtracting enclosed child-room footprints, without subtracting shared open prayer space. Keep tiles, displayed area and selection overlays consistent; furniture cannot occupy excluded pantry space.
- Include all eight generated dining-chair footprints in bounds checks; do not assume a fitting tabletop means eight seats fit.
- Verify bedroom-to-private-dressing and dressing-to-bathroom direct connections, with no common-space or other-suite access to a child's bath/dressing. Check real wardrobe footprints leave at least a 3 x 5 ft dressing aisle; this does not resolve all operating/accessible clearances.
- Check enclosed-shower intent beside soft bath/dressing dividers. Curtains alone are not wet-area separation or proof of humidity control.
- Office WC must have only office access. Retain common stair/lounge/rear-balcony reachability without crossing private rooms or using an outside-node shortcut.
- Export shared front/rear decks without internal privacy screens, retaining perimeter guards. First-floor SVGs must show the balconies and soft divider openings.
- Geometry outside the plot or approved candidate envelope is reported.
- Floor levels and vertical openings align across floors.
- Internal stairs connect basement, ground, first and roof; external maintenance access does not require crossing family interiors. No lift is required.
- Model pool barriers, balcony/roof guarding and appropriate opening protection; insect screens, nets, shallow pool depth and covers are not sufficient substitutes.

## 3D checks

- Mesh dimensions and floor elevations are consistent with the specification.
- Openings are actually represented in wall geometry, not merely drawn over solid walls.
- Object names/collections are stable and unique.
- No non-finite coordinates or unintended degenerate geometry.
- GLB export completes, references available textures and can be loaded by a test viewer.
- Visual-only revisions must preserve the source layout/brief fingerprints, all room-floor bounds/footprints and all source furniture placements, including generated dining chairs. Check saved Blender geometry and decoded exported geometry, not just unchanged JSON.
- Validate embedded PNG payloads and PBR assignments; exercise actual texture rendering and dimensions in a real high-DPI browser. The Node image adapter used for geometry tests is not a substitute for browser rendering.
- Batching/compression must preserve picking extras and separately identified guard, partition, closing-door, shower and soft-divider intent. Verify decoded position/normal/UV attributes and triangle topology; do not silently quantize a locked layout.
- Dimension overlays must derive from existing bounds, distinguish outer extents from net areas, stay sharp when zoomed and remain noninteractive so they cannot steal room clicks.
- Site, basement, ground, first and roof identities remain inspectable. Roof-terrace access and layer visibility must not break walkthrough navigation.
- Visualization includes finished first-floor spaces even if future construction furnishing is phased.

## Limitations

Automated checks are geometric heuristics. They do not verify affordability, structural/seismic adequacy, fire safety, egress compliance, accessibility, local code compliance, garage exhaust separation, ventilation adequacy, thermal/daylight performance, waterproofing/flooding, roof/soil loads, tree viability, pool safety or construction feasibility. LPG, generator/diesel, battery/electrical and water-storage locations require specialist review; no spare vehicle fuel is required. Flag these for a qualified local architect/engineer and relevant specialists/authority.
