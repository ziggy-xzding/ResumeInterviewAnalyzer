from datetime import datetime
from typing import Optional, ClassVar

from pydantic import Field

from Base.Repository.models.moduleDbModel import BaseModuleDBModel


class BaseEmailModels(BaseModuleDBModel):
    """
    邮件发送记录模型
    """
    table_alias: ClassVar[str] = "base_email_records"
    create_table_sql: ClassVar[str] = f"""
    CREATE TABLE {table_alias} (
        id INT AUTO_INCREMENT PRIMARY KEY,
        sender_email VARCHAR(255) NOT NULL COMMENT '发件人邮箱',
        receiver_emails TEXT NOT NULL COMMENT '收件人邮箱列表，逗号分隔',
        receiver_info VARCHAR(500) NOT NULL COMMENT '收件人信息',
        email_type VARCHAR(20) NOT NULL COMMENT '邮件类型: normal/system',
        subject VARCHAR(500) NOT NULL COMMENT '邮件主题',
        body TEXT NOT NULL COMMENT '邮件正文',
        is_html TINYINT(1) DEFAULT 0 COMMENT '是否HTML格式: 0=纯文本, 1=HTML',
        smtp_server VARCHAR(100) DEFAULT 'smtp.qq.com' COMMENT 'SMTP服务器地址',
        smtp_port INT DEFAULT 465 COMMENT 'SMTP服务器端口',
        status VARCHAR(20) DEFAULT 'pending' COMMENT '发送状态: pending=待发送, success=成功, failed=失败',
        error_message TEXT COMMENT '错误信息',
        retry_count INT DEFAULT 0 COMMENT '重试次数',
        attachments TEXT COMMENT '附件信息(JSON格式)',
        inline_images TEXT COMMENT '内联图片信息(JSON格式)',
        priority INT DEFAULT 0 COMMENT '优先级，数字越大优先级越高',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
        sent_at TIMESTAMP NULL COMMENT '发送时间(成功时)',
        INDEX idx_status (status),
        INDEX idx_created_at (created_at),
        INDEX idx_priority (priority)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='邮件发送记录表'
    """

    id: Optional[int] = Field(None, description="主键ID")
    sender_email: str = Field('', description="发件人邮箱")
    receiver_emails: str = Field('', description="收件人邮箱列表，逗号分隔")
    receiver_info: str = Field('', description="收件人信息")
    email_type: str = Field('normal', description="邮件类型: normal/system")
    subject: str = Field('', description="邮件主题")
    body: str = Field('', description="邮件正文")
    is_html: bool = Field(False, description="是否HTML格式")
    smtp_server: str = Field("smtp.qq.com", description="SMTP服务器地址")
    smtp_port: int = Field(465, description="SMTP服务器端口")
    status: str = Field("pending", description="发送状态: pending/success/failed")
    error_message: Optional[str] = Field(None, description="错误信息")
    retry_count: int = Field(0, description="重试次数")
    attachments: Optional[str] = Field(None, description="附件信息(JSON格式)")
    inline_images: Optional[str] = Field(None, description="内联图片信息(JSON格式)")
    priority: int = Field(0, description="优先级，数字越大优先级越高")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    sent_at: Optional[datetime] = Field(None, description="发送时间")


if __name__ == '__main__':
    # 测试1：字段必填校验

    # 测试2：创建完整邮件记录
    print("\n=== 测试2：创建邮件记录 ===")
    _email = BaseEmailModels(

    )
    res = _email.find_by()
    print(f"✓ 邮件记录创建成功" + str(res))
    print(f"  发件人: {_email.sender_email}")
    print(f"  收件人: {_email.receiver_emails}")
    print(f"  主题: {_email.subject}")
    print(f"  状态: {_email.status}")
