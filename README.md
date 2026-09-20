# Claude Code — Context Watch

**See the context window and the token burn of every Claude Code session on your machine, from one
side terminal.**

If you keep more than one Claude Code window open, two numbers decide how your day goes and neither
one is on screen:

- **Which window is about to run out of context.** `/context` answers for the window you are typing
  in, and only when you stop and ask it. The others say nothing until one of them silently
  auto-compacts in the middle of a task you cared about.
- **What all of them together are doing to your quota.** Claude Code never adds spend up across
  sessions. A subagent fan-out in a window you are not watching can drain a 5-hour quota while you
  are away from the keyboard — and afterwards nothing tells you which window did it.

Context Watch puts both on screen, refreshed every 5 seconds, in a terminal you park beside your
work:

```
19:08:15  burn 5h 4.7M | 10m 692.4k

> Context watch packaging                                 0s
  ███░░░░░░░░░░░░░░░░░░░   141.1k  14% ● busy

> aeo-first-82                                           14m
  █████░░░░░░░░░░░░░░░░░   227.9k  23% ● live

  312cee1c                                               28m
  ████░░░░░░░░░░░░░░░░░░   189.0k  19% x closed
```

One row per session. You glance at it and know which window to wrap up, which one to leave running,
and whether right now is a bad moment to spawn subagents.

Stdlib Python only — no `pip install`, no `jq`, no daemon, no background service. It reads the
transcript files Claude Code already writes to disk.

---

## What each part of a row means

| Element | Meaning |
|---|---|
| `>` | You submitted a prompt into this session from this working directory — this is *your* window |
| Name | The session's real name, the one on the app tab. Falls back to the session id when there is no name |
| `14m` | How long ago that session last wrote to its transcript |
| Bar + `227.9k` | Tokens currently in that session's context window (input + cache read + cache write of the last API turn) |
| `23%` | Share of the model's context window. Green under 50%, yellow from 50%, red from 75% |
| `● live` / `● busy` / `x closed` | Whether the process is still running, and whether it is mid-turn |
| `win?` | The model is unknown to the script, so the percentage assumes a 200k window. See *Context window sizes* |

The header line is the **burn** statusline: input-equivalent tokens spent across *every* session on
this machine in the last 5 hours and the last 10 minutes. That is the number that tells you a
subagent fan-out is running away with your quota while you are away from the keyboard.

---

## Three things it refuses to guess

This is the whole design, and the reason it is more than a `tail` on a log file.

**Which session a row belongs to.** `~/.claude/sessions/<pid>.json` maps a session id to the name
the app puts on the tab. Without it you get eight hex characters and no idea which window is which.

**Whether a session is alive.** That same file carries the pid. A closed session is reported
`x closed` instead of freezing on its last number while still looking live. The check uses
`OpenProcess` + `GetExitCodeProcess` on Windows — **not** `os.kill`, which on Windows *terminates*
the target for most signals instead of probing it.

**Which window is yours.** A `SessionStart` / `UserPromptSubmit` hook writes a pointer file keyed by
working directory. Picking "the newest transcript by mtime" instead reads whichever window happened
to write last: during development that reported **84.2k for a session actually holding 117.3k**.
The hook makes it exact rather than a guess.

---

## Install

Requires Python 3.8+ and Claude Code having run at least once (so `~/.claude/` exists).

```bash
python install.py --dry-run
```

```bash
python install.py
```

The installer copies four files into `~/.claude/`, backs up anything it overwrites with a
timestamp suffix, and adds the hook + statusline entries to `settings.json`. It never deletes, and
it refuses to take over `statusLine` if another command already owns it — it prints the line for
you to paste instead. `--no-hooks` and `--no-statusline` skip either half.

Or do it by hand:

| File in this repo | Copy to | Wiring needed |
|---|---|---|
| `ctx-watch.py` | `~/.claude/ctx-watch.py` | none — you run it yourself |
| `hooks/session-pointer.py` | `~/.claude/hooks/session-pointer.py` | `SessionStart` + `UserPromptSubmit` hooks |
| `statusline-burn.py` | `~/.claude/statusline-burn.py` | `statusLine` |
| `commands/burn.md` | `~/.claude/commands/burn.md` | none — replace `__CLAUDE_HOME__` with your real path |

The `settings.json` fragment, with absolute paths of your own:

```json
{
  "hooks": {
    "SessionStart": [
      { "hooks": [{ "type": "command", "command": "python /ABSOLUTE/PATH/.claude/hooks/session-pointer.py" }] }
    ],
    "UserPromptSubmit": [
      { "hooks": [{ "type": "command", "command": "python /ABSOLUTE/PATH/.claude/hooks/session-pointer.py" }] }
    ]
  },
  "statusLine": {
    "type": "command",
    "command": "python /ABSOLUTE/PATH/.claude/statusline-burn.py"
  }
}
```

Hooks take effect in the **next** session, not the one already running.

---

## Run it

```bash
python ~/.claude/ctx-watch.py
```

| Flag | Effect |
|---|---|
| `--once` | Print one frame and exit — good for piping or a cron line |
| `--interval=N` | Refresh every N seconds (default 5) |
| `--since=N` | Only show sessions touched in the last N **minutes** (default 30) |
| `--no-color` | Plain text, for terminals that do not do ANSI |

The layout is built from the terminal width, two short lines per session, so a 40-column side pane
does not wrap into soup. Widen the pane and the bars grow with it.

### A button instead of a command

In VS Code, add a terminal profile so the watcher is one click away in the Terminal pane's `+` menu.
Merge `vscode/settings-snippet.json` into your user `settings.json` and
`vscode/keybindings-snippet.json` into your `keybindings.json` — that binds `Ctrl+Alt+W` as well.
The profile uses `-NoExit`, so `Ctrl+C` leaves you at a prompt to restart it with one arrow key.

The snippets are written for PowerShell on Windows. On macOS or Linux use
`terminal.integrated.profiles.osx` / `.linux` with `"path": "bash"` and
`"args": ["-c", "python ~/.claude/ctx-watch.py"]`.

Why a plain terminal and not the statusline: the custom statusline does not render inside the
extension pane, and it only ever knows about its own session anyway.

---

## Context window sizes

The script knows one model explicitly:

```python
WINDOWS = {"claude-opus-5": 1_000_000}   # observed via /context
WINDOW_DEFAULT = 200_000
```

Anything else is assumed to be 200k and flagged `win?` so you know the percentage is a guess — the
token count itself is always exact. Two ways to fix a wrong guess: add the model id to `WINDOWS`,
or export `CLAUDE_CTX_WINDOW=1000000` before starting the watcher to force a window for the whole
run.

---

## The burn line and `/burn`

`statusline-burn.py` walks every transcript touched in the last 5 hours, **dedupes by
`requestId`** — summing per assistant line inflates the total roughly 1.8x — and prices tokens as
input-equivalents: input x1, cache write x2, cache read x0.1, output x5. It caches a byte offset
per file, so a refresh costs a few milliseconds no matter how large the transcripts get.

Markers on the 10-minute figure: `^` past 1M, `!` past 3M. `agents N/10m` appears if something is
logging subagent spawns to `~/.claude/hooks/state/spawns.jsonl`.

`/burn` is the same number on demand, as a slash command, without opening a terminal.

---

## Limits, stated honestly

- **Session names come from the desktop app.** `~/.claude/sessions/<pid>.json` is written by the
  Claude Code desktop app. In a CLI-only setup the file may not exist; rows then show the first
  eight characters of the session id and everything is reported `x closed`, because there is no pid
  to check.
- **Tested on Windows 11** with the desktop app and VS Code. The POSIX branches are there — `~`
  paths throughout, an `os.kill(pid, 0)` path for non-Windows — but macOS and Linux have not been
  exercised.
- **The percentage is only as good as the window size.** See above.
- **Input-equivalents are not dollars.** The weights approximate relative cost so you can compare
  one hour against another. On a subscription plan, read them as quota pressure, not as a bill.
- **It reads, it never writes** to anything Claude Code owns. The only file it creates is the
  pointer under `~/.claude/hooks/state/live/`, and the hook swallows every exception on purpose —
  a monitoring hook must never be able to break a session.

---

## Troubleshooting

| Symptom | Cause |
|---|---|
| Empty list | No session wrote a transcript in the last 30 minutes. Raise it: `--since=240` |
| No `>` on any row | The hooks are not registered, or you registered them after the session started |
| Every row says `x closed` | `~/.claude/sessions/` has no file for those pids — CLI-only setup, see *Limits* |
| Percentages look wrong, `win?` shown | Unknown model. Add it to `WINDOWS` or set `CLAUDE_CTX_WINDOW` |
| Boxes instead of bars | Terminal has no UTF-8; the script falls back to `#` and `.` when it detects that, force it with `--no-color` and a chcp 65001 shell |
| `burn n/a` in the header | `statusline-burn.py` is not at `~/.claude/statusline-burn.py` |

---

## Related

[**claude-global-rules**](https://github.com/anhtaicn/claude-global-rules) — the global `CLAUDE.md`
this was built alongside, with the measured cost model behind these numbers and
`hooks/agent-fanout-guard.py`, which *stops* a runaway fan-out instead of only showing it to you.
`statusline-burn.py` ships in both repos; it is the same file, so installing both is harmless.

---

## License

MIT — see [LICENSE](LICENSE). No credentials, no personal paths, no telemetry in this repo; copy
it, edit it, pass it on.
