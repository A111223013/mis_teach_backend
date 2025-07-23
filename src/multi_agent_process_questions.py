import os
import base64
import json
import requests
import google.generativeai as genai



# ========== Gemini API Key ==========
GEMINI_API_KEY = os.environ.get("AIzaSyCYsh5zsAH-DE4ChAD8PMT1xIvNw1YSWzQ", "AIzaSyBad7mpaX-fPPtpjbcgZ1JpKOBPJZJkmf4")

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

【題目內容】
{question_text}
"""

secondary_agent_prompt_template = """
你是「計算機概論判題系統」中的次要代理人 LLaMA 3.1。

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
你是「計算機概論判題系統」中的仲裁代理人 Gemini 2.5，當主代理人與次代理人意見不一致時，由你做出最終判斷。

請閱讀以下兩位代理人的意見後，完成以下任務，並將輸出結果**嚴格按照指定的 JSON 陣列格式（list of dict）**產出：

【主代理人分析】
{main_response}

【次代理人回應】
{secondary_response}

【任務說明】

請整合上述兩位代理人的回答，完成題目欄位的整合與補全，並遵守以下格式規範：

---

【輸出規則】

1. 請輸出一個「包含 1 筆題目資料的 JSON 陣列」（即 `[{{...}}]` 形式），即使只有一題，也不要省略 list 包裝。
2. 必須保留題目原本的所有欄位（例如：type、question_text、question_id、school、department、year... 等）。
3. 將 `"answer"` 欄位移動到 `"image_file"` 欄位之後。
4. 新增以下 4 個欄位（請務必補齊）：
   - `"detail-answer"`：提供清楚且完整的解題詳解。
   - `"key-points"`：請從以下 12 個選項中擇一填入（必填）：
     `"基本計概"、"數位邏輯"、"作業系統"、"程式語言"、"資料結構"、"網路"、"資料庫"、"AI與機器學習"、"資訊安全"、"雲端與虛擬化"、"MIS"、"軟體工程與系統開發"`
   - `"difficulty level"`：只能填入 `"簡單"`、`"中等"` 或 `"困難"`（必填）。
   - `"error reason"`：若主代理人與次代理人有「衝突或不同意見」，請填入簡短說明，否則留空字串。
5. 若題型與原始 `"answer_type"` 不一致，請採用主代理人提供的答案更新 `"answer_type"` 欄位。
6. 除上述調整，其餘原始欄位請勿遺漏，並保留原始順序與內容。

---

【輸出格式】

請以如下格式（list of one dict）回傳整合後的仲裁判斷結果，不要回傳任何解釋說明或額外文字，並以嚴格的 JSON 格式輸出：

[{{  
  "answer": "請按照仲裁結果填入簡要答案",  
  "detail-answer": "請按照仲裁結果填入詳細答案",  
  "key-points": "按照主代理人提供的關鍵點填寫，從以下選項中擇一：基本計概、數位邏輯、作業系統、程式語言、資料結構、網路、資料庫、AI與機器學習、資訊安全、雲端與虛擬化、MIS、軟體工程與系統開發",  
  "difficulty level": "按照仲裁結果填寫難度等級，只能填入：簡單、中等、困難",  
  "error reason": "若主代理人與次代理人有「衝突或不同意見」，請填入簡短說明，否則留空字串"  
}}]

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
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "llama3:8b",
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "max_tokens": 1024
            }
        }
    )
    if response.status_code == 200:
        return response.json()["response"].strip()
    else:
        raise Exception(f"Ollama 回應失敗：{response.status_code} - {response.text}")

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

    main_prompt = main_agent_prompt_template.format(question_text=question_text)
    main_response = call_gemini_model(main_prompt, image_base64=image_base64)

    secondary_prompt = secondary_agent_prompt_template.format(main_response=main_response)
    secondary_response = call_llama_model(secondary_prompt)

    arbiter_prompt = arbiter_agent_prompt_template.format(
        main_response=main_response,
        secondary_response=secondary_response
    )
    arbiter_response = call_gemini_model(arbiter_prompt)

    try:
        result = json.loads(arbiter_response)
        if isinstance(result, list) and result:
            return result[0]  # 回傳題目結構（仲裁後格式）
        else:
            raise ValueError("仲裁輸出格式不正確")
    except Exception as e:
        # 若解析失敗，回傳原始題目但補齊新欄位
        fallback = copy.deepcopy(question)
        fallback["answer"] = ""
        fallback["detail-answer"] = ""
        fallback["key-points"] = ""
        fallback["difficulty level"] = ""
        fallback["error reason"] = f"仲裁解析錯誤: {e}"
        return fallback
    
# ========== 處理 group ==========
def process_group_question(group):
    import copy
    group_copy = copy.deepcopy(group)
    processed_sub_questions = []

    for sub_question in group_copy["sub_questions"]:
        question_text = sub_question["question_text"]
        image_path = sub_question.get("image_file")
        image_base64 = None

        if isinstance(image_path, list):
            image_file = image_path[0] if image_path else None
        else:
            image_file = image_path

        if image_file:
            image_base64 = read_image_base64(os.path.join("backend", "src", "picture", image_file))

        main_prompt = main_agent_prompt_template.format(question_text=question_text)
        main_response = call_gemini_model(main_prompt, image_base64=image_base64)

        secondary_prompt = secondary_agent_prompt_template.format(main_response=main_response)
        secondary_response = call_llama_model(secondary_prompt)

        arbiter_prompt = arbiter_agent_prompt_template.format(
            main_response=main_response,
            secondary_response=secondary_response
        )
        arbiter_response = call_gemini_model(arbiter_prompt)

        try:
            result = json.loads(arbiter_response)
            if isinstance(result, list) and result:
                processed_sub_questions.append(result[0])
            else:
                raise ValueError("仲裁輸出格式錯誤")
        except Exception as e:
            fallback = copy.deepcopy(sub_question)
            fallback["answer"] = ""
            fallback["detail-answer"] = ""
            fallback["key-points"] = ""
            fallback["difficulty level"] = ""
            fallback["error reason"] = f"仲裁解析錯誤: {e}"
            processed_sub_questions.append(fallback)

    group_copy["sub_questions"] = processed_sub_questions
    return group_copy

# ========== 合併 ==========
def process_all_questions(questions):
    results = []
    count = 0

    for q in questions:
        if q["type"] == "group":
            print(f"🔄 處理群組題目：{q.get('group_question_text', '')}，共 {len(q['sub_questions'])} 題")
            group_result = process_group_question(q)
            results.append(group_result)
            count += len(q['sub_questions'])
            print(f"已處理 {count} 題")
        else:
            count += 1
            print(f"🔄 處理第 {count} 題...")
            result = process_question(q)
            results.append(result)

    return results




if __name__ == "__main__":
    with open("../data/grouped_exam_processed_test.json", "r", encoding="utf-8") as f:
        questions = json.load(f)

    results = process_all_questions(questions)
    with open("../data/results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("\n✅ 所有題目處理完成，結果已儲存至 results.json")
    print(f"🔍 共處理 {len(results)} 題目。")