# ADR-0006: Custom domain and DNS

- Status: Accepted 2026-11-20 (domain and Option A both confirmed by the owner).
  Switched on later: see "Update 2026-11-20" at the end
- Date: 2026-11-20
- Task: B3-04
- Replaces the decision of 2026-11-11 "No custom domain; use the default CloudFront
  domain"

## Context

The owner bought the domain `satrix.in` and wants the app at `tethrix.satrix.in`.
`satrix.in` is used for other things too, so this project must only ever touch the
subdomain `tethrix`.

Words used below:

- DNS: the internet's phone book. It turns a name like `tethrix.satrix.in` into the
  address of a server.
- DNS record: one line in that phone book. A CNAME says "this name is another name"; an
  NS record says "these name servers answer for this name and everything under it".
- Hosted zone: Route 53's container for the records of one domain or subdomain.
- Delegation: the parent (`satrix.in`) hands one subdomain (`tethrix`) to other name
  servers with NS records. The parent keeps everything else.
- ACM (AWS Certificate Manager): issues the TLS certificate that lets browsers trust
  `https://tethrix.satrix.in`. Public certificates are free and renew themselves.
- DNS validation: ACM proves we control the name by asking for a special record to be
  published. It stays published so renewals happen without anyone acting.
- Alias record: a Route 53 record that points a name at an AWS resource such as a
  CloudFront distribution. Queries for aliases to CloudFront are free.

What a custom domain changes:

- TLS: with the default `*.cloudfront.net` name, CloudFront always allows TLS 1.0 and
  1.1. With our own certificate we can require TLS 1.2 (policy `TLSv1.2_2021`), so
  SR-50 is met in full.
- The address is stable. Cognito callback URLs in B4 can be written before any deploy,
  and a rebuilt distribution keeps the same address.
- The name becomes public the moment the certificate is issued: every public certificate
  is published in Certificate Transparency logs. Writing it in the public repo therefore
  reveals nothing new.

## Options

### Option A: Route 53 hosted zone for `tethrix.satrix.in` only, delegated from the parent

Terraform creates a hosted zone for the subdomain. The owner adds four NS records for
`tethrix` at the DNS provider of `satrix.in`, once. After that every record (certificate
validation, the alias to CloudFront) is created and destroyed by Terraform.

- For: all records are in Terraform (hard constraint 4); the rest of `satrix.in` is never
  touched; the delegation is a one-time step outside AWS, like the root MFA bootstrap.
- Against: 0.50 USD a month for the hosted zone, not prorated, so about 3.50 USD until the
  account closes; one more service to learn and secure.
- Cost: 0.50 USD a month, plus fractions of a cent for queries.

### Option B: Records added by hand at the provider of `satrix.in`

A CNAME for `tethrix` pointing at the CloudFront name, and the ACM validation CNAME.

- For: free; no new AWS service.
- Against: two records outside Terraform, typed by hand; if the distribution is rebuilt,
  the CNAME must be changed by hand; does not practise Route 53.
- Cost: 0.

### Option C: Move all of `satrix.in` to Route 53

- Against: puts the owner's whole domain inside a learning account that will be closed;
  the final destroy would take the parent domain's DNS with it. Rejected.

## Decision

Option A. It keeps hard constraint 4 for a small, known cost, and
Route 53 is worth practising.

Details:

| Setting | Value |
|---|---|
| Name | `tethrix.satrix.in`, a Terraform variable with this default |
| Hosted zone | Public, for `tethrix.satrix.in` |
| Certificate | ACM, public, in us-east-1 (CloudFront only uses certificates from there), DNS validation |
| CloudFront | Alternate domain name `tethrix.satrix.in`, TLS policy `TLSv1.2_2021`, SNI only (the dedicated IP option costs 600 USD a month) |
| Records | `A` and `AAAA` alias records to the distribution (IPv4 and IPv6) |
| Default name | `*.cloudfront.net` keeps working; the app is only ever linked by the custom name |

Order of the first deploy: create the hosted zone, the owner adds the NS records at the
parent and waits until `dig NS tethrix.satrix.in` shows the Route 53 servers, then the
certificate can be validated and the distribution created. The runbook gives each step.

## Consequences

- SR-50 is met in full; there is no accepted TLS finding.
- Threat T-032 changes from "old TLS versions allowed" to "subdomain takeover": if the
  hosted zone is deleted while the NS records still exist at the parent, someone else
  could create a zone that matches them and serve content on our name. The final-destroy
  runbook therefore removes the NS records at the parent first, and only then destroys
  the zone.
- Cost: the app goes from under 0.05 to about 0.55 USD a month, still inside the 2 USD
  allowed in the cost model.
- ADR-0003: the Cognito callback and sign-out URLs are `https://tethrix.satrix.in/...`.
- Route 53 and ACM are checked against the Free plan before the first apply.

## Update 2026-11-20: switched on later

The registrar (GoDaddy) put `satrix.in` on `clientHold` five days after it was bought,
waiting for identity verification that keeps failing. While on hold the domain does not
exist in DNS, so it cannot be delegated and no certificate can be validated.

Owner's decision: deploy B3 on the default `*.cloudfront.net` address now and add the
domain later. Terraform has a switch, `use_custom_domain`, default `false` until the hold
is lifted. With `false` no zone, certificate or record is created (and no 0.50 USD a
month is paid), and CloudFront uses its own certificate.

What is lost until then: AWS fixes the minimum TLS version at 1.0 for the default
certificate, so SR-50 is not fully met (F-022, T-036). Browsers use TLS 1.3 anyway.
Nothing has to be rebuilt to switch: the same distribution gets the name and the
certificate.

## What I learned

To be filled in by the owner.
