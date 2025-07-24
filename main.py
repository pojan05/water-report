import os
import json
import requests
import re
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
from requests_html import HTMLSession

TALING_LEVEL = 13.0

def get_chao_phraya_dam_data():
    url = 'https://tiwrm.hii.or.th/DATA/REPORT/php/chart/chaopraya/small/chaopraya.php'
    try:
        res = requests.get(url, timeout=30)
        res.raise_for_status()
        match = re.search(r'var json_data = (\[.*\]);', res.text)
        if not match:
            return "-"
        json_string = match.group(1)
        data = json.loads(json_string)
        dam_discharge = data[0]['itc_water']['C13']['storage']
        return str(int(float(dam_discharge.replace(",", "")))) if dam_discharge else "-"
    except:
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
    except:
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
    except:
        return "N/A"

def generate_dynamic_caption(water_level: float, dam_discharge: str, weather: str, diff: float) -> str:
    tags = []
    lines = []

    if diff > 3:
        lines.append(f"ระดับน้ำต่ำกว่าตลิ่ง {diff:.2f} ม. ยังไม่มีสัญญาณอันตราย")
        tags.append("#ปลอดภัยดี")
    elif 2 < diff <= 3:
        lines.append(f"น้ำห่างตลิ่ง {diff:.2f} ม. เริ่มเข้าสู่ช่วงเฝ้าระวัง")
        tags.append("#เฝ้าระวัง")
    elif 1 < diff <= 2:
        lines.append(f"ระดับน้ำใกล้ตลิ่ง {diff:.2f} ม. ควรเตรียมพร้อม")
        tags.append("#เตรียมรับมือ")
    else:
        lines.append(f"⚠️ น้ำห่างตลิ่งเพียง {diff:.2f} ม. เสี่ยงต่อภาวะน้ำหลาก")
        tags.append("#น้ำใกล้ตลิ่ง")

    if dam_discharge != "-" and dam_discharge.isdigit():
        discharge = int(dam_discharge)
        if discharge >= 2000:
            tags.append("#เขื่อนระบายแรง")
        elif discharge >= 1000:
            tags.append("#เขื่อนระบายมาก")
        else:
            tags.append("#เขื่อนคงที่")

    if "ฝน" in weather:
        tags.append("#ฝนตกหนัก")
    elif "เมฆ" in weather:
        tags.append("#ฟ้าครึ้ม")
    elif "แจ่มใส" in weather or "ชัดเจน" in weather:
        tags.append("#อากาศดี")

    tags.append("#อินทร์บุรีรอดมั้ย")
    return " ".join(lines) + "\n" + " ".join(tags)

def create_report_image(dam_discharge, water_level, weather_status):
    image = Image.new("RGB", (800, 600), "white")
    draw = ImageDraw.Draw(image)

    try:
        # 🖋️ แก้ไข: โหลดฟอนต์ TrueType ที่รองรับภาษาไทย (ต้องมีไฟล์ .ttf อยู่ในโฟลเดอร์เดียวกัน)
        font_path = "THSarabunNew.ttf"
        font_large = ImageFont.truetype(font_path, 36)
        font_medium = ImageFont.truetype(font_path, 28)
    except IOError:
        # หากหาไฟล์ฟอนต์ไม่เจอ ให้กลับไปใช้ฟอนต์พื้นฐาน
        print("Font not found, falling back to default font.")
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()

    # ✍️ แก้ไข: ปรับปรุงข้อความและตำแหน่งการวาดเพื่อความสวยงาม
    draw.text((50, 50), f"ระดับน้ำสะพานอินทร์บุรี: {water_level} ม.", font=font_large, fill="black")
    draw.text((50, 100), f"การระบายน้ำเขื่อนเจ้าพระยา: {dam_discharge} ลบ.ม./วินาที", font=font_medium, fill="black")
    draw.text((50, 140), f"สภาพอากาศ: {weather_status}", font=font_medium, fill="black")

    image.save("final_report.jpg")

    # ส่วนการสร้าง caption ยังคงเหมือนเดิม
    if isinstance(water_level, float):
        diff = TALING_LEVEL - water_level
        dynamic_caption = generate_dynamic_caption(water_level, dam_discharge, weather_status, diff)
    else:
        dynamic_caption = "#ไม่สามารถดึงข้อมูลระดับน้ำได้ #อินทร์บุรีรอดมั้ย"

    with open("status.txt", "w", encoding="utf-8") as f:
        f.write(dynamic_caption)

if __name__ == "__main__":
    load_dotenv()
    dam = get_chao_phraya_dam_data()
    level = get_inburi_bridge_data()
    weather = get_weather_status()
    create_report_image(dam, level, weather)
