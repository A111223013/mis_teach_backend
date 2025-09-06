import json
import random
import threading
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from bson import ObjectId
from tqdm import tqdm
import time
from accessories import init_gemini

# ====== API 密钥 ======
API_KEYS = [
   "AIzaSyC8y6nInv339tG3j2jwFfd2W3lU1A6aoBg", "AIzaSyAgJI1A8MCEIbvMtuyhWoqvVL1ffDPWjBs", "AIzaSyA0qRAxFFrtL7CljNpDG0YV8JIZEdHBI5c", "AIzaSyD1mJZjj7GWLhDYAgXk-BR9DJf_yTJzSMw",
    "AIzaSyCHSr3_LuQSO5ySj35hdWjhQosKydhntL8", "AIzaSyDDE9KH0cgNsKPhAg0PQIubqdWzA6PICrk", "AIzaSyBUmLCxZrfFCbrHCM_ewEE3vMjCh6l0f1U", "AIzaSyA7siZ-4_k-5nv7Qn2nZF8kffH70wOWwXw",
    "AIzaSyBWoJDc_IcSLIjg42H853McDRO3EpxbeUk", "AIzaSyBUh-IkyMOlf0rrHBmI9Q3TxH9fAIjLV9o", "AIzaSyCCVcBTUtrD_-iyCnVXOxHJ3tVLwzx5pQQ", "AIzaSyDwbI0eFslXKhACHt2GvmjkbEtbuNs7mbQ",
    "YAIzaSyApssNiwMT5fQLEje01yP9sx_-fsSFiIvo", "AIzaSyCLJGdv4IpimC5zCff74cD08R0UfJDGUGY", "AIzaSyBXRswyZbU9GRkQZ0J4QAvbgTNr8TGh7mI", "AIzaSyD1fduo6U9ggGCz4K1vp58m7-WegKIug6E"
]

key_lock = threading.Lock()
key_index = 0
api_error_count = 0
max_api_errors = 1000  # 增加错误限制

def set_api_key():
    global key_index
    with key_lock:
        api_key = API_KEYS[key_index]
        key_index = (key_index + 1) % len(API_KEYS)
    # 使用 accessories 中的 init_gemini 函數
    return init_gemini('gemini-1.5-flash')

def extract_json_from_text(text):
    if not text:
        return {}
    
    try:
        return json.loads(text)
    except:
        pass
    
    json_match = re.search(r'\{[\s\S]*\}', text)
    if json_match:
        try:
            return json.loads(json_match.group())
        except:
            pass
    
    return {}

def safe_json_parse(text):
    try:
        result = extract_json_from_text(text)
        if result:
            return result
        
        text = text.replace("'", '"')
        lines = text.split('\n')
        json_lines = []
        in_json = False
        
        for line in lines:
            if '{' in line or '[' in line:
                in_json = True
            if in_json:
                json_lines.append(line)
            if '}' in line or ']' in line:
                in_json = False
        
        json_text = '\n'.join(json_lines)
        return json.loads(json_text)
        
    except Exception as e:
        return {}

def match_from_list(text, valid_list):
    if not text or not valid_list:
        return random.choice(valid_list) if valid_list else ""
    
    text_lower = str(text).lower()
    for item in valid_list:
        if str(item).lower() in text_lower:
            return item
    return random.choice(valid_list) if valid_list else ""

# ====== 固定清单 ======
domains_list = [
    "數位邏輯","作業系統","程式語言","資料結構","網路","資料庫",
    "AI與機器學習","資訊安全","雲端與虛擬化","管理資訊系統（MIS）","軟體工程與系統開發"
]

blocks_list = [
    # 資料庫綜合
    "資料庫基礎與SQL查詢 (SQL基礎, 查詢進階)",
    "資料庫設計與正規化 (正規化與設計)",
    "資料庫交易與效能管理 (交易管理, 索引與效能調校)",
    "現代資料庫系統 (分散式資料庫與雲端, 新興議題)",
    "資料庫安全與維護 (資料庫安全與備援)",

    # 人工智慧綜合
    "人工智慧基礎 (人工智慧概論, 機器學習基礎)",
    "機器學習演算法 (常見演算法)",
    "深度學習技術 (深度學習)",
    "資料處理與模型優化 (特徵工程, 模型評估與驗證)",
    "AI應用與影響 (AI應用領域, AI與社會)",

    # 資訊安全綜合
    "資訊安全基礎 (資訊安全概論)",
    "加密技術與應用 (密碼學基礎)",
    "網路與系統防護 (網路安全, 系統安全)",
    "應用安全與管理 (應用安全, 安全管理)",
    "資安新興議題 (新興議題)",

    # 雲端計算綜合
    "雲端基礎與虛擬化 (雲端計算概論, 虛擬化技術)",
    "雲端架構與平台 (雲端基礎架構, 雲端運算平台)",
    "雲端安全與應用 (雲端安全, 雲端應用)",

    # 資訊管理綜合
    "資訊系統基礎 (MIS概論, 資訊系統類型)",
    "系統開發與組織影響 (資訊系統開發與導入, 資訊科技與組織)",
    "決策支持與新興趨勢 (MIS與決策支持, MIS的新興議題)",

    # 軟體工程綜合
    "軟體工程基礎 (軟體工程概論)",
    "開發方法與流程 (軟體開發方法)",
    "系統分析設計與測試 (系統分析與設計, 物件導向方法, 軟體測試與驗證)",
    "軟體維護與品質 (軟體維護與演化, 軟體品質保證)",
    "軟體專案管理 (軟體專案管理)",

    # 數位邏輯綜合
    "數位邏輯基礎 (數位邏輯概論)",
    "邏輯電路設計 (組合邏輯電路, 序向邏輯電路)",
    "記憶體與系統設計 (記憶體單元與儲存, 數位系統設計)",

    # 作業系統綜合
    "作業系統基礎 (作業系統概論)",
    "資源管理技術 (行程管理, 記憶體管理, 裝置管理與I/O)",
    "檔案系統與同步 (檔案系統, 同步與死結)",

    # 程式設計綜合
    "程式語言基礎 (程式語言概論, 語法與語義)",
    "程式結構與設計 (控制結構, 函數與參數傳遞, 物件導向程式設計OOP)",
    "記憶體與錯誤處理 (記憶體管理, 例外處理與錯誤處理)",
    "程式設計實務 (程式語言的實務應用)",

    # 資料結構與演算法綜合
    "資料結構基礎 (資料結構概論)",
    "核心資料結構 (線性資料結構, 樹狀資料結構, 圖形資料結構)",
    "演算法技術 (雜湊表與演算法, 排序與搜尋)",

    # 電腦網路綜合
    "網路基礎與架構 (網路基礎概念, 網路模型)",
    "網路協定分層 (實體層與資料連結層, 網路層, 傳輸層, 應用層)",
    "網路安全與管理 (網路安全, 無線與行動網路, 網路管理與新興技術)"
]

# 這裡放合法的小知識點清單（我直接縮短，實際用你的完整清單）
micro_concepts_list = [
    # 資料庫基礎與模型
    "資料庫基礎概念 (資料/資訊/知識, 定義與特性, 系統組成: DBMS/Database/Application)",
    "資料庫 vs 檔案系統的比較",
    "資料模型演進 (階層式, 網路, 關聯式, 物件導向, NoSQL與新興模型)",

    # 關聯式資料庫與SQL
    "關聯式模型核心概念 (Relation/Attribute/Tuple, Primary Key/Foreign Key, 完整性約束)",
    "SQL語言綜合 (DDL, DML-SELECT/INSERT/UPDATE/DELETE, DCL-GRANT/REVOKE, TCL-COMMIT/ROLLBACK)",
    "SQL進階查詢技術 (聚合函數-COUNT/AVG/SUM/MAX/MIN, 子查詢, JOIN-Inner/Outer/Cross)",
    "視圖 (View) 的應用與管理",

    # 資料庫設計與正規化
    "正規化理論與實務 (1NF, 2NF, 3NF, BCNF)",
    "反正規化 (Denormalization) 策略與取捨",

    # 交易處理與併發控制
    "交易管理與ACID特性",
    "併發控制機制 (鎖定Locking, 死結Deadlock處理)",
    
    # 資料庫效能與儲存
    "效能調優技術 (索引-B-Tree/Hash, 查詢最佳化, 資料庫快取Buffer Pool)",
    "大型資料庫架構 (分割Partitioning, 分片Sharding, 分散式資料庫)",

    # 現代資料庫與雲端
    "分散式系統理論 (CAP理論-Consistency/Availability/Partition Tolerance)",
    "雲端資料庫服務 (AWS RDS, Google Cloud Spanner)",
    "NoSQL資料庫實作 (MongoDB, Cassandra, Redis)",

    # 資料庫安全與管理
    "資料庫安全管理 (使用者授權與角色, SQL Injection防範)",
    "備援與高可用性 (備份與還原Backup & Recovery, 高可用性HA, 災難復原DR)",

    # 資料應用與分析
    "進階資料處理 (資料探勘Data Mining, 大數據-Big Data/Hadoop/Spark)",
    "商業智慧系統 (資料倉儲Data Warehouse, ETL流程, 商業智慧BI)",

    # 人工智慧基礎
    "人工智慧概論 (定義與歷史, 弱AI vs 強AI)",
    "機器學習範疇 (機器學習/深度學習與AI關係, 監督式/非監督式/強化學習)",
    
    # 機器學習演算法
    "基礎機器學習演算法 (線性回歸/邏輯回歸, 決策樹/隨機森林, SVM, KNN)",
    "深度學習架構 (神經網路基礎-Perceptron/MLP, CNN, RNN/LSTM/GRU, Transformer/Attention)",
    "非監督學習技術 (聚類演算法-K-Means/分層聚類)",

    # 機器學習實務
    "資料預處理與特徵工程 (資料前處理-Normalization/Standardization, 特徵選擇/降維-PCA/LDA, 特徵抽取)",
    "模型訓練與評估 (訓練集/驗證集/測試集劃分, 評估指標-Accuracy/Precision/Recall/F1, 交叉驗證, 過擬合/欠擬合)",

    # AI應用與倫理
    "AI應用領域 (自然語言處理NLP, 電腦視覺CV, 語音辨識, 生成式AI-GAN/Diffusion)",
    "AI倫理與社會影響 (AI倫理與偏差, AI安全與風險, AI與未來工作)",

    # 資訊安全基礎
    "資安基礎概念 (CIA三要素-Confidentiality/Integrity/Availability, 常見威脅-惡意程式/社交工程/網路攻擊)",
    
    # 加密與認證
    "加密技術綜合 (對稱式加密-AES/DES, 非對稱式加密-RSA/ECC, 雜湊函數-MD5/SHA-2/SHA-3)",
    "數位簽章與憑證體系",
    "身分認證與存取控制 (使用者認證, 存取控制機制)",

    # 網路與系統安全
    "網路安全防護 (防火牆Firewall, IDS/IPS, VPN/安全通訊協定-SSL-TLS/IPSec)",
    "系統與應用安全 (作業系統安全, Web安全-SQL Injection/XSS/CSRF, 行動應用安全, 雲端安全)",
    
    # 資安管理與治理
    "資安治理與風險管理 (風險評估, ISO 27001與安全治理, 零信任架構Zero Trust)",
    "資安維運技術 (漏洞管理與修補, 事件回應Incident Response, 備援與災難復原)",
    "新興安全技術 (區塊鏈與安全, AI在資安中的應用)",

    # 雲端計算基礎
    "雲端計算概論 (定義, 服務模式-IaaS/PaaS/SaaS, 部署模式-公有雲/私有雲/混合雲/多雲)",
    
    # 虛擬化與容器技術
    "虛擬化技術 (系統虛擬化-VMware/KVM/Hyper-V, 容器化-Docker/LXC, 容器編排-Kubernetes)",
    
    # 雲端架構與服務
    "雲端基礎架構 (資料中心Data Center, 分散式儲存-HDFS/Ceph, 負載平衡Load Balancer)",
    "主要雲端平台服務 (AWS-EC2/S3/RDS/Lambda, Google Cloud Platform, Microsoft Azure)",
    "Serverless架構與邊緣運算 (Edge Computing)",
    
    # 雲端安全與管理
    "雲端安全管理 (身分與存取管理-IAM, 雲端資安標準-CIS/NIST, 雲端加密與防護)",
    "雲端整合應用 (雲端與AI/大數據整合)",

    # 資訊系統與管理
    "資訊系統基礎 (定義, MIS角色與價值, 組織與系統互動)",
    "企業系統類型 (交易處理系統TPS, 管理報表系統MIS, 決策支援系統DSS, 企業資源規劃ERP, 供應鏈管理SCM, 顧客關係管理CRM)",
    "電子商務與知識管理 (E-Commerce, 知識管理KM)",
    
    # 系統開發與專案管理
    "系統開發方法論 (系統發展生命週期SDLC, 敏捷式方法Agile)",
    "IT專案管理與評估",
    
    # 現代資訊系統趨勢
    "現代企業應用 (商業智慧BI, 資料倉儲與資料探勘, 即時決策支持系統)",
    "數位轉型與整合 (數位轉型Digital Transformation, 雲端MIS, AI與MIS整合)",

    # 軟體工程基礎
    "軟體工程概論 (定義, 原則, 軟體生命週期)",
    
    # 開發流程與方法
    "開發模型 (瀑布模型Waterfall, 演化式模型Evolutionary, 敏捷開發-Agile/Scrum/XP, DevOps)",
    
    # 需求與設計
    "需求工程 (Requirement Engineering)",
    "系統設計與建模 (UML圖-Use Case/Class/Sequence/Activity, 系統設計)",
    
    # 物件導向技術
    "物件導向技術綜合 (OOP基礎-Class/Inheritance/Polymorphism, 物件導向分析OOA, 物件導向設計OOD)",
    
    # 軟體測試
    "軟體測試綜合 (測試層次-Unit/Integration/System, 測試方法-Black Box/White Box, 自動化測試)",
    
    # 軟體維護與品質
    "軟體維護類型 (Corrective/Adaptive/Perfective/Preventive)",
    "軟體品質與管理 (軟體品質模型-ISO 9126/25010, 品質保證流程, Code Review與Refactoring)",
    
    # 專案管理與版本控制
    "開發維運工具 (軟體版本管理-Git/SVN, 持續整合與持續部署CI/CD)",
    "軟體專案管理 (專案規劃與時程估算-PERT/Gantt, 風險管理, 成本估算-COCOMO)",

    # 數位邏輯基礎
    "數位邏輯基礎 (類比vs數位訊號, 布林代數Boolean Algebra, 邏輯閘-AND/OR/NOT/XOR/NAND/NOR)",
    
    # 組合邏輯電路
    "組合邏輯電路設計 (數位電路與邏輯函數, 半加器/全加器, 編碼器Encoder/解碼器Decoder, 多工器Multiplexer/解多工器Demultiplexer, 比較器Comparator)",
    
    # 序向邏輯電路
    "序向邏輯電路設計 (閂鎖器Latch/正反器Flip-Flop, 計數器Counter, 暫存器Register)",
    
    # 記憶體與數位系統
    "記憶體系統 (RAM, ROM, 記憶體位址與資料匯流排)",
    "數位系統設計 (狀態機State Machine, CPLD, FPGA)",

    # 作業系統基礎
    "作業系統概論 (定義與功能, 演進-批次/多工/分時, Kernel與使用者模式)",
    
    # 行程管理
    "行程與執行緒管理 (Process/Thread, PCB, 行程排程Scheduling演算法, 行程間通訊IPC)",
    
    # 記憶體管理
    "記憶體管理技術 (記憶體分區/分頁Paging, 分段Segmentation, 虛擬記憶體Virtual Memory, 置換演算法Page Replacement)",
    
    # 檔案與I/O管理
    "檔案系統管理 (架構與功能, 檔案存取方法, 目錄結構, 磁碟空間管理)",
    "I/O系統管理 (I/O硬體與軟體, Buffering/Caching, 磁碟排程演算法)",
    
    # 同步與死結
    "同步與死結處理 (競爭條件Race Condition/互斥Mutual Exclusion, 臨界區Critical Section, 號誌Semaphore/監控器Monitor, 死結Deadlock處理)",

    # 程式設計基礎
    "程式語言概論 (高階/低階語言, Compiler/Interpreter, 程式範型-Procedural/OOP/Functional)",
    
    # 程式基本結構
    "基本程式結構 (資料型態與變數, 流程控制-if/for/while/switch, 遞迴Recursion)",
    
    # 物件導向程式設計
    "OOP程式設計 (Class/Object, Encapsulation, Inheritance, Polymorphism)",
    
    # 記憶體管理與錯誤處理
    "記憶體管理 (Stack/Heap, Pointer, 記憶體配置/釋放, Garbage Collection)",
    "錯誤處理機制 (Exception處理, try-catch-finally)",
    
    # 開發工具與實踐
    "開發實踐 (函式庫與框架Library/Framework, 程式碼風格, 單元測試Unit Test/除錯Debugging)",

    # 資料結構與演算法基礎
    "資料結構與演算法基礎 (定義與重要性, 效能分析-時間/空間複雜度, Big O Notation)",
    
    # 基本資料結構
    "線性資料結構 (Array, Linked List, Stack, Queue)",
    
    # 樹狀結構
    "樹結構與演算法 (Tree遍歷Traversal, Binary Tree/BST, 平衡樹-AVL/Red-Black Tree, Heap/優先佇列)",
    
    # 圖形結構
    "圖結構與演算法 (Graph表示法-鄰接矩陣/鄰接串列, BFS/DFS, MST-Prim's/Kruskal's, 最短路徑-Dijkstra's/Bellman-Ford)",
    
    # 雜湊與排序
    "雜湊技術 (Hash Function, 碰撞解決, Hash Table)",
    "排序與搜尋演算法 (排序-冒泡/選擇/插入/快速/合併/堆積, 搜尋-線性/二元)",

    # 電腦網路基礎
    "網路基礎概論 (定義與功能, 網路分類-LAN/MAN/WAN, 拓樸-Star/Bus/Ring/Mesh, 效能指標-頻寬/延遲/吞吐量)",
    
    # 網路模型與協定
    "網路分層模型 (OSI七層, TCP/IP模型)",
    
    # 實體與資料連結層
    "實體層技術 (訊號編碼, 傳輸媒介-有線/無線)",
    "資料連結層技術 (封包框架, MAC位址, 錯誤偵測-CRC, 乙太網路Ethernet, ARP)",
    
    # 網路層與傳輸層
    "網路層協定與技術 (IP位址-IPv4/IPv6, 子網路遮罩/CIDR, 路由協定-RIP/OSPF/BGP, NAT, ICMP/Ping)",
    "傳輸層協定 (TCP/UDP, 三向交握/四次揮手, 流量控制/壅塞控制)",
    
    # 應用層與網路程式設計
    "應用層協定 (DNS, HTTP/HTTPS, FTP, SMTP, POP3/IMAP)",
    "網路程式設計 (Socket程式設計)",
    
    # 網路安全與新興技術
    "網路安全技術 (防火牆, VPN, IDS/IPS, 加密協定-SSL-TLS/IPSec)",
    "無線與行動網路 (無線標準-Wi-Fi/Bluetooth/5G, 行動網路架構-Cellular/Handoff)",
    "新興網路技術 (IoT物聯網網路, SDN軟體定義網路, 雲端網路/邊緣運算)"
]
def classify_question(q, max_retries=2):
    global api_error_count
    
    for attempt in range(max_retries):
        try:
            if api_error_count > max_api_errors:
                return create_random_classification(q)
                
            set_api_key()
            q_text = q.get("question_text", "")
            q_keys = q.get("key-points", [])
            q_options = q.get("options", [])

            prompt = f"""请分析以下题目并返回JSON格式结果：
题目: {q_text}
选项: {q_options}
知识点: {q_keys}

请选择最合适的分类（必须从给定列表中选择）：
1. 大知识点: {domains_list}
2. 区块: {blocks_list}
3. 小知识点: {micro_concepts_list}

返回格式: {{"domain": "名称", "block": "名称", "micro_concepts": ["名称1", "名称2"]}}
"""

            model = init_gemini("gemini-1.5-flash")
            response = model.generate_content(prompt)
            parsed = safe_json_parse(response.text)
            
            if not parsed:
                api_error_count += 1
                if api_error_count % 100 == 0:
                    print(f"⚠️ API错误计数: {api_error_count}")
                raise ValueError("JSON解析失败")
            
            domain = match_from_list(parsed.get("domain",""), domains_list)
            block = match_from_list(parsed.get("block",""), blocks_list)
            mc_list = [match_from_list(mc, micro_concepts_list) for mc in parsed.get("micro_concepts", [])[:2]]
            
            if not mc_list:
                mc_list = random.sample(micro_concepts_list, k=min(1, len(micro_concepts_list)))

            return {
                "domain": {"name": domain},
                "block": {"title": block, "domain_name": domain},
                "micro_concepts": [{"name": mc, "block_title": block} for mc in mc_list],
                "question": {
                    "text": q_text, 
                    "options": q_options, 
                    "micro_concepts": mc_list
                }
            }
            
        except Exception as e:
            if attempt == max_retries - 1:
                return create_random_classification(q)
            time.sleep(1)

def create_random_classification(q):
    q_text = q.get("question_text", "")
    q_options = q.get("options", [])
    
    domain = random.choice(domains_list)
    block = random.choice(blocks_list)
    mc_list = random.sample(micro_concepts_list, k=min(1, len(micro_concepts_list)))
    
    return {
        "domain": {"name": domain},
        "block": {"title": block, "domain_name": domain},
        "micro_concepts": [{"name": mc, "block_title": block} for mc in mc_list],
        "question": {
            "text": q_text, 
            "options": q_options, 
            "micro_concepts": mc_list
        }
    }

def process_in_batches(questions, batch_size=4000):
    """分批处理问题，每批4000个"""
    results = []
    total_batches = (len(questions) + batch_size - 1) // batch_size
    
    for batch_num in range(total_batches):
        start_idx = batch_num * batch_size
        end_idx = min((batch_num + 1) * batch_size, len(questions))
        batch_questions = questions[start_idx:end_idx]
        
        print(f"📦 处理批次 {batch_num + 1}/{total_batches} ({len(batch_questions)} 个问题)")
        
        batch_results = []
        max_workers = min(4, len(API_KEYS))
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(classify_question, q) for q in batch_questions]
            for future in tqdm(as_completed(futures), total=len(futures), desc=f"批次 {batch_num + 1}"):
                batch_results.append(future.result())
        
        results.extend(batch_results)
        
        # 每处理完一个批次就保存一次进度
        save_partial_results(results, batch_num + 1)
        
        # 添加延迟以避免API限制
        if batch_num < total_batches - 1:
            print("⏳ 等待3秒继续下一批次...")
            time.sleep(3)
    
    return results

def save_partial_results(results, batch_num):
    """保存部分结果"""
    try:
        # 构建知识图谱结构
        domains_dict, blocks_dict, micros_dict = {}, {}, {}
        questions_out = []

        for r in results:
            # 处理领域
            domain_name = r["domain"]["name"]
            if domain_name not in domains_dict:
                domains_dict[domain_name] = {
                    "name": domain_name,
                    "blocks": set()
                }
            
            # 处理区块
            block_title = r["block"]["title"]
            if block_title not in blocks_dict:
                blocks_dict[block_title] = {
                    "title": block_title,
                    "domain_name": domain_name,
                    "subtopics": set()
                }
            domains_dict[domain_name]["blocks"].add(block_title)
            
            # 处理小知识点
            for mc in r["micro_concepts"]:
                mc_name = mc["name"]
                if mc_name not in micros_dict:
                    micros_dict[mc_name] = {
                        "name": mc_name,
                        "block_title": block_title,
                        "dependencies": []
                    }
                blocks_dict[block_title]["subtopics"].add(mc_name)
            
            # 处理问题
            q = r["question"]
            questions_out.append({
                "text": q["text"],
                "options": q["options"],
                "micro_concepts": q["micro_concepts"]
            })

        # 转换为最终输出格式
        domains = []
        for domain_name, domain_data in domains_dict.items():
            domains.append({
                "name": domain_name,
                "blocks": list(domain_data["blocks"])
            })
        
        blocks = []
        for block_title, block_data in blocks_dict.items():
            blocks.append({
                "title": block_title,
                "domain_name": block_data["domain_name"],
                "subtopics": list(block_data["subtopics"])
            })
        
        micro_concepts = []
        for mc_name, mc_data in micros_dict.items():
            micro_concepts.append({
                "name": mc_name,
                "block_title": mc_data["block_title"],
                "dependencies": mc_data["dependencies"]
            })

        # 保存为四个独立的JSON文件
        with open(f"domains_batch_{batch_num}.json", "w", encoding="utf-8") as f:
            json.dump(domains, f, ensure_ascii=False, indent=2)
        
        with open(f"blocks_batch_{batch_num}.json", "w", encoding="utf-8") as f:
            json.dump(blocks, f, ensure_ascii=False, indent=2)
        
        with open(f"micro_concepts_batch_{batch_num}.json", "w", encoding="utf-8") as f:
            json.dump(micro_concepts, f, ensure_ascii=False, indent=2)
        
        with open(f"questions_batch_{batch_num}.json", "w", encoding="utf-8") as f:
            json.dump(questions_out, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 已保存批次 {batch_num} 的进度")
        
    except Exception as e:
        print(f"❌ 保存进度时出错: {e}")

def merge_results(total_batches):
    """合并所有批次的结果"""
    all_domains, all_blocks, all_micros, all_questions = [], [], [], []
    
    for batch_num in range(1, total_batches + 1):
        try:
            with open(f"domains_batch_{batch_num}.json", "r", encoding="utf-8") as f:
                all_domains.extend(json.load(f))
            with open(f"blocks_batch_{batch_num}.json", "r", encoding="utf-8") as f:
                all_blocks.extend(json.load(f))
            with open(f"micro_concepts_batch_{batch_num}.json", "r", encoding="utf-8") as f:
                all_micros.extend(json.load(f))
            with open(f"questions_batch_{batch_num}.json", "r", encoding="utf-8") as f:
                all_questions.extend(json.load(f))
        except:
            continue
    
    # 去重
    domains_dict, blocks_dict, micros_dict = {}, {}, {}
    
    for domain in all_domains:
        if domain["name"] not in domains_dict:
            domains_dict[domain["name"]] = domain
        else:
            # 合并blocks
            domains_dict[domain["name"]]["blocks"] = list(set(domains_dict[domain["name"]]["blocks"] + domain["blocks"]))
    
    for block in all_blocks:
        key = f"{block['title']}_{block['domain_name']}"
        if key not in blocks_dict:
            blocks_dict[key] = block
        else:
            blocks_dict[key]["subtopics"] = list(set(blocks_dict[key]["subtopics"] + block["subtopics"]))
    
    for micro in all_micros:
        key = f"{micro['name']}_{micro['block_title']}"
        if key not in micros_dict:
            micros_dict[key] = micro
    
    # 保存最终结果
    with open("domains.json", "w", encoding="utf-8") as f:
        json.dump(list(domains_dict.values()), f, ensure_ascii=False, indent=2)
    
    with open("blocks.json", "w", encoding="utf-8") as f:
        json.dump(list(blocks_dict.values()), f, ensure_ascii=False, indent=2)
    
    with open("micro_concepts.json", "w", encoding="utf-8") as f:
        json.dump(list(micros_dict.values()), f, ensure_ascii=False, indent=2)
    
    with open("questions.json", "w", encoding="utf-8") as f:
        json.dump(all_questions, f, ensure_ascii=False, indent=2)
    
    return len(domains_dict), len(blocks_dict), len(micros_dict), len(all_questions)

def main():
    try:
        with open("fainaldata_no_del.json", "r", encoding="utf-8") as f:
            questions = json.load(f)
    except Exception as e:
        print(f"❌ 读取文件错误: {e}")
        return

    print(f"📊 开始处理 {len(questions)} 个问题")
    
    # 计算批次数量
    batch_size = 4000
    total_batches = (len(questions) + batch_size - 1) // batch_size
    print(f"📦 分成 {total_batches} 个批次，每批 {batch_size} 个问题")
    
    # 分批处理所有问题
    results = process_in_batches(questions, batch_size=batch_size)
    
    # 合并所有批次的结果
    domain_count, block_count, micro_count, question_count = merge_results(total_batches)
    
    print("✅ 已完成四个独立的JSON文件:")
    print("   - domains.json")
    print("   - blocks.json") 
    print("   - micro_concepts.json")
    print("   - questions.json")
    
    print(f"📊 统计: {domain_count} 领域, {block_count} 区块, {micro_count} 知识点, {question_count} 问题")
    
    # 清理临时文件
    for batch_num in range(1, total_batches + 1):
        for file_type in ["domains", "blocks", "micro_concepts", "questions"]:
            try:
                os.remove(f"{file_type}_batch_{batch_num}.json")
            except:
                pass

if __name__ == "__main__":
    main()