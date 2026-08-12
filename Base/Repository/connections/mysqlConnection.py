import pymysql
from pymysql.cursors import DictCursor
import logging

from Base.Config.setting import settings
from Base.Repository.base.baseConnection import BaseConnection

logger = logging.getLogger(__name__)


class MySQLConnection(BaseConnection):
    """
    MySQL 数据库连接实现

    继承自 BaseConnection，实现 MySQL 特定的连接管理。
    """

    def __init__(
        self,
        host: str,
        user: str,
        password: str,
        database: str,
        port: int = 3306,
        charset: str = "utf8mb4",
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
        # MySQL 特定配置
        self.config["cursorclass"] = DictCursor
        self.config["type"] = 'mysql'

        # 初始化连接池（如果失败则记录日志但不抛出异常）
        try:
            self._ensure_database_exists()
            self._create_connection_pool()
        except Exception as e:
            logger.warning(f"MySQL 连接初始化失败，相关功能将无法持久化：{str(e)}")
            self._is_available = False

    # ======================
    # MySQL 特定实现
    # ======================

    def _ensure_database_exists(self):
        """如果数据库不存在，则自动创建（MySQL 实现），失败则记录日志"""
        db_name = self.config["database"]

        try:
            # 临时连接（不指定数据库）
            temp_conn = pymysql.connect(
                host=self.config["host"],
                user=self.config["user"],
                password=self.config["password"],
                port=self.config["port"],
                charset=self.config["charset"],
                cursorclass=DictCursor,
                autocommit=False,
            )
            with temp_conn.cursor() as cur:
                # 检查数据库是否存在（MySQL 语法）
                cur.execute(
                    "SELECT 1 FROM information_schema.schemata WHERE schema_name = %s",
                    (db_name,)
                )
                exists = cur.fetchone() is not None

                if not exists:
                    logger.info(f"数据库 {db_name} 不存在，正在创建...")
                    cur.execute(f"CREATE DATABASE `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                    temp_conn.commit()
                    logger.info(f"数据库 {db_name} 创建成功")
                else:
                    logger.debug(f"数据库 {db_name} 已存在")

            temp_conn.close()
        except Exception as e:
            logger.warning(f"检查/创建数据库 {db_name} 失败：{e}")
            # 标记连接为不可用
            self._is_available = False

    def _create_connection_pool(self):
        """创建连接池（MySQL 实现），失败则记录日志"""
        try:
            from dbutils.pooled_db import PooledDB

            # 创建使用 DictCursor 的 creator 函数
            def dict_cursor_creator():
                return pymysql.connect(
                    cursorclass=DictCursor,
                    **{k: v for k, v in self.config.items() if k not in ["cursorclass", "type"]}
                )

            # PooledDB 的参数：creator 或 (module, *args, **kwargs)
            # 使用 creator 函数来确保所有连接都使用 DictCursor
            self._connection_pool = PooledDB(
                creator=dict_cursor_creator,
                maxconnections=self.pool_config['maxconnections'],
                mincached=self.pool_config['mincached'],
                maxcached=self.pool_config['maxcached'],
                blocking=self.pool_config['blocking']
            )
            logger.info(f"MySQL 连接池创建成功: mincached={self.pool_config['mincached']}, maxconnections={self.pool_config['maxconnections']}")
        except ImportError:
            logger.warning("DBUtils 未安装，使用单连接模式。请执行: pip install DBUtils")
            self._connection_pool = None
        except Exception as e:
            logger.warning(f"创建 MySQL 连接池失败：{e}")
            self._connection_pool = None
            self._is_available = False

    def _get_raw_connection(self):
        """获取原生数据库连接（MySQL 实现）"""
        # 过滤掉 pymysql 不支持的参数
        connection_config = {
            k: v for k, v in self.config.items()
            if k not in ["cursorclass", "type"]
        }
        return pymysql.connect(
            cursorclass=DictCursor,
            autocommit=False,
            **connection_config
        )

    # ======================
    # MySQL 便捷方法
    # ======================

    def table_exists(self, table_name: str) -> bool:
        """检查表是否存在（MySQL 特定语法）"""
        sql = """
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = %s AND table_name = %s
        """
        result = self.execute(
            sql,
            (self.config["database"], table_name)
        )
        return len(result) > 0

    # ======================
    # 抽象方法实现
    # ======================

    def get_connection_url(self) -> str:
        """
        获取 MySQL 连接URL（遵循 SQLAlchemy 数据库URL格式）
        
        Returns:
            MySQL 连接URL字符串
            格式: "mysql+pymysql://user:password@host:port/database?charset=utf8mb4"
        
        Examples:
            >>> conn = MySQLConnection(...)
            >>> conn.get_connection_url()
            'mysql+pymysql://root:123456@localhost:3306/mydb?charset=utf8mb4'
        """
        from urllib.parse import quote_plus
        
        # 获取连接参数
        user = self.config["user"]
        password = self.config["password"]
        host = self.config["host"]
        port = self.config["port"]
        database = self.config["database"]
        charset = self.config["charset"]
        
        # URL编码密码（处理特殊字符）
        encoded_password = quote_plus(password)
        
        # 构建连接URL
        # 格式: mysql+pymysql://user:password@host:port/database?charset=utf8mb4
        url = f"mysql+pymysql://{user}:{encoded_password}@{host}:{port}/{database}?charset={charset}"
        
        logger.debug(f"MySQL 连接URL: {user}:***@{host}:{port}/{database}")
        return url


