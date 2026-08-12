"""
数据库连接管理器
用于管理多个数据库连接，支持读写分离、分库分表等场景
"""

from typing import Dict, Optional
from Base.Repository.base.baseConnection import BaseConnection as DatabaseConnection
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """数据库连接管理器，支持多数据源/多数据库"""

    _connections: Dict[str, DatabaseConnection] = {}
    _default_key: Optional[str] = None

    @classmethod
    def register(cls, key: str, db_connection: DatabaseConnection, is_default: bool = False):
        """
        注册一个数据库连接

        Args:
            key: 连接的标识符（如 "read", "write", "order_db"）
            db_connection: 数据库连接对象
            is_default: 是否设置为默认连接
        """
        cls._connections[key] = db_connection
        if is_default or cls._default_key is None:
            cls._default_key = key
            logger.info(f"设置默认数据库连接: {key}")

        logger.debug(f"注册数据库连接: {key}")

    @classmethod
    def get(cls, key: Optional[str] = None) -> Optional[DatabaseConnection]:
        """
        获取数据库连接

        Args:
            key: 连接标识符，如果为 None 则返回默认连接

        Returns:
            DatabaseConnection: 数据库连接对象
        """
        if key is None:
            key = cls._default_key

        if key is None:
            raise RuntimeError("没有设置默认数据库连接")

        if key not in cls._connections:
            raise ValueError(f"未找到标识符为 '{key}' 的数据库连接")

        return cls._connections[key]

    @classmethod
    def get_default(cls) -> Optional[DatabaseConnection]:
        """获取默认数据库连接"""
        if cls._default_key is None:
            return None
        return cls._connections.get(cls._default_key)

    @classmethod
    def list_keys(cls) -> list:
        """列出所有已注册的连接标识符"""
        return list(cls._connections.keys())

    @classmethod
    def close_all(cls):
        """关闭所有连接"""
        for key, conn in cls._connections.items():
            try:
                conn.close()
                logger.debug(f"关闭数据库连接: {key}")
            except Exception as e:
                logger.error(f"关闭数据库连接失败 ({key}): {e}")
        cls._connections.clear()
        cls._default_key = None
        logger.info("所有数据库连接已关闭")

    @classmethod
    def close(cls, key: str):
        """关闭指定的连接"""
        if key in cls._connections:
            cls._connections[key].close()
            del cls._connections[key]
            logger.info(f"关闭数据库连接: {key}")

            if cls._default_key == key:
                cls._default_key = None


# 使用示例
"""
from Base.Repository.connections.mysqlConnection import MySQLConnection
from Base.Repository.base.baseDBModel import BaseDBModel
from Base.Repository.base.connectionManager import ConnectionManager

# 1. 创建多个数据库连接
read_db = MySQLConnection(
    host="read-host", user="root", password="pass",
    database="read_db", port=3306, charset="utf8mb4",
    mincached=1, maxcached=5, maxconnections=10, blocking=False
)
write_db = MySQLConnection(
    host="write-host", user="root", password="pass",
    database="write_db", port=3306, charset="utf8mb4",
    mincached=1, maxcached=5, maxconnections=10, blocking=False
)
order_db = MySQLConnection(
    host="order-host", user="root", password="pass",
    database="order_db", port=3306, charset="utf8mb4",
    mincached=1, maxcached=5, maxconnections=10, blocking=False
)

# 2. 注册到连接管理器
ConnectionManager.register("read", read_db, is_default=True)
ConnectionManager.register("write", write_db)
ConnectionManager.register("order", order_db)

# 3. 设置默认连接
BaseDBModel.set_default_db_connection(ConnectionManager.get_default())

# 4. 为特定模型类设置连接
User.set_db_connection(ConnectionManager.get("read"))
Order.set_db_connection(ConnectionManager.get("order"))

# 5. 为实例设置连接（支持读写分离）
user = User.get_by_id(1)
user.set_connection(ConnectionManager.get("write"))  # 写操作使用写库
user.update(name="李四")

# 6. 查询操作使用读库
user = User.get_by_id(1)  # 使用类的读库连接

# 7. 关闭所有连接
ConnectionManager.close_all()
"""
