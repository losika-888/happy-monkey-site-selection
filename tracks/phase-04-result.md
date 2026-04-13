# Phase 4 compare & output

## Pre-compare checks

- Every scheme finished inner loop: yes (`r01`, `r02` for all prompt tracks)
- `tracks/phase-01-acceptance.md` exists: yes
- At least one track fully checked: yes (all three are fully checked)
- Scheme scope consistency retained from phase 2: yes

## Prompt optimization analysis

Best scheme: prompt-b
Dimension: information architecture emphasis
Best score: 8.3/10
Worst scheme: prompt-a and prompt-c (tie)
Worst score: 8.1/10

Why best beats original:
- Stronger operational hierarchy around map-as-command-center.
- Better state scanning due to secondary pulse motion on status + active stage.
- Clearer token contrast for KPI/table readability.

Suggestions:
- Keep decision-first wording for future dashboard tasks.
- Keep motion requests constrained to state guidance, not decorative loops.

## Optimization result

Final score: 8.3/10 (baseline 6.8/10, +1.5)
Delivery source: tracks/prompt-b/r02.css
Consistency note (class A): byte match verified via `cmp` and `shasum -a 256`.

Best Prompt:
Run this task under Auto-Optimize with strict compliance.
You must obey SKILL.md, program.md, docs/verifiability.md,
docs/phase-01-spec.md through docs/phase-04-output.md, and docs/execution.md.
No skipped phases, no skipped gates, unless this exact waiver appears in this current message:
"This task waives the Skill / skips phases".
Execute in order: phase 1 (create tracks/phase-01-acceptance.md), then phase 2, phase 3, and phase 4.
Before final handoff in class-A, run:
FINAL_TRACK_FILE=<winning track file> DELIVERY_FILE=<delivery file> bash scripts/skill-verify.sh
Output must include a "Daily quick flow" with 4 numbered steps and an "Optional waiver" section.

Final artifact:
`static/style.css` copied verbatim from `tracks/prompt-b/r02.css`.
