"""Calendar Agent: exchange as calendar-agent, then create the interview event."""
import os
from common import CAL, EXCHANGE, JWT, basic, post, require, service

def start(ready, as_url, rs_url, secret, dispatch, mail_url=None):
    def task(path, auth, f):
        if path=="/probe" and mail_url:
            require(auth=="Bearer "+dispatch,403,"forbidden")
            response=post(mail_url+"/messages",{"to":f["email"],"subject":"Unauthorized test",
                          "text":"This must be rejected."},"Bearer "+f["token"])
            return 200,{"pid":os.getpid(),"resource":response}
        require(path=="/task",404,"not_found")

        scheme, _, batch_token = auth.partition(" ")
        require(scheme.lower()=="bearer" and bool(batch_token.strip()),
                401,"invalid_token")
        batch_token = batch_token.strip()

        exchange=post(as_url+"/token", {"grant_type":EXCHANGE,"subject_token_type":JWT,
                      "subject_token":batch_token,"resource":CAL},basic("calendar-agent",secret))
        trace={"pid":os.getpid(),"exchange":exchange,"target":CAL}
        if exchange["status"]==200:
            trace["resource"]=post(rs_url+"/events",{"summary":"Candidate interview","start":f["start"],
                                   "attendee":f["email"]},"Bearer "+exchange["body"]["access_token"])
        return 200,trace
    service(ready,task)
