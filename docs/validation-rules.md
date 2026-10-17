# Validation Rules

Validation must distinguish PASS, FAIL and NEEDS REVIEW. A passing geometry test is not evidence of building-code or structural compliance.

## Specification checks

- Required fields exist and have the correct types.
- Dimensions are finite positive numbers.
- Unit system is explicit; conversion from feet to metres happens once at input.
- IDs are unique within their defined scope.
- Setbacks, orientation and jurisdiction may remain unresolved, but unresolved site constraints must block any claim that the layout fits the legally buildable envelope.

## Layout geometry checks

- Every room rectangle has positive width/depth and lies inside the candidate envelope.
- Rooms intended to be separate must not overlap beyond a documented tolerance.
- Shared boundaries and wall centerlines/thicknesses are consistent.
- Doors and windows lie on a valid host wall and fit within its span and height.
- Stair openings, landings and travel paths connect the floors without geometric contradictions.
- Required paths from entrance to common spaces and stairs remain clear in the model.
- Parking target rectangle does not intersect required access/circulation.
- Geometry outside the plot or approved candidate envelope is reported.
- Floor levels and vertical openings align across floors.

## 3D checks

- Mesh dimensions and floor elevations are consistent with the specification.
- Openings are actually represented in wall geometry, not merely drawn over solid walls.
- Object names/collections are stable and unique.
- No non-finite coordinates or unintended degenerate geometry.
- GLB export completes, references available textures and can be loaded by a test viewer.

## Limitations

Automated checks are geometric heuristics. They do not verify structural adequacy, fire safety, egress compliance, accessibility, local code compliance, ventilation adequacy or construction feasibility. Flag these for review by a qualified architect/engineer and local authority as applicable.
