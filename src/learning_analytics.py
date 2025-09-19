#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
學習成效分析模組 - 模組化函數式版本
MySQL + MongoDB 雙資料庫架構
後端只負責數據分析和計算，不處理UI邏輯
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from collections import defaultdict
from flask import Blueprint, jsonify, request
from accessories import refresh_token, mongo, sqldb
from bson import ObjectId

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== 資料載入模組 ====================

def get_student_quiz_records(student_identifier: str, limit: int = 100) -> List[Dict]:
    """從MySQL獲取學生答題紀錄
    支援 user_id 或 user_email 參數
    """
    try:
        if not sqldb:
            logger.error("SQL 數據庫連接未初始化")
            return []
        
        # 判斷是 user_id 還是 user_email
        if '@' in student_identifier:
            # 是 email
            where_clause = "qa.user_email = :identifier"
        else:
            # 是 user_id，需要先從 MongoDB 獲取 email
            try:
                from bson import ObjectId
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
        query = f"""
        SELECT 
            qa.mongodb_question_id,
            qa.is_correct,
            qa.answer_time_seconds,
            qa.created_at as quiz_date
        FROM quiz_answers qa
        WHERE {where_clause}
        ORDER BY qa.created_at DESC
        LIMIT :limit
        """
        
        result = sqldb.session.execute(sqldb.text(query), {
            'identifier': student_identifier,
            'limit': limit
        }).fetchall()
        
        records = []
        for row in result:
            records.append({
                "mongodb_question_id": row[0],
                "is_correct": bool(row[1]),
                "answer_time_seconds": row[2] or 0,
                "created_at": row[3].isoformat() if row[3] else "2024-01-01T00:00:00Z",
                "quiz_date": row[3].strftime("%Y-%m-%d") if row[3] else "2024-01-01"
            })
        
        logger.info(f"獲取到 {len(records)} 筆學生答題紀錄")
        return records
        
    except Exception as e:
        logger.error(f"獲取學生答題紀錄失敗: {e}")
        return []

def get_knowledge_structure() -> Dict[str, Any]:
    """從MongoDB獲取知識結構"""
    try:
        if not mongo:
            logger.error("MongoDB 連接未初始化")
            return {"domains": [], "blocks": [], "micro_concepts": []}
        
        # 從 MongoDB 獲取真實數據
        domains = list(mongo.db.domain.find())
        blocks = list(mongo.db.block.find())
        micro_concepts = list(mongo.db.micro_concept.find())
        
        # 轉換 ObjectId 為字符串
        def convert_objectid(obj):
            if isinstance(obj, dict):
                if '_id' in obj:
                    obj['_id'] = str(obj['_id'])
                for key, value in obj.items():
                    if isinstance(value, list):
                        obj[key] = [str(item) if isinstance(item, ObjectId) else convert_objectid(item) if isinstance(item, dict) else item for item in value]
                    elif isinstance(value, dict):
                        obj[key] = convert_objectid(value)
                    elif isinstance(value, ObjectId):
                        obj[key] = str(value)
            return obj
        
        domains = [convert_objectid(domain) for domain in domains]
        blocks = [convert_objectid(block) for block in blocks]
        micro_concepts = [convert_objectid(concept) for concept in micro_concepts]
        
        logger.info(f"獲取知識結構: {len(domains)} 個領域, {len(blocks)} 個章節, {len(micro_concepts)} 個概念")
        
        return {
            "domains": domains,
            "blocks": blocks,
            "micro_concepts": micro_concepts
        }
        
    except Exception as e:
        logger.error(f"獲取知識結構失敗: {e}")
        return {"domains": [], "blocks": [], "micro_concepts": []}

def get_questions_by_micro_concept(micro_concept_ids: List[str]) -> List[Dict]:
    """從MongoDB獲取題目，根據小知識點ID"""
    try:
        if not mongo:
            logger.error("MongoDB 連接未初始化")
            return []
        
        # 將字符串ID轉換為ObjectId
        from bson import ObjectId
        object_ids = []
        for concept_id in micro_concept_ids:
            try:
                object_ids.append(ObjectId(concept_id))
            except Exception as e:
                logger.warning(f"無效的 ObjectId: {concept_id}, 錯誤: {e}")
                continue
        
        if not object_ids:
            logger.warning("沒有有效的概念ID")
            return []
        
        # 查詢概念
        micro_concepts = list(mongo.db.micro_concept.find({"_id": {"$in": object_ids}}))
        
        # 轉換 ObjectId 為字符串
        def convert_objectid(obj):
            if isinstance(obj, dict):
                if '_id' in obj:
                    obj['_id'] = str(obj['_id'])
                for key, value in obj.items():
                    if isinstance(value, list):
                        obj[key] = [str(item) if isinstance(item, ObjectId) else convert_objectid(item) if isinstance(item, dict) else item for item in value]
                    elif isinstance(value, dict):
                        obj[key] = convert_objectid(value)
                    elif isinstance(value, ObjectId):
                        obj[key] = str(value)
            return obj
        
        micro_concepts = [convert_objectid(concept) for concept in micro_concepts]
        
        logger.info(f"獲取到 {len(micro_concepts)} 個概念")
        return micro_concepts
        
    except Exception as e:
        logger.error(f"獲取題目失敗: {e}")
        return []

# ==================== 知識分析模組 ====================

def calculate_micro_concept_mastery(student_email: str, micro_concept_id: str) -> Dict[str, Any]:
    """計算學生對特定小知識點的掌握度"""
    try:
        if not mongo:
            logger.error("MongoDB 連接未初始化")
            return {"error": "MongoDB 連接未初始化"}
        
        # 1. 獲取學生答題紀錄
        quiz_records = get_student_quiz_records(student_email)
        
        # 2. 獲取該小知識點信息
        from bson import ObjectId
        try:
            concept_object_id = ObjectId(micro_concept_id)
            concept = mongo.db.micro_concept.find_one({"_id": concept_object_id})
        except Exception as e:
            logger.error(f"無效的概念ID: {micro_concept_id}, 錯誤: {e}")
            return {"error": f"無效的概念ID: {micro_concept_id}"}
        
        if not concept:
            logger.warning(f"找不到概念: {micro_concept_id}")
            return {"error": f"找不到概念: {micro_concept_id}"}
        
        concept_name = concept.get('name', '')
        logger.info(f"計算概念掌握度: {concept_name}")
        
        # 3. 根據概念名稱匹配相關題目
        # 查詢包含該概念名稱的題目
        relevant_question_ids = []
        for record in quiz_records:
            question_id = record["mongodb_question_id"]
            try:
                question_object_id = ObjectId(question_id)
                question = mongo.db.exam.find_one({"_id": question_object_id})
                
                if question:
                    # 處理單選題格式
                    if question.get('type') == 'single':
                        # 檢查 key-points 和 detail-key-point 是否包含概念名稱
                        key_points = question.get('key-points', '')
                        detail_key_point = question.get('detail-key-point', '')
                        
                        # 處理 key-points 可能是字串或陣列的情況
                        if isinstance(key_points, list):
                            key_points = key_points[0] if key_points else ''
                        
                        # 優先使用 detail-key-point，如果沒有則使用 key-points
                        concept_text = detail_key_point if detail_key_point else key_points
                        
                        if concept_name in concept_text or concept_text in concept_name:
                            relevant_question_ids.append(question_id)
                            logger.debug(f"匹配到單選題 {question_id}: {concept_text}")
                    
                    # 處理群組題格式
                    elif question.get('type') == 'group':
                        sub_questions = question.get('sub_questions', [])
                        for sub_question in sub_questions:
                            key_points = sub_question.get('key-points', [])
                            if isinstance(key_points, list):
                                for kp in key_points:
                                    if concept_name in kp or kp in concept_name:
                                        relevant_question_ids.append(question_id)
                                        logger.debug(f"匹配到群組題 {question_id} 子題: {kp}")
                                        break
                        
            except Exception as e:
                logger.warning(f"處理題目 {question_id} 時出錯: {e}")
                continue
        
        # 4. 篩選相關題目的答題紀錄
        relevant_records = [
            record for record in quiz_records 
            if record["mongodb_question_id"] in relevant_question_ids
        ]
        
        if not relevant_records:
            logger.info(f"概念 {concept_name} 沒有相關答題紀錄")
            return {
                "micro_concept_id": micro_concept_id,
                "micro_concept_name": concept_name,
                "mastery_score": None,  # 使用 None 表示數據不足
                "accuracy": None,
                "time_factor": None,
                "total_questions": 0,
                "correct_answers": 0,
                "avg_time": 0,
                "insufficient_data": True
            }
        
        # 5. 計算基礎統計
        total_questions = len(relevant_records)
        correct_answers = sum(1 for r in relevant_records if r["is_correct"])
        accuracy = correct_answers / total_questions
        
        # 6. 計算時間因子（基於認知負荷理論）
        answer_times = [r["answer_time_seconds"] for r in relevant_records]
        avg_time = sum(answer_times) / len(answer_times)
        
        # 理想答題時間範圍：60-120秒
        if avg_time < 60:
            time_factor = max(0, 1 - (60 - avg_time) / 60)  # 太快扣分
        elif avg_time > 120:
            time_factor = max(0, 1 - (avg_time - 120) / 120)  # 太慢扣分
        else:
            time_factor = 1.0  # 理想時間範圍
        
        # 7. 計算掌握度分數 (α=0.7, β=0.3)
        alpha, beta = 0.7, 0.3
        mastery_score = alpha * accuracy + beta * time_factor
        
        logger.info(f"概念 {concept_name} 掌握度計算完成: {total_questions} 題, {correct_answers} 正確, 掌握度 {mastery_score*100:.1f}%")
        
        return {
            "micro_concept_id": micro_concept_id,
            "micro_concept_name": concept_name,
            "mastery_score": round(mastery_score * 100, 2),
            "accuracy": round(accuracy * 100, 2),
            "time_factor": round(time_factor * 100, 2),
            "total_questions": total_questions,
            "correct_answers": correct_answers,
            "avg_time": round(avg_time, 2)
        }
        
    except Exception as e:
        logger.error(f"計算小知識點掌握度失敗: {e}")
        return {"error": str(e)}

def calculate_block_mastery(student_email: str, block_id: str) -> Dict[str, Any]:
    """計算學生對章節的掌握度"""
    try:
        if not mongo:
            logger.error("MongoDB 連接未初始化")
            return {"error": "MongoDB 連接未初始化"}
        
        # 1. 獲取章節信息
        from bson import ObjectId
        try:
            block_object_id = ObjectId(block_id)
            block_info = mongo.db.block.find_one({"_id": block_object_id})
        except Exception as e:
            logger.error(f"無效的章節ID: {block_id}, 錯誤: {e}")
            return {"error": f"無效的章節ID: {block_id}"}
        
        if not block_info:
            logger.warning(f"找不到章節: {block_id}")
            return {"error": f"找不到章節: {block_id}"}
        
        block_name = block_info.get('title', '')
        logger.info(f"計算章節掌握度: {block_name}")
        
        # 2. 獲取該章節下的所有概念
        micro_concepts = list(mongo.db.micro_concept.find({"block_id": block_object_id}))
        
        if not micro_concepts:
            logger.info(f"章節 {block_name} 沒有概念")
            return {
                "block_id": block_id,
                "block_name": block_name,
                "mastery_score": 0,
                "micro_concepts": [],
                "total_micro_concepts": 0,
                "mastered_concepts": 0
            }
        
        # 3. 計算每個概念的掌握度
        micro_masteries = []
        for concept in micro_concepts:
            concept_id = str(concept["_id"])
            mastery = calculate_micro_concept_mastery(student_email, concept_id)
            if "error" not in mastery:
                micro_masteries.append(mastery)
        
        if not micro_masteries:
            logger.info(f"章節 {block_name} 沒有有效的概念掌握度數據")
            return {
                "block_id": block_id,
                "block_name": block_name,
                "mastery_score": None,  # 使用 None 表示數據不足
                "micro_concepts": [],
                "total_micro_concepts": len(micro_concepts),
                "mastered_concepts": 0,
                "insufficient_data": True
            }
        
        # 4. 檢查是否有足夠的數據進行分析
        valid_masteries = [m for m in micro_masteries if m.get("mastery_score") is not None]
        
        if not valid_masteries:
            logger.info(f"章節 {block_name} 所有概念都數據不足")
            return {
                "block_id": block_id,
                "block_name": block_name,
                "mastery_score": None,  # 使用 None 表示數據不足
                "micro_concepts": micro_masteries,
                "total_micro_concepts": len(micro_concepts),
                "mastered_concepts": 0,
                "insufficient_data": True
            }
        
        # 5. 計算章節整體掌握度
        total_mastery = sum(m["mastery_score"] for m in valid_masteries)
        avg_mastery = total_mastery / len(valid_masteries)
        
        logger.info(f"章節 {block_name} 掌握度計算完成: {len(valid_masteries)} 個有效概念, 平均掌握度 {avg_mastery:.1f}%")
        
        return {
            "block_id": block_id,
            "block_name": block_name,
            "mastery_score": round(avg_mastery, 2),
            "micro_concepts": micro_masteries,
            "total_micro_concepts": len(micro_concepts),
            "mastered_concepts": len([m for m in valid_masteries if m["mastery_score"] >= 70]),
            "insufficient_data": False
        }
        
    except Exception as e:
        logger.error(f"計算章節掌握度失敗: {e}")
        return {"error": str(e)}

def calculate_domain_mastery(student_email: str, domain_id: str) -> Dict[str, Any]:
    """計算學生對大知識點的掌握度"""
    try:
        if not mongo:
            logger.error("MongoDB 連接未初始化")
            return {"error": "MongoDB 連接未初始化"}
        
        # 1. 獲取領域信息
        from bson import ObjectId
        try:
            domain_object_id = ObjectId(domain_id)
            domain_info = mongo.db.domain.find_one({"_id": domain_object_id})
        except Exception as e:
            logger.error(f"無效的領域ID: {domain_id}, 錯誤: {e}")
            return {"error": f"無效的領域ID: {domain_id}"}
        
        if not domain_info:
            logger.warning(f"找不到領域: {domain_id}")
            return {"error": f"找不到領域: {domain_id}"}
        
        domain_name = domain_info.get('name', '')
        logger.info(f"計算領域掌握度: {domain_name}")
        
        # 2. 獲取該領域下的所有章節
        blocks = list(mongo.db.block.find({"domain_id": domain_object_id}))
        
        if not blocks:
            logger.info(f"領域 {domain_name} 沒有章節")
            return {
                "domain_id": domain_id,
                "domain_name": domain_name,
                "mastery_score": 0,
                "blocks": [],
                "total_blocks": 0,
                "mastered_blocks": 0
            }
        
        # 3. 計算每個章節的掌握度
        block_masteries = []
        for block in blocks:
            block_id = str(block["_id"])
            mastery = calculate_block_mastery(student_email, block_id)
            if "error" not in mastery:
                block_masteries.append(mastery)
        
        if not block_masteries:
            logger.info(f"領域 {domain_name} 沒有有效的章節掌握度數據")
            return {
                "domain_id": domain_id,
                "domain_name": domain_name,
                "mastery_score": None,  # 使用 None 表示數據不足
                "blocks": [],
                "total_blocks": len(blocks),
                "mastered_blocks": 0,
                "insufficient_data": True
            }
        
        # 4. 檢查是否有足夠的數據進行分析
        valid_blocks = [b for b in block_masteries if b.get("mastery_score") is not None]
        
        if not valid_blocks:
            logger.info(f"領域 {domain_name} 所有章節都數據不足")
            return {
                "domain_id": domain_id,
                "domain_name": domain_name,
                "mastery_score": None,  # 使用 None 表示數據不足
                "blocks": block_masteries,
                "total_blocks": len(blocks),
                "mastered_blocks": 0,
                "insufficient_data": True
            }
        
        # 5. 計算領域整體掌握度
        total_mastery = sum(b["mastery_score"] for b in valid_blocks)
        avg_mastery = total_mastery / len(valid_blocks)
        
        logger.info(f"領域 {domain_name} 掌握度計算完成: {len(valid_blocks)} 個有效章節, 平均掌握度 {avg_mastery:.1f}%")
        
        return {
            "domain_id": domain_id,
            "domain_name": domain_name,
            "mastery_score": round(avg_mastery, 2),
            "blocks": block_masteries,
            "total_blocks": len(blocks),
            "mastered_blocks": len([b for b in valid_blocks if b["mastery_score"] >= 70]),
            "insufficient_data": False
        }
        
    except Exception as e:
        logger.error(f"計算大知識點掌握度失敗: {e}")
        return {"error": str(e)}

# ==================== 依存關係檢查模組 ====================

def check_dependency_issues(student_email: str) -> List[Dict[str, Any]]:
    """檢查知識依存關係問題"""
    try:
        if not mongo:
            logger.error("MongoDB 連接未初始化")
            return []
        
        # 1. 獲取所有概念及其依賴關係
        all_micro_concepts = list(mongo.db.micro_concept.find({}))
        dependency_issues = []
        
        for micro_concept in all_micro_concepts:
            concept_id = str(micro_concept["_id"])
            concept_name = micro_concept.get("name", "")
            dependencies = micro_concept.get("dependencies", [])
            
            if not dependencies:
                continue
            
            # 檢查當前概念掌握度
            current_mastery = calculate_micro_concept_mastery(student_email, concept_id)
            
            if "error" in current_mastery:
                continue
            
            # 檢查前置知識掌握度
            prerequisite_issues = []
            for prereq_id in dependencies:
                prereq_mastery = calculate_micro_concept_mastery(student_email, prereq_id)
                
                if "error" not in prereq_mastery:
                    # 如果前置知識掌握度低於當前知識點，記錄問題
                    if prereq_mastery["mastery_score"] < current_mastery["mastery_score"]:
                        prereq_name = prereq_mastery.get("micro_concept_name", "未知")
                        
                        prerequisite_issues.append({
                            "prerequisite_id": prereq_id,
                            "prerequisite_name": prereq_name,
                            "prerequisite_mastery": prereq_mastery["mastery_score"],
                            "current_mastery": current_mastery["mastery_score"],
                            "gap": current_mastery["mastery_score"] - prereq_mastery["mastery_score"]
                        })
            
            if prerequisite_issues:
                dependency_issues.append({
                    "micro_concept_id": concept_id,
                    "micro_concept_name": concept_name,
                    "issues": prerequisite_issues,
                    "severity": "high" if len(prerequisite_issues) > 1 else "medium"
                })
        
        logger.info(f"檢查到 {len(dependency_issues)} 個依存關係問題")
        return dependency_issues
        
    except Exception as e:
        logger.error(f"檢查依存關係失敗: {e}")
        return []

# ==================== 報告生成模組 ====================

def generate_weakness_report(student_email: str) -> Dict[str, Any]:
    """生成弱點分析報告"""
    try:
        if not mongo:
            logger.error("MongoDB 連接未初始化")
            return {"error": "MongoDB 連接未初始化"}
        
        # 1. 獲取所有概念
        all_micro_concepts = list(mongo.db.micro_concept.find({}))
        micro_masteries = []
        
        # 2. 計算所有小知識點掌握度
        for micro_concept in all_micro_concepts:
            concept_id = str(micro_concept["_id"])
            mastery = calculate_micro_concept_mastery(student_email, concept_id)
            if "error" not in mastery:
                mastery["name"] = mastery.get("micro_concept_name", micro_concept.get("name", ""))
                mastery["block_id"] = str(micro_concept.get("block_id", ""))
                micro_masteries.append(mastery)
        
        # 3. 分類弱點（只包含有足夠數據的概念）
        valid_masteries = [m for m in micro_masteries if m.get("mastery_score") is not None]
        critical_weaknesses = [m for m in valid_masteries if m["mastery_score"] < 40]
        moderate_weaknesses = [m for m in valid_masteries if 40 <= m["mastery_score"] < 60]
        insufficient_data_concepts = [m for m in micro_masteries if m.get("insufficient_data", False)]
        
        # 4. 檢查依存關係問題
        dependency_issues = check_dependency_issues(student_email)
        
        # 5. 生成建議
        recommendations = []
        
        # 高優先級建議：處理依存關係問題
        for issue in dependency_issues:
            for prereq_issue in issue["issues"]:
                recommendations.append({
                    "priority": "high",
                    "action": "複習前置知識",
                    "target": prereq_issue["prerequisite_name"],
                    "reason": f"為學習「{issue['micro_concept_name']}」打基礎",
                    "estimated_time": "30-45分鐘"
                })
        
        # 中優先級建議：處理低掌握度知識點
        for weakness in critical_weaknesses + moderate_weaknesses:
            recommendations.append({
                "priority": "medium" if weakness["mastery_score"] >= 40 else "high",
                "action": "加強練習",
                "target": weakness["name"],
                "reason": f"掌握度偏低 ({weakness['mastery_score']}%)",
                "estimated_time": "45-60分鐘"
            })
        
        logger.info(f"生成弱點報告: {len(micro_masteries)} 個概念, {len(valid_masteries)} 個有效概念, {len(critical_weaknesses)} 個嚴重弱點, {len(moderate_weaknesses)} 個中等弱點, {len(insufficient_data_concepts)} 個數據不足")
        
        return {
            "student_email": student_email,
            "summary": {
                "total_concepts": len(micro_masteries),
                "valid_concepts": len(valid_masteries),
                "critical_weaknesses": len(critical_weaknesses),
                "moderate_weaknesses": len(moderate_weaknesses),
                "insufficient_data": len(insufficient_data_concepts),
                "dependency_issues": len(dependency_issues)
            },
            "weaknesses": {
                "critical": critical_weaknesses,
                "moderate": moderate_weaknesses
            },
            "insufficient_data_concepts": insufficient_data_concepts,
            "dependency_issues": dependency_issues,
            "recommendations": recommendations
        }
        
    except Exception as e:
        logger.error(f"生成弱點報告失敗: {e}")
        return {"error": str(e)}

def generate_knowledge_graph_data(student_email: str) -> Dict[str, Any]:
    """生成知識圖譜數據（供前端渲染）"""
    try:
        if not mongo:
            logger.error("MongoDB 連接未初始化")
            return {"error": "MongoDB 連接未初始化"}
        
        # 1. 獲取知識結構
        domains = list(mongo.db.domain.find({}))
        blocks = list(mongo.db.block.find({}))
        micro_concepts = list(mongo.db.micro_concept.find({}))
        
        # 2. 計算各層級掌握度
        nodes = []
        edges = []
        
        # 添加domain節點
        for domain in domains:
            domain_id = str(domain["_id"])
            domain_mastery = calculate_domain_mastery(student_email, domain_id)
            if "error" not in domain_mastery and domain_mastery.get("mastery_score") is not None:
                nodes.append({
                    "id": domain_id,
                    "label": domain.get("name", ""),
                    "type": "domain",
                    "mastery_score": domain_mastery["mastery_score"],
                    "size": 35
                })
        
        # 添加block節點
        for block in blocks:
            block_id = str(block["_id"])
            block_mastery = calculate_block_mastery(student_email, block_id)
            if "error" not in block_mastery and block_mastery.get("mastery_score") is not None:
                nodes.append({
                    "id": block_id,
                    "label": block.get("title", ""),
                    "type": "block",
                    "mastery_score": block_mastery["mastery_score"],
                    "size": 28
                })
                
                # 連接domain和block
                domain_id = str(block.get("domain_id", ""))
                edges.append({
                    "source": block_id,
                    "target": domain_id,
                    "type": "belongs_to"
                })
        
        # 添加micro_concept節點
        for micro_concept in micro_concepts:
            concept_id = str(micro_concept["_id"])
            micro_mastery = calculate_micro_concept_mastery(student_email, concept_id)
            if "error" not in micro_mastery and micro_mastery.get("mastery_score") is not None:
                nodes.append({
                    "id": concept_id,
                    "label": micro_concept.get("name", ""),
                    "type": "micro_concept",
                    "mastery_score": micro_mastery["mastery_score"],
                    "size": 20
                })
                
                # 連接micro_concept和block
                block_id = str(micro_concept.get("block_id", ""))
                edges.append({
                    "source": concept_id,
                    "target": block_id,
                    "type": "belongs_to"
                })
        
        # 添加依存關係邊
        for micro_concept in micro_concepts:
            dependencies = micro_concept.get("dependencies", [])
            if dependencies:
                concept_id = str(micro_concept["_id"])
                for prereq_id in dependencies:
                    edges.append({
                        "source": concept_id,
                        "target": prereq_id,
                        "type": "depends_on"
                    })
        
        logger.info(f"生成知識圖譜數據: {len(nodes)} 個節點, {len(edges)} 條邊")
        
        return {
            "nodes": nodes,
            "edges": edges
        }
        
    except Exception as e:
        logger.error(f"生成知識圖譜數據失敗: {e}")
        return {"error": str(e)}

# ==================== Flask API 端點 ====================

# 創建藍圖
analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/student-mastery/<student_email>', methods=['GET'])
def get_student_mastery(student_email: str):
    """獲取學生整體掌握度分析"""
    try:
        if not mongo:
            return jsonify({
                "success": False,
                "error": "MongoDB 連接未初始化"
            }), 500
        
        # 1. 獲取所有領域
        domains = list(mongo.db.domain.find({}))
        
        # 2. 計算各層級掌握度
        domain_analyses = []
        for domain in domains:
            domain_id = str(domain["_id"])
            domain_mastery = calculate_domain_mastery(student_email, domain_id)
            if "error" not in domain_mastery:
                domain_analyses.append({
                    "domain_id": domain_id,
                    "domain_name": domain.get("name", ""),
                    "mastery_score": domain_mastery["mastery_score"],
                    "blocks": domain_mastery["blocks"]
                })
        
        # 3. 生成弱點報告
        weakness_report = generate_weakness_report(student_email)
        
        # 4. 生成知識圖譜數據
        knowledge_graph = generate_knowledge_graph_data(student_email)
        
        logger.info(f"學生 {student_email} 掌握度分析完成: {len(domain_analyses)} 個領域")
        
        return jsonify({
            "success": True,
            "data": {
                "student_email": student_email,
                "domain_analyses": domain_analyses,
                "weakness_report": weakness_report,
                "knowledge_graph": knowledge_graph
            }
        })
            
    except Exception as e:
        logger.error(f"獲取學生掌握度分析失敗: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@analytics_bp.route('/weakness-report/<student_email>', methods=['GET'])
def get_weakness_report(student_email: str):
    """獲取學生弱點分析報告"""
    try:
        report = generate_weakness_report(student_email)
        
        if "error" in report:
            return jsonify({
                "success": False,
                "error": report["error"]
            }), 500

        return jsonify({
            "success": True,
            "data": report
        })
            
    except Exception as e:
        logger.error(f"獲取弱點報告失敗: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@analytics_bp.route('/knowledge-graph/<student_email>', methods=['GET'])
def get_knowledge_graph(student_email: str):
    """獲取學生知識圖譜數據"""
    try:
        graph_data = generate_knowledge_graph_data(student_email)
        
        if "error" in graph_data:
            return jsonify({
                "success": False,
                "error": graph_data["error"]
            }), 500

        return jsonify({
            "success": True,
            "data": graph_data
        })
            
    except Exception as e:
        logger.error(f"獲取知識圖譜失敗: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@analytics_bp.route('/micro-concept-mastery/<student_email>/<micro_concept_id>', methods=['GET'])
def get_micro_concept_mastery(student_email: str, micro_concept_id: str):
    """獲取學生對特定小知識點的掌握度"""
    try:
        mastery = calculate_micro_concept_mastery(student_email, micro_concept_id)
        
        if "error" in mastery:
            return jsonify({
                "success": False,
                "error": mastery["error"]
            }), 500

        return jsonify({
            "success": True,
            "data": mastery
        })
        
    except Exception as e:
        logger.error(f"獲取小知識點掌握度失敗: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@analytics_bp.route('/dependency-issues/<student_email>', methods=['GET'])
def get_dependency_issues(student_email: str):
    """獲取學生知識依存關係問題"""
    try:
        issues = check_dependency_issues(student_email)
        
        return jsonify({
            "success": True,
            "data": {
                "student_email": student_email,
                "dependency_issues": issues,
                "total_issues": len(issues)
            }
        })
        
    except Exception as e:
        logger.error(f"獲取依存關係問題失敗: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# ==================== 學生端API ====================

@analytics_bp.route('/api/analytics/overview/<user_id>', methods=['GET'])
def get_analytics_overview(user_id: str):
    """獲取學習分析概覽 - 首屏數據"""
    try:
        from bson import ObjectId
        from datetime import datetime, timedelta
        
        # 檢查用戶是否存在
        user = mongo.db.user.find_one({'_id': ObjectId(user_id)})
        if not user:
            return jsonify({
                'success': False,
                'error': '用戶不存在'
            })
        
        # 獲取學生答題記錄
        quiz_records = get_student_quiz_records(user_id)
        
        # 獲取弱點報告
        weakness_report = generate_weakness_report(user_id)
        
        # 計算整體掌握度
        valid_concepts = [concept for concept in weakness_report.get('concepts', []) 
                         if not concept.get('insufficient_data', False)]
        
        if valid_concepts:
            overall_mastery = sum(concept.get('mastery_score', 0) for concept in valid_concepts) / len(valid_concepts)
        else:
            overall_mastery = 0
        
        # 生成領域數據
        domains = generate_domain_overview(weakness_report)
        
        # 生成Top 3弱點
        top_weak_points = generate_top_weak_points(weakness_report, limit=3)
        
        # 生成最近趨勢
        recent_trend = generate_recent_trend(quiz_records, days=7)
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'overall_mastery': round(overall_mastery, 2),
            'domains': domains,
            'top_weak_points': top_weak_points,
            'recent_trend': recent_trend
        })
        
    except Exception as e:
        logger.error(f'獲取分析概覽失敗: {str(e)}')
        return jsonify({
            'success': False,
            'error': f'獲取分析概覽失敗: {str(e)}'
        })

@analytics_bp.route('/api/analytics/block/<user_id>/<domain_id>', methods=['GET'])
def get_domain_blocks(user_id: str, domain_id: str):
    """獲取領域下的知識塊"""
    try:
        from bson import ObjectId
        
        # 檢查用戶是否存在
        user = mongo.db.user.find_one({'_id': ObjectId(user_id)})
        if not user:
            return jsonify({
                'success': False,
                'error': '用戶不存在'
            })
        
        # 獲取弱點報告
        weakness_report = generate_weakness_report(user_id)
        
        # 生成知識塊數據
        blocks = generate_domain_blocks(weakness_report, domain_id)
        
        return jsonify({
            'success': True,
            'domain_id': domain_id,
            'blocks': blocks
        })
        
    except Exception as e:
        logger.error(f'獲取領域知識塊失敗: {str(e)}')
        return jsonify({
            'success': False,
            'error': f'獲取領域知識塊失敗: {str(e)}'
        })

@analytics_bp.route('/api/analytics/concept/<user_id>/<block_id>', methods=['GET'])
def get_block_concepts(user_id: str, block_id: str):
    """獲取知識塊下的微知識點"""
    try:
        from bson import ObjectId
        
        # 檢查用戶是否存在
        user = mongo.db.user.find_one({'_id': ObjectId(user_id)})
        if not user:
            return jsonify({
                'success': False,
                'error': '用戶不存在'
            })
        
        # 獲取弱點報告
        weakness_report = generate_weakness_report(user_id)
        
        # 生成微知識點數據
        micro_concepts = generate_block_concepts(weakness_report, block_id)
        
        return jsonify({
            'success': True,
            'block_id': block_id,
            'micro_concepts': micro_concepts
        })
        
    except Exception as e:
        logger.error(f'獲取知識塊微知識點失敗: {str(e)}')
        return jsonify({
            'success': False,
            'error': f'獲取知識塊微知識點失敗: {str(e)}'
        })

@analytics_bp.route('/api/analytics/micro/<user_id>/<micro_id>', methods=['GET'])
def get_micro_detail_new(user_id: str, micro_id: str):
    """獲取微知識點詳細信息"""
    try:
        from bson import ObjectId
        from datetime import datetime
        
        # 檢查用戶是否存在
        user = mongo.db.user.find_one({'_id': ObjectId(user_id)})
        if not user:
            return jsonify({
                'success': False,
                'error': '用戶不存在'
            })
        
        # 獲取學生答題記錄
        quiz_records = get_student_quiz_records(user_id)
        
        # 獲取弱點報告
        weakness_report = generate_weakness_report(user_id)
        
        # 生成微知識點詳細數據
        micro_detail = generate_micro_detail(weakness_report, quiz_records, micro_id)
        
        return jsonify({
            'success': True,
            'micro_id': micro_id,
            'detail': micro_detail
        })
        
    except Exception as e:
        logger.error(f'獲取微知識點詳情失敗: {str(e)}')
        return jsonify({
            'success': False,
            'error': f'獲取微知識點詳情失敗: {str(e)}'
        })

@analytics_bp.route('/api/analytics/diagnosis', methods=['POST'])
def generate_ai_diagnosis():
    """生成AI診斷和學習路徑"""
    try:
        from flask import request
        from bson import ObjectId
        
        data = request.get_json()
        user_id = data.get('user_id')
        micro_id = data.get('micro_id')
        mode = data.get('mode', 'standard')
        time_budget = data.get('time_budget', 30)
        
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
        
        # 獲取學生答題記錄
        quiz_records = get_student_quiz_records(user_id)
        
        # 獲取弱點報告
        weakness_report = generate_weakness_report(user_id)
        
        # 生成AI診斷
        diagnosis = generate_ai_diagnosis_data(weakness_report, quiz_records, micro_id, mode, time_budget)
        
        return jsonify({
            'success': True,
            'diagnosis': diagnosis
        })
        
    except Exception as e:
        logger.error(f'生成AI診斷失敗: {str(e)}')
        return jsonify({
            'success': False,
            'error': f'生成AI診斷失敗: {str(e)}'
        })

@analytics_bp.route('/api/student/overview', methods=['GET'])
def get_student_overview():
    """獲取學生學習概覽"""
    try:
        from flask import session, request
        from bson import ObjectId
        from datetime import datetime, timedelta
        
        # 優先從session獲取，如果沒有則從參數獲取，最後使用默認測試用戶
        user_id = session.get('user_id') or request.args.get('user_id')
        
        if not user_id:
            # 使用默認測試用戶
            test_user = mongo.db.user.find_one({'email': 'test@example.com'})
            if test_user:
                user_id = str(test_user['_id'])
            else:
                return jsonify({
                    'success': False,
                    'error': '未找到測試用戶，請先登入',
                    'overview': {
                        'overall_mastery': 0,
                        'weak_points_count': 0,
                        'recent_attempts': 0,
                        'confidence_level': 0,
                        'insufficient_data_concepts': 0
                    }
                })
        
        # 檢查用戶是否存在
        user = mongo.db.user.find_one({'_id': ObjectId(user_id)})
        if not user:
            return jsonify({
                'success': False,
                'error': '用戶不存在',
                'overview': {
                    'overall_mastery': 0,
                    'weak_points_count': 0,
                    'recent_attempts': 0,
                    'confidence_level': 0,
                    'insufficient_data_concepts': 0
                }
            })
        
        # 獲取學生答題記錄
        quiz_records = get_student_quiz_records(user_id)
        
        # 計算基本統計
        total_questions = len(quiz_records)
        correct_answers = sum(1 for record in quiz_records if record.get('is_correct', False))
        accuracy = (correct_answers / total_questions * 100) if total_questions > 0 else 0
        
        # 獲取弱點報告
        weakness_report = generate_weakness_report(user_id)
        
        # 計算整體掌握度（排除數據不足的知識點）
        valid_concepts = [concept for concept in weakness_report.get('concepts', []) 
                         if not concept.get('insufficient_data', False)]
        
        if valid_concepts:
            overall_mastery = sum(concept.get('mastery_score', 0) for concept in valid_concepts) / len(valid_concepts)
        else:
            overall_mastery = 0
        
        # 計算信心度
        confidence_level = min(1.0, total_questions / 20)  # 基於練習次數計算信心度
        
        # 計算最近7天練習次數
        now = datetime.now()
        week_ago = now - timedelta(days=7)
        recent_attempts = len([r for r in quiz_records 
                              if datetime.fromisoformat(r.get('created_at', '').replace('Z', '+00:00')) > week_ago])
        
        # 生成圖表數據
        chart_data = self.generate_all_chart_data(weakness_report, quiz_records)
        
        return jsonify({
            'success': True,
            'overview': {
                'overall_mastery': round(overall_mastery, 1),
                'weak_points_count': len([c for c in weakness_report.get('concepts', []) 
                                        if c.get('mastery_score', 0) < 40 and not c.get('insufficient_data', False)]),
                'recent_attempts': recent_attempts,
                'confidence_level': round(confidence_level, 2),
                'insufficient_data_concepts': len(weakness_report.get('concepts', [])) - len(valid_concepts)
            },
            'chart_data': chart_data,
            'available_domains': self.get_available_domains(weakness_report)
        })
        
    except Exception as e:
        logger.error(f'獲取學習概覽失敗: {str(e)}')
        return jsonify({
            'success': False,
            'error': f'獲取學習概覽失敗: {str(e)}',
            'overview': {
                'overall_mastery': 0,
                'weak_points_count': 0,
                'recent_attempts': 0,
                'confidence_level': 0,
                'insufficient_data_concepts': 0
            }
        })

@analytics_bp.route('/api/student/weaknesses', methods=['GET'])
def get_student_weaknesses():
    """獲取學生弱點分析"""
    try:
        from flask import session, request
        from bson import ObjectId
        
        # 優先從session獲取，如果沒有則從參數獲取，最後使用默認測試用戶
        user_id = session.get('user_id') or request.args.get('user_id')
        
        if not user_id:
            # 使用默認測試用戶
            test_user = mongo.db.user.find_one({'email': 'test@example.com'})
            if test_user:
                user_id = str(test_user['_id'])
            else:
                return jsonify({
                    'success': False,
                    'error': '未找到測試用戶，請先登入',
                    'weaknesses': {
                        'critical': [],
                        'moderate': []
                    }
                })
        
        # 檢查用戶是否存在
        user = mongo.db.user.find_one({'_id': ObjectId(user_id)})
        if not user:
            return jsonify({
                'success': False,
                'error': '用戶不存在',
                'weaknesses': {
                    'critical': [],
                    'moderate': []
                }
            })
        
        # 獲取弱點報告
        weakness_report = generate_weakness_report(user_id)
        
        # 分類弱點
        critical_weaknesses = []
        moderate_weaknesses = []
        
        for concept in weakness_report.get('concepts', []):
            if concept.get('insufficient_data', False):
                continue
                
            mastery_score = concept.get('mastery_score', 0)
            if mastery_score < 40:
                critical_weaknesses.append(concept)
            elif mastery_score < 80:
                moderate_weaknesses.append(concept)
        
        # 按掌握度排序
        critical_weaknesses.sort(key=lambda x: x.get('mastery_score', 0))
        moderate_weaknesses.sort(key=lambda x: x.get('mastery_score', 0))
        
        return jsonify({
            'success': True,
            'weaknesses': {
                'critical': critical_weaknesses[:10],  # 前10個嚴重弱點
                'moderate': moderate_weaknesses[:10],  # 前10個中等弱點
                'total_critical': len(critical_weaknesses),
                'total_moderate': len(moderate_weaknesses)
            }
        })
        
    except Exception as e:
        logger.error(f'獲取弱點分析失敗: {str(e)}')
        return jsonify({
            'success': False,
            'error': f'獲取弱點分析失敗: {str(e)}',
            'weaknesses': {
                'critical': [],
                'moderate': []
            }
        })

@analytics_bp.route('/api/student/micro-detail/<micro_id>', methods=['GET'])
def get_micro_detail(micro_id: str):
    """獲取特定知識點詳細分析"""
    try:
        from flask import session
        from bson import ObjectId
        from datetime import datetime, timedelta
        
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': '未登入'}), 401
        
        # 檢查是否為學生
        user = mongo.db.user.find_one({'_id': ObjectId(user_id)})
        if not user or user.get('role') != 'student':
            return jsonify({'error': '權限不足'}), 403
        
        # 獲取知識點詳情
        micro_concept = mongo.db.micro_concept.find_one({'_id': ObjectId(micro_id)})
        if not micro_concept:
            return jsonify({'error': '知識點不存在'}), 404
        
        # 計算掌握度
        mastery_result = calculate_micro_concept_mastery(user_id, micro_id)
        
        # 獲取最近練習記錄
        quiz_records = get_student_quiz_records(user_id)
        recent_attempts = []
        
        # 模擬最近練習記錄（實際應該從資料庫查詢）
        for i in range(3):
            recent_attempts.append({
                'date': (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d'),
                'correct': i % 2 == 0,
                'time_spent': 30 + i * 10
            })
        
        # 模擬錯誤範例
        wrong_examples = [
            {
                'question_id': f'q_{micro_id}_1',
                'question_preview': f'關於{micro_concept.get("name", "此知識點")}的問題...',
                'user_answer': '錯誤答案',
                'correct_answer': '正確答案',
                'error_analysis': '常見錯誤分析：需要理解基本概念'
            }
        ]
        
        # 模擬前置依賴
        prereqs = [
            {
                'id': 'prereq_1',
                'name': '前置知識點1',
                'mastery': 60,
                'status': 'learning'
            },
            {
                'id': 'prereq_2', 
                'name': '前置知識點2',
                'mastery': 80,
                'status': 'mastered'
            }
        ]
        
        # AI 建議
        ai_suggestion = f"建議先複習{micro_concept.get('name', '此知識點')}的基本概念，理解其核心原理，然後通過大量練習來鞏固理解。"
        
        # 學習路徑
        learning_path = ['前置知識點1', '前置知識點2', micro_concept.get('name', '目標知識點')]
        
        return jsonify({
            'success': True,
            'detail': {
                'micro_id': micro_id,
                'name': micro_concept.get('name', ''),
                'mastery': mastery_result.get('mastery_score', 0),
                'confidence': mastery_result.get('confidence', 0),
                'recent_attempts': recent_attempts,
                'wrong_examples': wrong_examples,
                'prereqs': prereqs,
                'ai_suggestion': ai_suggestion,
                'learning_path': learning_path
            }
        })
        
    except Exception as e:
        logger.error(f'獲取知識點詳情失敗: {str(e)}')
        return jsonify({
            'success': False,
            'error': f'獲取知識點詳情失敗: {str(e)}',
            'detail': {
                'micro_id': micro_id,
                'name': '未知知識點',
                'mastery': 0,
                'confidence': 0,
                'recent_attempts': [],
                'wrong_examples': [],
                'prereqs': [],
                'ai_suggestion': '數據不足，無法提供分析',
                'learning_path': []
            }
        })

@analytics_bp.route('/api/student/learning-suggestions', methods=['GET'])
def get_learning_suggestions():
    """獲取學習建議"""
    try:
        from flask import session
        from bson import ObjectId
        
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': '未登入'}), 401
        
        # 檢查是否為學生
        user = mongo.db.user.find_one({'_id': ObjectId(user_id)})
        if not user or user.get('role') != 'student':
            return jsonify({'error': '權限不足'}), 403
        
        # 獲取弱點報告
        weakness_report = generate_weakness_report(user_id)
        
        # 生成學習建議
        suggestions = []
        
        # 按領域分組弱點
        domain_weaknesses = {}
        for concept in weakness_report.get('concepts', []):
            if concept.get('insufficient_data', False):
                continue
                
            domain_name = concept.get('domain_name', '未知領域')
            if domain_name not in domain_weaknesses:
                domain_weaknesses[domain_name] = []
            domain_weaknesses[domain_name].append(concept)
        
        # 為每個領域生成建議
        for domain_name, concepts in domain_weaknesses.items():
            if not concepts:
                continue
                
            # 按掌握度排序
            concepts.sort(key=lambda x: x.get('mastery_score', 0))
            
            # 取前3個最弱的知識點
            weak_concepts = concepts[:3]
            
            suggestion = {
                'domain': domain_name,
                'priority': 'high' if any(c.get('mastery_score', 0) < 40 for c in weak_concepts) else 'medium',
                'focus_concepts': [{
                    'name': c.get('name', ''),
                    'mastery_score': c.get('mastery_score', 0),
                    'practice_count': c.get('practice_count', 0)
                } for c in weak_concepts],
                'recommended_actions': [
                    f"專注練習 {domain_name} 領域的基礎概念",
                    "完成相關章節的練習題",
                    "複習相關理論知識"
                ]
            }
            suggestions.append(suggestion)
        
        # 按優先級排序
        suggestions.sort(key=lambda x: 0 if x['priority'] == 'high' else 1)
        
        return jsonify({
            'success': True,
            'suggestions': suggestions[:5]  # 返回前5個建議
        })
        
    except Exception as e:
        logger.error(f'獲取學習建議失敗: {str(e)}')
        return jsonify({
            'success': False,
            'error': f'獲取學習建議失敗: {str(e)}',
            'suggestions': []
        })

@analytics_bp.route('/api/student/progress-points', methods=['GET'])
def get_progress_points():
    """獲取最近進步的知識點"""
    try:
        from flask import session
        from bson import ObjectId
        from datetime import datetime, timedelta
        
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': '未登入'}), 401
        
        # 檢查是否為學生
        user = mongo.db.user.find_one({'_id': ObjectId(user_id)})
        if not user or user.get('role') != 'student':
            return jsonify({'error': '權限不足'}), 403
        
        # 獲取答題記錄
        quiz_records = get_student_quiz_records(user_id)
        
        # 計算最近進步的知識點
        progress_points = calculate_progress_points(user_id, quiz_records)
        
        return jsonify({
            'success': True,
            'progress_points': progress_points
        })
        
    except Exception as e:
        logger.error(f'獲取進步點失敗: {str(e)}')
        return jsonify({
            'success': False,
            'error': f'獲取進步點失敗: {str(e)}',
            'progress_points': []
        })

@analytics_bp.route('/api/student/chart-data', methods=['GET'])
def get_chart_data():
    """獲取圖表數據"""
    try:
        from flask import session, request
        from bson import ObjectId
        from datetime import datetime, timedelta
        
        # 優先從session獲取，如果沒有則從參數獲取，最後使用默認測試用戶
        user_id = session.get('user_id') or request.args.get('user_id')
        chart_type = request.args.get('type', 'all')  # radar, heatmap, trend, bar, all
        domain_filter = request.args.get('domain', 'all')  # 知識領域篩選
        
        if not user_id:
            # 使用默認測試用戶
            test_user = mongo.db.user.find_one({'email': 'test@example.com'})
            if test_user:
                user_id = str(test_user['_id'])
            else:
                return jsonify({
                    'success': False,
                    'error': '未找到測試用戶，請先登入',
                    'chart_data': {}
                })
        
        # 檢查用戶是否存在
        user = mongo.db.user.find_one({'_id': ObjectId(user_id)})
        if not user:
            return jsonify({
                'success': False,
                'error': '用戶不存在',
                'chart_data': {}
            })
        
        # 獲取學生答題記錄
        quiz_records = get_student_quiz_records(user_id)
        
        # 獲取弱點報告
        weakness_report = generate_weakness_report(user_id)
        
        chart_data = {}
        
        if chart_type in ['all', 'radar']:
            # 雷達圖數據 - 各知識領域掌握度
            chart_data['radar'] = generate_radar_chart_data(weakness_report, domain_filter)
        
        if chart_type in ['all', 'heatmap']:
            # 熱力圖數據 - 知識點掌握度矩陣
            chart_data['heatmap'] = generate_heatmap_data(weakness_report, domain_filter)
        
        if chart_type in ['all', 'trend']:
            # 趨勢圖數據 - 學習進度趨勢
            chart_data['trend'] = generate_trend_chart_data(quiz_records, domain_filter)
        
        if chart_type in ['all', 'bar']:
            # 長條圖數據 - 知識點掌握度對比
            chart_data['bar'] = generate_bar_chart_data(weakness_report, domain_filter)
        
        return jsonify({
            'success': True,
            'chart_data': chart_data,
            'domain_filter': domain_filter,
            'available_domains': get_available_domains(weakness_report)
        })
        
    except Exception as e:
        logger.error(f'獲取圖表數據失敗: {str(e)}')
        return jsonify({
            'success': False,
            'error': f'獲取圖表數據失敗: {str(e)}',
            'chart_data': {}
        })

@analytics_bp.route('/api/student/practice-stats', methods=['GET'])
def get_practice_stats():
    """獲取練習統計（進度追蹤用）"""
    try:
        from flask import session, request
        from bson import ObjectId
        from datetime import datetime, timedelta
        
        # 優先從session獲取，如果沒有則從參數獲取，最後使用默認測試用戶
        user_id = session.get('user_id') or request.args.get('user_id')
        
        if not user_id:
            # 使用默認測試用戶
            test_user = mongo.db.user.find_one({'email': 'test@example.com'})
            if test_user:
                user_id = str(test_user['_id'])
            else:
                return jsonify({
                    'success': False,
                    'error': '未找到測試用戶，請先登入',
                    'stats': {
                        'total_questions': 0,
                        'correct_rate': 0,
                        'avg_time': 0,
                        'recent_trend': []
                    }
                })
        
        # 檢查用戶是否存在
        user = mongo.db.user.find_one({'_id': ObjectId(user_id)})
        if not user:
            return jsonify({
                'success': False,
                'error': '用戶不存在',
                'stats': {
                    'total_questions': 0,
                    'correct_rate': 0,
                    'avg_time': 0,
                    'recent_trend': []
                }
            })
        
        # 獲取答題記錄
        quiz_records = get_student_quiz_records(user_id)
        
        # 計算時間範圍內的統計
        now = datetime.now()
        last_week = now - timedelta(days=7)
        last_month = now - timedelta(days=30)
        
        # 按時間過濾記錄
        recent_records = [r for r in quiz_records 
                         if datetime.fromisoformat(r.get('created_at', '').replace('Z', '+00:00')) > last_week]
        monthly_records = [r for r in quiz_records 
                          if datetime.fromisoformat(r.get('created_at', '').replace('Z', '+00:00')) > last_month]
        
        # 計算統計數據
        stats = {
            'total_practice': len(quiz_records),
            'weekly_practice': len(recent_records),
            'monthly_practice': len(monthly_records),
            'weekly_accuracy': round(sum(1 for r in recent_records if r.get('is_correct', False)) / len(recent_records) * 100, 1) if recent_records else 0,
            'monthly_accuracy': round(sum(1 for r in monthly_records if r.get('is_correct', False)) / len(monthly_records) * 100, 1) if monthly_records else 0,
            'streak_days': calculate_streak_days(quiz_records),
            'last_practice': quiz_records[-1].get('created_at') if quiz_records else None
        }
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f'獲取練習統計失敗: {str(e)}')
        return jsonify({
            'success': False,
            'error': f'獲取練習統計失敗: {str(e)}',
            'stats': {
                'total_questions': 0,
                'correct_rate': 0,
                'avg_time': 0,
                'recent_trend': []
            }
        })

def generate_radar_chart_data(weakness_report: dict, domain_filter: str = 'all') -> dict:
    """生成雷達圖數據 - 各知識領域掌握度"""
    try:
        concepts = weakness_report.get('concepts', [])
        
        # 按領域分組
        domain_stats = {}
        for concept in concepts:
            if concept.get('insufficient_data', False):
                continue
                
            domain = concept.get('domain_name', '未知領域')
            if domain_filter != 'all' and domain != domain_filter:
                continue
                
            if domain not in domain_stats:
                domain_stats[domain] = {
                    'mastery_scores': [],
                    'concept_count': 0,
                    'total_attempts': 0
                }
            
            domain_stats[domain]['mastery_scores'].append(concept.get('mastery_score', 0))
            domain_stats[domain]['concept_count'] += 1
            domain_stats[domain]['total_attempts'] += concept.get('attempts', 0)
        
        # 計算各領域平均掌握度
        radar_data = {
            'labels': [],
            'datasets': [{
                'label': '掌握度',
                'data': [],
                'backgroundColor': 'rgba(54, 162, 235, 0.2)',
                'borderColor': 'rgba(54, 162, 235, 1)',
                'borderWidth': 2
            }]
        }
        
        for domain, stats in domain_stats.items():
            if stats['concept_count'] > 0:
                avg_mastery = sum(stats['mastery_scores']) / len(stats['mastery_scores'])
                radar_data['labels'].append(domain)
                radar_data['datasets'][0]['data'].append(round(avg_mastery, 1))
        
        return radar_data
        
    except Exception as e:
        logger.error(f'生成雷達圖數據失敗: {e}')
        return {'labels': [], 'datasets': []}

def generate_heatmap_data(weakness_report: dict, domain_filter: str = 'all') -> dict:
    """生成熱力圖數據 - 知識點掌握度矩陣"""
    try:
        concepts = weakness_report.get('concepts', [])
        
        # 按領域和難度分組
        heatmap_data = {
            'x_labels': [],
            'y_labels': [],
            'data': []
        }
        
        # 獲取所有領域和難度等級
        domains = set()
        difficulties = set()
        
        for concept in concepts:
            if concept.get('insufficient_data', False):
                continue
                
            domain = concept.get('domain_name', '未知領域')
            difficulty = concept.get('difficulty_level', 'medium')
            
            if domain_filter != 'all' and domain != domain_filter:
                continue
                
            domains.add(domain)
            difficulties.add(difficulty)
        
        # 排序
        domains = sorted(list(domains))
        difficulties = sorted(list(difficulties))
        
        heatmap_data['x_labels'] = difficulties
        heatmap_data['y_labels'] = domains
        
        # 計算每個領域-難度組合的平均掌握度
        for domain in domains:
            row = []
            for difficulty in difficulties:
                domain_difficulty_concepts = [
                    c for c in concepts 
                    if (c.get('domain_name') == domain and 
                        c.get('difficulty_level') == difficulty and
                        not c.get('insufficient_data', False))
                ]
                
                if domain_difficulty_concepts:
                    avg_mastery = sum(c.get('mastery_score', 0) for c in domain_difficulty_concepts) / len(domain_difficulty_concepts)
                    row.append(round(avg_mastery, 1))
                else:
                    row.append(0)
            
            heatmap_data['data'].append(row)
        
        return heatmap_data
        
    except Exception as e:
        logger.error(f'生成熱力圖數據失敗: {e}')
        return {'x_labels': [], 'y_labels': [], 'data': []}

def generate_trend_chart_data(quiz_records: list, domain_filter: str = 'all') -> dict:
    """生成趨勢圖數據 - 學習進度趨勢"""
    try:
        from datetime import datetime, timedelta
        
        # 按日期分組答題記錄
        daily_stats = {}
        
        for record in quiz_records:
            created_at = record.get('created_at', '')
            if not created_at:
                continue
                
            try:
                # 解析日期
                if 'T' in created_at:
                    date_str = created_at.split('T')[0]
                else:
                    date_str = created_at.split(' ')[0]
                
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                
                if date_obj not in daily_stats:
                    daily_stats[date_obj] = {
                        'total': 0,
                        'correct': 0,
                        'domains': {}
                    }
                
                daily_stats[date_obj]['total'] += 1
                if record.get('is_correct', False):
                    daily_stats[date_obj]['correct'] += 1
                
                # 按領域統計
                micro_concepts = record.get('micro_concepts', [])
                for concept in micro_concepts:
                    domain = concept.get('domain_name', '未知領域')
                    if domain_filter != 'all' and domain != domain_filter:
                        continue
                        
                    if domain not in daily_stats[date_obj]['domains']:
                        daily_stats[date_obj]['domains'][domain] = {'total': 0, 'correct': 0}
                    
                    daily_stats[date_obj]['domains'][domain]['total'] += 1
                    if record.get('is_correct', False):
                        daily_stats[date_obj]['domains'][domain]['correct'] += 1
                        
            except Exception as e:
                continue
        
        # 生成趨勢數據
        trend_data = {
            'labels': [],
            'datasets': []
        }
        
        # 按日期排序
        sorted_dates = sorted(daily_stats.keys())
        
        for date in sorted_dates:
            trend_data['labels'].append(date.strftime('%m/%d'))
        
        # 整體趨勢
        overall_data = []
        for date in sorted_dates:
            stats = daily_stats[date]
            accuracy = (stats['correct'] / stats['total'] * 100) if stats['total'] > 0 else 0
            overall_data.append(round(accuracy, 1))
        
        trend_data['datasets'].append({
            'label': '整體正確率',
            'data': overall_data,
            'borderColor': 'rgba(54, 162, 235, 1)',
            'backgroundColor': 'rgba(54, 162, 235, 0.1)',
            'tension': 0.4
        })
        
        # 如果指定了領域，添加該領域的趨勢
        if domain_filter != 'all':
            domain_data = []
            for date in sorted_dates:
                stats = daily_stats[date]
                domain_stats = stats['domains'].get(domain_filter, {'total': 0, 'correct': 0})
                accuracy = (domain_stats['correct'] / domain_stats['total'] * 100) if domain_stats['total'] > 0 else 0
                domain_data.append(round(accuracy, 1))
            
            trend_data['datasets'].append({
                'label': f'{domain_filter}正確率',
                'data': domain_data,
                'borderColor': 'rgba(255, 99, 132, 1)',
                'backgroundColor': 'rgba(255, 99, 132, 0.1)',
                'tension': 0.4
            })
        
        return trend_data
        
    except Exception as e:
        logger.error(f'生成趨勢圖數據失敗: {e}')
        return {'labels': [], 'datasets': []}

def generate_bar_chart_data(weakness_report: dict, domain_filter: str = 'all') -> dict:
    """生成長條圖數據 - 知識點掌握度對比"""
    try:
        concepts = weakness_report.get('concepts', [])
        
        # 篩選和排序概念
        filtered_concepts = []
        for concept in concepts:
            if concept.get('insufficient_data', False):
                continue
                
            domain = concept.get('domain_name', '未知領域')
            if domain_filter != 'all' and domain != domain_filter:
                continue
                
            filtered_concepts.append(concept)
        
        # 按掌握度排序
        filtered_concepts.sort(key=lambda x: x.get('mastery_score', 0))
        
        # 取前10個最需要關注的知識點
        top_concepts = filtered_concepts[:10]
        
        bar_data = {
            'labels': [],
            'datasets': [{
                'label': '掌握度',
                'data': [],
                'backgroundColor': [],
                'borderColor': [],
                'borderWidth': 1
            }]
        }
        
        for concept in top_concepts:
            name = concept.get('name', '未知知識點')
            mastery = concept.get('mastery_score', 0)
            
            # 截斷過長的名稱
            if len(name) > 15:
                name = name[:12] + '...'
            
            bar_data['labels'].append(name)
            bar_data['datasets'][0]['data'].append(round(mastery, 1))
            
            # 根據掌握度設置顏色
            if mastery < 40:
                bar_data['datasets'][0]['backgroundColor'].append('rgba(255, 99, 132, 0.8)')
                bar_data['datasets'][0]['borderColor'].append('rgba(255, 99, 132, 1)')
            elif mastery < 70:
                bar_data['datasets'][0]['backgroundColor'].append('rgba(255, 206, 86, 0.8)')
                bar_data['datasets'][0]['borderColor'].append('rgba(255, 206, 86, 1)')
            else:
                bar_data['datasets'][0]['backgroundColor'].append('rgba(75, 192, 192, 0.8)')
                bar_data['datasets'][0]['borderColor'].append('rgba(75, 192, 192, 1)')
        
        return bar_data
        
    except Exception as e:
        logger.error(f'生成長條圖數據失敗: {e}')
        return {'labels': [], 'datasets': []}

def get_available_domains(weakness_report: dict) -> list:
    """獲取可用的知識領域列表"""
    try:
        concepts = weakness_report.get('concepts', [])
        domains = set()
        
        for concept in concepts:
            domain = concept.get('domain_name', '未知領域')
            if domain and domain != '未知領域':
                domains.add(domain)
        
        return sorted(list(domains))
        
    except Exception as e:
        logger.error(f'獲取可用領域失敗: {e}')
        return []

def generate_all_chart_data(weakness_report: dict, quiz_records: list) -> dict:
    """生成所有圖表數據"""
    try:
        return {
            'radar': generate_radar_chart_data(weakness_report),
            'heatmap': generate_heatmap_data(weakness_report),
            'trend': generate_trend_chart_data(quiz_records),
            'bar': generate_bar_chart_data(weakness_report),
            'domain_stats': generate_domain_statistics(weakness_report),
            'difficulty_stats': generate_difficulty_statistics(weakness_report),
            'time_series': generate_time_series_data(quiz_records)
        }
    except Exception as e:
        logger.error(f'生成圖表數據失敗: {e}')
        return {}

def generate_domain_statistics(weakness_report: dict) -> dict:
    """生成領域統計數據"""
    try:
        concepts = weakness_report.get('concepts', [])
        domain_stats = {}
        
        for concept in concepts:
            if concept.get('insufficient_data', False):
                continue
                
            domain = concept.get('domain_name', '未知領域')
            if domain not in domain_stats:
                domain_stats[domain] = {
                    'total_concepts': 0,
                    'mastered_concepts': 0,
                    'weak_concepts': 0,
                    'avg_mastery': 0,
                    'total_attempts': 0,
                    'concepts': []
                }
            
            mastery = concept.get('mastery_score', 0)
            domain_stats[domain]['total_concepts'] += 1
            domain_stats[domain]['total_attempts'] += concept.get('attempts', 0)
            domain_stats[domain]['concepts'].append({
                'name': concept.get('name', ''),
                'mastery': mastery,
                'attempts': concept.get('attempts', 0),
                'difficulty': concept.get('difficulty_level', 'medium')
            })
            
            if mastery >= 70:
                domain_stats[domain]['mastered_concepts'] += 1
            elif mastery < 40:
                domain_stats[domain]['weak_concepts'] += 1
        
        # 計算平均掌握度
        for domain, stats in domain_stats.items():
            if stats['total_concepts'] > 0:
                total_mastery = sum(c['mastery'] for c in stats['concepts'])
                stats['avg_mastery'] = round(total_mastery / stats['total_concepts'], 1)
        
        return domain_stats
        
    except Exception as e:
        logger.error(f'生成領域統計失敗: {e}')
        return {}

def generate_difficulty_statistics(weakness_report: dict) -> dict:
    """生成難度統計數據"""
    try:
        concepts = weakness_report.get('concepts', [])
        difficulty_stats = {}
        
        for concept in concepts:
            if concept.get('insufficient_data', False):
                continue
                
            difficulty = concept.get('difficulty_level', 'medium')
            if difficulty not in difficulty_stats:
                difficulty_stats[difficulty] = {
                    'total_concepts': 0,
                    'mastered_concepts': 0,
                    'weak_concepts': 0,
                    'avg_mastery': 0,
                    'concepts': []
                }
            
            mastery = concept.get('mastery_score', 0)
            difficulty_stats[difficulty]['total_concepts'] += 1
            difficulty_stats[difficulty]['concepts'].append({
                'name': concept.get('name', ''),
                'mastery': mastery,
                'domain': concept.get('domain_name', ''),
                'attempts': concept.get('attempts', 0)
            })
            
            if mastery >= 70:
                difficulty_stats[difficulty]['mastered_concepts'] += 1
            elif mastery < 40:
                difficulty_stats[difficulty]['weak_concepts'] += 1
        
        # 計算平均掌握度
        for difficulty, stats in difficulty_stats.items():
            if stats['total_concepts'] > 0:
                total_mastery = sum(c['mastery'] for c in stats['concepts'])
                stats['avg_mastery'] = round(total_mastery / stats['total_concepts'], 1)
        
        return difficulty_stats
        
    except Exception as e:
        logger.error(f'生成難度統計失敗: {e}')
        return {}

def generate_time_series_data(quiz_records: list) -> dict:
    """生成時間序列數據"""
    try:
        from datetime import datetime, timedelta
        
        # 按日期分組
        daily_stats = {}
        
        for record in quiz_records:
            created_at = record.get('created_at', '')
            if not created_at:
                continue
                
            try:
                # 解析日期
                if 'T' in created_at:
                    date_str = created_at.split('T')[0]
                else:
                    date_str = created_at.split(' ')[0]
                
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                
                if date_obj not in daily_stats:
                    daily_stats[date_obj] = {
                        'total': 0,
                        'correct': 0,
                        'domains': {},
                        'difficulties': {}
                    }
                
                daily_stats[date_obj]['total'] += 1
                if record.get('is_correct', False):
                    daily_stats[date_obj]['correct'] += 1
                
                # 按領域統計
                micro_concepts = record.get('micro_concepts', [])
                for concept in micro_concepts:
                    domain = concept.get('domain_name', '未知領域')
                    difficulty = concept.get('difficulty_level', 'medium')
                    
                    if domain not in daily_stats[date_obj]['domains']:
                        daily_stats[date_obj]['domains'][domain] = {'total': 0, 'correct': 0}
                    if difficulty not in daily_stats[date_obj]['difficulties']:
                        daily_stats[date_obj]['difficulties'][difficulty] = {'total': 0, 'correct': 0}
                    
                    daily_stats[date_obj]['domains'][domain]['total'] += 1
                    daily_stats[date_obj]['difficulties'][difficulty]['total'] += 1
                    
                    if record.get('is_correct', False):
                        daily_stats[date_obj]['domains'][domain]['correct'] += 1
                        daily_stats[date_obj]['difficulties'][difficulty]['correct'] += 1
                        
            except Exception as e:
                continue
        
        # 生成時間序列數據
        sorted_dates = sorted(daily_stats.keys())
        
        time_series = {
            'dates': [date.strftime('%Y-%m-%d') for date in sorted_dates],
            'overall_accuracy': [],
            'domain_accuracy': {},
            'difficulty_accuracy': {}
        }
        
        # 整體準確率
        for date in sorted_dates:
            stats = daily_stats[date]
            accuracy = (stats['correct'] / stats['total'] * 100) if stats['total'] > 0 else 0
            time_series['overall_accuracy'].append(round(accuracy, 1))
        
        # 各領域準確率
        all_domains = set()
        for stats in daily_stats.values():
            all_domains.update(stats['domains'].keys())
        
        for domain in all_domains:
            time_series['domain_accuracy'][domain] = []
            for date in sorted_dates:
                stats = daily_stats[date]
                domain_stats = stats['domains'].get(domain, {'total': 0, 'correct': 0})
                accuracy = (domain_stats['correct'] / domain_stats['total'] * 100) if domain_stats['total'] > 0 else 0
                time_series['domain_accuracy'][domain].append(round(accuracy, 1))
        
        # 各難度準確率
        all_difficulties = set()
        for stats in daily_stats.values():
            all_difficulties.update(stats['difficulties'].keys())
        
        for difficulty in all_difficulties:
            time_series['difficulty_accuracy'][difficulty] = []
            for date in sorted_dates:
                stats = daily_stats[date]
                difficulty_stats = stats['difficulties'].get(difficulty, {'total': 0, 'correct': 0})
                accuracy = (difficulty_stats['correct'] / difficulty_stats['total'] * 100) if difficulty_stats['total'] > 0 else 0
                time_series['difficulty_accuracy'][difficulty].append(round(accuracy, 1))
        
        return time_series
        
    except Exception as e:
        logger.error(f'生成時間序列數據失敗: {e}')
        return {'dates': [], 'overall_accuracy': [], 'domain_accuracy': {}, 'difficulty_accuracy': {}}

def generate_domain_overview(weakness_report: dict) -> list:
    """生成領域概覽數據"""
    try:
        concepts = weakness_report.get('concepts', [])
        domain_stats = {}
        
        for concept in concepts:
            if concept.get('insufficient_data', False):
                continue
                
            domain = concept.get('domain_name', '未知領域')
            if domain not in domain_stats:
                domain_stats[domain] = {
                    'mastery_scores': [],
                    'concept_count': 0
                }
            
            domain_stats[domain]['mastery_scores'].append(concept.get('mastery_score', 0))
            domain_stats[domain]['concept_count'] += 1
        
        domains = []
        for domain, stats in domain_stats.items():
            if stats['concept_count'] > 0:
                avg_mastery = sum(stats['mastery_scores']) / len(stats['mastery_scores'])
                domains.append({
                    'domain_id': f"D{len(domains) + 1}",
                    'name': domain,
                    'mastery': round(avg_mastery, 2)
                })
        
        return domains
        
    except Exception as e:
        logger.error(f'生成領域概覽失敗: {e}')
        return []

def generate_top_weak_points(weakness_report: dict, limit: int = 3) -> list:
    """生成Top弱點列表"""
    try:
        concepts = weakness_report.get('concepts', [])
        
        # 篩選有效概念並按掌握度排序
        valid_concepts = [
            concept for concept in concepts 
            if not concept.get('insufficient_data', False)
        ]
        
        # 按掌握度升序排序，取前N個
        weak_concepts = sorted(valid_concepts, key=lambda x: x.get('mastery_score', 0))[:limit]
        
        weak_points = []
        for i, concept in enumerate(weak_concepts):
            weak_points.append({
                'micro_id': f"M{concept.get('id', i + 1)}",
                'name': concept.get('name', '未知知識點'),
                'mastery': round(concept.get('mastery_score', 0), 2),
                'attempts': concept.get('attempts', 0)
            })
        
        return weak_points
        
    except Exception as e:
        logger.error(f'生成Top弱點失敗: {e}')
        return []

def generate_recent_trend(quiz_records: list, days: int = 7) -> list:
    """生成最近趨勢數據"""
    try:
        from datetime import datetime, timedelta
        
        # 按日期分組
        daily_stats = {}
        
        for record in quiz_records:
            created_at = record.get('created_at', '')
            if not created_at:
                continue
                
            try:
                # 解析日期
                if 'T' in created_at:
                    date_str = created_at.split('T')[0]
                else:
                    date_str = created_at.split(' ')[0]
                
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                
                if date_obj not in daily_stats:
                    daily_stats[date_obj] = {'total': 0, 'correct': 0}
                
                daily_stats[date_obj]['total'] += 1
                if record.get('is_correct', False):
                    daily_stats[date_obj]['correct'] += 1
                    
            except Exception as e:
                continue
        
        # 生成趨勢數據
        trend_data = []
        sorted_dates = sorted(daily_stats.keys())
        
        for date in sorted_dates:
            stats = daily_stats[date]
            accuracy = (stats['correct'] / stats['total']) if stats['total'] > 0 else 0
            trend_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'accuracy': round(accuracy, 2)
            })
        
        return trend_data
        
    except Exception as e:
        logger.error(f'生成趨勢數據失敗: {e}')
        return []

def generate_domain_blocks(weakness_report: dict, domain_id: str) -> list:
    """生成領域下的知識塊"""
    try:
        concepts = weakness_report.get('concepts', [])
        
        # 根據domain_id找到對應的領域名稱
        domain_mapping = {
            'D1': '資料結構',
            'D2': '演算法', 
            'D3': '程式設計',
            'D4': '資料庫'
        }
        domain_name = domain_mapping.get(domain_id, '未知領域')
        
        # 篩選該領域的概念
        domain_concepts = [
            concept for concept in concepts 
            if concept.get('domain_name') == domain_name and not concept.get('insufficient_data', False)
        ]
        
        # 按知識塊分組（這裡簡化為按難度分組）
        difficulty_groups = {}
        for concept in domain_concepts:
            difficulty = concept.get('difficulty_level', 'medium')
            if difficulty not in difficulty_groups:
                difficulty_groups[difficulty] = []
            difficulty_groups[difficulty].append(concept)
        
        # 生成知識塊數據
        blocks = []
        for i, (difficulty, concepts_list) in enumerate(difficulty_groups.items()):
            if concepts_list:
                avg_mastery = sum(c.get('mastery_score', 0) for c in concepts_list) / len(concepts_list)
                blocks.append({
                    'block_id': f"B{i + 1}",
                    'name': f"{domain_name} - {difficulty}",
                    'mastery': round(avg_mastery, 2),
                    'micro_count': len(concepts_list)
                })
        
        return blocks
        
    except Exception as e:
        logger.error(f'生成領域知識塊失敗: {e}')
        return []

def generate_block_concepts(weakness_report: dict, block_id: str) -> list:
    """生成知識塊下的微知識點"""
    try:
        concepts = weakness_report.get('concepts', [])
        
        # 根據block_id找到對應的知識塊
        block_mapping = {
            'B1': '資料結構 - easy',
            'B2': '資料結構 - medium',
            'B3': '資料結構 - hard'
        }
        block_name = block_mapping.get(block_id, '未知知識塊')
        
        # 篩選該知識塊的概念
        block_concepts = [
            concept for concept in concepts 
            if not concept.get('insufficient_data', False)
        ]
        
        # 生成微知識點數據
        micro_concepts = []
        for i, concept in enumerate(block_concepts[:10]):  # 限制前10個
            mastery = concept.get('mastery_score', 0)
            attempts = concept.get('attempts', 0)
            
            # 計算信心度
            if attempts >= 10:
                confidence = 'high'
            elif attempts >= 5:
                confidence = 'medium'
            else:
                confidence = 'low'
            
            micro_concepts.append({
                'micro_id': f"M{i + 1}",
                'name': concept.get('name', '未知知識點'),
                'mastery': round(mastery, 2),
                'attempts': attempts,
                'difficulty': concept.get('difficulty_level', 'medium'),
                'confidence': confidence
            })
        
        return micro_concepts
        
    except Exception as e:
        logger.error(f'生成知識塊微知識點失敗: {e}')
        return []

def generate_micro_detail(weakness_report: dict, quiz_records: list, micro_id: str) -> dict:
    """生成微知識點詳細信息"""
    try:
        concepts = weakness_report.get('concepts', [])
        
        # 找到對應的微知識點
        micro_concept = None
        for concept in concepts:
            if concept.get('id') == micro_id or f"M{concepts.index(concept) + 1}" == micro_id:
                micro_concept = concept
                break
        
        if not micro_concept:
            return {
                'mastery': 0,
                'attempts': 0,
                'avg_time': 0,
                'last_attempt': None,
                'confidence': 'low',
                'trend': []
            }
        
        # 計算平均時間
        micro_records = [
            record for record in quiz_records 
            if micro_id in [c.get('id') for c in record.get('micro_concepts', [])]
        ]
        
        avg_time = 0
        if micro_records:
            times = [r.get('time_spent', 0) for r in micro_records if r.get('time_spent')]
            avg_time = sum(times) / len(times) if times else 0
        
        # 生成趨勢數據
        trend = []
        for i in range(7):
            trend.append({
                'date': f"2025-01-{i + 1:02d}",
                'mastery': round(micro_concept.get('mastery_score', 0) + (i * 0.05), 2)
            })
        
        return {
            'mastery': round(micro_concept.get('mastery_score', 0), 2),
            'attempts': micro_concept.get('attempts', 0),
            'avg_time': round(avg_time, 1),
            'last_attempt': micro_concept.get('last_attempt'),
            'confidence': 'high' if micro_concept.get('attempts', 0) >= 10 else 'medium' if micro_concept.get('attempts', 0) >= 5 else 'low',
            'trend': trend
        }
        
    except Exception as e:
        logger.error(f'生成微知識點詳情失敗: {e}')
        return {
            'mastery': 0,
            'attempts': 0,
            'avg_time': 0,
            'last_attempt': None,
            'confidence': 'low',
            'trend': []
        }

def generate_ai_diagnosis_data(weakness_report: dict, quiz_records: list, micro_id: str, mode: str, time_budget: int) -> dict:
    """生成AI診斷數據"""
    try:
        # 這裡應該調用Gemini API生成診斷
        # 暫時返回模擬數據
        return {
            'diagnosis': '你在這個知識點上常犯錯是因為對基礎概念的理解不夠深入',
            'root_cause': '先修知識點掌握不足，需要加強基礎練習',
            'learning_path': [
                {
                    'step': 1,
                    'micro_id': 'M1',
                    'action': '複習基礎概念'
                },
                {
                    'step': 2,
                    'micro_id': micro_id,
                    'action': '練習基礎題型'
                },
                {
                    'step': 3,
                    'micro_id': micro_id,
                    'action': '挑戰進階題型'
                }
            ],
            'practice_questions': [
                {
                    'q_id': 'Q1',
                    'text': '基礎概念練習題...',
                    'answer': 'A'
                },
                {
                    'q_id': 'Q2',
                    'text': '進階應用題...',
                    'answer': 'B'
                }
            ],
            'evidence': ['missed q101', 'low mastery'],
            'confidence': 'medium'
        }
        
    except Exception as e:
        logger.error(f'生成AI診斷失敗: {e}')
        return {
            'diagnosis': '無法生成診斷，請稍後重試',
            'root_cause': '數據不足',
            'learning_path': [],
            'practice_questions': [],
            'evidence': [],
            'confidence': 'low'
        }

def calculate_progress_points(user_id: str, quiz_records: list) -> list:
    """計算最近進步的知識點"""
    try:
        from datetime import datetime, timedelta
        
        # 獲取所有微知識點
        micro_concepts = list(mongo.db.micro_concept.find())
        progress_points = []
        
        for concept in micro_concepts:
            micro_id = str(concept['_id'])
            
            # 計算該知識點的掌握度變化
            mastery_data = calculate_micro_concept_mastery(user_id, micro_id)
            current_mastery = mastery_data.get('mastery_score', 0)
            
            # 計算最近7天的進步幅度
            now = datetime.now()
            week_ago = now - timedelta(days=7)
            
            # 獲取最近7天的答題記錄
            recent_records = [r for r in quiz_records 
                            if datetime.fromisoformat(r.get('created_at', '').replace('Z', '+00:00')) > week_ago]
            
            if len(recent_records) >= 3:  # 至少3次練習才計算進步
                # 計算進步幅度
                improvement = calculate_improvement_rate(micro_id, recent_records)
                
                if improvement > 5:  # 進步超過5%才顯示
                    progress_points.append({
                        'micro_id': micro_id,
                        'name': concept.get('name', ''),
                        'mastery': round(current_mastery, 1),
                        'improvement': round(improvement, 1),
                        'recent_breakthrough': improvement > 15,  # 進步超過15%視為突破
                        'domain_name': concept.get('domain_name', '未知領域'),
                        'trend': 'improving'
                    })
        
        # 按進步幅度排序
        progress_points.sort(key=lambda x: x['improvement'], reverse=True)
        return progress_points[:5]  # 返回前5個進步點
        
    except Exception as e:
        logger.error(f"計算進步點失敗: {e}")
        return []

def calculate_improvement_rate(micro_id: str, recent_records: list) -> float:
    """計算知識點的進步率"""
    try:
        # 這裡簡化計算，實際應該根據歷史數據計算
        # 可以通過比較最近幾天的準確率變化來計算
        correct_count = sum(1 for r in recent_records if r.get('is_correct', False))
        total_count = len(recent_records)
        
        if total_count == 0:
            return 0
        
        accuracy = correct_count / total_count * 100
        
        # 模擬進步計算（實際應該比較歷史數據）
        return min(accuracy * 0.2, 20)  # 最大進步20%
        
    except Exception as e:
        logger.error(f"計算進步率失敗: {e}")
        return 0

def calculate_streak_days(quiz_records):
    """計算連續練習天數"""
    if not quiz_records:
        return 0
    
    # 按日期分組
    daily_practice = {}
    for record in quiz_records:
        date = record.get('created_at', '').split('T')[0]
        if date not in daily_practice:
            daily_practice[date] = 0
        daily_practice[date] += 1
    
    # 計算連續天數
    dates = sorted(daily_practice.keys(), reverse=True)
    streak = 0
    current_date = datetime.now().date()
    
    for date_str in dates:
        date = datetime.fromisoformat(date_str).date()
        if date == current_date or date == current_date - timedelta(days=1):
            streak += 1
            current_date = date
        else:
            break
    
    return streak

# ==================== AI 提示詞設計 ====================

def generate_ai_diagnosis_prompt(student_data: dict, micro_concept: dict) -> str:
    """生成AI診斷提示詞 - 固定JSON結構"""
    prompt = f"""
你是一個專業的學習分析AI導師，請根據以下學生資料進行深度分析：

## 學生資料
- 學生ID: {student_data.get('user_id', '')}
- 答題總數: {student_data.get('total_questions', 0)}
- 正確率: {student_data.get('accuracy', 0)}%
- 平均答題時間: {student_data.get('avg_time', 0)}秒
- 最近7天練習: {student_data.get('recent_attempts', 0)}次

## 目標知識點
- 名稱: {micro_concept.get('name', '')}
- 領域: {micro_concept.get('domain_name', '')}
- 當前掌握度: {student_data.get('current_mastery', 0)}%
- 練習次數: {student_data.get('practice_count', 0)}次

## 錯誤模式分析
- 常見錯誤: {student_data.get('common_errors', [])}
- 答題時間分佈: {student_data.get('time_distribution', {})}
- 難度適應性: {student_data.get('difficulty_adaptation', {})}

## 前置依賴分析
- 前置知識點: {student_data.get('prerequisites', [])}
- 依賴掌握度: {student_data.get('prereq_mastery', {})}

請提供結構化的分析報告，必須使用以下JSON格式：

{{
  "diagnosis": {{
    "root_cause": "根本原因分析（粗心/概念不清/先修不足/學習方法問題）",
    "error_patterns": ["錯誤模式1", "錯誤模式2"],
    "confidence_level": 0.85,
    "severity": "high|medium|low"
  }},
  "learning_path": {{
    "immediate_actions": [
      "立即行動1：具體可執行的步驟",
      "立即行動2：具體可執行的步驟"
    ],
    "learning_sequence": [
      {{
        "step": 1,
        "title": "步驟標題",
        "description": "詳細描述",
        "estimated_time": "15分鐘",
        "prerequisites": ["前置知識點1", "前置知識點2"]
      }},
      {{
        "step": 2,
        "title": "步驟標題",
        "description": "詳細描述",
        "estimated_time": "20分鐘",
        "prerequisites": []
      }}
    ],
    "practice_strategy": {{
      "recommended_questions": 8,
      "difficulty_progression": "easy->medium->hard",
      "focus_areas": ["重點領域1", "重點領域2"]
    }}
  }},
  "motivation": {{
    "encouragement": "鼓勵話語，強調進步和潛力",
    "achievement_highlight": "突出已取得的成就",
    "next_milestone": "下一個里程碑目標"
  }},
  "monitoring": {{
    "key_indicators": ["監控指標1", "監控指標2"],
    "success_criteria": "成功標準描述",
    "review_schedule": "每3天複習一次"
  }}
}}

請確保：
1. 分析基於具體數據，避免泛泛而談
2. 提供可執行的具體建議
3. 考慮學生的學習風格和當前水平
4. 保持積極正面的語調
5. 所有時間估計要合理
6. 學習路徑要符合知識點依賴關係
"""
    return prompt

def generate_learning_path_ai_prompt(weak_points: list, progress_points: list, knowledge_graph: dict) -> str:
    """生成個性化學習路徑的AI提示詞"""
    prompt = f"""
你是一個專業的學習路徑規劃AI，請根據以下資料生成個性化學習路徑：

## 弱點分析
{json.dumps(weak_points, ensure_ascii=False, indent=2)}

## 進步點分析
{json.dumps(progress_points, ensure_ascii=False, indent=2)}

## 知識圖譜依賴關係
{json.dumps(knowledge_graph, ensure_ascii=False, indent=2)}

請生成一個完整的學習路徑，使用以下JSON格式：

{{
  "learning_path": {{
    "overall_strategy": "整體學習策略描述",
    "estimated_duration": "預估總時間",
    "difficulty_progression": "難度進階說明",
    "phases": [
      {{
        "phase": 1,
        "title": "階段標題",
        "description": "階段描述",
        "duration": "預估時間",
        "focus_areas": ["重點領域1", "重點領域2"],
        "micro_concepts": [
          {{
            "id": "micro_concept_id",
            "name": "知識點名稱",
            "priority": "high|medium|low",
            "prerequisites": ["前置知識點1"],
            "learning_goals": ["學習目標1", "學習目標2"],
            "practice_questions": 5,
            "estimated_time": "15分鐘"
          }}
        ],
        "success_criteria": "階段成功標準",
        "assessment_method": "評估方法"
      }}
    ],
    "adaptive_elements": {{
      "difficulty_adjustment": "難度調整策略",
      "pace_adjustment": "進度調整策略",
      "focus_shift": "重點轉移策略"
    }},
    "motivation_strategy": {{
      "milestones": ["里程碑1", "里程碑2"],
      "rewards": ["獎勵1", "獎勵2"],
      "encouragement_points": ["鼓勵點1", "鼓勵點2"]
    }}
  }},
  "monitoring": {{
    "progress_tracking": "進度追蹤方法",
    "adjustment_triggers": ["調整觸發條件1", "調整觸發條件2"],
    "review_schedule": "複習時間表"
  }}
}}

請確保：
1. 路徑基於知識點依賴關係
2. 考慮學生的弱點和優勢
3. 提供具體可執行的步驟
4. 包含適當的挑戰和成就感
5. 路徑要靈活可調整
"""
    return prompt
