"""Render captured HTTP responses. Token decoding here is for display only."""
import base64
import json
from html import escape
from pathlib import Path

def decode(token,part):
    return json.loads(base64.urlsafe_b64decode(token.split(".")[part]+"==="))

def code(value):
    text=value if isinstance(value,str) else json.dumps(value,indent=2)
    return "<pre><code>"+escape(text)+"</code></pre>"

def http(r):
    location = "\nLocation: "+r["headers"]["Location"] if "Location" in r.get("headers",{}) else ""
    location += "\nWWW-Authenticate: "+r["headers"]["WWW-Authenticate"] if "WWW-Authenticate" in r.get("headers",{}) else ""
    return code(f'HTTP/{r["http_version"]} {r["status"]} {r["reason"]}\nContent-Type: {r["content_type"]}{location}\n\n'+json.dumps(r["body"],indent=2))

def token_panel(r):
    token=r["body"]["access_token"]
    return "<h4>Token payload (decoded JWT)</h4>"+code(decode(token,1))

def render(lab):
    def form(action,body):
        return f'<form method="post" action="/{action}"><input type="hidden" name="nonce" value="{lab.nonce}">'+body+"</form>"
    options=""
    for name,title,action in (("calendar-agent","Calendar Agent","create_calendar_event"),("email-agent","Email Agent","send_email")):
        selected="checked" if name in lab.selected else ""
        options+=f'<label><input type="checkbox" name="allow" value="{name}" {selected}><span><b>{title}</b><small>{action}</small></span></label>'
    inputs=(f'<div class="task-fields"><label>Candidate email<input type="email" name="email" required maxlength="254" value="{escape(lab.email,quote=True)}"></label>'
            f'<label>Interview start (ISO 8601 with UTC offset)<input type="text" name="start" required value="{escape(lab.start,quote=True)}"></label></div>')
    consent=form("approve",inputs+'<div class="permission-options">'+options+'</div><button>Submit decision</button>')
    results=""
    if lab.round:
        results=f'<section id="trace"><h2>Authorization trace <small>Run {lab.round}</small></h2>'
        if not lab.batch:
            results+="<article>Consent declined. No Batch Token was issued.</article>"
        else:
            results+='<article><header><h3>Leader · Batch Token</h3><em>Issued</em></header>'+token_panel(lab.batch)+'</article>'
            for name,r in lab.work.items():
                ok=r["exchange"]["status"]==200
                title="Calendar Agent" if name=="calendar-agent" else "Email Agent"
                results+=f'<article><header><h3>{title}</h3><em class="{"" if ok else "deny"}">{"Granted" if ok else "Denied"}</em></header><p>Process {r["pid"]} · Target <code>{escape(r["target"])}</code></p>'
                if ok:
                    path="/events" if name=="calendar-agent" else "/messages"
                    results+='<h4>Downscoped access token</h4>'+token_panel(r["exchange"])
                    results+=f'<h4>Resource response · POST {path}</h4>'+http(r["resource"])
                else:
                    results+='<h4>Exchange response · POST /token</h4>'+http(r["exchange"])+"<p>No resource request was sent.</p>"
                results+="</article>"
            if len(lab.selected)==2:
                results+='<article id="probe"><h3>Test the delegation boundary</h3><p>Calendar Agent sends its existing calendar access token to the Email resource server. The token audience does not match.</p>'+form("probe","<button>Try wrong-token resource access</button>")
                if lab.probe:
                    results+='<h4>Email RS response · POST /messages</h4>'+http(lab.probe["resource"])
                results+="</article>"
        results+="</section>"
    return (Path(__file__).with_name("page.html").read_text(encoding="utf-8")
            .replace("<!--EMAIL-->",escape(lab.email)).replace("<!--TIME-->",escape(lab.start)).replace("<!--CONSENT-->",consent).replace("<!--TRACE-->",results))
