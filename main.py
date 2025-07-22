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

# --- 1. ส่วนของการดึงข้อมูล (นำมาจากโค้ดของคุณ) ---

def get_chao_phraya_dam_data():
    """
    ดึงข้อมูลเขื่อนเจ้าพระยาจาก JSON ในหน้าเว็บ (จาก scraper.py)
    """
    url = 'https://tiwrm.hii.or.th/DATA/REPORT/php/chart/chaopraya/small/chaopraya.php'
    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        response.encoding = 'utf-8'
        
        match = re.search(r'var json_data = (\[.*\]);', response.text)
        if not match:
            print("Error: ไม่พบ json_data ในหน้าเว็บเขื่อนเจ้าพระยา")
            return "N/A"
            
        json_string = match.group(1)
        data = json.loads(json_string)
        
        # ค้นหาข้อมูลปล่อยน้ำของสถานี C.2 (ท้ายเขื่อนเจ้าพระยา)
        flow = data[0].get('itc_water', {}).get('C2', {}).get('q')
        return str(int(float(flow))) if flow else "N/A"

    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการดึงข้อมูลเขื่อนเจ้าพระยา: {e}")
        return "N/A"

def get_inburi_bridge_data():
    """
    ดึงข้อมูลสะพานอินทร์บุรีด้วย Selenium (จาก inburi_bridge_alert.py)
    """
    url = "https://singburi.thaiwater.net/wl"
    try:
        opts = Options()
        opts.add_argument("--headless")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")

        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=opts
        )
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
        return "N/A"
    
    print("Error: ไม่พบข้อมูลสถานีอินทร์บุรี")
    return "N/A"

# --- 2. ส่วนของการสร้างภาพ (จากโค้ดของผม) ---

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
