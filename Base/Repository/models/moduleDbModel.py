from Base.Config.setting import settings
from Base.Repository.base.baseDBModel import BaseDBModel
from Base.Repository.base.connectionManager import ConnectionManager


class BaseModuleDBModel(BaseDBModel):
    """
    Base模块数据库模型基类
    """
    _db_connection = ConnectionManager.get('base_module')