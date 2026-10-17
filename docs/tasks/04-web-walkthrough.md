# Codex Task M4 — GLB Export and First-Person Web Walkthrough

Implement M4 after Blender can reliably export a representative house GLB. If the final model is not ready, create only a clearly labeled test asset for UI scaffolding and do not represent it as the finished home.

## Read first

Read docs/architecture.md, the house specification, export script, and the M0–M3 task files.

## Goal

Build a responsive static web experience where visitors can inspect the house in 3D and walk through its rooms.

## Technology

- React and TypeScript.
- Vite for development/build.
- Three.js through React Three Fiber, plus Drei helpers where useful.
- Choose mutually compatible current stable versions and document the choice.
- Add an additional physics/collision library only if it demonstrably simplifies collision-aware movement.

## Requirements

1. Load the exported GLB with clear loading, error and retry states.
2. Provide orbit/inspection mode, reset-camera control and visibility for site, basement, ground, first and roof. Roof terrace and removable roof/slab geometry must have clear semantics.
3. Provide a first-person mode with keyboard movement and pointer/mouse look on desktop; show usable on-screen controls or an appropriate fallback on touch devices.
4. Implement collision-aware movement using simplified collision geometry where practical. The camera must not pass through walls or modeled pool/fall boundaries. Test internal basement-to-roof stairs, garden/external basement access and balconies; visibility changes must not trap the camera or break navigation.
5. Use stable floor/room IDs or documented object naming from Blender for visibility toggles and room selection.
6. Handle resize, device pixel ratio and reduced graphics capability without excessive GPU cost.
7. Use sensible model scale, camera height, movement speed and eye-level orientation. Include a way to return to a known spawn point.
8. Keep the viewer static: no backend or database unless a clear requirement appears.
9. Add lint/typecheck/build scripts and run them. Add a small test for UI logic where practical.
10. Document GLB replacement and export steps so regenerated assets can be swapped without code rewrites.

## Acceptance criteria

- npm run build (or documented equivalent) succeeds.
- The model loads in the browser without uncaught errors.
- Orbit mode, floor/roof toggles and first-person navigation work.
- Obvious wall collision and stair connectivity cases are tested manually or automated where feasible.
- The UI identifies the project as a design visualization, not approved construction documentation.
- The complete furnished dream is shown, including upstairs, with no implied cost, safety or site-compliance certification.

## Report back

Give setup/run/build commands, controls, test results, asset size and known issues. Do not deploy publicly until M5.
