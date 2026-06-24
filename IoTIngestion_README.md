# IoT Ingestion Service - Nhận dữ liệu môi trường từ HiveMQ

## 1. Mục tiêu của nhóm IoT

Nhóm **IoT Ingestion** xây dựng service nhận dữ liệu môi trường dạng **raw sensor data** từ HiveMQ, kiểm tra dữ liệu đầu vào, chuẩn hóa, phân loại trạng thái môi trường, sau đó gửi kết quả đã xử lý sang các service tiếp theo:

```text
Pi IoT Simulator
→ HiveMQ topic: smart-campus/raw/iot/environment
→ IoT Ingestion Service
→ Validate + Normalize + Classify + Transform
→ HiveMQ topic: smart-campus/events/sensor
→ Core Business
→ Analytics
```

Nhóm IoT **không chỉ đọc dữ liệu rồi chuyển tiếp nguyên trạng**. Nhiệm vụ chính là biến dữ liệu cảm biến raw thành **event sạch, có ý nghĩa nghiệp vụ**, để nhóm Core và nhóm Analytics có thể sử dụng.

---

## 2. Thông tin kết nối HiveMQ

```text
Broker Host:
f6f78e87db4a4c189dd3d706745a5e93.s1.eu.hivemq.cloud

MQTT Port:
8883

Protocol:
MQTTS / MQTT over TLS

Username:
DVKN_IOT_2026

Password:
ThaiBao12A@

Input topic:
smart-campus/raw/iot/environment

Output topic:
smart-campus/events/sensor
```

Nếu dùng MQTT qua WebSocket:

```text
WebSocket URL:
wss://f6f78e87db4a4c189dd3d706745a5e93.s1.eu.hivemq.cloud:8884/mqtt
```

> **Lưu ý bảo mật:** Credential trên dùng riêng cho nhóm IoT Ingestion trong môi trường thực hành. Khi nộp bài, không commit mật khẩu thật vào Git công khai. Hãy dùng file `.env` và `.gitignore` đúng chuẩn.

---

## 3. Nguồn sinh data

Pi IoT Simulator do **giảng viên vận hành, chạy liên tục 24/7** và đẩy event mỗi 5 giây lên topic `smart-campus/raw/iot/environment`.

```text
- Sinh viên KHÔNG cần tự build simulator.
- Sinh viên chỉ subscribe topic, xử lý event và publish kết quả.
- Nếu không nhận được data trong 1-2 phút, kiểm tra:
  1. Kết nối Internet và TLS cert.
  2. Username/password đã đúng chưa.
  3. Tên topic chính xác chưa.
  4. Nếu vẫn không nhận được data, liên hệ giảng viên kiểm tra simulator.
```

Simulator phát đủ các scenario: `normal`, `high_temperature`, `high_humidity`, `motion_detected`, `high_co2`, `smoke_detected`, `low_battery`, `sensor_error`, `unknown_device`. Field `scenario_hint_for_teacher` chỉ ra scenario hiện tại để giảng viên chấm điểm, sinh viên không được dùng field này trong logic.

---

## 4. Dữ liệu nhóm IoT nhận được

Nhóm IoT subscribe topic:

```text
smart-campus/raw/iot/environment
```

Cứ khoảng **5 giây** sẽ có một gói dữ liệu môi trường được gửi lên.

### Payload raw mẫu

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
  "light_lux": 420,
  "co2_ppm": 650,
  "smoke_ppm": 0.02,
  "battery_percent": 87,
  "scenario_hint_for_teacher": "normal"
}
```

### Lưu ý quan trọng

```text
- Đây là dữ liệu raw từ cảm biến.
- Dữ liệu raw chưa có kết luận normal / warning / danger.
- Dữ liệu raw chưa có alert_level.
- Dữ liệu raw có thể chứa lỗi: null, thiết bị lạ, giá trị vượt ngưỡng.
- Field scenario_hint_for_teacher chỉ để giảng viên debug, sinh viên KHÔNG được phụ thuộc vào field này để xử lý nghiệp vụ.
- Sinh viên sử dụng scenario_hint_for_teacher để quyết định status/alert_level sẽ bị trừ điểm.
```

---

## 5. Ý nghĩa các field dữ liệu

| Field | Kiểu dữ liệu | Ý nghĩa | Ví dụ |
|---|---|---|---|
| `event_id` | string | Mã sự kiện raw | `raw-iot-abc123` |
| `event_type` | string | Loại event | `iot.environment.sampled` |
| `source_service` | string | Nguồn sinh dữ liệu | `pi-iot-simulator` |
| `device_id` | string | Mã thiết bị cảm biến | `esp32-lab-a101` |
| `timestamp` | string | Thời điểm lấy mẫu | `2026-06-07T14:30:10+07:00` |
| `location` | string | Vị trí thiết bị | `Lab A101` |
| `temperature_c` | number/null | Nhiệt độ Celsius | `31.2` |
| `humidity_percent` | number/null | Độ ẩm phần trăm | `68.5` |
| `motion_detected` | boolean | Có chuyển động hay không | `false` |
| `light_lux` | number | Cường độ ánh sáng | `420` |
| `co2_ppm` | number | Nồng độ CO2 | `650` |
| `smoke_ppm` | number | Mức khói/khí bất thường | `0.02` |
| `battery_percent` | number | Pin thiết bị | `87` |

---

## 6. Các tình huống dữ liệu có thể gặp

| Scenario | Mô tả | Gợi ý xử lý |
|---|---|---|
| `normal` | Dữ liệu bình thường | `status = normal` |
| `high_temperature` | Nhiệt độ cao | `warning` hoặc `danger` |
| `high_humidity` | Độ ẩm cao | `warning` |
| `motion_detected` | Có chuyển động | Có thể gửi để Core kiểm tra theo giờ |
| `high_co2` | CO2 cao | `warning` hoặc `danger` |
| `smoke_detected` | Có khói | `warning` hoặc `danger` |
| `low_battery` | Pin yếu | `warning` |
| `sensor_error` | Cảm biến lỗi, field bị null | `sensor_error` |
| `unknown_device` | Thiết bị không có trong registry | `invalid_device` |

---

## 7. File danh sách thiết bị hợp lệ

Nhóm IoT được cung cấp file:

```text
device_registry.csv
```

Cấu trúc:

```csv
device_id,device_type,location,room,status
esp32-lab-a101,environment_sensor,Lab A101,A101,active
esp32-lab-a102,environment_sensor,Lab A102,A102,active
esp32-gate-a,environment_sensor,Main Gate A,GATE-A,active
esp32-library-01,environment_sensor,Library 01,LIB-01,active
esp32-hall-b201,environment_sensor,Hall B201,B201,active
```

Yêu cầu:

```text
- Service phải đọc danh sách thiết bị từ device_registry.csv hoặc database.
- Không hard-code toàn bộ danh sách thiết bị trong code xử lý chính.
- Nếu device_id không tồn tại trong registry thì gắn status = invalid_device.
```

---

## 8. Việc nhóm IoT phải làm trước khi gửi sang Core và Analytics

Trước khi publish dữ liệu sang topic `smart-campus/events/sensor`, nhóm IoT phải xử lý qua các bước sau:

### 8.1. Subscribe dữ liệu raw

Subscribe topic:

```text
smart-campus/raw/iot/environment
```

Nhận payload JSON từ HiveMQ.

---

### 8.2. Validate schema đầu vào

Kiểm tra các field bắt buộc:

```text
event_id
event_type
timestamp
device_id
temperature_c
humidity_percent
motion_detected
```

Nếu thiếu field bắt buộc, service phải log lỗi và không được publish event sai schema sang service tiếp theo.

Ví dụ lỗi:

```json
{
  "error": "missing_required_field",
  "missing_fields": ["temperature_c"]
}
```

---

### 8.3. Kiểm tra thiết bị

Đối chiếu `device_id` với `device_registry.csv`.

```text
Nếu device_id hợp lệ:
  tiếp tục xử lý

Nếu device_id không tồn tại:
  status = invalid_device
  alert_level = high
  reason = device_not_registered
```

---

### 8.4. Chuẩn hóa dữ liệu

Nhóm cần chuẩn hóa dữ liệu trước khi gửi đi:

```text
- Giữ thống nhất đơn vị nhiệt độ là Celsius.
- Giữ thống nhất độ ẩm theo phần trăm.
- Kiểm tra timestamp đúng ISO 8601.
- Ép kiểu number/boolean nếu cần.
- Loại bỏ field chỉ dùng để debug như scenario_hint_for_teacher.
```

Không gửi field `scenario_hint_for_teacher` sang Core và Analytics.

---

### 8.5. Phân loại trạng thái môi trường

Gợi ý rule:

```text
sensor_error:
- temperature_c = null
- humidity_percent = null
- dữ liệu không đúng kiểu số

invalid_device:
- device_id không tồn tại trong device_registry.csv

danger:
- temperature_c >= 40
- co2_ppm >= 1800
- smoke_ppm >= 1.0

warning:
- temperature_c >= 35
- humidity_percent >= 85
- co2_ppm >= 1200
- smoke_ppm >= 0.5
- battery_percent < 20

normal:
- Không rơi vào các trường hợp trên
```

---

### 8.6. Tạo processed event

Sau khi validate và phân loại, nhóm IoT phải tạo event mới theo schema thống nhất.

Output topic:

```text
smart-campus/events/sensor
```

---

## 9. Payload gửi sang Core và Analytics

### 9.1. Payload khi dữ liệu bình thường

```json
{
  "event_id": "sensor-event-001",
  "event_type": "sensor.reading.processed",
  "source_service": "team-iot",
  "timestamp": "2026-06-07T14:30:11+07:00",
  "raw_event_id": "raw-iot-abc123",
  "device_id": "esp32-lab-a101",
  "location": "Lab A101",
  "temperature_c": 31.2,
  "humidity_percent": 68.5,
  "motion_detected": false,
  "light_lux": 420,
  "co2_ppm": 650,
  "smoke_ppm": 0.02,
  "battery_percent": 87,
  "status": "normal",
  "alert_level": "none",
  "reason": "environment_normal"
}
```

### 9.2. Payload khi nhiệt độ nguy hiểm

```json
{
  "event_id": "sensor-event-002",
  "event_type": "sensor.reading.processed",
  "source_service": "team-iot",
  "timestamp": "2026-06-07T14:30:16+07:00",
  "raw_event_id": "raw-iot-def456",
  "device_id": "esp32-lab-a101",
  "location": "Lab A101",
  "temperature_c": 42.1,
  "humidity_percent": 71.2,
  "motion_detected": true,
  "light_lux": 390,
  "co2_ppm": 710,
  "smoke_ppm": 0.03,
  "battery_percent": 86,
  "status": "danger",
  "alert_level": "high",
  "reason": "temperature_too_high"
}
```

### 9.3. Payload khi thiết bị lạ

```json
{
  "event_id": "sensor-event-003",
  "event_type": "sensor.reading.processed",
  "source_service": "team-iot",
  "timestamp": "2026-06-07T14:30:20+07:00",
  "raw_event_id": "raw-iot-ghi789",
  "device_id": "esp32-unknown-01",
  "location": "Unknown Area",
  "temperature_c": 30.1,
  "humidity_percent": 66.0,
  "motion_detected": false,
  "light_lux": 300,
  "co2_ppm": 700,
  "smoke_ppm": 0.01,
  "battery_percent": 92,
  "status": "invalid_device",
  "alert_level": "high",
  "reason": "device_not_registered"
}
```

### 9.4. Payload khi lỗi cảm biến

```json
{
  "event_id": "sensor-event-004",
  "event_type": "sensor.reading.processed",
  "source_service": "team-iot",
  "timestamp": "2026-06-07T14:30:25+07:00",
  "raw_event_id": "raw-iot-jkl012",
  "device_id": "esp32-lab-a102",
  "location": "Lab A102",
  "temperature_c": null,
  "humidity_percent": 70.2,
  "motion_detected": false,
  "light_lux": 410,
  "co2_ppm": 600,
  "smoke_ppm": 0.01,
  "battery_percent": 77,
  "status": "sensor_error",
  "alert_level": "medium",
  "reason": "missing_sensor_value"
}
```

---

## 10. Core và Analytics sẽ dùng dữ liệu này như thế nào?

### 10.1. Nhóm Core Business

Core Business subscribe:

```text
smart-campus/events/sensor
```

Core dùng dữ liệu để:

```text
- Kiểm tra policy ngưỡng nhiệt độ, khói, CO2.
- Tạo alert nếu status = warning hoặc danger.
- Kết hợp motion_detected với khung giờ để phát hiện bất thường.
- Gửi alert sang Notification nếu cần.
```

Ví dụ Core có thể tạo alert khi:

```text
status = danger
hoặc reason = smoke_detected
hoặc temperature_c >= 40
hoặc motion_detected = true ngoài giờ cho phép
```

---

### 10.2. Nhóm Analytics

Analytics subscribe:

```text
smart-campus/events/sensor
```

Analytics dùng dữ liệu để:

```text
- Tính nhiệt độ trung bình theo phòng.
- Tính độ ẩm trung bình theo thời gian.
- Đếm số lần warning/danger theo ngày.
- Theo dõi pin yếu theo thiết bị.
- Vẽ biểu đồ CO2, smoke, temperature theo timeline.
- Tổng hợp KPI môi trường cho dashboard.
```

Ví dụ metric:

```text
avg_temperature_by_room
avg_humidity_by_room
danger_event_count_by_day
low_battery_device_count
co2_warning_count
smoke_alert_count
```

---

## 11. Test nhận dữ liệu bằng Python

Cài thư viện:

```bash
pip install paho-mqtt
```

Code subscribe tối thiểu:

```python
import ssl
from paho.mqtt import client as mqtt

MQTT_HOST = "f6f78e87db4a4c189dd3d706745a5e93.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_USERNAME = "DVKN_IOT_2026"
MQTT_PASSWORD = "ThaiBao12A@"

TOPIC = "smart-campus/raw/iot/environment"


def on_connect(client, userdata, flags, reason_code, properties=None):
    print("Connected:", reason_code)
    client.subscribe(TOPIC, qos=1)


def on_message(client, userdata, message):
    print("Topic:", message.topic)
    print("Payload:", message.payload.decode())


client = mqtt.Client(protocol=mqtt.MQTTv5)
client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
client.tls_set(tls_version=ssl.PROTOCOL_TLS_CLIENT)

client.on_connect = on_connect
client.on_message = on_message

client.connect(MQTT_HOST, MQTT_PORT)
client.loop_forever()
```

Khi triển khai thực tế, nên đẩy credential vào `.env`:

```bash
# .env
MQTT_HOST=f6f78e87db4a4c189dd3d706745a5e93.s1.eu.hivemq.cloud
MQTT_PORT=8883
MQTT_USERNAME=DVKN_IOT_2026
MQTT_PASSWORD=ThaiBao12A@
```

Và đọc bằng `python-dotenv`:

```python
import os
from dotenv import load_dotenv

load_dotenv()
MQTT_USERNAME = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")
```
