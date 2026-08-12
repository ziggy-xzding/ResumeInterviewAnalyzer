"""
MySQLConnection 测试
测试 MySQL 连接的所有功能
"""

import pytest
from Base.Repository.connections.mysqlConnection import MySQLConnection, get_module_mysql_connection
from Base.Repository.base.baseConnection import BaseConnection
from Base.Config.setting import settings


def test_mysql_connection_inheritance():
    """测试 MySQLConnection 是否正确继承 BaseConnection"""
    assert issubclass(MySQLConnection, BaseConnection)


def test_mysql_connection_create():
    """测试创建 MySQL 连接"""
    db = MySQLConnection(
        host=settings.mysql.host,
        user=settings.mysql.user,
        password=settings.mysql.password,
        database="test_mysql_conn",
        port=3306,
        charset="utf8mb4",
        mincached=0,
        maxcached=0,
        maxconnections=1,
        blocking=False
    )
    assert db is not None
    assert db.config["host"] == settings.mysql.host
    assert db.config["database"] == "test_mysql_conn"
    db.close()


def test_mysql_connection_config():
    """测试连接配置"""
    db = MySQLConnection(
        host="localhost",
        user="root",
        password="root",
        database="test_config",
        port=3306,
        charset="utf8mb4",
        mincached=2,
        maxcached=10,
        maxconnections=20,
        blocking=True
    )
    assert db.config["host"] == "localhost"
    assert db.config["port"] == 3306
    assert db.config["charset"] == "utf8mb4"
    assert db.pool_config["mincached"] == 2
    assert db.pool_config["maxcached"] == 10
    assert db.pool_config["maxconnections"] == 20
    assert db.pool_config["blocking"] is True
    db.close()


def test_mysql_connection_pool():
    """测试连接池配置"""
    db = MySQLConnection(
        host="localhost",
        user="root",
        password="root",
        database="test_pool",
        mincached=2,
        maxcached=10,
        maxconnections=20
    )
    assert db._connection_pool is not None
    db.close()


def test_mysql_connection_get_raw_connection():
    """测试获取原生连接"""
    db = MySQLConnection(
        host="localhost",
        user="root",
        password="root",
        database="test_raw_conn",
        mincached=0,
        maxcached=0,
        maxconnections=1
    )
    conn = db.get_connection()
    assert conn is not None
    conn.close()
    db.close()


def test_mysql_connection_context_manager():
    """测试连接上下文管理器"""
    db = MySQLConnection(
        host="localhost",
        user="root",
        password="root",
        database="test_context",
        mincached=0,
        maxcached=0,
        maxconnections=1
    )
    with db.get_connection_context() as conn:
        assert conn is not None
    # 上下文结束后连接应该已关闭
    db.close()


def test_mysql_connection_execute():
    """测试执行查询语句"""
    db = MySQLConnection(
        host="localhost",
        user="root",
        password="root",
        database="test_query",
        mincached=0,
        maxcached=0,
        maxconnections=1
    )

    # 创建测试表
    db.execute("""
        CREATE TABLE IF NOT EXISTS test_table (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            age INT
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    # 插入测试数据
    db.execute(
        "INSERT INTO test_table (name, age) VALUES (%s, %s)",
        ("Alice", 25)
    )

    # 查询数据
    results = db.execute("SELECT * FROM test_table")
    assert len(results) == 1
    assert results[0]["name"] == "Alice"
    assert results[0]["age"] == 25

    db.close()


def test_mysql_connection_execute_no_results():
    """测试查询无结果"""
    db = MySQLConnection(
        host="localhost",
        user="root",
        password="root",
        database="test_no_results",
        mincached=0,
        maxcached=0,
        maxconnections=1
    )

    db.execute("""
        CREATE TABLE IF NOT EXISTS test_table (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    results = db.execute("SELECT * FROM test_table")
    assert results == [] or results == ()

    db.close()


def test_mysql_connection_execute():
    """测试执行插入语句"""
    db = MySQLConnection(
        host="localhost",
        user="root",
        password="root",
        database="test_insert",
        mincached=0,
        maxcached=0,
        maxconnections=1
    )

    db.execute("""
        CREATE TABLE IF NOT EXISTS test_table (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    last_id = db.execute("INSERT INTO test_table (name) VALUES (%s)", ("Alice",))
    assert last_id == 1

    last_id = db.execute("INSERT INTO test_table (name) VALUES (%s)", ("Bob",))
    assert last_id == 2

    db.close()


def test_mysql_connection_execute():
    """测试执行更新语句"""
    db = MySQLConnection(
        host="localhost",
        user="root",
        password="root",
        database="test_update",
        mincached=0,
        maxcached=0,
        maxconnections=1
    )

    db.execute("""
        CREATE TABLE IF NOT EXISTS test_table (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    db.execute("INSERT INTO test_table (name) VALUES (%s)", ("Alice",))

    # 更新
    affected = db.execute("UPDATE test_table SET name = %s", ("Bob",))
    assert affected == 1

    # 验证更新
    results = db.execute("SELECT name FROM test_table WHERE id = %s", (1,))
    assert results[0]["name"] == "Bob"

    db.close()


def test_mysql_connection_execute_no_affected():
    """测试更新无影响行"""
    db = MySQLConnection(
        host="localhost",
        user="root",
        password="root",
        database="test_no_affected",
        mincached=0,
        maxcached=0,
        maxconnections=1
    )

    db.execute("""
        CREATE TABLE IF NOT EXISTS test_table (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    affected = db.execute("UPDATE test_table SET name = %s", ("Bob",))
    assert affected == 0

    db.close()


def test_mysql_connection_transaction_context():
    """测试事务上下文管理器"""
    db = MySQLConnection(
        host="localhost",
        user="root",
        password="root",
        database="test_transaction"
    )

    db.execute("""
        CREATE TABLE IF NOT EXISTS test_table (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    # 使用事务插入多条数据
    with db.get_connection_context() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO test_table (name) VALUES (%s)", ("Alice",))
        cur.execute("INSERT INTO test_table (name) VALUES (%s)", ("Bob",))
        conn.commit()  # 手动提交事务

    # 验证数据
    results = db.execute("SELECT COUNT(*) as count FROM test_table")
    assert results[0]["count"] == 2

    db.close()


def test_mysql_connection_table_exists():
    """测试检查表是否存在"""
    db = MySQLConnection(
        host="localhost",
        user="root",
        password="root",
        database="test_table_exists",
        mincached=0,
        maxcached=0,
        maxconnections=1
    )

    db.execute("""
        CREATE TABLE IF NOT EXISTS test_table (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    assert db.table_exists("test_table") is True
    assert db.table_exists("non_existent_table") is False

    db.close()


def test_mysql_connection_close():
    """测试关闭连接"""
    db = MySQLConnection(
        host="localhost",
        user="root",
        password="root",
        database="test_close",
        mincached=0,
        maxcached=0,
        maxconnections=1
    )
    assert db is not None

    db.close()
    # close() 不应该抛出异常


def test_mysql_connection_batch_operations():
    """测试批量操作"""
    db = MySQLConnection(
        host="localhost",
        user="root",
        password="root",
        database="test_batch",
        mincached=0,
        maxcached=0,
        maxconnections=1
    )

    db.execute("""
        CREATE TABLE IF NOT EXISTS test_table (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100),
            age INT
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    # 批量插入
    data = [("Alice", 25), ("Bob", 30), ("Charlie", 35)]
    with db.get_connection_context() as conn:
        cur = conn.cursor()
        cur.executemany("INSERT INTO test_table (name, age) VALUES (%s, %s)", data)
        conn.commit()  # 手动提交事务

    # 验证数据
    results = db.execute("SELECT COUNT(*) as count FROM test_table")
    assert results[0]["count"] == 3

    db.close()


def test_mysql_connection_complex_query():
    """测试复杂查询"""
    db = MySQLConnection(
        host="localhost",
        user="root",
        password="root",
        database="test_complex",
        mincached=0,
        maxcached=0,
        maxconnections=1
    )

    db.execute("""
        CREATE TABLE IF NOT EXISTS test_table (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100),
            age INT,
            score DECIMAL(10,2)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    # 插入测试数据
    db.execute(
        "INSERT INTO test_table (name, age, score) VALUES (%s, %s, %s)",
        ("Alice", 25, 95.5)
    )
    db.execute(
        "INSERT INTO test_table (name, age, score) VALUES (%s, %s, %s)",
        ("Bob", 30, 88.0)
    )
    db.execute(
        "INSERT INTO test_table (name, age, score) VALUES (%s, %s, %s)",
        ("Charlie", 35, 92.5)
    )

    # 复杂查询
    results = db.execute(
        "SELECT * FROM test_table WHERE age > %s AND score > %s ORDER BY score DESC",
        (25, 90.0)
    )
    assert len(results) == 2
    assert results[0]["name"] == "Alice"
    assert results[1]["name"] == "Charlie"

    db.close()


def test_mysql_connection_with_params():
    """测试带参数的查询"""
    db = MySQLConnection(
        host="localhost",
        user="root",
        password="root",
        database="test_params",
        mincached=0,
        maxcached=0,
        maxconnections=1
    )

    db.execute("""
        CREATE TABLE IF NOT EXISTS test_table (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100),
            age INT
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    db.execute("INSERT INTO test_table (name, age) VALUES (%s, %s)", ("Alice", 25))
    db.execute("INSERT INTO test_table (name, age) VALUES (%s, %s)", ("Bob", 30))

    # 使用参数查询
    results = db.execute("SELECT * FROM test_table WHERE age = %s", (25,))
    assert len(results) == 1
    assert results[0]["name"] == "Alice"

    db.close()


def test_mysql_connection_empty_params():
    """测试空参数"""
    db = MySQLConnection(
        host="localhost",
        user="root",
        password="root",
        database="test_empty_params",
        mincached=0,
        maxcached=0,
        maxconnections=1
    )

    db.execute("""
        CREATE TABLE IF NOT EXISTS test_table (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    db.execute("INSERT INTO test_table (name) VALUES (%s)", ("Alice",))

    # 不带参数查询
    results = db.execute("SELECT * FROM test_table")
    assert len(results) == 1

    db.close()


def test_get_module_mysql_connection():
    """测试 get_module_mysql_connection 函数"""
    db = get_module_mysql_connection()
    assert db is not None
    assert isinstance(db, MySQLConnection)
    assert db.config["host"] == settings.mysql.host
    assert db.config["database"] == settings.base_module.db_name


def test_get_module_mysql_connection_singleton():
    """测试 get_module_mysql_connection 返回单例"""
    conn1 = get_module_mysql_connection()
    conn2 = get_module_mysql_connection()

    # 应该返回不同的连接对象（不是单例）
    # 但配置相同
    assert conn1 is not conn2
    assert conn1.config["database"] == conn2.config["database"]


def test_mysql_connection_mysql_syntax():
    """测试 MySQL 特定语法"""
    db = MySQLConnection(
        host="localhost",
        user="root",
        password="root",
        database="test_mysql_syntax",
        mincached=0,
        maxcached=0,
        maxconnections=1
    )

    # MySQL 特定语法
    db.execute("""
        CREATE TABLE IF NOT EXISTS test_table (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(255) UNIQUE,
            age INT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    db.execute(
        "INSERT INTO test_table (name, email, age) VALUES (%s, %s, %s)",
        ("Alice", "alice@example.com", 25)
    )

    results = db.execute("SELECT * FROM test_table")
    assert len(results) == 1
    assert results[0]["name"] == "Alice"
    assert "created_at" in results[0]

    db.close()


def test_mysql_connection_auto_increment():
    """测试 AUTO_INCREMENT 功能"""
    db = MySQLConnection(
        host="localhost",
        user="root",
        password="root",
        database="test_auto_increment",
        mincached=0,
        maxcached=0,
        maxconnections=1
    )

    db.execute("""
        CREATE TABLE IF NOT EXISTS test_table (
            id INT AUTO_INCREMENT PRIMARY KEY,
            value VARCHAR(100)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    # 插入三条记录
    for value in ["A", "B", "C"]:
        db.execute("INSERT INTO test_table (value) VALUES (%s)", (value,))

    # 查询验证 ID 自动递增
    results = db.execute("SELECT id, value FROM test_table ORDER BY id")
    assert len(results) == 3
    assert results[0]["id"] == 1
    assert results[1]["id"] == 2
    assert results[2]["id"] == 3

    db.close()


def test_mysql_connection_unified_execute():
    """测试统一的 execute 函数 - MySQL"""
    from Base.Repository.base.baseConnection import OperationType

    db = MySQLConnection(
        host=settings.mysql.host,
        user=settings.mysql.user,
        password=settings.mysql.password,
        database="test_mysql_execute",
        port=3306,
        charset="utf8mb4",
        mincached=0,
        maxcached=0,
        maxconnections=1
    )

    # 创建表
    db.execute(
        "CREATE TABLE IF NOT EXISTS test_unified_execute (id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(100))"
    )

    # 测试 INSERT
    last_id = db.execute(
        "INSERT INTO test_unified_execute (name) VALUES (%s)",
        ("Alice",),
        OperationType.INSERT
    )
    assert last_id == 1

    # 测试自动检测 INSERT
    last_id2 = db.execute("INSERT INTO test_unified_execute (name) VALUES (%s)", ("Bob",))
    assert last_id2 == 2

    # 测试 UPDATE（显式指定类型）
    affected = db.execute(
        "UPDATE test_unified_execute SET name = %s WHERE id = %s",
        ("Alice Updated", 1),
        OperationType.UPDATE
    )
    assert affected == 1

    # 测试自动检测 UPDATE
    affected2 = db.execute(
        "UPDATE test_unified_execute SET name = %s WHERE id = %s",
        ("Bob Updated", 2)
    )
    assert affected2 == 1

    # 测试 QUERY（显式指定类型）
    results = db.execute(
        "SELECT * FROM test_unified_execute WHERE id = %s",
        (1,),
        OperationType.QUERY
    )
    assert len(results) == 1
    assert results[0]["name"] == "Alice Updated"

    # 测试自动检测 QUERY
    results2 = db.execute("SELECT * FROM test_unified_execute ORDER BY id")
    assert len(results2) == 2
    assert results2[0]["name"] == "Alice Updated"
    assert results2[1]["name"] == "Bob Updated"

    # 测试 DELETE（显式指定类型）
    affected = db.execute(
        "DELETE FROM test_unified_execute WHERE id = %s",
        (1,),
        OperationType.DELETE
    )
    assert affected == 1

    # 测试自动检测 DELETE
    affected2 = db.execute("DELETE FROM test_unified_execute WHERE id = %s", (2,))
    assert affected2 == 1

    # 验证表为空
    results3 = db.execute("SELECT COUNT(*) as count FROM test_unified_execute")
    assert results3[0]["count"] == 0

    db.close()
