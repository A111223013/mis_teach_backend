import json
import re
import concurrent.futures
from typing import List, Dict, Any, Tuple
from tool.api_keys import get_api_key, get_api_keys_count
from accessories import init_gemini

class AnswerGrader:
    """答案批改器 - 簡化版本"""
    
    def __init__(self):
        # 初始化Gemini API
        self.model = init_gemini('gemini-2.0-flash')
    
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
            # 使用 accessories 中的 init_gemini 函數
            model = init_gemini('gemini-2.0-flash')
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
                # 如果是繪圖題，需要特殊處理base64圖片
                if isinstance(user_answer, str) and user_answer.startswith('data:image/'):
                    try:
                        import base64
                        from google.generativeai.types import HarmCategory, HarmBlockThreshold
                        
                        # 提取base64數據部分
                        base64_data = user_answer.split(',')[1] if ',' in user_answer else user_answer
                        
                        # 解碼base64數據
                        image_data = base64.b64decode(base64_data)
                        
                        # 創建圖片內容
                        image_content = {
                            "mime_type": "image/png",
                            "data": image_data
                        }
                        
                        # 使用圖片和文字提示
                        response = model.generate_content([
                            image_content,
                            prompt
                        ])
                        
                        print(f"🔍 使用圖片分析模式")
                        
                    except Exception as e:
                        print(f"❌ 圖片處理失敗，使用文字模式: {e}")
                        response = model.generate_content(prompt)
                else:
                    response = model.generate_content(prompt)
                

                
                result = self._parse_ai_response(response.text)
                if result:
                    # 確保評分邏輯一致性：分數 ≥ 85 的答案被標記為正確
                    score = result.get('score', 0)
                    is_correct = score >= 85
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
        # 根據題目類型添加特定的評分指導
        type_guidance = self._get_type_specific_guidance(question_type)
        
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

**重要說明**：
- 如果學生答案是base64編碼的圖片（以data:image/開頭），請直接分析圖片內容
- 對於繪圖題，請根據圖片內容與題目要求的匹配度進行評分
- 圖片內容應該與題目相關，包含必要的圖形元素和結構

{type_guidance}

**通用評分重點**：
1. **只評分學生答案的內容**，與正確答案進行比較
2. **學生答案必須與題目內容相關**，不能是無意義的數字或符號
3. 如果學生答案與題目要求完全無關，必須給0分

**評分要求**：
1. 仔細分析學生答案的內容和邏輯
2. 判斷答案是否正確或部分正確
3. 給出0-100的分數
4. 提供具體的評分理由和改進建議
5. 必須填寫優點、需要改進的地方和學習建議，不能留空

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
    
    def _get_type_specific_guidance(self, question_type: str) -> str:
        """根據題目類型返回特定的評分指導"""
        
        if question_type == 'draw-answer' or 'draw' in question_type.lower():
            return """
**繪圖題評分標準**：
- 90-100分：完全正確 - 繪圖完全正確，包含所有必要元素，結構清晰，符合題目要求
- 70-89分：接近正確 - 繪圖基本正確，主要元素齊全，結構合理，有輕微錯誤
- 50-69分：答案對一半 - 繪圖包含部分必要元素，但結構不完整或有明顯錯誤
- 0-49分：答案錯誤 - 繪圖與題目要求無關，或只是隨意塗鴉，沒有實質內容

**繪圖題特別注意**：
- 必須檢查繪圖是否與題目內容相關
- 如果只是隨意畫線、塗鴉或與題目無關的圖形，必須給0分
- 繪圖必須包含題目要求的核心元素和結構
- 不能因為學生有畫圖就給分，必須看內容是否正確
- 如果繪圖內容與正確答案完全不符，必須給低分（0-39分）
- 對於空白或幾乎空白的圖片，必須給0分
- 對於只有簡單線條或無意義圖形的圖片，最多給30分
- 評分要客觀公正，嚴格按照繪圖內容與題目要求的匹配度給分
- 對於複雜的繪圖題目，要仔細分析每個必要元素是否正確呈現

**嚴格評分要求**：
- 對於數學計算題的繪圖，必須包含具體的計算過程和結果
- 如果只是畫了幾條線或簡單圖形，沒有數學內容，最多給20分
- 必須檢查繪圖是否真的回答了題目的問題
- 對於隨意塗鴉、無意義線條、或與題目完全無關的內容，必須給0分
- 評分時要非常嚴格，寧可給低分也不要給高分
"""
        
        elif question_type == 'coding-answer' or 'code' in question_type.lower():
            return """
**程式撰寫題評分標準**：
- 90-100分：完全正確 - 程式碼完全正確，邏輯清晰，語法正確，能正常運行
- 70-89分：接近正確 - 程式碼基本正確，邏輯合理，有輕微語法錯誤但不影響功能
- 50-69分：答案對一半 - 程式碼部分正確，邏輯有問題但基本結構正確
- 0-49分：答案錯誤 - 程式碼與題目要求無關，或完全無法運行

**程式題特別注意**：
- 必須檢查程式碼是否與題目要求相關
- 如果只是隨意輸入文字或無關代碼，必須給0分
- 程式碼必須能解決題目提出的問題
- 語法正確性和邏輯正確性都要考慮
- 對於"hello world"等無關文字，必須給0分
- 對於沒有函數定義、沒有邏輯結構的代碼，最多給10分
"""
        
        elif question_type in ['short-answer', 'long-answer', 'fill-in-the-blank']:
            return """
**問答題評分標準**：
- 90-100分：完全正確 - 答案完全正確，內容完整且準確，包含所有關鍵概念
- 70-89分：接近正確 - 答案基本正確，主要概念正確但有小錯誤或遺漏
- 50-69分：答案對一半 - 答案包含部分關鍵概念但理解不夠深入
- 0-49分：答案錯誤 - 答案錯誤，主要概念錯誤或與題目無關

**問答題特別注意**：
- 學生答案必須包含正確答案的核心概念和關鍵信息
- 如果學生只回答數字、符號或與題目無關的內容，必須給0分
- 答案必須與題目內容有實質關聯
- 不能因為學生努力就給高分，必須看內容正確性
- 對於"測試"、"不知道"、"隨便"等無關回答，必須給0分
- 對於只有一個數字或符號的回答，必須給0分
"""
        
        elif question_type in ['single-choice', 'multiple-choice', 'true-false']:
            return """
**選擇題評分標準**：
- 100分：答案完全正確
- 0分：答案錯誤或未作答

**選擇題特別注意**：
- 選擇題只有對錯，沒有部分分數
- 必須與正確答案完全一致才算正確
- 如果答案格式不正確或無法識別，視為錯誤
- 對於空白答案或無關回答，必須給0分
- 嚴格按照正確答案進行評分，不允許任何偏差
- 答案必須完全匹配，包括大小寫、格式、順序等
"""
        
        else:
            return """
**通用評分標準**：
- 90-100分：完全正確 - 答案完全正確，內容完整且準確
- 70-89分：接近正確 - 答案基本正確，主要概念正確但有小錯誤
- 50-69分：答案對一半 - 答案包含部分正確概念但理解不夠深入
- 0-49分：答案錯誤 - 答案錯誤，主要概念錯誤或與題目無關

**特別注意**：
- 評分要客觀公正，不能因為學生努力就給高分
- 如果學生答案與題目內容完全無關，必須給0分
- 只有當學生答案在內容上與題目有實質關聯時，才能給分數
- 對於無意義的數字、符號、重複字符，必須給0分
- 對於"不知道"、"隨便"、"測試"等無關回答，必須給0分
"""
    
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
