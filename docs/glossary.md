# Glossary

Plain-language meanings of the terms used in this project. New terms are added here when
they first come up. AWS service names are explained in the bolt where they are first used.

## The work cycle

| Term | Meaning |
|---|---|
| AI-DLC | AI-Driven Development Life Cycle. A way of working where the AI drafts and a human approves at each step. We do not use the AWS tool of that name, only the idea. |
| Phase | One of the three big stages of the project: Inception, Construction, Operations. |
| Inception | Deciding what to build and how: scope, design, risks and costs. No code yet. |
| Construction | Building the app, one piece at a time. |
| Operations | Running the app like a real service: monitoring, security testing, practising incidents. |
| Bolt | A short work cycle of one to three weeks that delivers one working piece, such as "Auth" or "Todos". It is AI-DLC's word for what Agile calls a sprint. Ours are numbered B1 to B11. |
| Gate | A checkpoint where Claude stops and the owner approves before anything continues. |
| Guardrails | The safety setup done before real work (Week 0): MFA, budget alerts, audit logging. A later mistake is then caught or limited. |
| Definition of Done | The checklist a bolt must meet before it counts as finished, so "done" means the same thing every time. |
| Walking skeleton | The thinnest possible version of the whole system, deployed end to end. Ours is a "hello world" page that passes through every AWS piece, proving the plumbing works before features depend on it. |
| MVP | Minimum viable product. The smallest version of the app that is actually useful. |
| Cut line | The agreed list of what gets dropped first if time runs short. |

## The documents

| Term | Meaning |
|---|---|
| ADR | Architecture decision record. A one-page note for one decision: the options, what we chose and why. It lets you look back later and see the reasoning. |
| Threat model | A structured list of what could go wrong security-wise and what we do about each item. |
| STRIDE | A checklist of six threat types used to build the threat model: Spoofing, Tampering, Repudiation, Information disclosure, Denial of service, Elevation of privilege. |
| Findings log | The list of every security problem a scanner or test reports, and whether we fixed or accepted it. |
| Runbook | Exact step-by-step instructions for a routine or emergency job, such as "end of session cleanup". |
| Postmortem | A write-up after an incident: what happened, why, and what changes to stop it recurring. |
| Retrospective | A look back at the end of the project on what worked and what did not. |

## App design terms

| Term | Meaning |
|---|---|
| User story | A short need in the form "As a user, I want ... so that ...". |
| Acceptance criteria | The checks that prove a story is done. Each becomes a test. |
| Domain model | The things the app knows about (todo, habit, page...), their fields and how they relate, independent of any database. |
| API | Application Programming Interface. Here: the list of web addresses the frontend calls to read and change data. |
| REST | A common API style: each kind of thing has its own address, and the HTTP method (GET, POST, PUT, PATCH, DELETE) says what to do. |
| Endpoint | One method plus path in the API, such as `POST /todos`. |
| Idempotent | Safe to repeat: doing it twice has the same effect as once. |
| ULID | A random ID that also sorts by creation time. |
| Pagination | Returning a long list in pages, with a cursor to fetch the next page. |
| Optimistic concurrency | Saving with the version you started from, so a save is refused (409) if someone saved in between, instead of silently overwriting. |

## DynamoDB terms

| Term | Meaning |
|---|---|
| Item | One record in a DynamoDB table, like a row. |
| Partition key (PK) | The part of the key that decides where an item is stored. Items with the same PK are kept together. |
| Sort key (SK) | The part of the key that orders items inside one partition. |
| Access pattern | A question the app asks the database. In DynamoDB the keys are designed from these. |
| Query | Reads items from one partition, optionally filtered by SK (begins with, between). Fast and cheap. |
| Scan | Reads the whole table. Slow and expensive; we never use it. |
| GSI | Global secondary index. A copy of selected items with different keys, so the same data can be queried another way. |
| Sparse index | An index that only contains items that have its key fields. |
| Projection | Which fields an index copies. |
| Single-table design | Storing several kinds of items in one table, told apart by their keys. |
| Provisioned capacity | Paying for a fixed number of read and write units per second. Ours stays inside the free tier. |
| Throttling | AWS slowing down requests that go over the capacity you set. |

## AWS edge, sign-in and packaging terms

| Term | Meaning |
|---|---|
| CloudFront | AWS's content delivery network. Serves the React app and forwards `/api/*` to the backend. |
| Origin | Where CloudFront fetches content from: the S3 bucket or the Lambda function URL. |
| Function URL | A built-in HTTPS address for one Lambda function. |
| OAC | Origin Access Control. CloudFront signs every request to the origin, so the origin can refuse anything that did not come through CloudFront. |
| SigV4 | AWS's way of signing a request with credentials, so AWS can check who sent it and that it was not changed. |
| CORS | Browser rules for calling an API on a different domain. Not needed here because the app and API share one domain. |
| Cognito user pool | AWS's user directory: stores users and passwords, handles MFA, issues tokens. |
| JWT | JSON Web Token. A signed piece of JSON saying who you are and until when. |
| Access token / refresh token | The short-lived JWT the API checks / the longer-lived token used to get a new access token. |
| JWKS | The public keys Cognito publishes, used to check a JWT's signature. |
| OAuth 2.0 / OIDC | The standard protocols for signing in through an identity provider. |
| PKCE | An extra check in the OAuth sign-in flow that stops a stolen sign-in code from being used. |
| ECR | Elastic Container Registry. AWS's private store for container images. |
| Lambda Web Adapter | A small AWS program inside the container that turns Lambda events into normal HTTP requests, so FastAPI runs unchanged. |
| Cold start | The delay when Lambda starts a new copy of a function after idle time. |
| arm64 / Graviton | AWS's ARM-based processors. Cheaper than x86 for Lambda. |

## Tools and security terms

| Term | Meaning |
|---|---|
| Terraform | A tool where you describe infrastructure in files and it creates it for you. |
| plan / apply / destroy | Terraform commands. `plan` shows what would change, `apply` makes the change, `destroy` removes it. |
| State | Terraform's record of what it has created. It lives in an S3 bucket so it is not lost. |
| Bootstrap | The small foundation that has to exist before the normal process can work, set up in a special way because the normal tools cannot build it yet. Ours (`infra/bootstrap/`) holds the state bucket and account-wide guardrails. It is created first, changes rarely and is destroyed last. The word comes from "pulling yourself up by your own bootstraps", and is also where computer "booting" gets its name. |
| Backend | Where Terraform stores its state. Ours is the S3 bucket. |
| Data source | A Terraform block that only reads something from AWS, such as the account ID. It never creates anything. |
| Import | Telling Terraform about a resource that already exists so it can manage it from then on. |
| Import block | The way to import written in code (`import { to = ..., id = ... }`), so the import shows up in the plan and can be reviewed first. |
| tfvars | A file (`terraform.tfvars`) that sets variable values. Terraform loads it automatically. Ours is git-ignored because it holds personal values like your email. |
| Dynamic block | A Terraform loop that writes several similar blocks from a list. Used for the 50%, 80% and 100% budget alerts. |
| Sensitive variable | A variable marked `sensitive = true`. Terraform hides its value in plan output. |
| Lab | A short hands-on exercise with a paid service, created and destroyed the same day. |
| Scanner | A tool that checks code automatically. |
| tflint, checkov | Scanners for Terraform files. |
| Semgrep | Scanner for application code. |
| Trivy | Scanner for container images. |
| gitleaks | Scanner that looks for secrets in the repo. |
| pip-audit, npm audit | Scanners for vulnerable Python and JavaScript dependencies. |
| uv | A fast Python package and project manager. It replaces pip and virtualenv, and writes the lockfile `uv.lock`. |
| CI/CD | Automation that tests every change (CI) and deploys it (CD). Ours runs on GitHub Actions. |
| OIDC | A way for GitHub to prove its identity to AWS and get temporary access, so no permanent AWS key is stored anywhere. |
| Account default | A setting made once for the whole account (or region) that applies to every resource created afterwards. A safety net for resources that forget a setting. |
| EBS | Elastic Block Store. The virtual hard disks attached to EC2 servers. |
| Snapshot | A point-in-time backup copy of an EBS disk. |
| AMI | Amazon Machine Image. A saved server image used to launch EC2 instances. |
| IMDS | Instance Metadata Service. A local address inside every EC2 server that tells it about itself and hands out its temporary AWS credentials. IMDSv2 requires a session token first, which blocks credential theft through SSRF. |
| SSRF | Server-side request forgery. A bug that lets an attacker make your server fetch a URL of their choosing. |
| CIS benchmark | A widely used checklist of secure settings, published by the Center for Internet Security. Scanners like checkov and Prowler test against it. |
| CloudTrail | The AWS service that records every action taken in the account: who, what, when and from where. |
| Management event | An action that creates, changes or deletes a resource, or a sign-in. Recorded free by the first trail. |
| Data event | An action on the data inside a resource, such as reading an S3 file. Costs money per event to record. |
| Event history | The free, read-only last 90 days of management events that every account has, even without a trail. |
| Digest file | An hourly signed file CloudTrail writes so you can later prove no log was changed or deleted. |
| ARN | Amazon Resource Name. The unique ID of anything in AWS, such as `arn:aws:s3:::my-bucket`. Policies refer to resources by ARN. |
| Confused deputy | When a trusted service is tricked into acting for someone else. Prevented by checking `aws:SourceArn` in policies. |
| Access Analyzer | A free AWS service that flags resource policies giving access to someone outside the account. Also checks policies for mistakes (`validate-policy`). |
| Finding | A problem reported by a scanner or analyzer. Ours are logged in `docs/security/findings-log.md`. |
| Privilege escalation | Using a small permission to gain a bigger one, for example `iam:PassRole` on `*` to hand yourself an admin role. |
| IAM role | An identity with permissions but no password or keys. Someone or something "assumes" it to get temporary credentials. |
| Assume role | Temporarily switching to a role's permissions. The credentials expire on their own. |
| Trust policy | The part of a role that says who may assume it. |
| Managed policy | A ready-made permissions policy maintained by AWS, such as `SecurityAudit`. |
| Image digest | A fingerprint (`sha256:...`) of one exact container image. Pinning it guarantees the same image every time, even if the tag is moved. |
| Baseline | A first measurement kept for later comparison. |
| Least privilege | Giving each piece only the permissions it needs and nothing more. |
| IDOR | A bug where user A can read user B's data just by changing an ID in a request. |
| XSS | A bug where an attacker's script gets saved in content and runs in another user's browser. |
| Prowler | A tool that audits the AWS account's settings. |
| OWASP ZAP | A tool that attacks the running web app to find weaknesses. |
| Trust boundary | A line where data moves from a less trusted place to a more trusted one, for example from the internet into our backend. Every boundary needs a check. |
| Asset | Something worth protecting, such as journal entries or the AWS account. |
| Mitigation | A control that blocks a threat or makes it less harmful. |
| Residual risk | The risk that is left after the mitigations. We accept it in writing, with a reason. |
| Denial of wallet | An attack that does not break the app but makes it cost money, for example a flood of requests. |
| Supply chain attack | An attack through something we depend on: a fake or hijacked package, base image or GitHub Action. |
| Clickjacking | Loading our app in a hidden frame on another site to trick the user into clicking things. |
| Security headers | Instructions the server sends with each page telling the browser to be stricter (CSP, HSTS and others). |
| CSP | Content Security Policy. A header listing where the browser may load scripts and data from. It stops most injected scripts from running. |
| HSTS | A header that tells the browser to always use HTTPS for this site. |
| OWASP | A non-profit that publishes free web security guides and tools. |
| ASVS | OWASP Application Security Verification Standard: a catalogue of security rules for web apps. We use a subset in I-12. |
| Security requirement | A rule the code must follow, with a test that proves it (SR-xx in I-12). |
| Always-free | AWS limits that stay free for the life of the account, such as 1 million Lambda requests a month. |
| Credit reserve | Credits we never spend on purpose. When the balance falls to the reserve, all labs stop (I-11). |
| Time box | A fixed time limit. A lab's resources must be destroyed by the time written in its README. |
| Availability Zone (AZ) | One data centre group inside a region. Some services charge per AZ. |
| Load balancer (ALB) | A service that spreads web requests over several servers or containers. It is charged by the hour. |
| Well-Architected Framework | AWS's checklist for judging a design, grouped into six pillars: operational excellence, security, reliability, performance efficiency, cost optimization, sustainability. |
| ECS | Elastic Container Service. AWS's own service for running long-lived containers. |
| Fargate | A way to run ECS (or EKS) containers without managing servers. Charged per second while running. |
| EKS | Elastic Kubernetes Service. Kubernetes run by AWS; the cluster alone costs 0.10 USD an hour. |
| Kubernetes | Open-source software that runs and connects many containers across many servers. Practised locally with kind. |
| Scale to zero | When nothing runs, and nothing is charged, while there are no requests. Lambda does this; ECS and EKS do not. |
| Repository (repo) | A project folder whose full change history is kept by git. |
| Commit | One saved change in git, with a message and an author. |
| Branch | A separate line of work in a repo. `main` is the line that counts. |
| Pull request (PR) | A request on GitHub to merge a branch into `main`. Checks run on it first. |
| Fork | Someone else's copy of a repo on GitHub, from which they can send a pull request. |
| CI | Continuous integration: checks that run automatically on every push. Ours is GitHub Actions. |
| Workflow | A file in `.github/workflows/` that tells GitHub Actions what to run and when. |
| Static check | A check that reads code without running it. |
| Linter | A tool that finds mistakes and bad style in code. tflint is one for Terraform. |
| Pre-commit hook | A check that runs on the laptop each time `git commit` is used. |
| Makefile | A file of named shortcuts for long commands, run with `make <name>`. |
| Pinning | Writing down the exact version of a dependency so it cannot change unnoticed. |
| Tag | A movable label on a version of an image or of code, such as `v4`. |
| Digest | The sha256 fingerprint of a Docker image. Unlike a tag, it cannot point at other content. |
| Commit SHA | The fingerprint of one git commit. Used to pin GitHub Actions. |
| Lockfile | A generated file listing the exact version and hash of every package installed. |
| Supply chain | Everything not written by us that ends up in the app or the build: packages, images, tools, actions. |
| Typosquatting | Publishing a malicious package under a name that looks like a popular one. |
| Dependabot | GitHub's bot that opens pull requests for dependency updates and raises security alerts. |
| Push protection | A GitHub feature that refuses a push containing a known secret format. |
| Ruleset | GitHub settings that protect a branch, for example "changes only through a pull request with passing checks". |
| State (Terraform) | Terraform's record of which real resources belong to which lines of code. |
| State lock | A marker that stops two Terraform runs from changing the same state at once. |
| Drift | When real infrastructure no longer matches the Terraform state because of a change made outside Terraform. |
| Module (Terraform) | A folder of Terraform files used as a unit, with inputs and outputs. |
| Blast radius | How much one mistake or break-in can damage. |
| Defence in depth | Several independent layers of protection, so one failing layer is not the end. |
| Dockerfile | The recipe for building a container image, one instruction per line. |
| Multi-stage build | A Dockerfile with several stages; only the result of the build is copied into the final, smaller image. |
| Docker Compose | A tool that starts several containers together from one file, `compose.yaml`. |
| Bind mount | A folder on the laptop made visible inside a container. |
| Hot reload | The app restarts or refreshes by itself when a source file changes. |
| Proxy | A server that passes a request on to another server. |
| CORS | Browser rules for when a page from one address may call an API on another address. Not needed here because pages and API share one address. |
| DynamoDB Local | AWS's free program that behaves like DynamoDB and runs on the laptop. |
| Health check | A cheap request that answers "is this service up?". |
| Seed data | Made-up data loaded into a local database so there is something to test with. |
| hadolint | A linter for Dockerfiles. |
| kind | "Kubernetes in Docker": a real Kubernetes cluster that runs inside Docker on the laptop. |
| Non-root user | A user inside a container without administrator rights, so a break-in can do less. |
| Cooldown (dependencies) | A waiting time before a newly published version may be used, because most malicious releases are found within days. |
| Build cache | Results of earlier build steps and downloads that Docker keeps, so the next build is faster. |
| tmpfs | A folder that exists only in memory. Used for `/tmp` in containers whose file system is read-only. |
| Linux capabilities | Separate pieces of root's power (for example opening low ports). Dropping them all leaves a container with only what an ordinary process can do. |
| IPv4 / IPv6 | The old and the new version of internet addresses. A network can have a good route for one and a bad route for the other. |
| ASGI | The standard way Python web servers (uvicorn) hand requests to web apps (FastAPI). |
| Middleware | Code that wraps every request, before and after the route runs. Ours writes the request log line. |
| Vite | The tool that serves the frontend during development (with hot reload) and builds the final files. |
| Dev server | A local web server for development only. It rebuilds on every change and is never used in AWS. |
| Production build | The finished, shrunk frontend files (`dist/`) that are uploaded to S3. |
| Single-page app (SPA) | A site with one HTML file; JavaScript swaps the screens. The server must answer every address with that one file. |
| nginx | A small, fast web server. Used here only in the frontend `static` image. |
| ESLint | A linter for JavaScript and TypeScript. |
| Prettier | A tool that formats code the same way every time, so layout is never discussed. |
| Vitest | The test runner for the frontend. |
| Mock | A stand-in used in a test, for example a fake `fetch` so no real server is called. |
| Peer dependency | A package that another package needs you to install yourself, in a version range it accepts. |
| Install script | Code a package runs on your machine when it is installed. Switched off here (`ignore-scripts`). |
| Source map | A file that maps built code back to the original source. Not published here. |
| Namespace (Linux) | A kernel feature that gives a process its own view of the system (processes, network, files). One of the things a container is made of. |
| cgroup | "Control group": a kernel feature that limits and counts the CPU and memory a process may use. |
| Image layer | One step of an image's file changes. Layers are stacked; a file deleted in a later layer is still in the earlier one. |
| Distroless image | A base image with only the language runtime: no shell and no package manager. |
| seccomp | A kernel filter that blocks system calls a normal app never needs. |
| Orchestrator | Software that runs containers across machines: restarts, scaling, rollouts. Kubernetes is one. |
| Cluster | A set of machines (nodes) run by Kubernetes. |
| Node | One machine in a cluster. In kind, a node is a Docker container. |
| Control plane | The parts of Kubernetes that decide (API server, etcd, controllers, scheduler). EKS runs these for an hourly price. |
| kubectl | The command-line tool that talks to a Kubernetes cluster. |
| Manifest | A YAML file that says what should exist in a cluster. |
| Pod | The smallest unit Kubernetes runs: one or more containers that share a network address. |
| Deployment | A Kubernetes object that keeps a set number of copies of a pod running and rolls out new versions. |
| ReplicaSet | The object a Deployment uses to keep the copies; one per version. |
| Service (Kubernetes) | A stable name and address in front of a changing set of pods. |
| Namespace (Kubernetes) | A named area in a cluster that groups objects. Not the same as a Linux namespace. |
| ConfigMap | Settings or small files stored in the cluster and given to pods. |
| Job (Kubernetes) | Runs a pod until it finishes successfully, once. |
| Probe | A check Kubernetes runs against a container. Readiness: may it get traffic? Liveness: must it be restarted? |
| Rolling update | Replacing pods with a new version a few at a time, so the service stays up. |
| NetworkPolicy | Rules for which pods may connect to which pods. Without one, every pod can reach every pod. |
| Pod Security Admission | A built-in Kubernetes check that refuses pods which do not meet a security level (ours: "restricted"). |
| Port-forward | A temporary tunnel from a port on the laptop to a pod or Service. |
| Distribution (CloudFront) | One CloudFront set-up: a domain name, its origins and its behaviours. |
| Behaviour (CloudFront) | A rule "requests whose path matches X go to origin Y, with these settings". We have two: `/api/*` and everything else. |
| Response headers policy | CloudFront settings that add headers such as CSP and HSTS to every response. |
| CloudFront Function | A few lines of JavaScript CloudFront runs on each request before choosing an origin. Ours sends React routes like `/todos` to `index.html`. |
| Invalidation | Telling CloudFront to forget cached copies, so newly published files are served. |
| Reserved concurrency | A cap on how many copies of one Lambda function may run at the same time. |
| Lambda extension | A program Lambda starts next to the function, from `/opt/extensions`. The Web Adapter is one. |
| Readiness check | A request the Web Adapter makes after a cold start; traffic only flows once it succeeds. |
| PITR (point-in-time recovery) | A continuous DynamoDB backup: the table can be restored to any second of the last 35 days. |
| Request body limit | The largest body the API accepts. Bigger requests get 413 before any route runs (SR-31). |
| DNS | The internet's phone book: turns a name like `tethrix.satrix.in` into a server address. |
| DNS record | One entry in DNS. A CNAME says "this name is another name"; an NS record says which servers answer for a name. |
| Route 53 | AWS's DNS service. |
| Hosted zone | Route 53's container for the DNS records of one domain or subdomain. 0.50 USD a month. |
| Delegation (DNS) | The parent domain hands one subdomain to other name servers with NS records, and keeps the rest. |
| Alias record | A Route 53 record that points a name at an AWS resource such as CloudFront. |
| ACM | AWS Certificate Manager: issues and renews the TLS certificate for our domain. Public certificates are free. |
| DNS validation | ACM proves we control a name by asking for a special DNS record; it stays in place so renewals are automatic. |
| Certificate Transparency | Public logs of every TLS certificate issued. A domain becomes public the moment its certificate exists. |
| Subdomain takeover | Someone else serves content on our name because a DNS record still points at something we deleted. |
