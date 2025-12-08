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

### 認證相關

所有需要認證的 API 都需要在 Header 中帶上 JWT Token:
```
Authorization: Bearer <token>
```

### 主要 API 端點

#### 身份驗證
- `POST /login` - 登入
- `POST /register` - 註冊
- `POST /login/logout` - 登出

#### 測驗
- `POST /quiz/generate` - 生成測驗
- `POST /quiz/submit` - 提交測驗
- `GET /quiz/result/<quiz_id>` - 查詢結果

#### AI 教學
- `POST /ai_teacher/chat` - AI 教學對話
- `GET /ai_teacher/session/<session_id>` - 查詢會話

#### 學習分析
- `GET /api/learning-analytics/overview` - 總覽
- `GET /api/learning-analytics/trends` - 趨勢
- `POST /api/learning-analytics/ai-diagnosis` - AI 診斷

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

## 常見問題

### 1. 資料庫連線失敗

- 檢查資料庫服務是否啟動
- 確認連線字串正確
- 檢查防火牆設定

### 2. Token 刷新失敗

- 檢查 Token 格式
- 確認安全密鑰設定
- 檢查 Token 過期時間

### 3. CORS 錯誤

- 確認來源域名在允許清單中
- 檢查 CORS 配置
- 確認請求頭設定

### 4. API 密鑰錯誤

- 檢查 `api.env` 配置
- 確認 API 密鑰有效
- 檢查密鑰組設定

## 未來規劃

- [ ] GraphQL API 支援
- [ ] WebSocket 即時通訊
- [ ] 微服務架構重構
- [ ] 容器化部署
- [ ] 自動化測試
- [ ] API 文檔自動生成

## 授權

MIT License

## 聯絡資訊

如有問題或建議，請聯繫開發團隊。

