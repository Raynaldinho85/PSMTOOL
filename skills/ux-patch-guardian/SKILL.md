---
name: ux-patch-guardian
description: Professional web design and UX patch-review skill for modern web apps. Use when a task involves frontend/UI changes, interaction design, layout polish, accessibility, responsive behavior, design consistency, or when the user asks for a strict UX/UI review before merge.
---

# UX Patch Guardian

Review and improve frontend patches to a production-ready UX/UI standard with deterministic checks.

## Review Mode

Run this workflow whenever a patch touches UI-facing files (`ui/`, `pages/`, components, CSS, templates, charts, forms, or exports that present visuals).

1. Identify UI impact
- Inspect the patch and list all user-visible changes.
- If no user-visible impact exists, state `No UI impact detected` and stop.

2. Run the quality gate
- Evaluate each changed surface against the checklist below.
- Record findings by severity: `critical`, `major`, `minor`.
- Prioritize behavior regressions and usability breaks before visual polish.

3. Fix with small diffs
- Apply targeted edits to resolve critical/major issues first.
- Keep structure and design language of the existing product unless user requests redesign.
- Avoid unrelated refactors.

4. Validate
- Run relevant tests/lint/smoke checks.
- Confirm responsive behavior for mobile and desktop where applicable.

5. Report
- Return findings first (ordered by severity with file references), then a short change summary.
- If no findings remain, state that explicitly.

## UX/UI Checklist

Use this checklist as a hard gate for every UI patch:

- Information hierarchy: clear visual priority, scannable sections, sensible grouping.
- Readability: typography scale, line length, spacing rhythm, contrast.
- Accessibility: keyboard reachability, visible focus, labels, meaningful alt/aria, color contrast.
- Interaction clarity: control affordance, disabled/loading/error/success states.
- Feedback: actionable validation and error messages, no dead-end flows.
- Responsiveness: layout stability and readability on narrow screens.
- Data visualization clarity: axis labels, units, legends, annotations, not misleading scales.
- Consistency: terms, button styles, spacing, component behavior.
- Performance perception: avoid unnecessary re-renders/heavy effects; keep interactions snappy.
- Privacy/safety UI: no accidental sensitive-data display or persistence hints.

## Heuristic Standards

Apply these standards consistently:

- Prefer simple, obvious user flows over clever complexity.
- Reduce clicks and cognitive load where possible.
- Keep copy concrete and task-focused.
- Use whitespace intentionally; avoid crowded layouts.
- Ensure primary actions are visually dominant.
- Keep dangerous/destructive actions explicit and confirmable.

## Output Format

When reporting a review, use this deterministic structure:

1. Findings
- `Severity` - `Issue` - `Impact` - `Fix`
- Include file references for each issue.

2. Applied Fixes
- List implemented UX/UI fixes with file references.

3. Residual Risks
- Mention any remaining gaps (e.g., no browser smoke test available).

## Patch Guardrails

- Do not add new UI frameworks or heavy dependencies unless required.
- Preserve established design systems in existing products.
- For greenfield UI tasks, choose an intentional visual direction (not boilerplate defaults).
- Keep accessibility and responsiveness as non-optional acceptance criteria.

