import os
import json
import requests
import re
import random
import math
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

# ปิด Warning SSL
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# --- 0. ตั้งค่าพิกัด (ต.อินทร์บุรี) ---
INBURI_LAT = 15.0076
INBURI_LON = 100.3273

# ตั้งค่าการกรองข้อมูล
MAX_DATA_AGE_SECONDS = 14400 # 4 ชั่วโมง
MAX_DISTANCE_KM = 150        # 150 กม.

# --- 1. คลังคำพูดแจ้งเตือน ---
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

# --- 3. ดึงข้อมูล (Air4Thai -> DustBoy -> OpenMeteo) ---
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
    except: return "-"

def get_pm25_data():
    print("🔄 กำลังดึงข้อมูลฝุ่น...")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    all_sources = [] 
    
    # 1. Air4Thai
    try:
        res = requests.get("http://air4thai.pcd.go.th/services/getNewAQI_JSON.php", headers=headers, timeout=15, verify=False)
        if res.status_code == 200:
            for st in res.json().get('stations', []):
                if 'PM25' not in st['LastUpdate'] or st['LastUpdate']['PM25']['value'] == "-": continue
                dist = get_dist(INBURI_LAT, INBURI_LON, st['lat'], st['long'])
                if dist > MAX_DISTANCE_KM: continue
                
                last_update = datetime.strptime(st['LastUpdate']['date'], "%Y-%m-%d %H:%M:%S")
                age = (datetime.utcnow() + timedelta(hours=7) - last_update).total_seconds()
                if age > MAX_DATA_AGE_SECONDS: continue

                all_sources.append({'source': 'Air4Thai', 'station': st['nameTH'], 'pm25': float(st['LastUpdate']['PM25']['value']), 'distance': dist, 'age': age, 'priority': 1})
    except Exception as e: print(f"❌ Air4Thai Error: {e}")

    # 2. DustBoy
    try:
        url = f"https://www.cmuccdc.org/api2/dustboy/near/{INBURI_LAT}/{INBURI_LON}"
        res = requests.get(url, headers=headers, timeout=10, verify=False)
        data = res.json()
        if data and isinstance(data, list):
            for st in data[:5]:
                if not st.get('pm25') or not st.get('dustboy_lat'): continue
                dist = get_dist(INBURI_LAT, INBURI_LON, st.get('dustboy_lat'), st.get('dustboy_lon'))
                if dist > MAX_DISTANCE_KM: continue
                age = datetime.now().timestamp() - int(st.get('dustboy_epoch', 0))
                if age > MAX_DATA_AGE_SECONDS: continue
                all_sources.append({'source': 'DustBoy', 'station': st.get('dustboy_name'), 'pm25': float(st.get('pm25')), 'distance': dist, 'age': age, 'priority': 2})
    except Exception as e: print(f"❌ DustBoy Error: {e}")

    # 3. OpenMeteo
    try:
        url = f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={INBURI_LAT}&longitude={INBURI_LON}&current=pm2_5&timezone=Asia%2FBangkok"
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()
        if 'current' in data:
            pm25 = data['current']['pm2_5']
            all_sources.append({'source': 'OpenMeteo', 'station': 'Model Forecast', 'pm25': float(pm25), 'distance': 0, 'age': 0, 'priority': 3})
            print(f"✅ OpenMeteo Found: {pm25}")
    except Exception as e: print(f"❌ OpenMeteo Error: {e}")

    if not all_sources: return ("-", analyze_air_quality(None), "-")
    
    all_sources.sort(key=lambda x: (x['priority'], x['distance'], x['age']))
    best = all_sources[0]
    print(f"🏆 Selected: {best['source']} = {best['pm25']}")
    return (f"{best['pm25']:.1f}", analyze_air_quality(best['pm25']), best['station'])

# --- 4. สร้าง Caption (ลบชื่อสถานีออก) ---
def generate_facebook_caption(weather, pm25_val, pm25_info, station_name) -> str:
    caption = []
    if pm25_info['level'] in ['unhealthy', 'hazardous']:
         caption.append(f"🚨 เตือนภัยฝุ่น! {pm25_info['desc']}")
    else:
         caption.append(f"📅 รายงานค่าฝุ่น PM2.5 อินทร์บุรี")

    caption.append("-----------------------------")
    if pm25_val != "-":
        caption.append(f"😷 ค่าฝุ่น PM2.5: {pm25_val} μg/m³")
        # ลบส่วนแสดง '📍 จุดวัด: ...' ออกตามคำขอ
        caption.append(f"📊 สถานะ: {pm25_info['label']}")
        caption.append(f"📉 {pm25_info['compare_text']}")
        caption.append(f"💡 {pm25_info['advice']}")
    
    caption.append("") 
    caption.append(f"☁️ สภาพอากาศ: {weather}")
    
    tags = ["#อินทร์บุรี", "#รายงานฝุ่น", "#PM25"]
    if pm25_info['level'] in ['unhealthy', 'hazardous']: tags.extend(["#ฝุ่นหนา", "#ดูแลสุขภาพ"])
    return "\n".join(caption) + "\n\n" + " ".join(tags)

# --- 5. สร้างรูปภาพ (Clean Layout) ---
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
    
    # --- ปรับ Layout ใหม่ให้ชิดกันพอดี ---
    y = 280

    # 1. Weather
    draw.text((cx, y), f"สภาพอากาศ: {clean_text_for_image(weather_status)}", font=font_sub, fill="#333333", anchor="mm")
    y += 70

    # 2. Title
    draw.text((cx, y), "ค่าฝุ่น PM2.5 (ต.อินทร์บุรี)", font=font_main, fill="#444444", anchor="mm")
    y += 75

    # 3. Value (ตัวเลขฝุ่น)
    draw.text((cx, y), f"{pm25_val} μg/m³", font=font_pm, fill=pm25_info['color'], anchor="mm")
    y += 70

    # 4. Status Label (ไม่มีบรรทัด 'จาก: ...' แล้ว)
    draw.text((cx, y), clean_text_for_image(pm25_info['label']), font=font_label, fill=pm25_info['color'], anchor="mm")

    image.save("final_report.jpg", quality=95)
    
    caption = generate_facebook_caption(weather_status, pm25_val, pm25_info, station_name)
    with open("status.txt", "w", encoding="utf-8") as f: f.write(caption)

    print(f"Done! PM2.5: {pm25_val} from {station_name}")

if __name__ == "__main__":
    load_dotenv()
    create_report_image(get_weather_status(), get_pm25_data())
