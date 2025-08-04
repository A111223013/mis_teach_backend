import json
import os
import glob
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
import shutil

class ImageViewer:
    def __init__(self, parent, image_path, image_type):
        self.parent = parent
        self.image_path = image_path
        self.image_type = image_type
        
        # 建立新視窗
        self.window = tk.Toplevel(parent)
        self.window.title(f"{image_type} - {os.path.basename(image_path)}")
        self.window.geometry("800x600")
        
        # 建立滾動框架
        canvas = tk.Canvas(self.window)
        scrollbar_y = ttk.Scrollbar(self.window, orient="vertical", command=canvas.yview)
        scrollbar_x = ttk.Scrollbar(self.window, orient="horizontal", command=canvas.xview)
        
        self.scrollable_frame = ttk.Frame(canvas)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        
        # 載入並顯示圖片
        try:
            image = Image.open(image_path)
            photo = ImageTk.PhotoImage(image)
            
            label = ttk.Label(self.scrollable_frame, image=photo)
            label.image = photo
            label.pack(padx=10, pady=10)
            
        except Exception as e:
            error_label = ttk.Label(self.scrollable_frame, text=f"無法載入圖片: {e}")
            error_label.pack(padx=10, pady=10)
        
        # 複製按鈕
        copy_button = ttk.Button(self.scrollable_frame, text="複製圖片到剪貼簿", command=self.copy_image)
        copy_button.pack(pady=(0, 10))
        
        # 配置滾動條
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar_y.pack(side="right", fill="y")
        scrollbar_x.pack(side="bottom", fill="x")
    
    def copy_image(self):
        """複製圖片到剪貼簿"""
        try:
            desktop_path = os.path.expanduser("~/Desktop")
            copy_path = os.path.join(desktop_path, f"copied_{os.path.basename(self.image_path)}")
            shutil.copy2(self.image_path, copy_path)
            messagebox.showinfo("成功", f"圖片已複製到桌面: {os.path.basename(copy_path)}")
        except Exception as e:
            messagebox.showerror("錯誤", f"複製失敗: {e}")

class ErrorQuestionProcessor:
    def __init__(self, root):
        self.root = root
        self.root.title("錯誤題目處理器")
        self.root.geometry("1400x900")
        
        # 載入資料
        self.load_data()
        
        # 當前題目索引
        self.current_index = 0
        
        # 建立UI
        self.setup_ui()
        
        # 載入第一題
        self.load_current_question()
    
    def load_data(self):
        """載入JSON檔案並篩選有錯誤的題目"""
        try:
            with open("backend/src/error_questions.json", 'r', encoding='utf-8') as f:
                all_questions = json.load(f)
            
            # 篩選出error reason不為空的題目
            self.error_questions = []
            for question in all_questions:
                error_reason = question.get('error reason', '')
                if error_reason and error_reason.strip():
                    self.error_questions.append(question)
            
            print(f"載入了 {len(all_questions)} 個題目，其中 {len(self.error_questions)} 個有錯誤")
            
            # 調試信息：顯示前幾個有錯誤的題目
            if self.error_questions:
                print(f"前3個有錯誤的題目:")
                for i, q in enumerate(self.error_questions[:3]):
                    print(f"  {i+1}. {q.get('year', '')} {q.get('school', '')} {q.get('department', '')} - {q.get('error reason', '')[:100]}...")
            
        except Exception as e:
            messagebox.showerror("錯誤", f"無法載入 error_questions.json: {e}")
            print(f"載入錯誤: {e}")
            self.error_questions = []
    
    def setup_ui(self):
        """建立使用者介面"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置網格權重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # 題目資訊區域
        info_frame = ttk.LabelFrame(main_frame, text="題目資訊", padding="5")
        info_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 年度、學校、系所、題號
        ttk.Label(info_frame, text="年度:").grid(row=0, column=0, sticky=tk.W)
        self.year_var = tk.StringVar()
        ttk.Entry(info_frame, textvariable=self.year_var, state='readonly', width=10).grid(row=0, column=1, sticky=tk.W, padx=(5, 20))
        
        ttk.Label(info_frame, text="學校:").grid(row=0, column=2, sticky=tk.W)
        self.school_var = tk.StringVar()
        ttk.Entry(info_frame, textvariable=self.school_var, state='readonly', width=25).grid(row=0, column=3, sticky=tk.W, padx=(5, 20))
        
        ttk.Label(info_frame, text="系所:").grid(row=0, column=4, sticky=tk.W)
        self.department_var = tk.StringVar()
        ttk.Entry(info_frame, textvariable=self.department_var, state='readonly', width=30).grid(row=0, column=5, sticky=tk.W, padx=(5, 20))
        
        ttk.Label(info_frame, text="題號:").grid(row=0, column=6, sticky=tk.W)
        self.question_number_var = tk.StringVar()
        ttk.Entry(info_frame, textvariable=self.question_number_var, state='readonly', width=10).grid(row=0, column=7, sticky=tk.W, padx=(5, 0))
        
        # 錯誤原因
        ttk.Label(info_frame, text="錯誤原因 (可編輯):").grid(row=1, column=0, sticky=tk.W, pady=(10, 0))
        self.error_reason_text = tk.Text(info_frame, height=2, width=80, wrap=tk.WORD)
        self.error_reason_text.grid(row=1, column=1, columnspan=7, sticky=(tk.W, tk.E), padx=(5, 0), pady=(10, 0))
        
        # 題目內容
        ttk.Label(info_frame, text="題目 (可編輯):").grid(row=2, column=0, sticky=tk.W, pady=(10, 0))
        self.question_text = tk.Text(info_frame, height=4, width=80, wrap=tk.WORD)
        self.question_text.grid(row=2, column=1, columnspan=7, sticky=(tk.W, tk.E), padx=(5, 0), pady=(10, 0))
        
        # 選項顯示區域
        ttk.Label(info_frame, text="選項 (可編輯):").grid(row=3, column=0, sticky=tk.W, pady=(10, 0))
        self.options_text = tk.Text(info_frame, height=3, width=80, wrap=tk.WORD)
        self.options_text.grid(row=3, column=1, columnspan=7, sticky=(tk.W, tk.E), padx=(5, 0), pady=(10, 0))
        
        # 左側：圖片顯示區域
        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(0, weight=1)
        
        # 圖片顯示區域
        image_frame = ttk.LabelFrame(left_frame, text="圖片", padding="5")
        image_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        image_frame.columnconfigure(0, weight=1)
        image_frame.rowconfigure(0, weight=1)
        
        # 圖片顯示
        self.image_canvas = tk.Canvas(image_frame, bg='white')
        self.image_canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 圖片滾動條
        image_scrollbar = ttk.Scrollbar(image_frame, orient=tk.VERTICAL, command=self.image_canvas.yview)
        image_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.image_canvas.configure(yscrollcommand=image_scrollbar.set)
        
        # 圖片內部框架
        self.image_inner_frame = ttk.Frame(self.image_canvas)
        self.image_canvas.create_window((0, 0), window=self.image_inner_frame, anchor=tk.NW)
        
        # 右側：修正輸入區域
        answer_frame = ttk.LabelFrame(main_frame, text="修正輸入", padding="5")
        answer_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        answer_frame.columnconfigure(1, weight=1)
        
        # 題型
        ttk.Label(answer_frame, text="題型:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.answer_type_var = tk.StringVar(value="single-choice")
        type_combo = ttk.Combobox(answer_frame, textvariable=self.answer_type_var,
                                 values=["single-choice", "multiple-choice", "fill-in-the-blank", "short-answer", "long-answer", "coding-answer", "draw-answer", "true-false"], state="readonly", width=15)
        type_combo.grid(row=0, column=1, sticky=tk.W, padx=(5, 0), pady=(0, 5))
        
        # 答案
        ttk.Label(answer_frame, text="答案:").grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        self.answer_text = tk.Text(answer_frame, height=3, width=50, wrap=tk.WORD)
        self.answer_text.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=(0, 5))
        
        # 詳答
        ttk.Label(answer_frame, text="詳答:").grid(row=2, column=0, sticky=tk.W, pady=(0, 5))
        self.detail_answer_text = tk.Text(answer_frame, height=4, width=50, wrap=tk.WORD)
        self.detail_answer_text.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=(0, 5))
        
        # 知識點
        ttk.Label(answer_frame, text="知識點:").grid(row=3, column=0, sticky=tk.W, pady=(0, 5))
        self.knowledge_text = tk.Text(answer_frame, height=2, width=50, wrap=tk.WORD)
        self.knowledge_text.grid(row=3, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=(0, 5))
        
        # 難易度
        ttk.Label(answer_frame, text="難易度:").grid(row=4, column=0, sticky=tk.W, pady=(0, 5))
        self.difficulty_var = tk.StringVar(value="中等")
        difficulty_combo = ttk.Combobox(answer_frame, textvariable=self.difficulty_var, 
                                       values=["簡單", "中等", "困難"], state="readonly", width=10)
        difficulty_combo.grid(row=4, column=1, sticky=tk.W, padx=(5, 0), pady=(0, 5))
        
        # 按鈕區域
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=(10, 0))
        
        ttk.Button(button_frame, text="上一題", command=self.previous_question).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="下一題", command=self.next_question).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="儲存修正", command=self.save_correction).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="儲存檔案", command=self.save_file).pack(side=tk.LEFT, padx=(0, 10))
        
        # 進度顯示
        self.progress_var = tk.StringVar()
        ttk.Label(button_frame, textvariable=self.progress_var).pack(side=tk.RIGHT)
    
    def load_current_question(self):
        """載入當前題目"""
        if not self.error_questions or self.current_index >= len(self.error_questions):
            return
        
        question = self.error_questions[self.current_index]
        
        # 更新題目資訊
        self.year_var.set(question.get('year', ''))
        self.school_var.set(question.get('school', ''))
        self.department_var.set(question.get('department', ''))
        self.question_number_var.set(question.get('question_number', ''))
        
        # 更新錯誤原因
        self.error_reason_text.delete(1.0, tk.END)
        self.error_reason_text.insert(1.0, question.get('error reason', ''))
        
        # 更新題目內容
        self.question_text.delete(1.0, tk.END)
        self.question_text.insert(1.0, question.get('question_text', ''))
        
        # 更新選項內容
        self.options_text.delete(1.0, tk.END)
        options = question.get('options', {})
        if options:
            options_text = ""
            if isinstance(options, dict):
                # 如果是字典格式
                for key, value in options.items():
                    options_text += f"{key}. {value}\n"
            elif isinstance(options, list):
                # 如果是列表格式
                for i, value in enumerate(options):
                    option_letter = chr(ord('a') + i)  # a, b, c, d...
                    options_text += f"{option_letter}. {value}\n"
            self.options_text.insert(1.0, options_text)
        
        # 載入圖片
        self.load_images(question)
        
        # 更新進度
        self.progress_var.set(f"第 {self.current_index + 1} 題 / 共 {len(self.error_questions)} 題")
        
        # 清空輸入欄位
        self.clear_input_fields()
        
        # 載入現有的答案和詳答
        if question.get('answer'):
            self.answer_text.insert(1.0, question.get('answer', ''))
        if question.get('detail-answer'):
            self.detail_answer_text.insert(1.0, question.get('detail-answer', ''))
        if question.get('key-points'):
            self.knowledge_text.insert(1.0, question.get('key-points', ''))
        if question.get('difficulty level'):
            self.difficulty_var.set(question.get('difficulty level', '中等'))
        if question.get('answer_type'):
            self.answer_type_var.set(question.get('answer_type', 'single-choice'))
    
    def load_images(self, question):
        """載入題目相關的圖片"""
        # 清除現有圖片
        for widget in self.image_inner_frame.winfo_children():
            widget.destroy()
        
        year = question.get('year', '')
        school = question.get('school', '')
        department = question.get('department', '')
        
        # 尋找原始考卷圖片
        exam_pattern = f"{year}-*-{school}-{department}_page_*.png"
        exam_files = glob.glob(os.path.join("ocr/exam_img", exam_pattern))
        
        # 尋找附圖
        picture_pattern = f"{year}-*-{school}-{department}_page_*_*.png"
        picture_files = glob.glob(os.path.join("backend/src/picture", picture_pattern))
        
        all_images = []
        if exam_files:
            all_images.extend([(f, "原始考卷") for f in exam_files])
        if picture_files:
            all_images.extend([(f, "附圖") for f in picture_files])
        
        # 顯示圖片
        for i, (image_path, image_type) in enumerate(all_images):
            try:
                # 建立圖片標籤
                label = ttk.Label(self.image_inner_frame, text=f"{image_type}: {os.path.basename(image_path)}")
                label.grid(row=i*3, column=0, sticky=tk.W, pady=(10, 0))
                
                # 載入並顯示縮圖
                image = Image.open(image_path)
                # 調整圖片大小
                max_width = 400
                max_height = 300
                image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
                
                photo = ImageTk.PhotoImage(image)
                
                # 建立圖片標籤
                img_label = ttk.Label(self.image_inner_frame, image=photo)
                img_label.image = photo  # 保持參考
                img_label.grid(row=i*3+1, column=0, pady=(5, 5))
                
                # 建立按鈕框架
                button_frame = ttk.Frame(self.image_inner_frame)
                button_frame.grid(row=i*3+2, column=0, pady=(0, 10))
                
                # 放大按鈕
                ttk.Button(button_frame, text="放大查看", 
                          command=lambda path=image_path, img_type=image_type: self.show_image_viewer(path, img_type)).pack(side=tk.LEFT, padx=(0, 5))
                
                # 複製按鈕（僅對附圖顯示）
                if image_type == "附圖":
                    ttk.Button(button_frame, text="複製圖片", 
                              command=lambda path=image_path: self.copy_image(path)).pack(side=tk.LEFT)
                
            except Exception as e:
                error_label = ttk.Label(self.image_inner_frame, text=f"無法載入圖片 {image_path}: {e}")
                error_label.grid(row=i*3+1, column=0, pady=(5, 10))
        
        # 更新滾動區域
        self.image_inner_frame.update_idletasks()
        self.image_canvas.configure(scrollregion=self.image_canvas.bbox("all"))
    
    def show_image_viewer(self, image_path, image_type):
        """顯示圖片查看器"""
        ImageViewer(self.root, image_path, image_type)
    
    def copy_image(self, image_path):
        """複製圖片"""
        try:
            desktop_path = os.path.expanduser("~/Desktop")
            copy_path = os.path.join(desktop_path, f"copied_{os.path.basename(image_path)}")
            shutil.copy2(image_path, copy_path)
            messagebox.showinfo("成功", f"圖片已複製到桌面: {os.path.basename(copy_path)}")
        except Exception as e:
            messagebox.showerror("錯誤", f"複製失敗: {e}")
    
    def clear_input_fields(self):
        """清空輸入欄位"""
        self.answer_type_var.set("single-choice")
        self.answer_text.delete(1.0, tk.END)
        self.detail_answer_text.delete(1.0, tk.END)
        self.knowledge_text.delete(1.0, tk.END)
        self.difficulty_var.set("中等")
    
    def save_correction(self):
        """儲存當前題目的修正"""
        if not self.error_questions or self.current_index >= len(self.error_questions):
            return
        
        # 取得輸入的資料
        answer_type = self.answer_type_var.get()
        answer = self.answer_text.get(1.0, tk.END).strip()
        detail_answer = self.detail_answer_text.get(1.0, tk.END).strip()
        knowledge = self.knowledge_text.get(1.0, tk.END).strip()
        difficulty = self.difficulty_var.get()
        
        # 取得題目內容的修改
        error_reason = self.error_reason_text.get(1.0, tk.END).strip()
        question_text = self.question_text.get(1.0, tk.END).strip()
        options_text = self.options_text.get(1.0, tk.END).strip()
        
        if not answer:
            messagebox.showwarning("警告", "請輸入答案")
            return
        
        # 更新當前題目
        current_question = self.error_questions[self.current_index]
        current_question['answer_type'] = answer_type
        current_question['answer'] = answer
        current_question['detail-answer'] = detail_answer
        current_question['key-points'] = knowledge
        current_question['difficulty level'] = difficulty
        
        # 更新題目內容相關字段
        current_question['error reason'] = error_reason
        current_question['question_text'] = question_text
        
        # 處理選項更新
        if options_text.strip():
            # 嘗試解析選項文本為字典格式
            options = {}
            lines = options_text.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line and '.' in line:
                    key, value = line.split('.', 1)
                    options[key.strip()] = value.strip()
            current_question['options'] = options
        
        messagebox.showinfo("成功", "題目修正已儲存")
    
    def save_file(self):
        """儲存整個檔案"""
        try:
            # 重新載入原始檔案
            with open("backend/src/error_questions.json", 'r', encoding='utf-8') as f:
                all_questions = json.load(f)
            
            updated_count = 0
            # 更新有錯誤的題目
            for error_q in self.error_questions:
                for i, original_q in enumerate(all_questions):
                    # 使用更可靠的匹配條件：年度、學校、系所、題號
                    if (original_q.get('year') == error_q.get('year') and
                        original_q.get('school') == error_q.get('school') and
                        original_q.get('department') == error_q.get('department') and
                        original_q.get('question_number') == error_q.get('question_number')):
                        # 更新原始檔案中的題目
                        all_questions[i].update(error_q)
                        updated_count += 1
                        print(f"已更新題目: {error_q.get('year')} {error_q.get('school')} {error_q.get('department')} 題號:{error_q.get('question_number')}")
                        break
            
            # 儲存檔案
            with open("backend/src/error_questions.json", 'w', encoding='utf-8') as f:
                json.dump(all_questions, f, ensure_ascii=False, indent=2)
            
            messagebox.showinfo("成功", f"檔案已儲存，共更新了 {updated_count} 個題目")
            
        except Exception as e:
            messagebox.showerror("錯誤", f"儲存失敗: {e}")
    
    def next_question(self):
        """下一題"""
        if self.current_index < len(self.error_questions) - 1:
            self.current_index += 1
            self.load_current_question()
        else:
            messagebox.showinfo("完成", "已處理完所有錯誤題目")
    
    def previous_question(self):
        """上一題"""
        if self.current_index > 0:
            self.current_index -= 1
            self.load_current_question()

def main():
    root = tk.Tk()
    app = ErrorQuestionProcessor(root)
    root.mainloop()

if __name__ == "__main__":
    main() 