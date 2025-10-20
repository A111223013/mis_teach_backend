# tool/ithome_crawler.py
from flask import Blueprint, jsonify
import requests
from lxml import html

ithome_bp = Blueprint('ithome', __name__)

@ithome_bp.route('/api/news', methods=['GET'])
def get_latest_ithome_news():
    """爬取 iThome 首頁前三則新聞（固定 XPath + 迴圈）"""
    url = "https://www.ithome.com.tw"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        tree = html.fromstring(response.content)

        news_data = []

        for i in range(1, 4):  # 抓前三則
            base_xpath = f'//*[@id="block-views-latest-news-block-3"]/div/div[1]/div[{i}]/div/span/div'

            # 1. 圖片
            img_xpath = f'{base_xpath}/p[1]/a/img/@src'
            img = tree.xpath(img_xpath)
            img_url = img[0] if img else ''

            # 2. Tags（文字 + href）
            tags_xpath = f'{base_xpath}/p[2]/a'
            tags_nodes = tree.xpath(tags_xpath)
            tags = [{"text": t.text.strip(), "href": t.get("href")} for t in tags_nodes if t.text]

            # 3. 標題（文字 + href）
            title_xpath = f'{base_xpath}/p[3]/a'
            title_nodes = tree.xpath(title_xpath)
            title_text = title_nodes[0].text.strip() if title_nodes else ''
            title_href = title_nodes[0].get('href') if title_nodes else ''
            full_href = f"https://www.ithome.com.tw{title_href}" if title_href else ''

            # 4. 副標（summary）
            summary_xpath = f'{base_xpath}/div/text()'
            summary_nodes = tree.xpath(summary_xpath)
            summary_text = summary_nodes[0].strip() if summary_nodes else ''

            # 5. 日期
            date_xpath = f'{base_xpath}/p[4]/text()'
            date_nodes = tree.xpath(date_xpath)
            date_text = date_nodes[0].strip() if date_nodes else ''

            # 整理成一筆新聞資料
            news_data.append({
                "headerType": "image",
                "headerContent": img_url,
                "tags": tags,
                "headline": title_text,
                "subheadline": summary_text,
                "date": date_text,
                "url": full_href
            })

        return jsonify(news_data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
