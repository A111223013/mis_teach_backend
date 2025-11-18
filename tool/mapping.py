import sys
import io
from pymongo import MongoClient

# 設置 UTF-8 輸出（解決 Windows 編碼問題）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 連接 MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["MIS_Teach"]   # 換成你的資料庫名稱
collection = db["exam"]   # 換成你的 collection 名稱

# 知識點映射表：將所有不符合標準的大知識點映射到11個標準大知識點
# 根據 data_processor.py 定義的標準知識點體系

# 11個標準大知識點（定義在 data_processor.py knowledge_domains 中）：
# 1. 數位邏輯（Digital Logic）
# 2. 作業系統（Operating System）
# 3. 資料結構（Data Structure）
# 4. 電腦網路（Computer Network）
# 5. 資料庫（Database）
# 6. AI與機器學習（AI & Machine Learning）
# 7. 資訊安全（Information Security）
# 8. 雲端與虛擬化（Cloud & Virtualization）
# 9. 管理資訊系統（MIS）
# 10. 軟體工程與系統開發（Software Engineering）
# 11. 數學與統計（Mathematics & Statistics）

STANDARD_KEY_POINTS = [
    "數位邏輯",
    "作業系統",
    "資料結構",
    "電腦網路",
    "資料庫",
    "AI與機器學習",
    "資訊安全",
    "雲端與虛擬化",
    "MIS",
    "軟體工程與系統開發",
    "數學與統計"
]

mapping = {
    # === 原本的基本計概 → 重新映射 ===
    # 計算複雜度、演算法相關 → 資料結構
    "計算複雜度": "資料結構",
    "計算複雜度理論": "資料結構",
    "遞迴": "資料結構",
    "Subset Sum 問題": "資料結構",
    "停止問題": "資料結構",
    "圖靈機": "資料結構",
    "可計算性": "資料結構",
    "NP-complete": "資料結構",
    "NP-complete問題": "資料結構",
    "計算理論": "資料結構",
    # 計算機基礎概念 → 軟體工程與系統開發
    "計算機概論": "軟體工程與系統開發",
    "電腦科學概論": "軟體工程與系統開發",
    "電腦科學基礎": "軟體工程與系統開發",
    "電腦科學基礎概念": "軟體工程與系統開發",
    
    # === 數位邏輯（Digital Logic）===
    "數位邏輯": "數位邏輯",
    "布林代數": "數位邏輯",
    "數制轉換": "數位邏輯",
    "數量表示法": "數位邏輯",
    "數位系統與類比系統": "數位邏輯",
    "邏輯準位與二進位表示法": "數位邏輯",
    "補數": "數位邏輯",
    "數位積體電路": "數位邏輯",
    "PLD": "數位邏輯",
    "基本邏輯關係": "數位邏輯",
    "邏輯閘": "數位邏輯",
    "或閘": "數位邏輯",
    "及閘": "數位邏輯",
    "反閘": "數位邏輯",
    "反或閘": "數位邏輯",
    "反及閘": "數位邏輯",
    "互斥或閘": "數位邏輯",
    "互斥反或閘": "數位邏輯",
    "布林代數特質": "數位邏輯",
    "單變數定理": "數位邏輯",
    "多變數定理": "數位邏輯",
    "第摩根定理": "數位邏輯",
    "布林代數式簡化": "數位邏輯",
    "卡諾圖": "數位邏輯",
    "組合邏輯設計": "數位邏輯",
    "CPU架構": "數位邏輯",
    "電腦架構": "數位邏輯",
    
    # === 作業系統（Operating System）===
    "作業系統": "作業系統",
    "作業系統結構": "作業系統",
    "行程": "作業系統",
    "行程觀念": "作業系統",
    "執行緒": "作業系統",
    "執行緒與並行性": "作業系統",
    "並行性": "作業系統",
    "CPU排程": "作業系統",
    "CPU 排班": "作業系統",
    "同步工具": "作業系統",
    "同步範例": "作業系統",
    "死結": "作業系統",
    "主記憶體": "作業系統",
    "記憶體階層": "作業系統",
    "虛擬記憶體": "作業系統",
    "大量儲存結構": "作業系統",
    "輸入輸出系統": "作業系統",
    "輸入/輸出系統": "作業系統",
    "遠端登入": "作業系統",
    
    # === 資料結構（Data Structure）===
    "資料結構": "資料結構",
    "資料結構定義": "資料結構",
    "資料結構對程式效率影響": "資料結構",
    "演算法": "資料結構",
    "演算法定義": "資料結構",
    "演算法定義,程式效率分析": "資料結構",
    "演算法效率分析": "資料結構",
    "程式效率分析": "資料結構",
    "程式效率": "資料結構",
    "一維陣列": "資料結構",
    "二維陣列": "資料結構",
    "陣列": "資料結構",
    "單向鏈結串列": "資料結構",
    "雙向鏈結串列": "資料結構",
    "環狀鏈結串列": "資料結構",
    "鏈結串列": "資料結構",
    "佇列": "資料結構",
    "堆疊": "資料結構",
    "二元樹": "資料結構",
    "二元搜尋樹": "資料結構",
    "樹狀結構": "資料結構",
    
    # === 電腦網路（Computer Network）===
    "網路": "電腦網路",
    "電腦網路": "電腦網路",
    "網路協定": "電腦網路",
    "TCP/IP": "電腦網路",
    "TCP/IP 通訊協定": "電腦網路",
    "通訊協定": "電腦網路",
    "區域網路": "電腦網路",
    "區域網路拓樸": "電腦網路",
    "區域網路開放架構": "電腦網路",
    "區域網路元件": "電腦網路",
    "區域網路連線": "電腦網路",
    "訊號": "電腦網路",
    "訊號傳輸": "電腦網路",
    "調變": "電腦網路",
    "類比傳輸": "電腦網路",
    "數位傳輸": "電腦網路",
    "網頁開發": "電腦網路",
    
    # === 資料庫（Database）===
    "資料庫": "資料庫",
    "資料庫由來": "資料庫",
    "資料庫管理系統": "資料庫",
    "DBMS": "資料庫",
    "資料模型": "資料庫",
    "三層式架構": "資料庫",
    "個體關係模型": "資料庫",
    "ER模型": "資料庫",
    "主鍵": "資料庫",
    "外部鍵": "資料庫",
    "正規化": "資料庫",
    "SQL": "資料庫",
    "SQL 語言": "資料庫",
    "SSMS": "資料庫",
    "資料型別": "資料庫",
    "數據分析": "資料庫",
    "資料探勘": "資料庫",
    
    # === AI與機器學習（AI & Machine Learning）===
    "AI": "AI與機器學習",
    "AI與機器學習": "AI與機器學習",
    "機器學習": "AI與機器學習",
    "AI 工程": "AI與機器學習",
    "基礎模型": "AI與機器學習",
    "AI 應用": "AI與機器學習",
    "訓練數據": "AI與機器學習",
    "建模": "AI與機器學習",
    "後訓練": "AI與機器學習",
    "取樣": "AI與機器學習",
    "語言建模": "AI與機器學習",
    "提示工程": "AI與機器學習",
    "RAG": "AI與機器學習",
    "代理": "AI與機器學習",
    "記憶管理": "AI與機器學習",
    "微調": "AI與機器學習",
    "數據調理": "AI與機器學習",
    "數據增強": "AI與機器學習",
    "與機器學習": "AI與機器學習",  # 從圖片中看到的奇怪知識點
    
    # === 資訊安全（Information Security）===
    "資訊安全": "資訊安全",
    "資訊安全概論": "資訊安全",
    "資訊法律": "資訊安全",
    "資訊安全事件": "資訊安全",
    "資訊安全威脅": "資訊安全",
    "認證": "資訊安全",
    "授權": "資訊安全",
    "存取控制": "資訊安全",
    "資訊安全架構": "資訊安全",
    "資訊安全設計": "資訊安全",
    "密碼學": "資訊安全",
    "基礎密碼學": "資訊安全",
    "資訊系統安全": "資訊安全",
    "網路安全": "資訊安全",
    "防火牆": "資訊安全",
    "使用政策": "資訊安全",
    "入侵偵測": "資訊安全",
    "防禦系統": "資訊安全",
    "惡意程式": "資訊安全",
    "防毒": "資訊安全",
    "資訊安全營運": "資訊安全",
    "資訊安全管理": "資訊安全",
    "開發維運安全": "資訊安全",
    
    # === 雲端與虛擬化（Cloud & Virtualization）===
    "雲端": "雲端與虛擬化",
    "雲端與虛擬化": "雲端與虛擬化",
    "虛擬化": "雲端與虛擬化",
    "CPU虛擬化": "雲端與虛擬化",
    "伺服器虛擬化": "雲端與虛擬化",
    "存儲虛擬化": "雲端與虛擬化",
    "網路虛擬化": "雲端與虛擬化",
    "Xen": "雲端與虛擬化",
    "KVM": "雲端與虛擬化",
    "RHEV": "雲端與虛擬化",
    "VMware": "雲端與虛擬化",
    "VirtualBox": "雲端與虛擬化",
    "Hyper-V": "雲端與虛擬化",
    "Qemu": "雲端與虛擬化",
    "Libvirt": "雲端與虛擬化",
    "XML配置": "雲端與虛擬化",
    "WebVirtMgr": "雲端與虛擬化",
    "SDN": "雲端與虛擬化",
    "RAID": "雲端與虛擬化",
    "邏輯卷管理": "雲端與虛擬化",
    
    # === 管理資訊系統（MIS）===
    "MIS": "MIS",
    "管理資訊系統": "MIS",
    "全球企業資訊系統": "MIS",
    "電子化企業": "MIS",
    "協同合作": "MIS",
    "資訊系統": "MIS",
    "資訊系統組織": "MIS",
    "資訊系統策略": "MIS",
    "資訊科技基礎建設": "MIS",
    "新興科技": "MIS",
    "資料庫與資訊管理": "MIS",
    "電傳通訊": "MIS",
    "網際網路": "MIS",
    "無線科技": "MIS",
    "企業系統應用": "MIS",
    "電子商務": "MIS",
    "數位市場": "MIS",
    "知識管理": "MIS",
    "建立資訊系統": "MIS",
    "管理專案": "MIS",
    "全球系統": "MIS",
    "系統分析與設計": "MIS",
    
    # === 軟體工程與系統開發（Software Engineering）===
    "軟體工程": "軟體工程與系統開發",
    "軟體工程與系統開發": "軟體工程與系統開發",
    "軟體工程定義": "軟體工程與系統開發",
    "軟體工程流程": "軟體工程與系統開發",
    "軟體系統": "軟體工程與系統開發",
    "開發程序": "軟體工程與系統開發",
    "需求工程": "軟體工程與系統開發",
    "系統模型": "軟體工程與系統開發",
    "軟體系統架構": "軟體工程與系統開發",
    "軟體系統架構設計": "軟體工程與系統開發",
    "物件導向": "軟體工程與系統開發",
    "物件導向設計": "軟體工程與系統開發",
    "物件導向實務": "軟體工程與系統開發",
    "系統測試": "軟體工程與系統開發",
    "系統測試流程": "軟體工程與系統開發",
    "軟體系統管理": "軟體工程與系統開發",
    "軟體維護": "軟體工程與系統開發",
    "品質管理": "軟體工程與系統開發",
    "設計模式": "軟體工程與系統開發",
    "軟體重構": "軟體工程與系統開發",
    "資料庫系統開發": "軟體工程與系統開發",
    "跨平台開發": "軟體工程與系統開發",
    "程式語言": "軟體工程與系統開發",  # 程式語言相關歸類到軟體工程
    
    # === 數學與統計（Mathematics & Statistics）===
    "數學": "數學與統計",
    "統計": "數學與統計",
    "數學與統計": "數學與統計",
    "集合論": "數學與統計",
    "數列": "數學與統計",
    "級數": "數學與統計",
    "極限": "數學與統計",
    "微分": "數學與統計",
    "積分": "數學與統計",
    "機率": "數學與統計",
    "統計推論": "數學與統計",
    "常態分配": "數學與統計",
    "假設檢定": "數學與統計",
    "線性代數": "數學與統計",
    "矩陣": "數學與統計",
    "向量": "數學與統計",
    "特徵值": "數學與統計",
    "線性代數矩陣向量特徵值": "數學與統計",  # 從圖片中看到的完整知識點
    "數理邏輯": "數學與統計",
    "離散數學": "數學與統計",
    "離散數學關係函數圖論": "數學與統計",  # 從圖片中看到的完整知識點
    "關係": "數學與統計",
    "函數": "數學與統計",
    "圖論": "數學與統計",
}

# 更新 MongoDB 中的 key-points
def main():
    try:
        # 測試連接
        client.admin.command('ping')
        print("[OK] MongoDB 連接成功")
        
        # 檢查集合是否存在
        collections = db.list_collection_names()
        if "exam" not in collections:
            print(f"[ERROR] 找不到 'exam' collection")
            print(f"可用的 collections: {collections}")
            return
        
        # 檢查集合中的資料總數
        total_count = collection.count_documents({})
        print(f"\n[DEBUG] exam collection 總共有 {total_count} 筆資料")
        
        # 檢查 key-points 欄位是否存在
        sample = collection.find_one({})
        if sample:
            print(f"[DEBUG] 範例文件欄位：{list(sample.keys())}")
            if "key-points" in sample:
                print(f"[DEBUG] 範例 key-points 值：{sample.get('key-points')}")
            else:
                print("[WARNING] 文件沒有 'key-points' 欄位！")
                # 查看是否有其他類似的欄位
                similar_fields = [k for k in sample.keys() if 'point' in k.lower() or '知識' in k or 'key' in k.lower()]
                if similar_fields:
                    print(f"[INFO] 找到類似的欄位：{similar_fields}")
        
        # 先查看資料庫中實際有哪些 key-points 值
        print("\n[DEBUG] 資料庫中實際的 key-points 值（全部）：")
        distinct_points = collection.distinct("key-points")
        if distinct_points:
            non_null_points = [p for p in distinct_points if p]
            print(f"總共有 {len(non_null_points)} 個不同的 key-points 值：")
            for point in sorted(non_null_points):
                count = collection.count_documents({"key-points": point})
                is_standard = point in STANDARD_KEY_POINTS
                status = "[標準]" if is_standard else "[需映射]"
                print(f"  {status} {point}: {count} 筆")
        else:
            print("  [WARNING] 沒有找到任何 key-points 值")
        
        # 檢查是否有 micro_concepts 欄位
        sample_with_micro = collection.find_one({"micro_concepts": {"$exists": True}})
        if sample_with_micro:
            print(f"\n[DEBUG] 範例 micro_concepts: {sample_with_micro.get('micro_concepts', [])}")
        
        # 找出所有非標準的 key-points，並自動映射
        print("\n[INFO] 開始執行映射更新...")
        non_standard_points = [p for p in distinct_points if p and p not in STANDARD_KEY_POINTS]
        
        total_updated = 0
        mapped_count = 0
        
        # 先處理明確的映射
        for old, new in mapping.items():
            count = collection.count_documents({"key-points": old})
            if count > 0:
                result = collection.update_many(
                    {"key-points": old},
                    {"$set": {"key-points": new}}
                )
                if result.modified_count > 0:
                    print(f"[OK] {old} -> {new} (更新 {result.modified_count} 筆資料)")
                    total_updated += result.modified_count
                    mapped_count += 1
        
        # 處理未在映射表中但也不符合標準的 key-points
        remaining_non_standard = [p for p in non_standard_points if p not in mapping]
        if remaining_non_standard:
            print(f"\n[WARNING] 發現 {len(remaining_non_standard)} 個未映射的非標準 key-points:")
            for point in sorted(remaining_non_standard):
                count = collection.count_documents({"key-points": point})
                print(f"  - {point}: {count} 筆 (需要手動添加到映射表)")
        
        print(f"\n[SUMMARY] 總共更新 {total_updated} 筆資料")
        print(f"[SUMMARY] 處理了 {mapped_count} 個映射規則")
        print(f"[SUMMARY] 標準大知識點列表: {', '.join(STANDARD_KEY_POINTS)}")
        
    except Exception as e:
        print(f"[ERROR] 錯誤：{str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()