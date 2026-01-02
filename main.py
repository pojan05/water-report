import os
import json
import requests
import re
import random
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
from requests_html import HTMLSession

# --- 1. คลังคำพูดแบบชาวบ้าน (Casual & Smart) ---
PM25_MESSAGES = {
    "very_good": [ # 0 - 15 (ฟ้า)
        {"label": "อากาศดีเหมือนอยู่บนดอย ⛰️", "desc": "สูดได้เต็มปอด โล่งจมูกสุดๆ", "advice": "ออกมาวิ่งเถอะ อากาศแบบนี้หายาก!"},
        {"label": "ฟ้าใสปิ๊ง ✨", "desc": "ไม่มีฝุ่นกวนใจเลยสักนิด", "advice": "เปิดหน้าต่างระบายอากาศในบ้านด่วนๆ"},
        {"label": "ดีต่อใจ ดีต่อปอด 💙", "desc": "ลมดี อากาศสะอาดเว่อร์", "advice": "ใครดองผ้าไว้ รีบซักรีบตาก แดดกำลังดี"}
    ],
    "good": [ # 15.1 - 25 (เขียว)
        {"label": "อากาศยังดีอยู่ 💚", "desc": "ใช้ชีวิตได้ปกติ ไม่ต้องกังวล", "advice": "ไปตลาด ไปนา ไปสวน ได้สบายๆ ครับ"},
        {"label": "เขียวผ่านตลอด ✅", "desc": "ฝุ่นมีนิดเดียว แทบไม่รู้สึก", "advice": "เที่ยวนอกบ้านได้ แต่อย่าตากแดดนาน เดี๋ยวร้อน!"},
        {"label": "หายใจคล่อง 🌬️", "desc": "ยังถือว่าปลอดภัยกับทุกคน", "advice": "ทำกิจกรรมกลางแจ้งได้ตามปกติครับ"}
    ],
    "moderate": [ # 25.1 - 37.5 (เหลือง)
        {"label": "เริ่มตุๆ แล้วนะ 💛", "desc": "ท้องฟ้าเริ่มมัว ไม่ใช่หมอกนะจ๊ะ", "advice": "คนแพ้ง่าย ใส่แมสก์หน่อยก็ดี กันไว้ก่อน"},
        {"label": "กลิ่นฝุ่นเริ่มมา 👃", "desc": "เริ่มเกินเกณฑ์ความสะอาดมานิดนึง", "advice": "เด็กเล็กกับคนแก่ อย่าเพิ่งซ่า ออกบ้านให้น้อยลง"},
        {"label": "การ์ดอย่าตก 🚧", "desc": "ฝุ่นเริ่มก่อตัว หายใจขัดๆ นิดหน่อย", "advice": "#งดเผาขยะ #งดเผาตอซัง ช่วยกันลดฝุ่นนะ"}
    ],
    "unhealthy": [ # 37.6 - 75 (ส้ม)
        {"label": "แสบจมูกแล้วแม่ 😷", "desc": "ฝุ่นหนา! เริ่มมีผลต่อสุขภาพชัดเจน", "advice": "ใส่หน้ากากอนามัยทันที! ใครไม่ใส่ถือว่าพลาด"},
        {"label": "ไม่น่าไหวแล้ว 🧡", "desc": "หายใจแล้วคอแห้ง ระคายคอ", "advice": "งดวิ่งกลางแจ้ง! เปลี่ยนไปโดดตบในบ้านแทนเถอะ"},
        {"label": "ฝุ่นบุกเมือง 🌪️", "desc": "เกินเกณฑ์มาตรฐานไปไกลแล้ว", "advice": "ปิดบ้านให้มิดชิด อย่าเปิดรับฝุ่นเข้ามานะ"}
    ],
    "hazardous": [ # > 75 (แดง)
        {"label": "แดงเดือด! เถื่อนมาก 🤬", "desc": "อันตรายสุดๆ ห้ามสูดดมเด็ดขาด", "advice": "❌ ห้ามออกจากบ้าน! ถ้าจำเป็นต้องใส่ N95 เท่านั้น"},
        {"label": "วิกฤตฝุ่นพิษ ☠️", "desc": "มองแทบไม่เห็นทาง หายใจคือตาย", "advice": "ขังตัวเองในห้องแอร์/ห้องปลอดฝุ่น ด่วนที่สุด!"},
        {"label": "นึกว่าอยู่ในท่อไอเสีย 🆘", "desc": "ค่าฝุ่นทะลุเพดาน อันตรายต่อทุกคน", "advice": "งดกิจกรรมทุกอย่างนอกบ้าน! ดูแลเด็กและคนแก่ดีๆ"}
    ]
}

# --- 2. ฟังก์ชันวิเคราะห์ (เพิ่มการเปรียบเทียบเกณฑ์) ---
def analyze_air_quality(pm25_value):
    try:
        val = float(pm25_value)
    except:
        return {
            "level": "Unsure",
            "label": "ไม่มีข้อมูล",
            "desc": "ระบบกำลังตรวจสอบ",
            "advice": "รอแป๊บนึงนะ",
            "compare_text": "",
            "color": "#808080"
        }

    selected_key = ""
    color_code = ""
    STANDARD_VAL = 37.5 # เกณฑ์มาตรฐานประเทศไทย (ใหม่)

    # เลือก Level และ สี
    if val <= 15:
        selected_key = "very_good"
        color_code = "#0099FF" # ฟ้าสดใส
    elif val <= 25:
        selected_key = "good"
        color_code = "#00C853" # เขียว
    elif val <= 37.5:
        selected_key = "moderate"
        color_code = "#FFAB00" # เหลืองเข้ม
    elif val <= 75:
        selected_key = "unhealthy"
        color_code = "#FF6D00" # ส้ม
    else:
        selected_key = "hazardous"
        color_code = "#D50000" # แดงเข้ม

    # --- ✨ ส่วนคำนวณเปรียบเทียบ (ให้เห็นภาพชัดๆ) ---
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

    # สุ่มคำพูด
    msg = random.choice(PM25_MESSAGES[selected_key])

    return {
        "level": selected_key,
        "label": msg['label'],
        "desc": msg['desc'],
        "advice": msg['advice'],
        "compare_text": compare_text, # ส่งค่าเปรียบเทียบกลับไป
        "color": color_code
    }

# --- 3. ฟังก์ชันดึงข้อมูล (คงเดิม) ---
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
    lat, lon = "14.9308", "100.3725"
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&lang=th&units=metric"
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
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key: return ("-", analyze_air_quality(None))
    lat, lon = "14.9308", "100.3725"
    url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={api_key}"
    try:
        res = requests.get(url, timeout=20)
        pm25 = res.json()['list'][0]['components']['pm2_5']
        return (f"{pm25:.1f}", analyze_air_quality(pm25))
    except:
        return ("-", analyze_air_quality(None))

# --- 4. สร้าง Caption (เพิ่มส่วนเปรียบเทียบ) ---
def generate_facebook_caption(water_level, discharge, weather, pm25_val, pm25_info) -> str:
    caption = []
    
    # พาดหัว
    if pm25_info['level'] in ['unhealthy', 'hazardous']:
         caption.append(f"🚨 ด่วน! {pm25_info['desc']}")
    else:
         caption.append(f"📅 รายงานอากาศ อินทร์บุรีบ้านเรา")

    caption.append("-----------------------------")
    
    # ส่วนฝุ่น
    if pm25_val != "-":
        caption.append(f"😷 ฝุ่น PM2.5 ตอนนี้: {pm25_val}")
        caption.append(f"📊 สถานะ: {pm25_info['label']}")
        caption.append(f"📉 เทียบเกณฑ์: {pm25_info['compare_text']}") # บรรทัดใหม่!
        caption.append(f"💡 ทำไงดี?: {pm25_info['advice']}")
    
    caption.append("") 
    
    # ส่วนน้ำ
    try:
        lvl = f"{float(water_level):.2f}"
    except: lvl = "รอตรวจสอบ"
    
    caption.append(f"🌊 ระดับน้ำ: {lvl} ม.")
    caption.append(f"💧 เขื่อนปล่อย: {discharge} ลบ.ม./วิ")
    caption.append(f"☁️ ฟ้าฝน: {weather}")
    
    # Hashtags
    tags = ["#อินทร์บุรี", "#รายงานฝุ่น", "#PM25"]
    if pm25_info['level'] in ['unhealthy', 'hazardous']:
        tags.append("#ฝุ่นหนามากแม่")
        tags.append("#ใส่แมสก์ด่วน")
    
    return "\n".join(caption) + "\n\n" + " ".join(tags)

# --- 5. สร้างรูปภาพ ---
def create_report_image(dam_discharge, water_level, weather_status, pm25_data_tuple):
    IMAGE_WIDTH = 788
    IMAGE_HEIGHT = 763
    
    pm25_val, pm25_info = pm25_data_tuple

    # ตั้งค่ารูปพื้นหลัง
    try:
        image = Image.open("background.png").convert("RGB")
    except:
        image = Image.new("RGB", (IMAGE_WIDTH, IMAGE_HEIGHT), "#fff6db")
    
    draw = ImageDraw.Draw(image)
    
    # โหลดฟอนต์ (ถ้าไม่มีจะใช้ Default)
    try:
        font_main = ImageFont.truetype("Sarabun-Bold.ttf", 44)
        font_sub = ImageFont.truetype("Sarabun-Regular.ttf", 38)
        font_pm = ImageFont.truetype("Sarabun-Bold.ttf", 55) # ใหญ่ขึ้น
    except:
        font_main = font_sub = font_pm = ImageFont.load_default()

    # ตำแหน่งกลาง
    center_x = IMAGE_WIDTH // 2
    y = 210 # เริ่มต้นเขียน Y
    spacing = 65

    # วาดข้อมูล
    # 1. น้ำ
    lvl_text = f"ระดับน้ำ: {water_level:.2f} ม." if isinstance(water_level, float) else "ระดับน้ำ: N/A"
    draw.text((center_x, y), lvl_text, font=font_main, fill="black", anchor="mm")
    y += spacing
    
    draw.text((center_x, y), f"ท้ายเขื่อนฯ: {dam_discharge} ลบ.ม./วิ", font=font_sub, fill="black", anchor="mm")
    y += spacing
    
    draw.text((center_x, y), f"ฟ้าฝน: {weather_status}", font=font_sub, fill="black", anchor="mm")
    y += spacing + 20 # เว้นวรรคใหญ่ก่อนเข้าเรื่องฝุ่น

    # 2. ฝุ่น PM2.5
    draw.text((center_x, y), "ค่าฝุ่น PM2.5 (อินทร์บุรี)", font=font_main, fill="#555555", anchor="mm")
    y += spacing
    
    # ตัวเลขฝุ่น (สีตามสถานการณ์)
    draw.text((center_x, y), f"{pm25_val} μg/m³", font=font_pm, fill=pm25_info['color'], anchor="mm")
    y += spacing
    
    # คำอธิบายชาวบ้าน
    draw.text((center_x, y), pm25_info['label'], font=font_sub, fill=pm25_info['color'], anchor="mm")

    # Save
    image.save("final_report.jpg", quality=95)
    
    # Gen Caption
    caption = generate_facebook_caption(water_level, dam_discharge, weather_status, pm25_val, pm25_info)
    with open("status.txt", "w", encoding="utf-8") as f:
        f.write(caption)

    print(f"Done! PM2.5: {pm25_val} ({pm25_info['label']})")

if __name__ == "__main__":
    load_dotenv()
    dam = get_chao_phraya_dam_data()
    level = get_inburi_bridge_data()
    weather = get_weather_status()
    pm25 = get_pm25_data()
    create_report_image(dam, level, weather, pm25)
