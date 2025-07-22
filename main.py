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

def initialize_driver():
    """Initializes a Chrome WebDriver for Selenium."""
    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)
    return driver

def get_chao_phraya_dam_data():
    """Fetches Chao Phraya Dam data using Selenium."""
    url = 'https://tiwrm.hii.or.th/DATA/REPORT/php/chart/chaopraya/small/chaopraya.php'
    driver = initialize_driver()
    try:
        driver.set_page_load_timeout(60)
        driver.get(url)
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'ท้ายเขื่อนเจ้าพระยา')]"))
        )
        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")
        
        strong_tag = soup.find('strong', string=lambda text: text and 'ที่ท้ายเขื่อนเจ้าพระยา' in text)
        if strong_tag:
            table = strong_tag.find_parent('table')
            if table:
                volume_header_cell = table.find('td', string=lambda text: text and 'ปริมาณน้ำ' in text)
                if volume_header_cell:
                    value_cell = volume_header_cell.find_next_sibling('td')
                    if value_cell:
                        value_text = value_cell.text.strip().split('/')[0].strip()
                        float(value_text)
                        driver.quit()
                        return str(int(float(value_text)))

    except (ValueError, IndexError, AttributeError) as e:
        print(f"Error parsing dam data: {e}")
    except Exception as e:
        print(f"Error fetching dam data: {e}")
    finally:
        if driver:
            driver.quit()
    return "N/A"

def get_inburi_bridge_data():
    """Fetches In Buri Bridge data using Selenium."""
    url = "https://singburi.thaiwater.net/wl"
    driver = initialize_driver()
    try:
        # เพิ่มการตั้งเวลารอโหลดหน้าเว็บโดยเฉพาะ เพื่อจัดการกับเว็บที่ตอบสนองช้า
        driver.set_page_load_timeout(60) 
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
        print(f"Error fetching In Buri data: {e}")
    finally:
        if driver:
            driver.quit()
    return "N/A"

def create_report_image(dam_discharge, water_level):
    """Creates the final report image with data."""
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
    font_size = 36
    font = ImageFont.truetype(font_path, font_size)

    image_width, _ = base_image.size
    box_left, box_right = 80, image_width - 80
    box_top, box_bottom = 165, 400
    box_width = box_right - box_left
    box_height = box_bottom - box_top
    
    line_spacing = 15
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
    print("📦 Starting data fetch and image generation...")
    dam_value = get_chao_phraya_dam_data()
    level_value = get_inburi_bridge_data()
    print(f"📊 Water Level: {level_value} | Dam Discharge: {dam_value}")
    create_report_image(dam_discharge=dam_value, water_level=level_value)
