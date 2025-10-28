# SQL 語言基礎

SQL (Structured Query Language，結構化查詢語言) 是所有關聯式資料庫的標準語言。它允許您操作和管理資料庫，執行資料查詢、插入、更新和刪除等操作。本章節將帶您認識 SQL 的核心概念、主要語法與應用。

### 核心概念：什麼是 SQL？

#### 定義與歷史
SQL 是一種宣告式語言，用於管理和查詢關聯式資料庫管理系統 (RDBMS) 中的資料。它最初由 IBM 在 1970 年代開發，當時稱為 SEQUEL (Structured English Query Language)，後來改名為 SQL，並成為 ANSI (美國國家標準協會) 和 ISO (國際標準化組織) 的標準。

#### SQL 的用途
SQL 語言的主要用途包括：
1.  **資料查詢 (Querying Data)**：從資料庫中檢索特定資料。
2.  **資料操作 (Manipulating Data)**：新增、修改或刪除資料。
3.  **資料定義 (Defining Data)**：建立、修改或刪除資料庫結構 (如表格、檢視、索引等)。
4.  **資料控制 (Controlling Data)**：管理資料庫的使用權限和安全性。
5.  **交易管理 (Transaction Management)**：確保資料操作的原子性、一致性、隔離性和持久性 (ACID)。

#### 關聯式資料庫系統 (RDBMS) 與 SQL
SQL 是與關聯式資料庫管理系統 (RDBMS) 互動的標準介面。常見的 RDBMS 包括 MySQL, PostgreSQL, Oracle Database, Microsoft SQL Server, SQLite 等。雖然各個 RDBMS 對 SQL 標準有其自身的方言 (dialect) 和擴展，但核心的 SQL 語法和概念是通用的。

#### SQL 語言的分類
SQL 語句可以根據其功能分為以下幾種類型：

1.  **資料定義語言 (DDL - Data Definition Language)**
    *   用於定義、修改或刪除資料庫物件的結構。
    *   主要指令：`CREATE` (建立), `ALTER` (修改), `DROP` (刪除)。
    *   例如：`CREATE TABLE`, `ALTER TABLE`, `DROP TABLE`。

2.  **資料操作語言 (DML - Data Manipulation Language)**
    *   用於管理和操作資料庫中的資料。
    *   主要指令：`SELECT` (查詢), `INSERT` (插入), `UPDATE` (更新), `DELETE` (刪除)。
    *   例如：`INSERT INTO`, `SELECT FROM`, `UPDATE SET`, `DELETE FROM`。

3.  **資料控制語言 (DCL - Data Control Language)**
    *   用於管理資料庫的安全和存取權限。
    *   主要指令：`GRANT` (授予權限), `REVOKE` (撤銷權限)。
    *   例如：`GRANT SELECT ON table_name TO user_name`。

4.  **交易控制語言 (TCL - Transaction Control Language)**
    *   用於管理資料庫交易，確保資料操作的完整性。
    *   主要指令：`COMMIT` (確認交易), `ROLLBACK` (回溯交易), `SAVEPOINT` (設定儲存點)。
    *   例如：`BEGIN TRANSACTION`, `COMMIT`, `ROLLBACK`。
    
本章節將主要聚焦於 DDL 和 DML 的基礎應用，因為它們是日常資料庫操作的核心。

-----

### 資料定義語言 (DDL)

DDL 語句用於建立、修改和刪除資料庫物件，例如表格 (Table)、檢視 (View)、索引 (Index) 等。

#### 1. `CREATE TABLE`：建立表格
`CREATE TABLE` 語句用於在資料庫中建立新的表格。表格是關聯式資料庫中儲存資料的基本單位，由多個欄位 (Columns) 和多筆記錄 (Rows) 組成。

##### 語法結構
```sql
CREATE TABLE table_name (
    column1_name data_type [CONSTRAINT],
    column2_name data_type [CONSTRAINT],
    ...
    [table_constraint]
);
```

##### 常用資料型態
*   **整數型**：`INT` (或 `INTEGER`), `SMALLINT`, `BIGINT`
*   **浮點數型**：`FLOAT`, `DOUBLE`, `DECIMAL(p, s)` (精確數字，p 為總位數，s 為小數點後位數)
*   **字串型**：`VARCHAR(length)` (變長字串), `CHAR(length)` (定長字串), `TEXT` (長文字)
*   **日期時間型**：`DATE` (日期), `TIME` (時間), `DATETIME` 或 `TIMESTAMP` (日期時間)
*   **布林型**：`BOOLEAN` (或 `BOOL`, `TINYINT(1)` 在 MySQL 中常用)

##### 表格約束 (Constraints)
約束是規則，用於限制表格中資料的有效性，確保資料的完整性。
*   `PRIMARY KEY`：主鍵，唯一識別表格中的每一筆記錄，不能為 NULL。一個表格只能有一個主鍵。
*   `NOT NULL`：強制欄位不能為 NULL。
*   `UNIQUE`：強制欄位中的所有值都是唯一的。
*   `DEFAULT value`：為欄位設定預設值。
*   `FOREIGN KEY`：外鍵，用於建立兩個表格之間的關聯，確保參照的完整性。
*   `CHECK condition`：強制欄位中的值必須符合特定條件。

##### 例子：建立 `Students` 表格
假設我們要建立一個 `Students` 表格，包含學號、姓名、性別、出生日期、主修和入學日期。

```sql
CREATE TABLE Students (
    StudentID INT PRIMARY KEY,
    Name VARCHAR(100) NOT NULL,
    Gender VARCHAR(10),
    DateOfBirth DATE,
    Major VARCHAR(50),
    EnrollmentDate DATE DEFAULT CURRENT_DATE
);
```
*   `StudentID` 被定義為主鍵，且是整數。
*   `Name` 不能為空值 (NOT NULL)。
*   `EnrollmentDate` 如果沒有明確指定，將自動設定為當前日期 (CURRENT_DATE)。

#### 2. `ALTER TABLE`：修改表格結構
`ALTER TABLE` 語句用於修改已存在的表格的結構，例如新增、修改或刪除欄位，或新增、刪除約束。

##### 新增欄位 (`ADD COLUMN`)
```sql
ALTER TABLE Students
ADD COLUMN Email VARCHAR(100) UNIQUE;
```
這會在 `Students` 表格中新增一個 `Email` 欄位，型態為 `VARCHAR(100)`，且值必須是唯一的。

##### 修改欄位 (`MODIFY COLUMN` 或 `ALTER COLUMN`)
語法在不同資料庫中可能略有不同。例如，在 MySQL 中使用 `MODIFY COLUMN`，在 PostgreSQL 中使用 `ALTER COLUMN`。

以 MySQL 為例：
```sql
ALTER TABLE Students
MODIFY COLUMN Major VARCHAR(100) DEFAULT '未定'; -- 修改 Major 欄位的長度並設定預設值
```

以 PostgreSQL 為例：
```sql
ALTER TABLE Students
ALTER COLUMN Major TYPE VARCHAR(100),
ALTER COLUMN Major SET DEFAULT '未定';
```

##### 刪除欄位 (`DROP COLUMN`)
```sql
ALTER TABLE Students
DROP COLUMN Gender;
```
這會從 `Students` 表格中刪除 `Gender` 欄位。

##### 新增/刪除約束
```sql
-- 新增一個 CHECK 約束
ALTER TABLE Students
ADD CONSTRAINT CHK_Age CHECK (DateOfBirth < CURRENT_DATE); -- 確保出生日期在未來

-- 刪除一個 UNIQUE 約束 (假設 Email 之前設定了 UNIQUE 約束)
-- 刪除約束通常需要知道約束的名稱。如果沒有指定名稱，資料庫會自動生成。
-- 以 MySQL 為例 (若約束名稱為 Students_Email_Key)：
ALTER TABLE Students
DROP INDEX Email;

-- 以 PostgreSQL 為例 (若約束名稱為 students_email_key)：
ALTER TABLE Students
DROP CONSTRAINT students_email_key;
```

#### 3. `DROP TABLE`：刪除表格
`DROP TABLE` 語句用於徹底刪除資料庫中的一個表格及其所有資料和結構。這是一個不可逆的操作，請謹慎使用。

##### 語法
```sql
DROP TABLE table_name;
```

##### 例子：刪除表格
```sql
DROP TABLE Students;
```
這會刪除 `Students` 表格及其所有資料。

-----

### 資料操作語言 (DML)

DML 語句用於對資料庫中的資料進行操作，包括新增、查詢、更新和刪除。

#### 1. `INSERT INTO`：新增資料
`INSERT INTO` 語句用於向表格中新增一筆或多筆記錄。

##### 指定所有欄位
如果按照表格定義的順序提供所有欄位的值，可以省略欄位名稱。
```sql
INSERT INTO Students VALUES (1001, '王小明', '男', '2000-01-15', '資訊工程', '2019-09-01');
```

##### 指定部分欄位
通常建議明確指定要插入的欄位，尤其當表格有預設值或允許 NULL 的欄位時。
```sql
INSERT INTO Students (StudentID, Name, DateOfBirth, Major)
VALUES (1002, '林美玲', '2001-05-20', '電機工程');
-- Gender 和 EnrollmentDate 將分別使用 NULL 和預設值
```

##### 新增多筆資料 (若資料庫支援)
許多資料庫允許在一個 `INSERT` 語句中插入多筆資料，以提高效率。
```sql
INSERT INTO Students (StudentID, Name, Gender, DateOfBirth, Major)
VALUES
    (1003, '陳大華', '男', '1999-11-10', '資訊工程'),
    (1004, '張雅婷', '女', '2002-03-25', '企業管理'),
    (1005, '李文傑', '男', '2000-08-08', '經濟學');
```

#### 2. `SELECT`：查詢資料 (SQL 的核心)
`SELECT` 語句是 SQL 中最常用、功能最強大的語句，用於從資料庫中檢索資料。

##### 語法結構 (基本形式)
```sql
SELECT column1, column2, ...
FROM table_name
WHERE condition
ORDER BY column_name ASC|DESC;
```

##### `SELECT *` 與 `SELECT column_list`
*   `SELECT *`：選取表格中的所有欄位。
    ```sql
    SELECT *
    FROM Students;
    ```
*   `SELECT column_list`：選取指定的欄位。
    ```sql
    SELECT StudentID, Name, Major
    FROM Students;
    ```

##### `FROM` 子句
指定要從哪個表格中查詢資料。

##### `WHERE` 子句：篩選條件
`WHERE` 子句用於根據指定的條件篩選記錄。只有滿足條件的記錄才會被選取。

*   **比較運算子**：
    *   `=`：等於
    *   `!=` 或 `<>`：不等於
    *   `<`：小於
    *   `>`：大於
    *   `<=`：小於或等於
    *   `>=`：大於或等於
    ```sql
    SELECT Name, Major
    FROM Students
    WHERE StudentID = 1001; -- 查詢學號為 1001 的學生
    ```

*   **邏輯運算子**：
    *   `AND`：邏輯與，兩個條件都必須為真
    *   `OR`：邏輯或，任一條件為真即可
    *   `NOT`：邏輯非，反轉條件
    ```sql
    SELECT Name, Major
    FROM Students
    WHERE Major = '資訊工程' AND Gender = '男'; -- 查詢資訊工程系的所有男生
    
    SELECT Name, Major
    FROM Students
    WHERE Major = '資訊工程' OR Major = '電機工程'; -- 查詢資訊工程系或電機工程系的學生
    
    SELECT Name, Major
    FROM Students
    WHERE NOT Major = '資訊工程'; -- 查詢非資訊工程系的學生
    ```

*   **特殊運算子**：
    *   `IN (value1, value2, ...)`：值在列表中的任一個。
        ```sql
        SELECT Name, Major
        FROM Students
        WHERE Major IN ('資訊工程', '經濟學'); -- 查詢主修是資訊工程或經濟學的學生
        ```
    *   `BETWEEN value1 AND value2`：值在指定範圍內 (包含兩端)。
        ```sql
        SELECT Name, DateOfBirth
        FROM Students
        WHERE DateOfBirth BETWEEN '2000-01-01' AND '2000-12-31'; -- 查詢 2000 年出生的學生
        ```
    *   `LIKE pattern`：模糊匹配字串。
        *   `%`：代表零個或多個字元。
        *   `_` (底線)：代表單個字元。
        ```sql
        SELECT Name, Major
        FROM Students
        WHERE Name LIKE '王%'; -- 查詢姓「王」的學生
        
        SELECT Name, Major
        FROM Students
        WHERE Major LIKE '%工程%'; -- 查詢主修名稱包含「工程」的學生
        ```
    *   `IS NULL` / `IS NOT NULL`：判斷值是否為 NULL。
        ```sql
        SELECT Name, Email
        FROM Students
        WHERE Email IS NULL; -- 查詢 Email 為空的學生
        ```

##### `ORDER BY` 子句：排序結果
`ORDER BY` 子句用於對查詢結果進行排序。
*   `ASC`：升序 (預設值)。
*   `DESC`：降序。
```sql
SELECT StudentID, Name, DateOfBirth
FROM Students
ORDER BY DateOfBirth DESC, Name ASC; -- 先按出生日期降序，如果日期相同，再按姓名升序
```

##### 聚合函數 (Aggregate Functions)
聚合函數對一組值執行計算，並返回一個單一值。
*   `COUNT()`：計算行數。
    *   `COUNT(*)`：計算所有行。
    *   `COUNT(column_name)`：計算指定欄位非 NULL 的行數。
    *   `COUNT(DISTINCT column_name)`：計算指定欄位唯一值的行數。
    ```sql
    SELECT COUNT(*) AS TotalStudents
    FROM Students; -- 計算學生總人數
    
    SELECT COUNT(DISTINCT Major) AS NumberOfMajors
    FROM Students; -- 計算主修的種類數量
    ```
*   `SUM(column_name)`：計算指定數值欄位的總和。
*   `AVG(column_name)`：計算指定數值欄位的平均值。
*   `MAX(column_name)`：找出指定欄位的最大值。
*   `MIN(column_name)`：找出指定欄位的最小值。
    ```sql
    -- 假設有一個 Courses 表格，有 Credits 欄位
    -- CREATE TABLE Courses (CourseID INT PRIMARY KEY, CourseName VARCHAR(100) NOT NULL, Credits INT NOT NULL);
    -- INSERT INTO Courses VALUES (101, '資料庫系統', 3), (102, '演算法', 3), (103, '線性代數', 2);
    
    SELECT SUM(Credits) AS TotalCredits,
           AVG(Credits) AS AverageCredits,
           MAX(Credits) AS MaxCredits,
           MIN(Credits) AS MinCredits
    FROM Courses;
    ```

##### `LIMIT` / `TOP` / `FETCH`：限制結果數量
用於限制查詢結果返回的記錄數量。語法因資料庫而異：
*   **MySQL, PostgreSQL, SQLite**：使用 `LIMIT`
    ```sql
    SELECT Name, Major
    FROM Students
    ORDER BY StudentID
    LIMIT 3; -- 選取前 3 筆記錄
    ```
*   **SQL Server**：使用 `TOP`
    ```sql
    SELECT TOP 3 Name, Major
    FROM Students
    ORDER BY StudentID;
    ```
*   **Oracle 12c+**：使用 `FETCH FIRST N ROWS ONLY`
    ```sql
    SELECT Name, Major
    FROM Students
    ORDER BY StudentID
    FETCH FIRST 3 ROWS ONLY;
    ```

#### 3. `UPDATE`：修改資料
`UPDATE` 語句用於修改表格中已存在的記錄。

##### 語法結構
```sql
UPDATE table_name
SET column1 = value1, column2 = value2, ...
WHERE condition;
```

##### `WHERE` 子句 (重要！)
`WHERE` 子句非常重要，它決定了哪些記錄會被更新。如果省略 `WHERE` 子句，表格中所有記錄的指定欄位都將被修改，這通常不是您想要的。

##### 例子：修改學生資料
```sql
-- 將學號 1001 的學生主修改為 '人工智慧'
UPDATE Students
SET Major = '人工智慧'
WHERE StudentID = 1001;

-- 將所有主修為 '電機工程' 的學生，入學日期更新為 '2020-09-01'
UPDATE Students
SET EnrollmentDate = '2020-09-01'
WHERE Major = '電機工程';
```

#### 4. `DELETE FROM`：刪除資料
`DELETE FROM` 語句用於從表格中刪除一筆或多筆記錄。

##### 語法結構
```sql
DELETE FROM table_name
WHERE condition;
```

##### `WHERE` 子句 (重要！)
同樣地，`WHERE` 子句非常重要，它決定了哪些記錄會被刪除。如果省略 `WHERE` 子句，表格中所有記錄都將被刪除，這也是一個非常危險的操作。

##### 例子：刪除學生資料
```sql
-- 刪除學號為 1005 的學生記錄
DELETE FROM Students
WHERE StudentID = 1005;

-- 刪除所有主修為 '經濟學' 的學生記錄
DELETE FROM Students
WHERE Major = '經濟學';

-- 刪除所有學生記錄 (請謹慎使用！)
-- DELETE FROM Students;
```

-----

### 與相鄰概念的關聯

#### SQL 與資料庫系統
SQL 是與關聯式資料庫系統 (RDBMS) 互動的標準語言。沒有 SQL，我們就無法有效地從這些資料庫中存取、管理或分析資料。它是 RDBMS 的使用者介面和操作指令集。

#### SQL 與應用程式開發
在現代應用程式開發中，無論是網頁應用、行動應用還是桌面應用，後端程式經常需要與資料庫互動以儲存和檢索資料。開發者會使用各種語言 (如 Python, Java, Node.js, PHP) 透過特定的資料庫連接器 (如 JDBC, ODBC) 或物件關聯對映 (ORM) 框架 (如 SQLAlchemy, Hibernate) 來執行 SQL 語句。SQL 是這些應用程式資料持久化的基石。

#### SQL 與資料分析
SQL 是資料分析師和資料科學家的基本工具之一。它允許他們從龐大的資料集中提取特定資料、進行聚合、過濾和排序，為進一步的分析和視覺化提供基礎。許多資料分析平台也直接支援 SQL 查詢。

-----

### 常見錯誤與澄清

#### 1. 忘記 `WHERE` 子句
**錯誤**：在 `UPDATE` 或 `DELETE` 語句中忘記 `WHERE` 子句會導致所有記錄被修改或刪除。這是最常見且最具破壞性的錯誤之一。
**澄清**：在執行 `UPDATE` 或 `DELETE` 前，務必仔細檢查 `WHERE` 子句，確保只影響目標記錄。在生產環境操作時，先在測試環境或使用 `SELECT` 語句模擬 `WHERE` 條件來驗證結果。

#### 2. 字串與數值的引用方式
**錯誤**：在 SQL 中，字串值必須用單引號 `' '` 包裹，而數值則不需要。混淆兩者會導致語法錯誤或非預期結果。
```sql
-- 錯誤範例 (字串沒有引號)
SELECT * FROM Students WHERE Name = 王小明; 
-- 錯誤範例 (數值加了引號，雖然有些資料庫會自動轉換，但不建議)
SELECT * FROM Students WHERE StudentID = '1001'; 
```
**澄清**：
*   字串：`WHERE Name = '王小明'`
*   數值：`WHERE StudentID = 1001`
*   日期時間：`WHERE DateOfBirth = '2000-01-15'` (通常也用單引號)

#### 3. SQL 語法的大小寫敏感度
**錯誤**：許多初學者認為 SQL 語法是大小寫敏感的。
**澄清**：SQL 關鍵字 (如 `SELECT`, `FROM`, `WHERE`) 通常是不區分大小寫的 (例如 `select` 和 `SELECT` 效果相同)。然而，資料庫中儲存的**資料**本身 (例如字串值 `Name = '王小明'`) 以及某些資料庫系統中的**物件名稱** (例如表格名稱 `Students` 或 `students`) 可能會區分大小寫，這取決於資料庫的配置和作業系統。最佳實踐是保持一致性，例如所有 SQL 關鍵字都大寫，所有物件名稱都小寫。

#### 4. `DELETE` 與 `TRUNCATE` 的差異
**錯誤**：混淆 `DELETE FROM table_name;` (沒有 `WHERE` 子句) 與 `TRUNCATE TABLE table_name;`。兩者都能刪除表格中的所有資料。
**澄清**：
*   `DELETE FROM table_name;`：DML 命令。它會逐行刪除資料，並記錄在交易日誌中。可以搭配 `WHERE` 篩選，可以觸發觸發器 (triggers)，並且可以被 `ROLLBACK` (回溯)。
*   `TRUNCATE TABLE table_name;`：DDL 命令。它會更快地刪除所有資料，透過重新建立表格的方式，不會記錄在交易日誌中 (或記錄極少)。不能搭配 `WHERE` 篩選，不能觸發觸發器，並且通常不能被 `ROLLBACK`。它還會重置自動增長 (AUTO_INCREMENT) 的計數器。
    一般來說，如果想快速清空整個表格且不需要回溯，使用 `TRUNCATE`。如果需要有條件刪除或需要交易管理，使用 `DELETE`。

#### 5. 錯誤的條件判斷
**錯誤**：在 `WHERE` 子句中使用不正確的邏輯或運算子。
```sql
-- 錯誤範例：試圖查詢 Major 等於 '資訊工程' AND '電機工程' (這是邏輯上的不可能)
SELECT * FROM Students WHERE Major = '資訊工程' AND Major = '電機工程';
```
**澄清**：當需要查詢一個欄位有多個可能值時，應該使用 `OR` 或 `IN`。
```sql
SELECT * FROM Students WHERE Major = '資訊工程' OR Major = '電機工程';
SELECT * FROM Students WHERE Major IN ('資訊工程', '電機工程');
```

-----

### 小練習（附詳解）

我們將使用以下表格結構和初始資料來進行練習：

**`Students` 表格**
*   `StudentID` (INT, PRIMARY KEY)
*   `Name` (VARCHAR(100), NOT NULL)
*   `Major` (VARCHAR(50))
*   `EnrollmentYear` (INT)
*   `GPA` (DECIMAL(3, 2))

**初始資料**
| StudentID | Name   | Major    | EnrollmentYear | GPA  |
| :-------- | :----- | :------- | :------------- | :--- |
| 101       | 林小君 | 資訊工程 | 2021           | 3.85 |
| 102       | 陳大明 | 電機工程 | 2022           | 3.20 |
| 103       | 張美麗 | 資訊工程 | 2021           | 3.92 |
| 104       | 王志遠 | 商業管理 | 2023           | 3.50 |
| 105       | 李曉華 | 電機工程 | 2022           | 3.65 |
| 106       | 黃國強 | 商業管理 | 2021           | 3.10 |

#### 練習一：學生資料庫操作

**問題描述：**
請根據上述表格結構和初始資料，完成以下 SQL 操作：

1.  **建立表格**：建立 `Students` 表格。
2.  **插入資料**：將上述初始資料插入到 `Students` 表格中。
3.  **查詢資料**：
    *   查詢所有學生中主修為「資訊工程」的學生姓名、學號和 GPA，並按照 GPA 由高到低排序。
    *   查詢入學年份在 2022 年之前的學生人數。
4.  **更新資料**：將學號為 104 的學生主修改為「會計學」，並將 GPA 調整為 3.70。
5.  **刪除資料**：刪除所有 GPA 低於 3.5 的學生記錄。

**詳解：**

1.  **建立表格**
    ```sql
    CREATE TABLE Students (
        StudentID INT PRIMARY KEY,
        Name VARCHAR(100) NOT NULL,
        Major VARCHAR(50),
        EnrollmentYear INT,
        GPA DECIMAL(3, 2)
    );
    ```

2.  **插入資料**
    ```sql
    INSERT INTO Students (StudentID, Name, Major, EnrollmentYear, GPA) VALUES
    (101, '林小君', '資訊工程', 2021, 3.85),
    (102, '陳大明', '電機工程', 2022, 3.20),
    (103, '張美麗', '資訊工程', 2021, 3.92),
    (104, '王志遠', '商業管理', 2023, 3.50),
    (105, '李曉華', '電機工程', 2022, 3.65),
    (106, '黃國強', '商業管理', 2021, 3.10);
    ```

3.  **查詢資料**
    *   查詢所有學生中主修為「資訊工程」的學生姓名、學號和 GPA，並按照 GPA 由高到低排序。
        ```sql
        SELECT Name, StudentID, GPA
        FROM Students
        WHERE Major = '資訊工程'
        ORDER BY GPA DESC;
        ```
        **預期結果：**
        | Name   | StudentID | GPA  |
        | :----- | :-------- | :--- |
        | 張美麗 | 103       | 3.92 |
        | 林小君 | 101       | 3.85 |

    *   查詢入學年份在 2022 年之前的學生人數。
        ```sql
        SELECT COUNT(*) AS StudentsBefore2022
        FROM Students
        WHERE EnrollmentYear < 2022;
        ```
        **預期結果：**
        | StudentsBefore2022 |
        | :----------------- |
        | 3                  |
        (學號 101, 103, 106)

4.  **更新資料**
    ```sql
    UPDATE Students
    SET Major = '會計學', GPA = 3.70
    WHERE StudentID = 104;
    ```
    **驗證結果：** (執行後可使用 `SELECT * FROM Students WHERE StudentID = 104;` 查詢確認)
    | StudentID | Name   | Major  | EnrollmentYear | GPA  |
    | :-------- | :----- | :----- | :------------- | :--- |
    | 104       | 王志遠 | 會計學 | 2023           | 3.70 |

5.  **刪除資料**
    ```sql
    DELETE FROM Students
    WHERE GPA < 3.5;
    ```
    **驗證結果：** (執行後可使用 `SELECT * FROM Students;` 查詢確認)
    被刪除的學生是：
    *   102 (3.20)
    *   106 (3.10)
    
    表格剩餘資料應為：
    | StudentID | Name   | Major    | EnrollmentYear | GPA  |
    | :-------- | :----- | :------- | :------------- | :--- |
    | 101       | 林小君 | 資訊工程 | 2021           | 3.85 |
    | 103       | 張美麗 | 資訊工程 | 2021           | 3.92 |
    | 104       | 王志遠 | 會計學   | 2023           | 3.70 |
    | 105       | 李曉華 | 電機工程 | 2022           | 3.65 |

-----

### 延伸閱讀

1.  **資料庫正規化 (Database Normalization)**：學習如何設計高效、無冗餘且資料完整性高的關聯式資料庫結構，例如 1NF, 2NF, 3NF。
2.  **檢視 (Views) 與索引 (Indexes)**：
    *   **檢視 (View)**：虛擬表格，基於一個或多個表格的查詢結果，常用於簡化複雜查詢和控制資料存取。
    *   **索引 (Index)**：類似書本的目錄，用於加速資料查詢，但會增加寫入操作的開銷。
3.  **交易管理 (Transactions) 與 ACID 特性**：深入了解 SQL 的交易 (Transaction) 概念，以及 ACID (原子性 Atomicity, 一致性 Consistency, 隔離性 Isolation, 持久性 Durability) 特性如何確保資料庫操作的可靠性。
4.  **常見 RDBMS 系統**：探索不同關聯式資料庫管理系統 (如 MySQL, PostgreSQL, SQL Server, Oracle) 的特性、優缺點和特定 SQL 方言。
5.  **資料庫管理工具**：學習使用如 DBeaver, DataGrip, HeidiSQL, pgAdmin, MySQL Workbench 等圖形化工具來更有效地管理和操作資料庫。