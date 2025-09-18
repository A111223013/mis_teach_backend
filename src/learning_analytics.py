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

def get_student_quiz_records(student_email: str, limit: int = 100) -> List[Dict]:
    """從MySQL獲取學生答題紀錄"""
    try:
        if not sqldb:
            logger.error("SQL 數據庫連接未初始化")
            return []
        
        # 查詢學生答題紀錄
        query = """
        SELECT 
            qa.mongodb_question_id,
            qa.is_correct,
            qa.answer_time_seconds,
            qa.created_at as quiz_date
        FROM quiz_answers qa
        WHERE qa.user_email = :user_email
        ORDER BY qa.created_at DESC
        LIMIT :limit
        """
        
        result = sqldb.session.execute(sqldb.text(query), {
            'user_email': student_email,
            'limit': limit
        }).fetchall()
        
        records = []
        for row in result:
            records.append({
                "mongodb_question_id": row[0],
                "is_correct": bool(row[1]),
                "answer_time_seconds": row[2] or 0,
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
