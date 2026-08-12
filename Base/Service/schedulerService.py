from Base.Client.schedulerClient import TaskSchedulerClient
from Base.Repository.base.connectionManager import ConnectionManager

base_module_scheduler_client = TaskSchedulerClient(
        mysql_url=ConnectionManager.get("base_module").get_connection_url()
    )

default_scheduler_client = TaskSchedulerClient(
        mysql_url=ConnectionManager.get_default().get_connection_url(),
        table_name="apscheduler_jobs"
    )

def get_base_module_scheduler_client():
    """
    获取Base模块的调度器客户端
    :return:
    """
    return base_module_scheduler_client


def get_default_scheduler_client():
    """
    获取默认(Setting 中配置的数据库DB)的调度器客户端
    :return:
    """
    return default_scheduler_client