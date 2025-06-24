import os
import json
import time
from datetime import datetime
from collections import Counter
import concurrent.futures
import shutil
from tqdm import tqdm
import threading

import google.generativeai as genai
from PIL import Image

# --- 組態設定 ---
API_KEYS = [
    "AIzaSyCnllszzkt3TMCpYq8vgbaaUWXCZzxJyk0", "AIzaSyDpI2FOAjUztmOK2x-K-AQtMhAtkUrNppY",
    "AIzaSyDlhMMaj4Owmw972C5uIMrq-mV71xvqf7I", "AIzaSyAz0QM_rV82V8ZopytpOPpQhiLTBROTxwU",
    "AIzaSyBKhBuTiOLtqh1_ZXDieFgyj6y_QiU28-s", "AIzaSyAxKs4FNJRnmZz6Fukz5qJDcX_Af46NkT4",
    "AIzaSyB6v3FEBazlViULPpfl8j6yw7sxMAGxnvg", "AIzaSyBa5Pm3ABDpqmZTTJHVI6GhF8b1h4T4Kj0",
    "AIzaSyB7inhc2xDJ3ZZmLujOR6hEeXaFtZZeRh4", "AIzaSyDxAbCMPA_aYZlvcpDlmVBpHinLxrEfDOg",
    "AIzaSyDdktjMeyQqmiM0Mj-rt6Tfr_yK80DomsQ", "AIzaSyBVBBtfqEbr-jV3h8JkCVES-GqhH1ebFlg",
    "AIzaSyDR6qAiFCRNqKMlXSm7x8InMLIGVDlI5-s",
]

# 創建一個全域的 lock 物件字典，每個暫存檔一個
file_locks = {i: threading.Lock() for i in range(len(API_KEYS))}

def chunk_list(data, num_chunks):
    """將一個列表盡可能均勻地分割成 N 個區塊"""
    k, m = divmod(len(data), num_chunks)
    return [data[i*k+min(i, m):(i+1)*k+min(i+1, m)] for i in range(num_chunks)]

def process_chunk(task_tuple):
    """
    工人執行緒的完整工作流程：處理一整個題庫區塊，並存入單一暫存檔。
    """
    worker_id, question_chunk, api_key, picture_dir, temp_dir = task_tuple
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        print(f"❌ 工人 {worker_id} API Key 初始化失敗: {e}")
        # 將錯誤寫入一個專門的錯誤日誌，而不是回傳
        error_log_path = os.path.join(temp_dir, f"error_log_{worker_id}.txt")
        with open(error_log_path, 'w', encoding='utf-8') as f:
            f.write(f"API Key init failed: {e}\n")
        return f"工人 #{worker_id} 失敗"

    temp_file_path = os.path.join(temp_dir, f"temp_chunk_{worker_id}.json")
    
    # 初始化暫存檔為一個空的 JSON 陣列 (使用二進位寫入)
    with open(temp_file_path, 'wb') as f:
        f.write(b'[]')

    progress_bar = tqdm(question_chunk, desc=f"工人 #{worker_id}", leave=False, position=worker_id)
    for i, item in enumerate(progress_bar):
        processed_item = item.copy()
        try:
            q_data = processed_item.get("question_data", processed_item)

            # --- 產生答案 ---
            answer_templates = { "single-choice": "請以單選題格式回答：", "multiple-choice": "請以多選題格式回答：", "true-false": "請以是非題格式回答：", "short-answer": "請以簡答題格式回答，詳述重點：", "long-answer": "請以詳題格式回答，條理分明：", "coding-answer": "請以程式碼範例形式回答：", "draw-answer": "請以繪圖描述的方式回答，並提供步驟：", "fill-in-the-blank": "請以填空題格式回答，並提供各空格答案：", "other": "請依題意回答：" }
            qtype = q_data.get("type", "other")
            template = answer_templates.get(qtype, answer_templates["other"])
            question_text = q_data.get("question_text", "")
            prompt_text = f"{template}\n{question_text}"
            options = q_data.get('options')
            if options and isinstance(options, list) and len(options) > 0:
                prompt_text += "\n選項："
                for opt in options: prompt_text += f"\n{opt}"
            answer_contents = [prompt_text]
            image_files = q_data.get('image_file')
            if image_files:
                for image_filename in image_files:
                    image_path = os.path.join(picture_dir, image_filename)
                    if os.path.exists(image_path): answer_contents.append(Image.open(image_path))
            answer_response = model.generate_content(answer_contents)
            q_data['answer'] = answer_response.text

            # --- 學科分類 ---
            # 為了讓分類更準確，將題目文字和選項組合在一起
            full_question_for_classification = q_data.get('question_text', '')
            classification_options = q_data.get('options')
            if classification_options and isinstance(classification_options, list) and len(classification_options) > 0:
                full_question_for_classification += "\n選項："
                for opt in classification_options:
                    full_question_for_classification += f"\n- {opt}"

            classification_prompt = f"""你是一位資訊工程領域的專家教授。請根據以下國際知名教科書的標準章節結構，精確分析考試題目的歸屬。

=== 題目資訊 ===
學校：{q_data.get('school', 'N/A')}
系所：{q_data.get('department', 'N/A')}
題目類型：{q_data.get('type', 'N/A')}
題目內容：{full_question_for_classification}

=== 標準教科書章節分類架構 ===
**1. 資料結構與演算法** (來源: "Introduction to Algorithms", Cormen et al.)
- Chapters: Elementary Data Structures, Trees, Hashing, Sorting, Graph Algorithms, Dynamic Programming, Greedy Algorithms.
**2. 作業系統** (來源: "Operating System Concepts", Silberschatz et al.)
- Chapters: Processes, Threads, CPU Scheduling, Synchronization, Deadlocks, Memory Management, File Systems.
**3. 資料庫系統** (來源: "Fundamentals of Database Systems", Elmasri & Navathe)
- Chapters: ER Model, Relational Model, SQL, Normalization, Transaction Processing, Concurrency Control.
**4. 電腦網路** (來源: "Computer Networks", Tanenbaum & Wetherall)
- Chapters: OSI Model, Physical/Data Link/Network/Transport/Application Layers, Network Security.
**5. 程式設計** (來源: "The C++ Programming Language", Stroustrup; "Effective Java", Bloch)
- Topics: Variables, Control Structures, Functions, OOP, Memory Management.
**6. 軟體工程** (來源: "Software Engineering", Sommerville)
- Chapters: Processes, Requirements, Design, Testing, Project Management.
**7. 資訊安全** (來源: "Cryptography and Network Security", Stallings)
- Chapters: Encryption, AES, RSA, Digital Signatures, Network Security.

請根據上述架構，將題目歸類到最適合的項目，並以嚴格的 JSON 格式輸出：
{{
    "主要學科": "對應上述7個領域之一",
    "教科書來源": "具體的教科書名稱與作者",
    "教科書章節": "對應標準教科書的具體章節名稱（英文）",
    "考點單元": "該章節下的具體考點或技術要點",
    "相關概念": ["相關的重要概念或技術", "最多3個"],
    "分析說明": "基於教科書架構的專業分析說明"
}}
"""
            classification_response = model.generate_content(classification_prompt)
            response_text = classification_response.text
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start != -1:
                classification = json.loads(response_text[json_start:json_end])
                processed_item.update(classification)
            else:
                processed_item['分析說明'] = "API 回應格式異常"
            processed_item['gemini_process_timestamp'] = datetime.now().isoformat()
        except Exception as e:
            processed_item['error'] = str(e)
            
        # 使用線程鎖和二進位模式來安全地即時寫入
        with file_locks[worker_id]:
            with open(temp_file_path, 'rb+') as temp_f:
                # 檢查檔案大小來判斷是否為初始狀態 '[]'
                temp_f.seek(0, os.SEEK_END)
                is_initial_file = temp_f.tell() <= 2
                
                # 移動到檔案的倒數第二個位置（在 ']' 前面）
                temp_f.seek(-1, os.SEEK_END)
                
                # 如果檔案不是剛初始化的，就先加上逗號和換行
                if not is_initial_file:
                    temp_f.write(b',\n')
                
                # 將 Python 物件轉為格式化的 JSON 字串，再編碼為 bytes
                new_data_bytes = json.dumps(processed_item, ensure_ascii=False, indent=4).encode('utf-8')
                temp_f.write(new_data_bytes)
                
                # 寫回結尾的 ']'
                temp_f.write(b'\n]')

    return f"工人 #{worker_id} 已完成。"

if __name__ == "__main__":
    if not API_KEYS or not all(API_KEYS):
        print("❌ 錯誤：請在 API_KEYS 列表中填入至少一個有效的 API Key。")
        exit()
        
    print(f"🚀 Gemini 區塊化並行處理系統已啟動 (共 {len(API_KEYS)} 個工人) 🚀")
    print("="*70)
    
    input_file_path = 'correct_exam.json'
    picture_dir = 'picture'
    output_dir = 'output'
    temp_dir = os.path.join(output_dir, 'temp_chunks')
    
    if os.path.exists(temp_dir): shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)
    os.makedirs(picture_dir, exist_ok=True)

    if not os.path.exists(input_file_path):
        print(f"❌ 錯誤：找不到輸入檔案！ 路徑: {os.path.abspath(input_file_path)}")
        exit()

    with open(input_file_path, 'r', encoding='utf-8') as f:
        all_questions = json.load(f)

    num_workers = len(API_KEYS)
    question_chunks = chunk_list(all_questions, num_workers)
    
    tasks = []
    for i, chunk in enumerate(question_chunks):
        if not chunk: continue
        tasks.append((i, chunk, API_KEYS[i % len(API_KEYS)], picture_dir, temp_dir))

    print(f"⏳ 將 {len(all_questions)} 道題目分割成 {len(tasks)} 個區塊，開始並行處理...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
        list(tqdm(executor.map(process_chunk, tasks), total=len(tasks), desc="總進度"))
    
    print("\n🔄 所有區塊處理完成，開始從暫存區合併檔案...")
    final_results = []
    all_files_found = True
    for i in range(len(tasks)):
        temp_path = os.path.join(temp_dir, f"temp_chunk_{i}.json")
        if os.path.exists(temp_path):
            with open(temp_path, 'r', encoding='utf-8') as f:
                try:
                    # 現在可以直接讀取整個合法的 JSON 檔案
                    final_results.extend(json.load(f))
                except json.JSONDecodeError:
                    print(f"⚠️ 警告：暫存檔 {temp_path} 不是有效的 JSON 格式。")
                    all_files_found = False
        else:
            print(f"⚠️ 警告：找不到暫存檔 {temp_path}，最終結果可能不完整。")
            all_files_found = False
            
    output_file_path = os.path.join(output_dir, os.path.basename(input_file_path))
    try:
        with open(output_file_path, 'w', encoding='utf-8') as wf:
            json.dump(final_results, wf, ensure_ascii=False, indent=4)
        print(f"✅ 最終檔案已成功合併並儲存至: {os.path.abspath(output_file_path)}")
        if all_files_found:
            shutil.rmtree(temp_dir)
            print("🗑️ 已成功清理暫存資料夾。")
    except Exception as e:
        print(f"❌ 合併或儲存檔案時發生錯誤: {e}")

    successful_results = [r for r in final_results if 'error' not in r]
    failed_count = len(final_results) - len(successful_results)
    
    if successful_results:
        print("\n" + "="*60)
        print("📊 Gemini 分類結果統計")
        print("="*60)
        subjects = [item.get('主要學科', '未分類') for item in successful_results]
        subject_counts = Counter(subjects)
        print(f"\n🎓 主要學科分布 (共 {len(subject_counts)} 個):")
        for subject, count in subject_counts.most_common():
            print(f"  • {subject}: {count} 題")
        if failed_count > 0: print(f"\n❗️ {failed_count} 題處理失敗。")
        print("\n" + "="*60)
    elif failed_count > 0:
         print(f"\n❌ 所有 {failed_count} 題均處理失敗，請檢查錯誤訊息。") 