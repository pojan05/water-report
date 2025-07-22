
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
from datetime import datetime
import random

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
        driver.set_page_load_timeout(60)
        driver.get(url)
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'ท้ายเขื่อนเจ้าพระยา')]")))
        soup = BeautifulSoup(driver.page_source, "html.parser")
        strong_tag = soup.find('strong', string=lambda text: text and 'ที่ท้ายเขื่อนเจ้าพระยา' in text)
        if strong_tag:
            table = strong_tag.find_parent('table')
            if table:
                volume_cell = table.find('td', string=lambda text: text and 'ปริมาณน้ำ' in text)
                if volume_cell:
                    next_td = volume_cell.find_next_sibling('td')
                    if next_td:
                        value = next_td.text.strip().split("/")[0]
                        return str(int(float(value)))
    except Exception as e:
        print(f"Error fetching dam data: {e}")
    finally:
        driver.quit()
    return "N/A"

def get_inburi_bridge_data():
    url = "https://singburi.thaiwater.net/wl"
    driver = initialize_driver()
    try:
        driver.set_page_load_timeout(60) 
        driver.get(url)
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, "th[scope='row']")))
        soup = BeautifulSoup(driver.page_source, "html.parser")
        for th in soup.select("th[scope='row']"):
            if "อินทร์บุรี" in th.get_text(strip=True):
                tr = th.find_parent("tr")
                cols = tr.find_all("td")
                return cols[1].get_text(strip=True)
    except Exception as e:
        print(f"Error fetching In Buri data: {e}")
    finally:
        driver.quit()
    return "N/A"

def get_dynamic_caption(water_level: float, weather_status: str, gender: str = "neutral") -> tuple[str, str]:
    try:
        water_level = float(water_level)
    except:
        return "อินทร์บุรีต้องรอด!", "#999999"

    if water_level < 7.0:
        level = "ต่ำ"
        color = "#00b050"
    elif water_level < 9.0:
        level = "ปกติ"
        color = "#ff9900"
    else:
        level = "เตือน"
        color = "#ff3b3b"
    captions = {
        "แดดจ้า": {
            "ต่ำ": {"neutral": ["แดดแรงแต่น้ำนิ่ง สบายใจได้จ้า~"]},
            "ปกติ": {"neutral": ["แดดแรงแต่น้ำยังไม่ล้น อินทร์บุรียังรอด!"]},
            "เตือน": {"neutral": ["แดดมาแต่น้ำก็มาด้วย อินทร์บุรีเฝ้าระวัง!"]}
        },
        "ฝนตก": {
            "ต่ำ": {"neutral": ["ฝนตกแต่น้ำยังน้อย อินทร์บุรียังปลอดภัย"]},
            "ปกติ": {"neutral": ["ฝนกับน้ำมาคู่กัน อินทร์บุรีต้องตั้งสติ"]},
            "เตือน": {"neutral": ["น้ำแรง ฝนแรง อย่าประมาทเด็ดขาด!"]}
        },
        "ครึ้มฟ้า": {
            "ต่ำ": {"neutral": ["ครึ้มฟ้าแต่น้ำยังน้อย อินทร์บุรียังนิ่ง"]},
            "ปกติ": {"neutral": ["ท้องฟ้าครึ้ม น้ำปกติ อินทร์บุรียังไหว"]},
            "เตือน": {"neutral": ["น้ำมาแน่ ฟ้าก็มืด อินทร์บุรีต้องรอด"]}
        }
    }
    today = datetime.today().strftime("%Y%m%d")
    random.seed(today + weather_status)
    cap_list = captions.get(weather_status, {}).get(level, {}).get(gender, [])
    caption = random.choice(cap_list) if cap_list else "อินทร์บุรีต้องรอด!"
    return caption, color

def create_report_image(dam_discharge, water_level):
    if not os.path.exists("background.png"):
        print("background.png not found.")
        return
    base_image = Image.open("background.png").convert("RGBA")
    draw = ImageDraw.Draw(base_image)

    lines = [
        f"ระดับน้ำ ณ อินทร์บุรี: {water_level} ม.",
        f"การระบายน้ำท้ายเขื่อนเจ้าพระยา: {dam_discharge} ลบ.ม./วินาที",
        "สภาพอากาศ: แดดจ้า ☀️"
    ]
    font_path = "Sarabun-Bold.ttf" if os.path.exists("Sarabun-Bold.ttf") else "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    font = ImageFont.truetype(font_path, 44)

    image_width, _ = base_image.size
    box_left, box_right = 80, image_width - 80
    box_top, box_bottom = 165, 400
    box_width = box_right - box_left
    box_height = box_bottom - box_top

    line_spacing = 25
    text_heights = [draw.textbbox((0, 0), line, font=font)[3] for line in lines]
    total_text_height = sum(text_heights) + line_spacing * (len(lines) - 1)
    y_start = box_top + (box_height - total_text_height) / 2

    for i, line in enumerate(lines):
        text_w = draw.textbbox((0, 0), line, font=font)[2]
        x = box_left + (box_width - text_w) / 2
        draw.text((x, y_start), line, font=font, fill="#003f5c", stroke_width=1, stroke_fill="white")
        y_start += text_heights[i] + line_spacing

    # แคปชั่นอัตโนมัติ
    caption, color = get_dynamic_caption(water_level, "แดดจ้า")
    caption_font = ImageFont.truetype(font_path, 38)
    draw.text((image_width / 2, 430), caption, font=caption_font, fill=color, anchor="mm")

    base_image.convert("RGB").save("final_report.jpg", "JPEG", quality=95)
    print("✅ final_report.jpg created successfully")

if __name__ == "__main__":
    print("📦 Starting data fetch and image generation...")
    dam_value = get_chao_phraya_dam_data()
    level_value = get_inburi_bridge_data()
    print(f"📊 Water Level: {level_value} | Dam Discharge: {dam_value}")
    create_report_image(dam_discharge=dam_value, water_level=level_value)
