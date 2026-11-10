# Batch Authorization Delegation 

Local Python demo of one Leader requesting permissions for Calendar Agent and Email Agent in one batch. Each agent exchanges the Batch Token for its own access token.

## Run

Python 3.12; no third-party dependencies.

```sh
python leader_agent.py
```

Windows PowerShell with uv:

```powershell
& "$env:USERPROFILE\.local\bin\uv.exe" run --offline --python 3.12 .\leader_agent.py
```

Open http://127.0.0.1:8080/ and keep the terminal open. Enter an email and interview time, select permissions, and submit. The page shows decoded tokens and actual local HTTP responses. The error button sends Calendar Agent’s token to Email RS, which rejects its audience with `401 invalid_token`. Stop with Ctrl+C.



## Files

- `leader_agent.py`: launcher and workflow
- `authorization_server.py`: consent, token issuance and exchange
- `calendar_agent.py`, `email_agent.py`: Sub-Clients
- `calendar_server.py`, `email_server.py`: resource servers
- `common.py`: shared HTTP helpers
- `view.py`, `page.html`: web interface
- `test_demo.py`: three core tests; run `python -m unittest -v`

Experimental single-domain demo, related to [Batch Authorization Delegation](https://datatracker.ietf.org/doc/draft-ni-oauth-batch-authorization-delegation/). Consent and token validation use private local endpoints; this is not a complete OAuth implementation. Agents are deterministic Python programs. Select an appropriate license before distributing the code as open source.
