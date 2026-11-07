import socketserver
import http.server
import datetime
import secrets
import string
import subprocess
import sys
import urllib.parse
import re
import os

from export_events import updateEvents
from pathlib import Path
from rewind7am import rewindTime

# Port settings
IP = "127.0.0.1"
if len(sys.argv) > 1:
  PORT = int(sys.argv[1])
else:
  PORT = 8124

# serve render/ folder, not current folder
rootdir = os.getcwd()
os.chdir('render')

#search old symlinks in render
for entry in Path(".").iterdir():
    if entry.is_symlink():
        print(f"found symlink {entry}")
        pathtoken = str(entry)

        if False: # generate a new random symlink each time
            print(f"deleting symlink {entry}")
            entry.unlink()
            del pathtoken

if "pathtoken" not in globals():
    pathtoken = "auth-token-" + "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))

    print(f"Creating random symlink: {pathtoken}")
    print("You can delete this link whenever you like, a new random one will be created on the next run")
    try:
        os.symlink(".", pathtoken, target_is_directory=True)
    except PermissionError as e:
        print(e)
        print(f"Cannot create random symlink {pathtoken}, likely windows without devmode.")
        print("please manually create a symlink named auth-token-<random alphanumeric> in render/ that points back to render/; this will serve as an authentication key in the URL")
        exit(1)

pathtoken = "/" + pathtoken

# Custom handler
class CustomHandler(http.server.SimpleHTTPRequestHandler):
  def parse_request(self):
    if not super().parse_request():
      return False

    if self.path == pathtoken or re.fullmatch(pathtoken + r"/[^/]*", self.path):
      sfs = self.headers.get("Sec-Fetch-Site")
      if sfs == "none" and self.command == "GET":
        if self.path == pathtoken or self.path.endswith("html"):
          return True
      elif sfs == "same-origin":
        return True

    print(f"Unpermitted request: {datetime.datetime.now()} Sender: {self.client_address} path: {self.path} command: {self.command} headers: {self.headers}")
    return False

  def do_GET(self):
    # default behavior
    assert(pathtoken in self.path)

    http.server.SimpleHTTPRequestHandler.do_GET(self)

  def read_form(self):
    length = int(self.headers.get('Content-Length', 0))
    body = self.rfile.read(length).decode('utf-8')
    return {key: values[0] for key, values in urllib.parse.parse_qs(body).items()}

  def do_POST(self):
    assert(pathtoken in self.path)

    form = self.read_form()
    result = 'NOT_UNDERSTOOD'

    if self.path == pathtoken + '/refresh':
      # recompute jsons. We have to pop out to root from render directory
      # temporarily. It's a little ugly
      refresh_time = form.get('time')
      os.chdir(rootdir) # pop out
      updateEvents() # defined in export_events.py
      os.chdir('render') # pop back to render directory
      result = 'OK'
      
    if self.path ==  pathtoken + '/addnote':
      # add note at specified time and refresh
      note = form.get('note') or ''
      note_time = int(form.get('time'))
      os.chdir(rootdir) # pop out
      subprocess.run(['./note.sh', str(note_time)], input=note + '\n', text=True)
      updateEvents() # defined in export_events.py
      os.chdir('render') # go back to render
      result = 'OK'

    if self.path == pathtoken + '/blog':
      # add note at specified time and refresh
      post = form.get('post')
      if post is None: post = ''
      post_time = int(form.get('time'))
      os.chdir(rootdir) # pop out
      trev = rewindTime(post_time)
      open('logs/blog_%d.txt' % (post_time, ), 'w').write(post)
      updateEvents() # defined in export_events.py
      os.chdir('render') # go back to render
      result = 'OK'
    
    self.send_response(200)
    self.send_header('Content-type','text/html')
    self.end_headers()
    self.wfile.write(result.encode('utf-8'))

httpd = socketserver.ThreadingTCPServer((IP, PORT), CustomHandler)

print('Serving ulogme, see it on http://localhost:' + repr(PORT) + pathtoken + "/index.html")
httpd.serve_forever()

