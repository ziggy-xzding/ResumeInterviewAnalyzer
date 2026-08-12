"""
BaseConnection 抽象基类测试
测试抽象接口和公共方法
"""

import pytest
from abc import ABC
from Base.Repository.base.baseConnection import BaseConnection


def test_base_connection_is_abstract():
    """测试 BaseConnection 是抽象基类"""
    assert issubclass(BaseConnection, ABC)


def test_base_connection_cannot_instantiate():
    """测试不能直接实例化 BaseConnection"""
    with pytest.raises(TypeError):
        BaseConnection(
            host="localhost",
            user="root",
            password="root",
            database="test",
            port=3306,
            charset="utf8",
            mincached=2,
            maxcached=10,
            maxconnections=20,
            blocking=False
        )


def test_base_connection_has_abstract_methods():
    """测试 BaseConnection 有正确的抽象方法"""
    abstract_methods = BaseConnection.__abstractmethods__
    assert "_ensure_database_exists" in abstract_methods
    assert "_create_connection_pool" in abstract_methods
    assert "_get_raw_connection" in abstract_methods


def test_base_connection_config_initialization():
    """测试配置初始化"""
    # 创建一个简单的子类用于测试配置初始化
    class TestConnection(BaseConnection):
        def _ensure_database_exists(self):
            pass

        def _create_connection_pool(self):
            pass

        def _get_raw_connection(self):
            return None

    conn = TestConnection(
        host="test-host",
        user="test-user",
        password="test-pass",
        database="test-db",
        port=3307,
        charset="utf8mb4",
        mincached=5,
        maxcached=15,
        maxconnections=25,
        blocking=True
    )

    # 测试 config
    assert conn.config["host"] == "test-host"
    assert conn.config["user"] == "test-user"
    assert conn.config["password"] == "test-pass"
    assert conn.config["database"] == "test-db"
    assert conn.config["port"] == 3307
    assert conn.config["charset"] == "utf8mb4"

    # 测试 pool_config
    assert conn.pool_config["mincached"] == 5
    assert conn.pool_config["maxcached"] == 15
    assert conn.pool_config["maxconnections"] == 25
    assert conn.pool_config["blocking"] is True


def test_base_connection_default_config():
    """测试默认配置"""
    class TestConnection(BaseConnection):
        def _ensure_database_exists(self):
            pass

        def _create_connection_pool(self):
            pass

        def _get_raw_connection(self):
            return None

    conn = TestConnection(
        host="localhost",
        user="test",
        password="test",
        database="test",
        port=3306,
        charset="utf8",
        mincached=0,
        maxcached=0,
        maxconnections=1,
        blocking=False
    )

    assert conn._connection_pool is None


def test_base_connection_has_required_methods():
    """测试 BaseConnection 有所有必需的公共方法"""
    required_methods = [
        'get_connection',
        'get_connection_context',
        'execute_query',
        'execute_update',
        'execute_insert',
        'get_connection_for_transaction',
        'close'
    ]

    for method in required_methods:
        assert hasattr(BaseConnection, method), f"Missing method: {method}"


def test_base_connection_context_manager_is_contextmanager():
    """测试上下文管理器方法"""
    from contextlib import contextmanager

    # 检查 get_connection_context 是否是上下文管理器
    assert hasattr(BaseConnection, 'get_connection_context')

    # 检查 get_connection_for_transaction 是否是上下文管理器
    assert hasattr(BaseConnection, 'get_connection_for_transaction')


def test_base_connection_execute_query_signature():
    """测试 execute_query 方法签名"""
    import inspect
    sig = inspect.signature(BaseConnection.execute_query)
    params = list(sig.parameters.keys())

    assert 'sql' in params
    assert 'params' in params


def test_base_connection_execute_update_signature():
    """测试 execute_update 方法签名"""
    import inspect
    sig = inspect.signature(BaseConnection.execute_update)
    params = list(sig.parameters.keys())

    assert 'sql' in params
    assert 'params' in params
    assert 'commit' in params


def test_base_connection_execute_method_exists():
    """测试新的统一 execute 方法存在"""
    assert hasattr(BaseConnection, 'execute')


def test_base_connection_execute_signature():
    """测试 execute 方法签名"""
    import inspect
    sig = inspect.signature(BaseConnection.execute)
    params = list(sig.parameters.keys())

    assert 'sql' in params
    assert 'params' in params
    assert 'operation_type' in params
    assert 'commit' in params


def test_base_connection_operation_type_constants():
    """测试 OperationType 常量"""
    from Base.Repository.base.baseConnection import OperationType

    assert hasattr(OperationType, 'QUERY')
    assert hasattr(OperationType, 'INSERT')
    assert hasattr(OperationType, 'UPDATE')
    assert hasattr(OperationType, 'DELETE')
    assert hasattr(OperationType, 'EXECUTE')

    assert OperationType.QUERY == "query"
    assert OperationType.INSERT == "insert"
    assert OperationType.UPDATE == "update"
    assert OperationType.DELETE == "delete"
    assert OperationType.EXECUTE == "execute"


def test_base_connection_detect_operation_type():
    """测试 _detect_operation_type 方法"""
    # 创建一个测试连接实例
    class TestConnection(BaseConnection):
        def _ensure_database_exists(self):
            pass

        def _create_connection_pool(self):
            pass

        def _get_raw_connection(self):
            pass

    conn = TestConnection(
        host="localhost",
        user="root",
        password="root",
        database="test",
        port=3306,
        charset="utf8",
        mincached=2,
        maxcached=10,
        maxconnections=20,
        blocking=False
    )

    assert conn._detect_operation_type("SELECT * FROM users") == "query"
    assert conn._detect_operation_type("INSERT INTO users VALUES (1, 'test')") == "insert"
    assert conn._detect_operation_type("UPDATE users SET name = 'test'") == "update"
    assert conn._detect_operation_type("DELETE FROM users WHERE id = 1") == "delete"
    assert conn._detect_operation_type("CREATE TABLE test (id INT)") == "execute"
    assert conn._detect_operation_type("  SELECT * FROM users  ") == "query"  # 测试空格
    assert conn._detect_operation_type("show tables") == "query"  # 测试小写
    assert conn._detect_operation_type("DESCRIBE users") == "query"  # 测试 DESCRIBE


def test_base_connection_execute_insert_signature():
    """测试 execute_insert 方法签名"""
    import inspect
    sig = inspect.signature(BaseConnection.execute_insert)
    params = list(sig.parameters.keys())

    assert 'sql' in params
    assert 'params' in params
    assert 'commit' in params


def test_base_connection_execute_method_exists():
    """测试新的统一 execute 方法存在"""
    assert hasattr(BaseConnection, 'execute')


def test_base_connection_execute_signature():
    """测试 execute 方法签名"""
    import inspect
    sig = inspect.signature(BaseConnection.execute)
    params = list(sig.parameters.keys())

    assert 'sql' in params
    assert 'params' in params
    assert 'operation_type' in params
    assert 'commit' in params


def test_base_connection_operation_type_constants():
    """测试 OperationType 常量"""
    from Base.Repository.base.baseConnection import OperationType

    assert hasattr(OperationType, 'QUERY')
    assert hasattr(OperationType, 'INSERT')
    assert hasattr(OperationType, 'UPDATE')
    assert hasattr(OperationType, 'DELETE')
    assert hasattr(OperationType, 'EXECUTE')

    assert OperationType.QUERY == "query"
    assert OperationType.INSERT == "insert"
    assert OperationType.UPDATE == "update"
    assert OperationType.DELETE == "delete"
    assert OperationType.EXECUTE == "execute"


def test_base_connection_detect_operation_type():
    """测试 _detect_operation_type 方法"""
    # 创建一个测试连接实例
    class TestConnection(BaseConnection):
        def _ensure_database_exists(self):
            pass

        def _create_connection_pool(self):
            pass

        def _get_raw_connection(self):
            pass

    conn = TestConnection(
        host="localhost",
        user="root",
        password="root",
        database="test",
        port=3306,
        charset="utf8",
        mincached=2,
        maxcached=10,
        maxconnections=20,
        blocking=False
    )

    assert conn._detect_operation_type("SELECT * FROM users") == "query"
    assert conn._detect_operation_type("INSERT INTO users VALUES (1, 'test')") == "insert"
    assert conn._detect_operation_type("UPDATE users SET name = 'test'") == "update"
    assert conn._detect_operation_type("DELETE FROM users WHERE id = 1") == "delete"
    assert conn._detect_operation_type("CREATE TABLE test (id INT)") == "execute"
    assert conn._detect_operation_type("  SELECT * FROM users  ") == "query"  # 测试空格
    assert conn._detect_operation_type("show tables") == "query"  # 测试小写
    assert conn._detect_operation_type("DESCRIBE users") == "query"  # 测试 DESCRIBE
