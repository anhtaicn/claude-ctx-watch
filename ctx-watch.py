#!/usr/bin/env python3
"""Context window of every live Claude Code session, sized for a narrow side terminal.

Runs in a split VS Code terminal because the custom statusline does not render in the
extension pane. Three things it refuses to guess:

  which session  -- ~/.claude/sessions/<pid>.json maps sessionId to the session's real
                    name, the same one the app puts on the tab.
  alive or not   -- that file carries the pid, so a closed session is reported closed
                    instead of freezing on its last number while still looking live.
  how wide       -- the layout is built from the terminal width, two short lines per
                    session, so a 40-column pane does not wrap into soup.
"""
import ctypes
import json
import os
import shutil
import subprocess
import sys
import time

ESC = chr(27)
HOME = os.path.expanduser("~")
PROJECTS = os.path.join(HOME, ".claude", "projects")
SESSIONS = os.path.join(HOME, ".claude", "sessions")
LIVE = os.path.join(HOME, ".claude", "hooks", "state", "live")
BURN = os.path.join(HOME, ".claude", "statusline-burn.py")

WINDOWS = {"claude-opus-5": 1_000_000}      # observed via /context
WINDOW_DEFAULT = 200_000
TAIL_BYTES = 400_000

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    FULL, EMPTY, DOT, ELLIPSIS = "█", "░", "●", "…"
except Exception:
    FULL, EMPTY, DOT, ELLIPSIS = "#", ".", "*", "~"

USE_COLOR = "--no-color" not in sys.argv


def paint(code, text):
    if not USE_COLOR:
        return text
    return "%s[%sm%s%s[0m" % (ESC, code, text, ESC)


def human(n):
    for unit, div in (("M", 1e6), ("k", 1e3)):
        if n >= div:
            return "%.1f%s" % (n / div, unit)
    return str(int(n))


def age_str(seconds):
    if seconds < 60:
        return "%ds" % int(seconds)
    if seconds < 3600:
        return "%dm" % int(seconds / 60)
    return "%.1fh" % (seconds / 3600.0)


def pid_alive(pid):
    if not pid:
        return False
    if os.name != "nt":
        try:
            os.kill(pid, 0)
            return True
        except Exception:
            return False
    # os.kill on Windows TERMINATES the target for most signals, so query a handle.
    k32 = ctypes.windll.kernel32
    handle = k32.OpenProcess(0x1000, False, int(pid))   # QUERY_LIMITED_INFORMATION
    if not handle:
        return False
    code = ctypes.c_ulong()
    ok = k32.GetExitCodeProcess(handle, ctypes.byref(code))
    k32.CloseHandle(handle)
    return bool(ok) and code.value == 259               # STILL_ACTIVE


def session_index():
    """sessionId -> metadata; on a restarted id the newer start wins."""
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
        sid = data.get("sessionId")
        if not sid:
            continue
        prev = index.get(sid)
        if prev and (prev.get("startedAt") or 0) >= (data.get("startedAt") or 0):
            continue
        index[sid] = data
    return index


def pointed():
    """Session ids the hook says a prompt was last submitted into."""
    out = set()
    try:
        names = os.listdir(LIVE)
    except OSError:
        return out
    for name in names:
        if not name.endswith(".json"):
            continue
        try:
            with open(os.path.join(LIVE, name), encoding="utf-8") as fh:
                sid = json.load(fh).get("session_id")
        except Exception:
            continue
        if sid:
            out.add(sid)
    return out


def last_record(path):
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as fh:
            fh.seek(max(0, size - TAIL_BYTES))
            lines = fh.read().decode("utf-8", "replace").splitlines()
    except OSError:
        return None, None
    for line in reversed(lines):
        if '"usage"' not in line:
            continue
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        msg = rec.get("message") or {}
        usage = msg.get("usage") or rec.get("usage")
        if isinstance(usage, dict) and usage.get("input_tokens") is not None:
            return usage, msg.get("model")
    return None, None


def window_for(model):
    override = os.environ.get("CLAUDE_CTX_WINDOW")
    if override:
        return int(override), True
    if model in WINDOWS:
        return WINDOWS[model], True
    return WINDOW_DEFAULT, False


def collect(since_s):
    now = time.time()
    index, marks, rows = session_index(), pointed(), []
    for root, _dirs, names in os.walk(PROJECTS):
        for name in names:
            if not name.endswith(".jsonl"):
                continue
            path = os.path.join(root, name)
            try:
                age = now - os.stat(path).st_mtime
            except OSError:
                continue
            if age > since_s:
                continue
            usage, model = last_record(path)
            if not usage:
                continue
            sid = name[:-6]
            meta = index.get(sid) or {}
            total = sum(usage.get(k) or 0 for k in
                        ("input_tokens", "cache_read_input_tokens",
                         "cache_creation_input_tokens"))
            window, known = window_for(model)
            rows.append({
                "age": age, "sid": sid, "total": total,
                "window": window, "known": known,
                "name": meta.get("name") or sid[:8],
                "alive": pid_alive(meta.get("pid")),
                "busy": meta.get("status") == "busy",
                "mine": sid in marks,
            })
    rows.sort(key=lambda r: (not r["alive"], r["age"]))
    return rows


def burn_line():
    try:
        out = subprocess.run([sys.executable, BURN], input="{}",
                             capture_output=True, text=True, timeout=20)
        return (out.stdout or "").strip() or "burn n/a"
    except Exception:
        return "burn n/a"


def render(width, since_s):
    rows = collect(since_s)
    out = ["%s  %s" % (paint("2", time.strftime("%H:%M:%S")),
                       paint("36", burn_line())), ""]
    if not rows:
        out.append("  khong co phien nao trong %s qua" % age_str(since_s))
        return "\n".join(out)

    bar_w = max(8, min(22, width - 26))
    for row in rows:
        frac = row["total"] / float(row["window"])
        filled = max(0, min(bar_w, int(round(frac * bar_w))))
        hue = "31" if frac >= 0.75 else ("33" if frac >= 0.5 else "32")
        if row["alive"]:
            state = paint("33", DOT + " busy") if row["busy"] else paint("32", DOT + " live")
        else:
            state = paint("2", "x closed")

        age = age_str(row["age"])
        room = max(8, width - len(age) - 4)
        label = row["name"]
        if len(label) > room:
            label = label[:room - 1] + ELLIPSIS
        pad = " " * max(1, width - 2 - len(label) - len(age))
        out.append("%s %s%s%s" % (
            paint("36", ">") if row["mine"] else " ",
            paint("1", label) if row["alive"] else paint("2", label),
            pad, paint("2", age)))
        out.append("  %s %s %s %s%s" % (
            paint(hue, FULL * filled) + paint("2", EMPTY * (bar_w - filled)),
            paint("1", "%8s" % human(row["total"])),
            paint("2", "%3d%%" % round(frac * 100)),
            state,
            paint("31", " win?") if not row["known"] else ""))
        out.append("")
    return "\n".join(out)


def main():
    interval, once, since_s = 5, False, 1800
    for arg in sys.argv[1:]:
        if arg == "--once":
            once = True
        elif arg.startswith("--interval="):
            interval = max(1, int(arg.split("=", 1)[1]))
        elif arg.startswith("--since="):
            since_s = max(60, int(arg.split("=", 1)[1]) * 60)
    while True:
        width = shutil.get_terminal_size((60, 20)).columns
        text = render(width, since_s)
        if once:
            print(text)
            return
        sys.stdout.write(ESC + "[H" + ESC + "[J" + text + "\n")
        sys.stdout.flush()
        time.sleep(interval)


try:
    main()
except KeyboardInterrupt:
    pass
