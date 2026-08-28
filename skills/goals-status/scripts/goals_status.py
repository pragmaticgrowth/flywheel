"""Read-only view of the docs/goals queue. Emits a report; NEVER mutates.

The goals-status skill runs this to show the OPEN goals — in_progress, blocked,
and not_started — each with its title and a short brief; completed goals are
hidden (only counted). It reads git + docs/goals/index.yaml + each goal file;
it never writes to the queue (dispatch owns queue state).

Status lives only in index.yaml. The title/type/model come from each goal
file's frontmatter — `model:` is the execution tier (heavy|medium|light|inherit;
legacy opus/sonnet/haiku stamps are read as heavy/medium/light aliases) — and
the "brief" is the file's `## Outcome (plain language)` paragraph — there is no
`brief:` field.

PyYAML is the only parser: factory-doctor already treats a missing PyYAML and a
malformed index as BLOCKERs, so this view points at that fix rather than
hand-rolling a second, weaker YAML reader.

The view ends with one `next:` line naming the command the owner runs next —
derived in next_command(), first match: /dispatch when anything is open,
else /process-inbox when the inbox carries unchecked items, else /ideate.
"""
import argparse, datetime, os, re, subprocess, sys, textwrap
try:
    import yaml
except ImportError:
    sys.stderr.write("PyYAML is required to read the queue "
                     "(pip install pyyaml) — run /factory-doctor\n")
    sys.exit(2)


# open statuses, in the order they render; `completed` is hidden.
STATUS_ORDER = ["in_progress", "blocked", "not_started"]
STATUS_META = {
    "in_progress": ("▶", "IN PROGRESS"),
    "blocked":     ("⛔", "BLOCKED"),
    "not_started": ("○", "NOT STARTED"),
}


class QueueError(Exception):
    """The queue itself is unreadable — the view cannot be trusted at all."""


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


# ---- queue parsing ------------------------------------------------------------

def load_index(index_path):
    """Return {id: {status, ...}} from a queue file. Missing file → {}.

    A malformed queue raises QueueError: a best-effort read could silently drop
    goals, and "some of your queue" is worse than a pointer at /factory-doctor.
    """
    if not os.path.exists(index_path):
        return {}
    text = open(index_path, encoding="utf-8", errors="replace").read()
    try:
        data = yaml.safe_load(text) or {}
    except yaml.YAMLError as e:
        raise QueueError("%s is not valid YAML (%s) — run /factory-doctor"
                         % (os.path.basename(index_path), e))
    if not isinstance(data, dict):
        return {}
    goals = data.get("goals") or {}
    if not isinstance(goals, dict):
        return {}
    return {k: (v or {}) for k, v in goals.items()}


# ---- goal-file frontmatter + brief -------------------------------------------

def _split_frontmatter(text):
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            return parts[1], parts[2]
    return "", text


def _parse_frontmatter(fm):
    """Return frontmatter as {key: str} (scalars only — title/type/model).

    One unparseable goal file degrades to an untitled row; it never takes the
    whole view down with it (unlike a bad index, which invalidates everything).
    """
    try:
        data = yaml.safe_load(fm)
    except yaml.YAMLError:
        return {}
    if not isinstance(data, dict):
        return {}
    return {k: ("" if v is None else str(v)) for k, v in data.items()}


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


TIER_ALIASES = {"opus": "heavy", "sonnet": "medium", "haiku": "light"}


def normalize_tier(value):
    """Map legacy model names to tier names; tier names and '' pass through."""
    v = (value or "").strip().lower()
    return TIER_ALIASES.get(v, v)


def parse_goal_file(path):
    """Return {title, type, model, brief}. Missing file → a clear placeholder."""
    try:
        text = open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return {"title": "(goal file missing)", "type": "", "model": "", "brief": ""}
    fm, body = _split_frontmatter(text)
    meta = _parse_frontmatter(fm)
    return {
        "title": meta.get("title") or "(untitled)",
        "type": meta.get("type") or "",
        "model": normalize_tier(meta.get("model")),
        "brief": _extract_brief(body),
    }


# ---- next-command derivation --------------------------------------------------

def _inbox_open_count(goals_dir):
    """Unchecked `- [ ]` lines in docs/goals/inbox.md (0 when absent/unreadable)."""
    try:
        text = open(os.path.join(goals_dir, "inbox.md"),
                    encoding="utf-8", errors="replace").read()
    except OSError:
        return 0
    return sum(1 for ln in text.splitlines() if ln.strip().startswith("- [ ]"))


def next_command(report, goals_dir):
    """The ONE command the owner runs next, derived from current queue state.

    First match: any open goal (in_progress/blocked/not_started) → /dispatch
    (dispatch works the queue and self-heals blocked contracts in-run); else
    unchecked `- [ ]` inbox lines → /process-inbox; else /ideate.
    """
    if report["open"] > 0:
        return "/dispatch"
    if _inbox_open_count(goals_dir) > 0:
        return "/process-inbox"
    return "/ideate"


# ---- report assembly ----------------------------------------------------------

def _status(entry):
    return str((entry or {}).get("status") or "").strip()


def _age_str(value, now=None):
    """Humanized elapsed time since an index timestamp ('41m', '2.3h', '3d').

    Timestamps (`claimed_at`/`settled_at`, dispatch v12.2.0) are optional
    metadata — anything unparseable returns '' and is simply not shown.
    """
    if not value:
        return ""
    try:
        ts = value if isinstance(value, datetime.datetime) \
            else datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=datetime.timezone.utc)
        now = now or datetime.datetime.now(datetime.timezone.utc)
        mins = (now - ts).total_seconds() / 60
    except (ValueError, TypeError):
        return ""
    if mins < 0:
        return ""
    if mins < 90:
        return "%dm" % round(mins)
    if mins < 48 * 60:
        return "%.1fh" % (mins / 60)
    return "%dd" % round(mins / 60 / 24)


def build_report(goals_dir):
    """Join index status + goal-file title/brief. None if there's no index.yaml."""
    index_path = os.path.join(goals_dir, "index.yaml")
    if not os.path.exists(index_path):
        return None
    index_goals = load_index(index_path)
    archived = load_index(os.path.join(goals_dir, "archive.yaml"))

    # a dep is "still blocking" only if it sits in the live queue unfinished;
    # completed/retired (in index) or archived (absent) deps count as satisfied.
    incomplete = {gid for gid, e in index_goals.items()
                  if _status(e) not in ("completed", "retired")}
    retired = sum(1 for e in index_goals.values() if _status(e) == "retired") \
        + sum(1 for e in archived.values() if _status(e) == "retired")
    completed = sum(1 for e in index_goals.values() if _status(e) == "completed") \
        + sum(1 for e in archived.values() if _status(e) != "retired")

    records = []
    for gid, entry in index_goals.items():
        raw = _status(entry)
        if raw in ("completed", "retired"):
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
            # elapsed since claim (in_progress) / since it blocked (blocked);
            # '' when the entry predates the v12.2.0 timestamp fields.
            "age": _age_str(entry.get("claimed_at")) if st == "in_progress"
                   else _age_str(entry.get("settled_at")) if st == "blocked" else "",
        })
    records.sort(key=lambda r: (STATUS_ORDER.index(r["status"]), r["id"]))
    report = {"open": len(records), "completed": completed, "retired": retired,
              "goals": records}
    report["next"] = next_command(report, goals_dir)
    return report


# ---- rendering ----------------------------------------------------------------

def _meta_str(rec):
    return " · ".join(b for b in (rec["type"], rec["model"]) if b)


def _empty_line(report):
    c = report["completed"]
    r = report.get("retired", 0)
    tail = " · %d retired" % r if r else ""
    if c or r:
        return "docs/goals — nothing open · %d completed%s \U0001f389\n" % (c, tail)
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
        lines.append("  › " + wrapped[0])
        lines.extend("    " + w for w in wrapped[1:])
    if rec["status"] == "blocked":
        age = " (blocked %s ago)" % rec["age"] if rec.get("age") else ""
        lines.append("  ✗ reason: " + (rec["reason"] or "(no reason recorded)") + age)
    elif rec["status"] == "in_progress" and rec.get("age"):
        lines.append("  ▶ claimed %s ago" % rec["age"])
    elif rec["status"] == "not_started" and rec["waiting_on"]:
        lines.append("  ⏳ waiting on " + ", ".join(rec["waiting_on"]))
    return "\n".join(lines)


def render_detailed(report):
    if report["open"] == 0:
        body = _empty_line(report).rstrip("\n")
    else:
        c = report["completed"]
        r = report.get("retired", 0)
        hidden = ""
        if c:
            hidden = " · %d completed (hidden)" % c
        if r:
            hidden += " · %d retired" % r
        head = "docs/goals — %d open%s" % (report["open"], hidden)
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
        body = "\n".join(out).rstrip()
    # the front-door answer: exactly one next line, last, queue-derived
    return "%s\n\nnext: %s\n" % (body, report["next"])


# ---- CLI ----------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="goals_status.py",
        description="Read-only view of the docs/goals queue (open goals only).")
    ap.add_argument("--dir", default=None,
                    help="path to the docs/goals directory "
                         "(default: <git root>/docs/goals)")
    a = ap.parse_args(argv)

    try:
        report = build_report(find_goals_dir(a.dir))
    except QueueError as e:
        sys.stderr.write("%s\n" % e)
        return 2
    if report is None:
        sys.stderr.write(
            "no docs/goals queue here — run /factory-doctor to scaffold one\n")
        return 2

    sys.stdout.write(render_detailed(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
