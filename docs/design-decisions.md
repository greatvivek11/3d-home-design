# Design Decisions and Open Questions

## Decisions so far

- Two floors: ground + first.
- Independent house on a provisional 30 ft × 50 ft plot.
- Modern minimalist aesthetic: warm white, light oak, light stone and charcoal accents.
- One-car parking target.
- Initial family-home concept with four bedrooms, subject to feasibility.
- Blender + Python is the modeling and authoring stack.
- GLB is the browser-delivery format.
- Future viewer: React + TypeScript + Vite + React Three Fiber + Drei.
- GitHub is the source repository and Vercel is the intended static deployment target.
- Visualization and iteration are the primary goal, not construction documentation.

## Unresolved site inputs

Do not assume values for any of the following:

- Actual surveyed width/depth and plot boundaries.
- Road-facing side, north direction, road width and approach/access.
- City, local jurisdiction and applicable regulations.
- Required setbacks, permitted coverage/FAR, height/storey restrictions and parking requirements.
- Easements, party-wall rules, adjacent buildings, drainage or utilities.
- Climate, preferred daylight orientation, privacy and ventilation constraints.

## Layout questions

- Confirm whether four bedrooms are required or a flexible office/guest room is acceptable.
- Decide preferred ground-floor bedroom use and bathroom access.
- Confirm whether an ensuite, balcony, utility yard, prayer/quiet room or home office is desired.
- Confirm car dimensions and whether two-wheeler/bicycle storage is needed.
- Review room-size targets once the buildable envelope is known.

## Rule

A provisional target is not a constraint if it makes a feasible design impossible, but the generator must report the conflict and ask for a decision. Do not silently shrink rooms, overlap spaces or invent regulatory values.
