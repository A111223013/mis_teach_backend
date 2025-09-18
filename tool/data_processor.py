#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
數據處理工具
功能：
1. 讀取 fainaldata_no_del.json
2. 過濾私立大學和107年之前的數據
3. 調用AI API檢查和修正知識點對應關係
4. 保存處理後的數據到 20250917_result.json
"""

import json
import os
import sys
import random
import threading
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from dataclasses import dataclass

# 添加項目根目錄到路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 導入API密鑰管理
from api_keys import MultiGroupAPIKeyManager, get_api_key, get_api_keys_count, get_available_groups

try:
    import google.generativeai as genai
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("警告: google-generativeai 未安裝，將使用模擬API")

@dataclass
class ProcessingConfig:
    """數據處理配置"""
    # 文件路徑
    input_file: str = "../data/fainaldata_no_del.json"
    filter_output_file: str = "../data/20250918_result.json"
    ai_output_file: str = "../data/20250918_ai_judged_final.json"
    
    # 過濾設定
    min_year: int = 107  # 民國107年
    schools_to_remove: List[str] = None
    
    # AI設定
    max_workers: int = 6
    progress_interval: int = 50
    
    def __post_init__(self):
        if self.schools_to_remove is None:
            self.schools_to_remove = [
                "義守大學", "聯合大學", "金門大學", "慈濟大學", "中原大學",
                "高雄大學", "東海大學", "長庚大學", "臺中科大", "高雄應用科技大學"
            ]

class DataProcessor:
    def __init__(self, mode="filter"):
        """
        初始化數據處理器
        mode: "filter" - 數據過濾模式, "ai_judge" - AI重新判斷模式
        """
        self.mode = mode
        
        if mode == "filter":
            self.input_file = "../data/fainaldata_no_del.json"
            self.output_file = "../data/20250918_result.json"
        else:  # ai_judge
            self.input_file = "../data/20250918_result.json"  # 使用模式1的輸出
            self.output_file = "../data/20250918_ai_judged_final.json"
        
        self.processed_count = 0
        self.filtered_count = 0
        self.error_count = 0
        self.ai_judged_count = 0
        
        # 定義需要完全移除的學校
        self.schools_to_remove = [
            "義守大學",
            "聯合大學", 
            "金門大學",
            "慈濟大學",
            "中原大學",
            "高雄大學",
            "東海大學",
            "長庚大學",
            "臺中科大",
            "高雄應用科技大學"
        ]
        
        # 定義需要移除的年份（106年之前）
        self.min_year = 107  # 民國107年
        
        # 統計各學校的題目數量
        self.school_stats = {}
        
        # 標準化知識點體系（基於 insert_mongodb.py + 數學與統計領域）
        self.knowledge_domains = {
            "數位邏輯（Digital Logic）": [
                "數量表示法", "數位系統與類比系統", "邏輯準位與二進位表示法", "數位積體電路與 PLD 簡介",
                "基本邏輯關係與布林代數", "或閘、及閘與反閘", "反或閘與反及閘", "互斥或閘與互斥反或閘",
                "布林代數特質", "單變數定理", "多變數定理與第摩根定理", "布林代數式簡化法", "卡諾圖與組合邏輯設計步驟"
            ],
            "作業系統（Operating System）": [
                "概說", "作業系統結構", "行程觀念", "執行緒與並行性", "CPU 排班",
                "同步工具", "同步範例", "死結", "主記憶體", "虛擬記憶體", "大量儲存結構", "輸入/輸出系統"
            ],
            "資料結構（Data Structure）": [
                "資料結構定義", "資料結構對程式效率影響", "演算法定義", "程式效率分析",
                "一維陣列", "二維陣列", "單向鏈結串列", "雙向與環狀鏈結串列", "佇列", "堆疊", "二元樹與二元搜尋樹"
            ],
            "電腦網路（Computer Network）": [
                "簡介", "訊號", "訊號傳輸", "調變", "類比傳輸與數位傳輸",
                "區域網路拓樸方式", "區域網路開放架構", "區域網路元件", "區域網路連線實作", "TCP/IP 通訊協定"
            ],
            "資料庫（Database）": [
                "1-1 資料庫由來", "1-2 資料庫管理系統", "1-3 資料模型", "1-4 三層式架構",
                "2-1 設計流程", "2-2 個體關係模型", "2-3 主鍵與外部鍵", "2-4 正規化",
                "3-1 SQL 語言", "3-2 SSMS 操作", "4-1 資料型別", "4-2 使用 SQL 敘述新增資料表"
            ],
            "AI與機器學習（AI & Machine Learning）": [
                "1-1 AI 工程崛起", "1-2 基礎模型使用案例", "1-3 AI 應用規劃",
                "2-1 訓練數據與建模", "2-2 後訓練與取樣", "3-1 語言建模指標與精確評估",
                "4-1 模型選擇與設計評估管道", "5-1 提示工程最佳實例", "6-1 RAG 與代理", "6-2 記憶管理",
                "7-1 微調概述與技術", "8-1 數據調理與增強"
            ],
            "資訊安全（Information Security）": [
                "1-1 資訊安全概論", "1-2 資訊法律與事件處理", "1-3 資訊安全威脅",
                "2-1 認證、授權與存取控制", "2-2 資訊安全架構與設計", "2-3 基礎密碼學", "2-4 資訊系統與網路模型",
                "3-1 防火牆與使用政策", "3-2 入侵偵測與防禦系統", "3-3 惡意程式與防毒", "3-4 多層次防禦",
                "4-1 資訊安全營運與管理", "4-2 開發維運安全"
            ],
            "雲端與虛擬化（Cloud & Virtualization）": [
                "1-1 CPU、伺服器、存儲、網路虛擬化", "1-2 Xen、KVM、RHEV 簡介", "1-3 VMware / VirtualBox / Hyper-V",
                "2-1 KVM 原理與架構", "2-2 Qemu 架構與運行模式", "2-3 Qemu 工具介紹",
                "3-1 Libvirt 架構與 API", "3-2 XML 配置文件", "4-1 安裝與使用介紹", "4-2 WebVirtMgr 管理平臺",
                "5-1 軟件 Overlay SDN", "5-2 硬件 Underlay SDN", "6-1 RAID 技術與硬盤接口", "6-2 邏輯卷管理"
            ],
            "管理資訊系統（MIS）": [
                "1-1 現今全球企業的資訊系統", "1-2 全球電子化企業與協同合作", "1-3 資訊系統、組織與策略",
                "2-1 資訊科技基礎建設與新興科技", "2-2 資料庫與資訊管理", "2-3 電傳通訊、網際網路與無線科技", "2-4 資訊系統安全",
                "3-1 企業系統應用", "3-2 電子商務與數位市場", "3-3 知識管理與 AI",
                "4-1 建立資訊系統", "4-2 管理專案與全球系統"
            ],
            "軟體工程與系統開發（Software Engineering）": [
                "1-1 軟體工程定義與流程", "1-2 軟體系統與開發程序", "2-1 需求工程與系統模型",
                "3-1 軟體系統架構設計", "4-1 物件導向設計與實務", "5-1 系統測試流程",
                "6-1 軟體系統管理", "6-2 軟體維護", "7-1 品質管理原則",
                "8-1 設計模式應用", "8-2 軟體重構原則", "9-1 資料庫系統開發流程", "10-1 跨平台開發概念"
            ],
            "數學與統計（Mathematics & Statistics）": [
                "集合論", "數列與級數", "極限", "微分", "積分",
                "機率", "統計推論", "常態分配", "假設檢定",
                "線性代數（矩陣、向量、特徵值）", "數理邏輯", "離散數學（關係、函數、圖論）"
            ]
        }
        
        # 需要移除的大知識點
        self.domains_to_remove = ["基本計概", "計算機概論"]
        
        # 初始化 Gemini API
        if GEMINI_AVAILABLE:
            self.setup_gemini()
    
    def setup_gemini(self):
        """設置 Gemini API"""
        try:
            # 使用API密鑰管理器
            api_key = get_api_key()
            if not api_key:
                print("警告: 未找到可用的API密鑰，將使用模擬API")
                return
            
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-2.0-flash')
            self.api_keys_count = get_api_keys_count()
            
            print(f"Gemini API 初始化成功，可用密鑰數量: {self.api_keys_count}")
        except Exception as e:
            print(f"Gemini API 初始化失敗: {e}")
            self.model = None
            self.api_keys_count = 0
    
    def load_data(self) -> List[Dict[str, Any]]:
        """載入原始數據"""
        try:
            with open(self.input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"成功載入 {len(data)} 筆數據")
            return data
        except Exception as e:
            print(f"載入數據失敗: {e}")
            return []
    
    def count_school_questions(self, data: List[Dict[str, Any]]):
        """統計各學校的題目數量"""
        for item in data:
            school = item.get('school', '')
            if school not in self.school_stats:
                self.school_stats[school] = 0
            self.school_stats[school] += 1
    
    def process_single_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """處理單個數據項目（用於多執行緒）"""
        try:
            if self.mode == "filter":
                # 過濾模式：只保留數據，不進行AI處理
                self.processed_count += 1
                return item
            else:  # ai_judge 模式
                # 1. 預處理題目格式
                processed_item = self.preprocess_question_format(item)
                
                # 2. 檢查是否需要AI判斷
                if self.needs_ai_judgment(processed_item):
                    # 3. 使用AI重新判斷
                    ai_result = self.ai_judge_question(processed_item)
                    if ai_result:
                        processed_item.update(ai_result)
                        self.ai_judged_count += 1
                    else:
                        # AI判斷失敗，保留原始數據
                        print(f"⚠️ AI判斷失敗，保留原始數據")
                        self.error_count += 1
                else:
                    # 不需要AI判斷，直接過濾移除的領域
                    processed_item = self.filter_removed_domains(processed_item)
                
                self.processed_count += 1
                return processed_item
                
        except Exception as e:
            print(f"❌ 處理單個項目時發生錯誤: {e}")
            self.error_count += 1
            return item  # 返回原始數據
    
    def should_filter_item(self, item: Dict[str, Any]) -> bool:
        """判斷是否應該過濾該筆數據"""
        school = item.get('school', '')
        year = item.get('year', '')
        
        # 1. 檢查是否為需要移除的學校
        if school in self.schools_to_remove:
            return True
        
        # 2. 檢查年份是否為106年之前
        try:
            year_int = int(year)
            if year_int < self.min_year:
                return True
        except (ValueError, TypeError):
            # 如果年份無法轉換，保留該筆數據
            pass
        
        return False
    
    def preprocess_question_format(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """預處理題目格式：將非single/group轉換為single格式"""
        item_type = item.get('type', '')
        
        # 如果已經是single或group，直接返回
        if item_type in ['single', 'group']:
            return item
        
        # 創建新的題目格式
        new_item = item.copy()
        
        # 將原本的type保存到answer_type
        original_type = item_type if item_type else 'unknown'
        new_item['answer_type'] = original_type
        
        # 設置為single格式
        new_item['type'] = 'single'
        
        # 如果原本沒有question_text，嘗試從其他字段獲取
        if 'question_text' not in new_item or not new_item['question_text']:
            # 嘗試從其他可能的字段獲取題目內容
            possible_fields = ['content', 'text', 'description', 'title']
            for field in possible_fields:
                if field in new_item and new_item[field]:
                    new_item['question_text'] = str(new_item[field])
                    break
        
        # 確保有answer_type字段
        if 'answer_type' not in new_item:
            new_item['answer_type'] = 'unknown'
        
        print(f"預處理題目格式: {original_type} -> single (保存到answer_type)")
        return new_item
    
    def needs_ai_judgment(self, item: Dict[str, Any]) -> bool:
        """判斷題目是否需要AI重新判斷（重新分類所有知識點）"""
        # 檢查是否包含需要移除的大知識點
        key_points = item.get('key-points', [])
        if isinstance(key_points, str):
            key_points = [key_points]
        
        # 檢查是否包含需要移除的大知識點
        for domain in self.domains_to_remove:
            if any(domain in kp for kp in key_points):
                return True
        
        # 檢查群組題的子題目知識點
        if 'sub_questions' in item:
            for sub_q in item['sub_questions']:
                sub_key_points = sub_q.get('key-points', [])
                if isinstance(sub_key_points, str):
                    sub_key_points = [sub_key_points]
                for domain in self.domains_to_remove:
                    if any(domain in kp for kp in sub_key_points):
                        return True
        
        # 檢查是否有 micro_concepts 字段，如果沒有則需要AI重新分類
        if 'micro_concepts' not in item:
            return True
        
        # 檢查群組題的子題目是否有 micro_concepts 字段
        if 'sub_questions' in item:
            for sub_q in item['sub_questions']:
                if 'micro_concepts' not in sub_q:
                    return True
        
        return False
    
    
    def ai_judge_question(self, question_data: Dict[str, Any]) -> Dict[str, Any]:
        """使用AI重新判斷題目格式和知識點"""
        if not GEMINI_AVAILABLE:
            print("AI API 不可用")
            return None
        
        try:
            # 獲取新的API密鑰
            api_key = get_api_key()
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.0-flash')
            
            # 構建AI判斷提示詞
            prompt = self.build_judgment_prompt(question_data)
            
            # 調用 Gemini API
            response = model.generate_content(
                prompt,
                safety_settings={
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                }
            )
            
            # 解析AI回應
            result = self.parse_ai_judgment(response.text, question_data)
            return result
            
        except Exception as e:
            print(f"AI判斷失敗: {e}")
            return None
    
    def build_judgment_prompt(self, question_data: Dict[str, Any]) -> str:
        """構建AI判斷提示詞"""
        question_text = question_data.get('question_text', '')
        if not question_text and 'group_question_text' in question_data:
            question_text = question_data.get('group_question_text', '')
        
        # 提取知識點信息
        key_points = question_data.get('key-points', [])
        if isinstance(key_points, str):
            key_points = [key_points]
        
        # 構建子題目信息
        sub_questions_info = ""
        if 'sub_questions' in question_data:
            for i, sub_q in enumerate(question_data['sub_questions']):
                sub_questions_info += f"\n子題 {i+1}: {sub_q.get('question_text', '')[:200]}..."
                sub_key_points = sub_q.get('key-points', [])
                if isinstance(sub_key_points, str):
                    sub_key_points = [sub_key_points]
                sub_questions_info += f"\n子題知識點: {sub_key_points}"
        
        # 構建標準化知識點體系說明
        domains_info = ""
        for domain, concepts in self.knowledge_domains.items():
            domains_info += f"\n- {domain}: {', '.join(concepts)}"
        
        prompt = f"""
你是一個教育知識點重新分類專家。你的任務是將題目重新分類到標準化的知識點體系中。

## 標準化知識點體系：
{domains_info}

## 分類規則：
1. **大知識點轉換**：如果原本大知識點是「基本計概」或「計算機概論」，必須重新分類到上述11個領域中的一個
2. **唯一大知識點**：每個題目只能有一個大知識點（key-points）
3. **小知識點隸屬**：小知識點（micro_concepts）必須隸屬於對應的大知識點
4. **一致性檢查**：大知識點和小知識點必須符合邏輯關係
   - 例如：key-points =「資料結構」，micro_concepts 不能是「假設檢定」（屬於數學與統計）
   - 但允許跨領域輔助概念，例如：key-points =「資料結構」，micro_concepts 可以是 ["陣列", "時間複雜度", "機率分析"]
5. **智能分析**：AI需要仔細分析題目內容，判斷最適合的大知識點，然後推斷該領域下的相關小知識點，若題目涉及數理邏輯、機率或統計，應優先歸類到「數學與統計」

## 輸出要求：
- 保持原始資料結構不變
- 重新分類 key-points 為：唯一的大知識點名稱（字符串）
- 重新分類 micro_concepts 為：該大知識點下的相關小知識點列表（數組）
- 格式範例：
  {{
    "key-points": "資料結構（Data Structure）",
    "micro_concepts": ["一維陣列", "二維陣列", "時間複雜度", "空間複雜度"]
  }}
- 必須確保大知識點和小知識點的邏輯一致性
- 輸出為 JSON 格式

## 題目信息：
題目: {question_text[:300]}...
當前知識點: {key_points}
{sub_questions_info}

請分析並輸出重新分類後的JSON格式數據。
"""
        return prompt
    
    def parse_ai_judgment(self, response_text: str, original_data: Dict[str, Any]) -> Dict[str, Any]:
        """解析AI判斷回應"""
        try:
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                result = json.loads(json_str)
                return result
            else:
                print("AI回應格式錯誤，無法解析")
                return None
        except Exception as e:
            print(f"解析AI判斷回應失敗: {e}")
            return None
    
    
    def filter_removed_domains(self, key_points) -> List[str]:
        """過濾掉需要移除的知識點，讓AI重新判斷"""
        if isinstance(key_points, str):
            key_points = [key_points]
        
        # 移除需要刪除的知識點
        filtered_key_points = []
        for kp in key_points:
            kp = kp.strip()
            if kp and not any(domain in kp for domain in self.domains_to_remove):
                filtered_key_points.append(kp)
        
        # 如果沒有有效的知識點，返回空列表（讓AI重新判斷）
        if not filtered_key_points:
            return []
        
        # 直接返回過濾後的知識點列表，讓AI來判斷和分類
        return filtered_key_points
    
    def filter_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """過濾數據：移除指定學校和106年之前的數據"""
        # 先統計各學校的題目數量
        self.count_school_questions(data)
        
        print("各學校題目統計：")
        for school, count in sorted(self.school_stats.items()):
            print(f"  {school}: {count} 題")
        print()
        
        filtered_data = []
        filter_reasons = {
            "指定學校": 0,
            "106年之前": 0
        }
        
        for item in data:
            school = item.get('school', '')
            year = item.get('year', '')
            
            # 檢查是否應該過濾
            if self.should_filter_item(item):
                self.filtered_count += 1
                
                # 記錄過濾原因
                if school in self.schools_to_remove:
                    filter_reasons["指定學校"] += 1
                else:
                    try:
                        year_int = int(year)
                        if year_int < self.min_year:
                            filter_reasons["106年之前"] += 1
                    except (ValueError, TypeError):
                        pass
                continue
            
            filtered_data.append(item)
        
        print("過濾詳情：")
        print(f"  移除指定學校: {filter_reasons['指定學校']} 題")
        print(f"  移除106年之前: {filter_reasons['106年之前']} 題")
        
        print(f"\n過濾完成：移除 {self.filtered_count} 筆數據，保留 {len(filtered_data)} 筆數據")
        return filtered_data
    
    def call_ai_api(self, question_data: Dict[str, Any]) -> Dict[str, Any]:
        """調用AI API檢查和修正知識點（過濾模式）"""
        if not GEMINI_AVAILABLE:
            return self.mock_ai_response(question_data)
        
        try:
            # 獲取新的API密鑰
            api_key = get_api_key()
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.0-flash')
            
            # 構建提示詞
            prompt = self.build_knowledge_point_prompt(question_data)
            
            # 調用 Gemini API
            response = model.generate_content(
                prompt,
                safety_settings={
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                }
            )
            
            # 解析回應
            result = self.parse_ai_response(response.text, question_data)
            return result
            
        except Exception as e:
            print(f"AI API 調用失敗: {e}")
            return self.mock_ai_response(question_data)
    
    def build_knowledge_point_prompt(self, question_data: Dict[str, Any]) -> str:
        """構建知識點修正AI提示詞"""
        # 提取題目信息
        question_text = question_data.get('question_text', '')
        if not question_text and 'group_question_text' in question_data:
            question_text = question_data.get('group_question_text', '')
        
        # 提取知識點
        key_points = question_data.get('key-points', [])
        if isinstance(key_points, str):
            key_points = [key_points]
        
        # 構建子題目信息
        sub_questions_info = ""
        if 'sub_questions' in question_data:
            for i, sub_q in enumerate(question_data['sub_questions']):
                sub_questions_info += f"\n子題 {i+1}: {sub_q.get('question_text', '')[:100]}..."
                sub_key_points = sub_q.get('key-points', [])
                if isinstance(sub_key_points, str):
                    sub_key_points = [sub_key_points]
                sub_questions_info += f"\n子題知識點: {sub_key_points}"
        
        prompt = f"""
你是一個教育知識點對應檢查器。你的任務是根據題目對應的大知識點（key_point）和小知識點（sub_point），確保資料符合以下規則：

1. 一致性檢查：
   - 如果一筆資料的 key_point = X，則至少要有一個 sub_point 屬於 X 的小知識點集合。
   - 不允許出現 key_point = X 卻只有 Y 類小知識點（Y ≠ X）。
   - 允許跨知識點，例如 key_point = A，sub_point 可以包含 A-1 和 C-2。

2. 替換規則：
   - 如果 key_point = "計算機概論"，請將其替換為其他大知識點（隨機或依照最相關的知識點）。
   - 替換後，該資料中不再保留 "計算機概論" 這個大知識點。

3. 輸出格式：
   - 保持原始資料結構不變，只修正或替換知識點。
   - 請輸出為 JSON 格式。

題目信息：
題目: {question_text[:200]}...
當前大知識點: {key_points}
{sub_questions_info}

請分析並輸出修正後的JSON格式數據。
"""
        return prompt
    
    def parse_ai_response(self, response_text: str, original_data: Dict[str, Any]) -> Dict[str, Any]:
        """解析AI回應"""
        try:
            # 嘗試從回應中提取JSON
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                result = json.loads(json_str)
                return result
            else:
                # 如果無法解析JSON，返回原始數據
                return original_data
        except Exception as e:
            print(f"解析AI回應失敗: {e}")
            return original_data
    
    def mock_ai_response(self, question_data: Dict[str, Any]) -> Dict[str, Any]:
        """模擬AI回應（當API不可用時）"""
        # 簡單的規則替換
        result = question_data.copy()
        
        # 替換 "計算機概論" 為其他知識點
        if 'key-points' in result:
            if isinstance(result['key-points'], str) and '計算機概論' in result['key-points']:
                replacements = ['作業系統', '資料結構', '程式語言', '資料庫', '網路概論']
                result['key-points'] = random.choice(replacements)
            elif isinstance(result['key-points'], list):
                result['key-points'] = [
                    random.choice(['作業系統', '資料結構', '程式語言', '資料庫', '網路概論']) 
                    if '計算機概論' in kp else kp 
                    for kp in result['key-points']
                ]
        
        # 處理子題目
        if 'sub_questions' in result:
            for sub_q in result['sub_questions']:
                if 'key-points' in sub_q:
                    if isinstance(sub_q['key-points'], str) and '計算機概論' in sub_q['key-points']:
                        sub_q['key-points'] = random.choice(['作業系統', '資料結構', '程式語言'])
                    elif isinstance(sub_q['key-points'], list):
                        sub_q['key-points'] = [
                            random.choice(['作業系統', '資料結構', '程式語言']) 
                            if '計算機概論' in kp else kp 
                            for kp in sub_q['key-points']
                        ]
        
        return result
    
    def process_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """處理數據"""
        processed_data = []
        
        for i, item in enumerate(data):
            try:
                if self.mode == "filter":
                    # 過濾模式：只保留數據，不進行AI處理
                    processed_data.append(item)
                    self.processed_count += 1
                else:  # ai_judge 模式
                    # AI判斷模式：先預處理格式，再重新判斷知識點
                    # 1. 預處理題目格式
                    processed_item = self.preprocess_question_format(item)
                    
                    # 2. 檢查是否需要AI判斷
                    if self.needs_ai_judgment(processed_item):
                        processed_item = self.ai_judge_question(processed_item)
                        self.ai_judged_count += 1
                    
                    processed_data.append(processed_item)
                    self.processed_count += 1
                
                if (i + 1) % 100 == 0:
                    if self.mode == "ai_judge":
                        print(f"已處理 {i + 1}/{len(data)} 筆數據，AI判斷 {self.ai_judged_count} 筆")
                    else:
                        print(f"已處理 {i + 1}/{len(data)} 筆數據")
                    
            except Exception as e:
                print(f"處理第 {i + 1} 筆數據時出錯: {e}")
                processed_data.append(item)  # 保留原始數據
                self.error_count += 1
        
        return processed_data
    
    def save_data(self, data: List[Dict[str, Any]]):
        """保存處理後的數據"""
        try:
            # 確保輸出目錄存在
            os.makedirs(os.path.dirname(self.output_file), exist_ok=True)
            
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"數據已保存到 {self.output_file}")
            print(f"總計處理 {self.processed_count} 筆數據")
            print(f"過濾掉 {self.filtered_count} 筆數據")
            print(f"處理錯誤 {self.error_count} 筆數據")
            
        except Exception as e:
            print(f"保存數據失敗: {e}")
    

    def run(self):
        """執行完整的數據處理流程"""
        mode_name = "數據過濾" if self.mode == "filter" else "AI重新判斷"
        print(f"🚀 開始{mode_name}...")
        print(f"📁 輸入文件: {self.input_file}")
        print(f"📁 輸出文件: {self.output_file}")
        print("-" * 60)
        
        # 檢查輸入文件是否存在
        if not os.path.exists(self.input_file):
            print(f"❌ 錯誤: 找不到輸入文件 {self.input_file}")
            return
        
        # 1. 載入數據
        print("📊 正在載入數據...")
        data = self.load_data()
        if not data:
            print("❌ 沒有數據需要處理")
            return
        
        print(f"✅ 成功載入 {len(data)} 筆數據")
        
        if self.mode == "filter":
            # 2. 過濾數據
            print("🔍 正在過濾數據...")
            filtered_data = self.filter_data(data)
            if not filtered_data:
                print("❌ 過濾後沒有數據需要處理")
                return
            
            print(f"✅ 過濾完成，保留 {len(filtered_data)} 筆數據")
            
            # 3. 保存過濾後的數據
            print("💾 正在保存過濾後的數據...")
            self.save_data(filtered_data)
            print("✅ 數據過濾完成！")
            
        else:  # ai_judge 模式
            # 2. 使用多執行緒處理AI判斷
            print("🤖 正在進行AI重新判斷...")
            print("⏳ 這可能需要較長時間，請耐心等待...")
            processed_data = self.process_with_multithreading(data, self.process_single_item)
            
            # 3. 保存處理後的數據
            print("💾 正在保存處理後的數據...")
            self.save_data(processed_data)
            print("✅ AI重新判斷完成！")
        
        # 4. 顯示統計信息
        self.print_statistics()
    
    def print_statistics(self):
        """打印統計信息"""
        print("\n" + "=" * 60)
        print("📊 處理統計")
        print("=" * 60)
        print(f"📝 總處理數量: {self.processed_count}")
        print(f"🔍 過濾數量: {self.filtered_count}")
        print(f"🤖 AI判斷數量: {self.ai_judged_count}")
        print(f"❌ 錯誤數量: {self.error_count}")
        
        if self.school_stats:
            print("\n🏫 學校統計:")
            for school, count in sorted(self.school_stats.items(), key=lambda x: x[1], reverse=True):
                status = "✅" if school not in self.schools_to_remove else "❌"
                print(f"  {status} {school}: {count} 題")
        
        print("\n" + "=" * 60)
    
    def ai_convert_knowledge_points(self, data: List[Dict[str, Any]]):
        """使用AI轉換知識點（多執行緒版本）"""
        if not GEMINI_AVAILABLE or not self.model:
            print("AI API 不可用，跳過知識點轉換")
            return
        
        print(f"開始AI知識點轉換，共 {len(data)} 筆數據...")
        print(f"使用 {self.api_keys_count} 個API密鑰進行並行處理")
        
        # 使用多執行緒處理
        converted_data = self.process_with_multithreading(data, self.call_ai_api)
        
        # 保存轉換後的數據
        ai_output_file = "../data/20250917_ai_converted.json"
        try:
            os.makedirs(os.path.dirname(ai_output_file), exist_ok=True)
            with open(ai_output_file, 'w', encoding='utf-8') as f:
                json.dump(converted_data, f, ensure_ascii=False, indent=2)
            print(f"AI知識點轉換完成！共轉換 {len(converted_data)} 筆數據")
            print(f"結果已保存到: {ai_output_file}")
        except Exception as e:
            print(f"保存AI轉換結果失敗: {e}")
    
    def process_with_multithreading(self, data: List[Dict[str, Any]], process_func) -> List[Dict[str, Any]]:
        """多執行緒處理數據"""
        if not data:
            return []
        
        # 計算每個執行緒處理的數據量
        max_workers = min(self.api_keys_count, len(data), 8)  # 最多8個執行緒
        batch_size = max(1, len(data) // max_workers)
        
        print(f"🔄 使用 {max_workers} 個執行緒，每批處理 {batch_size} 筆數據")
        
        # 將數據分批
        batches = []
        for i in range(0, len(data), batch_size):
            batch = data[i:i + batch_size]
            batches.append((i, batch))
        
        # 使用執行緒池處理
        results = [None] * len(data)
        completed_count = 0
        lock = Lock()
        
        def process_batch(batch_info):
            batch_start, batch_data = batch_info
            batch_results = []
            
            for item in batch_data:
                try:
                    result = process_func(item)
                    batch_results.append(result)
                except Exception as e:
                    print(f"❌ 處理數據時出錯: {e}")
                    batch_results.append(item)  # 保留原始數據
            
            # 更新結果
            with lock:
                nonlocal completed_count
                for i, result in enumerate(batch_results):
                    results[batch_start + i] = result
                completed_count += len(batch_data)
                if completed_count % 50 == 0 or completed_count == len(data):
                    progress = (completed_count / len(data)) * 100
                    print(f"⏳ 進度: {completed_count}/{len(data)} ({progress:.1f}%)")
            
            return batch_results
        
        # 執行多執行緒處理
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有批次任務
            future_to_batch = {executor.submit(process_batch, batch): batch for batch in batches}
            
            # 等待所有任務完成
            for future in as_completed(future_to_batch):
                try:
                    future.result()
                except Exception as e:
                    print(f"批次處理失敗: {e}")
        
        return results

def main():
    """主函數"""
    print("=" * 60)
    print("學習分析數據處理工具")
    print("=" * 60)
    print()
    
    # 選擇處理模式
    print("請選擇處理模式：")
    print("1. 數據過濾模式 - 移除指定學校和年份的數據")
    print("2. AI重新判斷模式 - 重新判斷題目格式和知識點分類")
    print()
    print("建議流程：先執行模式1，再執行模式2")
    print()
    
    while True:
        choice = input("請輸入選擇 (1 或 2): ").strip()
        if choice == "1":
            mode = "filter"
            break
        elif choice == "2":
            mode = "ai_judge"
            break
        else:
            print("無效選擇，請輸入 1 或 2")
    
    # 檢查輸入文件是否存在
    input_file = "../data/fainaldata_no_del.json"
    if not os.path.exists(input_file):
        print(f"錯誤: 找不到輸入文件 {input_file}")
        print("請確保文件存在於正確位置")
        return
    
    # 檢查文件大小
    file_size = os.path.getsize(input_file) / (1024 * 1024)  # MB
    print(f"輸入文件大小: {file_size:.2f} MB")
    
    if file_size > 100:  # 大於100MB
        print("警告: 文件較大，處理可能需要較長時間")
        response = input("是否繼續？(y/N): ")
        if response.lower() != 'y':
            print("已取消處理")
            return
    
    print()
    print("開始處理數據...")
    print("-" * 60)
    
    # 執行數據處理
    processor = DataProcessor(mode=mode)
    processor.run()
    
    print()
    print("=" * 60)
    print("處理完成！")
    print("=" * 60)

if __name__ == "__main__":
    main()
