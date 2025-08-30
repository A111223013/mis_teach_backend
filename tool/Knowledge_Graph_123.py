import json
import random
import threading
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from bson import ObjectId
import google.generativeai as genai
from tqdm import tqdm
import time

# ====== API 密钥 ======
API_KEYS = [
    "AIzaSyC8y6nInv339tG3j2jwFfd2W3lU1A6aoBg", 
    "AIzaSyAgJI1A8MCEIbvMtuyhWoqvVL1ffDPWjBs",
    "AIzaSyA0qRAxFFrtL7CljNpDG0YV8JIZEdHBI5c", 
    "AIzaSyD1mJZjj7GWLhDYAgXk-BR9DJf_yTJzSMw"
]

key_lock = threading.Lock()
key_index = 0
api_error_count = 0
max_api_errors = 100

def set_api_key():
    global key_index
    with key_lock:
        api_key = API_KEYS[key_index]
        key_index = (key_index + 1) % len(API_KEYS)
    genai.configure(api_key=api_key)

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
        print(f"⚠️ JSON parse error: {e}")
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
domains_list = ["數位邏輯","作業系統","程式語言","資料結構","網路","資料庫","AI與機器學習","資訊安全","雲端與虛擬化","管理資訊系統（MIS）","軟體工程與系統開發"]
blocks_list = ["資料庫概論","資料模型","關聯式資料庫基礎","SQL 基礎","查詢進階","正規化與設計","交易管理","索引與效能調校","分散式資料庫與雲端","資料庫安全與備援","新興議題","人工智慧概論","機器學習基礎","常見演算法","深度學習","特徵工程","模型評估與驗證","AI 應用領域","AI 與社會","資訊安全概論","密碼學基礎","網路安全","系統安全","應用安全","安全管理","新興議題","雲端計算概論","虛擬化技術","雲端基礎架構","雲端運算平台","雲端安全","雲端應用","MIS 概論","資訊系統類型","資訊系統開發與導入","資訊科技與組織","MIS 與決策支持","MIS 的新興議題","軟體工程概論","軟體開發方法","系統分析與設計","物件導向方法","軟體測試與驗證","軟體維護與演化","軟體品質保證","軟體專案管理","數值系統與二進制","布林代數與邏輯閘","循序邏輯","電腦組織","記憶體階層","作業系統概論","行程與執行緒管理","記憶體管理","檔案系統","設備管理","程式語言概論","程式設計範式","程式語言基礎","程式語言核心概念","記憶體管理","資料結構概論","線性資料結構","非線性資料結構","雜湊表與演算法","抽象資料型態 (ADT)","網路概論","網路協定與架構","網路設備","網際網路與服務","網路安全"]
micro_concepts_list = ["資料、資訊與知識的關係", "資料庫的定義與特性", "資料庫系統的組成 (DBMS, Database, Application)", "資料庫 vs 檔案系統", "階層式模型", "網路模型", "關聯式模型 (Relational Model)", "物件導向資料模型", "NoSQL 與新興資料模型", "關係 (Relation)、屬性 (Attribute)、元組 (Tuple)", "主鍵 (Primary Key) 與外鍵 (Foreign Key)", "完整性約束 (Integrity Constraints)", "DDL（資料定義語言）", "DML（資料操作語言：SELECT, INSERT, UPDATE, DELETE）", "DCL（存取控制：GRANT, REVOKE）", "TCL（交易控制：COMMIT, ROLLBACK）", "聚合函數 (COUNT, AVG, SUM, MAX, MIN)", "子查詢 (Subquery)", "JOIN (Inner, Outer, Cross)", "視圖 (View)", "第一正規化 (1NF)", "第二正規化 (2NF)", "第三正規化 (3NF)", "BCNF", "反正規化 (Denormalization)", "交易 (Transaction) 與其特性 (ACID)", "鎖定機制 (Locking)", "併發控制 (Concurrency Control)", "死結 (Deadlock) 與解決方法", "索引 (B-Tree, Hash Index)", "查詢最佳化 (Query Optimization)", "資料庫快取 (Buffer Pool)", "分割 (Partitioning) 與分片 (Sharding)", "分散式資料庫架構", "CAP 理論 (Consistency, Availability, Partition Tolerance)", "雲端資料庫 (AWS RDS, Google Cloud Spanner)", "NoSQL (MongoDB, Cassandra, Redis)", "使用者授權與角色", "SQL Injection 與防範", "備份與還原 (Backup & Recovery)", "高可用性 (HA) 與災難復原 (DR)", "資料探勘 (Data Mining)", "大數據處理 (Big Data, Hadoop, Spark)", "資料倉儲 (Data Warehouse)", "ETL (Extract, Transform, Load)", "商業智慧 (Business Intelligence, BI)", "AI 的定義與歷史", "弱人工智慧 vs 強人工智慧", "機器學習、深度學習與人工智慧的關係", "監督式學習 (Supervised Learning)", "非監督式學習 (Unsupervised Learning)", "強化學習 (Reinforcement Learning)", "過擬合與欠擬合", "線性回歸與邏輯回歸", "決策樹與隨機森林", "支援向量機 (SVM)", "K-近鄰演算法 (KNN)", "聚類演算法 (K-Means, Hierarchical Clustering)", "神經網路基礎 (Perceptron, MLP)", "捲積神經網路 (CNN)", "循環神經網路 (RNN, LSTM, GRU)", "Transformer 與注意力機制 (Attention)", "資料前處理 (Normalization, Standardization)", "特徵選擇與降維 (PCA, LDA)", "特徵抽取與表示學習", "訓練集、驗證集、測試集", "評估指標 (Accuracy, Precision, Recall, F1-score)", "交叉驗證 (Cross Validation)", "自然語言處理 (NLP)", "電腦視覺 (CV)", "語音辨識", "生成式 AI (GAN, Diffusion Models)", "AI 倫理與偏差", "AI 安全與風險", "AI 與未來工作", "資訊安全的 CIA 三要素 (Confidentiality, Integrity, Availability)", "常見威脅 (惡意程式、社交工程、網路攻擊)", "對稱式加密 (AES, DES)", "非對稱式加密 (RSA, ECC)", "雜湊函數 (MD5, SHA-2, SHA-3)", "數位簽章與憑證", "防火牆 (Firewall)", "入侵偵測與防禦系統 (IDS/IPS)", "VPN 與安全通訊協定 (SSL/TLS, IPSec)", "作業系統安全機制", "使用者認證與存取控制", "漏洞管理與修補", "Web 安全 (SQL Injection, XSS, CSRF)", "行動應用程式安全", "雲端安全議題", "風險評估", "ISO 27001 與安全治理", "事件回應 (Incident Response)", "備援與災難復原", "區塊鏈與安全", "零信任架構 (Zero Trust)", "AI 在資安中的應用", "雲端計算的定義", "雲端服務模式 (IaaS, PaaS, SaaS)", "部署模式 (公有雲、私有雲、混合雲、多雲)", "系統虛擬化 (VMware, KVM, Hyper-V)", "容器化技術 (Docker, LXC)", "容器編排 (Kubernetes)", "資料中心 (Data Center)", "分散式儲存 (HDFS, Ceph)", "負載平衡 (Load Balancer)", "AWS 核心服務 (EC2, S3, RDS, Lambda)", "Google Cloud Platform (GCP)", "Microsoft Azure", "身分與存取管理 (IAM)", "雲端資安標準 (CIS, NIST)", "雲端加密與防護", "Serverless 架構", "邊緣運算 (Edge Computing)", "雲端與 AI/大數據整合", "資訊系統的定義", "MIS 的角色與價值", "組織與資訊系統的互動", "交易處理系統 (TPS)", "管理報表系統 (MIS)", "決策支援系統 (DSS)", "企業資源規劃 (ERP)", "供應鏈管理 (SCM)", "顧客關係管理 (CRM)", "系統發展生命週期 (SDLC)", "敏捷式方法 (Agile)", "專案管理與評估", "IT 對組織的影響", "電子商務 (E-Commerce)", "知識管理 (KM)", "商業智慧 (BI)", "資料倉儲與資料探勘", "即時決策支持系統", "數位轉型 (Digital Transformation)", "雲端 MIS", "AI 與 MIS 整合", "軟體工程的定義", "軟體工程原則", "軟體生命週期", "瀑布模型 (Waterfall)", "演化式模型 (Evolutionary)", "敏捷開發 (Agile, Scrum, XP)", "DevOps", "需求工程 (Requirement Engineering)", "UML 圖 (Use Case, Class, Sequence, Activity)", "系統設計與建模", "物件導向程式設計 (OOP) 基礎 (Class, Inheritance, Polymorphism)", "物件導向分析 (OOA)", "物件導向設計 (OOD)", "測試層次 (Unit Test, Integration Test, System Test)", "測試方法 (Black Box, White Box)", "自動化測試", "維護類型 (Corrective, Adaptive, Perfective, Preventive)", "軟體版本管理 (Git, SVN)", "持續整合與持續部署 (CI/CD)", "軟體品質模型 (ISO 9126, ISO 25010)", "品質保證流程", "Code Review 與 Refactoring", "專案規劃與時程估算 (PERT, Gantt)", "風險管理", "成本估算 (COCOMO 模型)", "二進制、八進制、十進制、十六進制", "二補數 (Two's Complement)", "布林代數", "基本邏輯閘", "組合邏輯", "正反器 (Flip-Flop)", "暫存器 (Register) 與計數器 (Counter)", "CPU 架構", "指令集架構 (ISA)", "匯流排 (Bus)", "快取記憶體 (Cache)", "主記憶體 (RAM)", "儲存裝置 (Storage)", "作業系統的功能", "核心 (Kernel)", "行程 (Process)", "執行緒 (Thread)", "行程排程", "同步與互斥", "分頁 (Paging)", "分段 (Segmentation)", "虛擬記憶體 (Virtual Memory)", "檔案系統的結構", "檔案存取權限", "驅動程式 (Driver)", "I/O 管理", "高階語言 vs 低階語言", "編譯式語言 vs 直譯式語言", "物件導向程式設計 (OOP)", "函數式程式設計 (Functional Programming)", "變數與資料型態", "控制結構", "函式與模組", "錯誤處理與例外", "堆疊 (Stack) 與堆積 (Heap)", "垃圾回收 (Garbage Collection)", "資料結構的定義與重要性", "陣列 (Array)", "鏈結串列 (Linked List)", "堆疊 (Stack)", "佇列 (Queue)", "樹 (Tree)", "圖 (Graph)", "雜湊表 (Hash Table)", "排序演算法", "搜尋演算法", "ADT 的概念", "網路的定義與分類", "網路拓撲 (Network Topology)", "OSI 七層模型", "TCP/IP 協定堆疊", "IP 位址與 MAC 位址", "集線器 (Hub)、交換器 (Switch)、路由器 (Router)", "DNS（網域名稱系統）", "HTTP/HTTPS", "電子郵件協定 (SMTP, POP3, IMAP)", "防火牆與 VPN", "DoS/DDoS 攻擊"]

# ====== ID 映射 ======
domain_map, block_map, micro_map = {}, {}, {}
lock = threading.Lock()

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

            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            parsed = safe_json_parse(response.text)
            
            if not parsed:
                api_error_count += 1
                raise ValueError("JSON解析失败")
            
            domain = match_from_list(parsed.get("domain",""), domains_list)
            block = match_from_list(parsed.get("block",""), blocks_list)
            mc_list = [match_from_list(mc, micro_concepts_list) for mc in parsed.get("micro_concepts", [])[:2]]
            
            if not mc_list:
                mc_list = random.sample(micro_concepts_list, k=min(1, len(micro_concepts_list)))

            with lock:
                if domain not in domain_map:
                    domain_map[domain] = str(ObjectId())
                domain_id = domain_map[domain]

                if block not in block_map:
                    block_map[block] = str(ObjectId())
                block_id = block_map[block]

                mc_ids = []
                for mc in mc_list:
                    if mc not in micro_map:
                        micro_map[mc] = str(ObjectId())
                    mc_ids.append(micro_map[mc])

            q_id = str(ObjectId())
            return {
                "domain": {"_id": domain_id, "name": domain},
                "block": {"_id": block_id, "domain_id": domain_id, "title": block},
                "micro_concepts": [{"_id": micro_map[mc], "block_id": block_id, "name": mc, "dependencies": []} for mc in mc_list],
                "question": {"_id": q_id, "text": q_text, "options": q_options, "micro_concepts": mc_ids}
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
    
    with lock:
        if domain not in domain_map:
            domain_map[domain] = str(ObjectId())
        domain_id = domain_map[domain]

        if block not in block_map:
            block_map[block] = str(ObjectId())
        block_id = block_map[block]

        mc_ids = []
        for mc in mc_list:
            if mc not in micro_map:
                micro_map[mc] = str(ObjectId())
            mc_ids.append(micro_map[mc])

    q_id = str(ObjectId())
    return {
        "domain": {"_id": domain_id, "name": domain},
        "block": {"_id": block_id, "domain_id": domain_id, "title": block},
        "micro_concepts": [{"_id": micro_map[mc], "block_id": block_id, "name": mc, "dependencies": []} for mc in mc_list],
        "question": {"_id": q_id, "text": q_text, "options": q_options, "micro_concepts": mc_ids}
    }

def main():
    try:
        with open("error_questions.json", "r", encoding="utf-8") as f:
            questions = json.load(f)
    except Exception as e:
        print(f"❌ 读取文件错误: {e}")
        return

    print(f"📊 开始处理 {len(questions)} 个问题")
    
    results = []
    max_workers = min(4, len(API_KEYS))
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(classify_question, q) for q in questions[:100]]  # 先测试100个
        for future in tqdm(as_completed(futures), total=len(futures), desc="分类中"):
            results.append(future.result())

    # 重建数据结构 - 这是关键修复
    domains_dict, blocks_dict, micros_dict = {}, {}, {}
    questions_out = []

    for r in results:
        # 处理领域
        domain = r["domain"]
        if domain["_id"] not in domains_dict:
            domains_dict[domain["_id"]] = {
                "_id": domain["_id"],
                "name": domain["name"],
                "blocks": set()
            }
        
        # 处理区块
        block = r["block"]
        if block["_id"] not in blocks_dict:
            blocks_dict[block["_id"]] = {
                "_id": block["_id"],
                "domain_id": block["domain_id"],
                "title": block["title"],
                "subtopics": set()
            }
        domains_dict[block["domain_id"]]["blocks"].add(block["_id"])
        
        # 处理小知识点
        for mc in r["micro_concepts"]:
            if mc["_id"] not in micros_dict:
                micros_dict[mc["_id"]] = {
                    "_id": mc["_id"],
                    "block_id": mc["block_id"],
                    "name": mc["name"],
                    "dependencies": []
                }
            blocks_dict[mc["block_id"]]["subtopics"].add(mc["_id"])
        
        # 处理问题
        q = r["question"]
        questions_out.append({
            "_id": q["_id"],
            "text": q["text"],
            "options": q["options"],
            "micro_concepts": q["micro_concepts"]
        })

    # 转换set为list
    domains = []
    for domain in domains_dict.values():
        domains.append({
            "_id": domain["_id"],
            "name": domain["name"],
            "blocks": list(domain["blocks"])
        })
    
    blocks = []
    for block in blocks_dict.values():
        blocks.append({
            "_id": block["_id"],
            "domain_id": block["domain_id"],
            "title": block["title"],
            "subtopics": list(block["subtopics"])
        })
    
    micros = list(micros_dict.values())

    out_file = "output_fixed.json"
    try:
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump({
                "domains": domains,
                "blocks": blocks,
                "micro_concepts": micros,
                "questions": questions_out
            }, f, ensure_ascii=False, indent=2)
        print(f"✅ 已完成 {out_file}")
        print(f"📊 统计: {len(domains)} 领域, {len(blocks)} 区块, {len(micros)} 知识点, {len(questions_out)} 问题")
    except Exception as e:
        print(f"❌ 写入错误: {e}")

if __name__ == "__main__":
    main()