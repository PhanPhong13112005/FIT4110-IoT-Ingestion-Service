# README — Test tích hợp từ xa bằng Radmin VPN cho Buổi 6

**Học phần:** FIT4110 — Dịch vụ kết nối và Công nghệ nền tảng  
**Mục đích:** Thống nhất một phương án để các nhóm có thể test tích hợp từ xa ở nhà, đồng thời dùng lại được ở lớp khi iPhone hotspot bị giới hạn số thiết bị truy cập.

---

## 1. Vấn đề cần giải quyết

Trong Buổi 6, các nhóm cần kiểm tra service của mình có tích hợp được với nhóm khác hay không.

Nếu dùng iPhone hotspot trực tiếp, iPhone thường bị giới hạn số thiết bị kết nối. Khi nhiều nhóm cùng vào lớp, một hotspot có thể không đủ cho tất cả máy demo.

Ngoài ra, trước khi đến lớp, nhiều nhóm muốn ngồi ở nhà nhưng vẫn test được với nhóm khác. Khi đó, các nhóm không ở cùng một Wi-Fi vật lý nên không thể gọi nhau bằng IP LAN thông thường.

Vì vậy, lớp thống nhất dùng **Radmin VPN** như một phương án mạng LAN ảo.

---

## 2. Ý tưởng chính

Mỗi nhóm vẫn có thể tự dùng mạng riêng:

- Wi-Fi nhà riêng
- 4G/5G cá nhân
- Wi-Fi trường
- Hotspot laptop
- Router mini

Nhưng **máy demo chính của mỗi nhóm phải cài Radmin VPN và join chung một Radmin Network**.

Khi đó, các nhóm sẽ gọi service của nhau bằng **Radmin IP**, không dùng IP Wi-Fi/hotspot.

```text
Nhóm A dùng Wi-Fi nhà
Nhóm B dùng 4G
Nhóm C dùng Wi-Fi trường
        ↓
Tất cả cùng join Radmin VPN Network
        ↓
Các nhóm gọi nhau bằng Radmin IP
```

Ví dụ:

```text
team-iot       Radmin IP: 26.10.10.11
team-core      Radmin IP: 26.10.10.12
team-notify    Radmin IP: 26.10.10.13
```

team-iot gọi team-core:

```bash
curl http://26.10.10.12:8000/health
```

---

## 3. Lợi ích của phương án này

### 3.1. Test từ xa ở nhà được

Các nhóm không cần ngồi cùng phòng vẫn có thể test tích hợp:

```text
team-camera ở nhà
team-vision ở ký túc xá
team-core ở quán cà phê
        ↓
Cùng join Radmin VPN
        ↓
Gọi API qua Radmin IP
```

### 3.2. Lên lớp không cần đổi cấu hình mạng nhiều

Nếu trước đó các nhóm đã dùng Radmin IP trong file `.env`, khi lên lớp vẫn giữ nguyên cách gọi này.

Không cần chuyển từ:

```text
IP ở nhà → IP hotspot iPhone → IP router lớp
```

Mà chỉ cần tiếp tục dùng:

```text
Radmin IP của nhóm đối tác
```

Lưu ý: điều này đúng khi nhóm vẫn dùng **cùng máy demo** và **cùng Radmin Network**.

### 3.3. Tránh giới hạn thiết bị của iPhone hotspot

Khi lên lớp, mỗi máy vẫn có thể dùng mạng riêng. Miễn là có Internet để Radmin VPN hoạt động, các nhóm vẫn có thể gọi nhau qua Radmin IP.

---

## 4. Quy định chung của lớp

### 4.1. Mỗi nhóm chỉ cử một máy demo chính

Không cần tất cả thành viên cài Radmin VPN.

```text
1 nhóm = 1 máy demo chính join Radmin VPN
```

Máy demo chính là máy chạy:

```bash
docker compose up -d --build
```

### 4.2. Không cho toàn bộ sinh viên join một mạng

Nếu lớp đông, không cho 100–200 sinh viên cùng join một Radmin Network.

Chỉ máy demo chính của từng nhóm join.

Ví dụ:

```text
30 nhóm → chỉ cần khoảng 30 máy demo join
```

Nếu số nhóm quá nhiều, chia thành nhiều network theo Product hoặc cụm demo:

```text
FIT4110-DEMO-A
FIT4110-DEMO-B
FIT4110-DEMO-C
FIT4110-DEMO-D
```

### 4.3. Các nhóm có tích hợp với nhau phải join cùng một Radmin Network

Ví dụ:

```text
team-camera → team-vision → team-core → team-notify
```

Các nhóm này phải nằm trong cùng một Radmin Network thì mới gọi nhau bằng Radmin IP được.

---

## 5. Cài đặt Radmin VPN

### 5.1. Yêu cầu hệ điều hành

Radmin VPN dùng cho Windows. Máy demo nên là máy Windows 10/11. Nếu nhóm dùng macOS hoặc Linux làm máy chính, nhóm cần chọn một máy Windows khác làm máy demo hoặc thống nhất với giảng viên phương án VPN khác.

### 5.2. Tải Radmin VPN

Tải từ trang chính thức:

```text
https://www.radmin-vpn.com/vi/
```

Cài đặt như phần mềm Windows thông thường.

Sau khi cài xong, mở Radmin VPN và đặt tên máy dễ nhận diện, ví dụ:

```text
team-core-demo
team-vision-demo
team-notify-demo
```

---

## 6. Tạo Radmin Network

Giảng viên hoặc nhóm trưởng Product tạo network.

Trong Radmin VPN:

```text
Network → Create Network
```

Nhập thông tin, ví dụ:

```text
Network name: FIT4110-DEMO-A
Password: fit4110-demo-A@2026
```

Khuyến nghị đặt mật khẩu đủ mạnh, không dùng mật khẩu quá đơn giản như `12345678`.

---

## 7. Join Radmin Network

Các nhóm còn lại mở Radmin VPN:

```text
Network → Join Network
```

Nhập:

```text
Network name: FIT4110-DEMO-A
Password: fit4110-demo-A@2026
```

Sau khi join, trong cửa sổ Radmin VPN sẽ thấy danh sách các máy trong network.

Mỗi máy sẽ có một **Radmin IP** riêng.

Ví dụ:

```text
team-iot-demo       26.31.10.15
team-core-demo      26.31.10.22
team-notify-demo    26.31.10.34
```

---

## 8. Ghi bảng IP chung

Mỗi Product hoặc cụm demo tạo một bảng IP chung.

| Nhóm | Service | Radmin IP | Port REST | Ghi chú |
|---|---|---:|---:|---|
| team-iot | IoT Ingestion | `26.__.__.__` | 8000 | |
| team-camera | Camera Stream | `26.__.__.__` | 8000 | |
| team-gate | Access Gate | `26.__.__.__` | 8000 | |
| team-vision | AI Vision | `26.__.__.__` | 8000 | |
| team-analytics | Analytics | `26.__.__.__` | 8000 | |
| team-core | Core Business | `26.__.__.__` | 8000 | |
| team-notify | Notification | `26.__.__.__` | 8000 | |

---

## 9. Cấu hình service để nhóm khác gọi được

Radmin VPN chỉ giúp các laptop nhìn thấy nhau trong mạng LAN ảo. Muốn nhóm khác gọi được service đang chạy trong Docker, nhóm provider vẫn phải cấu hình đúng.

### 9.1. Docker Compose phải publish port ra host

Ví dụ service API chạy port 8000:

```yaml
services:
  api:
    ports:
      - "8000:8000"
```

Nếu thiếu phần `ports`, service chỉ chạy bên trong Docker, nhóm khác sẽ không gọi được.

### 9.2. Service phải bind `0.0.0.0`

FastAPI:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Hoặc trong Python:

```python
uvicorn.run(app, host="0.0.0.0", port=8000)
```

Express/Fastify:

```javascript
app.listen(8000, "0.0.0.0")
```

Nếu service bind `127.0.0.1`, máy khác trong Radmin VPN sẽ không gọi được.

### 9.3. Mở Windows Firewall cho port demo

Trên máy provider, mở PowerShell bằng quyền Administrator:

```powershell
netsh advfirewall firewall add rule name="FIT4110 Demo API 8000" dir=in action=allow protocol=TCP localport=8000
```

Nếu nhóm dùng port khác, thay `8000` bằng port thật.

Ví dụ port 9000:

```powershell
netsh advfirewall firewall add rule name="FIT4110 Demo API 9000" dir=in action=allow protocol=TCP localport=9000
```

---

## 10. Cập nhật `.env` bằng Radmin IP

Không hard-code IP trong source code. Đưa URL nhóm đối tác vào `.env`.

Ví dụ team-vision gọi team-camera:

```env
CAMERA_SERVICE_URL=http://26.31.10.15:8000
```

Ví dụ team-core gọi team-notify:

```env
NOTIFY_SERVICE_URL=http://26.31.10.34:8000
```

Ví dụ team-iot gửi sang team-core:

```env
CORE_SERVICE_URL=http://26.31.10.22:8000
```

Sau khi sửa `.env`, restart lại service:

```bash
docker compose restart
```

Nếu service cần build lại:

```bash
docker compose down
docker compose up -d --build
```

---

## 11. Test bắt buộc trước khi demo

### 11.1. Provider tự kiểm tra trên máy mình

Trên máy nhóm provider:

```bash
docker compose ps
curl http://localhost:8000/health
```

Kết quả mong muốn:

```json
{
  "status": "ok"
}
```

hoặc `200 OK`.

### 11.2. Consumer gọi sang provider bằng Radmin IP

Trên máy nhóm consumer:

```bash
curl http://<RADMIN_IP_PROVIDER>:8000/health
```

Ví dụ:

```bash
curl http://26.31.10.22:8000/health
```

Nếu lệnh này thành công, hai nhóm mới bắt đầu test endpoint nghiệp vụ.

---

## 12. Test nghiệp vụ REST

Ví dụ team-core gọi team-notify:

```bash
curl -X POST http://26.31.10.34:8000/api/v1/alerts \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Cảnh báo xâm nhập",
    "message": "Phát hiện người lạ tại camera cam-01",
    "severity": "high"
  }'
```

Nhóm provider phải mở log để chứng minh đã nhận request:

```bash
docker compose logs --tail=100
```

Cần thấy các bước:

```text
Received request
Validated payload
Processed business logic
Returned response
```

---

## 13. Test MQTT qua HiveMQ

Nếu contract dùng MQTT qua HiveMQ Cloud, Radmin VPN không thay thế broker.

MQTT vẫn đi theo luồng:

```text
Nhóm A → Internet → HiveMQ Cloud → Nhóm B
```

Radmin VPN chủ yếu dùng cho REST giữa các máy.

Với MQTT, nhóm cần chứng minh:

- Publish đúng broker
- Publish đúng topic
- Payload đúng schema
- Nhóm đối tác subscribe được

Ví dụ:

```bash
mosquitto_sub -h <broker-host> -p 8883 \
  -u <username> -P <password> \
  -t "smart-campus/events/<topic>" -v
```

---

## 14. Quy trình test từ xa ở nhà

Các nhóm có thể test trước buổi học theo thứ tự sau:

```text
1. Mỗi nhóm chọn một máy demo Windows.
2. Cài Radmin VPN trên máy demo.
3. Join cùng Radmin Network do giảng viên/Product cung cấp.
4. Ghi Radmin IP vào bảng chung.
5. Mỗi nhóm chạy docker compose up -d --build.
6. Mỗi nhóm tự test localhost /health.
7. Nhóm đối tác test /health qua Radmin IP.
8. Cập nhật .env bằng Radmin IP của nhóm đối tác.
9. Test endpoint nghiệp vụ hoặc MQTT topic.
10. Lưu log, screenshot, request/response vào reports/.
```

---

## 15. Quy trình khi lên lớp

Nếu đã test bằng Radmin VPN ở nhà, khi lên lớp làm như sau:

```text
1. Mỗi nhóm vẫn dùng đúng máy demo đã test ở nhà.
2. Máy demo kết nối Internet bằng bất kỳ cách nào: Wi-Fi, 4G, hotspot, router mini.
3. Mở Radmin VPN và kiểm tra vẫn đang join đúng network.
4. Không đổi .env nếu vẫn dùng cùng Radmin IP.
5. Chạy docker compose ps.
6. Test localhost /health.
7. Nhóm đối tác gọi /health qua Radmin IP.
8. Bắt đầu demo nghiệp vụ.
```

Lưu ý: Nếu đổi máy demo hoặc đổi sang Radmin Network khác, phải cập nhật lại Radmin IP trong `.env`.

---

## 16. Khi nào dùng Radmin VPN, khi nào dùng router/hotspot?

| Tình huống | Phương án khuyến nghị |
|---|---|
| Nhóm test từ xa ở nhà | Radmin VPN |
| Lên lớp nhưng iPhone bị giới hạn thiết bị | Radmin VPN hoặc router mini |
| Có router mini ổn định cho cả Product | Router mini |
| Các máy không cùng phòng/lớp | Radmin VPN |
| Không có Internet | Router mini/LAN nội bộ, không dùng được Radmin |
| Máy demo là macOS/Linux | Cần phương án khác hoặc dùng máy Windows làm demo |

---

## 17. Lỗi thường gặp và cách xử lý

| Lỗi | Nguyên nhân thường gặp | Cách xử lý |
|---|---|---|
| Local `/health` OK nhưng nhóm khác gọi timeout | Firewall chặn hoặc service bind `127.0.0.1` | Mở firewall, đổi bind sang `0.0.0.0` |
| Connection refused | Container chưa chạy hoặc chưa publish port | Kiểm tra `docker compose ps`, `ports` |
| Gọi nhầm IP | Dùng IP Wi-Fi thay vì Radmin IP | Lấy IP trong cửa sổ Radmin VPN |
| Gọi bằng Docker service name | Nhầm Docker network với VPN | Dùng `http://RADMIN_IP:PORT` |
| MQTT không nhận message | Sai broker, topic hoặc credential | Kiểm tra HiveMQ/MQTT Explorer |
| Radmin không connect | Firewall/antivirus chặn hoặc mạng yếu | Cho phép Radmin VPN qua firewall, đổi mạng, restart Radmin |
| Đổi máy demo | Radmin IP thay đổi | Cập nhật lại bảng IP và `.env` |

---

## 18. Điều giảng viên sẽ kiểm tra khi chấm

Giảng viên có thể yêu cầu nhóm thực hiện trực tiếp:

```bash
docker compose ps
curl http://localhost:8000/health
curl http://<RADMIN_IP_NHOM_DOI_TAC>:8000/health
docker compose logs --tail=100
```

Nhóm cần trả lời được:

```text
1. Service của nhóm làm nghiệp vụ gì?
2. Input là gì?
3. Service xử lý input như thế nào?
4. Output là gì?
5. Output gửi cho nhóm nào?
6. Gửi qua REST endpoint hay MQTT topic nào?
7. Nếu nhóm đối tác lỗi thì service xử lý thế nào?
8. Minh chứng nằm ở đâu trong reports/?
```

---

## 19. Checklist cho mỗi nhóm

Trước khi báo “sẵn sàng demo”, mỗi nhóm tự tick:

```text
[x] Máy demo chính đã cài Radmin VPN
[x] Đã join đúng Radmin Network của Product/cụm demo
[x] Đã ghi Radmin IP vào bảng chung
[x] Service chạy bằng docker compose
[x] docker compose ps hiển thị container running
[x] GET /health local thành công
[ ] Nhóm đối tác gọi được /health qua Radmin IP
[ ] .env đã dùng Radmin IP của nhóm đối tác
[ ] Endpoint nghiệp vụ hoặc MQTT topic đã test
[ ] Có log xử lý input/output
[ ] Có request/response hoặc payload MQTT mẫu
[ ] Có minh chứng trong reports/
[ ] Có xử lý timeout hoặc lỗi từ service phụ thuộc
```

---

## 20. Câu chốt thống nhất

Các nhóm có thể tự bắt mạng riêng ở nhà hoặc ở lớp. Tuy nhiên, để test tích hợp từ xa và tránh giới hạn thiết bị của iPhone hotspot, **mỗi nhóm dùng một máy demo chính cài Radmin VPN và join chung Radmin Network**.

Khi tích hợp, các nhóm dùng:

```text
http://<RADMIN_IP_NHOM_DOI_TAC>:<PORT>
```

Không dùng:

```text
IP Wi-Fi/hotspot
Docker service name
localhost của máy khác
```

Nếu đã test từ xa bằng Radmin IP ở nhà, khi lên lớp chỉ cần đảm bảo máy có Internet, Radmin VPN đang kết nối, Docker Compose chạy, và các nhóm test `/health` chéo lại trước khi demo.

---

## 21. Nguồn tham khảo

- Radmin VPN official website: https://www.radmin-vpn.com/vi/
- Radmin VPN help/support: https://www.radmin-vpn.com/help/
- Radmin Club guide: https://radmin-club.com/radmin-vpn/how-to-manage-your-network/

