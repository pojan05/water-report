import os
import json
import requests
import re
import random
import math
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

# ปิดการแจ้งเตือน SSL สำหรับเว็บราชการ
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# --- 0. ตั้งค่าพิกัด (ต.อินทร์บุรี) ---
INBURI_LAT = 15.0076
INBURI_LON = 100.3273

# ตั้งค่าการกรองข้อมูล
MAX_DATA_AGE_SECONDS = 7200  # ข้อมูลต้องไม่เก่าเกิน 2 ชั่วโมง (เผื่อ Air4Thai ดีเลย์)
MAX_DISTANCE_KM = 100        # ระยะทางค้นหาสูงสุด 100 กม.

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

# --- 2. ฟังก์ชันช่วยต่างๆ ---

def get_dist(lat1, lon1, lat2, lon2):
    """คำนวณระยะทาง (km) ด้วยสูตร Haversine"""
    R = 6371
    dlat = math.radians(float(lat2) - float(lat1))
    dlon = math.radians(float(lon2) - float(lon1))
    a = math.sin(dlat/2)**2 + math.cos(math.radians(float(lat1))) * math.cos(math.radians(float(lat2))) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return R * c

def clean_text_for_image(text):
    """ลบ Emoji ออกจากข้อความเพื่อป้องกันสี่เหลี่ยม [] ในรูปภาพ"""
    emojis = ["🌧️", "☁️", "☀️", "💙", "🌬️", "✨", "💚", "✅", "😊", 
              "💛", "🚧", "🌫️", "🧡", "😷", "🌪️", "❤️", "☠️", "🆘", 
              "📅", "🚨", "📊", "📉", "💡", "👉", "🏆"]
    cleaned = text
    for icon in emojis:
        cleaned = cleaned.replace(icon, "")
    return cleaned.strip()

def analyze_air_quality(pm25_value):
    try:
        val = float(pm25_value)
    except:
        return {"level": "Unsure", "label": "ไม่มีข้อมูล", "desc": "-", "advice": "-", "compare_text": "", "color": "#808080"}

    STANDARD_VAL = 37.5 
    if val <= 15: key, color = "very_good", "#0099FF"
    elif val <= 25: key, color = "good", "#00C853"
    elif val <= 37.5: key, color = "moderate", "#FFAB00"
    elif val <= 75: key, color = "unhealthy", "#FF6D00"
    else: key, color = "hazardous", "#D50000"

    if val > STANDARD_VAL:
        times = val / STANDARD_VAL
        if times >= 2: compare = f"🚨 เกินเกณฑ์มาตรฐาน {times:.1f} เท่า! (อันตรายมาก)"
        else: compare = f"⚠️ เกินเกณฑ์มาตรฐานมา {val - STANDARD_VAL:.1f} หน่วย"
    else:
        percent = (val / STANDARD_VAL) * 100
        compare = f"✅ อยู่ในเกณฑ์ปลอดภัย ({int(percent)}% ของขีดจำกัด)"

    msg = random.choice(PM25_MESSAGES[key])
    return {
        "level": key, "label": msg['label'], "desc": msg['desc'], 
        "advice": msg['advice'], "compare_text": compare, "color": color
    }

# --- 3. ฟังก์ชันดึงข้อมูล (Logic หลัก) ---

def get_weather_status():
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key: return "ไม่มีข้อมูล"
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={INBURI_LAT}&lon={INBURI_LON}&appid={api_key}&lang=th&units=metric"
        res = requests.get(url, timeout=30)
        data = res.json()
        if "weather" in data:
            desc = data["weather"][0]["main"].lower()
            if "rain" in desc: return "ฝนตก 🌧️"
            if "cloud" in desc: return "เมฆเยอะ ☁️"
            if "clear" in desc: return "ฟ้าโปร่ง ☀️"
            return data["weather"][0]["description"]
        return "ปกติ"
    except: return "ดึงข้อมูลไม่ได้"

def get_pm25_data():
    print("🔄 กำลังดึงข้อมูลฝุ่น (Multi-Source Validation)...")
    
    all_sources = [] 
    
    # ----------------------------------------------------
    # Priority 1: Air4Thai (ราชการ - น่าเชื่อถือสุด)
    # ----------------------------------------------------
    try:
        res = requests.get("http://air4thai.pcd.go.th/services/getNewAQI_JSON.php", timeout=15, verify=False)
        stations = res.json().get('stations', [])
        
        for st in stations:
            try:
                if 'PM25' not in st['LastUpdate'] or st['LastUpdate']['PM25']['value'] == "-": continue
                
                # Check Distance
                dist = get_dist(INBURI_LAT, INBURI_LON, st['lat'], st['long'])
                if dist > MAX_DISTANCE_KM: continue
                
                # Check Age (Fix Timezone Issue)
                update_str = st['LastUpdate']['date']
                last_update = datetime.strptime(update_str, "%Y-%m-%d %H:%M:%S")
                # แปลงเวลาปัจจุบัน (UTC) ให้เป็นเวลาไทย (UTC+7) เพื่อเทียบกับ Air4Thai
                now_thai = datetime.utcnow() + timedelta(hours=7)
                age_seconds = (now_thai - last_update).total_seconds()
                
                if age_seconds < 0: age_seconds = 0 # กันพลาดกรณีนาฬิกาไม่ตรง
                if age_seconds > MAX_DATA_AGE_SECONDS: 
                    # print(f"⚠️ Air4Thai Old: {st['nameTH']} ({int(age_seconds/60)} min)")
                    continue

                all_sources.append({
                    'source': 'Air4Thai',
                    'station': st['nameTH'],
                    'pm25': float(st['LastUpdate']['PM25']['value']),
                    'distance': dist,
                    'age_seconds': age_seconds,
                    'priority': 1
                })
            except: continue
    except Exception as e:
        print(f"❌ Air4Thai Error: {e}")

    # ----------------------------------------------------
    # Priority 2: DustBoy (เซนเซอร์ท้องถิ่น)
    # ----------------------------------------------------
    try:
        url_dustboy = f"https://www.cmuccdc.org/api2/dustboy/near/{INBURI_LAT}/{INBURI_LON}"
        res = requests.get(url_dustboy, timeout=10, verify=False)
        data = res.json()
        
        if data and isinstance(data, list):
            for st in data[:5]: # เช็ค 5 สถานีใกล้สุด
                try:
                    pm25 = st.get('pm25')
                    if pm25 is None: continue
                    
                    dist = get_dist(INBURI_LAT, INBURI_LON, st.get('dustboy_lat'), st.get('dustboy_lon'))
                    if dist > MAX_DISTANCE_KM: continue

                    # Check Age (Timestamp is UTC based)
                    epoch = int(st.get('dustboy_epoch', 0))
                    age_seconds = datetime.now().timestamp() - epoch
                    
                    if age_seconds > MAX_DATA_AGE_SECONDS: continue
                    
                    all_sources.append({
                        'source': 'DustBoy',
                        'station': st.get('dustboy_name', 'Unknown'),
                        'pm25': float(pm25),
                        'distance': dist,
                        'age_seconds': age_seconds,
                        'priority': 2
                    })
                except: continue
    except Exception as e:
        print(f"❌ DustBoy Error: {e}")

    # ----------------------------------------------------
    # Priority 3: OpenWeather (Backup)
    # ----------------------------------------------------
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if api_key:
        try:
            url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={INBURI_LAT}&lon={INBURI_LON}&appid={api_key}"
            res = requests.get(url, timeout=20)
            pm25 = res.json()['list'][0]['components']['pm2_5']
            all_sources.append({
                'source': 'OpenWeather',
                'station': 'Satellite',
                'pm25': float(pm25),
                'distance': 0,
                'age_seconds': 0,
                'priority': 3
            })
        except Exception as e:
            print(f"❌ OpenWeather Error: {e}")

    # ----------------------------------------------------
    # Decision Making
    # ----------------------------------------------------
    if not all_sources:
        return ("-", analyze_air_quality(None))
    
    # Sort by: Priority (น้อยไปมาก) -> Distance (ใกล้ไปไกล) -> Age (ใหม่ไปเก่า)
    all_sources.sort(key=lambda x: (x['priority'], x['distance'], x['age_seconds']))
    
    best = all_sources[0]
    print(f"🏆 Selected: {best['source']} [{best['station']}] PM2.5={best['pm25']}")
    
    # ส่งกลับทั้งค่า PM2.5, ข้อมูลวิเคราะห์, และชื่อสถานี (เผื่อใช้)
    return (f"{best['pm25']:.1f}", analyze_air_quality(best['pm25']), best['station'])

# --- 4. สร้าง Caption ---

def generate_facebook_caption(weather, pm25_val, pm25_info, station_name) -> str:
    caption = []
    if pm25_info['level'] in ['unhealthy', 'hazardous']:
         caption.append(f"🚨 เตือนภัยฝุ่น! {pm25_info['desc']}")
    else:
         caption.append(f"📅 รายงานค่าฝุ่น PM2.5 อินทร์บุรี")

    caption.append("-----------------------------")
    if pm25_val != "-":
        caption.append(f"😷 ค่าฝุ่น PM2.5: {pm25_val} μg/m³")
        caption.append(f"📍 จุดวัด: {station_name}")
        caption.append(f"📊 สถานะ: {pm25_info['label']}")
        caption.append(f"📉 {pm25_info['compare_text']}")
        caption.append(f"💡 {pm25_info['advice']}")
    
    caption.append("") 
    caption.append(f"☁️ สภาพอากาศ: {weather}")
    
    tags = ["#อินทร์บุรี", "#รายงานฝุ่น", "#PM25"]
    if pm25_info['level'] in ['unhealthy', 'hazardous']: tags.extend(["#ฝุ่นหนา", "#ดูแลสุขภาพ"])
    return "\n".join(caption) + "\n\n" + " ".join(tags)

# --- 5. สร้างรูปภาพ ---

def create_report_image(weather_status, pm25_data_result):
    IMAGE_WIDTH, IMAGE_HEIGHT = 788, 763
    
    # Unpack ค่าที่ได้ (ตอนนี้มี 3 ค่า)
    if len(pm25_data_result) == 3:
        pm25_val, pm25_info, station_name = pm25_data_result
    else:
        pm25_val, pm25_info = pm25_data_result
        station_name = "Unknown"

    try: image = Image.open("background.png").convert("RGB")
    except: image = Image.new("RGB", (IMAGE_WIDTH, IMAGE_HEIGHT), "#fff6db")
    
    draw = ImageDraw.Draw(image)
    try:
        font_main = ImageFont.truetype("Sarabun-Bold.ttf", 48)
        font_sub = ImageFont.truetype("Sarabun-Regular.ttf", 40)
        font_pm = ImageFont.truetype("Sarabun-Bold.ttf", 70)
        font_label = ImageFont.truetype("Sarabun-Bold.ttf", 55)
        font_small = ImageFont.truetype("Sarabun-Regular.ttf", 30)
    except:
        font_main = font_sub = font_pm = font_label = font_small = ImageFont.load_default()

    cx, y, sp = IMAGE_WIDTH // 2, 280, 80

    # 1. Weather (Clean)
    draw.text((cx, y), f"สภาพอากาศ: {clean_text_for_image(weather_status)}", font=font_sub, fill="#333333", anchor="mm")
    y += sp + 10

    # 2. Title
    draw.text((cx, y), "ค่าฝุ่น PM2.5 (ต.อินทร์บุรี)", font=font_main, fill="#444444", anchor="mm")
    y += sp + 10
    
    # 3. Value
    draw.text((cx, y), f"{pm25_val} μg/m³", font=font_pm, fill=pm25_info['color'], anchor="mm")
    y += 50
    
    # เพิ่มชื่อสถานีเล็กๆ ใต้ตัวเลข (Clean text ด้วย)
    clean_station = clean_text_for_image(station_name)
    draw.text((cx, y), f"(จาก: {clean_station})", font=font_small, fill="#666666", anchor="mm")
    y += sp - 20 # ขยับ space คืนนิดหน่อย
    
    # 4. Status (Clean)
    draw.text((cx, y), clean_text_for_image(pm25_info['label']), font=font_label, fill=pm25_info['color'], anchor="mm")

    image.save("final_report.jpg", quality=95)
    
    # Caption (ใช้ Emoji ได้)
    caption = generate_facebook_caption(weather_status, pm25_val, pm25_info, station_name)
    with open("status.txt", "w", encoding="utf-8") as f: f.write(caption)

    print(f"Done! PM2.5: {pm25_val} from {station_name}")

if __name__ == "__main__":
    load_dotenv()
    create_report_image(get_weather_status(), get_pm25_data())
