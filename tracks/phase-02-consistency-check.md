# Phase 2: outer schemes for UI redesign

## Scheme prompts

### prompt-a — Aurora Atlas
Dimension: visual language (soft neon atlas)

```text
Redesign the Happy Monkey interface with an Aurora Atlas visual system.
Keep all current functionality and JS hooks intact.
Use expressive typography, bright cartographic gradients, and glass-like analytical panels.
Preserve three-column workspace hierarchy, map prominence, KPI/scenario/table readability, and chat usability.
Apply meaningful but restrained motion and strong keyboard focus styles.
Ensure responsive behavior for desktop and mobile.
Deliver by updating templates/index.html and static/style.css.
```

### prompt-b — Metro Blueprint
Dimension: information architecture emphasis (ops dashboard clarity)

```text
Redesign the Happy Monkey interface as a Metro Blueprint operations dashboard.
Do not break existing app.js bindings or behavior.
Prioritize decision-making clarity: map as command center, side panels as control + intelligence rails.
Build a fresh tokenized visual system (colors, spacing, radii, shadows) and purposeful animation.
Keep KPI cards, scenario cards, alerts, table tabs, and chat panel visually cohesive.
Maintain accessible focus states and responsive layouts for desktop/mobile.
Implement in templates/index.html and static/style.css.
```

### prompt-c — Market Poster
Dimension: tone and style emphasis (editorial poster energy)

```text
Redesign Happy Monkey with a Market Poster aesthetic: bold editorial typography, vibrant accents, and layered background texture.
Retain all existing functionality and DOM ids required by static/app.js.
Maintain map-first hierarchy and clear analytical readability for controls, KPIs, scenario comparison, and chat.
Use CSS variables, restrained motion, and explicit focus-visible states.
Include robust responsive breakpoints for laptop/tablet/mobile.
Apply changes in templates/index.html and static/style.css.
```

## Scheme consistency check

Feature list: preserve JS hook ids and behavior; fresh visual system; map-first hierarchy; consistent KPI/scenario/table/chat styling; meaningful motion; responsive desktop/mobile support.
Stack: Flask template + CSS (`templates/index.html`, `static/style.css`).

Scheme 1 features: [same scope and output] -> match ✓
Scheme 2 features: [same scope and output] -> match ✓
Scheme 3 features: [same scope and output] -> match ✓

Result: pass

## Scheme-dimension table

| Scheme | Track dir | Phase-2 dimension | Note |
|---|---|---|---|
| prompt-a | `tracks/prompt-a/` | Visual language | Soft-neon cartographic direction |
| prompt-b | `tracks/prompt-b/` | Information architecture | Decision-first operations dashboard |
| prompt-c | `tracks/prompt-c/` | Tone & style | Editorial poster energy |
