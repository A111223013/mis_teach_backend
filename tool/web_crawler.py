import requests
from lxml import html
import json
import time
import os

# ======== 設定區 ========
BASE_URL = "https://www.ithome.com.tw/latest?page={}"
OUTPUT_FILE = "data/ithome_news.json"  # 你的指定路徑
TOTAL_PAGES = 15  # 要爬的頁數
DELAY_SECONDS = 1  # 每頁延遲時間（秒）
# =========================

# 確保資料夾存在
os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

all_news = []

for page in range(1, TOTAL_PAGES + 1):
    url = BASE_URL.format(page)
    print(f"📄 正在爬取第 {page} 頁: {url}")

    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    response.encoding = "utf-8"
    tree = html.fromstring(response.text)

    items = tree.xpath('/html/body/div[4]/div/section/div/div[1]/div')
    print(f"  └─ 共找到 {len(items)} 筆新聞")

    for i, item in enumerate(items, start=1):
        try:
            # image
            img = item.xpath(f'./div/span/div/p[1]/a/img/@src')
            img_url = img[0] if img else ""

            # image href
            img_href = item.xpath(f'./div/span/div/p[1]/a/@href')
            href = img_href[0] if img_href else ""

            # tags
            tags = item.xpath(f'./div/span/div/p[2]/a')
            tags_data = [{"text": t.text_content().strip(), "href": t.get("href")} for t in tags]

            # title
            title_elem = item.xpath(f'./div/span/div/p[3]/a')
            title_data = {"text": "", "href": ""}
            if title_elem:
                title_data["text"] = title_elem[0].text_content().strip()
                title_data["href"] = title_elem[0].get("href")

            # summary
            summary_elem = item.xpath(f'./div/span/div/div/p/text()')
            summary_text = summary_elem[0].strip() if summary_elem else ""

            # date
            date_elem = item.xpath(f'./div/span/div/p[4]/text()')
            date_text = date_elem[0].strip() if date_elem else ""

            all_news.append({
                "image": img_url,
                "href": href,
                "tags": tags_data,
                "title": title_data,
                "summary": summary_text,
                "date": date_text
            })

        except Exception as e:
            print(f"❌ 第 {page} 頁第 {i} 筆發生錯誤: {e}")

    time.sleep(DELAY_SECONDS)

# 儲存成 JSON 檔案
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(all_news, f, ensure_ascii=False, indent=2)

print(f"\n✅ 爬取完成，共 {len(all_news)} 筆新聞已儲存到：{OUTPUT_FILE}")
