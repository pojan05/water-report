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

# --- 1. ส่วนของการดึงข้อมูล (ไม่ต้องแก้ไข) ---

def initialize_driver():
    """ตั้งค่าและสร้าง Driver ของ Chrome สำหรับ Selenium"""
    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=opts
    )
    return driver

def get_chao_phraya_dam_data():
    """
    ดึงข้อมูลเขื่อนเจ้าพระยาด้วย Selenium
    """
    url = 'https://tiwrm.hii.or.th/DATA/REPORT/php/chart/chaopraya/small/chaopraya.php'
    driver = initialize_driver()
    try:
        print("กำลังดึงข้อมูลเขื่อนเจ้าพระยา...")
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
                print(f"พบข้อมูลเขื่อนเจ้าพระยา: {value}")
                return str(int(float(value))) if value else "N/A"

    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการดึงข้อมูลเขื่อนเจ้าพระยา: {e}")
        if driver:
            driver.quit()
        return "N/A"
    return "N/A"


def get_inburi_bridge_data():
    """
    ดึงข้อมูลสะพานอินทร์บุรีด้วย Selenium
    """
    url = "https://singburi.thaiwater.net/wl"
    driver = initialize_driver()
    try:
        print("กำลังดึงข้อมูลสะพานอินทร์บุรี...")
        driver.get(url)
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "th[scope='row']"))
        )
        html = driver.page_source
        driver.quit()

        soup = BeautifulSoup(html, "html.parser")
        for th in soup.select("th[scope='row']"):
            if "อินทร์บุรี" in th.get_text(strip=True):
                tr   = th.find_parent("tr")
                cols = tr.find_all("td")
                water_level = cols[1].get_text(strip=True)
                print(f"พบข้อมูลสะพานอินทร์บุรี: {water_level}")
                return water_level
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการดึงข้อมูลสะพานอินทร์บุรี: {e}")
        if driver:
            driver.quit()
        return "N/A"
    
    print("Error: ไม่พบข้อมูลสถานีอินทร์บุรี")
    return "N/A"

# --- 2. ส่วนของการสร้างภาพ (ปรับปรุงใหม่ทั้งหมด) ---

def create_report_image(dam_discharge, water_level):
    """สร้างภาพรายงานสรุปสถานการณ์น้ำ พร้อมจัดวางข้อความให้สวยงาม"""
    
    if not os.path.exists("background.png") or not os.path.exists("Sarabun-Bold.ttf"):
        print("Error: ไม่พบไฟล์ background.png หรือ Sarabun-Bold.ttf")
        return

    base_image = Image.open("background.png").convert("RGBA")
    draw = ImageDraw.Draw(base_image)
    
    # --- ส่วนแก้ไข: ปรับปรุงการจัดวางตำแหน่งข้อความให้สวยงาม ---

    # 1. กำหนดข้อความและฟอนต์
    line1 = f"ระดับน้ำเจ้าพระยา ณ อินทร์บุรี: {water_level} ม."
    line2 = f"ปล่อยน้ำท้ายเขื่อนเจ้าพระยา: {dam_discharge} ม³/s"
    line3 = "สภาพอากาศ: แดดจ้า ☀️"
    
    font_path = "Sarabun-Bold.ttf"
    font_size = 48
    font = ImageFont.truetype(font_path, font_size)
    
    # 2. กำหนดกรอบพื้นที่สำหรับวางข้อความ (Aesthetic Box)
    # ค่า Y เหล่านี้กำหนดให้ข้อความอยู่กลางโซนสีเขียวของภาพพื้นหลัง
    image_width, _ = base_image.size
    box_top = 160  # จุดเริ่มต้นบนของกรอบ
    box_height = 280 # ความสูงของกรอบ
    
    # 3. คำนวณตำแหน่งกึ่งกลางภายในกรอบ
    _, _, line1_width, line1_height = draw.textbbox((0, 0), line1, font=font)
    _, _, line2_width, _ = draw.textbbox((0, 0), line2, font=font)
    _, _, line3_width, _ = draw.textbbox((0, 0), line3, font=font)

    total_text_height = (line1_height * 3) + 30 # ความสูงรวมของ 3 บรรทัด + ระยะห่าง
    y_start = box_top + (box_height - total_text_height) / 2 # หาจุด Y เริ่มต้นของบล็อกข้อความ

    # 4. วาดข้อความแต่ละบรรทัดลงบนภาพ
    x1 = (image_width - line1_width) / 2
    y1 = y_start
    draw.text((x1, y1), line1, font=font, fill="#003f5c", stroke_width=1, stroke_fill="white")

    x2 = (image_width - line2_width) / 2
    y2 = y1 + line1_height + 15 # เว้นระยะห่าง
    draw.text((x2, y2), line2, font=font, fill="#003f5c", stroke_width=1, stroke_fill="white")
    
    x3 = (image_width - line3_width) / 2
    y3 = y2 + line1_height + 15 # เว้นระยะห่าง
    draw.text((x3, y3), line3, font=font, fill="#003f5c", stroke_width=1, stroke_fill="white")

    # --- สิ้นสุดส่วนแก้ไข ---

    base_image.convert("RGB").save("final_report.jpg", "JPEG", quality=90)
    print("สร้างภาพ 'final_report.jpg' สำเร็จ (จัดวางตำแหน่งสวยงาม)")

# --- 3. ส่วนของการรันโปรแกรม ---
if __name__ == "__main__":
    print("เริ่มต้นกระบวนการสร้างรายงาน...")
    
    dam_value = get_chao_phraya_dam_data()
    level_value = get_inburi_bridge_data()
    
    print(f"ข้อมูลที่ดึงได้: เขื่อนเจ้าพระยา={dam_value}, ระดับน้ำอินทร์บุรี={level_value}")
    
    create_report_image(dam_discharge=dam_value, water_level=level_value)
    print("กระบวนการเสร็จสิ้น")
