# Diagrams and Data Views

Use this for flowcharts, architecture maps, ERDs, timelines, roadmaps, inline SVG figure
sheets, and filterable data/log explorers.

## General SVG Diagram

Use for process, state machine, sequence, dependency graph, request flow, or concept map.

Layout:

- Inline SVG with `viewBox`.
- Caption and short prose explanation.
- Legend when color, line style, or shape carries meaning.
- Step numbers for sequences.
- Labels on edges, not only nodes.

Conventions:

- Rectangle: component/process.
- Cylinder: datastore.
- Diamond: decision.
- Pill/hexagon: queue/topic.
- Solid line: synchronous.
- Dashed line: async/event.
- Dotted line: optional/fallback.
- Red/danger: failure or blocker.

## Architecture Map

Use for services, deployment topology, ownership, integrations, or incident orientation.

Layout:

- Group by domain, trust boundary, region, or owner.
- Show ingress, service calls, queues, datastores, third parties, and observability path.
- Mark sync vs async edges.
- Highlight hot path and known fragile points.
- Include owner/runbook links if known.

Do not draw every service if it becomes unreadable. Use zoom levels: overview first,
then detail panels or subgraphs.

## ERD or Schema Explorer

Use when explaining database schema or migrations.

Layout:

- Tables as boxes with primary keys, foreign keys, and important columns.
- Cardinality labels on relationships.
- Highlight changed/new/deprecated tables for migrations.
- Include query examples or access patterns below.
- Optional filters for bounded domains in large schemas.

## Timeline, Roadmap, or Gantt

Use when time order matters.

Layout:

- Time axis with appropriate granularity.
- Lanes by team/workstream/system.
- Items as bars or cards sized by duration.
- Milestones and "today" marker when relevant.
- Dependencies as arrows.
- Mobile fallback as stacked cards in chronological order.

For incidents, use a vertical minute-by-minute timeline with log excerpts attached to the
event where they matter.

## Data Explorer

Use for logs, traces, search results, datasets, metrics, or tabular evidence.

Layout:

- Filter controls at the top or left.
- Table or list with sticky headers.
- Facets/counts for categories.
- Detail panel for selected row.
- Export filtered data as JSON/CSV/markdown.

Keep data in the file if it is small and non-sensitive. For large data, sample and state the
sampling boundary.

## Figure Sheet

Use for a set of diagrams/illustrations the user may copy into a doc or post.

Layout:

- Grid of figures with consistent line weight, palette, and typography.
- Each figure has a title, caption, and copy SVG button.
- Include usage notes like light/dark compatibility.

## Common Mistakes

- Using Mermaid when the layout needs manual control.
- Letting SVG text collide with shapes.
- Encoding status only with color.
- Creating diagrams too dense to read.
- Omitting a legend.
- Hiding important values in hover-only interactions.
