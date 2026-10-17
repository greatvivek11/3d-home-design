# Technical Architecture

## Guiding principle

Keep the house specification independent of Blender. The JSON design brief becomes the source of truth for dimensions and requirements. A Python pipeline validates the brief, computes geometry, creates the Blender scene and exports web assets.

## Data flow

1. house-spec/house.json defines plot inputs, room targets, floor levels, materials and web intentions.
2. Python loads the JSON, converts input feet to internal metres once at the boundary, validates schema and reports unresolved site inputs.
3. Layout logic proposes explicit room rectangles, walls, openings and circulation. It must not silently change required dimensions to make a plan fit.
4. Geometry checks run before 3D generation: envelope bounds, overlaps, host-wall relationships and connectivity.
5. Blender's bpy API generates an editable .blend scene with stable object names and meaningful collections.
6. Blender renders preview images and exports an optimized .glb asset.
7. A future web/ app uses React, TypeScript, Vite, Three.js through React Three Fiber and Drei to load the GLB.
8. The static frontend can be deployed via Vercel from GitHub; no backend is needed for the initial viewer.

## Blender organization

Use collections or stable naming prefixes for floors, rooms, walls, slabs, doors, windows, stairs, roof, furniture and lighting. Room/floor identity must survive export sufficiently for visibility toggles and navigation. Use metres inside geometry code and convert for presentation only.

## Rendering vs real-time web

Blender is the authoring source. Use Eevee for quick iteration and Cycles for final still renders. Do not assume Blender lighting/shader settings transfer identically to the browser. For the web, use compatible materials, conservative texture sizes, optimized geometry and a loading state.

## First-person walkthrough

The browser app owns interaction: camera control, keyboard/pointer input, collision checks, room/floor controls and UI. GLB is a model delivery format, not a walkthrough engine. Collision geometry can be simpler than visual geometry.

## Initial non-goals

No backend, database, user accounts, generative AI runtime, structural analysis or construction-document production is needed for the initial visualization project.
