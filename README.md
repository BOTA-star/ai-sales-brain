# Chatbot RAG / AI Sales Brain Demo

Dự án này là bản demo chatbot AI chạy local bằng Streamlit, có kết nối PostgreSQL để lưu thông tin khách hàng, phiên hội thoại và nội dung tin nhắn. Chatbot sử dụng Ollama để gọi mô hình AI local và hỗ trợ ghi nhớ ngữ cảnh hội thoại gần nhất trong từng phiên chat.

## Chức năng hiện tại

* Giao diện chatbot cơ bản bằng Streamlit.
* Kết nối database PostgreSQL.
* Tạo khách hàng demo khi mở chatbot.
* Tạo phiên hội thoại mới.
* Lưu tin nhắn của user và assistant vào database.
* Gọi model local thông qua Ollama.
* Hỗ trợ cấu hình qua file `.env`.

## Cách chạy dự án

1. Tạo môi trường ảo và cài thư viện:

```bash
pip install -r requirements.txt
```

2. Tạo file `.env` dựa trên `.env.example`.

3. Chạy PostgreSQL và kiểm tra kết nối database.

4. Chạy ứng dụng:

```bash
streamlit run app.py
```

## Ghi chú

File `.env` không được push lên Git vì chứa thông tin cấu hình riêng của môi trường local. Khi clone project về, mỗi thành viên cần tự tạo file `.env` theo mẫu `.env.example`.


