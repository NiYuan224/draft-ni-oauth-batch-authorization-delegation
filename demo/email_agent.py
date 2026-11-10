"""Email Agent: exchange as email-agent, then submit a notification."""
import os
from common import MAIL, EXCHANGE, JWT, basic, post, require, service

def start(ready, as_url, rs_url, secret, dispatch):
    def task(path, auth, f):
        require(path=="/task" and auth=="Bearer "+dispatch,403,"forbidden")
        exchange=post(as_url+"/token", {"grant_type":EXCHANGE,"subject_token_type":JWT,
                      "subject_token":f["batch"],"resource":MAIL},basic("email-agent",secret))
        trace={"pid":os.getpid(),"exchange":exchange,"target":MAIL}
        if exchange["status"]==200:
            trace["resource"]=post(rs_url+"/messages",{"to":f["email"],"subject":"Interview invitation",
                                   "text":"Your interview is scheduled for "+f["start"]+"."},"Bearer "+exchange["body"]["access_token"])
        return 200,trace
    service(ready,task)
