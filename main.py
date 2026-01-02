import os
import json
import requests
import re
import random
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
from requests_html import HTMLSession

# --- 1. คลังคำพูดแจ้งเตือนฝุ่นแบบฉลาด (Smart Messages) ---
PM25_MESSAGES = {
    "very_good": [ # 0 - 15 (ฟ้า)
        {"label": "อากาศดีมาก 💙", "desc": "ฟ้าใสปิ๊ง! สูดอากาศได้เต็มปอด", "advice": "เหมาะมากที่จะไปวิ่งออกกำลังกาย หรือตากผ้าครับ"},
        {"label": "สดชื่นสุดๆ 🌬️", "desc": "ลมพัดเย็นสบาย ไร้ฝุ่นกวนใจ", "advice": "เปิดหน้าต่างรับลมได้เลย อากาศดีแบบนี้หายากนะ"},
        {"label": "อากาศคลีนๆ ✨", "desc": "ไม่มีฝุ่นเลย ปอดคุณยิ้มได้", "advice": "ใครดองงานซักผ้าไว้ รีบจัดเลยครับ แดดดีลมดี!"}
    ],
    "good": [ # 15.1 - 25 (เขียว)
        {"label": "อากาศดี 💚", "desc": "ยังโอเค! ใช้ชีวิตได้ตามปกติ", "advice": "เที่ยวนอกบ้านได้สบายๆ แต่อย่าลืมดื่มน้ำเยอะๆ นะ"},
        {"label": "เขียวผ่านตลอด ✅", "desc": "ฝุ่นนิดเดียว แทบไม่รู้สึก", "advice": "ทำกิจกรรมกลางแจ้งได้ครับ วันนี้อากาศเป็นมิตร"},
        {"label": "สบายๆ หายห่วง 😊", "desc": "คุณภาพอากาศอยู่ในเกณฑ์ดี", "advice": "ใช้ชีวิตให้มีความสุขครับ วันนี้ปอดไม่ต้องทำงานหนัก"}
    ],
    "moderate": [ # 25.1 - 37.5 (เหลือง)
        {"label": "เริ่มขุ่นๆ 💛", "desc": "ฟ้าเริ่มมัว ไม่ใช่หมอกแต่คือฝุ่น", "advice": "กลุ่มเสี่ยง (เด็ก/คนแก่) ระวังหน่อยนะ #งดเผาขยะ ช่วยกันครับ"},
        {"label": "การ์ดอย่าตก 🚧", "desc": "ฝุ่นเริ่มมาเยือน จมูกไวเริ่มรู้เรื่อง", "advice": "ใครแพ้ง่าย เลี่ยงที่โล่งแจ้งนิดนึง ใส่หน้ากากกันไว้ดีกว่า"},
        {"label": "เริ่มหนาตา 🌫️", "desc": "มองไปไกลๆ เริ่มไม่ชัดแล้วนะ", "advice": "ลดการใช้รถยนต์ถ้าทำได้ และช่วยกันสอดส่องคนเผาหญ้าครับ"}
    ],
    "unhealthy": [ # 37.6 - 75 (ส้ม)
        {"label": "เริ่มแย่แล้ว 🧡", "desc": "แสบจมูก แสบคอ ฝุ่นเยอะชัดเจน", "advice": "⚠️ ใส่หน้ากากอนามัยทันทีที่ออกนอกบ้าน อย่าประมาท!"},
        {"label": "เตือนภัยฝุ่น 😷", "desc": "หายใจแล้วรู้สึกไม่โล่ง คอแห้ง", "advice": "งดวิ่งกลางแจ้งเปลี่ยนไปออกกำลังกายในร่มแทนนะ"},
        {"label": "ฝุ่นบุกหนัก 🌪️", "desc": "สภาพอากาศปิด ฝุ่นสะสมตัวสูง", "advice": "ปิดหน้าต่างให้มิดชิด! ใครเป็นภูมิแพ้เตรียมยาไว้เลย"}
    ],
    "hazardous": [ # > 75 (แดง)
        {"label": "วิกฤต! แดงเถือก ❤️", "desc": "อันตรายมาก! ฝุ่นหนาจนน่ากลัว", "advice": "❌ ห้ามออกกำลังกายกลางแจ้งเด็ดขาด! ต้องใส่ N95 เท่านั้น"},
        {"label": "ฉุกเฉินอากาศพิษ ☠️", "desc": "มองไม่เห็นตึก! หายใจแล้วอันตราย", "advice": "อยู่แต่ในห้องแอร์/ห้องปลอดฝุ่น ปกป้องเด็กและคนชราด่วน!"},
        {"label": "ไม่ไหวบอกไหว 🆘", "desc": "ค่าฝุ่นพุ่งทะลุเพดาน อันตรายต่อทุกคน", "advice": "งดออกจากบ้านถ้าไม่จำเป็น! นี่คือคำเตือนระดับสูงสุด"}
    ]
}

# --- 2. ฟังก์ชันวิเคราะห์คุณภาพอากาศ (เลือกคำพูด + สี) ---
def analyze_air_quality(pm25_value):
    try:
        val = float(pm25_value)
    except:
        return {
            "level": "Unsure",
            "label": "ไม่มีข้อมูล",
            "desc": "ระบบกำลังตรวจสอบ",
            "advice": "รอสักครู่นะครับ",
            "color": "#808080"
        }

    selected_key = ""
    color_code = ""
    
    # เกณฑ์ PM2.5 และการเลือกสี
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

    # สุ่มเลือกข้อความ 1 ชุดจากคลังคำพูด
    msg = random.choice(PM25_MESSAGES[selected_key])

    return {
        "level": selected_key,
        "label": msg['label'],
        "desc": msg['desc'],
        "advice": msg['advice'],
        "color": color_code
    }

# --- 3. ฟังก์ชันดึงข้อมูลต่างๆ (คงเดิมและปรับปรุง) ---

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
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"}
        r = session.get(url, headers=headers, timeout=30)
        r.html.render(sleep=5, timeout=90, scrolldown=3)
        soup = BeautifulSoup(r.html.html, "html.parser")
        for row in soup.find_all("tr"):
            station_th = row.find("th")
            if not station_th: continue
            station_name = station_th.get_text(strip=True)
            if "อินทร์บุรี" not in station_name: continue
            tds = row.find_all("td")
            if len(tds) >= 3:
                water_text = tds[2].get_text(strip=True)
                match = re.search(r"[0-9]+[\.,][0-9]+", water_text)
                if match:
                    try:
                        return float(water_text.replace(",", ""))
                    except ValueError: pass
            return "-"
        return "-"
    except Exception:
        return "-"

def get_weather_status():
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key: return "ไม่มีข้อมูลสภาพอากาศ"
    lat, lon = "14.9308", "100.3725"
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&lang=th&units=metric"
    try:
        res = requests.get(url, timeout=30)
        data = res.json()
        if "weather" not in data or len(data["weather"]) == 0: return "ไม่มีข้อมูลสภาพอากาศ"
        desc_en = data["weather"][0]["main"].lower()
        desc_detail = data["weather"][0]["description"].lower()
        if "rain" in desc_en: return "ฝนตก"
        elif "cloud" in desc_en:
            if "overcast" in desc_detail: return "เมฆครึ้มมาก"
            elif "scattered" in desc_detail: return "เมฆกระจาย"
            else: return "เมฆมาก"
        elif "clear" in desc_en: return "ท้องฟ้าแจ่มใส"
        elif "storm" in desc_en or "thunderstorm" in desc_en: return "พายุฝนฟ้าคะนอง"
        elif "mist" in desc_en or "fog" in desc_en: return "หมอกลง"
        else: return desc_detail.capitalize()
    except Exception: return "ดึงข้อมูลอากาศไม่สำเร็จ"

def get_pm25_data():
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        return ("-", analyze_air_quality(None))

    lat, lon = "14.9308", "100.3725"
    url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={api_key}"

    try:
        res = requests.get(url, timeout=20)
        data = res.json()
        pm25 = data['list'][0]['components']['pm2_5']
        # คืนค่าตัวเลข และ ผลวิเคราะห์ (Smart Data)
        return (f"{pm25:.1f}", analyze_air_quality(pm25))
    except Exception as e:
        print(f"Error fetching PM2.5: {e}")
        return ("-", analyze_air_quality(None))

# --- 4. ฟังก์ชันสร้าง Caption Facebook ---
def generate_facebook_caption(water_level, discharge, weather, pm25_val, pm25_info) -> str:
    caption = []
    
    # ส่วนหัวข้อ (Headlines)
    if pm25_info['level'] in ['unhealthy', 'hazardous']:
         caption.append(f"🚨 เตือนภัยฝุ่น! {pm25_info['desc']}")
    else:
         caption.append(f"📅 อัปเดตสถานการณ์น้ำและฝุ่น อินทร์บุรี")

    caption.append("-----------------------------")
    
    # ข้อมูลฝุ่น
    if pm25_val != "-":
        caption.append(f"😷 ค่าฝุ่น PM2.5: {pm25_val} μg/m³")
        caption.append(f"สถานะ: {pm25_info['label']}")
        caption.append(f"💡 คำแนะนำ: {pm25_info['advice']}")
    
    caption.append("") 
    
    # ข้อมูลน้ำ
    try:
        lvl = float(water_level)
        caption.append(f"🌊 ระดับน้ำเจ้าพระยา: {lvl:.2f} ม.")
    except:
        caption.append(f"🌊 ระดับน้ำเจ้าพระยา: รอตรวจสอบ")
        
    if str(discharge) != "-":
        caption.append(f"💧 เขื่อนระบาย: {discharge} ลบ.ม./วิ")
    
    caption.append(f"☁️ สภาพอากาศ: {weather}")
    
    # Hashtags
    tags = ["#อินทร์บุรี", "#PM25", "#ระดับน้ำเจ้าพระยา"]
    if pm25_info['level'] in ['unhealthy', 'hazardous']:
        tags.append("#ฝุ่นเยอะมาก")
        tags.append("#ดูแลสุขภาพด้วยนะ")
    elif pm25_info['level'] in ['very_good', 'good']:
        tags.append("#อากาศดี")
        tags.append("#น่าเที่ยว")
    
    return "\n".join(caption) + "\n\n" + " ".join(tags)

# --- 5. ฟังก์ชันสร้างรูปภาพ ---
def create_report_image(dam_discharge, water_level, weather_status, pm25_data_tuple):
    IMAGE_WIDTH = 788
    IMAGE_HEIGHT = 763
    TEXT_COLOR = "#000000"

    pm25_val, pm25_info = pm25_data_tuple # แตกตัวแปรออกมา

    box_left = 60
    box_right = IMAGE_WIDTH - 60
    box_top = 170
    center_x = (box_left + box_right) // 2
    
    Y_START = box_top + 40 
    line_spacing = 70 

    try:
        image = Image.open("background.png").convert("RGB")
    except FileNotFoundError:
        image = Image.new("RGB", (IMAGE_WIDTH, IMAGE_HEIGHT), "#fff6db")

    draw = ImageDraw.Draw(image)

    try:
        font_main = ImageFont.truetype("Sarabun-Bold.ttf", 44)
        font_sub = ImageFont.truetype("Sarabun-Regular.ttf", 38)
        font_pm = ImageFont.truetype("Sarabun-Bold.ttf", 48)
    except:
        font_main = font_sub = font_pm = ImageFont.load_default()

    # เตรียมข้อความ
    level_text = f"ระดับน้ำ ณ อินทร์บุรี: {water_level:.2f} ม." if isinstance(water_level, float) else "ระดับน้ำ ณ อินทร์บุรี: N/A"
    discharge_text = f"ท้ายเขื่อนฯ: {dam_discharge} ลบ.ม./วินาที"
    weather_text = f"สภาพอากาศ: {weather_status}"
    
    # ข้อความฝุ่นจาก Smart Info
    pm_label_text = f"ฝุ่น PM2.5 (ต.อินทร์บุรี):"
    pm_value_text = f"{pm25_val} μg/m³"
    pm_desc_text = pm25_info['label'] # เช่น "วิกฤต! แดงเถือก ❤️"

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
    y += line_spacing + 10 

    # 4. หัวข้อฝุ่น
    draw.text((center_x, y), pm_label_text, font=font_main, fill="#444444", anchor="mm")
    y += line_spacing
    
    # 5. ค่าฝุ่น (ใส่สีตามระดับความรุนแรง)
    draw.text((center_x, y), pm_value_text, font=font_pm, fill=pm25_info['color'], anchor="mm")
    y += line_spacing
    
    # 6. คำอธิบายสั้นๆ (ใส่สีเหมือนกัน)
    draw.text((center_x, y), pm_desc_text, font=font_sub, fill=pm25_info['color'], anchor="mm")

    # บันทึกภาพ
    image.save("final_report.jpg", quality=95)

    # สร้าง Caption และบันทึก
    dynamic_caption = generate_facebook_caption(water_level, dam_discharge, weather_status, pm25_val, pm25_info)
    with open("status.txt", "w", encoding="utf-8") as f:
        f.write(dynamic_caption)
    
    print(f"Report Generated: Level={water_level}, PM2.5={pm25_val}, Info={pm25_info['label']}")

# --- Main Execution ---
if __name__ == "__main__":
    load_dotenv()
    dam = get_chao_phraya_dam_data()
    level = get_inburi_bridge_data()
    weather = get_weather_status()
    pm25_data = get_pm25_data() # ดึงค่าฝุ่น + Smart Info
    
    create_report_image(dam, level, weather, pm25_data)
