
def generate_facebook_caption(water_level: float, discharge: int, weather: str) -> str:
    caption_lines = []
    hashtags = []

    if water_level >= 12.0:
        caption_lines.append(f"⚠️ น้ำสูงมาก! ระดับน้ำที่ {water_level:.2f} ม. เฝ้าระวังขั้นสูงสุด")
        hashtags.append("#น้ำวิกฤต")
    elif water_level >= 11.5:
        caption_lines.append(f"🔶 น้ำใกล้ตลิ่ง! ระดับ {water_level:.2f} ม. โปรดติดตามใกล้ชิด")
        hashtags.append("#เฝ้าระวัง")
    elif water_level >= 11.0:
        caption_lines.append(f"🟡 ระดับน้ำเริ่มสูง {water_level:.2f} ม. ติดตามสถานการณ์")
        hashtags.append("#ติดตามสถานการณ์")
    else:
        caption_lines.append(f"✅ ระดับน้ำอยู่ที่ {water_level:.2f} ม. ปลอดภัยดีในขณะนี้")
        hashtags.append("#ปลอดภัย")

    if discharge >= 2500:
        caption_lines.append(f"เขื่อนเจ้าพระยาระบายแรงถึง {discharge} ลบ.ม./วิ")
        hashtags.append("#เขื่อนระบายแรง")
    elif discharge >= 1500:
        caption_lines.append(f"เขื่อนยังระบายที่ {discharge} ลบ.ม./วิ")
        hashtags.append("#เขื่อนระบาย")

    if "ฝน" in weather or "ครึ้ม" in weather:
        caption_lines.append(f"สภาพอากาศวันนี้: {weather}")
        hashtags.append("#ฝนตก #อากาศไม่แจ่มใส")
    elif "แจ่มใส" in weather or "ชัดเจน" in weather:
        hashtags.append("#อากาศดี")

    hashtags.append("#อินทร์บุรีรอดมั้ย #อัปเดตน้ำ")

    return "\n".join(caption_lines) + "\n" + " ".join(hashtags)
