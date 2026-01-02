import os
import json
import requests
import re
import random
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
from requests_html import HTMLSession
# Suppress InsecureRequestWarning
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

# --- 3. ฟังก์ชันดึงข้อมูล ---

# พิกัด ต.อินทร์บุรี (สำหรับ Weather API)
INBURI_LAT = "15.0076"
INBURI_LON = "100.3273"

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

def get_inburi_bridge_data() -> float | str:
    url = "https://singburi.thaiwater.net/wl"
    try:
        session = HTMLSession()
        headers = {"User-Agent": "Mozilla/5.0"}
        r = session.get(url, headers=headers, timeout=30)
        r.html.render(sleep=5, timeout=90, scrolldown=3)
        soup = BeautifulSoup(r.html.html, "html.parser")
        for row in soup.find_all("tr"):
            if "อินทร์บุรี" in row.get_text():
                tds = row.find_all("td")
                if len(tds) >= 3:
                    match = re.search(r"[0-9]+[\.,][0-9]+", tds[2].get_text(strip=True))
                    if match: return float(match.group(0).replace(",", ""))
        return "-"
    except Exception:
        return "-"

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

# ฟังก์ชันดึงค่าฝุ่นจาก GISTDA
def get_pm25_data():
    # 1. ลองดึงจาก GISTDA ก่อน (Priority 1)
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
            print(f"GISTDA Data Found: {target_pm25}")
            return (f"{float(target_pm25):.1f}", analyze_air_quality(target_pm25))
            
    except Exception as e:
        print(f"GISTDA Error: {e}")

    # 2. ถ้า GISTDA ล่ม ให้ใช้ OpenWeather Backup (Priority 2)
    print("Switching to OpenWeather backup...")
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key: return ("-", analyze_air_quality(None))
    
    url_ow = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={INBURI_LAT}&lon={INBURI_LON}&appid={api_key}"
    try:
        res = requests.get(url_ow, timeout=20)
        pm25 = res.json()['list'][0]['components']['pm2_5']
        return (f"{pm25:.1f}", analyze_air_quality(pm25))
    except:
        return ("-", analyze_air_quality(None))

# --- 4. สร้าง Caption ---
def generate_facebook_caption(water_level, discharge, weather, pm25_val, pm25_info) -> str:
    caption = []
    
    if pm25_info['level'] in ['unhealthy', 'hazardous']:
         caption.append(f"🚨 ด่วน! {pm25_info['desc']}")
    else:
         caption.append(f"📅 รายงานอากาศ อินทร์บุรีบ้านเรา")

    caption.append("-----------------------------")
    
    if pm25_val != "-":
        # ใน Caption ยังคงบอกว่าอ้างอิง GISTDA เพื่อความน่าเชื่อถือของข้อมูล
        caption.append(f"😷 ค่าฝุ่น PM2.5 (อ้างอิง GISTDA): {pm25_val} μg/m³")
        caption.append(f"📊 สถานะ: {pm25_info['label']}")
        caption.append(f"📉 เทียบเกณฑ์: {pm25_info['compare_text']}")
        caption.append(f"💡 คำแนะนำ: {pm25_info['advice']}")
    
    caption.append("") 
    
    try:
        lvl = f"{float(water_level):.2f}"
    except: lvl = "รอตรวจสอบ"
    
    caption.append(f"🌊 ระดับน้ำ: {lvl} ม.")
    caption.append(f"💧 เขื่อนปล่อย: {discharge} ลบ.ม./วิ")
    caption.append(f"☁️ ฟ้าฝน: {weather}")
    
    tags = ["#อินทร์บุรี", "#รายงานฝุ่น", "#PM25", "#GISTDA"]
    if pm25_info['level'] in ['unhealthy', 'hazardous']:
        tags.append("#ฝุ่นหนามากแม่")
        tags.append("#ใส่แมสก์ด่วน")
    
    return "\n".join(caption) + "\n\n" + " ".join(tags)

# --- 5. สร้างรูปภาพ (แก้ไขข้อความตามสั่ง) ---
def create_report_image(dam_discharge, water_level, weather_status, pm25_data_tuple):
    IMAGE_WIDTH = 788
    IMAGE_HEIGHT = 763
    
    pm25_val, pm25_info = pm25_data_tuple

    try:
        image = Image.open("background.png").convert("RGB")
    except:
        image = Image.new("RGB", (IMAGE_WIDTH, IMAGE_HEIGHT), "#fff6db")
    
    draw = ImageDraw.Draw(image)
    
    try:
        font_main = ImageFont.truetype("Sarabun-Bold.ttf", 44)
        font_sub = ImageFont.truetype("Sarabun-Regular.ttf", 38)
        font_pm = ImageFont.truetype("Sarabun-Bold.ttf", 55)
    except:
        font_main = font_sub = font_pm = ImageFont.load_default()

    center_x = IMAGE_WIDTH // 2
    y = 210
    spacing = 65

    lvl_text = f"ระดับน้ำ: {water_level:.2f} ม." if isinstance(water_level, float) else "ระดับน้ำ: N/A"
    draw.text((center_x, y), lvl_text, font=font_main, fill="black", anchor="mm")
    y += spacing
    
    draw.text((center_x, y), f"ท้ายเขื่อนฯ: {dam_discharge} ลบ.ม./วิ", font=font_sub, fill="black", anchor="mm")
    y += spacing
    
    draw.text((center_x, y), f"ฟ้าฝน: {weather_status}", font=font_sub, fill="black", anchor="mm")
    y += spacing + 20 

    # --- [จุดที่แก้ไข] เปลี่ยนข้อความในรูปภาพ ---
    draw.text((center_x, y), "ค่าฝุ่น PM2.5 (ต.อินทร์บุรี)", font=font_main, fill="#555555", anchor="mm")
    y += spacing
    
    draw.text((center_x, y), f"{pm25_val} μg/m³", font=font_pm, fill=pm25_info['color'], anchor="mm")
    y += spacing
    
    draw.text((center_x, y), pm25_info['label'], font=font_sub, fill=pm25_info['color'], anchor="mm")

    image.save("final_report.jpg", quality=95)
    
    caption = generate_facebook_caption(water_level, dam_discharge, weather_status, pm25_val, pm25_info)
    with open("status.txt", "w", encoding="utf-8") as f:
        f.write(caption)

    print(f"Done! GISTDA PM2.5: {pm25_val} ({pm25_info['label']})")

if __name__ == "__main__":
    load_dotenv()
    dam = get_chao_phraya_dam_data()
    level = get_inburi_bridge_data()
    weather = get_weather_status()
    pm25 = get_pm25_data()
    create_report_image(dam, level, weather, pm25)
