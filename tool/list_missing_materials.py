import os
from typing import Dict, Set, List
from urllib.parse import urlparse

from pymongo import MongoClient
"""
看目前缺少了什麼md 課程檔案
"""

def get_db_from_env():
    """直接從環境或預設值建立 Mongo 連線，不依賴 config.py。

    環境變數：
      - MONGO_URI：例如 mongodb://localhost:27017/MIS_Teach
      - MONGO_DB_NAME：若 URI 無 DB 名稱時使用
    預設：mongodb://localhost:27017/MIS_Teach
    """
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/MIS_Teach")
    db_name_hint = os.getenv("MONGO_DB_NAME", "MIS_Teach")

    parsed = urlparse(mongo_uri)
    uri_db_name = parsed.path[1:] if parsed.path.startswith("/") else ""

    client = MongoClient(mongo_uri)
    db_name = uri_db_name or db_name_hint
    return client[db_name]


def materials_directory() -> str:
    """取得 data/materials 目錄（以專案根目錄為基準）。"""
    # 當前檔案位於 backend/tool/，往上一層是 backend/
    backend_root = os.path.dirname(os.path.abspath(__file__))
    backend_root = os.path.dirname(backend_root)
    materials_dir = os.path.join(backend_root, "data", "materials")
    os.makedirs(materials_dir, exist_ok=True)
    return materials_dir


def expected_filenames_from_db(db) -> Dict[str, Set[str]]:
    categories: Dict[str, Set[str]] = {
        "domains": set(),
        "blocks": set(),
        "micro_concepts": set(),
        "key_points": set(),
    }

    # domains -> name
    try:
        for doc in db.domain.find({}, {"name": 1}):
            name = (doc.get("name") or "").strip()
            if name:
                categories["domains"].add(f"{name}.md")
    except Exception:
        pass

    # blocks -> title
    try:
        for doc in db.block.find({}, {"title": 1}):
            title = (doc.get("title") or "").strip()
            if title:
                categories["blocks"].add(f"{title}.md")
    except Exception:
        pass

    # micro_concept -> name
    try:
        for doc in db.micro_concept.find({}, {"name": 1}):
            name = (doc.get("name") or "").strip()
            if name:
                categories["micro_concepts"].add(f"{name}.md")
    except Exception:
        pass

    # exam.key_points / key-points
    kp_all: List[str] = []
    try:
        kp_all.extend(db.exam.distinct("key_points") or [])
    except Exception:
        pass
    try:
        kp_all.extend(db.exam.distinct("key-points") or [])
    except Exception:
        pass

    for kp in kp_all:
        if isinstance(kp, list):
            for item in kp:
                text = (str(item) or "").strip()
                if text:
                    categories["key_points"].add(f"{text}.md")
        else:
            text = (str(kp) or "").strip()
            if text:
                categories["key_points"].add(f"{text}.md")

    return categories


def list_existing_material_files(materials_dir: str) -> Set[str]:
    try:
        return {f for f in os.listdir(materials_dir) if f.lower().endswith(".md")}
    except FileNotFoundError:
        return set()


def main() -> None:
    db = get_db_from_env()
    materials_dir = materials_directory()

    expected = expected_filenames_from_db(db)
    existing = list_existing_material_files(materials_dir)

    print("=== 資料夾 ===")
    print(materials_dir)
    print()

    print("=== 缺少的檔案（依分類）===")
    total_missing = 0
    for category in ["domains", "blocks", "micro_concepts", "key_points"]:
        want = expected.get(category, set())
        miss = sorted(name for name in want if name not in existing)
        total_missing += len(miss)
        print(f"[{category}] 缺少 {len(miss)} 個：")
        for name in miss:
            print(f"  - {name}")
        print()

    print(f"=== 總缺少檔案數：{total_missing} ===")


if __name__ == "__main__":
    main()


