"""Prompt templates for conversational and self-evaluation RAG flows."""


def build_query_rewrite_prompt(history_text: str, question: str) -> str:
    return (
        "Viết lại câu truy vấn để tăng chất lượng truy xuất tài liệu RAG. "
        "Tập trung từ khóa, thực thể, khái niệm chính. "
        "Chỉ trả về 1 câu truy vấn mới, không giải thích.\n\n"
        f"HISTORY:\n{history_text}\n\n"
        f"CÂU HỎI GỐC:\n{question}\n\n"
        "TRUY VẤN MỚI:"
    )


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
        f"CHAT HISTORY (3-5 câu gần nhất):\n{history_text}\n\n"
        f"RAG CONTEXT (chunks liên quan):\n{context_text}\n\n"
        f"CÂU HỎI HIỆN TẠI:\n{question}\n\n"
        "TRẢ LỜI:"
    )


def build_chat_retry_prompt(system_prompt: str, history_text: str, context_text: str, question: str) -> str:
    return (
        f"SYSTEM PROMPT:\n{system_prompt}\n\n"
        "Hãy suy luận như một chuyên gia và chỉ dùng dữ kiện có trong context.\n\n"
        f"CHAT HISTORY:\n{history_text}\n\n"
        f"RAG CONTEXT:\n{context_text}\n\n"
        f"QUESTION:\n{question}\n\n"
        "TRẢ LỜI:"
    )
