from pymongo import MongoClient

# 連線到 MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["MIS_Teach"]

# 三個 collections
domains_col = db["domain"]
blocks_col = db["block"]
micro_col = db["micro_concept"]

# 清空舊資料（避免重複）
domains_col.delete_many({})
blocks_col.delete_many({})
micro_col.delete_many({})

# 1️⃣ 插入 domain
domain_data = {
    "name": "數位邏輯（Digital Logic）",
    "blocks": []   # 先放空，待會補上 block 的 _id
}
domain_result = domains_col.insert_one(domain_data)
domain_id = domain_result.inserted_id

# 2️⃣ 插入 blocks（先不放 subtopics，之後用 micro 的 _id 補）
blocks_data = [
    {"domain_id": domain_id, "title": "Chapter 1 數位邏輯基本概念", "subtopics": []},
    {"domain_id": domain_id, "title": "Chapter 2 基本邏輯閘", "subtopics": []},
    {"domain_id": domain_id, "title": "Chapter 3 布林代數與第摩根定理", "subtopics": []},
    {"domain_id": domain_id, "title": "Chapter 4 布林代數化簡", "subtopics": []}
]
block_results = blocks_col.insert_many(blocks_data)
block_ids = block_results.inserted_ids

# 更新 domain.blocks
domains_col.update_one(
    {"_id": domain_id},
    {"$set": {"blocks": block_ids}}
)

# 3️⃣ 插入 micro concepts（先用 block_ids 對應）
micro_map = [
    (0, "數量表示法", []),
    (0, "數位系統與類比系統", []),
    (0, "邏輯準位與二進位表示法", []),
    (0, "數位積體電路與 PLD 簡介", []),
    (1, "基本邏輯關係與布林代數", []),
    (1, "或閘、及閘與反閘", []),
    (1, "反或閘與反及閘", []),
    (1, "互斥或閘與互斥反或閘", []),
    (2, "布林代數特質", []),
    (2, "單變數定理", []),
    (2, "多變數定理與第摩根定理（合併）", []),
    (3, "布林代數式簡化法", []),
    (3, "卡諾圖與組合邏輯設計步驟（合併）", [])
]

micro_docs = []
for block_idx, name, deps in micro_map:
    micro_docs.append({
        "block_id": block_ids[block_idx],
        "name": name,
        "dependencies": []  # 先放空，之後可以再用 micro 的 _id 更新
    })

micro_results = micro_col.insert_many(micro_docs)
micro_ids = micro_results.inserted_ids

# 4️⃣ 把 micro ids 塞回對應的 block.subtopics
for i, (block_idx, name, deps) in enumerate(micro_map):
    blocks_col.update_one(
        {"_id": block_ids[block_idx]},
        {"$push": {"subtopics": micro_ids[i]}}
    )

print("✅ 資料已成功改成用 ObjectId 關聯")
