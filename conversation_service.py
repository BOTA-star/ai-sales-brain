from psycopg2.extras import RealDictCursor

from config import DEFAULT_CUSTOMER_NAME, WELCOME_MESSAGE
from database import get_db_connection


def create_customer():
    """
    MVP hiện tại chưa có đăng nhập/customer thật,
    nên tạo 1 khách demo để gắn hội thoại.
    """
    conn = get_db_connection()

    try:
        with conn:
            with conn.cursor() as cur:
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
    conn = get_db_connection()

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO conversations (customer_id, channel, status)
                    VALUES (%s, %s, %s)
                    RETURNING id;
                    """,
                    (customer_id, "web", "active")
                )

                conversation_id = cur.fetchone()[0]
                return str(conversation_id)

    finally:
        conn.close()


def save_message(conversation_id: str, sender: str, content: str):
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

    finally:
        conn.close()


def load_messages(conversation_id: str):
    conn = get_db_connection()

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT sender, content
                FROM messages
                WHERE conversation_id = %s
                ORDER BY message_order ASC;
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
    conn = get_db_connection()

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT sender, content
                FROM messages
                WHERE conversation_id = %s
                ORDER BY message_order DESC
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


def init_chat_session(session_state):
    customer_id = create_customer_if_needed(session_state)

    if "conversation_id" not in session_state:
        conversation_id = create_conversation(customer_id)
        session_state["conversation_id"] = conversation_id

        session_state["messages"] = [
            {
                "role": "assistant",
                "content": WELCOME_MESSAGE
            }
        ]

        save_message(conversation_id, "assistant", WELCOME_MESSAGE)

    else:
        db_messages = load_messages(session_state["conversation_id"])

        if db_messages:
            session_state["messages"] = db_messages