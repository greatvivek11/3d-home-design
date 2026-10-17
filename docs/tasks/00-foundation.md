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
4. Load and validate house-spec/house.json. Report missing values and distinguish invalid input from intentionally unresolved site information.
5. Treat JSON dimensions as feet at the input boundary. Convert to internal metres exactly once, with explicit unit-aware helpers and tests.
6. Add tests for positive/finite dimensions, required fields, unique IDs and feet-to-metres conversions. Use the standard library unless a dependency offers clear value.
7. Add a Blender smoke-test/generation script that creates a minimal, clearly labeled scene and saves an editable .blend file when Blender is installed.
8. Add documented commands for configuration validation, tests and Blender generation. Support Blender background mode where practical.
9. If Blender is unavailable, do not claim the scene was generated. Document the blocker and keep non-Blender tests runnable.
10. Ensure generated outputs and caches are not accidentally committed. Keep last-known-good artifacts safe when generation fails.

## Acceptance criteria

- Fresh-checkout setup steps are documented.
- Configuration and unit tests pass.
- A Blender scene is successfully generated, or a precise environment blocker is reported.
- No detailed floor-plan solver or web frontend is added in this milestone.
- No site orientation, setbacks, buildable envelope or code compliance is invented.

## Report back

Summarize files changed, exact commands run and their exit status, generated artifacts, and remaining limitations. Do not move to M1 automatically.
