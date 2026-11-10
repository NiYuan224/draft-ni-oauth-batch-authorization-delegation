"""Start here: python leader_agent.py"""
import argparse
import json
import multiprocessing as mp
import os
import re
from contextlib import ExitStack
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs
import authorization_server, calendar_agent, email_agent, calendar_server, email_server
from common import CAL, MAIL, ITEMS, basic, post, uid
from view import render

NAMES=("calendar-agent","email-agent")

class Leader:
    def __init__(self, cleanup):
        self.cleanup=cleanup
        self.round=0
        self.nonce=uid()
        self.batch=None
        self.work={}
        self.probe=None
        self.selected=list(NAMES)
        clients={n:uid() for n in ("leader",)+NAMES}
        self.auth=basic("leader",clients["leader"])
        self.consent_key=uid()
        self.email="candidate@example.test"
        validators={CAL:uid(),MAIL:uid()}
        self.as_url=self.launch(authorization_server.start,clients,self.consent_key,validators)
        self.workers={}
        resources={CAL:self.launch(calendar_server.start,self.as_url,validators[CAL]),
                   MAIL:self.launch(email_server.start,self.as_url,validators[MAIL])}
        for name,audience,rs,worker in zip(NAMES,(CAL,MAIL),(calendar_server,email_server),(calendar_agent,email_agent)):
            resource=resources[audience]
            dispatch=uid()
            extra=(resources[MAIL],) if name=="calendar-agent" else ()
            endpoint=self.launch(worker.start,self.as_url,resource,clients[name],dispatch,*extra)
            self.workers[name]=(endpoint,dispatch)
        today=datetime.now().astimezone()
        friday=today+timedelta(days=(4-today.weekday())%7)
        self.start=friday.replace(hour=14,minute=0,second=0,microsecond=0)
        if self.start<=today:
            self.start+=timedelta(days=7)
        self.start=self.start.isoformat()

    def launch(self, function, *args):
        ctx=mp.get_context("spawn")
        reader,writer=ctx.Pipe(duplex=False)
        process=ctx.Process(target=function,args=(writer,)+args,daemon=True)
        process.start()
        writer.close()
        def stop():
            process.terminate()
            process.join()
        self.cleanup.callback(stop)
        with reader:
            if not reader.poll(15):
                raise RuntimeError("Service startup timed out: "+function.__module__)
            return reader.recv()

    def dispatch(self,name,target):
        url,key=self.workers[name]
        response=post(url+"/task",{"batch":self.batch["body"]["access_token"],"resource":target,
                                   "start":self.start,"email":self.email},"Bearer "+key)
        if response["status"]!=200:
            raise RuntimeError("Worker dispatch failed")
        return response["body"]

    def set_task(self, email, start):
        email=email.strip()
        if len(email)>254 or not re.fullmatch(r"[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+",email):
            raise ValueError("Enter a valid candidate email address.")
        try:
            parsed=datetime.fromisoformat(start)
        except ValueError:
            raise ValueError("Use an ISO 8601 date and time with a UTC offset.") from None
        if parsed.tzinfo is None:
            raise ValueError("Include a UTC offset, for example +08:00.")
        self.email,self.start=email,parsed.isoformat()

    def approve(self,selected):
        self.selected=selected
        self.round+=1
        self.batch,self.probe,self.work=None,None,{}
        self.nonce=uid()
        request=post(self.as_url+"/authorize",{"authorization_details":json.dumps(ITEMS)},self.auth)
        decision=post(self.as_url+"/consent",{"request_id":request["body"]["request_id"],
                      "selected":json.dumps(selected)},"Bearer "+self.consent_key)
        if not selected:
            return
        self.batch=post(self.as_url+"/token",{"grant_type":"authorization_code","code":decision["body"]["code"]},self.auth)
        for name,target in zip(NAMES,(CAL,MAIL)):
            self.work[name]=self.dispatch(name,target)

    def test_boundary(self):
        url,key=self.workers["calendar-agent"]
        self.probe=post(url+"/probe",{"token":self.work["calendar-agent"]["exchange"]["body"]["access_token"],
                                    "email":self.email},"Bearer "+key)["body"]

def serve(lab,port):
    class Page(BaseHTTPRequestHandler):
        def log_message(self,*args):
            pass
        def do_GET(self):
            if self.path!="/" or self.headers.get("Host")!=self.server.host:
                return self.send_error(404)
            body=render(lab).encode()
            self.send_response(200)
            self.send_header("Content-Type","text/html; charset=utf-8")
            self.send_header("Cache-Control","no-store")
            self.send_header("X-Frame-Options","DENY")
            self.end_headers()
            self.wfile.write(body)
        def do_POST(self):
            if self.headers.get("Host")!=self.server.host or self.headers.get("Origin") not in (None,"http://"+self.server.host):
                return self.send_error(403)
            size=int(self.headers.get("Content-Length","0"))
            if not 0<=size<=4096:
                return self.send_error(413)
            form=parse_qs(self.rfile.read(size).decode())
            if form.get("nonce")!=[lab.nonce]:
                return self.send_error(409,"Reload the page and try again")
            if self.path=="/approve":
                try:
                    lab.set_task(form.get("email",[""])[0],form.get("start",[""])[0])
                except ValueError as error:
                    return self.send_error(400,str(error))
                lab.approve([n for n in NAMES if n in form.get("allow",[])])
            elif self.path=="/probe" and len(lab.selected)==2 and lab.batch:
                lab.test_boundary()
            else:
                return self.send_error(400)
            self.send_response(303)
            self.send_header("Location","/#probe" if self.path=="/probe" else "/#trace")
            self.end_headers()
    with HTTPServer(("127.0.0.1",port),Page) as server:
        server.host="127.0.0.1:"+str(server.server_port)
        print("Open http://"+server.host+"   |   Press Ctrl+C to exit.",flush=True)
        server.serve_forever()

def self_test(lab):
    from view import decode
    for selected in ([],["calendar-agent"],["email-agent"],list(NAMES)):
        lab.approve(selected)
        page=render(lab)
        assert bool(lab.batch)==bool(selected)
        if lab.batch:
            token=lab.batch["body"]["access_token"]
            batch=decode(token,1)
            assert token not in page and len(batch["authorization_details"])==len(selected)
        for name,r in lab.work.items():
            if name in selected:
                exchanged=r["exchange"]["body"]["access_token"]
                claims=decode(exchanged,1)
                assert exchanged not in page and claims["client_id"]==name
                assert "may_act" not in claims["authorization_details"][0]
                assert len(claims["authorization_details"])==1
                assert r["resource"]["status"]==201 and claims["batch_id"]==batch["batch_id"]
                assert r["resource"]["body"]["id"] in page
            else:
                assert r["exchange"]["status"]==400 and "resource" not in r
    assert len({r["pid"] for r in lab.work.values()})==2
    lab.test_boundary()
    assert lab.probe["resource"]["status"]==401
    assert lab.probe["resource"]["body"]=={"error":"invalid_token"}
    assert lab.probe["resource"]["headers"]["WWW-Authenticate"]=='Bearer error="invalid_token"'
    assert "401 Unauthorized" in render(lab) and "WWW-Authenticate" in render(lab)
    print("PASS: four consent combinations, separate workers, signed tokens, resource receipts and RS rejection.")

if __name__=="__main__":
    mp.freeze_support()
    parser=argparse.ArgumentParser(description="Offline batch delegation lab")
    parser.add_argument("--port",type=int,default=8080)
    parser.add_argument("--self-test",action="store_true")
    options=parser.parse_args()
    try:
        with ExitStack() as cleanup:
            lab=Leader(cleanup)
            if options.self_test:
                self_test(lab)
            else:
                serve(lab,options.port)
    except KeyboardInterrupt:
        pass
