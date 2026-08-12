from datetime import datetime
from typing import Callable, Optional, List, Dict, Any

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger


class TaskSchedulerClient:
    def __init__(
            self,
            mysql_url: str,
            table_name: str = 'base_apscheduler_jobs',
            timezone: str = 'Asia/Shanghai',
            executor_max_workers: int = 20,
            auto_start: bool = True
    ):
        """
        初始化调度客户端

        :param mysql_url: MySQL 连接字符串，例如：
                          "mysql+pymysql://user:password@host:port/dbname?charset=utf8mb4"
        :param timezone: 时区，默认上海
        :param executor_max_workers: 线程池最大线程数
        :param auto_start: 是否自动启动调度器
        """
        jobstores = {
            'default': SQLAlchemyJobStore(url=mysql_url, tablename=table_name)
        }
        executors = {
            'default': ThreadPoolExecutor(max_workers=executor_max_workers)
        }

        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            timezone=timezone
        )

        if auto_start:
            self.start()

    def start(self):
        """启动调度器"""
        if not self.scheduler.running:
            self.scheduler.start()
            print("✅ 调度器已启动")

    def shutdown(self, wait=True):
        """关闭调度器"""
        self.scheduler.shutdown(wait=wait)
        print("🛑 调度器已关闭")

    def add_job(
            self,
            func: Callable,
            trigger: str = 'interval',
            id: Optional[str] = None,
            **trigger_args
    ) -> str:
        """
        手动添加任务

        :param func: 要调度的函数（必须可被 pickle，且在模块顶层定义）
        :param trigger: 触发器类型 ('interval', 'cron', 'date')
        :param id: 任务唯一 ID，若不提供则用 func.__name__
        :param trigger_args: 触发器参数，如 seconds=10, cron表达式等
        :return: 任务 ID
        """
        job_id = id or func.__name__

        # 如果提供了 cron 参数，自动使用 CronTrigger
        if 'cron' in trigger_args:
            cron_expr = trigger_args.pop('cron')
            self.scheduler.add_job(
                func=func,
                trigger=CronTrigger.from_crontab(cron_expr),
                id=job_id,
                replace_existing=True,
                **trigger_args
            )
        else:
            self.scheduler.add_job(
                func=func,
                trigger=trigger,
                id=job_id,
                replace_existing=True,
                **trigger_args
            )
        return job_id

    def get_jobs(self) -> List[Dict[str, Any]]:
        """获取所有调度中的任务信息（可读格式）"""
        jobs = self.scheduler.get_jobs()
        result = []
        for job in jobs:
            result.append({
                'id': job.id,
                'func': job.func_ref,
                'trigger': str(job.trigger),
                'next_run_time': job.next_run_time,
                'args': job.args,
                'kwargs': job.kwargs,
                'pending': job.next_run_time is None  # 如果为 None 表示已暂停或未激活
            })
        return result

    def pause_job(self, job_id: str):
        """暂停任务"""
        self.scheduler.pause_job(job_id)

    def resume_job(self, job_id: str):
        """恢复任务"""
        self.scheduler.resume_job(job_id)

    def remove_job(self, job_id: str):
        """删除任务"""
        self.scheduler.remove_job(job_id)

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """获取单个任务信息"""
        job = self.scheduler.get_job(job_id)
        if not job:
            return None
        return {
            'id': job.id,
            'func': job.func_ref,
            'trigger': str(job.trigger),
            'next_run_time': job.next_run_time,
            'args': job.args,
            'kwargs': job.kwargs,
            'pending': job.next_run_time is None
        }

    def scheduled(
            self,
            id: Optional[str] = None,
            trigger: str = 'interval',
            **trigger_args
    ):
        """
        装饰器：用于注册函数为定时任务

        示例：
            @client.scheduled(seconds=30)
            def my_task():
                print("每30秒执行")

            @client.scheduled(cron="0 2 * * *")  # 每天凌晨2点
            def daily_clean():
                ...
        """

        def decorator(func: Callable) -> Callable:
            job_id = id or func.__name__
            self.add_job(func, trigger=trigger, id=job_id, **trigger_args)
            return func

        return decorator


if __name__ == '__main__':
    from Base.Repository.base.connectionManager import ConnectionManager

    client = TaskSchedulerClient(
        mysql_url=ConnectionManager.get("base_module").get_connection_url()
    )


    # 方式1：使用装饰器注册任务
    @client.scheduled(seconds=10, id='hello_task')
    def say_hello():
        print("Hello from scheduled task!")


    @client.scheduled(cron="*/5 * * * *", id='cron_task')  # 每5分钟
    def cron_job():
        print("Cron job executed at", datetime.now())


    # 方式2：手动注册
    def manual_task():
        print("Manual task running...")


    client.add_job(manual_task, trigger='interval', minutes=2, id='manual_2min')

    # 查看当前所有任务
    print("\n当前调度任务列表：")
    for job in client.get_jobs():
        print(f"ID: {job['id']}, 下次运行: {job['next_run_time']}, 触发器: {job['trigger']}")

    # 主程序保持运行（Web 应用中不需要这个）
    try:
        import time

        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        client.shutdown()
