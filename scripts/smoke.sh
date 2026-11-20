#!/usr/bin/env bash
# Smoke and negative tests for the deployed app (B3-07, B3-08; ADR-0007).
#
# Checks from the outside, like a visitor or an attacker would, that:
#   - the page, its files and the API answer, with the security headers
#   - caching is right: files for a year, index.html never
#   - request bodies arrive, and oversized ones are refused
#   - the side doors are closed (other files, plain HTTP, old TLS, the default address
#     once the custom domain is on)
#
# Needs no AWS credentials: it only sends HTTP requests. `make smoke` passes the two
# host names from the Terraform outputs.
#
# Usage: scripts/smoke.sh APP_HOST API_HOST
#   APP_HOST  where the app is served: tethrix.satrix.in, or the execute-api host name
#   API_HOST  API Gateway's own execute-api host name (the same as APP_HOST while the
#             custom domain is off)

set -uo pipefail

app_host="${1:?app host, for example tethrix.satrix.in}"
api_host="${2:?execute-api host from terraform output}"
base="https://${app_host}"

passed=0
failed=0

ok() { echo "PASS  $1"; passed=$((passed + 1)); }
bad() { echo "FAIL  $1"; failed=$((failed + 1)); }
info() { echo "INFO  $1"; }

# status URL [curl options...] -> prints the HTTP status code only
status() { curl -s -o /dev/null -w '%{http_code}' --max-time 15 "$@"; }

# header NAME FILE -> the value of a response header from a saved header dump
header() { grep -i "^$1:" "$2" | head -1 | cut -d' ' -f2- | tr -d '\r'; }

expect_status() { # description expected actual
  if [ "$3" = "$2" ]; then ok "$1 ($3)"; else bad "$1: expected $2, got $3"; fi
}

has_security_headers() { # description header-file
  local missing=""
  for name in strict-transport-security content-security-policy x-content-type-options \
    x-frame-options referrer-policy; do
    [ -n "$(header "$name" "$2")" ] || missing="$missing $name"
  done
  if [ -z "$missing" ]; then ok "$1 has all security headers"; else bad "$1 is missing:$missing"; fi
}

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

echo "== The app: $base"

code=$(curl -s -D "$tmp/page" -o "$tmp/page.body" --max-time 15 "$base/" -w '%{http_code}')
expect_status "home page" 200 "$code"
has_security_headers "home page" "$tmp/page"
if [ "$(header cache-control "$tmp/page")" = "no-cache" ]; then ok "index.html is never cached"; else bad "index.html cache-control: '$(header cache-control "$tmp/page")'"; fi

expect_status "React route /todos is served by index.html" 200 "$(status "$base/todos")"

asset=$(grep -o '/assets/[^"]*\.js' "$tmp/page.body" | head -1)
if [ -n "$asset" ]; then
  code=$(curl -s -D "$tmp/asset" -o /dev/null --max-time 15 "$base$asset" -w '%{http_code}')
  expect_status "script file $asset" 200 "$code"
  case "$(header cache-control "$tmp/asset")" in
    *immutable*) ok "script file is cached for a year" ;;
    *) bad "script file cache-control: '$(header cache-control "$tmp/asset")'" ;;
  esac
else
  bad "no /assets/*.js link found in the home page"
fi

echo "== The API"

code=$(curl -s -D "$tmp/api" -o "$tmp/api.body" --max-time 15 "$base/api/v1/health" -w '%{http_code}')
expect_status "API health" 200 "$code"
if grep -q '"status":"ok"' "$tmp/api.body"; then ok "API health body"; else bad "API health body: $(cat "$tmp/api.body")"; fi
has_security_headers "API response" "$tmp/api"

code=$(curl -s -o "$tmp/nope.body" --max-time 15 "$base/api/v1/nope" -w '%{http_code}')
expect_status "unknown API path" 404 "$code"
if grep -q '"not_found"' "$tmp/nope.body"; then ok "unknown API path answers in the API error format, not the React page"; else bad "unknown API path body: $(head -c 120 "$tmp/nope.body")"; fi

body='{"hello":"world"}'
code=$(curl -s -o "$tmp/echo.body" --max-time 15 -X POST "$base/api/v1/echo" \
  -H 'Content-Type: application/json' --data "$body" -w '%{http_code}')
expect_status "POST with a body" 200 "$code"
if grep -q "\"received_bytes\":${#body}" "$tmp/echo.body"; then ok "echo counted ${#body} bytes"; else bad "echo body: $(cat "$tmp/echo.body")"; fi

big=$(head -c 17000 /dev/zero | tr '\0' 'x')
expect_status "17 KB body is over the limit (SR-31)" 413 "$(status -X POST "$base/api/v1/echo" --data "$big")"

echo "== Side doors must be closed"

code=$(status --path-as-is "$base/assets/%2e%2e/%2e%2e/etc/passwd")
if [ "$code" = "404" ] || [ "$code" = "400" ] || [ "$code" = "403" ]; then ok "path outside the static folder is refused ($code, T-037)"; else bad "path traversal answered $code"; fi

# API Gateway does not listen on plain HTTP at all, so the connection must fail or be
# refused; it must never serve the app.
code=$(status "http://${app_host}/")
if [ "$code" != "200" ]; then ok "plain HTTP does not serve the app (got '$code')"; else bad "plain HTTP served the app"; fi

if curl -s -o /dev/null --max-time 15 --tlsv1.1 --tls-max 1.1 "$base/" 2>/dev/null; then
  if [ "$app_host" = "$api_host" ]; then
    # The default address uses AWS's own TLS settings; only our domain has TLS_1_2 set
    # explicitly. Reported for the record, not counted.
    info "TLS 1.1 accepted on the default execute-api address (custom domain will require TLS 1.2)"
  else
    bad "TLS 1.1 was accepted on the custom domain (SR-50)"
  fi
else
  ok "TLS 1.1 is refused (SR-50)"
fi

if [ "$app_host" != "$api_host" ]; then
  code=$(status "https://${api_host}/api/v1/health")
  if [ "$code" != "200" ]; then ok "default execute-api address is switched off ($code, T-038)"; else bad "default execute-api address still answers"; fi
else
  info "custom domain is off: the execute-api address is the app's address for now"
fi

echo
echo "Passed: $passed  Failed: $failed"
[ "$failed" -eq 0 ]
