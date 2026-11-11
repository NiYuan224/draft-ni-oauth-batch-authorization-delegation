"""Local calendar resource server. Store created events in this process."""
from common import post, require, service, uid

def start(ready, as_url, secret):
    events={}
    def create(path, auth, f):
        require(path=="/events",404,"not_found")
        require(auth.startswith("Bearer "),401,"invalid_token")
        verdict=post(as_url+"/validate",{"token":auth[7:]},"Bearer "+secret)
        require(verdict["status"]==200,401,"invalid_token")
        claims=verdict["body"]
        require(any("create_calendar_event" in i["actions"] for i in claims["authorization_details"]),403,"insufficient_scope")
        event={"id":"evt_"+uid(),"summary":f["summary"],"start":f["start"],"attendee":f["attendee"],
               "status":"confirmed","created_by":claims["client_id"],"batch_id":claims["batch_id"]}
        events[event["id"]]=event
        return 201,{k:event[k] for k in ("id","start","attendee","status")}
    service(ready,create)
