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

def get_dynamic_caption(water_level: str, weather_status: str) -> tuple[str, str]:
    try:
        level_float = float(water_level)
    except (ValueError, TypeError):
        return "อินทร์บุรีต้องรอด!", "#999999" # Fallback if water_level is N/A or invalid

    if level_float < 7.0:
        level = "ต่ำ"
        color = "#00b050" # Green
    elif level_float < 9.0:
        level = "ปกติ"
        color = "#ff9900" # Orange
    else:
        level = "เตือน"
        color = "#ff3b3b" # Red

    captions = {
        "แดดจ้า": {
            "ต่ำ": ["แดดแรงแต่น้ำนิ่ง สบายใจได้จ้า~", "น้ำใสไหลเย็นเห็นตัวปลา แดดจ้าๆแบบนี้"],
            "ปกติ": ["แดดแรงแต่น้ำยังไม่ล้น อินทร์บุรียังรอด!", "สถานการณ์ยังคุมได้อยู่"],
            "เตือน": ["แดดมาแต่น้ำก็มาด้วย อินทร์บุรีเฝ้าระวัง!", "น้ำขึ้นสูง ให้รีบเก็บของ!"]
        },
        "ฝนตก": {
            "ต่ำ": ["ฝนตกแต่น้ำยังน้อย อินทร์บุรียังปลอดภัย", "ฝนตกชิลล์ๆ น้ำยังไม่มา"],
            "ปกติ": ["ฝนกับน้ำมาคู่กัน อินทร์บุรีต้องตั้งสติ", "ฝนตก น้ำเริ่มเยอะ จับตาดู!"],
            "เตือน": ["น้ำแรง ฝนแรง อย่าประมาทเด็ดขาด!", "พายุเข้า น้ำก็มา เตรียมพร้อม!"]
        },
        "ครึ้มฟ้า": {
            "ต่ำ": ["ครึ้มฟ้าแต่น้ำยังน้อย อินทร์บุรียังนิ่ง", "ฟ้ามืดแต่ใจสว่าง น้ำยังห่างไกล"],
            "ปกติ": ["ท้องฟ้าครึ้ม น้ำปกติ อินทร์บุรียังไหว", "เมฆเยอะ น้ำก็เยอะ เฝ้าระวังนะ"],
            "เตือน": ["น้ำมาแน่ ฟ้าก็มืด อินทร์บุรีต้องรอด", "ฟ้ามืด น้ำขึ้น เตรียมรับมือ!"]
        }
    }
    
    today = datetime.today().strftime("%Y%m%d")
    random.seed(today + weather_status) # Makes the random choice consistent for the day
    
    cap_list = captions.get(weather_status, {}).get(level, [])
    caption = random.choice(cap_list) if cap_list else "อินทร์บุรีต้องรอด!"
    
    return caption, color

def create_report_image(dam_discharge, water_level):
    if not os.path.exists("background.png"):
        print("background.png not found.")
        return
    base_image = Image.open("background.png").convert("RGBA")
    draw = ImageDraw.Draw(base_image)

    weather_status = "แดดจ้า" # You can make this dynamic later
    lines = [
        f"ระดับน้ำ ณ อินทร์บุรี: {water_level} ม.",
        f"การระบายน้ำท้ายเขื่อนเจ้าพระยา: {dam_discharge} ลบ.ม./วินาที",
        f"สภาพอากาศ: {weather_status} ☀️"
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

    # --- Start of Modified Section ---
    
    number_color = "#e60023"  # สีแดงสดสำหรับตัวเลข
    text_color = "#003f5c"    # สีน้ำเงินเข้มสำหรับข้อความ

    # Line 1: Water Level
    line1_parts = ["ระดับน้ำ ณ อินทร์บุรี: ", str(water_level), " ม."]
    line1_widths = [draw.textbbox((0,0), p, font=font)[2] for p in line1_parts]
    total_width1 = sum(line1_widths)
    x_start1 = box_left + (box_width - total_width1) / 2
    
    draw.text((x_start1, y_start), line1_parts[0], font=font, fill=text_color)
    x_start1 += line1_widths[0]
    draw.text((x_start1, y_start), line1_parts[1], font=font, fill=number_color)
    x_start1 += line1_widths[1]
    draw.text((x_start1, y_start), line1_parts[2], font=font, fill=text_color)
    y_start += text_heights[0] + line_spacing

    # Line 2: Dam Discharge
    line2_parts = ["การระบายน้ำท้ายเขื่อนเจ้าพระยา: ", str(dam_discharge), " ลบ.ม./วินาที"]
    line2_widths = [draw.textbbox((0,0), p, font=font)[2] for p in line2_parts]
    total_width2 = sum(line2_widths)
    x_start2 = box_left + (box_width - total_width2) / 2

    draw.text((x_start2, y_start), line2_parts[0], font=font, fill=text_color)
    x_start2 += line2_widths[0]
    draw.text((x_start2, y_start), line2_parts[1], font=font, fill=number_color)
    x_start2 += line2_widths[1]
    draw.text((x_start2, y_start), line2_parts[2], font=font, fill=text_color)
    y_start += text_heights[1] + line_spacing
    
    # Line 3: Weather
    line3 = lines[2]
    text_w3 = draw.textbbox((0, 0), line3, font=font)[2]
    x3 = box_left + (box_width - text_w3) / 2
    draw.text((x3, y_start), line3, font=font, fill=text_color)
    
    # --- End of Modified Section ---

    # Dynamic Caption
    caption, color = get_dynamic_caption(water_level, weather_status)
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
