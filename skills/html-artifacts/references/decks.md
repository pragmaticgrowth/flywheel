# Decks

Use this when the user asks for slides, a deck, a presentation, or material meant to be
spoken through in a meeting.

## When a Deck Fits

Make a deck when:

- The user explicitly asks for slides/deck/presentation.
- The content has 5-20 clear beats.
- Someone will present it live.
- Visual hierarchy matters more than dense reference detail.

Use a report/explainer instead when the reader will study the material alone.

## Required Behavior

- One slide per `<section>`.
- Full-viewport presentation mode, not a long scrolling page.
- Left/right arrows and space to navigate.
- Slide counter.
- Fullscreen control or `f` shortcut.
- Responsive 16:9 layout with sensible letterboxing.

Optional:

- Thumbnail overview.
- Presenter notes toggle.
- Print mode that lays slides vertically for PDF export.

## Slide Rules

- One idea per slide.
- Large type. If it reads like a paragraph, split it.
- Use varied slide shapes: title, quote, chart, code, diagram, comparison.
- Avoid decorative transitions.
- Include speaker notes only when they help the presenter.

## Minimal JS Pattern

```html
<script>
const slides = [...document.querySelectorAll(".slide")];
let index = 0;
function show(next) {
  index = Math.max(0, Math.min(slides.length - 1, next));
  slides.forEach((slide, i) => slide.classList.toggle("active", i === index));
  document.querySelector("[data-slide-index]").textContent = String(index + 1);
  document.querySelector("[data-slide-count]").textContent = String(slides.length);
}
document.addEventListener("keydown", (event) => {
  if (event.key === "ArrowRight" || event.key === " ") show(index + 1);
  if (event.key === "ArrowLeft") show(index - 1);
  if (event.key.toLowerCase() === "f") document.documentElement.requestFullscreen?.();
});
show(0);
</script>
```

## Common Mistakes

- Turning each slide into a markdown card.
- Too many bullets.
- Same layout on every slide.
- Missing keyboard navigation.
- Missing print/PDF fallback.
