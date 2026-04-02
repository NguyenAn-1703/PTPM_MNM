"""Prompt templates for conversational and self-evaluation RAG flows."""


def build_self_eval_prompt(question: str, answer: str, context_preview: str) -> str:
    return (
        "Bạn là bộ kiểm định câu trả lời RAG. "
        "Đánh giá câu trả lời có bám ngữ cảnh hay không. "
        "Trả về đúng JSON với schema: "
        "{\"supported\": bool, \"confidence\": number, \"feedback\": string}.\n\n"
        f"QUESTION:\n{question}\n\n"
        f"ANSWER:\n{answer}\n\n"
        f"CONTEXT:\n{context_preview}\n"
    )


def build_condense_question_prompt(history_text: str, question: str) -> str:
    return (
        "Dựa vào lịch sử hội thoại và câu hỏi mới nhất, "
        "hãy viết lại câu hỏi mới thành một câu hỏi độc lập, đầy đủ ý nghĩa. "
        "Chỉ trả về câu hỏi độc lập, không giải thích.\n\n"
        f"LỊCH SỬ HOI THOẠI:\n{history_text}\n\n"
        f"CÂU HỎI HIỆN TẠI: {question}\n\n"
        "CÂU HỎI ĐÔC LẬP:"
    )


def build_chat_answer_prompt(system_prompt: str, history_text: str, context_text: str, question: str) -> str:
    return (
        f"SYSTEM PROMPT:\n{system_prompt}\n\n"
        "HƯỚNG DẪN SUY LUẬN NỘI BỘ (KHÔNG IN RA):\n"
        "1) Trích xuất dữ kiện trực tiếp từ context.\n"
        "2) Liên kết dữ kiện để trả lời câu hỏi.\n"
        "3) Tự kiểm tra mâu thuẫn và phần thiếu bằng context.\n"
        "4) Chỉ in RA CÂU TRẢ LỜI CUỐI CÙNG, không mô tả chuỗi suy luận.\n\n"
        f"CHAT HISTORY (3-5 câu gần nhất):\n{history_text}\n\n"
        f"RAG CONTEXT (chunks liên quan):\n{context_text}\n\n"
        f"CÂU HỎI HIỆN TẠI:\n{question}\n\n"
        "TRẢ LỜI:"
    )

