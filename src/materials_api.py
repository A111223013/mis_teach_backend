from flask import Blueprint, jsonify
import os
from accessories import mongo
import markdown
from flask import Response
from bs4 import BeautifulSoup

# 建立 Blueprint
materials_bp = Blueprint("materials", __name__)

# 教材存放目錄在 backend/materials/
BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # backend/
MATERIALS_DIR = os.path.join(BASE_DIR, "data", "materials")

# 確保資料夾存在
os.makedirs(MATERIALS_DIR, exist_ok=True)



@materials_bp.route("/<filename>", methods=["GET"])
def get_material(filename):
    # ✅ 自動補上 .md（如果沒有副檔名）
    if not filename.lower().endswith(".md"):
        filename += ".md"

    filepath = os.path.join(MATERIALS_DIR, filename)

    if not os.path.exists(filepath):
        return jsonify({"error": "File not found"}), 404

    # 讀取 Markdown
    with open(filepath, "r", encoding="utf-8") as f:
        md_content = f.read()

    # Markdown -> HTML
    html_content = markdown.markdown(
        md_content,
        extensions=['fenced_code', 'tables', 'attr_list']
    )

    # 完整 HTML
    full_page = f"""
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>{filename}</title>

        <!-- Bootstrap -->
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">

        <!-- KaTeX -->
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.css">
        <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.js"></script>
        <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/contrib/auto-render.min.js"></script>

        <!-- Highlight.js -->
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/highlight.js@11.9.0/styles/github.min.css">
        <script src="https://cdn.jsdelivr.net/npm/highlight.js@11.9.0/lib/highlight.min.js"></script>
        <!-- 可選語言包，例如 Python、JavaScript -->
        <script src="https://cdn.jsdelivr.net/npm/highlight.js@11.9.0/lib/languages/python.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/highlight.js@11.9.0/lib/languages/javascript.min.js"></script>

        <style>
            body {{ margin:0; padding:0; }}
            .container {{ display:flex; height:100vh; }}
            .toc {{ width:300px; overflow-y:auto; border-right:1px solid #ddd; padding:20px; background:#f8f9fa; }}
            .content {{ flex:1; overflow-y:auto; padding:20px; }}
            .toc a {{ display:block; margin-bottom:5px; text-decoration:none; color:#000; }}
            .toc a:hover {{ text-decoration:underline; }}
            h1,h2,h3,h4,h5,h6 {{ scroll-margin-top:80px; }}
            pre {{ background-color:#e9ecef; padding:10px; border-radius:5px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="toc">
                <h5>目錄</h5>
                <div id="toc-list"></div>
            </div>
            <div class="content" id="content">
                {html_content}
            </div>
        </div>

        <script>
        document.addEventListener("DOMContentLoaded", function() {{
            // 自動生成目錄
            const content = document.getElementById("content");
            const tocList = document.getElementById("toc-list");
            const headers = content.querySelectorAll("h1,h2,h3,h4,h5,h6");

            headers.forEach(header => {{
                if (!header.id) {{
                    header.id = header.textContent.replace(/\\s+/g,"_");
                }}
                const a = document.createElement("a");
                a.href = "#" + header.id;
                a.textContent = header.textContent;
                tocList.appendChild(a);
            }});

            // KaTeX 自動渲染數學式
            renderMathInElement(document.body, {{
                delimiters: [
                    {{left: "$$", right: "$$", display: true}},
                    {{left: "$", right: "$", display: false}},
                    {{left: "\\\\(", right: "\\\\)", display: false}},
                    {{left: "\\\\[", right: "\\\\]", display: true}}
                ],
                throwOnError: false
            }});

            // Highlight.js 語法高亮
            hljs.highlightAll();
        }});
        </script>
    </body>
    </html>
    """
    return Response(full_page, mimetype="text/html")


@materials_bp.route("/key_points", methods=["GET"])
def get_key_points():
    """
    從 mongodb exam 集合中抓取所有 key_points，去重後回傳
    """
    exams = mongo.db.exam.find({}, {"key_points": 1})
    key_points_set = set()
    for exam in exams:
        key_points = exam.get("key_points", [])
        if isinstance(key_points, list):
            for kp in key_points:
                key_points_set.add(kp)
        elif isinstance(key_points, str):
            key_points_set.add(key_points)
    return jsonify({"key_points": list(key_points_set)})

@materials_bp.route('/domain', methods=['GET'])
def get_domains():
    try:
        domains = list(mongo.db.domain.find())
        if not domains:
            return jsonify({"error": "No domain collection or data found"}), 404

        for d in domains:
            d['_id'] = str(d['_id'])
            # 將 blocks 內的 ObjectId 都轉成字串
            if 'blocks' in d and d['blocks']:
                d['blocks'] = [str(b) for b in d['blocks']]
            else:
                d['blocks'] = []

        return jsonify(domains)
    except Exception as e:
        return jsonify({"error": f"Exception: {str(e)}"}), 500


@materials_bp.route('/block', methods=['GET'])
def get_blocks():
    try:
        blocks = list(mongo.db.block.find())
        if not blocks:
            return jsonify({"error": "No block collection or data found"}), 404

        for b in blocks:
            b['_id'] = str(b['_id'])
            # 將 domain_id 轉成字串
            if 'domain_id' in b:
                b['domain_id'] = str(b['domain_id'])
            else:
                b['domain_id'] = None

        return jsonify(blocks)
    except Exception as e:
        return jsonify({"error": f"Exception: {str(e)}"}), 500


@materials_bp.route('/micro_concept', methods=['GET'])
def get_micro_concepts():
    try:
        micro_concepts = list(mongo.db.micro_concept.find())
        if not micro_concepts:
            return jsonify({"error": "No micro_concept collection or data found"}), 404

        # 將 _id、block_id、dependencies 都轉成字串
        for m in micro_concepts:
            m['_id'] = str(m['_id'])
            # 如果 block_id 是 ObjectId，轉成字串
            if isinstance(m.get('block_id'), dict) and '$oid' in m['block_id']:
                m['block_id'] = m['block_id']['$oid']
            else:
                m['block_id'] = str(m.get('block_id'))

            # dependencies 陣列也轉成字串
            if 'dependencies' in m and m['dependencies']:
                m['dependencies'] = [str(d) if isinstance(d, dict) and '$oid' in d else str(d) for d in m['dependencies']]
            else:
                m['dependencies'] = []

        return jsonify(micro_concepts)
    except Exception as e:
        return jsonify({"error": f"Exception: {str(e)}"}), 500

