#!/usr/bin/env python3
"""Install the context-watch pack into ~/.claude and wire it into settings.json.

Copies four files, then adds two hook entries and one statusline entry to
settings.json. Everything it overwrites is backed up next to the original with a
timestamp suffix; nothing is deleted. Run with --dry-run to see the plan first.

Usage:
    python install.py [--dry-run] [--no-hooks] [--no-statusline]
"""
import json
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
CLAUDE = os.path.join(os.path.expanduser("~"), ".claude")
SETTINGS = os.path.join(CLAUDE, "settings.json")
STAMP = time.strftime("%Y%m%d-%H%M%S")

# source -> destination, relative to this folder and to ~/.claude
FILES = [
    ("ctx-watch.py", "ctx-watch.py"),
    ("statusline-burn.py", "statusline-burn.py"),
    (os.path.join("hooks", "session-pointer.py"), os.path.join("hooks", "session-pointer.py")),
    (os.path.join("commands", "burn.md"), os.path.join("commands", "burn.md")),
]

DRY = "--dry-run" in sys.argv
DO_HOOKS = "--no-hooks" not in sys.argv
DO_STATUSLINE = "--no-statusline" not in sys.argv

# Absolute paths are required inside settings.json: Claude Code runs these commands
# from the project directory, not from ~/.claude.
PY = sys.executable.replace("\\", "/")
HOME_FWD = CLAUDE.replace("\\", "/")
POINTER_CMD = '"%s" "%s/hooks/session-pointer.py"' % (PY, HOME_FWD)
STATUSLINE_CMD = '"%s" "%s/statusline-burn.py"' % (PY, HOME_FWD)

log = []


def backup(path):
    if not os.path.exists(path):
        return None
    dst = "%s.bak-%s" % (path, STAMP)
    if not DRY:
        shutil.copy2(path, dst)
    return dst


def copy_files():
    for src_rel, dst_rel in FILES:
        src = os.path.join(HERE, src_rel)
        dst = os.path.join(CLAUDE, dst_rel)
        if not os.path.exists(src):
            log.append("MISSING  %s (skipped)" % src_rel)
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True) if not DRY else None
        old = backup(dst)
        if not DRY:
            with open(src, encoding="utf-8") as fh:
                text = fh.read()
            text = text.replace("__CLAUDE_HOME__", HOME_FWD)
            with open(dst, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(text)
            if dst.endswith(".py"):
                os.chmod(dst, 0o755)
        log.append("copy     %s -> %s%s" % (src_rel, dst, "  (backed up)" if old else ""))


def load_settings():
    if not os.path.exists(SETTINGS):
        return {}
    with open(SETTINGS, encoding="utf-8") as fh:
        return json.load(fh)


def has_pointer(entries):
    for group in entries or []:
        for hook in group.get("hooks") or []:
            if "session-pointer.py" in (hook.get("command") or ""):
                return True
    return False


def wire_settings():
    settings = load_settings()
    changed = False

    if DO_HOOKS:
        hooks = settings.setdefault("hooks", {})
        for event in ("SessionStart", "UserPromptSubmit"):
            if has_pointer(hooks.get(event)):
                log.append("hooks    %s already points at session-pointer.py" % event)
                continue
            hooks.setdefault(event, []).append(
                {"hooks": [{"type": "command", "command": POINTER_CMD}]})
            log.append("hooks    %s <- session-pointer.py" % event)
            changed = True

    if DO_STATUSLINE:
        current = (settings.get("statusLine") or {}).get("command") or ""
        if "statusline-burn.py" in current:
            log.append("status   statusLine already points at statusline-burn.py")
        elif current:
            log.append("status   SKIPPED: statusLine is taken by another command.")
            log.append("         Set it by hand if you want the burn line:")
            log.append('         "statusLine": {"type": "command", "command": %s}'
                       % json.dumps(STATUSLINE_CMD))
        else:
            settings["statusLine"] = {"type": "command", "command": STATUSLINE_CMD}
            log.append("status   statusLine <- statusline-burn.py")
            changed = True

    if not changed:
        return
    old = backup(SETTINGS)
    if not DRY:
        with open(SETTINGS, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(settings, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
    log.append("write    %s%s" % (SETTINGS, "  (backed up)" if old else ""))


def main():
    if not os.path.isdir(CLAUDE):
        print("No %s found. Run Claude Code once, then install." % CLAUDE)
        return 1
    copy_files()
    wire_settings()
    print("\n".join(("  " + line) for line in log))
    print()
    if DRY:
        print("Dry run: nothing was written. Re-run without --dry-run to apply.")
        return 0
    print("Done. Restart Claude Code, then run:  python %s/ctx-watch.py" % HOME_FWD)
    return 0


if __name__ == "__main__":
    sys.exit(main())
