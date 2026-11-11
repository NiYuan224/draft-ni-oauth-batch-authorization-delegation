# Batch Authorization Delegation 

```mermaid
flowchart LR
    U["User"] -->|Request| L["Leader-Agent"]

    L -->|Subtask 1| A1["Sub-Agent 1"]
    L -->|Subtask 2| A2["Sub-Agent 2"]
    L -->|Subtask 3| A3["Sub-Agent 3"]

    A1 -->|Access| R1["Resource 1"]
    A2 -->|Access| R2["Resource 2"]
    A3 -->|Access| R3["Resource 3"]

    classDef user fill:#FFE0B2,stroke:#D98C28,color:#172E30
    classDef agent fill:#B2DFDB,stroke:#26867D,color:#172E30
    classDef resource fill:#D6EAF8,stroke:#5499C7,color:#172E30

    class U user
    class L,A1,A2,A3 agent
    class R1,R2,R3 resource

    linkStyle default stroke:#D9534F,stroke-width:2px
```


Batch Authorization Delegation lets an orchestrator agent request permissions for multiple sub-agents in a single authorization request, reducing repeated user approvals while allowing each sub-agent to obtain only the permissions approved for it.

This Python demo shows a Personal Assistant (Leader Agent) coordinating Calendar and Email Agents to schedule a meeting and notify attendees. Each sub-agent exchanges the Batch Token for an access token containing only its assigned permissions.

Run the demo locally to approve both permissions, just one, or neither, and inspect decoded tokens and resource responses through a web interface. Calendar and email operations are simulated; no external services are required.


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

Experimental single-domain demo, related to [Batch Authorization Delegation](https://datatracker.ietf.org/doc/draft-ni-oauth-batch-authorization-delegation/). Consent and token validation use private local endpoints; this is not a complete OAuth implementation. Agents are deterministic Python programs. 
