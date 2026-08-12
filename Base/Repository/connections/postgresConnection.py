import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional, List, Dict, Any
import logging

from Base.Repository.base.baseConnection import BaseConnection

logger = logging.getLogger(__name__)


class PostgreSQLConnection(BaseConnection):
    """
    PostgreSQL 数据库连接实现

    继承自 BaseConnection，实现 PostgreSQL 特定的连接管理。
    """

    def __init__(
        self,
        host: str,
        user: str,
        password: str,
        database: str,
        port: int = 5432,
        charset: str = "utf8",
        mincached: int = 2,
        maxcached: int = 10,
        maxconnections: int = 20,
        blocking: bool = False,
    ):
        # 调用父类初始化
        super().__init__(
            host=host,
            user=user,
            password=password,
            database=database,
            port=port,
            charset=charset,
            mincached=mincached,
            maxcached=maxcached,
            maxconnections=maxconnections,
            blocking=blocking,
        )
        # PostgreSQL 特定配置
        self.config["cursor_factory"] = RealDictCursor
        self.config["type"] = 'postgresql'

        # 初始化连接池
        self._ensure_database_exists()
        self._create_connection_pool()

    # ======================
    # PostgreSQL 特定实现
    # ======================

    def _ensure_database_exists(self):
        """如果数据库不存在，则自动创建（PostgreSQL 实现）"""
        db_name = self.config["database"]

        try:
            # 连接到默认数据库 postgres
            temp_conn = psycopg2.connect(
                host=self.config["host"],
                user=self.config["user"],
                password=self.config["password"],
                port=self.config["port"],
                dbname="postgres",
                cursor_factory=RealDictCursor,
                autocommit=True,
            )
            with temp_conn.cursor() as cur:
                # 检查数据库是否存在（PostgreSQL 语法）
                cur.execute(
                    "SELECT 1 FROM pg_database WHERE datname = %s",
                    (db_name,)
                )
                exists = cur.fetchone() is not None

                if not exists:
                    logger.info(f"数据库 {db_name} 不存在，正在创建...")
                    cur.execute(f"CREATE DATABASE \"{db_name}\" ENCODING 'UTF8'")
                    logger.info(f"数据库 {db_name} 创建成功")
                else:
                    logger.debug(f"数据库 {db_name} 已存在")

            temp_conn.close()
        except Exception as e:
            logger.error(f"检查/创建数据库 {db_name} 失败：{e}")
            raise

    def _create_connection_pool(self):
        """创建连接池（PostgreSQL 实现）"""
        try:
            from dbutils.pooled_db import PooledDB
            # PostgreSQL 需要使用 psycopg2.pool，但为了兼容性，这里简化处理
            # 实际生产环境建议使用 psycopg2.pool.ThreadedConnectionPool
            logger.warning("PostgreSQL 连接池暂未完全实现，使用单连接模式")
            self._connection_pool = None
        except ImportError:
            logger.warning("DBUtils 未安装，使用单连接模式。请执行: pip install DBUtils")
            self._connection_pool = None

    def _get_raw_connection(self):
        """获取原生数据库连接（PostgreSQL 实现）"""
        return psycopg2.connect(
            cursor_factory=RealDictCursor,
            dbname=self.config["database"],
            user=self.config["user"],
            password=self.config["password"],
            host=self.config["host"],
            port=self.config["port"],
        )

    # ======================
    # PostgreSQL 便捷方法
    # ======================

    def table_exists(self, table_name: str) -> bool:
        """检查表是否存在（PostgreSQL 特定语法）"""
        sql = """
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = %s
        """
        result = self.execute_query(sql, (table_name,))
        return len(result) > 0


# 向后兼容别名
PostgresConnection = PostgreSQLConnection
