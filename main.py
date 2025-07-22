import os
import requests
import pandas as pd
import matplotlib.pyplot as plt
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta

# --- 1. ส่วนของการดึงข้อมูล ---

def get_dam_data():
    """ดึงข้อมูลการปล่อยน้ำท้ายเขื่อนเจ้าพระยา (C.2)"""
    try:
        url = "https://tiwrm.hii.or.th/DATA/REPORT/php/chart/chaopraya/small/chaopraya.php"
        response = requests.get(url, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        table_cells = soup.find_all('td')
        for i, cell in enumerate(table_cells):
            if "ท้ายเขื่อนเจ้าพระยา" in cell.text:
                discharge_text = table_cells[i + 1].text.strip()
                discharge_value = discharge_text.split('/')[0].strip()
                return discharge_value
    except Exception as e:
        print(f"Error getting dam data: {e}")
        return "N/A"
    return "N/A"

def get_inburi_water_level():
    """ดึงข้อมูลระดับน้ำที่อินทร์บุรี (C.35) โดยใช้ Selenium"""
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_-options.add_argument("--disable-dev-shm-usage")
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.get("https://singburi.thaiwater.net/wl")
        
        # รอจนกว่าตารางข้อมูลจะปรากฏ
        wait = WebDriverWait(driver, 15)
        wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'C.35')]")))
        
        # ค้นหาแถวของสถานี C.35 แล้วดึงข้อมูลระดับน้ำ
        rows = driver.find_elements(By.TAG_NAME, "tr")
        for row in rows:
            if "C.35" in row.text:
                columns = row.find_elements(By.TAG_NAME, "td")
                water_level = columns[2].text.strip() # คอลัมน์ที่ 3 คือระดับน้ำ
                driver.quit()
                return water_level
    except Exception as e:
        print(f"Error getting In Buri water level: {e}")
        driver.quit()
        return "N/A"
    return "N/A"

# --- 2. ส่วนของการสร้างภาพ ---

def create_report_image(dam_discharge, water_level):
    """สร้างภาพรายงานสรุปสถานการณ์น้ำ"""
    # ค่าสมมติสำหรับกราฟ 7 วัน (ในโปรเจกต์จริงควรดึงข้อมูลจริงมาเก็บ)
    today = datetime.now()
    dates = [(today - timedelta(days=i)).strftime("%d/%m") for i in range(6, -1, -1)]
    mock_levels = [8.1, 7.8, 7.5, 7.9, 8.2, 8.0, float(water_level) if water_level != "N/A" else 8.0]

    # ตรวจสอบว่าไฟล์ที่จำเป็นอยู่ครบหรือไม่
    if not os.path.exists("background.png") or not os.path.exists("Sarabun-Regular.ttf"):
        print("ไม่พบไฟล์ background.png หรือ Sarabun-Regular.ttf")
        return

    # สร้างกราฟด้วย Matplotlib
    fig, ax = plt.subplots(figsize=(7.5, 3), dpi=100)
    ax.plot(dates, mock_levels, color="#0077b6", linewidth=3)
    ax.fill_between(dates, mock_levels, color="#00b4d8", alpha=0.3)
    ax.axis('off')
    fig.patch.set_alpha(0.0)
    
    graph_path = "graph.png"
    plt.savefig(graph_path, format='png', bbox_inches='tight', pad_inches=0, transparent=True)
    plt.close()

    # ประกอบภาพด้วย Pillow
    base_image = Image.open("background.png").convert("RGBA")
    graph_image = Image.open(graph_path)
    
    # วางกราฟลงบนพื้นหลัง (ปรับตำแหน่งตามต้องการ)
    base_image.paste(graph_image, (40, 290), graph_image)
    
    draw = ImageDraw.Draw(base_image)
    font_path = "Sarabun-Regular.ttf"
    font_large = ImageFont.truetype(font_path, 60)
    font_medium = ImageFont.truetype(font_path, 48)

    # วาดข้อความ (ปรับตำแหน่งและสีตามภาพตัวอย่าง)
    # ระดับน้ำวันนี้
    draw.text((120, 165), f"{water_level} ม.", font=font_large, fill="#003f5c")
    # ปล่อยน้ำจากเขื่อน
    draw.text((430, 165), f"{dam_discharge} ม³/s", font=font_medium, fill="#003f5c")
    # สภาพอากาศ (ในตัวอย่างนี้ใส่ค่าคงที่ไปก่อน)
    draw.text((120, 240), "แดดจ้า", font=font_medium, fill="#003f5c")
    
    # วาดตัวเลขบนกราฟ
    draw.text((630, 280), water_level, font=font_medium, fill="white", stroke_width=2, stroke_fill="black")

    # บันทึกเป็นไฟล์สุดท้าย
    base_image.convert("RGB").save("final_report.jpg", "JPEG", quality=90)
    print("สร้างภาพ final_report.jpg สำเร็จ")
    
    # ลบไฟล์กราฟชั่วคราว
    os.remove(graph_path)

# --- 3. ส่วนของการรันโปรแกรม ---

if __name__ == "__main__":
    print("เริ่มต้นกระบวนการสร้างรายงาน...")
    dam_value = get_dam_data()
    level_value = get_inburi_water_level()
    
    print(f"ข้อมูลที่ดึงได้: เขื่อนเจ้าพระยา={dam_value}, ระดับน้ำอินทร์บุรี={level_value}")
    
    create_report_image(dam_discharge=dam_value, water_level=level_value)
    print("กระบวนการเสร็จสิ้น")
