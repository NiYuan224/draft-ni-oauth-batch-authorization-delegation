"""The AS owns client authentication, local consent records, signing and token exchange."""
import base64
import hmac
import json
import time
from common import ACCESS, EXCHANGE, ITEMS, JWT, Rejection, basic, require, service, uid

def encode(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

def start(ready, clients, consent_secret, validators):
    def now():
        return time.time()
    key = uid().encode()
    pending, codes = {}, {}
    def issue(claims):
        claims.update(iss="urn:interview-lab:as", sub="demo-user", iat=int(now()), jti=uid())
        claims = {name: claims[name] for name in ("iss", "sub", "aud", "client_id", "exp", "iat", "jti", "batch_id", "authorization_details")}
        header = encode(b'{"alg":"HS256","typ":"JWT"}')
        payload = encode(json.dumps(claims,separators=(",",":")).encode())
        data = header+"."+payload
        return data+"."+encode(hmac.digest(key,data.encode(),"sha256"))

    def verify(token, audience):
        parts = token.split(".")
        require(len(parts)==3,401,"invalid_token")
        signed = ".".join(parts[:2]).encode()
        require(hmac.compare_digest(encode(hmac.digest(key,signed,"sha256")),parts[2]),401,"invalid_token")
        p = json.loads(base64.urlsafe_b64decode(parts[1]+"==="))
        require((p["iss"],p["aud"])==("urn:interview-lab:as",audience)
                and p["iat"]<=now()<p["exp"],401,"invalid_token")
        return p

    def process(path, auth, f):
        if path=="/consent":
            require(auth=="Bearer "+consent_secret,403,"forbidden")
            request = pending.pop(f["request_id"],None)
            require(request is not None,400,"invalid_request")
            approved = [i for i in request if i["may_act"]["sub"] in json.loads(f["selected"])]
            if not approved:
                return 200, {"decision":"denied"}
            code=uid()
            codes[code]=(approved,now()+60)
            return 200, {"code":code}
        if path=="/validate":
            audience=next((a for a,s in validators.items() if auth=="Bearer "+s),None)
            require(audience is not None,403,"forbidden")
            return 200, verify(f["token"],audience)
        client=next((n for n,s in clients.items() if hmac.compare_digest(auth,basic(n,s))),None)
        require(client is not None,401,"invalid_client")
        if path=="/authorize":
            details=json.loads(f["authorization_details"])
            require(client=="leader" and details==ITEMS,400,"invalid_authorization_details")
            request_id=uid()
            pending[request_id]=details
            return 200, {"request_id":request_id}
        require(path=="/token",404,"not_found")
        if f["grant_type"]=="authorization_code":
            require(client=="leader",400,"unauthorized_client")
            saved=codes.pop(f["code"],None)
            require(saved is not None and saved[1]>now(),400,"invalid_grant")
            token=issue(dict(aud="urn:interview-lab:as",client_id=client,batch_id=uid(),
                             authorization_details=saved[0],exp=int(now())+300))
            return 200, {"access_token":token,"token_type":"Bearer","expires_in":300}
        require(f["grant_type"]==EXCHANGE,400,"unsupported_grant_type")
        require(f["subject_token_type"]==JWT,400,"invalid_request")
        try:
            batch=verify(f["subject_token"],"urn:interview-lab:as")
        except (Rejection, ValueError, KeyError, TypeError):
            raise Rejection(400, "invalid_request") from None
        target=f["resource"]
        allowed=[i for i in batch["authorization_details"] if i["may_act"]["sub"]==client and target in i["locations"]]
        require(allowed,400,"invalid_target")
        exp=min(batch["exp"],int(now())+120)
        token=issue(dict(aud=target,client_id=client,batch_id=batch["batch_id"],
                         authorization_details=[{k:v for k,v in item.items() if k != "may_act"} for item in allowed],exp=exp))
        return 200, {"access_token":token,"token_type":"Bearer","issued_token_type":ACCESS,"expires_in":exp-int(now())}
    service(ready,process)
