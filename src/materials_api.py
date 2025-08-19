from flask import Blueprint, jsonify
import os

# 建立 Blueprint
materials_bp = Blueprint("materials", __name__)

# 假設教材存放目錄在 backend/materials/
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
