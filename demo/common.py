"""Shared loopback HTTP transport. No third-party packages required."""
import base64
import json
import secrets
import signal
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlencode
from urllib.request import Request, build_opener, ProxyHandler

EXCHANGE = "urn:ietf:params:oauth:grant-type:token-exchange"
JWT = "urn:ietf:params:oauth:token-type:jwt"
ACCESS = "urn:ietf:params:oauth:token-type:access_token"
CAL = "urn:interview-lab:calendar"
MAIL = "urn:interview-lab:mail"
ITEMS = [
    {"type":"calendar", "actions":["create_calendar_event"], "locations":[CAL], "may_act":{"sub":"calendar-agent"}},
    {"type":"email", "actions":["send_email"], "locations":[MAIL], "may_act":{"sub":"email-agent"}}
]
def uid():
    return secrets.token_urlsafe(20)

def basic(name, secret):
    return "Basic " + base64.b64encode((name + ":" + secret).encode()).decode()

def post(url, data, auth):
    req = Request(url, data=urlencode(data).encode(), headers={"Authorization":auth})
    opener = build_opener(ProxyHandler({}))
    try:
        response = opener.open(req, timeout=8)
    except HTTPError as error:
        response = error
    with response:
        return {"status":response.status, "reason":response.reason,
                    "http_version":{10:"1.0",11:"1.1"}[response.version],
                    "headers":dict(response.headers.items()), "content_type":response.headers["Content-Type"], "body":json.load(response)}

def require(condition, status, message):
    if not condition:
        raise Rejection(status, message)

class Rejection(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message

def service(ready, process):
    # The launcher handles Ctrl+C and terminates its child services.
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def do_POST(self):
            try:
                size = int(self.headers.get("Content-Length",0))
                require(0 <= size <= 32768, 413, "request_too_large")
                fields = {k:v[0] for k,v in parse_qs(self.rfile.read(size).decode()).items()}
                status, body = process(self.path, self.headers.get("Authorization",""), fields)
            except Rejection as error:
                status, body = error.status, {"error":error.message}
            except (KeyError, ValueError, TypeError):
                status, body = 400, {"error":"invalid_request"}
            payload = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type","application/json")
            self.send_header("Cache-Control","no-store")
            self.send_header("Pragma","no-cache")
            if status==201 and "id" in body:
                self.send_header("Location",self.path+"/"+body["id"])
            if status==401:
                challenge = 'Basic realm="token"' if body.get("error")=="invalid_client" else 'Bearer error="invalid_token"'
                self.send_header("WWW-Authenticate",challenge)
            if status==403 and body.get("error")=="insufficient_scope":
                self.send_header("WWW-Authenticate",'Bearer error="insufficient_scope"')
            self.send_header("Content-Length",str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
    with HTTPServer(("127.0.0.1",0),Handler) as http:
        ready.send("http://127.0.0.1:"+str(http.server_port))
        ready.close()
        http.serve_forever()
