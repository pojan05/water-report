import os
import json
import requests
import re
import random
from datetime import datetime
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
# ปิดแจ้งเตือน SSL (กรณีใช้ GISTDA)
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# --- 1. คลังคำพูดแจ้งเตือน (Smart Messages) ---
PM25_MESSAGES = {
    "very_good": [
        {"label": "อากาศดีมาก 💙", "desc": "ฟ้าใสปิ๊ง! สูดได้เต็มปอด", "advice": "เหมาะมากที่จะไปวิ่งออกกำลังกาย หรือตากผ้าครับ"},
        {"label": "สดชื่นสุดๆ 🌬️", "desc": "ลมพัดเย็นสบาย ไร้ฝุ่นกวนใจ", "advice": "เปิดหน้าต่างรับลมได้เลย อากาศดีแบบนี้หายากนะ"},
        {"label": "พื้นที่สีฟ้า ✨", "desc": "ไม่มีฝุ่นเลย ปอดคุณยิ้มได้", "advice": "ใครดองงานซักผ้าไว้ รีบจัดเลยครับ แดดดีลมดี!"}
    ],
    "good": [
        {"label": "อากาศดี 💚", "desc": "ยังโอเค! ใช้ชีวิตได้ตามปกติ", "advice": "เที่ยวนอกบ้านได้สบายๆ แต่อย่าลืมดื่มน้ำเยอะๆ นะ"},
        {"label": "เขียวผ่านตลอด ✅", "desc": "ฝุ่นนิดเดียว แทบไม่รู้สึก", "advice": "ทำกิจกรรมกลางแจ้งได้ครับ วันนี้อากาศเป็นมิตร"},
        {"label": "สบายๆ หายห่วง 😊", "desc": "คุณภาพอากาศอยู่ในเกณฑ์ดี", "advice": "ใช้ชีวิตให้มีความสุขครับ วันนี้ปอดไม่ต้องทำงานหนัก"}
    ],
    "moderate": [
        {"label": "เริ่มขุ่นๆ 💛", "desc": "ฟ้าเริ่มมัว (ระดับเฝ้าระวัง)", "advice": "กลุ่มเสี่ยง (เด็ก/คนแก่) ระวังหน่อยนะ #งดเผาขยะ ช่วยกันครับ"},
        {"label": "การ์ดอย่าตก 🚧", "desc": "ฝุ่นเริ่มมาเยือน จมูกไวเริ่มรู้เรื่อง", "advice": "ใครแพ้ง่าย เลี่ยงที่โล่งแจ้งนิดนึง ใส่หน้ากากกันไว้ดีกว่า"},
        {"label": "เริ่มหนาตา 🌫️", "desc": "มองไปไกลๆ เริ่มไม่ชัดแล้วนะ", "advice": "ลดการใช้รถยนต์ถ้าทำได้ และช่วยกันสอดส่องคนเผาหญ้าครับ"}
    ],
    "unhealthy": [
        {"label": "เริ่มมีผลกระทบ 🧡", "desc": "แสบจมูก แสบคอ ฝุ่นเยอะชัดเจน", "advice": "⚠️ ใส่หน้ากากอนามัยทันทีที่ออกนอกบ้าน อย่าประมาท!"},
        {"label": "เตือนภัยฝุ่น 😷", "desc": "หายใจแล้วรู้สึกไม่โล่ง คอแห้ง", "advice": "งดวิ่งกลางแจ้งเปลี่ยนไปออกกำลังกายในร่มแทนนะ"},
        {"label": "ฝุ่นบุกหนัก 🌪️", "desc": "สภาพอากาศปิด ฝุ่นสะสมตัวสูง", "advice": "ปิดหน้าต่างให้มิดชิด! ใครเป็นภูมิแพ้เตรียมยาไว้เลย"}
    ],
    "hazardous": [
        {"label": "วิกฤต! สีแดง ❤️", "desc": "อันตรายมาก! ฝุ่นหนาจนน่ากลัว", "advice": "❌ ห้ามออกกำลังกายกลางแจ้งเด็ดขาด! ต้องใส่ N95 เท่านั้น"},
        {"label": "ฉุกเฉินอากาศพิษ ☠️", "desc": "มองไม่เห็นตึก! หายใจแล้วอันตราย", "advice": "อยู่แต่ในห้องแอร์/ห้องปลอดฝุ่น ปกป้องเด็กและคนชราด่วน!"},
        {"label": "ไม่ไหวบอกไหว 🆘", "desc": "ค่าฝุ่นพุ่งทะลุเพดาน อันตรายต่อทุกคน", "advice": "งดออกจากบ้านถ้าไม่จำเป็น! นี่คือคำเตือนระดับสูงสุด"}
    ]
}

# --- 2. ฟังก์ชันวิเคราะห์คุณภาพอากาศ ---
def analyze_air_quality(pm25_value):
    try:
        val = float(pm25_value)
    except:
        return {
            "level": "Unsure",
            "label": "ไม่มีข้อมูล",
            "desc": "ระบบกำลังตรวจสอบ",
            "advice": "รอสักครู่นะครับ",
            "compare_text": "",
            "color": "#808080"
        }

    selected_key = ""
    color_code = ""
    STANDARD_VAL = 37.5 

    if val <= 15:
        selected_key = "very_good"
        color_code = "#0099FF" 
    elif val <= 25:
        selected_key = "good"
        color_code = "#00C853" 
    elif val <= 37.5:
        selected_key = "moderate"
        color_code = "#FFAB00" 
    elif val <= 75:
        selected_key = "unhealthy"
        color_code = "#FF6D00" 
    else:
        selected_key = "hazardous"
        color_code = "#D50000" 

    if val > STANDARD_VAL:
        times = val / STANDARD_VAL
        if times >= 2:
            compare_text = f"🚨 เกินมาตรฐาน {times:.1f} เท่า!"
        else:
            diff = val - STANDARD_VAL
            compare_text = f"⚠️ เกินมาตรฐาน {diff:.1f}"
    else:
        percent = (val / STANDARD_VAL) * 100
        compare_text = f"✅ ปลอดภัย ({int(percent)}%)"

    msg = random.choice(PM25_MESSAGES[selected_key])

    return {
        "level": selected_key,
        "label": msg['label'],
        "desc": msg['desc'],
        "advice": msg['advice'],
        "compare_text": compare_text,
        "color": color_code
    }

# --- 3. ฟังก์ชันดึงข้อมูล (พิกัดแม่นยำตลาดอินทร์บุรี) ---

# 📍 พิกัด: ตลาดอินทร์บุรี (ใจกลางชุมชน)
# Lat: 15.0108, Lon: 100.3314
INBURI_LAT = "15.0108"
INBURI_LON = "100.3314"

def get_weather_status():
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key: return "ไม่มีข้อมูล"
    # ดึงข้อมูลอากาศ ณ พิกัดตลาดอินทร์บุรี
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={INBURI_LAT}&lon={INBURI_LON}&appid={api_key}&lang=th&units=metric"
    try:
        res = requests.get(url, timeout=30)
        data = res.json()
        if "weather" in data and len(data["weather"]) > 0:
            desc = data["weather"][0]["main"].lower()
            temp = int(data["main"]["temp"]) # อุณหภูมิ
            
            weather_th = ""
            if "rain" in desc: weather_th = "ฝนตก 🌧️"
            elif "cloud" in desc: weather_th = "เมฆเยอะ ☁️"
            elif "clear" in desc: weather_th = "ฟ้าโปร่ง ☀️"
            elif "mist" in desc or "fog" in desc: weather_th = "หมอกลง 🌫️"
            else: weather_th = data["weather"][0]["description"]
            
            return f"{weather_th} {temp}°C"
        return "ปกติ"
    except: return "ดึงข้อมูลไม่ได้"

def get_pm25_data():
    """
    ดึงค่า PM2.5:
    Priority 1: OpenWeather (เพราะระบุพิกัดตลาดอินทร์บุรีได้แม่นยำกว่า)
    Priority 2: GISTDA (สำรอง - เป็นค่าเฉลี่ยจังหวัดสิงห์บุรี)
    """
    api_key = os.getenv("OPENWEATHER_API_KEY")
    
    # 1. ลอง OpenWeather ก่อน (แม่นยำพิกัด)
    if api_key:
        print("Fetching Local Data (OpenWeather)...")
        url_ow = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={INBURI_LAT}&lon={INBURI_LON}&appid={api_key}"
        try:
            res = requests.get(url_ow, timeout=20)
            pm25 = res.json()['list'][0]['components']['pm2_5']
            print(f"Local PM2.5 Found: {pm25}")
            return (f"{pm25:.1f}", analyze_air_quality(pm25))
        except Exception as e:
            print(f"OpenWeather Error: {e}")

    # 2. ถ้า OpenWeather พลาด ค่อยใช้ GISTDA (เฉลี่ยจังหวัด)
    print("Switching to GISTDA backup (Province Level)...")
    url_gistda = "https://pm25.gistda.or.th/rest/getPm25byProvince"
    try:
        res = requests.get(url_gistda, timeout=15, verify=False)
        data = res.json()
        target_pm25 = None
        for province in data:
            if "สิงห์บุรี" in province.get("province_name_th", "") or "Sing Buri" in province.get("province_name_en", ""):
                target_pm25 = province.get("pm25")
                break
        if target_pm25 is not None:
            return (f"{float(target_pm25):.1f}", analyze_air_quality(target_pm25))
    except Exception as e:
        print(f"GISTDA Error: {e}")

    return ("-", analyze_air_quality(None))

# --- 4. สร้าง Caption ---
def generate_facebook_caption(weather, pm25_val, pm25_info) -> str:
    caption = []
    
    # เวลาปัจจุบัน
    current_time = datetime.now().strftime("%H:%M")
    
    # พาดหัว
    if pm25_info['level'] in ['unhealthy', 'hazardous']:
         caption.append(f"🚨 เตือนภัยฝุ่น! {pm25_info['desc']}")
    else:
         caption.append(f"📅 รายงานฝุ่น ตลาดอินทร์บุรี ({current_time} น.)")

    caption.append("-----------------------------")
    
    # ข้อมูลฝุ่น
    if pm25_val != "-":
        caption.append(f"😷 PM2.5 (ตลาดอินทร์บุรี): {pm25_val} μg/m³")
        caption.append(f"📊 สถานะ: {pm25_info['label']}")
        caption.append(f"💡 คำแนะนำ: {pm25_info['advice']}")
    
    caption.append("") 
    caption.append(f"🌡️ สภาพอากาศ: {weather}")
    
    tags = ["#อินทร์บุรี", "#PM25", "#อากาศวันนี้", "#ตลาดอินทร์บุรี"]
    if pm25_info['level'] in ['unhealthy', 'hazardous']:
        tags.append("#ฝุ่นหนามาก")
        tags.append("#ใส่แมสก์")
    
    return "\n".join(caption) + "\n\n" + " ".join(tags)

# --- 5. สร้างรูปภาพ ---
def create_report_image(weather_status, pm25_data_tuple):
    IMAGE_WIDTH = 788
    IMAGE_HEIGHT = 763
    
    pm25_val, pm25_info = pm25_data_tuple
    
    # เวลาสำหรับใส่ในรูป
    time_str = datetime.now().strftime("%H:%M น.")

    try:
        image = Image.open("background.png").convert("RGB")
    except:
        image = Image.new("RGB", (IMAGE_WIDTH, IMAGE_HEIGHT), "#fff6db")
    
    draw = ImageDraw.Draw(image)
    
    try:
        font_weather = ImageFont.truetype("Sarabun-Bold.ttf", 55)
        font_main = ImageFont.truetype("Sarabun-Bold.ttf", 44)
        font_pm = ImageFont.truetype("Sarabun-Bold.ttf", 75)
        font_label = ImageFont.truetype("Sarabun-Bold.ttf", 44)
        font_small = ImageFont.truetype("Sarabun-Regular.ttf", 30)
    except:
        font_weather = font_main = font_pm = font_label = font_small = ImageFont.load_default()

    center_x = IMAGE_WIDTH // 2
    y = 260 
    spacing = 80

    # 1. สภาพอากาศ + อุณหภูมิ
    draw.text((center_x, y), f"{weather_status}", font=font_weather, fill="#2c3e50", anchor="mm")
    y += spacing + 15

    # 2. หัวข้อฝุ่น
    draw.text((center_x, y), "ค่าฝุ่น PM2.5 (ตลาดอินทร์บุรี)", font=font_main, fill="#555555", anchor="mm")
    y += spacing + 10
    
    # 3. ตัวเลขค่าฝุ่น
    draw.text((center_x, y), f"{pm25_val} μg/m³", font=font_pm, fill=pm25_info['color'], anchor="mm")
    y += spacing
    
    # 4. คำอธิบายสถานะ
    draw.text((center_x, y), pm25_info['label'], font=font_label, fill=pm25_info['color'], anchor="mm")
    
    # 5. เวลาอัปเดต (มุมขวาล่าง หรือตรงกลางล่างสุด)
    draw.text((center_x, y + 60), f"อัปเดตข้อมูล: {time_str}", font=font_small, fill="#888888", anchor="mm")

    image.save("final_report.jpg", quality=95)
    
    caption = generate_facebook_caption(weather_status, pm25_val, pm25_info)
    with open("status.txt", "w", encoding="utf-8") as f:
        f.write(caption)

    print(f"Done! Weather: {weather_status}, PM2.5: {pm25_val}")

if __name__ == "__main__":
    load_dotenv()
    
    weather = get_weather_status()
    pm25 = get_pm25_data()
    
    create_report_image(weather, pm25)
