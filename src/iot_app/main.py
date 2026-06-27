"""
IoT Ingestion Service — Smart Campus
=====================================
Pipeline xử lý: VALIDATE → CHECK → NORMALIZE → CLASSIFY → PRODUCE
Subscribe: smart-campus/raw/iot/environment
Publish:   smart-campus/events/sensor
"""

import os
import json
import ssl
import uuid
import csv
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from fastapi import FastAPI
import paho.mqtt.client as mqtt


# ╔══════════════════════════════════════════════════════════════╗
# ║                        CẤU HÌNH                             ║
# ╚══════════════════════════════════════════════════════════════╝
SERVICE_NAME = os.getenv("SERVICE_NAME", "iot-ingestion")
SERVICE_VERSION = "1.0.0"

MQTT_HOST = os.getenv("MQTT_HOST", "f6f78e87db4a4c189dd3d706745a5e93.s1.eu.hivemq.cloud")
MQTT_PORT = int(os.getenv("MQTT_PORT", "8883"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")

INPUT_TOPIC = "smart-campus/raw/iot/environment"
OUTPUT_TOPIC = "smart-campus/events/sensor"

app = FastAPI(title="FIT4110 Lab 05 - IoT Ingestion", version=SERVICE_VERSION)
mqtt_client: Optional[mqtt.Client] = None


REQUIRED_FIELDS = [
    "event_id", "event_type", "timestamp", "device_id",
    "temperature_c", "humidity_percent", "motion_detected"
]

NUMERIC_SENSOR_FIELDS = [
    "temperature_c", "humidity_percent", "light_lux", "co2_ppm",
    "smoke_ppm", "battery_percent"
]


# ╔══════════════════════════════════════════════════════════════╗
# ║              LOAD DEVICE REGISTRY (Mục 2)                   ║
# ╚══════════════════════════════════════════════════════════════╝
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REGISTRY_FILE = os.path.join(BASE_DIR, "device_registry.csv")

device_registry: Dict[str, Dict] = {}

if os.path.exists(REGISTRY_FILE):
    with open(REGISTRY_FILE, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            device_registry[row["device_id"]] = row
    print(f"✅ [REGISTRY] Đã load {len(device_registry)} thiết bị: "
          f"{list(device_registry.keys())}", flush=True)
else:
    print(f"⚠️ [REGISTRY] KHÔNG TÌM THẤY file {REGISTRY_FILE}!", flush=True)


# ╔══════════════════════════════════════════════════════════════╗
# ║                     UTILS / HELPERS                          ║
# ╚══════════════════════════════════════════════════════════════╝
def now_iso() -> str:
    """Trả về thời gian hiện tại theo chuẩn ISO 8601."""
    return datetime.now(timezone.utc).isoformat()


def is_number(value) -> bool:
    """Kiểm tra giá trị có phải kiểu số hợp lệ không (loại trừ bool)."""
    if isinstance(value, bool):
        return False
    return isinstance(value, (int, float))


def is_valid_iso8601(timestamp_str) -> bool:
    """Kiểm tra timestamp có đúng chuẩn ISO 8601 không."""
    if not isinstance(timestamp_str, str):
        return False
    try:
        datetime.fromisoformat(timestamp_str)
        return True
    except (ValueError, TypeError):
        return False


# ╔══════════════════════════════════════════════════════════════╗
# ║        MỤC 1 — VALIDATE: Kiểm tra schema đầu vào           ║
# ╚══════════════════════════════════════════════════════════════╝
def validate_schema(data: Dict) -> List[str]:
    """
    Kiểm tra payload có đủ 7 trường bắt buộc không.
    Trả về danh sách tất cả field thiếu (rỗng = hợp lệ).
    Nếu thiếu → log lỗi, KHÔNG publish.
    """
    missing = [f for f in REQUIRED_FIELDS if f not in data]
    if missing:
        print(f"⚠️ [VALIDATE] Thiếu {len(missing)} trường bắt buộc: {missing}", flush=True)
    return missing


# ╔══════════════════════════════════════════════════════════════╗
# ║    MỤC 2 — CHECK: Kiểm tra thiết bị trong registry          ║
# ╚══════════════════════════════════════════════════════════════╝
def check_device(device_id: str) -> bool:
    """
    Đối chiếu device_id với device_registry.csv.
    Trả True nếu hợp lệ, False nếu thiết bị lạ.
    """
    is_valid = device_id in device_registry
    if not is_valid:
        print(f"🚫 [CHECK] Thiết bị lạ: {device_id} — không có trong registry", flush=True)
    return is_valid


# ╔══════════════════════════════════════════════════════════════╗
# ║   MỤC 3 — NORMALIZE: Chuẩn hóa dữ liệu đầu vào           ║
# ╚══════════════════════════════════════════════════════════════╝
def normalize_data(data: Dict) -> Tuple[Dict, Optional[str]]:
    """
    Chuẩn hóa dữ liệu:
    - Kiểm tra timestamp ISO 8601, sửa nếu sai.
    - Kiểm tra kiểu dữ liệu số cho các sensor field.
    - Loại bỏ field scenario_hint_for_teacher.
    Trả về (data_đã_chuẩn_hóa, tên_field_lỗi_kiểu_số | None).
    """
    # 3a. Kiểm tra & sửa timestamp
    if not is_valid_iso8601(data.get("timestamp", "")):
        print(f"⚠️ [NORMALIZE] Timestamp không đúng ISO 8601 → thay bằng UTC hiện tại", flush=True)
        data["timestamp"] = now_iso()

    # 3b. Kiểm tra kiểu dữ liệu số cho từng sensor field
    for field in NUMERIC_SENSOR_FIELDS:
        value = data.get(field)
        if value is not None:
            if isinstance(value, str):
                try:
                    data[field] = float(value)
                except ValueError:
                    print(f"⚠️ [NORMALIZE] Trường '{field}' không thể ép kiểu số: {value}", flush=True)
                    return data, field
            elif not is_number(value):
                print(f"⚠️ [NORMALIZE] Trường '{field}' sai kiểu: {value} ({type(value).__name__})", flush=True)
                return data, field  # Trả về tên field lỗi

    # 3c. Ép kiểu boolean cho motion_detected
    motion = data.get("motion_detected")
    if isinstance(motion, str):
        if motion.lower() == "true":
            data["motion_detected"] = True
        elif motion.lower() == "false":
            data["motion_detected"] = False

    # 3d. Loại bỏ field debug (giảng viên KHÔNG cho phép dùng)
    data.pop("scenario_hint_for_teacher", None)

    return data, None


# ╔══════════════════════════════════════════════════════════════╗
# ║  MỤC 4 — CLASSIFY: Phân loại trạng thái môi trường          ║
# ╚══════════════════════════════════════════════════════════════╝
def classify_environment(data: Dict) -> Tuple[str, str, str]:
    """
    Phân loại theo bảng rule:
      sensor_error → null hoặc sai kiểu số
      danger       → temp>=40 | co2>=1800 | smoke>=1.0
      warning      → temp>=35 | hum>=85 | co2>=1200 | smoke>=0.5 | batt<20
      normal       → tất cả OK
    Trả về (status, alert_level, reason).
    """
    temp = data.get("temperature_c")
    hum = data.get("humidity_percent")
    co2 = data.get("co2_ppm")
    smoke = data.get("smoke_ppm")
    batt = data.get("battery_percent")

    # Bước 1: sensor_error — giá trị null (thiếu dữ liệu sensor)
    if temp is None or hum is None:
        return "sensor_error", "medium", "missing_sensor_value"

    # Bước 2: danger — ngưỡng nguy hiểm
    if temp >= 40:
        return "danger", "high", "temperature_too_high"
    if co2 is not None and co2 >= 1800:
        return "danger", "high", "co2_too_high"
    if smoke is not None and smoke >= 1.0:
        return "danger", "high", "smoke_detected"

    # Bước 3: warning — ngưỡng cảnh báo
    if temp >= 35:
        return "warning", "medium", "temperature_high"
    if hum >= 85:
        return "warning", "medium", "humidity_too_high"
    if co2 is not None and co2 >= 1200:
        return "warning", "medium", "co2_high"
    if smoke is not None and smoke >= 0.5:
        return "warning", "medium", "smoke_warning"
    if batt is not None and batt < 20:
        return "warning", "medium", "low_battery"

    # Bước 4: normal
    return "normal", "none", "environment_normal"


# ╔══════════════════════════════════════════════════════════════╗
# ║  MỤC 5 — PRODUCE: Đóng gói & Publish lên MQTT               ║
# ╚══════════════════════════════════════════════════════════════╝
def produce_event(client, raw_data: Dict, status: str,
                  alert_level: str, reason: str) -> None:
    """
    Tạo processed event và publish lên OUTPUT_TOPIC.
    - Loại bỏ scenario_hint_for_teacher (đã xử lý ở normalize).
    - Ghi đè event_id, event_type, source_service, timestamp.
    - Thêm raw_event_id, status, alert_level, reason.
    """
    processed_event = raw_data.copy()

    # Đảm bảo lần nữa: tuyệt đối không gửi field debug
    processed_event.pop("scenario_hint_for_teacher", None)

    processed_event.update({
        "event_id": str(uuid.uuid4()),
        "event_type": "sensor.reading.processed",
        "source_service": "team-iot",
        "timestamp": now_iso(),
        "raw_event_id": raw_data.get("event_id"),
        "status": status,
        "alert_level": alert_level,
        "reason": reason
    })

    payload_json = json.dumps(processed_event)
    msg_info = client.publish(OUTPUT_TOPIC, payload_json, qos=1)

    if msg_info.rc != mqtt.MQTT_ERR_SUCCESS:
        print(f"❌ [PRODUCE ERROR] Lỗi không thể đẩy dữ liệu lên hàng đợi (mã lỗi: {msg_info.rc})", flush=True)
    else:
        print(f"📤 [PRODUCE] Chuẩn bị gửi (mid={msg_info.mid}) → {OUTPUT_TOPIC} | "
              f"status={status} | alert={alert_level} | reason={reason}", flush=True)
        
        # Thêm log hiển thị rõ các thuộc tính theo nhu cầu của Core và Analytics
        core_keys = [k for k in ["status", "alert_level", "reason", "temperature_c", "co2_ppm", "smoke_ppm", "motion_detected"] if k in processed_event and processed_event[k] is not None]
        ana_keys = [k for k in ["temperature_c", "humidity_percent", "co2_ppm", "smoke_ppm", "battery_percent", "status", "alert_level"] if k in processed_event and processed_event[k] is not None]
        
        print(f"   ├── Đã gửi thuộc tính {', '.join(core_keys)} đến Core", flush=True)
        print(f"   └── Đã gửi thuộc tính {', '.join(ana_keys)} đến ana", flush=True)



def on_message(client, userdata, message):
    """Callback xử lý mỗi message MQTT nhận được."""
    try:
        raw_data = json.loads(message.payload.decode())
        device_id = raw_data.get("device_id", "unknown")

        print(f"\n{'='*60}", flush=True)
        print(f"📥 [MQTT IN] device={device_id} | temp={raw_data.get('temperature_c')} | "
              f"hum={raw_data.get('humidity_percent')} | co2={raw_data.get('co2_ppm')} | "
              f"smoke={raw_data.get('smoke_ppm')} | batt={raw_data.get('battery_percent')}",
              flush=True)

        missing_fields = validate_schema(raw_data)
        if missing_fields:
            print(f"❌ [REJECTED] {json.dumps({'error': 'missing_required_field', 'missing_fields': missing_fields})}",
                  flush=True)
            return  # KHÔNG publish

        if not check_device(device_id):
            status, alert_level, reason = "invalid_device", "high", "device_not_registered"
            raw_data, _ = normalize_data(raw_data)
            produce_event(client, raw_data, status, alert_level, reason)
            return
        
        # Nếu thiết bị hợp lệ, đồng bộ vị trí (location) từ registry để chống sai lệch từ sensor
        raw_data["location"] = device_registry[device_id].get("location", raw_data.get("location"))

        # ──── MỤC 3: NORMALIZE ────
        raw_data, bad_field = normalize_data(raw_data)
        if bad_field:
            # Dữ liệu rác (ví dụ: temperature_c = "abc") → sensor_error
            produce_event(client, raw_data, "sensor_error", "medium", "invalid_sensor_data_type")
            return

        # ──── MỤC 4: CLASSIFY ────
        status, alert_level, reason = classify_environment(raw_data)

        # ──── MỤC 5: PRODUCE ────
        produce_event(client, raw_data, status, alert_level, reason)

    except json.JSONDecodeError as e:
        print(f"❌ [JSON ERROR] Payload không phải JSON hợp lệ: {e}", flush=True)
    except Exception as e:
        print(f"❌ [PIPELINE ERROR] {e}", flush=True)


def on_connect_callback(client, userdata, flags, reason_code, properties=None):
    """Kiểm tra mã lỗi trả về khi kết nối MQTT broker."""
    if str(reason_code) == "Success" or reason_code == 0:
        print(f"✅ [MQTT] Kết nối THÀNH CÔNG! (Reason: {reason_code})", flush=True)
        client.subscribe(INPUT_TOPIC, qos=1)
        print(f"✅ [MQTT] Subscribed: {INPUT_TOPIC}", flush=True)
    else:
        print(f"❌ [MQTT] Kết nối THẤT BẠI. Reason: {reason_code}", flush=True)

def on_publish_callback(client, userdata, mid, *args):
    """Xác nhận broker đã nhận được gói tin (QoS 1) dành cho Core và Analytics."""
    print(f"📬 [MQTT OUT] Xác nhận (mid={mid}) đã GỬI THÀNH CÔNG cho Core & Analytics!", flush=True)

@app.on_event("startup")
def startup_event():
    global mqtt_client
    try:
        mqtt_client = mqtt.Client(protocol=mqtt.MQTTv5)
        mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        mqtt_client.tls_set(tls_version=ssl.PROTOCOL_TLS_CLIENT)
        mqtt_client.on_connect = on_connect_callback
        mqtt_client.on_message = on_message
        mqtt_client.on_publish = on_publish_callback
        mqtt_client.connect(MQTT_HOST, MQTT_PORT)
        mqtt_client.loop_start()
        print(f"🚀 [SYSTEM] IoT Ingestion Service v{SERVICE_VERSION} started!", flush=True)
        print(f"   ├── Subscribe: {INPUT_TOPIC}", flush=True)
        print(f"   └── Publish:   {OUTPUT_TOPIC}", flush=True)
    except Exception as e:
        print(f"❌ [SYSTEM ERROR] Lỗi kết nối MQTT: {e}", flush=True)


@app.on_event("shutdown")
def shutdown_event():
    if mqtt_client:
        mqtt_client.loop_stop()
        print("🛑 [SYSTEM] MQTT disconnected.", flush=True)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "devices_loaded": len(device_registry),
        "input_topic": INPUT_TOPIC,
        "output_topic": OUTPUT_TOPIC
    }