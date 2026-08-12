from Base.Ai.llms.qwenLlm import get_default_qwen_llm
from Base.Ai.service.commonService import RewriteQuestionParams, rewrite_question
from Base.Models.BaseLLMConversationModel import BaseLLMConversationModel
from Base.Models.VdbLLMConversation import VdbLLMConversation


class AiService:

    @staticmethod
    def rewrite_question(question: str, user_id: str, session_id: str):
        llm = get_default_qwen_llm()
        question_embedding = llm.embedding(text=question)[0]
        similarity = VdbLLMConversation.search(data=question_embedding, output_fields=['question'])
        history = BaseLLMConversationModel.get_last_n_turns_context(user_id, session_id, 5)
        history = BaseLLMConversationModel.db_res_2_messages(history, is_rewrite=True)
        return rewrite_question(RewriteQuestionParams(question=question, similarity=similarity, history=history))


if __name__ == '__main__':
    question_new = AiService.rewrite_question(question="一百个 奥特曼呢", user_id='string',
                                              session_id='string')
    print(question_new)
