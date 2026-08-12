"""
ConnectionManager 测试
测试数据库连接管理器
"""

import pytest
from Base.Repository.base.connectionManager import ConnectionManager
from Base.Repository.connections.sqliteConnection import SQLiteConnection


@pytest.fixture
def sample_connections():
    """创建示例连接"""
    conn1 = SQLiteConnection(database=":memory:")
    conn2 = SQLiteConnection(database=":memory:")
    conn3 = SQLiteConnection(database=":memory:")
    yield conn1, conn2, conn3
    # 清理
    conn1.close()
    conn2.close()
    conn3.close()


def test_connection_manager_register_single(sample_connections):
    """测试注册单个连接"""
    conn1, _, _ = sample_connections

    ConnectionManager.register("test1", conn1)

    assert "test1" in ConnectionManager.list_keys()
    assert ConnectionManager.get("test1") == conn1

    # 清理
    ConnectionManager.close("test1")


def test_connection_manager_register_with_default(sample_connections):
    """测试注册默认连接"""
    conn1, _, _ = sample_connections

    ConnectionManager.register("default_conn", conn1, is_default=True)

    assert ConnectionManager.get_default() == conn1

    # 清理
    ConnectionManager.close_all()


def test_connection_manager_register_multiple(sample_connections):
    """测试注册多个连接"""
    conn1, conn2, conn3 = sample_connections

    ConnectionManager.register("conn1", conn1)
    ConnectionManager.register("conn2", conn2)
    ConnectionManager.register("conn3", conn3)

    keys = ConnectionManager.list_keys()
    assert len(keys) == 3
    assert "conn1" in keys
    assert "conn2" in keys
    assert "conn3" in keys

    # 清理
    ConnectionManager.close_all()


def test_connection_manager_get(sample_connections):
    """测试获取连接"""
    conn1, _, _ = sample_connections

    ConnectionManager.register("test_conn", conn1)

    retrieved = ConnectionManager.get("test_conn")
    assert retrieved == conn1

    # 清理
    ConnectionManager.close_all()


def test_connection_manager_get_with_default(sample_connections):
    """测试获取默认连接"""
    conn1, _, _ = sample_connections

    ConnectionManager.register("default_conn", conn1, is_default=True)

    # 不指定 key 时应该返回默认连接
    retrieved = ConnectionManager.get()
    assert retrieved == conn1

    # 清理
    ConnectionManager.close_all()


def test_connection_manager_get_nonexistent():
    """测试获取不存在的连接"""
    with pytest.raises(ValueError, match="未找到标识符"):
        ConnectionManager.get("nonexistent_key")


def test_connection_manager_get_without_default():
    """测试没有默认连接时获取"""
    # 清理之前的连接
    ConnectionManager._connections.clear()
    ConnectionManager._default_key = None

    with pytest.raises(RuntimeError, match="没有设置默认数据库连接"):
        ConnectionManager.get()


def test_connection_manager_get_default(sample_connections):
    """测试获取默认连接"""
    conn1, _, _ = sample_connections

    ConnectionManager.register("default", conn1, is_default=True)

    default_conn = ConnectionManager.get_default()
    assert default_conn == conn1

    # 清理
    ConnectionManager.close_all()


def test_connection_manager_get_default_none():
    """测试没有默认连接时"""
    # 清理
    ConnectionManager._connections.clear()
    ConnectionManager._default_key = None

    assert ConnectionManager.get_default() is None


def test_connection_manager_list_keys(sample_connections):
    """测试列出所有连接"""
    conn1, conn2, conn3 = sample_connections

    ConnectionManager.register("conn1", conn1)
    ConnectionManager.register("conn2", conn2)
    ConnectionManager.register("conn3", conn3)

    keys = ConnectionManager.list_keys()
    assert isinstance(keys, list)
    assert len(keys) == 3
    assert set(keys) == {"conn1", "conn2", "conn3"}

    # 清理
    ConnectionManager.close_all()


def test_connection_manager_list_keys_empty():
    """测试列出连接（空）"""
    # 清理
    ConnectionManager._connections.clear()

    keys = ConnectionManager.list_keys()
    assert keys == []


def test_connection_manager_close_single(sample_connections):
    """测试关闭单个连接"""
    conn1, _, _ = sample_connections

    ConnectionManager.register("conn1", conn1)

    assert "conn1" in ConnectionManager.list_keys()

    ConnectionManager.close("conn1")

    assert "conn1" not in ConnectionManager.list_keys()


def test_connection_manager_close_default(sample_connections):
    """测试关闭默认连接"""
    conn1, _, _ = sample_connections

    ConnectionManager.register("default", conn1, is_default=True)
    assert ConnectionManager.get_default() == conn1

    ConnectionManager.close("default")

    assert ConnectionManager.get_default() is None


def test_connection_manager_close_nonexistent():
    """测试关闭不存在的连接"""
    # 不应该抛出异常
    ConnectionManager.close("nonexistent")


def test_connection_manager_close_all(sample_connections):
    """测试关闭所有连接"""
    conn1, conn2, conn3 = sample_connections

    ConnectionManager.register("conn1", conn1)
    ConnectionManager.register("conn2", conn2)
    ConnectionManager.register("conn3", conn3)

    assert len(ConnectionManager.list_keys()) == 3

    ConnectionManager.close_all()

    assert len(ConnectionManager.list_keys()) == 0
    assert ConnectionManager._default_key is None


def test_connection_manager_first_registration_is_default(sample_connections):
    """测试第一个注册的连接自动成为默认连接"""
    conn1, _, _ = sample_connections

    ConnectionManager.register("first", conn1)

    assert ConnectionManager.get_default() == conn1

    # 清理
    ConnectionManager.close_all()


def test_connection_manager_override_default(sample_connections):
    """测试覆盖默认连接"""
    conn1, conn2, _ = sample_connections

    ConnectionManager.register("first", conn1, is_default=True)
    assert ConnectionManager.get_default() == conn1

    ConnectionManager.register("second", conn2, is_default=True)
    assert ConnectionManager.get_default() == conn2

    # 清理
    ConnectionManager.close_all()


def test_connection_manager_is_singleton_class():
    """测试 ConnectionManager 是类级别的单例"""
    ConnectionManager._connections.clear()

    # 在不同的地方使用应该共享同一个连接字典
    conn = SQLiteConnection(database=":memory:")
    ConnectionManager.register("test", conn)

    keys = ConnectionManager.list_keys()
    assert len(keys) == 1

    conn.close()
    ConnectionManager.close_all()
