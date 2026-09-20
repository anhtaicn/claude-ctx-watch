#!/usr/bin/env python3
"""Statusline: how much quota this machine has burned recently.

Claude Code shows per-session context, but nothing shows spend ACROSS sessions —
which is exactly what a subagent fan-out consumes. Reads every transcript touched
in the last 5h, dedupes by requestId (summing per assistant line inflates ~1.8x),
and prices tokens as input-equivalents: in x1, cache_write x2, cache_read x0.1,
output x5.

Incremental: each file is read from a cached byte offset, so a render costs a few ms.
"""
import json
import os
import sys
import time

HOME = os.path.expanduser("~")
PROJECTS = os.path.join(HOME, ".claude", "projects")
STATE = os.path.join(HOME, ".claude", "hooks", "state")
CACHE = os.path.join(STATE, "burn-cache.json")
SPAWNS = os.path.join(STATE, "spawns.jsonl")
W5H = 5 * 3600
W10M = 600
WEIGHTS = (("input_tokens", 1.0), ("cache_creation_input_tokens", 2.0),
           ("cache_read_input_tokens", 0.1), ("output_tokens", 5.0))


def human(n):
    for unit, div in (("M", 1e6), ("k", 1e3)):
        if n >= div:
            return "%.1f%s" % (n / div, unit)
    return str(int(n))


def parse_ts(s):
    try:
        from datetime import datetime
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except Exception:
        return 0.0


def main():
    try:
        sys.stdin.read()
    except Exception:
        pass
    now = time.time()
    cutoff = now - W5H

    try:
        cache = json.load(open(CACHE, encoding="utf-8"))
    except Exception:
        cache = {"files": {}}
    files = cache.get("files", {})

    live = []
    for root, _dirs, names in os.walk(PROJECTS):
        for n in names:
            if not n.endswith(".jsonl"):
                continue
            p = os.path.join(root, n)
            try:
                st = os.stat(p)
            except OSError:
                continue
            if st.st_mtime >= cutoff:
                live.append((p, st.st_size))

    for p, size in live:
        ent = files.get(p) or {"off": 0, "pts": []}
        if ent["off"] > size:          # file rotated/truncated
            ent = {"off": 0, "pts": []}
        if size > ent["off"]:
            try:
                with open(p, "r", encoding="utf-8", errors="replace") as fh:
                    fh.seek(ent["off"])
                    chunk = fh.read()
                    ent["off"] = fh.tell()
            except OSError:
                chunk = ""
            for line in chunk.splitlines():
                if '"usage"' not in line:
                    continue
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                msg = d.get("message") or {}
                u = msg.get("usage") or d.get("usage")
                if not isinstance(u, dict):
                    continue
                rid = d.get("requestId") or msg.get("id")
                if not rid:
                    continue
                w = sum((u.get(k) or 0) * f for k, f in WEIGHTS)
                ent["pts"].append([parse_ts(d.get("timestamp") or ""), w, rid])
        ent["pts"] = [x for x in ent["pts"] if x[0] >= cutoff]
        files[p] = ent

    for p in list(files):
        if not any(p == q for q, _ in live):
            del files[p]
    try:
        os.makedirs(STATE, exist_ok=True)
        json.dump({"files": files}, open(CACHE, "w", encoding="utf-8"))
    except OSError:
        pass

    seen, t5, t10 = set(), 0.0, 0.0
    for ent in files.values():
        for ts, w, rid in ent["pts"]:
            if rid in seen:
                continue
            seen.add(rid)
            t5 += w
            if ts >= now - W10M:
                t10 += w

    spawns = 0
    try:
        with open(SPAWNS, encoding="utf-8") as fh:
            for line in fh:
                try:
                    if now - json.loads(line).get("ts", 0) <= W10M:
                        spawns += 1
                except ValueError:
                    pass
    except OSError:
        pass

    mark = " !" if t10 >= 3e6 else (" ^" if t10 >= 1e6 else "")
    out = "burn 5h %s | 10m %s%s" % (human(t5), human(t10), mark)
    if spawns:
        out += " | agents %d/10m" % spawns
    print(out)


try:
    main()
except Exception:
    print("burn n/a")
