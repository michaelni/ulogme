#!/bin/bash
set -euo pipefail
shopt -s inherit_errexit
umask 077

cd "$(dirname "$0")"

# a day starts at 7am, so late-night activity counts toward the previous day
function _day_start() {
    local t=${1:-$(date +%s)} day
    day=$(date -d "@$t" +%F)
    if (( $(date -d "@$t" +%-H) < 7 )); then
        day=$(date -d "$day -1 day" +%F)
    fi
    date -d "$day 07:00" +%s
}

function _count_key_releases() {
    while true; do
        # the parallel sleep keeps the 9 second window even if showkey exits early
        echo $({ timeout 9 showkey & sleep 9; wait; } | grep -c release) || return
    done
}

function keyfreq() {
    local num logfile
    LANG=en_US.utf8
    mkdir -p logs

    sudo ./ctrl.sh _count_key_releases | while read -r num; do
        logfile="logs/keyfreq_$(_day_start).txt"
        echo "$(date +%s) $num" >> "$logfile"
        echo "logged key frequency: $(date) $num release events detected into $logfile"
    done
}

function _is_private_title() {
    [[ -n "$1" ]] || return 1
    [[ -r private_titles ]] || return 2
    grep -qEf <(grep -vE '^(#|[[:space:]]*$)' private_titles | tr -d '\r') <<< "$1"
}

function _is_loggable_title() {
    local status=0
    _is_private_title "$1" || status=$?
    (( status == 1 )) && return 0
    (( status == 2 )) && echo "private_titles is missing or has an invalid regex, not logging window titles" >&2
    return 1
}

function _is_monitor_off() {
    xset q 2> /dev/null | grep -qE "Monitor is (Off|in Standby|in Suspend)"
}

function _is_screen_locked() {
    _is_monitor_off && return 0

    case "${GDMSESSION:-}" in
        xfce)
            if command -v xfce4-screensaver-command > /dev/null; then
                [[ ! $(xfce4-screensaver-command -q | head -1) =~ "The screensaver is inactive" ]]
            else
                [[ ! $(xscreensaver-command -time | cut -f2 -d: | cut -f2-3 -d' ') =~ "screen non-blanked" ]]
            fi
            ;;
        cinnamon)
            [[ ! $(cinnamon-screensaver-command -q 2> /dev/null) =~ inactive ]]
            ;;
        ubuntu | ubuntu-2d | gnome-shell | gnome-classic | gnome-fallback)
            [[ ! $(gnome-screensaver-command -q 2> /dev/null) =~ inactive ]]
            ;;
        *)
            [[ ${XDG_SESSION_DESKTOP:-} == KDE && $(qdbus org.kde.screensaver /ScreenSaver org.freedesktop.ScreenSaver.GetActive) == true ]]
            ;;
    esac
}

function _active_window_title() {
    local title=$(xdotool getactivewindow getwindowname 2> /dev/null) || true
    echo "${title//[$'\n\r']/ }"
}

function logactivewin() {
    local waittime=2 lasttitle="" curtitle logfile
    LANG=en_US.utf8
    mkdir -p logs
    [[ -e private_titles ]] || cp private_titles.example private_titles
    _is_private_title x || (( $? != 2 )) || { echo "invalid regex in private_titles" >&2; exit 1; }

    while true; do
        if _is_screen_locked; then
            curtitle="__LOCKEDSCREEN"
        else
            curtitle=$(_active_window_title)
        fi

        if [[ "$curtitle" != "$lasttitle" ]] && _is_loggable_title "$curtitle"; then
            logfile="logs/window_$(_day_start).txt"
            echo "$(date +%s) $curtitle" >> "$logfile"
            echo "logged window title: $(date) $curtitle into $logfile"
            lasttitle="$curtitle"
        fi

        sleep "$waittime"
    done
}

function logdesktop() {
    # periodically takes screenshot and saves them to desktopscr/
    # the filename contains unix time

    # wait time in seconds
    waittime="60"
    # directory to save screenshots to
    saveprefix="desktopscr/scr"
    mkdir -p desktopscr

    #------------------------------

    while true; do
        islocked=true; if [[ $(gnome-screensaver-command -q) =~ .*inactive.* ]]; then islocked=false; fi

        if ! $islocked; then
            # take screenshot into file
            T="$(date +%s)"
            fname="${saveprefix}_$T.jpg"
            # q is quality. Higher is higher quality
            scrot -q 50 "$fname"
        else
            echo "screen is locked, waiting..."
        fi

        sleep $waittime
    done
}

function note() {
    local T=${1:-$(date +%s)} n
    mkdir -p logs
    read -rp "Enter note: " n

    local logfile="logs/notes_$(_day_start "$T").txt"
    echo "$T $n" >> "$logfile"
    echo "logged note: $T $n into $logfile"
}

function serve() {
    [[ -e render/render_settings.js ]] || cp render/render_settings_example.js render/render_settings.js
    python3 ulogme.py export
    python3 ulogme.py serve "$@"
}

function _tmux() {
    tmux -L ulogme "$@"
}

function up() {
    local port="${1:-8124}" url

    if _tmux has-session -t ulogme 2> /dev/null; then
        echo "ulogme is already running: tmux -L ulogme attach -t ulogme"
        return 0
    fi

    chmod 700 .

    _tmux new-session -d -s ulogme -n keys -c "$PWD" \
        "echo 'Enter your sudo password if asked, then detach with Ctrl-b d'; ./ctrl.sh keyfreq" \; \
        set-option -g remain-on-exit on
    _tmux new-window -d -t ulogme -n windows -c "$PWD" "./ctrl.sh logactivewin"
    _tmux new-window -d -t ulogme -n web -c "$PWD" "./ctrl.sh serve $port"

    # -k ignores cached credentials, which would not apply inside the tmux pane anyway
    if ! sudo -k -n true 2> /dev/null; then
        _tmux attach -t ulogme:keys
    fi

    for _ in {1..20}; do
        url=$(_tmux capture-pane -J -p -t ulogme:web | grep -o 'http://[^ ]*' || true)
        [[ -n "$url" ]] && break
        sleep 0.1
    done
    echo "web UI: ${url:-not available yet, check: tmux -L ulogme attach -t ulogme:web}"
    echo "inspect: tmux -L ulogme attach -t ulogme"
}

function down() {
    if _tmux kill-session -t ulogme 2> /dev/null; then
        echo "ulogme stopped"
    else
        echo "ulogme was not running"
    fi
}

"$@"
