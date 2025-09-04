from pymongo import MongoClient
from bson import ObjectId

def initialize_mis_teach_db(uri="mongodb://localhost:27017/", db_name="MIS_Teach"):
    try:
        # 連線到 MongoDB
        client = MongoClient(uri)
        db = client[db_name]

        # 三個 collections
        domains_col = db["domain"]
        blocks_col = db["block"]
        micro_col = db["micro_concept"]

        # 清空舊資料
        domains_col.delete_many({})
        blocks_col.delete_many({})
        micro_col.delete_many({})

        # Domain 資料
        domain_name = "數位邏輯（Digital Logic）"
        domain_data = {
            "name": domain_name,
            "description": "介紹數位邏輯的基本概念與應用",
            "blocks": []
        }
        domain_id = domains_col.insert_one(domain_data).inserted_id

        # Block 資料
        block_titles = [
            "Chapter 1 數位邏輯基本概念",
            "Chapter 2 基本邏輯閘",
            "Chapter 3 布林代數與第摩根定理",
            "Chapter 4 布林代數化簡"
        ]
        block_docs = [{"domain_id": domain_id, "title": title, "subtopics": []} for title in block_titles]
        block_ids = blocks_col.insert_many(block_docs).inserted_ids

        # 更新 domain.blocks
        domains_col.update_one({"_id": domain_id}, {"$set": {"blocks": block_ids}})

        # Micro Concept 資料
        micro_map = [
            (0, "數量表示法"),
            (0, "數位系統與類比系統"),
            (0, "邏輯準位與二進位表示法"),
            (0, "數位積體電路與 PLD 簡介"),
            (1, "基本邏輯關係與布林代數"),
            (1, "或閘、及閘與反閘"),
            (1, "反或閘與反及閘"),
            (1, "互斥或閘與互斥反或閘"),
            (2, "布林代數特質"),
            (2, "單變數定理"),
            (2, "多變數定理與第摩根定理（合併）"),
            (3, "布林代數式簡化法"),
            (3, "卡諾圖與組合邏輯設計步驟（合併）")
        ]

        micro_docs = []
        for block_idx, name in micro_map:
            micro_docs.append({
                "block_id": block_ids[block_idx],
                "name": name,
                "dependencies": []  # 可日後補上依賴關係
            })
        micro_ids = micro_col.insert_many(micro_docs).inserted_ids

        # 更新 block.subtopics
        for i, (block_idx, _) in enumerate(micro_map):
            blocks_col.update_one(
                {"_id": block_ids[block_idx]},
                {"$push": {"subtopics": micro_ids[i]}}
            )

        print("✅ 資料初始化成功，已建立 ObjectId 關聯")
        return {
            "domain_id": domain_id,
            "block_ids": block_ids,
            "micro_ids": micro_ids
        }

    except Exception as e:
        print(f"❌ 初始化失敗：{e}")
        return None