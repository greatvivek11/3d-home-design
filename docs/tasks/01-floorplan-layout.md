# Codex Task M1 — Floor-Plan Layout and Feasibility

Implement M1 after M0 has a working configuration loader and tests. Do not generate detailed furniture or photorealistic materials yet.

## Read first

Read house-spec/house.json, docs/room-schedule.md, docs/validation-rules.md, docs/design-decisions.md and docs/tasks/00-foundation.md.

## Goal

Create editable, dimensioned 2D layout studies for basement, ground, first, roof and outdoor/access areas, with a clear report explaining whether the user-approved program fits the proposed study site.

## Site and coordinate rules

- Latest target restores approximately **7,000 sq ft**, with the spacious ground/first room pattern, larger gardens and pool. No site dimensions are approved; further plot growth needs approval.
- Front/back yard fractions of roughly 20%/30% include associated paths, driveway/ramp and other uses. Connect yards via side paths; do not infer a fixed building footprint or double-count access.
- Use a local plotting coordinate convention (for example, X across the plot width and Y along its depth). Treat the front edge as a drawing convention only; it does not establish compass direction or road orientation.
- Setbacks, road width, jurisdiction, basement permissions, ground conditions and buildable envelopes are unresolved. Do not present the whole plot as legally buildable or assume basement and above-ground envelopes match.
- Flat, standalone and front-road context may be used only as labeled study assumptions. Do not erase required outdoor space to fit the house. Any feasibility study remains unapproved, not permit-ready or code-compliant.
- Use metres internally. Show labels and dimensions in feet for review where helpful.

## Requirements

1. Define layout data with explicit rooms/zones, stable IDs, floor IDs, furniture/equipment footprints, doors, windows, stairs and circulation. Include site, verandas, balconies, pool/barriers and roof terrace.
2. Derive proposed sizes from approved furniture/storage/seating and movement requirements, not superseded starter dimensions. Keep proposals separate from the brief's null unknowns. Assign office and laundry exactly once to allowed floors.
3. Generate readable dimensioned plan outputs for basement, ground, first and roof/site. SVG is an acceptable first output because it can be generated without a graphics dependency; PNG is optional.
4. Show plot bounds, candidate envelopes/status, labels, proposed sizes, dimension strings, openings, stairs, ramp, full parking/access and allocated outdoor areas.
5. Check finite/positive dimensions, unintended overlaps, bounds, host walls, furniture use, three-SUV swept paths and independent exits, other vehicle storage, privacy sightlines, bathroom access and basement-to-roof stair connectivity. Flag occupied garage separation, drainage, services and pool/fall safety for professional review.
6. Distinguish PASS, FAIL and NEEDS REVIEW. An unresolved setback or jurisdiction should produce NEEDS REVIEW and block claims of regulatory compliance.
7. Add tests for positive cases and intentionally invalid cases.
8. Produce a candidate/report, not an approved plan. Restore front drawing/guest divided by Entrance Gallery, transverse House Gallery with left WC/right cupboard, rear master/family; upstairs front office/Child 1, two rear children and transverse lounge. Report local access/suite adjustments, retain five bedrooms/office and the basement/roof functions, and restore the pool outside basement/driveway. Further plot growth requires a new user decision. Do not imply affordability.
9. Represent one wall-backed master WC, one basin, tub/shower, private guest ensuite and other WCs: eight toilets. Retain sole front entry, labelled internal galleries, family privacy, right-gallery cupboard, pantry fridge, wall-backed beds/two bedside lamps and front-lawn lift directly ahead of the internal stair's full-floor front landing. **No external covered stair link or extra side strip.** Preserve equal recreation, clean laundry/drying, garden and required escape access; allow necessary basement/roof footprint and core alignment without reverting their functional arrangement.
10. Size the basement from its functions, not a 70-80% plot rule. Account for ramp/openings, potential garden-over-basement constraints, soil/groundwater and tree viability as unresolved review items.
11. Latest refinement: 4 ft ground galleries, explicit 3 ft private master-entry exception, bedroom-to-dressing-to-bath access without public dressing access. Reclaim office width for Child 1's front suite; preserve equal child sleeping rooms, merge east/west galleries into one lounge and recess its shared WC beside stairs. Deduct WC from lounge net floor/area. Preserve Study 008 basement/roof/site functions and realign the front path.
12. Study 010 correction: use the approved 4 x 2 ft cupboard at House Gallery's terminal right end, facing left, outside living and without narrowing the 4 ft through-route. Reduce first common WC to 6 x 5.5 ft, reposition toilet/basin, check clear inside doorway/toilet-frontal space and deduct only its 33 sq ft footprint from lounge.

## Acceptance criteria

- Basement, ground, first and roof/site plans are dimensioned and readable.
- Layout data is separate from geometry generation and can be edited without modifying Blender scripts.
- Geometry validation results are reproducible and covered by tests.
- All unresolved site constraints are visible in the report.
- Approved furniture-led functions and flexible-space assignments are traceable; budget and professional-review risks remain visible.
- No detailed 3D shell work starts until the candidate layout has been reviewed.

## Report back

Include plan artifact paths, the room schedule actually used, validation results, unresolved choices and exact test commands/results. Do not move to M2 automatically.
