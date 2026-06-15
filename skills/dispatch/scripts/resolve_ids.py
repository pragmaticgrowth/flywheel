#!/usr/bin/env python3
"""resolve_ids — the conductor's one safe way to address a pane.

Pane AND tab ids renumber whenever any pane/tab closes, and a backgrounded
`agent wait <pane_id>` can complete because a DIFFERENT agent now owns that
pane id (live-verified, pitfall #21). terminal_id is stable per-process but
dies if the agent's process restarts. So: resolve immediately before every
pane operation, via the ladder terminal_id -> session_id -> not found.

  resolve_ids.py --term <terminal_id> [--session <session_id>]

Prints JSON:
  {found, pane_id, tab_id, workspace_id, agent_status, session_id,
   session_match, resolved_by}

- resolved_by "terminal_id": normal case.
- resolved_by "session_id": the terminal vanished (process restart) but a pane
  carries the same agent session — UPDATE your stored managed_term to the new
  terminal_id in this output.
- found false: report to the human; do not guess a pane.
- session_match false (with --session): the pane exists but carries a DIFFERENT
  session — do NOT read or drive it; treat as not-yours.

Works for the managed agent and for the conductor itself (--term <your_term>
gives the pane_id for the conductor's own short pane-label rename; tabs are
never renamed).
"""

import argparse
import json
import os
import shutil
import subprocess
import sys

HERDR = shutil.which("herdr") or os.path.expanduser("~/.local/bin/herdr")

def panes():
    if not os.path.exists(HERDR):
        raise RuntimeError("herdr binary not found (PATH or ~/.local/bin)")
    p = subprocess.run([HERDR, "pane", "list"], capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"herdr pane list failed: {p.stderr.strip() or p.stdout.strip()}")
    return json.loads(p.stdout)["result"]["panes"]


def row(p, resolved_by, session):
    sid = (p.get("agent_session") or {}).get("value")
    return {
        "found": True,
        "pane_id": p["pane_id"],
        "tab_id": p["tab_id"],
        "workspace_id": p["workspace_id"],
        "terminal_id": p.get("terminal_id"),
        "agent_status": p.get("agent_status"),
        "session_id": sid,
        "session_match": (sid == session) if session else None,
        "resolved_by": resolved_by,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--term", required=True, help="stable terminal_id to resolve")
    ap.add_argument("--session", help="expected agent session id (second factor + fallback key)")
    a = ap.parse_args()

    ps = panes()
    p = next((x for x in ps if x.get("terminal_id") == a.term), None)
    if p:
        print(json.dumps(row(p, "terminal_id", a.session)))
        return 0
    if a.session:
        p = next((x for x in ps if (x.get("agent_session") or {}).get("value") == a.session), None)
        if p:
            print(json.dumps(row(p, "session_id", a.session)))
            return 0
    print(json.dumps({"found": False, "term": a.term, "session": a.session,
                      "hint": "terminal gone and no pane carries the session — report to the human"}))
    return 1


if __name__ == "__main__":
    sys.exit(main())
