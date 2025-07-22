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
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'ท้ายเขื่อนเจ้าพระยา')]")))
        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")
        strong_tag = soup.find('strong', string=lambda t: t and 'ที่ท้ายเขื่อนเจ้าพระยา' in t)
        if strong_tag:
            table = strong_tag.find_parent('table')
            volume_cell = table.find('td', string=lambda t: t and 'ปริมาณน้ำ' in t)
            if volume_cell:
                value_text = volume_cell.find_next_sibling('td').text.strip().split('/')[0].strip()
                float(value_text)  # validate
                return str(int(float(value_text)))
    except Exception as e:
        print(f"Error fetching dam data: {e}")
    finally:
        driver.quit()
    return "N/A"

def get_inburi_bridge_data():
    url = "https://singburi.thaiwater.net/wl"
    driver = initialize_driver()
    try:
        driver.get(url)
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, "th[scope='row']")))
        soup = BeautifulSoup(driver.page_source, "html.parser")
        for th in soup.select("th[scope='row']"):
            if "อินทร์บุรี" in th.get_text(strip=True):
                tr = th.find_parent("tr")
                return tr.find_all("td")[1].get_text(strip=True)
    except Exception as e:
        print(f"Error fetching In Buri data: {e}")
    finally:
        driver.quit()
    return "N/A"

def get_weather_text():
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=14.930&longitude=100.338&current=temperature_2m,weathercode&timezone=Asia/Bangkok"
        data = requests.get(url).json()
        code = data["current"]["weathercode"]
        code_map = {
            0: "แจ่มใส ☀",
            1: "มีเมฆน้อย 🌤",
            2: "ครึ้มฟ้า ☁",
            3: "เมฆมาก ☁☁",
            45: "มีหมอก 🌫",
            61: "ฝนเบา 🌦",
            63: "ฝนปานกลาง 🌧",
            65: "ฝนหนัก ⛈",
            80: "ฝนฟ้าคะนอง ⛈🌩",
        }
        return code_map.get(code, "ไม่สามารถระบุอากาศ")
    except:
        return "ข้อมูลอากาศไม่พร้อม"

def create_report_image(dam_discharge, water_level, weather):
    if not os.path.exists("background.png"):
        print("❌ ไม่พบไฟล์ background.png")
        return

    base_image = Image.open("background.png").convert("RGBA")
    draw = ImageDraw.Draw(base_image)

    font_path = "Sarabun-Bold.ttf"
    font = ImageFont.truetype(font_path, 38)
    lines = [
        f"ระดับน้ำ ณ อินทร์บุรี: {water_level} ม.",
        f"การระบายน้ำท้ายเขื่อนเจ้าพระยา: {dam_discharge} ลบ.ม./วินาที",
        f"สภาพอากาศ: {weather}"
    ]

    image_width, _ = base_image.size
    box_left, box_right = 80, image_width - 80
    box_top, box_bottom = 165, 400
    box_width = box_right - box_left
    box_height = box_bottom - box_top
    line_spacing = 20

    text_heights = [draw.textbbox((0, 0), line, font=font)[3] for line in lines]
    total_text_height = sum(text_heights) + line_spacing * (len(lines) - 1)
    y_start = box_top + (box_height - total_text_height) / 2

    for i, line in enumerate(lines):
        text_w = draw.textbbox((0, 0), line, font=font)[2]
        x = box_left + (box_width - text_w) / 2
        draw.text((x, y_start), line, font=font, fill="#003f5c", stroke_width=1, stroke_fill="white")
        y_start += text_heights[i] + line_spacing

    base_image.convert("RGB").save("final_report.jpg", "JPEG", quality=95)
    print("✅ final_report.jpg created successfully")

if __name__ == "__main__":
    print("📦 ดึงข้อมูล...")
    dam = get_chao_phraya_dam_data()
    water = get_inburi_bridge_data()
    weather = get_weather_text()
    print(f"📊 ระดับน้ำ: {water} ม. | ปล่อยน้ำ: {dam} | อากาศ: {weather}")
    create_report_image(dam, water, weather)
