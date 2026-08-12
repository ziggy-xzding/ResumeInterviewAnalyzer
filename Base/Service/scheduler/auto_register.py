import os
import sys
import importlib
import logging
from pathlib import Path
from typing import List, Dict, Any, Callable, Optional
import inspect

# 项目相关导入
from Base.Service.schedulerService import get_base_module_scheduler_client
from Base.RicUtils.pathUtils import find_project_root

logger = logging.getLogger(__name__)


def scan_and_register_scheduler_tasks(force_reload: bool = False) -> Dict[str, Any]:
    """
    扫描 Base/Service/scheduler 目录下的所有文件并自动注册定时任务

    Args:
        force_reload: 是否强制重新加载模块

    Returns:
        扫描和注册结果的字典
    """
    logger.info("🚀 开始扫描 Base/Service/scheduler 目录下的定时任务...")

    # 确定要扫描的目录
    project_root = find_project_root()
    scheduler_dir = project_root / "Base" / "Service" / "scheduler"

    if not scheduler_dir.exists():
        logger.error(f"调度器目录不存在: {scheduler_dir}")
        return {
            'success': False,
            'error': f'目录不存在: {scheduler_dir}',
            'registered_count': 0,
            'tasks': []
        }

    logger.info(f"🔍 扫描目录: {scheduler_dir}")

    registered_tasks = []
    errors = []
    total_files = 0

    # 遍历目录下的所有Python文件
    for py_file in scheduler_dir.glob("*.py"):
        # 跳过当前文件自身
        if py_file.name == "auto_register.py":
            continue

        total_files += 1
        logger.info(f"📄 处理文件: {py_file.name}")

        try:
            # 将文件名转换为模块名
            module_name = f"Base.Service.scheduler.{py_file.stem}"

            # 导入模块
            if force_reload and module_name in sys.modules:
                importlib.reload(sys.modules[module_name])

            module = importlib.import_module(module_name)

            # 查找并注册定时任务
            file_tasks = _register_module_tasks(module)
            registered_tasks.extend(file_tasks)

            if file_tasks:
                logger.info(f"  ✅ 注册了 {len(file_tasks)} 个任务")
            else:
                logger.info(f"  ℹ️  未找到定时任务")

        except Exception as e:
            error_msg = f"处理文件 {py_file.name} 失败: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)

    result = {
        'success': len(errors) == 0,
        'total_files': total_files,
        'registered_count': len(registered_tasks),
        'tasks': registered_tasks,
        'errors': errors
    }

    logger.info(f"✅ 扫描完成! 处理了 {total_files} 个文件，注册了 {len(registered_tasks)} 个任务")
    if errors:
        logger.warning(f"⚠️  发现 {len(errors)} 个错误")

    return result


def _register_module_tasks(module) -> List[Dict[str, Any]]:
    """
    注册模块中的定时任务

    Args:
        module: 要扫描的模块

    Returns:
        已注册任务的列表
    """
    registered_tasks = []
    scheduler_client = get_base_module_scheduler_client()

    # 遍历模块的所有属性
    for name, obj in inspect.getmembers(module):
        # 检查是否为函数且有scheduled装饰器
        if (inspect.isfunction(obj) and
                hasattr(obj, '__wrapped__') and
                hasattr(obj.__wrapped__, 'scheduled')):

            try:
                # 获取装饰器配置
                schedule_config = getattr(obj.__wrapped__, 'scheduled')

                # 注册任务
                job_id = scheduler_client.add_job(
                    func=obj,
                    **schedule_config
                )

                task_info = {
                    'name': name,
                    'module': module.__name__,
                    'job_id': job_id,
                    'config': schedule_config
                }

                registered_tasks.append(task_info)
                logger.debug(f"注册任务: {name} (ID: {job_id})")

            except Exception as e:
                logger.error(f"注册任务 {name} 失败: {str(e)}")
                continue

    return registered_tasks


def get_scheduler_status() -> Dict[str, Any]:
    """
    获取调度器状态信息

    Returns:
        调度器状态信息
    """
    try:
        scheduler_client = get_base_module_scheduler_client()
        jobs = scheduler_client.get_jobs()

        return {
            'running': hasattr(scheduler_client.scheduler, 'running') and scheduler_client.scheduler.running,
            'total_jobs': len(jobs),
            'jobs': [
                {
                    'id': job['id'],
                    'function': job['func'],
                    'trigger': job['trigger'],
                    'next_run': str(job['next_run_time']) if job['next_run_time'] else 'N/A'
                }
                for job in jobs
            ]
        }
    except Exception as e:
        logger.error(f"获取调度器状态失败: {str(e)}")
        return {'error': str(e)}


# 便捷函数
def auto_register_all_scheduler() -> Dict[str, Any]:
    """
    自动注册所有调度器任务的便捷函数
    """
    return scan_and_register_scheduler_tasks()


# 使用示例
if __name__ == "__main__":


    print("🤖 自动注册 Base/Service/scheduler 目录下的定时任务")
    print("=" * 50)

    # 执行自动注册
    result = auto_register_all_scheduler()

    print(f"\n📊 注册结果:")
    print(f"  处理文件数: {result['total_files']}")
    print(f"  注册任务数: {result['registered_count']}")
    print(f"  执行状态: {'✅ 成功' if result['success'] else '❌ 失败'}")

    if result['tasks']:
        print(f"\n📋 已注册的任务:")
        for task in result['tasks']:
            print(f"  • {task['name']} (ID: {task['job_id']})")

    if result['errors']:
        print(f"\n❌ 错误信息:")
        for error in result['errors']:
            print(f"  • {error}")

    # 显示当前调度器状态
    print(f"\n⚙️  调度器状态:")
    status = get_scheduler_status()
    if 'error' not in status:
        print(f"  运行状态: {'运行中' if status['running'] else '已停止'}")
        print(f"  任务总数: {status['total_jobs']}")
    else:
        print(f"  获取状态失败: {status['error']}")
