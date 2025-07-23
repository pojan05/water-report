import os
import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

load_dotenv()

def get_chao_phraya_dam_data():
    url = 'https://tiwrm.hii.or.th/DATA/REPORT/php/chart/chaopraya/small/chaopraya.php'
    try:
        res = requests.get(url, timeout=30)
        soup = BeautifulSoup(res.text, "html.parser")
        strong_tag = soup.find('strong', string=lambda t: t and 'ที่ท้ายเขื่อนเจ้าพระยา' in t)
        if strong_tag:
            table = strong_tag.find_parent('table')
            td = table.find('td', string=lambda t: t and 'ปริมาณน้ำ' in t)
            if td:
                value = td.find_next_sibling('td').text.strip().split('/')[0]
                print(f"✅ Dam discharge raw value: {value}")
                return str(int(float(value)))
    except Exception as e:
        print(f"❌ Dam error: {e}")
    return "-"

def get_inburi_bridge_data():
    url = "https://singburi.thaiwater.net/wl"
    try:
        res = requests.get(url, timeout=30)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
        rows = soup.find_all("tr")
        for row in rows:
            th = row.find("th", {"scope": "row"})
            if th and "อินทร์บุรี" in th.get_text(strip=True):
                tds = row.find_all("td")
                if len(tds) >= 1:
                    value = tds[1].get_text(strip=True)
                    print(f"✅ Water level @Inburi (no Selenium): {value}")
                    return value
        print("❌ Inburi row not found in table")
    except Exception as e:
        print(f"❌ Error fetching Inburi (no Selenium): {e}")
    return "-"

def get_weather_status():
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

def create_report_image(dam_discharge, water_value, weather_status):
    image = Image.open("background.png").convert("RGBA")
    draw = ImageDraw.Draw(image)

    lines_data = {
        f"ระดับน้ำ ณ อินทร์บุรี: {water_value} ม.": water_value,
        f"การระบายน้ำท้ายเขื่อนฯ: {dam_discharge} ลบ.ม./วินาที": dam_discharge,
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

if __name__ == "__main__":
    print("🔁 Updating water report...")
    dam_value = get_chao_phraya_dam_data()
    water_value = get_inburi_bridge_data()
    weather = get_weather_status()

    status_parts = []
    if water_value != "-": status_parts.append(f"ระดับน้ำ ณ อินทร์บุรี: {water_value} ม.")
    if dam_value != "-": status_parts.append(f"การระบายน้ำท้ายเขื่อนเจ้าพระยา: {dam_value} ลบ.ม./วินาที")
    if weather != "N/A": status_parts.append(f"สภาพอากาศ: {weather}")
    status_line = " | ".join(status_parts) if status_parts else "อัปเดตข้อมูลระดับน้ำ"

    print(f"📊 {status_line}")

    create_report_image(dam_value, water_value, weather)

    with open("status.txt", "w", encoding="utf-8") as f:
        f.write(status_line)
