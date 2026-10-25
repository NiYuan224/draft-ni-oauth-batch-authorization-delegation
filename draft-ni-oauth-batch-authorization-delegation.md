---
title: "Batch Authorization Delegation"
category: info

docname: draft-ni-oauth-batch-authorization-delegation-latest
submissiontype: IETF  # also: "independent", "editorial", "IAB", or "IRTF"
number:
date:
consensus: true
v: 3
# area: AREA
# workgroup: WG Working Group
keyword:
  - Rich Authorization Request
  - Token Exchange
  - Identity Chaining
  - Identity Assertion
  - Batch Authorization Delegation

venue:
#  group: WG
#  type: Working Group
#  mail: oauth@ietf.org
#  arch: https://example.com/WG
  github: "NiYuan224/draft-ni-oauth-batch-authorization-delegation"
  latest: "https://NiYuan224.github.io/draft-ni-oauth-batch-authorization-delegation/draft-ni-oauth-batch-authorization-delegation.html"

author:
 -
  name: Yuan Ni
  organization: Huawei
  email: niyuan1@huawei.com

 -
  name: Chunchi Peter Liu
  organization: Huawei
  email: liuchunchi@huawei.com

normative:
  RFC2119:
  RFC8174:
  RFC6749:
  RFC9396:
  RFC8693:
  RFC7523:
  RFC9068:
  RFC7662:

informative:
  I-D.ietf-oauth-identity-chaining:
  I-D.ietf-oauth-identity-assertion-authz-grant:
  I-D.ietf-wimse-wpt:
  I-D.ietf-wimse-http-signature:
  I-D.ietf-wimse-mutual-tls:
  SSF:
    title: OpenID Shared Signals Framework Specification 1.0
    date: 2025-08
    target: https://openid.net/specs/openid-sharedsignals-framework-1_0.html

...

--- abstract

This document describes a mechanism for Batch Authorization Delegation, which enables a batch of fine‑grained, actor‑bound permissions in a single request and securely delegates them to multiple collaborating actors.


--- middle

# Introduction {#intro}

Due to the rise of collaborative service ecosystems and AI Agents, resource access patterns are shifting from a traditional, linear, single client-server model to complex multi-entity orchestration. A task may consists of a batch of sub-tasks, which may require authorizations to different resources. Although a human user can request authorization for each resource, this work is usually carried out by a principal personal assistant AI Agent. While authorizing total privileges to the personal assistant agent is doable, it risks granting excessive privileges to it, thus oppose to the minimal privilege principle. On the other hand, if the principal agent request human authorization for every resource, it will reduce automated efficiency.

Therefore, the core challenge is to request access permissions to a batch of resources from the user at once, while precisely delegating fine-grained privileges to the respective sub-agent responsible for executing each sub-task.

Certain use cases include:

**(1) China UnionPay APOP (Agentic Payment Open Protocol) Framework:** A central agent from China UnionPay coordinates with multiple bank-specific sub-agents to calculate the best user discounts. The central agent requests a one-time batch authorization for all linked accounts from the user, and precisely delegates privileges so that each sub-agent only receives query and payment access for its respective bank. This strictly preventa one bank from leaking or spying on another bank's account existence, financial balances, or transaction histories.

**(2) Office Agent Orchestration:** An office agent coordinates the generation of a market insight report slide by deploying three specialized sub-agents in parallel based on a one-time batch approval from the user. It strictly delegates privileges to each sub-agent: the finance sub-agent is granted access to internal financial records, the internet search sub-agent is completely barred from seeing any intranet data to prevent confidential leaks during web queries, and the slide generator sub-agent is authorized to generate and save the final presentation using the aggregated outputs. Without batch authorization, the workflow would stall whenever a sub-agent reaches its specific sub-task and attempts to request its required permission, such as fetching external web resources or requesting file-write permissions. Asynchronously prompting the user for these consents would inevitably cause task blockages and ruin the automated multi-agent experience, which is unacceptable.

While the existing OAuth 2.0 protocol and its extensions provide a foundation for authorization, they lack native support for efficient, secure delegation for a batch of coordinated tasks:

**(1) OAuth 2.0{{RFC6749}}:**  The OAuth 2.0 authorization framework enables a client to obtain limited access to protected resources on behalf of a resource owner. However, in a multi-entity collaboration scenario, this requires each entity to independently initiate its own authorization flow. This results in multiple user interactions, introducing significant end-to-end latency and severe user fatigue.

**(2) OAuth 2.0 Token Exchange{{RFC8693}}:** Token Exchange defines a delegation mechanism and introduces the `may_act` claim to authorize an actor to act on behalf of a subject. However, the `may_act` claim only determines who is authorized to act. It does not provide a way to link or specify which subset of permissions are being delegated to this actor.

**(3) OAuth 2.0 Rich Authorization Request (RAR) {{RFC9396}}:** RAR introduces a new parameter `authorization_details` to allow clients to express their fine-grained authorization requirements using the JSON structures. Such a parameter allows several fine-grained permissions to be included in a single authorization request, as well as the issued access token. However, RAR does not currently specify how these structured permissions can be partitioned and delegated to different actors during a subsequent token exchange.

In summary, the existing OAuth 2.0 protocol and its extensions lack a mechanism to express, partition, and delegate fine-grained structured permissions across multiple collaborating entities.

To bridge this gap, this document adds the delegation information directly to the multiple fine-grained permissions in the RAR. By extending the `authorization_details` with a `may_act` field, a client can request a comprehensive set of permissions, each of which specify which actor is authorized to exercise such privilege. The Authorization Server (AS) then responds this request with a Batch Token, which contains the above permissions and their corresponding designated actors. When an actor performs a token exchange using the Batch Token, the AS applies a downscoping strategy, filtering the permissions based on the consistency of the `may_act` field and actor's identity. This ensures a convenient authorization experience for the user while strictly enforcing the principle of minimal privilege across multiple collaborating entities.


# Conventions and Definitions

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "NOT RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in BCP 14 {{RFC2119}} {{RFC8174}} when, and only when, they appear in all capitals, as shown here.

This document uses common OAuth and token processing terms such as "access token", "authorization server" (AS), "resource server" (RS), "authorization request", "access token response" defined by {{RFC6749}}, "Trust Domain", "JWT Authorization Grant" defined by {{I-D.ietf-oauth-identity-chaining}}, "identity assertion" defined by {{I-D.ietf-oauth-identity-assertion-authz-grant}}.

In addition, the following terms are defined for this document:

Leader-Client:  The entity responsible for coordinating tasks and requesting permissions in a batch on behalf of Sub-Clients. The Leader-Client initiates rich authorization requests to the AS, and sends the obtained Batch Token to Sub-Clients. According to examples listed above, Leader-Client is the principal personal assistant agent, a microservice orchestrator, or an API gateway.

Sub-Client:  The entity that is subordinate to the Leader-Client and redeem access tokens to Resource Servers (RS) to perform specific sub-tasks. The Sub-Client exchanges the received Batch Token for a downscoped access token with partial privileges. Sub-clients could be sub-agents and microservices.

Batch Authorization Delegation: A mechanism proposed in this document that a Leader-Client requests permissions in a batch and delegates them to its subordinate Sub-Clients.

Authorization Item: An authorization item defines one permission per one corresponding designated actor. There may be multiple Authorization Items within one `authorization_details`, which is later encapsulated in the rich authorization request and the issued Batch Token.

Batch Token: A special JWT access token issued by the AS to the Leader-Client. It encapsulates multiple Authorization Items, enabling subsequent delegation.

Designated Actor: The `may_act` field within an authorization item that specifies the Sub-Client authorized to exercise that permission.

Downscoped Token: The access token issued to a Sub-Client as a result of token exchange, which is to be used at the RS to access protected resources. It contains only a subset of authorization items whose designated actors match the requesting Sub-Client's identity.

# Batch Authorization Delegation {#basic}

This document specifies a mechanism combining OAuth RAR {{RFC9396}} and Token Exchange {{RFC8693}} to achieve Batch Authorization Delegation.

The Leader-Client sends a rich authorization request with multiple authorization items to the AS. Each authorization item not only describes the required permission but also declares the Sub-Client to which the permission can be delegated to via designated actors. Upon user confirmation, the AS issues a Batch Token to the Leader-Client, which encapsulates the authorization items confirmed by the user. The Leader-Client distributes the Batch Token to Sub-Clients.

The Sub-Client initiates a token exchange request to the AS. The AS verifies the Sub-Client's identity against the Designated Actors in the Batch Token, and then filters out one or more authorization items corresponding to this specific Sub-Client. Then the AS generates a Downscoped Token containing only the permissions from the filtered authorization items.

Such a mechanism enables the Leader-Client to perform a one-time batch authorization as well as ensuring each Sub-Client obtains an access token containing only the permissions it requires, thereby realizing both efficiency and security.

## Overview

Figure 1 shows the flow of Batch Authorization Delegation. Note that a Leader-Client MAY coordinate several Sub-Clients. For simplicity, only one Sub-Client is shown in Figure 1.

~~~
+----++-------------+    +----+      +----------++----+
|User||Leader-Client|    | AS |      |Sub-Client|| RS |
+-+--++------+------+    +--+-+      +-----+----++--+-+
  |          |(1)RAR        |              |        |
  |          |(with may_act)|              |        |
  |          +-------------->              |        |
  |          |(2)Ask for    |              |        |
  |          | consent      |              |        |
  <----------+--------------+              |        |
  |(3)Consent|              |              |        |
  +----------+-------------->              |        |
  |          |(4)Issue      |              |        |
  |          | Batch Token  |              |        |
  |          <--------------+              |        |
  |          |(5)Distribute |              |        |
  |          | Batch Token  |              |        |
  |          |--------------+-------------->        |
  |          |              |(6)Token      |        |
  |          |              | exchange     |        |
  |          |              | request      |        |
  |          |              <--------------+        |
  |          |              | <Batch Token>|        |
  |          |              |              |        |
  |          |              |(7)Verify     |        |
  |          |              +-+ identity   |        |
  |          |              | | &Downscope |        |
  |          |              <-+            |        |
  |          |              |(8)Downscoped |        |
  |          |              |   Token      |        |
  |          |              +-------------->        |
  |          |              |              |(9)Access
  |          |              |              |-------->
  |          |              |              |        |
~~~

*Figure 1: Batch Authorization Delegation Flow*

(1) The Leader-Client sends a rich authorization request containing multiple authorization items to the AS. Each authorization item includes a fine-grained permission (described by several fields defined in {{RFC9396}}, e.g., `type`, `actions`, `locations`, etc.) and a designated actor that uses the `may_act` field. to designate which Sub-Client is authorized for the permission.

(2) After receiving the rich authorization request, the AS presents all authorization items in the request to the user for consent.

(3) The user confirms all or some of the authorization items and sends the result back to the AS.

(4) The AS generates a Batch Token, which encapsulates the authorization items confirmed by the user and issues it to the Leader-Client.

(5) The Leader-Client distributes the Batch Token to the Sub-Client.

(6) The Sub-Client initiates a token exchange request to the AS to exchange the Batch Token to a Downscoped Token.

(7) The AS verifies the identity of Sub-Client against the designated actors in the Batch Token to filter the authorization items corresponding to the Sub-Client.

(8) The AS generates a Downscoped Token that only contains the permissions in the filtered authorization items and send it to the Sub-Client.

(9) The Sub-Client accesses the RS with the Downscoped Token.

This mechanism offers two key advantages.

* First, it fully reuses existing standards, combining RAR's flexible permission definitions with Token Exchange's delegation semantics by simply moving the `may_act` claim from the entity level down to individual authorization items without altering its original meaning. This slight change effectively fulfills the expression, partition, and delegation purpose of fine-grained structured permissions across multiple collaborating entities.

* Second, the final Downscoped Token introduces no new claims or structural changes. Since RS deployments are often numerous and costly to upgrade, this design ensures zero modification to existing RSs, enabling smooth adoption with minimal reconfiguration.

## Batch Token

### RAR Extension with the may_act field

In {{RFC8693}}, the may_act is a top-level claim, which makes a statement of one party is authorized to become the actor and act on behalf of another party. It is an entity-level delegation, without further distinguishing the permission subsets.

In contrast, this document leverages `authorization_details` defined in {{RFC9396}} to describe multiple authorization items, each of which contains a permission and a nested `may_act` field serving as a designated actor. This helps to define who is authorized to perform which permission, thus changing the entity-level delegation into an item-level delegation.

**may_act**<br>
**REQUIRED.** A JSON object that identifies the specific Sub-Client authorized to exercise the permission.

The `may_act` JSON object contains fields that specify the intended actor for a particular authorization item. This document defines the following two fields:

**sub**<br>
**REQUIRED.** A string that uniquely identifies the Sub-Client authorized to exercise the permission.


**aud**<br>
**OPTIONAL.** A string that identifies the AS of the trust domain where the Sub-Client resides. If the Sub-Client and the Leader-Client are located in different Trust Domains, this field MUST be present to specify the target AS. If this field is omitted, it MUST be assumed that the Sub-Client and the Leader-Client reside in the same trust domain.


Figure 2 shows an example of `authorization_details` containing the `may_act` field. It represents a typical travel management scenario in which the Leader-Client requests two distinct authorization items: a flight booking permission delegated to the Flight-Agent, and a hotel reservation permission delegated to the Hotel-Agent. Both Sub-Clients are located in the same trust domain as the Leader-Client so that the `may_act.aud` field is omitted. This structure demonstrates how multiple permissions can be bound to different actors within a single authorization request.

~~~
[
  {
    "type": "flight_booking",
    "actions": ["search", "book"],
    "locations": ["https://example.com/flights"],
    "may_act": {
        "sub": "flight_agent@example.com"
    }
  },
  {
    "type": "hotel_reservation",
    "actions": ["search", "book"],
    "locations": ["https://example.com/hotels"],
    "may_act": {
        "sub": "hotel_agent@example.com"
    }
  }
]
~~~
*Figure 2: authorization_details with the `may_act` field*

### Requesting and Issuing a Batch Token
The lead-client sends an authorization request that contains `authorization_details` with `may_act` fields to the AS. The AS MUST ask the user for consent to the requested authorization items. The general processing rules of the AS defined in {{RFC9396}} apply, with the following extensions:

* The AS MUST validate that the Sub-Client identified in the `may_act.sub` field is known. If the `may_act.aud` field is present, the AS MUST validate that the target AS is reachable and trusted according to local policies.

* The AS MUST present all the authorization items, including the requested permissions and their corresponding intended Sub-Clients to the user. The user MAY:

  * Grant all requested authorization items.

  * Grant only a subset of the authorization items.

* The AS MUST record the consented authorization items, including the `may_act` fields, as part of a grant (e.g., the authorization code).

After user consent, the AS issues an authorization code as a grant to the Leader-Client. The Leader-Client then exchanges the authorization code for a Batch Token, following the standard authorization response and token request flow as defined in {{RFC6749}}.

Subsequently, the AS generates a Batch Token and returns it to the Leader-Client in the Token response. The Batch Token is a JWT access token conforming to {{RFC9068}}, with the following claims and values.

### Batch Token Claims

**iss**<br>
**REQUIRED.** The identifier of the AS.

**sub**<br>
**REQUIRED.** The identifier of the user who grants the consent.

**aud**<br>
**REQUIRED.** MUST be set to the AS itself, as the Batch Token is intended only for token exchange at the AS and cannot be directly used at the RS.

**client_id**<br>
**REQUIRED.** The identifier of the Leader-Client that initiated the authorization request.

**authorization_details**<br>
**REQUIRED.** A JSON array containing all the consented authorization items, including the permission descriptions and their corresponding `may_act` Designated Actors.

**exp**<br>
**REQUIRED.** The expiration time of the Batch Token, which also defines the expiration of the batch authorization.

**batch_id**<br>
**REQUIRED.** An identifier for the batch authorization. The same identifier MUST be included in the Batch Token and all Downscoped Tokens derived from that batch authorization.

Figure 3 shows an example of the Batch Token JWT payload, which encapsulates all consented authorization items from Figure 2. The `sub` claim identifies the user who consents, the `client_id` claim identifies the travel assistant as the Leader-Client that initiates the request, each `may_act.sub` field identifies the Sub-Client authorized to exercise the corresponding permission. The `aud` claim is set to the AS itself, as the Batch Token will be presented back to the AS for further token exchange.

~~~
{
  "iss": "https://as.example.com",
  "sub": "user@example.com",
  "aud": "https://as.example.com",
  "client_id": "travel_assistant@example.com",
  "exp": 1777881600,
  "iat": 1777795200,
  "jti": "batch-token-8b4729cc-32e4-4370-8cf0-5796154d1296",
  "batch_id": "batch-auth-8b4729cc-32e4-4370-8cf0-5796154d1296"
  "authorization_details": [
    {
      "type": "flight_booking",
      "actions": ["search", "book"],
      "locations": ["https://example.com/flights"],
      "may_act": {
        "sub": "flight_agent@example.com"
      }
    },
    {
      "type": "hotel_reservation",
      "actions": ["search", "book"],
      "locations": ["https://example.com/hotels"],
      "may_act": {
        "sub": "hotel_agent@example.com"
      }
    }
  ]
}
~~~
*Figure 3: Batch Token JWT Payload*

## Downscoped Token


### Token Exchange Request

When a Sub-Client receives a Batch Token from the Leader-Client, it MUST perform a token exchange request to the AS to obtain a Downscoped Token. The Batch Token MUST NOT be used directly to the RS to redeem resources by anyone. Within the token exchange request, the parameters described in section 2.1 of {{RFC8693}} apply with the following additional requirements:

**resource**<br>
**OPTIONAL.** The URI of the target RS where the Sub-Client intends to use the Downscoped Token.

**audience**<br>
**OPTIONAL.** The well-known/logical name of the target RS where the Sub-Client intends to use the Downscoped Token.

**subject_token**<br>
**REQUIRED.** The Batch Token received from the Leader-Client.

**subject_token_type**<br>
**REQUIRED.** urn:ietf:params:oauth:token-type:jwt.

**actor_token**<br>
**OPTIONAL.** A security token representing the acting Sub-Client, as defined in {{RFC8693}}.

**actor_token_type**<br>
**REQUIRED.** if `actor_token` is present. The type of the provided `actor_token`, as defined in {{RFC8693}}.


Figure 4 shows a token exchange request initiated by the Flight-Agent. The Flight-Agent provides the Batch Token as the `subject_token` and its identity token as the `actor_token`. The AS validates both tokens and  matches the party identified in the `actor_token` against `may_act.sub` to select the authorized items assigned to the Flight-Agent. When no `actor_token` is provided, the AS uses the authenticated Sub-Client's identity instead.

~~~
 POST /as/token.oauth2 HTTP/1.1
 Host: as.example.com
 Content-Type: application/x-www-form-urlencoded

 grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Atoken-exchange
 &subject_token=<Encoded Batch Token>
 &subject_token_type=urn%3Aietf%3Aparams%3Aoauth%3Atoken-type%3Ajwt
 &actor_token=eyJhb...
 &actor_token_type=urn%3Aietf%3Aparams%3Aoauth%3Atoken-type%3Ajwt
~~~
*Figure 4: Token Exchange Request*

The claims of the `actor_token` are detailed in Figure 5.

~~~
{
  "aud":"https://as.example.com",
  "iss":"https://original-issuer.example.net",
  "exp": 1778400000,
  "sub":"flight_agent@example.com"
}
~~~
*Figure 5: Actor Token Claims*


### Processing Rules of the Authorization Server

Upon receiving a token exchange request, the AS MUST:

* Validate the Batch Token provided in the `subject_token`, including its signature, `iss`, `aud`, `exp`, and required claims. The AS MUST reject the request if the Batch Token is invalid or expired.

* Authenticate the requesting Sub-Client. The AS MAY use the following authentication methods:

  * Client password authentication as defined in Section 2.3.1 of {{RFC6749}}.
  * JWT-based client authentication as defined in {{RFC7523}}.
  * WIMSE-based authentication methods as defined in {{I-D.ietf-wimse-wpt}}, {{I-D.ietf-wimse-http-signature}}, and {{I-D.ietf-wimse-mutual-tls}}.

* If an `actor_token` is provided, validate it and identify the party represented by the token.

* Retrieve the `authorization_details` from the validated Batch Token and select only those authorization items whose `may_act.sub` exactly matches the authenticated Sub-Client's identity or the party identified in the actor_token, if provided. If no authorization items match, the AS MUST reject the request.

* The AS MUST preserve the `batch_id` when issuing a Downscoped Token. For JWT Downscoped Tokens, the AS MUST include the `batch_id` claim. For other token formats, the AS MUST maintain an equivalent association.

* If shared constraints apply to a batch authorization, such as a total spending limit, a maximum number of transactions, or a total usage quota, the AS MUST enforce them across all Downscoped Tokens associated with the same `batch_id`.

### Downscoped Token Claims

The AS generates a Downscoped Token that only contains the permissions in the filtered authorization items. The format of this token MAY be a JWT access token conforming to {{RFC9068}} or any other format at the AS's discretion. If a JWT Downscoped Token is used, the following constraints on its claim values apply:

**sub**<br>
**REQUIRED.** The owner who grants the consent (copied from the `sub` claim of the Batch Token in the `subject_token` parameter).

**client_id**<br>
**REQUIRED.** The identifier of the authenticated sub‑client.

**aud**<br>
**OPTIONAL.** The target RS where the Sub-Client intends to use the Downscoped Token.

**authorization_details**<br>
**OPTIONAL.** A JSON array containing the permissions from the filtered authorization items. Since the `may_act` field has already been enforced as a designated actor by the AS during token exchange, it MAY be omitted in the Downscoped Token.

**exp**<br>
**REQUIRED.** The expiration time of the Downscoped Token, which MUST NOT exceed the expiration time (`exp`) of the Batch Token.

**batch_id**<br>
**REQUIRED.** The identifier of the batch authorization from which
the Downscoped Token is derived. It MUST match the `batch_id` of
the corresponding Batch Token.

Figure 6 shows a Downscoped Token issued to the Flight-Agent after token exchange. Its `sub` claim identifies the end‑user who grants the consent, its `aud` claim points directly to target service (https://example.com/flights), and the `client_id` identifies the Flight-Agent. The `authorization_details` array contains only the flight‑booking permission, with the `may_act` field removed.

~~~
{
  "iss": "https://as.example.com",
  "sub": "user@example.com",
  "aud": "https://example.com/flights",
  "client_id": "flight_agent@example.com",
  "exp": 1777881600,
  "iat": 1777795210,
  "jti": "downscoped-token-7c8d9a2e-4b12-4a3f-8e6c-2f9a8b3c7d5e",
  "authorization_details": [
    {
      "type": "flight_booking",
      "actions": ["search", "book"],
      "locations": ["https://example.com/flights"]
    }
  ]
}
~~~
*Figure 6: Downscoped Token Payload*

# Derivative Scenarios

Until now, the main procedures of the Batch Authorization Delegation is done. There are some more derivative scenarios with detailed additional steps and considerations, including:

* Single-Domain Batch Authorization Delegation: The user, Leader-Client, and Sub-Clients all reside within the same trust domain managed by a single AS.

* Batch Authorization Delegation with Cross-Domain Sub-Clients: The user and Leader-Client belong to the same trust domain, but Sub-Clients reside in one or more other trust domains, each managed by its own AS.

* Batch Authorization Delegation with a Cross-Domain User: The Leader-Client and Sub-Clients belong to the same trust domain, while the user resides in another trust domain, each managed by its own AS.

* Combined Cross-Domain Scenario: The user, Leader-Client, and Sub-Clients each reside in different trust domains, each managed by its own AS.

## Single-Domain Batch Authorization Delegation
In this case, the workflow and the examples are already given in {{basic}} Figures. 1-6.

## Batch Authorization Delegation with Cross-Domain Sub-Clients

### Workflow
The workflow in this case is a combination of Batch Authorization Delegation and identity chaining {{I-D.ietf-oauth-identity-chaining}}.


Since the Sub-Client and Leader-Client reside in different trust domains, the Leader-Client in Domain A requests JWT Authorization Grants (JAGs) from the AS in Domain A via token exchange. The AS in Domain A inspects both the `may_act.aud` and `may_act.sub` fields within the Batch Token, filters and splits the authorization items to generates an actor-specific JAG for each designated Sub-Client.

Taking the Sub-Client in Domain B as an example, the Leader-Client then presents the corresponding JAG as an assertion to the AS in Domain B to obtain an access token, which is subsequently exchanged by the specific Sub-Client in Domain B for a final Downscoped Token. This token exchange ensures that the final Downscoped Token is bound to the Sub-Client's own identity and contains only the specific permissions it required.


~~~
+--------++-------------+  +--------++--------+ +----------+ +--------+
|  User  ||Leader-Client|  |   AS   ||   AS   | |Sub-Client| |   RS   |
|Domain A||   Domain A  |  |Domain A||Domain B| | Domain B | |Domain B|
+---+----++------+------+  +-----+--++---+----+ +-----+----+ +---+----+
    |            |(1)RAR         |       |            |          |
    |            |(with may_act) |       |            |          |
    |            +--------------->       |            |          |
    |            |(2)Ask for     |       |            |          |
    |            | consent       |       |            |          |
    <------------+---------------+       |            |          |
    |(3)Consent  |               |       |            |          |
    +------------+--------------->       |            |          |
    |            |(4)Issue       |       |            |          |
    |            | Batch Token   |       |            |          |
    |            <---------------+       |            |          |
    |            |(a)Token       |       |            |          |
    |            | exchange      |       |            |          |
    |            | request       |       |            |          |
    |            |--------------->       |            |          |
    |            |(b)Verify      |       |            |          |
    |            |   &Downscope  |       |            |          |
    |            |             +-+       |            |          |
    |            |             | |       |            |          |
    |            |(c)JAGs      +->       |            |          |
    |            <---------------+       |            |          |
    |            |(d)JAG         |       |            |          |
    |            +---------------+------->            |          |
    |            |(e)Access Token|       |            |          |
    |            <---------------+-------+            |          |
    |            |(f)Access Token|       |            |          |
    |            +---------------+-------+------------>          |
    |            |               |       |(6)Token    |          |
    |            |               |       | exchange   |          |
    |            |               |       | Request    |          |
    |            |               |       <------------|          |
    |            |               |       |(8)Downscope|          |
    |            |               |       | Token      |          |
    |            |               |       +------------>          |
    |            |               |       |            |(9)access |
    |            |               |       |            +---------->
    |            |               |       |            |          |
~~~
*Figure 7: Batch Authorization Delegation with Cross-Domain Sub-Clients*

Steps (1)-(4) are the same as in Figure 1.

(a) The Leader-Client in Domain A exchanges the Batch Token with the AS in Domain A for actor-specific JAGs that can be used in the AS in Domain B.

(b) The AS of Domain A inspects the may_act fields within the Batch Token, filtering and splitting the authorization items down to each target actor in Domain B.

(c) The AS of Domain A issues actor-specific JAGs, with the nested `may_act` field in the `authorization_details` removed. This step requires trust relationship between the ASs in Domain A and Domain B.  See Section 2.1 of {{I-D.ietf-oauth-identity-chaining}} for the trust relationship establishment.

(d) The Leader-Client in Domain A presents the JAG for the specific Sub-Client as an assertion to the AS of Domain B.

(e) The AS of Domain B validates the JAG, extracts and encapsulates the filtered authorization items in an access token and sends it to the Leader-Client.


(f) The Leader-Client sends the access token to the Sub-Client.

Steps (6)-(9) are the same as in Figure 1.

By splitting and filtering batch tokens entirely within the Domain A, the key advantage of the above mechanism is the AS of Domain B is relieved from handling complex batch authorization processing. This minimizes upgrade overhead for downstream ASs, ensuring rapid and seamless compatibility with existing cross-domain OAuth deployments.

### Examples

The following shows some typical examples in the workflow of Figure 7, which is correspond to the use case (1) in {{intro}}.

#### Batch Token

Figure 8 illustrates a Batch Token payload issued by a leading Chinese Financial Alliance's AS in step (4).

The Batch Token contains two authorization items: one for searching and calculating max availble coupons at Bank_A (benefit_agent), and another for the same actions at Bank_B. The `may_act.aud` field specifies the AS location, while the `may_act.sub` field specifies the designated actor.


~~~
{
  "iss": "https://as.alliance.example.com",
  "sub": "user@alliance.example.com",
  "aud": "https://as.alliance.example.com",
  "client_id": "finance_assistant@alliance.example.com",
  "exp": 1777881600,
  "iat": 1777795200,
  "jti": "4a7b203c-e591-4916-b8df-d2b389f4621c",
  "authorization_details": [
    {
      "type": "benefit_bank_a",
      "actions": ["search", "calculate"],
      "locations": ["https://bank_a.example.com/benefits"],
      "may_act": {
        "sub": "benefit_agent@bank_a.example.com",
        "aud": "https://as.bank_a.example.com"
      }
    },
    {
      "type": "benefit_bank_b",
      "actions": ["search", "calculate"],
      "locations": ["https://bank_b.example.com/benefits"],
      "may_act": {
        "sub": "benefit_agent@bank_b.example.com",
        "aud": "https://as.bank_b.example.com"
      }
    }
  ]
}
~~~
*Figure 8: Batch Token Payload*


#### JWT Authorization Grant
Figure 9 shows the JAG payload issued by the Finance Alliance AS in step (c), specifically filtered for Bank_A's benefit_agent.

In accordance with step (b), the Finance Alliance AS inspects the `may_act` fields of the Batch Token (Figure 8), extracts and encapsulates the benefit_bank_a item into the JAG, with the `may_act` field removed.

~~~
{
  "iss": "https://as.alliance.example.com",
  "sub": "user@alliance.example.com",
  "aud": "https://as.bank_a.example.com",
  "client_id": "finance_assistant@alliance.example.com",
  "iat": 1777795210,
  "exp": 1777795300,
  "authorization_details": [
    {
      "type": "benefit_bank_a",
      "actions": ["search", "calculate"],
      "locations": ["https://bank_a.example.com/benefits"],
    }
  ]
}
~~~
*Figure 9: JAG Payload*

The subsequent formats of the access token, token exchange requests, and downscoped tokens fully reuse the standard profiles defined in Section 3 of {{I-D.ietf-oauth-identity-chaining}}, and are therefore omitted here.


## Batch Authorization Delegation with the Cross-Domain User

When the user resides in a different trust domain from the clients, one potential approach is to explore the combination of batch authorization delegation and identity assertion {{I-D.ietf-oauth-identity-assertion-authz-grant}}. The user's client could obtain an Identity Assertion from its local IdP, exchange it for an Identity Assertion JWT Authorization Grant (ID-JAG) targeting the AS of the leader-client's domain, and then exchange it into an access token for the Leader-Client; the Leader-Client might then exchange this access token to a batch token. Because this pattern introduces the delegation of user's intent, the specific workflow require further analysis and are open for working group discussion.

## Combined Cross‑Domain Scenario

In some deployments, the user, the leader‑client, and the sub‑clients may each reside in different trust domains. A combination of the workflows defined in Sections 4.2 and 4.3 directly supports this scenario.

# Security Considerations

## Batch Authorization Revocation

The `batch_id` enables the AS to identify Downscoped Tokens derived from the same batch authorization when that authorization is revoked. The `batch_id` itself does not invalidate these tokens. The AS MUST use the `batch_id` to identify the affected tokens and apply an appropriate revocation mechanism to them. Deployments MAY use token introspection {{RFC7662}} or Token Status List to support token status checking, and event-based mechanisms such as the Shared Signals Framework {{SSF}} to propagate revocation notifications.


# IANA Considerations

This document has no IANA actions.


--- back

# Acknowledgments
{:numbered="false"}

TODO acknowledge.
