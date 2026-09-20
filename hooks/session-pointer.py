#!/usr/bin/env python3
"""Record which session is live in a given cwd, so an outside process can find it.

ctx-watch.py runs in a plain VS Code terminal, which inherits no CLAUDE_CODE_SESSION_ID
and cannot tell two sessions on the same repo apart. Picking the newest transcript by
mtime reads whichever window wrote last -- that produced a 84.2k reading for a session
actually holding 117.3k. This writes the pointer instead: exact, not a guess.

Fires on SessionStart and UserPromptSubmit, so the pointer follows the session you are
actually typing into. Prints NOTHING: on both events stdout would be injected into the
model's context.
"""
import hashlib
import json
import os
import sys
import time

STATE = os.path.join(os.path.expanduser("~"), ".claude", "hooks", "state", "live")


def main():
    raw = sys.stdin.read()
    if not raw.strip():
        return
    data = json.loads(raw)
    cwd = data.get("cwd") or os.getcwd()
    key = hashlib.sha1(cwd.lower().encode("utf-8")).hexdigest()[:16]
    payload = {
        "session_id": data.get("session_id"),
        "transcript_path": data.get("transcript_path"),
        "cwd": cwd,
        "event": data.get("hook_event_name"),
        "updated_at": time.time(),
    }
    os.makedirs(STATE, exist_ok=True)
    tmp = os.path.join(STATE, key + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh)
    os.replace(tmp, os.path.join(STATE, key + ".json"))


try:
    main()
except Exception:
    pass          # A monitoring hook must never break the session.
