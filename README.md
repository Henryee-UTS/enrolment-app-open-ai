# Student Enrolment — Labs 1–8

## 현재 파일 구조와 역할

| 경로 | 역할 |
|---|---|
| `frontend-service/` | Nginx 화면, Normal·AI·MCP·RAG 탭 (8080) |
| `enrolment-service/` | Flask API, DB·Ollama·RAG 호출 (5001) |
| `database-service/` | 학생 데이터 API와 Docker volume DB (5002) |
| `mcp-server/` | Lab 7: stdio MCP 도구 4개 |
| `rag-server/` | Lab 8: corpus·Chroma·검색·답변·감사 로그, HTTP (5003) 및 stdio MCP |
| `agentic_loop/` | collector → prompt → Qwen 구현 검토 → Llama 재검토 |
| `prompts/` | 과제별 구현·검토 프롬프트 |
| `reports/` | 실행 증빙, 실제 응답, 모델 검토 |
| 루트 `app.py`, `templates/`, `css/`, `legacy-lab3/` | 이전 단계 파일; 현재 Docker 화면과 구별 |
| 루트 `enrolment.db` | 로컬 MCP·RAG의 기본 데이터 원본 |

Docker DB와 루트 DB는 별도 파일입니다. 현재 검증에서는 둘 다 학생 10명이지만 자동 동기화되지 않습니다. 로컬 RAG는 루트 DB를 사용하고, 해당 파일이 없을 때만 database-service HTTP를 대체 경로로 사용합니다.

## Lab 8을 이해하는 순서

1. **Refresh Corpus**: DB, 보고서, 파일 목록을 읽고 검색 단위(chunk)로 분할합니다. 각 chunk에 source ID와 authority tier를 붙입니다.
2. **Index**: 단어를 256차원 해시 벡터로 바꿔 Chroma에 저장합니다. 이 과제 구현은 오프라인 단어 기반 baseline이며 의미를 학습한 임베딩은 아닙니다.
3. **Retrieve Context**: 질문 벡터와 가까운 후보를 가져오고 단어·과목 코드로 관련성을 확인합니다. `k`는 최대 검색 개수입니다.
4. **Answer with Citations**: 집계·과목 조회는 검색 근거를 직접 사용합니다. 일반 질문은 검색 문맥을 Qwen에 전달합니다. 근거가 없으면 답을 보류합니다.
5. **Evaluate**: 정답 chunk ID와 검색 ID를 비교합니다. P@5 = 관련 검색 수 / 5, R@5 = 찾은 관련 수 / 전체 정답 수입니다.
6. **Agentic Review**: 정적 구조와 저장된 실행 증빙을 Qwen·Llama가 검토합니다. 모델의 평가는 실제 테스트를 대체하지 않습니다.

MCP는 도구를 호출하는 통신 규약이고 RAG는 답변 근거를 검색하는 방식입니다. RAG 도구를 MCP로 노출할 수도 있고, HTTP로 화면에 연결할 수도 있습니다.

## 실행

프로젝트 루트에서 실행합니다. Docker Desktop과 Ollama가 먼저 실행되어야 합니다.

```bash
# Python 3.12 환경: 현재 .venv-lab7을 Lab 8에서도 사용
.venv-lab7/bin/python -m pip install -r rag-server/requirements.txt
# 터미널 A
docker compose up -d --build
# 터미널 B — HTTP UI에 필요한 서버
.venv-lab7/bin/python -u rag-server/rag_http_server.py
```

화면: <http://localhost:8080/#rag>. 순서대로 Refresh Corpus → Retrieve Context → Answer with Citations를 실행합니다. 예제 질문은 `Which students are enrolled in ASD101?` 및 `student count`입니다. 현재 단어 기반 검색은 영어 corpus와 영어 질문을 기준으로 검증했습니다.

```bash
# 터미널 C — 평가와 자동 테스트
.venv-lab7/bin/python rag-server/rag_eval.py
.venv-lab7/bin/python -m unittest discover -s tests -v
.venv-lab7/bin/python scripts/check_lab8_http.py
# 기존 agentic 환경 (openai·python-dotenv·requests)
.venv/bin/python agentic_loop.py
# 5: MCP, 6: RAG, 0: 종료
# 실제 모델 검토를 파일로 저장하고 요청 시간 제한 설정
.venv/bin/python -u scripts/run_lab_review.py rag --timeout 90
```

`rag_server.py`는 MCP 클라이언트가 실행하는 stdio 서버입니다. 웹 화면에는 `rag_http_server.py`가 필요합니다. MCP 설정의 경로는 사용하는 클라이언트의 작업 디렉터리에 맞춰야 합니다. HTTP 서버와 stdio 서버에서 동시에 corpus refresh를 실행하지 마세요.

## 증빙과 한계

- Lab 7: `reports/integration-report.md`, `boundary-analysis.md`, `tool-review.md`, `run-report.md`.
- Lab 8: `reports/rag-report.md`, `rag-validation-report.md`, `rag-http-checks.json`, `rag-server/retrieval-metrics.md`.
- 프로토콜 호출: `reports/mcp-protocol-check.json`.
- `rag-server/corpus/`, `chroma/`, `rag-audit.jsonl`은 재생성 가능한 로컬 실행 데이터로 Git에서 제외합니다.
- 신뢰도는 단어 커버리지 기반의 보수적 범주이며 확률로 보정된 점수가 아닙니다. 출처가 있다고 일반 LLM 답변의 모든 주장이 자동 검증되지는 않습니다.
- 수업용 corpus는 최대 500개의 학생 기록을 포함하며 top-k 조회는 전체 명단을 보장하지 않습니다.
- Lab 9–11 안내는 아직 제공되지 않아 범위·완료 여부를 확정하지 않았습니다.

## 2026-10-13 진행 상태

Lab 7 도구·HTTP·MCP 통신은 검증했습니다. Lab 8 구현, 회귀 테스트 7개, HTTP 검사 11개와 Qwen 검토는 실행했습니다. Llama 8B 검토는 CPU 실행 중 시간 초과가 발생해 전체 이중 모델 검증을 완료로 표시하지 않았습니다. 상세 실패 결과는 각 검토 보고서를 확인하세요.

마지막 소스는 회귀 테스트 7개를 통과했습니다. HTTP 11개 검사는 마지막 예외 처리 수정 이전에 통과했으며, 최종 HTTP 재실행은 승인되지 않아 실행하지 않았습니다.
