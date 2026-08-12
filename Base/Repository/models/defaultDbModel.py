from Base.Repository.base.baseDBModel import BaseDBModel
from Base.Repository.base.connectionManager import ConnectionManager


class DefaultDbModel(BaseDBModel):
    """
    ENV 配置中的 default_db 数据库模型基类
    """
    _db_connection = ConnectionManager.get_default()