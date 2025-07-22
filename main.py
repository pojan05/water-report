import os
import requests
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta

# --- 1. ส่วนของการดึงข้อมูลผ่าน API (วิธีใหม่ที่เสถียร) ---

def get_api_data(station_id, data_type):
    """
    ฟังก์ชันกลางสำหรับดึงข้อมูลจาก API ของสถาบันสารสนเทศทรัพยากรน้ำ (HII)
    data_type สามารถเป็น 'waterlevel' หรือ 'flow'
    """
    try:
        # URL ของ API สำหรับข้อมูลล่าสุด
        url = f"https://api-v3.thaiwater.net/api/v1/thaiwater30/public/latest_tele_data?station_type=tele_waterlevel&station_id={station_id}"
        response = requests.get(url, timeout=20)
        response.raise_for_status() # เช็คว่า request สำเร็จหรือไม่
        data = response.json()

        # ตรวจสอบว่ามีข้อมูลส่งกลับมาหรือไม่
        if data and data['data']:
            station_data = data['data'][0]
            if data_type == 'waterlevel':
                # ดึงข้อมูลระดับน้ำ (m. MSL)
                value = station_data.get('waterlevel_msl', {}).get('value')
                return f"{value:.2f}" if value is not None else "N/A"
            elif data_type == 'flow':
                # ดึงข้อมูลอัตราการไหล (m3/s)
                value = station_data.get('flow_rate', {}).get('value')
                return f"{int(value)}" if value is not None else "N/A"
        return "N/A"
    except requests.exceptions.RequestException as e:
        print(f"เกิดข้อผิดพลาดในการเชื่อมต่อ API ของสถานี {station_id}: {e}")
        return "N/A"
    except (KeyError, IndexError):
        print(f"ไม่พบข้อมูลที่ต้องการใน API response ของสถานี {station_id}")
        return "N/A"

# --- 2. ส่วนของการสร้างภาพ (ปรับปรุงเล็กน้อย) ---

def create_report_image(dam_discharge, water_level):
    today = datetime.now()
    dates = [(today - timedelta(days=i)).strftime("%d/%m") for i in range(6, -1, -1)]

    try:
        current_level_float = float(water_level)
    except (ValueError, TypeError):
        current_level_float = 0.0

    # สร้างข้อมูลกราฟย้อนหลังแบบคร่าวๆ
    mock_levels = [current_level_float - 0.2, current_level_float + 0.1, current_level_float - 0.1, 
                   current_level_float + 0.2, current_level_float - 0.3, current_level_float + 0.1, 
                   current_level_float]

    # ตรวจสอบไฟล์ หากไม่เจอจะสร้างภาพเปล่าพร้อมข้อความแจ้งเตือน
    if not os.path.exists("background.png") or not os.path.exists("Sarabun-Regular.ttf"):
        print("Error: ไม่พบไฟล์ background.png หรือ Sarabun-Regular.ttf")
        img = Image.new('RGB', (800, 600), color='white')
        d = ImageDraw.Draw(img)
        try:
            error_font = ImageFont.truetype("Sarabun-Regular.ttf", 20)
            d.text((10, 10), "Error: ไม่พบไฟล์ background.png หรือ Sarabun-Regular.ttf", fill='red', font=error_font)
        except IOError:
            d.text((10, 10), "Error: Missing background.png or font file.", fill='red')
        img.save('final_report.jpg')
        return

    # สร้างกราฟ
    fig, ax = plt.subplots(figsize=(7.5, 3), dpi=100)
    ax.plot(dates, mock_levels, color="#0077b6", linewidth=3)
    ax.fill_between(dates, mock_levels, color="#00b4d8", alpha=0.3)
    ax.axis('off')
    fig.patch.set_alpha(0.0)
    
    graph_path = "graph.png"
    plt.savefig(graph_path, format='png', bbox_inches='tight', pad_inches=0, transparent=True)
    plt.close()

    # ประกอบภาพ
    base_image = Image.open("background.png").convert("RGBA")
    graph_image = Image.open(graph_path)
    base_image.paste(graph_image, (40, 290), graph_image)
    
    draw = ImageDraw.Draw(base_image)
    font_path = "Sarabun-Regular.ttf"
    font_large = ImageFont.truetype(font_path, 60)
    font_medium = ImageFont.truetype(font_path, 48)

    # วาดข้อความ
    draw.text((120, 165), f"{water_level} ม.", font=font_large, fill="#003f5c")
    draw.text((430, 165), f"{dam_discharge} ม³/s", font=font_medium, fill="#003f5c")
    draw.text((120, 240), "แดดจ้า", font=font_medium, fill="#003f5c")
    draw.text((630, 280), water_level, font=font_medium, fill="white", stroke_width=2, stroke_fill="black")

    base_image.convert("RGB").save("final_report.jpg", "JPEG", quality=90)
    print("สร้างภาพ 'final_report.jpg' สำเร็จ")
    os.remove(graph_path)

# --- 3. ส่วนของการรันโปรแกรม ---
if __name__ == "__main__":
    print("เริ่มต้นกระบวนการสร้างรายงานผ่าน API...")
    
    # รหัสสถานีสำหรับ API
    CHAO_PHRAYA_DAM_STATION_ID = "37" # สถานีท้ายเขื่อนเจ้าพระยา (C.2)
    INBURI_STATION_ID = "24"          # สถานีสะพานอินทร์บุรี (C.35)

    dam_value = get_api_data(CHAO_PHRAYA_DAM_STATION_ID, 'flow')
    level_value = get_api_data(INBURI_STATION_ID, 'waterlevel')
    
    print(f"ข้อมูลที่ดึงได้: เขื่อนเจ้าพระยา={dam_value}, ระดับน้ำอินทร์บุรี={level_value}")
    
    create_report_image(dam_discharge=dam_value, water_level=level_value)
    print("กระบวนการเสร็จสิ้น")
