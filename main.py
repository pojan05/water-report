import os
import json
import requests
import re
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
from requests_html import HTMLSession

TALING_LEVEL = 13.0

# --- ฟังก์ชันดึงข้อมูล (ใช้ของเดิม) ---
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
    """
    Scrape the latest water level for the In Buri bridge gauge from ThaiWater.

    The ThaiWater provincial dashboard is highly dynamic and its DOM structure can
    change over time. The previous implementation assumed the station name was
    contained within a <th> element with a `scope="row"` attribute and that the
    second <td> contained the numeric water level. That assumption broke when
    the site markup changed. This function now takes a more flexible approach:

    * It renders the page using requests_html to execute JavaScript.
    * It iterates over every table row and checks the combined text of the row
      for the substring "อินทร์บุรี" (In Buri). This is more tolerant of
      structural changes because it doesn’t rely on a particular tag hierarchy.
    * Within the matching row we search for the first cell (td or th) that
      contains a numeric value with a decimal point or comma. This heuristic
      picks up the reported water level regardless of the exact column order.

    If parsing fails, the function returns "-" so that the caller can
    gracefully handle missing data.

    Returns:
        float or str: The water level in metres if found, otherwise "-".
    """
    url = "https://singburi.thaiwater.net/wl"
    try:
        session = HTMLSession()
        # Pretend to be a regular browser to avoid simple bot blocks
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        }
        r = session.get(url, headers=headers, timeout=30)
        # Render the page; scrolldown helps load lazy‑loaded tables
        r.html.render(sleep=5, timeout=90, scrolldown=3)
        soup = BeautifulSoup(r.html.html, "html.parser")
        # Search every row for the station name
        for row in soup.find_all("tr"):
            row_text = row.get_text(strip=True)
            if "อินทร์บุรี" not in row_text:
                continue
            # Find the first numeric cell in the row. We include both th and td
            for cell in row.find_all(["td", "th"]):
                cell_text = cell.get_text(strip=True)
                # Match numbers with decimal or comma as thousands separator
                match = re.search(r"[0-9]+[\.,][0-9]+", cell_text)
                if match:
                    try:
                        # Replace commas for decimal conversion
                        value_str = cell_text.replace(",", "")
                        return float(value_str)
                    except ValueError:
                        continue
            # Fallback: if we didn't find a numeric cell but we did match the row,
            # break early since subsequent rows refer to other stations
            break
        return "-"
    except Exception:
        return "-"

def get_weather_status():
    import os
    import requests

    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        return "ไม่มีข้อมูลสภาพอากาศ"

    # พิกัดของตำบลอินทร์บุรี อำเภออินทร์บุรี จังหวัดสิงห์บุรี
    lat, lon = "14.9308", "100.3725"
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&lang=th&units=metric"

    try:
        res = requests.get(url, timeout=30)
        data = res.json()
        if "weather" not in data or len(data["weather"]) == 0:
            return "ไม่มีข้อมูลสภาพอากาศ"

        desc_en = data["weather"][0]["main"].lower()
        desc_detail = data["weather"][0]["description"].lower()

        # Mapping แบบเข้าใจง่าย
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

    except Exception as e:
        return "ดึงข้อมูลอากาศไม่สำเร็จ"


# --- ✨ [เพิ่มใหม่] ฟังก์ชันสร้าง Caption ที่ขาดไป ---
def generate_facebook_caption(water_level, discharge, weather) -> str:
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

    if level == 0.0:
         caption_lines.append("ไม่สามารถดึงข้อมูลระดับน้ำได้ กำลังตรวจสอบ")
    elif level >= 12.0:
        caption_lines.append(f"⚠️ ระดับน้ำที่ {level:.2f} ม. เฝ้าระวังขั้นสูงสุด")
        hashtags.append("#น้ำวิกฤต")
    elif level >= 11.5:
        caption_lines.append(f"🔶 ระดับน้ำ {level:.2f} ม. โปรดติดตามใกล้ชิด")
        hashtags.append("#เฝ้าระวัง")
    else:
        caption_lines.append(f"✅ ระดับน้ำอยู่ที่ {level:.2f} ม. ปลอดภัยดีในขณะนี้")
        hashtags.append("#ปลอดภัยดี")

    if dis_val >= 2000:
        caption_lines.append(f"เขื่อนเจ้าพระยาระบายน้ำแรง {dis_val} ลบ.ม./วิ")
        hashtags.append("#เขื่อนระบายแรง")
    elif dis_val >= 1000:
        caption_lines.append(f"เขื่อนระบายน้ำ {dis_val} ลบ.ม./วิ")
        hashtags.append("#เขื่อนระบายมาก")

    if "ฝน" in weather:
        hashtags.append("#ฝนตก")
    elif "เมฆ" in weather:
        hashtags.append("#ฟ้าครึ้ม")

    hashtags.append("#อินทร์บุรีรอดมั้ย")

    return "\n".join(caption_lines) + "\n\n" + " ".join(hashtags)

# --- ✨ [แก้ไขใหม่ทั้งหมด] ฟังก์ชันสร้างรูปภาพ ---
def create_report_image(dam_discharge, water_level, weather_status):
    from PIL import Image, ImageDraw, ImageFont

    IMAGE_WIDTH = 788
    IMAGE_HEIGHT = 763
    TEXT_COLOR = "#000000"

    # พิกัดกรอบข้อความ (วัดจาก background.png จริง)
    box_left = 60
    box_right = IMAGE_WIDTH - 60
    box_top = 170
    box_bottom = 610
    center_x = (box_left + box_right) // 2
    Y_START = box_top + 20
    line_spacing = 60

    # โหลดภาพพื้นหลัง
    try:
        image = Image.open("background.png").convert("RGB")
    except FileNotFoundError:
        image = Image.new("RGB", (IMAGE_WIDTH, IMAGE_HEIGHT), "#fff6db")

    draw = ImageDraw.Draw(image)

    # โหลดฟอนต์
    try:
        font_main = ImageFont.truetype("Sarabun-Bold.ttf", 40)
        font_sub = ImageFont.truetype("Sarabun-Regular.ttf", 36)
    except:
        font_main = font_sub = ImageFont.load_default()

    # เตรียมข้อความ
    level_text = f"ระดับน้ำ ณ อินทร์บุรี: {water_level:.2f} ม." if isinstance(water_level, float) else "ระดับน้ำ ณ อินทร์บุรี: N/A"
    discharge_text = f"การระบายน้ำท้ายเขื่อนฯ: {dam_discharge} ลบ.ม./วินาที"
    weather_text = f"สภาพอากาศ: {weather_status}"

    TALING_LEVEL = 13.0
    diff = TALING_LEVEL - water_level if isinstance(water_level, float) else 99
    if diff <= 1.5:
        sit_text = "สถานการณ์: วิกฤต"
        sit_detail = "เสี่ยงน้ำล้นตลิ่ง"
    elif diff <= 2.5:
        sit_text = "สถานการณ์: เฝ้าระวัง"
        sit_detail = "ระดับน้ำใกล้ตลิ่ง"
    else:
        sit_text = "สถานการณ์: ปกติ"
        sit_detail = "น้ำยังห่างตลิ่ง ปลอดภัยจ้า"

    # วาดข้อความลงภาพ
    y = Y_START
    draw.text((center_x, y), level_text, font=font_main, fill=TEXT_COLOR, anchor="mm")
    y += line_spacing
    draw.text((center_x, y), discharge_text, font=font_sub, fill=TEXT_COLOR, anchor="mm")
    y += line_spacing
    draw.text((center_x, y), weather_text, font=font_sub, fill=TEXT_COLOR, anchor="mm")
    y += line_spacing
    draw.text((center_x, y), sit_text, font=font_main, fill=TEXT_COLOR, anchor="mm")
    y += line_spacing
    draw.text((center_x, y), sit_detail, font=font_sub, fill=TEXT_COLOR, anchor="mm")

    # บันทึกภาพผลลัพธ์
    image.save("final_report.jpg", quality=95)

    # สร้าง caption สำหรับ Facebook
    dynamic_caption = generate_facebook_caption(water_level, dam_discharge, weather_status)
    with open("status.txt", "w", encoding="utf-8") as f:
        f.write(dynamic_caption)





if __name__ == "__main__":
    load_dotenv()
    dam = get_chao_phraya_dam_data()
    level = get_inburi_bridge_data()
    weather = get_weather_status()
    create_report_image(dam, level, weather)
    
