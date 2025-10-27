import requests
from lxml import html
import json
import time
import os
from flask import Blueprint, jsonify, request

# 建立 Blueprint
ithome_bp = Blueprint("ithome", __name__)

# ======== 設定區 ========
BASE_URL = "https://www.ithome.com.tw/latest?page={}"
OUTPUT_FILE = "data/ithome_news.json"  # 你的指定路徑
TOTAL_PAGES = 15  # 要爬的頁數
DELAY_SECONDS = 1  # 每頁延遲時間（秒）
# =========================

def crawl_ithome_news():
    """爬取 iThome 新聞的函數"""
    # 確保資料夾存在
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    
    all_news = []
    
    for page in range(1, TOTAL_PAGES + 1):
        url = BASE_URL.format(page)
        print(f"📄 正在爬取第 {page} 頁: {url}")
        
        try:
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
            
        except Exception as e:
            print(f"❌ 爬取第 {page} 頁時發生錯誤: {e}")
            continue
    
    # 儲存成 JSON 檔案
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_news, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 爬取完成，共 {len(all_news)} 筆新聞已儲存到：{OUTPUT_FILE}")
    return all_news

@ithome_bp.route('/crawl', methods=['POST'])
def crawl_news():
    """手動觸發爬蟲的 API 端點"""
    try:
        news_data = crawl_ithome_news()
        return jsonify({
            "success": True,
            "message": f"成功爬取 {len(news_data)} 筆新聞",
            "count": len(news_data),
            "data_file": OUTPUT_FILE
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"爬蟲執行失敗: {str(e)}"
        }), 500

@ithome_bp.route('/news', methods=['GET'])
def get_news():
    """取得已爬取的新聞資料"""
    try:
        if os.path.exists(OUTPUT_FILE):
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                news_data = json.load(f)
            return jsonify({
                "success": True,
                "count": len(news_data),
                "data": news_data
            })
        else:
            return jsonify({
                "success": False,
                "message": "尚未爬取新聞資料，請先執行爬蟲"
            }), 404
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"讀取新聞資料失敗: {str(e)}"
        }), 500

@ithome_bp.route('/status', methods=['GET'])
def get_status():
    """檢查爬蟲狀態"""
    try:
        if os.path.exists(OUTPUT_FILE):
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                news_data = json.load(f)
            file_stats = os.stat(OUTPUT_FILE)
            return jsonify({
                "success": True,
                "has_data": True,
                "count": len(news_data),
                "last_modified": time.ctime(file_stats.st_mtime),
                "file_path": OUTPUT_FILE
            })
        else:
            return jsonify({
                "success": True,
                "has_data": False,
                "message": "尚未爬取新聞資料"
            })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"檢查狀態失敗: {str(e)}"
        }), 500

# 如果直接執行此檔案，則執行爬蟲
if __name__ == "__main__":
    crawl_ithome_news()

# 當模組被匯入時自動執行爬蟲
crawl_ithome_news()
