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
import sqlite3  # 實際使用時改為 MySQL 連接器

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== 資料載入模組 ====================

def get_student_quiz_records(student_email: str, limit: int = 100) -> List[Dict]:
    """從MySQL獲取學生答題紀錄"""
    try:
        # 實際使用時改為MySQL查詢
        # SELECT mongodb_question_id, is_correct, answer_time_seconds, quiz_date
        # FROM quiz_answers 
        # WHERE user_email = %s 
        # ORDER BY quiz_date DESC 
        # LIMIT %s
        
        # 這裡使用模擬數據
        return [
            {
                "mongodb_question_id": "q1",
                "is_correct": True,
                "answer_time_seconds": 45,
                "quiz_date": "2024-01-15"
            },
            {
                "mongodb_question_id": "q2", 
                "is_correct": False,
                "answer_time_seconds": 90,
                "quiz_date": "2024-01-15"
            },
            {
                "mongodb_question_id": "q3",
                "is_correct": True,
                "answer_time_seconds": 30,
                "quiz_date": "2024-01-15"
            }
        ]
    except Exception as e:
        logger.error(f"獲取學生答題紀錄失敗: {e}")
        return []

def get_knowledge_structure() -> Dict[str, Any]:
    """從MongoDB獲取知識結構"""
    try:
        # 實際使用時改為MongoDB查詢
        # db.domains.find()
        # db.blocks.find()
        # db.micro_concepts.find()
        
        # 這裡使用模擬數據
        return {
            "domains": [
                {
                    "_id": "domain_1",
                    "name": "計算機概論",
                    "blocks": ["block_1", "block_2"]
                }
            ],
            "blocks": [
                {
                    "_id": "block_1",
                    "domain_id": "domain_1",
                    "title": "硬體系統",
                    "micro_concepts": ["micro_1", "micro_2"]
                },
                {
                    "_id": "block_2",
                    "domain_id": "domain_1", 
                    "title": "軟體系統",
                    "micro_concepts": ["micro_3", "micro_4"]
                }
            ],
            "micro_concepts": [
                {
                    "_id": "micro_1",
                    "name": "CPU架構",
                    "block_id": "block_1",
                    "depends_on": []
                },
                {
                    "_id": "micro_2",
                    "name": "記憶體管理",
                    "block_id": "block_1",
                    "depends_on": ["micro_1"]
                },
                {
                    "_id": "micro_3",
                    "name": "作業系統",
                    "block_id": "block_2",
                    "depends_on": ["micro_1", "micro_2"]
                },
                {
                    "_id": "micro_4",
                    "name": "程式語言",
                    "block_id": "block_2",
                    "depends_on": ["micro_3"]
                }
            ]
        }
    except Exception as e:
        logger.error(f"獲取知識結構失敗: {e}")
        return {"domains": [], "blocks": [], "micro_concepts": []}

def get_questions_by_micro_concept(micro_concept_ids: List[str]) -> List[Dict]:
    """從MongoDB獲取題目，根據小知識點ID"""
    try:
        # 實際使用時改為MongoDB查詢
        # db.questions.find({micro_concept_ids: {$in: micro_concept_ids}})
        
        # 這裡使用模擬數據
        return [
            {
                "_id": "q1",
                "micro_concept_ids": ["micro_1"],
                "difficulty": "中等"
            },
            {
                "_id": "q2",
                "micro_concept_ids": ["micro_2"],
                "difficulty": "困難"
            },
            {
                "_id": "q3", 
                "micro_concept_ids": ["micro_3"],
                "difficulty": "簡單"
            }
        ]
    except Exception as e:
        logger.error(f"獲取題目失敗: {e}")
        return []

# ==================== 知識分析模組 ====================

def calculate_micro_concept_mastery(student_email: str, micro_concept_id: str) -> Dict[str, Any]:
    """計算學生對特定小知識點的掌握度"""
    try:
        # 1. 獲取學生答題紀錄
        quiz_records = get_student_quiz_records(student_email)
        
        # 2. 獲取該小知識點對應的題目
        questions = get_questions_by_micro_concept([micro_concept_id])
        question_ids = [q["_id"] for q in questions]
        
        # 3. 篩選相關題目的答題紀錄
        relevant_records = [
            record for record in quiz_records 
            if record["mongodb_question_id"] in question_ids
        ]
        
        if not relevant_records:
            return {
                "micro_concept_id": micro_concept_id,
                "mastery_score": 0,
                "accuracy": 0,
                "time_factor": 0,
            "total_questions": 0,
            "correct_answers": 0,
                "avg_time": 0
            }
        
        # 4. 計算基礎統計
        total_questions = len(relevant_records)
        correct_answers = sum(1 for r in relevant_records if r["is_correct"])
        accuracy = correct_answers / total_questions
        
        # 5. 計算時間因子（基於認知負荷理論）
        answer_times = [r["answer_time_seconds"] for r in relevant_records]
        avg_time = sum(answer_times) / len(answer_times)
        
        # 理想答題時間範圍：60-120秒
        if avg_time < 60:
            time_factor = max(0, 1 - (60 - avg_time) / 60)  # 太快扣分
        elif avg_time > 120:
            time_factor = max(0, 1 - (avg_time - 120) / 120)  # 太慢扣分
        else:
            time_factor = 1.0  # 理想時間範圍
        
        # 6. 計算掌握度分數 (α=0.7, β=0.3)
        alpha, beta = 0.7, 0.3
        mastery_score = alpha * accuracy + beta * time_factor
        
        return {
            "micro_concept_id": micro_concept_id,
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
        # 1. 獲取知識結構
        knowledge_structure = get_knowledge_structure()
        
        # 2. 找到該block下的所有micro_concepts
        block_info = next(
            (b for b in knowledge_structure["blocks"] if b["_id"] == block_id), 
            None
        )
        
        if not block_info:
            return {"error": "找不到章節資訊"}
        
        micro_concept_ids = block_info["micro_concepts"]
        
        # 3. 計算每個micro_concept的掌握度
        micro_masteries = []
        for micro_id in micro_concept_ids:
            mastery = calculate_micro_concept_mastery(student_email, micro_id)
            if "error" not in mastery:
                micro_masteries.append(mastery)
        
        if not micro_masteries:
            return {
                "block_id": block_id,
                "mastery_score": 0,
                "micro_concepts": [],
                "total_micro_concepts": len(micro_concept_ids)
            }
        
        # 4. 計算章節整體掌握度
        total_mastery = sum(m["mastery_score"] for m in micro_masteries)
        avg_mastery = total_mastery / len(micro_masteries)
        
        return {
            "block_id": block_id,
            "mastery_score": round(avg_mastery, 2),
            "micro_concepts": micro_masteries,
            "total_micro_concepts": len(micro_concept_ids),
            "mastered_concepts": len([m for m in micro_masteries if m["mastery_score"] >= 70])
        }
        
    except Exception as e:
        logger.error(f"計算章節掌握度失敗: {e}")
        return {"error": str(e)}

def calculate_domain_mastery(student_email: str, domain_id: str) -> Dict[str, Any]:
    """計算學生對大知識點的掌握度"""
    try:
        # 1. 獲取知識結構
        knowledge_structure = get_knowledge_structure()
        
        # 2. 找到該domain下的所有blocks
        domain_info = next(
            (d for d in knowledge_structure["domains"] if d["_id"] == domain_id), 
            None
        )
        
        if not domain_info:
            return {"error": "找不到大知識點資訊"}
        
        block_ids = domain_info["blocks"]
        
        # 3. 計算每個block的掌握度
        block_masteries = []
        for block_id in block_ids:
            mastery = calculate_block_mastery(student_email, block_id)
            if "error" not in mastery:
                block_masteries.append(mastery)
        
        if not block_masteries:
            return {
                "domain_id": domain_id,
                "mastery_score": 0,
                "blocks": [],
                "total_blocks": len(block_ids)
            }
        
        # 4. 計算大知識點整體掌握度
        total_mastery = sum(b["mastery_score"] for b in block_masteries)
        avg_mastery = total_mastery / len(block_masteries)
        
        return {
            "domain_id": domain_id,
            "mastery_score": round(avg_mastery, 2),
            "blocks": block_masteries,
            "total_blocks": len(block_ids),
            "mastered_blocks": len([b for b in block_masteries if b["mastery_score"] >= 70])
        }
        
    except Exception as e:
        logger.error(f"計算大知識點掌握度失敗: {e}")
        return {"error": str(e)}

# ==================== 依存關係檢查模組 ====================

def check_dependency_issues(student_email: str) -> List[Dict[str, Any]]:
    """檢查知識依存關係問題"""
    try:
        # 1. 獲取知識結構
        knowledge_structure = get_knowledge_structure()
        
        # 2. 獲取學生所有小知識點掌握度
        all_micro_concepts = knowledge_structure["micro_concepts"]
        dependency_issues = []
        
        for micro_concept in all_micro_concepts:
            if micro_concept["depends_on"]:
                # 檢查當前小知識點掌握度
                current_mastery = calculate_micro_concept_mastery(
                    student_email, micro_concept["_id"]
                )
                
                if "error" in current_mastery:
                    continue
                
                # 檢查前置知識掌握度
                prerequisite_issues = []
                for prereq_id in micro_concept["depends_on"]:
                    prereq_mastery = calculate_micro_concept_mastery(
                        student_email, prereq_id
                    )
                    
                    if "error" not in prereq_mastery:
                        # 如果前置知識掌握度低於當前知識點，記錄問題
                        if prereq_mastery["mastery_score"] < current_mastery["mastery_score"]:
                            prereq_info = next(
                                (mc for mc in all_micro_concepts if mc["_id"] == prereq_id), 
                                None
                            )
                            
                            prerequisite_issues.append({
                                "prerequisite_id": prereq_id,
                                "prerequisite_name": prereq_info["name"] if prereq_info else "未知",
                                "prerequisite_mastery": prereq_mastery["mastery_score"],
                                "current_mastery": current_mastery["mastery_score"],
                                "gap": current_mastery["mastery_score"] - prereq_mastery["mastery_score"]
                            })
                
                if prerequisite_issues:
                    dependency_issues.append({
                        "micro_concept_id": micro_concept["_id"],
                        "micro_concept_name": micro_concept["name"],
                        "issues": prerequisite_issues,
                        "severity": "high" if len(prerequisite_issues) > 1 else "medium"
                    })
        
        return dependency_issues
        
    except Exception as e:
        logger.error(f"檢查依存關係失敗: {e}")
        return []

# ==================== 報告生成模組 ====================

def generate_weakness_report(student_email: str) -> Dict[str, Any]:
    """生成弱點分析報告"""
    try:
        # 1. 獲取知識結構
        knowledge_structure = get_knowledge_structure()
        
        # 2. 計算所有小知識點掌握度
        all_micro_concepts = knowledge_structure["micro_concepts"]
        micro_masteries = []
        
        for micro_concept in all_micro_concepts:
            mastery = calculate_micro_concept_mastery(student_email, micro_concept["_id"])
            if "error" not in mastery:
                mastery["name"] = micro_concept["name"]
                mastery["block_id"] = micro_concept["block_id"]
                micro_masteries.append(mastery)
        
        # 3. 分類弱點
        critical_weaknesses = [m for m in micro_masteries if m["mastery_score"] < 40]
        moderate_weaknesses = [m for m in micro_masteries if 40 <= m["mastery_score"] < 60]
        
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
        
        return {
            "student_email": student_email,
            "summary": {
                "total_concepts": len(micro_masteries),
                "critical_weaknesses": len(critical_weaknesses),
                "moderate_weaknesses": len(moderate_weaknesses),
                "dependency_issues": len(dependency_issues)
            },
            "weaknesses": {
                "critical": critical_weaknesses,
                "moderate": moderate_weaknesses
            },
            "dependency_issues": dependency_issues,
            "recommendations": recommendations
        }
        
    except Exception as e:
        logger.error(f"生成弱點報告失敗: {e}")
        return {"error": str(e)}

def generate_knowledge_graph_data(student_email: str) -> Dict[str, Any]:
    """生成知識圖譜數據（供前端渲染）"""
    try:
        # 1. 獲取知識結構
        knowledge_structure = get_knowledge_structure()
        
        # 2. 計算各層級掌握度
        nodes = []
        edges = []
        
        # 添加domain節點
        for domain in knowledge_structure["domains"]:
            domain_mastery = calculate_domain_mastery(student_email, domain["_id"])
            if "error" not in domain_mastery:
                nodes.append({
                    "id": domain["_id"],
                    "label": domain["name"],
                    "type": "domain",
                    "mastery_score": domain_mastery["mastery_score"],
                    "size": 35
                })
        
        # 添加block節點
        for block in knowledge_structure["blocks"]:
            block_mastery = calculate_block_mastery(student_email, block["_id"])
            if "error" not in block_mastery:
                nodes.append({
                    "id": block["_id"],
                    "label": block["title"],
                    "type": "block",
                    "mastery_score": block_mastery["mastery_score"],
                    "size": 28
                })
                
                # 連接domain和block
                edges.append({
                    "source": block["_id"],
                    "target": block["domain_id"],
                    "type": "belongs_to"
                })
        
        # 添加micro_concept節點
        for micro_concept in knowledge_structure["micro_concepts"]:
            micro_mastery = calculate_micro_concept_mastery(
                student_email, micro_concept["_id"]
            )
            if "error" not in micro_mastery:
                nodes.append({
                    "id": micro_concept["_id"],
                    "label": micro_concept["name"],
                    "type": "micro_concept",
                    "mastery_score": micro_mastery["mastery_score"],
                    "size": 20
                })
                
                # 連接micro_concept和block
                edges.append({
                    "source": micro_concept["_id"],
                    "target": micro_concept["block_id"],
                    "type": "belongs_to"
                })
        
        # 添加依存關係邊
        for micro_concept in knowledge_structure["micro_concepts"]:
            if micro_concept["depends_on"]:
                for prereq_id in micro_concept["depends_on"]:
                    edges.append({
                        "source": micro_concept["_id"],
                        "target": prereq_id,
                        "type": "depends_on"
                    })
        
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
        # 1. 獲取知識結構
        knowledge_structure = get_knowledge_structure()
        
        # 2. 計算各層級掌握度
        domain_analyses = []
        for domain in knowledge_structure["domains"]:
            domain_mastery = calculate_domain_mastery(student_email, domain["_id"])
            if "error" not in domain_mastery:
                domain_analyses.append({
                    "domain_id": domain["_id"],
                    "domain_name": domain["name"],
                    "mastery_score": domain_mastery["mastery_score"],
                    "blocks": domain_mastery["blocks"]
                })
        
        # 3. 生成弱點報告
        weakness_report = generate_weakness_report(student_email)
        
        # 4. 生成知識圖譜數據
        knowledge_graph = generate_knowledge_graph_data(student_email)
        
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
