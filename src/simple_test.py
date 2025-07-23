import json
import os
from multi_agent_process_questions import process_question

def test_single_question():
    """測試單個題目處理"""
    
    # 創建一個簡單的測試題目
    test_question = {
        "type": "single",
        "school": "國立臺北科技大學",
        "department": "資訊工程研究所",
        "year": "105",
        "question_number": "test-1",
        "question_text": "什麼是CPU？請簡要說明。",
        "options": [],
        "answer_type": "short-answer",
        "image_file": []
    }
    
    print("🔄 開始測試單個題目處理...")
    
    try:
        result = process_question(test_question)
        print("✅ 題目處理完成")
        print("📋 處理結果：")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        # 驗證欄位
        required_fields = ["answer", "detail-answer", "key-points", "difficulty level", "error reason"]
        missing_fields = []
        for field in required_fields:
            if field not in result:
                missing_fields.append(field)
            else:
                print(f"✅ {field}: {result[field]}")
        
        if missing_fields:
            print(f"⚠️ 缺少欄位：{missing_fields}")
        else:
            print("✅ 所有必要欄位都存在")
            
    except Exception as e:
        print(f"❌ 處理過程中發生錯誤：{e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_single_question() 