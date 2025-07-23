
import os
import json
import requests
import re
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
from requests_html import HTMLSession

# --- ค่าคงที่และตัวแปร ---
LAST_DAM_DATA_FILE = 'last_dam_data.txt'
LAST_INBURI_DATA_FILE = 'last_inburi_data.json'
NOTIFICATION_THRESHOLD = 0.1
TALING_LEVEL = 13.0  # ตลิ่งคงที่ (เมตร)

LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_TARGET_ID = os.getenv('LINE_TARGET_ID')

# --- ฟังก์ชัน ---

def get_chao_phraya_dam_data():
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
        return str(int(float(dam_discharge))) if dam_discharge else "-"
    except Exception as e:
        print(f"❌ Dam error: {e}")
        return "-"

def get_inburi_bridge_data():
    url = "https://singburi.thaiwater.net/wl"
    print("💧 Fetching Inburi data using Requests-HTML...")
    try:
        session = HTMLSession()
        r = session.get(url, timeout=30)
        r.html.render(sleep=10, timeout=60)
        soup = BeautifulSoup(r.html.html, "html.parser")
        for row in soup.find_all("tr"):
            th = row.find("th", {"scope": "row"})
            if th and "อินทร์บุรี" in th.get_text(strip=True):
                tds = row.find_all("td")
                if len(tds) >= 2:
                    return float(tds[1].get_text(strip=True))
        return "-"
    except Exception as e:
        print(f"❌ An error occurred with Requests-HTML: {e}")
        return "-"

def classify_water_level_status(water_level: float):
    diff = TALING_LEVEL - water_level
    if diff > 3:
        return "✅ ปกติ", "น้ำยังห่างตลิ่ง ปลอดภัยจ้า 😎"
    elif 2.5 < diff <= 3:
        return "🟡 เฝ้าระวัง", "เริ่มขยับเข้ามา ใจเย็นแต่ดูข่าวไว้นะ 🧐"
    elif 1 < diff <= 2.5:
        return "🟠 ใกล้วิกฤต", "เตรียมของไว้สูง ๆ เดี๋ยวมาไวไม่รู้ตัว 😰"
    elif diff <= 1:
        return "🔴 วิกฤต", "ยกของขึ้นสูง เตรียมอพยพถ้าจำเป็นนะ 🚨"
    else:
        return "❓ ไม่ทราบ", "ข้อมูลผิดพลาดหรือไม่ชัดเจน"

def create_report_image(dam_discharge, water_level, weather_status):
    image = Image.open("background.png").convert("RGBA")
    draw = ImageDraw.Draw(image)
    water_value_str = f"{water_level:.2f}" if isinstance(water_level, float) else str(water_level)
    dam_discharge_str = str(dam_discharge)
    situation_line, situation_note = ("", "")
    if isinstance(water_level, float):
        situation_line, situation_note = classify_water_level_status(water_level)

    lines_data = {
        f"ระดับน้ำ ณ อินทร์บุรี: {water_value_str} ม.": water_level,
        f"การระบายน้ำท้ายเขื่อนฯ: {dam_discharge_str} ลบ.ม./วินาที": dam_discharge,
        f"สภาพอากาศ: {weather_status}": weather_status,
        f"สถานการณ์: {situation_line}": situation_line,
        f"{situation_note}": situation_note
    }

    lines = [text for text, value in lines_data.items() if value not in ["-", "N/A", ""]]
    font_path = "Sarabun-Bold.ttf" if os.path.exists("Sarabun-Bold.ttf") else "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
    font = ImageFont.truetype(font_path, 34)
    box_left, box_right, box_top, box_bottom = 60, 710, 125, 420
    box_height = box_bottom - box_top
    line_spacing = 20
    total_height = sum([font.getbbox(line)[3] - font.getbbox(line)[1] for line in lines]) + line_spacing * (len(lines)-1)
    y = box_top + (box_height - total_height) / 2
    for line in lines:
        x = box_left + ((box_right - box_left) - draw.textlength(line, font=font)) / 2
        draw.text((x, y), line, font=font, fill="#003f5c", stroke_width=1, stroke_fill="white")
        y += (font.getbbox(line)[3] - font.getbbox(line)[1]) + line_spacing
    image.convert("RGB").save("final_report.jpg", "JPEG", quality=95)
    print("✅ final_report.jpg created")

# --- main ---
if __name__ == "__main__":
    from datetime import datetime
    from openai import OpenAIError

    from dotenv import load_dotenv
    load_dotenv()

    print("🔁 Updating water report...")
    current_dam_value = get_chao_phraya_dam_data()
    current_inburi_level = get_inburi_bridge_data()
    weather = "🌤️ อากาศดี"

    alert_messages = []

    if isinstance(current_inburi_level, float):
        situation, note = classify_water_level_status(current_inburi_level)
        alert_messages.append(f"📍 สถานการณ์น้ำอินทร์บุรี: {situation}
{note}")

    if current_dam_value != "-":
        alert_messages.append(f"💧 เขื่อนเจ้าพระยา: {current_dam_value} ลบ.ม./วินาที")

    if isinstance(current_inburi_level, float):
        alert_messages.append(f"🌊 ระดับน้ำอินทร์บุรี: {current_inburi_level:.2f} ม.")

    create_report_image(current_dam_value, current_inburi_level, weather)

    # 📝 สร้างไฟล์ status.txt
    status_line = "

".join(alert_messages) if alert_messages else "วันนี้ไม่มีการเปลี่ยนแปลงระดับน้ำครับ 😄"
    with open("status.txt", "w", encoding="utf-8") as f:
        f.write(status_line)
    print("📄 status.txt created")

    print("📊 รายงานเสร็จสิ้น")
