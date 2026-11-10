"""Local mail resource server. A message enters the demo outbox only."""
from common import post, require, service, uid

def start(ready, as_url, secret):
    outbox={}
    def send(path,auth,f):
        require(path=="/messages",404,"not_found")
        require(auth.startswith("Bearer "),401,"invalid_token")
        verdict=post(as_url+"/validate",{"token":auth[7:]},"Bearer "+secret)
        require(verdict["status"]==200,401,"invalid_token")
        claims=verdict["body"]
        require(any("send_email" in i["actions"] for i in claims["authorization_details"]),403,"insufficient_scope")
        message={"id":"msg_"+uid(),"to":f["to"],"subject":f["subject"],"text":f["text"],
                 "status":"queued_locally","submitted_by":claims["client_id"],"batch_id":claims["batch_id"]}
        outbox[message["id"]]=message
        return 201,{k:message[k] for k in ("id","to","status")}
    service(ready,send)
