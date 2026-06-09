import uuid
from typing import MutableMapping

import streamlit as st


CLIENT_ID_KEY = "client_id"
CLIENT_ID_QUERY_PARAM = "client_id"


def _is_valid_uuid(value: str) -> bool:
    try:
        uuid.UUID(str(value))
        return True
    except (
        ValueError,
        TypeError,
        AttributeError,
    ):
        return False


def get_or_create_client_id(
    session_state: MutableMapping,
) -> str:
    """
    Tạo mã định danh riêng cho trình duyệt demo.

    Mã được giữ trong session_state và query parameter
    để vẫn còn sau khi refresh trang.

    Đây chỉ là giải pháp local/demo.
    Khi làm production cần thay bằng user_id từ đăng nhập.
    """

    current_value = session_state.get(
        CLIENT_ID_KEY
    )

    if (
        current_value
        and _is_valid_uuid(str(current_value))
    ):
        return str(current_value)

    query_value = st.query_params.get(
        CLIENT_ID_QUERY_PARAM
    )

    if isinstance(query_value, list):
        query_value = (
            query_value[0]
            if query_value
            else None
        )

    if (
        query_value
        and _is_valid_uuid(str(query_value))
    ):
        client_id = str(query_value)
    else:
        client_id = str(uuid.uuid4())

        st.query_params[
            CLIENT_ID_QUERY_PARAM
        ] = client_id

    session_state[CLIENT_ID_KEY] = client_id

    return client_id