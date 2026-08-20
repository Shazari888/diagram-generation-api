# Security Runbook

Operational playbook for security incidents affecting the Diagram Generation API.

---

## 1. Key Compromise Response

**Symptoms:** Unauthorized use of `API_KEY`, `OPENAI_API_KEY`, or x402 wallet.

**Steps:**
1. **Rotate immediately** — update the compromised secret in Railway Variables and redeploy
2. `API_KEY` — generate a new random 32-char string, update Railway, redeploy
3. `OPENAI_API_KEY` — revoke in OpenAI dashboard, generate new key, update Railway
4. `X402_PAY_TO` wallet — if private key is compromised, transfer remaining USDC to a new wallet immediately, then update `X402_PAY_TO` in Railway
5. After rotation, scan Railway logs for unauthorized calls during the exposure window
6. If `API_KEY` was exposed, audit all calls to `/diagrams/generate` and `/diagrams/{id}` in that window

---

## 2. Facilitator Outage Response

**Symptoms:** All `/paid/diagrams/generate/*` requests return `500` or hang; Railway logs show facilitator connection errors.

**Steps:**
1. Check facilitator status: `curl https://x402.dexter.cash/supported`
2. If Dexter is down, optionally switch to the Coinbase CDP facilitator:
   - Set `X402_FACILITATOR_URL=https://api.cdp.coinbase.com/platform/v2/x402` in Railway
   - Set `CDP_API_KEY_ID` and `CDP_API_KEY_SECRET` from Coinbase Developer Platform
   - Redeploy
3. If no alternative is available, set `X402_ENABLED=false` in Railway and redeploy — this disables paid routes and prevents 500 errors
4. Monitor `https://dexter.cash` for recovery, then re-enable

---

## 3. Payment Anomaly Triage

**Symptoms:** `security.anomaly` log entries showing repeated 402 failures from same IP; unexpected USDC movements.

**Steps:**
1. Check Railway logs for: `ANOMALY ip=<ip>` entries
2. If a single IP is hammering 402s (probe/replay attempt):
   - Add the IP to `ADMIN_IP_ALLOWLIST` is not relevant here — instead lower `RATE_LIMIT_PAID` temporarily (e.g. `5/minute`) in Railway and redeploy
3. For unexpected USDC movements on `X402_PAY_TO`:
   - Check Base mainnet explorer: `https://basescan.org/address/<X402_PAY_TO>`
   - If unauthorized, the payment wallet key is compromised — follow Key Compromise steps above
4. Replay attacks are rejected by the x402 facilitator's nonce enforcement (300s window). If a replay somehow succeeded, open an issue with Dexter support.

---

## 4. Rollback Steps

**Roll back a bad deploy:**
1. Go to Railway → your service → **Deployments** tab
2. Find the last known-good deploy
3. Click **Rollback** on that deployment
4. Verify `/health` returns `{"status": "ok"}`

**Roll back a database migration:**
- Currently using SQLAlchemy `create_all` (additive only, no destructive migrations)
- No rollback needed for schema changes — old columns are simply unused
- If data corruption occurs, restore from Railway Postgres automatic backup:
  - Railway → Postgres service → **Backups** tab → restore to point-in-time

---

## 5. Contact and Escalation

| Resource | URL |
|---|---|
| Railway status | https://status.railway.app |
| Dexter facilitator | https://dexter.cash |
| Base network status | https://status.base.org |
| OpenAI status | https://status.openai.com |
