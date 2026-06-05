from psycopg2.extras import RealDictCursor

from config import DEFAULT_CUSTOMER_NAME, WELCOME_MESSAGE
from database import get_db_connection

def create_customer():
    """
    MVP hiện tại chưa có đăng nhập/customer thật,
    nên dùng lại 1 khách demo cố định để xem được lịch sử hội thoại.
    """
    conn = get_db_connection()

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id
                    FROM customers
                    WHERE full_name = %s
                    AND source = %s
                    ORDER BY id ASC
                    LIMIT 1;
                    """,
                    (
                        DEFAULT_CUSTOMER_NAME,
                        "web"
                    )
                )

                existing_customer = cur.fetchone()

                if existing_customer:
                    return str(existing_customer[0])

                cur.execute(
                    """
                    INSERT INTO customers (full_name, source, note)
                    VALUES (%s, %s, %s)
                    RETURNING id;
                    """,
                    (
                        DEFAULT_CUSTOMER_NAME,
                        "web",
                        "Khách demo tạo từ Streamlit chatbot"
                    )
                )

                customer_id = cur.fetchone()[0]
                return str(customer_id)

    finally:
        conn.close()

def create_customer_if_needed(session_state):
    if "customer_id" in session_state:
        return session_state["customer_id"]

    customer_id = create_customer()
    session_state["customer_id"] = customer_id

    return customer_id


def create_conversation(customer_id: str):
    """
    Tạo một phiên chat mới.
    Mỗi conversation tương ứng với một phiên hội thoại.
    """
    conn = get_db_connection()

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO conversations (customer_id, channel, status, title)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id;
                    """,
                    (
                        customer_id,
                        "web",
                        "active",
                        "Cuộc trò chuyện mới"
                    )
                )

                conversation_id = cur.fetchone()[0]
                return str(conversation_id)

    finally:
        conn.close()

def load_conversations(customer_id: str):
    """
    Lấy danh sách phiên chat của một customer.
    Chỉ hiển thị conversation đã có ít nhất 1 tin nhắn từ user.
    """
    conn = get_db_connection()

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, title, status, created_at, updated_at
                FROM conversations c
                WHERE c.customer_id = %s
                AND EXISTS (
                    SELECT 1
                    FROM messages m
                    WHERE m.conversation_id = c.id
                    AND m.sender = 'user'
                )
                ORDER BY updated_at DESC, created_at DESC, id DESC;
                """,
                (customer_id,)
            )

            return cur.fetchall()

    finally:
        conn.close()    

def save_message(conversation_id: str, sender: str, content: str):
    """
    Lưu tin nhắn vào đúng phiên chat.
    Sau khi lưu message thì cập nhật updated_at của conversation.
    """
    conn = get_db_connection()

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO messages (conversation_id, sender, content)
                    VALUES (%s, %s, %s);
                    """,
                    (conversation_id, sender, content)
                )

                cur.execute(
                    """
                    UPDATE conversations
                    SET updated_at = NOW()
                    WHERE id = %s;
                    """,
                    (conversation_id,)
                )

    finally:
        conn.close()

def load_messages(conversation_id: str):
    """
    Load toàn bộ tin nhắn thuộc một phiên chat.
    """
    conn = get_db_connection()

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT sender, content
                FROM messages
                WHERE conversation_id = %s
                ORDER BY created_at ASC, id ASC;
                """,
                (conversation_id,)
            )

            rows = cur.fetchall()

            messages = []
            for row in rows:
                messages.append({
                    "role": row["sender"],
                    "content": row["content"]
                })

            return messages

    finally:
        conn.close()

def get_recent_context(conversation_id: str, limit: int = 8):
    """
    Lấy một số tin nhắn gần nhất để đưa vào context cho model.
    """
    if not conversation_id:
        return []

    conn = get_db_connection()

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT sender, content
                FROM messages
                WHERE conversation_id = %s
                ORDER BY created_at DESC, id DESC
                LIMIT %s;
                """,
                (conversation_id, limit)
            )

            rows = cur.fetchall()
            rows.reverse()

            context_messages = []

            for row in rows:
                context_messages.append({
                    "role": row["sender"],
                    "content": row["content"]
                })

            return context_messages

    finally:
        conn.close()

def update_conversation_title_if_needed(conversation_id: str, user_input: str):
    """
    Nếu conversation đang có title mặc định,
    lấy câu đầu tiên của user làm title.
    """
    title = user_input.strip()

    if len(title) > 60:
        title = title[:60] + "..."

    conn = get_db_connection()

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE conversations
                    SET title = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    AND (
                        title IS NULL
                        OR title = ''
                        OR title = 'Cuộc trò chuyện mới'
                    );
                    """,
                    (title, conversation_id)
                )

    finally:
        conn.close()

def init_chat_session(session_state):
    """
    Khởi tạo UI chat.
    Chưa tạo conversation trong DB cho đến khi user gửi tin nhắn đầu tiên.
    """
    create_customer_if_needed(session_state)

    session_state["conversation_id"] = None
    session_state["messages"] = [
        {
            "role": "assistant",
            "content": WELCOME_MESSAGE
        }
    ]