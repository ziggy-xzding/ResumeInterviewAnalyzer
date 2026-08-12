# Resume & Interview Analysis App

基于 **FastAPI + LangGraph + 阿里云 DashScope（qwen3-max / qwen3-asr-flash）** 的简历与面试分析应用。

支持上传**简历**（PDF）和**面试录音**（mp3/wav/m4a 等），通过 LLM 工作流自动生成面试分析报告，并以邮件形式发送到指定邮箱。

> 由"FastAPI AI 便捷开发脚手架"抽取出的简历+录音分析子项目。

## ✨ 功能

- **简历分析**：上传 PDF 简历 → 自动抽取结构化信息（教育、工作经历、技能等）→ 生成简历点评
- **面试分析**：上传面试录音 → ffmpeg 切片 → qwen3-asr-flash 语音转文字 → LLM 生成完整面试报告（自我评价 / AI 评价 / 问答对分析 / 报告段落）
- **录音可选**：只传简历也能单独分析
- **邮件报告**：分析完成后把报告（docx 附件 + 内联图）发送到指定邮箱
- **进度缓存**：ASR 转写结果 Redis 缓存，重复音频不重复调模型

## 🧱 技术栈

| 部分 | 技术 |
|------|------|
| Web 框架 | FastAPI + Uvicorn |
| LLM | 阿里云 DashScope（qwen3-max）|
| ASR | DashScope qwen3-asr-flash |
| 工作流 | LangGraph（`WorkFlow/` 自封装）|
| PDF 解析 | pdfplumber（中文友好，PyPDF2 兜底）|
| 报告生成 | docxtpl + Jinja2 |
| 存储 | Redis（缓存）/ MinIO（文件）/ MySQL（Base 框架）|

## 🚀 快速开始

### 1. 安装依赖（Python 3.10+）

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，至少填入：

- `DASHSCOPE_API_KEY` — 面试分析 / ASR 必填（阿里云百炼控制台获取）
- `SENDER_EMAIL` + `EMAIL_PASSWORD` — QQ 邮箱及 SMTP 授权码（报告发送）
- `FFMPEG_PATH` — 指向含 `ffmpeg.exe`/`ffprobe.exe` 的目录（`pip install static-ffmpeg` 后指向其 bin 目录；Linux 填 `/usr/bin`）

Redis / MinIO / MySQL 为可选，未配置时相关功能降级但不影响主流程。

### 3. 启动

```bash
python main.py
# 或
uvicorn Wolin.main:app --host 0.0.0.0 --port 8000
```

### 4. 访问

- 前端页面：<http://127.0.0.1:8000/>
- Swagger 文档：<http://127.0.0.1:8000/docs>

> ⚠️ Windows 控制台建议加 `PYTHONIOENCODING=utf-8` 运行，避免中文日志编码报错。

## 📡 API

| 方法 | 路径 | 说明 | 参数 |
|------|------|------|------|
| POST | `/interview/interview_analysis` | 面试/简历分析 | `receive_email`、`user_name`、`company_name`、`audio_file`(可选)、`resume_file`(可选)，至少传一个文件 |
| POST | `/interviewaudio_2_text` | 音频转文字 | `audio_file` |

## 📂 项目结构

```
ResumeInterviewAnalyzer/
├── main.py                 # 入口
├── Wolin/                  # 业务包
│   ├── main.py             # FastAPI 应用
│   ├── api/coreApi.py      # 接口定义
│   ├── ai/interview/       # 面试分析 workflow 节点
│   ├── core/               # 核心分析逻辑
│   ├── service/            # 邮件 / ASR / MinIO 服务
│   ├── frontend/           # 前端页面
│   ├── prompt/             # LLM 提示词
│   └── static/             # 报告模板 / 邮件图片
├── Base/                   # 基础框架（配置、Client、工具）
├── WorkFlow/               # 工作流引擎（LangGraph 封装）
├── requirements.txt
└── .env.example
```

## 🔒 安全说明

- `.env` 已被 gitignore，密钥不会入库
- 上传的音频/简历仅在处理期间临时保存，处理完自动删除
