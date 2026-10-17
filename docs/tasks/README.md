# Codex Tasks — Dream Home

This folder contains the canonical, copy-ready prompts for implementing Dream Home with Codex. Run one task at a time from the repository root, review the generated artifacts, and only then move to the next milestone.

## Milestone order

| Order | Prompt | Deliverable |
|---|---|---|
| M0 | [Foundation and environment](00-foundation.md) | Reproducible setup, config validation, minimal Blender smoke test |
| M1 | [Floor-plan layout](01-floorplan-layout.md) | Dimensioned concept layouts and feasibility report |
| M2 | [Blender architectural shell](02-blender-architecture.md) | Editable two-storey architectural model |
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

- The current brief is a concept for an independent two-storey modern minimalist home on a provisional 30 ft × 50 ft plot, with one-car parking and an initial four-bedroom target.
- The plot dimensions and room dimensions have not been confirmed. Plot orientation, road width, jurisdiction, setbacks and legally buildable envelope remain unresolved.
- Never invent setbacks or claim regulatory, structural or construction compliance.
- Do not silently shrink required rooms, overlap geometry, or claim the room schedule fits until the candidate layout has been tested.
- Use metres internally in geometry code; convert from feet once at the configuration boundary.
- Keep Blender as the editable authoring source and export GLB for the web viewer.
- Keep scope lean: no backend, database, account system or unnecessary infrastructure for the initial static portfolio experience.
- Do not commit secrets, caches, temporary renders or large generated files without a deliberate asset-storage decision.

## Dependencies

M1 depends on M0. M2 depends on a reviewed M1 layout. M3 depends on the M2 shell. M4 can begin only after there is a stable GLB export contract (a minimal mock asset may be used for UI scaffolding). M5 follows a successful local web build.

The prompts define acceptance criteria, not a guarantee of completion. Codex must report when an environment limitation or unresolved design input blocks a step.
