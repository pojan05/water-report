import os
import re
import json
import requests
import matplotlib.pyplot as plt
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta

# --- 1. ส่วนของการดึงข้อมูล ---

def initialize_driver():
    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("user-agent=Mozilla/5.0")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)
    return driver

def get_chao_phraya_dam_data():
    url = 'https://tiwrm.hii.or.th/DATA/REPORT/php/chart/chaopraya/small/chaopraya.php'
    driver = initialize_driver()
    try:
        driver.get(url)
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'ท้ายเขื่อนเจ้าพระยา')]"))
        )
        html = driver.page_source
        driver.quit()
        soup = BeautifulSoup(html, "html.parser")
        cells = soup.find_all('td')
        for i, cell in enumerate(cells):
            if "ท้ายเขื่อนเจ้าพระยา" in cell.text:
                value = cells[i + 1].text.strip().split('/')[0].strip()
                return str(int(float(value))) if value else "N/A"
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการดึงข้อมูลเขื่อนเจ้าพระยา: {e}")
        driver.quit()
        return "N/A"
    return "N/A"

def get_inburi_bridge_data():
    url = "https://singburi.thaiwater.net/wl"
    driver = initialize_driver()
    try:
        driver.get(url)
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "th[scope='row']"))
        )
        html = driver.page_source
        driver.quit()
        soup = BeautifulSoup(html, "html.parser")
        for th in soup.select("th[scope='row']"):
            if "อินทร์บุรี" in th.get_text(strip=True):
                tr = th.find_parent("tr")
                cols = tr.find_all("td")
                return cols[1].get_text(strip=True)
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการดึงข้อมูลอินทร์บุรี: {e}")
        driver.quit()
        return "N/A"
    return "N/A"

# --- 2. สร้างภาพสรุป (จัดให้อยู่ในกรอบสีเหลืองพอดี) ---

def create_report_image(dam_discharge, water_level):
    if not os.path.exists("background.png") or not os.path.exists("Sarabun-Bold.ttf"):
        print("ไม่พบไฟล์พื้นหลังหรือฟอนต์")
        return

    base_image = Image.open("background.png").convert("RGBA")
    draw = ImageDraw.Draw(base_image)

    lines = [
        f"ระดับน้ำ ณ อินทร์บุรี: {water_level} ม.",
        f"การระบายน้ำท้ายเขื่อนเจ้าพระยา: {dam_discharge} ลบ.ม./วินาที",
        "สภาพอากาศ: แดดจ้า ☀️"
    ]

    font_path = "Sarabun-Bold.ttf"
    font_size = 40
    font = ImageFont.truetype(font_path, font_size)

    img_w, img_h = base_image.size
    box_left = 100
    box_right = img_w - 100
    box_top = 170
    box_bottom = 170 + 340
    box_width = box_right - box_left
    box_height = box_bottom - box_top

    line_spacing = 15
    text_heights = []
    text_widths = []

    for line in lines:
        _, _, w, h = draw.textbbox((0, 0), line, font=font)
        text_widths.append(w)
        text_heights.append(h)

    total_text_height = sum(text_heights) + line_spacing * (len(lines) - 1)
    y_start = box_top + (box_height - total_text_height) / 2

    for i, line in enumerate(lines):
        text_w = text_widths[i]
        text_h = text_heights[i]
        x = box_left + (box_width - text_w) / 2
        y = y_start
        draw.text((x, y), line, font=font, fill="#003f5c", stroke_width=1, stroke_fill="white")
        y_start += text_h + line_spacing

    base_image.convert("RGB").save("final_report.jpg", "JPEG", quality=95)
    print("สร้างภาพ 'final_report.jpg' สำเร็จ")

# --- 3. เริ่มทำงาน ---

if __name__ == "__main__":
    print("กำลังดึงข้อมูลน้ำ...")
    dam_value = get_chao_phraya_dam_data()
    level_value = get_inburi_bridge_data()
    print(f"ระดับน้ำ: {level_value}, การปล่อยน้ำ: {dam_value}")
    create_report_image(dam_discharge=dam_value, water_level=level_value)
