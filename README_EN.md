<div align="center">

# Resume & Interview Analysis App

**AI Resume & Interview Analysis** — Upload your resume & interview recording, get a professional AI-generated interview analysis report

[中文](README.md) | **English**

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688)
![LangGraph](https://img.shields.io/badge/LangGraph-1.0-green)
![DashScope](https://img.shields.io/badge/DashScope-Qwen3-ff6a00)
![License](https://img.shields.io/badge/License-MIT-yellow)

</div>

<p align="center">
  <img src="assets/banner.png" width="100%" alt="Resume & Interview Analysis App">
</p>

---

## 📖 Overview

A job-hunting assistant built with **FastAPI + LangGraph + Alibaba Cloud DashScope**:

- Upload a **PDF resume** → automatically extract structured info → get a resume review
- Upload an **interview recording** → ASR speech-to-text → generate a **complete interview analysis report** based on the transcript + resume
- The report is rendered as a **Word document** and **emailed** to your inbox

**Audio is optional** — resume-only analysis is supported.

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📄 Resume parsing | pdfplumber extracts PDF text, LLM structures education/experience/skills |
| 🎙 Speech-to-text (ASR) | ffmpeg slicing + DashScope qwen3-asr-flash concurrent transcription |
| 🧠 Interview workflow | 11 nodes orchestrated by LangGraph, parallel report generation |
| 📧 Email report | Sends the docx report (with inline image) to the configured email |
| ☁️ Object storage | Reports & transcripts archived to MinIO |
| ⚡ Caching | ASR results cached in Redis — repeated audio doesn't re-call the model |
| 🖥 Out of the box | Built-in web frontend + Swagger docs |

## 📸 UI Preview

![Interview Analysis UI](assets/ui-preview.png)

## 🏗 Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                 Frontend (Web / Swagger)                     │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP
┌──────────────────────────▼──────────────────────────────────┐
│               API Layer  (Analyzer/api/coreApi.py)              │
│        /interview/interview_analysis   /interviewaudio_2_text│
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│         Business Layer — WorkFlow Engine (LangGraph)         │
│  resume extract → audio handle → report sections → evaluate  │
│  each node = one LLM call, independent nodes run in parallel │
└──────┬──────────────┬──────────────┬────────────────────────┘
       │              │              │
       ▼              ▼              ▼
┌──────────┐   ┌──────────┐   ┌──────────────┐
│EmailService│  │AsrService│   │  MinIOService │
└─────┬────┘   └────┬─────┘   └──────┬───────┘
      │             │               │
┌─────▼─────────────▼───────────────▼──────────┐
│        Client Layer (unified / singleton)      │
│   QwenLlm / AsrClient / RedisClient /          │
│   MinioClient / EmailClient                    │
└─────┬──────────────────┬──────────────────────┘
      │                  │
      ▼                  ▼
┌──────────────┐  ┌────────────────────┐
│  DashScope   │  │  Redis / MinIO /   │
│  (qwen3-max) │  │  MySQL(optional)   │
└──────────────┘  └────────────────────┘
```

**Layering principle**: business code only talks to the Client layer — swapping storage, models, or config never touches business logic.

## 🧱 Tech Stack

| Category | Tech |
|----------|------|
| Web framework | FastAPI · Uvicorn · python-multipart |
| LLM | Alibaba Cloud DashScope (qwen3-max) · OpenAI SDK |
| ASR | DashScope qwen3-asr-flash |
| Workflow | LangGraph (wrapped by a custom WorkFlow layer) |
| Docs parsing/rendering | pdfplumber · PyPDF2 · docxtpl · Jinja2 |
| Storage / cache | Redis · MinIO · MySQL (Base framework) |
| Audio processing | ffmpeg (static-ffmpeg) |

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Alibaba Cloud Bailian API Key ([get one here](https://bailian.console.aliyun.com/))
- A QQ email with SMTP auth code (for sending reports)

### 1. Install dependencies

```bash
git clone https://github.com/YOUR_USERNAME/ResumeInterviewAnalyzer.git
cd ResumeInterviewAnalyzer
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` — at minimum these three:

```ini
# LLM / ASR (required)
DASHSCOPE_API_KEY=your_bailian_api_key

# Email (required)
SENDER_EMAIL=your_email@qq.com
EMAIL_PASSWORD=your_qq_smtp_auth_code

# ffmpeg path (required, dir containing ffmpeg.exe/ffprobe.exe)
FFMPEG_PATH=/path/to/ffmpeg
```

> Redis / MinIO / MySQL are optional. Missing config degrades those features but doesn't break the main flow.

### 3. Run

```bash
python main.py
# or
uvicorn Analyzer.main:app --host 0.0.0.0 --port 8000
```

### 4. Access

| Entry | URL |
|-------|-----|
| Frontend | http://127.0.0.1:8000/ |
| Swagger docs | http://127.0.0.1:8000/docs |

> On Windows, run with `PYTHONIOENCODING=utf-8` to avoid Chinese log encoding errors.

## 📡 API

### POST `/interview/interview_analysis`
Resume / interview analysis (**audio optional**, at least one file required)

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `receive_email` | form | ✅ | Email to receive the report |
| `user_name` | form | ✅ | User name |
| `company_name` | form | ✅ | Company name |
| `resume_file` | file | ❌ | PDF resume |
| `audio_file` | file | ❌ | Interview recording |

### POST `/interviewaudio_2_text`
Audio to text

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `audio_file` | file | ✅ | Audio file (mp3/wav/m4a...) |

## 🔄 Interview Analysis Workflow

```
Stage 1  Resume extract + Audio handle (parallel)
         └─ extract_resume      LLM extracts resume fields
         └─ audio_handle        ffmpeg slice → ASR → LLM merge transcript

Stage 2  Report content (parallel LLM calls)
         └─ get_report_paragraph1   opening paragraph
         └─ get_qa_pair             Q&A pairs extraction
         └─ resume_analysis         resume review

Stage 3  Multi-dimensional evaluation (parallel)
         └─ analysis_end / self_evaluation / ai_evaluation
         └─ qa_pairs_analysis / get_report_table_data_json

Stage 4  generate_report   render docx → store to MinIO → send email
```

## 📂 Project Structure

```
ResumeInterviewAnalyzer/
├── main.py                    # Entry point
├── requirements.txt
├── .env.example               # Env config template
├── ARCHITECTURE.md            # Architecture doc (recommended reading)
├── Analyzer/                     # ★ Business package
│   ├── main.py                #   FastAPI app & middleware
│   ├── router/                #   Route registration
│   ├── api/coreApi.py         #   API definitions
│   ├── ai/interview/          #   Interview workflow (nodes + state)
│   ├── core/                  #   Core analysis logic
│   ├── service/               #   Email / ASR / MinIO services
│   ├── prompt/                #   LLM prompts
│   ├── frontend/              #   Web frontend
│   └── static/                #   Report template / email images
├── Base/                      # ★ Base framework
│   ├── Ai/                    #   LLM abstraction & implementation
│   ├── Client/                #   Unified external resource clients
│   ├── Config/                #   Config center (pydantic-settings)
│   ├── Service/               #   Common services (ASR / email)
│   ├── Repository/            #   Data access layer
│   └── RicUtils/              #   Utilities (PDF/audio/redis cache...)
└── WorkFlow/                  # ★ Workflow engine (LangGraph wrapper)
```

## 💡 Technical Highlights

- **Singleton + Factory**: Redis/MinIO/Milvus clients are singletons (metaclass / `__new__` / module-level — three implementations); `get_*_client()` factories isolate implementations.
- **Client-layer encapsulation**: business never touches third-party SDKs directly — swapping a library changes zero business code.
- **Workflow engine wrapper**: a `graph_node` decorator + parallel node groups on top of LangGraph, so business describes flows declaratively.
- **Config center**: pydantic-settings reads `.env` with per-module prefixes — type-safe, centralized, no secrets in code.
- **Chinese PDF parsing**: pdfplumber first (Chinese-friendly), PyPDF2 fallback — fixes garbled Chinese resumes.
- **Engineering details**: ASR result Redis caching (`ex=3600`), overlapping audio slicing, concurrent transcription preserving order, LLM timeout & retry, system-proxy bypass for stable connections.

## 🔒 Security

- `.env` is gitignored — secrets never enter the repo
- Uploaded audio/resume are temp files, auto-deleted after processing
- Sender display name & recipient emails are configurable

## 📄 License

[MIT](LICENSE)
