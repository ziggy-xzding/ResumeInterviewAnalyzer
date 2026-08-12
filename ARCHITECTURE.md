# 架构设计文档

> 本文档深入讲解项目的分层架构、核心设计模式与关键机制，帮助你（和面试官）理解代码的设计思路。
> [English](ARCHITECTURE_EN.md)

## 目录

1. [总体分层架构](#1-总体分层架构)
2. [各层职责详解](#2-各层职责详解)
3. [核心设计模式](#3-核心设计模式)
4. [一次请求的完整生命周期](#4-一次请求的完整生命周期)
5. [面试分析工作流引擎](#5-面试分析工作流引擎)
6. [关键机制](#6-关键机制)
7. [目录导览](#7-目录导览)

---

## 1. 总体分层架构

项目采用**分层架构**，自上而下五层，每层只依赖下一层，职责单一：

```
┌────────────────────────────────────────────────────────────┐
│  ① API 层      Wolin/api · Wolin/router · Wolin/main       │
│     接口定义、参数校验、异常兜底、前端挂载                   │
├────────────────────────────────────────────────────────────┤
│  ② 业务层      Wolin/core · Wolin/ai · WorkFlow            │
│     分析核心逻辑、工作流编排（节点 + 状态机）                │
├────────────────────────────────────────────────────────────┤
│  ③ 服务层      Wolin/service · Base/Service                │
│     邮件 / ASR / MinIO 等业务服务（组合多个 Client）         │
├────────────────────────────────────────────────────────────┤
│  ④ Client 层   Base/Client                                 │
│     外部资源统一封装：LLM / Redis / MinIO / 邮件 / ASR       │
├────────────────────────────────────────────────────────────┤
│  ⑤ 基础设施    DashScope · Redis · MinIO · MySQL · ffmpeg   │
└────────────────────────────────────────────────────────────┘
```

**关键原则**：业务层**只与 Client 层对话**，不直接触碰第三方 SDK。
→ 好处：换存储、换模型、换配置，改动都被隔离在某一层内，业务代码零侵入。

---

## 2. 各层职责详解

### ① API 层
| 文件 | 职责 |
|------|------|
| `Wolin/main.py` | 创建 FastAPI 应用、注册路由、挂载前端、统一 422 参数校验中文提示 |
| `Wolin/api/coreApi.py` | 接口定义：`interview_analysis` / `audio_2_text`，文件上传处理与清理 |
| `Wolin/router/router.py` | 路由注册（前缀 `/interview`）|

### ② 业务层
| 文件 | 职责 |
|------|------|
| `Wolin/core/interviewAnalysis.py` | 核心分析流程：ASR → 缓存 → 报告 → 邮件 |
| `Wolin/ai/interview/iaState.py` | 工作流状态（报告 / ASR / 简历 / 请求参数），Pydantic 模型 |
| `Wolin/ai/interview/nodes/iaNodes.py` | 11 个工作流节点函数 |
| `WorkFlow/` | LangGraph 二次封装的工作流引擎 |

### ③ 服务层
| 文件 | 职责 |
|------|------|
| `Wolin/service/emailService.py` | 面试报告邮件（HTML 正文 + 附件 + 内联图）|
| `Wolin/service/asrService.py` | ASR 服务（带 Redis 缓存）|
| `Wolin/service/minioService.py` | 转写文本归档 MinIO |
| `Base/Service/asrService.py` | 通用 ASR 处理：切片 → 并发转写 → 清理 |

### ④ Client 层
| 文件 | 封装对象 | 特点 |
|------|---------|------|
| `Base/Ai/llms/qwenLlm.py` | DashScope Qwen | 统一 chat / embedding 接口 |
| `Base/Client/qwen.py` | LangChain ChatTongyi | 备选接入方式 |
| `Base/Client/asrClient.py` | DashScope 多模态 ASR | 音频转 data-URI 再请求 |
| `Base/Client/redisClient.py` | redis-py | 单例 + 连接池 + 锁 |
| `Base/Client/minioClient.py` | minio SDK | 元类单例 + 自动建桶 |
| `Base/Client/emailClient.py` | smtplib | SSL/TLS + 超时重试 |

### ⑤ 基础设施
DashScope（LLM + ASR）、Redis（缓存）、MinIO（对象存储）、MySQL（可选持久化）、ffmpeg（音频切片）。

---

## 3. 核心设计模式

### 3.1 单例模式（三种实现）
| 实现 | 文件 | 特点 |
|------|------|------|
| **元类单例** | `Base/Meta/singletonMeta.py` | `__call__` 拦截 + 类级锁 + 双重检查；类声明 `metaclass=SingletonMeta` 即生效，可复用 |
| **`__new__` + 锁** | `Base/Client/redisClient.py` | 手写双重检查锁 + `_initialized` 防重复初始化 |
| **`__new__` 简化版** | `Base/Client/milvusClient.py` | 无锁，单线程初始化 |
| **模块级单例** | `Base/Config/setting.py` | Python 模块天然单例，`settings` 全局唯一 |

**为什么需要**：数据库 / 缓存连接创建代价高，全项目只建一份连接，处处复用。

### 3.2 工厂模式 + 服务定位器
```python
# Base/Client/__init__.py
def get_redis_client():
    return redis_client
def get_minio_client(is_async=False):
    return async_minio_client if is_async else default_minio_client
```
调用方通过工厂获取单例，不关心具体实现，**换实现零改动**。

### 3.3 配置中心（pydantic-settings）
- 每个模块一个 Settings 子类，用 `env_prefix` 声明前缀：`MySQLSettings(env_prefix="DB_")` ↔ `.env` 的 `DB_HOST` 等
- 字段名与变量名不一致时用 `alias` 显式映射（如 `DASHSCOPE_API_KEY`）
- 顶层 `Settings` 聚合所有子配置，`settings.mysql.host` 点号访问
- 类型安全 + 默认值兜底 + 敏感信息不入库

### 3.4 装饰器（graph_node）
```python
@graph_node
def extract_resume(state): ...
```
- 自动捕获节点异常并包装为 `节点函数执行失败:func_name`
- 节点返回 `None` 合法（不更新状态），返回 dict 则合并进状态

---

## 4. 一次请求的完整生命周期

以 `POST /interview/interview_analysis` 为例：

```
1. 客户端上传 简历(PDF) + 录音(可选) + 表单
   ──► coreApi.py 保存临时文件（处理完自动删除）
2. 构建 IAState（报告/ASR/简历/参数 四个子状态）
   ──► workflow.invoke(state)
3. 阶段1: extract_resume + audio_handle   （并行）
   │   resume: pdfplumber抽文本 → LLM提炼字段
   │   audio:  ffmpeg切片 → dashscope ASR → LLM合并成转录文本
   │           (结果 Redis 缓存 1 小时)
4. 阶段2/3: 报告段落 / 问答对 / 简历点评 / 多维评价（并行 LLM）
   ──► 状态合并：report.xxx 各字段逐步填充
5. 阶段4: generate_report
   │   context_params 渲染 template.docx（docxtpl + Jinja2）
   │   ├── 报告上传 MinIO interview-report 桶
   │   └── 邮件发送报告（HTML + 内联图 + docx 附件）
6. 返回"分析完成，报告已发送至您的邮箱"
```

**错误兜底**：任何节点失败 → `graph_node` 包装 → coreApi 捕获 → 返回 500 + 中文错误信息（不再吞错返回假成功）。

---

## 5. 面试分析工作流引擎

`WorkFlow/` 在 LangGraph 之上做了二次封装，让业务以**声明式**方式描述流程：

```python
# Wolin/ai/interview/nodes/iaNodes.py
def get_ia_node_list():
    return [
        ['extract_resume', 'audio_handle'],                    # 并行组
        ['get_report_paragraph1', 'get_qa_pair', 'resume_analysis'],  # 并行组
        ['analysis_end', 'self_evaluation', 'ai_evaluation',
         'qa_pairs_analysis', 'get_report_table_data_json'],   # 并行组
        'generate_report'                                       # 普通节点
    ]
```

节点类型映射（`WorkFlow/models/nodes/nodeFactory.py`）：

| 描述 | 映射 |
|------|------|
| `list[str]` | MultiNode —— 并行执行组 |
| `str` | NormalNode —— 普通节点 |
| `tuple` | ConditionalNode —— 条件分支节点 |

**设计价值**：
- 节点之间通过**状态对象**（IAState）解耦，而非直接调用
- 无依赖的节点自动并行，减少整链路等待时间
- 新业务只需写节点函数 + 声明节点列表，复用同一套引擎

---

## 6. 关键机制

### 6.1 LLM 请求（OpenAI 兼容）
- `Base/Ai/base/baseLlm.py` 初始化 OpenAI 客户端，统一 `chat()` / `embedding()` 接口
- **绕过系统代理**：`httpx.Client(trust_env=False)` 直连 DashScope，规避系统代理（如 Clash）导致的 SSL 断连

### 6.2 中文 PDF 解析
- pdfplumber 优先（中文编码友好），PyPDF2 兜底 —— 解决中文简历乱码

### 6.3 音频切片与并发转写
- `split_audio_with_overlap_ffmpeg`：长音频切成 ≤100s 小段，带重叠避免断词
- `audio_2_text(file_path, max_workers=50)`：线程池并发转写 + 保持原始顺序

### 6.4 缓存
- `cache_with_params` 装饰器：按参数哈希做函数级缓存
- ASR 转写结果 `ex=3600` 缓存，重复音频秒回

### 6.5 邮件发送
- smtplib SSL/TLS，超时 + 重试（最多 2 次）
- HTML 正文 + 内联图片（Content-ID）+ docx 附件
- 发件人 / 收件人可通过配置自定义

---

## 7. 目录导览

```
ResumeInterviewAnalyzer/
├── main.py / requirements.txt / .env.example / README.md / ARCHITECTURE.md
├── Wolin/                  # 业务包
│   ├── main.py             #   FastAPI 应用
│   ├── router/             #   路由注册
│   ├── api/coreApi.py      #   接口层
│   ├── ai/interview/       #   工作流（状态 + 节点）
│   ├── core/               #   分析核心
│   ├── service/            #   业务服务
│   ├── prompt/             #   LLM 提示词
│   ├── frontend/           #   前端页面
│   └── static/             #   报告模板 / 邮件图片
├── Base/                   # 基础框架
│   ├── Ai/                 #   LLM 抽象与实现
│   ├── Client/             #   外部资源 Client 层
│   ├── Config/             #   配置中心
│   ├── Service/            #   通用服务
│   ├── Repository/         #   数据访问层
│   └── RicUtils/           #   通用工具
└── WorkFlow/               # 工作流引擎
    ├── base/               #   BaseWorkFlow / decorators / baseState
    └── models/nodes/       #   NormalNode / MultiNode / ConditionalNode
```

---

*文档持续更新中，建议先读 [README.md](README.md) 了解项目全貌，再读本文档深入实现。*
