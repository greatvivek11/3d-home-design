# Codex Task M1 — Floor-Plan Layout and Feasibility

Implement M1 after M0 has a working configuration loader and tests. Do not generate detailed furniture or photorealistic materials yet.

## Read first

Read house-spec/house.json, docs/room-schedule.md, docs/validation-rules.md, docs/design-decisions.md and docs/tasks/00-foundation.md.

## Goal

Create editable, dimensioned 2D layout studies for both floors and a clear report explaining whether the provisional requirements fit together.

## Site and coordinate rules

- Plot target is 30 ft × 50 ft, still unconfirmed.
- Use a local plotting coordinate convention (for example, X across the plot width and Y along its depth). Treat the front edge as a drawing convention only; it does not establish compass direction or road orientation.
- Setbacks, road width, city/jurisdiction and buildable envelope are unresolved. Do not present the whole plot as the legally buildable envelope.
- If creating a maximal illustrative study using the entire plot rectangle, label it clearly as a visual feasibility study, not a permit-ready or code-compliant design.
- Use metres internally. Show labels and dimensions in feet for review where helpful.

## Requirements

1. Define a layout data structure with explicit room rectangles, room IDs, floor IDs, doors, windows, stairs and required circulation paths.
2. Keep target dimensions from house-spec/house.json separate from actual candidate layout dimensions. If a room cannot fit its target, report the conflict instead of silently resizing it.
3. Generate readable dimensioned 2D plan outputs for both floors. SVG is an acceptable first output because it can be generated without a graphics dependency; PNG is optional.
4. Show plot bounds, candidate envelope status, room labels, target/actual sizes, dimension strings, doors, windows, stairs and parking target.
5. Implement geometry checks for invalid or non-finite dimensions, room overlap beyond a documented tolerance, out-of-bounds placements, missing/invalid host walls for openings, parking/access conflicts and basic floor-to-floor stair connectivity.
6. Distinguish PASS, FAIL and NEEDS REVIEW. An unresolved setback or jurisdiction should produce NEEDS REVIEW and block claims of regulatory compliance.
7. Add tests for positive cases and intentionally invalid cases.
8. Produce a candidate layout and report, but do not describe it as approved. Where the four-bedroom target does not fit plausibly, show the conflict and propose explicit alternatives for review.

## Acceptance criteria

- Both floor plans are dimensioned and readable.
- Layout data is separate from geometry generation and can be edited without modifying Blender scripts.
- Geometry validation results are reproducible and covered by tests.
- All unresolved site constraints are visible in the report.
- No detailed 3D shell work starts until the candidate layout has been reviewed.

## Report back

Include plan artifact paths, the room schedule actually used, validation results, unresolved choices and exact test commands/results. Do not move to M2 automatically.
