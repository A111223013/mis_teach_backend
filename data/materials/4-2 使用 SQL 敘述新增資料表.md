# 4-2 使用 SQL 敘述新增資料表

在關聯式資料庫中，所有資料都儲存在資料表中。資料表是資料庫的基本組成單位，它定義了資料的結構和儲存方式。本章節將深入探討如何使用 SQL 語言中的 `CREATE TABLE` 敘述來建立新的資料表。

-----

### 核心概念：資料表與 `CREATE TABLE`

#### 什麼是資料表？
資料表 (Table) 是由「欄 (Column)」和「列 (Row)」組成的二維結構，用來組織和儲存特定主題的資料。
- **欄 (Column)**：代表資料的屬性或類別，例如「姓名」、「學號」或「價格」。每個欄位都有一個特定的資料型態（例如文字、數字、日期）和潛在的約束條件。
- **列 (Row)**：代表單一的紀錄或實體，包含該實體在所有欄位上的值。例如，一個學生的所有資訊（學號、姓名、年齡、主修）組成一列。

資料表的設計是資料庫設計的核心，它直接影響資料的完整性、查詢效率和資料庫的整體性能。

#### 為什麼需要建立資料表？
在您能儲存任何資料之前，必須先定義資料庫中資料的結構。`CREATE TABLE` 敘述就是 DDL (Data Definition Language，資料定義語言) 的一部分，專門用於定義這種結構。透過它，您可以：
1. **定義資料儲存的骨架**：明確每個欄位將儲存什麼類型的資料。
2. **確保資料完整性**：透過約束 (Constraints) 來限制資料的有效性，例如設定主鍵、非空、唯一值等。
3. **支援資料操作**：一旦資料表被建立，您才能使用 DML (Data Manipulation Language，資料操作語言) 語句（如 `INSERT`、`SELECT`、`UPDATE`、`DELETE`）來操作資料。

#### `CREATE TABLE` 的基本語法
`CREATE TABLE` 敘述用於在資料庫中建立一個新的資料表。其基本結構如下：

```sql
CREATE TABLE 表名 (
    欄位1 資料型態 [約束],
    欄位2 資料型態 [約束],
    ...
    [表級約束]
);
```

- **`CREATE TABLE`**：SQL 關鍵字，表示要建立一個新的資料表。
- **`表名`**：您為資料表指定的名稱，必須在資料庫中是唯一的。
- **`欄位名`**：資料表中每個欄位的名稱，必須在該表中是唯一的。
- **`資料型態 (Data Type)`**：指定該欄位可以儲存的資料種類（例如：`INT`、`VARCHAR`、`DATE`、`DECIMAL` 等）。這是每個欄位都必須指定的。
- **`約束 (Constraint)`**：可選的規則，用於限制該欄位或整個資料表中的資料。約束旨在確保資料的準確性和完整性。常見的約束有：
    - `PRIMARY KEY`：主鍵，唯一標識表中的每一列，且不能為 `NULL`。
    - `NOT NULL`：該欄位的值不能為 `NULL`。
    - `UNIQUE`：該欄位中的所有值都是唯一的。
    - `DEFAULT 值`：為該欄位設定一個預設值，當插入新列且未指定該欄位的值時，將自動使用預設值。
    - `FOREIGN KEY`：外來鍵，用於建立與另一個表的關聯。
    - `CHECK 條件`：確保欄位中的所有值都滿足特定條件。

-----

### 典型例子與推導

讓我們透過幾個例子來理解 `CREATE TABLE` 的實際應用。

#### 範例 1：建立一個簡單的學生資料表
我們想建立一個 `Students` 資料表，用於儲存學生的學號、姓名、年齡和主修科系。

```sql
CREATE TABLE Students (
    StudentID INT PRIMARY KEY,
    Name VARCHAR(100) NOT NULL,
    Age INT,
    Major VARCHAR(50) DEFAULT '未指定'
);
```

**推導：**
1. **`StudentID INT PRIMARY KEY`**:
   - `StudentID` 是欄位名稱。
   - `INT` 指定學號為整數型態。
   - `PRIMARY KEY` 設定 `StudentID` 為這個資料表的主鍵，表示每個學生的學號必須是唯一的，且不能為 `NULL`。

2. **`Name VARCHAR(100) NOT NULL`**:
   - `Name` 是欄位名稱。
   - `VARCHAR(100)` 指定姓名為可變長度字串，最大長度為 100 個字元。
   - `NOT NULL` 要求每個學生的姓名都必須提供，不能為 `NULL`。

3. **`Age INT`**:
   - `Age` 是欄位名稱。
   - `INT` 指定年齡為整數型態。這裡沒有其他約束，表示年齡可以為 `NULL`。

4. **`Major VARCHAR(50) DEFAULT '未指定'`**:
   - `Major` 是欄位名稱。
   - `VARCHAR(50)` 指定主修為可變長度字串，最大長度為 50 個字元。
   - `DEFAULT '未指定'` 表示如果插入新學生資料時沒有指定 `Major`，它將自動設定為 `'未指定'`。

#### 範例 2：引入日期、浮點數與複合主鍵
我們想建立一個 `Courses` 資料表，用於儲存課程資訊，並定義一個由課程代碼和學期組成的複合主鍵。

```sql
CREATE TABLE Courses (
    CourseCode VARCHAR(10) NOT NULL,
    Semester VARCHAR(10) NOT NULL,
    CourseName VARCHAR(200) UNIQUE,
    Credits DECIMAL(3,1) NOT NULL,
    StartDate DATE,
    PRIMARY KEY (CourseCode, Semester)
);
```

**推導：**
1. **`CourseCode VARCHAR(10) NOT NULL`** 和 **`Semester VARCHAR(10) NOT NULL`**:
   - 分別定義課程代碼和學期為非空字串。它們將共同構成主鍵。

2. **`CourseName VARCHAR(200) UNIQUE`**:
   - `CourseName` 為課程名稱，`UNIQUE` 約束確保每個課程名稱在表中都是唯一的，但允許為 `NULL`。

3. **`Credits DECIMAL(3,1) NOT NULL`**:
   - `DECIMAL(3,1)` 用於儲存帶小數點的數字，其中 `3` 表示總共可有 3 位數字，`1` 表示小數點後有 1 位數字。例如，2.5, 3.0。
   - `NOT NULL` 要求學分數必須提供。

4. **`StartDate DATE`**:
   - `DATE` 儲存日期值（年、月、日）。

5. **`PRIMARY KEY (CourseCode, Semester)`**:
   - 這是「表級約束」的例子。當主鍵由多個欄位組成時，需要這樣定義。它表示 `(CourseCode, Semester)` 的組合必須是唯一的，且兩者都不能為 `NULL`。

#### 範例 3：建立外來鍵關聯
我們想建立一個 `Enrollments` 資料表，記錄學生選修課程的資訊。這需要引用 `Students` 表的 `StudentID` 和 `Courses` 表的 `CourseCode` 和 `Semester`。

假設 `Students` 表和 `Courses` 表已經如上述範例建立。

```sql
CREATE TABLE Enrollments (
    EnrollmentID INT PRIMARY KEY AUTO_INCREMENT, -- AUTO_INCREMENT 為 MySQL 的自動遞增設定
    StudentID INT NOT NULL,
    CourseCode VARCHAR(10) NOT NULL,
    Semester VARCHAR(10) NOT NULL,
    EnrollmentDate DATE DEFAULT CURRENT_DATE, -- CURRENT_DATE 為當前日期
    Grade VARCHAR(2),
    
    FOREIGN KEY (StudentID) REFERENCES Students(StudentID),
    FOREIGN KEY (CourseCode, Semester) REFERENCES Courses(CourseCode, Semester)
);
```

**推導：**
1. **`EnrollmentID INT PRIMARY KEY AUTO_INCREMENT`**:
   - `EnrollmentID` 作為選課紀錄的主鍵。`AUTO_INCREMENT`（或 SQL Server 的 `IDENTITY(1,1)`，PostgreSQL 的 `SERIAL`）讓這個欄位在每次插入新資料時自動生成唯一的整數值，無需手動指定。

2. **`StudentID INT NOT NULL`, `CourseCode VARCHAR(10) NOT NULL`, `Semester VARCHAR(10) NOT NULL`**:
   - 這三個欄位用於儲存選課的學生、課程代碼和學期，都設定為非空。

3. **`EnrollmentDate DATE DEFAULT CURRENT_DATE`**:
   - 選課日期，預設值為當前系統日期。

4. **`Grade VARCHAR(2)`**:
   - 成績欄位，可以為 `NULL`。

5. **`FOREIGN KEY (StudentID) REFERENCES Students(StudentID)`**:
   - 這是一個外來鍵約束。它宣告 `Enrollments` 表中的 `StudentID` 欄位參考 `Students` 表中的 `StudentID` 欄位。這確保了所有選課的 `StudentID` 都必須在 `Students` 表中存在。

6. **`FOREIGN KEY (CourseCode, Semester) REFERENCES Courses(CourseCode, Semester)`**:
   - 這是一個複合外來鍵約束。它宣告 `Enrollments` 表中的 `CourseCode` 和 `Semester` 組合參考 `Courses` 表中的 `CourseCode` 和 `Semester` 組合。這確保了所有選課的課程都必須在 `Courses` 表中存在。

-----

### 與相鄰概念的關聯

#### 與資料型態 (Data Types) 的關聯
每個欄位在建立時都必須明確指定資料型態。資料型態決定了該欄位能儲存什麼樣的資料（例如：數字、文字、日期、布林值），以及這些資料將佔用多少儲存空間。選擇正確的資料型態對於資料的有效性、儲存效率和查詢性能都至關重要。

#### 與約束 (Constraints) 的關聯
約束是確保資料完整性的關鍵。在 `CREATE TABLE` 語句中定義約束，可以在資料進入資料庫時就強制執行資料規則，防止無效或不一致的資料被儲存。例如，`PRIMARY KEY` 保證唯一性和非空性，`FOREIGN KEY` 維護表之間的參考完整性。

#### 與 DDL (Data Definition Language) 其他語句的關聯
`CREATE TABLE` 是 DDL 的核心。一旦資料表被建立，您可能還需要使用其他 DDL 語句來修改或刪除它：
- **`ALTER TABLE`**：用於修改現有的資料表結構，例如添加、修改或刪除欄位，或者添加、刪除約束。
- **`DROP TABLE`**：用於永久刪除一個資料表及其所有資料。

#### 與 DML (Data Manipulation Language) 的關聯
`CREATE TABLE` 是所有 DML 操作的前提。沒有建立資料表，您就無法：
- **`INSERT`**：將新資料插入到表中。
- **`SELECT`**：從表中查詢資料。
- **`UPDATE`**：修改表中現有的資料。
- **`DELETE`**：從表中刪除資料。
資料表的結構定義了 DML 語句如何與資料互動的規則。

-----

### 進階內容：更多約束與索引觀念

#### `CHECK` 約束
`CHECK` 約束用於強制一個欄位中的所有值都滿足指定的條件。這是一個強大的工具，可以在資料儲存時進行業務邏輯驗證。

**範例：**
在 `Students` 表中添加一個 `CHECK` 約束，確保 `Age` 欄位的值必須大於 0 且小於 100。

```sql
-- 方法一：在 CREATE TABLE 時定義欄位級 CHECK
CREATE TABLE StudentsWithCheck (
    StudentID INT PRIMARY KEY,
    Name VARCHAR(100) NOT NULL,
    Age INT CHECK (Age > 0 AND Age < 100), -- 欄位級約束
    Major VARCHAR(50) DEFAULT '未指定'
);

-- 方法二：在 CREATE TABLE 時定義表級 CHECK
CREATE TABLE StudentsWithTableCheck (
    StudentID INT PRIMARY KEY,
    Name VARCHAR(100) NOT NULL,
    Age INT,
    Major VARCHAR(50) DEFAULT '未指定',
    CONSTRAINT CHK_Age CHECK (Age > 0 AND Age < 100) -- 表級約束，可命名
);
```
這兩種方法都能達到相同的效果，但表級約束允許您為約束命名，方便日後管理。

#### 索引 (Indexes) 的觀念
雖然 `CREATE INDEX` 是一個獨立的 DDL 語句，但 `PRIMARY KEY` 和 `UNIQUE` 約束在內部會自動為其所涉及的欄位建立索引。索引是一種特殊的查找表，可以加速資料庫查詢。當您將一個欄位定義為 `PRIMARY KEY` 或 `UNIQUE` 時，資料庫會自動為這些欄位建立索引，以確保快速的資料查找和唯一性檢查。

-----

### 常見錯誤與澄清

1.  **忘記指定資料型態**：
    ```sql
    -- 錯誤範例
    CREATE TABLE Products (
        ProductID PRIMARY KEY, -- 缺少資料型態
        ProductName VARCHAR(255)
    );
    ```
    **澄清**：每個欄位都必須有明確的資料型態，例如 `INT`、`VARCHAR(255)`。

2.  **關鍵字拼寫錯誤或語法不完整**：
    ```sql
    -- 錯誤範例
    CREAT TABLE Orders ( -- CREATE 拼寫錯誤
        OrderID INT PRIMAR KEY -- PRIMARY 拼寫錯誤
    );
    ```
    **澄清**：SQL 語法嚴謹，務必檢查關鍵字的拼寫和語句的完整性（如括號、逗號）。

3.  **重複的表名或欄位名**：
    資料庫中不允許存在兩個同名的資料表；在同一個資料表中也不允許存在兩個同名的欄位。
    ```sql
    -- 錯誤範例 (假設 Students 表已存在)
    CREATE TABLE Students (
        StudentID INT PRIMARY KEY
    );
    ```
    **澄清**：如果需要覆蓋現有表（通常不建議，除非是臨時表），可以考慮先 `DROP TABLE`，或者使用 `IF NOT EXISTS` (某些資料庫支援)。

4.  **外來鍵引用錯誤**：
    外來鍵必須引用目標表中的主鍵或具有 `UNIQUE` 約束的欄位，且資料型態必須匹配。
    ```sql
    -- 錯誤範例 (假設 Employees 表中沒有 EmpID 欄位)
    CREATE TABLE Projects (
        ProjectID INT PRIMARY KEY,
        ManagerID INT,
        FOREIGN KEY (ManagerID) REFERENCES Employees(EmpID) -- 如果 Employees 沒有 EmpID
    );
    ```
    **澄清**：確保引用的目標表和目標欄位確實存在，並且型態相容。

5.  **缺少逗號分隔欄位定義**：
    每個欄位定義後都需要用逗號分隔，除了最後一個欄位。
    ```sql
    -- 錯誤範例
    CREATE TABLE Items (
        ItemID INT PRIMARY KEY
        ItemName VARCHAR(100) -- 缺少逗號
    );
    ```
    **澄清**：仔細檢查每個欄位定義後的逗號。

-----

### 小練習（附詳解）

#### 小練習 1：建立書籍資料表
請建立一個名為 `Books` 的資料表，包含以下欄位和約束：
-   `BookID`：整數，主鍵。
-   `Title`：可變長度字串（最大 255 字元），不能為 `NULL`，且值必須是唯一的。
-   `Author`：可變長度字串（最大 100 字元），可以為 `NULL`。
-   `PublicationDate`：日期型態。
-   `Price`：精確的十進制數字，總共 5 位數字，其中小數點後 2 位，不能為 `NULL`，預設值為 0.00。

**解答步驟：**

1.  **定義表名**：`Books`。
2.  **定義 `BookID`**：`INT PRIMARY KEY`。
3.  **定義 `Title`**：`VARCHAR(255) NOT NULL UNIQUE`。
4.  **定義 `Author`**：`VARCHAR(100)`。
5.  **定義 `PublicationDate`**：`DATE`。
6.  **定義 `Price`**：`DECIMAL(5,2) NOT NULL DEFAULT 0.00`。

**SQL 敘述：**

```sql
CREATE TABLE Books (
    BookID INT PRIMARY KEY,
    Title VARCHAR(255) NOT NULL UNIQUE,
    Author VARCHAR(100),
    PublicationDate DATE,
    Price DECIMAL(5,2) NOT NULL DEFAULT 0.00
);
```

#### 小練習 2：建立訂單與客戶關聯資料表
假設您已經有一個 `Customers` 資料表，其結構如下：

```sql
CREATE TABLE Customers (
    CustomerID INT PRIMARY KEY AUTO_INCREMENT,
    CustomerName VARCHAR(200) NOT NULL,
    Email VARCHAR(255) UNIQUE
);
```

請建立一個名為 `Orders` 的資料表，包含以下欄位和約束：
-   `OrderID`：整數，主鍵，且自動遞增。
-   `CustomerID`：整數，不能為 `NULL`，作為外來鍵參考 `Customers` 表的 `CustomerID`。
-   `OrderDate`：日期型態，預設值為當前日期。
-   `TotalAmount`：精確的十進制數字，總共 8 位數字，其中小數點後 2 位，不能為 `NULL`，預設值為 0.00。

**解答步驟：**

1.  **定義表名**：`Orders`。
2.  **定義 `OrderID`**：`INT PRIMARY KEY AUTO_INCREMENT` (或適用於您的資料庫的自動遞增語法，如 `SERIAL` for PostgreSQL, `IDENTITY(1,1)` for SQL Server)。
3.  **定義 `CustomerID`**：`INT NOT NULL`。
4.  **定義 `OrderDate`**：`DATE DEFAULT CURRENT_DATE` (或適用於您的資料庫的當前日期函數，如 `GETDATE()` for SQL Server)。
5.  **定義 `TotalAmount`**：`DECIMAL(8,2) NOT NULL DEFAULT 0.00`。
6.  **定義外來鍵**：`FOREIGN KEY (CustomerID) REFERENCES Customers(CustomerID)`。

**SQL 敘述：**

```sql
CREATE TABLE Orders (
    OrderID INT PRIMARY KEY AUTO_INCREMENT, -- 或 SERIAL, IDENTITY(1,1)
    CustomerID INT NOT NULL,
    OrderDate DATE DEFAULT CURRENT_DATE,    -- 或 GETDATE()
    TotalAmount DECIMAL(8,2) NOT NULL DEFAULT 0.00,
    
    FOREIGN KEY (CustomerID) REFERENCES Customers(CustomerID)
);
```

-----

### 延伸閱讀/參考

-   **不同資料庫系統的資料型態差異**：雖然 SQL 標準定義了一些通用型態，但各資料庫系統（如 MySQL, PostgreSQL, SQL Server, Oracle）在資料型態的名稱、大小和特性上會有一些差異。建議查閱您所使用資料庫的官方文檔。
    -   [MySQL Data Types](https://dev.mysql.com/doc/refman/8.0/en/data-types.html)
    -   [PostgreSQL Data Types](https://www.postgresql.org/docs/current/datatype.html)
    -   [SQL Server Data Types](https://docs.microsoft.com/en-us/sql/t-sql/data-types/data-types-transact-sql)
-   **複合約束與級聯操作 (Cascading Actions)**：外來鍵除了定義參考關係外，還可以設定當父表資料被更新或刪除時，子表資料的行為（如 `ON DELETE CASCADE`, `ON UPDATE SET NULL` 等）。這對於維護資料庫的參考完整性非常重要。
-   **索引策略與最佳化**：深入理解索引的工作原理、類型（B-tree, Hash 等）以及如何設計高效的索引是提升資料庫性能的關鍵。
-   **正規化 (Normalization)**：資料庫設計的理論基礎，旨在消除資料冗餘，提高資料完整性。了解不同的正規形式 (1NF, 2NF, 3NF, BCNF) 有助於設計出更優良的資料表結構。