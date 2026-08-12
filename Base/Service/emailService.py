from Base.Config.setting import settings
from Base.Client.emailClient import send_email as _send_email
from Base.Models.BaseEmailModel import BaseEmailModels
from datetime import datetime


def send_email(
        sender_email,
        receiver_emails,
        receiver_info,
        email_type,
        subject,
        body,
        sender_password=settings.email.password,
        smtp_server: str = 'smtp.qq.com',
        smtp_port: int = 465,
        is_html=False,
        attachments=None,  # 附件列表，每个元素是附件的路径
        inline_images=None,
        timeout: int = 30,  # SMTP 连接超时时间（秒）
        max_retries: int = 2  # 最大重试次数
):
    """
        持久化赋能的 邮件发送 封装函数。
        - 使用后会持久化到数据库中
        - 非侵入式,数据库连接不正常不影响正常运行逻辑，只会日志警告 数据库连接 存在问题
        - 如需绕过数据库持久化,请使用 原emailClient.send_email 函数

        Args:
            sender_email (str): 发件人邮箱地址。
            receiver_emails (list): 收件人邮箱地址列表。
            receiver_info: 收件人信息
            email_type: 邮件类型
            subject (str): 邮件主题。
            body (str): 邮件正文。
            sender_password (str): 发件人邮箱授权码或密码。
            smtp_server (str): SMTP服务器地址（例如：'smtp.qq.com'）。
            smtp_port (int): SMTP服务器端口（例如：465 或 587）。
            is_html (bool, optional): 邮件正文是否为HTML格式。默认为False (纯文本)。
            attachments (list, optional): 附件文件路径列表。默认为None。
            inline_images: 内联图片列表，每个元素是一个元组 (图片路径, Content-ID)
            timeout: SMTP 连接超时时间（秒）
            max_retries: 最大重试次数
        Returns:
            bool: 邮件发送成功返回True，否则返回False。
        """
    error_msg = None
    try:
        send_status = _send_email(sender_email, receiver_emails,
                                  subject, body, sender_password,
                                  smtp_server, smtp_port,
                                  is_html, attachments,
                                  inline_images, timeout,
                                  max_retries)
    except Exception as e:
        send_status = False
        error_msg = str(e)
    finally:
        if isinstance(receiver_emails, list):
            receiver_emails = ','.join(receiver_emails)
        email = BaseEmailModels(sender_email=sender_email,
                                receiver_emails=receiver_emails,
                                receiver_info=receiver_info,
                                email_type=email_type,
                                subject=subject,
                                body=body,
                                is_html=is_html,
                                attachments=str(attachments),
                                inline_images=str(inline_images),
                                status='success' if send_status else 'failed',
                                retry_count=max_retries,
                                smtp_server=smtp_server,
                                smtp_port=smtp_port,
                                error_message=error_msg,
                                created_at=datetime.now(),
                                sent_at=datetime.now()
                                )
        email.save()


if __name__ == '__main__':
    send_email("your_email@qq.com",
               ['your_email@qq.com'],
               '测试收件人',
               '测试',
               '表白情书',
               '杰哥不要啊',
               )
    send_email("your_email@qq.com",
               ['your_email@qq.com'],
               '测试收件人',
               '测试',
               '表白情书2',
               '杰哥不要啊2',
               )
