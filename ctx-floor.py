#!/usr/bin/env python3
"""Context floor of every session on this machine: what a session costs before you type.

The floor is the context already loaded at the FIRST assistant turn — system prompt,
tool definitions, CLAUDE.md, MCP servers. It is not paid once. It sits under every later
turn of that session as cache read, so a 40k difference in the floor is 40k re-read on
every turn until the session ends.

Different Claude Code clients preload different tool surfaces, so the same project can
open at very different floors. This prints the number instead of guessing at it.

Compare like with like: only rows for the SAME project answer "what does the client
cost me", because CLAUDE.md and MCP servers move the floor too.

Usage:
    python ctx-floor.py              # every session the index still knows about
    python ctx-floor.py --all        # include sessions with no index entry
"""
import json
import os
import statistics
import sys

HOME = os.path.expanduser("~")
PROJECTS = os.path.join(HOME, ".claude", "projects")
SESSIONS = os.path.join(HOME, ".claude", "sessions")
SHOW_ALL = "--all" in sys.argv

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def session_index():
    index = {}
    try:
        names = os.listdir(SESSIONS)
    except OSError:
        return index
    for name in names:
        if not name.endswith(".json"):
            continue
        try:
            with open(os.path.join(SESSIONS, name), encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception:
            continue
        if data.get("sessionId"):
            index[data["sessionId"]] = data
    return index


def floor_of(path):
    """First assistant turn carrying usage -> tokens loaded before the first reply."""
    try:
        fh = open(path, encoding="utf-8", errors="replace")
    except OSError:
        return None, None
    with fh:
        for line in fh:
            if '"usage"' not in line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            msg = rec.get("message") or {}
            usage = msg.get("usage") or rec.get("usage")
            if not isinstance(usage, dict) or usage.get("input_tokens") is None:
                continue
            total = sum(usage.get(k) or 0 for k in
                        ("input_tokens", "cache_read_input_tokens",
                         "cache_creation_input_tokens"))
            return total, (rec.get("timestamp") or "")[:10]
    return None, None


def main():
    index, rows = session_index(), []
    for root, _dirs, names in os.walk(PROJECTS):
        for name in names:
            if not name.endswith(".jsonl"):
                continue
            sid = name[:-6]
            meta = index.get(sid)
            if not meta and not SHOW_ALL:
                continue
            floor, day = floor_of(os.path.join(root, name))
            if not floor:
                continue
            rows.append({
                "floor": floor, "day": day or "?",
                "client": (meta or {}).get("entrypoint") or "unknown",
                "project": os.path.basename(root),
                "name": (meta or {}).get("name") or sid[:8],
            })
    if not rows:
        print("No sessions found. Run with --all, or check that ~/.claude/projects exists.")
        return 0

    rows.sort(key=lambda r: r["floor"])
    print("%9s  %-10s  %-14s  %-34s  %s" % ("FLOOR", "DAY", "CLIENT", "PROJECT", "SESSION"))
    for r in rows:
        print("%9s  %-10s  %-14s  %-34s  %s" % (
            "{:,}".format(r["floor"]), r["day"], r["client"].replace("claude-", ""),
            r["project"][:34], r["name"][:40]))

    print()
    by_client = {}
    for r in rows:
        by_client.setdefault(r["client"], []).append(r["floor"])
    for client, vals in sorted(by_client.items()):
        print("%-14s n=%-3d min %-9s median %-9s max %s" % (
            client.replace("claude-", ""), len(vals),
            "{:,}".format(min(vals)), "{:,}".format(int(statistics.median(vals))),
            "{:,}".format(max(vals))))
    print("\nSame-project rows are the only fair comparison between clients.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
