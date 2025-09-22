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
from accessories import sqldb, mongo, init_gemini
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
                
                quiz_records.append({
                    'id': row.answer_id,
                    'question_id': row.question_id,
                    'attempt_time': row.attempt_time.isoformat() + 'Z',
                    'time_spent': row.time_spent or 0,
                    'is_correct': bool(row.is_correct),
                    'micro_concept_id': micro_concept_id,
                    'domain_name': key_points,  # 使用key-points作為領域名稱
                    'difficulty': question_doc.get('difficulty level', '中等')
                })
        
        logger.info(f"獲取到 {len(quiz_records)} 條答題紀錄")
        return quiz_records
            
    except Exception as e:
        logger.error(f"獲取學生答題紀錄失敗: {str(e)}")
        return []

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
    
    # 學習速度：每天學習的概念數
    concept_days = set()
    for record in quiz_records:
        # 使用 UTC 時區來避免時間比較問題
        from datetime import timezone
        attempt_date = datetime.fromisoformat(record['attempt_time'].replace('Z', '+00:00')).date()
        concept_days.add((attempt_date, record['micro_concept_id']))
    
    total_days = len(set(record['attempt_time'][:10] for record in quiz_records))  # 學習天數
    learning_velocity = len(concept_days) / max(total_days, 1)
    
    # 保持率：基於艾賓浩斯遺忘曲線的記憶保持率
    retention_data = []
    concept_attempts = defaultdict(list)
    
    for record in quiz_records:
        concept_id = record['micro_concept_id']
        # 使用 UTC 時區來避免時間比較問題
        attempt_time = datetime.fromisoformat(record['attempt_time'].replace('Z', '+00:00'))
        concept_attempts[concept_id].append({
            'time': attempt_time,
            'correct': record['is_correct']
        })
    
    for concept_id, attempts in concept_attempts.items():
        if len(attempts) < 2:
            continue
            
        attempts.sort(key=lambda x: x['time'])
        
        for i in range(len(attempts) - 1):
            current = attempts[i]
            next_attempt = attempts[i + 1]
            
            time_diff = (next_attempt['time'] - current['time']).total_seconds() / (24 * 3600)
            
            if 1 <= time_diff <= 30:
                expected_retention = math.exp(-time_diff)
                actual_retention = 1.0 if next_attempt['correct'] else 0.0
                
                if expected_retention > 0:
                    retention_ratio = actual_retention / expected_retention
                    retention_data.append(min(1.0, retention_ratio))
    
    retention_rate = sum(retention_data) / len(retention_data) * 100 if retention_data else 0
    
    # 平均每概念時間
    concept_times = defaultdict(list)
    for record in quiz_records:
        if record.get('time_spent', 0) > 0:
            concept_times[record['micro_concept_id']].append(record['time_spent'])
    
    avg_times = [sum(times) / len(times) for times in concept_times.values() if times]
    avg_time_per_concept = sum(avg_times) / len(avg_times) if avg_times else 0
    
    # 專注度：基於多維度學習行為分析
    focus_indicators = []
    
    if len(quiz_records) > 1:
        sorted_records = sorted(quiz_records, key=lambda x: x['attempt_time'])
        
        # 指標1：答題間隔一致性
        time_intervals = []
        for i in range(1, len(sorted_records)):
            prev_time = datetime.fromisoformat(sorted_records[i-1]['attempt_time'].replace('Z', '+00:00'))
            curr_time = datetime.fromisoformat(sorted_records[i]['attempt_time'].replace('Z', '+00:00'))
            interval = (curr_time - prev_time).total_seconds() / 60  # 分鐘
            time_intervals.append(interval)
        
        if time_intervals:
            import statistics
            mean_interval = sum(time_intervals) / len(time_intervals)
            if mean_interval > 0:
                interval_std = statistics.stdev(time_intervals) if len(time_intervals) > 1 else 0
                interval_cv = interval_std / mean_interval
                interval_consistency = max(0, 1 - interval_cv)
                focus_indicators.append(interval_consistency)
        
        # 指標2：概念切換頻率
        concept_switches = 0
        prev_concept = None
        for record in sorted_records:
            if prev_concept and prev_concept != record['micro_concept_id']:
                concept_switches += 1
            prev_concept = record['micro_concept_id']
        
        switch_rate = concept_switches / len(quiz_records)
        concept_focus = max(0, 1 - switch_rate)
        focus_indicators.append(concept_focus)
        
        # 指標3：答題時間分佈
        answer_times = [r.get('time_spent', 0) for r in quiz_records if r.get('time_spent', 0) > 0]
        if answer_times:
            mean_time = sum(answer_times) / len(answer_times)
            if mean_time > 0:
                time_std = statistics.stdev(answer_times) if len(answer_times) > 1 else 0
                time_cv = time_std / mean_time
                time_consistency = max(0, 1 - time_cv)
                focus_indicators.append(time_consistency)
        
        # 指標4：正確率穩定性
        if len(quiz_records) > 5:
            recent_10 = quiz_records[-10:]
            recent_accuracy = sum(1 for r in recent_10 if r.get('is_correct', False)) / len(recent_10)
            focus_indicators.append(recent_accuracy)
    
    # 綜合專注度分數（限制在0-10範圍內）
    if focus_indicators:
        focus_score = sum(focus_indicators) / len(focus_indicators) * 10  # 改為10分制
    else:
        focus_score = 5  # 默認中等專注度
        
    # 計算整體掌握度
    total_attempts = len(quiz_records)
    correct_attempts = sum(1 for r in quiz_records if r.get('is_correct', False))
    overall_mastery = correct_attempts / total_attempts if total_attempts > 0 else 0
    
    return {
        'learning_velocity': round(learning_velocity, 1),
        'retention_rate': round(retention_rate, 1),
        'avg_time_per_concept': round(avg_time_per_concept, 1),
        'focus_score': round(focus_score, 1),
        'overall_mastery': round(overall_mastery, 2)
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

@analytics_bp.route('/overview', methods=['POST', 'OPTIONS'])
def get_overview():
    if request.method == 'OPTIONS':
        return jsonify({'success': True})
    """獲取學習分析總覽"""
    try:
        # 獲取JWT token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': '缺少認證信息'}), 401
        
        token = auth_header.split(" ")[1]
        logger.info(f"收到的 token: {token[:20]}...")
        

        user_email = get_user_info(token, 'email')
        logger.info(f"解析出的用戶 email: {user_email}")
        
        # 獲取答題記錄
        quiz_records = get_student_quiz_records(user_email)
        
        # 計算學習指標
        learning_metrics = calculate_learning_metrics(quiz_records)
        
        # 計算總體掌握度
        if quiz_records:
            total_attempts = len(quiz_records)
            correct_attempts = sum(1 for r in quiz_records if r['is_correct'])
            overall_mastery = correct_attempts / total_attempts
        else:
            total_attempts = 0
            overall_mastery = 0
        
        # 獲取領域數據
        knowledge_structure = get_knowledge_structure()
        domains = []
        for domain in knowledge_structure.get('domains', []):
            domain_id = str(domain['_id'])
            domain_records = [r for r in quiz_records if r['domain_id'] == domain_id]
            
            if domain_records:
                domain_mastery = sum(1 for r in domain_records if r['is_correct']) / len(domain_records)
            else:
                domain_mastery = 0
            
            domains.append({
                'domain_id': domain_id,
                'name': domain['name'],
                'mastery': round(domain_mastery, 2)
            })
        
        # 獲取弱點數據
        weak_points = []
        concept_stats = defaultdict(lambda: {'total': 0, 'correct': 0})
        
        for record in quiz_records:
            concept_id = record['micro_concept_id']
            concept_stats[concept_id]['total'] += 1
            if record['is_correct']:
                concept_stats[concept_id]['correct'] += 1
        
        for concept_id, stats in concept_stats.items():
            if stats['total'] >= 2:  # 至少答過2題
                mastery = stats['correct'] / stats['total']
                if mastery < 0.6:  # 掌握度低於60%
                    # 找到概念名稱
                    concept_name = "未知概念"
                    for concept in knowledge_structure.get('concepts', []):
                        if str(concept['_id']) == concept_id:
                            concept_name = concept['name']
                            break
                    
                    weak_points.append({
                        'micro_id': concept_id,
                        'name': concept_name,
                        'mastery': round(mastery, 2),
                        'priority': 'high' if mastery < 0.3 else 'medium',
                        'attempts': stats['total'],
                        'wrong_count': stats['total'] - stats['correct'],
                        'reason': '需要加強練習'
                    })
        
        # 按掌握度排序
        weak_points.sort(key=lambda x: x['mastery'])
        
        overview = {
            'overall_mastery': round(overall_mastery, 2),
            'domains': domains,
            'top_weak_points': weak_points[:5],
            'recent_trend': [],
            'total_attempts': total_attempts,
            'weak_points_count': len(weak_points),
            'recent_activity': 0,
            'class_ranking': 0,
            'recent_improvements': [],
            'needs_attention': weak_points[:3],
            'ai_suggestions': [],
            'ai_summary': {
                'overall_performance': f"整體掌握度 {overall_mastery:.1%}",
                'key_insights': ["需要加強練習", "建議專注於弱點"],
                'recommendations': ["多做練習題", "複習基礎概念"]
            },
            **learning_metrics
        }
        
        return jsonify({
            'success': True,
            'data': overview
        })
        
    except Exception as e:
        logger.error(f'獲取總覽失敗: {str(e)}')
        return jsonify({
            'success': False,
            'error': f'獲取總覽失敗: {str(e)}'
        })

# 其他 API 端點...
@analytics_bp.route('/ai-diagnosis', methods=['POST', 'OPTIONS'])
def ai_diagnosis():
    """AI診斷特定知識點"""
    if request.method == 'OPTIONS':
        return jsonify({'success': True})
    
    try:
        data = request.get_json()
        print(f"AI診斷請求數據: {data}")
        
        concept_id = data.get('concept_id')
        concept_name = data.get('concept_name', '未知概念')
        domain_name = data.get('domain_name', '未知領域')
        
        print(f"解析的參數 - concept_id: {concept_id}, concept_name: {concept_name}, domain_name: {domain_name}")
        
        if not concept_id:
            print("錯誤: 缺少概念ID")
            return jsonify({'error': '缺少概念ID'}), 400
        
        # 獲取用戶信息
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': '缺少認證信息'}), 401
        
        token = auth_header.split(' ')[1]
        user_email = get_user_info(token, 'email')
        
        if not user_email:
            return jsonify({'error': '無法獲取用戶信息'}), 401
        
        # 獲取該概念的答題記錄
        quiz_records = get_student_quiz_records(user_email)
        
        # 調試：檢查答題記錄的結構
        print(f"答題記錄樣本（前3條）:")
        for i, record in enumerate(quiz_records[:3]):
            print(f"  記錄{i+1}: micro_concept_id='{record.get('micro_concept_id')}', micro_concept_name='{record.get('micro_concept_name')}'")
        
        # 嘗試用ID和名稱匹配
        # 注意：micro_concept_id字段實際包含的是概念名稱，不是ObjectId
        concept_records = [r for r in quiz_records if 
                          r.get('micro_concept_id') == concept_name or  # 用concept_name匹配micro_concept_id
                          r.get('micro_concept_name') == concept_name or
                          str(r.get('micro_concept_id', '')) == str(concept_id)]  # 也嘗試ObjectId匹配
        
        print(f"找到 {len(concept_records)} 條該概念的答題記錄")
        
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
        
        print(f"難易度統計: {difficulty_stats}")
        
        # 分析錯誤模式
        wrong_records = [r for r in concept_records if not r['is_correct']]
        recent_records = concept_records[:5]  # 最近5次答題
        recent_accuracy = sum(1 for r in recent_records if r['is_correct']) / len(recent_records) if recent_records else 0
        
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
            difficulty_stats=difficulty_stats
        )
        
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
        print(f"從MongoDB獲取到 {len(all_domains)} 個領域")
        
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
        
        print(f"domain_stats統計結果: {domain_stats}")
        
        # 構建領域數據 - 包含所有領域，即使沒有答題記錄
        domains = []
        for domain_doc in all_domains:
            domain_name = domain_doc.get('name', '未知領域')
            domain_id = str(domain_doc.get('_id', ''))
            
            # 嘗試匹配領域名稱（處理括號和英文部分）
            matched_stats = None
            for stats_domain_name, stats in domain_stats.items():
                # 檢查是否包含相同的核心名稱
                if (stats_domain_name in domain_name or 
                    domain_name.split('（')[0] in stats_domain_name or
                    stats_domain_name in domain_name.split('（')[0]):
                    matched_stats = stats
                    print(f"匹配成功: {domain_name} <-> {stats_domain_name}")
                    break
            
            # 如果沒有匹配到，使用默認值
            if matched_stats is None:
                matched_stats = {'total': 0, 'correct': 0, 'wrong': 0}
                print(f"未匹配: {domain_name}")
            
            stats = matched_stats.copy()  # 創建副本避免修改原始數據
            # 確保stats包含所有必要字段
            if 'wrong' not in stats:
                stats['wrong'] = stats['total'] - stats['correct']
            
            if stats['total'] > 0:
                domain_mastery = stats['correct'] / stats['total']
                print(f"領域 {domain_name}: {stats['correct']}/{stats['total']} = {domain_mastery:.3f}")
            else:
                domain_mastery = 0.0  # 沒有答題記錄時設為0
                print(f"領域 {domain_name}: 無答題記錄")
            
            # 從MongoDB獲取該領域下的小知識點（微概念）
            # 需要先通過block找到該領域下的微概念
            domain_id_obj = domain_doc.get('_id')
            
            # 先找到該領域下的所有block
            blocks = list(mongo.db.block.find({'domain_id': domain_id_obj}, {'_id': 1}))
            block_ids = [block['_id'] for block in blocks]
            
            # 再找到這些block下的微概念
            micro_concepts_query = {'block_id': {'$in': block_ids}} if block_ids else {}
            micro_concept_docs = list(mongo.db.micro_concept.find(micro_concepts_query, {'name': 1, '_id': 1, 'block_id': 1}))
            
            print(f"領域 {domain_name} 找到 {len(micro_concept_docs)} 個微概念")
            
            # 統計每個微概念的答題情況
            # 需要匹配簡化的領域名稱
            simplified_domain_name = domain_name.split('（')[0]  # 取括號前的部分
            domain_records = [r for r in quiz_records if r.get('domain_name') == simplified_domain_name]
            print(f"領域 {domain_name} -> 簡化名稱: {simplified_domain_name}, 找到 {len(domain_records)} 條答題記錄")
            micro_concept_stats = {}
            
            for record in domain_records:
                concept_id = record.get('micro_concept_id', '')
                if concept_id and concept_id != 'None':
                    if concept_id not in micro_concept_stats:
                        micro_concept_stats[concept_id] = {'total': 0, 'correct': 0, 'wrong': 0}
                    micro_concept_stats[concept_id]['total'] += 1
                    if record['is_correct']:
                        micro_concept_stats[concept_id]['correct'] += 1
                    else:
                        micro_concept_stats[concept_id]['wrong'] += 1
                
                # 也嘗試用概念名稱匹配
                concept_name = record.get('micro_concept_name', '')
                if concept_name and concept_name != 'None':
                    if concept_name not in micro_concept_stats:
                        micro_concept_stats[concept_name] = {'total': 0, 'correct': 0, 'wrong': 0}
                    micro_concept_stats[concept_name]['total'] += 1
                    if record['is_correct']:
                        micro_concept_stats[concept_name]['correct'] += 1
                    else:
                        micro_concept_stats[concept_name]['wrong'] += 1
            
            print(f"微概念統計結果: {micro_concept_stats}")
            
            # 構建小知識點數據
            concepts = []
            for concept_doc in micro_concept_docs:
                concept_id = str(concept_doc.get('_id', ''))
                concept_name = concept_doc.get('name', f'概念 {concept_id[:8]}')
                
                # 跳過沒有ID的概念
                if not concept_id or concept_id == 'None' or concept_id == '':
                    print(f"跳過無效的概念ID: {concept_doc}")
                    continue
                
                # 獲取該微概念的答題統計
                # 先嘗試用ID匹配，再用名稱匹配
                concept_stats = micro_concept_stats.get(concept_id, micro_concept_stats.get(concept_name, {'total': 0, 'correct': 0, 'wrong': 0}))
                
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
                'expanded': False  # 用於前端展開狀態
            })
        
        # 按掌握度排序
        domains.sort(key=lambda x: x['mastery'], reverse=True)
        
        # 顯示所有知識點（包含小知識點）
        all_knowledge_points = []
        for domain in domains:
            # 判斷狀態：數據不足、需要加強、掌握良好
            print(f"領域狀態判斷: {domain['name']} - questionCount: {domain['questionCount']}, mastery: {domain['mastery']}")
            
            if domain['questionCount'] == 0:
                status = 'no_data'
                status_text = '數據不足'
                print(f"  -> 狀態: 數據不足 (無答題記錄)")
            elif domain['mastery'] < 0.6:
                status = 'weak'
                status_text = '需要加強'
                print(f"  -> 狀態: 需要加強 (有{domain['questionCount']}題，掌握度{domain['mastery']:.1%})")
            else:
                status = 'good'
                status_text = '掌握良好'
                print(f"  -> 狀態: 掌握良好 (掌握度{domain['mastery']:.1%})")
            
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
            'study_intensity': study_intensity
        }
        
        # 生成趨勢數據（使用傳入的天數）
        trends = generate_trend_data(quiz_records, trend_days)
        
        # 生成進步知識點數據
        improvement_items = generate_improvement_items(domains, quiz_records)
        logger.info(f'生成進步知識點數據: {len(improvement_items)} 個')
        
        # 生成需要關注的知識點數據
        attention_items = generate_attention_items(domains, quiz_records)
        logger.info(f'生成關注知識點數據: {len(attention_items)} 個')
        
        # 調試信息
        logger.info(f'領域數據: {len(domains)} 個領域')
        for domain in domains:
            logger.info(f'領域 {domain.get("name", "未知")}: 掌握度 {domain.get("mastery", 0)}%, 題數 {domain.get("questionCount", 0)}')
        
        # 生成進度追蹤數據
        progress_tracking = generate_progress_tracking(quiz_records)
        
        # 生成雷達圖數據
        radar_data = generate_radar_data(domains, quiz_records)
        
        # 構建完整數據
        complete_data = {
            'overview': overview_data,
            'trends': trends,
            'improvement_items': improvement_items,
            'attention_items': attention_items,
            'progress_tracking': progress_tracking,
            'radar_data': radar_data
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
        
        print(f"解析的參數 - concept_name: {concept_name}, domain_name: {domain_name}, difficulty: {difficulty}, user_email: {user_email}")
        
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
        
        print(f"可用API密鑰數量: {len(available_keys)}")
        
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
        
        print(f"🚀 並行任務數量: {len(tasks)}")
        print(f"🎯 目標題目數量: {question_count}")
        print(f"⚡ 並行線程數: {max_workers}")
        print(f"🔑 使用API key數量: {len(used_keys)}")
        
        for i, task in enumerate(tasks):
            print(f"任務{i+1}: {task['api_group']} - {task['question_count']}題")
        
        if len(available_keys) >= question_count:
            print(f"✅ 理想模式：{question_count}個API key，每個生成1題")
        else:
            print(f"⚠️ 資源限制：{len(available_keys)}個API key，平均分配{question_count}題")
        
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
                        print(f"✅ {task['api_group']} 成功生成 {len(questions)} 題，總計: {len(all_questions)} 題")
                    else:
                        print(f"❌ {task['api_group']} 生成失敗: {result.get('error', '未知錯誤')}")
                except Exception as e:
                    print(f"❌ {task['api_group']} 執行異常: {str(e)}")
        
        if not all_questions:
            return {
                'success': False,
                'error': '所有API密鑰都生成失敗'
            }
        
        # 如果題目數量不足，嘗試用剩餘的API key補充
        if len(all_questions) < question_count:
            print(f"題目數量不足，當前: {len(all_questions)}, 需要: {question_count}")
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
    """生成趨勢數據"""
    trends = []
    for i in range(days):
        from datetime import timezone
        date = (datetime.now(timezone.utc) - timedelta(days=days-1-i)).strftime('%Y-%m-%d')
        # 計算該天的掌握度
        day_records = [r for r in quiz_records if r['attempt_time'].startswith(date)]
        if day_records:
            mastery = sum(1 for r in day_records if r['is_correct']) / len(day_records)
        else:
            mastery = 0
        
        trends.append({
            'date': date,
            'mastery': mastery,
            'questions': len(day_records),
            'accuracy': mastery
        })
    
    return trends

@analytics_bp.route('/trends', methods=['POST', 'OPTIONS'])
def get_trends():
    if request.method == 'OPTIONS':
        return jsonify({'success': True})
    """獲取學習趨勢數據"""
    return jsonify({'success': True, 'data': []})

@analytics_bp.route('/peer-comparison', methods=['POST', 'OPTIONS'])
def get_peer_comparison():
    if request.method == 'OPTIONS':
        return jsonify({'success': True})
    """獲取同儕比較數據"""
    return jsonify({'success': True, 'data': {}})

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
    
    # 使用實際記錄的答題時間
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
        
        improvement = (recent_accuracy - older_accuracy) * 100
        
        # 降低進步要求，只要有進步就顯示
        if improvement > 0:  # 只要有進步就顯示
            improvement_items.append({
                'name': domain_name,
                'improvement': round(improvement, 1),
                'priority': 'high' if improvement > 30 else 'medium' if improvement > 10 else 'low',
                'current_accuracy': round(recent_accuracy * 100, 1),
                'previous_accuracy': round(older_accuracy * 100, 1)
            })
    
    # 按進步幅度排序
    improvement_items.sort(key=lambda x: x['improvement'], reverse=True)
    return improvement_items[:5]  # 返回前5個

def get_knowledge_relations_from_neo4j(concept_name: str) -> Dict[str, Any]:
    """從Neo4j獲取知識點關聯數據"""
    try:
        from accessories import neo4j_driver
        
        if not neo4j_driver:
            print("Neo4j驅動未初始化，返回空關聯數據")
            return {
                'prerequisites': [],
                'related_concepts': [],
                'leads_to': []
            }
        
        with neo4j_driver.session() as session:
            # 查詢該概念的關聯知識點 - 使用Section節點類型
            query = """
            MATCH (c:Section {name: $concept_name})-[r:PREREQUISITE|SIMILAR_TO|CROSS_DOMAIN_LINK]-(related:Section)
            RETURN 
                related.name as related_name,
                type(r) as relation_type,
                id(related) as related_id
            LIMIT 10
            """
            
            result = session.run(query, concept_name=concept_name)
            relations = []
            
            print(f"Neo4j查詢結果: concept_name={concept_name}")
            for record in result:
                relation = {
                    'id': str(record['related_id']),  # 使用Neo4j的節點ID
                    'name': record['related_name'],
                    'type': record['relation_type'],
                    'strength': 0.5  # 默認強度
                }
                relations.append(relation)
                print(f"  找到關聯: {relation['name']} ({relation['type']})")
            
            print(f"總共找到 {len(relations)} 個關聯知識點")
            
            return {
                'prerequisites': [r for r in relations if r['type'] == 'PREREQUISITE'],
                'related_concepts': [r for r in relations if r['type'] in ['SIMILAR_TO', 'CROSS_DOMAIN_LINK']],
                'leads_to': [r for r in relations if r['type'] == 'LEADS_TO']
            }
            
    except Exception as e:
        logger.error(f"Neo4j查詢失敗: {e}")
        return {
            'prerequisites': [],
            'related_concepts': [],
            'leads_to': []
        }

def generate_ai_diagnosis(concept_name: str, domain_name: str, mastery: float, 
                         total_attempts: int, correct_attempts: int, recent_accuracy: float,
                         wrong_records: List[Dict], knowledge_relations: Dict[str, Any] = None,
                         difficulty_stats: Dict[str, Dict] = None) -> Dict[str, Any]:
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
        
        # 準備知識點關聯數據
        relations_info = ""
        if knowledge_relations:
            prereqs = knowledge_relations.get('prerequisites', [])
            related = knowledge_relations.get('related_concepts', [])
            leads_to = knowledge_relations.get('leads_to', [])
            
            if prereqs:
                prereq_names = [r['name'] for r in prereqs[:3]]
                relations_info += f"\n- 前置知識點：{', '.join(prereq_names)}"
            
            if related:
                related_names = [r['name'] for r in related[:3]]
                relations_info += f"\n- 相關知識點：{', '.join(related_names)}"
            
            if leads_to:
                leads_names = [r['name'] for r in leads_to[:3]]
                relations_info += f"\n- 後續知識點：{', '.join(leads_names)}"
        
        # 準備難易度分析數據
        difficulty_info = ""
        if difficulty_stats:
            difficulty_info = "\n- 題目難易度分布："
            for difficulty, stats in difficulty_stats.items():
                accuracy = stats['correct'] / stats['total'] if stats['total'] > 0 else 0
                difficulty_info += f"\n  * {difficulty}：{stats['correct']}/{stats['total']} 正確 ({accuracy:.1%})"

        # 構建Gemini提示詞 - 使用新的JSON schema
        import json
        
        prompt = f"""
你是教學診斷AI。只輸出JSON，遵守schema: summary(<=20中文字), metrics, root_causes[], top_actions[<=3], practice_examples[<=3], evidence[], confidence. 如果資料不足設定confidence=low並回傳baseline plan。不要多說話。

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
    "dependency": {json.dumps([{"id": r['id'], "name": r['name'], "mastery": r['strength']} for r in knowledge_relations.get('prerequisites', [])])},
    "difficulty_stats": {json.dumps(difficulty_stats)},
    "relations_info": "{relations_info if relations_info else '無關聯數據'}"
}}

請返回以下格式的JSON，top_actions的action字段必須使用以下標準化類型之一：
- "REVIEW_BASICS" (AI基礎教學)
- "PRACTICE" (AI出題練習) 
- "SEEK_HELP" (教材觀看)
- "ADD_TO_CALENDAR" (加入行事曆)

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
        {{"action": "REVIEW_BASICS", "detail": "AI導師進行基礎概念教學", "est_min": 15}},
        {{"action": "PRACTICE", "detail": "AI生成相關練習題進行練習", "est_min": 20}},
        {{"action": "SEEK_HELP", "detail": "觀看相關教材內容", "est_min": 10}}
    ],
    "practice_examples": [
        {{"q_id": "q101", "difficulty": "easy", "text": "string"}},
        {{"q_id": "q102", "difficulty": "easy", "text": "string"}},
        {{"q_id": "q103", "difficulty": "medium", "text": "string"}}
    ],
    "evidence": ["string1", "string2"],
    "confidence": "high/medium/low",
    "full_text": "string (<=500字)"
}}

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
            
            ai_data = json.loads(ai_response)
            
            # 驗證並返回新的schema格式
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
                'top_actions': ai_data.get('top_actions', [
                    {"action": "複習基礎", "detail": "重新學習基本概念", "est_min": 10},
                    {"action": "做練習", "detail": "完成相關練習題", "est_min": 20},
                    {"action": "尋求幫助", "detail": "重新複習課程", "est_min": 5}
                ]),
                'practice_examples': ai_data.get('practice_examples', [
                    {"q_id": "q101", "difficulty": "easy", "text": "基礎概念題"},
                    {"q_id": "q102", "difficulty": "medium", "text": "應用練習題"}
                ]),
                'evidence': ai_data.get('evidence', [f'答題{total_attempts}次', f'正確率{recent_accuracy:.1%}']),
                'confidence': ai_data.get('confidence', 'medium'),
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
            logger.error(f"原始響應: {ai_response}")
            return _generate_fallback_diagnosis(concept_name, domain_name, mastery, total_attempts, recent_accuracy)
    except Exception as e:
        logger.error(f"Gemini API調用失敗: {e}")
        return _generate_fallback_diagnosis(concept_name, domain_name, mastery, total_attempts, recent_accuracy)

def _generate_fallback_diagnosis(concept_name: str, domain_name: str, mastery: float, 
                                total_attempts: int, recent_accuracy: float) -> Dict[str, Any]:
    """生成fallback診斷 - 當AI診斷失敗時使用"""
    return {
        'summary': f'{concept_name}掌握度{mastery:.1%}，需重點關注',
        'metrics': {
            'domain': domain_name,
            'concept': concept_name,
            'mastery': mastery,
            'attempts': total_attempts,
            'recent_accuracy': recent_accuracy
        },
        'root_causes': ['基礎概念不牢固', '練習不足', '需要更多時間理解'],
        'top_actions': [
            {"action": "REVIEW_BASICS", "detail": "AI導師進行基礎概念教學", "est_min": 15},
            {"action": "PRACTICE", "detail": "AI生成相關練習題進行練習", "est_min": 25},
            {"action": "SEEK_HELP", "detail": "觀看相關教材內容", "est_min": 10}
        ],
        'practice_examples': [
            {"q_id": "q101", "difficulty": "easy", "text": "基礎概念理解題"},
            {"q_id": "q102", "difficulty": "medium", "text": "應用練習題"},
            {"q_id": "q103", "difficulty": "hard", "text": "綜合應用題"}
        ],
        'evidence': [f'答題{total_attempts}次', f'正確率{recent_accuracy:.1%}'],
        'confidence': 'low',
        'full_text': f'''
## 基礎學習建議

### 學習狀況
- **概念名稱**：{concept_name}
- **所屬領域**：{domain_name}
- **掌握度**：{mastery:.1%}
- **答題次數**：{total_attempts}次
- **最近準確率**：{recent_accuracy:.1%}

### 問題分析
由於數據不足或AI服務暫時不可用，提供基礎學習建議：

1. **掌握度偏低**：{mastery:.1%}的掌握度顯示需要加強學習
2. **練習量不足**：僅{total_attempts}次答題，需要更多練習
3. **理解深度不夠**：{recent_accuracy:.1%}的準確率說明概念理解還需深化

### 學習建議
1. **回歸基礎**：重新學習{concept_name}的基本定義和核心概念
2. **循序漸進**：從簡單題目開始，逐步提高難度
3. **大量練習**：建議完成至少10-15題相關練習
4. **尋求幫助**：遇到困難時及時向老師或同學請教

### 下一步行動
建議您立即開始學習，從基礎概念開始，通過大量練習來提升對{concept_name}的理解和掌握。
'''
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
