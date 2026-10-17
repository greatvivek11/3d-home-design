# Codex Task M3 — Materials, Furniture and Rendering

Implement M3 after the architectural shell is dimensionally consistent.

## Read first

Read the house specification, room schedule, reviewed layout, Blender generation code and docs/architecture.md.

## Goal

Create the complete finished warm, nature-connected modern minimalist visualization while preserving architectural readability and furniture/equipment clearances. This is not a budget-validated construction proposal.

## Style direction

- Warm white and light neutral walls.
- Light oak or similar restrained wood accents.
- Pale stone and understated charcoal details.
- Daylight-led lighting with supplementary warm interior lights.
- Clean silhouettes and uncluttered rooms, without excessive decorative elements.

## Requirements

1. Create reusable materials and lighting helpers with names and documented parameters.
2. Add furniture and fixtures using parametric objects or assets with suitable licenses. Prefer simple generated placeholders while getting placement correct; do not download assets with unclear licensing.
3. Keep object placement data-driven and separate from core wall geometry.
4. Check furniture bounds against room bounds and flag obvious blocked passages or door swings.
5. Create useful saved cameras for front/back gardens, exterior/verandas, living/dining, kitchen, master/children's rooms, office, basement recreation/parking, balconies/roof and cutaway/dollhouse views.
6. Use Eevee for quick previews and Cycles for higher-quality stills when supported by the installed Blender version.
7. Make render resolution, samples and output paths configurable. Use repeatable commands and keep generated renders outside tracked source unless explicitly chosen for documentation.
8. Ensure the roof and selected walls can be hidden for interior/cutaway rendering.
9. Avoid implying physically accurate daylight simulation or construction suitability from the visual render alone.
10. Furnish all five bedrooms including upstairs, separate office with workstation/shared table/piano, eight-seat dining, mandatory kitchen island, gym/gaming and outdoor/roof seating. Real-world furnishing deferral does not reduce visualization scope.
11. Render large glazing with appropriate shading/privacy intent, screens and guarding. Keep pool/fall safety and occupied basement separation legible; do not portray these as professionally verified.

## Acceptance criteria

- Repeated runs create consistent materials, object names and camera setups.
- At least one exterior, one interior and one cutaway preview render are generated when Blender is available.
- Furniture scale and clearances are reviewed and obvious collisions are reported.
- Performance-sensitive settings are configurable for local hardware.

## Report back

List render paths, settings, any external assets and their licenses, and checks performed. Do not move to M4 automatically.
