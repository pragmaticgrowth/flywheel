# Foundation

Read this before writing any artifact.

## File Shape

- Write a real `.html` file. Do not paste a fenced HTML block as the deliverable.
- Keep it self-contained: `<style>` and `<script>` in the file; no build step.
- Avoid required network dependencies. If a font or CDN library is useful, the artifact
  must still degrade to a readable page when offline.
- Include `<meta name="viewport" content="width=device-width, initial-scale=1">`.
- Put the artifact in a sensible location:
  - Durable docs: `docs/artifacts/<topic>.html` or the repo's existing docs folder.
  - PR/review attachment: `docs/artifacts/<pr-or-branch>-review.html`.
  - Throwaway editor with sensitive data: temp or gitignored path.

## Structure

Use this skeleton unless a reference gives a better one:

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Artifact title</title>
  <style>
    :root {
      --bg: #f8f7f3;
      --surface: #ffffff;
      --ink: #171717;
      --muted: #62615c;
      --rule: #dedbd2;
      --accent: #2563eb;
      --ok: #15803d;
      --warn: #b45309;
      --danger: #b91c1c;
      --sans: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      --serif: ui-serif, Georgia, "Times New Roman", serif;
      --mono: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    }
    @media (prefers-color-scheme: dark) {
      :root { --bg:#101114; --surface:#181a20; --ink:#f4f4f5; --muted:#a4a4aa; --rule:#2d3038; }
    }
    * { box-sizing: border-box; }
    body { margin: 0; background: var(--bg); color: var(--ink); font: 16px/1.55 var(--sans); }
    main { max-width: 1180px; margin: 0 auto; padding: 32px 20px 48px; }
    h1, h2, h3 { line-height: 1.15; margin: 0; }
    p { color: var(--muted); }
    code, pre { font-family: var(--mono); }
    table { width: 100%; border-collapse: collapse; }
    th, td { border-bottom: 1px solid var(--rule); padding: 10px 12px; text-align: left; vertical-align: top; }
    button, a { touch-action: manipulation; }
    :focus-visible { outline: 3px solid color-mix(in srgb, var(--accent) 45%, transparent); outline-offset: 2px; }
    @media print {
      body { background: white; color: black; }
      button, .no-print { display: none !important; }
    }
  </style>
</head>
<body>
  <main>
    <header>
      <h1>Artifact title</h1>
      <p>One short sentence explaining what this page is for.</p>
    </header>
  </main>
  <script>
    // JS only when the artifact needs interaction.
  </script>
</body>
</html>
```

Use the baseline as a starting point, not a visual identity. Match the target product or
document style when the repo gives you tokens.

## DOM and Security

- Use semantic HTML: tables for tabular data, lists for lists, forms for controls.
- Build dynamic DOM with `document.createElement`, `textContent`, and `append`.
- Never set `innerHTML` from user input, file content, fetched data, generated data, or
  variables. Static literal markup is acceptable only when no variable is interpolated.
- Do not embed API keys, tokens, passwords, private keys, `.env` values, DSNs, or connection
  strings. Mask to a stable reference like `{{SECRET:STRIPE_API_KEY}}`.
- For secret-shaped inputs, export only key names, masked previews, and intended actions.

Secret-shaped values include:

- Key names containing `key`, `secret`, `token`, `passw`, `credential`, `private`,
  `auth`, `dsn`, or `connection_string`.
- Common prefixes: `AKIA`, `ghp_`, `gho_`, `sk-`, `xox`, `AIza`, JWT-looking `eyJ`.
- PEM private key blocks.
- URLs with `user:password@host`.
- High-entropy strings in config/env-shaped sources.

## Export and Copy

Any artifact with user-manipulated state must include one primary Export or Copy button.
The export is the persistence layer and the handoff back to the agent.

Use a small local helper like this:

```html
<script>
async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    const area = document.createElement("textarea");
    area.value = text;
    area.setAttribute("readonly", "");
    area.style.position = "fixed";
    area.style.left = "-9999px";
    document.body.appendChild(area);
    area.select();
    const ok = document.execCommand("copy");
    area.remove();
    return ok;
  }
}

async function exportPayload(kind, data) {
  const payload = { skill: "html-artifacts", kind, data, version: 1 };
  const ok = await copyText(JSON.stringify(payload, null, 2));
  document.querySelector("[data-export-status]").textContent =
    ok ? "Copied. Paste it back into the agent." : "Copy failed. Select the JSON and copy manually.";
}
</script>
```

Do not add a server, local listener, webhook, MCP bridge, or background process. This
Flywheel skill stays skills-only.

## Visual Quality

- Let color carry meaning: status, severity, category, or axis.
- Avoid default AI decoration: gradient hero, glass blur, emoji headings, and a grid of
  identical cards.
- Use stable dimensions for dense UI surfaces so text and controls do not shift layout.
- Use restrained radii. Artifact cards can be 6-8px; diagrams and tools can be sharper.
- Keep readable line length: 60-75ch for prose; dense tools may use wider layouts.
- Make controls keyboard reachable and visible on focus.
- Do not communicate status by color alone. Pair color with text, icon, shape, or label.

## SVG Rules

- Use inline `<svg>` with a `viewBox`.
- Prefer `<g>` groups with labels/classes so the diagram can be edited.
- Use `<title>` or surrounding captions for accessibility.
- Plain SVG `<text>` does not wrap. For long labels, use `<foreignObject>` with an HTML
  `<div>`, or size the box from the label length.
- Put a small background rectangle behind edge labels that cross lines.

## Final Response

After writing the artifact, tell the user:

- The path to the file.
- Whether it is durable or throwaway.
- What the export button returns, if the artifact is interactive.

Keep the response short; the artifact is the deliverable.
