"""Read-only view of the docs/goals queue. Emits a report; NEVER mutates.

The goals-status skill runs this to show the OPEN goals — in_progress, blocked,
and not_started — each with its title and a short brief; completed goals are
hidden (only counted). It reads git + docs/goals/index.yaml + each goal file;
it never writes to the queue (dispatch owns queue state).

Status lives only in index.yaml. The title/type/model come from each goal
file's frontmatter, and the "brief" is the file's `## Outcome (plain language)`
paragraph — there is no `brief:` field.
"""
import argparse, glob, json, os, re, subprocess, sys, textwrap
try:
    import yaml  # PyYAML — primary parser; the factory already requires it
except ImportError:  # stdlib-only environment: the hand parsers below take over
    yaml = None


# open statuses, in the order they render; `completed` is hidden.
STATUS_ORDER = ["in_progress", "blocked", "not_started"]
STATUS_META = {
    "in_progress": ("▶", "IN PROGRESS"),   # ▶
    "blocked":     ("⛔", "BLOCKED"),        # ⛔
    "not_started": ("○", "NOT STARTED"),    # ○
}


def _run(cmd):
    """Read-only subprocess wrapper → (rc, stdout, stderr). Never mutates."""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True)
        return p.returncode, p.stdout, p.stderr
    except (OSError, subprocess.SubprocessError):
        return 1, "", ""


def find_goals_dir(explicit=None):
    """Locate docs/goals. --dir wins; else <git toplevel>/docs/goals; else cwd."""
    if explicit:
        return explicit
    rc, out, _ = _run(["git", "rev-parse", "--show-toplevel"])
    repo_root = out.strip() if rc == 0 else os.getcwd()
    return os.path.join(repo_root, "docs", "goals")


# ---- YAML-ish parsing (PyYAML primary, minimal stdlib fallback) ---------------

def _unquote(s):
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1]
    return s


def _split_top_level(s, sep=","):
    """Split on sep, ignoring separators inside [], {}, or quotes."""
    items, depth, quote, buf = [], 0, None, []
    for ch in s:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
            buf.append(ch)
        elif ch in "[{":
            depth += 1
            buf.append(ch)
        elif ch in "]}":
            depth = max(0, depth - 1)
            buf.append(ch)
        elif ch == sep and depth == 0:
            items.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    if buf:
        items.append("".join(buf))
    return [i.strip() for i in items if i.strip()]


def _coerce(v):
    v = v.strip()
    if v.startswith("[") and v.endswith("]"):
        return [_unquote(x) for x in _split_top_level(v[1:-1])]
    return _unquote(v)


def _parse_inline_map(s):
    """Parse `key: val, key2: [a, b], key3: "x, y"` (bracket/quote-aware) → dict."""
    out = {}
    for part in _split_top_level(s):
        if ":" not in part:
            continue
        k, v = part.split(":", 1)
        out[k.strip()] = _coerce(v)
    return out


def _parse_index_goals_fallback(text):
    """Stdlib fallback: read the inline-map entries under `goals:`.

    Handles the documented shape (`  NNN-slug: {status: ..., depends_on: [...]}`)
    and the empty `goals: {}`. Enough for a status view when PyYAML is absent.
    """
    goals, in_goals = {}, False
    for raw in text.splitlines():
        stripped = raw.strip()
        if not in_goals:
            if stripped == "goals:":
                in_goals = True
            elif stripped.startswith("goals:"):
                rest = stripped[len("goals:"):].strip()
                if rest == "{}":
                    return {}
                in_goals = True  # block entries follow (or empty)
            continue
        # a dedent to a new top-level key ends the goals block
        if raw and not raw[0].isspace():
            break
        m = re.match(r"^\s+([^\s:#][^:]*):\s*\{(.*)\}\s*$", raw)
        if m:
            goals[m.group(1).strip()] = _parse_inline_map(m.group(2))
    return goals


def load_index(index_path):
    """Return (goals_map, warning). goals_map is {id: {status, ...}} (may be {}).

    warning is a message string when PyYAML is present but the file is malformed
    (so we fell back to a best-effort read that may drop goals) — else None.
    """
    text = open(index_path, encoding="utf-8", errors="replace").read() \
        if os.path.exists(index_path) else ""
    if yaml is not None:
        try:
            data = yaml.safe_load(text) or {}
        except Exception:
            return (_parse_index_goals_fallback(text),
                    "index.yaml is not valid YAML — showing a best-effort read; "
                    "some goals may be missing (run /factory-doctor)")
        if isinstance(data, dict):
            goals = data.get("goals") or {}
            return ({k: (v or {}) for k, v in goals.items()}
                    if isinstance(goals, dict) else {}), None
    return _parse_index_goals_fallback(text), None


def parse_index(index_path):
    """Return just the goals map (convenience wrapper over load_index)."""
    return load_index(index_path)[0]


# ---- goal-file frontmatter + brief -------------------------------------------

def _split_frontmatter(text):
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            return parts[1], parts[2]
    return "", text


def _strip_inline_comment(v):
    if v[:1] in "\"'":
        return v  # quoted value — leave it to _unquote
    m = re.search(r"\s#", v)
    return v[:m.start()].strip() if m else v


def _parse_frontmatter(fm):
    """Return frontmatter as {key: str} (scalars only — title/type/model)."""
    if yaml is not None:
        try:
            data = yaml.safe_load(fm)
            if isinstance(data, dict):
                return {k: ("" if v is None else str(v)) for k, v in data.items()}
        except Exception:
            pass
    out = {}
    for line in fm.splitlines():
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if m:
            out[m.group(1)] = _unquote(_strip_inline_comment(m.group(2).strip()))
    return out


def _section_body(body, heading_re):
    """Text between the first heading matching heading_re and the next `## `."""
    lines = body.splitlines()
    start = None
    for i, ln in enumerate(lines):
        if re.match(heading_re, ln, re.IGNORECASE):
            start = i + 1
            break
    if start is None:
        return None
    out = []
    for ln in lines[start:]:
        if re.match(r"^##\s", ln):
            break
        out.append(ln)
    return "\n".join(out)


def _first_paragraph(section):
    para = []
    for ln in section.splitlines():
        if ln.strip() == "":
            if para:
                break
            continue
        para.append(ln.strip())
    return " ".join(para).strip()


def _extract_brief(body):
    """First paragraph under `## Outcome (plain language)`.

    Fallbacks: the first `##` section's first paragraph; else empty string.
    """
    section = _section_body(body, r"^##\s+Outcome\b")
    if section is None:
        section = _section_body(body, r"^##\s+\S")
    return _first_paragraph(section) if section else ""


def parse_goal_file(path):
    """Return {title, type, model, brief}. Missing file → a clear placeholder."""
    if not os.path.exists(path):
        return {"title": "(goal file missing)", "type": "", "model": "", "brief": ""}
    text = open(path, encoding="utf-8", errors="replace").read()
    fm, body = _split_frontmatter(text)
    meta = _parse_frontmatter(fm)
    return {
        "title": meta.get("title") or "(untitled)",
        "type": (meta.get("type") or "").split()[0] if meta.get("type") else "",
        "model": (meta.get("model") or "").split()[0] if meta.get("model") else "",
        "brief": _extract_brief(body),
    }


# ---- report assembly ----------------------------------------------------------

def _status(entry):
    return str((entry or {}).get("status") or "").strip()


def build_report(goals_dir):
    """Join index status + goal-file title/brief. None if there's no index.yaml."""
    index_path = os.path.join(goals_dir, "index.yaml")
    if not os.path.exists(index_path):
        return None
    index_goals, warning = load_index(index_path)
    archive_path = os.path.join(goals_dir, "archive.yaml")
    archive_goals = parse_index(archive_path) if os.path.exists(archive_path) else {}

    # a dep is "still blocking" only if it sits in the live queue unfinished;
    # completed (in index) or archived (absent) deps count as satisfied.
    incomplete = {gid for gid, e in index_goals.items()
                  if _status(e) != "completed"}
    completed = sum(1 for e in index_goals.values() if _status(e) == "completed") \
        + len(archive_goals)

    records = []
    for gid, entry in index_goals.items():
        raw = _status(entry)
        if raw == "completed":
            continue
        st = raw if raw in STATUS_ORDER else "not_started"
        gf = parse_goal_file(os.path.join(goals_dir, gid + ".md"))
        deps = entry.get("depends_on") or []
        if isinstance(deps, str):
            deps = [deps]
        waiting_on = [d for d in deps if d in incomplete and d != gid]
        records.append({
            "id": gid,
            "status": st,
            "title": gf["title"],
            "type": gf["type"],
            "model": gf["model"],
            "brief": gf["brief"],
            "reason": str(entry.get("reason") or "") if st == "blocked" else "",
            "waiting_on": waiting_on if st == "not_started" else [],
            "ready": st == "not_started" and not waiting_on,
        })
    records.sort(key=lambda r: (STATUS_ORDER.index(r["status"]), r["id"]))
    report = {"open": len(records), "completed": completed, "goals": records}
    if warning:
        report["warning"] = warning
    return report


# ---- rendering ----------------------------------------------------------------

def _truncate(s, n):
    s = " ".join(s.split())
    return s if len(s) <= n else s[: max(0, n - 1)].rstrip() + "…"


def _meta_str(rec):
    return " · ".join(b for b in (rec["type"], rec["model"]) if b)


def _empty_line(report):
    c = report["completed"]
    if c:
        return "docs/goals — nothing open · %d completed \U0001f389\n" % c
    return "docs/goals — queue is empty\n"


def _group(goals):
    g = {}
    for r in goals:
        g.setdefault(r["status"], []).append(r)
    return g


def _detailed_goal(rec, width=68):
    lines = []
    meta = _meta_str(rec)
    left = "  " + rec["id"]
    lines.append(left + " " * max(1, 42 - len(left)) + meta if meta else left)
    lines.append("  " + rec["title"])
    if rec["brief"]:
        wrapped = textwrap.wrap(rec["brief"], width=width) or [""]
        lines.append("  › " + wrapped[0])          # ›
        lines.extend("    " + w for w in wrapped[1:])
    if rec["status"] == "blocked":
        lines.append("  ✗ reason: " + (rec["reason"] or "(no reason recorded)"))  # ✗
    elif rec["status"] == "not_started" and rec["waiting_on"]:
        lines.append("  ⏳ waiting on " + ", ".join(rec["waiting_on"]))            # ⏳
    return "\n".join(lines)


def render_detailed(report):
    if report["open"] == 0:
        return _empty_line(report)
    c = report["completed"]
    head = "docs/goals — %d open%s" % (
        report["open"], " · %d completed (hidden)" % c if c else "")
    out = [head, ""]
    groups = _group(report["goals"])
    for st in STATUS_ORDER:
        recs = groups.get(st)
        if not recs:
            continue
        icon, label = STATUS_META[st]
        out.append("%s %s  (%d)" % (icon, label, len(recs)))
        for r in recs:
            out.append(_detailed_goal(r))
            out.append("")
    return "\n".join(out).rstrip() + "\n"


def _compact_note(rec):
    if rec["status"] == "blocked":
        return _truncate(rec["reason"] or "no reason recorded", 52)
    if rec["status"] == "not_started" and rec["waiting_on"]:
        return "waiting on " + ", ".join(rec["waiting_on"])
    return ""


def render_compact(report):
    if report["open"] == 0:
        return _empty_line(report)
    out = ["docs/goals — %d open · %d done" % (report["open"], report["completed"]), ""]
    idw = min(24, max((len(r["id"]) for r in report["goals"]), default=0))
    for r in report["goals"]:              # one line per goal
        label = STATUS_META[r["status"]][1]
        line = "%-12s %-*s %s" % (label, idw, r["id"], r["title"])
        note = _compact_note(r)
        if note:
            line += "  (%s)" % note
        out.append(line.rstrip())
    return "\n".join(out).rstrip() + "\n"


def render_json(report):
    return json.dumps(report, indent=2, ensure_ascii=False) + "\n"


# ---- CLI ----------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="goals_status.py",
        description="Read-only view of the docs/goals queue (open goals only).")
    ap.add_argument("--dir", default=None,
                    help="path to the docs/goals directory "
                         "(default: <git root>/docs/goals)")
    ap.add_argument("--compact", action="store_true", help="one line per goal")
    ap.add_argument("--json", action="store_true", help="machine-readable JSON")
    ap.add_argument("--self-test", action="store_true",
                    help="run the co-located test suite and exit")
    a = ap.parse_args(argv)

    if a.self_test:
        test_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "test_goals_status.py")
        return subprocess.run([sys.executable, test_file]).returncode

    report = build_report(find_goals_dir(a.dir))
    if report is None:
        if a.json:
            print(json.dumps({"error": "no docs/goals/index.yaml",
                              "open": 0, "completed": 0, "goals": []}, indent=2))
        else:
            sys.stderr.write(
                "no docs/goals queue here — run /factory-doctor to scaffold one\n")
        return 2

    sys.stdout.write(render_json(report) if a.json else
                     render_compact(report) if a.compact else
                     render_detailed(report))
    if report.get("warning") and not a.json:  # JSON carries it in the payload
        sys.stderr.write("⚠ " + report["warning"] + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
