from datetime import datetime
from typing import Optional, ClassVar
import json

from pydantic import Field

from Base.Ai.base import AssistantMessages, UserMessages
from Base.Repository.models.moduleDbModel import BaseModuleDBModel


class BaseLLMConversationModel(BaseModuleDBModel):
    """
    LLM 对话记录模型
    """
    table_alias: ClassVar[str] = "base_llm_conversation"
    create_table_sql: ClassVar[str] = f"""
                    CREATE TABLE `{table_alias}` (
                    -- 核心字段
                    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
                    `session_id` VARCHAR(64) COMMENT '会话ID',
                    `user_id` VARCHAR(64) COMMENT '用户ID',

                    -- 对话内容
                    `question` VARCHAR(2000) NOT NULL COMMENT '用户提问',
                    `rewrite_question` VARCHAR(2000) COMMENT '改写后问题',
                    `answer` TEXT COMMENT 'AI 回答',
                    `context` TEXT COMMENT '完整上下文（JSON 格式或拼接文本）',

                    -- 模型与模式
                    `ai_model` VARCHAR(100) COMMENT 'AI 模型名称',
                    `ai_agent` VARCHAR(100) COMMENT 'AI Agent/助手名称',
                    `stream_mode` VARCHAR(20) DEFAULT '0' COMMENT '交互模式：0-非流式，1-流式，2-深度思考，3-embedding，4-asr，5-ocr',

                    -- 状态与错误
                    `status` VARCHAR(20) DEFAULT 'success' COMMENT '状态：success|failed|timeout',
                    `error_msg` TEXT COMMENT '错误信息',
                    `source` VARCHAR(50) COMMENT '请求来源：web|app|api|plugin',

                    -- 性能与时间
                    `duration_ms` INT UNSIGNED COMMENT '总耗时（毫秒）',
                    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

                    -- 主键与索引
                    PRIMARY KEY (`id`),
                    KEY `idx_session_id` (`session_id`),
                    KEY `idx_user_id` (`user_id`),
                    KEY `idx_created_at` (`created_at`),
                    KEY `idx_ai_model` (`ai_model`),
                    KEY `idx_status` (`status`),
                    KEY `idx_source` (`source`)

                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='LLM 对话记录表';
                """

    # 字段定义
    id: Optional[int] = Field(None, description="主键ID")
    session_id: Optional[str] = Field(None, description="会话ID")
    user_id: Optional[str] = Field(None, description="用户ID")
    question: str = Field('', description="用户提问")
    rewrite_question: Optional[str] = Field('', description="改写后问题")
    answer: Optional[str] = Field(None, description="AI 回答")
    context: Optional[str] = Field(None, description="完整上下文（JSON 格式或拼接文本）")
    ai_model: Optional[str] = Field(None, description="AI 模型名称")
    ai_agent: Optional[str] = Field(None, description="AI Agent/助手名称")
    stream_mode: str = Field('0', description="交互模式：0-非流式，1-流式，2-深度思考，3-embedding，4-asr，5-ocr")
    status: str = Field('success', description="状态：success|failed|timeout")
    error_msg: Optional[str] = Field(None, description="错误信息")
    source: Optional[str] = Field(None, description="请求来源：web|app|api|plugin")
    duration_ms: Optional[int] = Field(None, description="总耗时（毫秒）")
    created_at: Optional[datetime] = Field(None, description="创建时间")

    def to_messages(self, is_rewrite=False):
        return [UserMessages(prompt=self.question if not is_rewrite else self.rewrite_question or self.question), AssistantMessages(prompt=self.answer[:100] if self.answer else self.error_msg + '...')]


    @property
    def is_stream(self):
        return self.stream_mode == "1" or self.stream_mode == "2"

    @property
    def get_answer(self):
        """安全地获取答案内容"""
        if not self.answer:
            return ""
        
        # 首先尝试直接返回字符串
        if isinstance(self.answer, str):
            # 检查是否是有效的 JSON 字符串
            if self.answer.strip().startswith('{') and self.answer.strip().endswith('}'):
                try:
                    parsed = json.loads(self.answer)
                    if isinstance(parsed, dict) and 'content' in parsed:
                        return parsed['content']
                    return self.answer
                except (json.JSONDecodeError, Exception):
                    # JSON 解析失败，直接返回原文
                    return self.answer
            else:
                # 普通字符串直接返回
                return self.answer
        
        # 其他类型转换为字符串
        return str(self.answer)

    @staticmethod
    def get_last_n_turns_context(user_id: str, session_id: str, n: int = 5):
        """
        获取最近 n 轮对话的上下文
        """
        context = BaseLLMConversationModel.find_by(user_id=user_id, session_id=session_id, limit=n,
                                                   order_by="created_at", order="DESC")
        return context

    @staticmethod
    def get_after_id(last_id: int,session_id: str, user_id: str):
        """
        获取 大于 某个ID  之后的 近50 条
        """
        db = BaseLLMConversationModel.get_db_connection()
        sql = f"SELECT * FROM {BaseLLMConversationModel.table_alias} WHERE id > %s and session_id = %s and user_id = %s ORDER BY id ASC LIMIT 50"
        params = (last_id, session_id, user_id)
        return db.execute(sql, params)

    @staticmethod
    def db_res_2_messages(context: list, is_rewrite=False):
        """
        DB 检索的会话结果 转换为 messages
        """
        res = [i.to_messages(is_rewrite) for i in context if i]
        res.reverse()
        return [item for sublist in res for item in sublist]

if __name__ == '__main__':
    res1 = BaseLLMConversationModel.get_after_id(10,'string','string')
    print(res1)
