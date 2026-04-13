# Acceptance checklist (locked in phase 1)

> Evaluate a candidate CSS artifact (`tracks/prompt-*/rNN.css`) against this list.

## Visual system

- [x] Candidate defines `:root` with at least 12 design tokens (`--*`).
- [x] Candidate includes layered background treatment (gradient + grid/pattern overlay).
- [x] Candidate includes `:focus-visible` styling for accessible keyboard focus.

## Core layout and components

- [x] Candidate styles `.workspace`, `.panel`, and `#map`.
- [x] Candidate styles `.kpi-grid`, `.scenario-card`, and `.alerts`.
- [x] Candidate styles `.chat-fab`, `.chat-panel`, and `.msg.user` / `.msg.assistant`.

## Motion and responsiveness

- [x] Candidate includes at least 2 `@keyframes` animations.
- [x] Candidate includes responsive rules for both `@media (max-width: 1280px)` and `@media (max-width: 700px)`.

## Functional safety

- [x] `templates/index.html` still contains IDs: `modelForm`, `map`, `summaryCards`, `tableWrap`, `timelineSteps`, `chatPanel`.
