# Ma Trận Truy Vết Yêu Cầu (Requirements Traceability Matrix - RTM)

| Use Case ID | Functional Req | Module Phụ Trách | Test Scenario | Status |
|---|---|---|---|---|
| **UC-01** | FR-01, NFR-02 | `frontend/live`, `ai-service/pipelines/vad.py` | TC-LIVE-01, TC-LIVE-02 | Pending |
| **UC-02** | FR-02, FR-03 | `backend-api/workers`, `ai-service/pipelines/asr.py` | TC-BATCH-01, TC-BATCH-02 | Pending |
| **UC-03** | FR-04, NFR-04 | `backend-api/services/transcript_service.py` | TC-STUDIO-01 | Pending |
| **UC-04** | FR-05, NFR-01 | `ai-service/rag/generator.py` | TC-SUMM-01, TC-SUMM-02 | Pending |
| **UC-05** | FR-06, NFR-01 | `ai-service/rag/retriever.py`, `backend-api/endpoints/chat.py` | TC-RAG-01, TC-RAG-02 | Pending |
