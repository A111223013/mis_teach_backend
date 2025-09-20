#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
學習成效分析模組 - 配合前端學習分析儀表板
提供完整的學習分析API，支援AI診斷、練習生成、學習計劃等功能
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from flask import Blueprint, jsonify, request
from accessories import refresh_token, mongo, sqldb
from bson import ObjectId
import json
from sqlalchemy import text
# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 創建藍圖
analytics_bp = Blueprint('learning_analytics', __name__, url_prefix='/api/learning-analytics')

# ==================== 核心數據獲取函數 ====================

def get_student_quiz_records(student_identifier: str, limit: int = 1000) -> List[Dict]:
    """從MySQL獲取學生答題紀錄"""
    try:
        if not sqldb:
            logger.error("SQL 數據庫連接未初始化")
            return []
        
        # 判斷是 user_id 還是 user_email
        if '@' in student_identifier:
            where_clause = "qa.user_email = :identifier"
        else:
            # 是 user_id，需要先從 MongoDB 獲取 email
            try:
                user = mongo.db.user.find_one({'_id': ObjectId(student_identifier)})
                if not user:
                    logger.error(f"找不到用戶: {student_identifier}")
                    return []
                student_identifier = user.get('email', '')
                where_clause = "qa.user_email = :identifier"
            except Exception as e:
                logger.error(f"獲取用戶email失敗: {e}")
                return []
        
        # 查詢學生答題紀錄

        query = text(f"""
        SELECT 
            qa.answer_id as id, qa.user_email, qa.mongodb_question_id as question_id, 
            qa.user_answer, qa.is_correct, qa.created_at as attempt_time,
            qa.answer_time_seconds as time_spent, 'medium' as difficulty_level,
            'unknown' as micro_concept_id, 'unknown' as domain_id, 'unknown' as block_id,
            'Question from MongoDB' as question_text, 'N/A' as correct_answer, 'N/A' as explanation
        FROM quiz_answers qa
        WHERE {where_clause}
        ORDER BY qa.created_at DESC
        LIMIT :limit
        """)
        
        result = sqldb.session.execute(query, {
            'identifier': student_identifier,
            'limit': limit
        })
        
        records = []
        for row in result:
            # 從MongoDB獲取題目詳細信息
            question_doc = mongo.db.exam.find_one({'_id': ObjectId(row.question_id)})
            
            if question_doc:
                # 從題目文檔中提取知識點信息
                micro_concept_id = question_doc.get('micro_concept', 'unknown')
                domain_id = question_doc.get('domain', 'unknown')
                block_id = question_doc.get('block', 'unknown')
                question_text = question_doc.get('question_text', 'Question from MongoDB')
                correct_answer = question_doc.get('correct_answer', 'N/A')
                explanation = question_doc.get('explanation', 'N/A')
                difficulty_level = question_doc.get('difficulty', 'medium')
            else:
                # 如果找不到題目，使用默認值
                micro_concept_id = 'unknown'
                domain_id = 'unknown'
                block_id = 'unknown'
                question_text = 'Question from MongoDB'
                correct_answer = 'N/A'
                explanation = 'N/A'
                difficulty_level = 'medium'
            
            records.append({
                'id': row.id,
                'user_email': row.user_email,
                'question_id': row.question_id,
                'user_answer': row.user_answer,
                'is_correct': bool(row.is_correct),
                'attempt_time': row.attempt_time.isoformat() if row.attempt_time else None,
                'time_spent': row.time_spent,
                'difficulty_level': difficulty_level,
                'micro_concept_id': micro_concept_id,
                'domain_id': domain_id,
                'block_id': block_id,
                'question_text': question_text,
                'correct_answer': correct_answer,
                'explanation': explanation
            })
        
        logger.info(f"獲取到 {len(records)} 條答題紀錄")
        return records
        
    except Exception as e:
        logger.error(f"獲取學生答題紀錄失敗: {e}")
        return []

def get_knowledge_structure() -> Dict[str, Any]:
    """獲取知識結構"""
    try:
        # 從MongoDB獲取知識結構
        domains = list(mongo.db.domain.find())
        blocks = list(mongo.db.block.find())
        concepts = list(mongo.db.micro_concept.find())
        
        return {
            'domains': domains,
            'blocks': blocks,
            'concepts': concepts
        }
    except Exception as e:
        logger.error(f"獲取知識結構失敗: {e}")
        return {'domains': [], 'blocks': [], 'concepts': []}

# ==================== 學習分析計算函數 ====================

def calculate_learning_metrics(quiz_records: List[Dict]) -> Dict[str, Any]:
    """計算學習效率指標"""
    if not quiz_records:
        return {
            'learning_velocity': 0,
            'retention_rate': 0,
            'avg_time_per_concept': 0,
            'focus_score': 0
        }
    
    # 學習速度：每日新增掌握概念數
    concept_mastery = defaultdict(list)
    for record in quiz_records:
        if record['is_correct']:
            concept_id = record['micro_concept_id']
            attempt_time = datetime.fromisoformat(record['attempt_time'].replace('Z', '+00:00'))
            concept_mastery[concept_id].append(attempt_time)
    
    # 計算每日掌握的新概念數
    daily_concepts = defaultdict(set)
    for concept_id, times in concept_mastery.items():
        for time in times:
            date_key = time.date()
            daily_concepts[date_key].add(concept_id)
    
    # 學習速度 = 平均每日掌握概念數
    if daily_concepts:
        learning_velocity = sum(len(concepts) for concepts in daily_concepts.values()) / len(daily_concepts)
    else:
        learning_velocity = 0
    
    # 保持率：7天後重複答題的正確率
    retention_data = []
    for record in quiz_records:
        attempt_time = datetime.fromisoformat(record['attempt_time'].replace('Z', '+00:00'))
        # 查找7天後的同概念答題
        later_time = attempt_time + timedelta(days=7)
        for later_record in quiz_records:
            if (later_record['micro_concept_id'] == record['micro_concept_id'] and
                later_record['user_email'] == record['user_email'] and
                datetime.fromisoformat(later_record['attempt_time'].replace('Z', '+00:00')) >= later_time):
                retention_data.append(later_record['is_correct'])
                break
    
    retention_rate = sum(retention_data) / len(retention_data) * 100 if retention_data else 0
    
    # 平均掌握時間：每個概念從第一次答題到掌握的時間
    concept_times = {}
    for record in quiz_records:
        concept_id = record['micro_concept_id']
        attempt_time = datetime.fromisoformat(record['attempt_time'].replace('Z', '+00:00'))
        
        if concept_id not in concept_times:
            concept_times[concept_id] = {'first': attempt_time, 'mastered': None}
        
        if record['is_correct'] and concept_times[concept_id]['mastered'] is None:
            concept_times[concept_id]['mastered'] = attempt_time
    
    mastered_times = []
    for times in concept_times.values():
        if times['mastered']:
            diff = times['mastered'] - times['first']
            mastered_times.append(diff.total_seconds() / 60)  # 轉換為分鐘
    
    avg_time_per_concept = sum(mastered_times) / len(mastered_times) if mastered_times else 0
    
    # 專注度：基於答題間隔和切換頻率
    if len(quiz_records) > 1:
        time_intervals = []
        concept_switches = 0
        prev_concept = None
        
        sorted_records = sorted(quiz_records, key=lambda x: x['attempt_time'])
        for i, record in enumerate(sorted_records[1:], 1):
            prev_record = sorted_records[i-1]
            prev_time = datetime.fromisoformat(prev_record['attempt_time'].replace('Z', '+00:00'))
            curr_time = datetime.fromisoformat(record['attempt_time'].replace('Z', '+00:00'))
            
            interval = (curr_time - prev_time).total_seconds() / 60  # 分鐘
            time_intervals.append(interval)
            
            if prev_concept and prev_concept != record['micro_concept_id']:
                concept_switches += 1
            prev_concept = record['micro_concept_id']
        
        # 專注度 = 100 - (間隔標準差 + 切換頻率) * 調整係數
        if time_intervals:
            import statistics
            interval_std = statistics.stdev(time_intervals) if len(time_intervals) > 1 else 0
            switch_rate = concept_switches / len(quiz_records) * 100
            focus_score = max(0, 100 - (interval_std * 0.1 + switch_rate * 0.5))
        else:
            focus_score = 100
    else:
        focus_score = 100
        
        return {
        'learning_velocity': round(learning_velocity, 1),
        'retention_rate': round(retention_rate, 1),
        'avg_time_per_concept': round(avg_time_per_concept, 1),
        'focus_score': round(focus_score, 1)
    }

def calculate_concept_mastery(quiz_records: List[Dict], concept_id: str) -> Dict[str, Any]:
    """計算特定概念的掌握度"""
    concept_records = [r for r in quiz_records if r['micro_concept_id'] == concept_id]
    
    if not concept_records:
        return {
            'mastery': 0,
            'attempts': 0,
            'correct': 0,
            'wrong_count': 0,
            'recent_accuracy': 0,
            'trend': 'stable'
        }
    
    total_attempts = len(concept_records)
    correct_attempts = sum(1 for r in concept_records if r['is_correct'])
    wrong_count = total_attempts - correct_attempts
    mastery = correct_attempts / total_attempts if total_attempts > 0 else 0
    
    # 最近5次答題的正確率
    recent_records = concept_records[:5]
    recent_correct = sum(1 for r in recent_records if r['is_correct'])
    recent_accuracy = recent_correct / len(recent_records) if recent_records else 0
    
    # 趨勢分析
    if len(concept_records) >= 3:
        first_half = concept_records[-3:]
        second_half = concept_records[:3] if len(concept_records) >= 6 else concept_records[:len(concept_records)//2]
        
        first_accuracy = sum(1 for r in first_half if r['is_correct']) / len(first_half)
        second_accuracy = sum(1 for r in second_half if r['is_correct']) / len(second_half)
        
        if second_accuracy - first_accuracy > 0.1:
            trend = 'improving'
        elif first_accuracy - second_accuracy > 0.1:
            trend = 'declining'
        else:
            trend = 'stable'
    else:
        trend = 'stable'
    
    return {
        'mastery': round(mastery, 2),
        'attempts': total_attempts,
        'correct': correct_attempts,
        'wrong_count': wrong_count,
        'recent_accuracy': round(recent_accuracy, 2),
        'trend': trend
    }

def generate_ai_diagnosis(concept_id: str, quiz_records: List[Dict], knowledge_structure: Dict) -> Dict[str, Any]:
    """生成AI診斷數據"""
    concept_records = [r for r in quiz_records if r['micro_concept_id'] == concept_id]
    
    if not concept_records:
        return {
            'concept_name': '未知概念',
            'diagnosis': '沒有足夠的答題數據進行分析',
            'root_cause': '請先完成相關練習題',
            'learning_path': [],
            'practice_questions': [],
            'evidence': [],
            'confidence': 0,
            'confidence_score': {'history': 0, 'pattern': 0, 'knowledge': 0},
            'error_analysis': [],
            'knowledge_relations': [],
            'practice_progress': {'completed': 0, 'total': 0, 'accuracy': 0}
        }
    
    # 獲取概念名稱
    concept_name = '未知概念'
    for concept in knowledge_structure.get('concepts', []):
        # 比較ObjectId和字符串
        if str(concept.get('_id')) == concept_id or concept.get('_id') == ObjectId(concept_id):
            concept_name = concept.get('name', '未知概念')
            break
    
    # 計算掌握度
    mastery_data = calculate_concept_mastery(quiz_records, concept_id)
    
    # 生成診斷
    if mastery_data['mastery'] >= 0.8:
        diagnosis = f"您在{concept_name}方面表現優秀，掌握度達到{mastery_data['mastery']*100:.1f}%"
        root_cause = "建議繼續保持並挑戰更高難度的相關題目"
        priority = 'maintain'
    elif mastery_data['mastery'] >= 0.6:
        diagnosis = f"您在{concept_name}方面表現良好，掌握度為{mastery_data['mastery']*100:.1f}%，仍有進步空間"
        root_cause = "建議加強練習以提升掌握度"
        priority = 'enhance'
    else:
        diagnosis = f"您在{concept_name}方面需要加強，掌握度僅為{mastery_data['mastery']*100:.1f}%"
        root_cause = "建議從基礎概念開始，逐步提升"
        priority = 'urgent'
    
    # 生成學習路徑
    learning_path = [
        f"1. 複習{concept_name}的基礎概念",
        f"2. 練習相關的基礎題目",
        f"3. 逐步提升題目難度",
        f"4. 進行綜合性練習",
        f"5. 定期複習鞏固"
    ]
    
    # 生成練習題建議
    practice_questions = [
        {
            'id': f'Q1_{concept_id}',
            'title': f'{concept_name}基礎練習',
            'difficulty': 'easy',
            'estimated_time': 10,
            'accuracy': 0.85,
            'completed': False
        },
        {
            'id': f'Q2_{concept_id}',
            'title': f'{concept_name}進階練習',
            'difficulty': 'medium',
            'estimated_time': 15,
            'accuracy': 0.65,
            'completed': False
        },
        {
            'id': f'Q3_{concept_id}',
            'title': f'{concept_name}綜合練習',
            'difficulty': 'hard',
            'estimated_time': 25,
            'accuracy': 0.45,
            'completed': False
        }
    ]
    
    # 生成證據
    evidence = [
        f"總共答題{mastery_data['attempts']}次，正確{mastery_data['correct']}次",
        f"最近答題正確率為{mastery_data['recent_accuracy']*100:.1f}%",
        f"學習趨勢：{mastery_data['trend']}"
    ]
    
    # 錯誤分析
    error_analysis = []
    if mastery_data['wrong_count'] > 0:
        error_analysis = [
            {'type': '概念理解錯誤', 'count': mastery_data['wrong_count'] // 2, 'percentage': 50},
            {'type': '計算錯誤', 'count': mastery_data['wrong_count'] // 3, 'percentage': 33},
            {'type': '粗心錯誤', 'count': mastery_data['wrong_count'] - mastery_data['wrong_count'] // 2 - mastery_data['wrong_count'] // 3, 'percentage': 17}
        ]
    
    # 知識關聯
    knowledge_relations = [
        {'name': '前置知識', 'type': 'prerequisite', 'mastery': 0.8},
        {'name': '相關概念', 'type': 'related', 'mastery': 0.6},
        {'name': '後續應用', 'type': 'application', 'mastery': 0.4}
    ]
        
    return {
        'concept_name': concept_name,
        'diagnosis': diagnosis,
        'root_cause': root_cause,
        'learning_path': learning_path,
        'practice_questions': practice_questions,
        'evidence': evidence,
        'confidence': round(mastery_data['mastery'], 2),
        'confidence_score': {
            'history': round(mastery_data['mastery'] * 100, 1),
            'pattern': round(mastery_data['recent_accuracy'] * 100, 1),
            'knowledge': round(mastery_data['mastery'] * 100, 1)
        },
        'error_analysis': error_analysis,
        'knowledge_relations': knowledge_relations,
        'practice_progress': {
            'completed': 0,
            'total': len(practice_questions),
            'accuracy': mastery_data['recent_accuracy']
        }
    }

# ==================== API 端點 ====================

@analytics_bp.route('/overview', methods=['POST', 'OPTIONS'])
def get_overview():
    """獲取學習分析總覽"""
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        # 獲取認證token
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({
                'success': False,
                'error': '未提供認證token'
            }), 401
        
        token = auth_header.split(" ")[1]
        from src.api import get_user_info
        user_email = get_user_info(token, 'email')
        
        # 根據郵箱查找用戶
        user = mongo.db.user.find_one({'email': user_email})
        if not user:
            return jsonify({
                'success': False,
                'error': '用戶不存在'
            }), 404
        
        # 獲取答題記錄
        quiz_records = get_student_quiz_records(user_email)
        
        # 獲取知識結構
        knowledge_structure = get_knowledge_structure()
        
        # 計算學習效率指標
        learning_metrics = calculate_learning_metrics(quiz_records)
        
        # 計算整體掌握度
        concept_masteries = {}
        for record in quiz_records:
            concept_id = record['micro_concept_id']
            if concept_id not in concept_masteries:
                concept_masteries[concept_id] = calculate_concept_mastery(quiz_records, concept_id)
        
        if concept_masteries:
            overall_mastery = sum(data['mastery'] for data in concept_masteries.values()) / len(concept_masteries)
        else:
            overall_mastery = 0
        
        # 生成領域數據
        domains = []
        for domain in knowledge_structure.get('domains', []):
            domain_id = str(domain['_id'])
            domain_records = [r for r in quiz_records if r['domain_id'] == domain_id]
            
            if domain_records:
                domain_concepts = set(r['micro_concept_id'] for r in domain_records)
                domain_mastery = sum(concept_masteries.get(cid, {}).get('mastery', 0) for cid in domain_concepts) / len(domain_concepts) if domain_concepts else 0
            else:
                domain_mastery = 0
            
            domains.append({
                'domain_id': domain_id,
                'name': domain.get('name', '未知領域'),
                'mastery': round(domain_mastery, 2),
                'concept_count': len(domain_concepts) if domain_records else 0,
                'weak_count': len([cid for cid in domain_concepts if concept_masteries.get(cid, {}).get('mastery', 0) < 0.6]) if domain_records else 0
            })
        
        # 生成弱點列表
        top_weak_points = []
        for concept_id, mastery_data in concept_masteries.items():
            if mastery_data['mastery'] < 0.6:  # 掌握度低於60%視為弱點
                # 獲取概念名稱
                concept_name = '未知概念'
                for concept in knowledge_structure.get('concepts', []):
                    if str(concept['_id']) == concept_id:
                        concept_name = concept.get('name', '未知概念')
                        break
                
                top_weak_points.append({
                    'micro_id': concept_id,
                    'name': concept_name,
                    'mastery': mastery_data['mastery'],
                    'attempts': mastery_data['attempts'],
                    'wrong_count': mastery_data['wrong_count'],
                    'reason': f"掌握度僅{mastery_data['mastery']*100:.1f}%",
                    'priority': 1 - mastery_data['mastery'],  # 優先級與掌握度成反比
                    'expanded': False,
                    'sub_concepts': [],
                    'error_types': []
                })
        
        # 按優先級排序，取前3個
        top_weak_points.sort(key=lambda x: x['priority'], reverse=True)
        top_weak_points = top_weak_points[:3]
        
        # 生成最近進步的知識點
        recent_improvements = []
        for concept_id, mastery_data in concept_masteries.items():
            if mastery_data['trend'] == 'improving' and mastery_data['mastery'] > 0.6:
                # 獲取概念名稱
                concept_name = '未知概念'
                for concept in knowledge_structure.get('concepts', []):
                    if str(concept['_id']) == concept_id:
                        concept_name = concept.get('name', '未知概念')
                        break
                
                recent_improvements.append({
                    'name': concept_name,
                    'improvement': round((mastery_data['recent_accuracy'] - mastery_data['mastery']) * 100, 1),
                    'mastery': round(mastery_data['mastery'] * 100, 1),
                    'priority': 'maintain',
                    'ai_strategy': '保持當前學習節奏'
                })
        
        # 生成需要關注的知識點
        needs_attention = []
        for concept_id, mastery_data in concept_masteries.items():
            if mastery_data['trend'] == 'declining' or mastery_data['mastery'] < 0.4:
                # 獲取概念名稱
                concept_name = '未知概念'
                for concept in knowledge_structure.get('concepts', []):
                    if str(concept['_id']) == concept_id:
                        concept_name = concept.get('name', '未知概念')
                        break
                
                needs_attention.append({
                    'name': concept_name,
                    'decline': round((mastery_data['mastery'] - mastery_data['recent_accuracy']) * 100, 1) if mastery_data['recent_accuracy'] < mastery_data['mastery'] else 0,
                    'mastery': round(mastery_data['mastery'] * 100, 1),
                    'priority': 'urgent',
                    'ai_strategy': '立即進行複習和練習'
                })
        
        # 生成AI建議
        ai_suggestions = []
        if top_weak_points:
            ai_suggestions.append({
                'title': '重點練習建議',
                'description': f'建議優先練習{top_weak_points[0]["name"]}',
                'priority': 'high',
                'action_text': '開始練習',
                'type': 'practice',
                'target': top_weak_points[0]['micro_id'],
                'basis': '基於掌握度分析'
            })
        
        # 生成AI摘要
        ai_summary = {
            'title': 'AI學習分析',
            'content': f'您的整體掌握度為{overall_mastery*100:.1f}%，共有{len(top_weak_points)}個需要加強的知識點。建議專注於弱點練習以提升整體表現。',
            'confidence': 0.85,
            'last_updated': datetime.now().isoformat()
        }
        
        # 生成最近趨勢數據
        recent_trend = []
        for i in range(7):
            date = datetime.now() - timedelta(days=6-i)
            date_str = date.strftime('%Y-%m-%d')
            
            # 計算當天的答題正確率
            day_records = [r for r in quiz_records if r['attempt_time'].startswith(date_str)]
            if day_records:
                accuracy = sum(1 for r in day_records if r['is_correct']) / len(day_records)
                attempts = len(day_records)
            else:
                accuracy = 0
                attempts = 0
            
            recent_trend.append({
                'date': date_str,
                'accuracy': round(accuracy, 2),
                'attempts': attempts
            })
        
        return jsonify({
            'success': True,
            'data': {
                'overall_mastery': round(overall_mastery, 2),
                'class_ranking': 5,  # 暫時硬編碼
                'domains': domains,
                'top_weak_points': top_weak_points,
                'recent_improvements': recent_improvements,
                'needs_attention': needs_attention,
                'ai_suggestions': ai_suggestions,
                'ai_summary': ai_summary,
                'recent_trend': recent_trend,
                'total_attempts': len(quiz_records),
                'weak_points_count': len(top_weak_points),
                'recent_activity': len([r for r in quiz_records if r['attempt_time'].startswith(datetime.now().strftime('%Y-%m-%d'))]),
                **learning_metrics  # 包含學習效率指標
            }
        })
        
    except Exception as e:
        logger.error(f'獲取學習分析總覽失敗: {str(e)}')
        return jsonify({
            'success': False,
            'error': f'獲取學習分析總覽失敗: {str(e)}'
        })

@analytics_bp.route('/domains', methods=['POST', 'OPTIONS'])
def get_domains():
    """獲取領域數據"""
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        # 獲取認證token
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({
                'success': False,
                'error': '未提供認證token'
            }), 401
        
        token = auth_header.split(" ")[1]
        from src.api import get_user_info
        user_email = get_user_info(token, 'email')
        
        # 根據郵箱查找用戶
        user = mongo.db.user.find_one({'email': user_email})
        if not user:
            return jsonify({
                'success': False,
                'error': '用戶不存在'
            }), 404
        
        # 獲取知識結構
        knowledge_structure = get_knowledge_structure()
        
        # 獲取答題記錄
        quiz_records = get_student_quiz_records(user_email)
        
        # 生成領域數據
        domains = []
        for domain in knowledge_structure.get('domains', []):
            domain_id = str(domain['_id'])
            domain_records = [r for r in quiz_records if r['domain_id'] == domain_id]
            
            if domain_records:
                domain_concepts = set(r['micro_concept_id'] for r in domain_records)
                concept_masteries = {}
                for concept_id in domain_concepts:
                    concept_masteries[concept_id] = calculate_concept_mastery(quiz_records, concept_id)
                
                domain_mastery = sum(data['mastery'] for data in concept_masteries.values()) / len(concept_masteries) if concept_masteries else 0
            else:
                domain_mastery = 0
                domain_concepts = set()
            
            domains.append({
                'domain_id': domain_id,
                'name': domain.get('name', '未知領域'),
                'mastery': round(domain_mastery, 2),
                'concept_count': len(domain_concepts),
                'weak_count': len([cid for cid in domain_concepts if concept_masteries.get(cid, {}).get('mastery', 0) < 0.6]) if domain_records else 0
            })
        
        return jsonify({
            'success': True,
            'data': domains
        })
        
    except Exception as e:
        logger.error(f'獲取領域數據失敗: {str(e)}')
        return jsonify({
            'success': False,
            'error': f'獲取領域數據失敗: {str(e)}'
        })

@analytics_bp.route('/blocks/<user_id>/<domain_id>', methods=['GET'])
def get_blocks(user_id: str, domain_id: str):
    """獲取領域下的知識塊"""
    try:
        # 檢查用戶是否存在
        user = mongo.db.user.find_one({'_id': ObjectId(user_id)})
        if not user:
            return jsonify({
                'success': False,
                'error': '用戶不存在'
            })
        
        # 獲取知識結構
        knowledge_structure = get_knowledge_structure()
        
        # 獲取答題記錄
        quiz_records = get_student_quiz_records(user_email)
        
        # 找到指定領域的知識塊
        blocks = []
        for block in knowledge_structure.get('blocks', []):
            if block.get('domain_id') == domain_id:
                block_id = str(block['_id'])
                block_records = [r for r in quiz_records if r['block_id'] == block_id]
                
                if block_records:
                    block_concepts = set(r['micro_concept_id'] for r in block_records)
                    concept_masteries = {}
                    for concept_id in block_concepts:
                        concept_masteries[concept_id] = calculate_concept_mastery(quiz_records, concept_id)
                    
                    block_mastery = sum(data['mastery'] for data in concept_masteries.values()) / len(concept_masteries) if concept_masteries else 0
                else:
                    block_mastery = 0
                    block_concepts = set()
                
                blocks.append({
                    'block_id': block_id,
                    'name': block.get('name', '未知知識塊'),
                    'mastery': round(block_mastery, 2),
                    'micro_count': len(block_concepts),
                    'weak_count': len([cid for cid in block_concepts if concept_masteries.get(cid, {}).get('mastery', 0) < 0.6]) if block_records else 0
                })
        
        return jsonify({
            'success': True,
            'data': blocks
        })
        
    except Exception as e:
        logger.error(f'獲取知識塊失敗: {str(e)}')
        return jsonify({
            'success': False,
            'error': f'獲取知識塊失敗: {str(e)}'
        })

@analytics_bp.route('/concepts/<user_id>/<block_id>', methods=['GET'])
def get_concepts(user_id: str, block_id: str):
    """獲取知識塊下的微知識點"""
    try:
        # 檢查用戶是否存在
        user = mongo.db.user.find_one({'_id': ObjectId(user_id)})
        if not user:
            return jsonify({
                'success': False,
                'error': '用戶不存在'
            })
        
        # 獲取知識結構
        knowledge_structure = get_knowledge_structure()
        
        # 獲取答題記錄
        quiz_records = get_student_quiz_records(user_email)
        
        # 找到指定知識塊的微知識點
        concepts = []
        for concept in knowledge_structure.get('concepts', []):
            if concept.get('block_id') == block_id:
                concept_id = str(concept['_id'])
                mastery_data = calculate_concept_mastery(quiz_records, concept_id)
                
                concepts.append({
                    'micro_id': concept_id,
                    'name': concept.get('name', '未知概念'),
                    'mastery': mastery_data['mastery'],
                    'attempts': mastery_data['attempts'],
                    'correct': mastery_data['correct'],
                    'wrong_count': mastery_data['wrong_count'],
                    'difficulty': concept.get('difficulty', 'medium'),
                    'confidence': mastery_data['mastery']
                })
        
        return jsonify({
            'success': True,
            'data': concepts
        })
        
    except Exception as e:
        logger.error(f'獲取微知識點失敗: {str(e)}')
        return jsonify({
            'success': False,
            'error': f'獲取微知識點失敗: {str(e)}'
        })

@analytics_bp.route('/micro-detail/<user_id>/<micro_id>', methods=['GET'])
def get_micro_detail(user_id: str, micro_id: str):
    """獲取微知識點詳情"""
    try:
        # 檢查用戶是否存在
        user = mongo.db.user.find_one({'_id': ObjectId(user_id)})
        if not user:
            return jsonify({
                'success': False,
                'error': '用戶不存在'
            })
        
        # 獲取答題記錄
        quiz_records = get_student_quiz_records(user_email)
        
        # 計算掌握度
        mastery_data = calculate_concept_mastery(quiz_records, micro_id)
        
        # 獲取概念名稱
        knowledge_structure = get_knowledge_structure()
        concept_name = '未知概念'
        for concept in knowledge_structure.get('concepts', []):
            if str(concept['_id']) == micro_id:
                concept_name = concept.get('name', '未知概念')
                break
        
        return jsonify({
            'success': True,
            'data': {
                'micro_id': micro_id,
                'name': concept_name,
                'mastery': mastery_data['mastery'],
                'attempts': mastery_data['attempts'],
                'correct': mastery_data['correct'],
                'wrong_count': mastery_data['wrong_count'],
                'difficulty': 'medium',
                'confidence': mastery_data['mastery']
            }
        })
            
    except Exception as e:
        logger.error(f'獲取微知識點詳情失敗: {str(e)}')
        return jsonify({
            'success': False,
            'error': f'獲取微知識點詳情失敗: {str(e)}'
        })

@analytics_bp.route('/ai-diagnosis', methods=['POST', 'OPTIONS'])
def get_ai_diagnosis():
    """獲取AI診斷"""
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        # 獲取認證token
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({
                'success': False,
                'error': '未提供認證token'
            }), 401
        
        token = auth_header.split(" ")[1]
        from src.api import get_user_info
        user_email = get_user_info(token, 'email')
        
        data = request.get_json()
        micro_id = data.get('micro_id')
        
        if not micro_id:
            return jsonify({
                'success': False,
                'error': '缺少知識點ID'
            }), 400
        
        # 獲取答題記錄
        quiz_records = get_student_quiz_records(user_email)
        
        # 獲取知識結構
        knowledge_structure = get_knowledge_structure()
        
        # 生成AI診斷
        diagnosis = generate_ai_diagnosis(micro_id, quiz_records, knowledge_structure)

        return jsonify({
            'success': True,
            'data': diagnosis
        })
            
    except Exception as e:
        logger.error(f'獲取AI診斷失敗: {str(e)}')
        return jsonify({
            'success': False,
            'error': f'獲取AI診斷失敗: {str(e)}'
        })

@analytics_bp.route('/practice/generate', methods=['POST'])
def generate_practice():
    """生成練習題"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        micro_id = data.get('micro_id')
        practice_type = data.get('type', 'standard')  # quick, standard, deep
        
        if not user_id or not micro_id:
            return jsonify({
                'success': False,
                'error': '缺少必要參數'
            })
        
        # 檢查用戶是否存在
        user = mongo.db.user.find_one({'_id': ObjectId(user_id)})
        if not user:
            return jsonify({
                'success': False,
                'error': '用戶不存在'
            })
        
        # 獲取知識結構
        knowledge_structure = get_knowledge_structure()
        
        # 獲取概念名稱
        concept_name = '未知概念'
        for concept in knowledge_structure.get('concepts', []):
            if str(concept['_id']) == micro_id:
                concept_name = concept.get('name', '未知概念')
                break
        
        # 根據練習類型生成不同數量的題目
        question_count = {'quick': 5, 'standard': 10, 'deep': 20}.get(practice_type, 10)
        
        # 生成練習題（這裡應該從數據庫獲取真實題目）
        practice_questions = []
        for i in range(question_count):
            practice_questions.append({
                'id': f'practice_{micro_id}_{i+1}',
                'title': f'{concept_name}練習題 {i+1}',
                'difficulty': 'medium',
                'estimated_time': 5,
                'question_text': f'這是關於{concept_name}的練習題 {i+1}',
                'options': ['選項A', '選項B', '選項C', '選項D'],
                'correct_answer': '選項A',
                'explanation': f'這是{concept_name}的解釋'
            })
        
        return jsonify({
            'success': True,
            'data': {
                'practice_id': f'practice_{micro_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
                'concept_name': concept_name,
                'practice_type': practice_type,
                'questions': practice_questions,
                'total_questions': question_count,
                'estimated_time': question_count * 5
            }
        })
            
    except Exception as e:
        logger.error(f'生成練習題失敗: {str(e)}')
        return jsonify({
            'success': False,
            'error': f'生成練習題失敗: {str(e)}'
        })

@analytics_bp.route('/learning-plan', methods=['POST'])
def add_to_learning_plan():
    """加入學習計劃"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        concept_name = data.get('concept_name')
        learning_path = data.get('learning_path', [])
        scheduled_time = data.get('scheduled_time')
        intensity = data.get('intensity', 'medium')
        reminders = data.get('reminders', {})
        
        if not user_id or not concept_name:
            return jsonify({
                'success': False,
                'error': '缺少必要參數'
            })
        
        # 檢查用戶是否存在
        user = mongo.db.user.find_one({'_id': ObjectId(user_id)})
        if not user:
            return jsonify({
                'success': False,
                'error': '用戶不存在'
            })
        
        # 創建學習計劃項目
        learning_plan_item = {
            'user_id': user_id,
            'concept_name': concept_name,
            'learning_path': learning_path,
            'scheduled_time': scheduled_time,
            'intensity': intensity,
            'reminders': reminders,
            'status': 'pending',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        # 保存到數據庫
        result = mongo.db.learning_plans.insert_one(learning_plan_item)
        
        return jsonify({
            'success': True,
            'data': {
                'plan_id': str(result.inserted_id),
                'message': f'已將{concept_name}加入學習計劃'
            }
        })
        
    except Exception as e:
        logger.error(f'加入學習計劃失敗: {str(e)}')
        return jsonify({
            'success': False,
            'error': f'加入學習計劃失敗: {str(e)}'
        })

@analytics_bp.route('/trends', methods=['POST', 'OPTIONS'])
def get_trends():
    """獲取學習趨勢數據"""
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        # 獲取認證token
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({
                'success': False,
                'error': '未提供認證token'
            }), 401
        
        token = auth_header.split(" ")[1]
        from src.api import get_user_info
        user_email = get_user_info(token, 'email')
        
        # 獲取答題記錄
        quiz_records = get_student_quiz_records(user_email)
        
        # 生成趨勢數據
        trend_data = []
        for i in range(30):  # 最近30天
            date = datetime.now() - timedelta(days=29-i)
            date_str = date.strftime('%Y-%m-%d')
            
            # 計算當天的答題正確率
            day_records = [r for r in quiz_records if r['attempt_time'].startswith(date_str)]
            if day_records:
                accuracy = sum(1 for r in day_records if r['is_correct']) / len(day_records)
                attempts = len(day_records)
            else:
                accuracy = 0
                attempts = 0
            
            trend_data.append({
                'date': date_str,
                'accuracy': round(accuracy, 2),
                'attempts': attempts
            })
        
        return jsonify({
            'success': True,
            'data': trend_data
        })
        
    except Exception as e:
        logger.error(f'獲取學習趨勢失敗: {str(e)}')
        return jsonify({
            'success': False,
            'error': f'獲取學習趨勢失敗: {str(e)}'
        })

@analytics_bp.route('/peer-comparison', methods=['POST', 'OPTIONS'])
def get_peer_comparison():
    """獲取同儕比較數據"""
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        # 獲取認證token
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({
                'success': False,
                'error': '未提供認證token'
            }), 401
        
        token = auth_header.split(" ")[1]
        from src.api import get_user_info
        user_email = get_user_info(token, 'email')
        
        # 獲取答題記錄
        quiz_records = get_student_quiz_records(user_email)
        
        # 計算用戶的整體掌握度
        concept_masteries = {}
        for record in quiz_records:
            concept_id = record['micro_concept_id']
            if concept_id not in concept_masteries:
                concept_masteries[concept_id] = calculate_concept_mastery(quiz_records, concept_id)
        
        if concept_masteries:
            user_mastery = sum(data['mastery'] for data in concept_masteries.values()) / len(concept_masteries)
        else:
            user_mastery = 0
        
        # 模擬同儕比較數據
        peer_data = {
            'user_mastery': round(user_mastery, 2),
            'class_average': round(user_mastery + 0.05, 2),  # 模擬班平均
            'class_ranking': 5,  # 模擬排名
            'percentile': 75,  # 模擬百分位數
            'improvement_rate': 0.12,  # 模擬進步率
            'comparison_text': f'您的掌握度為{user_mastery*100:.1f}%，超越班上75%的同學'
        }
        
        return jsonify({
            'success': True,
            'data': peer_data
        })
        
    except Exception as e:
        logger.error(f'獲取同儕比較失敗: {str(e)}')
        return jsonify({
            'success': False,
            'error': f'獲取同儕比較失敗: {str(e)}'
        })

# ==================== 註冊藍圖 ====================

def register_analytics_blueprint(app):
    """註冊學習分析藍圖"""
    app.register_blueprint(analytics_bp)
    logger.info("學習分析藍圖已註冊")
