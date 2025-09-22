import os
import re
import sys
import argparse
from typing import List, Optional, Iterable, Dict, Set, Tuple
from urllib.parse import urlparse

from pymongo import MongoClient
from concurrent.futures import ThreadPoolExecutor, as_completed

# 對齊 web_ai_assistant 的作法：加入專案根目錄到 sys.path，改用 tool/api_keys 取得金鑰
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_ROOT = os.path.dirname(CURRENT_DIR)
if BACKEND_ROOT not in sys.path:
    sys.path.append(BACKEND_ROOT)
try:
    from tool.api_keys import get_api_key  # type: ignore
except Exception:
    get_api_key = None  # 後備使用環境變數


def get_mongo_db():
    """從環境變數建立 Mongo 連線，不依賴 config.py。

    環境變數：
      - MONGO_URI（預設 mongodb://localhost:27017/MIS_Teach）
      - MONGO_DB_NAME（當 URI 無 DB 名稱時使用，預設 MIS_Teach）
    """
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/MIS_Teach")
    db_name_hint = os.getenv("MONGO_DB_NAME", "MIS_Teach")
    parsed = urlparse(mongo_uri)
    uri_db_name = parsed.path[1:] if parsed.path.startswith("/") else ""
    client = MongoClient(mongo_uri)
    db_name = uri_db_name or db_name_hint
    return client[db_name]


def materials_directory() -> str:
    """取得 data/materials 目錄（以後端根目錄為基準）。"""
    backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    materials_dir = os.path.join(backend_root, "data", "materials")
    os.makedirs(materials_dir, exist_ok=True)
    return materials_dir


def sanitize_filename(name: str) -> str:
    """保留原始中文名稱作為檔名，移除不適合作為檔名的字元。"""
    safe = re.sub(r"[\\/:*?\"<>|]", "_", name).strip()
    if not safe:
        safe = "untitled"
    return f"{safe}.md"


def normalize_topic_input(raw: str) -> str:
    """將使用者提供的主題清單標準化：
    - 去除開頭的條列符號（如 '-', '•' 等）
    - 去除前後空白
    - 去除結尾的 .md 副檔名
    """
    s = (raw or "").strip()
    s = re.sub(r"^[\-•\s]+", "", s)
    if s.lower().endswith(".md"):
        s = s[:-3]
    return s.strip()


def expected_filenames_from_db(db) -> Dict[str, Set[str]]:
    """讀取 DB 項目並轉換成期望的檔名集合（含 .md）。"""
    categories: Dict[str, Set[str]] = {
        "domains": set(),
        "blocks": set(),
        "micro_concepts": set(),
        "key_points": set(),
    }

    try:
        for doc in db.domain.find({}, {"name": 1}):
            name = (doc.get("name") or "").strip()
            if name:
                categories["domains"].add(f"{name}.md")
    except Exception:
        pass

    try:
        for doc in db.block.find({}, {"title": 1}):
            title = (doc.get("title") or "").strip()
            if title:
                categories["blocks"].add(f"{title}.md")
    except Exception:
        pass

    try:
        for doc in db.micro_concept.find({}, {"name": 1}):
            name = (doc.get("name") or "").strip()
            if name:
                categories["micro_concepts"].add(f"{name}.md")
    except Exception:
        pass

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


def compute_missing_topics_from_db() -> List[str]:
    """計算目前 data/materials 缺少的主題（轉為主題名稱，不含 .md）。"""
    db = get_mongo_db()
    materials_dir = materials_directory()
    expected = expected_filenames_from_db(db)
    existing = list_existing_material_files(materials_dir)

    missing_topics: List[str] = []
    # 順序：micro_concepts -> blocks -> domains -> key_points（較符合教材粒度）
    order = ["micro_concepts", "blocks", "domains", "key_points"]
    for cat in order:
        for filename in sorted(expected.get(cat, set())):
            if filename not in existing:
                # 還原主題名稱（去除 .md）
                missing_topics.append(filename[:-3])
    return missing_topics


STYLE_GUIDE = (
    "你是一位教材編寫專家，請依照以下風格產出完整、可直接上線的 Markdown：\n"
    "- 使用清晰的小節標題與層級（####、### 依內容深度）。\n"
    "- 合理插入分隔線（-----）分隔大段。\n"
    "- 每個概念提供：定義/核心觀念、例子或推導、與相鄰概念的關聯。\n"
    "- 至少加入 1~2 個『小練習（附詳解）』，步驟分條列。\n"
    "- 若適合，加入『常見錯誤與澄清』與『延伸閱讀』。\n"
    "- 內容語言使用繁體中文；數學表達可用 LaTeX。\n"
    "- 嚴格輸出為純 Markdown，不要加入任何多餘前後綴或解說。\n"
)


def build_prompt(topic: str) -> str:
    return (
        f"主題：{topic}\n\n" \
        f"請參考此風格與結構生成教材：\n{STYLE_GUIDE}\n\n" \
        "章節建議結構（可依主題調整）：\n"
        "1) 核心概念/定義\n"
        "2) 典型例子與轉換/推導\n"
        "3) 與相鄰概念的關聯\n"
        "4) 進階內容（若適合）\n"
        "5) 常見錯誤與澄清\n"
        "6) 小練習（附詳解）\n"
        "7) 延伸閱讀/參考\n"
    )


def get_gemini_model(model_name: str = "gemini-2.5-flash"):
    try:
        import google.generativeai as genai  # 動態載入
    except Exception as e:
        raise RuntimeError("未安裝 google-generativeai，請先 pip install google-generativeai") from e

    api_key = None
    if get_api_key is not None:
        try:
            api_key = get_api_key()
        except Exception:
            api_key = None
    if not api_key:
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GENAI_API_KEY")
    if not api_key:
        raise RuntimeError("找不到 Gemini API 金鑰，請於 tool/api_keys.py 設定或以環境變數 GOOGLE_API_KEY 提供。")

    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model_name)


def generate_markdown(model, topic: str) -> str:
    prompt = build_prompt(topic)
    response = model.generate_content(prompt)
    text = getattr(response, "text", None) or getattr(response, "candidates", None)
    if hasattr(response, "text"):
        return response.text
    # 若回傳非標準結構，嘗試最簡保險轉字串
    return str(response)


def topics_from_db(mongo_collections: Iterable[str] = ("domain", "block", "micro_concept"), include_key_points: bool = False) -> List[str]:
    db = get_mongo_db()
    result: List[str] = []

    if "domain" in mongo_collections:
        for doc in db.domain.find({}, {"name": 1}):
            name = (doc.get("name") or "").strip()
            if name:
                result.append(name)

    if "block" in mongo_collections:
        for doc in db.block.find({}, {"title": 1}):
            title = (doc.get("title") or "").strip()
            if title:
                result.append(title)

    if "micro_concept" in mongo_collections:
        for doc in db.micro_concept.find({}, {"name": 1}):
            name = (doc.get("name") or "").strip()
            if name:
                result.append(name)

    if include_key_points:
        seen: Set[str] = set()
        try:
            for kp in db.exam.distinct("key_points") or []:
                if isinstance(kp, list):
                    for x in kp:
                        v = (str(x) or "").strip()
                        if v and v not in seen:
                            seen.add(v)
                            result.append(v)
                else:
                    v = (str(kp) or "").strip()
                    if v and v not in seen:
                        seen.add(v)
                        result.append(v)
        except Exception:
            pass
        try:
            for kp in db.exam.distinct("key-points") or []:
                if isinstance(kp, list):
                    for x in kp:
                        v = (str(x) or "").strip()
                        if v and v not in seen:
                            seen.add(v)
                            result.append(v)
                else:
                    v = (str(kp) or "").strip()
                    if v and v not in seen:
                        seen.add(v)
                        result.append(v)
        except Exception:
            pass

    return result


def write_markdown(out_dir: str, topic: str, content: str, overwrite: bool) -> str:
    filename = sanitize_filename(topic)
    path = os.path.join(out_dir, filename)
    if not overwrite and os.path.exists(path):
        return path
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def main():
    parser = argparse.ArgumentParser(description="使用 Gemini 依教材風格自動生成 Markdown 教材檔案")
    parser.add_argument("--topic", action="append", help="指定要產生的主題，可重複指定多次。")
    parser.add_argument("--topic-file", help="從文字檔讀取主題（每行一個；可含 .md 或條列符號）。")
    parser.add_argument("--from-db", action="store_true", help="從 MongoDB 讀取 domain/block/micro_concept 名稱作為主題。")
    parser.add_argument("--include-keypoints", action="store_true", help="從 exam 的 key_points/key-points 也納入主題。")
    parser.add_argument("--out-dir", default=materials_directory(), help="輸出資料夾，預設為 data/materials。")
    parser.add_argument("--overwrite", action="store_true", help="若檔案已存在則覆寫。")
    parser.add_argument("--dry-run", action="store_true", help="僅列出將要產生的主題與檔案，不實際呼叫 Gemini 與寫檔。")
    parser.add_argument("--model", default="gemini-2.5-flash", help="Gemini 模型名稱。")
    parser.add_argument("--workers", type=int, default=16, help="平行產生的執行緒數（預設 16）。")
    args = parser.parse_args()

    out_dir = args.out_dir
    os.makedirs(out_dir, exist_ok=True)

    topics: List[str] = []
    default_mode = False
    # 若未提供任何輸入來源，啟用預設清單（內建）且自動補齊 DB 缺少主題
    if not any([args.topic, args.topic_file, args.from_db]):
        default_mode = True
        builtin_topics = [
            "電腦網路"
        ]
        topics.extend([normalize_topic_input(t) for t in builtin_topics])
        # 追加：自動從資料庫計算目前缺少的主題
        try:
            missing_from_db = compute_missing_topics_from_db()
            topics.extend(missing_from_db)
        except Exception:
            # 若資料庫不可用，略過此步
            pass
    if args.topic:
        topics.extend([normalize_topic_input(t) for t in args.topic if t and t.strip()])
    if args.topic_file and os.path.exists(args.topic_file):
        with open(args.topic_file, "r", encoding="utf-8") as f:
            for line in f:
                norm = normalize_topic_input(line)
                if norm:
                    topics.append(norm)
    if args.from_db:
        topics.extend(topics_from_db(include_key_points=args.include_keypoints))

    # 去重並維持相對順序
    seen: Set[str] = set()
    ordered_topics: List[str] = []
    for t in topics:
        tt = t.strip()
        if tt and tt not in seen:
            seen.add(tt)
            ordered_topics.append(tt)

    if not ordered_topics:
        print("未指定主題，請使用 --topic 或 --from-db。")
        return

    # 預設模式顯示概要，但直接執行產檔（非 dry-run）
    if args.dry_run:
        print("[DryRun] 將產生以下主題：")
        for t in ordered_topics:
            print(f"- {t} -> {sanitize_filename(t)}")
        print(f"輸出目錄：{out_dir}")
        print(f"工作執行緒：{args.workers}")
        return

    model = get_gemini_model(args.model)

    def worker(topic: str) -> Tuple[str, Optional[str], Optional[str]]:
        try:
            md = generate_markdown(model, topic)
            overwrite_flag = True if default_mode else args.overwrite
            path = write_markdown(out_dir, topic, md, overwrite_flag)
            return (topic, path, None)
        except Exception as e:
            return (topic, None, str(e))

    workers = max(1, int(args.workers or 16)) if not default_mode else 16
    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_map = {executor.submit(worker, t): t for t in ordered_topics}
        for fut in as_completed(future_map):
            topic = future_map[fut]
            try:
                t, path, err = fut.result()
                if err:
                    print(f"❌ 產生失敗：{t}，原因：{err}")
                else:
                    print(f"✅ 已產生：{t} -> {path}")
            except Exception as e:
                print(f"❌ 產生失敗：{topic}，原因：{e}")


if __name__ == "__main__":
    main()


