# Security Release Checklist

Gate every production deploy against this checklist. Check all boxes before merging to `main` or triggering a Railway redeploy.

## Secrets and Configuration

- [ ] `API_KEY` is at least 16 characters and not a placeholder (`changeme`, `secret`, etc.)
- [ ] `OPENAI_API_KEY` starts with `sk-` and is a live key
- [ ] `X402_PAY_TO` is the correct seller wallet address (42-char EVM address)
- [ ] `X402_FACILITATOR_URL` is `https://x402.dexter.cash` (or intentionally changed)
- [ ] `X402_NETWORK` is `eip155:8453` (Base mainnet)
- [ ] `X402_BUILDER_CODE` is blank
- [ ] `USE_LLM_FALLBACK` is `false`
- [ ] `ENFORCE_HTTPS` is `true`
- [ ] `REDIS_URL` and `DATABASE_URL` reference live Railway services (not localhost defaults)
- [ ] No secrets are hardcoded in source files or committed to git

## Payment and Auth

- [ ] Prices (`X402_PRICE_SVG`, `X402_PRICE_PNG`) match intended values
- [ ] Paid endpoints return `402` without a payment header (manually verify)
- [ ] Admin endpoints return `401` without `X-API-Key` header
- [ ] Admin endpoints return `403` if `ADMIN_IP_ALLOWLIST` is set and IP doesn't match

## Rate Limiting and Security Headers

- [ ] `RATE_LIMIT_PAID` is set (default `20/minute`)
- [ ] Paid endpoint returns `429` after exceeding limit (verify with smoke test)
- [ ] Response includes `Strict-Transport-Security` header
- [ ] Response includes `X-Content-Type-Options: nosniff`
- [ ] Response includes `X-Frame-Options: DENY`

## Code Quality

- [ ] No `print()` statements left in production paths
- [ ] No `TODO: remove before prod` comments
- [ ] No hardcoded URLs other than approved external services (mermaid.ink, kroki.io, x402.dexter.cash)
- [ ] All new env vars documented in `.env.example`

## Infrastructure

- [ ] Railway Postgres backup retention confirmed (check Backups tab)
- [ ] Railway Redis is connected (check deploy logs for `Redis connected`)
- [ ] `/health` returns `200` after deploy
- [ ] No `STARTUP SECURITY WARNING` lines in deploy logs

## Post-Deploy Smoke Test

Run after every deploy:
```bash
python scripts/x402_buyer_payment_test.py
```
Expected: `402` challenge → signed payment → `200` with diagram SVG.
