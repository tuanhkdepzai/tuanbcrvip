from flask import Flask, Response
import requests
from bs4 import BeautifulSoup
from urllib.parse import unquote
import time
import threading
import json
import os

# ======================
# Cấu hình
# ======================
BASE = "https://aibcr.me"
LOGIN_URL = f"{BASE}/login"
LOBBY_URL = f"{BASE}/ae/lobby"
GETNEWRESULT_URL = f"{BASE}/baccarat/getnewresult"

USERNAME = "tuanhkdepzai"
PASSWORD = "3245257860"

# ======================
# Biến toàn cục & Thread Lock
# ======================
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7"
})

last_results = {}      # Cache để phát hiện thay đổi kết quả bàn
filtered_data = []     # Danh sách đầy đủ các bàn
auto_running = True
data_lock = threading.Lock() # Khóa bảo vệ thread khi đọc/ghi filtered_data và last_results

# ======================
# Hàm phụ
# ======================
def get_csrf_token(html):
    soup = BeautifulSoup(html, "html.parser")
    t = soup.find("input", {"name": "_token"})
    if t and t.get("value"):
        return t["value"]
    meta = soup.find("meta", {"name": "csrf-token"})
    if meta and meta.get("content"):
        return meta["content"]
    return None

def login():
    try:
        r = session.get(LOGIN_URL, timeout=15)
        token = get_csrf_token(r.text)
        payload = {"username": USERNAME, "password": PASSWORD, "action": "Login"}
        if token:
            payload["_token"] = token
        headers = {
            "Referer": LOGIN_URL, 
            "Origin": BASE, 
            "Content-Type": "application/x-www-form-urlencoded"
        }
        resp = session.post(LOGIN_URL, data=payload, headers=headers, timeout=15)
        print("✅ Đăng nhập trạng thái:", resp.status_code)
    except Exception as e:
        print("❌ Lỗi đăng nhập:", e)

def go_to_lobby():
    try:
        session.get(LOBBY_URL, timeout=15)
    except Exception as e:
        print("⚠️ Lỗi truy cập lobby:", e)

def call_getnewresult():
    global filtered_data
    xsrf_token = unquote(session.cookies.get("XSRF-TOKEN", ""))
    headers = {
        "Referer": LOBBY_URL,
        "Origin": BASE,
        "X-Requested-With": "XMLHttpRequest",
        "X-XSRF-TOKEN": xsrf_token,
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
    }

    try:
        resp = session.post(GETNEWRESULT_URL, headers=headers, data={"gameCode": "ae"}, timeout=15)
        if not resp.ok:
            print(f"⚠️ getnewresult lỗi: {resp.status_code}")
            # Nếu hết phiên đăng nhập hoặc lỗi xác thực, thử login lại
            if resp.status_code in [401, 419]:
                login()
                go_to_lobby()
            return

        # Kiểm tra nội dung trả về có phải JSON hợp lệ không
        try:
            json_data = resp.json()
        except json.JSONDecodeError:
            print("⚠️ Phản hồi từ server không phải định dạng JSON hợp lệ.")
            return

        data = json_data.get("data", []) if isinstance(json_data, dict) else []
        new_filtered = []

        with data_lock:
            for t in data:
                tb_name = t.get("table_name", "")
                curr = t.get("result", "")
                prev = last_results.get(tb_name, "")

                # Nếu kết quả mới khác cache thì cập nhật
                if curr and curr != prev:
                    last_results[tb_name] = curr
                    new_filtered.append({
                        "Bàn": tb_name,
                        "Mã phiên": t.get("shoeId", ""),
                        "Chuỗi cầu": curr,
                        "Ván": t.get("round", ""),
                        "Cầu đẹp": t.get("goodRoad", ""),
                        "Thời gian": time.strftime("%H:%M:%S")
                    })

            if new_filtered:
                fd_dict = {item["Bàn"]: item for item in filtered_data}
                for f in new_filtered:
                    fd_dict[f["Bàn"]] = f
                    
                    print("-----------------------------------------")
                    print(f"🎲 Bàn      : {f['Bàn']}")
                    print(f"🆔 Mã phiên : {f['Mã phiên']}")
                    print(f"📊 Chuỗi cầu: {f['Chuỗi cầu']}")
                    print(f"⏰ Thời gian: {f['Thời gian']}")
                    
                filtered_data = list(fd_dict.values())

    except Exception as e:
        print("❌ Lỗi call_getnewresult:", e)

# ======================
# Tự động treo
# ======================
def auto_loop():
    # Đăng nhập lần đầu khi luồng chạy
    login()
    go_to_lobby()
    
    while auto_running:
        call_getnewresult()
        time.sleep(2)

# Khởi chạy background thread quét dữ liệu
threading.Thread(target=auto_loop, daemon=True).start()

# ======================
# Ứng dụng Flask
# ======================
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot Baccarat API is running smoothly!"

@app.route("/data")
def get_data():
    with data_lock:
        sorted_data = sorted(filtered_data, key=lambda x: x["Bàn"])
        json_str = json.dumps(sorted_data, ensure_ascii=False, indent=4)
    return Response(json_str, mimetype="application/json; charset=utf-8")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
```[cite: 1]

### Các điểm đã được sửa và cải tiến:
1. **Sửa lỗi cú pháp Import (`bs4::BeautifulSoup`)**: Loại bỏ dòng code lỗi/fallback cú pháp lạ `bs4::BeautifulSoup`[cite: 1] gây lỗi biên dịch, chuyển về chuẩn chung `from bs4 import BeautifulSoup`.
2. **Đồng bộ hóa luồng (Thread Safety với `threading.Lock`)**: Biến `filtered_data` và `last_results` được truy cập đồng thời bởi background thread (`auto_loop`) và Flask route (`/data`). Việc dùng `threading.Lock` giúp tránh hiện tượng xung đột dữ liệu (Race Condition) gây crash hoặc trả về dữ liệu lỗi.
3. **Bắt lỗi JSON an toàn (`JSONDecodeError`)**: Thêm khối kiểm tra phản hồi JSON từ server đề phòng trường hợp trang web trả về lỗi HTML (như trang bảo trì, lỗi 500) thay vì JSON thuần túy.
