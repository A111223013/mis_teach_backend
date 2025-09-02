from pymongo import MongoClient

# 連線到 MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["MIS_Teach"]

# 三個 collections
domains_col = db["domain"]
blocks_col = db["block"]
micro_col = db["micro_concept"]

# 1️⃣ 插入 domains
domain_data = {
    "name": "數位邏輯（Digital Logic）",
    "blocks": ["block_1", "block_2", "block_3", "block_4"]
}
domains_col.insert_one(domain_data)

# 2️⃣ 插入 blocks
blocks_data = [
    {
        "domain_id": "domain_1",
        "title": "Chapter 1 數位邏輯基本概念",
        "subtopics": ["micro_1", "micro_2", "micro_3", "micro_4"]
    },
    {
        "domain_id": "domain_1",
        "title": "Chapter 2 基本邏輯閘",
        "subtopics": ["micro_5", "micro_6", "micro_7", "micro_8"]
    },
    {
        "domain_id": "domain_1",
        "title": "Chapter 3 布林代數與第摩根定理",
        "subtopics": ["micro_9", "micro_10", "micro_11"]
    },
    {
        "domain_id": "domain_1",
        "title": "Chapter 4 布林代數化簡",
        "subtopics": ["micro_13", "micro_14"]
    }
]
blocks_col.insert_many(blocks_data)

# 3️⃣ 插入 micro_concepts
micro_data = [
    {"block_id": "block_1", "name": "數量表示法", "dependencies": []},
    {"block_id": "block_1", "name": "數位系統與類比系統", "dependencies": []},
    {"block_id": "block_1", "name": "邏輯準位與二進位表示法", "dependencies": []},
    {"block_id": "block_1", "name": "數位積體電路與 PLD 簡介", "dependencies": []},
    {"block_id": "block_2", "name": "基本邏輯關係與布林代數", "dependencies": []},
    {"block_id": "block_2", "name": "或閘、及閘與反閘", "dependencies": ["micro_5"]},
    {"block_id": "block_2", "name": "反或閘與反及閘", "dependencies": ["micro_5"]},
    {"block_id": "block_2", "name": "互斥或閘與互斥反或閘", "dependencies": ["micro_5"]},
    {"block_id": "block_3", "name": "布林代數特質", "dependencies": []},
    {"block_id": "block_3", "name": "單變數定理", "dependencies": ["micro_9"]},
    {"block_id": "block_3", "name": "多變數定理與第摩根定理（合併）", "dependencies": ["micro_9"]},
    {"block_id": "block_4", "name": "布林代數式簡化法", "dependencies": ["micro_10"]},
    {"block_id": "block_4", "name": "卡諾圖與組合邏輯設計步驟（合併）", "dependencies": ["micro_10"]}
]
micro_col.insert_many(micro_data)

print("✅ 資料已成功插入 MongoDB")
