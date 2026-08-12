from typing import Optional, List

from Base.Ai.base import UserMessages, AssistantMessages
from Base.Ai.llms.qwenLlm import get_default_qwen_llm
from Base.Ai.service.commonService import RewriteQuestionParams
from Base.Repository.base.baseVDB import BaseVDBModel
from pydantic import Field


class VdbLLMConversation(BaseVDBModel):
    collection_alias = "llm_conversation"
    description = "LLM 对话记录表"

    id: Optional[int] = Field(
        default=0,  # auto_id 时提供默认值，避免校验失败
        json_schema_extra={
            'is_primary': True,
            'auto_id': True
        }
    )

    db_id: Optional[str] = Field(
        default='',
        json_schema_extra={
            'max_length': 64
        }
    )

    session_id: Optional[str] = Field(
        default='',
        json_schema_extra={
            'max_length': 64
        }
    )

    user_id: Optional[str] = Field(
        default='',
        json_schema_extra={
            'max_length': 64
        }
    )

    question: Optional[str] = Field(
        default='',
        json_schema_extra={
            'enable_match': True,
            'enable_analyzer': True,
            'max_length': 65535
        }
    )

    rewrite_question: Optional[str] = Field(
        default='',
        json_schema_extra={
            'max_length': 65535
        }
    )

    answer: Optional[str] = Field(
        default='',
        json_schema_extra={
            'max_length': 65535
        }
    )

    embedding: Optional[List[float]] = Field(
        default_factory=list,
        json_schema_extra={
            'dim': 1024
        }
    )

    # 稀疏向量字段（基于 BM25 文本字段生成）
    content_sparse: Optional[List[float]] = Field(
        default_factory=list,
        json_schema_extra={
            'is_sparse_vector': True,
            'bm25_source_field': 'question'
        }
    )

    @staticmethod
    def get_n_high_similarity_item(question: str, user_id: str = None, session_id: str = None, n: int = 5):
        """
        获取与 query 最相似的 n 个对话
        使用混合搜索（密集向量 + 稀疏向量）
        可选择性地按 user_id 和 session_id 进行过滤
        """
        llm = get_default_qwen_llm()
        dense_vectors = llm.embedding(text=question, dimensions=1024)

        # 构建过滤表达式
        filter_conditions = []
        if user_id:
            filter_conditions.append(f"user_id == '{user_id}'")
        if session_id:
            filter_conditions.append(f"session_id == '{session_id}'")

        filter_expr = " and ".join(filter_conditions) if filter_conditions else ""

        res = VdbLLMConversation.hybrid_search(
            queries=[
                {
                    'data': dense_vectors,  # 密集向量搜索
                    'field': 'embedding',
                    'type': 'dense',
                    'params': {
                        'metric_type': 'COSINE',
                        'params': {'nprobe': 10}
                    }
                },
                {
                    'data': [question],
                    'field': 'content_sparse',
                    'type': 'sparse',
                    'params': {
                        'metric_type': 'BM25',
                        'params': {}
                    }
                }
            ],
            limit=n,
            filter_expr=filter_expr,  # 添加过滤条件
            weights=[0.7, 0.3],  # 密集向量权重0.7，稀疏向量权重0.3
            output_fields=['db_id', 'session_id', 'user_id', 'question', 'answer']  # 返回需要的字段
        )
        return res

    @staticmethod
    def vdb_res_2_messages(res):
        """
        VDB 检索的会话结果 转换为 messages
        """
        result_list = []

        def dict_2_messages_join_list(dict_item: dict):
            result_list.append(UserMessages(prompt=dict_item.get('question')))
            result_list.append(AssistantMessages(prompt=dict_item.get('answer')))

        list(map(dict_2_messages_join_list, res))
        return result_list


if __name__ == '__main__':
    VdbLLMConversation()
