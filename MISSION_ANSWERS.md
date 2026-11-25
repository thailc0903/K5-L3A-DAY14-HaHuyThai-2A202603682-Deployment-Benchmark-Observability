# Day 14 Lab — Mission Answers

**Họ tên:** [Điền họ tên]  
**MSSV:** [Điền MSSV]  
**Ngày thực hiện:** 25/11/2026

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found

1. API key có thể bị hard-code trong source code, dễ lộ khi chia sẻ hoặc commit repository.
2. Port cố định khiến ứng dụng không linh hoạt khi cloud platform cấp port qua biến môi trường `PORT`.
3. Không có endpoint health check nên platform không thể kiểm tra và tự khởi động lại service khi cần.
4. Dùng `print()` thay vì structured JSON logging khiến log khó tìm kiếm, lọc và phân tích.
5. Log có thể in thông tin nhạy cảm như API key, gây rủi ro bảo mật.
6. Không xử lý graceful shutdown có thể làm gián đoạn request đang chạy khi service bị dừng hoặc deploy lại.

### Exercise 1.2: Run basic version

Đã chạy `01-localhost-vs-production/develop/app.py` thành công trên localhost:8000.

Lệnh kiểm tra:

```bash
curl -X POST "http://localhost:8000/ask?question=Hello"
```

Kết quả: API trả response từ mock AI agent. Bản basic nhận `question` qua query parameter.

### Exercise 1.3: Comparison table

| Feature | Basic | Production | Tại sao quan trọng? |
|---|---|---|---|
| Configuration | Hard-code hoặc gắn chặt trong code | Đọc từ `.env` và environment variables | Không lộ secret, dễ thay đổi giữa local, staging và production mà không sửa source code. |
| Input API `/ask` | `question` nằm trong query string | Nhận JSON body `{"question":"Hello"}` | API contract rõ ràng hơn, phù hợp dữ liệu phức tạp và dễ mở rộng. |
| Health check | Không có endpoint kiểm tra | `GET /health` trả HTTP 200 | Docker/cloud platform dùng endpoint này để giám sát và quyết định restart service. |
| Logging | `print()`; có nguy cơ in API key | Structured JSON log, không log secret | Log an toàn, có cấu trúc và dễ truy vấn trong hệ thống observability. |
| Shutdown | Có thể dừng đột ngột | Có lifecycle và graceful shutdown | Giúp request đang xử lý có cơ hội hoàn tất trước khi service tắt. |

### Verification evidence

Production endpoint `GET /health` đã trả HTTP 200 với trạng thái `ok`, thông tin uptime, version, environment và timestamp.

Production endpoint `POST /ask` đã nhận JSON body và trả câu trả lời từ mock agent.

## Part 2: Docker

### Exercise 2.1: Dockerfile questions

1. **Base image:** Dockerfile basic dùng `python:3.11`; Dockerfile production dùng `python:3.11-slim` để giảm dung lượng runtime image.
2. **Working directory:** `/app`, là thư mục chứa source code và là nơi lệnh chạy app được thực thi trong container.
3. **Lý do copy `requirements.txt` trước source:** Docker cache theo từng layer. Khi chỉ thay đổi source code, layer cài dependencies được tái sử dụng nên build nhanh hơn.
4. **`CMD` và `ENTRYPOINT`:** `CMD` là lệnh mặc định, có thể bị ghi đè khi chạy container; `ENTRYPOINT` thường là lệnh cố định của container và chỉ nhận thêm đối số.

### Exercise 2.2: Build and run basic container

Đã build image:

```bash
docker build -f 02-docker/develop/Dockerfile -t my-agent:develop .
```

Đã chạy và kiểm tra container:

```bash
docker run --rm --name my-agent-develop -p 8000:8000 my-agent:develop
curl http://localhost:8000/health
curl -X POST "http://localhost:8000/ask?question=What%20is%20Docker%3F"
```

Kết quả: `/health` trả `status: ok` và `/ask` trả câu trả lời mock. Port mapping `8000:8000` hoạt động.

### Exercise 2.3: Multi-stage build and image-size comparison

Đã build image production:

```bash
docker build -f 02-docker/production/Dockerfile -t my-agent:advanced .
```

| Image | Disk usage | Content size |
|---|---:|---:|
| `my-agent:develop` | 1.67 GB | 426 MB |
| `my-agent:advanced` | 240 MB | 57.4 MB |
| Mức giảm | 85.6% | 86.5% |

Multi-stage build chỉ copy dependencies đã cài sang runtime stage, không giữ compiler (`gcc`), development packages và các layer build. Image production cũng dùng `python:3.11-slim` và non-root user `appuser`.

Đã chạy và kiểm tra image production:

```bash
docker run --rm --name my-agent-advanced -p 8000:8000 -e ENVIRONMENT=production my-agent:advanced
curl http://localhost:8000/health
curl -X POST http://localhost:8000/ask -H "Content-Type: application/json" -d '{"question":"What is Docker?"}'
```

Kết quả: `/health` trả `status: ok`, version `2.0.0`; `/ask` nhận JSON body và trả câu trả lời mock.

### Exercise 2.4: Docker Compose stack

Đã chạy Docker Compose bằng project name riêng để tránh trùng container với các bài sau:

```bash
docker compose -p k5-day14-docker up -d --build
docker compose -p k5-day14-docker ps
```

Các service đều chạy: `agent` (healthy), `redis` (healthy), `qdrant` (healthy) và `nginx`.

Do cổng host `80` và `443` không khả dụng trên Docker Desktop/Windows, Nginx được map qua `localhost:8080`; cổng nội bộ của Nginx vẫn là `80`.

```text
Client → Nginx (host :8080 → container :80) → Agent (:8000)
                                                  ├→ Redis (:6379)
                                                  └→ Qdrant (:6333)
```

Kết quả test qua Nginx:

```bash
curl http://localhost:8080/health
curl -X POST http://localhost:8080/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"Explain microservices"}'
```

`/health` trả `status: ok`, version `2.0.0`; `/ask` trả câu trả lời mock. Điều này xác nhận Nginx reverse proxy route request đến Agent thành công.

## Part 3: Cloud Deployment

Đã deploy trực tiếp working tree của `06-lab-complete/` lên Railway, không dùng GitHub commit/push.

- Platform: Railway, project `day14-ha-huy-thai-agent`, environment `production`.
- Services: `agent` và Redis managed service.
- Public URL: `https://agent-production-2b644bfe.up.railway.app`.
- Redis được nối nội bộ bằng `REDIS_URL=${{Redis.REDIS_URL}}`; API key được tạo trên Railway và không ghi giá trị vào tài liệu/repository.

Kết quả kiểm tra public ngày 2026-11-25:

```text
GET  /health                         → HTTP 200
GET  /ready                          → HTTP 200
POST /ask (không X-API-Key)          → HTTP 401
POST /ask (X-API-Key hợp lệ)         → HTTP 200
```

App khởi động trên `PORT` do Railway cấp (log xác nhận Uvicorn lắng nghe `0.0.0.0:8080`).

## Part 4: API Security

### Exercise 4.1: API key authentication

Đã chạy bản develop với `AGENT_API_KEY` đặt bằng environment variable cục bộ. Endpoint `/ask` dùng dependency `verify_api_key` để kiểm tra header `X-API-Key`.

| Trường hợp | Kết quả thực tế |
|---|---|
| Không gửi `X-API-Key` | `HTTP/1.1 401 Unauthorized`; response báo thiếu API key. |
| Gửi `X-API-Key` hợp lệ | `HTTP/1.1 200 OK`; agent trả câu trả lời mock. |

Key được đọc từ environment variable thay vì hard-code. Khi cần rotate key, tạo key mới trong secret manager/environment của nền tảng, triển khai cấu hình mới, rồi thu hồi key cũ sau khi client đã chuyển sang key mới.

### Exercise 4.2: JWT authentication

Đã chạy bản production và lấy JWT token từ endpoint `POST /auth/token` bằng tài khoản demo `student / demo123`. Token chứa username, role, issued-at và expiry; server kiểm tra chữ ký token ở dependency `verify_token` trước khi xử lý `/ask`.

Đã gọi `/ask` với header `Authorization: Bearer <redacted>` và nhận `HTTP/1.1 200 OK`. Response trả answer, thông tin usage và các security headers gồm `X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`, `Referrer-Policy`.

### Exercise 4.3: Rate limiting

Rate limiter dùng **Sliding Window Counter** trong `rate_limiter.py`. User role có limit 10 request/60 giây; admin có limit 100 request/60 giây. Timestamp các request được lưu trong `deque`; timestamp ngoài cửa sổ 60 giây bị loại bỏ trước mỗi lần kiểm tra.

Đã gửi 12 request liên tiếp với JWT của user `student`. Kết quả: request 1–9 trả `200` (một request JWT đã dùng trước đó), request 10–12 trả `429`.

Response 429 thực tế:

```text
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 0
Retry-After: 14

{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,
"retry_after_seconds":14}}
```

### Exercise 4.4: Cost guard

Cost guard kiểm tra ngân sách trước khi gọi LLM và ghi usage sau khi có response:

- Mỗi user có budget demo `$1/ngày`; budget toàn service là `$10/ngày`.
- `check_budget()` trả `402 Payment Required` khi user đã vượt budget; nếu global budget vượt ngưỡng, service trả `503`.
- `record_usage()` cộng input/output token và tính giá theo token để lưu tổng cost.
- Bản demo dùng in-memory state. Production thực tế và Part 6 phải dùng Redis/DB để budget không mất khi restart hoặc scale nhiều instance.

Không tạo kết quả 402 giả: với mock LLM, chi phí mỗi request rất nhỏ và rate limit sẽ chặn request trước khi tổng cost đạt `$1`.

## Part 5: Scaling & Reliability

### Exercise 5.1: Health and readiness checks

Đã chạy agent develop và kiểm tra:

```text
GET /health → status: ok, version: 1.0.0, environment: development
GET /ready  → ready: true
```

`/health` là liveness probe: xác nhận process còn sống. `/ready` là readiness probe: xác nhận app đã khởi tạo xong và được phép nhận traffic từ load balancer.

### Exercise 5.2: Graceful shutdown

Đã gửi `SIGTERM` tới process agent. Uvicorn thực hiện lifecycle shutdown và log xác nhận:

```text
Graceful shutdown initiated...
Shutdown complete
Application shutdown complete.
Finished server process
```

Khi shutdown bắt đầu, readiness được tắt và app chờ request đang xử lý hoàn tất, tối đa 30 giây.

### Exercise 5.3: Stateless design

Conversation history không được giữ trong RAM của từng agent instance. Mỗi request dùng `session_id`; messages được lưu trong Redis, nên instance bất kỳ đều có thể tiếp tục cùng session sau khi load balancer chuyển request sang instance khác.

### Exercise 5.4: Load balancing

Đã chạy stack với ba agent instances:

```bash
docker compose -p k5-day14-scaling up -d --build --scale agent=3
```

Stack gồm Nginx (`localhost:8080`) làm reverse proxy/load balancer, ba Agent và Redis. Ba instance agent đều khởi động; Redis healthy.

### Exercise 5.5: Stateless test

Đã chạy `python test_stateless.py`:

- 5 request được phân phối qua 3 instance: `instance-73080c`, `instance-99b81c`, `instance-9b2678`.
- Cùng một session ID được dùng xuyên suốt.
- Conversation history trả về 10 messages (5 user messages + 5 assistant messages).

Kết luận: request được load-balanced qua nhiều instance nhưng state vẫn được giữ trong Redis, do đó session không mất khi instance xử lý thay đổi.

## Part 6: Final Project — Production-ready AI Agent

Đã hoàn thiện code trong `06-lab-complete/` và chạy đầy đủ:

```bash
python check_production_ready.py
```

Kết quả local thực tế: **`PASS 12/12` — 41/41 checks passed**.

Sau khi deploy Railway, đã chạy lại với `--public-url` và nhận **`PASS 12/12` — 42/42 checks passed**, trong đó `GET https://agent-production-2b644bfe.up.railway.app/health` trả HTTP 200.

### Checklist Deliverable output

```text
✅ Dockerfile (multi-stage, < 500 MB) — image 238 MB
✅ docker-compose.yml (agent + redis)
✅ .dockerignore
✅ Health check endpoint (GET /health)
✅ Readiness endpoint (GET /ready)
✅ API Key authentication
✅ Rate limiting
✅ Cost guard
✅ Config từ environment variables
✅ Structured logging
✅ Graceful shutdown — Docker exit code 0, 0.8s
✅ Public URL ready (Railway / Render config)

Result local: 12/12 tiêu chí đạt · 41/41 checks passed
Result có public URL: 12/12 tiêu chí đạt · 42/42 checks passed
PASS 12/12 — PRODUCTION READY
```

Các điểm đã kiểm chứng gồm: `/health` vẫn 200 khi Redis down, `/ready` trả 503 khi Redis down, API key sai/thiếu trả 401, rate limit dùng Redis và còn hiệu lực sau restart, budget cạn trả 402, Docker image 238 MB, và `docker stop` hoàn thành an toàn.

## AI log

| Nội dung hỏi AI | Kết quả nhận được | Tự kiểm tra |
|---|---|---|
| Cách chạy và kiểm tra hai phiên bản localhost/production | Hướng dẫn lệnh Bash/PowerShell, cách gọi endpoint và giải thích API contract | Đã chạy basic, `/health` và `POST /ask` production; xác nhận response thực tế. |
| Dockerfile và Docker build | Giải thích layer cache, multi-stage build, non-root user và lệnh build/test | Đã build, chạy và đo cả image basic lẫn production bằng Docker. |
| Docker Compose và Nginx | Chẩn đoán cổng host 80/443 không khả dụng; remap Nginx qua cổng 8080 | Đã khởi động stack, xác nhận Redis/Qdrant/Agent healthy và gọi API qua Nginx. |
| API key authentication | Giải thích header `X-API-Key`, HTTP 401/403 và cách rotate key | Đã gọi `/ask` không key (401) và với key hợp lệ (200). |
| JWT, rate limit và cost guard | Giải thích JWT bearer token, sliding window và budget guard | Đã lấy token, gọi `/ask` thành công và quan sát 429 cùng các rate-limit headers. |
| Health checks, shutdown và stateless scale | Giải thích liveness/readiness, SIGTERM graceful shutdown, Redis state và load balancing | Đã kiểm tra `/health`, `/ready`, quan sát shutdown log, chạy 3 instances và `test_stateless.py`. |
| Final Project — config, Redis health và JSON logging | Hoàn thiện các TODO cấu hình môi trường, Redis client, `/health`, `/ready`, FastAPI lifespan và JSON formatter | Đã chạy checker đầy đủ; health/readiness, JSON logs và SIGTERM đều pass. |
| Final Project — bảo mật và Docker | Hoàn thiện API key, Redis rate limit/cost guard, Dockerfile multi-stage, Compose và Railway config | Đã chạy checker đầy đủ, nhận `PASS 12/12` và 41/41 checks passed. |
| Railway deployment | Hướng dẫn deploy local working tree, tạo Redis service, environment variables, public domain và kiểm tra endpoint | Đã kiểm tra public URL: health/ready 200, thiếu API key 401, API key hợp lệ 200. |
