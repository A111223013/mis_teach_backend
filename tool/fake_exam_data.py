#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成假的答題數據腳本
從 MongoDB exam 集合隨機選擇題目，模擬學生作答流程
"""

import sys
import os
import random
from datetime import datetime, timedelta
from bson import ObjectId

# 添加項目根目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from accessories import sqldb, mongo
from sqlalchemy import text

# 定義所有領域及其目標掌握度
DOMAIN_MASTERY_CONFIG = {
    "數位邏輯": 0.75,  # 75% 掌握度
    "作業系統": 0.60,  # 70% 掌握度
    "資料結構": 0.65,  # 65% 掌握度
    "電腦網路": 0.90,  # 80% 掌握度
    "資料庫": 0.60,    # 72% 掌握度
    "AI 與機器學習": 0.1,  # 68% 掌握度
    "資訊安全": 0.55,  # 60% 掌握度
    "雲端與虛擬化": 0.50,  # 35% 掌握度（需要加強）
    "管理資訊系統": 0.80,  # 30% 掌握度（需要加強）
    "軟體工程與系統開發": 0.35,  # 55% 掌握度
    "數學與統計": 0.20,  # 50% 掌握度
}

def get_domain_name_from_question(question_doc: dict) -> str:
    """從題目文檔中提取領域名稱"""
    # 嘗試多個字段來獲取領域名稱
    domain_name = (question_doc.get('domain') or 
                  question_doc.get('subject') or 
                  question_doc.get('field') or 
                  question_doc.get('key-points', '') or 
                  '未知領域')
    
    # 標準化領域名稱（處理可能的變體）
    domain_mapping = {
        '數位邏輯': '數位邏輯',
        '作業系統': '作業系統',
        '資料結構': '資料結構',
        '電腦網路': '電腦網路',
        '資料庫': '資料庫',
        'AI 與機器學習': 'AI 與機器學習',
        'AI': 'AI 與機器學習',
        '機器學習': 'AI 與機器學習',
        '資訊安全': '資訊安全',
        '雲端與虛擬化': '雲端與虛擬化',
        '雲端': '雲端與虛擬化',
        '虛擬化': '雲端與虛擬化',
        '管理資訊系統': '管理資訊系統',
        'MIS': '管理資訊系統',
        '軟體工程與系統開發': '軟體工程與系統開發',
        '軟體工程': '軟體工程與系統開發',
        '數學與統計': '數學與統計',
        '數學': '數學與統計',
        '統計': '數學與統計',
    }
    
    # 嘗試匹配領域名稱
    for key, value in domain_mapping.items():
        if key in domain_name:
            return value
    
    return domain_name

def get_exams_by_domains(questions_per_domain: int = 5) -> dict:
    """按領域分組獲取題目，確保每個領域都有不同難度的題目"""
    try:
        # 獲取所有題目
        all_exams = list(mongo.db.exam.find({}))
        
        if not all_exams:
            print("❌ MongoDB exam 集合中沒有題目")
            return {}
        
        # 按領域和難度分組
        domain_difficulty_exams = {}
        for exam in all_exams:
            domain_name = get_domain_name_from_question(exam)
            
            # 獲取難度
            difficulty = (exam.get('difficulty_level') or 
                         exam.get('difficulty') or 
                         exam.get('level') or 
                         '中等')
            
            # 標準化難度名稱
            difficulty_map = {
                '簡單': '簡單',
                'easy': '簡單',
                '中等': '中等',
                'medium': '中等',
                '困難': '困難',
                'hard': '困難',
            }
            normalized_difficulty = difficulty_map.get(difficulty, '中等')
            
            if domain_name not in domain_difficulty_exams:
                domain_difficulty_exams[domain_name] = {
                    '簡單': [],
                    '中等': [],
                    '困難': []
                }
            
            domain_difficulty_exams[domain_name][normalized_difficulty].append(exam)
        
        # 為每個領域按難度選擇題目，確保每個難度都有題目
        # 過濾掉「未知領域」
        selected_exams_by_domain = {}
        questions_per_difficulty = max(2, questions_per_domain // 3)  # 每個難度至少2題
        
        print(f"\n📊 按領域和難度分組的題目統計:")
        for domain_name, difficulty_exams in domain_difficulty_exams.items():
            # 跳過「未知領域」
            if domain_name == '未知領域' or domain_name == '未知' or not domain_name or domain_name.strip() == '':
                print(f"   ⏭️ 跳過「{domain_name}」領域")
                continue
            selected_exams = []
            difficulty_counts = {}
            
            for difficulty in ['簡單', '中等', '困難']:
                available_exams = difficulty_exams[difficulty]
                if available_exams:
                    # 選擇該難度的題目
                    count = min(questions_per_difficulty, len(available_exams))
                    selected = random.sample(available_exams, count)
                    selected_exams.extend(selected)
                    difficulty_counts[difficulty] = count
                else:
                    difficulty_counts[difficulty] = 0
                    print(f"   ⚠️ {domain_name} 沒有 {difficulty} 難度的題目")
            
            if selected_exams:
                selected_exams_by_domain[domain_name] = selected_exams
                total = sum(difficulty_counts.values())
                print(f"   ✅ {domain_name}: 總共 {total} 題 (簡單:{difficulty_counts['簡單']}, 中等:{difficulty_counts['中等']}, 困難:{difficulty_counts['困難']})")
            else:
                print(f"   ❌ {domain_name}: 沒有可用題目")
        
        return selected_exams_by_domain
        
    except Exception as e:
        print(f"❌ 獲取題目失敗: {e}")
        import traceback
        traceback.print_exc()
        return {}

def generate_fake_answer(question_doc: dict, is_correct: bool = None) -> tuple:
    """
    根據題目生成假的答案
    
    Returns:
        (user_answer, is_correct, score)
    """
    question_type = question_doc.get('type') or question_doc.get('answer_type', 'single-choice')
    correct_answer = question_doc.get('answer', '')
    options = question_doc.get('options', [])
    
    # 如果未指定是否正確，隨機決定（70% 正確率）
    if is_correct is None:
        is_correct = random.random() < 0.4
    
    # 根據題型生成答案
    if question_type in ['single-choice', 'multiple-choice']:
        if options:
            if is_correct:
                # 正確答案
                if question_type == 'multiple-choice':
                    # 多選題：正確答案可能是列表或字符串
                    if isinstance(correct_answer, list):
                        user_answer = correct_answer
                    elif isinstance(correct_answer, str) and ',' in correct_answer:
                        # 如果是逗號分隔的字符串，轉換為列表
                        user_answer = [opt.strip() for opt in correct_answer.split(',')]
                    else:
                        # 單選題格式，但題型是多選，選擇正確答案和一個隨機選項
                        user_answer = [correct_answer]
                        if len(options) > 1:
                            other_options = [opt for opt in options if opt != correct_answer]
                            if other_options:
                                user_answer.append(random.choice(other_options))
                else:
                    # 單選題：選擇正確選項
                    user_answer = correct_answer
            else:
                # 錯誤答案
                if question_type == 'multiple-choice':
                    # 多選題：選擇錯誤的選項組合
                    wrong_options = [opt for opt in options if opt != correct_answer]
                    if wrong_options:
                        # 隨機選擇1-3個錯誤選項
                        num_wrong = random.randint(1, min(3, len(wrong_options)))
                        user_answer = random.sample(wrong_options, num_wrong)
                    else:
                        user_answer = ['錯誤選項']
                else:
                    # 單選題：從選項中隨機選擇一個（排除正確答案）
                    wrong_options = [opt for opt in options if opt != correct_answer]
                    if wrong_options:
                        user_answer = random.choice(wrong_options)
                    else:
                        user_answer = f"錯誤選項_{random.randint(1, 10)}"
        else:
            # 沒有選項，使用正確答案或生成假答案
            if question_type == 'multiple-choice':
                user_answer = [correct_answer] if is_correct else ['錯誤答案']
            else:
                user_answer = correct_answer if is_correct else f"錯誤答案_{random.randint(1, 10)}"
    
    elif question_type == 'true-false':
        if is_correct:
            user_answer = correct_answer
        else:
            # 選擇相反的答案
            user_answer = '錯誤' if correct_answer == '正確' else '正確'
    
    elif question_type == 'fill-in-the-blank':
        if is_correct:
            user_answer = correct_answer
        else:
            # 生成一個類似的錯誤答案
            user_answer = f"{correct_answer}_錯誤" if correct_answer else "錯誤答案"
    
    else:
        # 其他題型，直接使用正確答案或生成假答案
        user_answer = correct_answer if is_correct else "錯誤答案"
    
    # 計算分數（正確=100，錯誤=0）
    score = 100.0 if is_correct else 0.0
    
    return user_answer, is_correct, score

def generate_random_time_spent(difficulty: str = '中等') -> int:
    """根據難度生成隨機答題時間（秒）"""
    # 難度對應的時間範圍（秒）
    time_ranges = {
        '簡單': (10, 60),
        '中等': (30, 120),
        '困難': (60, 300),
        'easy': (10, 60),
        'medium': (30, 120),
        'hard': (60, 300)
    }
    
    # 獲取難度對應的時間範圍
    min_time, max_time = time_ranges.get(difficulty, (30, 120))
    
    # 隨機生成時間
    return random.randint(min_time, max_time)

def generate_random_date(days_back: int = 30) -> datetime:
    """生成隨機的答題日期（過去 days_back 天內）"""
    # 隨機選擇過去幾天
    days_ago = random.randint(0, days_back)
    
    # 生成隨機時間（一天中的某個時間）
    hours = random.randint(8, 22)  # 8點到22點
    minutes = random.randint(0, 59)
    seconds = random.randint(0, 59)
    
    # 計算日期時間
    target_date = datetime.now() - timedelta(days=days_ago)
    target_date = target_date.replace(hour=hours, minute=minutes, second=seconds, microsecond=0)
    
    return target_date

def insert_fake_answers_by_domain(user_email: str, domain_exams: dict, days_back: int = 30):
    """按領域插入假的答題記錄，每個領域使用不同的掌握度"""
    try:
        with sqldb.engine.connect() as conn:
            total_inserted = 0
            total_correct = 0
            total_wrong = 0
            total_time_spent = 0
            domain_stats = {}
            
            # 為每個領域生成答題記錄
            for domain_name, exam_docs in domain_exams.items():
                if not exam_docs:
                    continue
                
                # 獲取該領域的目標掌握度
                target_mastery = DOMAIN_MASTERY_CONFIG.get(domain_name, 0.5)
                
                domain_inserted = 0
                domain_correct = 0
                domain_wrong = 0
                
                print(f"\n📚 處理領域: {domain_name} (目標掌握度: {target_mastery*100:.0f}%)")
                
                for exam_doc in exam_docs:
                    question_id = str(exam_doc['_id'])
                    
                    # 獲取難度
                    difficulty = (exam_doc.get('difficulty_level') or 
                                exam_doc.get('difficulty') or 
                                exam_doc.get('level') or 
                                '中等')
                    
                    # 標準化難度名稱
                    difficulty_map = {
                        '簡單': '簡單',
                        'easy': '簡單',
                        '中等': '中等',
                        'medium': '中等',
                        '困難': '困難',
                        'hard': '困難',
                    }
                    normalized_difficulty = difficulty_map.get(difficulty, '中等')
                    
                    # 根據難度設定絕對掌握度範圍，確保簡單 > 中等 > 困難
                    # 使用更嚴格的邏輯，確保簡單題目掌握度一定高於困難題目
                    if normalized_difficulty == '簡單':
                        # 簡單題目：目標掌握度 + 30% ~ +40%（確保明顯高於其他難度）
                        # 但最高不超過 95%
                        easy_base = min(0.95, target_mastery + 0.30)
                        easy_min = max(0.60, easy_base - 0.05)  # 簡單題目最低也要60%
                        easy_max = min(0.98, easy_base + 0.08)
                        mastery_range = (easy_min, easy_max)
                    elif normalized_difficulty == '中等':
                        # 中等題目：目標掌握度 - 8% ~ +8%（接近目標，但低於簡單題目）
                        medium_base = target_mastery
                        medium_min = max(0.20, medium_base - 0.08)
                        medium_max = min(0.85, medium_base + 0.08)
                        # 確保中等題目最高值不超過簡單題目最低值
                        if medium_max >= 0.60:  # 如果可能超過簡單題目最低值
                            medium_max = min(medium_max, 0.55)  # 限制在55%以下
                        mastery_range = (medium_min, medium_max)
                    else:  # 困難
                        # 困難題目：目標掌握度 - 40% ~ -30%（確保明顯低於其他難度）
                        hard_base = max(0.10, target_mastery - 0.40)
                        hard_min = hard_base
                        hard_max = min(0.50, hard_base + 0.10)  # 困難題目最高不超過50%
                        # 確保困難題目最高值不超過中等題目最低值
                        if hard_max >= 0.20:  # 如果可能超過中等題目最低值
                            hard_max = min(hard_max, 0.15)  # 限制在15%以下
                        mastery_range = (hard_min, hard_max)
                    
                    # 在範圍內隨機生成掌握度
                    actual_mastery = random.uniform(mastery_range[0], mastery_range[1])
                    
                    # 最終檢查：確保簡單 > 中等 > 困難（防止極端情況）
                    # 簡單題目：60-98%
                    # 中等題目：20-55%
                    # 困難題目：10-15%
                    # 這樣可以保證簡單 > 中等 > 困難
                    
                    is_correct = random.random() < actual_mastery
                    
                    user_answer, is_correct, score = generate_fake_answer(exam_doc, is_correct)
                    
                    # 處理 user_answer：如果是列表（多選題），轉換為 JSON 字符串
                    import json
                    if isinstance(user_answer, list):
                        user_answer_str = json.dumps(user_answer, ensure_ascii=False)
                    else:
                        user_answer_str = str(user_answer)
                    
                    # 生成隨機答題時間
                    time_spent = generate_random_time_spent(difficulty)
                    total_time_spent += time_spent
                    
                    # 生成隨機答題日期
                    created_at = generate_random_date(days_back)
                    
                    # 為每題創建一個測驗歷史記錄（模擬單題練習）
                    result = conn.execute(text("""
                        INSERT INTO quiz_history 
                        (user_email, quiz_type, submit_time, status, total_questions, answered_questions)
                        VALUES (:user_email, :quiz_type, :submit_time, :status, :total_questions, :answered_questions)
                    """), {
                        'user_email': user_email,
                        'quiz_type': 'knowledge',
                        'submit_time': created_at,
                        'status': 'completed',
                        'total_questions': 1,
                        'answered_questions': 1
                    })
                    quiz_history_id = result.lastrowid
                    
                    # 插入到 quiz_answers 表
                    conn.execute(text("""
                        INSERT INTO quiz_answers 
                        (quiz_history_id, user_email, mongodb_question_id, user_answer, is_correct, score, answer_time_seconds, created_at)
                        VALUES (:quiz_history_id, :user_email, :mongodb_question_id, :user_answer, :is_correct, :score, :answer_time_seconds, :created_at)
                    """), {
                        'quiz_history_id': quiz_history_id,
                        'user_email': user_email,
                        'mongodb_question_id': question_id,
                        'user_answer': user_answer_str,  # 使用轉換後的字符串
                        'is_correct': is_correct,
                        'score': score,
                        'answer_time_seconds': time_spent,
                        'created_at': created_at
                    })
                    
                    domain_inserted += 1
                    total_inserted += 1
                    if is_correct:
                        domain_correct += 1
                        total_correct += 1
                    else:
                        domain_wrong += 1
                        total_wrong += 1
                
                # 記錄領域統計
                if domain_inserted > 0:
                    actual_mastery_rate = domain_correct / domain_inserted
                    domain_stats[domain_name] = {
                        'total': domain_inserted,
                        'correct': domain_correct,
                        'wrong': domain_wrong,
                        'mastery': actual_mastery_rate * 100
                    }
                    print(f"   ✅ {domain_name}: {domain_correct}/{domain_inserted} 正確 ({actual_mastery_rate*100:.1f}%)")
            
            conn.commit()
            
            # 顯示總體統計
            if total_inserted > 0:
                print(f"\n" + "=" * 60)
                print(f"✅ 成功插入 {total_inserted} 條答題記錄")
                print(f"   - 總正確: {total_correct} 題 ({total_correct/total_inserted*100:.1f}%)")
                print(f"   - 總錯誤: {total_wrong} 題 ({total_wrong/total_inserted*100:.1f}%)")
                print(f"   - 總答題時間: {total_time_spent} 秒 ({total_time_spent/60:.1f} 分鐘)")
                print(f"   - 時間範圍: 過去 {days_back} 天內")
                
                print(f"\n📊 各領域掌握度統計:")
                for domain_name, stats in sorted(domain_stats.items(), key=lambda x: x[1]['mastery']):
                    status = "需要加強" if stats['mastery'] < 60 else "掌握良好"
                    print(f"   - {domain_name}: {stats['mastery']:.1f}% ({stats['correct']}/{stats['total']}) - {status}")
            else:
                print("\n⚠️ 沒有插入任何答題記錄")
            
            return total_inserted
            
    except Exception as e:
        print(f"❌ 插入答題記錄失敗: {e}")
        import traceback
        traceback.print_exc()
        return 0

def main():
    """主函數"""
    print("=" * 60)
    print("生成假的答題數據")
    print("=" * 60)
    
    # 檢查資料庫連接
    if not mongo:
        print("❌ MongoDB 未初始化")
        return
    
    if not sqldb:
        print("❌ SQL 資料庫未初始化")
        return
    
    # 配置參數
    user_email = input("請輸入用戶 Email（直接按 Enter 使用默認值 test@example.com）: ").strip()
    if not user_email:
        user_email = "archer.cbc@gmail.com"
    
    question_count = input("請輸入要生成的題目數量（直接按 Enter 使用默認值 20）: ").strip()
    try:
        question_count = int(question_count) if question_count else 20
    except ValueError:
        question_count = 20
    
    days_back = input("請輸入答題日期範圍（過去幾天，直接按 Enter 使用默認值 30）: ").strip()
    try:
        days_back = int(days_back) if days_back else 30
    except ValueError:
        days_back = 30
    
    questions_per_domain = input("請輸入每個領域的題目數量（直接按 Enter 使用默認值 5）: ").strip()
    try:
        questions_per_domain = int(questions_per_domain) if questions_per_domain else 5
    except ValueError:
        questions_per_domain = 5
    
    print(f"\n📋 配置:")
    print(f"   - 用戶 Email: {user_email}")
    print(f"   - 每個領域題目數量: {questions_per_domain}")
    print(f"   - 日期範圍: 過去 {days_back} 天")
    print(f"\n📚 領域掌握度配置:")
    for domain, mastery in DOMAIN_MASTERY_CONFIG.items():
        status = "需要加強" if mastery < 0.6 else "掌握良好"
        print(f"   - {domain}: {mastery*100:.0f}% - {status}")
    print()
    
    # 按領域分組獲取題目
    domain_exams = get_exams_by_domains(questions_per_domain)
    
    if not domain_exams:
        print("❌ 沒有可用的題目")
        return
    
    # 計算總題數
    total_questions = sum(len(exams) for exams in domain_exams.values())
    
    # 確認是否繼續
    confirm = input(f"將為用戶 {user_email} 生成 {total_questions} 條答題記錄（涵蓋 {len(domain_exams)} 個領域），是否繼續？(y/n): ").strip().lower()
    if confirm != 'y':
        print("❌ 已取消")
        return
    
    # 插入假的答題記錄（按領域，每個領域不同掌握度）
    inserted_count = insert_fake_answers_by_domain(user_email, domain_exams, days_back)
    
    if inserted_count > 0:
        print(f"\n🎉 完成！已為用戶 {user_email} 生成 {inserted_count} 條答題記錄")
    else:
        print("\n❌ 生成失敗")

if __name__ == "__main__":
    # 初始化 Flask 應用
    try:
        from app import app
        with app.app_context():
            main()
    except Exception as e:
        print(f"❌ 初始化應用失敗: {e}")
        import traceback
        traceback.print_exc()
        print("\n請確保:")
        print("1. 已啟動虛擬環境 (venv)")
        print("2. 資料庫連接配置正確")
        print("3. 在 backend 目錄下運行此腳本")

