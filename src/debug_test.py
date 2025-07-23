import json
import os
from multi_agent_process_questions import call_gemini_model, main_agent_prompt_template, secondary_agent_prompt_template, arbiter_agent_prompt_template

def debug_arbiter_output():
    """調試仲裁代理人的輸出"""
    
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
    
    print("🔄 開始調試仲裁代理人輸出...")
    
    # 主代理人
    main_prompt = main_agent_prompt_template.format(question_text=test_question["question_text"])
    main_response = call_gemini_model(main_prompt)
    print("✅ 主代理人分析完成")
    print(f"📋 主代理人回應：{main_response[:200]}...")
    
    # 次代理人
    secondary_prompt = secondary_agent_prompt_template.format(main_response=main_response)
    secondary_response = call_gemini_model(secondary_prompt)
    print("✅ 次代理人分析完成")
    print(f"📋 次代理人回應：{secondary_response[:200]}...")
    
    # 仲裁代理人
    arbiter_prompt = arbiter_agent_prompt_template.format(
        main_response=main_response,
        secondary_response=secondary_response
    )
    arbiter_response = call_gemini_model(arbiter_prompt)
    print("✅ 仲裁代理人分析完成")
    print(f"📋 仲裁代理人完整回應：")
    print(arbiter_response)
    
    # 嘗試解析
    try:
        arbiter_response = arbiter_response.strip()
        if arbiter_response.startswith('```json'):
            arbiter_response = arbiter_response[7:]
        if arbiter_response.endswith('```'):
            arbiter_response = arbiter_response[:-3]
        arbiter_response = arbiter_response.strip()
        
        result = json.loads(arbiter_response)
        print("✅ JSON解析成功")
        print(f"📋 解析結果：{json.dumps(result, ensure_ascii=False, indent=2)}")
        
    except Exception as e:
        print(f"❌ JSON解析失敗：{e}")

if __name__ == "__main__":
    debug_arbiter_output() 