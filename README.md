<div align="center">

# 🏫 FIT4110 — IoT Ingestion Service

### Phân hệ tiếp nhận & xử lý dữ liệu cảm biến cho hệ thống Smart Campus

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![MQTT](https://img.shields.io/badge/MQTT-HiveMQ_Cloud-660066?style=for-the-badge&logo=mqtt&logoColor=white)](https://www.hivemq.com/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

</div>

---

## 📖 Giới thiệu

**IoT Ingestion Service** là phân hệ đứng đầu chuỗi xử lý dữ liệu trong kiến trúc **Smart Campus** — hệ thống giám sát môi trường thông minh cho trường học. Service này nhận dữ liệu cảm biến thô (nhiệt độ, độ ẩm, CO₂, khói, pin...) từ các thiết bị ESP32 thông qua MQTT broker HiveMQ Cloud, sau đó **lọc, kiểm tra, chuẩn hóa và phân loại** dữ liệu trước khi chuyển tiếp đến các service xuôi dòng.

> **Nguyên tắc cốt lõi:** Service này **không** chuyển tiếp nguyên trạng dữ liệu thô.  
> Nhiệm vụ là biến _raw sensor data_ thành _clean business event_ có ý nghĩa.

---

## 🗺️ Kiến trúc hệ thống

```
┌─────────────────────┐
│   Pi IoT Simulator  │  (Giảng viên vận hành, 24/7, mỗi 5 giây)
└──────────┬──────────┘
           │ MQTT Publish
           ▼
┌─────────────────────────────────┐
│  Topic: smart-campus/raw/iot/   │
│         environment             │  ← HiveMQ Cloud (TLS/8883)
└──────────┬──────────────────────┘
           │ Subscribe (QoS 1)
           ▼
┌──────────────────────────────────────────────────────┐
│           🔧 IoT Ingestion Service (Repo này)         │
│                                                      │
│  [1] VALIDATE → [2] CHECK → [3] NORMALIZE            │
│              → [4] CLASSIFY → [5] PRODUCE            │
└──────────┬───────────────────────────────────────────┘
           │ MQTT Publish (QoS 1)
           ▼
┌─────────────────────────────────┐
│  Topic: smart-campus/events/    │
│         sensor                  │
└────────┬──────────┬─────────────┘
         │          │
         ▼          ▼
  Core Business   Analytics
    Service        Service
```

---

## ⚙️ Pipeline xử lý dữ liệu (5 bước)

Toàn bộ logic nghiệp vụ được thực thi tuần tự trong callback `on_message()` của `main.py`:

### Bước 1 — 🛡️ VALIDATE: Kiểm tra schema đầu vào

Kiểm tra payload có đủ **7 trường bắt buộc** không. Nếu thiếu → log lỗi và **từ chối ngay, không publish**.

```python
REQUIRED_FIELDS = [
    "event_id", "event_type", "timestamp", "device_id",
    "temperature_c", "humidity_percent", "motion_detected"
]
```

| Trường             | Kiểu              | Bắt buộc |
| ------------------ | ----------------- | :------: |
| `event_id`         | string            |    ✅    |
| `event_type`       | string            |    ✅    |
| `timestamp`        | string (ISO 8601) |    ✅    |
| `device_id`        | string            |    ✅    |
| `temperature_c`    | number / null     |    ✅    |
| `humidity_percent` | number / null     |    ✅    |
| `motion_detected`  | boolean           |    ✅    |

---

### Bước 2 — 🔍 CHECK: Kiểm tra thiết bị trong registry

Đối chiếu `device_id` với danh sách thiết bị hợp lệ được load từ `device_registry.csv` khi service khởi động.

```
device_id không có trong registry
  → status = invalid_device | alert_level = high | reason = device_not_registered
  → PRODUCE ngay, dừng pipeline
```

Cấu trúc `device_registry.csv`:

```csv
device_id,device_type,location,room,status
esp32-lab-a101,environment_sensor,Lab A101,A101,active
esp32-lab-a102,environment_sensor,Lab A102,A102,active
esp32-gate-a,environment_sensor,Main Gate A,GATE-A,active
esp32-library-01,environment_sensor,Library 01,LIB-01,active
esp32-hall-b201,environment_sensor,Hall B201,B201,active
```

---

### Bước 3 — 🔧 NORMALIZE: Chuẩn hóa dữ liệu

Ba thao tác chuẩn hóa bắt buộc:

| Thao tác            | Mô tả                                                                                                                               |
| ------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| **Timestamp**       | Kiểm tra ISO 8601 bằng `datetime.fromisoformat()`. Nếu sai → tự động thay bằng UTC hiện tại                                         |
| **Kiểu số**         | Kiểm tra `temperature_c`, `humidity_percent`, `co2_ppm`, `smoke_ppm`, `battery_percent` có phải số hợp lệ không. `bool` bị loại trừ |
| **Xóa field debug** | `data.pop("scenario_hint_for_teacher", None)` — tuyệt đối không gửi field này sang downstream                                       |

---

### Bước 4 — 🏷️ CLASSIFY: Phân loại trạng thái môi trường

Áp dụng bảng rule theo thứ tự ưu tiên **sensor_error → danger → warning → normal**:

| Mức độ          | Điều kiện                         | `status`       | `alert_level` | `reason`               |
| --------------- | --------------------------------- | -------------- | ------------- | ---------------------- |
| 🔴 Lỗi cảm biến | `temp is None` HOẶC `hum is None` | `sensor_error` | `medium`      | `missing_sensor_value` |
| 🔴 Nguy hiểm    | `temperature_c >= 40`             | `danger`       | `high`        | `temperature_too_high` |
| 🔴 Nguy hiểm    | `co2_ppm >= 1800`                 | `danger`       | `high`        | `co2_too_high`         |
| 🔴 Nguy hiểm    | `smoke_ppm >= 1.0`                | `danger`       | `high`        | `smoke_detected`       |
| 🟡 Cảnh báo     | `temperature_c >= 35`             | `warning`      | `medium`      | `temperature_high`     |
| 🟡 Cảnh báo     | `humidity_percent >= 85`          | `warning`      | `medium`      | `humidity_too_high`    |
| 🟡 Cảnh báo     | `co2_ppm >= 1200`                 | `warning`      | `medium`      | `co2_high`             |
| 🟡 Cảnh báo     | `smoke_ppm >= 0.5`                | `warning`      | `medium`      | `smoke_warning`        |
| 🟡 Cảnh báo     | `battery_percent < 20`            | `warning`      | `medium`      | `low_battery`          |
| 🟢 Bình thường  | Không rơi vào điều kiện nào       | `normal`       | `none`        | `environment_normal`   |

---

### Bước 5 — 📤 PRODUCE: Đóng gói & Publish

Tạo processed event và publish lên output topic với **QoS 1** (at-least-once delivery).

```python
processed_event.update({
    "event_id":       str(uuid.uuid4()),          # UUID mới
    "event_type":     "sensor.reading.processed", # Ghi đè
    "source_service": "team-iot",
    "timestamp":      now_iso(),                  # UTC hiện tại
    "raw_event_id":   raw_data.get("event_id"),   # Giữ ID gốc để trace
    "status":         status,
    "alert_level":    alert_level,
    "reason":         reason
})
client.publish(OUTPUT_TOPIC, json.dumps(processed_event), qos=1)
```

---

## 📡 Giao thức MQTT

| Thuộc tính       | Giá trị                                               |
| ---------------- | ----------------------------------------------------- |
| **Broker**       | `f6f78e87db4a4c189dd3d706745a5e93.s1.eu.hivemq.cloud` |
| **Port**         | `8883` (TLS) / `8884` (WebSocket TLS)                 |
| **Protocol**     | MQTTv5 over TLS (`ssl.PROTOCOL_TLS_CLIENT`)           |
| **Input Topic**  | `smart-campus/raw/iot/environment`                    |
| **Output Topic** | `smart-campus/events/sensor`                          |
| **QoS**          | 1 (at-least-once)                                     |

### Payload mẫu — Input (raw từ Pi Simulator)

```json
{
  "event_id": "raw-iot-abc123",
  "event_type": "iot.environment.sampled",
  "source_service": "pi-iot-simulator",
  "device_id": "esp32-lab-a101",
  "timestamp": "2026-06-07T14:30:10+07:00",
  "location": "Lab A101",
  "temperature_c": 31.2,
  "humidity_percent": 68.5,
  "motion_detected": false,
  "co2_ppm": 650,
  "smoke_ppm": 0.02,
  "battery_percent": 87,
  "scenario_hint_for_teacher": "normal"
}
```

### Payload mẫu — Output (processed event)

```json
{
  "event_id": "a3f7c2d1-84b0-4e5f-9c12-1a2b3c4d5e6f",
  "event_type": "sensor.reading.processed",
  "source_service": "team-iot",
  "timestamp": "2026-06-07T07:30:11.123456+00:00",
  "raw_event_id": "raw-iot-abc123",
  "device_id": "esp32-lab-a101",
  "location": "Lab A101",
  "temperature_c": 31.2,
  "humidity_percent": 68.5,
  "motion_detected": false,
  "co2_ppm": 650,
  "smoke_ppm": 0.02,
  "battery_percent": 87,
  "status": "normal",
  "alert_level": "none",
  "reason": "environment_normal"
}
```

---

## 🚀 Hướng dẫn cài đặt & triển khai

### Yêu cầu hệ thống

| Công cụ                                            | Phiên bản tối thiểu               |
| -------------------------------------------------- | --------------------------------- |
| [Docker](https://docs.docker.com/get-docker/)      | 24.x trở lên                      |
| [Docker Compose](https://docs.docker.com/compose/) | v2.x trở lên (plugin)             |
| Kết nối Internet                                   | Cần thiết để kết nối HiveMQ Cloud |

### Các bước triển khai

**1. Clone repository**

```bash
git clone https://github.com/<your-username>/FIT4110-IoT-Ingestion-Service.git
cd FIT4110-IoT-Ingestion-Service
```

**2. Tạo network liên nhóm (chỉ làm một lần)**

```bash
docker network create class-net
```

**3. Cấu hình biến môi trường**

```bash
cp .env.example .env
```

Mở file `.env` và điền các giá trị thực:

```bash
# Bắt buộc phải điền
MQTT_PASSWORD=<mật_khẩu_hivemq>
POSTGRES_PASSWORD=<mật_khẩu_postgres>
AUTH_TOKEN=<secret_token_của_nhóm>

# Điền IP máy nhóm bạn khi demo trên lớp
CORE_SERVICE_URL=http://<IP_NHOM_CORE>:8000
ANALYTICS_SERVICE_URL=http://<IP_NHOM_ANALYTICS>:8000
```

**4. Build và khởi động toàn bộ stack**

```bash
docker compose up -d --build
```

**5. Kiểm tra trạng thái**

```bash
# Xem tất cả container
docker compose ps

# Kiểm tra health endpoint
curl http://localhost:8000/health

# Theo dõi log pipeline real-time
docker compose logs -f api
```

**6. Dừng hệ thống**

```bash
docker compose down
```

---

## 🔐 Cấu hình biến môi trường

Tất cả cấu hình được quản lý qua file `.env`. **Không bao giờ commit file `.env` lên Git.**

| Biến                    | Mặc định          | Bắt buộc | Mô tả                                      |
| ----------------------- | ----------------- | :------: | ------------------------------------------ |
| `APP_PORT`              | `8000`            |    ❌    | Port expose của service api                |
| `AUTH_TOKEN`            | —                 |    ✅    | Token xác thực API nội bộ                  |
| `POSTGRES_USER`         | `lab05`           |    ❌    | Username PostgreSQL                        |
| `POSTGRES_PASSWORD`     | —                 |    ✅    | Mật khẩu PostgreSQL                        |
| `POSTGRES_DB`           | `iotdb`           |    ❌    | Tên database                               |
| `CORE_SERVICE_URL`      | —                 |    ✅    | URL service nhóm Core (điền khi demo)      |
| `ANALYTICS_SERVICE_URL` | —                 |    ✅    | URL service nhóm Analytics (điền khi demo) |
| `MQTT_HOST`             | `...hivemq.cloud` |    ❌    | HiveMQ broker hostname                     |
| `MQTT_PORT`             | `8883`            |    ❌    | Port MQTTS                                 |
| `MQTT_USERNAME`         | `DVKN_IOT_2026`   |    ❌    | Username HiveMQ                            |
| `MQTT_PASSWORD`         | —                 |    ✅    | Mật khẩu HiveMQ                            |

---

## 🧩 Cấu trúc dự án

```
FIT4110-IoT-Ingestion-Service/
├── src/
│   ├── iot_app/
│   │   ├── main.py                 # 🔑 Core pipeline: VALIDATE→CHECK→NORMALIZE→CLASSIFY→PRODUCE
│   │   └── device_registry.csv     # Danh sách thiết bị ESP32 hợp lệ
│   └── ai_service/
│       └── main.py                 # AI Service phụ trợ (port 9000)
├── docker-compose.yml              # Orchestration: api + db + ai-service
├── Dockerfile                      # Build image cho IoT Ingestion Service
├── requirements.txt                # Python dependencies
├── .env.example                    # Template biến môi trường (safe to commit)
├── .env                            # ⚠️ Cấu hình thực — KHÔNG commit lên Git
├── .gitignore
└── README.md
```

---

## 🩺 Health Check API

| Endpoint  | Method | Mô tả                       |
| --------- | ------ | --------------------------- |
| `/health` | `GET`  | Kiểm tra trạng thái service |

**Response mẫu:**

```json
{
  "status": "ok",
  "service": "iot-ingestion",
  "version": "1.0.0",
  "devices_loaded": 5,
  "input_topic": "smart-campus/raw/iot/environment",
  "output_topic": "smart-campus/events/sensor"
}
```

---

## 🐛 Troubleshooting

| Triệu chứng                              | Nguyên nhân có thể                                 | Giải pháp                                               |
| ---------------------------------------- | -------------------------------------------------- | ------------------------------------------------------- |
| Container `api` ở trạng thái `unhealthy` | `db` hoặc `ai-service` chưa sẵn sàng               | Chờ healthcheck pass, kiểm tra `docker compose logs db` |
| Không nhận được message MQTT             | Sai credential hoặc mất kết nối TLS                | Kiểm tra `MQTT_USERNAME`, `MQTT_PASSWORD` trong `.env`  |
| `[REGISTRY] KHÔNG TÌM THẤY file`         | `device_registry.csv` chưa có trong `src/iot_app/` | Đảm bảo file CSV tồn tại đúng đường dẫn                 |
| Network `class-net` not found            | Chưa tạo external network                          | Chạy `docker network create class-net`                  |
| `[VALIDATE] Thiếu N trường bắt buộc`     | Simulator đang gửi payload không đúng schema       | Kiểm tra log Pi Simulator, liên hệ giảng viên           |

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

---

<div align="center">

**FIT4110 — Dịch vụ Kết nối và Nền tảng Nội dung Thông minh**  
IoT Ingestion Service v1.0.0 · Smart Campus Project

</div>
