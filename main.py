import os
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from PIL import Image, ImageDraw, ImageFont

# --- ส่วนดึงข้อมูลจากเว็บไซต์ ---

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
        soup = BeautifulSoup(html, "html.parser")
        cells = soup.find_all('td')
        for i, cell in enumerate(cells):
            if "ท้ายเขื่อนเจ้าพระยา" in cell.text:
                value = cells[i + 1].text.strip().split('/')[0].strip()
                driver.quit()
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
        soup = BeautifulSoup(html, "html.parser")
        for th in soup.select("th[scope='row']"):
            if "อินทร์บุรี" in th.get_text(strip=True):
                tr = th.find_parent("tr")
                cols = tr.find_all("td")
                driver.quit()
                return cols[1].get_text(strip=True)
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการดึงข้อมูลอินทร์บุรี: {e}")
        driver.quit()
        return "N/A"
    return "N/A"

# --- สร้างภาพพร้อมจัดข้อความในกรอบเหลืองอย่างเหมาะสม ---

def create_report_image(dam_discharge, water_level):
    if not os.path.exists("background.png"):
        print("ไม่พบ background.png")
        return

    background_path = "background.png"
    base_image = Image.open(background_path).convert("RGBA")
    draw = ImageDraw.Draw(base_image)

    # ข้อความที่จะแสดง
    lines = [
        f"ระดับน้ำเจ้าพระยา ณ อินทร์บุรี: {water_level} ม.",
        f"ปล่อยน้ำท้ายเขื่อนเจ้าพระยา: {dam_discharge} ม³/s",
        "สภาพอากาศ: แดดจ้า ☀️"
    ]

    # ฟอนต์
    font_path = "Sarabun-Bold.ttf" if os.path.exists("Sarabun-Bold.ttf") else "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    font_size = 38
    font = ImageFont.truetype(font_path, font_size)

    # ขนาดภาพและกรอบเหลือง
    image_width, image_height = base_image.size
    box_left = 80
    box_right = image_width - 80
    box_top = 165
    box_bottom = 575  # ป้องกันไม่ให้ติด sponsor text
    box_width = box_right - box_left
    box_height = box_bottom - box_top

    # จัดข้อความให้อยู่ตรงกลางกรอบเหลือง
    line_spacing = 16
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
    print("✅ สร้างภาพ final_report.jpg เสร็จสมบูรณ์")

# --- เริ่มรันโปรแกรม ---

if __name__ == "__main__":
    print("📦 เริ่มต้นดึงข้อมูลและสร้างภาพ...")
    dam_value = get_chao_phraya_dam_data()
    level_value = get_inburi_bridge_data()
    print(f"📊 ระดับน้ำ: {level_value} | ปล่อยน้ำ: {dam_value}")
    create_report_image(dam_discharge=dam_value, water_level=level_value)
