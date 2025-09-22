# Chapter 4 建立資料表

在資料庫的世界中，資料表（Table）是儲存資料的基本單位。理解如何設計並建立資料表，是任何資料庫操作的基石。本章將深入探討 `CREATE TABLE` 語法，包含資料型態的選擇、各種欄位約束的應用，以及如何確保資料的完整性與正確性。

-----

### 4.1 核心概念：資料表與 CREATE TABLE 語法

#### 4.1.1 資料表 (Table) 定義

資料表是關聯式資料庫中用來組織和儲存資料的基本結構。想像它像一個電子試算表，由行（Row，也稱為記錄或Tuple）和列（Column，也稱為欄位或Attribute）組成：
*   **欄位 (Column / Field)：** 定義資料表的結構，每個欄位有其名稱和資料型態，代表了某一類型的資訊。例如，在一個「學生」資料表中，可能會有「學號」、「姓名」、「生日」等欄位。
*   **記錄 (Row / Record)：** 每一行代表一個獨立的實體或一組相關的資料。例如，學生資料表中的每一行都代表一個具體的學生及其所有相關資訊。

資料表的結構稱為「結構描述 (Schema)」，它定義了資料表包含哪些欄位、每個欄位的資料型態、以及施加在這些欄位上的約束條件。

#### 4.1.2 CREATE TABLE 語法核心結構

`CREATE TABLE` 語法用於在資料庫中建立一個新的資料表。其基本結構如下：

```sql
CREATE TABLE table_name (
    column1 datatype [constraint],
    column2 datatype [constraint],
    column3 datatype [constraint],
    ...
    [table_constraint]
);
```

*   `CREATE TABLE`: 這是建立資料表的關鍵字。
*   `table_name`: 您要建立的資料表的名稱。命名時應具有描述性，並通常遵循某些命名規範（例如，使用小寫字母和底線）。
*   `columnN`: 資料表中的欄位名稱。每個欄位都必須有一個唯一的名稱。
*   `datatype`: 定義欄位將儲存何種型態的資料，例如數字、文字、日期等。這是資料完整性的重要環節。
*   `constraint`: 對欄位或資料表施加的規則，用來限制資料的有效性，確保資料的準確性和一致性。例如，`PRIMARY KEY`, `NOT NULL`, `UNIQUE` 等。

**範例：建立一個簡單的學生資料表**

```sql
CREATE TABLE students (
    student_id INT,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    email VARCHAR(100),
    enrollment_date DATE
);
```
這個語法建立了一個名為 `students` 的資料表，其中包含五個欄位，每個欄位都指定了其資料型態。目前，這個資料表還沒有任何約束條件。

-----

### 4.2 欄位資料型態 (Data Types)

#### 4.2.1 資料型態定義與重要性

資料型態定義了欄位中可以儲存的資料種類。選擇正確的資料型態至關重要，原因如下：
*   **資料完整性：** 確保欄位只儲存符合預期的資料。
*   **儲存效率：** 不同的資料型態佔用不同的儲存空間。選擇最小但足夠的型態可以節省磁碟空間。
*   **查詢效能：** 資料庫系統會根據資料型態優化查詢操作。
*   **避免錯誤：** 避免因為型態不符而導致的資料截斷、溢位或轉換錯誤。

#### 4.2.2 常見資料型態

不同的資料庫系統（例如 MySQL, PostgreSQL, SQL Server, Oracle）在資料型態的名稱和具體實作上可能略有差異，但核心概念是相通的。以下是一些最常見的資料型態分類：

1.  **數值型 (Numeric Types)**
    *   **整數型：**
        *   `INT` (或 `INTEGER`): 標準整數，通常佔用 4 位元組。
        *   `SMALLINT`: 小範圍整數，通常佔用 2 位元組。
        *   `BIGINT`: 大範圍整數，通常佔用 8 位元組。
        *   `TINYINT`: 極小範圍整數（如 0-255），通常佔用 1 位元組。
    *   **浮點數型（近似數值）：**
        *   `FLOAT` (或 `REAL`): 單精度浮點數。
        *   `DOUBLE` (或 `DOUBLE PRECISION`): 雙精度浮點數。
        *   適用於科學計算，但由於精度問題，不建議用於貨幣計算。
    *   **精確數值型：**
        *   `DECIMAL(p, s)` 或 `NUMERIC(p, s)`: 精確數值。`p` 是總位數（精度），`s` 是小數點後的位數（刻度）。
        *   例如，`DECIMAL(10, 2)` 可以儲存最大為 99,999,999.99 的數字，適合用於貨幣和精確計算。

2.  **字串型 (String Types)**
    *   `VARCHAR(n)`: 可變長度字串。`n` 定義最大長度。只儲存實際使用的空間加上少量開銷，是處理文字資料最常用的型態。
    *   `CHAR(n)`: 固定長度字串。即使實際字串較短，也會佔用 `n` 個字元空間，並用空格填充。適用於長度固定的資料，如國家代碼。
    *   `TEXT`: 用於儲存大量文字資料，長度通常沒有明確上限（或上限非常大）。在某些資料庫中，可能有不同的 TEXT 變體，如 `TINYTEXT`, `MEDIUMTEXT`, `LONGTEXT`。

3.  **日期/時間型 (Date/Time Types)**
    *   `DATE`: 儲存日期，不包含時間資訊（例如：'YYYY-MM-DD'）。
    *   `TIME`: 儲存時間，不包含日期資訊（例如：'HH:MM:SS'）。
    *   `DATETIME`: 儲存日期和時間（例如：'YYYY-MM-DD HH:MM:SS'）。
    *   `TIMESTAMP`: 儲存日期和時間，通常與時區相關，或在某些系統中自動更新（如記錄建立/修改時間）。

4.  **布林型 (Boolean Types)**
    *   `BOOLEAN`: 儲存真/假值（TRUE/FALSE）。在某些資料庫中可能用 `TINYINT(1)` 或 `BIT` 0/1 來表示。

5.  **其他特殊型**
    *   `BLOB` (Binary Large Object): 儲存二進位大物件，如圖片、音訊、文件等。
    *   `CLOB` (Character Large Object): 儲存字元大物件，通常用於非常大的文字資料。

#### 4.2.3 選擇資料型態的考量

*   **資料範圍與精度：** 例如，薪水應該用 `DECIMAL` 而非 `FLOAT`；人數應用 `INT` 而非 `VARCHAR`。
*   **儲存空間：** `CHAR` 和 `VARCHAR` 的選擇，`INT` 和 `BIGINT` 的選擇。在不影響功能的情況下，盡量選擇佔用空間較小的型態。
*   **查詢與計算：** 日期型態適合日期計算，數值型適合數值運算。

**範例：為不同資料選擇型態**

| 資料描述       | 建議資料型態      | 備註                                       |
| :------------- | :---------------- | :----------------------------------------- |
| 商品價格       | `DECIMAL(10, 2)`  | 確保精確度，避免浮點數誤差。               |
| 使用者名稱     | `VARCHAR(255)`    | 大多數使用者名稱長度不固定，`255` 是一個常見上限。 |
| 使用者出生日期 | `DATE`            | 只需日期，無需時間。                       |
| 訂單總金額     | `DECIMAL(12, 2)`  | 可能金額較大，精度同價格。                 |
| 商品描述       | `TEXT`            | 可能很長，不設固定長度。                   |
| 庫存數量       | `INT`             | 整數，一般不會太大。                       |
| 是否啟用       | `BOOLEAN`         | 真/假狀態。                                |

-----

### 4.3 欄位約束 (Column Constraints)

#### 4.3.1 約束定義與重要性

約束是施加在資料表欄位上的一組規則，它們用於強制資料完整性，確保資料的準確性、有效性和可靠性。約束是資料庫設計中不可或缺的一部分，因為它們可以：
*   **防止無效資料：** 阻止不符合業務邏輯的資料被寫入資料庫。
*   **維護資料一致性：** 確保不同資料表之間的關聯是有效的。
*   **減少應用程式層的錯誤處理：** 許多資料驗證工作可以交由資料庫層處理。

約束可以定義在欄位層級 (Column-level) 或資料表層級 (Table-level)。

#### 4.3.2 常見約束類型

1.  **`NOT NULL` (非空約束)**
    *   定義：確保欄位不能儲存 `NULL` 值。
    *   作用：對於必填資訊（如用戶名、商品名稱），防止其留空。
    *   範例：
        ```sql
        CREATE TABLE products (
            product_id INT PRIMARY KEY,
            product_name VARCHAR(100) NOT NULL, -- 產品名稱不能為空
            price DECIMAL(10, 2)
        );
        ```

2.  **`UNIQUE` (唯一約束)**
    *   定義：確保欄位（或一組欄位）的所有值都是唯一的。
    *   作用：防止重複資料，例如電子郵件地址、身份證號碼等。允許 `NULL` 值，且多個 `NULL` 值被視為不同的值。
    *   範例：
        ```sql
        CREATE TABLE users (
            user_id INT PRIMARY KEY,
            username VARCHAR(50) NOT NULL UNIQUE, -- 用戶名必須唯一且非空
            email VARCHAR(100) UNIQUE             -- 電子郵件必須唯一，但可為空
        );
        ```

3.  **`PRIMARY KEY` (主鍵)**
    *   定義：唯一識別資料表中每一條記錄的欄位（或一組欄位）。主鍵是 `NOT NULL` 和 `UNIQUE` 的組合。
    *   作用：
        *   提供資料表的唯一性標識。
        *   優化查詢，因為主鍵通常會自動建立索引。
        *   作為其他資料表建立外鍵的目標。
    *   一個資料表只能有一個主鍵。
    *   範例（欄位層級定義）：
        ```sql
        CREATE TABLE categories (
            category_id INT PRIMARY KEY, -- category_id 是主鍵
            category_name VARCHAR(50) NOT NULL
        );
        ```
    *   範例（資料表層級定義 - 適用於複合主鍵或更清晰的定義）：
        ```sql
        CREATE TABLE order_items (
            order_id INT,
            item_id INT,
            quantity INT,
            PRIMARY KEY (order_id, item_id) -- order_id 和 item_id 共同構成主鍵
        );
        ```

4.  **`FOREIGN KEY` (外鍵)**
    *   定義：建立兩個資料表之間的連結。外鍵是一個或一組欄位，它們的值必須匹配另一個資料表（被參照表）的主鍵或唯一鍵的值。
    *   作用：維護參照完整性，確保資料表之間的關係有效。
    *   語法：`FOREIGN KEY (column_name) REFERENCES referenced_table(referenced_column_name)`
    *   **級聯操作 (`ON DELETE`, `ON UPDATE`)**：
        *   `ON DELETE CASCADE`: 當父表記錄被刪除時，子表相關記錄也跟著被刪除。
        *   `ON DELETE SET NULL`: 當父表記錄被刪除時，子表相關記錄的外鍵欄位設定為 `NULL`（前提是該外鍵欄位允許 `NULL`）。
        *   `ON DELETE RESTRICT` (或 `NO ACTION`): 預設行為。如果子表有相關記錄，則不允許刪除父表記錄。
        *   `ON UPDATE CASCADE`, `ON UPDATE SET NULL`, `ON UPDATE RESTRICT` 類似。
    *   範例：
        ```sql
        CREATE TABLE products (
            product_id INT PRIMARY KEY,
            product_name VARCHAR(100) NOT NULL,
            category_id INT,
            FOREIGN KEY (category_id) REFERENCES categories(category_id)
                ON DELETE SET NULL -- 當所屬分類被刪除時，產品的 category_id 設為 NULL
                ON UPDATE CASCADE   -- 當分類 ID 更改時，產品的 category_id 也跟著更改
        );
        ```

5.  **`DEFAULT` (預設值)**
    *   定義：為欄位設定一個預設值。當插入新記錄時，如果該欄位沒有明確指定值，則會自動使用預設值。
    *   作用：簡化資料輸入，確保欄位總是有一個合理的值。
    *   範例：
        ```sql
        CREATE TABLE tasks (
            task_id INT PRIMARY KEY,
            task_name VARCHAR(255) NOT NULL,
            status VARCHAR(20) DEFAULT 'Pending', -- 預設狀態為 'Pending'
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP -- 預設為當前時間
        );
        ```
        `CURRENT_TIMESTAMP` 是許多資料庫系統中獲取當前日期時間的函數。

6.  **`CHECK` (檢查約束)**
    *   定義：指定一個布林表達式，確保欄位中的值滿足特定條件。
    *   作用：實施更複雜的業務規則。
    *   範例：
        ```sql
        CREATE TABLE employees (
            employee_id INT PRIMARY KEY,
            full_name VARCHAR(100) NOT NULL,
            age INT CHECK (age >= 18), -- 年齡必須大於或等於 18
            salary DECIMAL(10, 2) CHECK (salary > 0) -- 薪水必須大於 0
        );
        ```
    *   `CHECK` 約束也可以在資料表層級定義，用於多個欄位之間的關係檢查：
        ```sql
        CREATE TABLE orders (
            order_id INT PRIMARY KEY,
            order_date DATE,
            shipped_date DATE,
            CHECK (shipped_date IS NULL OR shipped_date >= order_date) -- 發貨日期必須晚於或等於訂單日期
        );
        ```

-----

### 4.4 與相鄰概念的關聯

#### 4.4.1 與資料庫正規化 (Normalization) 的關聯

資料庫正規化是一套設計資料表結構的準則，旨在減少資料冗餘、提高資料完整性並避免更新異常。`CREATE TABLE` 語法是將正規化設計付諸實踐的工具。
*   **設計指導：** 正規化理論（如第一範式、第二範式、第三範式等）指導我們如何將實體拆分成多個邏輯上獨立的資料表，以及如何定義欄位。
*   **主鍵與外鍵的應用：** 正規化要求每個資料表都有主鍵以唯一識別記錄。當我們將一個大表分解成多個小表時，主鍵和外鍵被用來建立這些新表之間的關係，以確保資料的一致性和可關聯性。例如，將客戶資料和訂單資料分開，再用 `customer_id` 作為外鍵連接。

#### 4.4.2 與 ER 模型 (Entity-Relationship Model) 的關聯

ER 模型是一種概念性設計工具，用於視覺化資料庫中的實體、屬性及其之間的關係。
*   **實體到資料表：** ER 模型中的每個實體（例如「學生」、「課程」）通常會轉換為一個資料庫中的資料表。
*   **屬性到欄位：** 實體的屬性（例如學生的「學號」、「姓名」）會轉換為資料表中的欄位。
*   **關係到外鍵：** 實體之間的關係（例如「學生選修課程」）會通過在相關資料表中添加外鍵來實現。例如，在選課表中添加 `student_id` 和 `course_id` 作為外鍵。

#### 4.4.3 與 ALTER TABLE 語法 (修改資料表) 的關聯

`CREATE TABLE` 用於資料表的首次建立，定義其初始結構。然而，資料庫設計很少一蹴而就，且業務需求會不斷變化。
*   **結構調整：** `ALTER TABLE` 語法用於在資料表建立後修改其結構，例如添加、刪除或修改欄位，添加、刪除約束等。
*   **互補關係：** `CREATE TABLE` 是奠基，`ALTER TABLE` 是修繕與擴展。兩者共同構成了資料表生命週期管理的重要部分。例如，在最初 `CREATE TABLE` 時可能未考慮到所有約束，之後可以使用 `ALTER TABLE ADD CONSTRAINT` 來完善。

-----

### 4.5 常見錯誤與澄清

1.  **未正確選擇資料型態**
    *   **錯誤範例：** 用 `VARCHAR` 儲存數字（如價格、數量），或者用 `FLOAT` 儲存貨幣金額。
    *   **澄清：**
        *   數字應使用 `INT` 或 `DECIMAL`。`DECIMAL` 適用於需要精確度的數值（如貨幣、百分比），`FLOAT`/`DOUBLE` 僅適用於可以接受近似值的科學計算。
        *   選擇最合適且最小的資料型態，以節省儲存空間並提升效能。例如，如果數值範圍在 -128 到 127，`TINYINT` 比 `INT` 更優。

2.  **主鍵/外鍵定義錯誤或遺漏**
    *   **錯誤範例：** 學生資料表沒有主鍵；訂單明細表中的 `product_id` 沒有設定為外鍵。
    *   **澄清：**
        *   每個資料表都應有主鍵以唯一識別記錄，這是關係型資料庫的基礎。
        *   外鍵對於維護參照完整性至關重要，它確保了相關資料表之間的連結有效。遺漏外鍵會導致「孤兒」資料（即子表記錄參照到不存在的父表記錄）。

3.  **資料表與欄位命名不規範**
    *   **錯誤範例：** 使用像 `tblUsers` (hungarian notation), `USER_DETAILS`, `fldName` (應用程式前綴) 等命名。
    *   **澄清：**
        *   建議使用小寫字母和底線 `_` 分隔單詞（例如 `user_id`, `product_name`）。這在大多數資料庫系統中是慣例，且不易引起大小寫敏感問題。
        *   資料表名稱通常是複數名詞（`users`, `products`），欄位名稱是單數名詞（`user_id`, `name`）。
        *   保持一致性。一套清晰的命名規則可以極大地提高資料庫的可讀性和維護性。

4.  **過度或不足使用約束**
    *   **錯誤範例：** 對每個欄位都設置 `CHECK` 約束，即使資料驗證可以在應用程式層處理；或者反之，完全沒有使用約束。
    *   **澄清：**
        *   約束應該用於強制核心的業務邏輯和資料完整性，特別是那些跨應用程式或確保基礎一致性的規則。
        *   過多的 `CHECK` 約束可能會增加插入/更新操作的開銷。對於一些複雜或業務變動頻繁的驗證，放在應用程式層處理可能更靈活。
        *   但 `NOT NULL`, `UNIQUE`, `PRIMARY KEY`, `FOREIGN KEY` 這些基本約束通常都是必須的。

-----

### 4.6 小練習（附詳解）

#### 小練習 1：建立員工資料表

**需求：** 請建立一個名為 `employees` 的資料表，包含以下欄位：
1.  **員工 ID (employee_id)：** 唯一識別員工，自動增長，為主鍵。
2.  **名 (first_name)：** 員工的名字，不可為空，最大長度 50。
3.  **姓 (last_name)：** 員工的姓氏，不可為空，最大長度 50。
4.  **電子郵件 (email)：** 員工的電子郵件，必須是唯一的，最大長度 100。
5.  **職稱 (job_title)：** 員工的職稱，最大長度 50。
6.  **薪水 (salary)：** 員工的薪水，必須是正數，小數點後兩位，最大總位數 10。
7.  **入職日期 (hire_date)：** 員工的入職日期，不可為空，預設為當前日期。

**步驟與詳解：**

1.  **選擇合適的資料型態和約束：**
    *   `employee_id`: `INT` 或 `BIGINT`，通常搭配 `AUTO_INCREMENT` (MySQL) 或 `SERIAL` (PostgreSQL) 實現自動增長，並設為 `PRIMARY KEY`。
    *   `first_name`, `last_name`: `VARCHAR(50) NOT NULL`。
    *   `email`: `VARCHAR(100) UNIQUE`。
    *   `job_title`: `VARCHAR(50)`。
    *   `salary`: `DECIMAL(10, 2) CHECK (salary > 0)`。
    *   `hire_date`: `DATE NOT NULL DEFAULT CURRENT_DATE` (或 `CURRENT_TIMESTAMP` 若要包含時間)。

2.  **撰寫 `CREATE TABLE` 語法：**

    ```sql
    CREATE TABLE employees (
        employee_id INT AUTO_INCREMENT PRIMARY KEY, -- MySQL / MariaDB 語法
        -- employee_id SERIAL PRIMARY KEY,           -- PostgreSQL 語法
        first_name VARCHAR(50) NOT NULL,
        last_name VARCHAR(50) NOT NULL,
        email VARCHAR(100) UNIQUE,
        job_title VARCHAR(50),
        salary DECIMAL(10, 2) CHECK (salary > 0),
        hire_date DATE NOT NULL DEFAULT CURRENT_DATE
    );
    ```
    *   **注意：** `AUTO_INCREMENT` 語法為 MySQL/MariaDB 特有。在 PostgreSQL 中，會使用 `SERIAL` 或 `BIGSERIAL` 偽型態來自動創建序列並將欄位設為整數。

#### 小練習 2：建立部門與員工的關係

**需求：**
1.  建立一個名為 `departments` 的資料表，包含：
    *   **部門 ID (department_id)：** 唯一識別部門，自動增長，為主鍵。
    *   **部門名稱 (department_name)：** 部門名稱，不可為空，必須是唯一的，最大長度 100。
2.  修改 `employees` 資料表，為其添加一個 `department_id` 欄位，並將其設定為外鍵，參照 `departments` 資料表的 `department_id`。
3.  設定外鍵的級聯操作：當部門被刪除時，該部門下的員工的 `department_id` 應設為 `NULL` (假設員工可以暫時沒有部門)。當部門的 `department_id` 更新時，員工表的 `department_id` 也應自動更新。

**步驟與詳解：**

1.  **建立 `departments` 資料表：**

    ```sql
    CREATE TABLE departments (
        department_id INT AUTO_INCREMENT PRIMARY KEY, -- MySQL / MariaDB 語法
        -- department_id SERIAL PRIMARY KEY,           -- PostgreSQL 語法
        department_name VARCHAR(100) NOT NULL UNIQUE
    );
    ```

2.  **修改 `employees` 資料表添加 `department_id` 欄位：**
    *   這個步驟需要用到 `ALTER TABLE` 語法，因為 `employees` 資料表已經存在。
    *   `department_id` 欄位應該允許為 `NULL`，以配合 `ON DELETE SET NULL` 的級聯操作。

    ```sql
    ALTER TABLE employees
    ADD COLUMN department_id INT;
    ```

3.  **為 `employees` 資料表添加外鍵約束：**
    *   定義外鍵，並設定 `ON DELETE SET NULL` 和 `ON UPDATE CASCADE`。

    ```sql
    ALTER TABLE employees
    ADD CONSTRAINT fk_department
    FOREIGN KEY (department_id) REFERENCES departments(department_id)
    ON DELETE SET NULL
    ON UPDATE CASCADE;
    ```
    *   `fk_department` 是這個外鍵約束的名稱，方便日後管理或刪除。

-----

### 4.7 延伸閱讀/參考

*   **資料庫正規化 (Database Normalization)：** 深入理解資料表設計背後的理論，有助於建立更健壯、高效的資料庫結構。
    *   維基百科：[資料庫正規化](https://zh.wikipedia.org/zh-tw/%E6%95%B0%E6%8D%AE%E5%BA%93%E8%8C%83%E5%BC%8F%E5%8C%96)
*   **SQL `ALTER TABLE` 語法：** 學習如何在資料表建立後修改其結構、添加或刪除欄位、約束等。
    *   W3Schools: [SQL ALTER TABLE Statement](https://www.w3schools.com/sql/sql_alter.asp) (英文)
*   **特定資料庫系統的資料型態與約束：** 不同的資料庫管理系統（如 MySQL, PostgreSQL, SQL Server, Oracle）在資料型態的命名、範圍和某些特定約束的實作上可能存在細微差異。查閱您所使用資料庫的官方文件是最佳實踐。
    *   MySQL Data Types: [https://dev.mysql.com/doc/refman/8.0/en/data-types.html](https://dev.mysql.com/doc/refman/8.0/en/data-types.html)
    *   PostgreSQL Data Types: [https://www.postgresql.org/docs/current/datatype.html](https://www.postgresql.org/docs/current/datatype.html)
    *   SQL Server Data Types: [https://docs.microsoft.com/en-us/sql/t-sql/data-types/data-types-transact-sql](https://docs.microsoft.com/en-us/sql/t-sql/data-types/data-types-transact-sql)