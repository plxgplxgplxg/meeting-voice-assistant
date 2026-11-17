# Documentation Map

## Authoritative — đồng bộ với code 16/11/2026

- `01-requirements/prd.md`
- `01-requirements/srs.md`
- `01-requirements/use-cases.md`
- `01-requirements/traceability-matrix.md`
- `03-architecture/system-architecture.md`
- `03-architecture/api-first-architecture.md`
- `03-architecture/sequence-diagrams.md`
- `04-design/api-communication-guide.md`
- `04-design/database-erd.md`
- `04-design/ui-ux-design-system.md`
- `05-testing/test-plan.md`
- `05-testing/evaluation-metrics.md`
- `05-testing/dataset-specification.md`
- `deployment/huong-dan-trien-khai-ec2-va-chay-end-to-end.md`

OpenAPI runtime `/openapi.json` và SQLAlchemy models vẫn là nguồn kỹ thuật cuối cùng nếu có sai khác.

## Improvement plan

- `07-improvement-plan/refactor-and-agent-roadmap.md` — audit findings, refactor phases, and Meeting Assistant agent design (target state).
- `07-improvement-plan/implementation-status.md` — what has been implemented from the roadmap, deviations, and what remains.

## Research/historical

Các file trong `00-administrative`, `02-research-tech`, tài liệu migration, báo cáo tiến độ và slide phản ánh quyết định/nghiên cứu ở thời điểm trước. Chúng có thể nhắc PhoWhisper, Pyannote, GPU hoặc live two-pass pipeline nhưng không phải kiến trúc runtime hiện tại.

Khi viết báo cáo/slide mới, dùng tài liệu authoritative phía trên và ghi rõ phần nghiên cứu lịch sử nếu so sánh phương án cũ.

## Thesis report

Các chương trong `06-thesis-report` cần được rà lại trước khi nộp bản cuối để thay mô tả pipeline GPU cũ bằng kiến trúc API-first hiện hành và trích kết quả đo thật thay vì số mục tiêu.
