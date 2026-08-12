import os

from dotenv import load_dotenv

from Base.Service.emailService import send_email
from Base.Config.setting import settings
from Base.RicUtils.dateUtils import get_current_date
from Wolin.service.base import service_logger

load_dotenv()

logger = service_logger

class EmailService:

    def __init__(self,receiver_emails: list[str] = None):
        self.sender_email = settings.email.sender_email
        self.receiver_emails = receiver_emails or ['your_email@qq.com']




    def send_emails_base(self,
                         subject:str,
                         email_content:str,
                         receiver_emails: list[str] = None,
                         receiver_info: str = None,
                         is_html:bool=False,
                         attachments= None,
                         inline_images=None):
        """
        发送邮件
        :param subject: 邮件标题
        :param email_content: 邮件内容
        :param receiver_emails: 收件人邮箱
        :param receiver_info: 收件人信息
        :param is_html:  是否是HTML格式
        :param attachments: 附件
        :param inline_images: 图片
        :return:
        """
        send_email(sender_email=self.sender_email,
                   receiver_emails=receiver_emails or self.receiver_emails,
                   receiver_info=receiver_info,
                   email_type='InterviewAnalysis',
                   subject=subject,
                   body=email_content,
                   is_html=is_html,
                   attachments=attachments,
                   inline_images=inline_images)

    def send_emails_4_ia(self,
                         user_name: str,
                         ia_id: str,
                         report_path: str,
                         user_email: list[str] | str,
                         ):
        name = user_name or '小伙伴'
        content = \
            f"""
                <html>
                <body>
                    <p><img src="cid:wolin" ></p>
                    <h1>{name},你好！</h1>
                    <p>这是一封由<b>Ziggy</b>发送的面试报告邮件（ID：{ia_id}）,请查收附件.</p>
                    <p>祝你今天愉快！</p>
                </body>
                </html>
            """
        try:
            self.send_emails_base(
                subject=f"面试报告 {get_current_date()}",
                email_content=content,
                receiver_emails=user_email,
                receiver_info=name,
                is_html=True,
                attachments=report_path,
                inline_images=[("Wolin/static/ziggy.jpg", "wolin")]
            )
            logger.info(f"邮件发送成功！ Receives_Email:{user_email}")
        except Exception as e:
            logger.error(f"邮件发送异常:{e}")

email_service = EmailService()

if __name__ == '__main__':

    email_service.send_emails_4_ia(user_name='刘硕',ia_id='123456',report_path='Wolin/static/report.pdf',user_email=['your_email@qq.com'])