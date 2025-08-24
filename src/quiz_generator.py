#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI考卷生成器 - 根據用戶需求自動創建考卷並插入數據庫
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import random
import time

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QuizGenerator:
    """AI考卷生成器"""
    
    def __init__(self):
        self.question_types = {
            'single-choice': '單選題',
            'multiple-choice': '多選題', 
            'fill-in-the-blank': '填空題',
            'true-false': '是非題',
            'short-answer': '簡答題',
            'long-answer': '申論題'
        }
        
        self.difficulty_levels = {
            'easy': '簡單',
            'medium': '中等', 
            'hard': '困難'
        }
    
    def generate_quiz(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """
        根據需求生成考卷
        
        Args:
            requirements: 包含以下字段的字典
                - topic: 知識點/主題
                - question_types: 題型列表
                - difficulty: 難度
                - question_count: 題目數量
                - exam_type: 考卷類型 ('knowledge' 或 'pastexam')
                - school: 學校 (考古題用)
                - year: 年份 (考古題用)
                - department: 科系 (考古題用)
        
        Returns:
            生成的考卷數據
        """
        try:
            logger.info(f"開始生成考卷，需求: {requirements}")
            
            # 驗證需求
            validated_req = self._validate_requirements(requirements)
            
            # 根據考卷類型生成題目
            if validated_req['exam_type'] == 'pastexam':
                questions = self._generate_pastexam_questions(validated_req)
            else:
                questions = self._generate_knowledge_questions(validated_req)
            
            # 生成考卷信息
            quiz_info = self._generate_quiz_info(validated_req, questions)
            
            logger.info(f"考卷生成完成，題目數量: {len(questions)}")
            
            return {
                'success': True,
                'quiz_info': quiz_info,
                'questions': questions,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"生成考卷失敗: {e}")
            return {
                'success': False,
                'error': f"生成考卷失敗: {str(e)}"
            }
    
    def generate_and_save_quiz(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成考卷並保存到數據庫
        
        Args:
            requirements: 考卷需求
            
        Returns:
            包含數據庫ID的考卷數據
        """
        try:
            # 生成考卷
            quiz_result = self.generate_quiz(requirements)
            
            if not quiz_result['success']:
                return quiz_result
            
            # 保存到數據庫
            saved_questions = self._save_questions_to_database(quiz_result['questions'], requirements)
            
            if saved_questions:
                quiz_result['database_ids'] = saved_questions
                quiz_result['message'] = "考卷已成功生成並保存到數據庫"
            
            return quiz_result
            
        except Exception as e:
            logger.error(f"生成並保存考卷失敗: {e}")
            return {
                'success': False,
                'error': f"生成並保存考卷失敗: {str(e)}"
            }
    
    def _save_questions_to_database(self, questions: List[Dict], requirements: Dict) -> List[str]:
        """
        將題目保存到MongoDB數據庫
        
        Args:
            questions: 題目列表
            requirements: 需求參數
            
        Returns:
            保存的題目ID列表
        """
        try:
            from accessories import mongo
            
            saved_ids = []
            
            for question in questions:
                # 轉換為數據庫格式
                db_question = self._convert_to_database_format(question, requirements)
                
                # 插入到數據庫
                result = mongo.db.exam.insert_one(db_question)
                saved_ids.append(str(result.inserted_id))
                
                logger.info(f"題目已保存到數據庫，ID: {result.inserted_id}")
            
            logger.info(f"成功保存 {len(saved_ids)} 道題目到數據庫")
            return saved_ids
            
        except Exception as e:
            logger.error(f"保存題目到數據庫失敗: {e}")
            return []
    
    def _convert_to_database_format(self, question: Dict, requirements: Dict) -> Dict:
        """
        將題目轉換為數據庫格式
        
        Args:
            question: 原始題目
            requirements: 需求參數
            
        Returns:
            數據庫格式的題目
        """
        # 根據您的數據庫格式創建題目
        db_question = {
            "type": "single",  # 單題類型
            "school": requirements.get('school', 'AI生成'),
            "department": requirements.get('department', 'AI生成'),
            "year": requirements.get('year', str(datetime.now().year)),
            "question_number": str(question.get('id', 1)),
            "question_text": question.get('question_text', ''),
            "options": question.get('options', []),
            "answer": question.get('correct_answer', ''),
            "answer_type": self._map_answer_type(question.get('type', 'single-choice')),
            "image_file": question.get('image_file', []),
            "detail-answer": question.get('explanation', ''),
            "key-points": [question.get('key_points', requirements.get('topic', 'AI生成'))],
            "difficulty level": self._map_difficulty(question.get('difficulty', 'medium')),
            "error reason": "",
            "create_time": datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        }
        
        return db_question
    
    def _map_answer_type(self, question_type: str) -> str:
        """映射題目類型到答案類型"""
        type_mapping = {
            'single-choice': 'single-choice',
            'multiple-choice': 'multiple-choice',
            'fill-in-the-blank': 'fill-in-the-blank',
            'true-false': 'true-false',
            'short-answer': 'short-answer',
            'long-answer': 'long-answer'
        }
        return type_mapping.get(question_type, 'single-choice')
    
    def _map_difficulty(self, difficulty: str) -> str:
        """映射難度等級"""
        difficulty_mapping = {
            'easy': '簡單',
            'medium': '中等',
            'hard': '困難'
        }
        return difficulty_mapping.get(difficulty, '中等')
    
    def _validate_requirements(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """驗證和標準化需求"""
        # 設置默認值
        defaults = {
            'topic': '計算機概論',
            'question_types': ['single-choice', 'multiple-choice'],
            'difficulty': 'medium',
            'question_count': 5,  # 改為5題默認
            'exam_type': 'knowledge',
            'school': '',
            'year': '',
            'department': ''
        }
        
        # 合併用戶需求和默認值
        validated = defaults.copy()
        validated.update(requirements)
        
        # 確保題目數量在合理範圍內
        validated['question_count'] = max(1, min(50, validated['question_count']))
        
        return validated
    
    def _generate_knowledge_questions(self, requirements: Dict[str, Any]) -> List[Dict[str, Any]]:
        """使用AI生成知識點題目 - 一次生成一題"""
        questions = []
        topic = requirements['topic']
        difficulty = requirements['difficulty']
        question_count = requirements['question_count']
        question_types = requirements['question_types']
        
        logger.info(f"開始逐題生成，總共需要 {question_count} 題")
        
        try:
            # 逐題生成，避免一次生成全部導致的JSON過長問題
            for i in range(question_count):
                question_type = random.choice(question_types)
                logger.info(f"正在生成第 {i + 1}/{question_count} 題，題型: {question_type}")
                
                # 生成單題
                question = self._generate_single_ai_question(
                    question_number=i + 1,
                    topic=topic,
                    difficulty=difficulty,
                    question_type=question_type
                )
                
                if question:
                    questions.append(question)
                    logger.info(f"✅ 第 {i + 1} 題生成成功")
                else:
                    logger.warning(f"⚠️ 第 {i + 1} 題生成失敗，使用備用題目")
                    # 使用備用題目
                    fallback_question = self._create_fallback_question(
                        question_number=i + 1,
                        topic=topic,
                        difficulty=difficulty,
                        question_type=question_type
                    )
                    questions.append(fallback_question)
                
                # 每題之間稍作延遲，避免API限制
                if i < question_count - 1:
                    time.sleep(1)
                
        except Exception as e:
            logger.error(f"AI生成題目過程中發生錯誤: {e}")
            # 如果整個過程失敗，使用備用題目
            for i in range(question_count):
                question_type = random.choice(question_types)
                question = self._create_fallback_question(
                    question_number=i + 1,
                    topic=topic,
                    difficulty=difficulty,
                    question_type=question_type
                )
                questions.append(question)
        
        logger.info(f"題目生成完成，成功生成 {len(questions)} 題")
        return questions
    
    def _generate_single_ai_question(self, question_number: int, topic: str, 
                                   difficulty: str, question_type: str) -> Optional[Dict[str, Any]]:
        """使用AI生成單一題目 - 避免JSON過長問題"""
        try:
            from src.web_ai_assistant import get_web_ai_service
            
            # 獲取AI服務
            service = get_web_ai_service()
            llm = service['llm']
            
            # 構建更清晰的AI提示詞 - 只生成一題
            prompt = f"""請為我創建一道關於{topic}的{self.difficulty_levels[difficulty]}程度{self.question_types[question_type]}。

要求：
1. 題目要真實、有教育意義，符合大學課程標準
2. 選項要合理且具有迷惑性，避免明顯錯誤的選項
3. 答案要正確且有詳細解釋，解釋要清晰易懂
4. 題目內容要符合{self.difficulty_levels[difficulty]}程度
5. 如果是單選題，提供4個選項；如果是多選題，提供4個選項，正確答案可以是1-3個

請務必以以下 JSON Schema 格式回傳（只生成一題）：

{{
  "question_text": "請創建一道關於{topic}的真實題目，例如：'在二元搜尋樹中，左子樹的所有節點值都必須滿足什麼條件？'",
  "options": [
    "選項A: 請創建真實的選項內容，例如：'大於根節點的值'",
    "選項B: 請創建真實的選項內容，例如：'小於根節點的值'",
    "選項C: 請創建真實的選項內容，例如：'等於根節點的值'",
    "選項D: 請創建真實的選項內容，例如：'與根節點值無關'"
  ],
  "correct_answer": "請寫出正確答案，例如：'B'",
  "explanation": "請寫出具體的解釋內容，例如：'在二元搜尋樹中，左子樹的所有節點值都必須小於根節點的值，這是二元搜尋樹的基本性質。'",
  "key_points": "請寫出具體的知識點，例如：'二元搜尋樹, 左子樹性質, 節點值比較'"
}}

重要提醒：
- 請確保JSON格式完整，不要中途截斷
- 所有字符串都要用雙引號包圍，不要使用單引號
- 選項數組必須包含4個元素，每個選項都要有標籤（A、B、C、D）
- 題目內容要專業且準確，符合{topic}學科標準
- 請使用繁體中文撰寫所有內容
- 請嚴格按照上述JSON Schema格式，不要添加任何其他文字或格式
- 嚴禁使用佔位符文字，必須生成真實的題目內容
- 題目內容應該與{topic}相關，具有實際的教學價值
- 由於只生成一題，請確保JSON完整且不截斷
- 請根據{topic}創建全新的真實題目，不要複製示例內容
- 示例只是格式參考，內容必須是您自己創建的"""
            
            # 調用AI生成
            response = llm.invoke(prompt)
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            logger.info(f"AI回應長度: {len(response_text)} 字符")
            
            # 提取和驗證JSON
            question_data = self._extract_and_validate_single_question(response_text)
            
            if question_data:
                # 添加題目編號和類型
                question_data['id'] = question_number
                question_data['type'] = question_type
                question_data['topic'] = topic
                question_data['difficulty'] = difficulty
                question_data['image_file'] = []
                
                return question_data
            else:
                logger.warning(f"第 {question_number} 題JSON提取或驗證失敗")
                return None
                
        except Exception as e:
            logger.error(f"生成第 {question_number} 題時發生錯誤: {e}")
            return None
    
    def _clean_json_string(self, json_str: str) -> str:
        """清理JSON字符串，移除多餘的換行符和縮進"""
        # 移除開頭的 ```json 和結尾的 ```
        cleaned = json_str.strip()
        if cleaned.startswith('```json'):
            cleaned = cleaned[7:]
        if cleaned.endswith('```'):
            cleaned = cleaned[:-3]
        
        # 移除控制字符和無效字符
        # 移除控制字符（除了換行符和製表符）
        cleaned = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', cleaned)
        
        # 移除多餘的換行符和縮進
        cleaned = cleaned.replace('\n', ' ').replace('\r', ' ').replace('    ', ' ')
        
        # 移除多餘的空格
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        # 確保大括號和中括號的平衡
        if cleaned.count('{') > cleaned.count('}'):
            cleaned = cleaned.replace('{', '{\n', 1)
            cleaned = cleaned.replace('}', '\n}', 1)
        elif cleaned.count('{') == 1 and cleaned.count('}') == 0:
            cleaned += '\n}'
        elif cleaned.count('{') == 0 and cleaned.count('}') == 1:
            cleaned = '{\n' + cleaned
        
        if cleaned.count('[') > cleaned.count(']'):
            cleaned = cleaned.replace('[', '[\n', 1)
            cleaned = cleaned.replace(']', '\n]', 1)
        elif cleaned.count('[') == 1 and cleaned.count(']') == 0:
            cleaned += '\n]'
        elif cleaned.count('[') == 0 and cleaned.count(']') == 1:
            cleaned = '[\n' + cleaned
        
        # 移除開頭和結尾的空格
        cleaned = cleaned.strip()
        
        return cleaned
    
    def _repair_truncated_json(self, json_str: str) -> str:
        """修復被截斷的JSON字符串"""
        try:
            # 基本清理
            cleaned = json_str.strip()
            logger.info(f"開始修復截斷的JSON: {cleaned[:100]}...")
            
            # 如果JSON已經完整，直接返回
            try:
                json.loads(cleaned)
                logger.info("JSON已經完整，無需修復")
                return cleaned
            except:
                pass
            
            # 檢查是否缺少結尾的大括號
            if cleaned.count('{') > cleaned.count('}'):
                logger.info("檢測到缺少結尾大括號，開始修復...")
                
                # 檢查最後一個字段是否完整
                if '"key_points"' in cleaned:
                    if not cleaned.endswith('"') and not cleaned.endswith('}'):
                        # 補全key_points字段
                        if cleaned.endswith(','):
                            cleaned = cleaned[:-1]  # 移除最後的逗號
                        cleaned += ': "關鍵知識點"'
                        logger.info("已補全key_points字段")
                
                if '"explanation"' in cleaned and not cleaned.endswith('"') and not cleaned.endswith('}'):
                    # 補全explanation字段
                    if cleaned.endswith(','):
                        cleaned = cleaned[:-1]  # 移除最後的逗號
                    cleaned += ': "詳細解釋"'
                    logger.info("已補全explanation字段")
                
                if '"correct_answer"' in cleaned and not cleaned.endswith('"') and not cleaned.endswith('}'):
                    # 補全correct_answer字段
                    if cleaned.endswith(','):
                        cleaned = cleaned[:-1]  # 移除最後的逗號
                    cleaned += ': "A"'
                    logger.info("已補全correct_answer字段")
                
                if '"options"' in cleaned and not cleaned.endswith(']'):
                    # 補全options字段
                    if not cleaned.endswith('"'):
                        cleaned += '"'
                    cleaned += ']'
                    logger.info("已補全options字段")
                
                if '"question_text"' in cleaned and not cleaned.endswith('"') and not cleaned.endswith('}'):
                    # 補全question_text字段
                    if cleaned.endswith(','):
                        cleaned = cleaned[:-1]  # 移除最後的逗號
                    cleaned += ': "題目內容"'
                    logger.info("已補全question_text字段")
                
                # 添加結尾大括號
                cleaned += '}'
                logger.info("已添加結尾大括號")
            
            # 檢查是否缺少結尾的中括號
            if cleaned.count('[') > cleaned.count(']'):
                cleaned += ']'
                logger.info("已補全結尾中括號")
            
            # 嘗試解析修復後的JSON
            try:
                json.loads(cleaned)
                logger.info(f"JSON修復成功: {cleaned[:100]}...")
                return cleaned
            except:
                # 如果還是無法解析，嘗試更激進的修復
                logger.warning("基本修復失敗，嘗試激進修復")
                return self._aggressive_json_repair(cleaned)
                
        except Exception as e:
            logger.warning(f"JSON修復失敗: {e}")
            raise ValueError(f"JSON修復失敗: {e}")
    
    def _aggressive_json_repair(self, json_str: str) -> str:
        """激進的JSON修復方法"""
        try:
            # 創建一個最小的有效JSON結構
            repaired = {
                "question_text": "題目內容",
                "options": [
                    "選項A: 選項內容",
                    "選項B: 選項內容",
                    "選項C: 選項內容",
                    "選項D: 選項內容"
                ],
                "correct_answer": "A",
                "explanation": "詳細解釋",
                "key_points": "關鍵知識點"
            }
            
            # 嘗試從原始字符串中提取可用的字段
            if '"question_text"' in json_str:
                # 提取question_text
                start = json_str.find('"question_text"') + 15
                end = json_str.find('"', start + 1)
                if end > start:
                    question_text = json_str[start:end].strip()
                    if question_text and not question_text.startswith(':'):
                        repaired["question_text"] = question_text
            
            if '"options"' in json_str:
                # 提取options
                start = json_str.find('"options"')
                if start > 0:
                    # 尋找選項內容
                    options_start = json_str.find('[', start)
                    if options_start > 0:
                        # 簡單提取選項
                        options_text = json_str[options_start:]
                        # 提取選項A
                        if '"選項A:"' in options_text:
                            a_start = options_text.find('"選項A:"') + 8
                            a_end = options_text.find('"', a_start + 1)
                            if a_end > a_start:
                                option_a = options_text[a_start:a_end].strip()
                                if option_a:
                                    repaired["options"][0] = f"選項A: {option_a}"
            
            return json.dumps(repaired, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"激進JSON修復失敗: {e}")
            # 返回最基本的JSON結構
            return '{"question_text": "題目內容", "options": ["選項A: 選項內容", "選項B: 選項內容", "選項C: 選項內容", "選項D: 選項內容"], "correct_answer": "A", "explanation": "詳細解釋", "key_points": "關鍵知識點"}'
    
    def _create_basic_json_structure(self) -> str:
        """創建基本的JSON結構作為最後的備用方案"""
        return '''{
            "question_text": "關於基礎概念的題目",
            "options": ["選項A: 基礎概念A", "選項B: 基礎概念B", "選項C: 基礎概念C", "選項D: 基礎概念D"],
            "correct_answer": "A",
            "explanation": "這是正確答案的解釋",
            "key_points": "基礎概念"
        }'''
    
    def _create_fallback_question(self, question_number: int, topic: str, 
                                 difficulty: str, question_type: str) -> Dict[str, Any]:
        """創建備用題目（當AI生成失敗時使用）"""
        if topic == "資料結構":
            return self._create_data_structure_fallback(question_number, difficulty, question_type)
        else:
            return self._create_generic_fallback(question_number, topic, difficulty, question_type)
    
    def _create_data_structure_fallback(self, question_number: int, difficulty: str, question_type: str) -> Dict[str, Any]:
        """創建資料結構備用題目"""
        # 這裡保留一些基本的備用題目，以防AI生成失敗
        if question_type == 'single-choice':
            questions = [
                {
                    'question_text': '下列哪種資料結構具有「後進先出」(LIFO)的特性？',
                    'options': ['佇列(Queue)', '堆疊(Stack)', '雙向佇列(Deque)', '優先佇列(Priority Queue)'],
                    'correct_answer': '堆疊(Stack)',
                    'explanation': '堆疊(Stack)是一種後進先出(LIFO)的資料結構，最後放入的元素會最先被取出。',
                    'key_points': '資料結構基礎概念'
                },
                {
                    'question_text': '在二元搜尋樹中，左子樹的所有節點值都必須：',
                    'options': ['大於根節點值', '小於根節點值', '等於根節點值', '與根節點值無關'],
                    'correct_answer': '小於根節點值',
                    'explanation': '二元搜尋樹的特性：左子樹的所有節點值都小於根節點值，右子樹的所有節點值都大於根節點值。',
                    'key_points': '資料結構基礎概念'
                },
                {
                    'question_text': '下列哪種排序演算法的時間複雜度為O(n²)？',
                    'options': ['快速排序(Quick Sort)', '合併排序(Merge Sort)', '氣泡排序(Bubble Sort)', '堆積排序(Heap Sort)'],
                    'correct_answer': '氣泡排序(Bubble Sort)',
                    'explanation': '氣泡排序的時間複雜度為O(n²)，是最簡單但效率較低的排序演算法。',
                    'key_points': '資料結構基礎概念'
                },
                {
                    'question_text': '連結串列(Linked List)相比陣列(Array)的優點是：',
                    'options': ['隨機存取速度快', '記憶體使用效率高', '插入和刪除操作快', '搜尋速度快'],
                    'correct_answer': '插入和刪除操作快',
                    'explanation': '連結串列在插入和刪除操作時只需要改變指標，不需要移動其他元素，因此操作較快。',
                    'key_points': '資料結構基礎概念'
                },
                {
                    'question_text': '下列哪種資料結構最適合實現「先進先出」(FIFO)的排隊系統？',
                    'options': ['堆疊(Stack)', '佇列(Queue)', '樹(Tree)', '圖(Graph)'],
                    'correct_answer': '佇列(Queue)',
                    'explanation': '佇列(Queue)是一種先進先出(FIFO)的資料結構，最適合實現排隊系統。',
                    'key_points': '資料結構基礎概念'
                }
            ]
            
            # 根據題目編號選擇對應的題目，避免重複
            question_data = questions[(question_number - 1) % len(questions)]
            
            return {
                'id': question_number,
                'question_text': question_data['question_text'],
                'type': question_type,
                'options': question_data['options'],
                'correct_answer': question_data['correct_answer'],
                'topic': '資料結構',
                'difficulty': difficulty,
                'key_points': question_data['key_points'],
                'explanation': question_data['explanation'],
                'image_file': []
            }
        else:
            # 多選題備用
            questions = [
                {
                    'question_text': '下列哪些是線性資料結構？',
                    'options': ['陣列(Array)', '連結串列(Linked List)', '堆疊(Stack)', '樹(Tree)'],
                    'correct_answer': '陣列(Array), 連結串列(Linked List), 堆疊(Stack)',
                    'explanation': '陣列、連結串列、堆疊都是線性資料結構，而樹是非線性資料結構。',
                    'key_points': '資料結構綜合概念'
                },
                {
                    'question_text': '關於二元搜尋樹，下列哪些敘述正確？',
                    'options': ['中序遍歷會得到有序序列', '每個節點最多有兩個子節點', '左子樹值小於根節點', '右子樹值大於根節點'],
                    'correct_answer': '中序遍歷會得到有序序列, 每個節點最多有兩個子節點, 左子樹值小於根節點, 右子樹值大於根節點',
                    'explanation': '二元搜尋樹的所有特性都正確：中序遍歷會得到有序序列，每個節點最多有兩個子節點，左子樹值小於根節點，右子樹值大於根節點。',
                    'key_points': '資料結構綜合概念'
                },
                {
                    'question_text': '下列哪些排序演算法的時間複雜度為O(n log n)？',
                    'options': ['快速排序(Quick Sort)', '合併排序(Merge Sort)', '氣泡排序(Bubble Sort)', '堆積排序(Heap Sort)'],
                    'correct_answer': '快速排序(Quick Sort), 合併排序(Merge Sort), 堆積排序(Heap Sort)',
                    'explanation': '快速排序、合併排序、堆積排序的平均時間複雜度都是O(n log n)，而氣泡排序是O(n²)。',
                    'key_points': '資料結構綜合概念'
                }
            ]
            
            # 根據題目編號選擇對應的題目，避免重複
            question_data = questions[(question_number - 1) % len(questions)]
            
            return {
                'id': question_number,
                'question_text': question_data['question_text'],
                'type': question_type,
                'options': question_data['options'],
                'correct_answer': question_data['correct_answer'],
                'topic': '資料結構',
                'difficulty': difficulty,
                'key_points': question_data['key_points'],
                'explanation': question_data['explanation'],
                'image_file': []
            }
    
    def _create_generic_fallback(self, question_number: int, topic: str, 
                                difficulty: str, question_type: str) -> Dict[str, Any]:
        """創建通用備用題目"""
        return {
            'id': question_number,
            'question_text': f'關於{topic}的{self.difficulty_levels[difficulty]}程度問題 {question_number}',
            'type': question_type,
            'options': [f'{topic}相關概念A', f'{topic}相關概念B', f'{topic}相關概念C', f'{topic}相關概念D'],
            'correct_answer': f'{topic}相關概念A',
            'topic': topic,
            'difficulty': difficulty,
            'key_points': f'{topic}基礎概念',
            'explanation': f'這是{topic}的基礎知識點，難度為{self.difficulty_levels[difficulty]}。',
            'image_file': []
        }
    
    def _generate_pastexam_questions(self, requirements: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成考古題目"""
        questions = []
        school = requirements['school']
        year = requirements['year']
        department = requirements['department']
        question_count = requirements['question_count']
        
        # 這裡可以從數據庫查詢真實的考古題，目前使用模擬數據
        for i in range(question_count):
            question = self._create_sample_pastexam_question(
                question_number=i + 1,
                school=school,
                year=year,
                department=department
            )
            questions.append(question)
        
        return questions
    
    def _create_sample_pastexam_question(self, question_number: int, school: str, 
                                        year: str, department: str) -> Dict[str, Any]:
        """創建示例考古題"""
        return {
            'id': question_number,
            'question_text': f"{school} {year}年 {department}考古題 {question_number}：關於程式設計的基本概念",
            'type': 'single-choice',
            'options': [
                "選項A: 程式設計基礎概念A",
                "選項B: 程式設計基礎概念B",
                "選項C: 程式設計基礎概念C", 
                "選項D: 程式設計基礎概念D"
            ],
            'correct_answer': 'A',
            'topic': f"{school}考古題",
            'difficulty': 'medium',
            'key_points': f"{school} {year}年考點",
            'explanation': f"這是{school} {year}年的真實考題，考察程式設計的基本概念...",
            'image_file': []
        }
    
    def _generate_quiz_info(self, requirements: Dict[str, Any], questions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成考卷信息"""
        if requirements['exam_type'] == 'pastexam':
            title = f"{requirements['school']} {requirements['year']}年 {requirements['department']}考古題"
        else:
            title = f"{requirements['topic']}知識點測驗"
        
        return {
            'title': title,
            'exam_type': requirements['exam_type'],
            'topic': requirements['topic'],
            'difficulty': requirements['difficulty'],
            'question_count': len(questions),
            'time_limit': 60,  # 默認60分鐘
            'total_score': len(questions) * 5,  # 每題5分
            'created_at': datetime.now().isoformat()
        }

    def _extract_and_validate_single_question(self, response_text: str) -> Optional[Dict[str, Any]]:
        """提取和驗證單一題目的JSON"""
        try:
            # 方法1: 尋找 ```json ... ``` 格式
            if '```json' in response_text:
                json_start = response_text.find('```json') + 7
                json_end = response_text.find('```', json_start)
                if json_end > json_start:
                    json_data = response_text[json_start:json_end].strip()
                    logger.info(f"找到JSON標記，提取的JSON: {json_data[:100]}...")
                    
                    # 清理和驗證JSON
                    json_data = self._clean_json_string(json_data)
                    question_data = json.loads(json_data)
                    
                    # 驗證題目數據
                    if self._validate_question_data(question_data):
                        return question_data
                
                # JSON標記不完整，嘗試修復
                json_data = response_text[json_start:].strip()
                logger.info(f"JSON標記不完整，嘗試修復: {json_data[:100]}...")
                json_data = self._repair_truncated_json(json_data)
                question_data = json.loads(json_data)
                
                if self._validate_question_data(question_data):
                    return question_data
            
            # 方法2: 尋找 { ... } 格式
            elif '{' in response_text and '}' in response_text:
                brace_start = response_text.find('{')
                brace_end = response_text.rfind('}')
                if brace_end > brace_start:
                    json_data = response_text[brace_start:brace_end + 1].strip()
                    logger.info(f"找到大括號，提取的JSON: {json_data[:100]}...")
                    
                    # 清理和驗證JSON
                    json_data = self._clean_json_string(json_data)
                    question_data = json.loads(json_data)
                    
                    if self._validate_question_data(question_data):
                        return question_data
                
                # 大括號不完整，嘗試修復
                json_data = response_text[brace_start:].strip()
                logger.info(f"大括號不完整，嘗試修復: {json_data[:100]}...")
                json_data = self._repair_truncated_json(json_data)
                question_data = json.loads(json_data)
                
                if self._validate_question_data(question_data):
                    return question_data
            
            # 方法3: 嘗試直接解析整個回應
            else:
                logger.info("嘗試直接解析AI回應")
                # 清理回應內容
                cleaned_content = self._clean_json_string(response_text)
                question_data = json.loads(cleaned_content)
                
                if self._validate_question_data(question_data):
                    return question_data
            
            logger.warning("所有JSON提取方法都失敗")
            return None
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"AI回應解析失敗: {e}")
            logger.warning(f"AI回應內容: {response_text[:200]}...")
            return None
    
    def _validate_question_data(self, question_data: Dict[str, Any]) -> bool:
        """驗證題目數據的完整性和正確性"""
        try:
            # 驗證必要字段
            required_fields = ['question_text', 'options', 'correct_answer', 'explanation']
            for field in required_fields:
                if field not in question_data:
                    logger.warning(f"缺少必要字段: {field}")
                    return False
            
            # 檢查是否包含佔位符
            placeholder_patterns = [
                # 通用佔位符
                '題目內容', '選項內容', '詳細解釋', '關鍵知識點', '正確答案',
                # 具體佔位符（您遇到的問題）
                '關於.*的中等程度問題', '關於.*的問題', '問題.*',
                '相關概念A', '相關概念B', '相關概念C', '相關概念D',
                '概念A', '概念B', '概念C', '概念D',
                # 檢查是否包含"例如"等提示詞
                '例如：', '例如:', '例如',
                # 檢查是否過於簡短或模糊（但允許作為知識點）
                '計算機概論基礎概念', '資料結構基礎概念', '演算法基礎概念', '作業系統基礎概念'
            ]
            
            for field, value in question_data.items():
                if isinstance(value, str):
                    # 檢查佔位符模式
                    for pattern in placeholder_patterns:
                        if re.search(pattern, value, re.IGNORECASE):
                            logger.warning(f"檢測到佔位符模式 '{pattern}' 在字段 '{field}' 中: {value}")
                            return False
                    
                    # 檢查內容是否過於簡短或模糊
                    if field == 'question_text' and len(value.strip()) < 20:
                        logger.warning(f"題目內容過於簡短: {value}")
                        return False
                    
                    if field == 'explanation' and len(value.strip()) < 30:
                        logger.warning(f"解釋內容過於簡短: {value}")
                        return False
                    
                    # 檢查是否包含明顯的佔位符文字
                    if any(placeholder in value for placeholder in ['請寫出', '請創建', '請參考', '示例']):
                        logger.warning(f"檢測到指令性文字在字段 '{field}' 中: {value}")
                        return False
                        
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, str):
                            # 檢查選項中的佔位符
                            for pattern in placeholder_patterns:
                                if re.search(pattern, item, re.IGNORECASE):
                                    logger.warning(f"檢測到佔位符模式 '{pattern}' 在字段 '{field}' 的列表中: {item}")
                                    return False
                            
                            # 檢查選項是否過於簡短
                            if field == 'options' and len(item.strip()) < 10:
                                logger.warning(f"選項內容過於簡短: {item}")
                                return False
            
            # 驗證選項數量
            if len(question_data.get('options', [])) != 4:
                logger.warning("選項數量必須是4個")
                return False
            
            # 驗證選項格式（確保每個選項都有標籤）
            options = question_data.get('options', [])
            for i, option in enumerate(options):
                if not option.strip():
                    logger.warning(f"選項{i+1}不能為空")
                    return False
                
                # 檢查選項是否包含標籤
                option_text = option.strip()
                if any(option_text.startswith(f"選項{label}") for label in ['A', 'B', 'C', 'D']):
                    logger.info(f"選項{i+1}標籤正確: {option_text[:20]}...")
                else:
                    logger.warning(f"選項{i+1}缺少標籤: {option_text}")
                    # 自動修復標籤
                    if i < len(['A', 'B', 'C', 'D']):
                        label = ['A', 'B', 'C', 'D'][i]
                        question_data['options'][i] = f"選項{label}: {option_text}"
                        logger.info(f"已修復選項{i+1}標籤: 選項{label}: {option_text[:20]}...")
            
            logger.info(f"題目數據驗證成功: {question_data['question_text'][:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"題目數據驗證失敗: {e}")
            return False

# 創建全局實例
quiz_generator = QuizGenerator()

def generate_quiz_by_ai(requirements: Dict[str, Any]) -> Dict[str, Any]:
    """AI考卷生成的便捷函數"""
    return quiz_generator.generate_quiz(requirements)

def generate_and_save_quiz_by_ai(requirements: Dict[str, Any]) -> Dict[str, Any]:
    """AI考卷生成並保存到數據庫的便捷函數"""
    return quiz_generator.generate_and_save_quiz(requirements)

def get_available_topics() -> List[str]:
    """獲取可用的知識點列表"""
    return [
        "計算機概論", "程式設計", "資料結構", "演算法",
        "作業系統", "資料庫系統", "網路概論", "軟體工程",
        "人工智慧", "機器學習", "資料科學", "資訊安全"
    ]

def get_available_schools() -> List[str]:
    """獲取可用的學校列表"""
    return [
        "台大", "清大", "交大", "成大", "政大",
        "中央", "中興", "中山", "中正", "台科大"
    ]

def get_available_years() -> List[str]:
    """獲取可用的年份列表"""
    current_year = datetime.now().year
    return [str(year) for year in range(current_year - 5, current_year + 1)]

def get_available_departments() -> List[str]:
    """獲取可用的科系列表"""
    return [
        "資訊工程學系", "資訊管理學系", "資訊科學學系",
        "電機工程學系", "電子工程學系", "通訊工程學系"
    ]


def _parse_quiz_requirements(text: str) -> dict:
    """從文本中解析考卷需求"""
    requirements = {
        'topic': '計算機概論',
        'question_types': ['single-choice', 'multiple-choice'],
        'difficulty': 'medium',
        'question_count': 20,
        'exam_type': 'knowledge'
    }
    
    text_lower = text.lower()
    
    # 檢測知識點
    topics = ['計算機概論', '程式設計', '資料結構', '演算法', '作業系統', '資料庫', '網路', '軟體工程', '人工智慧', '機器學習']
    for topic in topics:
        if topic in text:
            requirements['topic'] = topic
            break
    
    # 檢測題型
    if '單選' in text or '選擇' in text:
        requirements['question_types'] = ['single-choice']
    elif '多選' in text:
        requirements['question_types'] = ['multiple-choice']
    elif '填空' in text:
        requirements['question_types'] = ['fill-in-the-blank']
    elif '是非' in text or '判斷' in text:
        requirements['question_types'] = ['true-false']
    elif '簡答' in text:
        requirements['question_types'] = ['short-answer']
    elif '申論' in text:
        requirements['question_types'] = ['long-answer']
    
    # 檢測難度
    if '簡單' in text or 'easy' in text_lower:
        requirements['difficulty'] = 'easy'
    elif '困難' in text or 'hard' in text_lower:
        requirements['difficulty'] = 'hard'
    
    # 檢測題目數量
    import re
    count_match = re.search(r'(\d+)題', text)
    if count_match:
        requirements['question_count'] = int(count_match.group(1))
    
    # 檢測考古題
    schools = ['台大', '清大', '交大', '成大', '政大', '中央', '中興', '中山', '中正', '台科大']
    for school in schools:
        if school in text:
            requirements['exam_type'] = 'pastexam'
            requirements['school'] = school
            break
    
    # 檢測年份
    year_match = re.search(r'(\d{4})年', text)
    if year_match:
        requirements['year'] = year_match.group(1)
    
    return requirements

def _is_quiz_generation_request(text: str) -> bool:
    """檢查是否為考卷生成請求"""
    quiz_keywords = [
        '創建', '生成', '建立', '製作', '產生',
        '考卷', '測驗', '題目', '考試', '練習',
        '單選題', '多選題', '填空題', '是非題', '簡答題', '申論題'
    ]
    
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in quiz_keywords)

def create_quiz_generator_tool():
    """創建考卷生成工具"""
    from langchain_core.tools import tool
    
    @tool
    def quiz_generator_tool(requirements: str) -> str:
        """考卷生成工具，根據用戶需求自動創建考卷並保存到數據庫"""
        try:
            # 解析用戶需求
            try:
                # 嘗試解析JSON格式的需求
                req_dict = json.loads(requirements)
            except:
                # 如果不是JSON，嘗試從文本中提取信息
                req_dict = _parse_quiz_requirements(requirements)
            
            # 生成考卷並保存到數據庫
            result = generate_and_save_quiz_by_ai(req_dict)
            
            if result['success']:
                quiz_info = result['quiz_info']
                questions = result['questions']
                database_ids = result.get('database_ids', [])
                
                # 返回可跳轉的考卷數據
                quiz_data = {
                    'quiz_id': f"ai_generated_{int(time.time())}",
                    'template_id': f"ai_template_{int(time.time())}",
                    'questions': questions,
                    'time_limit': quiz_info['time_limit'],
                    'quiz_info': quiz_info,
                    'database_ids': database_ids
                }
                
                response = f"✅ 考卷生成成功！\n\n"
                response += f"📝 考卷標題: {quiz_info['title']}\n"
                response += f"📚 主題: {quiz_info['topic']}\n"
                response += f"📊 難度: {quiz_info['difficulty']}\n"
                response += f"🔢 題目數量: {quiz_info['question_count']}\n"
                response += f"⏱️ 時間限制: {quiz_info['time_limit']}分鐘\n"
                response += f"💯 總分: {quiz_info['total_score']}分\n\n"
                
                if database_ids:
                    response += f"💾 已保存到數據庫，題目ID: {', '.join(database_ids[:3])}{'...' if len(database_ids) > 3 else ''}\n\n"
                
                response += "📋 題目預覽:\n"
                for i, q in enumerate(questions[:3]):  # 只顯示前3題
                    response += f"{i+1}. {q['question_text'][:100]}...\n"
                
                if len(questions) > 3:
                    response += f"... 還有 {len(questions)-3} 題\n\n"
                
                response += "🚀 **點擊下方按鈕開始測驗！**\n\n"
                response += "```json\n"
                response += json.dumps(quiz_data, ensure_ascii=False, indent=2)
                response += "\n```\n\n"
                
                response += "💡 提示：點擊「開始測驗」按鈕即可開始答題！"
                
                return response
            else:
                return f"❌ 考卷生成失敗: {result.get('error', '未知錯誤')}"
                
        except Exception as e:
            logger.error(f"考卷生成工具執行失敗: {e}")
            return f"❌ 考卷生成失敗，請稍後再試。錯誤: {str(e)}"
    
    return quiz_generator_tool
