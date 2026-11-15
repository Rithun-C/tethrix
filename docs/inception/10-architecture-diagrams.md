# I-10: Architecture and data-flow diagrams

- Status: Approved 2026-11-15
- Viewable page: https://claude.ai/artifact/CBHZiLc5RJZ3XxEkahCAbP (private)
- Date: 2026-11-15
- Based on: ADR-0001 to ADR-0004

The diagrams are written in Mermaid, a text format that GitHub shows as pictures. In
VS Code, a Mermaid preview extension is needed to see them.

## 1. The whole system

What lives where, and which way requests go.

```mermaid
flowchart LR
  user([Browser])

  subgraph aws [AWS account, us-east-1]
    cf[CloudFront<br/>default domain]
    s3[(S3 bucket<br/>React build)]
    url[Lambda function URL<br/>auth: AWS_IAM]
    lambda[Lambda<br/>FastAPI container]
    ddb[(DynamoDB<br/>productivity-app-data)]
    cognito[Cognito user pool<br/>hosted sign-in]
    ecr[(ECR<br/>container images)]
  end

  user -- "1 load app: /*" --> cf
  cf -- "OAC signed" --> s3
  user -- "2 sign in" --> cognito
  user -- "3 API call: /api/* + X-Auth-Token" --> cf
  cf -- "OAC signed (SigV4)" --> url
  url --> lambda
  lambda -- "check token keys (JWKS)" --> cognito
  lambda -- "read / write USER#sub" --> ddb
  ecr -. "image pulled at deploy" .-> lambda
```

Reading it:

1. The browser loads the React app. CloudFront fetches the files from a private S3
   bucket, signing each request with OAC.
2. The user signs in on Cognito's hosted page and gets tokens.
3. The app calls the API on the same CloudFront domain. CloudFront signs the request and
   forwards it to the function URL, which only accepts signed requests from this
   distribution. Lambda runs FastAPI, checks the token and reads or writes DynamoDB.

## 2. Sign-in (authorization code flow with PKCE)

```mermaid
sequenceDiagram
  autonumber
  actor U as User
  participant A as React app
  participant C as Cognito hosted sign-in

  U->>A: Click "Sign in"
  A->>A: Create a random secret (PKCE verifier) and its hash (challenge)
  A->>C: Redirect to sign-in page, with the challenge
  U->>C: Email + password
  U->>C: 6-digit code from authenticator app (MFA)
  C->>A: Redirect back with a one-time code
  A->>C: Swap the code for tokens, sending the original secret
  C->>C: Hash(secret) matches the challenge?
  C-->>A: Access token (1 h) + refresh token (12 h max)
  A->>A: Access token in memory, refresh token in sessionStorage
```

Why PKCE: if someone steals the one-time code in step 6, it is useless to them, because
only the app knows the secret from step 2.

## 3. One API call, end to end

Example: adding a todo.

```mermaid
sequenceDiagram
  autonumber
  participant A as React app
  participant CF as CloudFront
  participant L as Lambda (FastAPI)
  participant C as Cognito JWKS
  participant D as DynamoDB

  A->>A: body = {"title": "Buy milk"}<br/>hash = SHA-256(body)
  A->>CF: POST /api/v1/todos<br/>X-Auth-Token: jwt<br/>x-amz-content-sha256: hash
  CF->>CF: Sign request with SigV4 (OAC)<br/>puts signature in Authorization
  CF->>L: Forward via function URL
  Note over L: Lambda checks the SigV4 signature:<br/>only our distribution is allowed
  L->>C: Get public keys (cached after first time)
  L->>L: Check JWT: signature, RS256, issuer,<br/>expiry, token_use=access, client_id
  L->>D: GetItem USER#sub / PROFILE (account still exists?)
  L->>L: Validate body (title 1-200 chars)
  L->>D: PutItem PK=USER#sub, SK=TODO#ulid
  L-->>CF: 201 Created + todo JSON
  CF-->>A: 201 Created
```

Where a request can be stopped:

| Step | Rejected if | Response |
|---|---|---|
| 4 | The request did not come through our CloudFront | 403 (from AWS) |
| 6 | The token is missing, forged, expired or for another app | 401 |
| 7 | The account was deleted | 401 |
| 8 | The input breaks a rule | 400 |

The user ID used in step 9 comes only from the token (`sub`), never from the request.

## 4. Trust boundaries

A trust boundary is a line where data moves from a less trusted place to a more trusted
one. Every boundary needs a check. The threat model (I-09) goes through each one.

```mermaid
flowchart LR
  subgraph internet [Untrusted: the internet]
    user([Browser + user input])
    attacker([Anyone else])
  end

  subgraph edge [AWS edge]
    cf[CloudFront]
  end

  subgraph app [Our backend]
    lambda[Lambda FastAPI]
  end

  subgraph data [Data]
    ddb[(DynamoDB)]
    s3[(S3 React build)]
  end

  cognito[Cognito]

  user -- "TB1: HTTPS, untrusted input" --> cf
  attacker -. "TB1: blocked by OAC if direct" .-> lambda
  cf -- "TB2: SigV4 via OAC" --> lambda
  lambda -- "TB3: IAM role, own table only" --> ddb
  cf -- "TB2: SigV4 via OAC" --> s3
  user -- "TB4: sign-in" --> cognito
```

| Boundary | What crosses it | Main check |
|---|---|---|
| TB1 | Everything the browser sends | HTTPS; token check; input validation; size limits |
| TB2 | CloudFront to origins | OAC signature; resource policies allow only our distribution |
| TB3 | Lambda to the database | Lambda's IAM role may only use our table; every key built from the token's `sub` |
| TB4 | User to Cognito | Password + MFA; admin-only accounts |

## 5. Local development (bolt B2)

Same code, no AWS.

```mermaid
flowchart LR
  dev([Browser on laptop])

  subgraph compose [Docker Compose on the Mac]
    fe[frontend<br/>Vite dev server]
    be[backend<br/>same FastAPI image]
    ddbl[(DynamoDB Local)]
  end

  tok[[Local token script<br/>signs test tokens]]

  dev --> fe
  fe -- "/api/* proxied" --> be
  be --> ddbl
  tok -. "test JWT" .-> dev
```

Differences from AWS: no CloudFront or OAC, DynamoDB Local instead of DynamoDB, and
tokens signed by a local key instead of Cognito. The backend refuses local mode if it
finds itself running in Lambda.

## 6. Deploy (from bolt B6)

```mermaid
flowchart LR
  push([git push]) --> gha[GitHub Actions]
  gha -- "tests + scanners" --> gate{All pass?}
  gate -- no --> stop([Stop])
  gate -- yes --> oidc[Get temporary AWS<br/>credentials via OIDC]
  oidc --> build[Build image,<br/>Trivy scan]
  build --> ecr[(Push to ECR,<br/>tag = commit ID)]
  ecr --> plan[terraform plan]
  plan --> approve{Owner approves?}
  approve -- yes --> apply[terraform apply<br/>Lambda uses new image]
  apply --> sync[Upload React build to S3,<br/>clear CloudFront cache]
```

No long-lived AWS keys exist anywhere in this flow. GitHub proves who it is with OIDC and
gets credentials that expire within an hour.
