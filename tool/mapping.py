from pymongo import MongoClient

# 連接 MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["MIS_Teach"]   # 換成你的資料庫名稱
collection = db["exam"]   # 換成你的 collection 名稱

# 36→12 對照表
mapping = {
    "計算複雜度": "基本計概",
    "計算複雜度理論": "基本計概",
    "遞迴": "基本計概",
    "Subset Sum 問題": "基本計概",
    "停止問題": "基本計概",
    "圖靈機": "基本計概",
    "可計算性": "基本計概",
    "NP-complete": "基本計概",
    "計算理論": "基本計概",

    "數位邏輯": "數位邏輯",
    "布林代數": "數位邏輯",
    "數制轉換": "數位邏輯",
    "補數": "數位邏輯",
    "CPU架構": "數位邏輯",
    "電腦架構": "數位邏輯",

    "作業系統": "作業系統",
    "CPU排程": "作業系統",
    "記憶體階層": "作業系統",
    "遠端登入": "作業系統",  # 主要放在 OS

    "程式語言": "程式語言",
    "演算法": "程式語言",   # 預設放程式語言

    "資料結構": "資料結構",

    "網路": "網路",
    "網路協定": "網路",
    "網頁開發": "網路",

    "資料庫": "資料庫",
    "數據分析": "資料庫",   # 預設放在資料庫
    "資料探勘": "資料庫",

    "AI與機器學習": "AI與機器學習",

    "資訊安全": "資訊安全",

    "雲端與虛擬化": "雲端與虛擬化",

    "MIS": "MIS",
    "系統分析與設計": "MIS",   # 預設放 MIS

    "軟體工程與系統開發": "軟體工程與系統開發",
    "物件導向": "軟體工程與系統開發"
    
}

# 更新 MongoDB 中的 key_points
for old, new in mapping.items():
    result = collection.update_many(
        {"key_points": old},
        {"$set": {"key_points": new}}
    )
    if result.modified_count > 0:
        print(f"✅ {old} → {new} （更新 {result.modified_count} 筆資料）")
