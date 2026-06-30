# Design and Prototypes

Use this for design-token references, component variant sheets, UI directions, motion
tuners, and clickable interaction flows.

## Match Existing Style First

If the repo has a design system, inspect it before inventing visuals:

- CSS variables, Tailwind config, theme files, token JSON, Storybook stories.
- Existing pages/components for density, typography, borders, spacing, and color.
- Brand assets if present.

When useful, create a durable `design-system-reference.html` with token swatches and type
specimens, then reuse its variables in future artifacts.

## Design Tokens Reference

Use when the user wants to understand or share a design system.

Layout:

- Color tokens as swatches with names and values.
- Type scale rendered at actual sizes.
- Spacing/radius/shadow specimens.
- Motion/easing tokens with tiny visual samples.
- Copy buttons for token names and values.

The artifact must reflect the real source of truth, not plausible invented tokens.

## Component Variant Sheet

Use for buttons, cards, inputs, alerts, navigation items, or any component with states.

Layout:

- One component per page.
- Matrix by size, intent, and state.
- Include hover/focus/disabled/loading/error/empty states.
- Show props or class names under each variant.
- Include notes for missing or inconsistent states.

Do not mix many components into one dense page unless the user asks for a catalog.

## Visual Direction Grid

Use for early UI direction decisions.

Layout:

- 4-6 mini mockups in a responsive grid.
- Each direction differs in layout, density, hierarchy, and interaction model.
- Captions name the tradeoff: dense ops console, calm single-task flow, editorial
  onboarding, compact mobile-first, etc.
- Optional full-width preview when a mockup is selected.

Avoid color-only variation. The user should be able to pick based on workflow and
information hierarchy.

## Motion or Parameter Prototype

Use when the user needs to feel an animation, tune timing, or explore parameters.

Layout:

- Large stage for the thing being tuned.
- Sliders/toggles/selects for meaningful parameters.
- Replay/reset control.
- Live code/config output plus a copy button.
- Optional presets to compare quickly.

For animation, include duration, delay, easing, distance, opacity/scale, and a small
easing curve if relevant.

## Clickable Flow

Use when sequence matters more than pixel perfection.

Layout:

- 3-6 screens or states.
- Real buttons for next/back/branching paths.
- Thumbnail tray or state list.
- Notes panel for assumptions and open questions.
- Export selected path or feedback if interactive.

Keep fidelity just high enough to test the flow. Do not build the product.

## Common Mistakes

- Defaulting to purple gradients, glass effects, or generic SaaS cards.
- Making a static screenshot of something HTML can render.
- Omitting weird states like loading, error, and empty.
- Prototyping an animation without a way to copy the resulting values.
- Ignoring the product's existing density and style.
