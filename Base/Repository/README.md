# Repository 模块文档

## 目录

- [概述](#概述)
- [架构设计](#架构设计)
- [核心模块](#核心模块)
- [快速开始](#快速开始)
- [详细使用指南](#详细使用指南)
- [多数据库支持](#多数据库支持)
- [连接管理](#连接管理)
- [模型使用](#模型使用)
- [最佳实践](#最佳实践)
- [迁移指南](#迁移指南)
- [常见问题](#常见问题)

---

## 概述

Repository 模块提供了一个完整的数据持久化解决方案，支持多种数据库，具有以下特点：

- ✅ **多数据库支持** - MySQL, PostgreSQL, SQLite
- ✅ **连接池管理** - 高性能并发访问
- ✅ **ORM 风格** - 简洁的模型操作接口
- ✅ **事务管理** - 完善的事务支持
- ✅ **类型安全** - 基于 Pydantic 的数据验证
- ✅ **向后兼容** - 平滑升级路径

---

## 架构设计

### 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    BaseDBModel (ORM)                        │
│  - save(), get_by_id(), update(), delete()                  │
│  - find_by(), find_one_by(), get_all(), count()             │
└────────────────────┬────────────────────────────────────────┘
                     │ 使用
                     ↓
┌─────────────────────────────────────────────────────────────┐
│              BaseConnection (抽象基类)                       │
│  - 连接池管理                                                │
│  - SQL 执行方法 (execute)                                    │
│  - 事务管理                                                  │
└────┬────────────────┬────────────────┬──────────────────────┘
     │                │                │
     │ 继承           │ 继承           │ 继承
     ↓                ↓                ↓
┌──────────┐   ┌──────────┐   ┌──────────┐
│ MySQL    │   │PostgreSQL│   │  SQLite  │
│Connection│   │Connection│   │Connection│
└──────────┘   └──────────┘   └──────────┘
```

### 模块职责


| 模块                    | 职责            | 说明                             |
| ----------------------- | --------------- | -------------------------------- |
| `baseConnection.py`     | 抽象基类        | 定义通用连接接口，实现连接池管理 |
| `databaseConnection.py` | MySQL 实现      | MySQL 特定的连接逻辑             |
| `postgresConnection.py` | PostgreSQL 实现 | PostgreSQL 特定的连接逻辑        |
| `sqliteConnection.py`   | SQLite 实现     | SQLite 特定的连接逻辑            |
| `baseDBModel.py`        | ORM 基类        | 提供模型操作接口                 |
| `connectionManager.py`  | 连接管理器      | 管理多个数据库连接               |

---

## 核心模块

### 1. BaseConnection (抽象基类)

**位置**: `Base/Repository/base/baseConnection.py`

**作用**: 定义所有数据库连接的通用接口

**核心方法**:

```python
class BaseConnection(ABC):
    # 抽象方法（子类必须实现）
    def _ensure_database_exists(self): ...
    def _create_connection_pool(self): ...
    def _get_raw_connection(self): ...

    # 公共方法
    def execute_query(sql, params): ...
    def execute_update(sql, params, commit): ...
    def execute_insert(sql, params, commit): ...
    def get_connection_context(): ...
    def get_connection_for_transaction(): ...
```

### 2. MySQLConnection

**位置**: `Base/Repository/base/databaseConnection.py`

**作用**: MySQL 数据库的具体实现

**特点**:

- 连接池支持
- 自动创建数据库
- 字典游标
- 表存在性检查

**向后兼容**: `DatabaseConnection` 是 `MySQLConnection` 的别名

### 3. PostgreSQLConnection

**位置**: `Base/Repository/base/postgresConnection.py`

**作用**: PostgreSQL 数据库的具体实现

**特点**:

- 支持 psycopg2
- 自动创建数据库
- RealDictCursor 返回

### 4. SQLiteConnection

**位置**: `Base/Repository/base/sqliteConnection.py`

**作用**: SQLite 数据库的具体实现

**特点**:

- 内存数据库支持 (`:memory:`)
- 文件数据库支持
- 单连接模式（不支持连接池）

### 5. BaseDBModel

**位置**: `Base/Repository/base/baseDBModel.py`

**作用**: ORM 风格的模型基类

**核心功能**:

- 自动表名映射（类名或 table_alias）
- CRUD 操作
- 连接管理（三级优先级）
- 事务支持

**必须字段**:

```python
class MyModel(BaseDBModel):
    id: Optional[int] = None  # 主键字段（必选）
```

### 6. ConnectionManager

**位置**: `Base/Repository/base/connectionManager.py`

**作用**: 管理多个数据库连接

**使用场景**:

- 读写分离
- 分库分表
- 多租户隔离

---

## 快速开始

### 1. 创建数据库连接

```python
from Base.Repository.base.databaseConnection import MySQLConnection

# 创建 MySQL 连接
db = MySQLConnection(
    host="localhost",
    user="root",
    password="root",
    database="my_app"
)
```

### 2. 定义模型

```python
from Base.Repository.base.baseDBModel import BaseDBModel
from typing import Optional, ClassVar

class User(BaseDBModel):
    """用户模型"""
    table_alias: ClassVar[str] = "users"  # 可选表名
    id: Optional[int] = None  # 主键（必选）
    name: str
    email: str
    age: Optional[int] = None
```

### 3. 设置连接

```python
# 方式 1: 设置全局默认连接
BaseDBModel.set_default_db_connection(db)

# 方式 2: 为特定模型设置连接
User.set_db_connection(db)

# 方式 3: 为实例设置连接
user = User(name="Alice")
user.set_connection(write_db)
```

### 4. 创建表

```python
table_sql = """
CREATE TABLE `users` (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    age INT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""

if not User.table_exists():
    User.create_table(table_sql)
```

### 5. 基本操作

```python
# 插入
user = User(name="Alice", email="alice@example.com", age=25)
user_id = user.save()

# 查询
user = User.get_by_id(1)
print(user.name)

# 更新
user.age = 26
user.update()
# 或
user.update(age=26)

# 删除
user.delete()

# 条件查询
users = User.find_by(name="Alice")
user = User.find_one_by(email="alice@example.com")

# 查询所有
all_users = User.get_all()
all_users = User.get_all(limit=10, offset=0)

# 统计
count = User.count()
```

---

## 详细使用指南

### 数据库连接

#### MySQL 连接

```python
from Base.Repository.base.databaseConnection import MySQLConnection

db = MySQLConnection(
    host="localhost",
    user="root",
    password="root",
    database="my_app",
    port=3306,
    charset="utf8mb4",
    # 连接池配置
    mincached=2,          # 最小空闲连接数
    maxcached=10,         # 最大空闲连接数
    maxconnections=20,    # 最大连接数
    blocking=False,        # 连接池满时是否阻塞
)

# 使用连接
results = db.execute_query("SELECT * FROM users")
db.close()
```

#### PostgreSQL 连接

```python
from Base.Repository.base.postgresConnection import PostgreSQLConnection

db = PostgreSQLConnection(
    host="localhost",
    user="postgres",
    password="postgres",
    database="my_app",
    port=5432
)

# 使用方式与 MySQL 相同
results = db.execute_query("SELECT * FROM users")
db.close()
```

#### SQLite 连接

```python
from Base.Repository.base.sqliteConnection import SQLiteConnection

# 内存数据库
db = SQLiteConnection(database=":memory:")

# 文件数据库
db = SQLiteConnection(database="my_app.db")

# 使用方式与其他数据库相同
results = db.execute_query("SELECT * FROM users")
db.close()
```

### 模型定义

#### 基本定义

```python
from Base.Repository.base.baseDBModel import BaseDBModel
from typing import Optional, ClassVar

class Product(BaseDBModel):
    """商品模型"""
    table_alias: ClassVar[str] = "products"  # 可选：自定义表名

    id: Optional[int] = None  # 必选：主键字段
    name: str
    price: float
    stock: int = 0
    description: Optional[str] = None
```

#### 自动表名映射

如果未指定 `table_alias`，会自动使用类名转下划线：

```python
# 类名 UserInfo → 表名 user_info
class UserInfo(BaseDBModel):
    id: Optional[int] = None
    name: str

# 表名为 "user_info"
print(UserInfo.get_table_name())  # "user_info"
```

#### 字段验证

```python
from pydantic import Field

class Order(BaseDBModel):
    id: Optional[int] = None

    # 使用 Field 添加验证
    amount: float = Field(..., gt=0, description="订单金额必须大于0")
    quantity: int = Field(default=1, gt=0, le=100)
    status: str = Field(default="pending", pattern="^(pending|paid|shipped)$")

    # 重新定义 id 字段
    order_id: Optional[int] = Field(None, description="订单ID")
```

### CRUD 操作

#### 插入数据

```python
# 方式 1: 创建实例后保存
user = User(name="Alice", email="alice@example.com")
user_id = user.save()
print(f"新用户 ID: {user_id}")

# 方式 2: 使用 save() 自动判断插入/更新
user = User(id=1, name="Alice")
user.save()  # 存在 ID 则更新，否则插入
```

#### 查询数据

```python
# 根据 ID 查询
user = User.get_by_id(1)

# 条件查询
users = User.find_by(age=25)
users = User.find_by(age=25, name="Alice")

# 查询单条记录
user = User.find_one_by(email="alice@example.com")

# 查询所有（分页）
users = User.get_all()
users = User.get_all(limit=10, offset=0)

# 统计数量
count = User.count()
```

#### 更新数据

```python
# 方式 1: 修改属性后保存
user = User.get_by_id(1)
user.age = 26
user.save()

# 方式 2: 使用 update() 方法
user.update(age=27)

# 方式 3: 更新多个字段
user.update(age=28, email="new_email@example.com")
```

#### 删除数据

```python
# 方式 1: 删除实例
user = User.get_by_id(1)
user.delete()

# 方式 2: 根据 ID 删除
User.delete_by_id(1)
```

### 事务处理

#### 使用上下文管理器

```python
from Base.Repository.base.databaseConnection import MySQLConnection

db = MySQLConnection(
    host="localhost",
    user="root",
    password="root",
    database="my_app"
)

# 自动提交事务
with db.get_connection_context() as conn:
    with conn.cursor() as cur:
        cur.execute("INSERT INTO users (name) VALUES (%s)", ("Alice",))
        cur.execute("INSERT INTO logs (message) VALUES (%s)", ("User created",))
    # 退出上下文时自动提交
```

#### 手动控制事务

```python
# 手动提交/回滚
with db.get_connection_for_transaction() as conn:
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO users (name) VALUES (%s)", ("Alice",))
            cur.execute("INSERT INTO logs (message) VALUES (%s)", ("User created",))
        conn.commit()  # 手动提交
    except Exception as e:
        conn.rollback()  # 出错回滚
        raise
```

#### BaseDBModel 事务

```python
from Base.Repository.base.databaseConnection import MySQLConnection

db = MySQLConnection(...)

# 使用连接的事务上下文
with db.get_connection_for_transaction() as conn:
    try:
        # 多个模型操作
        user = User(name="Alice")
        user.set_connection(db)  # 设置连接
        user.save()

        log = Log(message="User created")
        log.set_connection(db)
        log.save()

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise
```

---

## 多数据库支持

### 读写分离

```python
from Base.Repository.base.databaseConnection import MySQLConnection
from Base.Repository.base.baseDBModel import BaseDBModel

# 读库
read_db = MySQLConnection(
    host="read-db-host",
    user="root",
    password="root",
    database="my_app_read"
)

# 写库
write_db = MySQLConnection(
    host="write-db-host",
    user="root",
    password="root",
    database="my_app_write"
)

# 设置默认读连接
BaseDBModel.set_default_db_connection(read_db)

# 查询操作使用读库
users = User.get_all()

# 更新操作使用写库
user = User(name="Alice")
user.set_connection(write_db)  # 切换到写库
user.save()
```

### 分库分表

```python
# 用户库
user_db = MySQLConnection(
    host="localhost",
    user="root",
    password="root",
    database="user_db"
)

# 订单库
order_db = MySQLConnection(
    host="localhost",
    user="root",
    password="root",
    database="order_db"
)

# 为不同模型设置不同连接
User.set_db_connection(user_db)
Order.set_db_connection(order_db)

# 现在不同模型使用不同的数据库
user = User(name="Alice")  # 写入 user_db
user.save()

order = Order(user_id=user.id)  # 写入 order_db
order.save()
```

### 多数据库类型

```python
from Base.Repository.base.databaseConnection import MySQLConnection
from Base.Repository.base.postgresConnection import PostgreSQLConnection
from Base.Repository.base.sqliteConnection import SQLiteConnection
from Base.Repository.base.baseDBModel import BaseDBModel

# 用户数据使用 MySQL
mysql_db = MySQLConnection(
    host="localhost",
    user="root",
    password="root",
    database="my_app"
)

# 分析数据使用 PostgreSQL
postgres_db = PostgreSQLConnection(
    host="localhost",
    user="postgres",
    password="postgres",
    database="analytics"
)

# 日志数据使用 SQLite
sqlite_db = SQLiteConnection(database=":memory:")

# 为不同模型设置不同数据库
User.set_db_connection(mysql_db)
Report.set_db_connection(postgres_db)
Log.set_db_connection(sqlite_db)
```

---

## 连接管理

### ConnectionManager 使用

```python
from Base.Repository.base.connectionManager import ConnectionManager
from Base.Repository.base.databaseConnection import MySQLConnection

# 注册连接
read_db = MySQLConnection(...)
write_db = MySQLConnection(...)

ConnectionManager.register("read", read_db, is_default=True)
ConnectionManager.register("write", write_db)

# 获取连接
default_conn = ConnectionManager.get_default()
read_conn = ConnectionManager.get("read")
write_conn = ConnectionManager.get("write")

# 列出所有连接
keys = ConnectionManager.list_keys()
print(keys)  # ['read', 'write']

# 关闭所有连接
ConnectionManager.close_all()
```

### 连接优先级

BaseDBModel 支持三级连接优先级（从高到低）：

1. **实例级连接** (最高)

   ```python
   user.set_connection(db)
   ```
2. **类级连接**

   ```python
   User.set_db_connection(db)
   ```
3. **全局默认连接** (最低)

   ```python
   BaseDBModel.set_default_db_connection(db)
   ```

**示例**:

```python
# 设置全局默认
BaseDBModel.set_default_db_connection(read_db)

# 为 Order 设置类级连接
Order.set_db_connection(write_db)

# 查询用户（使用全局默认）
users = User.get_all()  # read_db

# 查询订单（使用类级连接）
orders = Order.get_all()  # write_db

# 特定实例使用实例级连接（优先级最高）
order = Order.get_by_id(1)
order.set_connection(special_db)  # 临时切换
order.update()  # special_db
```

---

## 最佳实践

### 1. 模型定义

```python
# ✅ 推荐：明确指定表名和主键
class User(BaseDBModel):
    table_alias: ClassVar[str] = "users"
    id: Optional[int] = None  # 必选
    name: str

# ❌ 不推荐：缺少主键
class BadUser(BaseDBModel):
    name: str  # 会触发验证错误
```

### 2. 连接管理

```python
# ✅ 推荐：使用 ConnectionManager 管理多个连接
ConnectionManager.register("read", read_db)
ConnectionManager.register("write", write_db)

# ❌ 不推荐：全局变量管理
DB_CONNECTION = MySQLConnection(...)
```

### 3. 事务处理

```python
# ✅ 推荐：使用上下文管理器
with db.get_connection_for_transaction() as conn:
    try:
        # 操作
        conn.commit()
    except:
        conn.rollback()
        raise

# ❌ 不推荐：忘记处理异常
conn = db.get_connection()
conn.execute("INSERT ...")
conn.commit()  # 如果出错无法回滚
```

### 4. 批量操作

```python
# ✅ 推荐：使用事务批量插入
with db.get_connection_for_transaction() as conn:
    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO users (name, email) VALUES (%s, %s)",
            [("Alice", "a@e.com"), ("Bob", "b@e.com")]
        )
    conn.commit()

# ❌ 不推荐：循环单条插入
for name, email in users:
    User(name=name, email=email).save()  # 低效
```

### 5. 连接池配置

```python
# ✅ 推荐：根据负载调整
db = MySQLConnection(
    ...,
    mincached=5,         # 高并发环境增加最小连接数
    maxcached=20,        # 增加最大连接数
    maxconnections=50,    # 总连接数
    blocking=True,        # 高并发时启用阻塞等待
)

# ❌ 不推荐：连接池过小
db = MySQLConnection(
    ...,
    mincached=1,  # 连接池过小会导致等待
    maxcached=2,
)
```

---

## 迁移指南

### 从旧架构迁移

#### 步骤 1: 更新导入

```python
# 旧代码
from Base.Repository.adapters.mysqlAdapter import MySQLAdapter

# 新代码
from Base.Repository.base.databaseConnection import MySQLConnection
```

#### 步骤 2: 更新连接创建

```python
# 旧代码
adapter = MySQLAdapter(
    host="localhost",
    user="root",
    password="root",
    database="test_db"
)
db = adapter.get_db_connection()

# 新代码
db = MySQLConnection(
    host="localhost",
    user="root",
    password="root",
    database="test_db"
)
```

#### 步骤 3: 更新方法调用

```python
# 旧代码
adapter.table_exists("users")
adapter.create_table(sql)
adapter.close()

# 新代码
db.table_exists("users")  # 如果需要
db.execute_update(sql)     # 直接执行 SQL
db.close()
```

### 兼容性说明

✅ **向后兼容**

- `DatabaseConnection` 是 `MySQLConnection` 的别名
- `MySQLAdapter` 仍然可用（但已标记为废弃）

⚠️ **注意事项**

- 新代码推荐直接使用 `MySQLConnection`
- `DBAdapter` 可以考虑移除（职责过轻）

---

## 常见问题

### Q1: 如何选择使用哪个数据库？

**A**: 根据场景选择：

- **MySQL**: 成熟稳定，适合大多数应用
- **PostgreSQL**: 需要复杂查询、JSON 支持
- **SQLite**: 轻量级，适合测试、桌面应用

### Q2: 连接池如何配置？

**A**: 根据并发量调整：

```python
db = MySQLConnection(
    ...,
    mincached=2,          # 最小空闲连接
    maxcached=10,         # 最大空闲连接
    maxconnections=20,    # 总连接数
    blocking=False,        # 连接满时是否阻塞
)
```

### Q3: 如何处理事务？

**A**: 使用上下文管理器：

```python
with db.get_connection_for_transaction() as conn:
    try:
        # 操作
        conn.commit()
    except:
        conn.rollback()
        raise
```

### Q4: BaseDBModel 如何设置连接？

**A**: 三级优先级：

```python
# 全局默认
BaseDBModel.set_default_db_connection(db)

# 类级
User.set_db_connection(db)

# 实例级
user.set_connection(db)
```

### Q5: 如何添加新数据库支持？

**A**: 继承 BaseConnection：

```python
class OracleConnection(BaseConnection):
    def _ensure_database_exists(self):
        # Oracle 实现
        pass

    def _create_connection_pool(self):
        # Oracle 实现
        pass

    def _get_raw_connection(self):
        # Oracle 实现
        pass
```

### Q6: MySQLAdapter 还能用吗？

**A**: 可以，但不推荐：

```python
# 仍然工作
from Base.Repository.adapters.mysqlAdapter import MySQLAdapter
adapter = MySQLAdapter(...)
db = adapter.get_db_connection()

# 推荐
from Base.Repository.base.databaseConnection import MySQLConnection
db = MySQLConnection(...)
```

### Q7: 如何实现读写分离？

**A**: 使用不同连接：

```python
BaseDBModel.set_default_db_connection(read_db)
user.save()  # 查询用读库

user.set_connection(write_db)
user.update()  # 更新用写库
```

### Q8: 性能优化建议？

**A**:

- 使用连接池
- 批量操作使用事务
- 合理设置索引
- 避免 N+1 查询
- 使用分页查询

---

## 示例代码

完整示例请查看：

- `Base/Repository/examples/model_example.py` - 基本使用
- `Base/Repository/examples/multi_db_example.py` - 多数据源
- `Base/Repository/examples/connection_pool_test.py` - 连接池测试
- `Base/Repository/examples/multi_database_example.py` - 多数据库类型

---
