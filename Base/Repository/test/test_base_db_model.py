"""
BaseDBModel 测试
"""

import pytest
from Base.Repository.base.baseDBModel import BaseDBModel
from Base.Repository.connections.mysqlConnection import MySQLConnection
from typing import Optional, ClassVar


@pytest.fixture
def test_db():
    """创建测试数据库"""
    db = MySQLConnection(
        host="localhost",
        user="root",
        password="root",
        database="test_base_db_model",
        port=3306,
        charset="utf8mb4",
        mincached=0,
        maxcached=0,
        maxconnections=1,
        blocking=False
    )
    yield db
    db.close()


@pytest.fixture
def user_model(test_db):
    """创建用户模型（测试自动建表）"""
    class User(BaseDBModel):
        table_alias: ClassVar[str] = "users"
        create_table_sql = """
            CREATE TABLE users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(255) UNIQUE,
                age INT
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
        id: Optional[int] = None
        name: str
        email: str
        age: Optional[int] = None

    User.set_db_connection(test_db)
    return User


# ========== 表相关测试 ==========

def test_table_name():
    """测试表名生成"""
    class User(BaseDBModel):
        table_alias: ClassVar[str] = "my_users"
        id: Optional[int] = None
        name: str

    assert User.get_table_name() == "my_users"

    class UserProfile(BaseDBModel):
        id: Optional[int] = None
        name: str

    assert UserProfile.get_table_name() == "user_profile"


def test_auto_create_table(user_model):
    """测试自动创建表"""
    user = user_model(name="Alice", email="alice@example.com")
    user_id = user.save()

    assert user_id is not None
    assert user_model.table_exists() is True


def test_table_exists(user_model):
    """测试检查表是否存在"""
    assert user_model.table_exists() is True

    class NonExistent(BaseDBModel):
        table_alias: ClassVar[str] = "non_existent_table"
        id: Optional[int] = None
        name: str

    NonExistent.set_db_connection(user_model.get_db_connection())
    assert NonExistent.table_exists() is False


# ========== CRUD 测试 ==========

def test_save_insert(user_model):
    """测试插入"""
    user = user_model(name="Bob", email="bob@example.com", age=30)
    user_id = user.save()

    assert user_id is not None
    assert user.id == user_id


def test_save_update(user_model):
    """测试更新"""
    user = user_model(name="Charlie", email="charlie@example.com", age=35)
    user.save()

    user.age = 36
    user.save()

    updated = user_model.get_by_id(user.id)
    assert updated.age == 36


def test_update_fields(user_model):
    """测试更新指定字段"""
    user = user_model(name="David", email="david@example.com", age=40)
    user.save()

    user.update(age=41, email="david_new@example.com")

    updated = user_model.get_by_id(user.id)
    assert updated.age == 41
    assert updated.email == "david_new@example.com"
    assert updated.name == "David"


def test_get_by_id(user_model):
    """测试根据 ID 查询"""
    user = user_model(name="Eve", email="eve@example.com", age=25)
    user.save()

    found = user_model.get_by_id(user.id)
    assert found.name == "Eve"
    assert found.email == "eve@example.com"

    assert user_model.get_by_id(999999) is None


def test_find_by(user_model):
    """测试条件查询"""
    user_model(name="Alice", email="alice1@example.com", age=25).save()
    user_model(name="Alice", email="alice2@example.com", age=30).save()
    user_model(name="Bob", email="bob@example.com", age=25).save()

    assert len(user_model.find_by(name="Alice")) == 2
    assert len(user_model.find_by(age=25)) == 2
    assert len(user_model.find_by(name="Alice", age=30)) == 1


def test_find_one_by(user_model):
    """测试查询单条记录"""
    user_model(name="Frank", email="frank@example.com").save()

    user = user_model.find_one_by(email="frank@example.com")
    assert user is not None
    assert user.name == "Frank"

    assert user_model.find_one_by(email="nonexistent@example.com") is None


def test_get_all(user_model):
    """测试查询所有记录"""
    for i in range(3):
        user_model(name=f"User{i}", email=f"user{i}@example.com").save()

    users = user_model.get_all()
    assert len(users) == 3

    assert len(user_model.get_all(limit=2)) == 2


def test_delete(user_model):
    """测试删除"""
    user = user_model(name="Grace", email="grace@example.com")
    user.save()
    user_id = user.id

    assert user.delete() is True
    assert user_model.get_by_id(user_id) is None


def test_delete_by_id(user_model):
    """测试根据 ID 删除"""
    user = user_model(name="Henry", email="henry@example.com")
    user.save()
    user_id = user.id

    assert user_model.delete_by_id(user_id) is True
    assert user_model.get_by_id(user_id) is None


def test_count(user_model):
    """测试统计数量"""
    assert user_model.count() == 0

    for _ in range(3):
        user_model(name="Test", email="test@example.com").save()

    assert user_model.count() == 3


def test_to_dict(user_model):
    """测试转换为字典"""
    user = user_model(id=1, name="Test", email="test@example.com", age=25)
    result = user.to_dict()

    assert result["id"] == 1
    assert result["name"] == "Test"
    assert result["age"] == 25


# ========== 连接测试 ==========

def test_connection_priority(test_db):
    """测试连接优先级"""
    class TestModel(BaseDBModel):
        table_alias: ClassVar[str] = "test"
        create_table_sql = """
            CREATE TABLE test (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
        id: Optional[int] = None
        name: str

    # 全局连接
    BaseDBModel._default_db_connection = test_db

    # 类连接
    TestModel.set_db_connection(test_db)

    # 实例连接
    model = TestModel(name="test")
    model.set_connection(test_db)

    assert model.get_connection() == test_db
