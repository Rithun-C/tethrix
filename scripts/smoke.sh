#!/usr/bin/env bash
# Smoke and negative tests for the deployed app (B3-07, B3-08).
#
# Checks from the outside, like a visitor or an attacker would, that:
#   - the site and the API answer through CloudFront, with the security headers
#   - a request body travels with its SHA-256 hash (ADR-0002)
#   - every way around CloudFront is closed (function URL, bucket, plain HTTP, old TLS)
#
# Needs no AWS credentials: it only sends HTTP requests. `make smoke` passes the
# function URL and bucket name from the Terraform outputs.
#
# Usage: scripts/smoke.sh DOMAIN FUNCTION_URL BUCKET
# DOMAIN is the host name only: tethrix.satrix.in, or the *.cloudfront.net address.

set -uo pipefail

domain="${1:?domain, for example tethrix.satrix.in}"
function_url="${2:?function URL from terraform output}"
bucket="${3:?frontend bucket from terraform output}"
base="https://${domain}"

passed=0
failed=0

ok() { echo "PASS  $1"; passed=$((passed + 1)); }
bad() { echo "FAIL  $1"; failed=$((failed + 1)); }

# status URL [curl options...] -> prints the HTTP status code only
status() { curl -s -o /dev/null -w '%{http_code}' --max-time 15 "$@"; }

# header NAME FILE -> the value of a response header from a saved header dump
header() { grep -i "^$1:" "$2" | head -1 | cut -d' ' -f2- | tr -d '\r'; }

expect_status() { # description expected actual
  if [ "$3" = "$2" ]; then ok "$1 ($3)"; else bad "$1: expected $2, got $3"; fi
}

sha256() { printf '%s' "$1" | shasum -a 256 | cut -d' ' -f1; }

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

echo "== Site and API through CloudFront"

code=$(status -D "$tmp/page" "$base/")
expect_status "home page" 200 "$code"
for name in strict-transport-security content-security-policy x-content-type-options \
  x-frame-options referrer-policy; do
  if [ -n "$(header "$name" "$tmp/page")" ]; then ok "page header $name"; else bad "page header $name missing"; fi
done

expect_status "React route /todos is served by index.html" 200 "$(status "$base/todos")"

code=$(curl -s -D "$tmp/api" -o "$tmp/api.body" --max-time 15 "$base/api/v1/health" -w '%{http_code}')
expect_status "API health" 200 "$code"
if grep -q '"status":"ok"' "$tmp/api.body"; then ok "API health body"; else bad "API health body: $(cat "$tmp/api.body")"; fi
if [ -n "$(header content-security-policy "$tmp/api")" ]; then ok "API response has security headers"; else bad "API response has no CSP header"; fi

code=$(curl -s -o "$tmp/nope.body" --max-time 15 "$base/api/v1/nope" -w '%{http_code}')
expect_status "unknown API path" 404 "$code"
if grep -q '"not_found"' "$tmp/nope.body"; then ok "unknown API path answers in the API error format, not the React page"; else bad "unknown API path body: $(head -c 120 "$tmp/nope.body")"; fi

echo "== Request bodies (ADR-0002)"

body='{"hello":"world"}'
code=$(curl -s -o "$tmp/echo.body" --max-time 15 -X POST "$base/api/v1/echo" \
  -H 'Content-Type: application/json' -H "x-amz-content-sha256: $(sha256 "$body")" \
  --data "$body" -w '%{http_code}')
expect_status "POST with the body hash" 200 "$code"
if grep -q "\"received_bytes\":${#body}" "$tmp/echo.body"; then ok "echo counted ${#body} bytes"; else bad "echo body: $(cat "$tmp/echo.body")"; fi

code=$(status -X POST "$base/api/v1/echo" -H 'Content-Type: application/json' --data "$body")
if [ "$code" != "200" ]; then ok "POST without the body hash is refused ($code)"; else bad "POST without the body hash was accepted"; fi

big=$(head -c 17000 /dev/zero | tr '\0' 'x')
code=$(status -X POST "$base/api/v1/echo" -H "x-amz-content-sha256: $(sha256 "$big")" --data "$big")
expect_status "17 KB body is over the limit (SR-31)" 413 "$code"

echo "== Ways around CloudFront must be closed"

expect_status "function URL called directly (SR-62)" 403 "$(status "${function_url%/}/api/v1/health")"
expect_status "bucket read directly" 403 "$(status "https://${bucket}.s3.us-east-1.amazonaws.com/index.html")"

code=$(curl -s -o /dev/null -D "$tmp/http" --max-time 15 "http://${domain}/" -w '%{http_code}')
location=$(header location "$tmp/http")
if [ "$code" = "301" ] && [ "${location#https://}" != "$location" ]; then ok "plain HTTP redirects to HTTPS"; else bad "plain HTTP: got $code, location '$location'"; fi

if [ "${domain%.cloudfront.net}" != "$domain" ]; then
  # On the default address AWS fixes the minimum at TLS 1.0 (F-022); only our own domain
  # and certificate can require TLS 1.2. Reported, not counted as a pass or a failure.
  echo "SKIP  TLS 1.1 check: default *.cloudfront.net address (F-022, until the custom domain)"
elif curl -s -o /dev/null --max-time 15 --tlsv1.1 --tls-max 1.1 "$base/" 2>/dev/null; then
  bad "TLS 1.1 was accepted (SR-50)"
else
  ok "TLS 1.1 is refused (SR-50)"
fi

echo
echo "Passed: $passed  Failed: $failed"
[ "$failed" -eq 0 ]
