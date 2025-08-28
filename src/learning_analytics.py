#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
學習成效分析模組 - 統一版本
提供知識圖譜分析、掌握率計算、學習弱點分析等功能
支援兩種數據結構：知識關係圖和題目數據
"""

import json
import sqlite3
import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging
import numpy as np
from collections import defaultdict
from flask import Blueprint, jsonify, request

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LearningAnalytics:
    """學習成效分析器 - 統一版本"""
    
    def __init__(self, db_path: str = "instance/mis_teach.db"):
        self.db_path = db_path
        self.knowledge_hierarchy = self._init_knowledge_hierarchy()
        
    def _init_knowledge_hierarchy(self) -> Dict[str, Dict[str, Any]]:
        """初始化知識層次結構"""
        return {
            "計算機概論": {
                "name": "計算機概論",
                "weight": 1.0,
                "sub_topics": {
                    "硬體系統": {
                        "name": "硬體系統",
                        "weight": 0.3,
                        "concepts": [
                            "CPU架構", "記憶體管理", "儲存設備", "輸入輸出設備"
                        ]
                    },
                    "軟體系統": {
                        "name": "軟體系統", 
                        "weight": 0.25,
                        "concepts": [
                            "作業系統", "程式語言", "應用軟體", "系統軟體"
                        ]
                    },
                    "網路技術": {
                        "name": "網路技術",
                        "weight": 0.25,
                        "concepts": [
                            "網路拓樸", "通訊協定", "網路安全", "網際網路"
                        ]
                    },
                    "資料處理": {
                        "name": "資料處理",
                        "weight": 0.2,
                        "concepts": [
                            "資料結構", "演算法", "資料庫", "資料分析"
                        ]
                    }
                }
            },
            "資訊管理": {
                "name": "資訊管理",
                "weight": 1.0,
                "sub_topics": {
                    "系統分析": {
                        "name": "系統分析",
                        "weight": 0.4,
                        "concepts": [
                            "需求分析", "系統設計", "流程建模", "資料建模"
                        ]
                    },
                    "專案管理": {
                        "name": "專案管理",
                        "weight": 0.3,
                        "concepts": [
                            "專案規劃", "時程管理", "風險管理", "品質管理"
                        ]
                    },
                    "企業應用": {
                        "name": "企業應用",
                        "weight": 0.3,
                        "concepts": [
                            "ERP系統", "CRM系統", "SCM系統", "BI系統"
                        ]
                    }
                }
            }
        }
    
    def get_mock_data(self) -> Dict[str, Any]:
        """獲取模擬學習數據"""
        return {
            "questions": [
                {
                    "id": 1,
                    "text": "Linux檔案系統中，檔案或目錄的屬性「rwx」代表何意義？",
                    "difficulty": "一般",
                    "big_topic": "計算機概論",
                    "sub_topic": "軟體系統",
                    "concepts": ["作業系統", "檔案權限"],
                    "detail_knowledge_key": ["檔案權限", "Linux系統"]
                },
                {
                    "id": 2,
                    "text": "說明CPU中Instruction Register及Program counter各有何用途？",
                    "difficulty": "困難",
                    "big_topic": "計算機概論",
                    "sub_topic": "硬體系統",
                    "concepts": ["CPU架構", "指令執行"],
                    "detail_knowledge_key": ["CPU架構", "指令執行", "暫存器"]
                },
                {
                    "id": 3,
                    "text": "試說明及比較IP address及MAC address？",
                    "difficulty": "一般",
                    "big_topic": "計算機概論",
                    "sub_topic": "網路技術",
                    "concepts": ["網路協定", "網路位址"],
                    "detail_knowledge_key": ["網路協定", "IP位址", "MAC位址"]
                },
                {
                    "id": 4,
                    "text": "何謂資料庫正規化？請說明其目的與步驟？",
                    "difficulty": "困難",
                    "big_topic": "計算機概論",
                    "sub_topic": "資料處理",
                    "concepts": ["資料庫", "資料正規化"],
                    "detail_knowledge_key": ["資料庫", "資料正規化", "資料庫設計"]
                },
                {
                    "id": 5,
                    "text": "系統開發生命週期包含哪些階段？",
                    "difficulty": "簡單",
                    "big_topic": "資訊管理",
                    "sub_topic": "系統分析",
                    "concepts": ["系統分析", "開發流程"],
                    "detail_knowledge_key": ["系統分析", "開發流程", "軟體工程"]
                }
            ],
            "student_answers": [
                {
                    "question_id": 1,
                    "is_correct": False,
                    "answer_time": 45,
                    "total_time": 120,
                    "score": 30
                },
                {
                    "question_id": 2,
                    "is_correct": True,
                    "answer_time": 90,
                    "total_time": 180,
                    "score": 85
                },
                {
                    "question_id": 3,
                    "is_correct": False,
                    "answer_time": 60,
                    "total_time": 150,
                    "score": 45
                },
                {
                    "question_id": 4,
                    "is_correct": False,
                    "answer_time": 120,
                    "total_time": 200,
                    "score": 25
                },
                {
                    "question_id": 5,
                    "is_correct": True,
                    "answer_time": 30,
                    "total_time": 90,
                    "score": 90
                }
            ]
        }
    
    def get_mock_knowledge_graph(self) -> Dict[str, Any]:
        """獲取模擬知識關係圖數據"""
        return {
            "knowledge_nodes": [
                {
                    "id": "stack",
                    "name": "堆疊",
                    "type": "concept",
                    "category": "資料結構"
                },
                {
                    "id": "array",
                    "name": "陣列操作",
                    "type": "concept",
                    "category": "演算法"
                },
                {
                    "id": "sorting",
                    "name": "排序演算法",
                    "type": "concept",
                    "category": "演算法"
                },
                {
                    "id": "data_structure",
                    "name": "資料結構",
                    "type": "topic",
                    "category": "計算機概論"
                },
                {
                    "id": "algorithm",
                    "name": "演算法",
                    "type": "topic",
                    "category": "計算機概論"
                }
            ],
            "knowledge_edges": [
                {
                    "source": "堆疊",
                    "target": "資料結構",
                    "type": "hierarchy"
                },
                {
                    "source": "陣列操作",
                    "target": "排序演算法",
                    "type": "pre-requisite"
                },
                {
                    "source": "排序演算法",
                    "target": "演算法",
                    "type": "hierarchy"
                },
                {
                    "source": "堆疊",
                    "target": "演算法",
                    "type": "application"
                }
            ]
        }
    
    def calculate_concept_mastery(self, mock_data: Dict[str, Any]) -> Dict[str, Any]:
        """計算小知識點掌握率"""
        concept_stats = defaultdict(lambda: {
            "total_questions": 0,
            "correct_answers": 0,
            "total_time": 0,
            "difficulty_scores": {"簡單": 0, "一般": 0, "困難": 0},
            "concept_scores": []
        })
        
        # 統計每個概念的答題情況
        for question in mock_data["questions"]:
            # 使用 detail_knowledge_key 作為主要知識點
            for concept in question.get("detail_knowledge_key", question.get("concepts", [])):
                concept_stats[concept]["total_questions"] += 1
                concept_stats[concept]["difficulty_scores"][question["difficulty"]] += 1
        
        # 統計答題結果
        for answer in mock_data["student_answers"]:
            question = next(q for q in mock_data["questions"] if q["id"] == answer["question_id"])
            for concept in question.get("detail_knowledge_key", question.get("concepts", [])):
                if answer["is_correct"]:
                    concept_stats[concept]["correct_answers"] += 1
                concept_stats[concept]["total_time"] += answer["answer_time"]
                concept_stats[concept]["concept_scores"].append(answer["score"])
        
        # 計算掌握率
        concept_mastery = {}
        for concept, stats in concept_stats.items():
            if stats["total_questions"] > 0:
                # 基礎掌握率（答對率）
                accuracy_rate = stats["correct_answers"] / stats["total_questions"]
                
                # 時間效率分數（標準化答題時間）
                avg_time = stats["total_time"] / stats["total_questions"]
                time_efficiency = max(0, 1 - (avg_time - 60) / 120)  # 60秒為基準，120秒為標準差
                
                # 難度加權分數
                difficulty_weight = (
                    stats["difficulty_scores"]["簡單"] * 0.3 +
                    stats["difficulty_scores"]["一般"] * 0.5 +
                    stats["difficulty_scores"]["困難"] * 0.2
                ) / stats["total_questions"]
                
                # 綜合掌握率
                mastery_rate = (
                    accuracy_rate * 0.6 +
                    time_efficiency * 0.3 +
                    difficulty_weight * 0.1
                ) * 100
                
                concept_mastery[concept] = {
                    "mastery_rate": round(mastery_rate, 2),
                    "accuracy_rate": round(accuracy_rate * 100, 2),
                    "time_efficiency": round(time_efficiency * 100, 2),
                    "total_questions": stats["total_questions"],
                    "correct_answers": stats["correct_answers"],
                    "avg_time": round(avg_time, 2)
                }
        
        return concept_mastery
    
    def calculate_topic_mastery(self, concept_mastery: Dict[str, Any]) -> Dict[str, Any]:
        """計算大知識點掌握率"""
        topic_mastery = {}
        
        for big_topic, topic_info in self.knowledge_hierarchy.items():
            topic_concepts = []
            topic_weighted_score = 0
            total_weight = 0
            
            # 收集該大知識點下的所有小知識點
            for sub_topic, sub_info in topic_info["sub_topics"].items():
                for concept in sub_info["concepts"]:
                    if concept in concept_mastery:
                        topic_concepts.append({
                            "name": concept,
                            "mastery_rate": concept_mastery[concept]["mastery_rate"],
                            "sub_topic": sub_topic
                        })
                        # 加權計算
                        weight = sub_info["weight"] / len(sub_info["concepts"])
                        topic_weighted_score += concept_mastery[concept]["mastery_rate"] * weight
                        total_weight += weight
            
            if total_weight > 0:
                overall_mastery = topic_weighted_score / total_weight
                topic_mastery[big_topic] = {
                    "name": big_topic,
                    "overall_mastery": round(overall_mastery, 2),
                    "concepts": topic_concepts,
                    "concept_count": len(topic_concepts),
                    "mastered_concepts": len([c for c in topic_concepts if c["mastery_rate"] >= 70])
                }
        
        return topic_mastery
    
    def generate_knowledge_graph(self, concept_mastery: Dict[str, Any], topic_mastery: Dict[str, Any]) -> Dict[str, Any]:
        """生成知識圖譜數據"""
        nodes = []
        edges = []
        
        # 添加大知識點節點
        for topic_name, topic_info in topic_mastery.items():
            nodes.append({
                "id": f"topic_{topic_name}",
                "label": topic_name,
                "type": "topic",
                "mastery_rate": topic_info["overall_mastery"],
                "size": 30,
                "color": self._get_color_by_mastery(topic_info["overall_mastery"])
            })
        
        # 添加小知識點節點
        for concept_name, concept_info in concept_mastery.items():
            nodes.append({
                "id": f"concept_{concept_name}",
                "label": concept_name,
                "type": "concept",
                "mastery_rate": concept_info["mastery_rate"],
                "size": 20,
                "color": self._get_color_by_mastery(concept_info["mastery_rate"])
            })
            
            # 找到對應的大知識點
            for topic_name, topic_info in self.knowledge_hierarchy.items():
                for sub_topic, sub_info in topic_info["sub_topics"].items():
                    if concept_name in sub_info["concepts"]:
                        edges.append({
                            "source": f"concept_{concept_name}",
                            "target": f"topic_{topic_name}",
                            "type": "belongs_to"
                        })
                        break
        
        return {
            "nodes": nodes,
            "edges": edges
        }
    
    def _get_color_by_mastery(self, mastery_rate: float) -> str:
        """根據掌握率獲取顏色"""
        if mastery_rate >= 80:
            return "#28a745"  # 綠色 - 優秀
        elif mastery_rate >= 60:
            return "#ffc107"  # 黃色 - 良好
        elif mastery_rate >= 40:
            return "#fd7e14"  # 橙色 - 一般
        else:
            return "#dc3545"  # 紅色 - 需加強
    
    def identify_weaknesses(self, concept_mastery: Dict[str, Any]) -> Dict[str, Any]:
        """識別學習弱點和補強建議"""
        weaknesses = []
        recommendations = []
        
        # 找出掌握率低的概念
        for concept, info in concept_mastery.items():
            if info["mastery_rate"] < 60:
                weaknesses.append({
                    "concept": concept,
                    "mastery_rate": info["mastery_rate"],
                    "issues": []
                })
                
                # 分析具體問題
                if info["accuracy_rate"] < 50:
                    weaknesses[-1]["issues"].append("答題正確率過低")
                if info["time_efficiency"] < 50:
                    weaknesses[-1]["issues"].append("答題時間過長")
                if info["total_questions"] < 2:
                    weaknesses[-1]["issues"].append("練習題目不足")
        
        # 生成補強建議
        for weakness in weaknesses:
            if weakness["mastery_rate"] < 40:
                recommendations.append({
                    "concept": weakness["concept"],
                    "priority": "高",
                    "suggestions": [
                        "重新學習基礎概念",
                        "多做相關練習題",
                        "尋求老師或同學協助"
                    ]
                })
            elif weakness["mastery_rate"] < 60:
                recommendations.append({
                    "concept": weakness["concept"],
                    "priority": "中",
                    "suggestions": [
                        "複習相關概念",
                        "增加練習頻率",
                        "注意答題時間控制"
                    ]
                })
        
        return {
            "weaknesses": weaknesses,
            "recommendations": recommendations,
            "overall_assessment": self._get_overall_assessment(concept_mastery)
        }
    
    def _get_overall_assessment(self, concept_mastery: Dict[str, Any]) -> str:
        """獲取整體學習評估"""
        if not concept_mastery:
            return "資料不足"
        
        avg_mastery = sum(info["mastery_rate"] for info in concept_mastery.values()) / len(concept_mastery)
        
        if avg_mastery >= 80:
            return "學習成效優秀，繼續保持！"
        elif avg_mastery >= 60:
            return "學習成效良好，有進步空間"
        elif avg_mastery >= 40:
            return "學習成效一般，需要加強練習"
        else:
            return "學習成效較差，建議重新學習基礎概念"
    
    def get_learning_analytics(self) -> Dict[str, Any]:
        """獲取完整的學習分析數據"""
        try:
            # 獲取模擬數據
            mock_data = self.get_mock_data()
            
            # 計算小知識點掌握率
            concept_mastery = self.calculate_concept_mastery(mock_data)
            
            # 計算大知識點掌握率
            topic_mastery = self.calculate_topic_mastery(concept_mastery)
            
            # 生成知識圖譜
            knowledge_graph = self.generate_knowledge_graph(concept_mastery, topic_mastery)
            
            # 識別弱點和建議
            weaknesses_analysis = self.identify_weaknesses(concept_mastery)
            
            # 計算整體統計
            total_questions = len(mock_data["questions"])
            total_correct = sum(1 for a in mock_data["student_answers"] if a["is_correct"])
            avg_time = sum(a["answer_time"] for a in mock_data["student_answers"]) / len(mock_data["student_answers"])
            
            return {
                "success": True,
                "data": {
                    "overview": {
                        "total_questions": total_questions,
                        "correct_answers": total_correct,
                        "accuracy_rate": round(total_correct / total_questions * 100, 2),
                        "avg_answer_time": round(avg_time, 2),
                        "overall_assessment": weaknesses_analysis["overall_assessment"]
                    },
                    "concept_mastery": concept_mastery,
                    "topic_mastery": topic_mastery,
                    "knowledge_graph": knowledge_graph,
                    "weaknesses_analysis": weaknesses_analysis,
                    "questions_data": mock_data["questions"],
                    "student_answers": mock_data["student_answers"]
                }
            }
            
        except Exception as e:
            logger.error(f"學習分析失敗: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_knowledge_relationship_graph(self) -> Dict[str, Any]:
        """獲取知識關係圖數據"""
        try:
            knowledge_data = self.get_mock_knowledge_graph()
            return {
                "success": True,
                "data": knowledge_data
            }
        except Exception as e:
            logger.error(f"知識關係圖獲取失敗: {e}")
            return {
                "success": False,
                "error": str(e)
            }

# 創建分析器實例
learning_analytics = LearningAnalytics()

# ==================== Flask API 端點 ====================

# 創建藍圖
analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/learning-analytics', methods=['GET'])
def get_learning_analytics():
    """獲取學習成效分析數據"""
    try:
        # 獲取學習分析數據
        analytics_data = learning_analytics.get_learning_analytics()
        
        if analytics_data["success"]:
            return jsonify(analytics_data), 200
        else:
            return jsonify({
                "success": False,
                "error": analytics_data.get("error", "分析失敗")
            }), 500
            
    except Exception as e:
        logger.error(f"學習分析API錯誤: {e}")
        return jsonify({
            "success": False,
            "error": f"系統錯誤: {str(e)}"
        }), 500

@analytics_bp.route('/concept-mastery', methods=['GET'])
def get_concept_mastery():
    """獲取小知識點掌握率"""
    try:
        analytics_data = learning_analytics.get_learning_analytics()
        
        if analytics_data["success"]:
            return jsonify({
                "success": True,
                "data": analytics_data["data"]["concept_mastery"]
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": analytics_data.get("error", "分析失敗")
            }), 500
            
    except Exception as e:
        logger.error(f"概念掌握率API錯誤: {e}")
        return jsonify({
            "success": False,
            "error": f"系統錯誤: {str(e)}"
        }), 500

@analytics_bp.route('/topic-mastery', methods=['GET'])
def get_topic_mastery():
    """獲取大知識點掌握率"""
    try:
        analytics_data = learning_analytics.get_learning_analytics()
        
        if analytics_data["success"]:
            return jsonify({
                "success": True,
                "data": analytics_data["data"]["topic_mastery"]
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": analytics_data.get("error", "分析失敗")
            }), 500
            
    except Exception as e:
        logger.error(f"主題掌握率API錯誤: {e}")
        return jsonify({
            "success": False,
            "error": f"系統錯誤: {str(e)}"
        }), 500

@analytics_bp.route('/knowledge-graph', methods=['GET'])
def get_knowledge_graph():
    """獲取知識圖譜數據"""
    try:
        analytics_data = learning_analytics.get_learning_analytics()
        
        if analytics_data["success"]:
            return jsonify({
                "success": True,
                "data": analytics_data["data"]["knowledge_graph"]
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": analytics_data.get("error", "分析失敗")
            }), 500
            
    except Exception as e:
        logger.error(f"知識圖譜API錯誤: {e}")
        return jsonify({
            "success": False,
            "error": f"系統錯誤: {str(e)}"
        }), 500

@analytics_bp.route('/weaknesses-analysis', methods=['GET'])
def get_weaknesses_analysis():
    """獲取學習弱點分析"""
    try:
        analytics_data = learning_analytics.get_learning_analytics()
        
        if analytics_data["success"]:
            return jsonify({
                "success": True,
                "data": analytics_data["data"]["weaknesses_analysis"]
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": analytics_data.get("error", "分析失敗")
            }), 500
            
    except Exception as e:
        logger.error(f"弱點分析API錯誤: {e}")
        return jsonify({
            "success": False,
            "error": f"系統錯誤: {str(e)}"
        }), 500

@analytics_bp.route('/overview', methods=['GET'])
def get_overview():
    """獲取學習概覽數據"""
    try:
        analytics_data = learning_analytics.get_learning_analytics()
        
        if analytics_data["success"]:
            return jsonify({
                "success": True,
                "data": analytics_data["data"]["overview"]
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": analytics_data.get("error", "分析失敗")
            }), 500
            
    except Exception as e:
        logger.error(f"概覽API錯誤: {e}")
        return jsonify({
            "success": False,
            "error": f"系統錯誤: {str(e)}"
        }), 500

@analytics_bp.route('/knowledge-relationship', methods=['GET'])
def get_knowledge_relationship():
    """獲取知識關係圖數據"""
    try:
        relationship_data = learning_analytics.get_knowledge_relationship_graph()
        
        if relationship_data["success"]:
            return jsonify(relationship_data), 200
        else:
            return jsonify({
                "success": False,
                "error": relationship_data.get("error", "知識關係圖獲取失敗")
            }), 500
            
    except Exception as e:
        logger.error(f"知識關係圖API錯誤: {e}")
        return jsonify({
            "success": False,
            "error": f"系統錯誤: {str(e)}"
        }), 500
