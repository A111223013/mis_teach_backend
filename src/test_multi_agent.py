import json
import os
import sys
from multi_agent_process_questions import process_all_questions

def test_multi_agent_system():
    """測試多代理人系統"""
    
    # 讀取測試數據
    test_file = "../data/grouped_exam_processed_test.json"
    
    if not os.path.exists(test_file):
        print(f"❌ 測試文件不存在：{test_file}")
        return
    
    try:
        with open(test_file, "r", encoding="utf-8") as f:
            questions = json.load(f)
        
        print(f"📊 載入 {len(questions)} 個題目")
        
        # 處理題目
        results = process_all_questions(questions)
        
        # 驗證結果
        print("\n🔍 驗證處理結果...")
        
        for i, result in enumerate(results):
            if result["type"] == "group":
                print(f"群組題目 {i+1}：{len(result['sub_questions'])} 個子題目")
                for j, sub_q in enumerate(result["sub_questions"]):
                    validate_question_fields(sub_q, f"群組 {i+1} 子題 {j+1}")
            else:
                validate_question_fields(result, f"單題 {i+1}")
        
        # 儲存結果
        output_file = "../data/results_test.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 測試完成，結果已儲存至 {output_file}")
        
    except Exception as e:
        print(f"❌ 測試過程中發生錯誤：{e}")

def validate_question_fields(question, question_name):
    """驗證題目欄位是否完整"""
    required_fields = [
        "answer", "detail-answer", "key-points", 
        "difficulty level", "error reason"
    ]
    
    missing_fields = []
    for field in required_fields:
        if field not in question:
            missing_fields.append(field)
    
    if missing_fields:
        print(f"⚠️  {question_name} 缺少欄位：{missing_fields}")
    else:
        print(f"✅ {question_name} 欄位完整")

if __name__ == "__main__":
    test_multi_agent_system() 