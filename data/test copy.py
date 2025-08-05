import json
from difflib import get_close_matches

# 你的12個有效知識點
VALID_KEY_POINTS = [
    "基本計概",
    "數位邏輯",
    "作業系統",
    "程式語言",
    "資料結構",
    "網路",
    "資料庫",
    "AI與機器學習",
    "資訊安全",
    "雲端與虛擬化",
    "MIS",
    "軟體工程與系統開發"
]

# 對照表 (錯誤知識點 → 正確)

MAPPING_TABLE = {
    "編譯原理": "程式語言",
    "離散數學": "數位邏輯",
    "物件導向程式設計 (OOP)": "程式語言",
    "物件導向": "程式語言",
    "物件導向程式語言、程式語言分類": "程式語言",
    "線性代數": "數位邏輯",
    "線性代數, 正交矩陣, 向量範數, 矩陣運算": "數位邏輯",
    "線性代數, 矩陣運算, 對稱矩陣, 轉置矩陣": "數位邏輯",
    "計算機組織/結構": "數位邏輯",
    "計算機組織與結構": "數位邏輯",
    "計算機組織 — Cache 記憶體失誤類型": "數位邏輯",
    "計算機組織, 快取記憶體": "數位邏輯",
    "計算機組織與架構、pipeline hazard 分析": "數位邏輯",
    "電路學": "數位邏輯",
    "類比電路": "數位邏輯",
    "演算法": "資料結構",
    "演算法與計算複雜性理論": "資料結構",
    "演算法設計與分析": "資料結構",
    "演算法複雜度,子集和問題,NP-完全問題": "資料結構",
    "電子商務": "MIS",
    "電子商務, 資訊安全": ["MIS", "資訊安全"],
    "區塊鏈": "MIS",
    "分散式系統": "MIS",
    "數制轉換": "數位邏輯",
    "計算機架構": "數位邏輯",
    "計算機結構": "數位邏輯",
    "計算機組成原理": "數位邏輯",
    "資料庫系統概念": "資料庫",
    "資訊科技應用、智慧製造": "MIS",
    "RFID 應用領域, 資訊科技基礎": "MIS",
    "內容管理系統, 圖書資訊學, 整合圖書館系統, 數位典藏庫": "MIS",
    "命題邏輯、恆真式、真值表、邏輯推理": "數位邏輯",
    "基本計算機概論, 儲存單位轉換": "基本計概",
    "數值方法": "數位邏輯",
    "數值最佳化": "數位邏輯",
    "機率統計": "數位邏輯",
    "機率與統計": "數位邏輯",
    "微積分, 無窮級數, 交錯級數, 調和級數": "數位邏輯",
    "微積分, 無窮級數, 調和級數": "數位邏輯",
    "數位簽章、非對稱加密、PKI、公鑰與私鑰的用途": "資訊安全",
    "數位邏輯電路分析、基本邏輯閘組合": "數位邏輯",
    "文法推導、語法樹繪製、形式語言與自動機": "程式語言",
    "機率與統計, 動差生成函數, 二項分佈, 伯努利分佈": "數位邏輯",
    "檔案系統, 作業系統, Linux/Windows 系統知識": "作業系統",
    "程式編譯, 連結, 執行": "程式語言",
    "程式設計, 迴圈, do-while, break": "程式語言",
    "程式設計, 陣列, 迴圈, C語言": "程式語言",
    "程式語言, C語言, 字串處理, 指標": "程式語言",
    "程式語言, Java, 流程控制, 賦值運算符, 邏輯運算符, 條件判斷": "程式語言",
    "程式語言, Java, 浮點數型別, 型別轉換": "程式語言",
    "程式語言, Java, 運算子, 遞增遞減運算子": "程式語言",
    "程式語言, 指標, 陣列": "程式語言",
    "程式語言, 物件導向": "程式語言",
    "程式語言, 編譯錯誤, Java語法": "程式語言",
    "程式語言, 遞迴, 函數計算": "程式語言",
    "程式語言, 遞迴, 費氏數列": "程式語言",
    "程式語言、物件導向觀念": "程式語言",
    "程式語言、資料類型、類型轉換": "程式語言",
    "網路, HTTP 協定": "網路",
    "網路, IP位址轉換, NAT, DNS": "網路",
    "網路, 網頁伺服器, 資料庫": ["網路", "資料庫"],
    "網路, 通訊協定, 傳輸效率": "網路",
    "網路標準, IEEE 802.11, WLAN": "網路",
    "網路通訊協定, 作業系統, 網路": ["網路", "作業系統"],
    "虛擬記憶體, 主記憶體管理, 作業系統": "作業系統",
    "計算機硬體, 儲存裝置, 硬碟規格": "數位邏輯",
    "計算機硬體基本概念、容量單位趨勢": "數位邏輯",
    "資料庫, 關聯式代數, SELECT, PROJECT": "資料庫",
    "資料庫, 關聯式資料庫, 主鍵, 外鍵, 關係模型": "資料庫",
    "資料結構, 中序轉後序, 運算子堆疊": "資料結構",
    "資料結構, 二元搜尋樹, 後序遍歷": "資料結構",
    "資料結構, 二元樹, 後序走訪": "資料結構",
    "資料結構, 堆疊, LIFO": "資料結構",
    "資料結構, 指標, 二元樹建構": "資料結構",
    "資料結構, 最小堆, 二元搜尋樹": "資料結構",
    "資料結構, 最小堆積, 樹": "資料結構",
    "資料結構, 棧, 單向鏈表, 時間複雜度": "資料結構",
    "資料結構, 樹": "資料結構",
    "資料結構, 樹, 節點, 邊": "資料結構",
    "資訊安全, AES, 對稱式加密, 混淆, 擴散, 替換, 重置": "資訊安全",
    "資訊安全, 資料庫安全, SQL Injection, 預處理語句, 輸入驗證, 最小權限原則": "資訊安全",
    "資訊安全, 防火牆, 電腦病毒, 駭客入侵": "資訊安全",
    "資訊安全、DDoS、botnet": "資訊安全",
    "資訊安全、加密技術、機密性": "資訊安全",
    "軟體工程與系統開發, MIS": ["軟體工程與系統開發", "MIS"],
    "進位制轉換, 方程式解法, 數位合法性": "數位邏輯",
    "靜態與動態型別語言、型別檢查時機": "程式語言",
    "光碟儲存容量, 硬體常識": "數位邏輯"
}

def normalize_keypoints(raw_keypoints):
    if isinstance(raw_keypoints, list):
        return [kp.strip() for kp in raw_keypoints if isinstance(kp, str) and kp.strip()]
    elif isinstance(raw_keypoints, str):
        kp = raw_keypoints.strip()
        return [kp] if kp else []
    else:
        return []

def find_closest_key(original_list):
    combined = "、".join(original_list)
    match = get_close_matches(combined, VALID_KEY_POINTS, n=1, cutoff=0.4)
    if match:
        return match[0]
    else:
        return "基本計概"

def clean_key_points(raw_keypoints):
    raw_keypoints = normalize_keypoints(raw_keypoints)
    if not raw_keypoints:
        return []

    result = []
    unmapped = []

    for kp in raw_keypoints:
        if kp in VALID_KEY_POINTS:
            result.append(kp)
        elif kp in MAPPING_TABLE:
            mapped = MAPPING_TABLE[kp]
            if isinstance(mapped, list):
                result.extend(mapped)
            else:
                result.append(mapped)
        else:
            unmapped.append(kp)
            print(f"[警告] 無法對應的 key-point: {kp}")

    if not result:
        fallback = find_closest_key(raw_keypoints)
        print(f"[補齊] 原本是 {raw_keypoints} → 設為 {fallback}")
        result = [fallback]

    return sorted(set(result))

# 讀檔
with open('./error_questions.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for item in data:
    if item.get("type") == "group":
        # 處理 group 裡每個子題的 key-points
        subs = item.get("sub_questions", [])
        for sub_q in subs:
            raw_kp = sub_q.get("key-points", [])
            sub_q['key-points'] = clean_key_points(raw_kp)
    else:
        # 一般題直接處理外層 key-points
        raw_kp = item.get("key-points", [])
        item['key-points'] = clean_key_points(raw_kp)

# 輸出結果
with open('./error_questions.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("處理完成，結果已儲存到 output.json")
