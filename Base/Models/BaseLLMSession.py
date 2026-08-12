import logging
import uuid
from datetime import datetime
from typing import Optional, ClassVar, List

from pydantic import Field

from Base.Ai.base import UserMessages, AssistantMessages
from Base.Repository.models.moduleDbModel import BaseModuleDBModel

logger = logging.getLogger(__name__)


class BaseLLMSession(BaseModuleDBModel):
    """
    LLM 会话模型
    """
    table_alias: ClassVar[str] = "base_llm_session"
    create_table_sql: ClassVar[str] = f"""
    -- 创建会话表
    CREATE TABLE `{table_alias}` (
      `id` BIGINT(20) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
      `session_uuid` VARCHAR(64) NOT NULL COMMENT '会话唯一标识',
      `user_id` VARCHAR(64) NOT NULL COMMENT '用户 ID',
      `title` VARCHAR(255) COMMENT '会话标题',
      `session_desc` VARCHAR(500) COMMENT '会话简介',
      `model_name` VARCHAR(64) COMMENT '模型名称',
      `agent_id` VARCHAR(64) COMMENT 'Agent ID',
      `ai_summary` TEXT COMMENT 'AI汇总内容',
      `tags` VARCHAR(500) COMMENT '内容标签，多个用逗号分隔',
      `update_logs` VARCHAR(500) COMMENT '上次更新日志',
      `last_handle_id` BIGINT(20) DEFAULT 0 COMMENT '上次处理到的对话ID',
      `create_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
      `update_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
      PRIMARY KEY (`id`),
      UNIQUE KEY `uk_session_uuid` (`session_uuid`),
      KEY `idx_create_at` (`create_at`),
      KEY `idx_update_at` (`update_at`),
      KEY `idx_title` (`title`(20))
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='聊天会话表';

    """

    # 字段定义
    id: Optional[int] = Field(None, description="主键ID")
    session_uuid: Optional[str] = Field(None, description="会话唯一标识")
    user_id: Optional[str] = Field(None, description="用户ID")
    title: Optional[str] = Field(None, description="会话标题")
    session_desc: Optional[str] = Field(None, description="会话简介")
    model_name: Optional[str] = Field(None, description="模型名称")
    agent_id: Optional[str] = Field(None, description="Agent ID")
    ai_summary: Optional[str] = Field(None, description="AI汇总内容")
    tags: Optional[str] = Field(None, description="内容标签，多个用逗号分隔")
    update_logs: Optional[str] = Field(None, description="上次更新日志")
    last_handle_id: Optional[int] = Field(0, description="上次处理到的对话ID")
    create_at: Optional[datetime] = Field(None, description="创建时间")
    update_at: Optional[datetime] = Field(None, description="更新时间")

    def get_tags_list(self) -> List[str]:
        """
        获取标签列表

        Returns:
            标签列表
        """
        if not self.tags:
            return []
        return [tag.strip() for tag in self.tags.split(',') if tag.strip()]

    def set_tags_list(self, tags: List[str]):
        """
        设置标签列表

        Args:
            tags: 标签列表
        """
        self.tags = ','.join(tags)

    @classmethod
    def get_by_session_uuid(cls, session_uuid: str):
        """
        根据 session_uuid 获取会话记录

        Args:
            session_uuid: 会话唯一标识

        Returns:
            会话记录对象，未找到返回 None
        """
        try:
            cls._ensure_table_exists()
            result = cls.find_by(session_uuid=session_uuid, limit=1)
            return result[0] if result else None
        except Exception as e:
            logger.error(f"get_by_session_uuid({session_uuid}) 失败：{str(e)}")
            return None

    @classmethod
    def get_user_last_session(cls, user_id: str, session_id: str = None):
        """
        获取用户的最新会话
        Args:
            user_id: 用户ID
            session_id: 会话ID
        Returns:
            会话记录对象，未找到返回 None
        """
        try:
            cls._ensure_table_exists()
            find_by_filter = {"session_uuid": session_id, "user_id": user_id,
                      "order_by": "update_at", "order": "DESC", "limit": 1}
            if not session_id:
                find_by_filter.pop("session_uuid")
            result = cls.find_by(**find_by_filter)
            if not result:
                return cls.get_or_create_session(user_id=user_id)
            return result[0] if result else None
        except Exception as e:
            logger.error(f"get_user_last_session({user_id}) 失败：{str(e)}",exc_info= True)
            return None

    @classmethod
    def get_sessions_by_user(cls, user_id: str, limit: int = 20, offset: int = 0):
        """
        获取用户的会话列表

        Args:
            user_id: 用户ID
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            会话记录列表
        """
        try:
            cls._ensure_table_exists()
            return cls.find_by(
                user_id=user_id,
                limit=limit,
                offset=offset,
                order_by="update_at",
                order="DESC"
            )
        except Exception as e:
            logger.error(f"get_sessions_by_user({user_id}) 失败：{str(e)}")
            return []

    def update_last_handle_id(self, conversation_id: int):
        """
        更新上次处理的对话ID

        Args:
            conversation_id: 对话记录ID
        """
        self.last_handle_id = conversation_id
        self.save()

    def update_ai_summary(self, summary: str):
        """
        更新AI汇总内容

        Args:
            summary: 汇总内容
        """
        self.ai_summary = summary
        self.save()

    @classmethod
    def get_or_create_session(cls, session_uuid: str = None, user_id: str = None, title: str = None, **kwargs):
        """
        获取或创建会话

        Args:
            session_uuid: 会话唯一标识
            title: 会话标题（创建时使用）
            user_id: 用户ID
            **kwargs: 其他字段

        Returns:
            会话记录对象
        """
        if session_uuid:
            session = cls.get_by_session_uuid(session_uuid)
            if session:
                return session
        # 创建新会话
        session = cls(
            session_uuid=uuid.uuid4().hex,
            user_id=user_id,
            title=title or "新会话",
            **kwargs
        )
        session.save()
        return session


    def to_messages(self):
        """
        转换成消息列表
        """
        return [
            UserMessages(prompt="帮我总结一下此会话中我们之前讨论的内容"),
            AssistantMessages(prompt=self.ai_summary)
        ]


if __name__ == '__main__':
    # 创建表
    res = BaseLLMSession.get_user_last_session("liujie")
    print(f"{res}")
