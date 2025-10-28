# 3-2 SSMS 操作：資料庫管理工具入門

本章將引導您熟悉 SQL Server Management Studio (SSMS) 的核心功能與操作。SSMS 是微軟為 SQL Server 設計的整合式管理環境，讓您能輕鬆地連接、查詢、管理與開發 SQL Server 的各項功能。

-----

### 核心概念：SSMS 是什麼？

#### 核心觀念：SQL Server Management Studio (SSMS) 的角色與用途

SQL Server Management Studio (SSMS) 是一個免費的、基於圖形使用者介面 (GUI) 的應用程式，用於管理所有 SQL 基礎架構。無論您的 SQL Server 是部署在內部部署、Azure 雲端還是其他環境，SSMS 都能提供一個統一的介面來完成各種資料庫管理任務。

其主要用途包括：

*   **連接到 SQL Server 實例**：無論是本機或遠端的 SQL Server。
*   **執行 SQL 查詢**：編寫、執行 T-SQL 語句，並檢視查詢結果。
*   **管理資料庫物件**：建立、修改、刪除資料庫、資料表、索引、檢視表、預存程序、函式等。
*   **監控效能**：檢查資料庫活動、鎖定、等待事件等。
*   **安全性管理**：設定使用者、角色、權限。
*   **備份與還原**：執行資料庫的備份和還原操作。
*   **排程作業**：建立和管理 SQL Server Agent 作業。

#### 與相鄰概念的關聯

*   **與 SQL Server 資料庫引擎的關係**：SSMS 就像是您的車輛方向盤和儀表板，而 SQL Server 資料庫引擎則是引擎本身。SSMS 讓您發出指令（例如執行 SQL 查詢），而引擎則負責處理這些指令並管理資料。沒有 SSMS，您也可以透過命令列工具或程式碼連接到 SQL Server，但 SSMS 提供更直觀、更有效率的圖形化操作。
*   **與 SQL 語法的關係**：SSMS 是執行 SQL 語法的平台。您在 SSMS 的查詢編輯器中撰寫 T-SQL（Transact-SQL）語句，然後透過 SSMS 將這些語句發送到 SQL Server 引擎執行。沒有 SQL 語法，SSMS 就無法有效地與資料庫溝通；沒有 SSMS，編寫和測試 SQL 語法將會相對困難。
*   **與其他 GUI 工具的差異**：市面上還有其他第三方工具（例如 DataGrip, DBeaver, Azure Data Studio 等）可以連接和管理 SQL Server。SSMS 是微軟官方提供的工具，對於 SQL Server 的功能支援最完整且即時。Azure Data Studio 則是另一個由微軟提供的輕量級、跨平台的工具，更適合開發者進行日常的 SQL 查詢和資料探索，但其管理功能不如 SSMS 完整。

-----

### 典型操作範例：連接、查詢與瀏覽

本節將帶您逐步完成 SSMS 中最常用的幾項操作。

#### 1. 連接到資料庫伺服器

這是您使用 SSMS 的第一步。

##### 核心觀念：伺服器類型、認證方式

*   **伺服器類型 (Server type)**：通常是 `Database Engine`。此外還有 Analysis Services, Reporting Services, Integration Services 等。
*   **伺服器名稱 (Server name)**：指定您要連接的 SQL Server 實例。常見的名稱包括：
    *   `localhost` 或 `.`：連接到本機預設實例。
    *   `localhost\SQLEXPRESS`：連接到本機的 SQLEXPRESS 命名實例。
    *   `192.168.1.100` 或 `YourServerName`：連接到遠端伺服器。
*   **認證 (Authentication)**：
    *   **Windows 驗證 (Windows Authentication)**：使用您登入 Windows 的帳戶進行驗證。這是最常用且推薦的方式，安全性較高。
    *   **SQL Server 驗證 (SQL Server Authentication)**：使用在 SQL Server 內部建立的登入帳戶（包含使用者名稱和密碼）進行驗證。當您無法使用 Windows 驗證或連接到遠端伺服器時常用。

##### 例子：詳細步驟

1.  **開啟 SSMS**：從您的開始菜單中啟動 SQL Server Management Studio。
2.  **連接到伺服器視窗**：SSMS 啟動後，通常會自動彈出「連接到伺服器 (Connect to Server)」對話框。如果沒有，可以點擊工具列上的「連接 (Connect)」按鈕，然後選擇「資料庫引擎 (Database Engine)」。
    ![SSMS 連接到伺服器](https://i.imgur.com/example_connect_server.png) <!-- Placeholder image link -->
3.  **輸入連接資訊**：
    *   **伺服器類型 (Server type)**：保持 `Database Engine`。
    *   **伺服器名稱 (Server name)**：輸入您的 SQL Server 實例名稱。例如，如果您安裝的是預設實例，可以輸入 `.` 或 `localhost`。如果安裝的是 SQLEXPRESS，可能需要輸入 `.\SQLEXPRESS` 或 `localhost\SQLEXPRESS`。
    *   **認證 (Authentication)**：選擇 `Windows Authentication`。如果選擇 `SQL Server Authentication`，您需要額外輸入 `Login` 和 `Password`。
    *   **連接 (Connect)**：點擊「連接」按鈕。

    成功連接後，SSMS 介面左側的「物件總管 (Object Explorer)」將會顯示您連接的伺服器實例。

#### 2. 使用物件總管 (Object Explorer)

物件總管是 SSMS 的核心導航工具，用於瀏覽和管理 SQL Server 實例中的所有物件。

##### 核心觀念：瀏覽資料庫物件

物件總管以樹狀結構顯示伺服器上的所有資料庫物件，讓您能直觀地探索資料庫的結構。您可以展開節點來查看更詳細的內容。

主要節點包括：

*   **資料庫 (Databases)**：包含伺服器上的所有使用者資料庫和系統資料庫。
*   **安全性 (Security)**：管理登入、伺服器角色、憑證等。
*   **伺服器物件 (Server Objects)**：管理連結伺服器、端點、觸發器等。
*   **管理 (Management)**：包含 SQL Server Agent、備份計畫、日誌等。

##### 例子：如何展開節點、尋找特定的資料表

1.  **展開「資料庫」節點**：在物件總管中，點擊您連接的伺服器名稱旁邊的 `+` 號來展開。然後找到「資料庫 (Databases)」節點，點擊其旁邊的 `+` 號展開。
2.  **選擇一個資料庫**：您會看到所有可用的資料庫，例如 `AdventureWorks2019` 或 `Northwind`。點擊其中一個您想探索的資料庫旁邊的 `+` 號展開。
3.  **探索資料表**：在選定的資料庫下，找到「資料表 (Tables)」節點並展開。您會看到所有屬於該資料庫的資料表，例如 `dbo.Customers` 或 `Sales.SalesOrderHeader`。
4.  **查看資料表內容**：
    *   右鍵點擊一個資料表（例如 `dbo.Customers`），然後選擇「選取前 1000 個資料列 (Select Top 1000 Rows)」。這將在新的查詢視窗中生成並執行一個 `SELECT TOP 1000` 語句，並在結果視窗中顯示前 1000 筆資料。
    *   右鍵點擊資料表，選擇「設計 (Design)」可以查看資料表的結構（欄位名稱、資料類型、主鍵等）。

#### 3. 開啟與執行 SQL 查詢視窗

這是您與資料庫進行互動的核心介面。

##### 核心觀念：編寫、執行 SQL 語句的核心介面

查詢視窗（或稱查詢編輯器）是您編寫 T-SQL 語句的地方。您可以執行單一語句、多個語句，或整個查詢批次。

##### 例子：撰寫一個簡單的 `SELECT` 語句並執行，檢視結果

1.  **開啟新查詢視窗**：在 SSMS 工具列上，點擊「新增查詢 (New Query)」按鈕。這會開啟一個空白的查詢編輯器視窗。
2.  **選擇目標資料庫**：在查詢編輯器上方的工具列中，有一個下拉式選單顯示當前連接的資料庫。請確保選擇了您要操作的資料庫，例如 `AdventureWorks2019`。
3.  **撰寫 SQL 語句**：在查詢編輯器中輸入以下 SQL 語句（請替換為您資料庫中實際存在的資料表名稱，例如 `Sales.Customer`）：

    ```sql
    USE AdventureWorks2019; -- 指定要使用的資料庫
    GO -- 批次分隔符，可省略，但養成習慣較好

    SELECT
        CustomerID,
        PersonID,
        AccountNumber
    FROM
        Sales.Customer
    WHERE
        TerritoryID = 6;
    ```
    *   `USE AdventureWorks2019;`：明確指出您的查詢將針對 `AdventureWorks2019` 資料庫執行。這是一個好習慣，避免在錯誤的資料庫中執行查詢。
    *   `SELECT ... FROM ... WHERE ...`：這是最基本的資料查詢語句。

4.  **執行查詢**：
    *   **執行所有語句**：點擊工具列上的「執行 (Execute)」按鈕（或按 `F5` 鍵）。這將執行查詢視窗中的所有 T-SQL 語句。
    *   **執行選定語句**：如果您只選擇了部分語句，然後點擊「執行」或按 `F5`，則只會執行選定的部分。

5.  **檢視結果**：查詢執行後，結果會顯示在查詢視窗下方的「結果 (Results)」窗格中。如果查詢有錯誤，錯誤訊息會顯示在「訊息 (Messages)」窗格中。

#### 4. 儲存查詢與查詢結果

管理您的工作成果是效率的關鍵。

##### 核心觀念：保存工作成果，匯出資料

*   **儲存查詢**：將您編寫的 T-SQL 腳本保存為 `.sql` 文件，以便將來重複使用或分享。
*   **匯出查詢結果**：將查詢返回的資料匯出為其他格式（如 CSV、Excel），用於進一步的分析或報告。

##### 例子：如何儲存 `.sql` 檔案，如何將結果匯出為 CSV

1.  **儲存查詢（.sql 檔案）**：
    *   在開啟的查詢視窗中，點擊工具列上的「儲存 (Save)」按鈕（磁碟圖示）或按 `Ctrl + S`。
    *   選擇一個目錄和檔案名稱（例如 `MyFirstQuery.sql`），然後點擊「儲存 (Save)」。
    *   下次您就可以直接開啟這個 `.sql` 檔案，而不需要重新輸入 SQL 語句。

2.  **匯出查詢結果（為 CSV）**：
    *   執行一個查詢，確保結果顯示在「結果 (Results)」窗格中。
    *   在「結果 (Results)」窗格中，右鍵點擊任何一個儲存格。
    *   選擇「將結果另存為 (Save Results As...)」。
    *   在彈出的對話框中，選擇一個目錄。
    *   在「存檔類型 (Save as type)」下拉選單中，選擇 `CSV (逗點分隔)`。
    *   輸入檔案名稱（例如 `CustomerData.csv`），然後點擊「儲存 (Save)」。
    *   您現在可以使用 Excel 或其他文本編輯器打開 `CustomerData.csv` 文件，查看匯出的資料。

-----

### 常見錯誤與澄清

在使用 SSMS 過程中，您可能會遇到一些常見問題。

#### 1. 連接失敗

*   **問題**: 「無法連接到 `伺服器名稱`。」
*   **可能原因與澄清**:
    *   **伺服器名稱錯誤**: 檢查您輸入的伺服器名稱是否正確（大小寫不敏感，但實例名稱要準確）。例如，`localhost` 和 `.\SQLEXPRESS`。
    *   **SQL Server 服務未運行**: SQL Server 資料庫引擎服務可能沒有啟動。您可以到 Windows 的「服務」管理器中檢查並啟動對應的 SQL Server (MSSQLSERVER) 或 SQL Server (SQLEXPRESS) 服務。
    *   **防火牆阻擋**: Windows 防火牆可能阻擋了 SSMS 連接 SQL Server 的埠 (預設為 `1433`)。您可能需要新增防火牆規則來允許此連接。
    *   **網路問題**: 如果是連接遠端伺服器，請檢查網路連線是否正常。
    *   **認證失敗**: 如果使用 `SQL Server Authentication`，請確認登入名稱和密碼是否正確。該登入帳戶可能被禁用或密碼已過期。

#### 2. 查詢錯誤

*   **問題**: 執行查詢時在「訊息」窗格中顯示錯誤。
*   **可能原因與澄清**:
    *   **語法錯誤**: 最常見的問題是 SQL 語句的拼寫、關鍵字使用或標點符號不正確。SSMS 的查詢編輯器會嘗試用紅色波浪線標記出潛在的語法錯誤。仔細閱讀錯誤訊息，它通常會指出錯誤所在的行號和大致原因。
    *   **選擇的資料庫不正確**: 如果您沒有使用 `USE 資料庫名稱;` 或在下拉選單中選擇正確的資料庫，您的查詢可能會在 `master` 或其他預設資料庫中執行，導致找不到指定的資料表或檢視表。
    *   **物件不存在**: 您查詢的資料表、欄位或檢視表可能拼寫錯誤，或者在選定的資料庫中根本不存在。檢查物件總管以確認物件名稱。
    *   **權限不足**: 您的登入帳戶可能沒有足夠的權限來執行特定的查詢或訪問特定的資料庫物件。

#### 3. 結果集太大導致的效能問題或當機

*   **問題**: 執行一個 `SELECT * FROM BigTable;` 語句，結果集太大，導致 SSMS 反應緩慢甚至當機。
*   **澄清**:
    *   **避免無限制的 `SELECT *`**: 在不知道資料表大小的情況下，盡量不要直接 `SELECT *`。
    *   **使用 `TOP` 或 `LIMIT` 限制結果數量**: 在開發或測試階段，使用 `SELECT TOP N ...`（SQL Server）來限制返回的資料列數，例如 `SELECT TOP 100 * FROM BigTable;`。
    *   **限制查詢欄位**：只選擇您需要的欄位，而不是所有欄位。
    *   **適當的過濾條件**：使用 `WHERE` 子句來篩選資料。

-----

### 小練習（附詳解）

#### 小練習一：連接並執行基本查詢

**情境**：您需要連接到本地 SQL Server 實例，並從 `AdventureWorks2019` 資料庫中的 `HumanResources.Employee` 資料表檢索前 5 筆員工的 `BusinessEntityID`, `JobTitle` 和 `HireDate`。

**步驟**：

1.  開啟 SQL Server Management Studio。
2.  在「連接到伺服器」對話框中，使用 `Windows 驗證` 連接到您的本機 SQL Server 實例（例如 `.` 或 `localhost`）。
3.  開啟一個新的查詢視窗。
4.  在查詢編輯器上方的下拉選單中，選擇 `AdventureWorks2019` 資料庫（如果您的 SQL Server 上沒有此資料庫，請嘗試安裝或使用其他現有的資料庫，並替換表格名稱）。
5.  撰寫 SQL 查詢語句，檢索 `HumanResources.Employee` 資料表的前 5 筆員工的 `BusinessEntityID`, `JobTitle` 和 `HireDate` 欄位。
6.  執行查詢並觀察結果。

**詳解**：

1.  開啟 SSMS。
2.  連接到伺服器。
3.  點擊「新增查詢」按鈕。
4.  確保下拉選單中選取了 `AdventureWorks2019`。
5.  輸入以下 SQL 語句：

    ```sql
    USE AdventureWorks2019;
    GO

    SELECT TOP 5
        BusinessEntityID,
        JobTitle,
        HireDate
    FROM
        HumanResources.Employee
    ORDER BY
        BusinessEntityID;
    ```

6.  點擊「執行」按鈕。您應該會在結果窗格中看到類似以下的輸出：

    | BusinessEntityID | JobTitle                 | HireDate            |
    | :--------------- | :----------------------- | :------------------ |
    | 1                | Chief Executive Officer  | 2007-08-01 00:00:00 |
    | 2                | Vice President of Engineering | 2008-01-31 00:00:00 |
    | 3                | Engineering Manager      | 2008-01-31 00:00:00 |
    | 4                | Research and Development Manager | 2008-01-31 00:00:00 |
    | 5                | Design Engineer          | 2008-01-31 00:00:00 |

#### 小練習二：瀏覽物件與儲存查詢

**情境**：您想查看 `AdventureWorks2019` 資料庫中 `Sales.SalesOrderHeader` 資料表的設計（欄位名稱及資料類型），並將您剛才執行的小練習一的查詢儲存起來。

**步驟**：

1.  使用物件總管導航到 `AdventureWorks2019` 資料庫。
2.  展開「資料表」節點，找到 `Sales.SalesOrderHeader` 資料表。
3.  右鍵點擊 `Sales.SalesOrderHeader`，選擇「設計」來查看其欄位設計。觀察其包含哪些欄位以及它們的資料類型。完成後關閉設計視窗。
4.  切換回您在小練習一中使用的查詢視窗。
5.  將該查詢儲存為 `EmployeeTop5Query.sql` 到您電腦上一個易於找到的位置（例如桌面或文件夾）。

**詳解**：

1.  在物件總管中，展開您的伺服器實例 -> 「資料庫」 -> `AdventureWorks2019` -> 「資料表」。
2.  找到 `Sales.SalesOrderHeader` 資料表。
3.  右鍵點擊 `Sales.SalesOrderHeader`，選擇「設計」。您會看到一個新的視窗，其中列出了如 `SalesOrderID`, `OrderDate`, `CustomerID` 等欄位，以及它們各自的資料類型（例如 `int`, `datetime`, `nvarchar(15)` 等）。
    ![SSMS Table Design](https://i.imgur.com/example_table_design.png) <!-- Placeholder image link -->
4.  確認無誤後，關閉 `Sales.SalesOrderHeader` 的設計視窗。
5.  切換到包含小練習一 SQL 語句的查詢視窗。
6.  點擊工具列上的「儲存」按鈕（或 `Ctrl + S`）。
7.  在「另存新檔」對話框中，選擇一個目錄，並將檔案名稱設定為 `EmployeeTop5Query.sql`，然後點擊「儲存」。
8.  您可以關閉 SSMS，然後再從您儲存的檔案位置雙擊 `EmployeeTop5Query.sql`，它應該會自動用 SSMS 打開該查詢。

-----

### 延伸閱讀/參考

*   **Microsoft Docs: SQL Server Management Studio (SSMS)**
    *   這是 SSMS 最權威的官方文件。您可以在這裡找到所有功能的詳細說明、最新更新和故障排除指南。
    *   [https://docs.microsoft.com/zh-tw/sql/ssms/sql-server-management-studio-ssms?view=sql-server-ver16](https://docs.microsoft.com/zh-tw/sql/ssms/sql-server-management-studio-ssms?view=sql-server-ver16)
*   **SQL Server 基本語法入門**
    *   學習 T-SQL 語法是使用 SSMS 的基礎。建議您在熟悉 SSMS 介面後，深入學習 SQL 的 `SELECT`, `INSERT`, `UPDATE`, `DELETE`, `JOIN` 等基本語句。
    *   可參考 W3Schools: [https://www.w3schools.com/sql/default.asp](https://www.w3schools.com/sql/default.asp) (英文，但內容非常基礎易懂)
*   **安裝 AdventureWorks 資料庫**
    *   許多 SQL Server 教學範例都會使用 AdventureWorks。如果您想跟隨這些範例，可以學習如何安裝它。
    *   [https://docs.microsoft.com/zh-tw/sql/samples/adventureworks-install-configure?view=sql-server-ver16](https://docs.microsoft.com/zh-tw/sql/samples/adventureworks-install-configure?view=sql-server-ver16)