from typing import Any, MutableMapping

from psycopg2.extras import RealDictCursor

from config import (
    DEFAULT_CUSTOMER_NAME,
    WELCOME_MESSAGE,
)
from database import get_db_connection


VALID_SENDERS = {
    "user",
    "assistant",
    "system",
}


def create_customer(
    external_id: str,
) -> str:
    """
    Tìm hoặc tạo customer riêng
    theo external_id của trình duyệt demo.

    Sử dụng UPSERT để tránh lỗi khi có hai request
    đồng thời cùng tạo một external_id.
    """

    if not external_id:
        raise ValueError(
            "external_id is required"
        )

    conn = get_db_connection()

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO customers (
                        external_id,
                        full_name,
                        source,
                        note
                    )
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (external_id)
                    WHERE external_id IS NOT NULL
                    DO UPDATE SET
                        external_id = EXCLUDED.external_id
                    RETURNING id;
                    """,
                    (
                        external_id,
                        DEFAULT_CUSTOMER_NAME,
                        "web",
                        (
                            "Khách demo được tạo từ "
                            "Streamlit chatbot"
                        ),
                    ),
                )

                inserted_customer = cur.fetchone()

                if not inserted_customer:
                    raise RuntimeError(
                        "Could not create or load customer."
                    )

                return str(
                    inserted_customer[0]
                )

    finally:
        conn.close()


def create_customer_if_needed(
    session_state: MutableMapping[str, Any],
    external_id: str,
) -> str:
    """
    Lấy customer_id trong session nếu customer hiện tại
    khớp với external_id.

    Nếu chưa có thì tìm hoặc tạo customer trong database.
    """

    customer_id = session_state.get(
        "customer_id"
    )

    customer_external_id = session_state.get(
        "customer_external_id"
    )

    if (
        customer_id
        and customer_external_id == external_id
    ):
        return str(customer_id)

    customer_id = create_customer(
        external_id
    )

    session_state[
        "customer_id"
    ] = customer_id

    session_state[
        "customer_external_id"
    ] = external_id

    return customer_id


def create_conversation(
    customer_id: str,
) -> str:
    """
    Tạo conversation mới cho đúng customer.
    """

    if not customer_id:
        raise ValueError(
            "customer_id is required"
        )

    conn = get_db_connection()

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO conversations (
                        customer_id,
                        channel,
                        status,
                        title
                    )
                    VALUES (%s, %s, %s, %s)
                    RETURNING id;
                    """,
                    (
                        customer_id,
                        "web",
                        "active",
                        "Cuộc trò chuyện mới",
                    ),
                )

                inserted_conversation = (
                    cur.fetchone()
                )

                if not inserted_conversation:
                    raise RuntimeError(
                        "Could not create conversation."
                    )

                return str(
                    inserted_conversation[0]
                )

    finally:
        conn.close()


def load_conversations(
    customer_id: str,
) -> list[dict[str, Any]]:
    """
    Chỉ lấy conversation thuộc customer hiện tại
    và đã có ít nhất một tin nhắn từ user.
    """

    if not customer_id:
        return []

    conn = get_db_connection()

    try:
        with conn.cursor(
            cursor_factory=RealDictCursor
        ) as cur:
            cur.execute(
                """
                SELECT
                    c.id,
                    c.title,
                    c.status,
                    c.created_at,
                    c.updated_at
                FROM conversations c
                WHERE c.customer_id = %s
                  AND EXISTS (
                      SELECT 1
                      FROM messages m
                      WHERE m.conversation_id = c.id
                        AND m.sender = 'user'
                  )
                ORDER BY
                    c.updated_at DESC,
                    c.created_at DESC,
                    c.id DESC;
                """,
                (customer_id,),
            )

            return list(
                cur.fetchall()
            )

    finally:
        conn.close()


def save_message(
    conversation_id: str,
    customer_id: str,
    sender: str,
    content: str,
) -> str:
    """
    Lưu message sau khi kiểm tra conversation
    thuộc đúng customer.

    Hàm trả về message_id vừa được tạo.
    """

    normalized_sender = (
        sender or ""
    ).strip().lower()

    normalized_content = (
        content or ""
    ).strip()

    if not conversation_id:
        raise ValueError(
            "conversation_id is required"
        )

    if not customer_id:
        raise ValueError(
            "customer_id is required"
        )

    if normalized_sender not in VALID_SENDERS:
        raise ValueError(
            f"Invalid sender: {sender}"
        )

    if not normalized_content:
        raise ValueError(
            "Message content cannot be empty"
        )

    conn = get_db_connection()

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO messages (
                        conversation_id,
                        sender,
                        content
                    )
                    SELECT
                        c.id,
                        %s,
                        %s
                    FROM conversations c
                    WHERE c.id = %s
                      AND c.customer_id = %s
                    RETURNING id;
                    """,
                    (
                        normalized_sender,
                        normalized_content,
                        conversation_id,
                        customer_id,
                    ),
                )

                inserted = cur.fetchone()

                if not inserted:
                    raise PermissionError(
                        "Conversation does not belong "
                        "to the current customer."
                    )

                cur.execute(
                    """
                    UPDATE conversations
                    SET updated_at = NOW()
                    WHERE id = %s
                      AND customer_id = %s;
                    """,
                    (
                        conversation_id,
                        customer_id,
                    ),
                )

                return str(
                    inserted[0]
                )

    finally:
        conn.close()


def load_messages(
    conversation_id: str,
    customer_id: str,
) -> list[dict[str, str]]:
    """
    Load toàn bộ message đúng thứ tự
    và đúng phạm vi customer.
    """

    if not conversation_id or not customer_id:
        return []

    conn = get_db_connection()

    try:
        with conn.cursor(
            cursor_factory=RealDictCursor
        ) as cur:
            cur.execute(
                """
                SELECT
                    m.sender,
                    m.content
                FROM messages m
                INNER JOIN conversations c
                    ON c.id = m.conversation_id
                WHERE m.conversation_id = %s
                  AND c.customer_id = %s
                ORDER BY
                    m.message_order ASC;
                """,
                (
                    conversation_id,
                    customer_id,
                ),
            )

            return [
                {
                    "role": row["sender"],
                    "content": row["content"],
                }
                for row in cur.fetchall()
            ]

    finally:
        conn.close()


def get_recent_context(
    conversation_id: str,
    customer_id: str,
    limit: int = 8,
    exclude_message_id: str | None = None,
) -> list[dict[str, str]]:
    """
    Lấy short-term context gần nhất.

    exclude_message_id được dùng để loại message user
    hiện tại ra khỏi history, tránh câu hỏi bị đưa
    vào prompt hai lần.

    Đây là lịch sử chat gần nhất,
    chưa phải long-term Agent Memory.
    """

    if not conversation_id or not customer_id:
        return []

    try:
        parsed_limit = int(limit)
    except (
        TypeError,
        ValueError,
    ):
        parsed_limit = 8

    safe_limit = max(
        1,
        min(parsed_limit, 50),
    )

    conn = get_db_connection()

    try:
        with conn.cursor(
            cursor_factory=RealDictCursor
        ) as cur:
            cur.execute(
                """
                SELECT
                    m.sender,
                    m.content
                FROM messages m
                INNER JOIN conversations c
                    ON c.id = m.conversation_id
                WHERE m.conversation_id = %s
                  AND c.customer_id = %s
                  AND (
                      %s::uuid IS NULL
                      OR m.id <> %s::uuid
                  )
                ORDER BY
                    m.message_order DESC
                LIMIT %s;
                """,
                (
                    conversation_id,
                    customer_id,
                    exclude_message_id,
                    exclude_message_id,
                    safe_limit,
                ),
            )

            rows = list(
                cur.fetchall()
            )

            # Query lấy mới nhất trước.
            # Đảo lại để LLM nhận lịch sử từ cũ đến mới.
            rows.reverse()

            return [
                {
                    "role": row["sender"],
                    "content": row["content"],
                }
                for row in rows
            ]

    finally:
        conn.close()


def update_conversation_title_if_needed(
    conversation_id: str,
    customer_id: str,
    user_input: str,
) -> None:
    """
    Dùng câu hỏi đầu tiên làm tiêu đề conversation.

    Chỉ cập nhật nếu tiêu đề hiện tại vẫn là tiêu đề mặc định.
    """

    title = (
        user_input or ""
    ).strip()

    if (
        not conversation_id
        or not customer_id
        or not title
    ):
        return

    if len(title) > 60:
        title = title[:60] + "..."

    conn = get_db_connection()

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE conversations
                    SET
                        title = %s,
                        updated_at = NOW()
                    WHERE id = %s
                      AND customer_id = %s
                      AND (
                          title IS NULL
                          OR title = ''
                          OR title = 'Cuộc trò chuyện mới'
                      );
                    """,
                    (
                        title,
                        conversation_id,
                        customer_id,
                    ),
                )

    finally:
        conn.close()

def init_chat_session(
    session_state: MutableMapping[str, Any],
    external_id: str,
) -> None:
    """
    Khởi tạo customer và giao diện chat.

    Conversation chỉ được tạo khi
    user gửi tin nhắn đầu tiên.
    """

    create_customer_if_needed(
        session_state,
        external_id,
    )

    session_state.setdefault(
        "conversation_id",
        None,
    )

    session_state.setdefault(
        "messages",
        [
            {
                "role": "assistant",
                "content": WELCOME_MESSAGE,
            }
        ],
    )