import json

def test_question_fields():
    try:
        with open("backend/src/error_questions.json", 'r', encoding='utf-8') as f:
            all_questions = json.load(f)
        
        print(f"總題目數: {len(all_questions)}")
        
        # 檢查第一個題目的所有字段
        if all_questions:
            first_question = all_questions[0]
            print(f"\n第一個題目的所有字段:")
            for key, value in first_question.items():
                if isinstance(value, str) and len(value) > 100:
                    print(f"  {key}: {value[:100]}...")
                else:
                    print(f"  {key}: {value}")
        
        # 檢查前5個題目的type和answer_type字段
        print(f"\n前5個題目的type和answer_type字段:")
        for i, question in enumerate(all_questions[:5]):
            print(f"  題目{i+1}:")
            print(f"    type: {question.get('type', 'N/A')}")
            print(f"    answer_type: {question.get('answer_type', 'N/A')}")
        
    except Exception as e:
        print(f"錯誤: {e}")

if __name__ == "__main__":
    test_question_fields() 