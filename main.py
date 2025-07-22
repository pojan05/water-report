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

# --- 1. ส่วนของการดึงข้อมูล (อัปเกรดเป็น Selenium ทั้งหมด) ---

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
    ดึงข้อมูลเขื่อนเจ้าพระยาด้วย Selenium (วิธีใหม่ที่เสถียร)
    """
    url = 'https://tiwrm.hii.or.th/DATA/REPORT/php/chart/chaopraya/small/chaopraya.php'
    driver = initialize_driver()
    try:
        driver.get(url)
        # รอให้ตารางข้อมูลโหลดเสร็จ
        WebDriverWait(driver, 20).until(
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
        if driver:
            driver.quit()
        return "N/A"
    return "N/A"


def get_inburi_bridge_data():
    """
    ดึงข้อมูลสะพานอินทร์บุรีด้วย Selenium (จากโค้ดของคุณ)
    """
    url = "https://singburi.thaiwater.net/wl"
    driver = initialize_driver()
    try:
        driver.get(url)
        WebDriverWait(driver, 20).until(
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
                return water_level
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการดึงข้อมูลสะพานอินทร์บุรี: {e}")
        if driver:
            driver.quit()
        return "N/A"
    
    print("Error: ไม่พบข้อมูลสถานีอินทร์บุรี")
    return "N/A"

# --- 2. ส่วนของการสร้างภาพ (ไม่ต้องแก้ไข) ---

def create_report_image(dam_discharge, water_level):
    """สร้างภาพรายงานสรุปสถานการณ์น้ำ"""
    today = datetime.now()
    dates = [(today - timedelta(days=i)).strftime("%d/%m") for i in range(6, -1, -1)]
    
    try:
        current_level_float = float(water_level)
    except (ValueError, TypeError):
        current_level_float = 0.0

    mock_levels = [current_level_float - 0.2, current_level_float + 0.1, current_level_float - 0.1, 
                   current_level_float + 0.2, current_level_float - 0.3, current_level_float + 0.1, 
                   current_level_float]

    if not os.path.exists("background.png") or not os.path.exists("Sarabun-Regular.ttf"):
        print("Error: ไม่พบไฟล์ background.png หรือ Sarabun-Regular.ttf")
        return

    fig, ax = plt.subplots(figsize=(7.5, 3), dpi=100)
    ax.plot(dates, mock_levels, color="#0077b6", linewidth=3)
    ax.fill_between(dates, mock_levels, color="#00b4d8", alpha=0.3)
    ax.axis('off')
    fig.patch.set_alpha(0.0)
    
    graph_path = "graph.png"
    plt.savefig(graph_path, format='png', bbox_inches='tight', pad_inches=0, transparent=True)
    plt.close()

    base_image = Image.open("background.png").convert("RGBA")
    graph_image = Image.open(graph_path)
    base_image.paste(graph_image, (40, 290), graph_image)
    
    draw = ImageDraw.Draw(base_image)
    font_path = "Sarabun-Regular.ttf"
    font_large = ImageFont.truetype(font_path, 60)
    font_medium = ImageFont.truetype(font_path, 48)

    draw.text((120, 165), f"{water_level} ม.", font=font_large, fill="#003f5c")
    draw.text((430, 165), f"{dam_discharge} ม³/s", font=font_medium, fill="#003f5c")
    draw.text((120, 240), "แดดจ้า", font=font_medium, fill="#003f5c")
    draw.text((630, 280), water_level, font=font_medium, fill="white", stroke_width=2, stroke_fill="black")

    base_image.convert("RGB").save("final_report.jpg", "JPEG", quality=90)
    print("สร้างภาพ 'final_report.jpg' สำเร็จ")
    os.remove(graph_path)

# --- 3. ส่วนของการรันโปรแกรม ---
if __name__ == "__main__":
    print("เริ่มต้นกระบวนการสร้างรายงาน...")
    
    dam_value = get_chao_phraya_dam_data()
    level_value = get_inburi_bridge_data()
    
    print(f"ข้อมูลที่ดึงได้: เขื่อนเจ้าพระยา={dam_value}, ระดับน้ำอินทร์บุรี={level_value}")
    
    create_report_image(dam_discharge=dam_value, water_level=level_value)
    print("กระบวนการเสร็จสิ้น")
