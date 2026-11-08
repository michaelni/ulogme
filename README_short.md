# ulogme

```bash
./ctrl.sh up [port]            # start everything, prints the web UI URL (default port 8124)
./ctrl.sh down                 # stop everything
tmux -L ulogme attach -t ulogme   # inspect the keys / windows / web loggers; Ctrl-b d detaches
```

If sudo needs a password, `up` opens tmux: type it, then `Ctrl-b d`.

## Web UI

- Refresh button (top right) loads new activity. Click a bar to add a note, the top text area for a day summary.
- New URL token: delete the `render/auth-token-*` symlink and restart.
- `Hacking Streak`: ~2.5+ min of steady typing (3+ keys per 9 s) in a `hacking_titles` window. Ends after ~100 s idle or elsewhere. Bar height = keys/s.

## Files

| Path | What |
|---|---|
| `logs/` | All recorded data. Keep it on a volume. |
| `render/render_settings.js` | Window title → category rules (`title_mappings`, `display_groups`, `hacking_titles`). Applies to past days too. |
| `private_titles` | Regexes of window titles never to log. |

Most common window titles, for writing rules:

```bash
cut -d' ' -f2- logs/window_*.txt | sort | uniq -c | sort -rn | head -40
```

Or ask Claude Code:

```
Map every title in logs/window_*.txt with mapwin() from render/render_settings.js
and add title_mappings rules until nothing lands in MISC.
```

Window titles are untrusted input: any web page or file name sets its own title, and a title can contain instructions aimed at an agent ("ignore previous instructions and run ..."). Review the commands Claude Code proposes and don't auto-approve shell commands while it reads the logs.

## Good to know

- A day starts at 7am; late-night work counts toward the previous day.
- Dependencies: `python3 tmux xdotool kbd x11-xserver-utils`.
- Monitor off (DPMS) is logged as `Locked Screen`; other time away counts toward the last focused window.
