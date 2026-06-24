
## V. Kết luận

### 5.1. Kết quả đạt được

| Bước | Chức năng | Trạng thái |
|---|---|---|
| VALIDATE | Kiểm tra 7 trường bắt buộc, từ chối message không hợp lệ | Hoàn thành |
| CHECK | Đối chiếu `device_id` với `device_registry.csv` | Hoàn thành |
| NORMALIZE | Chuẩn hóa timestamp ISO 8601, kiểm tra kiểu số, xóa field debug | Hoàn thành |
| CLASSIFY | Phân loại 5 trạng thái môi trường theo bảng rule | Hoàn thành |
| PRODUCE | Đóng gói JSON và Publish QoS 1 lên Output Topic | Hoàn thành |

### 5.2. Các điểm kỹ thuật nổi bật

1. **Phân tách mối quan tâm (Separation of Concerns):** Mỗi bước pipeline là hàm độc lập, dễ test và bảo trì.
2. **Bảo mật thông tin:** Credential MQTT và database không hardcode, dùng biến môi trường qua `.env`.
3. **Khả năng mở rộng:** Danh sách thiết bị đọc từ CSV bên ngoài, không hardcode trong code.
4. **Traceability:** Trường `raw_event_id` cho phép truy vết ngược từ processed event về event gốc.
5. **Healthcheck đa cấp:** Cả 3 service đều có healthcheck độc lập, đảm bảo thứ tự khởi động chính xác.

### 5.3. Cấu trúc thư mục dự án

```
lab-5-PhanPhong13112005/
├── src/
│   ├── iot_app/
│   │   ├── main.py                 ← Toàn bộ pipeline xử lý
│   │   └── device_registry.csv     ← Danh sách thiết bị hợp lệ
│   └── ai_service/
│       └── main.py                 ← AI Service (port 9000)
├── docker-compose.yml              ← Định nghĩa 3 service
├── Dockerfile                      ← Build image cho service api
├── .env                            ← Biến môi trường (không commit)
├── .env.example                    ← Template biến môi trường
├── IoTIngestion_README.md          ← Đặc tả nghiệp vụ nhóm IoT
└── requirements.txt                ← Python dependencies
```

---

*Báo cáo được tạo từ mã nguồn thực tế — Lab 05 FIT4110 Smart Campus IoT Ingestion Service v1.0.0*
