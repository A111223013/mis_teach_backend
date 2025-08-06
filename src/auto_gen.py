from autogen import AssistantAgent
import os

answer_grader = AssistantAgent(
    name="AnswerGraderAgent",
    llm_config={
        "config_list": [{
            "model": "gemini-2.5-flash",
            "api_key": "AIzaSyAwJ_e-baluaPPe4NHU-GWR0vf6FXD-BG8"
        }],
        "temperature": 0.3,
    },
    system_message=(
        "你是一位專業的資管系教授，負責判斷改考卷並提供錯誤原因"
        "請檢查答案、解釋為什麼正確或錯誤，並給學生簡明易懂的指導。"
    )
)
study_grader = AssistantAgent(
    name="studyGraderAgent",
    llm_config={
        "config_list": [{
            "model": "gemini-2.5-flash",
            "api_key": "AIzaSyCHbkAjiy2O6syJDU5g1GqmMjjS9rjwRAs"
        }],
        "temperature": 0.3,
    },
    system_message=(
        "你是一位專業的資管系教授，負責判斷改考卷並提供錯誤原因"
        "請檢查答案、解釋為什麼正確或錯誤，並給學生簡明易懂的指導。"
    )
)


def grade_question(question, correct_answer, user_answer):  ##批改題目
    grading_prompt = f"""
    你是一位資管系教授，請批改下列題目並給予評分與教學回饋。

    【題目】
    {question}

    【正確答案】
    {correct_answer}

    【學生作答】
    {user_answer}

   請回傳以下 JSON 格式，不要有其他解說文字：

{{
  "score": 0.0 ~ 1.0,
  "is_correct": true or false,
  "error_reason": "錯誤原因"
}}
"""
    response = answer_grader.generate_reply(grading_prompt)
    return response



def study_question(question, error_reason, user_answer):  ##批改題目
    grading_prompt = f"""
    你是一位資管系教授，請看完題目後，給予學生學習建議

    【題目】
    {question}

    【錯誤原因】
    {error_reason}

    【學生作答】
    {user_answer}
    
   請給出：
    1️. 學習建議
    2️. 延伸例句
"""
    response = study_grader.generate_reply(grading_prompt)
    return response

