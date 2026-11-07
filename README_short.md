# ulogme cheat sheet

## Start / stop

```bash
./ctrl.sh up          # start everything in the background, prints the web UI URL
./ctrl.sh up 8125     # same, web UI on another port
./ctrl.sh down        # stop everything
```

If sudo needs a password, `up` opens tmux: type the password, then detach with `Ctrl-b d`.

## Web UI

- Open the URL printed by `up` (`http://localhost:8124/auth-token-.../index.html`).
- The token is the `render/auth-token-*` symlink. Delete it to get a new one on the next start.
- Click the refresh button (top right) to load new activity.
- Click a bar to add a note; click the text area on top to write a summary of the day.
- `Overview` compares days.

## Inspect running processes

```bash
tmux -L ulogme attach -t ulogme          # windows: keys, windows, web
tmux -L ulogme attach -t ulogme:web      # jump straight to one window
```

`Ctrl-b n` / `Ctrl-b p` next/previous window, `Ctrl-b d` detach. Crashed windows stay open and show their error.

## Other commands

```bash
./ctrl.sh note [unix_time]     # add a note from the terminal
./ctrl.sh export_events        # rebuild render/*.json from logs/
./ctrl.sh serve [port]         # web UI only, in the foreground
./ctrl.sh logactivewin         # window logger only, in the foreground
sudo ./ctrl.sh keyfreq         # keystroke logger only, in the foreground
```

## Files

| Path | What |
|---|---|
| `logs/` | All recorded data. Keep it on a volume. |
| `render/render_settings.js` | Map window titles to categories (`title_mappings`, `display_groups`, `hacking_titles`). Changes apply to past days too. |
| `private_titles` | Regexes of window titles never to log, one per line. |

Find your most common window titles to write mappings:

```bash
cut -d' ' -f2- logs/window_*.txt | sort | uniq -c | sort -rn | head -40
```

Or ask Claude Code to do it:

```
Run mapwin() from render/render_settings.js over all titles in logs/window_*.txt
and list the ones that land in MISC. Add rules for them to title_mappings (reuse
existing categories, or create new ones and add them to display_groups;
add work ones to hacking_titles). Keep existing categories. Re-run until MISC is empty.
```

## Good to know

- A day starts at 7am; late-night work counts toward the previous day.
- Dependencies: `python3 tmux xdotool wmctrl kbd x11-xserver-utils`.
- Time with the monitor off (`xset dpms force off`, or DPMS timeout) is logged as `Locked Screen`. Screensaver-based lock detection doesn't work in the container, so other time away counts toward the last focused window.
