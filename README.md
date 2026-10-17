# Dream Home — Blender + Python

A code-driven two-storey modern minimalist home design project. The first goal is a dimensionally consistent, editable Blender model with a reproducible Python pipeline, followed by a browser-based first-person walkthrough.

## Current status

**Concept stage.** Plot dimensions and room targets are provisional. This repository does not contain an approved architectural plan and does not establish structural or building-code compliance.

## Initial brief

- Property: independent house
- Plot target: 30 ft × 50 ft (1,500 sq ft gross site area), not yet confirmed
- Floors: ground + first
- Style: modern minimalist
- Parking: one car
- Target: four bedrooms, subject to spatial feasibility
- Primary goal: visualization and design exploration
- Web goal: React + TypeScript + Vite + React Three Fiber/Drei, using a GLB exported from Blender and hosted on Vercel

## Planned workflow

1. Validate the design specification and unresolved site constraints.
2. Generate dimensioned 2D floor-plan studies.
3. Review and revise the layout before detailed modeling.
4. Generate the architectural shell in Blender using Python (bpy).
5. Add furniture, materials and lighting; create repeatable renders.
6. Export an optimized .glb model.
7. Build the first-person viewer and deploy through GitHub + Vercel.

## Repository map

- house-spec/house.json — provisional source-of-truth design brief
- docs/architecture.md — technical architecture and data flow
- docs/design-decisions.md — confirmed decisions and open questions
- docs/validation-rules.md — geometry checks and boundaries of validation
- docs/implementation-plan.md — milestones and acceptance criteria
- docs/room-schedule.md — initial room targets, not a fitted plan
- docs/tasks/README.md — canonical task index and execution order
- docs/tasks/ — copy-ready Codex prompts for milestones M0–M5

## Important caveats

A 30 × 50 ft plot does not imply that the entire site can be built upon. Plot orientation, road width, jurisdiction, setbacks, coverage/FAR limits, height, parking/access, ventilation and easements must be confirmed. A qualified local architect and relevant professionals must verify plans for a real build.

## Next step

Open this repository in Codex and start with docs/tasks/README.md, then execute docs/tasks/00-foundation.md. Work one milestone at a time: validate the inputs, review the floor plans, build the Blender shell, add visualization, implement the walkthrough, then deploy.
