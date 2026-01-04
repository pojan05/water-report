import os
import json
import requests
import re
import random
import math
from datetime import datetime
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

# ปิดการแจ้งเตือน SSL สำหรับเว็บราชการบางเว็บที่ใบรับรองอาจเก่า
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# --- 0. ตั้งค่าพิกัด (ต.อินทร์บุรี) ---
INBURI_LAT = 15.0076
INBURI_LON = 100.3273

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

# --- 2. ฟังก์ชันคำนวณระยะทาง (Haversine Formula) ---
def get_dist(lat1, lon1, lat2, lon2):
    """คำนวณระยะทาง (km) ระหว่างสองพิกัดโลก"""
    R = 6371  # รัศมีโลก (km)
    dlat = math.radians(float(lat2) - float(lat1))
    dlon = math.radians(float(lon2) - float(lon1))
    a = math.sin(dlat/2)**2 + math.cos(math.radians(float(lat1))) * math.cos(math.radians(float(lat2))) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return R * c

# --- 3. ฟังก์ชันวิเคราะห์คุณภาพอากาศ ---
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
            compare_text = f"🚨 เกินเกณฑ์มาตรฐาน {times:.1f} เท่า! (อันตรายมาก)"
        else:
            diff = val - STANDARD_VAL
            compare_text = f"⚠️ เกินเกณฑ์มาตรฐานมา {diff:.1f} หน่วย"
    else:
        percent = (val / STANDARD_VAL) * 100
        compare_text = f"✅ อยู่ในเกณฑ์ปลอดภัย ({int(percent)}% ของขีดจำกัด)"

    msg = random.choice(PM25_MESSAGES[selected_key])

    return {
        "level": selected_key,
        "label": msg['label'],
        "desc": msg['desc'],
        "advice": msg['advice'],
        "compare_text": compare_text,
        "color": color_code
    }

# --- 4. ฟังก์ชันดึงข้อมูล (Smart Fallback Logic) ---

def get_weather_status():
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key: return "ไม่มีข้อมูล"
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={INBURI_LAT}&lon={INBURI_LON}&appid={api_key}&lang=th&units=metric"
    try:
        res = requests.get(url, timeout=30)
        data = res.json()
        if "weather" in data and len(data["weather"]) > 0:
            desc = data["weather"][0]["main"].lower()
            if "rain" in desc: return "ฝนตก 🌧️"
            if "cloud" in desc: return "เมฆเยอะ ☁️"
            if "clear" in desc: return "ฟ้าโปร่ง ☀️"
            return data["weather"][0]["description"]
        return "ปกติ"
    except: return "ดึงข้อมูลไม่ได้"

def get_pm25_data():
    print("🔄 กำลังดึงข้อมูลฝุ่น (Logic: Smart Fallback)...")

    # --- Priority 1: DustBoy (แม่นยำสุด แต่ต้องสดใหม่) ---
    url_dustboy = f"https://www.cmuccdc.org/api2/dustboy/near/{INBURI_LAT}/{INBURI_LON}"
    try:
        res = requests.get(url_dustboy, timeout=10, verify=False)
        data = res.json()
        
        if data and len(data) > 0:
            station = data[0]
            pm25 = station.get('pm25')
            epoch = station.get('dustboy_epoch', 0)
            station_name = station.get('dustboy_name', 'Unknown')
            
            # เช็คความสด: ต้องไม่เก่าเกิน 2 ชม. (7200 วินาที)
            if pm25 is not None and (datetime.now().timestamp() - int(epoch)) < 7200:
                print(f"✅ DustBoy Found: {pm25} (Station: {station_name})")
                return (f"{float(pm25):.1f}", analyze_air_quality(pm25))
            else:
                print(f"⚠️ DustBoy ข้อมูลเก่าเกินไป หรือไม่มีค่า (Last Update: {int(datetime.now().timestamp() - int(epoch))}s ago)")
                
    except Exception as e:
        print(f"❌ DustBoy Error: {e}")

    # --- Priority 2: Air4Thai (มาตรฐานราชการ เช็คระยะทาง) ---
    try:
        res = requests.get("http://air4thai.pcd.go.th/services/getNewAQI_JSON.php", timeout=10, verify=False)
        stations = res.json()['stations']
        
        nearest = None
        min_dist = 100  # จำกัดระยะค้นหาแค่ 100 km เกินนี้ไม่เอา
        
        for st in stations:
            # ข้ามสถานีที่ค่าเป็น "-" หรือไม่มีค่า
            if 'PM25' not in st['LastUpdate'] or st['LastUpdate']['PM25']['value'] == "-": 
                continue
            
            dist = get_dist(INBURI_LAT, INBURI_LON, st['lat'], st['long'])
            if dist < min_dist:
                min_dist = dist
                nearest = st
        
        if nearest:
            pm25 = float(nearest['LastUpdate']['PM25']['value'])
            name = nearest['nameTH']
            print(f"✅ Air4Thai Found: {pm25} (Station: {name}, Dist: {min_dist:.1f}km)")
            return (f"{pm25:.1f}", analyze_air_quality(pm25))
        else:
            print("⚠️ Air4Thai: ไม่พบสถานีที่มีข้อมูลในรัศมี 100km")

    except Exception as e:
        print(f"❌ Air4Thai Error: {e}")

    # --- Priority 3: OpenWeather (Fallback: กันตายด้วยข้อมูลดาวเทียม) ---
    print("⚠️ Sensors offline/too far. Switching to OpenWeather backup...")
    api_key = os.getenv("OPENWEATHER_API_KEY")
    
    if not api_key: 
        return ("-", analyze_air_quality(None))
    
    url_ow = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={INBURI_LAT}&lon={INBURI_LON}&appid={api_key}"
    try:
        res = requests.get(url_ow, timeout=20)
        pm25 = res.json()['list'][0]['components']['pm2_5']
        print(f"✅ OpenWeather Found: {pm25}")
        return (f"{pm25:.1f}", analyze_air_quality(pm25))
    except Exception as e:
        print(f"❌ OpenWeather Error: {e}")
        return ("-", analyze_air_quality(None))

# --- 5. สร้าง Caption ---
def generate_facebook_caption(weather, pm25_val, pm25_info) -> str:
    caption = []
    
    # พาดหัว
    if pm25_info['level'] in ['unhealthy', 'hazardous']:
         caption.append(f"🚨 เตือนภัยฝุ่น! {pm25_info['desc']}")
    else:
         caption.append(f"📅 รายงานค่าฝุ่น PM2.5 อินทร์บุรี")

    caption.append("-----------------------------")
    
    # ข้อมูลฝุ่น (พระเอก)
    if pm25_val != "-":
        caption.append(f"😷 ค่าฝุ่น PM2.5 (ต.อินทร์บุรี): {pm25_val} μg/m³")
        caption.append(f"📊 สถานะ: {pm25_info['label']}")
        caption.append(f"📉 เทียบเกณฑ์: {pm25_info['compare_text']}")
        caption.append(f"💡 คำแนะนำ: {pm25_info['advice']}")
    
    caption.append("") 
    caption.append(f"☁️ สภาพอากาศ: {weather}")
    
    # Hashtags
    tags = ["#อินทร์บุรี", "#รายงานฝุ่น", "#PM25", "#อากาศอินทร์บุรี"]
    if pm25_info['level'] in ['unhealthy', 'hazardous']:
        tags.append("#ฝุ่นหนามากแม่")
        tags.append("#ใส่แมสก์ด่วน")
    
    return "\n".join(caption) + "\n\n" + " ".join(tags)

# --- 6. สร้างรูปภาพ ---
def create_report_image(weather_status, pm25_data_tuple):
    IMAGE_WIDTH = 788
    IMAGE_HEIGHT = 763
    
    pm25_val, pm25_info = pm25_data_tuple

    try:
        image = Image.open("background.png").convert("RGB")
    except:
        image = Image.new("RGB", (IMAGE_WIDTH, IMAGE_HEIGHT), "#fff6db")
    
    draw = ImageDraw.Draw(image)
    
    try:
        # พยายามโหลดฟอนต์ภาษาไทย
        font_main = ImageFont.truetype("Sarabun-Bold.ttf", 48)
        font_sub = ImageFont.truetype("Sarabun-Regular.ttf", 40)
        font_pm = ImageFont.truetype("Sarabun-Bold.ttf", 70)
        font_label = ImageFont.truetype("Sarabun-Bold.ttf", 44)
    except:
        # ถ้าไม่มีฟอนต์ ให้ใช้ default (อาจอ่านไทยไม่ออก)
        font_main = font_sub = font_pm = font_label = ImageFont.load_default()

    center_x = IMAGE_WIDTH // 2
    
    # จัดตำแหน่งข้อความ
    y = 280 
    spacing = 80

    # 1. สภาพอากาศ (อยู่บนสุด)
    draw.text((center_x, y), f"สภาพอากาศ: {weather_status}", font=font_sub, fill="#333333", anchor="mm")
    y += spacing + 10

    # 2. หัวข้อฝุ่น
    draw.text((center_x, y), "ค่าฝุ่น PM2.5 (ต.อินทร์บุรี)", font=font_main, fill="#444444", anchor="mm")
    y += spacing + 10
    
    # 3. ตัวเลขค่าฝุ่น (ใหญ่สุด)
    draw.text((center_x, y), f"{pm25_val} μg/m³", font=font_pm, fill=pm25_info['color'], anchor="mm")
    y += spacing
    
    # 4. คำอธิบายสถานะ
    draw.text((center_x, y), pm25_info['label'], font=font_label, fill=pm25_info['color'], anchor="mm")

    image.save("final_report.jpg", quality=95)
    
    # สร้าง Caption และบันทึก
    caption = generate_facebook_caption(weather_status, pm25_val, pm25_info)
    with open("status.txt", "w", encoding="utf-8") as f:
        f.write(caption)

    print(f"Done! Result PM2.5: {pm25_val} ({pm25_info['label']})")

if __name__ == "__main__":
    load_dotenv()
    
    weather = get_weather_status()
    pm25 = get_pm25_data()
    
    create_report_image(weather, pm25)
