from flask import Blueprint, jsonify
import os
from accessories import mongo

# 建立 Blueprint
materials_bp = Blueprint("materials", __name__)

# 教材存放目錄在 backend/materials/
BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # backend/
MATERIALS_DIR = os.path.join(BASE_DIR, "data", "materials")

# 確保資料夾存在
os.makedirs(MATERIALS_DIR, exist_ok=True)

@materials_bp.route("/list", methods=["GET"])
def list_materials():
    """
    列出所有教材檔名（只抓 .md）
    """
    files = [f for f in os.listdir(MATERIALS_DIR) if f.endswith(".md")]
    return jsonify({"files": files})


@materials_bp.route("/<filename>", methods=["GET"])
def get_material(filename):
    """
    讀取單一教材的內容並回傳
    """
    filepath = os.path.join(MATERIALS_DIR, filename)

    if not os.path.exists(filepath):
        return jsonify({"error": "File not found"}), 404

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    return jsonify({
        "filename": filename,
        "content": content
    })

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
        domain = list(mongo.db.domain.find())
        if not domain:
            return jsonify({"error": "No domain collection or data found"}), 404
        for d in domain:
            d['_id'] = str(d['_id'])  # ObjectId 轉字串
        return jsonify(domain)
    except Exception as e:
        return jsonify({"error": f"Exception: {str(e)}"}), 500

@materials_bp.route('/block', methods=['GET'])
def get_blocks():
    try:
        block = list(mongo.db.block.find())
        if not block:
            return jsonify({"error": "No block collection or data found"}), 404
        for b in block:
            b['_id'] = str(b['_id'])
        return jsonify(block)
    except Exception as e:
        return jsonify({"error": f"Exception: {str(e)}"}), 500

@materials_bp.route('/micro_concept', methods=['GET'])
def get_micro_concepts():
    try:
        micro_concept = list(mongo.db.micro_concept.find())
        if not micro_concept:
            return jsonify({"error": "No micro_concept collection or data found"}), 404
        for m in micro_concept:
            m['_id'] = str(m['_id'])
        return jsonify(micro_concept)
    except Exception as e:
        return jsonify({"error": f"Exception: {str(e)}"}), 500
