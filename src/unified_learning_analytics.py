"""
統一學習分析模組
整合所有學習分析相關功能：
1. 跨資料庫數據整合 (SQL + MongoDB)
2. Neo4j 知識圖譜操作
3. 學習效果分析與推薦
4. API 端點

簡化設計：
- 使用函數式編程，減少複雜的 class
- 統一的配置管理
- 單一檔案包含所有功能
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import json
from flask import Blueprint, request, jsonify, current_app
from accessories import mongo, sqldb, get_neo4j_driver, refresh_token
from accessories import init_gemini
from bson import ObjectId
import jwt

# 設置日誌
logger = logging.getLogger(__name__)

# ==================== 輔助函數 ====================

def convert_objectid(obj):
    """將 ObjectId 轉換為字符串，用於 JSON 序列化"""
    if isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, dict):
        return {key: convert_objectid(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_objectid(item) for item in obj]
    else:
        return obj

# ==================== 配置參數 ====================

# BKT (Bayesian Knowledge Tracing) 參數
BKT_CONFIG = {
    'learning_alpha': 0.7,           # 學習效應權重
    'time_beta': 0.3,                # 時間因子權重
    'initial_learning_velocity': 0.1, # 初始學習速度
    'max_learning_velocity': 0.3,    # 最大學習速度
    'velocity_decay_factor': 0.95,   # 學習速度衰減因子
    'velocity_boost_factor': 1.1,    # 學習速度提升因子
    'forgetting_rate': 0.05,         # 遺忘率
    'mastery_threshold': 0.8,        # 掌握度閾值
    'struggling_threshold': 0.4      # 困難閾值
}

# 學習路徑配置
LEARNING_PATH_CONFIG = {
    'max_path_length': 10,
    'difficulty_increment': 0.1,
    'prerequisite_weight': 0.8,
    'mastery_weight': 0.6,
    'time_weight': 0.4
}

# 適應性測驗配置
ADAPTIVE_QUIZ_CONFIG = {
    'min_questions': 5,
    'max_questions': 20,
    'difficulty_adjustment': 0.1,
    'confidence_threshold': 0.8
}

# ==================== 數據載入函數 ====================

def load_knowledge_structure():
    """從MongoDB載入知識結構"""
    try:
        if mongo.db is None:
            logger.error("MongoDB連接未初始化")
            return {"domains": [], "blocks": [], "micro_concepts": []}
        
        db = mongo.db
        
        # 獲取domains
        domains = list(db.domain.find({}, {'_id': 1, 'name': 1, 'description': 1}))
        domains = convert_objectid(domains)
        
        # 獲取blocks
        blocks = list(db.block.find({}, {'_id': 1, 'domain_id': 1, 'title': 1, 'description': 1}))
        blocks = convert_objectid(blocks)
        
        # 獲取micro_concepts
        micro_concepts = list(db.micro_concept.find({}, {'_id': 1, 'block_id': 1, 'name': 1, 'description': 1}))
        micro_concepts = convert_objectid(micro_concepts)
        
        # 為每個概念添加掌握狀態（暫時設為默認值）
        for concept in micro_concepts:
            concept['mastery_status'] = '需加強'  # 默認狀態，實際應該根據學生記錄計算
        
        knowledge_structure = {
            "domains": domains,
            "blocks": blocks,
            "micro_concepts": micro_concepts
        }
        
        logger.info(f"載入知識結構: {len(domains)} 個領域, {len(blocks)} 個章節, {len(micro_concepts)} 個概念")
        return knowledge_structure
        
    except Exception as e:
        logger.error(f"載入知識結構失敗: {e}")
        return {"domains": [], "blocks": [], "micro_concepts": []}

def load_student_records(student_email: str):
    """從SQL載入學生答題記錄"""
    try:
        if not sqldb:
            logger.error("SQL資料庫連接未初始化")
            return {}
        
        # 簡化查詢，只使用 quiz_answers 表
        query = """
        SELECT 
            mongodb_question_id as question_id,
            user_answer as answer,
            is_correct,
            answer_time_seconds as time_spent,
            created_at as submit_time,
            quiz_history_id as quiz_id,
            mongodb_question_id as question_text,
            0.5 as difficulty_level
        FROM quiz_answers 
        WHERE user_email = :student_email
        ORDER BY created_at DESC
        """
        
        records = sqldb.session.execute(sqldb.text(query), {'student_email': student_email}).fetchall()
        # 轉換為字典列表
        records = [dict(row._mapping) for row in records]
        
        # 組織數據
        student_data = {
            "total_questions": len(records),
            "correct_answers": sum(1 for r in records if r['is_correct']),
            "total_time": sum(r['time_spent'] or 0 for r in records),
            "records": records,
            "concept_performance": analyze_concept_performance(records)
        }
        return student_data
        
    except Exception as e:
        logger.error(f"載入學生記錄失敗: {e}")
        return {}

def analyze_concept_performance(records: List[Dict]):
    """分析概念表現"""
    concept_performance = defaultdict(lambda: {
        'total_questions': 0,
        'correct_answers': 0,
        'total_time': 0,
        'difficulty_scores': []
    })
    
    logger.info(f"開始分析 {len(records)} 筆答題記錄")
    
    for i, record in enumerate(records):
        question_id = record.get('question_id', '')
        concept_name = extract_concept_from_question(question_id)
        
        if i < 3:  # 只記錄前3筆的調試信息
            logger.info(f"記錄 {i+1}: question_id={question_id}, concept_name={concept_name}")
        
        if concept_name:
            concept_performance[concept_name]['total_questions'] += 1
            if record['is_correct']:
                concept_performance[concept_name]['correct_answers'] += 1
            concept_performance[concept_name]['total_time'] += record['time_spent'] or 0
            concept_performance[concept_name]['difficulty_scores'].append(record['difficulty_level'] or 0.5)
    
    logger.info(f"分析完成，找到 {len(concept_performance)} 個知識點")
    for concept, data in concept_performance.items():
        logger.info(f"知識點 {concept}: {data['total_questions']} 題, {data['correct_answers']} 正確")
    
    return dict(concept_performance)

def extract_concept_from_question(question_id: str) -> Optional[str]:
    """從題目 ID 提取知識點（使用 key-points 和 detail-key-point）"""
    try:
        if not mongo:
            logger.warning("MongoDB 連接未初始化")
            return None
            
        # 從 MongoDB 中查找題目，使用 _id 字段匹配 ObjectId
        from bson import ObjectId
        try:
            object_id = ObjectId(question_id)
            question = mongo.db.exam.find_one({'_id': object_id})
        except Exception as e:
            logger.warning(f"無效的 ObjectId 格式: {question_id}, 錯誤: {e}")
            return None
            
        if not question:
            logger.warning(f"找不到題目 ID: {question_id}")
            return None
        
        # 獲取 key-points 和 detail-key-point
        key_points = question.get('key-points', '')
        detail_key_point = question.get('detail-key-point', '')
        
        logger.info(f"題目 {question_id}: key-points='{key_points}', detail-key-point='{detail_key_point}'")
        
        # 優先使用 detail-key-point，如果沒有則使用 key-points
        concept_name = detail_key_point if detail_key_point else key_points
        
        if not concept_name:
            logger.warning(f"題目 {question_id} 沒有知識點信息")
            return None
        
        # 從 micro_concept 集合中查找匹配的概念
        micro_concept = mongo.db.micro_concept.find_one({'name': concept_name})
        if micro_concept:
            logger.info(f"找到完全匹配的知識點: {concept_name}")
            return concept_name
        
        # 如果沒有找到完全匹配，嘗試模糊匹配
        micro_concepts = mongo.db.micro_concept.find({})
        for concept in micro_concepts:
            concept_name_db = concept.get('name', '')
            if concept_name in concept_name_db or concept_name_db in concept_name:
                logger.info(f"找到模糊匹配的知識點: {concept_name} -> {concept_name_db}")
                return concept_name_db
        
        # 如果還是沒有找到，返回原始概念名稱
        logger.info(f"使用原始概念名稱: {concept_name}")
        return concept_name
        
    except Exception as e:
        logger.error(f"提取知識點失敗: {e}")
        return None

# ==================== 掌握度計算函數 ====================

def calculate_concept_mastery(student_email: str, concept_name: str):
    """計算概念掌握度"""
    try:
        student_data = load_student_records(student_email)
        concept_performance = student_data.get('concept_performance', {}).get(concept_name, {})
        
        if not concept_performance or concept_performance['total_questions'] == 0:
            return {
                'mastery_level': 0.0,
                'practice_count': 0,
                'error_rate': 0.0,
                'status': '未知',
                'confidence': 0.0
            }
        
        # 使用改進的掌握度計算
        mastery_data = calculate_improved_mastery(concept_performance, concept_name)
        return mastery_data
        
    except Exception as e:
        logger.error(f"計算掌握度失敗: {e}")
        return {
            'mastery_level': 0.0,
            'practice_count': 0,
            'error_rate': 0.0,
            'status': '未知',
            'confidence': 0.0
        }

def calculate_improved_mastery(concept_performance: Dict, concept_name: str):
    """改進的掌握度計算"""
    total_questions = concept_performance['total_questions']
    correct_answers = concept_performance['correct_answers']
    total_time = concept_performance['total_time']
    difficulty_scores = concept_performance['difficulty_scores']
    
    if total_questions == 0:
        return {
            'mastery_level': 0.0,
            'practice_count': 0,
            'error_rate': 0.0,
            'status': '未知',
            'confidence': 0.0
        }
    
    # 基本準確率
    accuracy = correct_answers / total_questions
    
    # Wilson Score Interval (Agresti-Coull調整)
    n = total_questions
    p = accuracy
    z = 1.96  # 95% 置信區間
    n_adjusted = n + z**2
    p_adjusted = (correct_answers + z**2/2) / n_adjusted
    margin = z * np.sqrt((p_adjusted * (1 - p_adjusted)) / n_adjusted)
    wilson_lower = max(0, p_adjusted - margin)
    wilson_upper = min(1, p_adjusted + margin)
    wilson_score = (wilson_lower + wilson_upper) / 2
    
    # BKT 掌握度計算
    bkt_mastery = calculate_bkt_mastery(concept_performance, concept_name)
    
    # 時間因子
    avg_time = total_time / total_questions if total_questions > 0 else 0
    time_factor = calculate_time_factor(avg_time, difficulty_scores)
    
    # 最終掌握度
    final_mastery = calculate_final_mastery(wilson_score, bkt_mastery, time_factor)
    
    # 狀態判斷
    status = determine_status(final_mastery, wilson_score)
    
    return {
        'mastery_level': final_mastery,
        'practice_count': total_questions,
        'error_rate': 1 - accuracy,
        'status': status,
        'confidence': wilson_score,
        'wilson_score': wilson_score,
        'bkt_mastery': bkt_mastery,
        'time_factor': time_factor
    }

def calculate_bkt_mastery(concept_performance: Dict, concept_name: str) -> float:
    """BKT 掌握度計算"""
    total_questions = concept_performance['total_questions']
    correct_answers = concept_performance['correct_answers']
    
    if total_questions == 0:
        return 0.0
    
    # 簡化的BKT計算
    learning_rate = BKT_CONFIG['learning_alpha']
    forgetting_rate = BKT_CONFIG['forgetting_rate']
    
    # 基於答題歷史的掌握度估計
    mastery = 0.0
    for i in range(total_questions):
        if i < correct_answers:
            mastery = mastery + learning_rate * (1 - mastery)
        else:
            mastery = mastery * (1 - forgetting_rate)
    
    return min(1.0, mastery)

def calculate_time_factor(avg_time: float, difficulty_scores: List[float]) -> float:
    """計算時間因子"""
    if not difficulty_scores:
        return 1.0
    
    avg_difficulty = np.mean(difficulty_scores)
    expected_time = avg_difficulty * 60  # 預期時間（秒）
    
    if expected_time == 0:
        return 1.0
    
    time_ratio = avg_time / expected_time
    
    # 時間因子：太快或太慢都會降低掌握度
    if time_ratio < 0.5:  # 太快，可能是猜的
        return 0.8
    elif time_ratio > 2.0:  # 太慢，可能不熟練
        return 0.9
    else:
        return 1.0

def calculate_final_mastery(wilson_score: float, bkt_mastery: float, time_factor: float) -> float:
    """計算最終掌握度"""
    # 加權平均
    weights = [0.4, 0.4, 0.2]  # Wilson, BKT, 時間因子
    final_mastery = (wilson_score * weights[0] + 
                    bkt_mastery * weights[1] + 
                    time_factor * weights[2])
    
    return min(1.0, max(0.0, final_mastery))

def determine_status(mastery_score: float, confidence: float) -> str:
    """判斷學習狀態"""
    if mastery_score >= BKT_CONFIG['mastery_threshold'] and confidence >= 0.7:
        return '已掌握'
    elif mastery_score >= BKT_CONFIG['struggling_threshold']:
        return '學習中'
    else:
        return '需加強'

# ==================== 學習分析函數 ====================

def generate_weakness_analysis(student_email: str):
    """生成弱點分析"""
    try:
        student_data = load_student_records(student_email)
        concept_performance = student_data.get('concept_performance', {})
        
        weaknesses = []
        for concept, performance in concept_performance.items():
            mastery_data = calculate_improved_mastery(performance, concept)
            if mastery_data['status'] in ['需加強', '學習中']:
                weaknesses.append({
                    'concept': concept,
                    'mastery_level': mastery_data['mastery_level'],
                    'practice_count': mastery_data['practice_count'],
                    'error_rate': mastery_data['error_rate'],
                    'status': mastery_data['status']
                })
        
        # 按掌握度排序
        weaknesses.sort(key=lambda x: x['mastery_level'])
        
        return {
            'total_weaknesses': len(weaknesses),
            'weaknesses': weaknesses[:10],  # 前10個弱點
            'analysis_time': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"生成弱點分析失敗: {e}")
        return {'total_weaknesses': 0, 'weaknesses': []}

def generate_learning_path(student_email: str, focus_weaknesses: bool = False):
    """生成學習路徑"""
    try:
        knowledge_structure = load_knowledge_structure()
        
        if focus_weaknesses:
            # 專注於弱點
            weakness_analysis = generate_weakness_analysis(student_email)
            learning_path = []
            for w in weakness_analysis['weaknesses'][:5]:
                if isinstance(w, dict) and 'concept' in w:
                    learning_path.append({
                        'concept': w['concept'],
                        'type': 'concept',
                        'estimated_time': 45,  # 每個概念45分鐘
                        'difficulty': 'high'
                    })
                elif isinstance(w, str):
                    learning_path.append({
                        'concept': w,
                        'type': 'concept',
                        'estimated_time': 45,
                        'difficulty': 'high'
                    })
        else:
            # 基於知識結構的學習路徑
            learning_path = generate_structured_learning_path(knowledge_structure)
        
        return {
            'learning_path': learning_path,
            'total_concepts': len(learning_path),
            'estimated_time': len(learning_path) * 30,  # 每個概念30分鐘
            'focus_weaknesses': focus_weaknesses
        }
        
    except Exception as e:
        logger.error(f"生成學習路徑失敗: {e}")
        return {'learning_path': [], 'total_concepts': 0}

def build_knowledge_hierarchy(knowledge_structure, student_email):
    """構建層級式知識結構"""
    hierarchy = []
    
    for domain in knowledge_structure.get('domains', []):
        domain_data = {
            'id': str(domain['_id']),
            'name': domain['name'],
            'type': 'domain',
            'description': domain.get('description', ''),
            'mastery_level': 0.0,  # 默認掌握度
            'practice_count': 0,
            'status': '未開始',
            'blocks': []
        }
        
        # 添加該領域下的章節
        for block in knowledge_structure.get('blocks', []):
            if block.get('domain_id') == domain['_id']:
                block_data = {
                    'id': str(block['_id']),
                    'name': block['title'],
                    'type': 'block',
                    'description': block.get('description', ''),
                    'mastery_level': 0.0,
                    'practice_count': 0,
                    'status': '未開始',
                    'concepts': []
                }
                
                # 添加該章節下的概念
                for concept in knowledge_structure.get('micro_concepts', []):
                    if concept.get('block_id') == block['_id']:
                        concept_data = {
                            'id': str(concept['_id']),
                            'name': concept['name'],
                            'type': 'concept',
                            'description': concept.get('description', ''),
                            'mastery_level': 0.0,
                            'practice_count': 0,
                            'status': '未開始',
                            'confidence': 0.0
                        }
                        block_data['concepts'].append(concept_data)
                
                domain_data['blocks'].append(block_data)
        
        hierarchy.append(domain_data)
    
    return hierarchy

def build_knowledge_hierarchy_with_mastery(knowledge_structure, student_email, concept_mastery_data):
    """構建帶有掌握度數據的層級式知識結構"""
    hierarchy = []
    
    for domain in knowledge_structure.get('domains', []):
        domain_data = {
            'id': str(domain['_id']),
            'name': domain['name'],
            'type': 'domain',
            'description': domain.get('description', ''),
            'mastery_level': 0.0,
            'practice_count': 0,
            'status': '未開始',
            'blocks': []
        }
        
        domain_mastery_sum = 0.0
        domain_concept_count = 0
        
        # 添加該領域下的章節
        for block in knowledge_structure.get('blocks', []):
            if block.get('domain_id') == domain['_id']:
                block_data = {
                    'id': str(block['_id']),
                    'name': block['title'],
                    'type': 'block',
                    'description': block.get('description', ''),
                    'mastery_level': 0.0,
                    'practice_count': 0,
                    'status': '未開始',
                    'concepts': []
                }
                
                block_mastery_sum = 0.0
                block_concept_count = 0
                
                # 添加該章節下的概念
                for concept in knowledge_structure.get('micro_concepts', []):
                    if concept.get('block_id') == block['_id']:
                        concept_name = concept['name']
                        mastery_data = concept_mastery_data.get(concept_name, {
                            'mastery_level': 0.0,
                            'practice_count': 0,
                            'status': '未知',
                            'confidence': 0.0
                        })
                        
                        concept_data = {
                            'id': str(concept['_id']),
                            'name': concept_name,
                            'type': 'concept',
                            'description': concept.get('description', ''),
                            'mastery_level': mastery_data['mastery_level'],
                            'practice_count': mastery_data['practice_count'],
                            'status': mastery_data['status'],
                            'confidence': mastery_data['confidence']
                        }
                        block_data['concepts'].append(concept_data)
                        
                        block_mastery_sum += mastery_data['mastery_level']
                        block_concept_count += 1
                
                # 計算章節掌握度
                if block_concept_count > 0:
                    block_data['mastery_level'] = block_mastery_sum / block_concept_count
                    block_data['practice_count'] = sum(c['practice_count'] for c in block_data['concepts'])
                    block_data['status'] = determine_status(block_data['mastery_level'], block_data['mastery_level'])
                
                domain_data['blocks'].append(block_data)
                domain_mastery_sum += block_data['mastery_level']
                domain_concept_count += 1
        
        # 計算領域掌握度
        if domain_concept_count > 0:
            domain_data['mastery_level'] = domain_mastery_sum / domain_concept_count
            domain_data['practice_count'] = sum(b['practice_count'] for b in domain_data['blocks'])
            domain_data['status'] = determine_status(domain_data['mastery_level'], domain_data['mastery_level'])
        
        hierarchy.append(domain_data)
    
    return hierarchy

def generate_structured_learning_path(knowledge_structure):
    """生成結構化學習路徑"""
    if not knowledge_structure:
        return []
    
    path = []
    for domain in knowledge_structure.get('domains', []):
        domain_name = domain['name']
        path.append({
            'concept': domain_name,
            'type': 'domain',
            'estimated_time': 60,  # 每個領域60分鐘
            'difficulty': 'medium'
        })
        
        # 添加該領域的章節
        for block in knowledge_structure.get('blocks', []):
            if block.get('domain_id') == domain['_id']:
                path.append({
                    'concept': block['title'],
                    'type': 'block',
                    'estimated_time': 30,  # 每個章節30分鐘
                    'difficulty': 'medium'
                })
    
    return path[:10]  # 限制路徑長度

# ==================== Neo4j 知識圖譜函數 ====================

def get_concept_context(concept_name: str):
    """從 Neo4j 獲取概念上下文"""
    try:
        driver = get_neo4j_driver()
        if not driver:
            return {}
        
        with driver.session() as session:
            # 查詢概念及其相關節點
            query = """
            MATCH (c {name: $concept_name})
            OPTIONAL MATCH (c)-[r]-(related)
            RETURN c, r, related
            LIMIT 20
            """
            
            result = session.run(query, concept_name=concept_name)
            context = {
                'concept': None,
                'relationships': [],
                'related_concepts': []
            }
            
            for record in result:
                if record['c']:
                    context['concept'] = dict(record['c'])
                if record['r'] and record['related']:
                    context['relationships'].append({
                        'type': record['r'].type,
                        'related': dict(record['related'])
                    })
            
            return context
            
    except Exception as e:
        logger.error(f"獲取概念上下文失敗: {e}")
        return {}

def build_knowledge_graph_context(concept_name: str):
    """構建知識圖譜上下文"""
    try:
        # 從 Neo4j 獲取上下文
        neo4j_context = get_concept_context(concept_name)
        
        # 從 MongoDB 獲取基本資訊
        if mongo.db:
            concept_info = mongo.db.micro_concept.find_one({'name': concept_name})
            if concept_info:
                neo4j_context['mongo_info'] = {
                    'description': concept_info.get('description', ''),
                    'block_id': str(concept_info.get('_id', ''))
                }
        
        return {
            "concept_name": concept_name,
            "neo4j_context": neo4j_context,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"構建知識圖譜上下文失敗: {e}")
        return {"concept_name": concept_name, "neo4j_context": {}}

# ==================== AI 分析函數 ====================

def generate_ai_learning_advice(concept_name: str, student_email: str):
    """生成 AI 學習建議"""
    try:
        # 獲取學生掌握度數據
        mastery_data = calculate_concept_mastery(student_email, concept_name)
        
        # 獲取知識圖譜上下文
        knowledge_context = build_knowledge_graph_context(concept_name)
        
        # 獲取弱點分析
        weakness_analysis = generate_weakness_analysis(student_email)
        
        # 構建 AI 提示詞
        prompt = f"""
        作為一位專業的學習顧問，請為學生提供關於「{concept_name}」的個人化學習建議。

        學生當前掌握度：{mastery_data['mastery_level']:.1%}
        練習次數：{mastery_data['practice_count']} 次
        錯誤率：{mastery_data['error_rate']:.1%}
        學習狀態：{mastery_data['status']}

        知識圖譜上下文：{json.dumps(knowledge_context, ensure_ascii=False, indent=2)}

        弱點分析：{json.dumps(weakness_analysis, ensure_ascii=False, indent=2)}

        請提供：
        1. 當前學習狀態分析
        2. 具體的學習建議
        3. 推薦的學習順序
        4. 練習建議
        5. 注意事項

        請用繁體中文回答，內容要具體且實用。
        """
        
        # 調用 AI
        genai_model = init_gemini()
        if genai_model:
            response = genai_model.generate_content(prompt)
            return {
                'advice': response.text,
                'mastery_analysis': mastery_data,
                'knowledge_context': knowledge_context,
                'timestamp': datetime.now().isoformat()
            }
        else:
            return {
                'advice': 'AI 服務暫時無法使用，請稍後再試。',
                'mastery_analysis': mastery_data,
                'knowledge_context': knowledge_context,
                'timestamp': datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"生成 AI 學習建議失敗: {e}")
        return {
            'advice': '生成學習建議時發生錯誤，請稍後再試。',
            'mastery_analysis': mastery_data,
            'knowledge_context': {},
            'timestamp': datetime.now().isoformat()
        }

# ==================== API 端點 ====================

# 創建藍圖
learning_analytics_bp = Blueprint('learning_analytics', __name__)

@learning_analytics_bp.route('/learning-analysis/current', methods=['GET'])
def get_learning_analysis():
    """獲取當前學生的學習分析"""
    try:
        # 使用統一的 token 驗證方式
        from .api import verify_token
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        student_email = verify_token(token)
        
        if not student_email:
            return jsonify({'error': '認證失敗，請重新登錄'}), 401
        
        # 獲取參數
        domain = request.args.get('domain')
        focus_weaknesses = request.args.get('focus_weaknesses', 'false').lower() == 'true'
        
        # 載入數據
        knowledge_structure = load_knowledge_structure()
        student_records = load_student_records(student_email)
        weakness_analysis = generate_weakness_analysis(student_email)
        learning_path = generate_learning_path(student_email, focus_weaknesses)
        
        # 計算統計數據
        total_concepts = len(knowledge_structure.get('micro_concepts', []))
        mastered_concepts = 0
        learning_concepts = 0
        struggling_concepts = 0
        total_mastery = 0.0
        
        # 為每個概念計算掌握度
        concept_mastery_data = {}
        for concept in knowledge_structure.get('micro_concepts', []):
            mastery_data = calculate_concept_mastery(student_email, concept['name'])
            concept_mastery_data[concept['name']] = mastery_data
            
            if mastery_data['status'] == '已掌握':
                mastered_concepts += 1
            elif mastery_data['status'] == '學習中':
                learning_concepts += 1
            else:
                struggling_concepts += 1
            
            total_mastery += mastery_data['mastery_level']
        
        # 計算整體掌握度
        overall_mastery = (total_mastery / total_concepts * 100) if total_concepts > 0 else 0.0
        
        # 構建響應結構
        response_data = {
            'student_email': student_email,
            'generated_at': datetime.now().isoformat(),
            'overview': {
                'total_domains': len(knowledge_structure.get('domains', [])),
                'total_blocks': len(knowledge_structure.get('blocks', [])),
                'total_concepts': total_concepts,
                'total_practice_count': student_records.get('total_questions', 0),
                'overall_mastery': overall_mastery,
                'mastered_concepts': mastered_concepts,
                'learning_concepts': learning_concepts,
                'struggling_concepts': struggling_concepts
            },
            'knowledge_hierarchy': build_knowledge_hierarchy_with_mastery(knowledge_structure, student_email, concept_mastery_data),
            'learning_path': learning_path.get('learning_path', [])[:5]  # 只返回前5個學習步驟
        }
        
        return jsonify({
            'success': True,
            'data': response_data
        })
        
    except Exception as e:
        logger.error(f"獲取學習分析失敗: {e}")
        return jsonify({
            'success': False,
            'error': '獲取學習分析失敗'
        }), 500

@learning_analytics_bp.route('/concept-basic-info/<concept_name>', methods=['GET'])
def get_concept_basic_info(concept_name: str):
    """獲取概念基本資訊"""
    try:
        # 使用統一的 token 驗證方式
        from .api import verify_token
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        student_email = verify_token(token)
        
        if not student_email:
            return jsonify({'error': '認證失敗，請重新登錄'}), 401
        
        # 計算掌握度數據
        mastery_data = calculate_concept_mastery(student_email, concept_name)
        
        # 獲取子概念
        sub_concepts = []
        if mongo.db:
            # 查找相關的子概念
            related_concepts = mongo.db.micro_concept.find({
                'name': {'$regex': concept_name, '$options': 'i'}
            }).limit(5)
            sub_concepts = [{'name': c['name'], 'description': c.get('description', '')} for c in related_concepts]
        
        response_data = {
            'concept_name': concept_name,
            'mastery_level': mastery_data['mastery_level'],
            'practice_count': mastery_data['practice_count'],
            'error_rate': mastery_data['error_rate'],
            'status': mastery_data['status'],
            'confidence': mastery_data['confidence'],
            'sub_concepts': sub_concepts,
            'last_practice': '無記錄',  # 可以從學生記錄中獲取
            'difficulty_level': '中等'  # 可以從題目數據中計算
        }
        
        return jsonify({
            'success': True,
            'data': response_data
        })
        
    except Exception as e:
        logger.error(f"獲取概念基本資訊失敗: {e}")
        return jsonify({
            'success': False,
            'error': '獲取概念基本資訊失敗'
        }), 500

@learning_analytics_bp.route('/concept-analysis/<concept_name>', methods=['GET'])
def get_concept_analysis(concept_name: str):
    """獲取概念 AI 分析"""
    try:
        # 使用統一的 token 驗證方式
        from .api import verify_token
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        student_email = verify_token(token)
        
        if not student_email:
            return jsonify({'error': '認證失敗，請重新登錄'}), 401
        
        # 生成 AI 學習建議
        ai_analysis = generate_ai_learning_advice(concept_name, student_email)
        
        response_data = {
            'concept_name': concept_name,
            'mastery_analysis': ai_analysis['mastery_analysis'],
            'ai_advice': ai_analysis['advice'],
            'knowledge_context': ai_analysis['knowledge_context'],
            'timestamp': ai_analysis['timestamp']
        }
        
        return jsonify({
            'success': True,
            'data': response_data
        })
        
    except Exception as e:
        logger.error(f"獲取概念分析失敗: {e}")
        return jsonify({
            'success': False,
            'error': '獲取概念分析失敗'
        }), 500

@learning_analytics_bp.route('/add-to-calendar', methods=['POST'])
def add_to_calendar():
    """添加到行事曆"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '未提供數據'}), 400
        
        # 這裡可以實現添加到行事曆的邏輯
        # 目前只是返回成功響應
        
        return jsonify({
            'success': True,
            'message': '已添加到學習計劃',
            'data': data
        })
        
    except Exception as e:
        logger.error(f"添加到行事曆失敗: {e}")
        return jsonify({'error': '添加到行事曆失敗'}), 500

# ==================== 向後兼容 ====================

# 為了向後兼容，提供舊的函數名
def cross_db_analytics():
    """向後兼容的別名"""
    return {
        'load_knowledge_structure': load_knowledge_structure,
        'load_student_records': load_student_records,
        'calculate_concept_mastery': calculate_concept_mastery,
        'generate_weakness_analysis': generate_weakness_analysis,
        'generate_learning_path': generate_learning_path
    }

# 創建全局實例
unified_analytics = cross_db_analytics()