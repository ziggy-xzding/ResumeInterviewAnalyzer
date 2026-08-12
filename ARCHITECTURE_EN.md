# Architecture Design

> An in-depth walkthrough of the layered architecture, core design patterns, and key mechanisms — useful for understanding the codebase (and for interviews).
> [中文](ARCHITECTURE.md)

## Contents

1. [Layered Architecture](#1-layered-architecture)
2. [Layer Responsibilities](#2-layer-responsibilities)
3. [Core Design Patterns](#3-core-design-patterns)
4. [Request Lifecycle](#4-request-lifecycle)
5. [Workflow Engine](#5-workflow-engine)
6. [Key Mechanisms](#6-key-mechanisms)
7. [Directory Guide](#7-directory-guide)

---

## 1. Layered Architecture

Five layers, top-down. Each layer only depends on the one below it:

```
┌────────────────────────────────────────────────────────────┐
│  ① API Layer    Analyzer/api · Analyzer/router · Analyzer/main     │
│     endpoints, validation, error handling, frontend mount  │
├────────────────────────────────────────────────────────────┤
│  ② Business Layer  Analyzer/core · Analyzer/ai · WorkFlow       │
│     core analysis logic, workflow orchestration (nodes+state)│
├────────────────────────────────────────────────────────────┤
│  ③ Service Layer  Analyzer/service · Base/Service            │
│     email / ASR / MinIO services (compose multiple Clients)│
├────────────────────────────────────────────────────────────┤
│  ④ Client Layer  Base/Client                              │
│     unified wrappers: LLM / Redis / MinIO / Email / ASR    │
├────────────────────────────────────────────────────────────┤
│  ⑤ Infrastructure  DashScope · Redis · MinIO · MySQL · ffmpeg│
└────────────────────────────────────────────────────────────┘
```

**Key principle**: the business layer only talks to the Client layer — it never touches third-party SDKs directly.
→ Swapping storage, models, or config is isolated to one layer; business code stays untouched.

---

## 2. Layer Responsibilities

### ① API Layer
| File | Responsibility |
|------|----------------|
| `Analyzer/main.py` | FastAPI app, route registration, frontend mount, friendly 422 validation messages |
| `Analyzer/api/coreApi.py` | Endpoints: `interview_analysis` / `audio_2_text`, file upload handling & cleanup |
| `Analyzer/router/router.py` | Route registration (prefix `/interview`) |

### ② Business Layer
| File | Responsibility |
|------|----------------|
| `Analyzer/core/interviewAnalysis.py` | Core flow: ASR → cache → report → email |
| `Analyzer/ai/interview/iaState.py` | Workflow state (report / ASR / resume / params), Pydantic models |
| `Analyzer/ai/interview/nodes/iaNodes.py` | 11 workflow node functions |
| `WorkFlow/` | LangGraph-based workflow engine |

### ③ Service Layer
| File | Responsibility |
|------|----------------|
| `Analyzer/service/emailService.py` | Interview report email (HTML + attachment + inline image) |
| `Analyzer/service/asrService.py` | ASR service with Redis cache |
| `Analyzer/service/minioService.py` | Archive transcripts to MinIO |
| `Base/Service/asrService.py` | Generic ASR: slicing → concurrent transcription → cleanup |

### ④ Client Layer
| File | Wraps | Notes |
|------|-------|-------|
| `Base/Ai/llms/qwenLlm.py` | DashScope Qwen | unified chat / embedding interface |
| `Base/Client/qwen.py` | LangChain ChatTongyi | alternative integration |
| `Base/Client/asrClient.py` | DashScope multimodal ASR | audio → data-URI before request |
| `Base/Client/redisClient.py` | redis-py | singleton + connection pool + lock |
| `Base/Client/minioClient.py` | minio SDK | metaclass singleton + auto bucket creation |
| `Base/Client/emailClient.py` | smtplib | SSL/TLS + timeout retry |

### ⑤ Infrastructure
DashScope (LLM + ASR), Redis (cache), MinIO (object storage), MySQL (optional persistence), ffmpeg (audio slicing).

---

## 3. Core Design Patterns

### 3.1 Singleton (three implementations)
| Implementation | File | Notes |
|----------------|------|-------|
| **Metaclass** | `Base/Meta/singletonMeta.py` | intercepts `__call__` + class-level lock + double-checked locking; just declare `metaclass=SingletonMeta` |
| **`__new__` + lock** | `Base/Client/redisClient.py` | hand-written double-checked locking + `_initialized` guard |
| **`__new__` (simple)** | `Base/Client/milvusClient.py` | no lock, single-threaded init |
| **Module-level** | `Base/Config/setting.py` | Python modules are naturally singletons |

**Why**: creating database/cache connections is expensive — build once, reuse everywhere.

### 3.2 Factory + Service Locator
```python
# Base/Client/__init__.py
def get_redis_client():
    return redis_client
def get_minio_client(is_async=False):
    return async_minio_client if is_async else default_minio_client
```
Callers get singletons through factories without knowing the implementation — swapping is zero-change.

### 3.3 Config Center (pydantic-settings)
- One Settings subclass per module, with `env_prefix`: `MySQLSettings(env_prefix="DB_")` ↔ `DB_HOST` in `.env`
- `alias` maps field names to differently-named env vars (e.g. `DASHSCOPE_API_KEY`)
- Top-level `Settings` aggregates everything, accessed as `settings.mysql.host`
- Type-safe + default values + no secrets in code

### 3.4 Decorator (graph_node)
```python
@graph_node
def extract_resume(state): ...
```
- Wraps node exceptions as `节点函数执行失败:func_name`
- Returning `None` is valid (no state update); returning a dict merges into state

---

## 4. Request Lifecycle

`POST /interview/interview_analysis`:

```
1. Client uploads resume(PDF) + audio(optional) + form
   ──► coreApi.py saves temp files (auto-deleted after processing)
2. Build IAState (report / ASR / resume / params)
   ──► workflow.invoke(state)
3. Stage 1: extract_resume + audio_handle   (parallel)
   │   resume: pdfplumber text → LLM field extraction
   │   audio:  ffmpeg slice → dashscope ASR → LLM merge transcript
   │           (result cached in Redis for 1 hour)
4. Stage 2/3: report sections / Q&A / resume review / evaluations (parallel LLM)
   ──► state merge: report.* fields filled incrementally
5. Stage 4: generate_report
   │   render template.docx via context_params (docxtpl + Jinja2)
   │   ├── report uploaded to MinIO `interview-report` bucket
   │   └── email sent (HTML + inline image + docx attachment)
6. Return "分析完成，报告已发送至您的邮箱"
```

**Error handling**: any node failure → wrapped by `graph_node` → caught by coreApi → 500 + friendly message (no silent "fake success").

---

## 5. Workflow Engine

`WorkFlow/` wraps LangGraph so business describes flows declaratively:

```python
# Analyzer/ai/interview/nodes/iaNodes.py
def get_ia_node_list():
    return [
        ['extract_resume', 'audio_handle'],                    # parallel group
        ['get_report_paragraph1', 'get_qa_pair', 'resume_analysis'],  # parallel
        ['analysis_end', 'self_evaluation', 'ai_evaluation',
         'qa_pairs_analysis', 'get_report_table_data_json'],   # parallel
        'generate_report'                                       # normal node
    ]
```

Node type mapping (`WorkFlow/models/nodes/nodeFactory.py`):

| Descriptor | Maps to |
|------------|---------|
| `list[str]` | MultiNode — parallel group |
| `str` | NormalNode — single node |
| `tuple` | ConditionalNode — conditional branch |

**Design value**:
- Nodes decouple through a **state object** (IAState), not direct calls
- Independent nodes run in parallel, cutting total latency
- New business = write node functions + declare the node list, reusing the same engine

---

## 6. Key Mechanisms

### 6.1 LLM Requests (OpenAI-compatible)
- `Base/Ai/base/baseLlm.py` initializes the OpenAI client with a unified `chat()` / `embedding()` interface
- **Bypasses the system proxy**: `httpx.Client(trust_env=False)` connects to DashScope directly, avoiding SSL drops caused by system proxies (e.g. Clash)

### 6.2 Chinese PDF Parsing
- pdfplumber first (Chinese-friendly), PyPDF2 fallback — fixes garbled Chinese resumes

### 6.3 Audio Slicing & Concurrent Transcription
- `split_audio_with_overlap_ffmpeg`: splits long audio into ≤100s chunks with overlap to avoid cut words
- `audio_2_text(file_path, max_workers=50)`: thread-pool concurrent transcription, order preserved

### 6.4 Caching
- `cache_with_params` decorator: function-level cache keyed by parameter hash
- ASR transcripts cached with `ex=3600` — repeated audio returns instantly

### 6.5 Email Sending
- smtplib SSL/TLS with timeout + retry (up to 2)
- HTML body + inline image (Content-ID) + docx attachment
- Sender name & recipient email configurable

---

## 7. Directory Guide

```
ResumeInterviewAnalyzer/
├── main.py / requirements.txt / .env.example / README.md / README_EN.md / ARCHITECTURE.md
├── Analyzer/                  # Business package
│   ├── main.py             #   FastAPI app
│   ├── router/             #   Route registration
│   ├── api/coreApi.py      #   API layer
│   ├── ai/interview/       #   Workflow (state + nodes)
│   ├── core/               #   Analysis core
│   ├── service/            #   Business services
│   ├── prompt/             #   LLM prompts
│   ├── frontend/           #   Web frontend
│   └── static/             #   Report template / email images
├── Base/                   # Base framework
│   ├── Ai/                 #   LLM abstraction & implementation
│   ├── Client/             #   External resource Client layer
│   ├── Config/             #   Config center
│   ├── Service/            #   Common services
│   ├── Repository/         #   Data access layer
│   └── RicUtils/           #   Utilities
└── WorkFlow/               # Workflow engine
    ├── base/               #   BaseWorkFlow / decorators / baseState
    └── models/nodes/       #   NormalNode / MultiNode / ConditionalNode
```

---

*Docs evolve continuously — start with [README_EN.md](README_EN.md) for an overview, then this document for the implementation.*
