# 第八章 設計模式與軟體重構

本章將深入探討軟體開發中兩個極為關鍵的實踐：設計模式與軟體重構。它們分別代表了軟體設計的「最佳實踐藍圖」與「持續改進手段」，對於提升程式碼品質、可維護性、可擴展性及團隊協作效率有著不可或缺的作用。

-----

## 8.1 核心概念與定義

### 8.1.1 設計模式 (Design Patterns)

#### 定義/核心觀念

設計模式是針對在特定上下文 (context) 下，反覆出現的設計問題，所提出的一套經過驗證的、通用且可重複使用的解決方案。它們並不是可以直接轉換為程式碼的函式庫或框架，而是一種更高層次的、抽象的、關於如何組織類別和物件以解決特定問題的描述。

*   **GoF (Gang of Four) 分類**: 最經典的設計模式分類來自於 1994 年 Erich Gamma 等四位作者的著作《Design Patterns: Elements of Reusable Object-Oriented Software》。他們將設計模式分為三大類：
    1.  **創建型模式 (Creational Patterns)**：處理物件的創建機制，旨在以靈活且控制的方式產生物件。例如：`Singleton` (單例模式)、`Factory Method` (工廠方法模式)、`Abstract Factory` (抽象工廠模式)、`Builder` (建造者模式)、`Prototype` (原型模式)。
    2.  **結構型模式 (Structural Patterns)**：關注類別和物件的組合，以形成更大的結構。例如：`Adapter` (轉接器模式)、`Decorator` (裝飾器模式)、`Facade` (外觀模式)、`Proxy` (代理模式)、`Composite` (組合模式)、`Bridge` (橋接模式)、`Flyweight` (享元模式)。
    3.  **行為型模式 (Behavioral Patterns)**：專注於物件之間的通訊和職責分配，以提高彈性。例如：`Strategy` (策略模式)、`Observer` (觀察者模式)、`Command` (命令模式)、``Iterator` (迭代器模式)、`State` (狀態模式)、`Template Method` (模板方法模式)、`Mediator` (中介者模式)、`Chain of Responsibility` (責任鏈模式)、`Visitor` (訪問者模式)、`Memento` (備忘錄模式)。

*   **核心觀念**：
    *   **提供共同語言**: 設計模式為開發者提供了一種通用的、高層次的抽象語言來討論設計問題和解決方案。
    *   **經驗的結晶**: 它們是前人在軟體開發中遇到的重複性問題及其最佳解決方案的總結。
    *   **提高可維護性與可擴展性**: 正確應用設計模式可以使程式碼更具彈性、更容易理解和修改，從而提高軟體的生命週期。
    *   **抽象化**: 模式是抽象的解決方案，需要根據具體問題進行調整和實作。

#### 例子或推導

以 `Singleton` (單例模式) 為例：
**問題**: 確保一個類別只有一個實例，並提供一個全域訪問點。
**解決方案**:

```java
public class Singleton {
    private static Singleton instance; // 靜態變數保存唯一實例

    // 私有建構子，防止外部直接實例化
    private Singleton() {
        // ... 初始化邏輯 ...
    }

    // 提供一個靜態方法獲取實例
    public static Singleton getInstance() {
        if (instance == null) {
            instance = new Singleton(); // 首次調用時創建實例
        }
        return instance;
    }

    public void showMessage() {
        System.out.println("Hello from Singleton!");
    }
}

// 如何使用
// Singleton s1 = Singleton.getInstance();
// Singleton s2 = Singleton.getInstance();
// // s1 和 s2 是同一個物件實例
```
**推導**: 如果沒有 `Singleton` 模式，我們可能會透過全域變數或靜態類別來達到類似目的，但 `Singleton` 模式提供了一個更結構化、更受控的創建方式，並能更好地處理懶加載 (lazy initialization) 和多執行緒安全等問題。

#### 與相鄰概念的關聯

設計模式與物件導向設計原則 (SOLID 原則)、抽象化、模組化、框架 (Framework) 等概念緊密相關。它們是實踐這些原則的具體方法，也是許多框架底層設計的基礎。

-----

### 8.1.2 軟體重構 (Software Refactoring)

#### 定義/核心觀念

軟體重構是指在不改變軟體外部行為的前提下，改變其內部結構的過程。其主要目的是改善程式碼的設計、可讀性、可維護性和可擴展性，同時降低其複雜度和技術債務。

*   **核心觀念**:
    *   **不改變外部行為**: 這是重構的黃金法則。用戶看到的軟體功能必須保持不變。這通常需要仰賴完善的測試來保證。
    *   **改善內部結構**: 透過一系列小而安全的變更，例如重新組織類別、方法、變數等，使程式碼更清晰、更符合設計原則。
    *   **消除「壞味道」 (Code Smells)**: 重構通常是為了消除程式碼中的各種「壞味道」，這些是潛在問題的指標。
    *   **持續的過程**: 重構不應是一次性的大規模活動，而應是開發過程中的一個持續、頻繁、小規模的實踐。

#### 例子或推導

以「提取方法 (Extract Method)」重構為例：
**問題**: 一個方法過於冗長，包含多個不同的邏輯段落。
**原始程式碼 (Python 示例)**:

```python
def calculate_order(items, customer_info):
    # 第一部分：計算總價
    total_price = 0
    for item in items:
        total_price += item['price'] * item['quantity']
    print(f"總價計算完成: {total_price}")

    # 第二部分：處理折扣
    discount = 0
    if customer_info['is_vip']:
        discount = total_price * 0.1
        print("VIP 折扣已應用")
    else:
        print("無 VIP 折扣")
    final_price = total_price - discount

    # 第三部分：生成發票號
    import random
    invoice_id = f"INV-{random.randint(10000, 99999)}"
    print(f"發票號生成: {invoice_id}")

    return final_price, invoice_id
```

**重構後 (Python 示例)**:

```python
def _calculate_total_price(items): # 輔助方法1
    total = 0
    for item in items:
        total += item['price'] * item['quantity']
    return total

def _apply_discount(total_price, customer_info): # 輔助方法2
    discount = 0
    if customer_info['is_vip']:
        discount = total_price * 0.1
        print("VIP 折扣已應用")
    else:
        print("無 VIP 折扣")
    return total_price - discount

def _generate_invoice_id(): # 輔助方法3
    import random
    return f"INV-{random.randint(10000, 99999)}"

def calculate_order(items, customer_info):
    total_price = _calculate_total_price(items)
    print(f"總價計算完成: {total_price}")

    final_price = _apply_discount(total_price, customer_info)
    
    invoice_id = _generate_invoice_id()
    print(f"發票號生成: {invoice_id}")

    return final_price, invoice_id
```
**推導**: 透過將原方法中的三個獨立邏輯塊提取為獨立的私有輔助方法，`calculate_order` 方法變得更短、更易讀，每個輔助方法也更容易理解和測試。這就是重構的一個基本手法。

#### 與相鄰概念的關聯

重構與測試驅動開發 (TDD)、極限編程 (XP)、敏捷開發、程式碼審查 (Code Review)、程式碼品質度量等概念緊密相連。TDD 提供安全網，敏捷開發鼓勵持續重構，程式碼審查則能發現重構的機會。

-----

### 8.1.3 壞味道 (Code Smells)

#### 定義/核心觀念

「壞味道」是程式碼中潛在問題或設計缺陷的表面跡象。它們本身不一定是錯誤，但它們通常指出設計有問題，需要重構以改善。識別壞味道是重構的第一步。

*   **核心觀念**:
    *   **警示信號**: 壞味道是程式碼告訴我們「這裡可能需要改進」的訊號。
    *   **重構的動機**: 消除壞味道是進行重構的主要原因和目標。
    *   **非絕對的錯誤**: 有時候，在特定情境下，某種「壞味道」可能是可以接受甚至必要的妥協。判斷需要經驗。

#### 例子或推導

常見的壞味道包括：

*   **重複程式碼 (Duplicate Code)**：相同或非常相似的程式碼段在多個地方出現。這是最常見也最容易處理的壞味道之一，通常可以透過提取方法、提取類別或使用模板方法等重構手法來消除。
*   **長方法 (Long Method)**：一個方法包含過多的程式碼行數或過多的邏輯。它降低了可讀性，使得測試和維護變得困難。重構手法主要是「提取方法」。
*   **大類 (Large Class)**：一個類別承擔了過多的職責，擁有很多欄位和方法。這違反了單一職責原則 (SRP)。重構手法包括「提取類別」、「移動方法/欄位」等。
*   **過長的參數列表 (Long Parameter List)**：一個方法的參數過多。這使得方法調用變得複雜，難以理解其功能。可以透過「引入參數物件」或將參數移動到物件中來重構。
*   **霰彈式修改 (Shotgun Surgery)**：修改某個功能需要在多個地方進行小幅度的修改。這表明相關邏輯分散在多處，缺乏內聚性。可以透過「移動方法/欄位」、「提取類別」來增強內聚。
*   **依賴情節 (Feature Envy)**：一個方法過多地訪問另一個物件的資料，而非自身物件的資料。這表明該方法可能更適合放在它所羨慕的那個物件中。重構手法是「移動方法」。
*   **過度耦合 (Coupling)**：類別之間過於緊密的依賴，導致一個類別的改變會影響到許多其他類別。需要解耦，例如透過介面、依賴反轉等。

**推導**: 當你看到兩個不同的方法有幾乎完全相同的 10 行程式碼時，這就是明顯的「重複程式碼」壞味道。這 10 行程式碼可以被提取成一個新的私有輔助方法，然後在原來兩個地方調用這個新方法。這不僅減少了程式碼量，也使未來修改這段邏輯時只需要改一個地方。

#### 與相鄰概念的關聯

壞味道是設計原則 (如 SOLID 原則) 被違反的表象。例如，「大類」常常違反「單一職責原則」，「霰彈式修改」則暗示低內聚高耦合。理解壞味道是進行有效重構和應用設計模式的先決條件。

-----

## 8.2 設計模式的應用與重構實踐

### 8.2.1 設計模式如何輔助重構

設計模式和重構是相輔相成的關係。設計模式提供了經過驗證的解決方案模板，而重構則是將現有程式碼演進至符合這些模式的手段。

*   **將既有程式碼重構為符合某個設計模式**:
    當現有程式碼存在「壞味道」，例如大量的條件判斷 (if-else if-else 或 switch-case)，這些判值邏輯如果隨著業務需求變化，會變得難以維護和擴展。此時，可以考慮將其重構為行為型模式，例如 `Strategy` (策略模式) 或 `State` (狀態模式)。
*   **在新的開發中採用設計模式，減少未來重構需求**:
    預見性地使用設計模式，可以從一開始就建立更健壯、更靈活的架構，減少未來因為設計不良而需要大規模重構的可能性。
*   **設計模式作為重構的目標結構**:
    當識別出程式碼中的問題時，我們可以將某個設計模式作為解決該問題的「理想目標結構」。重構的過程就是逐步將程式碼朝這個目標結構演進。

#### 例子：將條件判斷重構為策略模式 (Strategy Pattern)

**情境**: 一個處理不同訂單類型支付的方法。

**原始程式碼 (Java 示例)**:

```java
public class OrderProcessor {
    public void processPayment(String orderType, double amount) {
        if ("CreditCard".equals(orderType)) {
            System.out.println("Processing credit card payment for $" + amount);
            // ... 信用卡支付邏輯 ...
        } else if ("PayPal".equals(orderType)) {
            System.out.println("Processing PayPal payment for $" + amount);
            // ... PayPal 支付邏輯 ...
        } else if ("BankTransfer".equals(orderType)) {
            System.out.println("Processing bank transfer for $" + amount);
            // ... 銀行轉帳支付邏輯 ...
        } else {
            System.out.println("Unsupported payment type: " + orderType);
        }
    }
}
```

**問題分析**:
*   `processPayment` 方法過長且包含多個分支，違反了單一職責原則。
*   每次新增一種支付方式，都需要修改此方法，違反了開放/封閉原則 (Open/Closed Principle)。

**推導重構為策略模式**:

1.  **識別變化點與不變點**: 支付方式是變化的，而處理支付這個動作是不變的。
2.  **定義策略介面**: 建立一個支付策略介面，定義共同的支付方法。

    ```java
    public interface PaymentStrategy {
        void pay(double amount);
    }
    ```

3.  **實作具體策略類別**: 為每種支付方式建立一個實現 `PaymentStrategy` 介面的類別。

    ```java
    public class CreditCardPayment implements PaymentStrategy {
        @Override
        public void pay(double amount) {
            System.out.println("Processing credit card payment for $" + amount);
            // ... 信用卡支付邏輯 ...
        }
    }

    public class PayPalPayment implements PaymentStrategy {
        @Override
        public void pay(double amount) {
            System.out.println("Processing PayPal payment for $" + amount);
            // ... PayPal 支付邏輯 ...
        }
    }

    public class BankTransferPayment implements PaymentStrategy {
        @Override
        public void pay(double amount) {
            System.out.println("Processing bank transfer for $" + amount);
            // ... 銀行轉帳支付邏輯 ...
        }
    }
    ```

4.  **建立 Context 類別或使用工廠模式**:
    *   **Context 類別**: 持有一個 `PaymentStrategy` 的實例，並將請求委託給它。

        ```java
        public class PaymentContext {
            private PaymentStrategy strategy;

            public void setPaymentStrategy(PaymentStrategy strategy) {
                this.strategy = strategy;
            }

            public void executePayment(double amount) {
                if (strategy == null) {
                    throw new IllegalStateException("Payment strategy not set.");
                }
                strategy.pay(amount);
            }
        }
        ```
    *   **工廠模式 (Factory Pattern)** (可選，但常見於處理策略選擇): 建立一個工廠來根據輸入動態地返回相應的策略實例。

        ```java
        public class PaymentStrategyFactory {
            public static PaymentStrategy getStrategy(String orderType) {
                if ("CreditCard".equals(orderType)) {
                    return new CreditCardPayment();
                } else if ("PayPal".equals(orderType)) {
                    return new PayPalPayment();
                } else if ("BankTransfer".equals(orderType)) {
                    return new BankTransferPayment();
                }
                throw new IllegalArgumentException("Unsupported payment type: " + orderType);
            }
        }
        ```

5.  **修改原始 `OrderProcessor` (或其調用者)**:

    ```java
    public class NewOrderProcessor {
        public void processPayment(String orderType, double amount) {
            PaymentStrategy strategy = PaymentStrategyFactory.getStrategy(orderType);
            PaymentContext context = new PaymentContext();
            context.setPaymentStrategy(strategy);
            context.executePayment(amount);
        }
    }

    // 使用方式:
    // NewOrderProcessor processor = new NewOrderProcessor();
    // processor.processPayment("CreditCard", 100.0);
    // processor.processPayment("PayPal", 50.0);
    ```

**重構結果**:
現在，新增支付方式只需要新增一個 `PaymentStrategy` 的實現類別，並在工廠中稍微修改，而不需要改動 `NewOrderProcessor` 的核心邏輯。這大大提高了系統的可擴展性和可維護性。

-----

### 8.2.2 典型的重構手法

重構通常由一系列小而安全的步驟組成。以下是一些常見的重構手法：

*   **提取方法 (Extract Method)**：將一個方法中一段獨立的邏輯程式碼提取到一個新的獨立方法中。
    *   **用途**: 減少方法長度、提高可讀性、消除重複程式碼、使每個方法職責更單一。
*   **移動方法/欄位 (Move Method/Field)**：將一個方法或欄位從一個類別移動到另一個更適合它的類別。
    *   **用途**: 改善類別之間的內聚性 (cohesion) 和耦合性 (coupling)，使資料和其操作更靠近。通常用於處理「依賴情節」壞味道。
*   **取代條件判斷為多型 (Replace Conditional with Polymorphism)**：將基於類型碼或條件邏輯的 `if-else` 或 `switch-case` 語句替換為多型行為。
    *   **用途**: 消除重複的條件邏輯，使系統更容易擴展，符合開放/封閉原則。這是將壞味道重構為策略模式或狀態模式的關鍵步驟。
*   **引入物件 (Introduce Parameter Object)**：當一個方法的參數列表過長時，將相關的參數組合封裝到一個新的物件中。
    *   **用途**: 減少參數數量、提高程式碼可讀性、方便參數傳遞、為未來的擴展預留空間。
*   **重命名 (Rename)**：為變數、方法、類別等程式碼元素提供更清晰、更有意義的名稱。
    *   **用途**: 提高程式碼的可讀性和可理解性。這是最簡單但也最常用的重構手法。
*   **提取類別 (Extract Class)**：當一個類別承擔了過多的職責時，將其中一部分職責移動到一個新的類別中。
    *   **用途**: 遵守單一職責原則 (SRP)，降低類別的複雜度，提高內聚性。

#### 推導：以提取方法為例

**情境**: 一個使用者管理類別中的方法，既負責驗證使用者資料，又負責寫入日誌，還處理資料庫儲存。

**原始程式碼 (C# 示例)**:

```csharp
public class UserManager
{
    public void RegisterUser(string username, string email, string password)
    {
        // 1. 驗證使用者名稱
        if (string.IsNullOrWhiteSpace(username))
        {
            Console.WriteLine("Error: Username cannot be empty.");
            return;
        }
        if (username.Length < 5)
        {
            Console.WriteLine("Error: Username too short.");
            return;
        }

        // 2. 驗證電子郵件
        if (!email.Contains("@") || !email.Contains("."))
        {
            Console.WriteLine("Error: Invalid email format.");
            return;
        }

        // 3. 驗證密碼強度
        if (password.Length < 8)
        {
            Console.WriteLine("Error: Password too weak.");
            return;
        }
        // ... 更多密碼複雜度檢查 ...

        // 4. 寫入日誌
        Console.WriteLine($"[INFO] User registration attempt for {username} - {email}");

        // 5. 儲存到資料庫
        // Assume some database logic here...
        Console.WriteLine($"User {username} registered successfully to DB.");
        Console.WriteLine($"[INFO] User {username} registration successful.");
    }
}
```

**問題分析**: `RegisterUser` 方法太長，包含多個不同職責的邏輯塊 (驗證、日誌、儲存)。

**重構步驟**:

1.  **識別邏輯塊**: 程式碼中可以清晰地分為「驗證使用者名稱」、「驗證電子郵件」、「驗證密碼」、「寫入日誌」和「儲存到資料庫」五個部分。
2.  **提取「驗證使用者名稱」方法**:

    ```csharp
    private bool IsUsernameValid(string username)
    {
        if (string.IsNullOrWhiteSpace(username))
        {
            Console.WriteLine("Error: Username cannot be empty.");
            return false;
        }
        if (username.Length < 5)
        {
            Console.WriteLine("Error: Username too short.");
            return false;
        }
        return true;
    }
    ```
    將原方法中的驗證邏輯替換為 `if (!IsUsernameValid(username)) return;`。

3.  **提取「驗證電子郵件」方法**:

    ```csharp
    private bool IsEmailValid(string email)
    {
        if (!email.Contains("@") || !email.Contains("."))
        {
            Console.WriteLine("Error: Invalid email format.");
            return false;
        }
        return true;
    }
    ```
    替換為 `if (!IsEmailValid(email)) return;`。

4.  **提取「驗證密碼」方法**:

    ```csharp
    private bool IsPasswordStrong(string password)
    {
        if (password.Length < 8)
        {
            Console.WriteLine("Error: Password too weak.");
            return false;
        }
        // ... 更多密碼複雜度檢查 ...
        return true;
    }
    ```
    替換為 `if (!IsPasswordStrong(password)) return;`。

5.  **提取「記錄操作」方法**:

    ```csharp
    private void LogRegistrationAttempt(string username, string email)
    {
        Console.WriteLine($"[INFO] User registration attempt for {username} - {email}");
    }

    private void LogRegistrationSuccess(string username)
    {
        Console.WriteLine($"[INFO] User {username} registration successful.");
    }
    ```
    替換為 `LogRegistrationAttempt(username, email);` 和 `LogRegistrationSuccess(username);`。

6.  **提取「儲存使用者」方法**:

    ```csharp
    private void SaveUserToDatabase(string username, string email, string password)
    {
        // Assume some database logic here...
        Console.WriteLine($"User {username} registered successfully to DB.");
    }
    ```
    替換為 `SaveUserToDatabase(username, email, password);`。

**重構後 (C# 示例)**:

```csharp
public class UserManager
{
    public void RegisterUser(string username, string email, string password)
    {
        if (!IsUsernameValid(username)) return;
        if (!IsEmailValid(email)) return;
        if (!IsPasswordStrong(password)) return;

        LogRegistrationAttempt(username, email);
        SaveUserToDatabase(username, email, password);
        LogRegistrationSuccess(username);
    }

    private bool IsUsernameValid(string username) { /* ... same as above ... */ return true; }
    private bool IsEmailValid(string email) { /* ... same as above ... */ return true; }
    private bool IsPasswordStrong(string password) { /* ... same as above ... */ return true; }
    private void LogRegistrationAttempt(string username, string email) { /* ... same as above ... */ }
    private void LogRegistrationSuccess(string username) { /* ... same as above ... */ }
    private void SaveUserToDatabase(string username, string email, string password) { /* ... same as above ... */ }
}
```

**重構結果**: `RegisterUser` 方法現在非常簡潔，每個提取出來的方法都有清晰的單一職責。這使得程式碼更易讀、易於測試和維護。

-----

## 8.3 設計模式與重構的關聯性

設計模式與重構是軟體開發中兩個密不可分的概念，它們共同協助開發者創造更高品質、更具彈性的軟體系統。

### 8.3.1 協同作用

*   **設計模式是「重構的目標」，重構是「達到目標的手段」**:
    當我們發現程式碼存在「壞味道」，例如重複的條件邏輯，我們可能會考慮將其重構為 `Strategy` 模式。此時，`Strategy` 模式就是重構要達成的目標架構，而一系列的「提取方法」、「取代條件判斷為多型」等重構手法，就是實現這個目標的具體步驟。
*   **重構為設計模式的導入鋪平道路**:
    有時候，程式碼的現有結構可能非常混亂，直接引入一個設計模式會很困難。這時，需要先進行一系列小規模的重構（如提取方法、重命名）來清理程式碼，使其變得更容易理解和修改，為後續導入設計模式創造條件。
*   **設計模式提供「重構的藍圖」**:
    當開發者遇到特定的設計問題時，設計模式為他們提供了一個經過驗證的解決方案藍圖。在重構過程中，這個藍圖可以指導開發者如何組織類別和物件，以達到更好的設計。

### 8.3.2 選擇時機

*   **何時引入設計模式？**
    *   **當遇到特定問題且該模式是已知解決方案時**: 設計模式應該是解決實際問題的工具，而不是為了用而用。例如，當你需要確保一個類別只有一個實例時，考慮 `Singleton`；當你需要讓物件在不修改類別的情況下擁有新功能時，考慮 `Decorator`。
    *   **當程式碼需要更強的彈性、可擴展性或可維護性時**: 設計模式可以幫助你解耦、抽象化、以及管理複雜性。
    *   **在設計初期或重構階段**: 在設計初期考慮設計模式可以避免未來的大量返工；在重構階段，則用於改進現有設計。

*   **何時進行重構？**
    *   **當程式碼品質下降、維護困難、出現壞味道時**: 這是最直接的重構動機。例如，發現長方法、重複程式碼、大類等。
    *   **在新增功能之前**: Martin Fowler 建議「先重構，再添加功能」。透過重構，可以使程式碼更清晰，為新功能的加入提供更穩固的基礎。
    *   **在修復錯誤之前**: 重構可以幫助你更好地理解有問題的程式碼，並在修復錯誤時避免引入新的問題。
    *   **在程式碼審查時**: 程式碼審查是發現壞味道和重構機會的絕佳時機。
    *   **作為持續開發的一部分**: 優秀的團隊會將重構視為日常工作的一部分，不斷地小幅改進程式碼。

### 8.3.3 誤解與正確理解

*   **設計模式不是銀彈，不應過度使用**:
    *   **誤解**: 認為所有程式碼都應該應用設計模式，模式越多越好。
    *   **澄清**: 過度使用設計模式會導致程式碼過於複雜、難以理解，反而降低可維護性。應該根據實際需求和問題的複雜度來選擇是否使用模式，並力求簡潔。
*   **重構不是一次性活動，而是持續改進的過程**:
    *   **誤解**: 認為重構是只有在專案後期或程式碼品質極差時才進行的大規模活動。
    *   **澄清**: 重構應該是小步快跑、頻繁進行的。每次提交程式碼前，都應該對其進行小規模的清理和改進。這就像日常清潔，而不是年終大掃除。
*   **重構不應改變外部行為，測試是重構的安全網**:
    *   **誤解**: 重構就是重寫，可以修改功能。
    *   **澄清**: 重構的核心原則是「不改變外部行為」。為了確保這一點，必須有完善的自動化測試套件。在沒有足夠測試的情況下進行重構是極其危險的。

-----

## 8.4 進階內容：重構工具與自動化

### 8.4.1 IDE 支援

現代的整合開發環境 (IDE) 為重構提供了強大的自動化支援，這極大地提高了重構的效率和安全性。這些工具能夠理解程式碼的語法結構，並在進行重構時自動處理相關的引用和依賴。

*   **常見 IDE 及其重構功能**:
    *   **IntelliJ IDEA (Java, Kotlin 等)**: 以其卓越的重構功能而聞名，幾乎涵蓋了所有常見的重構手法，如 `Rename` (重命名)、`Extract Method` (提取方法)、`Extract Variable` (提取變數)、`Introduce Parameter` (引入參數)、`Move` (移動類別/方法/欄位)、`Change Signature` (改變簽章) 等。它能確保在修改程式碼時，所有引用都會同步更新。
    *   **Visual Studio (C#, VB.NET 等)**: 提供了豐富的重構功能，包括 `Rename`、`Extract Method`、`Encapsulate Field` (封裝欄位)、`Remove Parameters` (移除參數) 等。
    *   **VS Code (多語言，透過擴展)**: 雖然核心功能相對輕量，但透過語言服務和擴展 (如 C# for VS Code, Python, JavaScript/TypeScript 等)，也能提供如 `Rename Symbol` (重命名符號)、`Extract to function/variable` (提取到函式/變數) 等基本重構功能。
    *   **Eclipse (Java)**: 提供了廣泛的重構選項，與 IntelliJ IDEA 類似，涵蓋了大部分常見的重構操作。

*   **例子**:
    在 IntelliJ IDEA 中，如果你選中一段程式碼，按下 `Ctrl + Alt + M` (Windows/Linux) 或 `Cmd + Option + M` (macOS)，IDE 會自動彈出「提取方法」對話框，讓你為新方法命名，並自動處理參數和返回值，然後將選中的程式碼替換為對新方法的調用。這比手動操作安全且高效許多。

### 8.4.2 自動化重構的局限性

雖然 IDE 提供了極大的便利，但自動化重構也有其局限性：

*   **語法層面的重構**: IDE 主要擅長處理語法層面的重構，例如變數重命名、方法提取、移動類別等，這些操作程式碼的結構化改變，工具可以精確地分析和執行。
*   **語義層面的重構仍需人工判斷**:
    *   **設計模式導入**: 將一段 `if-else` 邏輯重構為 `Strategy` 模式，需要人工設計介面、實現具體策略、引入 Context 等，這超出了 IDE 的自動化能力。
    *   **職責劃分**: 判斷一個方法是否「過長」，一個類別是否承擔了「過多職責」，這些都需要開發者的經驗和對業務邏輯的理解。IDE 無法自動判斷程式碼的「壞味道」並自動應用複雜的設計模式。
    *   **程式碼意圖**: 自動化工具無法理解程式碼的「意圖」。例如，雖然可以自動提取方法，但新方法的命名和它的參數設計，以及是否真的應該提取，仍需要人來判斷。

### 8.4.3 持續重構與持續整合 (CI/CD)

為了確保重構的有效性和安全性，並使其成為開發流程的常態，需要將其整合到持續整合/持續部署 (CI/CD) 流程中。

*   **將重構作為開發流程的一部分**:
    *   **小步快跑**: 鼓勵開發者在日常工作中，頻繁進行小規模的重構，而不是等到累積了大量「技術債務」才一次性處理。
    *   **與新功能開發結合**: 在實現新功能或修復 Bug 之前，先重構相關的程式碼，使其更清晰、更容易修改。
*   **如何整合到版本控制與 CI/CD 流程中**:
    1.  **版本控制 (Git)**:
        *   將重構變更視為與功能開發同等重要的變更。
        *   鼓勵在獨立的分支上進行重構，或將重構與功能開發的 commit 分開，以便於審查和回溯。
    2.  **單元測試與整合測試**:
        *   **安全網**: 測試是重構的基石。在每次重構之前，確保有足夠的自動化測試覆蓋重構的程式碼，以驗證重構後外部行為未改變。
        *   **快速回饋**: CI/CD 流程中的自動化測試可以在重構後立即運行，提供快速回饋，指出任何潛在的功能破壞。
    3.  **程式碼審查 (Code Review)**:
        *   在將重構後的程式碼合併到主分支之前，進行程式碼審查。
        *   審查者可以檢查重構是否合理、是否引入了新的問題、是否改善了程式碼品質。
    4.  **靜態程式碼分析工具**:
        *   **自動檢測壞味道**: 整合 SonarQube、ESLint (JavaScript)、Pylint (Python) 等靜態分析工具到 CI/CD 流程中。
        *   這些工具可以自動檢測程式碼中的「壞味道」、潛在 Bug、風格問題等，為開發者提供重構的建議和依據。
        *   可以設定品質閘門 (Quality Gate)，要求程式碼在合併前必須滿足一定的品質標準。
    5.  **小批量提交 (Small Commits)**:
        *   重構應當是小規模、原子性的提交。每次提交只做一件事，要麼是重構，要麼是新增功能。
        *   這使得程式碼審查更容易，也更容易回溯和定位問題。

透過這些整合，重構不再是額外的負擔，而是成為軟體開發生命週期中不可或缺且受保護的一個環節，有助於持續提升軟體品質。

-----

## 8.5 常見錯誤與澄清

### 8.5.1 過度設計與「模式狂熱」

*   **常見錯誤**: 開發者可能因為學習了設計模式而過於熱衷，嘗試在任何地方都應用設計模式，即使問題本身很簡單。這被稱為「模式狂熱」(Pattern Mania) 或「銀彈情結」。
*   **澄清**:
    *   **YAGNI (You Ain't Gonna Need It)**: 不要為尚未發生的需求預先設計複雜的模式。保持簡單，只解決當前的問題。
    *   **KISS (Keep It Simple, Stupid)**: 程式碼越簡單越好。只有當簡單的解決方案不足以應對複雜性或變化時，才考慮引入設計模式。
    *   **設計模式是工具，不是目的**: 設計模式的目的是解決特定的設計問題，提高程式碼品質，而不是為了展示你對模式的了解。過度設計會增加不必要的複雜性，降低可讀性和維護性。

### 8.5.2 將重構與重寫混淆

*   **常見錯誤**: 許多人將重構與「重寫 (Rewrite)」或「改造 (Rearchitect)」混為一談，認為重構意味著可以改變軟體的外部行為，甚至從頭開始寫。
*   **澄清**:
    *   **重構的核心原則是「不改變外部行為」**: 這是重構與重寫的根本區別。重構的目標是改善程式碼的內部結構，使其更易於理解和修改，但使用者感受到的功能必須保持不變。
    *   **重寫是從零開始**: 重寫通常是因為現有系統已經無法修復，需要從頭構建一個新系統，這會改變外部行為，且風險高、成本大。
    *   **測試是關鍵**: 判斷重構是否成功的唯一標準是，在重構前後，所有自動化測試都能通過。沒有測試的「重構」往往就是隱藏錯誤的重寫。

### 8.5.3 缺乏測試下的重構

*   **常見錯誤**: 在沒有足夠自動化測試覆蓋的情況下進行大規模重構。
*   **澄清**:
    *   **測試是重構的「安全網」**: 重構本身是高風險的操作，因為它涉及到對現有程式碼的修改。自動化單元測試和整合測試是確保這些修改不會引入新的錯誤或破壞現有功能的關鍵。
    *   **「綠燈狀態」下的重構**: 理想情況下，應該在所有測試都通過（綠燈）的情況下開始重構，並在每次重構步驟後再次運行測試，確保仍然是綠燈。
    *   **先寫測試，再重構**: 如果沒有足夠的測試，重構的第一步應該是為要重構的程式碼編寫測試，以提供安全保障。

### 8.5.4 一次性大範圍重構

*   **常見錯誤**: 試圖在很長一段時間內進行一次性的大規模重構，例如「重構月」或「重構季」。
*   **澄清**:
    *   **小步快跑，頻繁且小範圍的重構更安全有效**: 大規模重構風險高、難以管理、容易引入新的 Bug，並且會阻礙新功能的開發。
    *   **持續的、日常的重構**: 最佳的重構實踐是將其融入日常開發流程。當你發現一個壞味道時，立即進行小規模重構，而不是將其累積起來。
    *   **容易整合與回溯**: 小規模的重構更容易在版本控制系統中合併，也更容易在出問題時回溯。每次提交只包含少量、明確的變更。

-----

## 8.6 小練習（附詳解）

### 練習一：將重複程式碼重構為策略模式

**情境**：你正在開發一個銷售系統，需要根據不同的商品類型計算不同的運費。目前，計算運費的邏輯都集中在一個方法中，使用 `if-else if` 判斷。

**原始程式碼 (Python 示例)**：

```python
def calculate_shipping_cost(item_type, weight, distance):
    if item_type == "Electronics":
        cost = 50 + (weight * 2) + (distance * 0.5)
        print(f"計算電子產品運費: {cost}")
    elif item_type == "Books":
        cost = 30 + (weight * 1.5) + (distance * 0.3)
        print(f"計算書籍運費: {cost}")
    elif item_type == "Furniture":
        cost = 100 + (weight * 3) + (distance * 0.8)
        print(f"計算家具運費: {cost}")
    else:
        cost = 20 + (weight * 1) + (distance * 0.2) # 默認運費
        print(f"計算默認產品運費: {cost}")
    return cost

# 測試
print(f"電子產品運費: {calculate_shipping_cost('Electronics', 10, 100)}")
print(f"書籍運費: {calculate_shipping_cost('Books', 5, 50)}")
print(f"家具運費: {calculate_shipping_cost('Furniture', 50, 200)}")
print(f"服裝運費: {calculate_shipping_cost('Apparel', 2, 30)}")
```

**問題**：
1.  `calculate_shipping_cost` 方法過於冗長。
2.  每次新增一種商品類型，都需要修改此方法，違反了開放/封閉原則。
3.  測試不同商品類型的運費計算較為困難。

**目標**：將這些運費計算邏輯抽象化，使用策略模式進行重構。

**步驟**：

1.  **定義運費計算策略介面 (或抽象基類)**。
2.  **為每種商品類型創建具體策略類別**，實作運費計算邏輯。
3.  **創建一個 Context (上下文) 類別**，用於持有和執行運費計算策略。
4.  **修改原始方法或其調用者**，使用 Context 類別和策略。

---

**詳解**：

1.  **定義策略介面 (或抽象基類)**：
    ```python
    from abc import ABC, abstractmethod

    class ShippingStrategy(ABC):
        @abstractmethod
        def calculate(self, weight: float, distance: float) -> float:
            pass
    ```

2.  **為每種商品類型創建具體策略類別**：
    ```python
    class ElectronicsShipping(ShippingStrategy):
        def calculate(self, weight: float, distance: float) -> float:
            cost = 50 + (weight * 2) + (distance * 0.5)
            print(f"計算電子產品運費: {cost}")
            return cost

    class BooksShipping(ShippingStrategy):
        def calculate(self, weight: float, distance: float) -> float:
            cost = 30 + (weight * 1.5) + (distance * 0.3)
            print(f"計算書籍運費: {cost}")
            return cost

    class FurnitureShipping(ShippingStrategy):
        def calculate(self, weight: float, distance: float) -> float:
            cost = 100 + (weight * 3) + (distance * 0.8)
            print(f"計算家具運費: {cost}")
            return cost

    class DefaultShipping(ShippingStrategy):
        def calculate(self, weight: float, distance: float) -> float:
            cost = 20 + (weight * 1) + (distance * 0.2)
            print(f"計算默認產品運費: {cost}")
            return cost
    ```

3.  **創建一個 Context (上下文) 類別**：
    ```python
    class ShippingContext:
        def __init__(self, strategy: ShippingStrategy):
            self._strategy = strategy

        def set_strategy(self, strategy: ShippingStrategy):
            self._strategy = strategy

        def get_shipping_cost(self, weight: float, distance: float) -> float:
            return self._strategy.calculate(weight, distance)
    ```

4.  **修改原始方法或其調用者 (通常我們會創建一個工廠來選擇策略)**：
    ```python
    class ShippingStrategyFactory:
        @staticmethod
        def get_strategy(item_type: str) -> ShippingStrategy:
            if item_type == "Electronics":
                return ElectronicsShipping()
            elif item_type == "Books":
                return BooksShipping()
            elif item_type == "Furniture":
                return FurnitureShipping()
            else:
                return DefaultShipping()

    # 使用新的方式計算運費
    def calculate_shipping_cost_refactored(item_type, weight, distance):
        strategy = ShippingStrategyFactory.get_strategy(item_type)
        context = ShippingContext(strategy)
        return context.get_shipping_cost(weight, distance)

    print("\n--- 重構後測試 ---")
    print(f"電子產品運費: {calculate_shipping_cost_refactored('Electronics', 10, 100)}")
    print(f"書籍運費: {calculate_shipping_cost_refactored('Books', 5, 50)}")
    print(f"家具運費: {calculate_shipping_cost_refactored('Furniture', 50, 200)}")
    print(f"服裝運費: {calculate_shipping_cost_refactored('Apparel', 2, 30)}")
    ```

**重構結果**：
*   `calculate_shipping_cost_refactored` 方法變得非常簡潔，其職責只是選擇正確的策略並執行。
*   新增新的商品類型運費時，只需要新增一個 `ShippingStrategy` 的實現類別，並在 `ShippingStrategyFactory` 中新增一個判斷分支即可，而不需要修改核心邏輯，符合開放/封閉原則。
*   每個運費計算邏輯現在都在各自的類別中，更容易單獨測試。

-----

### 練習二：提取方法與重新命名

**情境**：你正在處理一個訂單報告生成的方法，它執行多個步驟：從資料庫獲取資料、計算統計數據、格式化報告頭部、生成報告內容，最後將報告輸出到文件。這個方法很長，且內部變數命名不夠清晰。

**原始程式碼 (Java 示例)**：

```java
public class OrderReportGenerator {

    public void generateDailyReport(String date) {
        System.out.println("Starting report generation for " + date);

        // Part 1: Fetch data from database
        List<Order> ords = new ArrayList<>();
        // Simulate fetching orders
        if (date.equals("2023-10-26")) {
            ords.add(new Order("A001", 100.0));
            ords.add(new Order("A002", 150.0));
        } else {
            ords.add(new Order("B001", 200.0));
        }
        System.out.println("Fetched " + ords.size() + " orders.");

        // Part 2: Calculate statistics
        double tot = 0;
        int num = 0;
        for (Order o : ords) {
            tot += o.getAmount();
            num++;
        }
        double avg = (num > 0) ? tot / num : 0;
        System.out.println("Calculated total: " + tot + ", average: " + avg);

        // Part 3: Format report header
        StringBuilder sb = new StringBuilder();
        sb.append("===== Daily Order Report for ").append(date).append(" =====\n");
        sb.append("Total Orders: ").append(num).append("\n");
        sb.append("Total Revenue: ").append(String.format("%.2f", tot)).append("\n");
        sb.append("Average Order Value: ").append(String.format("%.2f", avg)).append("\n");
        sb.append("--------------------------------------------------\n");
        System.out.println("Formatted report header.");

        // Part 4: Generate report body
        for (Order o : ords) {
            sb.append("Order ID: ").append(o.getOrderId()).append(", Amount: ").append(String.format("%.2f", o.getAmount())).append("\n");
        }
        System.out.println("Generated report body.");

        // Part 5: Output to file (simulate)
        String rptCnt = sb.toString();
        System.out.println("Report Content:\n" + rptCnt);
        System.out.println("Report generation finished.");
    }

    // Assume Order class exists
    private static class Order {
        String orderId;
        double amount;
        public Order(String orderId, double amount) {
            this.orderId = orderId;
            this.amount = amount;
        }
        public String getOrderId() { return orderId; }
        public double getAmount() { return amount; }
    }
}
```

**問題**：
1.  `generateDailyReport` 方法過長，包含多個不相關的任務。
2.  變數命名不夠描述性 (例如 `ords`, `tot`, `num`, `sb`, `rptCnt`)。
3.  難以測試單一邏輯塊，如統計計算或報告格式化。

**目標**：拆分方法，改善命名，提高可讀性、可維護性和可測試性。

**步驟**：

1.  **識別方法內的邏輯塊**，並考慮它們的職責。
2.  **使用「提取方法」重構**每個邏輯塊。
3.  **改善新的方法名、參數名和變數名**，使其更具描述性。
4.  （可選）為統計數據創建一個專門的數據傳輸物件 (DTO)。

---

**詳解**：

1.  **識別邏輯塊**:
    *   獲取訂單資料
    *   計算訂單統計數據
    *   格式化報告頭部
    *   生成報告內容 (每一條訂單的細節)
    *   輸出報告

2.  **為統計數據創建 DTO** (輔助步驟，提高可讀性)：

    ```java
    public class OrderStatistics {
        public double totalRevenue;
        public int totalOrders;
        public double averageOrderValue;

        public OrderStatistics(double totalRevenue, int totalOrders, double averageOrderValue) {
            this.totalRevenue = totalRevenue;
            this.totalOrders = totalOrders;
            this.averageOrderValue = averageOrderValue;
        }
    }
    ```

3.  **提取方法並改善命名**:

    ```java
    import java.util.ArrayList;
    import java.util.List;

    public class OrderReportGeneratorRefactored {

        public void generateDailyReport(String date) {
            System.out.println("Starting report generation for " + date);

            List<Order> orders = fetchOrdersFromDatabase(date);
            OrderStatistics statistics = calculateOrderStatistics(orders);
            String reportContent = formatReport(date, orders, statistics);
            outputReportToFile(reportContent);

            System.out.println("Report generation finished.");
        }

        private List<Order> fetchOrdersFromDatabase(String date) {
            List<Order> fetchedOrders = new ArrayList<>();
            // Simulate fetching orders
            if (date.equals("2023-10-26")) {
                fetchedOrders.add(new Order("A001", 100.0));
                fetchedOrders.add(new Order("A002", 150.0));
            } else {
                fetchedOrders.add(new Order("B001", 200.0));
            }
            System.out.println("Fetched " + fetchedOrders.size() + " orders for date " + date + ".");
            return fetchedOrders;
        }

        private OrderStatistics calculateOrderStatistics(List<Order> orders) {
            double totalRevenue = 0;
            int totalOrders = 0;
            for (Order order : orders) {
                totalRevenue += order.getAmount();
                totalOrders++;
            }
            double averageOrderValue = (totalOrders > 0) ? totalRevenue / totalOrders : 0;
            System.out.println("Calculated total revenue: " + totalRevenue + ", average order value: " + averageOrderValue);
            return new OrderStatistics(totalRevenue, totalOrders, averageOrderValue);
        }

        private String formatReport(String date, List<Order> orders, OrderStatistics statistics) {
            StringBuilder reportBuilder = new StringBuilder();
            
            // Format header
            reportBuilder.append(formatReportHeader(date, statistics));
            
            // Generate body
            reportBuilder.append(formatReportBody(orders));

            System.out.println("Formatted report content.");
            return reportBuilder.toString();
        }

        private String formatReportHeader(String date, OrderStatistics statistics) {
            StringBuilder headerBuilder = new StringBuilder();
            headerBuilder.append("===== Daily Order Report for ").append(date).append(" =====\n");
            headerBuilder.append("Total Orders: ").append(statistics.totalOrders).append("\n");
            headerBuilder.append("Total Revenue: ").append(String.format("%.2f", statistics.totalRevenue)).append("\n");
            headerBuilder.append("Average Order Value: ").append(String.format("%.2f", statistics.averageOrderValue)).append("\n");
            headerBuilder.append("--------------------------------------------------\n");
            System.out.println("Formatted report header.");
            return headerBuilder.toString();
        }

        private String formatReportBody(List<Order> orders) {
            StringBuilder bodyBuilder = new StringBuilder();
            for (Order order : orders) {
                bodyBuilder.append("Order ID: ").append(order.getOrderId()).append(", Amount: ").append(String.format("%.2f", order.getAmount())).append("\n");
            }
            System.out.println("Generated report body.");
            return bodyBuilder.toString();
        }

        private void outputReportToFile(String reportContent) {
            // Simulate writing to file
            System.out.println("Report Content:\n" + reportContent);
            // File I/O logic would go here
            System.out.println("Report outputted to file (simulated).");
        }

        // Assume Order class exists
        private static class Order {
            String orderId;
            double amount;
            public Order(String orderId, double amount) {
                this.orderId = orderId;
                this.amount = amount;
            }
            public String getOrderId() { return orderId; }
            public double getAmount() { return amount; }
        }

        // OrderStatistics DTO as defined above
        private static class OrderStatistics {
            public double totalRevenue;
            public int totalOrders;
            public double averageOrderValue;

            public OrderStatistics(double totalRevenue, int totalOrders, double averageOrderValue) {
                this.totalRevenue = totalRevenue;
                this.totalOrders = totalOrders;
                this.averageOrderValue = averageOrderValue;
            }
        }

        public static void main(String[] args) {
            OrderReportGeneratorRefactored generator = new OrderReportGeneratorRefactored();
            generator.generateDailyReport("2023-10-26");
            System.out.println("\n--- Another day ---");
            generator.generateDailyReport("2023-10-27");
        }
    }
    ```

**重構結果**：
*   `generateDailyReport` 方法現在非常短，清晰地展示了生成報告的各個高層次步驟，提高了可讀性。
*   每個提取出來的方法（如 `fetchOrdersFromDatabase`, `calculateOrderStatistics` 等）都有明確的單一職責，且命名清晰，內部變數也使用了描述性名稱。
*   現在可以更容易地對 `calculateOrderStatistics` 或 `formatReportHeader` 等獨立邏輯塊進行單元測試。
*   程式碼的可維護性和可擴展性都得到了顯著提升。

-----

## 8.7 延伸閱讀/參考

*   **設計模式經典**
    *   **《設計模式：可再用物件導向軟體的要素》(Design Patterns: Elements of Reusable Object-Oriented Software)** by Erich Gamma, Richard Helm, Ralph Johnson, John Vlissides (GoF)
        *   設計模式領域的開山之作，定義了 23 個經典的設計模式。所有學習設計模式的人都應閱讀。

*   **重構經典**
    *   **《重構：改善既有程式碼的設計》(Refactoring: Improving the Design of Existing Code)** by Martin Fowler
        *   重構領域的聖經，詳細解釋了重構的動機、原則、各種手法及其應用時機，強調測試的重要性。第二版 (2018) 更新了 JavaScrip/Python 範例，更貼近現代開發。
    *   **《Clean Code：軟體程式碼品質的實踐之道》(Clean Code: A Handbook of Agile Software Craftsmanship)** by Robert C. Martin (Uncle Bob)
        *   雖然不完全是關於重構，但書中大量闡述了什麼是「好程式碼」以及如何寫出「好程式碼」，這直接引導了重構的需求和目標。

*   **其他相關資源**
    *   **《Head First Design Patterns》** by Eric Freeman, Elisabeth Robson, Bert Bates, Kathy Sierra
        *   以生動活潑的方式介紹設計模式，非常適合初學者。
    *   **《Agile Software Development, Principles, Patterns, and Practices》** by Robert C. Martin (Uncle Bob)
        *   探討了敏捷開發原則、SOLID 原則、設計模式如何整合到軟體開發中。

*   **線上資源**
    *   **Refactoring.Guru**: 一個優秀的網站，提供了 GoF 設計模式和許多重構手法的詳細解釋、UML 圖和程式碼範例。
    *   **Wikipedia**: 搜尋 "Design Patterns" 或 "Code Refactoring" 可以獲得概覽和相關連結。
    *   **各大技術部落格和社群**: 許多開發者會分享他們在設計模式和重構方面的經驗和見解。