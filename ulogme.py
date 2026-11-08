import datetime
import http.server
import json
import os
import re
import secrets
import socketserver
import string
import subprocess
import sys
import threading
import urllib.parse
from pathlib import Path

# Unicode / legacy line separators that splitlines() would treat as line breaks
BAD_LINE_SEPARATORS = {
    ord('\r'): None,
    ord('\v'): None,
    ord('\f'): None,
    ord('\x1c'): None,
    ord('\x1d'): None,
    ord('\x1e'): None,
    ord('\x85'): None,
    ord('\u2028'): None,  # LINE SEPARATOR
    ord('\u2029'): None,  # PARAGRAPH SEPARATOR
}

os.umask(0o077)

ROOT = Path(__file__).resolve().parent
RENDER_ROOT = ROOT / 'render'
LOGS_ROOT = ROOT / 'logs'
TOKEN_PATTERN = re.compile(r'auth-token-[A-Za-z0-9]{32,}')
MAX_FORM_BYTES = 1 << 20
SECURITY_HEADERS = {
  'Cache-Control': 'no-store',
  'X-Content-Type-Options': 'nosniff',
  # d3 and spin.js set style attributes, and the pages use inline scripts and onload handlers
  'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'",
}


def loadEvents(fname):
  """
  Reads a file that consists of first column of unix timestamps
  followed by arbitrary string, one per line.
  """
  try:
    ws = open(fname, 'r').read().translate(BAD_LINE_SEPARATORS).splitlines()
  except FileNotFoundError:
    print(f' {fname} not found, setting empty events list')
    return []
  events = []
  for w in ws:
    ix = w.find(' ') # find first space, that's where stamp ends
    events.append({'t': int(w[:ix]), 's': w[ix+1:]})
  return events


def mtime(f):
  """
  return time file was last modified, or 0 if it doesnt exist
  """
  if os.path.isfile(f):
    return os.path.getmtime(f)
  return 0


def updateEvents():
  """
  goes down the list of .txt log files and writes all .json
  files that can be used by the frontend
  """
  L = []
  L.extend(LOGS_ROOT.glob("keyfreq_[0-9]*.txt"))
  L.extend(LOGS_ROOT.glob("window_[0-9]*.txt"))
  L.extend(LOGS_ROOT.glob("notes_[0-9]*.txt"))

  # extract all times. all log files of form {type}_{stamp}.txt
  ts = sorted(set(int(p.stem.split('_')[1]) for p in L))
  if not ts:
    return

  os.makedirs(RENDER_ROOT, exist_ok=True)
  out_list = []
  for t0 in ts:
    t1 = t0 + 60*60*24 # 24 hrs later
    fout = 'events_%d.json' % (t0, )
    out_list.append({'t0':t0, 't1':t1, 'fname': fout})

    fwrite = RENDER_ROOT / fout
    e1f = LOGS_ROOT / f'window_{t0}.txt'
    e2f = LOGS_ROOT / f'keyfreq_{t0}.txt'
    e3f = LOGS_ROOT / f'notes_{t0}.txt'
    e4f = LOGS_ROOT / f'blog_{t0}.txt'

    # if the log files have not changed there is no need to regen
    if os.path.isfile(fwrite):
      tmod = mtime(fwrite)
      if not any(mtime(f) > tmod for f in (e1f, e2f, e3f, e4f)):
        continue
      print(f'a log file has changed, so will update {fwrite}')

    e1 = loadEvents(e1f)
    e2 = loadEvents(e2f)
    e3 = loadEvents(e3f)
    for k in e2: k['s'] = int(k['s']) # int convert

    e4 = ''
    if os.path.isfile(e4f):
      e4 = open(e4f, 'r').read()

    eout = {'window_events': e1, 'keyfreq_events': e2, 'notes_events': e3, 'blog': e4}
    open(fwrite, 'w').write(json.dumps(eout))
    print(f'wrote {fwrite}')

  fwrite = RENDER_ROOT / 'export_list.json'
  open(fwrite, 'w').write(json.dumps(out_list))
  print(f'wrote {fwrite}')


def authToken():
  """
  the render/auth-token-* symlink name is the secret part of the URL; reuse it or create one
  """
  for entry in RENDER_ROOT.iterdir():
    if entry.is_symlink() and entry.name.startswith("auth-token-"):
      if not TOKEN_PATTERN.fullmatch(entry.name):
        sys.exit(f"{entry} is not a safe token: it needs 32+ letters or digits after auth-token-. Delete it and restart to create a new one.")
      print(f"found symlink {entry}")
      return entry.name

  token = "auth-token-" + "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
  print(f"Creating random symlink: {token}")
  print("You can delete this link whenever you like, a new random one will be created on the next run")
  try:
    os.symlink(".", RENDER_ROOT / token, target_is_directory=True)
  except PermissionError as e:
    print(e)
    print(f"Cannot create random symlink {token}, likely windows without devmode.")
    print("please manually create a symlink named auth-token-<random alphanumeric> in render/ that points back to render/; this will serve as an authentication key in the URL")
    sys.exit(1)
  return token


def serve(port):
  pathtoken = "/" + authToken()
  allowed_path = re.compile(re.escape(pathtoken) + r"(/[^/]*)?")
  allowed_hosts = {f"localhost:{port}", f"127.0.0.1:{port}"}
  update_lock = threading.Lock()

  def thenUpdate(fn):
    with update_lock:
      fn()
      updateEvents()

  def writeBlog(post_time, post):
    with open(LOGS_ROOT / f'blog_{post_time}.txt', 'w') as f:
      f.write(post)

  class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
      super().__init__(*args, directory=RENDER_ROOT, **kwargs)

    def parse_request(self):
      if not super().parse_request():
        return False

      if self.headers.get("Host") in allowed_hosts and allowed_path.fullmatch(self.path):
        sfs = self.headers.get("Sec-Fetch-Site")
        if sfs == "none" and self.command == "GET":
          if self.path == pathtoken or self.path.endswith("html"):
            return True
        elif sfs == "same-origin":
          return True

      print(f"Unpermitted request: {datetime.datetime.now()} Sender: {self.client_address} path: {self.path!r} command: {self.command!r} headers: {dict(self.headers)!r}")
      return False

    def end_headers(self):
      for name, value in SECURITY_HEADERS.items():
        self.send_header(name, value)
      super().end_headers()

    def do_GET(self):
      assert(pathtoken in self.path)
      http.server.SimpleHTTPRequestHandler.do_GET(self)

    def form_length(self):
      try:
        length = int(self.headers.get('Content-Length', 0))
      except ValueError:
        return None
      return length if 0 <= length <= MAX_FORM_BYTES else None

    def read_form(self, length):
      body = self.rfile.read(length).decode('utf-8')
      return {key: values[0] for key, values in urllib.parse.parse_qs(body).items()}

    def do_POST(self):
      assert(pathtoken in self.path)

      length = self.form_length()
      if length is None:
        self.send_error(413, f"Content-Length must be between 0 and {MAX_FORM_BYTES}")
        return
      form = self.read_form(length)
      result = 'NOT_UNDERSTOOD'

      if self.path == pathtoken + '/refresh':
        thenUpdate(lambda: None)
        result = 'OK'

      if self.path == pathtoken + '/addnote':
        note = form.get('note') or ''
        note_time = int(form.get('time'))
        thenUpdate(lambda: subprocess.run([ROOT / 'ctrl.sh', 'note', str(note_time)], input=note + '\n', text=True))
        result = 'OK'

      if self.path == pathtoken + '/blog':
        post = form.get('post') or ''
        post_time = int(form.get('time'))
        thenUpdate(lambda: writeBlog(post_time, post))
        result = 'OK'

      self.send_response(200)
      self.send_header('Content-type','text/html')
      self.end_headers()
      self.wfile.write(result.encode('utf-8'))

  socketserver.ThreadingTCPServer.allow_reuse_address = True
  httpd = socketserver.ThreadingTCPServer(("127.0.0.1", port), CustomHandler)

  print('Serving ulogme, see it on http://localhost:' + repr(port) + pathtoken + "/index.html")
  httpd.serve_forever()


if __name__ == '__main__':
  command = sys.argv[1] if len(sys.argv) > 1 else ''
  if command == 'export':
    updateEvents()
  elif command == 'serve':
    serve(int(sys.argv[2]) if len(sys.argv) > 2 else 8124)
  else:
    sys.exit('usage: python3 ulogme.py export | serve [port]')
