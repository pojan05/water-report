import os
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

load_dotenv()

def initialize_driver():
    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)

def get_chao_phraya_dam_data():
    url = 'https://tiwrm.hii.or.th/DATA/REPORT/php/chart/chaopraya/small/chaopraya.php'
    driver = initialize_driver()
    try:
        driver.set_page_load_timeout(60)
        driver.get(url)
        WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'ท้ายเขื่อนเจ้าพระยา')]")))
        soup = BeautifulSoup(driver.page_source, "html.parser")
        strong_tag = soup.find('strong', string=lambda t: t and 'ที่ท้ายเขื่อนเจ้าพระยา' in t)
        if strong_tag:
            table = strong_tag.find_parent('table')
            td = table.find('td', string=lambda t: t and 'ปริมาณน้ำ' in t)
            if td:
                value = td.find_next_sibling('td').text.strip().split('/')[0]
                print(f"✅ Dam discharge raw value: {value}")
                return str(int(float(value)))
    except Exception as e:
        print(f"❌ Dam error: {e}")
    finally:
        driver.quit()
    return "-" # แก้ไข: คืนค่าเป็น "-" เมื่อเกิดข้อผิดพลาด

def get_inburi_bridge_data():
    url = "https://singburi.thaiwater.net/wl"
    driver = initialize_driver()
    try:
        driver.set_page_load_timeout(60)
        driver.get(url)
        WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.XPATH, "//th[contains(text(), 'อินทร์บุรี')]")))
        soup = BeautifulSoup(driver.page_source, "html.parser")
        for th in soup.select("th[scope='row']"):
            if "อินทร์บุรี" in th.get_text(strip=True):
                value = th.find_parent("tr").find_all("td")[1].get_text(strip=True)
                print(f"✅ Water level @Inburi (Selenium): {value}")
                return value
        print("❌ 'อินทร์บุรี' not found in table")
    except TimeoutException:
        print("❌ Timeout loading Inburi bridge data via Selenium")
    except Exception as e:
        print(f"❌ Inburi (Selenium) error: {e}")
    finally:
        driver.quit()
    return "-" # แก้ไข: คืนค่าเป็น "-" เมื่อเกิดข้อผิดพลาด

def get_weather_status():
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        return "N/A"
    lat, lon = "14.9", "100.4"
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&lang=th&units=metric"
    try:
        res = requests.get(url, timeout=30)
        data = res.json()
        desc = data["weather"][0]["description"]
        emoji = "🌧️" if "ฝน" in desc else "☁️" if "เมฆ" in desc else "☀️"
        return f"{desc.capitalize()} {emoji}"
    except Exception as e:
        print(f"❌ Weather fetch error: {e}")
        return "N/A"

def create_report_image(dam_discharge, water_level, weather_status):
    image = Image.open("background.png").convert("RGBA")
    draw = ImageDraw.Draw(image)
    
    # สร้างรายการข้อความที่จะแสดง โดยกรองบรรทัดที่ข้อมูลเป็น "-" ออกไป
    lines_data = {
        f"ระดับน้ำ ณ อินทร์บุรี: {water_level} ม.": water_level,
        f"การระบายน้ำท้ายเขื่อนฯ: {dam_discharge} ลบ.ม./วินาที": dam_discharge,
        f"สภาพอากาศ: {weather_status}": weather_status
    }
    lines = [text for text, value in lines_data.items() if value != "-"]

    if not lines: # กรณีที่ไม่มีข้อมูลเลย
        lines = ["ไม่สามารถอัปเดตข้อมูลได้ในขณะนี้"]

    font_path = "Sarabun-Bold.ttf" if os.path.exists("Sarabun-Bold.ttf") else "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
    font = ImageFont.truetype(font_path, 34)

    box_left, box_right = 60, 710
    box_top, box_bottom = 125, 370
    box_width = box_right - box_left
    box_height = box_bottom - box_top
    line_spacing = 20
    
    total_text_height = sum([font.getbbox(line)[3] - font.getbbox(line)[1] for line in lines])
    total_height_with_spacing = total_text_height + line_spacing * (len(lines) - 1)
    y = box_top + (box_height - total_height_with_spacing) / 2

    for line in lines:
        text_width = draw.textlength(line, font=font)
        x = box_left + (box_width - text_width) / 2
        draw.text((x, y), line, font=font, fill="#003f5c", stroke_width=1, stroke_fill="white")
        y += (font.getbbox(line)[3] - font.getbbox(line)[1]) + line_spacing

    image.convert("RGB").save("final_report.jpg", "JPEG", quality=95)
    print("✅ final_report.jpg created")

if __name__ == "__main__":
    print("🔁 Updating water report...")
    dam_value = get_chao_phraya_dam_data()
    water_value = get_inburi_bridge_data()
    weather = get_weather_status()

    # สร้าง status_line โดยกรองข้อมูลที่เป็น "-" ออกไป
    status_parts = []
    if water_level != "-": status_parts.append(f"ระดับน้ำ ณ อินทร์บุรี: {water_level} ม.")
    if dam_value != "-": status_parts.append(f"การระบายน้ำท้ายเขื่อนเจ้าพระยา: {dam_value} ลบ.ม./วินาที")
    if weather != "N/A": status_parts.append(f"สภาพอากาศ: {weather}")
    status_line = " | ".join(status_parts)
    
    print(f"📊 {status_line}")

    create_report_image(dam_value, water_level, weather)

    with open("status.txt", "w", encoding="utf-8") as f:
        f.write(status_line)
