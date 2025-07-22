import os
import requests

def post_image():
    token = os.getenv("FB_PAGE_TOKEN")
    page_id = os.getenv("FB_PAGE_ID")
    url = f"https://graph.facebook.com/{page_id}/photos"

    with open("final_report.jpg", "rb") as img:
        res = requests.post(
            url,
            data={"caption": "📊 รายงานระดับน้ำประจำวัน #อินทร์บุรีรอดมั้ย", "access_token": token},
            files={"source": img}
        )
        print("✅ Response:", res.text)

if __name__ == "__main__":
    post_image()
