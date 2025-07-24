import os
import json
import requests
import re
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

# --- ✨ เพิ่ม Library สำหรับ Requests-HTML ---
from requests_html import HTMLSession

# โหลดค่าจากไฟล์ .env
load_dotenv()

# --- ค่าคงที่และตัวแปรสำหรับแจ้งเตือน ---
LAST_DAM_DATA_FILE = 'last_dam_data.txt'
LAST_INBURI_DATA_FILE = 'last_inburi_data.json'
NOTIFICATION_THRESHOLD = 0.1
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_TARGET_ID = os.getenv('LINE_TARGET_ID')

# --- ฟังก์ชันดึงข้อมูล ---

def get_chao_phraya_dam_data():
    """ดึงข้อมูลการระบายน้ำท้ายเขื่อนเจ้าพระยา (JSON method)"""
    url = 'https://tiwrm.hii.or.th/DATA/REPORT/php/chart/chaopraya/small/chaopraya.php'
    print("💧 Fetching Chao Phraya Dam data (JSON method)...")
    try:
        res = requests.get(url, timeout=30)
        res.raise_for_status()
        res.encoding = 'utf-8'

        match = re.search(r'var json_data = (\[.*\]);', res.text)
        if not match:
            print("❌ Dam error: Could not find json_data variable.")
            return "-"

        json_string = match.group(1)
        data = json.loads(json_string)
        dam_discharge = data[0]['itc_water']['C13']['storage']
        
        if dam_discharge:
            value = str(int(float(dam_discharge)))
            print(f"✅ Dam discharge raw value (JSON): {value}")
            return value

    except (requests.exceptions.RequestException, KeyError, IndexError, json.JSONDecodeError) as e:
        print(f"❌ Dam error: {e}")
    return "-"

def get_inburi_bridge_data():
    """ดึงข้อมูลระดับน้ำที่สะพานอินทร์บุรี (ใช้ Requests-HTML)"""
    url = "https://singburi.thaiwater.net/wl"
    print("💧 Fetching Inburi data using Requests-HTML...")
    try:
        session = HTMLSession()
        r = session.get(url, timeout=30)
        
        # รัน JavaScript บนหน้าเว็บและรอ 10 วินาทีให้ข้อมูลโหลด
        r.html.render(sleep=10, timeout=60)
        
        # ตอนนี้ r.html.html จะเป็น HTML เวอร์ชันสมบูรณ์ที่มีตารางแล้ว
        soup = BeautifulSoup(r.html.html, "html.parser")
        
        rows = soup.find_all("tr")
        for row in rows:
            th = row.find("th", {"scope": "row"})
            if th and "อินทร์บุรี" in th.get_text(strip=True):
                tds = row.find_all("td")
                if len(tds) >= 2:
                    value = tds[1].get_text(strip=True)
                    print(f"✅ Water level @Inburi (Requests-HTML): {value}")
                    return float(value)
                    
        print("❌ Inburi row not found in table after rendering.")
        return "-"

    except Exception as e:
        print(f"❌ An error occurred with Requests-HTML: {e}")
        return "-"

# --- ส่วนที่เหลือของไฟล์ไม่ต้องแก้ไข ---
def get_weather_status():
    """ดึงข้อมูลสภาพอากาศ"""
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key: return "N/A"
    lat, lon = "14.9", "100.4"
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&lang=th&units=metric"
    try:
        res = requests.get(url, timeout=30)
        data = res.json()
        desc = data["weather"][0]["description"]
        emoji = "🌧️" if "ฝน" in desc else "☁️" if "เมฆ" in desc else "☀️"
        return f"{desc.capitalize()} {emoji}"
    except Exception as e:
        print(f"❌ Weather fetch error: {e}")
        return "N/A"


def create_report_image(dam_discharge, water_level, weather_status):
    image = Image.open("background.png").convert("RGBA")
    draw = ImageDraw.Draw(image)
    water_value_str = f"{water_level:.2f}" if isinstance(water_level, float) else str(water_level)
    dam_discharge_str = str(dam_discharge)
    lines_data = {
        f"ระดับน้ำ ณ อินทร์บุรี: {water_value_str} ม.": water_level,
        f"การระบายน้ำท้ายเขื่อนฯ: {dam_discharge_str} ลบ.ม./วินาที": dam_discharge,
        f"สภาพอากาศ: {weather_status}": weather_status
    }
    lines = [text for text, value in lines_data.items() if value not in ["-", "N/A"]]
    if not lines:
        lines = ["ไม่สามารถอัปเดตข้อมูลได้ในขณะนี้"]
    font_path = "Sarabun-Bold.ttf" if os.path.exists("Sarabun-Bold.ttf") else "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
    font = ImageFont.truetype(font_path, 34)
    box_left, box_right, box_top, box_bottom = 60, 710, 125, 370
    box_width = box_right - box_left
    box_height = box_bottom - box_top
    line_spacing = 20
    total_text_height = sum([font.getbbox(line)[3] - font.getbbox(line)[1] for line in lines])
    total_height_with_spacing = total_text_height + line_spacing * (len(lines) - 1)
    y = box_top + (box_height - total_height_with_spacing) / 2
    for line in lines:
        text_width = draw.textlength(line, font=font)
        x = box_left + (box_width - text_width) / 2
        draw.text((x, y), line, font=font, fill="#003f5c", stroke_width=1, stroke_fill="white")
        y += (font.getbbox(line)[3] - font.getbbox(line)[1]) + line_spacing
    image.convert("RGB").save("final_report.jpg", "JPEG", quality=95)
    print("✅ final_report.jpg created")


def send_line_message(message: str):
    if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_TARGET_ID:
        print("⚠️ LINE credentials are not set. Skipping notification.")
        return
    print(f"🚀 Sending LINE message: {message}")
    url = 'https://api.line.me/v2/bot/message/push'
    headers = { 'Content-Type': 'application/json', 'Authorization': f'Bearer {LINE_CHANNEL_ACCESS_TOKEN}' }
    payload = { 'to': LINE_TARGET_ID, 'messages': [{'type': 'text', 'text': message}] }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        resp.raise_for_status()
        print("✅ LINE message sent successfully:", resp.status_code)
    except Exception as e:
        print(f"❌ Failed to send LINE message: {e}")

if __name__ == "__main__":
    print("🔁 Updating water report...")
    current_dam_value = get_chao_phraya_dam_data()
    current_inburi_level = get_inburi_bridge_data()
    weather = get_weather_status()
    alert_messages = []
    if current_dam_value != "-":
        last_dam_value = ""
        if os.path.exists(LAST_DAM_DATA_FILE):
            with open(LAST_DAM_DATA_FILE, 'r', encoding='utf-8') as f:
                last_dam_value = f.read().strip()
        if current_dam_value != last_dam_value:
            print(f"💧 Dam data changed: {last_dam_value} -> {current_dam_value}. Preparing alert.")
            alert_messages.append(
                f"🌊 แจ้งเตือนเขื่อนเจ้าพระยา\n"
                f"การระบายน้ำ: {current_dam_value} ลบ.ม./วินาที\n"
                f"(เดิม: {last_dam_value or 'N/A'})"
            )
            with open(LAST_DAM_DATA_FILE, 'w', encoding='utf-8') as f:
                f.write(current_dam_value)
    if isinstance(current_inburi_level, float):
        last_inburi_level = None
        if os.path.exists(LAST_INBURI_DATA_FILE):
            with open(LAST_INBURI_DATA_FILE, 'r', encoding='utf-8') as f:
                try:
                    last_data = json.load(f)
                    last_inburi_level = last_data.get("water_level")
                except json.JSONDecodeError: pass
        if last_inburi_level is not None:
            diff = current_inburi_level - last_inburi_level
            if abs(diff) >= NOTIFICATION_THRESHOLD:
                direction = "⬆️ เพิ่มขึ้น" if diff > 0 else "⬇️ ลดลง"
                print(f"💧 Inburi level changed significantly: {last_inburi_level:.2f} -> {current_inburi_level:.2f}. Preparing alert.")
                alert_messages.append(
                    f"📢 แจ้งเตือนระดับน้ำอินทร์บุรี\n"
                    f"ระดับน้ำ: {current_inburi_level:.2f} ม.\n"
                    f"เปลี่ยนแปลง {direction} {abs(diff):.2f} ม."
                )
        else:
            print("[INFO] No previous Inburi data. Skipping alert for the first time.")
        with open(LAST_INBURI_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump({"water_level": current_inburi_level}, f)
    if alert_messages:
        FOOTER_MESSAGE = "\n\n✨ สนับสนุนโดย ร้านจิปาถะอินทร์บุรี"
        full_message = "\n\n".join(alert_messages) + FOOTER_MESSAGE
        send_line_message(full_message)
    else:
        print("✅ No significant changes detected. No LINE alert will be sent.")
    status_parts = []
    if isinstance(current_inburi_level, float):
        status_parts.append(f"ระดับน้ำ ณ อินทร์บุรี: {current_inburi_level:.2f} ม.")
    if current_dam_value != "-":
        status_parts.append(f"การระบายน้ำท้ายเขื่อนเจ้าพระยา: {current_dam_value} ลบ.ม./วินาที")
    if weather != "N/A":
        status_parts.append(f"สภาพอากาศ: {weather}")
    status_line = " | ".join(status_parts) if status_parts else "อัปเดตข้อมูลระดับน้ำ"
    print(f"📊 Status: {status_line}")
    create_report_image(current_dam_value, current_inburi_level, weather)
    with open("status.txt", "w", encoding="utf-8") as f:
        f.write(status_line)
