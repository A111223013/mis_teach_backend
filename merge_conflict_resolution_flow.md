# 合併衝突解決流程圖

## 系統架構流程

```mermaid
graph TD
    A[前端請求] --> B{請求類型}
    
    B -->|測驗提交| C[quiz.py /submit-quiz]
    B -->|AI教學對話| D[ai_teacher.py /ai-tutoring]
    B -->|獲取考卷數據| E[quiz.py /get-quiz-from-database]
    B -->|獲取測驗結果| F[quiz.py /get-quiz-result]
    
    C --> G{檢查題目數據來源}
    G -->|前端傳遞| H[使用前端題目數據]
    G -->|資料庫讀取| I[從SQL模板獲取題目]
    
    H --> J[AI批量評分]
    I --> J
    J --> K[儲存結果到SQL]
    K --> L[返回評分結果]
    
    D --> M[RAG系統處理]
    M --> N[返回AI教學回應]
    
    E --> O[從MongoDB獲取考卷]
    O --> P[格式化題目數據]
    P --> Q[返回考卷數據]
    
    F --> R[從SQL獲取歷史記錄]
    R --> S[從MongoDB獲取題目詳情]
    S --> T[返回完整結果]
    
    subgraph "資料庫層"
        U[(MongoDB)]
        V[(MySQL)]
    end
    
    H --> U
    I --> V
    O --> U
    R --> V
    S --> U
    K --> V
```

## 主要修改內容

### 1. quiz.py 新增功能
- ✅ 添加 `get_quiz_from_database()` 函數
- ✅ 添加 `/get-quiz-from-database` 端點
- ✅ 修復 `submit_quiz()` 中的 `questions_data` 變數未定義問題
- ✅ 添加必要的 import 語句

### 2. 功能整合
- ✅ 統一考卷數據獲取邏輯
- ✅ 保持向後兼容性
- ✅ 支持前端傳遞題目數據和資料庫讀取兩種模式

### 3. 錯誤處理
- ✅ 完善的異常處理機制
- ✅ 詳細的日誌記錄
- ✅ 用戶友好的錯誤訊息

## 數據流程

```mermaid
sequenceDiagram
    participant F as 前端
    participant Q as quiz.py
    participant A as ai_teacher.py
    participant M as MongoDB
    participant S as MySQL
    
    F->>Q: POST /submit-quiz
    Q->>Q: 檢查 questions_data
    alt 有前端數據
        Q->>Q: 使用前端題目數據
    else 無前端數據
        Q->>S: 查詢模板
        S->>M: 獲取題目詳情
        M->>Q: 返回題目數據
    end
    Q->>Q: AI批量評分
    Q->>S: 儲存結果
    Q->>F: 返回評分結果
    
    F->>Q: POST /get-quiz-from-database
    Q->>M: 查詢考卷數據
    M->>Q: 返回考卷
    Q->>F: 返回格式化數據
    
    F->>A: POST /ai-tutoring
    A->>A: RAG系統處理
    A->>F: 返回AI回應
```

## 技術要點

1. **模組化設計**: 將考卷數據獲取邏輯封裝為獨立函數
2. **靈活性**: 支持多種數據來源（前端傳遞、資料庫讀取）
3. **可擴展性**: 易於添加新的考卷類型和評分方式
4. **錯誤恢復**: 完善的錯誤處理和日誌記錄
5. **性能優化**: 批量處理和緩存機制

## 測試建議

1. 測試前端傳遞題目數據的場景
2. 測試從資料庫讀取題目的場景
3. 測試AI評分的準確性
4. 測試錯誤處理機制
5. 測試性能表現
