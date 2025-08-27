import json
import re
import concurrent.futures
from typing import List, Dict, Any, Tuple
import google.generativeai as genai
from tool.api_keys import get_api_key, get_api_keys_count

class AnswerGrader:
    """答案批改器 - 簡化版本"""
    
    def __init__(self):
        # 初始化Gemini API
        try:
            api_key = get_api_key()
            genai.configure(api_key=api_key)
            # 使用正確的模型名稱
            self.model = genai.GenerativeModel('gemini-2.0-flash')
        except Exception as e:
            print(f"❌ Gemini API 初始化失敗: {e}")
            self.model = None
    
    def batch_grade_ai_questions(self, questions_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """批量評分AI題目 - 並行處理版本"""
        if not questions_data:
            return []
        
        # 獲取可用的API金鑰數量
        api_keys_count = get_api_keys_count()
        total_questions = len(questions_data)

        # 計算每個API金鑰處理的題目數量
        questions_per_key = total_questions // api_keys_count
        remainder = total_questions % api_keys_count

        # 分配題目給不同的API金鑰
        all_results = [None] * total_questions  # 預分配結果陣列
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=api_keys_count) as executor:
            futures = []
            start_index = 0
            
            for i in range(api_keys_count):
                # 計算這個金鑰要處理的題目數量
                batch_size = questions_per_key + (1 if i < remainder else 0)
                end_index = start_index + batch_size
                
                # 提取這批題目
                questions_batch = questions_data[start_index:end_index]
                batch_indices = list(range(start_index, end_index))  # 記錄原始索引
                
                # 提交任務
                future = executor.submit(
                    self._process_questions_batch, 
                    questions_batch, 
                    batch_indices,
                    i
                )
                futures.append(future)
                
                start_index = end_index
            
            # 收集結果
            for future in concurrent.futures.as_completed(futures):
                try:
                    batch_results = future.result()
                    # 將結果放入正確的位置
                    for result in batch_results:
                        if result and 'original_index' in result:
                            original_idx = result.pop('original_index')
                            all_results[original_idx] = result
                except Exception as e:
                    print(f"❌ 並行處理批次失敗: {e}")
        
        # 過濾掉None值（如果有錯誤的話）
        final_results = [result for result in all_results if result is not None]

        return final_results
    
    def _process_questions_batch(self, questions_batch: List[Dict], batch_indices: List[int], api_key_index: int) -> List[Dict]:
        """處理一批題目（單個API金鑰）"""
        results = []
        
        for i, question_data in enumerate(questions_batch):
            try:
                original_index = batch_indices[i]
                
                # 為這個批次創建專用的Gemini模型實例
                batch_model = self._create_batch_model(api_key_index)
                
                user_answer = question_data['user_answer']
                question_type = question_data['question_type']
                
                is_correct, score, feedback = self._ai_grade_answer_with_model(
                    batch_model,
                    user_answer, 
                    question_data.get('question_text', ''),
                    question_data.get('correct_answer', ''),
                    question_data.get('options', []),
                    question_type
                )
                
                result = {
                    'question_id': question_data['question_id'],
                    'is_correct': is_correct,
                    'score': score,
                    'feedback': feedback,
                    'original_index': original_index,  # 保持原始順序
                    'api_key_used': api_key_index + 1  # 記錄使用的API金鑰
                }
                results.append(result)
                
            except Exception as e:
                print(f"  ❌ API金鑰 {api_key_index+1} 評分題目 {batch_indices[i]+1} 失敗: {e}")
                # 創建錯誤結果
                error_result = {
                    'question_id': question_data.get('question_id', ''),
                    'is_correct': False,
                    'score': 0,
                    'feedback': {'error': f'評分失敗: {str(e)}'},
                    'original_index': batch_indices[i],
                    'api_key_used': api_key_index + 1
                }
                results.append(error_result)
        
        return results
    
    def _create_batch_model(self, api_key_index: int):
        """為批次創建專用的Gemini模型實例"""
        try:
            # 使用指定的API金鑰索引
            api_key = self._get_api_key_by_index(api_key_index)
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.0-flash')
            return model
        except Exception as e:
            print(f"❌ 創建批次模型失敗: {e}")
            return self.model  # 回退到主模型
    
    def _get_api_key_by_index(self, index: int) -> str:
        """根據索引獲取特定的API金鑰"""
        try:
            from tool.api_keys import api_key_manager
            # 獲取所有可用的API金鑰
            all_keys = api_key_manager.api_keys
            if 0 <= index < len(all_keys):
                return all_keys[index]
            else:
                # 如果索引超出範圍，使用隨機選擇
                return get_api_key()
        except Exception as e:
            print(f"⚠️ 獲取指定索引API金鑰失敗，使用隨機選擇: {e}")
            return get_api_key()
    
    def _ai_grade_answer_with_model(self, model, user_answer: Any, question_text: str, correct_answer: str, 
                                    options: List[str], question_type: str) -> Tuple[bool, float, Dict[str, Any]]:
        """使用指定的模型進行AI評分"""
        try:
            
            prompt = self._build_grading_prompt(user_answer, question_text, correct_answer, options, question_type)
            
            if model:
                response = model.generate_content(prompt)
                
                # 調試：顯示AI的完整回應
                print(f"🔍 AI完整回應:")
                print(f"🔍 {response.text}")
                print(f"🔍 回應長度: {len(response.text)}")
                
                result = self._parse_ai_response(response.text)
                if result:
                    print(f"🔍 解析後的結果: {result}")
                    
                    # 確保評分邏輯一致性：分數 ≥ 85 的答案被標記為正確
                    score = result.get('score', 0)
                    is_correct = score >= 85
                    
                    print(f"🔍 AI給的分數: {score}")
                    print(f"🔍 AI判斷的正確性: {result.get('is_correct')}")
                    print(f"🔍 系統計算的正確性: {is_correct}")
                    
                    # 如果AI的判斷與我們的標準不一致，進行修正
                    if result.get('is_correct') != is_correct:
                        print(f"⚠️ AI判斷與系統標準不一致，進行修正")
                        result['is_correct'] = is_correct
                    
                    return result['is_correct'], result['score'], result['feedback']
                else:
                    print(f"❌ AI回應解析失敗")
            
            return False, 0, {'error': 'AI評分失敗'}
            
        except Exception as e:
            print(f"❌ AI評分異常: {str(e)}")
            return False, 0, {'error': f'評分失敗: {str(e)}'}
    
    def _build_grading_prompt(self, user_answer: str, question_text: str, correct_answer: str, 
                             options: List[str], question_type: str) -> str:
        """構建AI評分提示"""
        prompt = f"""
請作為一位專業的MIS課程教師，對以下學生答案進行評分。

**評分任務說明**：
請記住你只需要評分學生的答案，不要評分正確答案。正確答案只是用來參考比較的標準。

**題目資訊**：
題目類型：{question_type}
題目內容：{question_text}

**需要評分的內容**：
學生答案：{user_answer}

**參考標準（不要評分這個）**：
正確答案：{correct_answer}
選項：{options if options else '無'}

**評分重點**：
1. **只評分學生答案的內容**，與正確答案進行比較
2. **學生答案必須與題目內容相關**，不能是無意義的數字或符號
3. 如果學生答案與題目要求完全無關，必須給0分

評分要求：
1. 仔細分析學生答案的內容和邏輯
2. 判斷答案是否正確或部分正確
3. 給出0-100的分數
4. 提供具體的評分理由和改進建議
5. 必須填寫優點、需要改進的地方和學習建議，不能留空

**評分標準**：
- 90-100分：完全正確，答案完整且準確
- 80-89分：接近正確，主要概念正確但有小錯誤
- 60-79分：勉強及格，部分正確但理解不夠深入
- 40-59分：部分正確，有基本概念但錯誤較多
- 0-39分：錯誤，主要概念錯誤或與題目無關

**特別注意**：
- 對於問答題，學生答案必須包含正確答案的核心概念和關鍵信息
- 如果學生只回答數字、符號或與題目無關的內容，必須給0分
- 評分要客觀公正，不能因為學生努力就給高分
- 如果學生答案與題目內容完全無關，必須給0分
- 只有當學生答案在內容上與題目有實質關聯時，才能給分數



**正確性判斷**：
- 分數 ≥ 85分：答案被認為是正確的 (is_correct: true)
- 分數 < 85分：答案被認為是不正確的 (is_correct: false)

請務必以嚴格規範的JSON格式返回評分結果，不要有任何其他文字：
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

**評分示例**：
題目：說明CPU中Instruction Register及Program Counter的用途
學生答案：10
正確答案：Instruction Register (IR)：存放目前正在執行的指令。Program Counter (PC)：存放下一個要執行的指令的記憶體位址
評分：0分，is_correct: false（因為"10"只是數字，與題目完全無關，不包含任何CPU概念）

題目：Linux檔案系統中，"rwx"代表何意義？
學生答案：100
正確答案：r代表讀取權限，w代表寫入權限，x代表執行權限
評分：0分，is_correct: false（因為"100"只是數字，與題目完全無關，不包含任何權限概念）

題目：說明CPU中Instruction Register及Program Counter的用途
學生答案：Instruction Register存放指令，Program Counter存放下一個指令的位址
正確答案：Instruction Register (IR)：存放目前正在執行的指令。Program Counter (PC)：存放下一個要執行的指令的記憶體位址
評分：85分，is_correct: true（因為學生答案包含了正確的核心概念）
"""
        return prompt
    
    def _parse_ai_response(self, response_text: str) -> Dict[str, Any]:
        """解析AI回應"""
        try:
            # 嘗試提取JSON部分
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                result = json.loads(json_str)
                
                # 驗證必要字段
                if all(key in result for key in ['is_correct', 'score', 'feedback']):
                    # 確保 feedback 字段完整
                    feedback = result.get('feedback', {})
                    if not feedback.get('strengths') or feedback.get('strengths') == '無':
                        feedback['strengths'] = '勇於嘗試，認真作答'
                    if not feedback.get('weaknesses') or feedback.get('weaknesses') == '無':
                        feedback['weaknesses'] = '需要加強對相關概念的理解'
                    if not feedback.get('suggestions') or feedback.get('suggestions') == '無':
                        feedback['suggestions'] = '建議複習相關章節，多做練習題'
                    
                    result['feedback'] = feedback
                    return result
                else:
                    print("⚠️ AI回應缺少必要字段")
                    return None
            else:
                print("⚠️ 無法從AI回應中提取JSON")
                return None
                
        except Exception as e:
            print(f"⚠️ 解析AI回應失敗: {e}")
            return None

# 創建全局實例
grader = AnswerGrader()

def batch_grade_ai_questions(questions_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """批量批改AI題目的便捷函數"""
    return grader.batch_grade_ai_questions(questions_data)
