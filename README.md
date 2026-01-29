# MIS_Teach 後端系統

## 專案簡介

MIS_Teach 後端是一個基於 Flask 3.0 開發的智慧學習平台後端系統，提供完整的 RESTful API、AI 教學、測驗管理、學習分析等功能。整合多種資料庫（MySQL、MongoDB、Redis、Neo4j）、AI 服務（Google Gemini）、以及 LINE Bot 等外部服務。

## 技術架構

### 核心技術棧

- **框架**: Flask 3.0.3
- **語言**: Python 3.11+
- **資料庫**:
  - MySQL (SQLAlchemy 2.0.36)
  - MongoDB (PyMongo 4.10.1)
  - Redis 5.2.0
  - Neo4j 5.28.2 (知識圖譜)
- **AI 服務**: Google Gemini API
- **認證**: JWT (Flask-JWT-Extended 4.7.1)
- **其他**: Flask-CORS, Flask-Mail, LINE Bot SDK

### 主要依賴套件

- **Web 框架**: Flask, Flask-CORS, Flask-Mail
- **資料庫**: SQLAlchemy, PyMongo, redis, neo4j
- **AI/ML**: langchain 0.3.27, chromadb 1.0.16, sentence-transformers 5.1.0
- **文件處理**: PyMuPDF 1.26.3, pdf2image 1.17.0, unstructured 0.18.13
- **其他工具**: schedule 1.2.2, requests 2.32.3, beautifulsoup4 4.13.4

## 專案結構

```
backend/
├── app.py                          # Flask 應用主入口
├── config.py                       # 配置管理
├── accessories.py                  # 共用工具（資料庫、郵件、Redis 等）
├── requirements.txt                # Python 依賴
├── api.env                         # API 密鑰配置
├── security_key                    # JWT 安全密鑰
├── src/                            # 主要業務邏輯
│   ├── login.py                    # 登入 API
│   ├── register.py                 # 註冊 API
│   ├── dashboard.py                # 儀表板 API
│   ├── quiz.py                     # 測驗 API
│   ├── ai_quiz.py                  # AI 測驗 API
│   ├── ai_teacher.py               # AI 教學 API
│   ├── grade_answer.py             # 答案評分
│   ├── learning_analytics.py       # 學習分析 API
│   ├── materials_api.py            # 教材 API
│   ├── note.py                     # 筆記 API
│   ├── news_api.py                 # 新聞 API
│   ├── linebot.py                  # LINE Bot API
│   ├── web_ai_assistant.py         # 網頁 AI 助手
│   ├── website_guide.py            # 網站導覽
│   ├── website_knowledge_db.py     # 網站知識庫
│   ├── web_automation.py           # 網頁自動化
│   ├── memory_manager.py           # 記憶管理
│   ├── api.py                      # API 工具函數
│   └── rag_sys/                    # RAG 系統
│       ├── rag_ai_role.py          # RAG AI 角色定義
│       ├── rag_build.py            # RAG 建構
│       ├── config.py               # RAG 配置
│       └── data/                   # RAG 資料
│           ├── knowledge_db/       # ChromaDB 知識庫
│           ├── pdfs/               # PDF 教材
│           └── outputs/            # 輸出資料
├── tool/                           # 工具腳本
│   ├── insert_mongodb.py           # MongoDB 資料插入
│   ├── insert_test_school.py       # 測試學校資料插入
│   ├── init_neo4j_knowledge_graph.py # Neo4j 知識圖譜初始化
│   ├── init_news_table.py          # 新聞表初始化
│   ├── api_keys.py                 # API 密鑰管理
│   ├── web_crawler.py              # 網頁爬蟲
│   └── ...                         # 其他工具腳本
├── data/                           # 資料目錄
│   ├── materials/                  # Markdown 教材
│   └── ...                         # 其他資料
└── instance/                       # 實例目錄
    └── mis_teach.db                # SQLite 資料庫（開發用）
```

## 核心功能模組

### 1. 身份驗證系統 (`login.py`, `register.py`)

- 使用者註冊與郵件驗證
- JWT Token 認證
- Token 刷新機制
- 密碼加密（Flask-Bcrypt）
- 登入狀態管理

**主要端點**:
- `POST /login` - 使用者登入
- `POST /register` - 使用者註冊
- `POST /login/logout` - 登出

### 2. 測驗系統

#### 傳統測驗 (`quiz.py`)
- 測驗生成與管理
- 題目查詢與篩選
- 作答提交與評分
- 測驗結果查詢
- 支援多種題型

#### AI 測驗 (`ai_quiz.py`)
- AI 生成測驗
- 動態題目生成
- 概念導向測驗
- 難度自適應

**主要端點**:
- `POST /quiz/generate` - 生成測驗
- `POST /quiz/submit` - 提交測驗
- `GET /quiz/result/<quiz_id>` - 查詢結果
- `POST /ai_quiz/generate` - AI 生成測驗

### 3. AI 教學系統 (`ai_teacher.py`)

- 五階段學習流程管理
- RAG (Retrieval-Augmented Generation) 整合
- 學習會話管理
- 上下文記憶
- 學習進度追蹤

**主要端點**:
- `POST /ai_teacher/chat` - AI 教學對話
- `GET /ai_teacher/session/<session_id>` - 查詢會話
- `POST /ai_teacher/start` - 開始學習會話

### 4. RAG 系統 (`rag_sys/`)

#### RAG AI 角色 (`rag_ai_role.py`)
- 多階段教學策略
- 知識庫檢索
- 上下文理解
- 學習路徑規劃

#### RAG 建構 (`rag_build.py`)
- ChromaDB 向量資料庫建構
- PDF 文件處理與分塊
- 嵌入向量生成
- 知識庫更新

**功能特點**:
- 使用 ChromaDB 儲存向量嵌入
- 支援 PDF 文件解析
- 語義搜尋
- 上下文相關檢索

### 5. 學習分析系統 (`learning_analytics.py`)

- 學習趨勢分析
- 弱點識別
- 能力評估
- 進步追蹤
- AI 診斷與建議
- 學習路徑推薦

**主要端點**:
- `GET /api/learning-analytics/overview` - 總覽資料
- `GET /api/learning-analytics/trends` - 趨勢分析
- `GET /api/learning-analytics/weak-points` - 弱點分析
- `POST /api/learning-analytics/ai-diagnosis` - AI 診斷

### 6. 教材管理系統 (`materials_api.py`)

- Markdown 教材管理
- 教材列表查詢
- 教材內容檢索
- 進度追蹤

**主要端點**:
- `GET /materials/list` - 教材列表
- `GET /materials/<filename>` - 教材內容

### 7. 新聞系統 (`news_api.py`)

- IT 新聞聚合
- 新聞分類
- 關鍵字搜尋
- 新聞詳情

**主要端點**:
- `GET /api/news` - 新聞列表
- `GET /api/news/<news_id>` - 新聞詳情

### 8. LINE Bot 整合 (`linebot.py`)

- LINE Bot Webhook 處理
- 訊息接收與回覆
- QR Code 綁定
- 與主 AI 系統整合

**主要端點**:
- `POST /linebot/webhook` - LINE Bot Webhook
- `POST /linebot/generate-qr` - 生成綁定 QR Code

### 9. 網頁 AI 助手 (`web_ai_assistant.py`)

- 網頁內容分析
- 自動化操作輔助
- 多工具整合
- 上下文管理

**主要端點**:
- `POST /web-ai/chat` - AI 對話
- `POST /web-ai/analyze` - 網頁分析

### 10. 筆記系統 (`note.py`)

- 使用者筆記管理
- 筆記 CRUD 操作
- 筆記搜尋

**主要端點**:
- `GET /note` - 查詢筆記
- `POST /note` - 創建筆記
- `PUT /note/<note_id>` - 更新筆記
- `DELETE /note/<note_id>` - 刪除筆記

## 資料庫架構

### MySQL (主要資料庫)

- **使用者表**: 使用者基本資訊、認證資訊
- **測驗表**: 測驗記錄、結果
- **作答表**: 使用者作答記錄
- **行事曆表**: 學習行事曆
- **筆記表**: 使用者筆記

### MongoDB (題目資料庫)

- **題目集合**: 考試題目、答案、詳解
- **學校集合**: 學校資訊
- **領域集合**: 知識領域分類

### Redis (快取與會話)

- Token 儲存
- 會話快取
- 臨時資料儲存

### Neo4j (知識圖譜)

- 概念節點
- 關係邊
- 知識路徑
- 概念關聯分析

## 配置說明

### 環境變數配置 (`config.py`)

```python
# 資料庫配置
SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://user:password@localhost:3306/mis_teach'
MONGO_URI = 'mongodb://localhost:27017/MIS_Teach'
REDIS_URL = 'redis://localhost:6379/0'
NEO4J_URI = 'bolt://localhost:7687'

# JWT 配置
JWT_ACCESS_TOKEN_EXPIRES = 3600  # 1小時
JWT_REFRESH_TOKEN_EXPIRES = 2592000  # 30天

# 郵件配置
MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 587
```

### API 密鑰配置 (`api.env`)

```env
# Google Gemini API 密鑰組
WU_API_KEYS=key1,key2,key3,...
PAN_API_KEYS=key1,key2,key3,...

# 預設 API 密鑰組
DEFAULT_API_GROUP=wu_api
```

## 安裝與執行

### 前置需求

- Python 3.11+
- MySQL 8.0+
- MongoDB 6.0+
- Redis 6.0+
- Neo4j 5.0+ (可選)

### 安裝步驟

```bash
# 進入後端目錄
cd backend

# 創建虛擬環境
python -m venv venv

# 啟動虛擬環境
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# 安裝依賴
pip install -r requirements.txt
```

### 資料庫初始化

```bash
# 初始化 MySQL 資料表
python -c "from app import app, sqldb; from src.quiz import init_quiz_tables; from src.dashboard import init_calendar_tables; app.app_context().push(); init_quiz_tables(); init_calendar_tables()"

# 初始化 MongoDB 資料
python tool/insert_mongodb.py

# 初始化 Neo4j 知識圖譜（可選）
python tool/init_neo4j_knowledge_graph.py

# 初始化新聞表
python tool/init_news_table.py
```

### 執行應用

```bash
# 開發模式
python app.py

# 或使用 Flask CLI
flask run

# 生產模式（使用 Gunicorn）
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## API 文檔

### 認證機制

所有需要認證的 API 都需要在 Header 中帶上 JWT Token:
```
Authorization: Bearer <token>
```

Token 會在回應中自動刷新，請使用回應中的新 Token。

### 完整 API 端點列表

#### 身份驗證 (`/login`, `/register`)

**POST /login** - 使用者登入
```json
請求:
{
  "email": "user@example.com",
  "password": "password123"
}

回應:
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "email": "user@example.com",
    "name": "使用者名稱"
  }
}
```

**POST /register** - 使用者註冊
```json
請求:
{
  "email": "user@example.com",
  "password": "password123",
  "name": "使用者名稱"
}

回應:
{
  "message": "Verification email sent."
}
```

**POST /login/logout** - 登出
```json
回應:
{
  "message": "success logged out"
}
```

#### 測驗系統 (`/quiz`)

**POST /quiz/generate** - 生成測驗
```json
請求:
{
  "template_id": "123",
  "count": 20,
  "difficulty": "medium",
  "domain": "資料庫"
}

回應:
{
  "quiz_id": "quiz_abc123",
  "title": "測驗標題",
  "questions": [...],
  "time_limit": 3600
}
```

**POST /quiz/submit-quiz** - 提交測驗
```json
請求:
{
  "template_id": "123",
  "answers": {
    "1": "A",
    "2": ["A", "B"],
    "3": "答案內容"
  },
  "time_taken": 1800,
  "question_answer_times": {
    "1": 120,
    "2": 150
  }
}

回應:
{
  "result_id": "result_xyz789",
  "score": 85,
  "total_questions": 20,
  "correct_count": 17
}
```

**GET /quiz/result/<result_id>** - 查詢測驗結果
```json
回應:
{
  "result_id": "result_xyz789",
  "quiz_id": "quiz_abc123",
  "score": 85,
  "total_questions": 20,
  "correct_count": 17,
  "answers": [...],
  "analysis": {...}
}
```

**GET /quiz/templates** - 獲取測驗模板列表
```json
回應:
{
  "templates": [
    {
      "id": "123",
      "title": "模板標題",
      "description": "模板描述",
      "question_count": 20
    }
  ]
}
```

#### AI 測驗 (`/ai_quiz`)

**POST /ai_quiz/generate** - AI 生成測驗
```json
請求:
{
  "concept": "資料庫正規化",
  "domain": "資料庫",
  "difficulty": "medium",
  "count": 10
}

回應:
{
  "quiz_id": "ai_quiz_123",
  "questions": [...]
}
```

#### AI 教學 (`/ai_teacher`)

**POST /ai_teacher/start** - 開始學習會話
```json
請求:
{
  "concept": "資料庫正規化",
  "domain": "資料庫"
}

回應:
{
  "session_id": "session_abc123",
  "concept": "資料庫正規化",
  "stage": "core_concept_confirmation"
}
```

**POST /ai_teacher/chat** - AI 教學對話
```json
請求:
{
  "session_id": "session_abc123",
  "message": "什麼是正規化？"
}

回應:
{
  "session_id": "session_abc123",
  "response": "正規化是...",
  "stage": "core_concept_confirmation",
  "understanding_level": 0.6
}
```

**GET /ai_teacher/session/<session_id>** - 查詢會話
```json
回應:
{
  "session_id": "session_abc123",
  "concept": "資料庫正規化",
  "stage": "core_concept_confirmation",
  "messages": [...],
  "learning_progress": [...]
}
```

#### 學習分析 (`/api/learning-analytics`)

**GET /api/learning-analytics/overview** - 學習總覽
```json
回應:
{
  "total_quizzes": 50,
  "total_questions": 1000,
  "average_score": 75.5,
  "weak_points": [...],
  "improvement_items": [...]
}
```

**GET /api/learning-analytics/trends** - 學習趨勢
```json
請求參數:
?period=7&domain=all

回應:
{
  "trends": [
    {
      "date": "2024-01-01",
      "score": 70,
      "questions_count": 20
    }
  ]
}
```

**POST /api/learning-analytics/ai-diagnosis** - AI 診斷
```json
請求:
{
  "weak_points": ["資料庫", "網路"]
}

回應:
{
  "diagnosis": "根據您的學習數據...",
  "recommendations": [...],
  "learning_path": [...]
}
```

#### 教材管理 (`/materials`)

**GET /materials/list** - 教材列表
```json
回應:
{
  "materials": [
    {
      "filename": "資料庫概論.md",
      "title": "資料庫概論",
      "category": "資料庫"
    }
  ]
}
```

**GET /materials/<filename>** - 教材內容
```json
回應:
{
  "filename": "資料庫概論.md",
  "content": "# 資料庫概論\n...",
  "metadata": {...}
}
```

#### 筆記系統 (`/note`)

**GET /note** - 查詢筆記
```json
請求參數:
?question_id=123

回應:
{
  "notes": [
    {
      "id": 1,
      "content": "筆記內容",
      "question_id": "123",
      "created_at": "2024-01-01T00:00:00"
    }
  ]
}
```

**POST /note** - 創建筆記
```json
請求:
{
  "content": "筆記內容",
  "question_id": "123"
}

回應:
{
  "id": 1,
  "message": "筆記創建成功"
}
```

**PUT /note/<note_id>** - 更新筆記
```json
請求:
{
  "content": "更新後的筆記內容"
}

回應:
{
  "id": 1,
  "message": "筆記更新成功"
}
```

**DELETE /note/<note_id>** - 刪除筆記
```json
回應:
{
  "message": "筆記刪除成功"
}
```

#### 新聞系統 (`/api/news`)

**GET /api/news** - 新聞列表
```json
請求參數:
?page=1&limit=10&category=科技

回應:
{
  "news": [...],
  "total": 100,
  "page": 1,
  "limit": 10
}
```

**GET /api/news/<news_id>** - 新聞詳情
```json
回應:
{
  "id": "news_123",
  "title": "新聞標題",
  "content": "新聞內容",
  "source": "來源",
  "published_at": "2024-01-01T00:00:00"
}
```

#### LINE Bot (`/linebot`)

**POST /linebot/webhook** - LINE Bot Webhook
```json
請求: (LINE 平台格式)

回應:
{
  "success": true
}
```

**POST /linebot/generate-qr** - 生成綁定 QR Code
```json
請求:
{
  "user_email": "user@example.com"
}

回應:
{
  "qr_code": "data:image/png;base64,...",
  "binding_code": "ABC123"
}
```

#### 網頁 AI 助手 (`/web-ai`)

**POST /web-ai/chat** - AI 對話
```json
請求:
{
  "message": "使用者訊息",
  "user_id": "user123",
  "platform": "web"
}

回應:
{
  "success": true,
  "message": "AI 回應",
  "timestamp": "2024-01-01T00:00:00"
}
```

**GET /web-ai/health** - 健康檢查
```json
回應:
{
  "success": true,
  "health": {
    "overall": "healthy",
    "ai_service": "healthy"
  }
}
```

### API 錯誤碼

- `200` - 成功
- `400` - 請求參數錯誤
- `401` - 未授權（Token 無效或過期）
- `403` - 禁止訪問
- `404` - 資源不存在
- `500` - 伺服器內部錯誤

### API 回應格式

**成功回應**:
```json
{
  "success": true,
  "data": {...},
  "token": "新的 token（如有）"
}
```

**錯誤回應**:
```json
{
  "success": false,
  "error": "錯誤訊息",
  "code": "ERROR_CODE"
}
```

## CORS 配置

後端支援動態 CORS 配置，允許以下來源：
- `localhost` (開發環境)
- `.ngrok-free.app` (ngrok instant endpoints)
- `.ngrok.io` (ngrok 域名)

## 安全機制

### JWT Token 管理

- Token 自動刷新
- Token 驗證與清理
- 過期處理
- 無效 Token 檢測

### 密碼安全

- Bcrypt 加密
- 鹽值處理
- 密碼強度驗證

### API 安全

- Token 驗證中間件
- 請求限流（可選）
- 輸入驗證與清理

## 工具腳本

### 資料管理工具

```bash
# 插入測試學校資料
python tool/insert_test_school.py

# 檢查測試學校資料
python tool/check_test_school.py

# 修正答案類型
python tool/fix_answer_types.py

# 重新插入測試學校
python tool/reinsert_test_school.py
```

### 資料庫初始化工具

```bash
# 初始化 MongoDB
python tool/insert_mongodb.py

# 初始化 Neo4j
python tool/init_neo4j_knowledge_graph.py

# 初始化新聞表
python tool/init_news_table.py
```

## 部署

### 生產環境配置

1. 設定環境變數
2. 配置資料庫連線
3. 設定 API 密鑰
4. 配置郵件服務
5. 設定安全密鑰

### Docker 部署（可選）

```dockerfile
FROM python:3.11
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

## 監控與日誌

### 日誌配置

- 應用日誌記錄
- 錯誤追蹤
- 效能監控（可選）

### 健康檢查

- `/health` - 健康檢查端點（可自行實作）

## 使用範例

### Python 客戶端範例

```python
import requests

# 1. 登入獲取 Token
login_url = "http://localhost:5000/login"
login_data = {
    "email": "user@example.com",
    "password": "password123"
}
response = requests.post(login_url, json=login_data)
token = response.json()["access_token"]

# 2. 使用 Token 訪問 API
headers = {"Authorization": f"Bearer {token}"}

# 生成測驗
quiz_url = "http://localhost:5000/quiz/generate"
quiz_data = {
    "template_id": "123",
    "count": 20
}
quiz_response = requests.post(quiz_url, json=quiz_data, headers=headers)
quiz = quiz_response.json()

# 3. 提交測驗
submit_url = "http://localhost:5000/quiz/submit-quiz"
submit_data = {
    "template_id": "123",
    "answers": {"1": "A", "2": "B"},
    "time_taken": 1800
}
result = requests.post(submit_url, json=submit_data, headers=headers)
print(result.json())
```

### JavaScript/TypeScript 範例

```typescript
// 使用 fetch API
const API_BASE = 'http://localhost:5000';

// 登入
async function login(email: string, password: string) {
  const response = await fetch(`${API_BASE}/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  });
  const data = await response.json();
  localStorage.setItem('token', data.access_token);
  return data;
}

// 生成測驗
async function generateQuiz(templateId: string, count: number) {
  const token = localStorage.getItem('token');
  const response = await fetch(`${API_BASE}/quiz/generate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({ template_id: templateId, count })
  });
  return await response.json();
}
```

### cURL 範例

```bash
# 登入
curl -X POST http://localhost:5000/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123"}'

# 生成測驗（需要 Token）
curl -X POST http://localhost:5000/quiz/generate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"template_id":"123","count":20}'

# 提交測驗
curl -X POST http://localhost:5000/quiz/submit-quiz \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "template_id":"123",
    "answers":{"1":"A","2":"B"},
    "time_taken":1800
  }'
```

## 資料庫操作範例

### MySQL 操作

```python
from accessories import sqldb
from sqlalchemy import text

# 查詢使用者資訊
def get_user_info(email):
    query = text("SELECT * FROM users WHERE email = :email")
    with sqldb.engine.connect() as conn:
        result = conn.execute(query, {"email": email})
        return result.fetchone()

# 插入測驗記錄
def insert_quiz_history(user_email, quiz_id, score):
    query = text("""
        INSERT INTO quiz_history (user_email, quiz_id, score, created_at)
        VALUES (:email, :quiz_id, :score, NOW())
    """)
    with sqldb.engine.connect() as conn:
        conn.execute(query, {
            "email": user_email,
            "quiz_id": quiz_id,
            "score": score
        })
        conn.commit()
```

### MongoDB 操作

```python
from accessories import mongo
from bson import ObjectId

# 查詢題目
def get_question(question_id):
    return mongo.db.exam.find_one({"_id": ObjectId(question_id)})

# 查詢多個題目
def get_questions_by_school(school, year):
    return list(mongo.db.exam.find({
        "school": school,
        "year": year
    }))

# 插入題目
def insert_question(question_data):
    result = mongo.db.exam.insert_one(question_data)
    return result.inserted_id
```

### Redis 操作

```python
from accessories import redis_client

# 儲存快取
def cache_data(key, value, expire=3600):
    redis_client.setex(key, expire, value)

# 獲取快取
def get_cache(key):
    return redis_client.get(key)

# 刪除快取
def delete_cache(key):
    redis_client.delete(key)
```

## 開發指南

### 創建新的 API 端點

```python
from flask import Blueprint, request, jsonify
from src.api import verify_token

# 創建 Blueprint
my_bp = Blueprint('my_module', __name__)

@my_bp.route('/my-endpoint', methods=['POST'])
def my_endpoint():
    # 驗證 Token
    token = request.headers.get('Authorization', '').split(' ')[1]
    user_email = verify_token(token)
    if not user_email:
        return jsonify({'error': '未授權'}), 401
    
    # 處理請求
    data = request.get_json()
    # ... 業務邏輯 ...
    
    # 返回回應
    return jsonify({
        'success': True,
        'data': {...}
    }), 200

# 在 app.py 中註冊
# app.register_blueprint(my_bp, url_prefix='/my-module')
```

### 使用 RAG 系統

```python
from src.rag_sys.rag_ai_role import get_rag_service

# 初始化 RAG 服務
rag_service = get_rag_service()

# 檢索相關知識
results = rag_service.search("資料庫正規化", top_k=5)

# 生成回應
response = rag_service.generate_response(
    query="什麼是正規化？",
    context=results
)
```

### 使用 AI 服務

```python
from tool.api_keys import get_api_key
import google.generativeai as genai

# 初始化 Gemini
api_key = get_api_key()
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.5-flash')

# 生成內容
response = model.generate_content("解釋資料庫正規化")
print(response.text)
```

## 效能優化

### 1. 資料庫優化

- **索引優化**: 為常用查詢欄位建立索引
- **查詢優化**: 避免 N+1 查詢，使用 JOIN
- **連線池**: 使用適當的連線池大小
- **分頁**: 大量資料使用分頁查詢

### 2. 快取策略

- **Redis 快取**: 快取常用資料（題目列表、使用者資訊）
- **HTTP 快取**: 設定適當的 Cache-Control 標頭
- **查詢快取**: 快取複雜查詢結果

### 3. API 優化

- **非同步處理**: 長時間任務使用背景任務
- **批量操作**: 支援批量查詢和更新
- **壓縮回應**: 使用 gzip 壓縮
- **分頁**: 列表 API 支援分頁

## 測試

### 單元測試範例

```python
import unittest
from app import app
from src.api import verify_token

class TestAPI(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
    
    def test_login(self):
        response = self.app.post('/login', json={
            'email': 'test@example.com',
            'password': 'password123'
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('access_token', data)
    
    def test_protected_endpoint(self):
        # 先登入獲取 Token
        login_response = self.app.post('/login', json={
            'email': 'test@example.com',
            'password': 'password123'
        })
        token = login_response.get_json()['access_token']
        
        # 使用 Token 訪問受保護的端點
        response = self.app.get('/dashboard/user-info',
                               headers={'Authorization': f'Bearer {token}'})
        self.assertEqual(response.status_code, 200)

if __name__ == '__main__':
    unittest.main()
```

### 執行測試

```bash
# 執行所有測試
python -m pytest tests/

# 執行特定測試文件
python -m pytest tests/test_api.py

# 顯示覆蓋率
python -m pytest --cov=src tests/
```

## 授權

MIT License

## 聯絡資訊

如有問題或建議，請聯繫開發團隊。

