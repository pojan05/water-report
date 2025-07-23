import os
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

# โหลด .env สำหรับ OPENWEATHER_API_KEY
load_dotenv()

def initialize_driver():
    """ตั้งค่าและคืนค่า Chrome Driver สำหรับ Selenium"""
    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)

def get_chao_phraya_dam_data():
    """ดึงข้อมูลการระบายน้ำท้ายเขื่อนเจ้าพระยาด้วย Selenium"""
    url = 'https://tiwrm.hii.or.th/DATA/REPORT/php/chart/chaopraya/small/chaopraya.php'
    driver = initialize_driver()
    try:
        driver.set_page_load_timeout(45) # เพิ่มเวลารอ
        driver.get(url)
        WebDriverWait(driver, 45).until(
            EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'ท้ายเขื่อนเจ้าพระยา')]"))
        )
        soup = BeautifulSoup(driver.page_source, "html.parser")
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
    finally:
        driver.quit()
    return "ไม่สามารถดึงข้อมูล"

def get_inburi_bridge_data():
    """
    (ปรับปรุงใหม่) ดึงข้อมูลระดับน้ำที่สะพานอินทร์บุรีผ่าน API โดยตรง
    วิธีนี้เร็วกว่าและเสถียรกว่าการใช้ Selenium มาก
    """
    url = "https://singburi.thaiwater.net/api/v1/wl/tele_waterlevel"
    try:
        print("📡 Fetching Inburi water level from API...")
        response = requests.get(url, timeout=30)
        response.raise_for_status() # เช็คว่า request สำเร็จหรือไม่
        data = response.json()
        for station in data.get('data', []):
            if station.get('station_name') == 'สะพานอินทร์บุรี':
                value = station.get('storage_data', {}).get('value')
                if value is not None:
                    print(f"✅ Water level @Inburi (API): {value}")
                    return str(value)
        print("❌ 'สะพานอินทร์บุรี' not found in API response")
    except requests.exceptions.RequestException as e:
        print(f"❌ Inburi API request error: {e}")
    except Exception as e:
        print(f"❌ Inburi API processing error: {e}")
    return "ไม่สามารถดึงข้อมูล"


def get_weather_status():
    """ดึงข้อมูลสภาพอากาศจาก OpenWeatherMap"""
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        print("❌ OPENWEATHER_API_KEY not found in environment")
        return "ข้อมูลสภาพอากาศไม่พร้อม"
    lat, lon = "14.9", "100.4"
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&lang=th&units=metric"
    try:
        print(f"📡 Fetching weather from: {url.split('?')[0]}")
        res = requests.get(url, timeout=30)
        data = res.json()
        desc = data["weather"][0]["description"]
        # กำหนด emoji ให้หลากหลายขึ้น
        if "ฝน" in desc: emoji = "🌧️"
        elif "เมฆ" in desc: emoji = "☁️"
        elif "แดด" in desc or "ท้องฟ้า" in desc: emoji = "☀️"
        else: emoji = "⛅"
        return f"{desc.capitalize()} {emoji}"
    except Exception as e:
        print(f"❌ Weather fetch error: {e}")
        return "ข้อมูลสภาพอากาศไม่พร้อม"

def create_report_image(dam_discharge, water_level, weather_status):
    """
    (ปรับปรุงใหม่) สร้างรูปภาพรายงานพร้อมจัดวางข้อความให้อยู่กึ่งกลาง
    """
    if not os.path.exists("background.png"):
        print("❌ background.png not found")
        return

    image = Image.open("background.png").convert("RGBA")
    draw = ImageDraw.Draw(image)

    # แก้ไขข้อความให้สวยงามขึ้น
    lines = [
        f"ระดับน้ำ ณ อินทร์บุรี: {water_level} ม.",
        f"การระบายน้ำท้ายเขื่อนฯ: {dam_discharge} ลบ.ม./วินาที",
        f"สภาพอากาศ: {weather_status}"
    ]

    # กำหนดฟอนต์ (รองรับทั้ง local และบน GitHub Actions)
    font_path = "Sarabun-Bold.ttf" if os.path.exists("Sarabun-Bold.ttf") else "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
    font = ImageFont.truetype(font_path, 34)

    # กำหนดกรอบและคำนวณตำแหน่งกึ่งกลาง
    box_left, box_right = 60, 710
    box_top, box_bottom = 125, 370
    box_width = box_right - box_left
    box_height = box_bottom - box_top

    line_spacing = 20  # เพิ่มระยะห่างระหว่างบรรทัด
    
    # คำนวณความสูงรวมของข้อความทั้งหมดเพื่อหาจุดเริ่มต้นในแนวตั้ง (y)
    total_text_height = sum([font.getbbox(line)[3] - font.getbbox(line)[1] for line in lines])
    total_height_with_spacing = total_text_height + line_spacing * (len(lines) - 1)
    y = box_top + (box_height - total_height_with_spacing) / 2

    # วาดข้อความแต่ละบรรทัด
    for line in lines:
        # คำนวณตำแหน่งกึ่งกลางในแนวนอน (x)
        text_width = draw.textlength(line, font=font)
        x = box_left + (box_width - text_width) / 2
        
        # วาดข้อความพร้อมขอบสีขาวเพื่อให้อ่านง่ายขึ้น
        draw.text((x, y), line, font=font, fill="#003f5c", stroke_width=1, stroke_fill="white")
        
        # เลื่อนตำแหน่ง y สำหรับบรรทัดถัดไป
        y += (font.getbbox(line)[3] - font.getbbox(line)[1]) + line_spacing

    # บันทึกรูปภาพ
    image.convert("RGB").save("final_report.jpg", "JPEG", quality=95)
    print("✅ final_report.jpg created")

if __name__ == "__main__":
    print("🔁 Updating water report...")
    dam_value = get_chao_phraya_dam_data()
    water_value = get_inburi_bridge_data()
    weather = get_weather_status()

    status_line = f"ระดับน้ำ ณ อินทร์บุรี: {water_value} ม. | การระบายน้ำท้ายเขื่อนเจ้าพระยา: {dam_value} ลบ.ม./วินาที | สภาพอากาศ: {weather}"
    print(f"📊 {status_line}")

    create_report_image(dam_value, water_value, weather)

    with open("status.txt", "w", encoding="utf-8") as f:
        f.write(status_line)
