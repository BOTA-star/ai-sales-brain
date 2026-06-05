from intent_service import classify_intent, normalize_text


def get_source_value(source, key: str, default="N/A"):
    """
    Lấy giá trị source an toàn.
    Hỗ trợ cả object source.file_name và dict source["file_name"].
    """
    if source is None:
        return default

    if isinstance(source, dict):
        return source.get(key, default)

    return getattr(source, key, default)


def format_rag_sources(sources) -> str:
    """
    Format nguồn tham khảo an toàn hơn.
    """
    if not sources:
        return ""

    source_lines = ["\n\n---\nNguồn tham khảo:"]

    for index, source in enumerate(sources, start=1):
        file_name = get_source_value(source, "file_name")
        page = get_source_value(source, "page")
        chunk_index = get_source_value(source, "chunk_index")

        source_lines.append(
            f"{index}. File: {file_name} | Page: {page} | Chunk: {chunk_index}"
        )

    return "\n".join(source_lines)


def answer_simple_math(user_input: str) -> str:
    """
    Tính toán đơn giản.
    Chỉ dùng cho input đã được lọc bằng regex trong intent_service.
    """
    text = normalize_text(user_input)

    try:
        result = eval(text, {"__builtins__": {}}, {})
        return str(result)
    except Exception:
        return "Mình chưa xử lý được phép tính này."


def answer_by_rule(intent: str) -> str:
    """
    Các câu không cần RAG thì trả lời bằng rule.
    """
    if intent == "empty":
        return "Bạn vui lòng nhập câu hỏi trước nha."

    if intent == "greeting":
        return (
            "Hi bạn 👋 Mình là chatbot RAG demo. "
            "Mình có thể trả lời câu hỏi dựa trên tài liệu đã được nạp vào hệ thống."
        )

    if intent == "thanks":
        return "Không có gì nha 😊 Bạn cần hỏi thêm gì về tài liệu thì cứ nhắn mình."

    if intent == "upload_info":
        return (
            "Bạn có thể gửi các tài liệu như PDF, DOCX hoặc TXT. "
            "Tuy nhiên hiện tại bản demo đang dùng tài liệu được nạp sẵn trong lúc code. "
            "Bước tiếp theo có thể thêm chức năng upload file để bạn tự nạp tài liệu."
        )

    if intent == "bot_capability":
        return (
            "Mình có thể hỗ trợ hỏi đáp dựa trên tài liệu đã được nạp vào hệ thống. "
            "Ví dụ: hỏi khái niệm chính, phương pháp, kết quả, nội dung trong PDF "
            "hoặc yêu cầu tóm tắt một phần trong tài liệu."
        )

    return ""


def get_chat_answer(user_input: str, conversation_id: str, rag_pipeline) -> str:
    """
    Hàm điều phối chính:
    - Phân loại intent
    - Câu nào không cần tài liệu thì trả lời rule
    - Câu nào cần tài liệu thì mới gọi RAG
    """
    intent = classify_intent(user_input)

    if intent == "simple_math":
        return answer_simple_math(user_input)

    if intent != "document_question":
        return answer_by_rule(intent)

    try:
        rag_response = rag_pipeline.answer(user_input)

        answer = normalize_text(getattr(rag_response, "answer", ""))
        sources = getattr(rag_response, "sources", [])

        if not answer:
            return "Tài liệu chưa cung cấp đủ thông tin để trả lời câu hỏi này."

        if not sources:
            return (
                "Tài liệu chưa cung cấp đủ thông tin để trả lời câu hỏi này. "
                "Mình chưa tìm thấy nguồn tham khảo phù hợp trong dữ liệu đã nạp."
            )

        return answer + format_rag_sources(sources)

    except Exception as error:
        return (
            "Hiện tại hệ thống RAG đang gặp lỗi trong quá trình xử lý. "
            f"Chi tiết lỗi: {str(error)}"
        )