import os
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from PIL import Image, ImageDraw, ImageFont

def initialize_driver():
    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("user-agent=Mozilla/5.0")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)

def get_chao_phraya_dam_data():
    url = 'https://tiwrm.hii.or.th/DATA/REPORT/php/chart/chaopraya/small/chaopraya.php'
    driver = initialize_driver()
    try:
        driver.get(url)
        WebDriverWait(driver, 30).until(
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
        print("❌ Dam error:", e)
    finally:
        driver.quit()
    return "ไม่สามารถดึงข้อมูล"

def get_inburi_bridge_data():
    url = "https://singburi.thaiwater.net/wl"
    driver = initialize_driver()
    try:
        driver.get(url)
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "th[scope='row']"))
        )
        soup = BeautifulSoup(driver.page_source, "html.parser")
        for th in soup.select("th[scope='row']"):
            if "อินทร์บุรี" in th.get_text(strip=True):
                value = th.find_parent("tr").find_all("td")[1].get_text(strip=True)
                print(f"✅ Water level @Inburi: {value}")
                return value
        print("❌ 'อินทร์บุรี' not found in table")
    except Exception as e:
        print("❌ Inburi error:", e)
    finally:
        driver.quit()
    return "ไม่สามารถดึงข้อมูล"

def get_weather_status():
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        print("❌ OPENWEATHER_API_KEY not found in environment")
        return "ข้อมูลสภาพอากาศไม่พร้อม"
    lat, lon = "14.9", "100.4"
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&lang=th&units=metric"
    try:
        print("📡 Fetching weather from:", url)
        res = requests.get(url)
        data = res.json()
        print("✅ Weather API response:", data)
        desc = data["weather"][0]["description"]
        emoji = "🌧️" if "ฝน" in desc else "⛅" if "เมฆ" in desc else "☀️"
        return f"{desc.capitalize()} {emoji}"
    except Exception as e:
        print("❌ Weather fetch error:", e)
        return "ข้อมูลสภาพอากาศไม่พร้อม"

def create_report_image(dam_discharge, water_level, weather_status):
    if not os.path.exists("background.png"):
        print("❌ background.png not found")
        return

    image = Image.open("background.png").convert("RGBA")
    draw = ImageDraw.Draw(image)

    lines = [
        f"ระดับน้ำ ณ อินทร์บุรี: {water_level} ม.",
        f"การระบายน้ำท้ายเขื่อนเจ้าพระยา: {dam_discharge} ลบ.ม./วินาที",
        f"สภาพอากาศ: {weather_status}"
    ]

    font_path = "Sarabun-Bold.ttf" if os.path.exists("Sarabun-Bold.ttf") else "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    font = ImageFont.truetype(font_path, 34)

    # พิกัดกรอบข้อความ: x = 60 to 710, y = 125 to 370
    box_left, box_right = 60, 710
    box_top, box_bottom = 125, 370
    box_width = box_right - box_left
    box_height = box_bottom - box_top

    line_spacing = 15
    text_heights = [draw.textbbox((0, 0), l, font=font)[3] for l in lines]
    total_height = sum(text_heights) + line_spacing * (len(lines) - 1)
    y = box_top + (box_height - total_height) / 2

    for i, line in enumerate(lines):
        text_w = draw.textbbox((0, 0), line, font=font)[2]
        x = box_left + (box_width - text_w) / 2
        draw.text((x, y), line, font=font, fill="#003f5c", stroke_width=1, stroke_fill="white")
        y += text_heights[i] + line_spacing

    image.convert("RGB").save("final_report.jpg", "JPEG", quality=95)
    print("✅ final_report.jpg created")

if __name__ == "__main__":
    print("🔁 Updating water report...")
    dam_value = get_chao_phraya_dam_data()
    water_value = get_inburi_bridge_data()
    weather = get_weather_status()
    print(f"📊 ระดับน้ำ: {water_value} | เขื่อน: {dam_value} | อากาศ: {weather}")
    create_report_image(dam_value, water_value, weather)
