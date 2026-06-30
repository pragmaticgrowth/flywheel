# Custom Editors

Use this when the user needs to manipulate structured input and prose would be clumsy:
triage, reorder, bucket, annotate, tune, curate, select, or configure.

## Non-Negotiable

Every editor exports. Without export, the user's work is trapped in the artifact.

Export can be:

- JSON payload for the agent.
- Markdown summary.
- CSV for a spreadsheet.
- Patch/diff text.
- Prompt text for the next agent turn.

Prefer one primary export button. Add secondary formats only when the user needs them.

## Layout

- Work area dominates the page.
- Header explains the exact one-off task.
- Input data is prefilled. Do not make the user paste it again.
- Controls match the data: drag handles, toggles, segmented controls, sliders, selects,
  text inputs, tags.
- Live validation and counts are visible.
- Export bar stays visible or appears at the end.
- Reset button if the interaction has many actions.

## Patterns

### Triage Board

Columns such as Now / Next / Later / Cut. Cards carry title, ID, short rationale, and tags.
Drag between columns. Export markdown grouped by column plus changed order.

### Config or Feature Flag Editor

Group toggles by area. Show dependency warnings immediately. Export only changed keys and
intended environment. Mask secret-shaped values.

### Prompt Tuner

Template editor on one side, sample previews on the other. Highlight variables, show
character/token estimates, and export the chosen template plus sample results.

### Dataset Curator

Rows or cards with approve/reject/tag controls. Keyboard shortcuts matter. Export selected
ids and labels, not the whole dataset if it is large.

### Annotation Tool

Show the source text/diff/transcript and annotation controls. Export spans with offsets or
stable ids, labels, and notes.

### Parameter Playground

Sliders/toggles update a live preview and code/config output. Export the final parameters.

## Secrets

For config/env-like data:

- Mask values before writing HTML.
- Render secret fields read-only.
- Export references and intended action, not values.
- If the user needs to rotate a secret, export a rotation marker and collect the new value
  outside the artifact.

## Ergonomics

- Keyboard shortcuts for repetitive workflows.
- Visible focus states.
- Counters for each bucket/status.
- Undo if the editor invites many small changes.
- No login, backend, server, or persistent account model.

## Common Mistakes

- Building a generic app instead of a one-task tool.
- No export.
- Pretty board, slow workflow.
- Hiding validation until export.
- Storing data only in `localStorage`.
- Embedding secrets in source or payloads.
