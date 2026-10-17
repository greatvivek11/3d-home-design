# Codex Task M0 — Foundation and Environment

Implement the foundation milestone for this project. Work from the repository root.

## Read first

- README.md
- house-spec/house.json
- docs/architecture.md
- docs/design-decisions.md
- docs/validation-rules.md
- docs/implementation-plan.md

## Goals

Establish a reproducible Python + Blender workflow before attempting to solve the house layout or create detailed visuals.

## Requirements

1. Inspect macOS, Git, Python, Blender, Node.js and npm versions before installing or upgrading anything. Do not install packages unless the implementation needs them.
2. Review the existing repository and preserve working files. Propose a short plan before editing.
3. Create a maintainable Python project structure, for example src/dream_home/, scripts/ and tests/. Keep the implementation as simple as practical.
4. Load and validate house-spec/house.json version 2. Distinguish user-approved requirements from illustrative assumptions, unapproved candidate dimensions and intentionally unresolved nulls. A valid brief is not necessarily ready to generate geometry.
5. Treat linear JSON dimensions as feet at the geometry boundary and convert to metres exactly once. Convert explicit square-foot areas using squared units; do not convert money, counts or fractions as lengths.
6. Add tests for specified positive/finite dimensions, allowed unresolved nulls, required fields, unique IDs, valid room/bathroom references, five-bedroom distribution and unit conversions. Required flexible office/laundry floor assignment belongs to later candidate layout data. Use the standard library unless a dependency offers clear value.
7. Add a Blender smoke-test/generation script that creates a minimal, clearly labeled scene and saves an editable .blend file when Blender is installed.
8. Add documented commands for configuration validation, tests and Blender generation. Support Blender background mode where practical.
9. If Blender is unavailable, do not claim the scene was generated. Document the blocker and keep non-Blender tests runnable.
10. Ensure generated outputs and caches are not accidentally committed. Keep last-known-good artifacts safe when generation fails.
11. The earlier temporary Blender 5.2.2 LTS probe verified headless bpy, JSON access, save/reopen and GLB export only. Do not report M0 or rendering complete until reusable scripts, tests and the required artifacts are verified.

## Acceptance criteria

- Fresh-checkout setup steps are documented.
- Configuration and unit tests pass.
- A Blender scene is successfully generated, or a precise environment blocker is reported.
- No detailed floor-plan solver or web frontend is added in this milestone.
- No site orientation, setbacks, buildable envelope or code compliance is invented.

## Report back

Summarize files changed, exact commands run and their exit status, generated artifacts, and remaining limitations. Do not move to M1 automatically.
