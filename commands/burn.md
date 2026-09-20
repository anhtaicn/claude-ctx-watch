---
description: Quota burned across ALL sessions on this machine, last 5h / 10m
allowed-tools: Bash(echo:*), Bash(python:*)
---

Current burn rate (input-equivalent tokens, deduped by `requestId`):

!`echo '{}' | python __CLAUDE_HOME__/statusline-burn.py`

Read the number above and report it back in ONE line, including the warning if present:

- `^` = the last 10m crossed 1M input-equivalent tokens -> running hot, avoid spawning subagents.
- `!` = the last 10m crossed 3M -> stop fanning out now.
- `agents N/10m` = how many Agent/Task spawns happened in the last 10 minutes.

Run no other command. Read no other file.
