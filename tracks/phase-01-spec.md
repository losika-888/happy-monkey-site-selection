# Phase 1 spec (Happy Monkey UI redesign)

## Task goal
Ignore previous visual attempts and redesign the Happy Monkey web interface with a new visual system while keeping existing product behavior and JavaScript bindings intact.

## Feature list
1. Preserve all functional IDs/classes required by `static/app.js`.
2. Deliver a fresh visual direction (tokens, atmosphere background, expressive typography).
3. Keep three-panel analytical workspace readability and map-first hierarchy.
4. Include meaningful motion (entry/state feedback) without over-animation.
5. Ensure responsive behavior on desktop and mobile.
6. Keep chat panel, KPI cards, scenario cards, and tables visually consistent with the new system.

## Tech stack
- Flask template: `templates/index.html`
- Frontend style: `static/style.css`

## Output shape
- Final delivery file: `static/style.css`
- Supporting phase artifacts under `tracks/`

## Quality bar
- New design is visibly different from prior version.
- No JS hook IDs are removed.
- Mobile layout remains usable.
- Final delivery provenance is machine-verifiable against selected track artifact.
