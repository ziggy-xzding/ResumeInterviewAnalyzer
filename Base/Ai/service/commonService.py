from typing import Any, Optional

from Base.Ai.base.baseLlm import BaseLlm
from pydantic import BaseModel,Field

from Base.Ai.llms.qwenLlm import get_default_qwen_llm
from Base.Ai.prompt.commonPrompt import rewrite_question_prompt_v1
from Base.Ai.utils.common import jinja2_prompt_render


class RewriteQuestionParams(BaseModel):
    """
    问题改写 函数入参
    """
    model_config = {"arbitrary_types_allowed": True}  # 添加这行配置

    question: str = Field(..., description="问题")
    similarity: Optional[Any] = Field(None, description="相似问题")
    history: Optional[Any] = Field(None, description="历史问题")
    llm: BaseLlm = Field(get_default_qwen_llm(), description="llm")


def rewrite_question(params: RewriteQuestionParams):
    """
    问题改写
    :params
        question: 问题
        similarity: 相似问题
        history: 历史问题
        llm: 可以不传 指定LLM
    """
    prompt = jinja2_prompt_render(rewrite_question_prompt_v1, params.model_dump())
    rewrite_q = params.llm.invoke(prompt)
    return rewrite_q