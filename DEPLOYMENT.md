# Deployment Information

## Public URL

https://agent-production-2b644bfe.up.railway.app

## Platform

Railway — project `day14-ha-huy-thai-agent`, environment `production`.

## Test commands

Sau khi deploy, thay các biến bên dưới bằng giá trị thật. Không commit API key.

```bash
BASE="https://agent-production-2b644bfe.up.railway.app"
AGENT_API_KEY="$(railway variable list --service agent --environment production --kv | sed -n 's/^AGENT_API_KEY=//p')"

curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/health"     # 200
curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/ready"      # 200
curl -sS -o /dev/null -w '%{http_code}\n' -X POST "$BASE/ask" \
  -H 'Content-Type: application/json' -d '{"question":"Hello"}'  # 401
curl -sS -o /dev/null -w '%{http_code}\n' -X POST "$BASE/ask" \
  -H 'Content-Type: application/json' -H "X-API-Key: $AGENT_API_KEY" \
  -d '{"question":"Hello"}'  # 200
```

Verified on 2026-11-25: `/health` → 200, `/ready` → 200, `/ask` without key → 401, and `/ask` with a valid key → 200.

## Environment variables set

Không ghi giá trị secret.

- `PORT`: Railway tự cấp.
- `REDIS_URL`: `${{Redis.REDIS_URL}}` (tham chiếu service Redis nội bộ).
- `AGENT_API_KEY`: tạo ngẫu nhiên trên Railway.
- `RATE_LIMIT_PER_MINUTE=10`
- `DAILY_BUDGET_USD=1.00`
- `ENVIRONMENT=production`

## Screenshots

Đã lưu ảnh thật từ Railway và terminal:

- `screenshots/dashboard.png`: Agent và Redis đều Online.
- `screenshots/running.png`: deployment cuối Active và successful.
- `screenshots/test.png`: checker báo PASS 12/12, 42/42 checks passed.
