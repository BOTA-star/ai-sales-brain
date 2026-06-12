from __future__ import annotations

import sys
import uuid
from pathlib import Path

# Cho phép file trong thư mục tests import module ở thư mục gốc.
ROOT_DIR = Path(__file__).resolve().parents[1]

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from memory_service import MemoryService 

def require(condition: bool, message: str) -> None:
    """Dừng kiểm thử nếu điều kiện không đạt."""
    if not condition:
        raise AssertionError(message)

def main() -> None:
    service = MemoryService()

    marker = f"MEMSERVICE-{uuid.uuid4().hex[:8].upper()}"
    customer_id = f"module-test-{uuid.uuid4().hex[:8]}"
    other_customer_id = f"module-other-{uuid.uuid4().hex[:8]}"

    content = (
        f"{marker}: Khách hàng Lan đang quan tâm DigiAI Platform, ưu tiên triển khai chatbot chăm sóc khách hàng và dự kiến bắt đầu trong tháng sau.")

    print("=" * 70)
    print("KIỂM THỬ MEMORY SERVICE")
    print("=" * 70)

    # 1. Kiểm tra health
    print("\n[1] Kiểm tra kết nối AgentMemory...")

    health_status = service.health_check()

    require(
        health_status,
        "AgentMemory không hoạt động hoặc không thể kết nối.",
    )

    print("PASS - AgentMemory healthy.")

    # 2. Kiểm tra build project
    print("\n[2] Kiểm tra project theo customer_id...")

    expected_project = f"chatbot-rag/customer/{customer_id}"
    actual_project = service.build_project(customer_id)

    require(
        actual_project == expected_project,
        (
            "Project không đúng. "
            f"Expected={expected_project}, actual={actual_project}"
        ),
    )

    print(f"PASS - Project: {actual_project}")

    # 3. Lưu memory
    print("\n[3] Lưu memory cho khách hàng...")

    saved_memory = service.save_memory(
        customer_id=customer_id,
        content=content,
        memory_type="fact",
        concepts=[
            "Lan",
            "DigiAI Platform",
            "chatbot",
            "chăm sóc khách hàng",
            "tháng sau",
        ],
    )

    require(
        saved_memory is not None,
        "Không lưu được memory.",
    )

    require(
        saved_memory.get("project") == expected_project,
        "Memory được lưu sai project.",
    )

    print(f"PASS - Memory ID: {saved_memory.get('id')}")
    print(f"PASS - Marker: {marker}")

    # 4. Truy vấn bằng marker chính xác
    print("\n[4] Truy vấn memory bằng marker chính xác...")

    exact_results = service.search_memory(
        customer_id=customer_id,
        query=marker,
        limit=5,
    )

    exact_match = any(
        marker in str(item.get("content", ""))
        for item in exact_results
    )

    require(
        exact_match,
        "Không tìm thấy memory bằng marker chính xác.",
    )

    print(
        f"PASS - Tìm thấy {len(exact_results)} "
        "kết quả trong đúng project."
    )

    # 5. Truy vấn ngữ nghĩa
    print("\n[5] Kiểm tra semantic search...")

    semantic_query = (
        "Lan muốn dùng giải pháp nào để hỗ trợ khách hàng "
        "và dự kiến triển khai vào lúc nào?"
    )

    semantic_results = service.search_memory(
        customer_id=customer_id,
        query=semantic_query,
        limit=5,
    )

    semantic_match = any(
        marker in str(item.get("content", ""))
        for item in semantic_results
    )

    require(
        semantic_match,
        "Semantic search không tìm được memory đã lưu.",
    )

    print(
        f"PASS - Semantic search trả về "
        f"{len(semantic_results)} kết quả."
    )

    # 6. Kiểm tra phân tách khách hàng
    print("\n[6] Kiểm tra phân tách memory giữa khách hàng...")

    isolated_results = service.search_memory(
        customer_id=other_customer_id,
        query=marker,
        limit=5,
    )

    leaked_memory = any(
        marker in str(item.get("content", ""))
        for item in isolated_results
    )

    require(
        not leaked_memory,
        "Phát hiện memory bị truy xuất chéo giữa hai khách hàng.",
    )

    print("PASS - Không truy xuất chéo memory.")

    # 7. Chuẩn hóa context
    print("\n[7] Kiểm tra format context cho prompt...")

    memory_context = service.format_memory_context(
        semantic_results
    )

    require(
        marker in memory_context,
        "Context sau khi chuẩn hóa không chứa memory cần thiết.",
    )

    print("PASS - Memory context đã được chuẩn hóa.")
    print("\nMemory context:")
    print("-" * 70)
    print(memory_context)
    print("-" * 70)

    print("\n" + "=" * 70)
    print("TẤT CẢ KIỂM THỬ MEMORY SERVICE ĐÃ PASS")
    print("=" * 70)


if __name__ == "__main__":
    main()