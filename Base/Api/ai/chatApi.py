import json
import time
from functools import wraps
from typing import Optional, Any

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from Base.Ai.base import UserMessages
from Base.Ai.base.baseEnum import LLMTypeEnum
from Base.Ai.llms.qwenLlm import get_default_qwen_llm
from Base.Models.BaseLLMConversationModel import BaseLLMConversationModel
from Base.Models.BaseLLMSession import BaseLLMSession
from Base.RicUtils.httpUtils import HttpResponse
from Base.Service.MemoryV1Service import MemoryV1Service
from Base.Service.aiService import AiService
from Base.Service.llmConversationService import save_conversation_from_db_2_vdb


def persist_conversation(auto_save_vdb: bool = True, is_rewriting: bool = True):
    """
    装饰器：自动持久化对话记录

    Args:
        auto_save_vdb: 是否自动保存到向量数据库
        is_rewriting: 是否问题改写
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 获取参数
            params = kwargs.get('params') or (args[0] if args else None)

            if not params:
                return func(*args, **kwargs)

            rewrite_question = ''
            # 创建会话记录
            llm = get_default_qwen_llm()
            session = BaseLLMSession.get_user_last_session(params.user_id, params.session_id)
            conversation = params.to_log_instance()
            conversation.ai_model = llm.model_name
            conversation.source = "base_chat_api"
            conversation.session_id = session.session_uuid
            if is_rewriting:
                rewrite_question = AiService.rewrite_question(question=params.question, user_id=params.user_id,
                                                              session_id=params.session_id)
                conversation.rewrite_question = rewrite_question
            context = MemoryV1Service.get_simple_memory(
                question=rewrite_question or params.question,
                user_id=params.user_id,
                session_id=session.session_uuid or params.session_id
            )
            kwargs.get('params').messages = context + [UserMessages(prompt=params.question)]
            conversation.context = str(context)

            # 记录开始时间
            start_time = time.time()

            try:
                # 执行原始函数
                result = func(*args, **kwargs)

                # 如果是流式响应，需要特殊处理
                if params.is_stream:
                    # 包装流式响应生成器
                    original_generator = result.body_iterator

                    async def wrapped_generator():
                        content_parts = []
                        reasoning_parts = []  # 专门收集思考内容
                        answer_parts = []  # 专门收集答案内容
                        try:
                            # 先完成流式输出
                            async for chunk in original_generator:
                                # 根据 chunk 类型进行处理
                                if isinstance(chunk, dict):
                                    # 如果是字典类型（Qwen thinking 模式）
                                    chunk_type = chunk.get('type', 'content')
                                    chunk_content = chunk.get('content', '')

                                    # 分别收集不同类型的內容
                                    if chunk_type == 'reasoning':
                                        reasoning_parts.append(chunk_content)
                                    else:  # 'content' 或其他类型
                                        answer_parts.append(chunk_content)

                                    sse_data = f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                                    content_parts.append(chunk_content)
                                    yield sse_data.encode("utf-8")  # 必须是 bytes

                                elif isinstance(chunk, str):
                                    # 如果是字符串类型（普通流式输出）
                                    answer_parts.append(chunk)
                                    content_parts.append(chunk)
                                    sse_data = f"data: {chunk}\n\n"
                                    yield sse_data.encode("utf-8")

                                elif isinstance(chunk, bytes):
                                    # 如果已经是 bytes 类型
                                    decoded_chunk = chunk.decode("utf-8", errors="ignore")
                                    answer_parts.append(decoded_chunk)
                                    content_parts.append(decoded_chunk)
                                    yield chunk
                                else:
                                    # 其他类型转换为字符串处理
                                    chunk_str = str(chunk)
                                    answer_parts.append(chunk_str)
                                    content_parts.append(chunk_str)
                                    sse_data = f"data: {chunk_str}\n\n"
                                    yield sse_data.encode("utf-8")

                            # 流式输出完全结束后再进行持久化
                            try:
                                if params.is_thinking:
                                    # 思考模式：分别保存思考过程和答案
                                    full_content = {
                                        'reasoning': ''.join(reasoning_parts),
                                        'content': ''.join(answer_parts)
                                    }
                                    conversation.answer = json.dumps(full_content, ensure_ascii=False,
                                                                     separators=(',', ':'))
                                else:
                                    # 普通模式：只保存答案
                                    conversation.answer = ''.join(answer_parts)

                                conversation.duration_ms = int((time.time() - start_time) * 1000)
                                conversation.save()
                                if auto_save_vdb:
                                    save_conversation_from_db_2_vdb(conversation)

                            except Exception as save_error:
                                logger = __import__('logging').getLogger(__name__)
                                logger.error(f"流式结束后保存对话记录失败：{str(save_error)}")
                                # 持久化异常不影响流式输出
                                pass

                        except Exception as e:
                            logger = __import__('logging').getLogger(__name__)
                            logger.error(f"流式处理异常：{str(e)}")
                            raise

                    # 创建新的 StreamingResponse
                    result.body_iterator = wrapped_generator()
                    return result
                else:
                    result_str = result.data if isinstance(result, HttpResponse) else result
                    # 非流式响应直接保存
                    conversation.answer = result_str if isinstance(result_str, str) else str(result_str)
                    conversation.duration_ms = int((time.time() - start_time) * 1000)
                    conversation.save()
                    if auto_save_vdb:
                        save_conversation_from_db_2_vdb(conversation)
                    return result

            except Exception as e:
                # 异常时也记录错误信息
                conversation.status = 'failed'
                conversation.error_msg = str(e)
                conversation.duration_ms = int((time.time() - start_time) * 1000)
                conversation.save()
                raise

        return wrapper

    return decorator


class ChatParams(BaseModel):
    question: str = Field(..., description="用户问题")
    user_id: Optional[str] = Field(None, description="用户标识")
    model_type: LLMTypeEnum = Field(LLMTypeEnum.QWEN, description="模型类型")
    session_id: Optional[str] = Field(None, description="会话标识")
    is_stream: bool = Field(False, description="是否流式输出")
    is_thinking: bool = Field(False, description="是否思考")
    is_online_search: bool = Field(False, description="是否在线搜索")
    invoke_params: Optional[dict] = Field({}, description="调用参数")
    messages: Optional[list] = Field(None, description="消息列表")

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        if self.is_thinking:
            self.is_stream = True

    def to_log_instance(self) -> BaseLLMConversationModel:
        return BaseLLMConversationModel(
            question=self.question,
            user_id=self.user_id,
            session_id=self.session_id,
            ai_model=self.model_type.value,
            stream_mode="1" if self.is_stream else "0"
        )


router = APIRouter()


@router.post("/chat-v1")
@persist_conversation(auto_save_vdb=True)
def chat(params: ChatParams):
    """
    对话接口
    - 支持流式输出（is_stream=True）
    - 支持思考模式（is_thinking=True）
    - 自动持久化会话记录到传统 DB 和 VDB（通过装饰器非侵入式实现）
    """
    llm = get_default_qwen_llm()

    full_messages = params.messages or [UserMessages(prompt=params.question)]
    del params.messages

    if params.is_stream:
        # 流式输出：启用思考模式和流式传输
        stream = llm.chat(
            messages=full_messages,
            enable_thinking=params.is_thinking,
            enable_search=params.is_online_search,
            stream=True,
            **params.invoke_params
        )
        return StreamingResponse(stream, media_type="text/event-stream")
    else:
        # 非流式输出
        result = llm.chat(messages=full_messages, enable_search=params.is_online_search, **params.invoke_params)
        return HttpResponse.ok(result)


def register_ai_chat_router(app):
    app.include_router(router)
