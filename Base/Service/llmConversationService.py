from Base.Ai.llms.qwenLlm import get_default_qwen_llm
from Base.Models.BaseLLMConversationModel import BaseLLMConversationModel
from Base.Models.VdbLLMConversation import VdbLLMConversation


def save_conversation_from_db_2_vdb(db_instance: BaseLLMConversationModel):
    """
    将对话记录从数据库保存到 VDB
    """
    llm = get_default_qwen_llm()
    question_embedding = llm.embedding(text=db_instance.question, dimensions=1024)

    question_embedding = question_embedding[0] if question_embedding and isinstance(question_embedding[0],
                                                                                    list) else question_embedding


    vdb = VdbLLMConversation(db_id=str(db_instance.id),
                             session_id=db_instance.session_id,
                             user_id=db_instance.user_id,
                             question=db_instance.question,
                             rewrite_question=db_instance.rewrite_question or '',
                             answer=db_instance.get_answer,
                             embedding=question_embedding)
    vdb.save()


if __name__ == '__main__':
    # 查询数据库中所有对话记录 存到VDB
    db_instances = BaseLLMConversationModel.find_by()
    for i in db_instances:
        save_conversation_from_db_2_vdb(i)

