import os
import json
import requests
import re
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
from requests_html import HTMLSession

TALING_LEVEL = 13.0

# --- ฟังก์ชันดึงข้อมูล (ใช้ของเดิม) ---
def get_chao_phraya_dam_data():
    url = 'https://tiwrm.hii.or.th/DATA/REPORT/php/chart/chaopraya/small/chaopraya.php'
    try:
        res = requests.get(url, timeout=30)
        res.raise_for_status()
        match = re.search(r'var json_data = (\[.*\]);', res.text)
        if not match: return "-"
        json_string = match.group(1)
        data = json.loads(json_string)
        dam_discharge = data[0]['itc_water']['C13']['storage']
        return str(int(float(dam_discharge.replace(",", "")))) if dam_discharge else "-"
    except Exception:
        return "-"

def get_inburi_bridge_data():
    url = "https://singburi.thaiwater.net/wl"
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
    except Exception:
        return "-"

def get_weather_status():
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key: return "N/A"
    lat, lon = "14.9", "100.4"
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&lang=th&units=metric"
    try:
        res = requests.get(url, timeout=30)
        data = res.json()
        return f"{data['weather'][0]['description'].capitalize()}"
    except Exception:
        return "N/A"

# ✨ ฟังก์ชันสร้างรูปภาพที่ปรับปรุงใหม่
def create_report_image(dam_discharge, water_level, weather_status):
    TEXT_COLOR = "#2c3e50"
    IMAGE_WIDTH = 1080
    Y_START = 340

    try:
        image = Image.open("background.png").convert("RGB")
    except FileNotFoundError:
        image = Image.new("RGB", (IMAGE_WIDTH, 1080), "white")

    draw = ImageDraw.Draw(image)

    try:
        # ❗ ปรับขนาดตัวอักษรให้เล็กลง
        font_bold_l = ImageFont.truetype("Sarabun-Bold.ttf", 54)
        font_regular_l = ImageFont.truetype("Sarabun-Regular.ttf", 42)
        font_regular_m = ImageFont.truetype("Sarabun-Regular.ttf", 42)
    except FileNotFoundError:
        font_bold_l = font_regular_l = font_regular_m = ImageFont.load_default()

    level_text = f"{water_level:.2f} ม." if isinstance(water_level, float) else "N/A"
    discharge_text = f"{dam_discharge} ลบ.ม./วินาที"
    weather_text = weather_status

    diff = TALING_LEVEL - water_level if isinstance(water_level, float) else 99
    if diff <= 1.5:
        sit_text, sit_detail = "วิกฤต", "เสี่ยงน้ำล้นตลิ่ง"
    elif diff <= 2.5:
        sit_text, sit_detail = "เฝ้าระวัง", "ระดับน้ำใกล้ตลิ่ง"
    else:
        sit_text, sit_detail = "ปกติ", "น้ำยังห่างตลิ่ง ปลอดภัยจ้า"

    y = Y_START
    # ระดับน้ำ
    draw.text((IMAGE_WIDTH / 2, y), f"ระดับน้ำ ณ อินทร์บุรี: {level_text}", font=font_bold_l, fill=TEXT_COLOR, anchor="ms")
    y += 100
    # การระบายน้ำ
    draw.text((IMAGE_WIDTH / 2, y), f"การระบายน้ำท้ายเขื่อนฯ: {discharge_text}", font=font_regular_l, fill=TEXT_COLOR, anchor="ms")
    y += 100
    # สภาพอากาศ
    draw.text((IMAGE_WIDTH / 2, y), f"สภาพอากาศ: {weather_text}", font=font_regular_l, fill=TEXT_COLOR, anchor="ms")
    y += 110
    # สถานการณ์
    draw.text((IMAGE_WIDTH / 2, y), f"สถานการณ์: {sit_text}", font=font_bold_l, fill=TEXT_COLOR, anchor="ms")
    y += 80
    draw.text((IMAGE_WIDTH / 2, y), sit_detail, font=font_regular_m, fill=TEXT_COLOR, anchor="ms")

    image.save("final_report.jpg", quality=95)

    dynamic_caption = generate_facebook_caption(water_level, dam_discharge, weather_status)
    with open("status.txt", "w", encoding="utf-8") as f:
        f.write(dynamic_caption)

if __name__ == "__main__":
    load_dotenv()
    dam = get_chao_phraya_dam_data()
    level = get_inburi_bridge_data()
    weather = get_weather_status()
    create_report_image(dam, level, weather)
