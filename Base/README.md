# Base 包架构文档

## 概述

Base 包是一个通用的 Python 基础框架，提供了数据库操作、AI 集成、客户端封装、配置管理、工具函数等核心功能。采用模块化设计，易于扩展和维护。

## 目录结构

```
Base/
├── Ai/                    # AI/LLM 相关功能
├── Client/                 # 第三方服务客户端
├── Config/                 # 配置管理
├── DataSet/               # 数据集管理
├── Meta/                  # 元类和设计模式
├── Models/                # 数据模型
├── Repository/             # 数据库仓储层
├── RicUtils/              # 通用工具函数
└── Service/               # 业务服务层
```

## 核心模块

### 1. Repository - 数据库仓储层

提供统一的数据库操作接口，支持多种数据库和连接池管理。

#### 架构设计

```
Repository/
├── base/                   # 抽象基类
│   ├── baseConnection.py      # 数据库连接抽象基类
│   ├── baseDBModel.py         # ORM 模型基类
│   └── connectionManager.py   # 连接管理器
├── connections/             # 具体数据库实现
│   ├── mysqlConnection.py    # MySQL 连接实现
│   ├── postgresConnection.py # PostgreSQL 连接实现
│   └── sqliteConnection.py  # SQLite 连接实现
├── models/                 # 数据模型
│   └── moduleDbModel.py     # 模块数据模型基类
└── register.py            # 连接注册
```

#### 核心组件

**baseConnection.py**
- 抽象基类，定义数据库连接核心接口
- 统一的 `execute()` 方法，支持自动操作类型检测
- SQL 日志记录和参数格式化
- 连接池支持（通过 DBUtils）
- 事务管理上下文管理器

**baseDBModel.py**
- Pydantic 模型基类，提供 ORM 功能
- 自动表检测和创建（支持手动声明建表 SQL）
- 完整的 CRUD 操作：save、get_by_id、find_by、delete 等
- 支持多数据库连接（全局默认、类级别、实例级别）
- 字段类型安全

**connectionManager.py**
- 数据库连接管理器，支持多数据源
- 连接注册和获取
- 适用于读写分离、分库分表等场景

**connections/**
- MySQLConnection: MySQL 实现，支持连接池和 DictCursor
- PostgreSQLConnection: PostgreSQL 实现
- SQLiteConnection: SQLite 实现（内存/文件）

#### 使用示例

```python
from Base.Repository.base.baseDBModel import BaseDBModel
from Base.Repository.connections.mysqlConnection import MySQLConnection

# 创建连接
db = MySQLConnection(
    host="localhost",
    user="root",
    password="password",
    database="mydb",
    port=3306,
    charset="utf8mb4",
    mincached=2,
    maxcached=10,
    maxconnections=20,
    blocking=False
)

# 定义模型
class User(BaseDBModel):
    table_alias = "users"
    create_table_sql = """
        CREATE TABLE users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100),
            email VARCHAR(255)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """
    id: Optional[int] = None
    name: str
    email: str

# 设置连接
User.set_db_connection(db)

# CRUD 操作
user = User(name="Alice", email="alice@example.com")
user.save()  # 自动建表

found_user = User.get_by_id(user.id)
users = User.find_by(name="Alice")
```

### 2. Ai - AI/LLM 集成

提供统一的 LLM 调用接口，支持多种 AI 模型。

#### 架构设计

```
Ai/
├── base/                   # LLM 抽象基类
│   ├── baseLlm.py          # LLM 抽象基类
│   ├── baseMessages.py      # 消息封装
│   ├── baseEnum.py         # 枚举定义
│   └── baseSetting.py      # LLM 配置
└── llms/                   # 具体实现
    ├── qwenLlm.py         # 通义千问实现
    └── deepseekLlm.py     # DeepSeek 实现
```

#### 核心功能

- 统一的 LLM 调用接口（同步/异步）
- 流式输出支持
- 配置管理
- 多模型支持（Qwen、DeepSeek 等）

### 3. Client - 客户端封装

提供常用第三方服务的客户端封装，简化调用。

#### 支持的服务

- **emailClient.py**: 邮件发送（SMTP）
  - 支持 HTML/纯文本
  - 支持附件
  - 支持内联图片
  - 重试机制和错误处理

- **redisClient.py**: Redis 缓存
- **minioClient.py**: MinIO 对象存储
- **asrClient.py**: 语音识别服务
- **mysqlClient.py**: MySQL 操作封装
- **qwen.py**: 通义千问 API

#### 使用示例

```python
from Base.Client.emailClient import send_email

success = send_email(
    sender_email="sender@example.com",
    receiver_emails=["user1@example.com", "user2@example.com"],
    subject="测试邮件",
    body="邮件内容",
    is_html=False,
    attachments=["/path/to/file.pdf"],
    timeout=30,
    max_retries=2
)
```

### 4. Config - 配置管理

基于 Pydantic Settings 的配置管理，支持环境变量。

#### 核心组件

**setting.py**
- 继承自 `pydantic_settings.BaseSettings`
- 自动从 `.env` 文件加载配置
- 支持环境变量前缀
- 类型安全的配置访问
- 支持嵌套配置类

**logConfig.py**
- 日志配置管理
- 自动设置日志系统

#### 使用示例

```python
# .env 文件
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=password

# Python 代码
from Base.Config.setting import settings

print(settings.mysql.host)  # localhost
print(settings.mysql.user)   # root
```

### 5. Models - 数据模型

数据库模型的业务层定义。

#### BaseEmailModels.py

邮件发送记录模型，包含：
- 发件人/收件人信息
- 邮件主题和内容
- SMTP 配置
- 发送状态管理
- 附件支持（JSON 格式）
- 重试机制
- 状态管理方法（mark_success、mark_failed 等）

### 6. RicUtils - 工具函数库

提供常用的工具函数集合。

#### 工具分类

| 文件 | 功能 |
|------|------|
| `fileUtils.py` | 文件操作工具 |
| `pathUtils.py` | 路径处理工具（项目根目录查找） |
| `dateUtils.py` | 日期时间工具 |
| `dataUtils.py` | 数据处理工具 |
| `httpUtils.py` | HTTP 请求工具 |
| `decoratorUtils.py` | 装饰器工具 |
| `docUtils.py` | 文档处理工具 |
| `pdfUtils.py` | PDF 操作工具 |
| `audioFileUtils.py` | 音频文件处理 |
| `redisUtils.py` | Redis 操作工具 |
| `redis_cache_example.py` | Redis 缓存示例 |
| `reflectUtils.py` | 反射工具 |

### 7. Meta - 设计模式

提供元类和设计模式的实现。

#### singletonMeta.py

线程安全的单例模式元类：

```python
class MyClass(metaclass=SingletonMeta):
    pass

# MyClass 在整个应用中只有唯一实例
```

### 8. Service - 业务服务层

提供业务逻辑封装。

#### asrService.py

语音识别服务，封装 ASR 相关的业务逻辑。

### 9. DataSet - 数据集管理

数据集管理和处理工具。

## 技术栈

### 核心依赖

- **Pydantic**: 数据验证和模型
- **Pydantic Settings**: 配置管理
- **DBUtils**: 数据库连接池
- **pymysql**: MySQL 驱动
- **psycopg2**: PostgreSQL 驱动
- **OpenAI**: LLM 调用

### 数据库支持

- ✅ MySQL（支持连接池）
- ✅ PostgreSQL
- ✅ SQLite（支持内存数据库）

## 设计模式和架构原则

### 1. 分层架构

```
Service (业务逻辑)
    ↓
Repository (数据访问)
    ↓
Connections (数据库连接)
```

### 2. 抽象工厂模式

- `BaseConnection` → MySQLConnection/PostgreSQLConnection/SQLiteConnection
- `BaseLlm` → QwenLlm/DeepSeekLlm

### 3. 单例模式

- `ConnectionManager`: 全局连接管理
- `SingletonMeta`: 线程安全单例元类

### 4. ORM 模式

- Pydantic 模型 + 自动表检测
- CRUD 操作封装

### 5. 配置驱动

- 环境变量配置
- 类型安全
- 支持 `.env` 文件

## 初始化流程

Base 包导入时的自动初始化顺序：

```python
# Base/__init__.py
1. from Base.Config.logConfig import setup_logging
2. from Base.Config.setting import settings
3. setup_logging()  # 初始化日志
4. default_qwen_llm = create_qwen_llm()  # 初始化默认 LLM

# Repository/__init__.py
1. register_default_connection()  # 注册默认数据库连接
2. register_base_module_connection()  # 注册 Base 模块连接
```

## 使用建议

### 1. 数据库操作

- 优先使用 `BaseDBModel` 的 ORM 方法
- 利用连接池提升性能
- 使用 `ConnectionManager` 管理多数据源

### 2. 配置管理

- 在 `.env` 文件中定义配置
- 使用 `settings` 访问配置
- 支持环境变量覆盖

### 3. AI 集成

- 继承 `BaseLlm` 实现新的 LLM
- 使用统一的 `invoke()` 和 `ainvoke()` 接口
- 支持流式输出

### 4. 客户端使用

- 导入所需的客户端实例
- 使用统一的方法接口
- 注意错误处理和重试机制

## 扩展指南

### 添加新数据库支持

1. 在 `Repository/connections/` 创建新文件
2. 继承 `BaseConnection`
3. 实现抽象方法：
   - `_ensure_database_exists()`
   - `_create_connection_pool()`
   - `_get_raw_connection()`

### 添加新 LLM 支持

1. 在 `Ai/llms/` 创建新文件
2. 继承 `BaseLlm`
3. 实现 `init_model()` 方法

### 添加新模型

1. 在 `Models/` 创建新文件
2. 继承 `BaseModuleDBModel` 或 `BaseDBModel`
3. 定义 `create_table_sql`
4. 添加业务方法

## 测试

Repository 层提供完整的测试覆盖：

```bash
cd Base/Repository/test
pytest test_*.py
```

测试覆盖：
- 数据库连接
- CRUD 操作
- 自动建表
- 事务管理
- 错误处理
