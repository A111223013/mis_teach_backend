# Chapter 9 資料庫系統開發

資料庫系統是現代資訊系統的基石，其開發過程的品質直接影響整個系統的穩定性、效能與可維護性。本章將深入探討資料庫系統的開發生命週期，從最初的需求分析到最終的部署與維護，提供一套系統性的方法與最佳實踐。

-----

### 9.1 核心概念：資料庫系統開發生命週期 (DSDLC)

#### 9.1.1 什麼是資料庫系統開發？

資料庫系統開發是指從無到有地建立一個資料庫應用程式的過程，它涵蓋了從理解使用者需求、設計資料庫結構、實作資料庫，到最終的部署、測試及後續維護等一系列活動。這個過程與一般軟體開發有許多共通之處，但更專注於資料的組織、儲存、檢索、完整性、安全性和效能優化。

*   **核心觀念**：資料庫系統開發不單單只是撰寫 SQL 語句，而是一個涵蓋了資料建模、結構設計、資料管理策略及效能考量的綜合性工程。
*   **與軟體開發的關聯**：資料庫是許多應用程式的核心「資料層」，它的設計與實作品質直接影響前端應用程式的功能性與使用者體驗。資料庫開發通常是軟體開發生命週期 (SDLC) 中一個關鍵且獨立的階段。

#### 9.1.2 資料庫系統開發生命週期 (DSDLC)

資料庫系統開發生命週期 (Database System Development Life Cycle, DSDLC) 是 SDLC 在資料庫開發領域的具體應用。它提供了一個結構化的框架，確保資料庫系統能被有效且高效地開發。

*   **定義**：DSDLC 是一系列有組織、有步驟的活動，用來規劃、設計、實作、測試、部署和維護資料庫系統。
*   **主要階段**：
    1.  **需求分析 (Requirement Analysis)**：理解業務需求，識別所需儲存的資料及其彼此之間的關係。
    2.  **概念設計 (Conceptual Design)**：建立獨立於任何特定資料庫管理系統 (DBMS) 的高階資料模型（如 ER Model）。
    3.  **邏輯設計 (Logical Design)**：將概念模型轉換為特定資料模型的結構（如關係模型），但不涉及實體的 DBMS 特性。
    4.  **實體設計 (Physical Design)**：根據選定的 DBMS 產品，定義實際的儲存結構、索引、存取路徑等。
    5.  **實作 (Implementation)**：使用 DDL (Data Definition Language) 建立資料庫結構，並使用 DML (Data Manipulation Language) 載入初始資料。
    6.  **測試 (Testing)**：驗證資料庫的正確性、完整性、效能和安全性。
    7.  **部署與維護 (Deployment & Maintenance)**：將資料庫上線，並進行日常監控、備份、恢復、效能調校和必要的功能更新。
*   **與相鄰概念的關聯**：DSDLC 是 SDLC 的一個特化版本，它強調資料導向的設計與管理。它與系統分析與設計緊密結合，並為應用程式開發提供穩固的資料基礎。

-----

### 9.2 資料庫設計階段詳解

資料庫設計是 DSDLC 中最核心的環節，它將複雜的業務需求逐步轉化為可管理的資料庫結構。

#### 9.2.1 需求分析 (Requirement Analysis)

*   **核心觀念**：這是 DSDLC 的起始階段，目標是清晰地理解用戶對資料庫系統的功能需求、非功能需求（如效能、安全性）、業務規則以及現有的資料流程。
*   **工具與技術**：
    *   **訪談**：與最終使用者、業務專家溝通，了解他們的需求。
    *   **問卷**：收集大量用戶的意見。
    *   **文件分析**：審查現有業務流程文件、報表、表格。
    *   **用例圖 (Use Case Diagram)**：從功能角度描述用戶與系統的互動。
    *   **資料流程圖 (Data Flow Diagram, DFD)**：描繪資料在系統內部的流動和處理。
*   **例子**：為一個電子商務平台進行需求分析。我們可能需要收集以下資訊：
    *   **功能需求**：商品管理、用戶註冊/登入、訂單處理、支付、庫存管理、評價系統。
    *   **資料需求**：用戶資訊（姓名、地址、電話）、商品資訊（名稱、價格、庫存）、訂單資訊（訂單號、狀態、購買商品）、支付記錄、物流資訊。
    *   **業務規則**：訂單一旦發貨不能修改、商品庫存不足時不能下單、用戶評價後才能再次購買同類商品。
*   **與相鄰概念的關聯**：需求分析的產出是概念設計的直接輸入。精確的需求分析能有效避免後續設計與實作階段的返工。

#### 9.2.2 概念設計 (Conceptual Design)

*   **核心觀念**：將需求分析中收集到的資訊，轉換為一個高階的、獨立於任何 DBMS 的資料模型。這個模型主要關注**實體 (Entities)**、**屬性 (Attributes)** 和**關係 (Relationships)**。
*   **典型例子**：實體關係模型 (Entity-Relationship Model, ER Model) 是概念設計最常用的工具。它使用圖形符號來表示實體集、屬性、關係集及其基數比 (Cardinality Ratio)。
*   **推導**：從需求分析中識別出：
    1.  **實體集**：名詞通常代表實體（例如：學生、課程、教師）。
    2.  **屬性**：實體的特性（例如：學生有學號、姓名、科系）。
    3.  **關係集**：實體之間的互動（例如：學生「選修」課程、教師「教授」課程）。
    4.  **主鍵 (Primary Key)**：唯一識別實體實例的屬性或屬性組合。
    5.  **基數比**：例如，一對多 (1:N)、多對多 (M:N)。
*   **與相鄰概念的關聯**：概念設計的輸出（如 ER 圖）是邏輯設計的藍圖，它提供了一個清晰、易懂的資料結構概覽。

#### 9.2.3 邏輯設計 (Logical Design)

*   **核心觀念**：將概念模型轉換為特定資料模型（如關係模型、物件導向模型），但仍保持對特定 DBMS 實作細節的獨立性。對於關聯式資料庫，這意味著將 ER Model 轉換為一組關聯綱要 (Relational Schema)，即表格、屬性、主鍵、外鍵。
*   **典型例子**：將 ER 模型轉換為關係模型。
    1.  **實體轉換為表格**：每個強實體集轉換為一個表格，實體的屬性成為表格的欄位。
    2.  **關係轉換為外鍵或表格**：
        *   **一對一 (1:1)**：通常將其中一方的主鍵作為外鍵加入另一方表格。
        *   **一對多 (1:N)**：將「一」方的主鍵作為外鍵加入「多」方表格。
        *   **多對多 (M:N)**：建立一個新的「連接表」，包含兩方實體的主鍵作為聯合外鍵。
    3.  **多值屬性 (Multivalued Attributes)**：為多值屬性建立單獨的表格。
*   **推導：正規化 (Normalization)**
    *   正規化是邏輯設計的關鍵步驟，旨在消除資料冗餘、減少更新異常 (Update Anomaly)、插入異常 (Insertion Anomaly) 和刪除異常 (Deletion Anomaly)，確保資料的完整性。
    *   **第一正規化形式 (1NF)**：所有屬性都是原子性的，沒有重複的群組。
    *   **第二正規化形式 (2NF)**：滿足 1NF，且所有非主鍵屬性都完全函數依賴於候選鍵。
    *   **第三正規化形式 (3NF)**：滿足 2NF，且所有非主鍵屬性都不傳遞函數依賴於候選鍵。
    *   **Boyce-Codd 正規化形式 (BCNF)**：滿足 3NF，且對於任何函數依賴 $X \to Y$，如果 $Y$ 不包含在 $X$ 中，則 $X$ 必須是候選鍵。
*   **與相鄰概念的關聯**：邏輯設計是實體設計的直接輸入。正規化確保了資料庫結構的合理性和一致性，為後續資料操作提供了良好的基礎。

#### 9.2.4 實體設計 (Physical Design)

*   **核心觀念**：針對選定的特定 DBMS 產品（如 MySQL, PostgreSQL, SQL Server, Oracle），決定資料庫的實際儲存結構和存取方法，以優化效能、儲存效率和安全性。
*   **典型例子**：
    1.  **選擇資料類型**：根據資料特性選擇最合適的資料類型（例如，`VARCHAR(255)` vs `TEXT`, `INT` vs `BIGINT`）。
    2.  **建立索引 (Indexes)**：為經常查詢的欄位建立索引以加速資料檢索。
    3.  **定義儲存參數**：如表空間 (Tablespace)、檔案群組 (Filegroups)。
    4.  **資料分區 (Partitioning)**：將大表拆分成更小、更易管理的塊，以提高查詢效能和維護便利性。
    5.  **叢集化 (Clustering)**：物理上將相關資料儲存在一起。
    6.  **安全性設定**：定義用戶權限、存取控制列表。
    7.  **備份與恢復策略**：規劃資料庫的備份頻率、儲存位置和恢復流程。
*   **與相鄰概念的關聯**：實體設計直接影響資料庫的運行效能和系統的整體響應速度。它需要深入了解特定 DBMS 的內部機制和優化技巧。

-----

### 9.3 資料庫實作、測試與部署

#### 9.3.1 資料庫實作 (Implementation)

*   **核心觀念**：根據實體設計階段的藍圖，使用資料定義語言 (DDL) 在選定的 DBMS 中建立資料庫對象（表格、視圖、索引、觸發器、儲存過程等），並使用資料操作語言 (DML) 載入初始資料。
*   **例子**：
    ```sql
    -- 建立學生表格
    CREATE TABLE Students (
        StudentID INT PRIMARY KEY,
        Name VARCHAR(100) NOT NULL,
        Major VARCHAR(50),
        EnrollmentYear INT
    );

    -- 建立課程表格
    CREATE TABLE Courses (
        CourseID VARCHAR(10) PRIMARY KEY,
        Title VARCHAR(100) NOT NULL,
        Credits INT
    );

    -- 建立選課表格（多對多關係）
    CREATE TABLE Enrollments (
        StudentID INT,
        CourseID VARCHAR(10),
        EnrollmentDate DATE,
        Grade VARCHAR(2),
        PRIMARY KEY (StudentID, CourseID), -- 複合主鍵
        FOREIGN KEY (StudentID) REFERENCES Students(StudentID),
        FOREIGN KEY (CourseID) REFERENCES Courses(CourseID)
    );

    -- 插入初始資料
    INSERT INTO Students (StudentID, Name, Major, EnrollmentYear) VALUES
    (101, '張三', '資工', 2020),
    (102, '李四', '電機', 2021);

    INSERT INTO Courses (CourseID, Title, Credits) VALUES
    ('CS101', '資料庫導論', 3),
    ('EE201', '電路學', 4);
    ```
*   **與相鄰概念的關聯**：實作階段是將設計圖紙變為現實的過程，其正確性直接影響後續的測試。

#### 9.3.2 資料庫測試 (Testing)

*   **核心觀念**：確保資料庫系統在功能、效能、安全性和完整性方面滿足預期要求。
*   **類型**：
    1.  **單元測試 (Unit Testing)**：測試單一的資料庫對象（如儲存過程、觸發器、視圖）或 SQL 查詢的正確性。
    2.  **整合測試 (Integration Testing)**：測試資料庫與應用程式之間、或不同資料庫組件之間的互動是否正確。
    3.  **資料完整性測試**：驗證主鍵、外鍵、唯一約束、檢查約束等是否正常工作，確保資料的一致性。
    4.  **效能測試 (Performance Testing)**：測量查詢響應時間、吞吐量、並發用戶數等，以評估資料庫在不同負載下的表現。
    5.  **壓力測試 (Stress Testing)**：將資料庫置於極端負載下，檢查其穩定性和瓶頸。
    6.  **安全性測試**：測試存取控制是否有效、是否存在 SQL 注入等漏洞。
    7.  **備份與恢復測試**：驗證備份是否可用，以及在發生故障時能否成功恢復資料。
*   **與相鄰概念的關聯**：充分的測試可以發現設計或實作中的問題，防止在部署後出現嚴重故障。

#### 9.3.3 資料庫部署與維護 (Deployment & Maintenance)

*   **核心觀念**：將開發完成且通過測試的資料庫系統發布到生產環境，並在運行過程中進行持續的管理與優化。
*   **部署活動**：
    1.  **環境準備**：安裝和配置 DBMS 軟體，準備伺服器資源。
    2.  **腳本執行**：在生產環境中執行 DDL 和 DML 腳本以建立資料庫結構和載入初始資料。
    3.  **權限配置**：設定應用程式和用戶的存取權限。
    4.  **監控配置**：設定監控工具，以便實時了解資料庫的運行狀況。
*   **維護活動**：
    1.  **效能監控與調校 (Performance Tuning)**：定期分析查詢計畫、索引使用情況，進行優化。
    2.  **備份與恢復**：執行定期備份，並確保恢復策略的有效性。
    3.  **安全性管理**：定期審查用戶權限，更新安全補丁，防範潛在威脅。
    4.  **資料庫更新**：處理結構變更 (schema evolution)、資料遷移。
    5.  **空間管理**：監控磁碟空間使用，進行資料歸檔或清理。
*   **與相鄰概念的關聯**：部署與維護是確保資料庫系統長期穩定運行的關鍵環節，通常由資料庫管理員 (DBA) 負責。這也是 DSDLC 的終點，同時也可能觸發新的開發需求。

-----

### 9.4 常見錯誤與澄清

#### 9.4.1 忽視正規化或過度正規化

*   **常見錯誤**：
    1.  **忽視正規化**：導致資料冗餘，更新、插入、刪除異常，影響資料完整性。例如，一個訂單表格中直接儲存客戶的姓名和地址，當客戶地址更改時，需要更新所有相關訂單記錄。
    2.  **過度正規化**：將所有表格都分解到最高正規化形式 (如 BCNF 或 4NF)，可能導致查詢時需要連接過多表格，從而降低查詢效能。
*   **澄清**：正規化的目的是平衡資料完整性與查詢效能。一般而言，將資料庫設計到 3NF 是一個良好的起點。對於某些查詢頻繁且更新不頻繁的場景，適度的**反正規化 (Denormalization)** 可以提高效能，但必須仔細權衡其對資料完整性的潛在影響，並輔以應用程式層的邏輯或資料庫觸發器來維護一致性。

#### 9.4.2 忽略資料庫安全考量

*   **常見錯誤**：只關注資料庫的功能性，而忽視了資料的安全性，例如使用弱密碼、賦予應用程式過高的資料庫權限、未加密敏感資料等。
*   **澄清**：資料庫安全性應從設計初期就納入考量。這包括：
    *   **最小權限原則**：只賦予用戶或應用程式所需的最小權限。
    *   **強密碼策略**：強制使用複雜密碼。
    *   **敏感資料加密**：對信用卡號、個人身份資訊等敏感資料進行加密儲存和傳輸。
    *   **存取控制**：設定防火牆、限制 IP 存取、使用虛擬私人網路 (VPN) 等。
    *   **審計日誌 (Audit Logs)**：記錄所有資料庫操作，以便追溯異常行為。
    *   **SQL 注入防禦**：使用參數化查詢 (Parameterized Queries) 或預處理語句 (Prepared Statements)。

#### 9.4.3 未進行充分測試

*   **常見錯誤**：認為資料庫只需要「建立」即可，而忽略了對其功能、效能和完整性的嚴格測試，導致上線後出現數據錯誤、響應遲緩甚至系統崩潰。
*   **澄清**：資料庫與應用程式一樣，都需要經過嚴格的測試。這不僅包括驗證 SQL 語句的正確性，更要確保：
    *   **資料完整性**：所有約束（主鍵、外鍵、唯一、非空、檢查）都按預期工作。
    *   **資料一致性**：在並發環境下，多個事務操作不會導致資料不一致。
    *   **效能基準**：在模擬真實負載下，查詢和更新操作的響應時間是否達標。
    *   **恢復能力**：驗證備份是否有效，能否在災難發生時快速恢復。

-----

### 9.5 小練習 (附詳解)

#### 9.5.1 練習一：從需求到關係模型

**題目**：請為一個簡單的「圖書館借閱系統」設計資料庫。
**需求描述**：
*   圖書館有多本書籍。每本書有一個唯一的書號、書名、作者、出版社和出版年份。
*   每本書可以有多個副本，每個副本有一個唯一的副本號，並有狀態（可借閱、已借閱、遺失）。
*   圖書館有多名讀者。每位讀者有一個唯一的讀者號、姓名、地址和電話。
*   讀者可以借閱書籍副本。每次借閱需要記錄借閱日期和歸還日期。
*   一位讀者可以借閱多個書籍副本，一個書籍副本同一時間只能被一位讀者借閱。

**詳解**：

**步驟一：概念設計 (繪製 ER Model)**

*   **實體**：
    *   `書籍 (Book)`：書號 (PK)、書名、作者、出版社、出版年份
    *   `書籍副本 (BookCopy)`：副本號 (PK)、狀態
    *   `讀者 (Reader)`：讀者號 (PK)、姓名、地址、電話
*   **關係**：
    *   `書籍` 和 `書籍副本`：**一對多**關係（一個書籍有多個副本）
    *   `讀者` 和 `書籍副本`：**多對多**關係（一個讀者可以借閱多個副本，一個副本可以被多個讀者借閱過，但同一時間只能被一個讀者借閱），需要一個連接實體 `借閱記錄 (Borrowing)` 來記錄借閱資訊。
*   **連接實體 / 關係屬性**：
    *   `借閱記錄`：借閱日期、歸還日期。

**(想像中的 ERD 結構)**
```
+-------------+      1         N      +-----------+     1         N       +-------------+
|    書籍     | <---------> | 書籍副本  | <---------> |  借閱記錄   | <---------> |     讀者     |
+-------------+             +-----------+             +-------------+             +-------------+
|PK 書號      |             |PK 副本號   |             |PK 讀者號 (FK)|             |PK 讀者號    |
|  書名       |             |  狀態      |             |PK 副本號 (FK)|             |  姓名       |
|  作者       |             |FK 書號     |             |  借閱日期   |             |  地址       |
|  出版社     |             +-----------+             |  歸還日期   |             |  電話       |
|  出版年份   |                                       +-------------+             +-------------+
+-------------+
```

**步驟二：邏輯設計 (轉換為關係模型)**

將 ER Model 轉換為關係綱要，並標註主鍵 (PK) 和外鍵 (FK)。

1.  **書籍 (Book)**:
    *   `Book(<u>BookID</u>, Title, Author, Publisher, PublicationYear)`
    *   **PK**: `BookID`

2.  **書籍副本 (BookCopy)**:
    *   `BookCopy(<u>CopyID</u>, Status, BookID)`
    *   **PK**: `CopyID`
    *   **FK**: `BookID` 參考 `Book(BookID)`

3.  **讀者 (Reader)**:
    *   `Reader(<u>ReaderID</u>, Name, Address, Phone)`
    *   **PK**: `ReaderID`

4.  **借閱記錄 (Borrowing)**:
    *   `Borrowing(<u>ReaderID</u>, <u>CopyID</u>, <u>BorrowDate</u>, ReturnDate)`
    *   **PK**: `(ReaderID, CopyID, BorrowDate)` (因為同一讀者可能多次借閱同一副本，故加入借閱日期作為主鍵的一部分以唯一識別每次借閱行為)
    *   **FK1**: `ReaderID` 參考 `Reader(ReaderID)`
    *   **FK2**: `CopyID` 參考 `BookCopy(CopyID)`

#### 9.5.2 練習二：正規化應用

**題目**：假設有一個圖書館系統的初始設計表格 `LibraryMembers` 如下，它包含了一些冗餘資訊。請將此表格正規化至 3NF。

`LibraryMembers(<u>MemberID</u>, MemberName, MemberAddress, BookBorrowed, BorrowDate, BookTitle, Author, Publisher, BorrowLimit)`

其中：
*   `MemberID` 是讀者唯一識別碼。
*   `BookBorrowed` 是讀者借閱的書籍副本號。
*   `BorrowLimit` 是每個讀者可以借閱的最大書籍數量。

**函數依賴 (Functional Dependencies, FD)**：
1.  `MemberID` $\to$ `MemberName`, `MemberAddress`, `BorrowLimit` (讀者ID決定讀者姓名、地址、借閱上限)
2.  `BookBorrowed` $\to$ `BookTitle`, `Author`, `Publisher` (書籍副本號決定書名、作者、出版社)
3.  `(MemberID, BookBorrowed)` $\to$ `BorrowDate` (讀者和書籍副本一起決定借閱日期)

**詳解**：

**步驟一：識別主鍵與第一正規化形式 (1NF)**

*   **主鍵**：根據 FD3，`MemberID` 和 `BookBorrowed` 的組合可以唯一識別一條記錄，因為它能決定 `BorrowDate`。其他屬性則由 `MemberID` 或 `BookBorrowed` 單獨決定。因此，候選鍵是 `(MemberID, BookBorrowed)`。
*   **1NF 判斷**：所有屬性都是原子性的（例如，`MemberAddress` 雖然可能包含街名、城市等，但在這個語境下可視為單一屬性）。表格已經在 1NF。

**步驟二：第二正規化形式 (2NF)**

2NF 要求所有非主鍵屬性都完全函數依賴於主鍵。檢查部分函數依賴：

*   `MemberID` $\to$ `MemberName`, `MemberAddress`, `BorrowLimit`
    *   這三個屬性 `MemberName`, `MemberAddress`, `BorrowLimit` 只依賴於主鍵的一部分 (`MemberID`)。這違反了 2NF。
*   `BookBorrowed` $\to$ `BookTitle`, `Author`, `Publisher`
    *   這三個屬性 `BookTitle`, `Author`, `Publisher` 只依賴於主鍵的一部分 (`BookBorrowed`)。這也違反了 2NF。

**分解表格以達到 2NF**：

1.  **讀者資訊表格 (Members)**：包含所有只依賴於 `MemberID` 的屬性。
    *   `Members(<u>MemberID</u>, MemberName, MemberAddress, BorrowLimit)`
    *   **FD**: `MemberID` $\to$ `MemberName`, `MemberAddress`, `BorrowLimit`

2.  **書籍副本資訊表格 (BookCopies)**：包含所有只依賴於 `BookBorrowed` 的屬性。
    *   `BookCopies(<u>BookBorrowed</u>, BookTitle, Author, Publisher)`
    *   **FD**: `BookBorrowed` $\to$ `BookTitle`, `Author`, `Publisher`

3.  **借閱記錄表格 (Borrowings)**：包含主鍵及所有完全依賴於主鍵的屬性。
    *   `Borrowings(<u>MemberID</u>, <u>BookBorrowed</u>, BorrowDate)`
    *   **FD**: `(MemberID, BookBorrowed)` $\to$ `BorrowDate`
    *   **FK1**: `MemberID` 參考 `Members(MemberID)`
    *   **FK2**: `BookBorrowed` 參考 `BookCopies(BookBorrowed)`

至此，我們已經將表格分解至 2NF。

**步驟三：第三正規化形式 (3NF)**

3NF 要求所有非主鍵屬性不傳遞函數依賴於候選鍵。檢查新分解的表格：

1.  **`Members(<u>MemberID</u>, MemberName, MemberAddress, BorrowLimit)`**:
    *   `MemberID` 是主鍵。
    *   沒有非主鍵屬性傳遞依賴於 `MemberID`。該表格已在 3NF。

2.  **`BookCopies(<u>BookBorrowed</u>, BookTitle, Author, Publisher)`**:
    *   `BookBorrowed` 是主鍵。
    *   沒有非主鍵屬性傳遞依賴於 `BookBorrowed`。該表格已在 3NF。

3.  **`Borrowings(<u>MemberID</u>, <u>BookBorrowed</u>, BorrowDate)`**:
    *   `(MemberID, BookBorrowed)` 是主鍵。
    *   `BorrowDate` 完全依賴於複合主鍵。沒有傳遞依賴。該表格已在 3NF。

因此，最終正規化至 3NF 的關係模型為：

*   `Members(<u>MemberID</u>, MemberName, MemberAddress, BorrowLimit)`
*   `BookCopies(<u>BookBorrowed</u>, BookTitle, Author, Publisher)`
*   `Borrowings(<u>MemberID</u>, <u>BookBorrowed</u>, BorrowDate)`

**注意**：在這個例子中，`BookBorrowed` 實際上是書籍副本的 ID。為了命名更清晰，可以將 `BookBorrowed` 重命名為 `CopyID`。如果 `BookTitle`, `Author`, `Publisher` 實際上是描述書籍本身的資訊，而不是特定副本的資訊，那麼我們可能還需要一個 `Books` 表格來儲存這些資訊，而 `BookCopies` 表格則透過 `BookID` 連結到 `Books` 表格。但根據目前的 FD，我們依照題意給出的屬性進行正規化。

-----

### 9.6 延伸閱讀

*   **資料庫系統概念 (Database System Concepts)**：通常指 Abraham Silberschatz、Henry F. Korth 和 S. Sudarshan 所著的經典教科書，對資料庫理論、設計、實作和應用有深入且全面的闡述。
*   **資料庫管理系統 (Database Management Systems)**：由 Raghu Ramakrishnan 和 Johannes Gehrke 所著，另一本廣受推薦的資料庫教科書，側重於 DBMS 的內部機制和實作細節。
*   **SQL 語言標準**：了解 SQL 的 ANSI/ISO 標準，有助於撰寫可移植性更好的資料庫語句。
*   **特定 DBMS 官方文檔**：如 MySQL Documentation、PostgreSQL Documentation、Oracle Database Documentation 或 Microsoft SQL Server Documentation。這些文檔提供了最權威的產品特性、最佳實踐和效能調校指南。
*   **資料庫設計模式 (Database Design Patterns)**：此類書籍或資源提供了常見資料庫設計問題的標準解決方案，例如「多租戶資料庫」、「版本控制」等。
*   **敏捷資料庫開發 (Agile Database Development)**：探索如何在敏捷開發框架下管理資料庫的變更與演進。