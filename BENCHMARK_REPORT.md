# Benchmark & Observability Report — Day 14

> Copy file này thành `BENCHMARK_REPORT.md` trong repo của bạn và điền đầy đủ.
> Mọi con số phải lấy từ report JSON / CSV / screenshot thật, không ước lượng.

**Họ tên:** Hà Huy Thái — 2A202603682
**Ngày chạy:** 2026-11-25
**Môi trường:** Windows 11, WSL2, Docker Desktop 4.99.0; benchmark local chạy trong Python virtual environment.

---

## 1. SLO của agent

| SLI | SLO | Lý do chọn ngưỡng này |
|---|---|---|
| p95 latency `/ask` | ≤ 500 ms | Bảo vệ phần lớn người dùng khỏi tail latency, thay vì che giấu bằng latency trung bình. |
| Error rate `/ask` | ≤ 2% | Phù hợp ngưỡng SLO mặc định của `load_test.py`. |
| Accuracy trên golden dataset | ≥ 100% | Quality gate cuối yêu cầu 23/23 câu và không regression so với baseline v2. |

---

## 2. Benchmark hiệu năng (develop, `load_test.py`)

### 2.1 Concurrency vs latency (agent v2)

| Concurrency | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Error rate | SLO |
|---|---|---|---|---|---|---|
| 1 | 4.36 | 192.1 | 221.0 | 1698.0 | 1.67% | PASS |
| 10 | 35.22 | 189.0 | 220.1 | 1700.1 | 0.67% | PASS |
| 50 | 108.63 | 196.2 | 239.9 | 1710.1 | 1.67% | PASS |
| 100 | 55.22 | 379.8 | 3361.0 | 3741.4 | 0.67% | FAIL (p95) |

**Nhận xét:** RPS tăng mạnh từ 4.36 (c=1) lên 108.63 req/s (c=50), nhưng không tuyến tính và giảm còn 55.22 req/s ở c=100. Khi concurrency quá cao, hàng đợi/event loop và cạnh tranh CPU làm latency tăng; p95 vượt SLO.

### 2.2 Tail latency

| `MOCK_SLOW_RATE` | avg (ms) | p95 (ms) | p99 (ms) |
|---|---|---|---|
| 0 | 188.2 | 217.3 | 221.5 |
| 0.03 (mặc định) | 257.1 | 234.8 | 1698.7 |
| 0.1 | 340.6 | 1691.0 | 1713.5 |

**Nhận xét:** p99 nhạy nhất ngay ở slow rate 0.03 (1698.7 ms), còn average chỉ tăng lên 257.1 ms. Ở slow rate 0.1, p95 cũng tăng vọt lên 1691.0 ms. Average che giấu nhóm người dùng chờ lâu, nên SLO phải dùng percentile như p95/p99.

---

## 3. Benchmark chất lượng (develop, `eval/run_eval.py`)

| Chỉ số | Agent v1 | Agent v2 | Agent v2 (sau khi sửa KB) |
|---|---|---|---|
| Accuracy | 4.35% (1/23) | 91.30% (21/23) | 100.00% (23/23) |
| Avg tokens / câu | 57.6 | 109.0 | 113.0 |
| Tổng cost (USD) | 0.000411 | 0.000759 | 0.000785 |
| Cost / câu đúng (USD) | 0.00041115 | 0.00003616 | 0.00003413 |
| Quality gate | FAIL | PASS | PASS |

**Những câu v2 trả lời sai ban đầu và cách bạn sửa:**

| ID | Keyword bị thiếu | Bạn đã sửa gì |
|---|---|---|
| security-02 | `token`, `hết hạn`, `chữ ký` | Thêm entry `jwt` / `api key` vào `KNOWLEDGE_BASE`, mô tả JWT có chữ ký và hết hạn. |
| scaling-03 | `cpu`, `memory`, `custom metrics` | Thêm entry `kubernetes` / `hpa` vào `KNOWLEDGE_BASE`, mô tả HPA scale theo ba loại chỉ số này. |

**Nhận xét về trade-off chất lượng / chi phí / latency giữa v1 và v2:**

v2 dùng retrieval nên tăng accuracy từ 4.35% lên 91.30%, đổi lại average tokens gần gấp đôi (57.6 → 109.0) và tổng cost tăng từ $0.000411 lên $0.000759. Tuy nhiên cost trên mỗi câu đúng giảm mạnh từ $0.00041115 xuống $0.00003616. Sau khi bổ sung knowledge base, v2 đạt 23/23 với cost/câu đúng $0.00003413; p95 của lần eval cuối tăng do có request chậm ngẫu nhiên, nên latency được đánh giá tin cậy hơn bằng load test 300 request.

---

## 4. Observability stack (production)

### 4.1 Screenshot

- [ ] Dashboard Grafana khi đang có tải (thấy rõ Golden Signals)
- [ ] Một trace chậm trong Jaeger (thấy span nào chiếm thời gian)
- [ ] Một trace lỗi trong Jaeger (có event `exception`)
- [ ] Trang Alerts của Prometheus với ít nhất 1 alert đang **firing**

### 4.2 Thí nghiệm "phá hệ thống"

| # | Thay đổi | Alert nào firing | Thời gian từ lúc đổi → firing | Panel nào phản ánh rõ nhất |
|---|---|---|---|---|
| A | `MOCK_ERROR_RATE=0.2` | | | |
| B | `MOCK_SLOW_RATE=0.3` | | | |
| C | `LLM_MODEL=mock-llm-large` | | | |
| D | `docker pause` 1 instance | | | |
| E | `AGENT_VERSION=v1` | | | |

**Thí nghiệm E không làm alert nào firing. Bạn sẽ phát hiện loại sự cố này trong production bằng cách nào?**

...

### 4.3 Debug bằng trace

Chọn 1 trace chậm nhất bạn tìm được:

- `trace_id`: ...
- Tổng thời gian: ... ms
- Span chiếm nhiều thời gian nhất: ... (... ms, ...%)
- Dòng log tương ứng (grep theo `trace_id`):

```json

```

---

## 5. Benchmark scaling (production, Locust headless, 100 users, 2 phút)

| Số instance | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Failures |
|---|---|---|---|---|---|
| 1 | 61.32 | 190 | 290 | 1700 | 67 / 7158 (0.94%) |
| 3 | 64.11 | 190 | 220 | 1700 | 87 / 7211 (1.21%) |

**Giải thích kết quả:** Scale từ 1 lên 3 instance làm p95 giảm từ 290 ms xuống 220 ms và RPS tăng nhẹ từ 61.32 lên 64.11. Tuy nhiên p99 vẫn 1700 ms vì request chậm được fault injection ở mock LLM; đây là nút thắt upstream nên thêm instance không loại bỏ tail latency đó.

---

## 6. Kết luận

- 3 điều bạn học được về benchmark & observability:
  1. ...
  2. ...
  3. ...
- Nếu đưa agent này lên production thật, bạn sẽ thêm metric / alert nào nữa?

...
