#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG AI回應器 - 簡化清潔版本
只支援中文，簡化問題分類邏輯
"""

from typing import Dict, List, Any, Optional
import json
import logging
import requests
from datetime import datetime

# 導入配置
try:
    from . import config
except ImportError:
    import config

# 設定日誌
logger = logging.getLogger(__name__)

class AIResponder:
    
    def __init__(self, language: str = 'chinese', rag_processor: Optional[Any] = None, ai_model: str = None):
        """
        初始化AI回應器
        
        Args:
            language: 語言設定（固定為中文）
            rag_processor: RAG處理器實例
            ai_model: AI模型名稱
        """
        self.language = 'chinese'  # 固定為中文
        self.rag_processor = rag_processor
        # AI模型配置
        self.ai_model = ai_model 
    
    def answer_question(self, question: str, use_ai: bool = True) -> Dict[str, Any]:
        """
        回答問題的主要方法
        
        Args:
            question: 用戶問題
            use_ai: 是否使用AI（保留參數，實際總是使用AI）
            
        Returns:
            Dict: 包含回答和相關信息的字典
        """
        try:
            # 1. AI智能問題分類 - 判斷是否需要查詢資料庫
            question_category = self._classify_question_intent(question)

            # 2. 根據問題類型決定處理方式
            if question_category == 'non_academic':
                # 非學術問題，不需要查詢資料庫
                return self._handle_non_academic(question)
            else:
                return self._handle_academic(question)
                
        except Exception as e:
            logger.error(f"❌ 回答問題時發生錯誤: {e}")
            return {
                "詳細回答": "抱歉，處理您的問題時遇到了技術問題。請稍後再試，或者換個方式提問。",
            }
    
    def _classify_question_intent(self, question: str) -> str:
        """
        使用AI智能分類問題意圖，判斷是否需要查詢資料庫
        
        Args:
            question: 用戶問題
            
        Returns:
            str: 問題類型 ('non_academic', 'mis_academic')
        """
        try:
            # 使用AI進行問題分類
            classification_prompt = f"""你是一位專業的教學助理。請分析以下問題，判斷它是否為資管學術問題：

問題：{question}

分類標準：
- mis_academic（資管學術）：資訊管理、作業系統、資料庫、網路、程式設計、演算法、資料結構、系統分析、軟體工程等專業問題
- non_academic（非學術）：問候語、身份詢問、能力詢問、感謝、道別、一般知識等其他問題

請只回答：mis_academic 或 non_academic"""
            
            response = requests.post(
                f"{self.ai_base_url}/api/generate",
                json={
                    "model": self.ai_model,
                    "prompt": classification_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 50
                    }
                },
                timeout=15
            )
            
            if response.status_code == 200:
                ai_response = response.json().get('response', '').strip().lower()
                
                if 'mis_academic' in ai_response or '資管學術' in ai_response:
                    return 'mis_academic'
                else:
                    return 'non_academic'
            else:
                return 'non_academic'
                
        except Exception as e:
            logger.warning(f"AI分類失敗: {e}")
            return 'non_academic'
    
    def _handle_non_academic(self, question: str) -> Dict[str, Any]:
        """
        處理非學術問題，使用AI直接回答，不查詢資料庫
        """
        
        try:
            prompt = f"""你是一位友善的資管系智能教學助理。請回答以下問題：

問題：{question}

請提供自然、有用的回答。如果是問候或身份詢問，請介紹自己是資管系AI教學助理。
如果是一般知識問題，請提供簡潔的回答並引導用戶提問資管相關問題。"""
            
            response = requests.post(
                f"{self.ai_base_url}/api/generate",
                json={
                    "model": self.ai_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "num_predict": 500
                    }
                },
                timeout=30
            )
            
            if response.status_code == 200:
                ai_answer = response.json().get('response', '').strip()
                detailed_answer = ai_answer if ai_answer else f"您好！我是資管系智能教學助理。關於「{question}」，我很樂意為您解答。有什麼資管相關問題想要討論嗎？"
            else:
                detailed_answer = f"您好！我是資管系智能教學助理。關於「{question}」，我很樂意為您解答。有什麼資管相關問題想要討論嗎？"
                
        except Exception as e:
            logger.warning(f"AI回答非學術問題失敗: {e}")
            detailed_answer = f"您好！我是資管系智能教學助理。關於「{question}」，我很樂意為您解答。有什麼資管相關問題想要討論嗎？"
            
        return {
            "詳細回答": detailed_answer,
            "時間戳": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    def _handle_academic(self, question: str) -> Dict[str, Any]:
        """
        處理資管學術問題，查詢向量資料庫
        """
        
        # 如果有RAG處理器，使用完整的RAG流程
        if self.rag_processor and hasattr(self.rag_processor, 'collection') and self.rag_processor.collection:
            try:
                # 搜索相關知識
                search_results = self.rag_processor.search_knowledge(question, top_k=5)
                if search_results:
                    # 基於搜索結果生成回答
                    return self._generate_answer_from_search(question, search_results)
                else:
                    # 沒有搜索結果時的處理
                    return self._generate_fallback_academic_answer(question)

            except Exception as e:
                logger.warning(f"⚠️ RAG處理過程中出現錯誤: {e}")
                return self._generate_fallback_academic_answer(question)
        else:
            logger.warning("⚠️ 向量資料庫未初始化")
            return self._generate_fallback_academic_answer(question)
    
    def _generate_answer_from_search(self, question: str, search_results: List[Dict]) -> Dict[str, Any]:
        """基於搜索結果生成回答"""
        # 提取最相關的結果
        best_result = search_results[0] if search_results else {}
        
        # 構建基於搜索結果的回答
        content = best_result.get('content', '')
        title = best_result.get('title', '相關知識')
        
        detailed_answer = f"""
📚 **關於「{question}」的回答**

**基本概念：**
{content}

**相關知識點：**
{title}

**學習建議：**
建議您深入理解這個概念的核心原理，並嘗試將其與實際應用場景結合。

💡 **提示**：如需更詳細的解釋，請提出更具體的問題。
"""
        
        return {
            "科目": best_result.get('subject', '資訊管理'),
            "教材": best_result.get('source', '教學資料'),
            "知識點": title,
            "詳細回答": detailed_answer.strip(),
            "相關概念": " | ".join(best_result.get('keywords', ['相關概念'])),
            "時間戳": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    def _generate_fallback_academic_answer(self, question: str) -> Dict[str, Any]:
        """當無法查詢資料庫時的學術問題回答"""
        detailed_answer = f"""
📚 **關於「{question}」的回答**

這是一個很好的資管相關問題！由於目前向量資料庫正在配置中，我先為您提供一個基本的回答框架：

**概念解釋：**
這個概念在資管系課程中是一個重要的主題，涉及到理論和實務的結合。

**重要特點：**
• 具有系統性的特徵
• 在實際應用中很常見
• 需要理解其基本原理

**學習建議：**
建議您可以從基礎概念開始，逐步深入理解其應用場景。

💡 **提示**：完整的RAG系統配置完成後，我將能提供更詳細和準確的回答！
"""

        return {
            "科目": "資訊管理",
            "教材": "基礎教材",
            "知識點": "基礎概念",
            "詳細回答": detailed_answer.strip(),
            "相關概念": "資管概念 | 系統思維",
            "問題類型": "資管學術問題",
            "時間戳": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    
    def format_response_for_display(self, response: Dict) -> str:
        """格式化回應以供顯示"""
        if isinstance(response, dict) and '詳細回答' in response:
            return response['詳細回答']
        elif isinstance(response, str):
            return response
        else:
            return "抱歉，無法格式化回應。"
