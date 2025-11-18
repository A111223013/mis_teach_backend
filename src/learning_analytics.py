import logging
import math
import json
import time
import os
import threading
import concurrent.futures
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from flask import Blueprint, request, jsonify
from sqlalchemy import text
from accessories import sqldb, mongo, init_gemini, redis_client
from bson import ObjectId
from src.api import get_user_info
from src.quiz_generator import generate_quiz_by_ai

# 設置日誌
logger = logging.getLogger(__name__)

# 創建藍圖
analytics_bp = Blueprint('learning_analytics', __name__)

def get_student_quiz_records(user_email: str) -> List[Dict]:
    """獲取學生的答題記錄"""
    try:
        # 查詢答題記錄，直接從 quiz_answers 表獲取
        query = text("""
            SELECT 
                qa.answer_id as answer_id,
                qa.mongodb_question_id as question_id,
                qa.created_at as attempt_time,
                qa.answer_time_seconds as time_spent,
                qa.is_correct
            FROM quiz_answers qa
            WHERE qa.user_email = :user_email
            ORDER BY qa.created_at DESC
        """)
        
        result = sqldb.session.execute(query, {"user_email": user_email})
        records = result.fetchall()
        
        quiz_records = []
        for row in records:
            # 從 MongoDB 獲取題目詳細信息
            question_doc = mongo.db.exam.find_one({"_id": ObjectId(row.question_id)})
            if question_doc:
                # 處理微概念數組
                micro_concepts = question_doc.get('micro_concepts', [])
                micro_concept_id = str(micro_concepts[0]) if micro_concepts else ''
                
                # 從key-points獲取領域信息
                key_points = question_doc.get('key-points', '')
                
                # 獲取難度信息，處理不同的字段名
                difficulty = (question_doc.get('difficulty level') or 
                            question_doc.get('difficulty') or 
                            question_doc.get('level') or 
                            '中等')
                
                # 獲取領域信息 - 嘗試多個字段
                domain_name = (question_doc.get('domain') or 
                             question_doc.get('subject') or 
                             question_doc.get('field') or 
                             key_points or 
                             '未知領域')
                
                quiz_records.append({
                    'id': row.answer_id,
                    'question_id': row.question_id,
                    'attempt_time': row.attempt_time.isoformat() + 'Z',
                    'time_spent': row.time_spent or 0,
                    'is_correct': bool(row.is_correct),
                    'micro_concept_id': micro_concept_id,
                    'domain_name': domain_name,  # 使用更準確的領域名稱
                    'difficulty': difficulty,
                    'key_points': key_points  # 保留原始key-points用於調試
                })
        
        logger.info(f"獲取到 {len(quiz_records)} 條答題紀錄")
        
        # 調試信息：顯示領域分佈
        domain_counts = {}
        for record in quiz_records:
            domain = record['domain_name']
            domain_counts[domain] = domain_counts.get(domain, 0) + 1
        
        return quiz_records
            
    except Exception as e:
        logger.error(f"獲取學生答題紀錄失敗: {str(e)}")
        return []

def calculate_difficulty_statistics(quiz_records: List[Dict]) -> Dict[str, Any]:
    """計算各難度的統計數據"""
    if not quiz_records:
        return {
            'easy': {'total': 0, 'correct': 0, 'accuracy': 0.0, 'mastery': 0.0},
            'medium': {'total': 0, 'correct': 0, 'accuracy': 0.0, 'mastery': 0.0},
            'hard': {'total': 0, 'correct': 0, 'accuracy': 0.0, 'mastery': 0.0}
        }
    
    difficulty_stats = {
        'easy': {'total': 0, 'correct': 0, 'records': []},
        'medium': {'total': 0, 'correct': 0, 'records': []},
        'hard': {'total': 0, 'correct': 0, 'records': []}
    }
    
    # 統計各難度的答題情況
    for record in quiz_records:
        difficulty = record.get('difficulty', '中等')
        if difficulty == '簡單':
            key = 'easy'
        elif difficulty == '困難':
            key = 'hard'
        else:
            key = 'medium'
        
        difficulty_stats[key]['total'] += 1
        difficulty_stats[key]['records'].append(record)
        if record.get('is_correct', False):
            difficulty_stats[key]['correct'] += 1
    
    # 計算準確率和掌握度
    result = {}
    for key, stats in difficulty_stats.items():
        total = stats['total']
        correct = stats['correct']
        accuracy = correct / total if total > 0 else 0.0
        
        # 計算該難度的掌握度
        mastery = calculate_mixed_mastery(stats['records']) if stats['records'] else 0.0
        
        result[key] = {
            'total': total,
            'correct': correct,
            'accuracy': round(accuracy, 3),
            'mastery': round(mastery, 3)
        }
    
    return result

def calculate_historical_metrics(quiz_records: List[Dict], trend_days: int) -> Dict[str, Any]:
    """計算歷史數據用於趨勢分析"""
    if not quiz_records:
        return {
            'learning_velocity': 0,
            'retention_rate': 0,
            'avg_time_per_concept': 0,
            'focus_score': 0
        }
    
    # 計算歷史期間（前一個週期）
    from datetime import datetime, timedelta
    current_time = datetime.now()
    historical_start = current_time - timedelta(days=trend_days*2)
    historical_end = current_time - timedelta(days=trend_days)
    
    # 篩選歷史期間的記錄
    historical_records = []
    for record in quiz_records:
        try:
            record_time = datetime.fromisoformat(record['attempt_time'].replace('Z', '+00:00'))
            if historical_start <= record_time < historical_end:
                historical_records.append(record)
        except:
            continue
    
    # 如果沒有歷史數據，返回當前數據的80%作為基準
    if not historical_records:
        current_metrics = calculate_learning_metrics(quiz_records)
        return {
            'learning_velocity': current_metrics['learning_velocity'] * 0.8,
            'retention_rate': current_metrics['retention_rate'] * 0.8,
            'avg_time_per_concept': current_metrics['avg_time_per_concept'] * 1.2,  # 時間越少越好
            'focus_score': current_metrics['focus_score'] * 0.8
        }
    
    # 計算歷史指標
    return calculate_learning_metrics(historical_records)

def calculate_learning_metrics(quiz_records: List[Dict]) -> Dict[str, Any]:
    """計算學習效率指標"""
    if not quiz_records:
        return {
            'learning_velocity': 0,
            'retention_rate': 0,
            'avg_time_per_concept': 0,
            'focus_score': 0,
            'overall_mastery': 0
        }
    
    # 學習速度：使用增強版演算法
    learning_velocity = calculate_enhanced_learning_velocity(quiz_records)
    
    # 保持率：使用增強版遺忘感知演算法
    retention_rate = calculate_enhanced_retention_rate(quiz_records)
    
    # 平均每概念時間：使用增強版時間分析演算法
    avg_time_per_concept = calculate_enhanced_avg_time_per_concept(quiz_records)
    
    # 專注度：使用增強版專注度分析演算法
    focus_score = calculate_enhanced_focus_score(quiz_records) * 10  # 轉換為10分制
        
    # 使用混合演算法計算整體掌握度
    overall_mastery = calculate_mixed_mastery(quiz_records)
    difficulty_aware_mastery = overall_mastery
    forgetting_aware_mastery = overall_mastery
    
    # 計算額外的統計數據
    total_questions = len(quiz_records)
    correct_questions = sum(1 for r in quiz_records if r.get('is_correct', False))
    wrong_questions = total_questions - correct_questions
    accuracy_rate = correct_questions / total_questions if total_questions > 0 else 0
    error_rate = wrong_questions / total_questions if total_questions > 0 else 0
    
    # 計算各難度的統計
    difficulty_stats = calculate_difficulty_statistics(quiz_records)
    
    return {
        'learning_velocity': round(learning_velocity, 1),
        'retention_rate': round(retention_rate, 3),  # 保持0-1範圍，前端會轉換為百分比
        'avg_time_per_concept': round(avg_time_per_concept, 1),
        'focus_score': round(focus_score, 1),
        'overall_mastery': round(overall_mastery, 3),
        'difficulty_aware_mastery': round(difficulty_aware_mastery, 3),
        'forgetting_aware_mastery': round(forgetting_aware_mastery, 3),
        # 新增統計數據
        'total_questions': total_questions,
        'correct_questions': correct_questions,
        'wrong_questions': wrong_questions,
        'accuracy_rate': round(accuracy_rate, 3),
        'error_rate': round(error_rate, 3),
        'difficulty_stats': difficulty_stats
    }

def calculate_concept_mastery(quiz_records: List[Dict], concept_id: str) -> Dict[str, Any]:
    """計算特定概念的掌握度 - 使用新的Knowledge Tracing演算法"""
    concept_records = [r for r in quiz_records if r['micro_concept_id'] == concept_id]
    
    if not concept_records:
        return {
            'mastery': 0,
            'attempts': 0,
            'correct': 0,
            'wrong_count': 0,
            'recent_accuracy': 0,
            'trend': 'stable',
            'difficulty_breakdown': {'簡單': 0, '中等': 0, '困難': 0},
            'forgetting_analysis': {
                'base_mastery': 0,
                'current_mastery': 0,
                'days_since_practice': 0,
                'review_urgency': 'low'
            }
        }
    
    # 使用新的演算法計算掌握度
    difficulty_data = calculate_difficulty_aware_mastery(quiz_records, concept_id)
    forgetting_data = calculate_forgetting_aware_mastery(concept_records, concept_id)
    
    # 使用難度感知的掌握度作為主要掌握度
    enhanced_mastery = difficulty_data['overall_mastery']
    
    # 計算基本統計數據
    total_attempts = len(concept_records)
    correct_attempts = sum(1 for r in concept_records if r['is_correct'])
    wrong_count = total_attempts - correct_attempts
    
    # 最近5次答題的正確率
    recent_records = concept_records[:5]
    recent_correct = sum(1 for r in recent_records if r['is_correct'])
    recent_accuracy = recent_correct / len(recent_records) if recent_records else 0
    
    # 趨勢分析（基於遺忘感知的掌握度變化）
    base_mastery = forgetting_data['base_mastery']
    current_mastery = forgetting_data['current_mastery']
    
    if current_mastery > base_mastery + 0.1:
            trend = 'improving'
    elif current_mastery < base_mastery - 0.1:
            trend = 'declining'
    else:
        trend = 'stable'
    
    return {
        'mastery': round(enhanced_mastery, 2),  # 使用新演算法的掌握度
        'attempts': total_attempts,
        'correct': correct_attempts,
        'wrong_count': wrong_count,
        'recent_accuracy': round(recent_accuracy, 2),
        'trend': trend,
        # 新演算法的詳細結果
        'difficulty_breakdown': difficulty_data['difficulty_breakdown'],
        'forgetting_analysis': {
            'base_mastery': forgetting_data['base_mastery'],
            'current_mastery': forgetting_data['current_mastery'],
            'days_since_practice': forgetting_data['days_since_practice'],
            'review_urgency': forgetting_data['review_urgency']
        },
        'difficulty_analysis': difficulty_data['difficulty_analysis']
    }

def calculate_difficulty_aware_mastery(quiz_records: List[Dict], concept_id: str) -> Dict[str, Any]:
    """計算難度感知的掌握度 - Difficulty-aware KT"""
    # 如果是領域ID，直接使用所有記錄；如果是微概念ID，則篩選
    if len(concept_id) == 24:  # MongoDB ObjectId長度
        # 可能是領域ID，直接使用所有記錄
        concept_records = quiz_records
    else:
        # 微概念ID，按micro_concept_id篩選
        concept_records = [r for r in quiz_records if r['micro_concept_id'] == concept_id]
    
    if not concept_records:
        return {
            'overall_mastery': 0,
            'difficulty_breakdown': {'簡單': 0, '中等': 0, '困難': 0},
            'difficulty_analysis': {
                'easy_mastery': 0,
                'medium_mastery': 0,
                'hard_mastery': 0,
                'bottleneck_level': 'none',
                'recommended_difficulty': '簡單'
            }
        }
    
    # 按難度分組統計
    difficulty_stats = {}
    for record in concept_records:
        difficulty = record.get('difficulty', '中等')
        if difficulty not in difficulty_stats:
            difficulty_stats[difficulty] = {'total': 0, 'correct': 0}
        difficulty_stats[difficulty]['total'] += 1
        if record['is_correct']:
            difficulty_stats[difficulty]['correct'] += 1
    # 計算各難度掌握度
    difficulty_breakdown = {}
    for difficulty in ['簡單', '中等', '困難']:
        if difficulty in difficulty_stats:
            stats = difficulty_stats[difficulty]
            mastery = stats['correct'] / stats['total'] if stats['total'] > 0 else 0
            difficulty_breakdown[difficulty] = round(mastery, 2)
        else:
            difficulty_breakdown[difficulty] = 0
    
    # 計算加權掌握度（困難題權重更高）
    difficulty_weights = {'簡單': 1, '中等': 2, '困難': 3}
    weighted_mastery = 0
    total_weight = 0
    
    for difficulty, stats in difficulty_stats.items():
        weight = difficulty_weights.get(difficulty, 2)
        mastery = stats['correct'] / stats['total'] if stats['total'] > 0 else 0
        weighted_mastery += mastery * weight
        total_weight += weight
    
    overall_mastery = weighted_mastery / total_weight if total_weight > 0 else 0
    
    # 分析學習瓶頸
    easy_mastery = difficulty_breakdown.get('簡單', 0)
    medium_mastery = difficulty_breakdown.get('中等', 0)
    hard_mastery = difficulty_breakdown.get('困難', 0)
    
    if easy_mastery < 0.6:
        bottleneck_level = 'easy'
        recommended_difficulty = '簡單'
    elif medium_mastery < 0.6:
        bottleneck_level = 'medium'
        recommended_difficulty = '中等'
    elif hard_mastery < 0.6:
        bottleneck_level = 'hard'
        recommended_difficulty = '困難'
    else:
        bottleneck_level = 'none'
        recommended_difficulty = '困難'  # 可以挑戰更難的題目
    
    return {
        'overall_mastery': round(overall_mastery, 2),
        'difficulty_breakdown': difficulty_breakdown,
        'difficulty_analysis': {
            'easy_mastery': easy_mastery,
            'medium_mastery': medium_mastery,
            'hard_mastery': hard_mastery,
            'bottleneck_level': bottleneck_level,
            'recommended_difficulty': recommended_difficulty
        }
    }

def calculate_forgetting_aware_mastery(concept_records: List[Dict], concept_id: str) -> Dict[str, Any]:
    """計算遺忘感知的掌握度 - Forgetting-aware KT"""
    if not concept_records:
        return {
            'base_mastery': 0,
            'current_mastery': 0,
            'forgetting_factor': 1.0,
            'days_since_practice': 0,
            'review_urgency': 'low',
            'forgetting_curve_data': []
        }
    
    # 計算基礎掌握度
    total_attempts = len(concept_records)
    correct_attempts = sum(1 for r in concept_records if r['is_correct'])
    base_mastery = correct_attempts / total_attempts if total_attempts > 0 else 0
    
    # 獲取最後練習時間
    last_practice = max(record['attempt_time'] for record in concept_records)
    last_practice_time = datetime.fromisoformat(last_practice.replace('Z', '+00:00'))
    
    # 計算時間差（天）
    from datetime import timezone
    time_diff = (datetime.now(timezone.utc) - last_practice_time).days
    
    # 計算遺忘衰減因子（基於艾賓浩斯遺忘曲線）
    forgetting_rate = 0.1  # 可調整參數，控制遺忘速度
    forgetting_factor = math.exp(-forgetting_rate * time_diff)
    
    # 計算當前有效掌握度
    current_mastery = base_mastery * forgetting_factor
    
    # 判斷複習緊急程度
    if time_diff > 7:
        review_urgency = 'high'
    elif time_diff > 3:
        review_urgency = 'medium'
    else:
        review_urgency = 'low'
    
    # 生成遺忘曲線數據（用於前端展示）
    forgetting_curve_data = []
    for days in range(0, 15):  # 生成15天的遺忘曲線
        decay_factor = math.exp(-forgetting_rate * days)
        predicted_mastery = base_mastery * decay_factor
        forgetting_curve_data.append({
            'days': days,
            'mastery': round(predicted_mastery, 2)
        })
    
    return {
        'base_mastery': round(base_mastery, 2),
        'current_mastery': round(current_mastery, 2),
        'forgetting_factor': round(forgetting_factor, 2),
        'days_since_practice': time_diff,
        'review_urgency': review_urgency,
        'forgetting_curve_data': forgetting_curve_data
    }

def get_knowledge_structure():
    """獲取知識結構"""
    try:
        domains = list(mongo.db.domain.find({}))
        blocks = list(mongo.db.block.find({}))
        concepts = list(mongo.db.micro_concept.find({}))
        
        return {
            'domains': domains,
            'blocks': blocks,
            'concepts': concepts
        }
    except Exception as e:
        logger.error(f"獲取知識結構失敗: {str(e)}")
        return {'domains': [], 'blocks': [], 'concepts': []}

# 已移除 /overview API - 功能已整合到 /init-data
@analytics_bp.route('/ai-diagnosis', methods=['POST', 'OPTIONS'])
def ai_diagnosis():
    """AI診斷特定知識點"""
    if request.method == 'OPTIONS':
        return jsonify({'success': True})
    
    try:
        data = request.get_json()
        concept_id = data.get('concept_id')
        concept_name = data.get('concept_name', '未知概念')
        domain_name = data.get('domain_name', '未知領域')
        if not concept_id:
            logger.error("錯誤: 缺少概念ID")
            return jsonify({'error': '缺少概念ID'}), 400
        
        # 獲取用戶信息
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': '缺少認證信息'}), 401
        
        token = auth_header.split(' ')[1]
        user_email = get_user_info(token, 'email')
        
        if not user_email:
            return jsonify({'error': '無法獲取用戶信息'}), 401
        
        # 檢查Redis快取
        # 使用標準化的快取鍵格式：learning_analytics:ai_diagnosis:{user_email}:{concept_id}:{concept_name}
        # 確保每個知識點都有獨立的快取，與前端存儲命名保持一致
        cache_key = f"learning_analytics:ai_diagnosis:{user_email}:{concept_id}:{concept_name}"
        cached_data = redis_client.get(cache_key)
        if cached_data:
            # 檢查鍵是否還有過期時間（避免使用已過期的快取）
            ttl = redis_client.ttl(cache_key)
            if ttl > 0:
                logger.info(f"✅ 使用AI診斷快取: {cache_key} (剩餘 {ttl} 秒) - 跳過所有查詢")
                return json.loads(cached_data)
            else:
                # 如果鍵存在但已過期，刪除它（Redis 會自動刪除，但我們明確刪除以確保）
                redis_client.delete(cache_key)
                logger.info(f"⏰ AI診斷快取已過期，刪除: {cache_key}")
        else:
            logger.info(f"❌ AI診斷快取不存在: {cache_key} - 將執行查詢")
        
        # 只有在快取不存在時才執行以下查詢
        logger.info(f"🔄 開始執行AI診斷查詢流程...")
        
        # 獲取該概念的答題記錄
        quiz_records = get_student_quiz_records(user_email)
        
        # 嘗試用ID和名稱匹配
        # 注意：micro_concept_id字段實際包含的是概念名稱，不是ObjectId
        concept_records = [r for r in quiz_records if 
                          r.get('micro_concept_id') == concept_name or  # 用concept_name匹配micro_concept_id
                          r.get('micro_concept_name') == concept_name or
                          str(r.get('micro_concept_id', '')) == str(concept_id)]  # 也嘗試ObjectId匹配
        
        # 獲取Neo4j知識點關聯數據
        knowledge_relations = get_knowledge_relations_from_neo4j(concept_name)
        
        if not concept_records:
            return jsonify({
                'concept_name': concept_name,
                'domain_name': domain_name,
                'diagnosis': '暫無答題記錄，無法進行AI診斷。建議先完成相關練習題。',
                'suggestions': [
                    '完成該知識點的基礎練習題',
                    '閱讀相關教材內容',
                    '觀看教學影片'
                ],
                'difficulty_level': '未知',
                'mastery_level': 0
            })
        
        # 計算掌握度統計
        total_attempts = len(concept_records)
        correct_attempts = sum(1 for r in concept_records if r['is_correct'])
        mastery = correct_attempts / total_attempts if total_attempts > 0 else 0
        
        # 分析題目難易度分布
        difficulty_stats = {}
        for record in concept_records:
            # 嘗試從不同字段獲取難易度
            difficulty = (record.get('difficulty_level') or 
                        record.get('difficulty') or 
                        record.get('level') or 
                        '中等')  # 默認設為中等
            if difficulty not in difficulty_stats:
                difficulty_stats[difficulty] = {'total': 0, 'correct': 0}
            difficulty_stats[difficulty]['total'] += 1
            if record['is_correct']:
                difficulty_stats[difficulty]['correct'] += 1
        
        # 分析錯誤模式
        wrong_records = [r for r in concept_records if not r['is_correct']]
        recent_records = concept_records[:5]  # 最近5次答題
        recent_accuracy = sum(1 for r in recent_records if r['is_correct']) / len(recent_records) if recent_records else 0
        
        # 獲取學習路徑推薦
        learning_path_data = calculate_graph_based_mastery(user_email, concept_id)
        
        # 獲取難度分析數據
        difficulty_aware_data = calculate_difficulty_aware_mastery(concept_records, concept_id)
        
        # 獲取遺忘分析數據
        forgetting_aware_data = calculate_forgetting_aware_mastery(concept_records, concept_id)
        
        # 生成AI診斷
        diagnosis_result = generate_ai_diagnosis(
            concept_name=concept_name,
            domain_name=domain_name,
            mastery=mastery,
            total_attempts=total_attempts,
            correct_attempts=correct_attempts,
            recent_accuracy=recent_accuracy,
            wrong_records=wrong_records,
            knowledge_relations=knowledge_relations,
            difficulty_stats=difficulty_stats,
            learning_path=learning_path_data['learning_path']
        )
        
        # 添加新演算法的數據到診斷結果
        diagnosis_result['difficulty_breakdown'] = difficulty_aware_data['difficulty_breakdown']
        diagnosis_result['forgetting_analysis'] = {
            'base_mastery': forgetting_aware_data['base_mastery'],
            'current_mastery': forgetting_aware_data['current_mastery'],
            'days_since_practice': forgetting_aware_data['days_since_practice'],
            'review_urgency': forgetting_aware_data['review_urgency'],
            'forgetting_curve_data': forgetting_aware_data.get('forgetting_curve_data', [])
        }
        
        # 快取診斷結果到Redis（30分鐘）
        # 使用 SET ... NX EX 原子操作：只在鍵不存在時設置，並設置過期時間
        # 避免重複創建相同鍵名，確保所有快取都有過期時間
        cache_ttl = 30 * 60  # 30分鐘
        cache_value = json.dumps(diagnosis_result, ensure_ascii=False)
        
        # 使用原子操作 SET ... NX EX：只在鍵不存在時創建，並自動設置過期時間
        set_result = redis_client.set(cache_key, cache_value, ex=cache_ttl, nx=True)
        if set_result:
            logger.info(f"AI診斷已快取: {cache_key} (過期時間: {cache_ttl} 秒)")
        else:
            # 鍵已存在，可能是並發請求創建的，記錄但不報錯（這是正常情況）
            logger.debug(f"AI診斷快取鍵已存在（可能是並發請求），跳過創建: {cache_key}")
        
        return jsonify(diagnosis_result)
        
    except Exception as e:
        logger.error(f"AI診斷失敗: {e}")
        return jsonify({'error': 'AI診斷失敗'}), 500

@analytics_bp.route('/init-data', methods=['POST', 'OPTIONS'])
def init_data():
    if request.method == 'OPTIONS':
        return jsonify({'success': True})
    """初始化學習分析數據 - 獲取所有數據"""
    try:
        # 獲取請求參數
        data = request.get_json() or {}
        trend_days = data.get('trendDays', 7)
        
        # 從請求中獲取JWT token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': '缺少認證令牌'}), 401
        
        token = auth_header.split(' ')[1]
        user_email = get_user_info(token, 'email')
        
        # 獲取學生答題紀錄
        quiz_records = get_student_quiz_records(user_email)
        
        # 計算學習指標
        learning_metrics = calculate_learning_metrics(quiz_records)
        # 獲取知識結構
        knowledge_structure = get_knowledge_structure()
        
        # 從MongoDB獲取所有領域
        all_domains = list(mongo.db.domain.find({}, {'name': 1, '_id': 1}))
        
        # 基於答題記錄計算各領域掌握度
        domain_stats = {}
        
        # 統計各領域的答題情況
        for record in quiz_records:
            domain_name = record.get('domain_name', '未知領域')
            if domain_name not in domain_stats:
                domain_stats[domain_name] = {
                    'total': 0,
                    'correct': 0,
                    'wrong': 0
                }
            
            domain_stats[domain_name]['total'] += 1
            if record['is_correct']:
                domain_stats[domain_name]['correct'] += 1
            else:
                domain_stats[domain_name]['wrong'] += 1
        
        
        # 構建領域數據 - 包含所有領域，即使沒有答題記錄
        # 過濾掉「未知領域」
        domains = []
        for domain_doc in all_domains:
            domain_name = domain_doc.get('name', '')
            # 跳過「未知領域」
            if domain_name == '未知領域' or domain_name == '未知' or not domain_name or domain_name.strip() == '':
                continue
            domain_id = str(domain_doc.get('_id', ''))
            
            # 嘗試匹配領域名稱（處理括號和英文部分）
            matched_stats = None
            for stats_domain_name, stats in domain_stats.items():
                # 檢查是否包含相同的核心名稱
                if (stats_domain_name in domain_name or 
                    domain_name.split('（')[0] in stats_domain_name or
                    stats_domain_name in domain_name.split('（')[0]):
                    matched_stats = stats
                    break
            
            # 如果沒有匹配到，使用默認值
            if matched_stats is None:
                matched_stats = {'total': 0, 'correct': 0, 'wrong': 0}
            
            stats = matched_stats.copy()  # 創建副本避免修改原始數據
            # 確保stats包含所有必要字段
            if 'wrong' not in stats:
                stats['wrong'] = stats['total'] - stats['correct']
            
            if stats['total'] > 0:
                domain_mastery = stats['correct'] / stats['total']
            else:
                domain_mastery = 0.0  # 沒有答題記錄時設為0
            
            # 計算該領域的難度感知掌握度
            domain_records = [r for r in quiz_records if r.get('domain_name') == domain_name.split('（')[0]]
            difficulty_aware_data = calculate_difficulty_aware_mastery(domain_records, domain_id)
            
            
            # 從MongoDB獲取該領域下的小知識點（微概念）
            # 需要先通過block找到該領域下的微概念
            domain_id_obj = domain_doc.get('_id')
            
            # 先找到該領域下的所有block
            blocks = list(mongo.db.block.find({'domain_id': domain_id_obj}, {'_id': 1}))
            block_ids = [block['_id'] for block in blocks]
            
            # 再找到這些block下的微概念
            micro_concepts_query = {'block_id': {'$in': block_ids}} if block_ids else {}
            micro_concept_docs = list(mongo.db.micro_concept.find(micro_concepts_query, {'name': 1, '_id': 1, 'block_id': 1}))
            
            
            # 統計每個微概念的答題情況
            # 需要匹配簡化的領域名稱
            simplified_domain_name = domain_name.split('（')[0]  # 取括號前的部分
            domain_records = [r for r in quiz_records if r.get('domain_name') == simplified_domain_name]
            micro_concept_stats = {}
            for record in domain_records:
                concept_id = record.get('micro_concept_id', '')
                concept_name = record.get('micro_concept_name', '')
                # 使用概念ID作為主要匹配方式
                if concept_id and concept_id != 'None' and concept_id != '':
                    if concept_id not in micro_concept_stats:
                        micro_concept_stats[concept_id] = {'total': 0, 'correct': 0, 'wrong': 0}
                    micro_concept_stats[concept_id]['total'] += 1
                    if record['is_correct']:
                        micro_concept_stats[concept_id]['correct'] += 1
                    else:
                        micro_concept_stats[concept_id]['wrong'] += 1
                
                # 也嘗試用概念名稱匹配（作為備選）
                elif concept_name and concept_name != 'None' and concept_name != '':
                    if concept_name not in micro_concept_stats:
                        micro_concept_stats[concept_name] = {'total': 0, 'correct': 0, 'wrong': 0}
                    micro_concept_stats[concept_name]['total'] += 1
                    if record['is_correct']:
                        micro_concept_stats[concept_name]['correct'] += 1
                    else:
                        micro_concept_stats[concept_name]['wrong'] += 1
            
            # 構建小知識點數據
            concepts = []
            for concept_doc in micro_concept_docs:
                concept_id = str(concept_doc.get('_id', ''))
                concept_name = concept_doc.get('name', f'概念 {concept_id[:8]}')
                
                # 跳過沒有ID的概念
                if not concept_id or concept_id == 'None' or concept_id == '':
                    continue
                
                # 獲取該微概念的答題統計
                # 優先使用概念名稱匹配（因為答題記錄中的concept_id實際上是概念名稱）
                concept_stats = micro_concept_stats.get(concept_name, micro_concept_stats.get(concept_id, {'total': 0, 'correct': 0, 'wrong': 0}))
                
                
                if concept_stats['total'] > 0:
                    concept_mastery = concept_stats['correct'] / concept_stats['total']
                else:
                    concept_mastery = 0.0  # 沒有答題記錄時設為0
                
                concepts.append({
                    'id': concept_id,
                    'name': concept_name,
                    'mastery': round(concept_mastery, 2),
                    'questionCount': concept_stats['total'],
                    'wrongCount': concept_stats['total'] - concept_stats['correct']
                })
            
            domains.append({
                'id': domain_id,
                'name': domain_name,
                'mastery': round(domain_mastery, 2),  # 使用domain_mastery變量
                'questionCount': stats['total'],
                'wrongCount': stats['wrong'],
                'concepts': concepts,  # 包含小知識點
                'expanded': False,  # 用於前端展開狀態
                # 新增難度感知數據
                'difficulty_aware_mastery': difficulty_aware_data['overall_mastery'],
                'difficulty_breakdown': difficulty_aware_data['difficulty_breakdown'],
                'difficulty_analysis': difficulty_aware_data['difficulty_analysis'],
            })
        
        # 按掌握度排序
        domains.sort(key=lambda x: x['mastery'], reverse=True)
        
        # 顯示所有知識點（包含小知識點）
        all_knowledge_points = []
        for domain in domains:
            # 判斷狀態：數據不足、需要加強、掌握良好
            
            if domain['questionCount'] == 0:
                status = 'no_data'
                status_text = '數據不足'
            elif domain['mastery'] < 0.6:
                status = 'weak'
                status_text = '需要加強'
            else:
                status = 'good'
                status_text = '掌握良好'
            
            all_knowledge_points.append({
                    'id': domain['id'],
                    'name': domain['name'],
                    'mastery': domain['mastery'],
                'questionCount': domain['questionCount'],
                'wrongCount': domain['wrongCount'],
                'status': status,
                'status_text': status_text,
                'concepts': domain['concepts'],  # 包含小知識點
                'expanded': False  # 用於前端展開狀態
            })
        
        # 按掌握度排序，顯示所有知識點
        all_knowledge_points.sort(key=lambda x: x['mastery'])
        top_weak_points = all_knowledge_points  # 顯示所有知識點
        
        # 構建總覽數據
        # 計算額外的統計數據
        total_attempts = len(quiz_records)
        correct_attempts = sum(1 for r in quiz_records if r['is_correct'])
        accuracy = correct_attempts / total_attempts if total_attempts > 0 else 0
        
        # 計算連續學習天數
        consecutive_days = calculate_consecutive_days(quiz_records)
        
        # 計算本週已作答題數
        from datetime import timezone
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        recent_activity = len([r for r in quiz_records if datetime.fromisoformat(r['attempt_time'].replace('Z', '+00:00')) >= week_ago])
        
        # 計算已掌握和學習中的概念
        mastered_concepts = len([d for d in domains if d['mastery'] >= 0.8])
        learning_concepts = len([d for d in domains if 0.3 <= d['mastery'] < 0.8])
        
        # 計算學習時間統計
        total_study_time = calculate_total_study_time(quiz_records)
        avg_daily_time = calculate_avg_daily_time(quiz_records)
        longest_session = calculate_longest_session(quiz_records)
        study_intensity = calculate_study_intensity(quiz_records)
        
        # 計算歷史數據用於趨勢分析
        historical_metrics = calculate_historical_metrics(quiz_records, trend_days)
        
        overview_data = {
            'total_mastery': learning_metrics['overall_mastery'],
            'learning_velocity': learning_metrics['learning_velocity'],
            'retention_rate': learning_metrics['retention_rate'],
            'avg_time_per_concept': learning_metrics['avg_time_per_concept'],
            'focus_score': learning_metrics['focus_score'],
            'domains': domains,
            'top_weak_points': top_weak_points,
            'recent_activity': recent_activity,
            # 新增的統計數據
            'total_attempts': total_attempts,
            'accuracy': accuracy,
            'consecutive_days': consecutive_days,
            'mastered_concepts': mastered_concepts,
            'learning_concepts': learning_concepts,
            'total_study_time': total_study_time,
            'avg_daily_time': avg_daily_time,
            'longest_session': longest_session,
            'study_intensity': study_intensity,
            # 歷史數據用於趨勢計算
            'previous_learning_velocity': historical_metrics['learning_velocity'],
            'previous_retention_rate': historical_metrics['retention_rate'],
            'previous_avg_time_per_concept': historical_metrics['avg_time_per_concept'],
            'previous_focus_score': historical_metrics['focus_score']
        }
        
        # 生成趨勢數據（使用傳入的天數）
        trends = generate_trend_data(quiz_records, trend_days)
        
        # 生成按領域篩選的趨勢數據
        domain_trends = {}
        
        for domain in domains:
            domain_name = domain['name']
            simplified_name = domain_name.split('（')[0]  # 取括號前的部分
            # 篩選該領域的答題記錄
            domain_records = [r for r in quiz_records if r.get('domain_name') == simplified_name]
            
            if domain_records:
                domain_trends[domain_name] = generate_trend_data(domain_records, trend_days)
            else:
                pass
        
        for name, trends in domain_trends.items():
            total_questions = sum(day['questions'] for day in trends)
            pass
        
        # 生成進步知識點數據
        improvement_items = generate_improvement_items(domains, quiz_records)
        # 生成需要關注的知識點數據
        attention_items = generate_attention_items(domains, quiz_records)
        
        
        # 生成進度追蹤數據
        progress_tracking = generate_progress_tracking(quiz_records)
        
        # 生成雷達圖數據
        radar_data = generate_radar_data(domains, quiz_records)
        
        # 生成AI教練分析
        ai_coach_analysis = generate_ai_coach_analysis(overview_data, domains, quiz_records, user_email)
        
        # 生成學習趨勢數據（結合遺忘曲線）
        learning_trends = generate_learning_trends_with_forgetting(domains, quiz_records, trend_days)
        
        # 構建完整數據
        complete_data = {
            'overview': overview_data,
            'trends': learning_trends,  # 使用新的學習趨勢
            'domain_trends': domain_trends,  # 新增：按領域篩選的趨勢數據
            'improvement_items': improvement_items,
            'attention_items': attention_items,
            'progress_tracking': progress_tracking,
            'radar_data': radar_data,
            'ai_coach_analysis': ai_coach_analysis  # 新增AI教練分析
        }

        return jsonify({
            'success': True,
            'data': complete_data
        })
        
    except Exception as e:
        logger.error(f'初始化學習分析數據失敗: {str(e)}')
        return jsonify({
            'success': False,
            'error': '初始化學習分析數據失敗'
        }), 500


@analytics_bp.route('/ai-practice-parallel', methods=['POST', 'OPTIONS'])
def ai_practice_parallel():
    """AI並行出題練習 - 使用多個API key並行生成題目"""
    if request.method == 'OPTIONS':
        return jsonify({'success': True})
    
    try:
        data = request.get_json()
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'success': False,
                'error': '缺少認證信息'
            }), 401
        token = auth_header.split(' ')[1]
        user_email = get_user_info(token, 'email')
        if not user_email:
            return jsonify({
                'success': False,
                'error': '無法獲取用戶信息，請重新登入'
            }), 401
        
        concept_name = data.get('concept_name', '未知概念')
        domain_name = data.get('domain_name', '未知領域')
        difficulty = data.get('difficulty', 'medium')
        question_count = data.get('question_count', 20)
        
        
        # 使用並行生成
        quiz_result = generate_quiz_parallel(concept_name, domain_name, difficulty, question_count, user_email)
        
        if quiz_result.get('success'):
            return jsonify({
                'success': True,
                'quiz_id': quiz_result.get('quiz_id'),
                'template_id': quiz_result.get('template_id', quiz_result.get('quiz_id')),  # 添加template_id
                'quiz_info': quiz_result.get('quiz_info', {}),
                'questions': quiz_result.get('questions', []),
                'concept_name': concept_name,
                'domain_name': domain_name,
                'difficulty': difficulty,
                'question_count': len(quiz_result.get('questions', [])),
                'generation_time': quiz_result.get('generation_time', 0),
                'api_keys_used': quiz_result.get('api_keys_used', 0)
            })
        else:
            return jsonify({
                'success': False,
                'error': quiz_result.get('error', '生成題目失敗')
            }), 500
        
    except Exception as e:
        logger.error(f"AI並行出題練習失敗: {e}")
        return jsonify({
            'success': False,
            'error': f'AI並行出題練習失敗: {str(e)}'
        }), 500

def generate_quiz_parallel(concept_name: str, domain_name: str, difficulty: str, question_count: int, user_email: str = 'ai_system@mis_teach.com') -> Dict[str, Any]:
    """使用多個API key並行生成題目"""
    start_time = time.time()
    
    try:
        # 讀取API keys - 需要先載入環境變數
        from dotenv import load_dotenv
        load_dotenv('api.env')
        
        wu_keys = os.getenv('WU_API_KEYS', '').split(',')
        pan_keys = os.getenv('PAN_API_KEYS', '').split(',')
        
        # 過濾空字符串
        wu_keys = [key.strip() for key in wu_keys if key.strip()]
        pan_keys = [key.strip() for key in pan_keys if key.strip()]
        
        all_keys = wu_keys + pan_keys
        # 去重複，確保每個API key只使用一次
        available_keys = list(dict.fromkeys([key for key in all_keys if key]))
        
        if not available_keys:
            return {
                'success': False,
                'error': '沒有可用的API密鑰'
            }
        
        
        # 根據傳入的question_count參數分配任務
        # 優先使用1題1key模式，如果API key不足則平均分配
        if len(available_keys) >= question_count:
            # API key足夠：每個key生成1題，只使用需要的API key數量
            questions_per_key = 1
            remaining_questions = 0
            used_keys = available_keys[:question_count]
        else:
            # API key不足：平均分配題目
            questions_per_key = question_count // len(available_keys)
            remaining_questions = question_count % len(available_keys)
            used_keys = available_keys
        
        # 準備並行任務
        tasks = []
        for i, api_key in enumerate(used_keys):
            # 分配題目數量
            if len(available_keys) >= question_count:
                # API key足夠：每個key生成1題
                key_question_count = 1
            else:
                # API key不足：平均分配
                key_question_count = questions_per_key
                if i < remaining_questions:
                    key_question_count += 1
            
            if key_question_count <= 0:
                continue
                
            # 決定使用哪個API組
            api_group = 'wu_api' if api_key in wu_keys else 'pan_api'
            
            task = {
                'api_key': api_key,
                'api_group': api_group,
                'question_count': key_question_count,
                'concept_name': concept_name,
                'domain_name': domain_name,
                'difficulty': difficulty
            }
            tasks.append(task)
        
        # 最大化並行度：使用所有可用的API key
        max_workers = min(len(tasks), 20)  # 最多20個並行任務
        
        
        # 並行執行任務
        all_questions = []
        successful_keys = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任務
            future_to_task = {
                executor.submit(generate_questions_with_key, task): task 
                for task in tasks
            }
            
            # 收集結果
            for future in concurrent.futures.as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    result = future.result()
                    if result.get('success'):
                        questions = result.get('questions', [])
                        all_questions.extend(questions)
                        successful_keys += 1
                    else:
                        logger.error(f"{task['api_group']} 生成失敗: {result.get('error', '未知錯誤')}")
                except Exception as e:
                    logger.error(f"{task['api_group']} 執行異常: {str(e)}")
        
        if not all_questions:
            return {
                'success': False,
                'error': '所有API密鑰都生成失敗'
            }
        
        # 如果題目數量不足，嘗試用剩餘的API key補充
        if len(all_questions) < question_count:
            logger.warning(f"題目數量不足，當前: {len(all_questions)}, 需要: {question_count}")
            # 這裡可以添加補充邏輯
        
        # 限制題目數量
        all_questions = all_questions[:question_count]
        
        generation_time = time.time() - start_time
        
        # 生成測驗信息
        quiz_info = {
            'title': f'{concept_name} - {difficulty}難度練習',
            'description': f'AI生成的{concept_name}練習題，共{len(all_questions)}題',
            'total_questions': len(all_questions),
            'difficulty': difficulty,
            'concept': concept_name,
            'domain': domain_name,
            'generation_time': round(generation_time, 2),
            'api_keys_used': successful_keys
        }
        
        # 保存到MongoDB並創建SQL template
        quiz_id, template_id = save_quiz_to_database(quiz_info, all_questions, concept_name, domain_name, user_email)
        
        return {
            'success': True,
            'quiz_id': quiz_id,
            'template_id': template_id,
            'quiz_info': quiz_info,
            'questions': all_questions,
            'generation_time': round(generation_time, 2),
            'api_keys_used': successful_keys
        }
        
    except Exception as e:
        logger.error(f"並行生成題目失敗: {e}")
        return {
            'success': False,
            'error': f'並行生成失敗: {str(e)}'
        }

def generate_questions_with_key(task: Dict[str, Any]) -> Dict[str, Any]:
    """使用單個API key生成題目"""
    try:
        api_key = task['api_key']
        api_group = task['api_group']
        question_count = task['question_count']
        concept_name = task['concept_name']
        domain_name = task['domain_name']
        difficulty = task['difficulty']
        
        # 構建需求參數，結合概念名稱和領域
        full_topic = f"{domain_name} - {concept_name}" if domain_name and domain_name != concept_name else concept_name
        requirements = {
            'topic': full_topic,
            'concept_name': concept_name,
            'domain_name': domain_name,
            'question_types': ['single-choice', 'multiple-choice', 'fill-in-the-blank', 'true-false'],
            'difficulty': difficulty,
            'question_count': question_count,
            'exam_type': 'knowledge'
        }
        
        # 調用quiz_generator
        result = generate_quiz_by_ai(requirements)
        
        if result.get('success'):
            return {
                'success': True,
                'questions': result.get('questions', []),
                'api_group': api_group
            }
        else:
            return {
                'success': False,
                'error': result.get('error', '生成失敗'),
                'api_group': api_group
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'api_group': task.get('api_group', 'unknown')
        }

def save_quiz_to_database(quiz_info: Dict[str, Any], questions: List[Dict], concept_name: str, domain_name: str, user_email: str = 'ai_system@mis_teach.com') -> tuple[str, str]:
    """保存測驗到MongoDB資料庫的exam集合"""
    try:
        # 生成唯一的exam_id，使用ObjectId格式
        from bson import ObjectId
        exam_id = str(ObjectId())
        
        # 轉換題目格式以符合exam集合的結構
        exam_questions = []
        for i, question in enumerate(questions):
            # 根據題型確定answer_type，AI生成的題目都設為single類型
            question_type = question.get('question_type', 'single-choice')
            if question_type == 'single-choice':
                answer_type = 'single-choice'
            elif question_type == 'multiple-choice':
                answer_type = 'multiple-choice'  # 改為single類型
            elif question_type == 'fill-in-the-blank':
                answer_type = 'fill-in-the-blank'
            elif question_type == 'true-false':
                answer_type = 'true-false'
            else:
                answer_type = 'single-choice'
            
            # 處理選項格式
            options = question.get('options', [])
            if options and isinstance(options, list):
                # 如果選項包含標籤（如"選項A: 內容"），提取內容
                processed_options = []
                for option in options:
                    if ': ' in option:
                        processed_options.append(option.split(': ', 1)[1])
                    else:
                        processed_options.append(option)
            else:
                processed_options = []
            
            exam_question = {
                # 讓MongoDB自動生成_id，避免重複ID問題
                '_id': ObjectId(),
                'type': answer_type,
                'school': '',
                'department': '',
                'year': '',
                'question_number': str(i + 1),
                'question_text': question.get('question_text', ''),
                'options': processed_options,
                'answer': question.get('correct_answer', ''),
                'answer_type': answer_type,
                'image_file': [],
                'detail-answer': question.get('explanation', ''),
                'key-points': concept_name,  # 使用單一字符串而不是數組
                'micro_concepts': [concept_name, f"{concept_name}基礎", f"{concept_name}應用"],
                'difficulty_level': '中等' if quiz_info['difficulty'] == 'medium' else ('簡單' if quiz_info['difficulty'] == 'easy' else '困難'),
                'error_reason': '',
                'created_at': datetime.now()
            }
            exam_questions.append(exam_question)
        
        # 直接保存題目作為獨立文檔，不需要測驗文檔
        if exam_questions:
            try:
                question_results = mongo.db.exam.insert_many(exam_questions)
                
                # 創建SQL template（使用所有題目的ID）
                question_ids = [str(q_id) for q_id in question_results.inserted_ids]
                
                template_id = create_sql_template(question_ids, {
                    'title': quiz_info['title'],
                    'total_questions': len(exam_questions),
                    'difficulty': quiz_info['difficulty'],
                    'concept': concept_name,
                    'domain': domain_name
                }, user_email)
                
                return str(question_results.inserted_ids[0]), template_id  # 返回第一個題目的ID和template_id
                
            except Exception as e:
                successful_ids = []
                for i, question in enumerate(exam_questions):
                    try:
                        result = mongo.db.exam.insert_one(question)
                        successful_ids.append(str(result.inserted_id))
                    except Exception as single_error:
                        continue
                
                if successful_ids:
                    template_id = create_sql_template(successful_ids, {
                        'title': quiz_info['title'],
                        'total_questions': len(successful_ids),
                        'difficulty': quiz_info['difficulty'],
                        'concept': concept_name,
                        'domain': domain_name
                    }, user_email)
                    return exam_id, template_id
                else:
                    raise e
        else:
            return f"temp_{int(time.time())}", f"temp_template_{int(time.time())}"
            
    except Exception as e:
        return f"temp_{int(time.time())}", f"temp_template_{int(time.time())}"

def create_sql_template(question_ids: List[str], quiz_info: Dict[str, Any], user_email: str = '') -> str:
    """為AI生成的測驗創建SQL template，參考學校考古題的創建方式"""
    try:
        from accessories import sqldb
        from sqlalchemy import text
        import json
        
        # 創建SQL template記錄
        template_query = text("""
            INSERT INTO quiz_templates (
                user_email,
                template_type,
                question_ids,
                school,
                department,
                year
            ) VALUES (
                :user_email,
                :template_type,
                :question_ids,
                :school,
                :department,
                :year
            )
        """)
        
        # 準備數據
        template_data = {
            'user_email': user_email,
            'template_type': 'knowledge',
            'question_ids': json.dumps(question_ids),  # 使用所有題目的ID
            'school': '',
            'department': '',
            'year': ''
        }
        
        # 執行SQL並獲取lastrowid作為template_id
        with sqldb.engine.connect() as conn:
            result = conn.execute(template_query, template_data)
            conn.commit()
            template_id = result.lastrowid
            
        logger.info(f"SQL template已創建: {template_id}")
        return str(template_id)
        
    except Exception as e:
        logger.error(f"創建SQL template失敗: {e}")
        return f"ai_template_{int(time.time())}"

def generate_trend_data(quiz_records: List[Dict], days: int = 7) -> List[Dict]:
    """生成趨勢數據，包含遺忘曲線分析"""
    trends = []
    for i in range(days):
        from datetime import timezone
        date = (datetime.now(timezone.utc) - timedelta(days=days-1-i)).strftime('%Y-%m-%d')
        # 計算該天的掌握度
        day_records = [r for r in quiz_records if r['attempt_time'].startswith(date)]
        if day_records:
            correct_count = sum(1 for r in day_records if r['is_correct'])
            total_count = len(day_records)
            mastery = correct_count / total_count
        else:
            mastery = 0
        
        # 計算該天的遺忘曲線數據
        forgetting_data = []
        if day_records:
            # 按概念分組計算遺忘率
            concept_groups = {}
            for record in day_records:
                concept_id = record.get('micro_concept_id')
                if concept_id:
                    if concept_id not in concept_groups:
                        concept_groups[concept_id] = []
                    concept_groups[concept_id].append(record)
            
            # 計算每個概念的遺忘率
            for concept_id, concept_records in concept_groups.items():
                forgetting_info = calculate_forgetting_aware_mastery(concept_records, concept_id)
                # 確保遺忘率是合理的數值
                forgetting_rate = max(0, 1 - forgetting_info['current_mastery'])
                forgetting_data.append({
                    'concept_id': concept_id,
                    'base_mastery': forgetting_info['base_mastery'],
                    'current_mastery': forgetting_info['current_mastery'],
                    'forgetting_rate': forgetting_rate,
                    'days_since_practice': forgetting_info['days_since_practice']
                })
            if forgetting_data:
                avg_forgetting = sum(item['forgetting_rate'] for item in forgetting_data) / len(forgetting_data)
        
        trends.append({
            'date': date,
            'mastery': mastery,
            'questions': len(day_records),
            'accuracy': mastery,
            'forgetting_data': forgetting_data
        })
    
    return trends

# 已移除 /trends API - 功能已整合到 /init-data

# 已移除 /peer-comparison API - 前端未使用

@analytics_bp.route('/difficulty-analysis', methods=['POST', 'OPTIONS'])
def get_difficulty_analysis():
    if request.method == 'OPTIONS':
        return jsonify({'success': True})
    """獲取難度分析數據 - Difficulty-aware KT"""
    try:
        # 獲取JWT token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': '缺少認證信息'}), 401
        
        token = auth_header.split(' ')[1]
        user_email = get_user_info(token, 'email')
        
        if not user_email:
            return jsonify({'success': False, 'error': '無法獲取用戶信息'}), 401
        
        # 獲取學生答題記錄
        quiz_records = get_student_quiz_records(user_email)
        
        # 計算整體難度分析
        overall_difficulty_stats = {}
        for record in quiz_records:
            difficulty = record.get('difficulty', '中等')
            if difficulty not in overall_difficulty_stats:
                overall_difficulty_stats[difficulty] = {'total': 0, 'correct': 0}
            overall_difficulty_stats[difficulty]['total'] += 1
            if record['is_correct']:
                overall_difficulty_stats[difficulty]['correct'] += 1
        
        # 計算整體難度分佈
        overall_difficulty_breakdown = {}
        for difficulty in ['簡單', '中等', '困難']:
            if difficulty in overall_difficulty_stats:
                stats = overall_difficulty_stats[difficulty]
                mastery = stats['correct'] / stats['total'] if stats['total'] > 0 else 0
                overall_difficulty_breakdown[difficulty] = {
                    'mastery': round(mastery, 2),
                    'total_questions': stats['total'],
                    'correct_questions': stats['correct']
                }
            else:
                overall_difficulty_breakdown[difficulty] = {
                    'mastery': 0,
                    'total_questions': 0,
                    'correct_questions': 0
                }
        
        # 計算各領域的難度分析
        domain_difficulty_analysis = []
        domains = list(mongo.db.domain.find({}, {'name': 1, '_id': 1}))
        
        for domain_doc in domains:
            domain_name = domain_doc.get('name', '未知領域')
            domain_id = str(domain_doc.get('_id', ''))
            
            # 獲取該領域的答題記錄
            domain_records = [r for r in quiz_records if r.get('domain_name') == domain_name.split('（')[0]]
            
            if domain_records:
                difficulty_data = calculate_difficulty_aware_mastery(domain_records, domain_id)
            else:
                # 沒有答題記錄時，返回默認數據
                difficulty_data = {
                    'overall_mastery': 0,
                    'difficulty_breakdown': {'簡單': 0, '中等': 0, '困難': 0},
                    'difficulty_analysis': {
                        'easy_mastery': 0,
                        'medium_mastery': 0,
                        'hard_mastery': 0,
                        'bottleneck_level': 'none',
                        'recommended_difficulty': '簡單'
                    }
                }
            
            domain_difficulty_analysis.append({
                'domain_id': domain_id,
                'domain_name': domain_name,
                'overall_mastery': difficulty_data['overall_mastery'],
                'difficulty_breakdown': difficulty_data['difficulty_breakdown'],
                'difficulty_analysis': difficulty_data['difficulty_analysis']
            })
        
        # 生成個人化難度推薦
        personalized_recommendations = []
        for domain_data in domain_difficulty_analysis:
            analysis = domain_data['difficulty_analysis']
            if analysis['bottleneck_level'] != 'none':
                personalized_recommendations.append({
                    'domain': domain_data['domain_name'],
                    'bottleneck_level': analysis['bottleneck_level'],
                    'recommended_difficulty': analysis['recommended_difficulty'],
                    'reason': f"在{analysis['bottleneck_level']}難度題目上表現不佳，建議先練習{analysis['recommended_difficulty']}難度"
                })
        
        return jsonify({
            'success': True,
            'data': {
                'overall_difficulty_breakdown': overall_difficulty_breakdown,
                'domain_difficulty_analysis': domain_difficulty_analysis,
                'personalized_recommendations': personalized_recommendations
            }
        })
        
    except Exception as e:
        logger.error(f'獲取難度分析數據失敗: {str(e)}')
        return jsonify({
            'success': False,
            'error': f'獲取難度分析數據失敗: {str(e)}'
        }), 500

@analytics_bp.route('/forgetting-analysis', methods=['POST', 'OPTIONS'])
def get_forgetting_analysis():
    if request.method == 'OPTIONS':
        return jsonify({'success': True})
    """獲取遺忘分析數據 - Forgetting-aware KT"""
    try:
        # 獲取JWT token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': '缺少認證信息'}), 401
        
        token = auth_header.split(' ')[1]
        user_email = get_user_info(token, 'email')
        
        if not user_email:
            return jsonify({'success': False, 'error': '無法獲取用戶信息'}), 401
        
        # 獲取學生答題記錄
        quiz_records = get_student_quiz_records(user_email)
        
        # 按概念分組計算遺忘分析
        concept_forgetting_analysis = {}
        for record in quiz_records:
            concept_id = record['micro_concept_id']
            if concept_id not in concept_forgetting_analysis:
                concept_forgetting_analysis[concept_id] = []
            concept_forgetting_analysis[concept_id].append(record)
        
        # 計算每個概念的遺忘分析
        forgetting_results = []
        review_recommendations = []
        
        for concept_id, concept_records in concept_forgetting_analysis.items():
            forgetting_data = calculate_forgetting_aware_mastery(concept_records, concept_id)
            
            # 獲取概念名稱
            concept_name = "未知概念"
            for concept_doc in mongo.db.micro_concept.find({'_id': ObjectId(concept_id) if concept_id else None}):
                concept_name = concept_doc.get('name', '未知概念')
                break
            
            forgetting_results.append({
                'concept_id': concept_id,
                'concept_name': concept_name,
                'base_mastery': forgetting_data['base_mastery'],
                'current_mastery': forgetting_data['current_mastery'],
                'forgetting_factor': forgetting_data['forgetting_factor'],
                'days_since_practice': forgetting_data['days_since_practice'],
                'review_urgency': forgetting_data['review_urgency'],
                'forgetting_curve_data': forgetting_data['forgetting_curve_data']
            })
            
            # 生成複習建議
            if forgetting_data['review_urgency'] != 'low':
                review_recommendations.append({
                    'concept_id': concept_id,
                    'concept_name': concept_name,
                    'urgency': forgetting_data['review_urgency'],
                    'days_since_practice': forgetting_data['days_since_practice'],
                    'current_mastery': forgetting_data['current_mastery'],
                    'suggested_review_time': _get_suggested_review_time(forgetting_data['review_urgency']),
                    'review_method': _get_review_method(forgetting_data['current_mastery'])
                })
        
        # 按緊急程度排序複習建議
        review_recommendations.sort(key=lambda x: {'high': 3, 'medium': 2, 'low': 1}[x['urgency']], reverse=True)
        
        return jsonify({
            'success': True,
            'data': {
                'concept_forgetting_analysis': forgetting_results,
                'review_recommendations': review_recommendations,
                'summary': {
                    'total_concepts': len(forgetting_results),
                    'high_urgency_count': len([r for r in review_recommendations if r['urgency'] == 'high']),
                    'medium_urgency_count': len([r for r in review_recommendations if r['urgency'] == 'medium']),
                    'low_urgency_count': len([r for r in review_recommendations if r['urgency'] == 'low'])
                }
            }
        })
        
    except Exception as e:
        logger.error(f'獲取遺忘分析數據失敗: {str(e)}')
        return jsonify({
            'success': False,
            'error': f'獲取遺忘分析數據失敗: {str(e)}'
        }), 500

# ==================== LINE Bot 專用函數 ====================

def get_learning_analysis_for_linebot(line_id: str) -> str:
    """LINE Bot 專用的學習分析函數"""
    try:
        # 通過 line_id 找到用戶
        user = mongo.db.user.find_one({"lineId": line_id})
        if not user:
            return "❌ 請先綁定您的帳號才能使用學習分析功能！"
        
        user_email = user.get('email')
        user_name = user.get('name', '同學')
        
        # 獲取學習分析數據
        quiz_records = get_student_quiz_records(user_email)
        learning_metrics = calculate_learning_metrics(quiz_records)
        
        # 計算整體掌握度
        total_questions = learning_metrics.get('total_questions', 0)
        correct_answers = learning_metrics.get('correct_questions', 0)
        overall_accuracy = (correct_answers / total_questions * 100) if total_questions > 0 else 0
        # 獲取領域數據
        all_domains = list(mongo.db.domain.find({}, {'name': 1, '_id': 1}))
        domain_stats = {}
        
        for record in quiz_records:
            domain_name = record.get('domain_name', '未知領域')
            if domain_name not in domain_stats:
                domain_stats[domain_name] = {'total': 0, 'correct': 0, 'wrong': 0}
            
            domain_stats[domain_name]['total'] += 1
            if record['is_correct']:
                domain_stats[domain_name]['correct'] += 1
            else:
                domain_stats[domain_name]['wrong'] += 1
        
        # 構建領域掌握度
        domains = []
        for domain_doc in all_domains:
            domain_name = domain_doc.get('name', '未知領域')
            stats = domain_stats.get(domain_name, {'total': 0, 'correct': 0, 'wrong': 0})
            mastery = (stats['correct'] / stats['total'] * 100) if stats['total'] > 0 else 0
            
            domains.append({
                'name': domain_name,
                'mastery': mastery,
                'total': stats['total'],
                'correct': stats['correct']
            })
        
        # 找出強項和弱項
        strong_domains = [d for d in domains if d['mastery'] >= 70]
        weak_domains = [d for d in domains if d['mastery'] < 50 and d['total'] > 0]
        
        # 格式化報告
        report = f"""📊 學習分析報告 - {user_name}

🎯 整體表現：
• 總答題數：{total_questions} 題
• 正確率：{overall_accuracy:.1f}%

💪 強項領域："""
        
        if strong_domains:
            for domain in strong_domains:
                report += f"\n• {domain['name']} ({domain['mastery']:.1f}%)"
        else:
            report += "\n• 暫無強項領域"
        
        report += "\n\n⚠️ 需要加強："
        if weak_domains:
            for domain in weak_domains:
                report += f"\n• {domain['name']} ({domain['mastery']:.1f}%)"
        else:
            report += "\n• 暫無弱項領域"
        
        report += f"""

💡 學習建議：
1. 專注於弱項領域的練習
2. 保持每日學習習慣
3. 定期複習已掌握的知識點

📱 更多詳細分析請至網站查看！"""
        
        return report
        
    except Exception as e:
        print(f"❌ LINE Bot 學習分析失敗: {e}")
        return "❌ 學習分析功能暫時無法使用，請稍後再試。"

def generate_ai_coach_analysis(overview_data: Dict, domains: List[Dict], quiz_records: List[Dict], user_email: str = None) -> Dict[str, Any]:
    """生成AI教練分析（使用Redis快取）"""
    try:
        # 生成快取鍵
        # 使用標準化的快取鍵格式：learning_analytics:ai_coach_analysis:{user_email}:{total_attempts}:{total_mastery}
        # 與前端存儲命名保持一致
        total_attempts = overview_data.get('total_attempts', 0)
        total_mastery = overview_data.get('total_mastery', 0)
        cache_key = f"learning_analytics:ai_coach_analysis:{user_email or 'anonymous'}:{total_attempts}:{total_mastery:.2f}"
        
        # 檢查Redis快取
        cached_data = redis_client.get(cache_key)
        if cached_data:
            # 檢查鍵是否還有過期時間（避免使用已過期的快取）
            ttl = redis_client.ttl(cache_key)
            if ttl > 0:
                logger.info(f"✅ 使用AI教練分析快取: {cache_key} (剩餘 {ttl} 秒) - 跳過所有查詢")
                return json.loads(cached_data)
            else:
                # 如果鍵存在但已過期，刪除它
                redis_client.delete(cache_key)
                logger.info(f"⏰ AI教練分析快取已過期，刪除: {cache_key}")
        else:
            logger.info(f"❌ AI教練分析快取不存在: {cache_key} - 將執行查詢")
        
        # 只有在快取不存在時才執行以下查詢
        logger.info(f"🔄 開始執行AI教練分析查詢流程...")
        
        # 初始化Gemini模型
        model = init_gemini('gemini-2.5-flash')
        
        # 準備分析數據
        total_attempts = overview_data.get('total_attempts', 0)
        total_mastery = overview_data.get('total_mastery', 0)
        learning_velocity = overview_data.get('learning_velocity', 0)
        retention_rate = overview_data.get('retention_rate', 0)
        
        # 找出需要關注的領域
        weak_domains = [d for d in domains if d.get('mastery', 0) < 0.3 and d.get('questionCount', 0) > 0]
        strong_domains = [d for d in domains if d.get('mastery', 0) > 0.7 and d.get('questionCount', 0) > 0]
        
        # 分析遺忘情況
        forgetting_analysis = []
        for domain in domains:
            if domain.get('forgetting_analysis'):
                fa = domain['forgetting_analysis']
                if fa.get('days_since_practice', 0) > 3:
                    forgetting_analysis.append({
                        'name': domain['name'],
                        'days': fa['days_since_practice'],
                        'mastery': fa['current_mastery']
                    })
        
        # 構建Gemini提示詞
        prompt = f"""
你是學習分析AI教練。請基於以下學習數據生成簡潔的學習建議（不超過50字）：

學習數據：
- 總答題數：{total_attempts}
- 整體掌握度：{total_mastery:.1%}
- 學習速度：{learning_velocity:.1f} 概念/小時
- 記憶保持率：{retention_rate:.1%}

需要關注的領域：
{', '.join([d['name'] for d in weak_domains[:3]]) if weak_domains else '無'}

表現良好的領域：
{', '.join([d['name'] for d in strong_domains[:3]]) if strong_domains else '無'}

遺忘提醒：
{', '.join([f"{fa['name']}已{fa['days']}天未複習" for fa in forgetting_analysis[:3]]) if forgetting_analysis else '無'}

請生成：
1. 簡潔的學習狀況總結
2. 具體的學習建議
3. 需要重點關注的領域
4. 請使用繁體中文回答

格式：直接輸出文字，不要使用markdown格式。
"""

        # 調用Gemini API
        response = model.generate_content(prompt)
        ai_analysis = response.text.strip()
        
        result = {
            'analysis': ai_analysis,
            'last_updated': datetime.now().strftime('%m/%d %H:%M'),
            'weak_domains': [d['name'] for d in weak_domains[:3]],
            'strong_domains': [d['name'] for d in strong_domains[:3]],
            'forgetting_reminders': forgetting_analysis[:3]
        }
        
        # 快取結果到Redis（2小時）
        # 使用 SET ... NX EX 原子操作：只在鍵不存在時設置，並設置過期時間
        # 避免重複創建相同鍵名，確保所有快取都有過期時間
        cache_ttl = 2 * 60 * 60  # 2小時
        cache_value = json.dumps(result, ensure_ascii=False)
        
        # 使用原子操作 SET ... NX EX：只在鍵不存在時創建，並自動設置過期時間
        set_result = redis_client.set(cache_key, cache_value, ex=cache_ttl, nx=True)
        if set_result:
            logger.info(f"AI教練分析已快取: {cache_key} (過期時間: {cache_ttl} 秒)")
        else:
            # 鍵已存在，可能是並發請求創建的，記錄但不報錯（這是正常情況）
            logger.debug(f"AI教練分析快取鍵已存在（可能是並發請求），跳過創建: {cache_key}")
        
        return result
        
    except Exception as e:
        logger.error(f"生成AI教練分析失敗: {e}")
        return {
            'analysis': '正在分析您的學習數據...',
            'last_updated': datetime.now().strftime('%m/%d %H:%M'),
            'weak_domains': [],
            'strong_domains': [],
            'forgetting_reminders': []
        }

def generate_learning_trends_with_forgetting(domains: List[Dict], quiz_records: List[Dict], trend_days: int) -> List[Dict]:
    """生成結合遺忘曲線的學習趨勢數據"""
    trends = []
    
    # 按日期分組答題記錄
    from collections import defaultdict
    daily_records = defaultdict(list)
    
    for record in quiz_records:
        try:
            date_str = record['attempt_time'][:10]  # 提取日期部分
            daily_records[date_str].append(record)
        except:
            continue
    
    # 生成趨勢數據
    for i in range(trend_days):
        date = (datetime.now() - timedelta(days=trend_days-1-i)).strftime('%Y-%m-%d')
        day_records = daily_records.get(date, [])
        
        if day_records:
            # 計算當天的學習指標
            total_questions = len(day_records)
            correct_questions = sum(1 for r in day_records if r['is_correct'])
            accuracy = correct_questions / total_questions if total_questions > 0 else 0
            
            # 計算遺忘曲線數據
            forgetting_data = []
            for domain in domains:
                if domain.get('forgetting_analysis'):
                    fa = domain['forgetting_analysis']
                    forgetting_data.append({
                        'domain': domain['name'],
                        'current_mastery': fa.get('current_mastery', 0),
                        'days_since_practice': fa.get('days_since_practice', 0)
                    })
            
            trends.append({
                'date': date,
                'questions': total_questions,
                'accuracy': accuracy,
                'mastery': accuracy,  # 使用準確率作為掌握度
                'forgetting_data': forgetting_data
            })
        else:
            trends.append({
                'date': date,
                'questions': 0,
                'accuracy': 0,
                'mastery': 0,
                'forgetting_data': []
            })
    
    return trends

def _get_suggested_review_time(urgency: str) -> str:
    """根據緊急程度獲取建議複習時間"""
    if urgency == 'high':
        return '立即複習'
    elif urgency == 'medium':
        return '3天內複習'
    else:
        return '1週內複習'

def calculate_enhanced_learning_velocity(quiz_records: List[Dict]) -> float:
    """計算學習速度 - 基於Piech et al., 2015 Deep Knowledge Tracing文獻"""
    if not quiz_records:
        return 0.0
    
    # 只計算答對的題目，因為答錯不算學習
    correct_records = [r for r in quiz_records if r.get('is_correct', False)]
    if not correct_records:
        return 0.0
    
    # 按照文獻演算法：計算學習的概念數量（去重）
    concept_hours = set()
    for record in correct_records:
        concept_id = record.get('micro_concept_id')
        if concept_id:
            # 精確到小時，避免同一天多次答對同一概念重複計算
            hour_key = record['attempt_time'][:13]  # YYYY-MM-DDTHH
            concept_hours.add((hour_key, concept_id))
    
    # 計算總學習小時數（所有答題記錄的不同小時數）
    total_hours = len(set(r['attempt_time'][:13] for r in quiz_records))
    
    if total_hours == 0:
        return 0.0
    
    # 學習速度 = 掌握的概念數量 / 總學習小時數
    velocity = len(concept_hours) / max(total_hours, 1)
    

    
    return round(velocity, 1)

def calculate_enhanced_retention_rate(quiz_records: List[Dict]) -> float:
    """計算記憶保持率 - 基於混合演算法的時間衰減"""
    if not quiz_records:
        return 0.0
    
    # 使用混合演算法計算整體掌握度
    overall_mastery = calculate_mixed_mastery(quiz_records)
    
    # 記憶保持率 = 混合掌握度（已包含時間衰減）
    return overall_mastery

def calculate_mixed_mastery(quiz_records: List[Dict], concept_id: str = None) -> float:
    """計算混合掌握度 - 基於PFA + Forgetting-aware BKT + Difficulty-aware KT，添加難度上限限制"""
    if not quiz_records:
        return 0.0
    
    import math
    from datetime import datetime
    
    # 如果指定概念ID，只計算該概念的記錄
    if concept_id:
        concept_records = [r for r in quiz_records if r.get('micro_concept_id') == concept_id]
    else:
        concept_records = quiz_records
    
    if not concept_records:
        return 0.0
    
    # 按時間排序
    concept_records.sort(key=lambda x: x['attempt_time'])
    
    # 參數設定（調整為更合理的值）
    theta = 0.0   # 基礎能力參數（調整為0）
    w_s = 0.4    # 成功權重（增加）
    w_f = 0.2    # 失敗權重（減少）
    w_d = 0.2    # 難度權重（減少）
    w_t = 0.2    # 時間衰減權重（減少）
    lambda_decay = 0.05  # 遺忘率（減少）
    
    # 計算最近的成功和失敗次數（加權）
    successes_recent = 0
    failures_recent = 0
    difficulty_sum = 0
    time_decay_sum = 0
    
    current_time = datetime.now()
    
    for i, record in enumerate(concept_records):
        # 時間權重：最近的答題權重更高
        attempt_time = datetime.fromisoformat(record['attempt_time'].replace('Z', '+00:00'))
        # 轉換為naive datetime
        attempt_time = attempt_time.replace(tzinfo=None)
        time_diff_hours = (current_time - attempt_time).total_seconds() / 3600
        time_weight = math.exp(-lambda_decay * time_diff_hours / 24)  # 按天計算
        
        # 難度權重
        difficulty = record.get('difficulty', '中等')
        difficulty_weight = {'簡單': 1.0, '中等': 2.0, '困難': 3.0}.get(difficulty, 2.0)
        
        # 時間衰減
        time_decay = math.exp(-lambda_decay * time_diff_hours / 24)
        
        if record.get('is_correct', False):
            successes_recent += time_weight
        else:
            failures_recent += time_weight
        
        difficulty_sum += difficulty_weight * time_weight
        time_decay_sum += time_decay * time_weight
    
    # 計算平均難度和時間衰減
    total_attempts = len(concept_records)
    avg_difficulty = difficulty_sum / total_attempts if total_attempts > 0 else 2.0
    avg_time_decay = time_decay_sum / total_attempts if total_attempts > 0 else 1.0
    
    # 混合掌握度公式（保持原本的計算方式）
    mastery_raw = theta + w_s * successes_recent - w_f * failures_recent - w_d * avg_difficulty + w_t * avg_time_decay
    
    # Sigmoid函數壓縮到0-1
    mastery = 1 / (1 + math.exp(-mastery_raw))
    
    # 添加難度上限限制
    difficulty_limits = {
        '簡單': 0.6,  # 簡單題最多60%
        '中等': 0.8,  # 中等題最多80%
        '困難': 1.0   # 困難題最多100%
    }
    
    # 根據答題記錄中主要難度設定上限
    difficulty_counts = {'簡單': 0, '中等': 0, '困難': 0}
    for record in concept_records:
        difficulty = record.get('difficulty', '中等')
        if difficulty in difficulty_counts:
            difficulty_counts[difficulty] += 1
    
    # 找出主要難度（答題次數最多的）
    main_difficulty = max(difficulty_counts, key=difficulty_counts.get)
    max_mastery = difficulty_limits.get(main_difficulty, 1.0)
    
    # 應用上限限制
    mastery = min(mastery, max_mastery)
    
    return round(mastery, 3)

def calculate_enhanced_avg_time_per_concept(quiz_records: List[Dict]) -> float:
    """計算平均掌握時間 - 基於混合演算法"""
    if not quiz_records:
        return 0.0
    
    # 只計算答對的題目
    correct_records = [r for r in quiz_records if r.get('is_correct', False)]
    if not correct_records:
        return 0.0
    
    # 計算所有答對題目的平均時間
    total_time = 0
    count = 0
    
    for record in correct_records:
        time_spent = record.get('time_spent', 0)
        if time_spent > 0:
            total_time += time_spent
            count += 1
    
    if count == 0:
        return 0.0
    
    # 返回平均時間（分鐘）
    return (total_time / count) / 60

def calculate_enhanced_focus_score(quiz_records: List[Dict]) -> float:
    """計算增強版專注程度 - 基於專注度分析演算法"""
    if not quiz_records:
        return 0.0
    
    from collections import defaultdict
    from datetime import datetime, timezone, timedelta
    
    # 按會話分組（30分鐘內的答題視為同一會話）
    session_groups = defaultdict(list)
    current_session = []
    last_time = None
    
    for record in sorted(quiz_records, key=lambda x: x['attempt_time']):
        attempt_time = datetime.fromisoformat(record['attempt_time'].replace('Z', '+00:00'))
        
        if last_time is None or (attempt_time - last_time).total_seconds() > 1800:  # 30分鐘
            if current_session:
                session_groups[len(session_groups)] = current_session
            current_session = [record]
        else:
            current_session.append(record)
        
        last_time = attempt_time
    
    if current_session:
        session_groups[len(session_groups)] = current_session
    
    if not session_groups:
        return 0.0
    
    session_scores = []
    
    for session_id, session_records in session_groups.items():
        if len(session_records) < 2:
            continue
            
        # 計算會話專注度指標
        total_questions = len(session_records)
        correct_questions = sum(1 for r in session_records if r.get('is_correct', False))
        accuracy = correct_questions / total_questions
        
        # 時間一致性（答題間隔是否穩定）
        time_intervals = []
        for i in range(1, len(session_records)):
            prev_time = datetime.fromisoformat(session_records[i-1]['attempt_time'].replace('Z', '+00:00'))
            curr_time = datetime.fromisoformat(session_records[i]['attempt_time'].replace('Z', '+00:00'))
            interval = (curr_time - prev_time).total_seconds()
            time_intervals.append(interval)
        
        # 計算時間間隔的變異係數（越小越專注）
        if time_intervals:
            avg_interval = sum(time_intervals) / len(time_intervals)
            variance = sum((x - avg_interval) ** 2 for x in time_intervals) / len(time_intervals)
            cv = (variance ** 0.5) / avg_interval if avg_interval > 0 else 1
            time_consistency = max(0, 1 - cv)  # 變異係數越小，一致性越高
        else:
            time_consistency = 0
        
        # 難度適應性（能否處理不同難度的題目）
        difficulties = [r.get('difficulty', '中等') for r in session_records]
        difficulty_diversity = len(set(difficulties)) / 3  # 最多3種難度
        
        # 連續答對率（專注時更容易連續答對）
        consecutive_correct = 0
        max_consecutive = 0
        for r in session_records:
            if r.get('is_correct', False):
                consecutive_correct += 1
                max_consecutive = max(max_consecutive, consecutive_correct)
            else:
                consecutive_correct = 0
        
        consecutive_rate = max_consecutive / total_questions if total_questions > 0 else 0
        
        # 綜合專注度分數
        focus_score = (
            accuracy * 0.4 +           # 準確率權重40%
            time_consistency * 0.3 +   # 時間一致性權重30%
            difficulty_diversity * 0.2 + # 難度適應性權重20%
            consecutive_rate * 0.1     # 連續答對率權重10%
        )
        
        session_scores.append(focus_score)
    
    return sum(session_scores) / len(session_scores) if session_scores else 0.0

def _get_review_method(current_mastery: float) -> str:
    """根據當前掌握度獲取複習方法"""
    if current_mastery < 0.3:
        return '重新學習基礎概念'
    elif current_mastery < 0.6:
        return '重點練習相關題目'
    else:
        return '快速複習鞏固記憶'

def calculate_graph_based_mastery(student_id: str, concept_id: str, knowledge_graph: Dict = None) -> Dict[str, Any]:
    """計算圖基於的掌握度預測 - Graph-based KT"""
    try:
        # 獲取學生答題記錄
        quiz_records = get_student_quiz_records(student_id)
        
        # 獲取知識點關聯關係 - 需要先獲取概念名稱
        # 從概念ID獲取概念名稱（從MongoDB查詢）
        concept_name = get_concept_name_by_id(concept_id)
        logger.info(f"🔍 [DEBUG] 獲取概念名稱: {concept_id} -> {concept_name}")
        
        concept_relations = get_knowledge_relations_from_neo4j(concept_name)
        logger.info(f"🔍 [DEBUG] Neo4j關聯關係: 前置={len(concept_relations.get('prerequisites', []))}, 相關={len(concept_relations.get('related_concepts', []))}")
        
        # 簡化的圖神經網絡預測（基於關聯知識點的掌握度）
        related_concepts = concept_relations.get('prerequisites', []) + concept_relations.get('related_concepts', [])
        
        # 計算關聯知識點的平均掌握度
        related_mastery_scores = []
        for related_concept in related_concepts:
            related_concept_id = related_concept.get('id', '')
            related_records = [r for r in quiz_records if r['micro_concept_id'] == related_concept_id]
            if related_records:
                mastery = sum(1 for r in related_records if r['is_correct']) / len(related_records)
                related_mastery_scores.append(mastery)
        
        # 預測當前知識點的掌握度
        if related_mastery_scores:
            predicted_mastery = sum(related_mastery_scores) / len(related_mastery_scores)
            # 根據關聯強度調整預測
            avg_relation_strength = sum(r.get('strength', 0.5) for r in related_concepts) / len(related_concepts) if related_concepts else 0.5
            predicted_mastery *= avg_relation_strength
        else:
            predicted_mastery = 0.5  # 默認中等掌握度
        
        # 生成學習路徑推薦（基於Neo4j關聯關係）
        learning_path = generate_learning_path_recommendations(concept_id, concept_relations, quiz_records)
        
        return {
            'predicted_mastery': round(predicted_mastery, 2),
            'confidence': min(0.9, len(related_mastery_scores) * 0.2),  # 基於關聯知識點數量
            'related_concepts': related_concepts,
            'learning_path': learning_path,
            'prerequisites_analysis': analyze_prerequisites(concept_relations.get('prerequisites', []), quiz_records)
        }
        
    except Exception as e:
        logger.error(f"圖基於掌握度預測失敗: {e}")
        return {
            'predicted_mastery': 0.5,
            'confidence': 0.1,
            'related_concepts': [],
            'learning_path': [],
            'prerequisites_analysis': []
        }

def generate_learning_path_recommendations(concept_id: str, concept_relations: Dict, quiz_records: List[Dict]) -> List[Dict]:
    """使用AI生成個性化學習路徑推薦"""
    try:
        # 獲取當前概念的掌握度
        current_records = [r for r in quiz_records if r['micro_concept_id'] == concept_id]
        current_mastery = sum(1 for r in current_records if r['is_correct']) / len(current_records) if current_records else 0
        current_concept_name = get_concept_name_by_id(concept_id)
        
        # 分析學習歷史
        total_attempts = len(current_records)
        recent_attempts = len([r for r in current_records if r['attempt_time'] >= (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')])
        avg_time_per_question = sum(r.get('time_spent', 0) for r in current_records) / len(current_records) if current_records else 0
        
        # 分析錯誤模式
        wrong_records = [r for r in current_records if not r['is_correct']]
        common_errors = []
        if wrong_records:
            # 簡單的錯誤分析（實際可以更複雜）
            common_errors = ['概念理解不足', '計算錯誤', '應用能力欠缺']
        
        # 分析前置知識點
        prerequisites = concept_relations.get('prerequisites', [])
        related_concepts = concept_relations.get('related_concepts', [])
        
        # 準備AI提示詞 - 強化Neo4j關聯要求
        # 構建詳細的關聯資訊
        relations_context = ""
        if concept_relations and concept_relations.get('has_relations', False):
            prereqs = concept_relations.get('prerequisites', [])
            related = concept_relations.get('related_concepts', [])
            leads_to = concept_relations.get('leads_to', [])
            
            if prereqs:
                prereq_list = [f"{p['name']}(強度:{p.get('strength', 0.5):.2f})" for p in prereqs[:5]]
                relations_context += f"\n- **前置知識點**（必須先掌握，按強度排序）：{', '.join(prereq_list)}"
            
            if related:
                related_list = [f"{r['name']}(強度:{r.get('strength', 0.5):.2f})" for r in related[:5]]
                relations_context += f"\n- **相關知識點**（可同時學習）：{', '.join(related_list)}"
            
            if leads_to:
                leads_list = [f"{l['name']}(強度:{l.get('strength', 0.5):.2f})" for l in leads_to[:5]]
                relations_context += f"\n- **後續知識點**（掌握後可學習）：{', '.join(leads_list)}"
        else:
            relations_context = "\n- ⚠️ **無Neo4j關聯數據**：此知識點在知識圖譜中沒有關聯關係。"
        
        prompt = f"""
你是個性化學習路徑設計AI。請為學生設計3-5個具體的學習步驟，幫助他們系統性地掌握知識。

**⚠️ 重要：學習路徑設計必須嚴格遵循Neo4j知識圖譜的關聯關係！**

學生資料：
- 概念：{current_concept_name}
- 當前掌握度：{current_mastery:.1%}
- 總答題次數：{total_attempts}
- 最近7天答題：{recent_attempts}次
- 平均答題時間：{avg_time_per_question:.1f}分鐘
- 常見錯誤：{', '.join(common_errors) if common_errors else '無'}

**Neo4j知識圖譜關聯關係（必須參考）：**
{relations_context}

**設計要求（必須遵守）：**
1. **如果有前置知識點且掌握度低**：
   - 第一步必須是「先學習前置知識點：[具體知識點名稱]」
   - 必須按照前置知識點的強度順序安排學習
   - 如果有多個前置知識點，必須先學習強度最高的

2. **學習順序必須符合知識圖譜邏輯**：
   - 前置知識點 → 當前概念基礎 → 當前概念應用 → 相關知識點拓展 → 後續知識點預習

3. **如果沒有Neo4j關聯數據**：
   - 基於一般教學原則設計學習路徑
   - 在step_info中說明「缺少知識圖譜數據，使用一般學習順序」

請返回JSON格式的學習路徑，包含3個步驟，每個步驟需要：
- step_info: 學習任務描述（如"去課程觀看二維陣列基礎知識"）
- estimated_time: 預估時間（分鐘，數字）
- step_order: 步驟順序（1,2,3）

要求：
1. 根據掌握度設計適合的學習步驟（低掌握度<30%：基礎學習，中等30-70%：強化練習，高>70%：鞏固拓展）
2. 每個步驟都要具體明確，使用簡單易懂的描述
3. 步驟要有邏輯順序，循序漸進
4. 考慮學生的學習歷史和錯誤模式
5. 學習方式多樣化（觀看課程、練習題目、實際應用等）
6. 時間分配合理（總計不超過60分鐘）
7. 描述要簡潔明瞭，避免過於複雜的術語

返回格式：
{{
  "learning_path": [
    {{
      "step_info": "去課程觀看二維陣列基礎知識",
      "estimated_time": 15,
      "step_order": 1
    }},
    {{
      "step_info": "練習二維陣列基礎題目10題",
      "estimated_time": 20,
      "step_order": 2
    }},
    {{
      "step_info": "解決3個二維陣列實際應用問題",
      "estimated_time": 25,
      "step_order": 3
    }}
  ]
}}
"""
        
        # 調用Gemini API
        model = init_gemini('gemini-2.5-flash')
        response = model.generate_content(prompt)
        ai_response = response.text.strip()
        
        # 解析AI回應
        import json
        try:
            # 清理回應，移除可能的markdown格式
            if ai_response.startswith('```json'):
                ai_response = ai_response[7:]
            if ai_response.endswith('```'):
                ai_response = ai_response[:-3]
            
            ai_data = json.loads(ai_response)
            learning_path = ai_data.get('learning_path', [])
            
            # 確保learning_path是列表且不為None
            if not learning_path or not isinstance(learning_path, list):
                logger.warning("AI回傳的learning_path為空或格式錯誤，使用默認路徑")
                learning_path = []
            
            # 確保每個步驟都有必要的字段
            for step in learning_path:
                if step and isinstance(step, dict):
                    step.setdefault('step_order', 1)
                    step.setdefault('estimated_time', 15)
            
            logger.info(f"AI生成學習路徑成功：{len(learning_path)}個步驟")
            return learning_path
            
        except json.JSONDecodeError as e:
            logger.error(f"AI回應JSON解析失敗: {e}")
            logger.error(f"AI原始回應: {ai_response}")
    except Exception as e:
        logger.error(f"AI生成學習路徑失敗: {e}")

def ensure_diverse_action_types(top_actions: List[Dict], learning_path: List[Dict]) -> List[Dict]:
    """
    確保 top_actions 包含三種不同類型（SEEK_HELP, REVIEW_BASICS, PRACTICE）
    如果 AI 返回的類型重複，根據 learning_path 自動修正
    
    Args:
        top_actions: AI 生成的 top_actions 列表
        learning_path: 學習路徑步驟列表
        
    Returns:
        修正後的 top_actions 列表，確保包含三種不同類型
    """
    if not top_actions or not learning_path:
        return top_actions
    
    # 定義關鍵字映射
    def infer_type(step_info: str) -> str:
        if not step_info:
            return "SEEK_HELP"
        step_lower = step_info.lower()
        # 練習優先
        if any(kw in step_info for kw in ['練習', '答題', '應用', '嘗試', '回答', '問題', '情境']):
            return "PRACTICE"
        # 理解/掌握
        if any(kw in step_info for kw in ['深入理解', '理解', '掌握', '鞏固']):
            return "REVIEW_BASICS"
        # 觀看/閱讀
        if any(kw in step_info for kw in ['觀看', '閱讀', '課程']):
            return "SEEK_HELP"
        # 學習
        if any(kw in step_info for kw in ['學習']):
            return "REVIEW_BASICS"
        return "SEEK_HELP"
    
    # 檢查現有類型
    existing_types = [action.get('action', '') for action in top_actions[:3]]
    required_types = ['SEEK_HELP', 'REVIEW_BASICS', 'PRACTICE']
    missing_types = [t for t in required_types if t not in existing_types]
    
    # 如果已經有三種不同類型，直接返回
    if len(set(existing_types)) == 3:
        return top_actions[:3]
    
    # 需要修正：根據 learning_path 重新分配類型
    fixed_actions = []
    used_types = set()
    
    for i in range(min(3, len(learning_path))):
        step = learning_path[i]
        step_info = step.get('step_info', '')
        estimated_time = step.get('estimated_time', 15)
        
        # 優先使用缺失的類型
        inferred_type = infer_type(step_info)
        
        # 如果這個類型已經用過，且還有缺失的類型，優先使用缺失的
        if inferred_type in used_types and missing_types:
            inferred_type = missing_types[0]
            missing_types.remove(inferred_type)
        
        used_types.add(inferred_type)
        
        # 使用原始 detail 或 step_info
        original_action = top_actions[i] if i < len(top_actions) else {}
        detail = original_action.get('detail', step_info)
        
        fixed_actions.append({
            'action': inferred_type,
            'detail': detail,
            'est_min': estimated_time
        })
    
    return fixed_actions

def analyze_prerequisites(prerequisites: List[Dict], quiz_records: List[Dict]) -> List[Dict]:
    """分析前置知識點掌握情況"""
    analysis = []
    
    for prereq in prerequisites:
        prereq_id = prereq.get('id', '')
        prereq_records = [r for r in quiz_records if r['micro_concept_id'] == prereq_id]
        
        if prereq_records:
            mastery = sum(1 for r in prereq_records if r['is_correct']) / len(prereq_records)
            status = '已掌握' if mastery >= 0.8 else '部分掌握' if mastery >= 0.5 else '未掌握'
        else:
            mastery = 0
            status = '未學習'
        
        analysis.append({
            'concept_id': prereq_id,
            'concept_name': prereq.get('name', '未知概念'),
            'mastery': round(mastery, 2),
            'status': status,
            'is_ready': mastery >= 0.6
        })
    
    return analysis

# 已移除 /learning-path-prediction API - 前端未使用

# 新增的統計計算函數
def calculate_consecutive_days(quiz_records: List[Dict]) -> int:
    """計算連續學習天數"""
    if not quiz_records:
        return 0
    
    # 按日期分組
    daily_records = {}
    for record in quiz_records:
        date = record['attempt_time'][:10]  # 提取日期部分
        if date not in daily_records:
            daily_records[date] = []
        daily_records[date].append(record)
    
    # 按日期排序
    sorted_dates = sorted(daily_records.keys(), reverse=True)
    
    consecutive_days = 0
    from datetime import timezone
    current_date = datetime.now(timezone.utc).date()
    
    for date_str in sorted_dates:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        if date_obj == current_date or date_obj == current_date - timedelta(days=consecutive_days):
            consecutive_days += 1
            current_date = date_obj - timedelta(days=1)
        else:
            break
    
    return consecutive_days

def calculate_total_study_time(quiz_records: List[Dict]) -> float:
    """計算總學習時間（小時）"""
    if not quiz_records:
        return 0.0
    
    # 計算所有答題的時間（包括答對和答錯）
    total_seconds = sum(record.get('time_spent', 0) for record in quiz_records)
    total_hours = total_seconds / 3600  # 轉換為小時
    return round(total_hours, 1)

def calculate_avg_daily_time(quiz_records: List[Dict]) -> int:
    """計算平均每日學習時間（分鐘）"""
    if not quiz_records:
        return 0
    
    # 計算學習天數
    daily_records = set()
    for record in quiz_records:
        date = record['attempt_time'][:10]
        daily_records.add(date)
    
    if not daily_records:
        return 0
    
    # 使用實際記錄的答題時間
    total_seconds = sum(record.get('time_spent', 0) for record in quiz_records)
    total_minutes = total_seconds / 60  # 轉換為分鐘
    avg_daily = total_minutes / len(daily_records)
    return int(avg_daily)

def calculate_longest_session(quiz_records: List[Dict]) -> int:
    """計算最長學習時段（分鐘）"""
    if not quiz_records:
        return 0
    
    # 按時間排序
    sorted_records = sorted(quiz_records, key=lambda x: x['attempt_time'])
    
    max_session = 0
    current_session = 0
    last_time = None
    
    for record in sorted_records:
        current_time = datetime.fromisoformat(record['attempt_time'].replace('Z', '+00:00'))
        answer_time = record.get('time_spent', 0)  # 實際答題時間（秒）
        
        if last_time is None:
            current_session = answer_time / 60  # 轉換為分鐘
        else:
            time_diff = (current_time - last_time).total_seconds() / 60  # 轉換為分鐘
            
            if time_diff <= 30:  # 30分鐘內算作同一個學習時段
                current_session += answer_time / 60  # 累加實際答題時間
            else:
                max_session = max(max_session, current_session)
                current_session = answer_time / 60  # 重新開始計算
        
        last_time = current_time
    
    max_session = max(max_session, current_session)
    return int(max_session)

def calculate_study_intensity(quiz_records: List[Dict]) -> int:
    """計算學習強度（百分比）"""
    if not quiz_records:
        return 0
    
    # 計算最近7天的學習強度
    from datetime import timezone
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    recent_records = [r for r in quiz_records 
                     if datetime.fromisoformat(r['attempt_time'].replace('Z', '+00:00')) >= week_ago]
    
    if not recent_records:
        return 0
    
    # 計算每日學習次數
    daily_counts = {}
    for record in recent_records:
        date = record['attempt_time'][:10]
        daily_counts[date] = daily_counts.get(date, 0) + 1
    
    if not daily_counts:
        return 0
    
    # 計算學習強度：平均每日學習次數 / 10 * 100
    avg_daily = sum(daily_counts.values()) / len(daily_counts)
    intensity = min(100, int((avg_daily / 10) * 100))
    
    return intensity

def generate_improvement_items(domains: List[Dict], quiz_records: List[Dict]) -> List[Dict]:
    """生成最近進步的知識點數據"""
    improvement_items = []
    
    # 按領域分組分析
    domain_records = {}
    for record in quiz_records:
        domain_name = record.get('domain_name', '未知領域')
        if domain_name not in domain_records:
            domain_records[domain_name] = []
        domain_records[domain_name].append(record)
    
    # 為每個領域分析進步情況
    for domain_name, records in domain_records.items():
        # 跳過「未知領域」
        if domain_name == '未知領域' or domain_name == '未知' or not domain_name or domain_name.strip() == '':
            continue
        if len(records) < 3:
            continue
            
        # 按時間排序（最新的在前）
        records.sort(key=lambda x: x['attempt_time'], reverse=True)
        
        # 計算最近和之前的正確率
        mid_point = len(records) // 2
        recent_records = records[:mid_point]  # 最近的一半
        older_records = records[mid_point:]   # 較早的一半
        
        if len(older_records) == 0:
            continue
            
        recent_accuracy = sum(1 for r in recent_records if r['is_correct']) / len(recent_records)
        older_accuracy = sum(1 for r in older_records if r['is_correct']) / len(older_records)
        
        improvement = (recent_accuracy - older_accuracy) * 100
        
        
        # 降低進步要求，只要有進步就顯示
        if improvement > 0:  # 只要有進步就顯示
            # 計算該領域的掌握度
            domain_mastery = recent_accuracy  # 使用最近準確率作為掌握度
            
            improvement_items.append({
                'name': domain_name,
                'improvement': round(improvement, 1),
                'priority': 'high' if improvement > 30 else 'medium' if improvement > 10 else 'low',
                'current_accuracy': round(recent_accuracy * 100, 1),
                'previous_accuracy': round(older_accuracy * 100, 1),
                'mastery': round(domain_mastery, 3),  # 添加掌握度字段
                'questions': len(records)  # 添加題目數量字段
            })
    
    # 按進步幅度排序
    improvement_items.sort(key=lambda x: x['improvement'], reverse=True)
    return improvement_items[:5]  # 返回前5個

def get_concept_name_by_id(concept_id: str) -> str:
    """根據概念ID獲取概念名稱 - 改進版本，支援多種查找方式"""
    try:
        from accessories import mongo
        
        if not mongo:
            logger.warning("MongoDB未初始化，返回默認概念名稱")
            return f"概念_{concept_id[-6:]}"
        
        # 方法1：嘗試使用 ObjectId 查詢（標準方式）
        try:
            if len(concept_id) == 24:  # MongoDB ObjectId 長度
                concept_doc = mongo.db.micro_concept.find_one({'_id': ObjectId(concept_id)})
                if concept_doc:
                    concept_name = concept_doc.get('name', '')
                    if concept_name:
                        logger.debug(f"✅ 找到概念名稱（ObjectId）: {concept_id} -> {concept_name}")
                        return concept_name
        except Exception as e:
            logger.debug(f"ObjectId 查詢失敗: {e}")
        
        # 方法2：嘗試使用概念ID作為名稱直接查詢（某些情況下 micro_concept_id 就是名稱）
        try:
            concept_doc = mongo.db.micro_concept.find_one({'name': concept_id})
            if concept_doc:
                concept_name = concept_doc.get('name', '')
                if concept_name:
                    logger.debug(f"✅ 找到概念名稱（名稱查詢）: {concept_id} -> {concept_name}")
                    return concept_name
        except Exception as e:
            logger.debug(f"名稱查詢失敗: {e}")
        
        # 方法3：嘗試使用 _id 字串匹配（某些情況下可能是字串格式的ID）
        try:
            concept_doc = mongo.db.micro_concept.find_one({'_id': concept_id})
            if concept_doc:
                concept_name = concept_doc.get('name', '')
                if concept_name:
                    logger.debug(f"✅ 找到概念名稱（字串ID）: {concept_id} -> {concept_name}")
                    return concept_name
        except Exception as e:
            logger.debug(f"字串ID查詢失敗: {e}")
        
        # 如果都找不到，返回警告和默認名稱
        logger.warning(f"⚠️ 未找到概念ID {concept_id}，返回默認名稱。這可能導致 Neo4j 查詢失敗。")
        default_name = f"概念_{concept_id[-6:]}"
        logger.warning(f"   默認名稱: {default_name}（此名稱在 Neo4j 中可能不存在）")
        return default_name
            
    except Exception as e:
        logger.error(f"❌ 獲取概念名稱失敗: {e}", exc_info=True)
        return f"概念_{concept_id[-6:]}"

def get_knowledge_relations_from_neo4j(concept_name: str) -> Dict[str, Any]:
    """從Neo4j獲取知識點關聯數據 - 改進版本，使用 elementId 並增強關聯資訊"""
    try:
        from accessories import neo4j_driver
        
        if not neo4j_driver:
            logger.warning("Neo4j驅動未初始化，返回空關聯數據")
            return {
                'prerequisites': [],
                'related_concepts': [],
                'leads_to': [],
                'all_relations': [],
                'relation_graph': {}
            }
        
        with neo4j_driver.session() as session:
            # 改進查詢：使用 elementId 替代已棄用的 id()，不查詢不存在的 strength 屬性
            # 注意：Neo4j 關聯關係可能沒有 strength 屬性，我們在程式碼中根據類型設定默認值
            query = """
            MATCH (c:Section {name: $concept_name})-[r:PREREQUISITE|SIMILAR_TO|CROSS_DOMAIN_LINK|LEADS_TO]-(related:Section)
            RETURN 
                related.name as related_name,
                type(r) as relation_type,
                elementId(related) as related_id,
                elementId(c) as current_id,
                c.name as current_name
            ORDER BY 
                CASE type(r)
                    WHEN 'PREREQUISITE' THEN 1
                    WHEN 'SIMILAR_TO' THEN 2
                    WHEN 'CROSS_DOMAIN_LINK' THEN 3
                    WHEN 'LEADS_TO' THEN 4
                END
            LIMIT 20
            """
            
            result = session.run(query, concept_name=concept_name)
            relations = []
            relation_graph = {
                'current_concept': concept_name,
                'current_id': None,
                'nodes': [],
                'edges': []
            }
            
            logger.info(f"🔍 [Neo4j] 查詢知識點關聯: {concept_name}")
            
            for record in result:
                # 根據關聯類型設定默認強度（因為 Neo4j 關聯關係中沒有 strength 屬性）
                rel_type = record['relation_type']
                if rel_type == 'PREREQUISITE':
                    relation_strength = 0.9  # 前置知識點強度較高
                elif rel_type == 'SIMILAR_TO':
                    relation_strength = 0.7
                elif rel_type == 'CROSS_DOMAIN_LINK':
                    relation_strength = 0.6
                elif rel_type == 'LEADS_TO':
                    relation_strength = 0.8
                else:
                    relation_strength = 0.5
                
                relation = {
                    'id': str(record['related_id']),
                    'name': record['related_name'],
                    'type': record['relation_type'],
                    'strength': float(relation_strength),
                    'type_display': get_relation_type_display(record['relation_type'])
                }
                relations.append(relation)
                
                # 構建關聯圖數據
                if not relation_graph['current_id']:
                    relation_graph['current_id'] = str(record.get('current_id', ''))
                
                relation_graph['nodes'].append({
                    'id': str(record['related_id']),
                    'name': record['related_name'],
                    'type': record['relation_type']
                })
                
                relation_graph['edges'].append({
                    'source': str(record.get('current_id', '')),
                    'target': str(record['related_id']),
                    'type': record['relation_type'],
                    'strength': float(relation_strength),
                    'label': get_relation_type_display(record['relation_type'])
                })
                
                logger.debug(f"  ✅ 找到關聯: {relation['name']} ({relation['type_display']}, 強度: {relation['strength']:.2f})")
            
            # 分類關聯關係
            prerequisites = [r for r in relations if r['type'] == 'PREREQUISITE']
            related = [r for r in relations if r['type'] in ['SIMILAR_TO', 'CROSS_DOMAIN_LINK']]
            leads_to = [r for r in relations if r['type'] == 'LEADS_TO']
            
            # 去重處理：如果同一個知識點有多種類型的關聯，合併關聯類型並保留最高強度
            def deduplicate_relations(relation_list):
                """去重關聯關係，合併多種類型並保留最高強度"""
                seen = {}
                for rel in relation_list:
                    key = rel['id']  # 使用知識點ID作為唯一標識
                    if key not in seen:
                        # 首次出現，初始化
                        seen[key] = rel.copy()
                        seen[key]['types'] = [rel['type']]
                    else:
                        # 已存在，合併關聯類型
                        if rel['type'] not in seen[key]['types']:
                            seen[key]['types'].append(rel['type'])
                        
                        # 更新為最高強度
                        if rel['strength'] > seen[key]['strength']:
                            seen[key]['strength'] = rel['strength']
                        
                        # 更新顯示類型（合併所有類型）
                        seen[key]['type'] = seen[key]['types'][0]  # 保留第一個類型作為主要類型
                        seen[key]['type_display'] = '、'.join([get_relation_type_display(t) for t in seen[key]['types']])
                
                return list(seen.values())
            
            # 對各類關聯進行去重
            prerequisites = deduplicate_relations(prerequisites)
            related = deduplicate_relations(related)
            leads_to = deduplicate_relations(leads_to)
            
            logger.info(f"📊 [Neo4j] 關聯統計（去重後）: 前置={len(prerequisites)}, 相關={len(related)}, 後續={len(leads_to)}, 總計={len(prerequisites) + len(related) + len(leads_to)}")
            
            return {
                'prerequisites': prerequisites,
                'related_concepts': related,
                'leads_to': leads_to,
                'all_relations': relations,
                'relation_graph': relation_graph,
                'has_relations': len(relations) > 0
            }
            
    except Exception as e:
        logger.error(f"❌ Neo4j查詢失敗: {e}", exc_info=True)
        return {
            'prerequisites': [],
            'related_concepts': [],
            'leads_to': [],
            'all_relations': [],
            'relation_graph': {},
            'has_relations': False
        }

def get_relation_type_display(relation_type: str) -> str:
    """獲取關聯類型的中文顯示名稱"""
    type_mapping = {
        'PREREQUISITE': '前置知識點',
        'SIMILAR_TO': '相似概念',
        'CROSS_DOMAIN_LINK': '跨領域關聯',
        'LEADS_TO': '後續知識點'
    }
    return type_mapping.get(relation_type, relation_type)

def generate_ai_diagnosis(concept_name: str, domain_name: str, mastery: float, 
                         total_attempts: int, correct_attempts: int, recent_accuracy: float,
                         wrong_records: List[Dict], knowledge_relations: Dict[str, Any] = None,
                         difficulty_stats: Dict[str, Dict] = None, learning_path: List[Dict] = None) -> Dict[str, Any]:
    """使用Gemini API生成AI診斷結果"""
    
    try:
        # 初始化Gemini模型
        model = init_gemini('gemini-2.5-flash')
        
        # 準備診斷數據
        wrong_count = total_attempts - correct_attempts
        error_analysis = ""
        if wrong_records:
            error_types = []
            for record in wrong_records[:5]:  # 分析最近5次錯誤
                if record.get('error_reason'):
                    error_types.append(record['error_reason'])
            if error_types:
                error_analysis = f"常見錯誤類型：{', '.join(set(error_types))}"
        
        # 準備知識點關聯數據 - 增強版本，包含關聯強度和類型
        relations_info = ""
        relations_detail = {}
        if knowledge_relations and knowledge_relations.get('has_relations', False):
            prereqs = knowledge_relations.get('prerequisites', [])
            related = knowledge_relations.get('related_concepts', [])
            leads_to = knowledge_relations.get('leads_to', [])
            all_relations = knowledge_relations.get('all_relations', [])
            
            # 構建詳細的關聯資訊
            if prereqs:
                prereq_details = [f"{r['name']}(強度:{r['strength']:.2f})" for r in prereqs[:5]]
                relations_info += f"\n- **前置知識點**（必須先掌握）：{', '.join(prereq_details)}"
                relations_detail['prerequisites'] = [
                    {'name': r['name'], 'strength': r['strength'], 'type': r['type_display']} 
                    for r in prereqs[:5]
                ]
            
            if related:
                related_details = [f"{r['name']}(強度:{r['strength']:.2f})" for r in related[:5]]
                relations_info += f"\n- **相關知識點**（可同時學習）：{', '.join(related_details)}"
                relations_detail['related'] = [
                    {'name': r['name'], 'strength': r['strength'], 'type': r['type_display']} 
                    for r in related[:5]
                ]
            
            if leads_to:
                leads_details = [f"{r['name']}(強度:{r['strength']:.2f})" for r in leads_to[:5]]
                relations_info += f"\n- **後續知識點**（掌握後可學習）：{', '.join(leads_details)}"
                relations_detail['leads_to'] = [
                    {'name': r['name'], 'strength': r['strength'], 'type': r['type_display']} 
                    for r in leads_to[:5]
                ]
            
            # 添加關聯圖數據
            relations_detail['relation_graph'] = knowledge_relations.get('relation_graph', {})
            relations_detail['total_relations'] = len(all_relations)
        else:
            relations_info = "\n- ⚠️ **無Neo4j關聯數據**：此知識點在知識圖譜中沒有關聯關係，請基於一般教學原則進行診斷。"
            relations_detail = {'has_relations': False}
        
        # 準備難易度分析數據
        difficulty_info = ""
        if difficulty_stats:
            difficulty_info = "\n- 題目難易度分布："
            for difficulty, stats in difficulty_stats.items():
                accuracy = stats['correct'] / stats['total'] if stats['total'] > 0 else 0
                difficulty_info += f"\n  * {difficulty}：{stats['correct']}/{stats['total']} 正確 ({accuracy:.1%})"
        
        # 準備學習路徑數據
        learning_path_info = ""
        if learning_path:
            learning_path_info = "\n- 推薦學習路徑："
            for i, step in enumerate(learning_path[:5]):  # 只顯示前5個步驟
                step_info = step.get('step_info', step.get('concept_name', '未知步驟'))
                estimated_time = step.get('estimated_time', 15)
                learning_path_info += f"\n  {i+1}. {step_info} (預估時間: {estimated_time}分鐘)"

        # 構建Gemini提示詞 - 使用新的JSON schema
        import json
        
        prompt = f"""
你是教學診斷AI。只輸出JSON，遵守schema: summary(<=20中文字), metrics, root_causes[], top_actions[<=3], practice_examples[<=3], evidence[], confidence, knowledge_relations. 如果資料不足設定confidence=low並回傳baseline plan。不要多說話。

**⚠️ 重要：你必須基於Neo4j知識圖譜的關聯關係進行診斷！**

學生資料:
{{
    "concept": "{concept_name}",
    "domain": "{domain_name}",
    "metrics": {{
        "mastery": {mastery:.2f},
        "attempts": {total_attempts},
        "recent_accuracy": {recent_accuracy:.2f},
        "avg_time": 22
    }},
    "recent_wrong_questions": {json.dumps([{"q_id": f"q{i}", "err": r.get('error_reason', '未知錯誤'), "text": "題目內容"} for i, r in enumerate(wrong_records[:3])])},
    "difficulty_stats": {json.dumps(difficulty_stats)},
    "learning_path": {json.dumps(learning_path[:5]) if learning_path else '[]'},
    "learning_path_info": "{learning_path_info if learning_path_info else '無學習路徑數據'}"
}}

**Neo4j知識圖譜關聯數據（必須參考）：**
{relations_info}

**關聯數據詳細資訊：**
{json.dumps(relations_detail, ensure_ascii=False, indent=2)}

**診斷要求（必須遵守）：**
1. **必須分析Neo4j關聯關係**：
   - 如果有前置知識點，必須在root_causes中分析是否因為前置知識不足導致當前概念理解困難
   - 如果有相關知識點，必須在top_actions中建議同時複習相關概念
   - 如果有後續知識點，必須在evidence中說明掌握當前概念對後續學習的重要性

2. **學習路徑設計必須基於關聯關係**：
   - 如果有前置知識點且掌握度低，必須先建議學習前置知識點
   - 如果有相關知識點，可以建議同時學習以加深理解
   - 學習順序必須符合知識圖譜的邏輯關係

3. **如果沒有Neo4j關聯數據**：
   - 在confidence中標記為"low"
   - 在evidence中說明"缺少知識圖譜關聯數據，診斷基於一般教學原則"
   - 仍然提供基礎的學習建議

請返回以下格式的JSON，top_actions的action字段必須使用以下標準化類型之一：
- "REVIEW_BASICS" (AI基礎教學) - 用於需要AI導師教學、深入理解的步驟
- "PRACTICE" (AI出題練習) - 用於需要練習題目、實際應用的步驟
- "SEEK_HELP" (教材觀看) - 用於需要觀看課程、閱讀教材的步驟
- "ADD_TO_CALENDAR" (加入行事曆) - 用於需要安排時間的步驟

**⚠️ 重要：top_actions 必須嚴格遵守以下規則！**

1. **必須包含三種不同類型**：
   - top_actions 必須包含至少一個 "SEEK_HELP" (教材觀看)
   - top_actions 必須包含至少一個 "REVIEW_BASICS" (AI基礎教學)
   - top_actions 必須包含至少一個 "PRACTICE" (AI出題練習)
   - 總共3個 actions，每個類型各一個，不能重複

2. **必須根據 learning_path 生成**：
   - 仔細分析 learning_path 中每個步驟的 step_info
   - 為前3個步驟生成對應的 top_actions
   - 每個 top_actions[i] 對應 learning_path[i]
   - action.detail = learning_path[i].step_info（直接使用，不要修改）
   - action.est_min = learning_path[i].estimated_time（直接使用，不要修改）

3. **類型判斷規則（必須遵守）**：
   - 如果 step_info 包含「觀看」、「閱讀」、「課程」等關鍵字 → 使用 "SEEK_HELP" (教材觀看)
   - 如果 step_info 包含「深入理解」、「理解」、「掌握」、「學習」等關鍵字 → 使用 "REVIEW_BASICS" (AI基礎教學)
   - 如果 step_info 包含「練習」、「答題」、「應用」、「嘗試」、「回答」、「問題」等關鍵字 → 使用 "PRACTICE" (AI出題練習)
   - 如果一個步驟包含多個關鍵字，優先順序：PRACTICE > REVIEW_BASICS > SEEK_HELP

4. **類型分配策略**：
   - 如果 learning_path 有3個步驟，必須確保三個步驟分別對應三種不同類型
   - 如果前3個步驟類型重複，必須調整分配，確保三種類型都有
   - 優先將包含「練習」、「回答」等關鍵字的步驟分配為 PRACTICE
   - 優先將包含「觀看」、「閱讀」等關鍵字的步驟分配為 SEEK_HELP
   - 優先將包含「理解」、「掌握」等關鍵字的步驟分配為 REVIEW_BASICS

{{
    "summary": "string (<=20中文字)",
    "metrics": {{
        "domain": "{domain_name}",
        "concept": "{concept_name}",
        "mastery": {mastery:.2f},
        "attempts": {total_attempts},
        "recent_accuracy": {recent_accuracy:.2f}
    }},
    "root_causes": ["string1", "string2", "string3"],
    "top_actions": [
        {{"action": "SEEK_HELP", "detail": "根據learning_path[0]的step_info", "est_min": learning_path[0].estimated_time}},
        {{"action": "REVIEW_BASICS", "detail": "根據learning_path[1]的step_info", "est_min": learning_path[1].estimated_time}},
        {{"action": "PRACTICE", "detail": "根據learning_path[2]的step_info", "est_min": learning_path[2].estimated_time}}
    ],
    "practice_examples": [
        {{"q_id": "q101", "difficulty": "easy", "text": "string"}},
        {{"q_id": "q102", "difficulty": "easy", "text": "string"}},
        {{"q_id": "q103", "difficulty": "medium", "text": "string"}}
    ],
    "evidence": ["string1", "string2"],
    "confidence": "high/medium/low",
    "learning_path": {json.dumps(learning_path[:5]) if learning_path else '[]'},
    "full_text": "string (200-300字，給學生看的親切診斷報告)"
}}

**full_text 格式要求（非常重要）：**
- **語氣**：親切、鼓勵、像老師在跟學生說話，不要用學術論文語氣
- **長度**：200-300字，簡潔明瞭，不要冗長
- **結構**：
  1. 開頭：簡短總結學習狀況（1-2句）
  2. 問題：用簡單的話說明主要問題（2-3點，每點1句）
  3. 建議：具體的學習建議（2-3點，每點1句）
  4. 結尾：鼓勵的話（1句）
- **避免**：
  - ❌ 不要用「精熟度」、「關聯強度為0.6」等技術術語
  - ❌ 不要用「為有效提升學習成效」等學術化表達
  - ❌ 不要過度解釋知識圖譜的技術細節
  - ❌ 不要用「持續的學習與反思，將是突破當前學習困境的關鍵」等空泛的話
- **應該**：
  - ✅ 用「掌握度14%」、「答題正確率20%」等簡單數字
  - ✅ 用「建議你先...」、「你可以試試...」等親切語氣
  - ✅ 用「這個概念和XX有關，一起學習會更容易理解」等簡單說明
  - ✅ 用「加油！多練習幾次就會進步」等鼓勵的話

**範例（好的 full_text）：**
「你在「AI 工程崛起」這個概念上還需要多加強。目前掌握度只有14%，答題正確率20%，顯示對基本概念還不夠熟悉。

主要問題是基礎概念理解不足，特別是中等難度的題目答錯較多。建議你先透過AI導師重新學習基本定義，然後多做一些練習題來鞏固。

這個概念和「知識管理與 AI」有關聯，可以一起學習會更容易理解。記住，學習需要時間，多練習幾次就會進步，加油！」

重要：action字段必須嚴格使用上述4個標準化類型之一，不要使用其他文字。
"""

        # 調用Gemini API
        response = model.generate_content(prompt)
        ai_response = response.text.strip()
        
        # 解析JSON響應
        try:
            # 清理響應文本，移除可能的markdown格式
            if ai_response.startswith('```json'):
                ai_response = ai_response[7:]
            if ai_response.endswith('```'):
                ai_response = ai_response[:-3]
            
            # 處理控制字符（換行符等）- 使用更可靠的方法
            import re
            import sys
            
            # 方法1：嘗試使用 strict=False（Python 3.9+）
            try:
                if sys.version_info >= (3, 9):
                    ai_data = json.loads(ai_response, strict=False)
                else:
                    raise TypeError("Python < 3.9")
            except (TypeError, json.JSONDecodeError) as e:
                # 方法2：手動修復 full_text 字段中的控制字符
                # 使用正則表達式找到 "full_text" 字段並修復其中的換行符
                try:
                    # 匹配 "full_text": "..." 模式（支持多行）
                    # 使用非貪婪匹配和 DOTALL 模式
                    pattern = r'"full_text"\s*:\s*"((?:[^"\\]|\\.)*)"'
                    
                    def fix_control_chars(match):
                        """修復字串值中的控制字符"""
                        content = match.group(1)
                        # 轉義控制字符（但保留已轉義的字符）
                        # 只替換未轉義的控制字符
                        content = re.sub(r'(?<!\\)\n', '\\n', content)
                        content = re.sub(r'(?<!\\)\r', '\\r', content)
                        content = re.sub(r'(?<!\\)\t', '\\t', content)
                        return f'"full_text": "{content}"'
                    
                    ai_response_cleaned = re.sub(pattern, fix_control_chars, ai_response, flags=re.DOTALL)
                    ai_data = json.loads(ai_response_cleaned)
                except json.JSONDecodeError:
                    # 方法3：最後嘗試 - 使用更寬鬆的修復
                    # 直接替換所有控制字符（可能破壞結構，但作為最後手段）
                    try:
                        ai_response_cleaned = ai_response.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
                        # 但這會破壞 full_text 的格式，所以我們需要更智能的方法
                        # 改用：只替換字串值中的控制字符
                        # 簡單方法：找到所有字串值並修復
                        def escape_string_value(match):
                            quote = match.group(1)
                            content = match.group(2)
                            # 轉義控制字符
                            content = content.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
                            return f'{quote}{content}{quote}'
                        
                        # 匹配字串值（簡化版本）
                        ai_response_cleaned = re.sub(r'(")((?:[^"\\]|\\.)*)(")', escape_string_value, ai_response)
                        ai_data = json.loads(ai_response_cleaned)
                    except json.JSONDecodeError as final_error:
                        logger.error(f"所有 JSON 修復方法都失敗: {final_error}")
                        logger.error(f"原始響應前1000字符: {ai_response[:1000]}")
                        raise
            
            # 獲取 learning_path 和 top_actions
            ai_learning_path = ai_data.get('learning_path', learning_path or [])
            ai_top_actions = ai_data.get('top_actions', [
                {"action": "複習基礎", "detail": "重新學習基本概念", "est_min": 10},
                {"action": "做練習", "detail": "完成相關練習題", "est_min": 20},
                {"action": "尋求幫助", "detail": "重新複習課程", "est_min": 5}
            ])
            
            # 確保 top_actions 包含三種不同類型
            fixed_top_actions = ensure_diverse_action_types(ai_top_actions, ai_learning_path)
            
            # 驗證並返回新的schema格式，包含Neo4j關聯資訊
            return {
                'summary': ai_data.get('summary', f'{concept_name}掌握度{mastery:.1%}，需重點關注'),
                'metrics': {
                    'domain': domain_name,
                    'concept': concept_name,
                    'mastery': mastery,
                    'attempts': total_attempts,
                    'recent_accuracy': recent_accuracy
                },
                'root_causes': ai_data.get('root_causes', ['基礎概念不牢固', '練習不足']),
                'top_actions': fixed_top_actions,
                'practice_examples': ai_data.get('practice_examples', [
                    {"q_id": "q101", "difficulty": "easy", "text": "基礎概念題"},
                    {"q_id": "q102", "difficulty": "medium", "text": "應用練習題"}
                ]),
                # 使用後端準備的 relations_detail，而不是 AI 返回的格式
                # AI 可能返回錯誤格式的 knowledge_relations，我們忽略它
                'knowledge_relations': {
                    'has_relations': knowledge_relations.get('has_relations', False) if knowledge_relations else False,
                    'prerequisites': relations_detail.get('prerequisites', []) if relations_detail else [],
                    'related_concepts': relations_detail.get('related', []) if relations_detail else [],
                    'leads_to': relations_detail.get('leads_to', []) if relations_detail else [],
                    'relation_graph': relations_detail.get('relation_graph', {}) if relations_detail else {},
                    'total_relations': relations_detail.get('total_relations', 0) if relations_detail else 0
                },
                'evidence': ai_data.get('evidence', [f'答題{total_attempts}次', f'正確率{recent_accuracy:.1%}']),
                'confidence': ai_data.get('confidence', 'medium'),
                'learning_path': ai_learning_path,  # 優先使用AI生成的學習路徑
                'full_text': ai_data.get('full_text', f'''
## 詳細診斷分析

### 學習狀況評估
- **概念名稱**：{concept_name}
- **所屬領域**：{domain_name}
- **整體掌握度**：{mastery:.1%}
- **答題次數**：{total_attempts}次
- **最近準確率**：{recent_accuracy:.1%}

### 問題分析
根據您的答題記錄分析，在{concept_name}這個知識點上存在以下問題：

1. **基礎概念理解不足**：掌握度僅{mastery:.1%}，顯示對基本概念的理解還不夠深入
2. **練習量不足**：總共只答了{total_attempts}題，需要更多練習來鞏固知識
3. **應用能力待提升**：最近準確率{recent_accuracy:.1%}，說明在實際應用中還有困難

### 學習建議
1. **回歸基礎**：重新學習{concept_name}的基本定義和核心概念
2. **循序漸進**：從簡單題目開始，逐步提高難度
3. **大量練習**：建議至少完成10-15題相關練習
4. **尋求幫助**：遇到困難時及時向老師或同學請教

### 下一步行動
建議您立即開始練習，從基礎概念題開始，逐步提升到應用題，並在學習過程中注意總結錯誤類型，避免重複犯錯。
''')
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"解析Gemini響應失敗: {e}")
            logger.error(f"原始響應: {ai_response[:2000] if len(ai_response) > 2000 else ai_response}")
            # 返回默認診斷結果
            return {
                'summary': f'{concept_name}掌握度{mastery:.1%}，需重點關注',
                'metrics': {
                    'domain': domain_name,
                    'concept': concept_name,
                    'mastery': mastery,
                    'attempts': total_attempts,
                    'recent_accuracy': recent_accuracy
                },
                'root_causes': ['基礎概念不牢固', '練習不足'],
                'top_actions': [
                    {"action": "REVIEW_BASICS", "detail": "AI導師進行基礎概念教學", "est_min": 15},
                    {"action": "PRACTICE", "detail": "AI生成相關練習題進行練習", "est_min": 20},
                    {"action": "SEEK_HELP", "detail": "觀看相關教材內容", "est_min": 10}
                ],
                'practice_examples': [],
                'knowledge_relations': {
                    'has_relations': knowledge_relations.get('has_relations', False) if knowledge_relations else False,
                    'prerequisites': relations_detail.get('prerequisites', []) if relations_detail else [],
                    'related_concepts': relations_detail.get('related', []) if relations_detail else [],
                    'leads_to': relations_detail.get('leads_to', []) if relations_detail else [],
                    'relation_graph': relations_detail.get('relation_graph', {}) if relations_detail else {},
                    'total_relations': relations_detail.get('total_relations', 0) if relations_detail else 0
                },
                'evidence': [f'答題{total_attempts}次', f'正確率{recent_accuracy:.1%}'],
                'confidence': 'low',
                'learning_path': learning_path or [],
                'full_text': f'你在「{concept_name}」這個概念上還需要多加強。目前掌握度{mastery:.1%}，答題正確率{recent_accuracy:.1%}。建議你先透過AI導師重新學習基本概念，然後多做一些練習題來鞏固。'
            }
    except Exception as e:
        logger.error(f"AI診斷失敗: {e}", exc_info=True)
        # 返回默認診斷結果
        return {
            'summary': f'{concept_name}掌握度{mastery:.1%}，需重點關注',
            'metrics': {
                'domain': domain_name,
                'concept': concept_name,
                'mastery': mastery,
                'attempts': total_attempts,
                'recent_accuracy': recent_accuracy
            },
            'root_causes': ['基礎概念不牢固', '練習不足'],
            'top_actions': [
                {"action": "REVIEW_BASICS", "detail": "AI導師進行基礎概念教學", "est_min": 15},
                {"action": "PRACTICE", "detail": "AI生成相關練習題進行練習", "est_min": 20},
                {"action": "SEEK_HELP", "detail": "觀看相關教材內容", "est_min": 10}
            ],
            'practice_examples': [],
            'knowledge_relations': {
                'has_relations': knowledge_relations.get('has_relations', False) if knowledge_relations else False,
                'prerequisites': relations_detail.get('prerequisites', []) if relations_detail else [],
                'related_concepts': relations_detail.get('related', []) if relations_detail else [],
                'leads_to': relations_detail.get('leads_to', []) if relations_detail else [],
                'relation_graph': relations_detail.get('relation_graph', {}) if relations_detail else {},
                'total_relations': relations_detail.get('total_relations', 0) if relations_detail else 0
            },
            'evidence': [f'答題{total_attempts}次', f'正確率{recent_accuracy:.1%}'],
            'confidence': 'low',
            'learning_path': learning_path or [],
            'full_text': f'你在「{concept_name}」這個概念上還需要多加強。目前掌握度{mastery:.1%}，答題正確率{recent_accuracy:.1%}。建議你先透過AI導師重新學習基本概念，然後多做一些練習題來鞏固。'
        }

def generate_attention_items(domains: List[Dict], quiz_records: List[Dict]) -> List[Dict]:
    """生成需要關注的知識點數據 - 基於答題記錄分析退步情況"""
    attention_items = []
    
    # 按領域分組分析
    domain_records = {}
    for record in quiz_records:
        domain_name = record.get('domain_name', '未知領域')
        if domain_name not in domain_records:
            domain_records[domain_name] = []
        domain_records[domain_name].append(record)
    
    # 為每個領域分析退步情況
    for domain_name, records in domain_records.items():
        # 跳過「未知領域」
        if domain_name == '未知領域' or domain_name == '未知' or not domain_name or domain_name.strip() == '':
            continue
        if len(records) < 3:
            continue
            
        # 按時間排序
        records.sort(key=lambda x: x['attempt_time'])
        
        # 計算最近和之前的正確率
        mid_point = len(records) // 2
        recent_records = records[:mid_point]  # 前半部分
        older_records = records[mid_point:]   # 後半部分
        
        if len(older_records) == 0:
            continue
            
        recent_accuracy = sum(1 for r in recent_records if r['is_correct']) / len(recent_records)
        older_accuracy = sum(1 for r in older_records if r['is_correct']) / len(older_records)
        
        decline = (older_accuracy - recent_accuracy) * 100
        
        # 降低退步要求，只要有退步就顯示
        if decline > 0:  # 只要有退步就顯示
            # 計算總掌握度
            total_questions = len(records)
            correct_questions = sum(1 for r in records if r['is_correct'])
            mastery = correct_questions / total_questions if total_questions > 0 else 0
            
            attention_items.append({
                'name': domain_name,
                'mastery': round(mastery, 3),  # 統一使用mastery
                'decline': round(decline, 1),
                'priority': 'high' if decline > 20 else 'medium' if decline > 10 else 'low',
                'current_accuracy': round(mastery * 100, 1),  # 使用mastery而不是recent_accuracy
                'previous_accuracy': round((mastery + decline/100) * 100, 1),  # 基於mastery計算
                'questions': total_questions,
                'ai_strategy': f'掌握度僅{round(mastery * 100, 1)}%，建議加強練習'  # 統一使用mastery
            })
    
    # 按退步幅度排序
    attention_items.sort(key=lambda x: x['decline'], reverse=True)
    return attention_items[:5]  # 返回前5個

def generate_progress_tracking(quiz_records: List[Dict]) -> List[Dict]:
    """生成進度追蹤數據"""
    if not quiz_records:
        return []
    
    # 計算各種進度指標
    total_questions = len(quiz_records)
    correct_questions = sum(1 for r in quiz_records if r['is_correct'])
    accuracy = (correct_questions / total_questions * 100) if total_questions > 0 else 0
    
    # 計算學習天數
    learning_days = len(set(r['attempt_time'][:10] for r in quiz_records))
    
    # 計算連續學習天數
    consecutive_days = calculate_consecutive_days(quiz_records)
    
    progress_tracking = [
        {
            'title': '答題準確率',
            'percentage': round(accuracy, 1),
            'target': 80,
            'color': 'success' if accuracy >= 80 else 'warning' if accuracy >= 60 else 'danger'
        },
        {
            'title': '學習天數',
            'percentage': min(100, round(learning_days / 30 * 100, 1)),
            'target': 30,
            'color': 'info'
        },
        {
            'title': '連續學習',
            'percentage': min(100, round(consecutive_days / 7 * 100, 1)),
            'target': 7,
            'color': 'primary'
        }
    ]
    
    return progress_tracking

def generate_radar_data(domains: List[Dict], quiz_records: List[Dict]) -> Dict:
    """生成雷達圖數據"""
    if not domains:
        return {
            'labels': [],
            'data': []
        }
    
    labels = []
    mastery_data = []
    
    for domain in domains:
        domain_name = domain.get('name', '未知領域')
        mastery = domain.get('mastery', 0) * 100  # 轉換為百分比
        
        labels.append(domain_name)
        mastery_data.append(round(mastery, 1))
    
    return {
        'labels': labels,
        'data': mastery_data
    }

# AI教練分析現在使用Redis快取服務
