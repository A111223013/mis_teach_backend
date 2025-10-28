# Chapter 8 數據集工程

#### 8.1 數據集工程概論

數據集工程 (Dataset Engineering) 是一個關鍵的領域，旨在準備和管理用於機器學習模型、分析或應用程式的數據集。它涵蓋了從數據收集、清理、轉換、驗證到版本控制和維護的整個數據生命週期中的一系列活動。

### 核心觀念：什麼是數據集工程？

數據集工程不僅僅是簡單的數據預處理。它是一個更為廣泛、更具策略性的過程，其核心目標是確保數據集的高品質、可用性、一致性和可擴展性，以便數據能夠可靠地支援數據科學專案的成功。

**數據集工程的主要任務包括：**

1.  **數據收集 (Data Collection)：** 從各種內部和外部來源獲取原始數據。
2.  **數據清理 (Data Cleaning)：** 處理數據中的錯誤、不一致性、缺失值和異常值。
3.  **數據轉換 (Data Transformation)：** 將數據轉換為適合模型訓練的格式和尺度。
4.  **特徵工程 (Feature Engineering)：** 從現有數據中創造出新的、更有意義的特徵。
5.  **數據驗證 (Data Validation)：** 確保數據符合預期的格式、類型和業務規則。
6.  **數據管理與版本控制 (Data Management & Versioning)：** 有效地儲存、組織和追蹤數據集的變化。
7.  **數據隱私與安全 (Data Privacy & Security)：** 確保數據處理符合隱私法規和安全標準。

### 重要性：為何數據集工程至關重要？

數據集工程在現代數據科學和機器學習專案中扮演著不可或缺的角色，其重要性體現在以下幾個方面：

*   **模型性能的基石：** 「垃圾進，垃圾出」(Garbage In, Garbage Out) 的原則在機器學習領域尤為適用。一個乾淨、準備充分的數據集是訓練高性能模型的基礎。數據品質問題（如錯誤、缺失值或偏差）會直接導致模型學習到錯誤的模式，進而影響模型的準確性和泛化能力。
*   **縮短開發週期：** 高品質的數據集能夠減少模型開發者在調試模型或排查數據問題上的時間，加速模型從原型到部署的過程。
*   **提升決策品質：** 基於高品質數據的分析和模型能夠提供更準確、可靠的洞察，從而支援更好的業務決策。
*   **可重複性與可維護性：** 良好的數據集工程實踐，如數據版本控制和自動化清理流程，確保了實驗的可重複性，並使數據管道更易於維護和更新。
*   **應對數據複雜性：** 隨著數據量、種類和來源的增加，數據集工程提供了一套系統性的方法來處理數據的複雜性。

### 數據生命週期中的位置

數據集工程通常位於機器學習工作流程的早期階段，緊隨在數據規劃和探索性數據分析 (EDA) 之後，並在模型訓練、評估和部署之前。它為後續的模型開發和部署提供了堅實的數據基礎。

![ML Workflow](https://raw.githubusercontent.com/dair-ai/ml-visuals/master/workflow.png)
*(圖片來源：Dair.ai ML Visuals，示意圖)*

-----

#### 8.2 數據收集與來源

數據是所有數據科學和機器學習專案的起點。數據收集是獲取原始數據的過程，為數據集工程的後續步驟奠定基礎。

### 核心觀念：數據來源、採集策略

數據來源的選擇和數據採集策略的制定，對數據集的品質、可用性和專案的成功有著深遠的影響。

*   **數據來源 (Data Sources)：** 數據可以來自多種渠道，包括：
    *   **內部資料庫：** 企業內部的營運數據、客戶關係管理 (CRM) 系統、銷售數據、日誌文件等。
    *   **外部開放數據：** 政府開放數據平台、學術數據庫、公開的數據集儲存庫（如 Kaggle、UCI Machine Learning Repository）。
    *   **API (Application Programming Interface)：** 透過調用第三方服務的 API 獲取數據，如社群媒體數據、天氣數據、地圖數據等。
    *   **網路爬蟲 (Web Scraping)：** 從網頁上自動提取信息，需要注意合法性、服務條款和反爬機制。
    *   **感測器數據：** IoT 設備、環境監測器、智慧穿戴設備等實時或近實時生成的數據。
    *   **用戶生成內容 (UGC)：** 評論、論壇貼文、社交媒體互動等。

*   **採集策略 (Acquisition Strategies)：**
    *   **批量採集 (Batch Acquisition)：** 定期（例如每日、每週）從來源獲取大量數據。適用於數據變化不頻繁或對實時性要求不高的場景。
    *   **實時採集 (Real-time Acquisition)：** 數據生成後立即獲取和處理。適用於需要即時響應的應用，如股票交易、異常檢測。
    *   **增量採集 (Incremental Acquisition)：** 僅獲取自上次採集以來新增或更改的數據。效率高，減少了重複數據傳輸。
    *   **流式採集 (Streaming Acquisition)：** 持續不斷地從數據流中獲取數據。常與實時採集結合，例如使用 Kafka、Spark Streaming 等技術。

### 典型例子：API 爬取、資料庫匯出、感測器數據

1.  **API 爬取範例：**
    *   **情境：** 需要獲取某個城市的歷史天氣數據。
    *   **方法：** 使用公開的天氣 API (例如 OpenWeatherMap API)。
    *   **Python 程式碼片段：**
        ```python
        import requests
        import pandas as pd

        API_KEY = "YOUR_API_KEY" # 替換為你的 API 密鑰
        CITY_NAME = "Taipei"
        BASE_URL = "http://api.openweathermap.org/data/2.5/weather"

        params = {
            "q": CITY_NAME,
            "appid": API_KEY,
            "units": "metric" # 獲取攝氏溫度
        }

        response = requests.get(BASE_URL, params=params)

        if response.status_code == 200:
            data = response.json()
            # 提取主要天氣資訊
            weather_data = {
                "city": data["name"],
                "temperature": data["main"]["temp"],
                "humidity": data["main"]["humidity"],
                "description": data["weather"][0]["description"],
                "timestamp": pd.to_datetime(data["dt"], unit='s')
            }
            df = pd.DataFrame([weather_data])
            print("天氣數據獲取成功：")
            print(df)
        else:
            print(f"錯誤：無法獲取天氣數據，狀態碼 {response.status_code}")
        ```

2.  **資料庫匯出範例：**
    *   **情境：** 從企業的 SQL 資料庫中獲取客戶訂單數據。
    *   **方法：** 透過 SQL 查詢或 ETL 工具將數據匯出為 CSV、Parquet 等格式。
    *   **SQL 程式碼片段：**
        ```sql
        -- 從訂單表和客戶表聯接獲取特定時間範圍內的訂單數據
        SELECT
            o.order_id,
            o.order_date,
            o.total_amount,
            c.customer_id,
            c.customer_name,
            c.city
        FROM
            Orders o
        JOIN
            Customers c ON o.customer_id = c.customer_id
        WHERE
            o.order_date >= '2023-01-01' AND o.order_date < '2024-01-01';
        ```

3.  **感測器數據範例：**
    *   **情境：** 智慧工廠中的機器溫度感測器，每秒鐘傳送一次數據。
    *   **方法：** 使用消息佇列 (如 Kafka) 收集流式數據，並儲存到時間序列資料庫 (如 InfluxDB) 或數據湖。
    *   **概念流程：**
        感測器 -> MQTT/AMQP (消息協議) -> Kafka (消息佇列) -> Spark Streaming (實時處理) -> HDFS/InfluxDB (儲存)

### 與相鄰概念的關聯：數據隱私、倫理考量

數據收集過程與**數據隱私 (Data Privacy)** 和**倫理考量 (Ethical Considerations)** 密切相關。

*   **數據隱私：** 收集個人身份信息 (PII) 時，必須遵守相關的法律法規，如歐盟的 GDPR (通用數據保護條例) 或台灣的個人資料保護法。這可能涉及數據匿名化、假名化、最小化收集以及獲得用戶的明確同意。
*   **倫理考量：** 數據收集不能用於歧視、監控或任何不道德的目的。例如，不應收集受保護群體的敏感屬性用於風險評估，以免加劇偏見。網路爬蟲應尊重網站的 `robots.txt` 文件，避免過度請求導致服務中斷，並尊重內容的版權。

在數據收集階段就考慮這些因素，可以避免在專案後期遇到法律風險或聲譽問題。

-----

#### 8.3 數據清理：提升數據品質的基石

數據清理 (Data Cleaning)，又稱數據清洗或數據清洗，是數據集工程中最關鍵的步驟之一。其目標是檢測並糾正（或移除）數據集中的錯誤、不一致性、缺失值和異常值，從而提高數據的整體品質和可靠性。

### 核心觀念：數據品質問題類型

數據品質問題通常可分為以下幾類：

1.  **缺失值 (Missing Values)：** 數據集中某些觀測值的特定屬性沒有記錄。
2.  **異常值 (Outliers)：** 數據集中與大多數數據顯著不同的觀測值。
3.  **重複值 (Duplicate Values)：** 數據集中存在完全相同或高度相似的記錄。
4.  **不一致性 (Inconsistencies)：** 數據格式、命名或內容不一致，或違反業務規則。

這些問題可能由數據輸入錯誤、數據傳輸失敗、系統故障、測量誤差或數據採集過程中的人為疏忽引起。

### 8.3.1 缺失值處理

缺失值是數據集中最常見的問題之一。處理缺失值的方法有很多種，選擇哪種方法取決於缺失值的模式、數量以及數據的特性。

#### 方法：刪除、插補（均值、中位數、眾數、預測模型）

1.  **刪除 (Deletion)：**
    *   **列表式刪除 (Listwise Deletion)：** 直接刪除包含任何缺失值的整行（觀測值）。
        *   **優點：** 簡單，不引入新偏差（如果缺失是完全隨機的）。
        *   **缺點：** 如果缺失值很多，可能會損失大量數據，導致統計效能下降，甚至引入偏差（如果缺失不是隨機的）。
    *   **成對式刪除 (Pairwise Deletion)：** 在進行特定分析時，僅刪除該分析所需的變量中包含缺失值的觀測值。
        *   **優點：** 保留更多數據。
        *   **缺點：** 每次分析使用的觀測值數量可能不同，導致結果難以比較，且可能引入偏差。

2.  **插補 (Imputation)：** 用估計值填補缺失值。

    *   **統計量插補：**
        *   **均值插補 (Mean Imputation)：** 用該特徵的平均值填補缺失值。
            *   **適用情境：** 數值型數據，缺失值數量不多，且數據分佈近似對稱。
            *   **缺點：** 降低數據的方差，可能導致標準差和相關係數失真。
        *   **中位數插補 (Median Imputation)：** 用該特徵的中位數填補缺失值。
            *   **適用情境：** 數值型數據，數據分佈偏斜或存在異常值。
            *   **優點：** 對異常值不敏感。
        *   **眾數插補 (Mode Imputation)：** 用該特徵的眾數填補缺失值。
            *   **適用情境：** 分類型數據或離散型數值數據。
        *   **固定值插補 (Constant Value Imputation)：** 用一個預定義的固定值（例如 0, -1, 'Unknown'）填補。
            *   **適用情境：** 缺失值本身具有特殊含義，或作為一個類別。
            *   **缺點：** 可能引入錯誤的模式。

    *   **基於預測模型的插補：**
        *   **回歸插補 (Regression Imputation)：** 將有缺失值的特徵作為因變量，其他特徵作為自變量，建立回歸模型來預測缺失值。
            *   **優點：** 考慮了特徵間的關係，比簡單統計量更準確。
            *   **缺點：** 計算量較大，且可能使模型過擬合（如果用於插補的特徵也被用於最終模型）。
        *   **K-近鄰插補 (K-Nearest Neighbors Imputation, KNN Imputation)：** 根據與缺失值記錄最相似的 K 個鄰居的特徵值來插補。
            *   **優點：** 考慮了數據的局部結構，可以處理數值和分類數據。
            *   **缺點：** 對於高維數據或大量數據，計算成本高。
        *   **多重插補 (Multiple Imputation by Chained Equations, MICE)：** 通過迭代方式，為每個缺失值生成多個可能的插補值，然後對每個完整的數據集進行分析，最後合併結果。
            *   **優點：** 提供了對插補不確定性的量化，產生更穩健的統計推斷。
            *   **缺點：** 複雜度高，計算量大。

#### 推導：Imputation 選擇考量

選擇哪種缺失值處理方法，主要考量以下幾點：

1.  **缺失值的比例：** 如果缺失值比例極小（例如小於 1%），簡單的刪除或均值/中位數插補可能就足夠。如果比例很高（例如超過 50%），則可能需要重新評估該特徵的可用性，或者考慮更複雜的插補方法。
2.  **缺失值的類型/模式：**
    *   **完全隨機缺失 (Missing Completely at Random, MCAR)：** 缺失值的出現與任何變量（無論觀察到與否）都沒有關係。此時，刪除或簡單插補偏差較小。
    *   **隨機缺失 (Missing At Random, MAR)：** 缺失值的出現與其他已觀察到的變量有關，但與其自身未觀察到的值無關。例如，男性更少填寫收入。這種情況下，基於模型的插補會更有效。
    *   **非隨機缺失 (Missing Not At Random, MNAR)：** 缺失值的出現與其自身未觀察到的值有關。例如，收入較高的人更不願意透露收入。這是最難處理的情況，任何插補方法都可能引入偏差。
3.  **數據類型：** 數值數據適合均值、中位數、回歸等；分類數據適合眾數、K-近鄰等。
4.  **模型需求：** 某些模型（如決策樹）對缺失值有內建處理能力，而另一些模型（如線性回歸、SVM）則要求數據完整。

### 8.3.2 異常值處理

異常值 (Outliers) 是數據集中那些與大多數數據點顯著偏離的觀測值。它們可能是數據輸入錯誤、測量誤差，也可能是數據分佈中真實存在的極端情況。

#### 定義：異常值檢測方法

異常值檢測的目標是識別出數據集中不符合預期模式的點。

1.  **統計方法：**
    *   **Z-score (標準分數)：** 假設數據呈常態分佈，計算每個數據點與均值的標準差距離。通常，如果 $|Z| > 3$，則被視為異常值。
        $$Z = \frac{x - \mu}{\sigma}$$
        *   **缺點：** 對於非常態分佈數據或存在多個異常值時效果不佳，因為均值和標準差會被異常值影響。
    *   **IQR (Interquartile Range，四分位距)：** 對於非常態分佈數據更穩健。IQR 是 $Q_3 - Q_1$。異常值通常定義為 $x < Q_1 - 1.5 \times IQR$ 或 $x > Q_3 + 1.5 \times IQR$。
    *   **盒形圖 (Box Plot)：** 可視化 IQR 方法，清晰地顯示數據的四分位數和異常值。

2.  **模型方法：**
    *   **孤立森林 (Isolation Forest)：** 一種基於樹的模型，通過隨機選擇特徵並隨機切分值來隔離觀測值。異常值通常在更少的分割步驟中被隔離。
    *   **局部異常因子 (Local Outlier Factor, LOF)：** 計算數據點相對於其鄰居的密度。密度顯著低於其鄰居的點被視為異常值。
    *   **基於距離的方法 (Distance-based Methods)：** 例如 K-近鄰算法，將遠離其最近鄰居的點視為異常值。
    *   **單類 SVM (One-Class SVM)：** 訓練一個模型來學習正常數據的邊界，任何落在邊界之外的點都被視為異常值。

#### 處理方法：刪除、轉換、保留

識別出異常值後，如何處理它們取決於異常值的性質及其對分析的影響。

1.  **刪除 (Deletion)：**
    *   **情境：** 當異常值明顯是數據輸入錯誤、測量誤差，且數量不多時。
    *   **優點：** 簡化數據，防止模型被誤導。
    *   **缺點：** 損失信息，可能隱藏真實但極端的行為模式。

2.  **轉換 (Transformation)：**
    *   **對數轉換 (Log Transformation)：** 對於右偏分佈的數據，取對數可以壓縮高端的值，使其更接近常態分佈，從而減輕異常值的影響。
    *   **開根號轉換 (Square Root Transformation)：** 類似於對數轉換，對數據進行非線性壓縮。
    *   **截斷/封頂 (Capping/Winsorization)：** 將超出預設閾值（如 $Q_1 - 1.5 \times IQR$ 和 $Q_3 + 1.5 \times IQR$）的異常值替換為該閾值本身。
        *   **優點：** 保留了觀測值，只是限制了其極端程度。

3.  **保留 (Retention)：**
    *   **情境：** 當異常值是真實的、重要的信息，且分析目的就是探究這些極端情況時（例如欺詐檢測）。
    *   **處理方式：** 有些模型（如決策樹、基於樹的集成模型）對異常值不那麼敏感，可以直接使用。也可以考慮將異常值作為一個單獨的類別特徵。

### 8.3.3 重複值與不一致性處理

重複值和不一致性是影響數據準確性和可靠性的另兩個常見問題。

#### 方法：識別與刪除重複記錄、標準化文本、資料類型轉換

1.  **重複值處理 (Duplicate Handling)：**
    *   **識別：** 完全重複的行很容易識別。對於部分重複或概念上重複的記錄（例如同一客戶有兩條略有不同的記錄），需要更複雜的模糊匹配算法。
    *   **刪除：** 一旦識別出重複記錄，通常會保留一條，刪除其餘的。
        *   **Python 範例 (Pandas)：**
            ```python
            import pandas as pd
            data = {'col1': [1, 2, 2, 3], 'col2': ['A', 'B', 'B', 'C']}
            df = pd.DataFrame(data)
            print("原始 DataFrame:")
            print(df)

            df_cleaned = df.drop_duplicates()
            print("\n刪除重複值後的 DataFrame:")
            print(df_cleaned)

            # 根據特定列判斷重複（例如只考慮 'col1'）
            df_cleaned_subset = df.drop_duplicates(subset=['col1'])
            print("\n根據 'col1' 刪除重複值後的 DataFrame:")
            print(df_cleaned_subset)
            ```

2.  **不一致性處理 (Inconsistency Handling)：**
    *   **數據格式不一致：**
        *   **統一日期格式：** 例如 '2023-01-01'、'01/01/2023'、'Jan 1, 2023' 統一為 'YYYY-MM-DD'。
        *   **統一單位：** 例如溫度單位攝氏、華氏，貨幣單位美元、歐元。
        *   **統一資料類型：** 確保數字列都是數值類型，日期列都是日期類型。
            *   **Python 範例 (Pandas)：**
                ```python
                df['date_column'] = pd.to_datetime(df['date_column'], errors='coerce')
                df['numeric_column'] = pd.to_numeric(df['numeric_column'], errors='coerce')
                ```
    *   **文本數據不一致：**
        *   **大小寫統一：** 將所有文本轉換為小寫或大寫。
        *   **拼寫錯誤糾正：** 使用模糊匹配或詞典校正。
        *   **移除多餘空格：** 移除文本前後或中間的多餘空格。
        *   **標準化詞彙：** 例如 'St.', 'Street', 'Str.' 都標準化為 'Street'。
            *   **Python 範例 (Pandas)：**
                ```python
                df['text_column'] = df['text_column'].str.lower().str.strip()
                df['city'] = df['city'].replace({'NY': 'New York', 'LA': 'Los Angeles'})
                ```
    *   **業務規則不一致：**
        *   **範圍檢查：** 確保數據值在合理範圍內（例如年齡不能為負數）。
        *   **邏輯檢查：** 例如訂單日期不能晚於出貨日期。

### 與相鄰概念的關聯：數據探索分析 (EDA)

數據清理與**數據探索分析 (Exploratory Data Analysis, EDA)** 緊密相連，互為補充。

*   **EDA 揭示問題：** 在數據清理之前，EDA 用於通過統計摘要、視覺化（如直方圖、散佈圖、盒形圖）來識別和理解數據中的潛在問題，包括缺失值、異常值、數據分佈、特徵間的關係以及不一致性。
*   **清理解決問題：** EDA 發現的問題會引導數據清理的具體操作。例如，EDA 中的盒形圖可能揭示異常值，導致決定對其進行截斷處理；而直方圖中的長尾分佈可能建議進行對數轉換。
*   **清理後再驗證：** 數據清理完成後，通常會再次進行 EDA，以驗證清理操作是否成功解決了問題，以及是否引入了新的偏差。

兩者共同構成數據理解和準備的關鍵步驟，確保後續模型訓練的數據品質。

-----

#### 8.4 數據轉換與特徵工程：為模型優化數據

在數據清理完成後，數據可能仍然不適合直接用於機器學習模型。數據轉換 (Data Transformation) 和特徵工程 (Feature Engineering) 是兩個關鍵步驟，旨在將原始數據轉換為更適合模型訓練的格式，以提高模型的性能和解釋性。

### 核心觀念：數據轉換的目的、特徵工程的意義

*   **數據轉換的目的：**
    *   **尺度統一：** 許多機器學習算法（如梯度下降、SVM、KNN）對特徵的尺度敏感。不同尺度的特徵可能導致大尺度特徵支配小尺度特徵，影響模型的收斂速度和性能。
    *   **滿足算法假設：** 某些算法假設數據服從特定的分佈（如常態分佈），數據轉換可以幫助滿足這些假設。
    *   **減少雜訊：** 通過平滑或聚合等操作減少數據中的隨機雜訊。
    *   **提高可解釋性：** 某些轉換可能使模型結果更易於解釋。

*   **特徵工程的意義：**
    *   **提升模型性能：** 創造出更能捕捉數據中潛在模式的新特徵，直接影響模型的預測能力。通常，良好的特徵工程比複雜的模型調整更能帶來性能提升。
    *   **降低模型複雜度：** 有時一個好的特徵可以替代多個原始特徵，簡化模型結構。
    *   **引入領域知識：** 將領域專家對問題的理解融入到數據中，使其對機器學習模型「可見」。
    *   **解決維度災難：** 通過組合或降維，管理高維數據帶來的問題。

### 8.4.1 數值數據轉換

數值數據轉換主要處理特徵的尺度和分佈。

#### 正規化 (Normalization)：Min-Max Scaling

**核心觀念：** 將數據按比例縮放到一個固定範圍內，通常是 $[0, 1]$ 或 $[-1, 1]$。

**數學公式：**
對於特徵 $X$ 中的每個值 $x_i$，其正規化後的 $x_i'$ 為：
$$x_i' = \frac{x_i - X_{min}}{X_{max} - X_{min}}$$
其中，$X_{min}$ 是特徵 $X$ 的最小值，$X_{max}$ 是特徵 $X$ 的最大值。

**適用情境：**
*   當數據的分佈不是常態分佈，且不希望改變其分佈形狀時。
*   需要將所有特徵限制在固定範圍內時，例如圖像處理中的像素值。
*   一些對尺度敏感的算法，如 KNN、K-Means、ANN (人工神經網絡) 在沒有偏置項的隱藏層。

**缺點：** 對異常值非常敏感。如果數據中存在極端值，它們會壓縮其他數據點的範圍，使得大部分數據點都聚集在 $[0, 1]$ 範圍的一個小區間內。

#### 標準化 (Standardization)：Z-score Scaling

**核心觀念：** 將數據轉換為零均值和單位標準差的常態分佈。

**數學公式：**
對於特徵 $X$ 中的每個值 $x_i$，其標準化後的 $x_i'$ 為：
$$x_i' = \frac{x_i - \mu}{\sigma}$$
其中，$\mu$ 是特徵 $X$ 的均值，$\sigma$ 是特徵 $X$ 的標準差。

**適用情境：**
*   當數據可能存在異常值，或數據分佈未知時。
*   許多線性模型（如線性回歸、邏輯回歸、SVM）以及基於距離的算法。
*   當需要確保不同特徵對模型的貢獻程度相當時。

**優點：**
*   對異常值不那麼敏感（相對於 Min-Max Scaling），因為它只調整分佈，而不是將其壓縮到固定範圍。
*   轉換後的數據符合標準常態分佈的特性，對許多模型是理想的輸入。

**缺點：
*   不將數據約束到特定範圍，因此在需要固定範圍的應用中不適用。

#### 推導：各自的數學公式與適用情境

| 轉換方法 | 公式 | 適用情境 | 優點 | 缺點 |
| :------- | :--- | :------- | :--- | :--- |
| **正規化 (Min-Max Scaling)** | $x' = \frac{x - X_{min}}{X_{max} - X_{min}}$ | 數據分佈不明顯偏態，無極端異常值；需要將數據壓縮到固定範圍 (如 $[0,1]$)。 | 保持原始數據分佈形狀；輸出範圍確定。 | 對異常值敏感；$X_{min}$, $X_{max}$ 需要是訓練集的值。 |
| **標準化 (Z-score Scaling)** | $x' = \frac{x - \mu}{\sigma}$ | 數據分佈近似常態分佈或有異常值；需要減少特徵尺度對模型訓練的影響。 | 處理異常值較穩健；使數據服從標準常態分佈。 | 不將數據約束到固定範圍。 |

### 8.4.2 分類數據編碼

機器學習模型通常無法直接處理文本類型的分類特徵，需要將其轉換為數值形式。

#### 獨熱編碼 (One-Hot Encoding)

**核心觀念：** 將一個分類特徵的每個類別轉換為一個新的二進制特徵（0 或 1）。如果原始數據中的觀測值屬於該類別，則對應的新特徵值為 1，否則為 0。

**典型例子：** 假設有一個 '顏色' 特徵，包含 '紅'、'綠'、'藍' 三個類別。
| 顏色 |
| :--- |
| 紅 |
| 綠 |
| 藍 |
| 紅 |

經過獨熱編碼後：
| 紅 | 綠 | 藍 |
| :- | :- | :- |
| 1 | 0 | 0 |
| 0 | 1 | 0 |
| 0 | 0 | 1 |
| 1 | 0 | 0 |

**適用情境：**
*   **名目型分類特徵 (Nominal Categorical Features)：** 類別之間沒有任何順序關係（例如顏色、城市）。
*   當模型（如線性模型、SVM）會錯誤地解釋標籤編碼中的數值順序時。

**優點：**
*   避免了模型錯誤地推斷類別之間的序數關係。
*   對大多數機器學習算法都友好。

**缺點：**
*   **維度災難：** 如果一個特徵有很多類別，會生成大量的稀疏特徵，增加數據維度，導致計算成本增加和稀疏性問題。
*   可能導致多重共線性問題（Dummy Variable Trap），但現代機器學習庫通常會自動處理。

#### 標籤編碼 (Label Encoding)

**核心觀念：** 將分類特徵的每個類別映射到一個唯一的整數。

**典型例子：** 假設有一個 '教育程度' 特徵，包含 '小學'、'中學'、'大學' 三個類別。
| 教育程度 |
| :------- |
| 小學 |
| 中學 |
| 大學 |
| 小學 |

經過標籤編碼後：
| 教育程度_Encoded |
| :--------------- |
| 0 |
| 1 |
| 2 |
| 0 |

**適用情境：**
*   **序數型分類特徵 (Ordinal Categorical Features)：** 類別之間存在自然的順序關係（例如，'小' < '中' < '大'）。
*   基於樹的模型（如決策樹、隨機森林、XGBoost）通常對標籤編碼不敏感，因為它們處理的是數值分割點，而不是數值本身的大小。
*   當類別數量非常多，獨熱編碼會導致維度災難時，但需謹慎評估是否引入了錯誤的順序。

**優點：**
*   簡單，不需要增加額外的特徵列，節省內存和計算資源。

**缺點：**
*   **引入錯誤的順序關係：** 如果用於名目型特徵，模型可能會錯誤地學習到類別之間的數值順序關係，這在某些算法中會導致性能下降。例如，將 '紅' 編碼為 0，'綠' 編碼為 1，'藍' 編碼為 2，模型可能會認為 '藍' > '綠' > '紅'。

#### 推導：適用情境與潛在問題

| 編碼方法 | 核心思想 | 適用情境 | 潛在問題 |
| :------- | :------- | :------- | :------- |
| **獨熱編碼 (One-Hot Encoding)** | 每個類別生成一個二進制特徵 | 名目型分類特徵；對大多數模型安全 | 類別多時造成維度災難；數據稀疏。 |
| **標籤編碼 (Label Encoding)** | 每個類別映射為一個整數 | 序數型分類特徵；基於樹的模型 | 錯誤引入名目型特徵的順序關係。 |

### 8.4.3 特徵工程

特徵工程是利用領域知識，從原始數據中提取或構造新特徵的過程，以提高機器學習模型的性能。

#### 定義：從現有數據中創造新特徵

特徵工程不僅僅是數據轉換，它更側重於“創造”信息，而這些信息在原始數據中並不明顯，但對模型的預測非常有價值。

#### 典型例子：組合特徵、多項式特徵、時間序列特徵

1.  **組合特徵 (Feature Combinations)：**
    *   **概念：** 將兩個或多個現有特徵組合成一個新特徵，以捕捉它們之間的交互關係。
    *   **例子：**
        *   從 '長度' 和 '寬度' 創建 '面積'：$面積 = 長度 \times 寬度$。
        *   從 '銷售額' 和 '客戶數量' 創建 '平均每客戶銷售額'：$平均銷售額 = 銷售額 / 客戶數量$。
        *   在推薦系統中，用戶 ID 和物品 ID 的組合可以作為交互特徵。

2.  **多項式特徵 (Polynomial Features)：**
    *   **概念：** 考慮特徵的高次項，以捕捉非線性關係。
    *   **例子：** 如果原始特徵是 $x$，可以創建 $x^2, x^3$ 甚至 $x_1 x_2$ 等特徵。
    *   **Python 範例 (Scikit-learn)：**
        ```python
        from sklearn.preprocessing import PolynomialFeatures
        import numpy as np

        data = np.array([[2, 3], [4, 5]]) # x1, x2
        poly = PolynomialFeatures(degree=2, include_bias=False) # degree=2 包含二次項和交互項
        poly_features = poly.fit_transform(data)
        print("原始數據:\n", data)
        # 輸出包含 x1, x2, x1^2, x1*x2, x2^2
        print("多項式特徵:\n", poly_features)
        # 原始特徵為 [x1, x2]
        # PolynomialFeatures(degree=2) 會生成 [x1, x2, x1^2, x1*x2, x2^2]
        # 對於 [2, 3] -> [2, 3, 2^2, 2*3, 3^2] -> [2, 3, 4, 6, 9]
        # 對於 [4, 5] -> [4, 5, 4^2, 4*5, 5^2] -> [4, 5, 16, 20, 25]
        ```

3.  **時間序列特徵 (Time Series Features)：**
    *   **概念：** 從時間戳或日期數據中提取有用的信息。
    *   **例子：**
        *   從 '日期' 中提取 '年份'、'月份'、'日期'、'星期幾'、'是週末嗎'、'是節假日嗎'。
        *   **滯後特徵 (Lag Features)：** 過去時間點的觀測值。例如，今天的銷售額可能與昨天的銷售額相關。
        *   **滾動窗口統計 (Rolling Window Statistics)：** 在某個時間窗口內的統計量，如過去 7 天的平均銷售額、最大溫度等。
        *   **趨勢特徵 (Trend Features)：** 過去一段時間內的變化趨勢。

4.  **基於業務規則的特徵：**
    *   **概念：** 根據領域專家的知識或業務邏輯創建的二進制或數值特徵。
    *   **例子：** 如果用戶購買了 VIP 服務，則創建一個 'is_vip' 特徵。如果訂單金額超過某個閾值，則創建一個 'is_large_order' 特徵。

### 與相鄰概念的關聯：模型性能、維度災難

*   **模型性能 (Model Performance)：**
    *   好的數據轉換和特徵工程能夠顯著提升模型性能。經過適當處理的數據能夠幫助模型更快地收斂，減少過擬合或欠擬合，並提高預測準確性。例如，標準化可以加速梯度下降的收斂；有意義的組合特徵可以幫助模型捕捉更複雜的模式。

*   **維度災難 (Curse of Dimensionality)：**
    *   **問題：** 當特徵數量（數據維度）過多時，數據點在空間中變得極其稀疏，導致模型訓練困難、泛化能力下降，且計算成本急劇增加。
    *   **關聯：**
        *   **獨熱編碼** 在處理類別數多的特徵時，可能直接導致維度災難。
        *   **特徵工程** 雖然旨在創造有用的特徵，但如果盲目創建過多的冗餘或低質量特徵，也可能加劇維度災難。
        *   為應對維度災難，特徵工程中也包含了特徵選擇 (Feature Selection) 和特徵降維 (Feature Reduction) 的技術，例如 PCA (主成分分析) 或卡方檢定，以選擇最重要的特徵子集或減少特徵數量。

因此，在進行數據轉換和特徵工程時，需要權衡其對模型性能的潛在益處和引入維度災難的風險。

-----

#### 8.5 數據驗證與管理

數據集工程不僅關乎數據的準備，還包括確保數據品質的持續性以及數據資產的有效管理。數據驗證和數據管理是確保數據集長期可靠性和可用性的重要環節。

### 核心觀念：數據驗證的重要性、數據版本控制

*   **數據驗證的重要性 (Importance of Data Validation)：**
    *   **預防「垃圾進，垃圾出」：** 數據驗證是防止低質量數據進入數據管道和模型訓練的最後一道防線。它在數據收集和清理之後進行，確保數據符合預期規範和業務規則。
    *   **確保數據一致性與準確性：** 驗證可以捕獲數據類型錯誤、範圍錯誤、格式錯誤以及數據之間的邏輯不一致性。
    *   **提高模型穩定性：** 只有經過驗證的穩定數據才能訓練出穩定且可靠的模型，減少模型在生產環境中因數據變化而失效的風險。
    *   **遵守法規：** 在某些行業中，數據的準確性和一致性是合規性要求的一部分。

*   **數據版本控制的核心觀念 (Core Concepts of Data Versioning)：**
    *   **可追溯性 (Traceability)：** 能夠追溯任何數據集的來源、處理過程、使用時間和相關的代碼版本。
    *   **可重現性 (Reproducibility)：** 確保能夠在未來任何時候，使用相同的代碼和數據版本，重現模型訓練結果或分析報告。
    *   **協同開發 (Collaborative Development)：** 在團隊中協同處理數據集，避免不同成員使用不同版本數據導致的混亂。
    *   **錯誤恢復 (Error Recovery)：** 當數據集或管道出現問題時，能夠回溯到之前穩定的版本。

### 典型例子：Schema 驗證、數據完整性檢查

1.  **Schema 驗證 (Schema Validation)：**
    *   **定義：** 確保數據集的結構（如列名、數據類型、列的數量）符合預定義的 Schema 規範。
    *   **典型應用：** 當數據從不同來源匯入或通過不同管道傳輸時，需要檢查其結構是否一致。
    *   **Python 範例 (使用 Pandera 或 Great Expectations 庫)：**
        ```python
        import pandas as pd
        import pandera as pa

        # 定義數據集的 Schema
        schema = pa.DataFrameSchema(
            {
                "id": pa.Column(int, pa.Check.greater_than(0)),
                "name": pa.Column(str, pa.Check.str_length(min_value=1)),
                "age": pa.Column(int, pa.Check.in_range(0, 120)),
                "city": pa.Column(str, pa.Check.isin(["Taipei", "Kaohsiung", "Tainan"], ignore_na=True)),
                "email": pa.Column(str, pa.Check.str_matches(r"^[^@]+@[^@]+\.[^@]+$"))
            }
        )

        # 模擬一個符合 Schema 的 DataFrame
        data_valid = pd.DataFrame({
            "id": [1, 2, 3],
            "name": ["Alice", "Bob", "Charlie"],
            "age": [25, 30, 35],
            "city": ["Taipei", "Kaohsiung", None],
            "email": ["alice@example.com", "bob@example.com", "charlie@example.com"]
        })

        # 模擬一個不符合 Schema 的 DataFrame (例如 'age' 超出範圍)
        data_invalid = pd.DataFrame({
            "id": [1, 2, 4],
            "name": ["Alice", "Bob", "David"],
            "age": [25, 150, 40], # 150 超出範圍
            "city": ["Taipei", "Hsinchu", "Tainan"], # Hsinchu 不在允許列表
            "email": ["alice@example.com", "bobexample.com", "david@example.com"] # 無效 email
        })

        try:
            schema.validate(data_valid)
            print("數據集符合預期的 Schema。")
        except pa.errors.SchemaErrors as err:
            print("數據集不符合預期的 Schema，錯誤詳情：")
            print(err)

        try:
            schema.validate(data_invalid)
            print("數據集符合預期的 Schema。")
        except pa.errors.SchemaErrors as err:
            print("\n數據集不符合預期的 Schema，錯誤詳情：")
            print(err)
        ```

2.  **數據完整性檢查 (Data Integrity Checks)：**
    *   **定義：** 確保數據的邏輯一致性、關係完整性和業務規則符合度。
    *   **典型應用：**
        *   **唯一性約束：** 確保主鍵或某些關鍵特徵沒有重複值（例如用戶 ID 必須唯一）。
        *   **非空約束：** 確保關鍵特徵沒有缺失值。
        *   **參考完整性：** 在關聯數據中，確保外鍵的值在主表中存在。
        *   **範圍檢查：** 確保數值在合理範圍內（例如價格不能為負）。
        *   **邏輯檢查：** 確保多個特徵之間的邏輯關係正確（例如訂單總額應等於所有商品金額之和）。
    *   **Python 範例 (使用 Pandas 和基本邏輯)：**
        ```python
        import pandas as pd

        df_orders = pd.DataFrame({
            'order_id': [101, 102, 103, 104],
            'customer_id': [1, 2, 1, 3],
            'total_amount': [100.5, 200.0, 100.5, 50.0]
        })

        df_customers = pd.DataFrame({
            'customer_id': [1, 2, 3],
            'customer_name': ['Alice', 'Bob', 'Charlie']
        })

        # 檢查 order_id 唯一性
        if not df_orders['order_id'].is_unique:
            print("錯誤：order_id 存在重複值。")

        # 檢查 customer_id 是否在客戶表中存在 (參考完整性)
        missing_customers = df_orders[~df_orders['customer_id'].isin(df_customers['customer_id'])]
        if not missing_customers.empty:
            print("錯誤：訂單中存在 customer_id 不在客戶表中的記錄。")
            print(missing_customers)

        # 檢查 total_amount 是否為負
        if (df_orders['total_amount'] < 0).any():
            print("錯誤：total_amount 存在負值。")
        ```

### 與相鄰概念的關聯：MLOps、數據治理

*   **MLOps (Machine Learning Operations)：**
    *   數據驗證和數據版本控制是 MLOps 管道的關鍵組成部分。在 MLOps 中，自動化的數據驗證會在數據進入模型訓練管道之前執行，以確保數據品質。數據版本控制則確保模型訓練、評估和部署的可重現性。一個穩健的 MLOps 實踐必須整合數據集工程的這些方面，以實現模型的持續集成、交付和部署 (CI/CD)。

*   **數據治理 (Data Governance)：**
    *   數據治理是一套全面的策略和流程，用於管理整個組織的數據資產。數據集工程，特別是數據驗證和數據管理，是數據治理的實踐層面。數據治理定義了數據品質標準、數據所有權、存取控制和合規性要求，而數據集工程則負責實現這些要求，確保數據的可靠性、安全性和合規性。

兩者共同作用，為組織提供了一個結構化的框架，以有效地管理和利用數據，從而支持數據驅動的決策和創新。

-----

#### 8.6 常見錯誤與澄清

數據集工程是實踐性很強的領域，初學者常會犯一些錯誤。理解這些常見錯誤並加以澄清，有助於建立更穩健的數據處理流程。

### 錯誤：忽略數據清理直接訓練模型

*   **錯誤描述：** 許多初學者在獲取數據後，會跳過耗時的數據清理步驟，直接將原始數據饋入機器學習模型進行訓練。
*   **後果：**
    *   **模型性能差：** 原始數據中的缺失值、異常值、不一致性、錯誤值會直接誤導模型學習到錯誤的模式，導致模型性能低下、準確性差。
    *   **模型不穩定：** 數據中的噪音會使模型對新數據的預測結果不穩定。
    *   **難以解釋的結果：** 模型的決策可能基於錯誤的數據，導致無法合理地解釋其行為。
    *   **數據偏見：** 未經處理的數據偏見可能被模型放大，導致不公平或歧視性的結果。
*   **澄清：** **「垃圾進，垃圾出」(Garbage In, Garbage Out) 是數據科學的金科玉律。** 數據清理是任何成功機器學習專案的基礎。投入時間在數據清理上，通常比花費更多時間在模型調優上更能顯著提升模型性能。數據科學家和機器學習工程師花費大部分時間在數據預處理上是常態。

### 錯誤：錯誤地應用數據轉換方法

*   **錯誤描述：** 在數據轉換階段，不區分訓練集和測試集，將數據轉換（如正規化、標準化）的參數（如均值、標準差、最大值、最小值）基於整個數據集計算，然後應用於所有數據。
*   **後果：**
    *   **數據洩漏 (Data Leakage)：** 測試集或驗證集的信息會洩漏到訓練過程中。這是因為轉換參數（如均值、標準差）包含了測試集的信息，導致模型在測試集上的表現看起來比實際情況要好，從而對模型的泛化能力產生過於樂觀的估計。
    *   **模型在生產環境中表現不佳：** 在實際部署時，模型會處理全新的、未見過的數據。如果數據轉換參數是基於訓練集計算的，那麼在生產環境中，它才能正確地處理新數據。
*   **澄清：** **數據轉換參數必須只從訓練集中學習。**
    *   **正確流程：**
        1.  將原始數據集劃分為訓練集和測試集（或驗證集）。
        2.  在**訓練集**上計算所有數據轉換所需的參數（例如 Min-Max Scaler 的 $X_{min}, X_{max}$，Standard Scaler 的 $\mu, \sigma$）。
        3.  使用這些從**訓練集**學習到的參數來轉換**訓練集**。
        4.  使用同樣從**訓練集**學習到的參數來轉換**測試集**（以及未來的生產數據）。**切勿在測試集上重新計算轉換參數。**

    *   **Python 範例 (使用 Scikit-learn)：**
        ```python
        from sklearn.model_selection import train_test_split
        from sklearn.preprocessing import StandardScaler
        import pandas as pd
        import numpy as np

        # 創建一個示例 DataFrame
        data = pd.DataFrame({
            'feature1': np.random.rand(100) * 100,
            'feature2': np.random.randn(100) * 10 + 50,
            'target': np.random.randint(0, 2, 100)
        })

        X = data[['feature1', 'feature2']]
        y = data['target']

        # 1. 劃分訓練集和測試集
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        # 2. 在訓練集上初始化並學習標準化參數
        scaler = StandardScaler()
        scaler.fit(X_train) # 只在訓練集上 fit

        # 3. 使用學習到的參數轉換訓練集
        X_train_scaled = scaler.transform(X_train)

        # 4. 使用同樣學習到的參數轉換測試集
        X_test_scaled = scaler.transform(X_test) # 注意：這裡依然是 transform，不是 fit_transform

        print("訓練集原始數據前5行:\n", X_train.head())
        print("\n訓練集標準化後數據前5行:\n", X_train_scaled[:5])
        print("\n測試集原始數據前5行:\n", X_test.head())
        print("\n測試集標準化後數據前5行:\n", X_test_scaled[:5])

        # 錯誤的範例 (將會在測試集上重新 fit，導致數據洩漏)
        # scaler_wrong = StandardScaler()
        # X_test_scaled_wrong = scaler_wrong.fit_transform(X_test)
        # 這樣做會讓 scaler_wrong 從測試集學習均值和標準差，導致數據洩漏
        ```

### 澄清：訓練集與測試集的數據處理分離

這一點是機器學習中「防止數據洩漏」的核心原則之一，不僅適用於數據轉換，也適用於特徵工程（例如基於數據的特徵選擇）。任何從數據中學習的過程（例如計算統計量、選擇特徵），都必須只在訓練集上進行。測試集和驗證集應被視為未來的、真實的數據，僅用於評估模型的泛化能力，不能參與任何學習過程。

-----

#### 8.7 小練習

以下提供兩個小練習，幫助您鞏固數據集工程中的數據清理和數據轉換概念。

### 小練習 1：缺失值與異常值處理

你收到一個客戶數據集，其中包含 `Age` (年齡)、`Income` (收入)、`Experience` (工作經驗) 三個數值特徵。

**數據集預覽：**
```
   Age  Income  Experience
0   25   50000           3
1   -5   60000           5
2   30       NaN         7
3   45   75000         -2
4   NaN  80000           8
5   50   55000          10
6   28  200000           4  <- 可能是收入異常值
7   35   62000           6
8   99  580000           1  <- 可能是年齡、收入異常值
```

**任務要求：**

1.  **識別並處理缺失值：**
    *   計算每個特徵的缺失值數量和比例。
    *   對於 `Age` 特徵，使用**中位數**進行插補。
    *   對於 `Income` 特徵，使用**均值**進行插補。
    *   對於 `Experience` 特徵，使用**眾數**進行插補。
2.  **識別並處理異常值：**
    *   針對 `Age` 特徵：
        *   將小於 0 或大於 90 的值視為異常值。
        *   將這些異常值替換為 `Age` 特徵的**中位數**。
    *   針對 `Experience` 特徵：
        *   將小於 0 的值視為異常值。
        *   將這些異常值替換為 `Experience` 特徵的**眾數**。
    *   針對 `Income` 特徵：
        *   使用 **IQR 方法**識別異常值（超出 $Q_1 - 1.5 \times IQR$ 或 $Q_3 + 1.5 \times IQR$）。
        *   將識別出的異常值替換為其對應的上限或下限（即截斷/封頂）。

**提示：** 使用 Pandas 庫進行操作。

---

#### 詳解：小練習 1

```python
import pandas as pd
import numpy as np

# 創建數據集
data = {
    'Age': [25, -5, 30, 45, np.nan, 50, 28, 35, 99],
    'Income': [50000, 60000, np.nan, 75000, 80000, 55000, 200000, 62000, 580000],
    'Experience': [3, 5, 7, -2, 8, 10, 4, 6, 1]
}
df = pd.DataFrame(data)
print("原始數據集:\n", df)
print("-" * 30)

# 1. 識別並處理缺失值
print("--- 1. 處理缺失值 ---")
print("各特徵缺失值數量:\n", df.isnull().sum())
print("各特徵缺失值比例:\n", df.isnull().sum() / len(df) * 100, "%\n")

# Age 特徵使用中位數插補
age_median = df['Age'].median()
df['Age'].fillna(age_median, inplace=True)
print(f"Age 特徵使用中位數 {age_median} 進行插補。")

# Income 特徵使用均值插補
income_mean = df['Income'].mean()
df['Income'].fillna(income_mean, inplace=True)
print(f"Income 特徵使用均值 {income_mean:.2f} 進行插補。")

# Experience 特徵使用眾數插補
experience_mode = df['Experience'].mode()[0] # mode() 可能返回多個值，取第一個
df['Experience'].fillna(experience_mode, inplace=True)
print(f"Experience 特徵使用眾數 {experience_mode} 進行插補。\n")

print("缺失值處理後的數據集:\n", df)
print("-" * 30)

# 2. 識別並處理異常值
print("--- 2. 處理異常值 ---")

# 處理 Age 特徵異常值 (小於0或大於90)
age_median_after_imputation = df['Age'].median() # 重新計算中位數，因為缺失值已插補
df['Age'] = np.where((df['Age'] < 0) | (df['Age'] > 90), age_median_after_imputation, df['Age'])
print(f"Age 特徵異常值 (小於0或大於90) 已替換為中位數 {age_median_after_imputation}。")

# 處理 Experience 特徵異常值 (小於0)
experience_mode_after_imputation = df['Experience'].mode()[0] # 重新計算眾數
df['Experience'] = np.where(df['Experience'] < 0, experience_mode_after_imputation, df['Experience'])
print(f"Experience 特徵異常值 (小於0) 已替換為眾數 {experience_mode_after_imputation}。")

# 處理 Income 特徵異常值 (IQR 方法)
Q1_income = df['Income'].quantile(0.25)
Q3_income = df['Income'].quantile(0.75)
IQR_income = Q3_income - Q1_income
lower_bound_income = Q1_income - 1.5 * IQR_income
upper_bound_income = Q3_income + 1.5 * IQR_income

print(f"\nIncome 特徵 IQR 方法閾值：")
print(f"  Q1: {Q1_income:.2f}, Q3: {Q3_income:.2f}, IQR: {IQR_income:.2f}")
print(f"  下限: {lower_bound_income:.2f}, 上限: {upper_bound_income:.2f}")

# 識別異常值
outliers_income = df[(df['Income'] < lower_bound_income) | (df['Income'] > upper_bound_income)]
print("\nIncome 特徵識別到的異常值:\n", outliers_income)

# 替換異常值為上限或下限 (截斷/封頂)
df['Income'] = np.where(df['Income'] < lower_bound_income, lower_bound_income, df['Income'])
df['Income'] = np.where(df['Income'] > upper_bound_income, upper_bound_income, df['Income'])
print("Income 特徵異常值已使用 IQR 方法進行截斷/封頂處理。\n")


print("異常值處理後的最終數據集:\n", df)
```

---

### 小練習 2：數據正規化與編碼

你擁有一個包含客戶信息的數據集，其中包含數值特徵和分類特徵。

**數據集預覽：**
```
   Age  Salary      City Education
0   30   60000    Taipei      High
1   22   35000   Kaohsiung    Junior
2   45   90000    Taipei    College
3   38   75000     Tainan      High
4   55  120000   Kaohsiung    Master
5   28   50000     Tainan    Junior
```

**任務要求：**

1.  **數值特徵處理：**
    *   將 `Age` 特徵進行 **Min-Max 正規化**，範圍縮放到 $[0, 1]$。
    *   將 `Salary` 特徵進行 **Z-score 標準化**。
2.  **分類特徵編碼：**
    *   對 `City` 特徵使用 **獨熱編碼 (One-Hot Encoding)**。
    *   對 `Education` 特徵使用 **標籤編碼 (Label Encoding)**。假設教育程度有自然的順序：Junior < High < College < Master。請手動定義這種順序映射。
3.  **組合處理：** 將處理後的特徵重新組合成一個新的 DataFrame。

**提示：**
*   使用 Scikit-learn 的 `MinMaxScaler`, `StandardScaler`, `OneHotEncoder`。
*   對於 `Education` 的標籤編碼，可以直接使用 Pandas 的 `map` 或 `replace` 方法，也可以使用 Scikit-learn 的 `OrdinalEncoder` 並指定類別順序。

---

#### 詳解：小練習 2

```python
import pandas as pd
from sklearn.preprocessing import MinMaxScaler, StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
import numpy as np

# 創建數據集
data = {
    'Age': [30, 22, 45, 38, 55, 28],
    'Salary': [60000, 35000, 90000, 75000, 120000, 50000],
    'City': ['Taipei', 'Kaohsiung', 'Taipei', 'Tainan', 'Kaohsiung', 'Tainan'],
    'Education': ['High', 'Junior', 'College', 'High', 'Master', 'Junior']
}
df = pd.DataFrame(data)
print("原始數據集:\n", df)
print("-" * 30)

# 1. 數值特徵處理
print("--- 1. 數值特徵處理 ---")
# Age 特徵進行 Min-Max 正規化
min_max_scaler = MinMaxScaler()
df['Age_MinMax'] = min_max_scaler.fit_transform(df[['Age']])
print(f"Age 特徵 Min-Max 正規化後的 Age_MinMax (Min: {df['Age_MinMax'].min():.2f}, Max: {df['Age_MinMax'].max():.2f}):\n", df[['Age', 'Age_MinMax']])

# Salary 特徵進行 Z-score 標準化
std_scaler = StandardScaler()
df['Salary_ZScore'] = std_scaler.fit_transform(df[['Salary']])
print(f"\nSalary 特徵 Z-score 標準化後的 Salary_ZScore (Mean: {df['Salary_ZScore'].mean():.2f}, Std: {df['Salary_ZScore'].std():.2f}):\n", df[['Salary', 'Salary_ZScore']])
print("-" * 30)


# 2. 分類特徵編碼
print("--- 2. 分類特徵編碼 ---")
# City 特徵獨熱編碼
onehot_encoder = OneHotEncoder(sparse_output=False, handle_unknown='ignore')
# 注意：OneHotEncoder 需要 2D 數組，因此使用 df[['City']]
city_encoded = onehot_encoder.fit_transform(df[['City']])
city_df = pd.DataFrame(city_encoded, columns=onehot_encoder.get_feature_names_out(['City']))
print("\nCity 特徵獨熱編碼後的 City_Taipei, City_Kaohsiung, City_Tainan:\n", city_df)

# Education 特徵標籤編碼 (序數型)
# 手動定義順序映射
education_mapping = {
    'Junior': 0,
    'High': 1,
    'College': 2,
    'Master': 3
}
df['Education_Encoded'] = df['Education'].map(education_mapping)
print("\nEducation 特徵標籤編碼後的 Education_Encoded:\n", df[['Education', 'Education_Encoded']])
print("-" * 30)

# 3. 組合處理後的特徵
print("--- 3. 組合處理後的特徵 ---")
# 創建一個新的 DataFrame，包含所有處理後的特徵
df_processed = pd.concat([
    df[['Age_MinMax', 'Salary_ZScore', 'Education_Encoded']], # 數值和序數編碼特徵
    city_df # 獨熱編碼特徵
], axis=1)

print("所有處理後的特徵組合 DataFrame:\n", df_processed)

# ----------------- 額外：使用 ColumnTransformer 簡化流程 -----------------
print("\n" + "=" * 50)
print("--- 額外：使用 ColumnTransformer 簡化流程 ---")

# 重建原始 DataFrame
df_original = pd.DataFrame(data)

# 定義要處理的列和處理器
preprocessor = ColumnTransformer(
    transformers=[
        ('age_scaler', MinMaxScaler(), ['Age']),
        ('salary_scaler', StandardScaler(), ['Salary']),
        ('city_onehot', OneHotEncoder(sparse_output=False, handle_unknown='ignore'), ['City']),
        ('edu_ordinal', Pipeline([
            ('map_education', pa.DataFrameSchema(  # Using a dummy schema for demonstration, direct map is better here
                pa.Column(str, checks=[pa.Check(lambda s: s.map(education_mapping), element_wise=False)]),
                index=pa.Index(int) # Dummy index
            ))
        ]), ['Education'])
    ],
    remainder='passthrough' # 保留未處理的列，如果有的話
)

# For education, direct mapping is typically done before ColumnTransformer or within a custom transformer
# Let's adjust for Education to be simpler or use OrdinalEncoder with categories
# Using a custom function or pandas map is generally clearer for ordinal with specific order.
# For OrdinalEncoder, you'd specify categories:
from sklearn.preprocessing import OrdinalEncoder
education_categories = ['Junior', 'High', 'College', 'Master']

preprocessor_simplified = ColumnTransformer(
    transformers=[
        ('age_scaler', MinMaxScaler(), ['Age']),
        ('salary_scaler', StandardScaler(), ['Salary']),
        ('city_onehot', OneHotEncoder(sparse_output=False, handle_unknown='ignore'), ['City']),
        ('edu_ordinal', OrdinalEncoder(categories=[education_categories], handle_unknown='use_encoded_value', unknown_value=-1), ['Education'])
    ],
    remainder='passthrough'
)

# 應用轉換
X_processed_array = preprocessor_simplified.fit_transform(df_original)

# 獲取新的列名
feature_names = (
    ['Age_MinMax', 'Salary_ZScore'] +
    list(preprocessor_simplified.named_transformers_['city_onehot'].get_feature_names_out(['City'])) +
    ['Education_Encoded']
)

df_processed_ct = pd.DataFrame(X_processed_array, columns=feature_names)
print("\n使用 ColumnTransformer 處理後的 DataFrame:\n", df_processed_ct)
```

---

#### 8.8 延伸閱讀/參考

數據集工程是一個廣泛的領域，涵蓋了從基礎的數據處理到複雜的數據治理。以下是一些推薦的延伸閱讀和參考資料，可以幫助您更深入地理解和實踐數據集工程。

### 書籍

*   **《Hands-On Machine Learning with Scikit-Learn, Keras, and TensorFlow》** by Aurélien Géron
    *   這本書是機器學習領域的經典入門，其中包含了大量關於數據預處理和特徵工程的實踐範例，特別是使用 Scikit-learn 庫。
*   **《Feature Engineering for Machine Learning》** by Alice Zheng and Amanda Casari
    *   專注於特徵工程的書籍，深入探討了如何從各種數據類型中提取和創造有效特徵的技術和策略。
*   **《Designing Data-Intensive Applications》** by Martin Kleppmann
    *   雖然不是直接關於機器學習的，但這本書深入探討了數據系統的設計原則、數據存儲、處理和可靠性，對於理解大型數據集的工程基礎非常有幫助。

### 線上資源與文章

*   **Towards Data Science (Medium 平台)**
    *   這個平台上有大量關於數據清理、特徵工程、數據驗證和 MLOps 的文章。您可以搜索相關關鍵字找到實用的教程和案例研究。
*   **Kaggle Learn Courses: Feature Engineering**
    *   Kaggle 提供了一個免費的特徵工程課程，通過實例教導如何應用各種特徵工程技術。
*   **Scikit-learn 官方文檔**
    *   Scikit-learn 庫是 Python 中進行數據預處理和轉換的標準工具。其官方文檔對於理解各種轉換器（如 `MinMaxScaler`, `StandardScaler`, `OneHotEncoder` 等）的用法和原理非常有價值。
    *   [Scikit-learn Preprocessing data](https://scikit-learn.org/stable/modules/preprocessing.html)
*   **Great Expectations / Pandera 庫**
    *   這兩個庫專注於數據驗證。它們提供了強大的工具來定義和執行數據品質檢查，確保數據的可靠性。
    *   [Great Expectations 官方網站](https://greatexpectations.io/)
    *   [Pandera 官方網站](https://pandera.readthedocs.io/en/stable/)
*   **DVC (Data Version Control) 官方文檔**
    *   如果您需要對數據集進行版本控制，DVC 是一個與 Git 協同工作的優秀工具。
    *   [DVC 官方網站](https://dvc.org/)

### 學術論文/研究

*   **"A Survey on Data Preprocessing for Machine Learning"**
    *   這類綜述性文章通常會提供數據預處理技術的全面概覽和比較。
*   **特定領域的數據處理論文**
    *   如果您專注於特定領域（如自然語言處理、計算機視覺、金融數據），搜索該領域中關於數據集工程的最新研究會非常有益。

持續學習和實踐是掌握數據集工程的關鍵。通過閱讀這些資源並將所學應用到實際專案中，您將能夠顯著提升您的數據處理能力。