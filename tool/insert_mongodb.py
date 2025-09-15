from pymongo import MongoClient
from bson import ObjectId

def initialize_mis_teach_db(uri="mongodb://localhost:27017/", db_name="MIS_Teach"):
    """
    連線到 MongoDB，若尚未初始化則清空並插入教材資料
    """
    try:
        client = MongoClient(uri)
        db = client[db_name]

        domains_col = db["domain"]
        blocks_col = db["block"]
        micro_col = db["micro_concept"]

        # 預期數量
        expected_domains = 10
        expected_blocks = 55
        expected_micro = 126

        # 目前資料數量
        domain_count = domains_col.count_documents({})
        block_count = blocks_col.count_documents({})
        micro_count = micro_col.count_documents({})

        if (domain_count == expected_domains and
            block_count == expected_blocks and
            micro_count == expected_micro):
            print(f"⚠️ 教材資料已存在，跳過初始化")
            print(f"📊 現有資料：Domains={domain_count}, Blocks={block_count}, Micro Concepts={micro_count}")
            return db

        # 清空舊資料
        domains_col.delete_many({})
        blocks_col.delete_many({})
        micro_col.delete_many({})

        # 插入所有教材
        insert_dl_domain(db)
        insert_os_domain(db)
        insert_ds_domain(db)
        insert_cn_domain(db)
        insert_db_domain(db)
        insert_ai_domain(db)
        insert_sec_domain(db)
        insert_cloud_domain(db)
        insert_mis_domain(db)
        insert_se_domain(db)

        print("✅ 所有教材資料初始化完成")
        return db

    except Exception as e:
        print(f"❌ 初始化失敗：{e}")
        return None


def insert_dl_domain(db):
    """
    插入「數位邏輯（Digital Logic）」的 Domain、Blocks、Micro Concepts
    """
    try:
        # collections
        domains_col = db["domain"]
        blocks_col = db["block"]
        micro_col = db["micro_concept"]

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
            (2, "多變數定理與第摩根定理"),
            (3, "布林代數式簡化法"),
            (3, "卡諾圖與組合邏輯設計步驟")
        ]

        micro_docs = []
        for block_idx, name in micro_map:
            micro_docs.append({
                "block_id": block_ids[block_idx],
                "name": name,
                "dependencies": []
            })
        micro_ids = micro_col.insert_many(micro_docs).inserted_ids

        # 更新 block.subtopics
        for i, (block_idx, _) in enumerate(micro_map):
            blocks_col.update_one(
                {"_id": block_ids[block_idx]},
                {"$push": {"subtopics": micro_ids[i]}}
            )

        print("✅ 數位邏輯資料插入成功")
        return {
            "domain_id": domain_id,
            "block_ids": block_ids,
            "micro_ids": micro_ids
        }

    except Exception as e:
        print(f"❌ 插入數位邏輯失敗：{e}")
        return None


def insert_os_domain(db):
    """
    插入「作業系統（Operating System）」的 Domain、Blocks、Micro Concepts
    """
    try:
        domains_col = db["domain"]
        blocks_col = db["block"]
        micro_col = db["micro_concept"]

        # Domain
        domain_data = {
            "name": "作業系統（Operating System）",
            "description": "介紹作業系統的基本概念、行程管理、同步、記憶體與儲存管理",
            "blocks": []
        }
        domain_id = domains_col.insert_one(domain_data).inserted_id

        # Blocks
        block_titles = [
            "Chapter 1 作業系統基本概念",
            "Chapter 2 行程管理",
            "Chapter 3 行程同步",
            "Chapter 4 記憶體管理",
            "Chapter 5 儲存管理"
        ]
        block_docs = [{"domain_id": domain_id, "title": title, "subtopics": []} for title in block_titles]
        block_ids = blocks_col.insert_many(block_docs).inserted_ids
        domains_col.update_one({"_id": domain_id}, {"$set": {"blocks": block_ids}})

        # Micro Concepts
        micro_map = [
            (0, "概說"),
            (0, "作業系統結構"),
            (1, "行程觀念"),
            (1, "執行緒與並行性"),
            (1, "CPU 排班"),
            (2, "同步工具"),
            (2, "同步範例"),
            (2, "死結"),
            (3, "主記憶體"),
            (3, "虛擬記憶體"),
            (4, "大量儲存結構"),
            (4, "輸入/輸出系統")
        ]
        micro_ids = micro_col.insert_many(
            [{"block_id": block_ids[idx], "name": name, "dependencies": []} for idx, name in micro_map]
        ).inserted_ids

        # 更新 block.subtopics
        for i, (block_idx, _) in enumerate(micro_map):
            blocks_col.update_one({"_id": block_ids[block_idx]}, {"$push": {"subtopics": micro_ids[i]}})

        print("✅ 作業系統資料插入成功")
    except Exception as e:
        print(f"❌ 插入作業系統失敗：{e}")


def insert_ds_domain(db):
    """
    插入「資料結構（Data Structure）」的 Domain、Blocks、Micro Concepts
    """
    try:
        domains_col = db["domain"]
        blocks_col = db["block"]
        micro_col = db["micro_concept"]

        domain_data = {
            "name": "資料結構（Data Structure）",
            "description": "介紹資料結構與演算法的基本概念及應用",
            "blocks": []
        }
        domain_id = domains_col.insert_one(domain_data).inserted_id

        block_titles = [
            "Chapter 1 資料結構簡介",
            "Chapter 2 陣列",
            "Chapter 3 鏈結串列",
            "Chapter 4 佇列與堆疊",
            "Chapter 5 樹狀結構"
        ]
        block_docs = [{"domain_id": domain_id, "title": t, "subtopics": []} for t in block_titles]
        block_ids = blocks_col.insert_many(block_docs).inserted_ids
        domains_col.update_one({"_id": domain_id}, {"$set": {"blocks": block_ids}})

        micro_map = [
            (0, "資料結構定義"),
            (0, "資料結構對程式效率影響"),
            (0, "演算法定義"),
            (0, "程式效率分析"),
            (1, "一維陣列"),
            (1, "二維陣列"),
            (2, "單向鏈結串列"),
            (2, "雙向與環狀鏈結串列"),
            (3, "佇列"),
            (3, "堆疊"),
            (4, "二元樹與二元搜尋樹")
        ]
        micro_ids = micro_col.insert_many(
            [{"block_id": block_ids[idx], "name": name, "dependencies": []} for idx, name in micro_map]
        ).inserted_ids

        for i, (block_idx, _) in enumerate(micro_map):
            blocks_col.update_one({"_id": block_ids[block_idx]}, {"$push": {"subtopics": micro_ids[i]}})

        print("✅ 資料結構資料插入成功")
    except Exception as e:
        print(f"❌ 插入資料結構失敗：{e}")


def insert_cn_domain(db):
    """
    插入「電腦網路（Computer Network）」的 Domain、Blocks、Micro Concepts
    """
    try:
        domains_col = db["domain"]
        blocks_col = db["block"]
        micro_col = db["micro_concept"]

        domain_data = {
            "name": "電腦網路（Computer Network）",
            "description": "介紹電腦網路的基本概念、訊號、調變、區域網路與網際網路應用",
            "blocks": []
        }
        domain_id = domains_col.insert_one(domain_data).inserted_id

        block_titles = [
            "Chapter 1 概論",
            "Chapter 2 訊號調變與編碼",
            "Chapter 3 區域網路",
            "Chapter 4 區域網路之元件及連線",
            "Chapter 5 網際網路應用"
        ]
        block_docs = [{"domain_id": domain_id, "title": t, "subtopics": []} for t in block_titles]
        block_ids = blocks_col.insert_many(block_docs).inserted_ids
        domains_col.update_one({"_id": domain_id}, {"$set": {"blocks": block_ids}})

        micro_map = [
            (0, "簡介"),
            (0, "訊號"),
            (0, "訊號傳輸"),
            (1, "調變"),
            (1, "類比傳輸與數位傳輸"),
            (2, "區域網路拓樸方式"),
            (2, "區域網路開放架構"),
            (3, "區域網路元件"),
            (3, "區域網路連線實作"),
            (4, "TCP/IP 通訊協定")
        ]
        micro_ids = micro_col.insert_many(
            [{"block_id": block_ids[idx], "name": name, "dependencies": []} for idx, name in micro_map]
        ).inserted_ids

        for i, (block_idx, _) in enumerate(micro_map):
            blocks_col.update_one({"_id": block_ids[block_idx]}, {"$push": {"subtopics": micro_ids[i]}})

        print("✅ 電腦網路資料插入成功")
    except Exception as e:
        print(f"❌ 插入電腦網路失敗：{e}")


def insert_db_domain(db):
    """
    插入「資料庫（Database）」的 Domain、Blocks、Micro Concepts
    """
    try:
        domains_col = db["domain"]
        blocks_col = db["block"]
        micro_col = db["micro_concept"]

        domain_data = {
            "name": "資料庫（Database）",
            "description": "介紹資料庫的基本概念、設計流程、SQL 操作與資料表建立",
            "blocks": []
        }
        domain_id = domains_col.insert_one(domain_data).inserted_id

        block_titles = [
            "Chapter 1 資料庫概念",
            "Chapter 2 資料庫設計",
            "Chapter 3 SQL Server 使用",
            "Chapter 4 建立資料表"
        ]
        block_docs = [{"domain_id": domain_id, "title": t, "subtopics": []} for t in block_titles]
        block_ids = blocks_col.insert_many(block_docs).inserted_ids
        domains_col.update_one({"_id": domain_id}, {"$set": {"blocks": block_ids}})

        micro_map = [
            (0, "1-1 資料庫由來"),
            (0, "1-2 資料庫管理系統"),
            (0, "1-3 資料模型"),
            (0, "1-4 三層式架構"),
            (1, "2-1 設計流程"),
            (1, "2-2 個體關係模型"),
            (1, "2-3 主鍵與外部鍵"),
            (1, "2-4 正規化"),
            (2, "3-1 SQL 語言"),
            (2, "3-2 SSMS 操作"),
            (3, "4-1 資料型別"),
            (3, "4-2 使用 SQL 敘述新增資料表")
        ]
        micro_ids = micro_col.insert_many(
            [{"block_id": block_ids[idx], "name": name, "dependencies": []} for idx, name in micro_map]
        ).inserted_ids

        for i, (block_idx, _) in enumerate(micro_map):
            blocks_col.update_one({"_id": block_ids[block_idx]}, {"$push": {"subtopics": micro_ids[i]}})

        print("✅ 資料庫資料插入成功")
    except Exception as e:
        print(f"❌ 插入資料庫失敗：{e}")


def insert_ai_domain(db):
    """
    插入「AI 與機器學習（AI & Machine Learning）」的 Domain、Blocks、Micro Concepts
    """
    try:
        domains_col = db["domain"]
        blocks_col = db["block"]
        micro_col = db["micro_concept"]

        domain_data = {
            "name": "AI 與機器學習（AI & Machine Learning）",
            "description": "介紹 AI 工程、基礎模型、提示工程與微調技術",
            "blocks": []
        }
        domain_id = domains_col.insert_one(domain_data).inserted_id

        block_titles = [
            "Chapter 1 使用基礎模型建構 AI 應用導論",
            "Chapter 2 理解基礎模型",
            "Chapter 3 評估方法",
            "Chapter 4 評估 AI 系統",
            "Chapter 5 提示工程",
            "Chapter 6 RAG 與代理",
            "Chapter 7 微調",
            "Chapter 8 數據集工程"
        ]
        block_docs = [{"domain_id": domain_id, "title": t, "subtopics": []} for t in block_titles]
        block_ids = blocks_col.insert_many(block_docs).inserted_ids
        domains_col.update_one({"_id": domain_id}, {"$set": {"blocks": block_ids}})

        micro_map = [
            (0, "1-1 AI 工程崛起"),
            (0, "1-2 基礎模型使用案例"),
            (0, "1-3 AI 應用規劃"),
            (1, "2-1 訓練數據與建模"),
            (1, "2-2 後訓練與取樣"),
            (2, "3-1 語言建模指標與精確評估"),
            (3, "4-1 模型選擇與設計評估管道"),
            (4, "5-1 提示工程最佳實例"),
            (5, "6-1 RAG 與代理"),
            (5, "6-2 記憶管理"),
            (6, "7-1 微調概述與技術"),
            (7, "8-1 數據調理與增強")
        ]
        micro_ids = micro_col.insert_many(
            [{"block_id": block_ids[idx], "name": name, "dependencies": []} for idx, name in micro_map]
        ).inserted_ids

        for i, (block_idx, _) in enumerate(micro_map):
            blocks_col.update_one({"_id": block_ids[block_idx]}, {"$push": {"subtopics": micro_ids[i]}})

        print("✅ AI 與機器學習資料插入成功")
    except Exception as e:
        print(f"❌ 插入 AI 與機器學習失敗：{e}")


def insert_sec_domain(db):
    """
    插入「資訊安全（Information Security）」的 Domain、Blocks、Micro Concepts
    """
    try:
        domains_col = db["domain"]
        blocks_col = db["block"]
        micro_col = db["micro_concept"]

        domain_data = {
            "name": "資訊安全（Information Security）",
            "description": "介紹資訊安全的認知、架構、防禦與管理策略",
            "blocks": []
        }
        domain_id = domains_col.insert_one(domain_data).inserted_id

        block_titles = [
            "Chapter 1 資訊安全認知與風險識別",
            "Chapter 2 信任與安全架構",
            "Chapter 3 數位邊界與防禦部署",
            "Chapter 4 資訊安全管理與未來挑戰"
        ]
        block_docs = [{"domain_id": domain_id, "title": t, "subtopics": []} for t in block_titles]
        block_ids = blocks_col.insert_many(block_docs).inserted_ids
        domains_col.update_one({"_id": domain_id}, {"$set": {"blocks": block_ids}})

        micro_map = [
            (0, "1-1 資訊安全概論"),
            (0, "1-2 資訊法律與事件處理"),
            (0, "1-3 資訊安全威脅"),
            (1, "2-1 認證、授權與存取控制"),
            (1, "2-2 資訊安全架構與設計"),
            (1, "2-3 基礎密碼學"),
            (1, "2-4 資訊系統與網路模型"),
            (2, "3-1 防火牆與使用政策"),
            (2, "3-2 入侵偵測與防禦系統"),
            (2, "3-3 惡意程式與防毒"),
            (2, "3-4 多層次防禦"),
            (3, "4-1 資訊安全營運與管理"),
            (3, "4-2 開發維運安全")
        ]
        micro_ids = micro_col.insert_many(
            [{"block_id": block_ids[idx], "name": name, "dependencies": []} for idx, name in micro_map]
        ).inserted_ids

        for i, (block_idx, _) in enumerate(micro_map):
            blocks_col.update_one({"_id": block_ids[block_idx]}, {"$push": {"subtopics": micro_ids[i]}})

        print("✅ 資訊安全資料插入成功")
    except Exception as e:
        print(f"❌ 插入資訊安全失敗：{e}")


def insert_cloud_domain(db):
    """
    插入「雲端與虛擬化（Cloud & Virtualization）」的 Domain、Blocks、Micro Concepts
    """
    try:
        domains_col = db["domain"]
        blocks_col = db["block"]
        micro_col = db["micro_concept"]

        domain_data = {
            "name": "雲端與虛擬化（Cloud & Virtualization）",
            "description": "介紹虛擬化技術、KVM/Qemu、Libvirt、網路虛擬化與儲存架構",
            "blocks": []
        }
        domain_id = domains_col.insert_one(domain_data).inserted_id

        block_titles = [
            "Chapter 1 虛擬化技術",
            "Chapter 2 Qemu-KVM",
            "Chapter 3 Libvirt",
            "Chapter 4 Virt-Manager",
            "Chapter 5 網路虛擬化",
            "Chapter 6 傳統存儲技術與 RAID"
        ]
        block_docs = [{"domain_id": domain_id, "title": t, "subtopics": []} for t in block_titles]
        block_ids = blocks_col.insert_many(block_docs).inserted_ids
        domains_col.update_one({"_id": domain_id}, {"$set": {"blocks": block_ids}})

        micro_map = [
            (0, "1-1 CPU、伺服器、存儲、網路虛擬化"),
            (0, "1-2 Xen、KVM、RHEV 簡介"),
            (0, "1-3 VMware / VirtualBox / Hyper-V"),
            (1, "2-1 KVM 原理與架構"),
            (1, "2-2 Qemu 架構與運行模式"),
            (1, "2-3 Qemu 工具介紹"),
            (2, "3-1 Libvirt 架構與 API"),
            (2, "3-2 XML 配置文件"),
            (3, "4-1 安裝與使用介紹"),
            (3, "4-2 WebVirtMgr 管理平臺"),
            (4, "5-1 軟件 Overlay SDN"),
            (4, "5-2 硬件 Underlay SDN"),
            (5, "6-1 RAID 技術與硬盤接口"),
            (5, "6-2 邏輯卷管理")
        ]
        micro_ids = micro_col.insert_many(
            [{"block_id": block_ids[idx], "name": name, "dependencies": []} for idx, name in micro_map]
        ).inserted_ids

        for i, (block_idx, _) in enumerate(micro_map):
            blocks_col.update_one({"_id": block_ids[block_idx]}, {"$push": {"subtopics": micro_ids[i]}})

        print("✅ 雲端與虛擬化資料插入成功")
    except Exception as e:
        print(f"❌ 插入雲端與虛擬化失敗：{e}")

    
def insert_mis_domain(db):
    """
    插入「管理資訊系統（MIS）」的 Domain、Blocks、Micro Concepts
    """
    try:
        domains_col = db["domain"]
        blocks_col = db["block"]
        micro_col = db["micro_concept"]

        domain_data = {
            "name": "管理資訊系統（MIS）",
            "description": "介紹企業資訊系統的架構、應用與建置管理",
            "blocks": []
        }
        domain_id = domains_col.insert_one(domain_data).inserted_id

        block_titles = [
            "Chapter 1 組織、管理與連網企業",
            "Chapter 2 資訊科技基礎建設",
            "Chapter 3 數位時代的關鍵系統應用",
            "Chapter 4 建立與維護系統"
        ]
        block_docs = [{"domain_id": domain_id, "title": t, "subtopics": []} for t in block_titles]
        block_ids = blocks_col.insert_many(block_docs).inserted_ids
        domains_col.update_one({"_id": domain_id}, {"$set": {"blocks": block_ids}})

        micro_map = [
            (0, "1-1 現今全球企業的資訊系統"),
            (0, "1-2 全球電子化企業與協同合作"),
            (0, "1-3 資訊系統、組織與策略"),
            (1, "2-1 資訊科技基礎建設與新興科技"),
            (1, "2-2 資料庫與資訊管理"),
            (1, "2-3 電傳通訊、網際網路與無線科技"),
            (1, "2-4 資訊系統安全"),
            (2, "3-1 企業系統應用"),
            (2, "3-2 電子商務與數位市場"),
            (2, "3-3 知識管理與 AI"),
            (3, "4-1 建立資訊系統"),
            (3, "4-2 管理專案與全球系統")
        ]
        micro_ids = micro_col.insert_many(
            [{"block_id": block_ids[idx], "name": name, "dependencies": []} for idx, name in micro_map]
        ).inserted_ids

        for i, (block_idx, _) in enumerate(micro_map):
            blocks_col.update_one({"_id": block_ids[block_idx]}, {"$push": {"subtopics": micro_ids[i]}})

        print("✅ 管理資訊系統資料插入成功")
    except Exception as e:
        print(f"❌ 插入管理資訊系統失敗：{e}")


def insert_se_domain(db):
    """
    插入「軟體工程與系統開發（Software Engineering）」的 Domain、Blocks、Micro Concepts
    """
    try:
        domains_col = db["domain"]
        blocks_col = db["block"]
        micro_col = db["micro_concept"]

        domain_data = {
            "name": "軟體工程與系統開發（Software Engineering）",
            "description": "介紹軟體開發流程、架構設計、測試與品質管理",
            "blocks": []
        }
        domain_id = domains_col.insert_one(domain_data).inserted_id

        block_titles = [
            "Chapter 1 軟體工程簡介",
            "Chapter 2 軟體系統需求工程",
            "Chapter 3 系統規格到架構設計",
            "Chapter 4 物件導向軟體工程",
            "Chapter 5 系統測試與部署安裝",
            "Chapter 6 軟體系統管理與維護",
            "Chapter 7 軟體系統品質管理",
            "Chapter 8 設計模式與軟體重構",
            "Chapter 9 資料庫系統開發",
            "Chapter 10 跨平台可移植性開發"
        ]
        block_docs = [{"domain_id": domain_id, "title": t, "subtopics": []} for t in block_titles]
        block_ids = blocks_col.insert_many(block_docs).inserted_ids
        domains_col.update_one({"_id": domain_id}, {"$set": {"blocks": block_ids}})

        micro_map = [
            (0, "1-1 軟體工程定義與流程"),
            (0, "1-2 軟體系統與開發程序"),
            (1, "2-1 需求工程與系統模型"),
            (2, "3-1 軟體系統架構設計"),
            (3, "4-1 物件導向設計與實務"),
            (4, "5-1 系統測試流程"),
            (5, "6-1 軟體系統管理"),
            (5, "6-2 軟體維護"),
            (6, "7-1 品質管理原則"),
            (7, "8-1 設計模式應用"),
            (7, "8-2 軟體重構原則"),
            (8, "9-1 資料庫系統開發流程"),
            (9, "10-1 跨平台開發概念")
        ]
        micro_ids = micro_col.insert_many(
            [{"block_id": block_ids[idx], "name": name, "dependencies": []} for idx, name in micro_map]
        ).inserted_ids

        for i, (block_idx, _) in enumerate(micro_map):
            blocks_col.update_one({"_id": block_ids[block_idx]}, {"$push": {"subtopics": micro_ids[i]}})

        print("✅ 軟體工程與系統開發資料插入成功")
    except Exception as e:
        print(f"❌ 插入軟體工程與系統開發失敗：{e}")


# ---- 使用範例 ----
if __name__ == "__main__":
    initialize_mis_teach_db()

