import os
import json
import requests
import re
import random
import math
import time
from datetime import datetime, timedelta, timezone
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

# ปิด Warning SSL
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# ==========================================
# ⚙️ ส่วนตั้งค่า (Configuration)
# ==========================================
INBURI_LAT = 15.0076
INBURI_LON = 100.3273
MAX_DATA_AGE_SECONDS = 21600 # 6 ชั่วโมง (เผื่อเวลา Server เหลื่อมล้ำ)
MAX_DISTANCE_KM = 150        # รัศมีค้นหา 150 กม.

# ==========================================
# 💬 คลังคำพูด (Messages)
# ==========================================
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

# ==========================================
# 🛠️ ฟังก์ชันช่วยคำนวณ (Helper Functions)
# ==========================================
def get_dist(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(float(lat2) - float(lat1))
    dlon = math.radians(float(lon2) - float(lon1))
    a = math.sin(dlat/2)**2 + math.cos(math.radians(float(lat1))) * math.cos(math.radians(float(lat2))) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return R * c

def clean_text_for_image(text):
    emojis = ["🌧️", "☁️", "☀️", "💙", "🌬️", "✨", "💚", "✅", "😊", 
              "💛", "🚧", "🌫️", "🧡", "😷", "🌪️", "❤️", "☠️", "🆘", 
              "📅", "🚨", "📊", "📉", "💡", "👉", "🏆", "📍"]
    cleaned = text
    for icon in emojis:
        cleaned = cleaned.replace(icon, "")
    return cleaned.strip()

def analyze_air_quality(pm25_value):
    try: val = float(pm25_value)
    except: return {"level": "Unsure", "label": "รออัปเดต", "desc": "-", "advice": "-", "compare_text": "", "color": "#808080"}

    STANDARD_VAL = 37.5 
    if val <= 15: key, color = "very_good", "#0099FF"
    elif val <= 25: key, color = "good", "#00C853"
    elif val <= 37.5: key, color = "moderate", "#FFAB00"
    elif val <= 75: key, color = "unhealthy", "#FF6D00"
    else: key, color = "hazardous", "#D50000"

    if val > STANDARD_VAL:
        times = val / STANDARD_VAL
        if times >= 2: compare = f"🚨 เกินเกณฑ์มาตรฐาน {times:.1f} เท่า!"
        else: compare = f"⚠️ เกินเกณฑ์มา {val - STANDARD_VAL:.1f} หน่วย"
    else:
        percent = (val / STANDARD_VAL) * 100
        compare = f"✅ ปลอดภัย ({int(percent)}% ของเกณฑ์)"

    msg = random.choice(PM25_MESSAGES[key])
    return {
        "level": key, "label": msg['label'], "desc": msg['desc'], 
        "advice": msg['advice'], "compare_text": compare, "color": color
    }

# ==========================================
# 📡 ส่วนดึงข้อมูล (Data Fetching)
# ==========================================
def get_weather_status():
    try:
        # ใช้ OpenMeteo (ฟรี ไม่ต้องใช้ Key)
        url = f"https://api.open-meteo.com/v1/forecast?latitude={INBURI_LAT}&longitude={INBURI_LON}&current=weather_code&timezone=Asia%2FBangkok"
        res = requests.get(url, timeout=30)
        data = res.json()
        if "current" in data:
            code = data["current"]["weather_code"]
            if code == 0: return "ฟ้าโปร่ง ☀️"
            if 1 <= code <= 3: return "เมฆบางส่วน ☁️"
            if 45 <= code <= 48: return "หมอกลง 🌫️"
            if 51 <= code <= 67: return "ฝนตก 🌧️"
            if code >= 80: return "ฝนฟ้าคะนอง ⛈️"
            return "ปกติ"
        return "ปกติ"
    except: return "-"

def get_pm25_data():
    print("🔄 กำลังดึงข้อมูลฝุ่น (Checking Real-time)...")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    all_sources = [] 
    
    # ------------------------------------------------------------------
    # 1. GISTDA (Priority 0) - แหล่งข้อมูลหลัก
    # ------------------------------------------------------------------
    try:
        print("   > ตรวจสอบ GISTDA...")
        current_ts = int(time.time())
        # เพิ่ม t=timestamp เพื่อป้องกัน Cache
        url_gistda = f"https://pm25.gistda.or.th/rest/getPM25byLocation?lat={INBURI_LAT}&lng={INBURI_LON}&t={current_ts}"
        
        res = requests.get(url_gistda, headers=headers, timeout=15, verify=False)
        
        if res.status_code == 200:
            raw_data = res.json()
            # *** FIX NESTED JSON: ถ้ามี data ซ้อน data ให้เจาะเข้าไป ***
            data = raw_data.get('data', raw_data)

            if 'pm25' in data and data['pm25'] is not None:
                 val = float(data['pm25'])
                 
                 # *** FIX TIMEZONE: ใช้เวลาไทย (GMT+7) เสมอ ***
                 data_age = 0
                 tz_bkk = timezone(timedelta(hours=7))
                 now_bkk = datetime.now(tz_bkk)

                 if 'datetimeEng' in data and 'timeEng' in data['datetimeEng']:
                     try:
                         # GISTDA ส่งมาแค่ "HH:MM" ต้องเอามาผสมกับวันที่ปัจจุบัน
                         time_str = data['datetimeEng']['timeEng']
                         
                         data_time = datetime.strptime(time_str, "%H:%M").replace(
                             year=now_bkk.year, month=now_bkk.month, day=now_bkk.day, 
                             tzinfo=tz_bkk
                         )
                         
                         # ถ้าเวลาข้อมูล ล้ำหน้าเวลาปัจจุบัน (เช่น ตอนนี้ 10:00 แต่ข้อมูลมา 11:00) 
                         # แสดงว่าเป็นข้อมูลของเมื่อวาน (ข้ามวัน)
                         if data_time > now_bkk:
                             data_time = data_time - timedelta(days=1)
                             
                         data_age = (now_bkk - data_time).total_seconds()
                         print(f"     🕒 GISTDA Time: {time_str} (Age: {int(data_age/60)} min)")
                     except Exception as e:
                         print(f"     ⚠️ Parse Time Error: {e} (ใช้ค่าฝุ่นเลย)")

                 # ถ้าข้อมูลไม่เก่าเกิน 6 ชม. ให้เอาเลย
                 if data_age <= MAX_DATA_AGE_SECONDS:
                     all_sources.append({'source': 'GISTDA (CheckFun)', 'station': 'Inburi (GISTDA)', 'pm25': val, 'distance': 0, 'age': data_age, 'priority': 0})
                     print(f"     ✅ GISTDA ใช้ได้: {val}")
                 else:
                     print(f"     ❌ ข้อมูล GISTDA เก่าเกินไป! ({int(data_age/3600)} ชม.)")

    except Exception as e: 
        print(f"     ❌ GISTDA Error: {e}")

    # ------------------------------------------------------------------
    # 2. Air4Thai (Priority 1)
    # ------------------------------------------------------------------
    try:
        res = requests.get(f"http://air4thai.pcd.go.th/services/getNewAQI_JSON.php?t={int(time.time())}", headers=headers, timeout=15, verify=False)
        if res.status_code == 200:
            for st in res.json().get('stations', []):
                if 'PM25' not in st['LastUpdate'] or st['LastUpdate']['PM25']['value'] == "-": continue
                dist = get_dist(INBURI_LAT, INBURI_LON, st['lat'], st['long'])
                if dist > MAX_DISTANCE_KM: continue
                
                # Air4Thai ส่งเวลามาเป็น Local Time
                last_update = datetime.strptime(st['LastUpdate']['date'], "%Y-%m-%d %H:%M:%S")
                # แปลงเป็น UTC เพื่อเทียบกับ utcnow หรือใช้ logic ง่ายๆ
                age = (datetime.utcnow() + timedelta(hours=7) - last_update).total_seconds()
                
                if age <= MAX_DATA_AGE_SECONDS:
                    all_sources.append({'source': 'Air4Thai', 'station': st['nameTH'], 'pm25': float(st['LastUpdate']['PM25']['value']), 'distance': dist, 'age': age, 'priority': 1})
    except Exception as e: print(f"❌ Air4Thai Error: {e}")

    # ------------------------------------------------------------------
    # 3. OpenMeteo (Backup - Priority 3)
    # ------------------------------------------------------------------
    try:
        url = f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={INBURI_LAT}&longitude={INBURI_LON}&current=pm2_5&timezone=Asia%2FBangkok"
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()
        if 'current' in data:
            pm25 = data['current']['pm2_5']
            all_sources.append({'source': 'OpenMeteo', 'station': 'Model Forecast', 'pm25': float(pm25), 'distance': 0, 'age': 0, 'priority': 3})
            # print(f"✅ OpenMeteo Found: {pm25}") # ไม่ต้องโชว์ถ้ามีตัวอื่น
    except Exception as e: print(f"❌ OpenMeteo Error: {e}")

    if not all_sources: return ("-", analyze_air_quality(None), "-")
    
    # Sort: Priority (น้อยไปหามาก) > Distance > Age
    all_sources.sort(key=lambda x: (x['priority'], x['distance'], x['age']))
    best = all_sources[0]
    print(f"🏆 Selected Source: {best['source']} = {best['pm25']}")
    return (f"{best['pm25']:.1f}", analyze_air_quality(best['pm25']), best['station'])

# ==========================================
# 🎨 ส่วนสร้างรูปภาพ (Image & Caption)
# ==========================================
def generate_facebook_caption(weather, pm25_val, pm25_info, station_name) -> str:
    caption = []
    if pm25_info['level'] in ['unhealthy', 'hazardous']:
         caption.append(f"🚨 เตือนภัยฝุ่น! {pm25_info['desc']}")
    else:
         caption.append(f"📅 รายงานค่าฝุ่น PM2.5 อินทร์บุรี")

    caption.append("-----------------------------")
    if pm25_val != "-":
        caption.append(f"😷 ค่าฝุ่น PM2.5: {pm25_val} μg/m³")
        # caption.append(f"📍 จุดวัด: {station_name}") # เปิด/ปิด ตามต้องการ
        caption.append(f"📊 สถานะ: {pm25_info['label']}")
        caption.append(f"📉 {pm25_info['compare_text']}")
        caption.append(f"💡 {pm25_info['advice']}")
    
    caption.append("") 
    caption.append(f"☁️ สภาพอากาศ: {weather}")
    
    tags = ["#อินทร์บุรี", "#รายงานฝุ่น", "#PM25", "#GISTDA"]
    if pm25_info['level'] in ['unhealthy', 'hazardous']: tags.extend(["#ฝุ่นหนา", "#ดูแลสุขภาพ"])
    return "\n".join(caption) + "\n\n" + " ".join(tags)

def create_report_image(weather_status, pm25_data_result):
    IMAGE_WIDTH, IMAGE_HEIGHT = 788, 763
    
    if len(pm25_data_result) == 3: pm25_val, pm25_info, station_name = pm25_data_result
    else: pm25_val, pm25_info, station_name = pm25_data_result[0], pm25_data_result[1], "Unknown"

    try: image = Image.open("background.png").convert("RGB")
    except: image = Image.new("RGB", (IMAGE_WIDTH, IMAGE_HEIGHT), "#fff6db")
    
    draw = ImageDraw.Draw(image)
    try:
        font_main = ImageFont.truetype("Sarabun-Bold.ttf", 48)
        font_sub = ImageFont.truetype("Sarabun-Regular.ttf", 40)
        font_pm = ImageFont.truetype("Sarabun-Bold.ttf", 70)
        font_label = ImageFont.truetype("Sarabun-Bold.ttf", 55)
    except:
        font_main = font_sub = font_pm = font_label = ImageFont.load_default()

    cx = IMAGE_WIDTH // 2
    y = 250 

    # 1. Weather
    draw.text((cx, y), f"สภาพอากาศ: {clean_text_for_image(weather_status)}", font=font_sub, fill="#333333", anchor="mm")
    y += 70

    # 2. Title
    draw.text((cx, y), "ค่าฝุ่น PM2.5 (ต.อินทร์บุรี)", font=font_main, fill="#444444", anchor="mm")
    y += 80

    # 3. Value
    draw.text((cx, y), f"{pm25_val} μg/m³", font=font_pm, fill=pm25_info['color'], anchor="mm")
    y += 100  

    # 4. Status Label
    draw.text((cx, y), clean_text_for_image(pm25_info['label']), font=font_label, fill=pm25_info['color'], anchor="mm")

    image.save("final_report.jpg", quality=95)
    
    caption = generate_facebook_caption(weather_status, pm25_val, pm25_info, station_name)
    with open("status.txt", "w", encoding="utf-8") as f: f.write(caption)

    print(f"Done! PM2.5: {pm25_val} from {station_name}")

if __name__ == "__main__":
    load_dotenv()
    create_report_image(get_weather_status(), get_pm25_data())
