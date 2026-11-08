
# ulogme

## Fork differences

The original https://github.com/karpathy/ulogme has a few bugs and is since 10 years sadly unmaintained.
I need to figure out why i cant get more work done per day and so i needed to fix this :)

Pull requests are welcome!

This fixes:
- python 3 support (taken from fork of Fedor Chervinskii)
- xfce4-screensaver support
- Fix window title logging on Cinnamon 18 (by Ilija Ilievski)
- not storing detailed keypresses to disk, the intermediate file with detailed keypressed is no more
- minor bugfixes
- python 3.13+ support (no longer uses the removed cgi module)

This adds:
- `ctrl.sh`: a single entry point for all commands (`./ctrl.sh <command>`), replacing the separate shell scripts
- private_titles file (simple list of window titles you want never logged; created from private_titles.example on first run, not tracked by git)
- basic path based authentication (enabled by default)
- basic Sec-Fetch-Site / same-origin checks

## Original README: (with links updated)

> ### How productive were you today? How much code have you written? Where did your time go?

Keep track of your computer activity throughout the day: visualize your active window titles and the number of keystrokes in beautiful HTML timelines. Current features:

- Records your **active window** title throughout the day
- Records the **frequency of key presses** throughout the day
- Record custom **note annotations** for particular times of day, or for day in general
- Everything runs **completely locally**: none of your data is uploaded anywhere
- **Beautiful, customizable UI** in HTML/CSS/JS (d3js).

The project currently **only works on Ubuntu and OSX**, and uses new fancy **Promises** feature of ECMAScript 6. This might not be implemented in all browsers. My Chrome has it, but for example my Firefox doesn't.

## Demo

See a blog post (along with multiple screenshots) describing the project [here.](http://karpathy.github.io/2014/08/03/quantifying-productivity/)

## Getting Started

**To start recording**

1. Clone the repository to some folder: `$ git clone https://github.com/michaelni/ulogme.git`
2. Make sure you have Python 3 (`python3`); ulogme does not support Python 2. If you're on Ubuntu, make sure you have the dependencies: `$ sudo apt-get install python3 xdotool kbd x11-xserver-utils` (`kbd` provides `showkey`, `x11-xserver-utils` provides `xset`, used to treat a turned-off monitor as a locked screen). On Fedora, you may also need `sudo yum install gnome-screensaver`.
3. `cd` inside and run `$ ./ctrl.sh up` on Linux, or `$ ./osx/run_ulogme_osx.sh` on OSX (on Linux this needs sudo for the `showkey` command). This starts two recorders in the background. One records the frequency of keystrokes and the other records active window titles. Both write their logs into log files in the `logs/` directory. Every log file is very simply just the unix time stamp followed by data, one per line. You can also start them separately with `$ ./ctrl.sh keyfreq` and `$ ./ctrl.sh logactivewin`. Only `showkey` runs as root; `keyfreq` asks for sudo itself and writes the logs as your user. `up` makes the ulogme folder private (`chmod 700`), and new files are created readable only by you.

   `up` also starts the web UI, all in a background tmux session (requires `tmux`), and returns your terminal; `$ ./ctrl.sh down` stops everything. If sudo needs a password, `up` opens the tmux window of the keystroke logger: type your password there, then detach with `Ctrl-b d` and `up` continues. To look at the running processes later, use `$ tmux -L ulogme attach -t ulogme`.
4. For **OSX** only: there might be an additional step where you have to go to System Preferences > Security & Privacy > Accessibility, and make sure that Terminal (or iTerm2, or whatever you use to launch ulogme) is checked. If it wasn't checked previously and you just checked it, you may need to restart ulogme. If you don't do this step, you might find that window logging works but keypress logging doesn't.
5. As of Mac OS 10.14 there is an additional permission that needs to be granted to the shell script in order to count keystrokes. To do so, go to System Preferences > Security & Privacy > Input Monitoring, add ulogme/osx/dist/ulogme_osx and make sure it is checked off. Lock the settings, and restart the script and keystrokes should begin to get recorded.

**The user interface**

1. On its first start, `./ctrl.sh serve` (or `up`) creates your own settings file `render/render_settings.js` from `render/render_settings_example.js`. In this file modify everything to your own preferences. Follow the provided example to specify title mappings: A raw window title comes in, and we match it against regular expressions to determine what type of activity it is. For example, the code would convert "Google Chrome - some cool website" into just "Google Chrome". Follow the provided example and read the comments for all settings in the file.
2. Once that's set up, start the web server viewer: `$ ./ctrl.sh serve`, and go to the address it prints (for example `http://localhost:8124/auth-token-.../index.html`) in your browser. Hit the refresh button on top right every time you'd like to refresh the results based on most recently recorded activity
3. If your data isn't loading, try to explicitly run `$ python3 ulogme.py export` and then hit refresh. This should only be an issue the very first time you run ulogme.

## ctrl.sh commands

Run every command from the repository root as `./ctrl.sh <command>`:

| Command | What it does |
|---|---|
| `up [port]` | Start keystroke logging, window logging and the web UI in a background tmux session, then print the web UI address |
| `down` | Stop everything started by `up` |
| `keyfreq` | Record keystroke frequency (asks for sudo to run `showkey`) |
| `logactivewin` | Record active window titles |
| `logdesktop` | Take a screenshot every minute into `desktopscr/` (needs `scrot`) |
| `note [time]` | Add a note for now, or for the given unix time |
| `serve [port]` | Start the web UI (default port 8124) |

## User Interface

The user interface can switch between a single day view and an overview view by link on top. You have to hit the refresh button every time you'd like to pull in new data.

#### Single day page

- You can enter a reminder "blog" on top if you'd like to summarize the day for yourself or enter other memos.
- Click on any bar in the *barcode view* to enter a custom (short) note snippet for the time when the selected activity began. I use this to mark meetings, track my coffee/food intake, sleep time, or my total time spent running/swimming/gym or to leave notes for certain patterns of activity, etc. These could all later be correlated with various measures of productivity, in future.

#### Overview page

- You can click the window titles to toggle them on and off from the visualization 
- Clicking on the vertical bars takes you to the full statistics for that day.

## Known issues
- One Ubuntu user reported broken view with no data. On further inspection we found that the logs were corrupt. One of the lines in a file in `/logs` was, instead of looking as `{timestamp} {data}`  looked as `@@@@@@@{timestamp} {data}`, in other words an odd character was appended to the timestamp somehow. We manually erased these characters from the log file to fix the issue.
- You may see *"address already in use"* if you try to run `./ctrl.sh serve`. Sometimes the system can get confused and takes a while to update what ports are being used. Use the optional argument to specify a different port, for example `./ctrl.sh serve 8125` and then go to `http://localhost:8125/auth-token-.../index.html` instead, for example.
- Overview page is blank. Are you sure your browser supports ECMAScript 6? Chrome should be fine, Firefox might not be, yet. 

## Contributing

The Ubuntu and OSX code base are a little separate on the data collection side. However, they each just record very simple log files in `/logs`. Once the log files are written, `ulogme.py export` takes the log files, does some simple processing and writes the results into `.json` files in `/render`. The Javascript/HTML/CSS UI codebase is all common and all lives in `/render`.

### Ubuntu
ulogme has three main parts: 

1. Recording functions `keyfreq` and `logactivewin` in `ctrl.sh`. You probably won't touch these.
2. Webserver: `ulogme.py serve` which wraps Python's `SimpleHTTPServer` and does some basic communication with the UI. For example, the UI can ask the server to write a note to a log file, or for a refresh.
3. The UI. Majority of the codebase is here, reading the `.json` files in `/render` and creating the visualizations. There are several common `.js` files, and crucially the `index.html` and `overview.html` files. I expect that most people might be able to contribute here to add features/cleanup/bugfix.

### OSX code
Things get a little ugly in OSX if you want to change anything with recording the log files because you have to recompile these portions any time you make any changes. It's ugly and it had to be done. However, if you're only interested in hacking with the UI, just change Javascript in `render` and no recompile is necessary, naturally.

## Related projects

* [selfspy](https://github.com/gurgeh/selfspy), Log everything you do on the computer, for statistics, future reference and all-around fun.
* [arbtt](http://freecode.com/projects/arbtt), automatic rule-based time tracker.

For more projects, [this question on Personal Productivity Stack Exchange](https://productivity.stackexchange.com/questions/13913/automatic-time-tracking-software-for-computer-work-for-windows-linux-mac) might be also worth a look.

## License
MIT
