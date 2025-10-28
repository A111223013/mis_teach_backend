#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
測驗創建工具 - 返回 JSON 數據供前端操作
"""

import json

def create_university_quiz(university: str, department: str, year: int) -> str:
    """創建大學考古題測驗"""
    try:
        return json.dumps({
            "type": "university_quiz",
            "argument": {
                "university": university,
                "department": department
            },
            "number": year
        })
    except Exception as e:
        return f"❌ 創建測驗失敗: {e}"

def create_knowledge_quiz(knowledge_point: str, difficulty: str, question_count: int) -> str:
    """創建知識點測驗"""
    try:
        return json.dumps({
            "type": "knowledge_quiz",
            "argument": {
                "knowledge_point": knowledge_point,
                "difficulty": difficulty
            },
            "number": question_count
        })
    except Exception as e:
        return f"❌ 創建測驗失敗: {e}"