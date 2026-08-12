from Base.Service.llmSessionService import ai_summary_4_all_session
from Base.Service.schedulerService import get_base_module_scheduler_client

client = get_base_module_scheduler_client()


@client.scheduled(cron="0 0 * * *", id='ai_summary_session_daily')
def ai_summary_session_scheduler():
    """
    AI生成 会话总结  每天零点执行
    """
    ai_summary_4_all_session()

# @client.scheduled(seconds=10, id='hello_task')
# def test():
#     import logging
#     logger = logging.getLogger(__name__)
#     logger.info("hello")