#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI批改模組 - 簡化版本，不依賴aiohttp
"""

import json
from typing import Dict, Any, Tuple, List
from accessories import mongo
from bson import ObjectId
from tool.api_keys import get_api_key, get_api_keys_count

class AnswerGrader:
    """答案批改器"""
    
    def __init__(self):
        self.supported_types = {
            'single-choice': self._grade_single_choice,
            'multiple-choice': self._grade_multiple_choice,
            'true-false': self._grade_true_false,
            'fill-in-the-blank': self._grade_fill_in_blank,
            'short-answer': self._grade_short_answer,
            'long-answer': self._grade_long_answer,
            'group': self._grade_group_question
        }
    
    def grade_answer(self, question_id: str, user_answer: Any, question_type: str = None) -> Tuple[bool, float, Dict[str, Any]]:
        """批改單個答案"""
        try:
            # 從MongoDB獲取題目詳情
            question = self._get_question_by_id(question_id)
            if not question:
                return False, 0, {'error': '題目不存在'}
            
            # 獲取題目類型
            if not question_type:
                question_type = self._get_question_type(question)
            
            # 根據題目類型進行批改
            if question_type in self.supported_types:
                return self.supported_types[question_type](question, user_answer)
            else:
                return False, 0, {'error': f'不支持的題目類型: {question_type}'}
                
        except Exception as e:
            return False, 0, {'error': f'批改失敗: {str(e)}'}
    
    def batch_grade_ai_questions(self, questions_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """批量批改需要AI評分的題目（同步版本）"""
        if not questions_data:
            return []
        
        print(f"🔑 可用API密鑰數量: {get_api_keys_count()}")
        print(f"🔑 隨機API密鑰: {get_api_key()[:20]}...")
        
        results = []
        for question_data in questions_data:
            try:
                question_id = question_data['question_id']
                user_answer = question_data['user_answer']
                question_type = question_data['question_type']
                
                # 獲取題目詳情
                question = self._get_question_by_id(question_id)
                if not question:
                    results.append({
                        'question_id': question_id,
                        'is_correct': False,
                        'score': 0,
                        'feedback': {'error': '題目不存在'}
                    })
                    continue
                
                # 使用簡單AI評分
                is_correct, score, feedback = self._simple_ai_grading(
                    user_answer, 
                    question.get('answer', ''),
                    question.get('detail-answer', ''),
                    question.get('key-points', []),
                    question_type
                )
                
                results.append({
                    'question_id': question_id,
                    'is_correct': is_correct,
                    'score': score,
                    'feedback': feedback
                })
                
            except Exception as e:
                results.append({
                    'question_id': question_data.get('question_id', ''),
                    'is_correct': False,
                    'score': 0,
                    'feedback': {'error': f'批改失敗: {str(e)}'}
                })
        
        return results
    
    def _get_question_by_id(self, question_id: str) -> Dict[str, Any]:
        """從MongoDB獲取題目"""
        try:
            # 嘗試使用ObjectId查詢
            question = mongo.db.exam.find_one({"_id": ObjectId(question_id)})
            if not question:
                # 如果ObjectId查詢失敗，嘗試直接查詢
                question = mongo.db.exam.find_one({"_id": question_id})
            return question
        except Exception as e:
            print(f"⚠️ 獲取題目失敗: {e}")
            return None
    
    def _get_question_type(self, question: Dict[str, Any]) -> str:
        """獲取題目類型"""
        exam_type = question.get('type', 'single')
        if exam_type == 'group':
            # 如果是題組，讀取子題目的answer_type
            sub_questions = question.get('sub_questions', [])
            if sub_questions:
                return sub_questions[0].get('answer_type', 'single-choice')
            else:
                return 'single-choice'
        else:
            # 如果是單題，直接讀取answer_type
            return question.get('answer_type', 'single-choice')
    
    def _grade_single_choice(self, question: Dict[str, Any], user_answer: Any) -> Tuple[bool, float, Dict[str, Any]]:
        """批改單選題"""
        correct_answer = question.get('answer', '')
        is_correct = str(user_answer).strip() == str(correct_answer).strip()
        score = 100 if is_correct else 0
        
        feedback = {
            'user_answer': user_answer,
            'reference_answer': correct_answer,
            'is_correct': is_correct,
            'score': score,
            'explanation': '單選題完全匹配評分'
        }
        
        return is_correct, score, feedback
    
    def _grade_multiple_choice(self, question: Dict[str, Any], user_answer: Any) -> Tuple[bool, float, Dict[str, Any]]:
        """批改多選題"""
        correct_answer = question.get('answer', '')
        
        if isinstance(user_answer, list) and isinstance(correct_answer, list):
            is_correct = sorted(user_answer) == sorted(correct_answer)
        else:
            is_correct = str(user_answer) == str(correct_answer)
        
        score = 100 if is_correct else 0
        
        feedback = {
            'user_answer': user_answer,
            'reference_answer': correct_answer,
            'is_correct': is_correct,
            'score': score,
            'explanation': '多選題完全匹配評分'
        }
        
        return is_correct, score, feedback
    
    def _grade_true_false(self, question: Dict[str, Any], user_answer: Any) -> Tuple[bool, float, Dict[str, Any]]:
        """批改是非題"""
        correct_answer = question.get('answer', '')
        
        user_bool = str(user_answer).lower() in ['true', '是', '1', 'yes']
        correct_bool = str(correct_answer).lower() in ['true', '是', '1', 'yes']
        is_correct = user_bool == correct_bool
        score = 100 if is_correct else 0
        
        feedback = {
            'user_answer': user_answer,
            'reference_answer': correct_answer,
            'is_correct': is_correct,
            'score': score,
            'explanation': '是非題完全匹配評分'
        }
        
        return is_correct, score, feedback
    
    def _grade_fill_in_blank(self, question: Dict[str, Any], user_answer: Any) -> Tuple[bool, float, Dict[str, Any]]:
        """批改填空題"""
        correct_answer = question.get('answer', '')
        
        user_text = str(user_answer).strip().lower()
        correct_text = str(correct_answer).strip().lower()
        
        if user_text == correct_text:
            is_correct = True
            score = 100
        elif len(user_text) > 3 and len(correct_text) > 3:
            # 關鍵詞匹配（70%以上）
            user_words = set(user_text.split())
            correct_words = set(correct_text.split())
            if len(user_words.intersection(correct_words)) >= min(len(user_words), len(correct_words)) * 0.7:
                is_correct = True
                score = 80
            else:
                is_correct = False
                score = 0
        else:
            is_correct = False
            score = 0
        
        feedback = {
            'user_answer': user_answer,
            'reference_answer': correct_answer,
            'is_correct': is_correct,
            'score': score,
            'explanation': '填空題關鍵詞匹配評分'
        }
        
        return is_correct, score, feedback
    
    def _grade_short_answer(self, question: Dict[str, Any], user_answer: Any) -> Tuple[bool, float, Dict[str, Any]]:
        """批改簡答題"""
        return self._simple_ai_grading(
            user_answer,
            question.get('answer', ''),
            question.get('detail-answer', ''),
            question.get('key-points', []),
            'short-answer'
        )
    
    def _grade_long_answer(self, question: Dict[str, Any], user_answer: Any) -> Tuple[bool, float, Dict[str, Any]]:
        """批改申論題"""
        return self._simple_ai_grading(
            user_answer,
            question.get('answer', ''),
            question.get('detail-answer', ''),
            question.get('key-points', []),
            'long-answer'
        )
    
    def _grade_group_question(self, question: Dict[str, Any], user_answer: Any) -> Tuple[bool, float, Dict[str, Any]]:
        """批改題組題"""
        sub_questions = question.get('sub_questions', [])
        if not sub_questions:
            return False, 0, {'error': '題組沒有子題目'}
        
        total_score = 0
        total_correct = 0
        
        for sub_q in sub_questions:
            sub_answer = user_answer.get(str(sub_q.get('index', 0)), '')
            sub_type = sub_q.get('answer_type', 'single-choice')
            
            if sub_type in self.supported_types:
                is_correct, score, _ = self.supported_types[sub_type](sub_q, sub_answer)
                if is_correct:
                    total_correct += 1
                total_score += score
        
        avg_score = total_score / len(sub_questions) if sub_questions else 0
        is_correct = avg_score >= 60
        
        feedback = {
            'user_answer': user_answer,
            'reference_answer': '題組題目',
            'is_correct': is_correct,
            'score': avg_score,
            'explanation': f'題組題目，{total_correct}/{len(sub_questions)} 題正確'
        }
        
        return is_correct, avg_score, feedback
    
    def _simple_ai_grading(self, user_answer: str, reference_answer: str, detail_answer: str, key_points: List[str], answer_type: str) -> Tuple[bool, float, Dict[str, Any]]:
        """使用 Gemini API 進行智能評分"""
        try:
            # 嘗試使用 Gemini API 進行評分
            api_key = get_api_key()
            if not api_key:
                print("⚠️ 沒有可用的 API Key，使用關鍵詞匹配評分")
                return self._fallback_keyword_grading(user_answer, reference_answer, detail_answer, key_points, answer_type)
            
            # 構建評分提示
            prompt = self._build_grading_prompt(user_answer, reference_answer, detail_answer, key_points, answer_type)
            
            # 調用 Gemini API
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-pro')
                
                response = model.generate_content(prompt)
                result = self._parse_ai_response(response.text)
                
                if result:
                    return result['is_correct'], result['score'], result['feedback']
                else:
                    print("⚠️ AI 評分失敗，使用關鍵詞匹配評分")
                    return self._fallback_keyword_grading(user_answer, reference_answer, detail_answer, key_points, answer_type)
                    
            except Exception as ai_error:
                print(f"⚠️ Gemini API 調用失敗: {ai_error}")
                return self._fallback_keyword_grading(user_answer, reference_answer, detail_answer, key_points, answer_type)
                
        except Exception as e:
            print(f"❌ AI 評分錯誤: {e}")
            return False, 0, {'error': f'AI 評分失敗: {str(e)}'}
    
    def _fallback_keyword_grading(self, user_answer: str, reference_answer: str, detail_answer: str, key_points: List[str], answer_type: str) -> Tuple[bool, float, Dict[str, Any]]:
        """關鍵詞匹配評分（回退方案）"""
        try:
            # 計算關鍵詞匹配率
            user_words = set(str(user_answer).lower().split())
            reference_words = set(str(reference_answer).lower().split())
            
            if not reference_words:
                return False, 0, {'error': '沒有參考答案'}
            
            # 計算匹配率
            intersection = user_words.intersection(reference_words)
            match_ratio = len(intersection) / len(reference_words)
            
            # 根據題型設置不同的閾值
            if answer_type == 'short-answer':
                threshold = 0.4  # 簡答題要求40%以上匹配
            elif answer_type == 'long-answer':
                threshold = 0.3  # 申論題要求30%以上匹配
            else:
                threshold = 0.5  # 其他題型要求50%以上匹配
            
            # 根據匹配率評分
            if match_ratio >= 0.9:
                score = 95  # 完全正確
                is_correct = True
            elif match_ratio >= 0.8:
                score = 85  # 接近正確
                is_correct = True
            elif match_ratio >= 0.6:
                score = 70  # 勉強及格
                is_correct = True
            elif match_ratio >= threshold:
                score = 60  # 勉強及格
                is_correct = True
            else:
                score = 0   # 完全錯誤
                is_correct = False
            
            feedback = {
                'user_answer': user_answer,
                'reference_answer': reference_answer,
                'detail_answer': detail_answer,
                'key_points': key_points,
                'match_ratio': round(match_ratio, 2),
                'threshold': threshold,
                'is_correct': is_correct,
                'score': score,
                'explanation': f'關鍵詞匹配率: {match_ratio:.1%}，閾值: {threshold:.1%}'
            }
            
            return is_correct, score, feedback
            
        except Exception as e:
            return False, 0, {'error': f'AI評分失敗: {str(e)}'}
    
    def _build_grading_prompt(self, user_answer: str, reference_answer: str, detail_answer: str, key_points: List[str], answer_type: str) -> str:
        """構建 AI 評分提示"""
        prompt = f"""
請作為一位專業的 MIS 課程教師，對以下學生答案進行評分。

題目類型：{answer_type}
學生答案：{user_answer}
參考答案：{reference_answer}
詳細答案：{detail_answer}
關鍵要點：{', '.join(key_points) if key_points else '無'}

評分標準：
- 90-100分：完全正確，答案完整且準確
- 80-89分：接近正確，主要概念正確但有小錯誤
- 60-79分：勉強及格，部分正確但理解不夠深入
- 0-59分：錯誤，主要概念錯誤或答案不完整

請以JSON格式返回評分結果：
{{
    "is_correct": true/false,
    "score": 分數(0-100),
    "feedback": {{
        "explanation": "評分說明",
        "strengths": "優點",
        "weaknesses": "需要改進的地方",
        "suggestions": "學習建議"
    }}
}}
"""
        return prompt
    
    def _parse_ai_response(self, response_text: str) -> Dict[str, Any]:
        """解析 AI 回應"""
        try:
            # 嘗試提取 JSON 部分
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                result = json.loads(json_str)
                
                # 驗證必要字段
                if all(key in result for key in ['is_correct', 'score', 'feedback']):
                    return result
                else:
                    print("⚠️ AI 回應缺少必要字段")
                    return None
            else:
                print("⚠️ 無法從 AI 回應中提取 JSON")
                return None
                
        except Exception as e:
            print(f"⚠️ 解析 AI 回應失敗: {e}")
            return None

# 創建全局實例
grader = AnswerGrader()

def grade_single_answer(question_id: str, user_answer: Any, question_type: str = None) -> Tuple[bool, float, Dict[str, Any]]:
    """批改單個答案的便捷函數"""
    return grader.grade_answer(question_id, user_answer, question_type)

def batch_grade_ai_questions(questions_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """批量批改AI題目的便捷函數（同步版本）"""
    return grader.batch_grade_ai_questions(questions_data)

# 測試函數
def test_grading():
    """測試評分功能"""
    print("🧪 測試評分功能...")
    
    # 測試單選題
    result = grade_single_answer("test_id", "A", "single-choice")
    print(f"單選題測試: {result}")
    
    # 測試API密鑰
    try:
        from tool.api_keys import get_api_key, get_api_keys_count
        print(f"API密鑰數量: {get_api_keys_count()}")
        print(f"隨機密鑰: {get_api_key()[:20]}...")
    except Exception as e:
        print(f"API密鑰測試失敗: {e}")

if __name__ == "__main__":
    test_grading()
