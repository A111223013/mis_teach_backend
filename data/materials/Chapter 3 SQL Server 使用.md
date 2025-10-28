# Chapter 3 SQL Server 使用

本章將引導您學習如何實際操作 SQL Server，從連線到資料庫實例，到執行核心的資料定義語言 (DDL) 和資料操作語言 (DML) 指令。掌握這些基本操作是您在 SQL Server 上進行任何開發或管理工作的基石。

-----

### 3.1 連線至 SQL Server

#### 核心概念：使用 SQL Server Management Studio (SSMS)

SQL Server Management Studio (SSMS) 是 Microsoft 提供的一個整合式環境，用於管理 SQL Server 的所有元件。它是資料庫管理員和開發人員最常用的工具，提供了圖形化介面和 T-SQL 編輯器，讓您可以輕鬆地連線、查詢、修改資料庫。

#### 例子：首次連線到 SQL Server 實例

1.  **啟動 SSMS**：從 Windows 的「開始」選單中找到並開啟「SQL Server Management Studio」。
2.  **出現連線視窗**：當 SSMS 啟動時，通常會自動彈出「連線到伺服器」對話框。
3.  **輸入伺服器名稱**：
    *   如果您使用預設實例，通常是 `.` (本機)、`localhost` 或您的電腦名稱。
    *   如果您使用具名實例（例如：`SQLEXPRESS`），則格式為 `電腦名稱\實例名稱`，例如 `.\SQLEXPRESS` 或 `localhost\SQLEXPRESS`。
4.  **選擇驗證方式**：
    *   **Windows 驗證 (Windows Authentication)**：這是最常見且推薦的方式。它使用您當前登入 Windows 的使用者帳戶來驗證。如果您的 Windows 帳戶被授予了 SQL Server 的存取權限，則可以使用此方式。
    *   **SQL Server 驗證 (SQL Server Authentication)**：需要提供 SQL Server 建立的使用者名稱 (Login) 和密碼。通常用於遠端連線或特定應用程式。
5.  **點擊「連線」**：成功後，您將在 SSMS 的「物件總管」中看到您的 SQL Server 實例，展開它可以看到資料庫、安全性、伺服器物件等節點。

![SSMS Connect to Server](https://learn.microsoft.com/zh-tw/sql/ssms/download-sql-server-management-studio-ssms?view=sql-server-ver16#connection-properties-tab-options)
*此圖片為示意，實際介面可能因版本而異。*

#### 與相鄰概念的關聯

連線是您開始在 SQL Server 上進行任何操作的第一步。沒有成功的連線，您將無法執行 DDL 或 DML 指令，也無法管理資料庫物件。這確保了只有經過授權的使用者才能存取和修改您的資料。

-----

### 3.2 資料庫基本操作 (DDL)

DDL (Data Definition Language)，資料定義語言，主要用於定義、修改和刪除資料庫物件（如資料庫、資料表、索引等）的結構。

#### 核心概念：創建、選擇、修改與刪除資料庫

資料庫是 SQL Server 中組織資料的最高層級容器。在 SQL Server 中，您可以擁有多個資料庫，每個資料庫都是獨立的。

1.  **創建資料庫 (CREATE DATABASE)**：建立一個新的資料庫。
2.  **選擇資料庫 (USE)**：切換到指定的資料庫，以便後續的 SQL 指令都在該資料庫中執行。
3.  **修改資料庫 (ALTER DATABASE)**：修改資料庫的屬性，例如名稱、大小等。
4.  **刪除資料庫 (DROP DATABASE)**：永久刪除一個資料庫及其所有內容。

#### 例子與推導

##### 3.2.1 創建資料庫

使用 `CREATE DATABASE` 語句來建立新的資料庫。

```sql
CREATE DATABASE MyNewDatabase;
```

您可以指定更多選項，例如檔案路徑、大小等，但對於初學者，上述語法足夠。

##### 3.2.2 選擇資料庫

在執行操作之前，您需要告訴 SQL Server 您要在哪個資料庫中工作。

```sql
USE MyNewDatabase;
GO -- GO 是批次分隔符號，表示前面語句的結束，對某些工具如 SSMS 來說是必要的。
```
**注意**: `GO` 不是 T-SQL 語句，而是 SQL Server 工具 (如 SSMS) 用來分隔批次命令的。

##### 3.2.3 修改資料庫

修改資料庫名稱或屬性。

```sql
-- 修改資料庫名稱 (注意：此操作需要在 master 或其他資料庫中執行)
USE master;
ALTER DATABASE MyNewDatabase MODIFY NAME = NewDatabaseName;
```

```sql
-- 修改資料庫選項 (例如，將資料庫設定為唯讀)
USE master; -- 或其他非NewDatabaseName的資料庫
ALTER DATABASE NewDatabaseName SET READ_ONLY ON;
```

##### 3.2.4 刪除資料庫

使用 `DROP DATABASE` 語句來永久刪除一個資料庫。**此操作不可逆，請謹慎使用！**

```sql
-- 確保沒有其他使用者連線到此資料庫，否則會失敗
ALTER DATABASE NewDatabaseName SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
DROP DATABASE NewDatabaseName;
```
`ALTER DATABASE SET SINGLE_USER WITH ROLLBACK IMMEDIATE` 會強制斷開所有連線，以便刪除操作能夠成功。

#### 與相鄰概念的關聯

資料庫操作是資料表操作的基礎。您必須先有一個資料庫，才能在其中創建資料表。DDL 不僅僅限於資料庫本身，它更廣泛地應用於資料表、視圖、預存程序、索引等所有資料庫物件的結構定義。

-----

### 3.3 資料表基本操作 (DDL)

資料表是資料庫中實際儲存資料的容器，它由行 (rows) 和列 (columns) 組成。每列都有一個特定的資料類型，定義了該列可以儲存何種類型的資料。

#### 核心概念：創建、修改與刪除資料表

1.  **創建資料表 (CREATE TABLE)**：定義資料表的結構，包括欄位名稱、資料類型和約束。
2.  **修改資料表 (ALTER TABLE)**：在現有資料表中添加、修改或刪除欄位，或者添加、刪除約束。
3.  **刪除資料表 (DROP TABLE)**：永久刪除一個資料表及其所有資料。

#### 例子與推導

##### 3.3.1 常見資料類型簡介

在創建資料表時，為每個欄位選擇適當的資料類型非常重要。

| 資料類型        | 說明                                          | 範例                 |
| :-------------- | :-------------------------------------------- | :------------------- |
| `INT`           | 整數                                          | `123`, `-45`         |
| `BIGINT`        | 大整數                                        | `123456789012345`    |
| `DECIMAL(p, s)` | 精確數字，`p` 為總位數，`s` 為小數位數          | `DECIMAL(10, 2)` -> `123.45` |
| `VARCHAR(n)`    | 可變長度字串，`n` 為最大字元數                 | `VARCHAR(255)`       |
| `NVARCHAR(n)`   | 可變長度 Unicode 字串，`n` 為最大字元數        | `NVARCHAR(255)` (支援中文) |
| `DATE`          | 日期 (YYYY-MM-DD)                             | `'2023-10-26'`       |
| `DATETIME`      | 日期時間 (YYYY-MM-DD HH:MI:SS.mmm)            | `'2023-10-26 14:30:00'` |
| `BIT`           | 布林值 (0 或 1)                               | `0`, `1`             |

##### 3.3.2 常見約束簡介

約束用於強制資料庫中的資料完整性。

*   `PRIMARY KEY`：唯一識別資料表中的每一行。一個資料表只能有一個主鍵。主鍵欄位自動為 `NOT NULL` 和 `UNIQUE`。
*   `NOT NULL`：欄位不能包含 `NULL` 值。
*   `UNIQUE`：欄位中的所有值都必須是唯一的（除了 `NULL`）。
*   `FOREIGN KEY`：建立兩個資料表之間的關聯，強制參照完整性。
*   `DEFAULT`：為欄位提供一個預設值。
*   `CHECK`：強制欄位中的值滿足特定條件。

##### 3.3.3 創建資料表

使用 `CREATE TABLE` 語句來定義資料表的結構。

```sql
USE MyNewDatabase; -- 確保您正在正確的資料庫中工作
GO

CREATE TABLE Students (
    StudentID INT PRIMARY KEY,
    FirstName NVARCHAR(50) NOT NULL,
    LastName NVARCHAR(50) NOT NULL,
    DateOfBirth DATE,
    Email VARCHAR(100) UNIQUE,
    EnrollmentDate DATETIME DEFAULT GETDATE(),
    Grade DECIMAL(3, 1) CHECK (Grade >= 0 AND Grade <= 4.0)
);
```

##### 3.3.4 修改資料表

使用 `ALTER TABLE` 語句來修改現有資料表的結構。

```sql
-- 添加一個新欄位
ALTER TABLE Students
ADD PhoneNumber VARCHAR(20);

-- 修改一個欄位的資料類型或屬性 (注意：這可能導致資料遺失或轉換錯誤)
-- 例如，將 FirstName 的長度從 50 增加到 100
ALTER TABLE Students
ALTER COLUMN FirstName NVARCHAR(100) NOT NULL;

-- 刪除一個欄位
ALTER TABLE Students
DROP COLUMN PhoneNumber;

-- 添加一個新的約束 (例如，為 Email 欄位添加 UNIQUE 約束)
-- 如果 Email 欄位已經存在且可能包含重複值，這個操作會失敗
-- ALTER TABLE Students
-- ADD CONSTRAINT UQ_Students_Email UNIQUE (Email); 
-- (在 CREATE TABLE 時已經添加了，此處僅作示範)
```

##### 3.3.5 刪除資料表

使用 `DROP TABLE` 語句來永久刪除一個資料表及其所有資料。**此操作不可逆！**

```sql
DROP TABLE Students;
```

#### 與相鄰概念的關聯

資料表是儲存實際資料的地方，是 DML (資料操作語言) 操作的目標。在沒有資料表的情況下，您無法執行 `INSERT`、`SELECT`、`UPDATE` 或 `DELETE` 等操作。資料表的良好設計（包括資料類型和約束）直接影響資料的品質、儲存效率和查詢效能。

-----

### 3.4 資料操作語言 (DML) 核心

DML (Data Manipulation Language)，資料操作語言，主要用於查詢和修改資料庫中的資料。

#### 核心概念：插入、查詢、更新與刪除資料

1.  **插入資料 (INSERT INTO)**：將新的資料行添加到資料表中。
2.  **查詢資料 (SELECT)**：從一個或多個資料表中檢索資料。這是最常用的 DML 指令。
3.  **更新資料 (UPDATE)**：修改資料表中現有的資料行。
4.  **刪除資料 (DELETE FROM)**：從資料表中刪除資料行。

#### 例子與推導

##### 3.4.1 插入資料 (INSERT INTO)

將新的資料行添加到資料表中。

```sql
USE MyNewDatabase;
GO

-- 插入單行資料，明確指定所有欄位及其值
INSERT INTO Students (StudentID, FirstName, LastName, DateOfBirth, Email, EnrollmentDate, Grade)
VALUES (1, N'張', N'三', '2000-01-15', 'zhangsan@example.com', '2023-09-01', 3.5);

-- 插入單行資料，如果插入所有欄位且順序與定義一致，可以省略欄位列表
INSERT INTO Students
VALUES (2, N'李', N'四', '1999-05-20', 'lisi@example.com', '2023-09-01', 3.8);

-- 插入多行資料
INSERT INTO Students (StudentID, FirstName, LastName, DateOfBirth, Email) -- 注意：EnrollmentDate 有 DEFAULT 值，Grade 可為 NULL
VALUES
    (3, N'王', N'五', '2001-03-10', 'wangwu@example.com'),
    (4, N'趙', N'六', '2002-07-25', 'zhaoliu@example.com');
```

##### 3.4.2 查詢資料 (SELECT)

從資料表中檢索資料。

```sql
-- 查詢所有欄位和所有資料行
SELECT *
FROM Students;

-- 查詢特定欄位的所有資料行
SELECT StudentID, FirstName, LastName, Email
FROM Students;

-- 查詢特定條件的資料行 (WHERE 子句)
SELECT FirstName, LastName, Grade
FROM Students
WHERE Grade >= 3.7;

-- 查詢並排序結果 (ORDER BY 子句)
SELECT FirstName, LastName, Grade
FROM Students
ORDER BY Grade DESC, LastName ASC; -- 按成績降序，若成績相同則按姓氏升序

-- 限制查詢結果的數量 (TOP 子句)
SELECT TOP 2 *
FROM Students
ORDER BY Grade DESC;

-- 結合多個條件 (AND, OR)
SELECT *
FROM Students
WHERE DateOfBirth < '2000-01-01' AND Grade < 3.0;

-- 使用 LIKE 進行模糊查詢
SELECT *
FROM Students
WHERE FirstName LIKE N'張%'; -- 查詢姓「張」的學生
```

##### 3.4.3 更新資料 (UPDATE)

修改資料表中現有的資料行。

```sql
-- 更新所有學生的入學日期 (沒有 WHERE 子句會影響所有行，請謹慎！)
-- UPDATE Students
-- SET EnrollmentDate = GETDATE();

-- 更新特定學生的成績和郵箱
UPDATE Students
SET Grade = 4.0, Email = 'zhangsan_new@example.com'
WHERE StudentID = 1;

-- 更新多個符合條件的學生的入學日期
UPDATE Students
SET EnrollmentDate = '2024-01-01'
WHERE Grade < 3.5;
```

##### 3.4.4 刪除資料 (DELETE FROM)

從資料表中刪除資料行。

```sql
-- 刪除所有學生資料 (沒有 WHERE 子句會影響所有行，請謹慎！)
-- DELETE FROM Students;

-- 刪除特定學生的資料
DELETE FROM Students
WHERE StudentID = 2;

-- 刪除所有成績低於 2.0 的學生資料
DELETE FROM Students
WHERE Grade < 2.0;
```

#### 與相鄰概念的關聯

DML 操作是與資料庫互動最頻繁的方式。它們依賴於 DDL 所定義的資料表結構。如果資料表結構不正確或不完整，DML 操作可能會失敗（例如，插入違反 `NOT NULL` 約束的值），或者無法達到預期的結果。理解 DDL 和 DML 之間的關係是高效使用 SQL Server 的關鍵。

-----

### 3.5 常見錯誤與澄清

#### 1. 忘記 `WHERE` 子句的重要性

**錯誤**: 在 `UPDATE` 或 `DELETE` 語句中忘記使用 `WHERE` 子句。
**澄清**: `UPDATE` 和 `DELETE` 語句如果沒有 `WHERE` 子句，將會影響資料表中的所有資料行。這可能導致資料大量被修改或刪除，而且往往是不可逆的。

```sql
-- 錯誤範例：刪除 Students 資料表中的所有資料！
-- DELETE FROM Students;

-- 正確範例：只刪除 StudentID 為 5 的資料
-- DELETE FROM Students WHERE StudentID = 5;
```

#### 2. 資料類型選擇不當

**錯誤**: 為欄位選擇了不合適的資料類型，例如將日期儲存為 `VARCHAR`，或將大數字儲存為 `INT`。
**澄清**:
*   選擇精確的資料類型有助於資料完整性、儲存效率和查詢效能。
*   例如，日期應使用 `DATE` 或 `DATETIME` 類型，而不是 `VARCHAR`，這樣可以進行日期計算和有效排序。
*   如果數字超出 `INT` 的範圍（約 $\pm 2 \times 10^9$），應使用 `BIGINT` 或 `DECIMAL`。
*   文字資料如果包含多語言字符（如中文），應使用 `NVARCHAR` 而非 `VARCHAR`。

#### 3. SSMS 連線問題

**錯誤**: 無法連線到 SQL Server 實例。
**澄清**:
*   **伺服器名稱錯誤**: 檢查您輸入的伺服器名稱是否正確（例如，`.\SQLEXPRESS` 或 `localhost`）。
*   **SQL Server 服務未運行**: 確保 SQL Server 服務（和 SQL Server Browser 服務，如果使用具名實例）正在運行。可以通過「服務」管理工具檢查。
*   **防火牆問題**: 如果是遠端連線，防火牆可能阻擋了 SQL Server 的預設埠（1433）。
*   **驗證模式錯誤**: 確保您使用的驗證模式（Windows 驗證或 SQL Server 驗證）與伺服器設定相符，且憑證有效。
*   **網路連線問題**: 確保客戶端電腦可以與 SQL Server 所在的伺服器進行網路通訊。

#### 4. 忽略交易 (Transaction)

**錯誤**: 在重要操作中沒有使用交易。
**澄清**: 對於任何會修改資料的指令 (`INSERT`, `UPDATE`, `DELETE`)，特別是在多個相關操作需要同時成功或同時失敗時，都應考慮使用交易。交易可以確保資料的一致性，並允許在出錯時進行 `ROLLBACK` (回復)。

```sql
BEGIN TRANSACTION; -- 開始一個交易

-- 執行一組操作
INSERT INTO MyTable (Col1) VALUES ('Value1');
UPDATE AnotherTable SET Col2 = 'NewValue' WHERE Id = 1;

-- 檢查操作是否成功，如果失敗則 ROLLBACK
IF @@ERROR <> 0
BEGIN
    ROLLBACK TRANSACTION; -- 回復所有操作
    PRINT '操作失敗，已回復。';
END
ELSE
BEGIN
    COMMIT TRANSACTION; -- 確認所有操作
    PRINT '操作成功，已提交。';
END
```

-----

### 3.6 小練習 (附詳解)

#### 小練習 1：建立資料庫與資料表

**情境**: 為一家小型線上書店建立一個資料庫。您需要儲存書籍的基本資訊。

**目標**:
1.  創建一個名為 `BookStoreDB` 的資料庫。
2.  在 `BookStoreDB` 中創建一個名為 `Books` 的資料表，包含以下欄位：
    *   `BookID`：整數，主鍵，不能為空。
    *   `Title`：Unicode 字串，最大長度 255，不能為空。
    *   `Author`：Unicode 字串，最大長度 100，不能為空。
    *   `PublicationYear`：整數。
    *   `Price`：精確數字，總共 6 位，小數點後 2 位，不能為空。
    *   `StockQuantity`：整數，預設值為 0。

**步驟**:

1.  開啟 SQL Server Management Studio (SSMS)。
2.  開啟一個新的查詢視窗。
3.  撰寫 SQL 語句來完成上述目標。

**詳解**:

```sql
-- 1. 創建資料庫
CREATE DATABASE BookStoreDB;
GO

-- 2. 切換到 BookStoreDB 資料庫
USE BookStoreDB;
GO

-- 3. 創建 Books 資料表
CREATE TABLE Books (
    BookID INT PRIMARY KEY,
    Title NVARCHAR(255) NOT NULL,
    Author NVARCHAR(100) NOT NULL,
    PublicationYear INT,
    Price DECIMAL(6, 2) NOT NULL,
    StockQuantity INT DEFAULT 0
);
GO
```

#### 小練習 2：插入、查詢與更新資料

**情境**: 繼續使用 `BookStoreDB` 中的 `Books` 資料表。

**目標**:
1.  向 `Books` 資料表插入三本書籍的資料。
2.  查詢所有書籍的所有資訊。
3.  查詢由「村上春樹」撰寫的書籍的標題和價格。
4.  將 ID 為 101 的書籍價格更新為 499.00，並將庫存增加 50。

**步驟**:

1.  開啟 SQL Server Management Studio (SSMS)，並在 `BookStoreDB` 中開啟一個新的查詢視窗。
2.  撰寫 SQL 語句來完成上述目標。

**詳解**:

```sql
USE BookStoreDB;
GO

-- 1. 插入三本書籍的資料
INSERT INTO Books (BookID, Title, Author, PublicationYear, Price, StockQuantity)
VALUES
    (101, N'挪威的森林', N'村上春樹', 1987, 350.00, 100),
    (102, N'1Q84', N'村上春樹', 2009, 680.50, 75),
    (103, N'哈利波特：神秘的魔法石', N'J.K. 羅琳', 1997, 420.00, 120);
GO

-- 2. 查詢所有書籍的所有資訊
SELECT *
FROM Books;
GO

-- 3. 查詢由「村上春樹」撰寫的書籍的標題和價格
SELECT Title, Price
FROM Books
WHERE Author = N'村上春樹';
GO

-- 4. 將 ID 為 101 的書籍價格更新為 499.00，並將庫存增加 50
UPDATE Books
SET Price = 499.00, StockQuantity = StockQuantity + 50
WHERE BookID = 101;
GO

-- 再次查詢 ID 為 101 的書籍以驗證更新
SELECT *
FROM Books
WHERE BookID = 101;
GO
```

-----

### 3.7 延伸閱讀/參考

*   **SQL Server 官方文件**: Microsoft Docs 是學習 SQL Server 最權威的資源，包含了詳細的語法、功能說明和範例。
    *   [SQL Server 文件首頁](https://docs.microsoft.com/zh-tw/sql/sql-server/?view=sql-server-ver16)
    *   [T-SQL 參考 (Transact-SQL)](https://docs.microsoft.com/zh-tw/sql/t-sql/language-reference?view=sql-server-ver16)
*   **資料庫正規化 (Database Normalization)**: 理解如何設計高效且無冗餘的資料庫結構。
*   **進階 SELECT 語法**: 學習 `JOIN` (連接多個資料表)、`GROUP BY` (分組聚合)、`HAVING` (分組篩選)、子查詢 (Subqueries) 等。
*   **索引 (Indexes)**: 了解如何建立和使用索引來優化查詢效能。
*   **視圖 (Views)**、**預存程序 (Stored Procedures)** 和 **函數 (Functions)**: 學習如何建立和使用這些資料庫物件來簡化複雜操作、提高安全性與重複使用性。