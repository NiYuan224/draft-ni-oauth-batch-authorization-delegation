"""Calendar Agent: exchange as calendar-agent, then create the interview event."""
import os
from common import CAL, EXCHANGE, JWT, basic, post, require, service

def start(ready, as_url, rs_url, secret, dispatch, mail_url=None):
    def task(path, auth, f):
        require(auth=="Bearer "+dispatch,403,"forbidden")
        if path=="/probe" and mail_url:
            response=post(mail_url+"/messages",{"to":f["email"],"subject":"Unauthorized test","text":"This must be rejected."},"Bearer "+f["token"])
            return 200,{"pid":os.getpid(),"resource":response}
        require(path=="/task",404,"not_found")
        exchange=post(as_url+"/token", {"grant_type":EXCHANGE,"subject_token_type":JWT,
                      "subject_token":f["batch"],"resource":f["resource"]},basic("calendar-agent",secret))
        trace={"pid":os.getpid(),"exchange":exchange,"target":f["resource"]}
        if exchange["status"]==200 and f["resource"]==CAL:
            trace["resource"]=post(rs_url+"/events",{"summary":"Candidate interview","start":f["start"],
                                   "attendee":f["email"]},"Bearer "+exchange["body"]["access_token"])
        return 200,trace
    service(ready,task)
