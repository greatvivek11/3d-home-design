# Codex Tasks — Dream Home

This folder contains the canonical, copy-ready prompts for implementing Dream Home with Codex. Run one task at a time from the repository root, review the generated artifacts, and only then move to the next milestone.

## Milestone order

| Order | Prompt | Deliverable |
|---|---|---|
| M0 | [Foundation and environment](00-foundation.md) | Reproducible setup, config validation, minimal Blender smoke test |
| M1 | [Floor-plan layout](01-floorplan-layout.md) | Basement, ground, first, roof/site layouts and feasibility report |
| M2 | [Blender architectural shell](02-blender-architecture.md) | Editable basement + two-storey house, roof terrace and site shell |
| M3 | [Materials, furniture and rendering](03-visualization-rendering.md) | Consistent minimalist visualization and render outputs |
| M4 | [GLB and web walkthrough](04-web-walkthrough.md) | Browser-based interactive first-person viewer |
| M5 | [GitHub and Vercel deployment](05-deploy-portfolio.md) | Reproducible portfolio deployment |

## How to use

1. Open the repository root in Codex.
2. Open the relevant task prompt and paste it into Codex, or ask Codex to read that file and execute it.
3. Have Codex inspect the current repository before editing. It should preserve working code and modify the existing structure rather than duplicate it.
4. Ask Codex to run the available tests and commands, report exact results, and list unverified items.
5. Review the output and commit the milestone before moving forward.

## Project constraints every task must respect

- The user approved the requirements brief on 17 October 2026, not a site or floor plan. Read [design decisions](../design-decisions.md), [room schedule](../room-schedule.md) and [house specification](../../house-spec/house.json) before implementing.
- The complete warm, nature-connected minimalist visualization includes five bedrooms, a separate quiet office, three-SUV basement with gym/gaming/storage, gardens, covered verandas, pool, balconies and accessible roof terrace.
- Initial plot area target is 4,000-5,000 sq ft, flexible upward. Front/back yard targets of 20%/30% include associated access/ramp, not planting alone. No fixed site rectangle, room sizes or basement coverage are approved.
- Plot orientation, road width, jurisdiction, setbacks, basement permissions and legally buildable envelopes remain unresolved. Flat/standalone/front-road context is an illustrative assumption only.
- Never invent setbacks or claim regulatory, structural or construction compliance.
- Do not silently shrink required functions, overlap geometry, or claim the program fits until the candidate layout has been tested and reviewed. Budget aspirations are not verified costs.
- Keep approved requirements distinct from candidate dimensions. Preserve null unknowns in the brief; assign required flexible office/laundry spaces in separate layout data.
- Use metres internally; convert linear feet and square feet appropriately at the boundary, not INR, fractions or counts.
- Protect five bedrooms, gardens, basement parking and quality. Double height and premium finishes can be cut first; visualize upstairs fully even if future furnishing is phased.
- Flag basement flooding/exhaust, fuel/LPG/battery placement, structure, pool/fall safety and thermal performance for professional review, not certification by renders.
- Keep Blender as the editable authoring source and export GLB for the web viewer.
- Keep scope lean: no backend, database, account system or unnecessary infrastructure for the initial static portfolio experience.
- Do not commit secrets, caches, temporary renders or large generated files without a deliberate asset-storage decision.

## Dependencies

M1 depends on M0. M2 depends on a reviewed M1 layout. M3 depends on the M2 shell. M4 can begin only after there is a stable GLB export contract (a minimal mock asset may be used for UI scaffolding). M5 follows a successful local web build.

The prompts define acceptance criteria, not a guarantee of completion. Codex must report when an environment limitation or unresolved design input blocks a step.
