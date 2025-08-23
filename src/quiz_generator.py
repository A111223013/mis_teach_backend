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
            'question_count': 20,
            'exam_type': 'knowledge',
            'school': '',
            'year': '',
            'department': ''
        }
        
        # 合併用戶需求和默認值
        validated = defaults.copy()
        validated.update(requirements)
        
        # 確保題目數量在合理範圍內
        validated['question_count'] = max(5, min(50, validated['question_count']))
        
        return validated
    
    def _generate_knowledge_questions(self, requirements: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成知識點題目"""
        questions = []
        topic = requirements['topic']
        difficulty = requirements['difficulty']
        question_count = requirements['question_count']
        question_types = requirements['question_types']
        
        # 這裡可以調用AI來生成題目，目前使用模擬數據
        for i in range(question_count):
            question_type = random.choice(question_types)
            question = self._create_sample_question(
                question_number=i + 1,
                topic=topic,
                difficulty=difficulty,
                question_type=question_type
            )
            questions.append(question)
        
        return questions
    
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
    
    def _create_sample_question(self, question_number: int, topic: str, 
                               difficulty: str, question_type: str) -> Dict[str, Any]:
        """創建真實的資料結構題目"""
        if topic == "資料結構":
            return self._create_data_structure_question(question_number, difficulty, question_type)
        else:
            return self._create_generic_question(question_number, topic, difficulty, question_type)
    
    def _create_data_structure_question(self, question_number: int, difficulty: str, question_type: str) -> Dict[str, Any]:
        """創建真實的資料結構題目"""
        if question_type == 'single-choice':
            questions = [
                {
                    'question_text': '下列哪種資料結構具有「後進先出」(LIFO)的特性？',
                    'options': ['佇列(Queue)', '堆疊(Stack)', '雙向佇列(Deque)', '優先佇列(Priority Queue)'],
                    'correct_answer': '堆疊(Stack)',
                    'explanation': '堆疊(Stack)是一種後進先出(LIFO)的資料結構，最後放入的元素會最先被取出。'
                },
                {
                    'question_text': '在二元搜尋樹中，左子樹的所有節點值都必須：',
                    'options': ['大於根節點值', '小於根節點值', '等於根節點值', '與根節點值無關'],
                    'correct_answer': '小於根節點值',
                    'explanation': '二元搜尋樹的特性：左子樹的所有節點值都小於根節點值，右子樹的所有節點值都大於根節點值。'
                },
                {
                    'question_text': '下列哪種排序演算法的時間複雜度為O(n²)？',
                    'options': ['快速排序(Quick Sort)', '合併排序(Merge Sort)', '氣泡排序(Bubble Sort)', '堆積排序(Heap Sort)'],
                    'correct_answer': '氣泡排序(Bubble Sort)',
                    'explanation': '氣泡排序的時間複雜度為O(n²)，是最簡單但效率較低的排序演算法。'
                },
                {
                    'question_text': '連結串列(Linked List)相比陣列(Array)的優點是：',
                    'options': ['隨機存取速度快', '記憶體使用效率高', '插入和刪除操作快', '搜尋速度快'],
                    'correct_answer': '插入和刪除操作快',
                    'explanation': '連結串列在插入和刪除操作時只需要改變指標，不需要移動其他元素，因此操作較快。'
                },
                {
                    'question_text': '下列哪種資料結構最適合實現「先進先出」(FIFO)的排隊系統？',
                    'options': ['堆疊(Stack)', '佇列(Queue)', '樹(Tree)', '圖(Graph)'],
                    'correct_answer': '佇列(Queue)',
                    'explanation': '佇列(Queue)是一種先進先出(FIFO)的資料結構，最適合實現排隊系統。'
                }
            ]
            
            # 根據題目編號選擇對應的題目
            question_data = questions[(question_number - 1) % len(questions)]
            
            return {
                'id': question_number,
                'question_text': question_data['question_text'],
                'type': question_type,
                'options': question_data['options'],
                'correct_answer': question_data['correct_answer'],
                'topic': '資料結構',
                'difficulty': difficulty,
                'key_points': '資料結構基礎概念',
                'explanation': question_data['explanation'],
                'image_file': []
            }
            
        elif question_type == 'multiple-choice':
            questions = [
                {
                    'question_text': '下列哪些是線性資料結構？',
                    'options': ['陣列(Array)', '連結串列(Linked List)', '堆疊(Stack)', '樹(Tree)'],
                    'correct_answer': '陣列(Array), 連結串列(Linked List), 堆疊(Stack)',
                    'explanation': '陣列、連結串列、堆疊都是線性資料結構，而樹是非線性資料結構。'
                },
                {
                    'question_text': '關於二元搜尋樹，下列哪些敘述正確？',
                    'options': ['中序遍歷會得到有序序列', '每個節點最多有兩個子節點', '左子樹值小於根節點', '右子樹值大於根節點'],
                    'correct_answer': '中序遍歷會得到有序序列, 每個節點最多有兩個子節點, 左子樹值小於根節點, 右子樹值大於根節點',
                    'explanation': '二元搜尋樹的所有特性都正確：中序遍歷會得到有序序列，每個節點最多有兩個子節點，左子樹值小於根節點，右子樹值大於根節點。'
                }
            ]
            
            question_data = questions[(question_number - 1) % len(questions)]
            
            return {
                'id': question_number,
                'question_text': question_data['question_text'],
                'type': question_type,
                'options': question_data['options'],
                'correct_answer': question_data['correct_answer'],
                'topic': '資料結構',
                'difficulty': difficulty,
                'key_points': '資料結構綜合概念',
                'explanation': question_data['explanation'],
                'image_file': []
            }
            
        elif question_type == 'fill-in-the-blank':
            questions = [
                {
                    'question_text': '在堆疊(Stack)中，插入新元素的操作稱為____，移除元素的操作稱為____。',
                    'correct_answer': 'push, pop',
                    'explanation': '堆疊的基本操作：push(推入)用於插入新元素，pop(彈出)用於移除頂部元素。'
                },
                {
                    'question_text': '二元搜尋樹的中序遍歷順序是：____ → ____ → ____。',
                    'correct_answer': '左子樹, 根節點, 右子樹',
                    'explanation': '二元搜尋樹的中序遍歷順序是：先遍歷左子樹，再訪問根節點，最後遍歷右子樹。'
                }
            ]
            
            question_data = questions[(question_number - 1) % len(questions)]
            
            return {
                'id': question_number,
                'question_text': question_data['question_text'],
                'type': question_type,
                'correct_answer': question_data['correct_answer'],
                'topic': '資料結構',
                'difficulty': difficulty,
                'key_points': '資料結構關鍵概念',
                'explanation': question_data['explanation'],
                'image_file': []
            }
            
        else:  # short-answer
            questions = [
                {
                    'question_text': '請簡述堆疊(Stack)和佇列(Queue)的差異，並各舉一個實際應用例子。',
                    'correct_answer': '堆疊是後進先出(LIFO)的資料結構，佇列是先進先出(FIFO)的資料結構。堆疊應用：瀏覽器的返回按鈕、函數呼叫堆疊。佇列應用：排隊系統、印表機工作佇列。',
                    'explanation': '堆疊和佇列是兩種基本的線性資料結構，主要差異在於元素的存取順序。堆疊適合需要「撤銷」功能的場景，佇列適合需要「排隊」的場景。'
                },
                {
                    'question_text': '解釋什麼是二元搜尋樹，並說明其搜尋、插入、刪除操作的時間複雜度。',
                    'correct_answer': '二元搜尋樹是一種有序的二元樹，左子樹值小於根節點，右子樹值大於根節點。搜尋、插入、刪除的時間複雜度平均為O(log n)，最壞情況為O(n)。',
                    'explanation': '二元搜尋樹是一種高效的搜尋資料結構，在平衡的情況下，所有操作的時間複雜度都是對數級別。'
                }
            ]
            
            question_data = questions[(question_number - 1) % len(questions)]
            
            return {
                'id': question_number,
                'question_text': question_data['question_text'],
                'type': 'short-answer',
                'correct_answer': question_data['correct_answer'],
                'topic': '資料結構',
                'difficulty': difficulty,
                'key_points': '資料結構概念理解',
                'explanation': question_data['explanation'],
                'image_file': []
            }
    
    def _create_generic_question(self, question_number: int, topic: str, 
                                difficulty: str, question_type: str) -> Dict[str, Any]:
        """創建通用題目（非資料結構）"""
        if question_type == 'single-choice':
            return {
                'id': question_number,
                'question_text': f"關於{topic}的{self.difficulty_levels[difficulty]}程度問題 {question_number}：下列何者正確？",
                'type': question_type,
                'options': [
                    f"{topic}相關概念A",
                    f"{topic}相關概念B", 
                    f"{topic}相關概念C",
                    f"{topic}相關概念D"
                ],
                'correct_answer': f"{topic}相關概念A",
                'topic': topic,
                'difficulty': difficulty,
                'key_points': f"{topic}基礎概念",
                'explanation': f"這是{topic}的基礎知識點，難度為{self.difficulty_levels[difficulty]}。正確答案是A，因為...",
                'image_file': []
            }
        elif question_type == 'multiple-choice':
            return {
                'id': question_number,
                'question_text': f"關於{topic}的多選題 {question_number}：下列哪些選項正確？",
                'type': question_type,
                'options': [
                    f"{topic}相關概念A",
                    f"{topic}相關概念B",
                    f"{topic}相關概念C",
                    f"{topic}相關概念D"
                ],
                'correct_answer': f"{topic}相關概念A, {topic}相關概念B",
                'topic': topic,
                'difficulty': difficulty,
                'key_points': f"{topic}綜合概念",
                'explanation': f"這題考察{topic}的多個相關概念，正確答案是A和B，因為...",
                'image_file': []
            }
        elif question_type == 'fill-in-the-blank':
            return {
                'id': question_number,
                'question_text': f"請填寫{topic}相關的關鍵詞：____",
                'type': question_type,
                'correct_answer': f"{topic}關鍵詞",
                'topic': topic,
                'difficulty': difficulty,
                'key_points': f"{topic}關鍵概念",
                'explanation': f"這題考察{topic}的核心概念理解，正確答案是...",
                'image_file': []
            }
        else:
            return {
                'id': question_number,
                'question_text': f"請簡述{topic}的相關概念",
                'type': 'short-answer',
                'correct_answer': f"{topic}的相關概念說明",
                'topic': topic,
                'difficulty': difficulty,
                'key_points': f"{topic}概念理解",
                'explanation': f"這題考察對{topic}概念的理解和表達能力，答案應該包含...",
                'image_file': []
            }
    
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
