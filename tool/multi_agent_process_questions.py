import os
import base64
import json
import requests
import google.generativeai as genai



# ========== Gemini API Key ==========
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyBad7mpaX-fPPtpjbcgZ1JpKOBPJZJkmf4")

# ========== 提示詞定義 ==========
main_agent_prompt_template = """
你是「計算機概論判題系統」中的主代理人 Gemini 2.0。

請根據題目內容，完成以下任務：
1. 判斷正確答案為何，並說明理由。
2. 請說明本題屬於以下哪一種固定題型，並指出是否存在題意錯誤或敘述模糊情形。可用的題型如下：
   - "single-choice"：單選題  
   - "multiple-choice"：多選題  
   - "fill-in-the-blank"：填空題  
   - "true-false"：是非題  
   - "short-answer"：簡答題／問答題  
   - "long-answer"：申論題／長答題  
   - "choice-answer"：選填題  
   - "draw-answer"：畫圖題  
   - "coding-answer"：程式撰寫題
3. 判斷題目敘述是否有誤（若有錯誤請指出並說明）。
4. 從以下 12 個知識點中，選出本題最相關的一項：
   - 基本計概、數位邏輯、作業系統、程式語言、資料結構、網路、資料庫、AI與機器學習、資訊安全、雲端與虛擬化、MIS、軟體工程與系統開發
5. 評估難易度（簡單、中等、困難）。
6. 詳細說明解析與思路。

【重要要求】
- 請用中文回答所有分析內容
- 不要修改原始題目內容
- 保持題目的原始語言（英文題目保持英文，中文題目保持中文）

【題目內容】
{question_text}
"""

secondary_agent_prompt_template = """
你是「計算機概論判題系統」中的次要代理人 Gemini 2.0。

請閱讀以下主代理人 Gemini 2.0 的分析結果，並依下列規則做出回應：

【主代理人分析】
{main_response}

【任務】
請判斷你是否同意主代理人的判斷與結論，回覆格式如下：

1. 你是否同意主代理人的「正確答案」判斷？（同意 / 不同意）若不同意，請說明你認為正確的選項與理由。
2. 你是否同意其「題型判定」與「題意是否錯誤」的分析？
3. 你是否同意其選定的「知識分類」與「難易度」？
4. 有無其他補充或異議？
"""

arbiter_agent_prompt_template = """
你是「計算機概論判題系統」中的仲裁代理人。

請根據以下兩位代理人的分析，輸出一個JSON格式的題目結果。

【主代理人分析】
{main_response}

【次代理人回應】
{secondary_response}

【任務】
請整合上述分析，輸出一個包含完整題目資訊的JSON陣列。

【重要要求】
1. 保持原始題目內容不變（英文題目保持英文，中文題目保持中文）
2. 保持所有原始欄位不變（school、department、year、question_number等）
3. 只有以下欄位使用中文：
   - detail-answer：對於答案的詳細詳細說明解釋（中文）
   - key-points：知識點分類（中文）
   - difficulty level：難度等級（中文）
   - error reason：錯誤原因（中文）
4. answer欄位必須是明確、簡短、直接的正確答案，**不能出現「請參考詳細解答」、「見上」等無意義內容**，要直接給出答案本身。
   - 簡答題、問答題：用中文直接給出正確答案
   - 選擇題：直接給出正確選項（如A、B、True、False等，或選項內容）
5. detail-answer 是對 answer 的詳細說明、推導、理由，並說明為什麼知識點式著個跟為甚麼難易度是這樣（中文）
6. difficulty level 判斷原則：
   - 若題目為定義、事實、基礎知識，請填「簡單」
   - 若需推理、計算、綜合，請填「中等」或「困難」
7. 不要修改或覆蓋原始欄位

【輸出格式】
請直接輸出以下格式的JSON陣列（不要包含任何其他文字）：

[{{  
  "answer": "答案（明確簡短直接，不能是請參考詳細解答）",
  "detail-answer": "詳細解答（中文）",
  "key-points": "基本計概",
  "difficulty level": "簡單",
  "error reason": ""
}}]

注意：
1. 只輸出新增的欄位，不要包含原始欄位
2. key-points 必須從以下選項選擇：基本計概、數位邏輯、作業系統、程式語言、資料結構、網路、資料庫、AI與機器學習、資訊安全、雲端與虛擬化、MIS、軟體工程與系統開發
3. difficulty level 只能填入：簡單、中等、困難
4. 直接輸出JSON，不要有任何解釋文字
5. 必須包含 key-points 欄位
6. 不要修改原始題目內容
"""




# ========== 模型初始化 ==========
# 設定金鑰
genai.configure(api_key=GEMINI_API_KEY)

def read_image_base64(image_path):
    if not os.path.exists(image_path):
        return None
    with open(image_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
        return encoded

def call_gemini_model(prompt, image_base64=None):
    model = genai.GenerativeModel("gemini-2.0-flash")

    if image_base64:
        import base64
        import io
        from PIL import Image

        image_data = base64.b64decode(image_base64)
        image = Image.open(io.BytesIO(image_data))

        response = model.generate_content([
            prompt,
            image  # 注意這裡是直接傳圖片物件
        ])
    else:
        response = model.generate_content(prompt)

    return response.text.strip()

def call_llama_model(prompt):
    """調用次代理人模型（改為使用 Gemini）"""
    try:
        # 使用 Gemini 作為次代理人，而不是本地 Ollama
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"⚠️ 次代理人調用失敗，使用備用方案：{e}")
       

# ========== 處理 single ==========
def process_question(question):
    import copy
    question_text = question["question_text"]
    image_path = question.get("image_file")
    image_base64 = None

    if isinstance(image_path, list):
        image_file = image_path[0] if image_path else None
    else:
        image_file = image_path

    if image_file:
        image_base64 = read_image_base64(os.path.join("backend", "src", "picture", image_file))

    print(f"🔄 處理題目：{question_text[:50]}...")

    main_prompt = main_agent_prompt_template.format(question_text=question_text)
    main_response = call_gemini_model(main_prompt, image_base64=image_base64)
    print("✅ 主代理人分析完成")

    secondary_prompt = secondary_agent_prompt_template.format(main_response=main_response)
    secondary_response = call_llama_model(secondary_prompt)
    print("✅ 次代理人分析完成")

    arbiter_prompt = arbiter_agent_prompt_template.format(
        main_response=main_response,
        secondary_response=secondary_response
    )
    arbiter_response = call_gemini_model(arbiter_prompt)
    print("✅ 仲裁代理人分析完成")

    try:
        # 嘗試清理回應，移除可能的非JSON內容
        arbiter_response = arbiter_response.strip()
        if arbiter_response.startswith('```json'):
            arbiter_response = arbiter_response[7:]
        if arbiter_response.endswith('```'):
            arbiter_response = arbiter_response[:-3]
        arbiter_response = arbiter_response.strip()
        
        print(f"🔍 仲裁回應：{arbiter_response[:100]}...")
        
        result = json.loads(arbiter_response)
        if isinstance(result, list) and result:
            # 確保結果包含所有原始欄位
            processed_question = copy.deepcopy(question)
            processed_question.update(result[0])
            print("✅ JSON解析成功")
            return processed_question
        else:
            raise ValueError("仲裁輸出格式不正確")
    except Exception as e:
        print(f"⚠️ JSON解析失敗：{e}")
        # 若解析失敗，回傳原始題目但補齊新欄位
        fallback = copy.deepcopy(question)
        # 確保所有新增欄位都有預設值
        fallback.setdefault("answer", "")
        fallback.setdefault("detail-answer", "")
        fallback.setdefault("key-points", "")
        fallback.setdefault("difficulty level", "")
        fallback.setdefault("error reason", f"仲裁解析錯誤: {e}")
        print("✅ 使用fallback機制")
        return fallback
    
# ========== 處理 group ==========
def process_group_question(group):
    import copy
    group_copy = copy.deepcopy(group)
    processed_sub_questions = []

    print(f"🔄 處理群組題目：{group_copy.get('group_question_text', '')}")

    for i, sub_question in enumerate(group_copy["sub_questions"]):
        question_text = sub_question["question_text"]
        image_path = sub_question.get("image_file")
        image_base64 = None

        if isinstance(image_path, list):
            image_file = image_path[0] if image_path else None
        else:
            image_file = image_path

        if image_file:
            image_base64 = read_image_base64(os.path.join("backend", "src", "picture", image_file))

        print(f"🔄 處理子題目 {i+1}：{question_text[:50]}...")

        main_prompt = main_agent_prompt_template.format(question_text=question_text)
        main_response = call_gemini_model(main_prompt, image_base64=image_base64)
        print(f"✅ 子題目 {i+1} 主代理人分析完成")

        secondary_prompt = secondary_agent_prompt_template.format(main_response=main_response)
        secondary_response = call_llama_model(secondary_prompt)
        print(f"✅ 子題目 {i+1} 次代理人分析完成")

        arbiter_prompt = arbiter_agent_prompt_template.format(
            main_response=main_response,
            secondary_response=secondary_response
        )
        arbiter_response = call_gemini_model(arbiter_prompt)
        print(f"✅ 子題目 {i+1} 仲裁代理人分析完成")

        try:
            # 嘗試清理回應，移除可能的非JSON內容
            arbiter_response = arbiter_response.strip()
            if arbiter_response.startswith('```json'):
                arbiter_response = arbiter_response[7:]
            if arbiter_response.endswith('```'):
                arbiter_response = arbiter_response[:-3]
            arbiter_response = arbiter_response.strip()
            
            print(f"🔍 子題目 {i+1} 仲裁回應：{arbiter_response[:100]}...")
            
            result = json.loads(arbiter_response)
            if isinstance(result, list) and result:
                # 確保結果包含所有原始欄位
                processed_sub_question = copy.deepcopy(sub_question)
                processed_sub_question.update(result[0])
                print(f"✅ 子題目 {i+1} JSON解析成功")
                processed_sub_questions.append(processed_sub_question)
            else:
                raise ValueError("仲裁輸出格式錯誤")
        except Exception as e:
            print(f"⚠️ 子題目 {i+1} JSON解析失敗：{e}")
            fallback = copy.deepcopy(sub_question)
            # 確保所有新增欄位都有預設值
            fallback.setdefault("answer", "")
            fallback.setdefault("detail-answer", "")
            fallback.setdefault("key-points", "")
            fallback.setdefault("difficulty level", "")
            fallback.setdefault("error reason", f"仲裁解析錯誤: {e}")
            print(f"✅ 子題目 {i+1} 使用fallback機制")
            processed_sub_questions.append(fallback)

    group_copy["sub_questions"] = processed_sub_questions
    return group_copy

# ========== 合併 ==========
def process_all_questions(questions):
    results = []
    count = 0
    total_questions = len(questions)

    for i, q in enumerate(questions, 1):
        try:
            if q["type"] == "group":
                print(f"🔄 處理群組題目 ({i}/{total_questions})：{q.get('group_question_text', '')}，共 {len(q['sub_questions'])} 題")
                group_result = process_group_question(q)
                results.append(group_result)
                count += len(q['sub_questions'])
                print(f"✅ 群組題目處理完成，已處理 {count} 題")
            else:
                count += 1
                print(f"🔄 處理第 {count} 題 ({i}/{total_questions})...")
                result = process_question(q)
                results.append(result)
                print(f"✅ 第 {count} 題處理完成")
        except Exception as e:
            print(f"❌ 處理第 {i} 題時發生錯誤：{e}")
            # 確保即使出錯也能繼續處理其他題目
            if q["type"] == "group":
                results.append(q)  # 保留原始群組題目
            else:
                results.append(q)  # 保留原始題目

    return results




if __name__ == "__main__":
    with open("../data/grouped_exam_processed.json", "r", encoding="utf-8") as f:
        questions = json.load(f)

    results = process_all_questions(questions)
    with open("../data/results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("\n✅ 所有題目處理完成，結果已儲存至 results.json")
    print(f"🔍 共處理 {len(results)} 題目。")