from neo4j import GraphDatabase

def create_courses(tx):
    """
    Creates course nodes in the Neo4j graph.
    """
    queries = """
    // 課程建立
    CREATE (:Course {name: "數位邏輯", english_name: "Digital Logic"});
    CREATE (:Course {name: "作業系統", english_name: "Operating System"});
    CREATE (:Course {name: "資料結構", english_name: "Data Structure"});
    CREATE (:Course {name: "電腦網路", english_name: "Computer Network"});
    CREATE (:Course {name: "資料庫", english_name: "Database"});
    CREATE (:Course {name: "AI 與機器學習", english_name: "AI & Machine Learning"});
    CREATE (:Course {name: "資訊安全", english_name: "Information Security"});
    CREATE (:Course {name: "雲端與虛擬化", english_name: "Cloud & Virtualization"});
    CREATE (:Course {name: "管理資訊系統", english_name: "MIS"});
    CREATE (:Course {name: "軟體工程與系統開發", english_name: "Software Engineering"});
    """
    # 修正：將多個語句拆分並逐一執行
    for query in queries.split(';'):
        cleaned_query = query.strip()
        if cleaned_query:
            tx.run(cleaned_query)

def create_chapters(tx):
    """
    Creates chapter nodes and links them to their respective courses.
    """
    queries = """
    // 章節建立
    MATCH (c:Course {name: "數位邏輯"})
    CREATE (c)-[:HAS_CHAPTER]->(:Chapter {chapter_no: 1, name: "數位邏輯基本概念"});
    CREATE (c)-[:HAS_CHAPTER]->(:Chapter {chapter_no: 2, name: "基本邏輯閘"});
    CREATE (c)-[:HAS_CHAPTER]->(:Chapter {chapter_no: 3, name: "布林代數與第摩根定理"});
    CREATE (c)-[:HAS_CHAPTER]->(:Chapter {chapter_no: 4, name: "布林代數化簡"});

    MATCH (c:Course {name: "作業系統"})
    CREATE (c)-[:HAS_CHAPTER]->(:Chapter {chapter_no: 1, name: "作業系統基本概念"});
    CREATE (c)-[:HAS_CHAPTER]->(:Chapter {chapter_no: 2, name: "行程管理"});
    CREATE (c)-[:HAS_CHAPTER]->(:Chapter {chapter_no: 3, name: "行程同步"});
    CREATE (c)-[:HAS_CHAPTER]->(:Chapter {chapter_no: 4, name: "記憶體管理"});
    CREATE (c)-[:HAS_CHAPTER]->(:Chapter {chapter_no: 5, name: "儲存管理"});

    MATCH (c:Course {name: "資料結構"})
    CREATE (c)-[:HAS_CHAPTER]->(:Chapter {chapter_no: 1, name: "資料結構簡介"});
    CREATE (c)-[:HAS_CHAPTER]->(:Chapter {chapter_no: 2, name: "陣列"});
    CREATE (c)-[:HAS_CHAPTER]->(:Chapter {chapter_no: 3, name: "鏈結串列"});
    CREATE (c)-[:HAS_CHAPTER]->(:Chapter {chapter_no: 4, name: "佇列與堆疊"});
    CREATE (c)-[:HAS_CHAPTER]->(:Chapter {chapter_no: 5, name: "樹狀結構"});

    MATCH (c:Course {name: "電腦網路"})
    CREATE (c)-[:HAS_CHAPTER]->(:Chapter {chapter_no: 1, name: "概論"});
    CREATE (c)-[:HAS_CHAPTER]->(:Chapter {chapter_no: 2, name: "訊號調變與編碼"});
    CREATE (c)-[:HAS_CHAPTER]->(:Chapter {chapter_no: 3, name: "區域網路"});
    CREATE (c)-[:HAS_CHAPTER]->(:Chapter {chapter_no: 4, name: "區域網路之元件及連線"});
    CREATE (c)-[:HAS_CHAPTER]->(:Chapter {chapter_no: 5, name: "網際網路應用"});

    MATCH (c:Course {name: "資料庫"})
    CREATE (c)-[:HAS_CHAPTER]->(:Chapter {chapter_no: 1, name: "資料庫概念"});
    CREATE (c)-[:HAS_CHAPTER]->(:Chapter {chapter_no: 2, name: "資料庫設計"});
    CREATE (c)-[:HAS_CHAPTER]->(:Chapter {chapter_no: 3, name: "SQL Server 使用"});
    CREATE (c)-[:HAS_CHAPTER]->(:Chapter {chapter_no: 4, name: "建立資料表"});

    MATCH (c:Course {name: "AI 與機器學習"})
    CREATE (c)-[:HAS_CHAPTER]->(:Chapter {chapter_no: 1, name: "使用基礎模型建構 AI 應用導論"});
    CREATE (c)-[:HAS_CHAPTER]->(:Chapter {chapter_no: 2, name: "理解基礎模型"});
    CREATE (c)-[:HAS_CHAPTER]->(:Chapter {chapter_no: 3, name: "評估方法"});
    CREATE (c)-[:HAS_CHAPTER]->(:Chapter {chapter_no: 4, name: "評估 AI 系統"});
    CREATE (c)-[:HAS_CHAPTER]->(:Chapter {chapter_no: 5, name: "提示工程"});
    CREATE (c)-[:HAS_CHAPTER]->(:Chapter {chapter_no: 6, name: "RAG 與代理"});
    CREATE (c)-[:HAS_CHAPTER]->(:Chapter {chapter_no: 7, name: "微調"});
    CREATE (c)-[:HAS_CHAPTER]->(:Chapter {chapter_no: 8, name: "數據集工程"});

    MATCH (c:Course {name: "資訊安全"})
    CREATE (c)-[:HAS_CHAPTER]->(:Chapter {chapter_no: 1, name: "資訊安全認知與風險識別"});
    CREATE (c)-[:HAS_CHAPTER]->(:Chapter {chapter_no: 2, name: "信任與安全架構"});
    CREATE (c)-[:HAS_CHAPTER]->(:Chapter {chapter_no: 3, name: "數位邊界與防禦部署"});
    CREATE (c)-[:HAS_CHAPTER]->(:Chapter {chapter_no: 4, name: "資訊安全管理與未來挑戰"});

    MATCH (c:Course {name: "雲端與虛擬化"})
    CREATE (c)-[:HAS_CHAPTER]->(:Chapter {chapter_no: 1, name: "虛擬化技術"});
    CREATE (c)-[:HAS_CHAPTER]->(:Chapter {chapter_no: 2, name: "Qemu-KVM"});
    CREATE (c)-[:HAS_CHAPTER]->(:Chapter {chapter_no: 3, name: "Libvirt"});
    CREATE (c)-[:HAS_CHAPTER]->(:Chapter {chapter_no: 4, name: "Virt-Manager"});
    CREATE (c)-[:HAS_CHAPTER]->(:Chapter {chapter_no: 5, name: "網路虛擬化"});
    CREATE (c)-[:HAS_CHAPTER]->(:Chapter {chapter_no: 6, name: "傳統存儲技術與 RAID"});

    MATCH (c:Course {name: "管理資訊系統"})
    CREATE (c)-[:HAS_CHAPTER]->(:Chapter {chapter_no: 1, name: "組織、管理與連網企業"});
    CREATE (c)-[:HAS_CHAPTER]->(:Chapter {chapter_no: 2, name: "資訊科技基礎建設"});
    CREATE (c)-[:HAS_CHAPTER]->(:Chapter {chapter_no: 3, name: "數位時代的關鍵系統應用"});
    CREATE (c)-[:HAS_CHAPTER]->(:Chapter {chapter_no: 4, name: "建立與維護系統"});

    MATCH (c:Course {name: "軟體工程與系統開發"})
    CREATE (c)-[:HAS_CHAPTER]->(:Chapter {chapter_no: 1, name: "軟體工程簡介"});
    CREATE (c)-[:HAS_CHAPTER]->(:Chapter {chapter_no: 2, name: "軟體系統需求工程"});
    CREATE (c)-[:HAS_CHAPTER]->(:Chapter {chapter_no: 3, name: "系統規格到架構設計"});
    CREATE (c)-[:HAS_CHAPTER]->(:Chapter {chapter_no: 4, name: "物件導向軟體工程"});
    CREATE (c)-[:HAS_CHAPTER]->(:Chapter {chapter_no: 5, name: "系統測試與部署安裝"});
    CREATE (c)-[:HAS_CHAPTER]->(:Chapter {chapter_no: 6, name: "軟體系統管理與維護"});
    CREATE (c)-[:HAS_CHAPTER]->(:Chapter {chapter_no: 7, name: "軟體系統品質管理"});
    CREATE (c)-[:HAS_CHAPTER]->(:Chapter {chapter_no: 8, name: "設計模式與軟體重構"});
    CREATE (c)-[:HAS_CHAPTER]->(:Chapter {chapter_no: 9, name: "資料庫系統開發"});
    CREATE (c)-[:HAS_CHAPTER]->(:Chapter {chapter_no: 10, name: "跨平台可移植性開發"});
    """
    # 修正：將多個語句拆分並逐一執行
    for query in queries.split(';'):
        cleaned_query = query.strip()
        if cleaned_query:
            tx.run(cleaned_query)

def create_sections(tx):
    """
    Creates section nodes and links them to their respective chapters.
    """
    queries = """
    // 小節建立
    MATCH (ch:Chapter {chapter_no: 1, name: "數位邏輯基本概念"})
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "1-1", name: "數量表示法"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "1-2", name: "數位系統與類比系統"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "1-3", name: "邏輯準位與二進位表示法"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "1-4", name: "數位積體電路與 PLD 簡介"});

    MATCH (ch:Chapter {chapter_no: 2, name: "基本邏輯閘"})
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "2-1", name: "基本邏輯關係與布林代數"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "2-2", name: "或閘、及閘與反閘"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "2-3", name: "反或閘與反及閘"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "2-4", name: "互斥或閘與互斥反或閘"});

    MATCH (ch:Chapter {chapter_no: 3, name: "布林代數與第摩根定理"})
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "3-1", name: "布林代數特質"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "3-2", name: "單變數定理"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "3-3", name: "多變數定理與第摩根定理"});

    MATCH (ch:Chapter {chapter_no: 4, name: "布林代數化簡"})
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "4-3", name: "布林代數式簡化法"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "4-4", name: "卡諾圖與組合邏輯設計步驟"});

    MATCH (ch:Chapter {chapter_no: 1, name: "作業系統基本概念"})
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "1-1", name: "概說"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "1-2", name: "作業系統結構"});

    MATCH (ch:Chapter {chapter_no: 2, name: "行程管理"})
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "2-1", name: "行程觀念"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "2-2", name: "執行緒與並行性"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "2-3", name: "CPU 排班"});

    MATCH (ch:Chapter {chapter_no: 3, name: "行程同步"})
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "3-1", name: "同步工具"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "3-2", name: "同步範例"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "3-3", name: "死結"});

    MATCH (ch:Chapter {chapter_no: 4, name: "記憶體管理"})
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "4-1", name: "主記憶體"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "4-2", name: "虛擬記憶體"});

    MATCH (ch:Chapter {chapter_no: 5, name: "儲存管理"})
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "5-1", name: "大量儲存結構"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "5-2", name: "輸入/輸出系統"});

    MATCH (ch:Chapter {chapter_no: 1, name: "資料結構簡介"})
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "1-1", name: "資料結構定義"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "1-2", name: "資料結構對程式效率影響"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "1-3", name: "演算法定義"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "1-4", name: "程式效率分析"});

    MATCH (ch:Chapter {chapter_no: 2, name: "陣列"})
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "2-1", name: "一維陣列"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "2-2", name: "二維陣列"});

    MATCH (ch:Chapter {chapter_no: 3, name: "鏈結串列"})
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "3-1", name: "單向鏈結串列"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "3-2", name: "雙向與環狀鏈結串列"});

    MATCH (ch:Chapter {chapter_no: 4, name: "佇列與堆疊"})
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "4-1", name: "佇列"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "4-2", name: "堆疊"});

    MATCH (ch:Chapter {chapter_no: 5, name: "樹狀結構"})
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "5-2", name: "二元樹與二元搜尋樹"});

    MATCH (ch:Chapter {chapter_no: 1, name: "概論"})
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "1-1", name: "簡介"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "1-2", name: "訊號"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "1-3", name: "訊號傳輸"});

    MATCH (ch:Chapter {chapter_no: 2, name: "訊號調變與編碼"})
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "2-1", name: "調變"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "2-2", name: "類比傳輸與數位傳輸"});

    MATCH (ch:Chapter {chapter_no: 3, name: "區域網路"})
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "3-1", name: "區域網路拓樸方式"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "3-2", name: "區域網路開放架構"});

    MATCH (ch:Chapter {chapter_no: 4, name: "區域網路之元件及連線"})
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "4-1", name: "區域網路元件"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "4-2", name: "區域網路連線實作"});

    MATCH (ch:Chapter {chapter_no: 5, name: "網際網路應用"})
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "5-1", name: "TCP/IP 通訊協定"});

    MATCH (ch:Chapter {chapter_no: 1, name: "資料庫概念"})
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "1-1", name: "資料庫由來"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "1-2", name: "資料庫管理系統"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "1-3", name: "資料模型"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "1-4", name: "三層式架構"});

    MATCH (ch:Chapter {chapter_no: 2, name: "資料庫設計"})
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "2-1", name: "設計流程"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "2-2", name: "個體關係模型"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "2-3", name: "主鍵與外部鍵"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "2-4", name: "正規化"});

    MATCH (ch:Chapter {chapter_no: 3, name: "SQL Server 使用"})
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "3-1", name: "SQL 語言"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "3-2", name: "SSMS 操作"});

    MATCH (ch:Chapter {chapter_no: 4, name: "建立資料表"})
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "4-1", name: "資料型別"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "4-2", name: "使用 SQL 敘述新增資料表"});

    MATCH (ch:Chapter {chapter_no: 1, name: "使用基礎模型建構 AI 應用導論"})
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "1-1", name: "AI 工程崛起"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "1-2", name: "基礎模型使用案例"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "1-3", name: "AI 應用規劃"});

    MATCH (ch:Chapter {chapter_no: 2, name: "理解基礎模型"})
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "2-1", name: "訓練數據與建模"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "2-2", name: "後訓練與取樣"});

    MATCH (ch:Chapter {chapter_no: 3, name: "評估方法"})
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "3-1", name: "語言建模指標與精確評估"});

    MATCH (ch:Chapter {chapter_no: 4, name: "評估 AI 系統"})
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "4-1", name: "模型選擇與設計評估管道"});

    MATCH (ch:Chapter {chapter_no: 5, name: "提示工程"})
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "5-1", name: "提示工程最佳實例"});

    MATCH (ch:Chapter {chapter_no: 6, name: "RAG 與代理"})
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "6-1", name: "RAG 與代理"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "6-2", name: "記憶管理"});

    MATCH (ch:Chapter {chapter_no: 7, name: "微調"})
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "7-1", name: "微調概述與技術"});

    MATCH (ch:Chapter {chapter_no: 8, name: "數據集工程"})
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "8-1", name: "數據調理與增強"});

    MATCH (ch:Chapter {chapter_no: 1, name: "資訊安全認知與風險識別"})
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "1-1", name: "資訊安全概論"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "1-2", name: "資訊法律與事件處理"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "1-3", name: "資訊安全威脅"});

    MATCH (ch:Chapter {chapter_no: 2, name: "信任與安全架構"})
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "2-1", name: "認證、授權與存取控制"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "2-2", name: "資訊安全架構與設計"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "2-3", name: "基礎密碼學"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "2-4", name: "資訊系統與網路模型"});

    MATCH (ch:Chapter {chapter_no: 3, name: "數位邊界與防禦部署"})
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "3-1", name: "防火牆與使用政策"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "3-2", name: "入侵偵測與防禦系統"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "3-3", name: "惡意程式與防毒"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "3-4", name: "多層次防禦"});

    MATCH (ch:Chapter {chapter_no: 4, name: "資訊安全管理與未來挑戰"})
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "4-1", name: "資訊安全營運與管理"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "4-2", name: "開發維運安全"});

    MATCH (ch:Chapter {chapter_no: 1, name: "虛擬化技術"})
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "1-1", name: "CPU、伺服器、存儲、網路虛擬化"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "1-2", name: "Xen、KVM、RHEV 簡介"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "1-3", name: "VMware / VirtualBox / Hyper-V"});

    MATCH (ch:Chapter {chapter_no: 2, name: "Qemu-KVM"})
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "2-1", name: "KVM 原理與架構"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "2-2", name: "Qemu 架構與運行模式"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "2-3", name: "Qemu 工具介紹"});

    MATCH (ch:Chapter {chapter_no: 3, name: "Libvirt"})
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "3-1", name: "Libvirt 架構與 API"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "3-2", name: "XML 配置文件"});

    MATCH (ch:Chapter {chapter_no: 4, name: "Virt-Manager"})
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "4-1", name: "安裝與使用介紹"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "4-2", name: "WebVirtMgr 管理平臺"});

    MATCH (ch:Chapter {chapter_no: 5, name: "網路虛擬化"})
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "5-1", name: "軟件 Overlay SDN"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "5-2", name: "硬件 Underlay SDN"});

    MATCH (ch:Chapter {chapter_no: 6, name: "傳統存儲技術與 RAID"})
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "6-1", name: "RAID 技術與硬盤接口"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "6-2", name: "邏輯卷管理"});

    MATCH (ch:Chapter {chapter_no: 1, name: "組織、管理與連網企業"})
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "1-1", name: "現今全球企業的資訊系統"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "1-2", name: "全球電子化企業與協同合作"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "1-3", name: "資訊系統、組織與策略"});

    MATCH (ch:Chapter {chapter_no: 2, name: "資訊科技基礎建設"})
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "2-1", name: "資訊科技基礎建設與新興科技"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "2-2", name: "資料庫與資訊管理"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "2-3", name: "電傳通訊、網際網路與無線科技"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "2-4", name: "資訊系統安全"});

    MATCH (ch:Chapter {chapter_no: 3, name: "數位時代的關鍵系統應用"})
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "3-1", name: "企業系統應用"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "3-2", name: "電子商務與數位市場"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "3-3", name: "知識管理與 AI"});

    MATCH (ch:Chapter {chapter_no: 4, name: "建立與維護系統"})
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "4-1", name: "建立資訊系統"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "4-2", name: "管理專案與全球系統"});

    MATCH (ch:Chapter {chapter_no: 1, name: "軟體工程簡介"})
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "1-1", name: "軟體工程定義與流程"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "1-2", name: "軟體系統與開發程序"});

    MATCH (ch:Chapter {chapter_no: 2, name: "軟體系統需求工程"})
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "2-1", name: "需求工程與系統模型"});

    MATCH (ch:Chapter {chapter_no: 3, name: "系統規格到架構設計"})
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "3-1", name: "軟體系統架構設計"});

    MATCH (ch:Chapter {chapter_no: 4, name: "物件導向軟體工程"})
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "4-1", name: "物件導向設計與實務"});

    MATCH (ch:Chapter {chapter_no: 5, name: "系統測試與部署安裝"})
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "5-1", name: "系統測試流程"});

    MATCH (ch:Chapter {chapter_no: 6, name: "軟體系統管理與維護"})
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "6-1", name: "軟體系統管理"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "6-2", name: "軟體維護"});

    MATCH (ch:Chapter {chapter_no: 7, name: "軟體系統品質管理"})
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "7-1", name: "品質管理原則"});

    MATCH (ch:Chapter {chapter_no: 8, name: "設計模式與軟體重構"})
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "8-1", name: "設計模式應用"});
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "8-2", name: "軟體重構原則"});

    MATCH (ch:Chapter {chapter_no: 9, name: "資料庫系統開發"})
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "9-1", name: "資料庫系統開發流程"});

    MATCH (ch:Chapter {chapter_no: 10, name: "跨平台可移植性開發"})
    CREATE (ch)-[:HAS_SECTION]->(:Section {section_no: "10-1", name: "跨平台開發概念"});
    """
    # 修正：將多個語句拆分並逐一執行
    for query in queries.split(';'):
        cleaned_query = query.strip()
        if cleaned_query:
            tx.run(cleaned_query)

def create_prerequisite_relationships(tx):
    """
    Creates PREREQUISITE relationships between nodes.
    """
    queries = """
    // 建立先修關係 (PREREQUISITE)
    MATCH (a:Section {name: "邏輯準位與二進位表示法"}), (b:Section {name: "程式效率分析"}) CREATE (b)-[:PREREQUISITE]->(a);
    MATCH (a:Section {name: "布林代數特質"}), (b:Section {name: "第摩根定理"}) CREATE (b)-[:PREREQUISITE]->(a);
    MATCH (a:Section {name: "基本邏輯關係與布林代數"}), (b:Section {name: "布林代數化簡"}) CREATE (b)-[:PREREQUISITE]->(a);
    MATCH (a:Course {name: "線性代數"}), (b:Section {name: "向量搜尋"}) CREATE (b)-[:PREREQUISITE]->(a);
    MATCH (a:Course {name: "機率論"}), (b:Section {name: "異常檢測"}) CREATE (b)-[:PREREQUISITE]->(a);

    // 程式設計基礎
    MATCH (a:Section {name: "一維陣列"}), (b:Section {name: "二維陣列"}) CREATE (b)-[:PREREQUISITE]->(a);
    MATCH (a:Chapter {name: "陣列"}), (b:Chapter {name: "鏈結串列"}) CREATE (b)-[:PREREQUISITE]->(a);
    MATCH (a:Chapter {name: "陣列"}), (b:Section {name: "二分搜尋"}) CREATE (b)-[:PREREQUISITE]->(a);
    MATCH (a:Chapter {name: "鏈結串列"}), (b:Chapter {name: "堆疊"}) CREATE (b)-[:PREREQUISITE]->(a);
    MATCH (a:Chapter {name: "堆疊"}), (b:Chapter {name: "遞迴"}) CREATE (b)-[:PREREQUISITE]->(a);
    MATCH (a:Chapter {name: "佇列與堆疊"}), (b:Chapter {name: "樹狀結構"}) CREATE (b)-[:PREREQUISITE]->(a);
    MATCH (a:Chapter {name: "二元樹"}), (b:Section {name: "二元搜尋樹"}) CREATE (b)-[:PREREQUISITE]->(a);

    // 系統架構理解
    MATCH (a:Chapter {name: "作業系統基本概念"}), (b:Chapter {name: "行程管理"}) CREATE (b)-[:PREREQUISITE]->(a);
    MATCH (a:Section {name: "行程觀念"}), (b:Section {name: "執行緒與並行性"}) CREATE (b)-[:PREREQUISITE]->(a);
    MATCH (a:Chapter {name: "行程管理"}), (b:Chapter {name: "行程同步"}) CREATE (b)-[:PREREQUISITE]->(a);
    MATCH (a:Section {name: "並行性"}), (b:Chapter {name: "行程同步"}) CREATE (b)-[:PREREQUISITE]->(a);
    MATCH (a:Section {name: "主記憶體"}), (b:Section {name: "虛擬記憶體"}) CREATE (b)-[:PREREQUISITE]->(a);
    MATCH (a:Section {name: "虛擬記憶體"}), (b:Section {name: "分頁系統"}) CREATE (b)-[:PREREQUISITE]->(a);
    MATCH (a:Section {name: "分頁系統"}), (b:Section {name: "分段系統"}) CREATE (b)-[:PREREQUISITE]->(a);

    // 網路與通訊基礎
    MATCH (a:Section {name: "訊號"}), (b:Section {name: "訊號傳輸"}) CREATE (b)-[:PREREQUISITE]->(a);
    MATCH (a:Chapter {name: "訊號調變與編碼"}), (b:Chapter {name: "區域網路"}) CREATE (b)-[:PREREQUISITE]->(a);
    MATCH (a:Section {name: "區域網路拓樸方式"}), (b:Section {name: "區域網路元件"}) CREATE (b)-[:PREREQUISITE]->(a);

    // 資料庫設計流程
    MATCH (a:Section {name: "資料模型"}), (b:Section {name: "個體關係模型"}) CREATE (b)-[:PREREQUISITE]->(a);
    MATCH (a:Section {name: "個體關係模型"}), (b:Section {name: "主鍵與外部鍵"}) CREATE (b)-[:PREREQUISITE]->(a);
    MATCH (a:Section {name: "主鍵與外部鍵"}), (b:Section {name: "正規化"}) CREATE (b)-[:PREREQUISITE]->(a);
    MATCH (a:Section {name: "資料型別"}), (b:Section {name: "SQL語言"}) CREATE (b)-[:PREREQUISITE]->(a);

    // 軟體開發流程
    MATCH (a:Chapter {name: "軟體工程定義與流程"}), (b:Chapter {name: "需求工程與系統模型"}) CREATE (b)-[:PREREQUISITE]->(a);
    MATCH (a:Chapter {name: "需求工程"}), (b:Chapter {name: "軟體系統架構設計"}) CREATE (b)-[:PREREQUISITE]->(a);
    MATCH (a:Chapter {name: "軟體系統架構設計"}), (b:Section {name: "物件導向設計與實務"}) CREATE (b)-[:PREREQUISITE]->(a);

    // 安全基礎建設
    MATCH (a:Section {name: "資訊安全概論"}), (b:Section {name: "認證、授權與存取控制"}) CREATE (b)-[:PREREQUISITE]->(a);
    MATCH (a:Section {name: "基礎密碼學"}), (b:Section {name: "防火牆與使用政策"}) CREATE (b)-[:PREREQUISITE]->(a);

    // 虛擬化技術層次
    MATCH (a:Section {name: "CPU、伺服器、存儲、網路虛擬化"}), (b:Section {name: "KVM原理與架構"}) CREATE (b)-[:PREREQUISITE]->(a);
    MATCH (a:Section {name: "Qemu架構與運行模式"}), (b:Section {name: "Libvirt架構與API"}) CREATE (b)-[:PREREQUISITE]->(a);
    MATCH (a:Section {name: "Qemu"}), (b:Section {name: "KVM"}) CREATE (b)-[:PREREQUISITE]->(a);
    """
    # 修正：將多個語句拆分並逐一執行
    for query in queries.split(';'):
        cleaned_query = query.strip()
        if cleaned_query:
            tx.run(cleaned_query)

def create_similar_relationships(tx):
    """
    Creates SIMILAR_TO relationships between nodes.
    """
    queries = """
    // 建立相似關係 (SIMILAR_TO)
    MATCH (a:Section {name: "反或閘"}), (b:Section {name: "反及閘"}) CREATE (a)-[:SIMILAR_TO]->(b), (b)-[:SIMILAR_TO]->(a);
    MATCH (a:Section {name: "互斥或閘"}), (b:Section {name: "互斥反或閘"}) CREATE (a)-[:SIMILAR_TO]->(b), (b)-[:SIMILAR_TO]->(a);

    // 資料結構相似概念
    MATCH (a:Section {name: "佇列"}), (b:Section {name: "堆疊"}) CREATE (a)-[:SIMILAR_TO]->(b), (b)-[:SIMILAR_TO]->(a);
    MATCH (a:Section {name: "單向鏈結串列"}), (b:Section {name: "雙向鏈結串列"}) CREATE (a)-[:SIMILAR_TO]->(b), (b)-[:SIMILAR_TO]->(a);
    MATCH (a:Section {name: "HashMap"}), (b:Section {name: "Dictionary"}) CREATE (a)-[:SIMILAR_TO]->(b), (b)-[:SIMILAR_TO]->(a);

    // 記憶體管理相關性
    MATCH (a:Section {name: "邏輯卷管理"}), (b:Chapter {name: "記憶體管理"}) CREATE (a)-[:SIMILAR_TO]->(b), (b)-[:SIMILAR_TO]->(a);

    // 網路傳輸與協定比較
    MATCH (a:Section {name: "類比傳輸"}), (b:Section {name: "數位傳輸"}) CREATE (a)-[:SIMILAR_TO]->(b), (b)-[:SIMILAR_TO]->(a);
    MATCH (a:Section {name: "TCP"}), (b:Section {name: "UDP"}) CREATE (a)-[:SIMILAR_TO]->(b), (b)-[:SIMILAR_TO]->(a);
    MATCH (a:Section {name: "軟件 Overlay SDN"}), (b:Section {name: "硬件 Underlay SDN"}) CREATE (a)-[:SIMILAR_TO]->(b), (b)-[:SIMILAR_TO]->(a);

    // 系統管理與維護
    MATCH (a:Section {name: "軟體系統管理"}), (b:Section {name: "軟體維護"}) CREATE (a)-[:SIMILAR_TO]->(b), (b)-[:SIMILAR_TO]->(a);
    MATCH (a:Section {name: "入侵偵測系統"}), (b:Section {name: "入侵防禦系統"}) CREATE (a)-[:SIMILAR_TO]->(b), (b)-[:SIMILAR_TO]->(a);

    // 虛擬化技術對應
    MATCH (a:Section {name: "Xen"}), (b:Section {name: "VMware"}) CREATE (a)-[:SIMILAR_TO]->(b), (b)-[:SIMILAR_TO]->(a);
    """
    # 修正：將多個語句拆分並逐一執行
    for query in queries.split(';'):
        cleaned_query = query.strip()
        if cleaned_query:
            tx.run(cleaned_query)

def create_common_misconception_relationships(tx):
    """
    Creates COMMON_MISCONCEPTION_WITH relationships between nodes.
    """
    queries = """
    // 建立錯誤關聯 (COMMON_MISCONCEPTION_WITH)
    // 邏輯閘混淆
    MATCH (a:Section {name: "或閘"}), (b:Section {name: "反或閘"}) CREATE (a)-[:COMMON_MISCONCEPTION_WITH]->(b);
    MATCH (a:Section {name: "及閘"}), (b:Section {name: "反及閘"}) CREATE (a)-[:COMMON_MISCONCEPTION_WITH]->(b);
    MATCH (a:Section {name: "互斥或閘"}), (b:Section {name: "或閘"}) CREATE (a)-[:COMMON_MISCONCEPTION_WITH]->(b);

    // 資料結構概念混淆
    MATCH (a:Section {name: "佇列"}), (b:Section {name: "堆疊"}) CREATE (a)-[:COMMON_MISCONCEPTION_WITH]->(b);
    MATCH (a:Section {name: "二元樹"}), (b:Section {name: "二元搜尋樹"}) CREATE (a)-[:COMMON_MISCONCEPTION_WITH]->(b);
    MATCH (a:Section {name: "單向鏈結串列"}), (b:Section {name: "雙向鏈結串列"}) CREATE (a)-[:COMMON_MISCONCEPTION_WITH]->(b);
    MATCH (a:Section {name: "主鍵"}), (b:Section {name: "外部鍵"}) CREATE (a)-[:COMMON_MISCONCEPTION_WITH]->(b);

    // 程式語言與記憶體混淆
    MATCH (a:Section {name: "指標"}), (b:Section {name: "引用"}) CREATE (a)-[:COMMON_MISCONCEPTION_WITH]->(b);
    MATCH (a:Section {name: "主記憶體"}), (b:Section {name: "虛擬記憶體"}) CREATE (a)-[:COMMON_MISCONCEPTION_WITH]->(b);
    MATCH (a:Chapter {name: "記憶體管理"}), (b:Chapter {name: "儲存管理"}) CREATE (a)-[:COMMON_MISCONCEPTION_WITH]->(b);

    // 行程與執行緒混淆
    MATCH (a:Section {name: "行程"}), (b:Section {name: "執行緒"}) CREATE (a)-[:COMMON_MISCONCEPTION_WITH]->(b);

    // 網路傳輸混淆
    MATCH (a:Section {name: "調變"}), (b:Section {name: "編碼"}) CREATE (a)-[:COMMON_MISCONCEPTION_WITH]->(b);
    MATCH (a:Section {name: "區域網路"}), (b:Section {name: "網際網路"}) CREATE (a)-[:COMMON_MISCONCEPTION_WITH]->(b);

    // 資料庫設計混淆
    MATCH (a:Section {name: "個體關係模型"}), (b:Section {name: "資料模型"}) CREATE (a)-[:COMMON_MISCONCEPTION_WITH]->(b);

    // 軟體開發階段混淆
    MATCH (a:Section {name: "軟體維護"}), (b:Section {name: "軟體系統管理"}) CREATE (a)-[:COMMON_MISCONCEPTION_WITH]->(b);
    MATCH (a:Section {name: "系統測試"}), (b:Chapter {name: "品質管理"}) CREATE (a)-[:COMMON_MISCONCEPTION_WITH]->(b);

    // 機器學習概念混淆
    MATCH (a:Section {name: "過擬合"}), (b:Section {name: "欠擬合"}) CREATE (a)-[:COMMON_MISCONCEPTION_WITH]->(b);
    """
    # 修正：將多個語句拆分並逐一執行
    for query in queries.split(';'):
        cleaned_query = query.strip()
        if cleaned_query:
            tx.run(cleaned_query)

def create_cross_domain_relationships(tx):
    """
    Creates CROSS_DOMAIN_LINK relationships between nodes.
    """
    queries = """
    // 建立跨領域關聯 (CROSS_DOMAIN_LINK)
    // 數位邏輯 ↔ 其他領域
    MATCH (a:Section {name: "邏輯準位"}), (b:Section {name: "數位邊界防禦"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);
    MATCH (a:Chapter {name: "布林代數"}), (b:Section {name: "邏輯推理模型"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);
    MATCH (a:Section {name: "數位積體電路"}), (b:Section {name: "CPU虛擬化"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);

    // 作業系統 ↔ 其他領域
    MATCH (a:Chapter {name: "行程管理"}), (b:Chapter {name: "系統架構設計"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);
    MATCH (a:Chapter {name: "記憶體管理"}), (b:Section {name: "程式效率分析"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);
    MATCH (a:Chapter {name: "儲存管理"}), (b:Section {name: "資料儲存結構"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);
    MATCH (a:Section {name: "CPU排班"}), (b:Section {name: "資源管理"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);
    MATCH (a:Section {name: "虛擬記憶體"}), (b:Section {name: "記憶體虛擬化"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);
    MATCH (a:Section {name: "I/O 系統"}), (b:Section {name: "傳輸層協定"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);
    MATCH (a:Section {name: "權限管理"}), (b:Section {name: "存取控制"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);

    // 資料結構 ↔ 其他領域
    MATCH (a:Section {name: "演算法分析"}), (b:Section {name: "模型訓練效率"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);
    MATCH (a:Chapter {name: "樹狀結構"}), (b:Section {name: "索引結構設計"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);
    MATCH (a:Section {name: "雜湊表"}), (b:Section {name: "加密雜湊函數"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);
    MATCH (a:Chapter {name: "陣列"}), (b:Section {name: "封包緩衝區"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);
    MATCH (a:Section {name: "佇列"}), (b:Section {name: "行程排程佇列"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);
    MATCH (a:Section {name: "向量搜尋"}), (b:Section {name: "RAG系統"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);
    MATCH (a:Section {name: "搜尋演算法"}), (b:Section {name: "索引"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);

    // 電腦網路 ↔ 其他領域
    MATCH (a:Section {name: "TCP/IP 協定"}), (b:Section {name: "網路安全架構"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);
    MATCH (a:Chapter {name: "區域網路"}), (b:Section {name: "企業網路架構"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);
    MATCH (a:Section {name: "訊號傳輸"}), (b:Chapter {name: "網路虛擬化"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);
    MATCH (a:Section {name: "網際網路應用"}), (b:Section {name: "分散式系統設計"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);
    MATCH (a:Section {name: "安全傳輸"}), (b:Section {name: "密碼學"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);
    MATCH (a:Section {name: "封包過濾"}), (b:Section {name: "防火牆"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);

    // 資料庫 ↔ 其他領域
    MATCH (a:Section {name: "正規化"}), (b:Section {name: "資料模型設計"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);
    MATCH (a:Section {name: "索引"}), (b:Section {name: "搜尋演算法"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);
    MATCH (a:Section {name: "交易管理"}), (b:Section {name: "並行控制"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);
    MATCH (a:Section {name: "資料安全"}), (b:Section {name: "存取控制"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);
    MATCH (a:Section {name: "分散式資料庫"}), (b:Section {name: "分散式存儲"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);
    MATCH (a:Section {name: "大數據處理"}), (b:Chapter {name: "基礎模型"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);
    MATCH (a:Section {name: "資料清理"}), (b:Section {name: "數據調理"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);
    MATCH (a:Section {name: "企業資料管理"}), (b:Section {name: "企業系統應用"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);

    // AI與機器學習 ↔ 其他領域
    MATCH (a:Chapter {name: "基礎模型"}), (b:Section {name: "大數據處理"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);
    MATCH (a:Section {name: "提示工程"}), (b:Section {name: "用戶需求分析"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);
    MATCH (a:Section {name: "RAG系統"}), (b:Section {name: "向量搜尋"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);
    MATCH (a:Section {name: "微調技術"}), (b:Section {name: "系統優化"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);
    MATCH (a:Section {name: "數據調理"}), (b:Section {name: "資料清理"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);
    MATCH (a:Section {name: "異常檢測"}), (b:Section {name: "入侵偵測"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);
    MATCH (a:Section {name: "知識表示"}), (b:Section {name: "知識管理"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);
    MATCH (a:Course {name: "高斯分布"}), (b:Section {name: "常態分布"}) CREATE (b)-[:CROSS_DOMAIN_LINK]->(a);
    MATCH (a:Section {name: "模型訓練"}), (b:Chapter {name: "矩陣運算"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);
    MATCH (a:Section {name: "模型測試"}), (b:Section {name: "測試"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);
    MATCH (a:Section {name: "MLOps"}), (b:Section {name: "DevOps"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);

    // 資訊安全 ↔ 其他領域
    MATCH (a:Section {name: "密碼學"}), (b:Section {name: "安全傳輸"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);
    MATCH (a:Section {name: "存取控制"}), (b:Section {name: "權限管理"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);
    MATCH (a:Section {name: "防火牆"}), (b:Section {name: "封包過濾"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);
    MATCH (a:Section {name: "入侵偵測"}), (b:Section {name: "異常檢測"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);
    MATCH (a:Section {name: "安全架構"}), (b:Section {name: "安全設計模式"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);

    // 雲端與虛擬化 ↔ 其他領域
    MATCH (a:Chapter {name: "虛擬化技術"}), (b:Section {name: "資源抽象化"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);
    MATCH (a:Section {name: "軟體定義網路"}), (b:Section {name: "網路控制"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);
    MATCH (a:Section {name: "分散式存儲"}), (b:Section {name: "數據分散管理"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);
    MATCH (a:Section {name: "容器技術"}), (b:Section {name: "應用部署"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);
    MATCH (a:Section {name: "資源調度"}), (b:Section {name: "資源最佳化"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);
    MATCH (a:Section {name: "平台抽象化"}), (b:Section {name: "跨平台開發"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);

    // 管理資訊系統 ↔ 其他領域
    MATCH (a:Section {name: "企業系統應用"}), (b:Section {name: "企業資料管理"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);
    MATCH (a:Section {name: "電子商務"}), (b:Section {name: "網路安全"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);
    MATCH (a:Section {name: "知識管理"}), (b:Section {name: "知識表示"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);
    MATCH (a:Section {name: "專案管理"}), (b:Section {name: "專案生命週期"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);
    MATCH (a:Section {name: "系統整合"}), (b:Section {name: "系統架構"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);
    MATCH (a:Section {name: "變更管理"}), (b:Section {name: "版本控制"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);
    MATCH (a:Section {name: "品質控制流程"}), (b:Section {name: "品質管理"}) CREATE (a)-[:CROSS_DOMAIN_LINK]->(b), (b)-[:CROSS_DOMAIN_LINK]->(a);
    """
    # 修正：將多個語句拆分並逐一執行
    for query in queries.split(';'):
        cleaned_query = query.strip()
        if cleaned_query:
            tx.run(cleaned_query)

def init_neo4j_knowledge_graph():
    """
    Initializes the Neo4j knowledge graph by creating nodes and relationships.
    """
    # Neo4j connection details
    uri = "bolt://localhost:7687"
    username = "neo4j"
    password = "12345678"  # 請替換為您的實際密碼

    driver = GraphDatabase.driver(uri, auth=(username, password))

    with driver.session() as session:
        print("Creating nodes and relationships in Neo4j...")
        # 清除舊的資料，以便重新建立
        session.run("MATCH (n) DETACH DELETE n")

        session.execute_write(create_courses)
        session.execute_write(create_chapters)
        session.execute_write(create_sections)
        session.execute_write(create_prerequisite_relationships)
        session.execute_write(create_similar_relationships)
        session.execute_write(create_common_misconception_relationships)
        session.execute_write(create_cross_domain_relationships)
        print("Knowledge graph initialization complete.")
    driver.close()

if __name__ == '__main__':
    init_neo4j_knowledge_graph()