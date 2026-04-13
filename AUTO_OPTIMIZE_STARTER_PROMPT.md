# Auto-Optimize + Codex Starter

Use this message at the start of a task:

```text
Enable Auto-Optimize Skill for this task.
Follow SKILL.md, program.md, docs/verifiability.md,
docs/phase-01-spec.md to docs/phase-04-output.md, and docs/execution.md strictly.
Do not skip phases or gates unless I explicitly say in THIS message:
"This task waives the Skill / skips phases".
Start from phase 1 and write tracks/phase-01-acceptance.md first.
Then continue through phase 2, phase 3, and phase 4.
Before final delivery in class-A environment, run:
FINAL_TRACK_FILE=<winning track file> DELIVERY_FILE=<delivery file> bash scripts/skill-verify.sh
```

## Daily quick flow

1. Send the starter message above.
2. Confirm Codex created:
   - `tracks/phase-01-acceptance.md`
   - `tracks/phase-02-consistency-check.md`
   - `tracks/prompt-*/r01.*`, `r02.*` ...
3. Ask Codex to report acceptance checklist status before shipping.
4. Ask Codex to run `scripts/skill-verify.sh` before final handoff.

## Optional waiver

Only when you really need speed, add this line in your task message:

```text
This task waives the Skill / skips phases.
```

Without that exact intent in the current message, full workflow stays on.
