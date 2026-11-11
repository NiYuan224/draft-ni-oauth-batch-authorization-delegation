# Batch Authorization Delegation 

Local Python demo of one Leader requesting permissions for Calendar Agent and Email Agent in one batch. Each agent exchanges the Batch Token for its own access token.

## Run

Requires Python 3.11 or later. No third-party dependencies.

Download and extract this repository, then open a terminal in the `demo` directory.

```sh
python leader_agent.py
```

Open http://127.0.0.1:8080/ in your browser and keep the terminal open. Stop with Ctrl+C.

To run the tests:

```sh
python -m unittest -v
```


## Files

- `leader_agent.py`: launcher and workflow
- `authorization_server.py`: consent, token issuance and exchange
- `calendar_agent.py`, `email_agent.py`: Sub-Clients
- `calendar_server.py`, `email_server.py`: resource servers
- `common.py`: shared HTTP helpers
- `view.py`, `page.html`: web interface
- `test_demo.py`: three core tests; run `python -m unittest -v`

Experimental single-domain demo, related to [Batch Authorization Delegation](https://datatracker.ietf.org/doc/draft-ni-oauth-batch-authorization-delegation/). Consent and token validation use private local endpoints; this is not a complete OAuth implementation. Agents are deterministic Python programs. Select an appropriate license before distributing the code as open source.
