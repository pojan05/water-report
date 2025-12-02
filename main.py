import os
import json
import requests
import re
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
from requests_html import HTMLSession

# --- 1. ฟังก์ชันดึงข้อมูลเขื่อน (คงเดิม) ---
def get_chao_phraya_dam_data():
    url = 'https://tiwrm.hii.or.th/DATA/REPORT/php/chart/chaopraya/small/chaopraya.php'
    try:
        res = requests.get(url, timeout=30)
        res.raise_for_status()
        match = re.search(r'var json_data = (\[.*\]);', res.text)
        if not match: return "-"
        json_string = match.group(1)
        data = json.loads(json_string)
        dam_discharge = data[0]['itc_water']['C13']['storage']
        return str(int(float(dam_discharge.replace(",", "")))) if dam_discharge else "-"
    except Exception:
        return "-"

# --- 2. ฟังก์ชันดึงระดับน้ำอินทร์บุรี (คงเดิม) ---
def get_inburi_bridge_data() -> float | str:
    url = "https://singburi.thaiwater.net/wl"
    try:
        session = HTMLSession()
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        }
        r = session.get(url, headers=headers, timeout=30)
        r.html.render(sleep=5, timeout=90, scrolldown=3)
        soup = BeautifulSoup(r.html.html, "html.parser")
        for row in soup.find_all("tr"):
            station_th = row.find("th")
            if not station_th:
                continue
            station_name = station_th.get_text(strip=True)
            if "อินทร์บุรี" not in station_name:
                continue
            tds = row.find_all("td")
            if len(tds) >= 3:
                water_text = tds[2].get_text(strip=True)
                match = re.search(r"[0-9]+[\.,][0-9]+", water_text)
                if match:
                    try:
                        return float(water_text.replace(",", ""))
                    except ValueError:
                        pass
            return "-"
        return "-"
    except Exception:
        return "-"

# --- 3. ฟังก์ชันดึงสภาพอากาศ (คงเดิม) ---
def get_weather_status():
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        return "ไม่มีข้อมูลสภาพอากาศ"

    # พิกัดของตำบลอินทร์บุรี
    lat, lon = "14.9308", "100.3725"
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&lang=th&units=metric"

    try:
        res = requests.get(url, timeout=30)
        data = res.json()
        if "weather" not in data or len(data["weather"]) == 0:
            return "ไม่มีข้อมูลสภาพอากาศ"

        desc_en = data["weather"][0]["main"].lower()
        desc_detail = data["weather"][0]["description"].lower()

        if "rain" in desc_en:
            return "ฝนตก"
        elif "cloud" in desc_en:
            if "overcast" in desc_detail:
                return "เมฆครึ้มมาก"
            elif "scattered" in desc_detail:
                return "เมฆกระจาย"
            else:
                return "เมฆมาก"
        elif "clear" in desc_en:
            return "ท้องฟ้าแจ่มใส"
        elif "storm" in desc_en or "thunderstorm" in desc_en:
            return "พายุฝนฟ้าคะนอง"
        elif "mist" in desc_en or "fog" in desc_en:
            return "หมอกลง"
        else:
            return desc_detail.capitalize()

    except Exception:
        return "ดึงข้อมูลอากาศไม่สำเร็จ"

# --- ✨ [เพิ่มใหม่] ฟังก์ชันดึงค่าฝุ่น PM2.5 เฉพาะจุด (อินทร์บุรี) ---
def get_pm25_data():
    """
    ดึงค่า PM2.5 จากพิกัดตำบลอินทร์บุรีโดยตรง (ใช้ OpenWeather Air Pollution API)
    แม่นยำกว่าการใช้สถานีจังหวัดเพราะระบุ Lat/Lon ของตำบล
    """
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        return ("-", "ไม่มีข้อมูล")

    # พิกัด ต.อินทร์บุรี อ.อินทร์บุรี จ.สิงห์บุรี (ตรงกับฟังก์ชัน Weather)
    lat, lon = "14.9308", "100.3725"
    url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={api_key}"

    try:
        res = requests.get(url, timeout=20)
        data = res.json()
        # ดึงค่า PM2.5 (หน่วย μg/m3)
        pm25 = data['list'][0]['components']['pm2_5']
        
        # แปลงเกณฑ์ตามมาตรฐานประเทศไทย (กรมควบคุมมลพิษ)
        # 0-15 ฟ้า(ดีมาก), 15.1-25 เขียว(ดี), 25.1-37.5 เหลือง(ปานกลาง), 
        # 37.6-75 ส้ม(เริ่มมีผล), >75 แดง(มีผลกระทบ)
        if pm25 <= 15:
            quality = "อากาศดีมาก"
        elif pm25 <= 25:
            quality = "อากาศดี"
        elif pm25 <= 37.5:
            quality = "ปานกลาง"
        elif pm25 <= 75:
            quality = "เริ่มมีผลกระทบฯ"
        else:
            quality = "มีผลกระทบต่อสุขภาพ"
            
        return (f"{pm25:.1f}", quality)
    except Exception as e:
        print(f"Error fetching PM2.5: {e}")
        return ("-", "รออัปเดต")

# --- ✨ [แก้ไข] ฟังก์ชันสร้าง Caption (เปลี่ยนจากแจ้งเตือนน้ำ เป็นแจ้งฝุ่น) ---
def generate_facebook_caption(water_level, discharge, weather, pm25_val, pm25_quality) -> str:
    caption_lines = []
    hashtags = []
    
    try:
        level = float(water_level)
    except (ValueError, TypeError):
        level = 0.0

    try:
        dis_val = int(discharge)
    except (ValueError, TypeError):
        dis_val = 0

    # บรรทัด 1: ระดับน้ำ
    if level == 0.0:
         caption_lines.append("กำลังตรวจสอบระดับน้ำ")
    else:
        caption_lines.append(f"📊 ระดับน้ำ: {level:.2f} ม.")
    
    # บรรทัด 2: การระบายน้ำ
    if dis_val > 0:
        caption_lines.append(f"💧 เขื่อนระบาย: {dis_val} ลบ.ม./วิ")

    # บรรทัด 3: ฝุ่น PM2.5
    if pm25_val != "-":
        caption_lines.append(f"😷 PM2.5 อินทร์บุรี: {pm25_val} μg/m³ ({pm25_quality})")
        
        # เพิ่ม Hashtag ตามความรุนแรงของฝุ่น
        if "เริ่มมีผล" in pm25_quality or "มีผลกระทบ" in pm25_quality:
            hashtags.append("#ฝุ่นเยอะ")
            hashtags.append("#ใส่หน้ากากด้วยนะ")
        elif "ดี" in pm25_quality:
            hashtags.append("#อากาศดี")
    
    # เพิ่ม Hashtag พื้นฐาน
    hashtags.append("#อินทร์บุรี")
    hashtags.append("#ระดับน้ำเจ้าพระยา")

    return "\n".join(caption_lines) + "\n\n" + " ".join(hashtags)

# --- ✨ [แก้ไข] ฟังก์ชันสร้างรูปภาพ (เอาสถานการณ์น้ำออก ใส่ PM2.5 แทน) ---
def create_report_image(dam_discharge, water_level, weather_status, pm25_data):
    IMAGE_WIDTH = 788
    IMAGE_HEIGHT = 763
    TEXT_COLOR = "#000000"

    pm25_val, pm25_quality = pm25_data

    # พิกัดกรอบข้อความ
    box_left = 60
    box_right = IMAGE_WIDTH - 60
    box_top = 170
    center_x = (box_left + box_right) // 2
    
    # เริ่มต้นเขียนข้อความที่ตำแหน่ง Y
    Y_START = box_top + 40 
    line_spacing = 70  # เพิ่มระยะห่างบรรทัดนิดหน่อยให้อ่านง่าย

    try:
        image = Image.open("background.png").convert("RGB")
    except FileNotFoundError:
        image = Image.new("RGB", (IMAGE_WIDTH, IMAGE_HEIGHT), "#fff6db")

    draw = ImageDraw.Draw(image)

    try:
        font_main = ImageFont.truetype("Sarabun-Bold.ttf", 44) # เพิ่มขนาดฟอนต์หัวข้อ
        font_sub = ImageFont.truetype("Sarabun-Regular.ttf", 38)
        font_pm = ImageFont.truetype("Sarabun-Bold.ttf", 48) # ฟอนต์ใหญ่สำหรับค่าฝุ่น
    except:
        font_main = font_sub = font_pm = ImageFont.load_default()

    # เตรียมข้อความ
    level_text = f"ระดับน้ำ ณ อินทร์บุรี: {water_level:.2f} ม." if isinstance(water_level, float) else "ระดับน้ำ ณ อินทร์บุรี: N/A"
    discharge_text = f"ท้ายเขื่อนฯ: {dam_discharge} ลบ.ม./วินาที"
    weather_text = f"สภาพอากาศ: {weather_status}"
    
    # ข้อความฝุ่น (มาแทนที่ สถานการณ์เฝ้าระวัง)
    pm_label_text = f"ฝุ่น PM2.5 (ต.อินทร์บุรี):"
    pm_value_text = f"{pm25_val} μg/m³ ({pm25_quality})"

    # วาดข้อความลงภาพ
    y = Y_START
    
    # 1. ระดับน้ำ
    draw.text((center_x, y), level_text, font=font_main, fill=TEXT_COLOR, anchor="mm")
    y += line_spacing
    
    # 2. การระบายน้ำ
    draw.text((center_x, y), discharge_text, font=font_sub, fill=TEXT_COLOR, anchor="mm")
    y += line_spacing
    
    # 3. สภาพอากาศ
    draw.text((center_x, y), weather_text, font=font_sub, fill=TEXT_COLOR, anchor="mm")
    y += line_spacing + 10 # เว้นวรรคเยอะหน่อยก่อนเข้าเรื่องฝุ่น

    # 4. หัวข้อฝุ่น
    draw.text((center_x, y), pm_label_text, font=font_main, fill="#444444", anchor="mm")
    y += line_spacing
    
    # 5. ค่าฝุ่น (เปลี่ยนสีตามความรุนแรง)
    pm_color = "#000000" # Default ดำ
    if pm25_quality == "อากาศดีมาก": pm_color = "#0099cc" # ฟ้า
    elif pm25_quality == "อากาศดี": pm_color = "#00b050" # เขียว
    elif pm25_quality == "ปานกลาง": pm_color = "#e6b800" # เหลืองเข้ม
    elif "เริ่มมีผล" in pm25_quality: pm_color = "#ff6600" # ส้ม
    elif "มีผลกระทบ" in pm25_quality: pm_color = "#cc0000" # แดง

    draw.text((center_x, y), pm_value_text, font=font_pm, fill=pm_color, anchor="mm")

    # บันทึกภาพ
    image.save("final_report.jpg", quality=95)

    # สร้าง Caption และบันทึก
    dynamic_caption = generate_facebook_caption(water_level, dam_discharge, weather_status, pm25_val, pm25_quality)
    with open("status.txt", "w", encoding="utf-8") as f:
        f.write(dynamic_caption)
    
    print(f"Report Generated: Level={water_level}, PM2.5={pm25_val}")

if __name__ == "__main__":
    load_dotenv()
    dam = get_chao_phraya_dam_data()
    level = get_inburi_bridge_data()
    weather = get_weather_status()
    pm25 = get_pm25_data() # ดึงค่าฝุ่น
    create_report_image(dam, level, weather, pm25)
