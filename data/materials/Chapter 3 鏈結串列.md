# Chapter 3 鏈結串列

-----

### 什麼是鏈結串列？

鏈結串列（Linked List）是一種常見的線性資料結構。與陣列不同，它在記憶體中不是連續儲存的。鏈結串列由一系列稱為「節點」（Node）的獨立元素組成，每個節點都包含資料本身，以及一個指向下一個節點的「指標」（Pointer）或「參考」（Reference）。

#### 核心概念：節點 (Node)

每個節點是鏈結串列的基本單位。一個典型的節點至少包含以下兩個部分：
1.  **資料欄位 (Data Field)**：儲存節點的實際數據。
2.  **指標欄位 (Pointer/Reference Field)**：儲存指向鏈結串列中下一個節點的記憶體位址。在單向鏈結串列中，這是指向下一個節點的指標；在雙向鏈結串列中，會有指向前一個和下一個節點的兩個指標。

#### 鏈結串列的結構

鏈結串列通常由一個「頭節點」（Head Node）開始，這個頭節點指向串列中的第一個實際資料節點。如果鏈結串列是空的，頭節點通常指向空（`NULL` 或 `nullptr`）。串列的最後一個節點，其指標欄位會指向空，表示串列的結束。

#### 與陣列的關聯與差異

| 特性           | 鏈結串列                                 | 陣列                                     |
| :------------- | :--------------------------------------- | :--------------------------------------- |
| **記憶體配置** | 非連續，透過指標連結                       | 連續，依索引存取                         |
| **大小**       | 動態調整，可隨時擴展或縮小                 | 固定大小（除非使用動態陣列），需預先定義 |
| **插入/刪除**  | O(1)（若已知位置），O(N)（若需搜尋）     | O(N)（因為需要移動後續元素）           |
| **隨機存取**   | O(N)（需要從頭遍歷）                     | O(1)（直接透過索引存取）               |
| **空間利用**   | 彈性，但需額外空間儲存指標                 | 緊湊，但可能會有空間浪費（未滿或不足）   |

-----

### 鏈結串列的類型

根據節點中指標的數量和指向方式，鏈結串列可以分為以下幾種主要類型：

#### 1. 單向鏈結串列 (Singly Linked List)

*   **定義：** 每個節點只包含一個指向下一個節點的指標。
*   **結構：** `Node { data, next_pointer }`
*   **特性：**
    *   只能從頭部開始向後遍歷。
    *   插入和刪除操作需要追蹤前一個節點，才能修改指標。
    *   在已知前一個節點的情況下，插入和刪除是高效的。
*   **示意圖：**
    `Head -> [Data|Next] -> [Data|Next] -> [Data|Next] -> NULL`

#### 2. 雙向鏈結串列 (Doubly Linked List)

*   **定義：** 每個節點包含兩個指標：一個指向前一個節點，另一個指向下一個節點。
*   **結構：** `Node { data, prev_pointer, next_pointer }`
*   **特性：**
    *   可以從頭部向後遍歷，也可以從尾部向前遍歷。
    *   插入和刪除操作更為方便，因為可以輕鬆找到前一個和後一個節點。
    *   相比單向鏈結串列，每個節點需要額外的記憶體來儲存 `prev_pointer`。
*   **示意圖：**
    `Head <-> [Data|Prev|Next] <-> [Data|Prev|Next] <-> [Data|Prev|Next] <-> NULL`

#### 3. 環狀鏈結串列 (Circular Linked List)

*   **定義：** 鏈結串列的最後一個節點的 `next_pointer` 指向頭節點，形成一個環。可以是單向環狀或雙向環狀。
*   **結構：** `Node { data, next_pointer }` (單向環狀)，最後節點的 `next` 指向 `Head`。
*   **特性：**
    *   從任何節點開始都可以遍歷整個串列。
    *   沒有明確的「尾部」，遍歷時需要判斷是否回到起始點。
    *   常用於實作緩衝區、多工處理中的排程器。
*   **示意圖 (單向環狀)：**
    `Head -> [Data|Next] -> [Data|Next] -> ... -> [Data|Next] --^`
    `                                                      |_____|`

-----

### 鏈結串列的基本操作

以下以單向鏈結串列為例，說明其主要操作：

#### 1. 初始化 (Initialization)

建立一個空的鏈結串列，通常只需將 `head` 指標設定為 `NULL`。

```cpp
struct Node {
    int data;
    Node* next;
};

Node* head = nullptr; // 創建一個空的鏈結串列
```

#### 2. 遍歷鏈結串列 (Traversal)

從 `head` 節點開始，依序跟隨 `next_pointer` 訪問每個節點，直到遇到 `NULL`。

```cpp
void traverse(Node* head) {
    Node* current = head;
    while (current != nullptr) {
        // 訪問 current->data
        std::cout << current->data << " ";
        current = current->next;
    }
    std::cout << std::endl;
}
```

#### 3. 插入節點 (Insertion)

插入操作根據位置不同分為幾種情況：

*   **在頭部插入 (Insert at Head)：**
    1.  建立新節點。
    2.  將新節點的 `next` 指向目前的 `head`。
    3.  更新 `head` 指向新節點。

    ```cpp
    void insertAtHead(Node*& head, int newData) {
        Node* newNode = new Node;
        newNode->data = newData;
        newNode->next = head; // 新節點指向原來的頭節點
        head = newNode;       // 頭節點更新為新節點
    }
    ```

*   **在尾部插入 (Insert at Tail)：**
    1.  建立新節點，其 `next` 指向 `NULL`。
    2.  如果串列為空，新節點成為 `head`。
    3.  否則，遍歷到最後一個節點，將其 `next` 指向新節點。

    ```cpp
    void insertAtTail(Node*& head, int newData) {
        Node* newNode = new Node;
        newNode->data = newData;
        newNode->next = nullptr; // 新節點將是最後一個，所以指向空

        if (head == nullptr) { // 如果串列是空的
            head = newNode;
            return;
        }

        Node* current = head;
        while (current->next != nullptr) { // 找到最後一個節點
            current = current->next;
        }
        current->next = newNode; // 最後一個節點指向新節點
    }
    ```

*   **在指定節點後插入 (Insert After a Specific Node)：**
    1.  建立新節點。
    2.  將新節點的 `next` 指向 `prevNode->next`。
    3.  將 `prevNode->next` 指向新節點。
    *   **關聯：** 這個操作在雙向鏈結串列中更為簡單，因為可以直接修改 `prevNode` 和 `newNode` 之間的 `prev` 和 `next` 指標。

    ```cpp
    void insertAfter(Node* prevNode, int newData) {
        if (prevNode == nullptr) { // 檢查前一個節點是否存在
            std::cout << "前一個節點不能為空。" << std::endl;
            return;
        }

        Node* newNode = new Node;
        newNode->data = newData;
        newNode->next = prevNode->next; // 新節點指向 prevNode 的下一個節點
        prevNode->next = newNode;       // prevNode 指向新節點
    }
    ```

#### 4. 刪除節點 (Deletion)

刪除操作同樣根據位置和值有不同處理：

*   **刪除頭部節點 (Delete Head Node)：**
    1.  如果串列為空，直接返回。
    2.  儲存目前 `head` 的指標。
    3.  更新 `head` 指向原 `head` 的 `next`。
    4.  釋放原 `head` 節點的記憶體。

    ```cpp
    void deleteHead(Node*& head) {
        if (head == nullptr) {
            return;
        }
        Node* temp = head; // 暫存目前的頭節點
        head = head->next; // 頭節點移到下一個
        delete temp;       // 釋放原頭節點的記憶體
    }
    ```

*   **刪除指定節點 (Delete a Specific Node by Value)：**
    1.  如果串列為空，返回。
    2.  如果目標是 `head` 節點，處理方式同「刪除頭部」。
    3.  遍歷串列，找到目標節點及其前一個節點。
    4.  將前一個節點的 `next` 指向目標節點的 `next`。
    5.  釋放目標節點的記憶體。

    ```cpp
    void deleteNodeByValue(Node*& head, int targetData) {
        if (head == nullptr) {
            return;
        }

        // 如果要刪除的是頭節點
        if (head->data == targetData) {
            Node* temp = head;
            head = head->next;
            delete temp;
            return;
        }

        Node* current = head;
        Node* prev = nullptr;

        // 找到目標節點和其前一個節點
        while (current != nullptr && current->data != targetData) {
            prev = current;
            current = current->next;
        }

        if (current == nullptr) { // 未找到目標節點
            std::cout << "未找到要刪除的節點: " << targetData << std::endl;
            return;
        }

        // 跳過 current 節點
        prev->next = current->next;
        delete current; // 釋放目標節點
    }
    ```

#### 5. 搜尋節點 (Search)

從 `head` 開始遍歷串列，比較每個節點的資料與目標值，直到找到或遍歷結束。

```cpp
Node* search(Node* head, int targetData) {
    Node* current = head;
    while (current != nullptr) {
        if (current->data == targetData) {
            return current; // 找到目標節點
        }
        current = current->next;
    }
    return nullptr; // 未找到
}
```

-----

### 鏈結串列與陣列的比較

這部分已在「什麼是鏈結串列？」中初步提及，此處進行更詳細的總結和應用場景分析。

*   **記憶體配置：** 陣列在記憶體中是連續儲存的，而鏈結串列節點是分散儲存的。這使得陣列在快取命中率上通常優於鏈結串列。
*   **大小彈性：** 鏈結串列的大小是動態的，可以根據需要增長或縮小，避免了陣列固定大小的限制和潛在的空間浪費或不足。
*   **插入/刪除效率：**
    *   在陣列中，插入或刪除元素通常需要移動後續所有元素來保持連續性，時間複雜度為 $O(N)$。
    *   在鏈結串列中，一旦找到插入/刪除點，只需修改幾個指標即可，時間複雜度為 $O(1)$。但如果需要搜尋特定值才能找到插入/刪除點，則搜尋本身的 $O(N)$ 時間複雜度仍會佔主導。
*   **隨機存取：** 陣列可以透過索引 $O(1)$ 時間內直接存取任何元素。鏈結串列不支援隨機存取，必須從頭部開始遍歷，時間複雜度為 $O(N)$。
*   **空間開銷：** 鏈結串列的每個節點都需要額外的空間來儲存指標。當資料量很大或資料本身很小時，指標的開銷可能顯著。

**應用場景選擇依據：**
*   當需要頻繁在中間位置進行插入和刪除操作，且對隨機存取要求不高時，鏈結串列是更好的選擇（如實現佇列、堆疊、撤銷/重做功能）。
*   當需要頻繁隨機存取，且資料大小相對固定時，陣列更為合適（如表格資料、圖片像素）。
*   當記憶體有限且需要精確控制記憶體分配時，鏈結串列的動態性很有優勢。

-----

### 小練習（附詳解）

#### 練習一：實現單向鏈結串列的插入與遍歷

請實作一個 C++ 程式，定義 `Node` 結構，並包含以下功能：
1.  `insertAtHead(Node*& head, int data)`: 在鏈結串列頭部插入一個節點。
2.  `printList(Node* head)`: 遍歷並印出鏈結串列的所有元素。
3.  在 `main` 函數中，建立一個空的鏈結串列，連續插入幾個數字 (例如 10, 20, 30, 40) 到頭部，然後印出鏈結串列。

**詳解：**

```cpp
#include <iostream>

// 節點結構
struct Node {
    int data;
    Node* next;

    // 構造函數方便初始化
    Node(int val) : data(val), next(nullptr) {}
};

// 在鏈結串列頭部插入節點
void insertAtHead(Node*& head, int data) {
    Node* newNode = new Node(data); // 創建新節點
    newNode->next = head;           // 新節點指向原來的頭節點
    head = newNode;                 // 更新頭節點為新節點
}

// 遍歷並印出鏈結串列
void printList(Node* head) {
    Node* current = head;
    while (current != nullptr) {
        std::cout << current->data << " -> ";
        current = current->next;
    }
    std::cout << "NULL" << std::endl;
}

int main() {
    Node* head = nullptr; // 初始化一個空的鏈結串列

    // 在頭部插入節點
    std::cout << "在頭部插入 10..." << std::endl;
    insertAtHead(head, 10);
    printList(head); // 輸出: 10 -> NULL

    std::cout << "在頭部插入 20..." << std::endl;
    insertAtHead(head, 20);
    printList(head); // 輸出: 20 -> 10 -> NULL

    std::cout << "在頭部插入 30..." << std::endl;
    insertAtHead(head, 30);
    printList(head); // 輸出: 30 -> 20 -> 10 -> NULL

    std::cout << "在頭部插入 40..." << std::endl;
    insertAtHead(head, 40);
    printList(head); // 輸出: 40 -> 30 -> 20 -> 10 -> NULL

    // 釋放記憶體，防止記憶體洩漏
    Node* current = head;
    while (current != nullptr) {
        Node* nextNode = current->next;
        delete current;
        current = nextNode;
    }
    head = nullptr;

    return 0;
}
```

-----

#### 練習二：反轉鏈結串列

請實作一個函數 `reverseList(Node* head)`，它接收一個單向鏈結串列的頭節點，並返回反轉後的鏈結串列的新頭節點。

**詳解：**

要反轉鏈結串列，我們需要遍歷原始串列，並在每個節點將其 `next` 指標指向其前一個節點。這需要三個指標來完成：
1.  `prev`: 指向反轉後的串列的頭部，初始為 `NULL`。
2.  `current`: 指向當前正在處理的節點，初始為原始串列的 `head`。
3.  `next_node`: 暫存 `current` 的下一個節點，以便在 `current->next` 被修改後仍然能繼續遍歷。

**步驟：**
1.  初始化 `prev = nullptr`，`current = head`。
2.  當 `current` 不為 `nullptr` 時，重複以下步驟：
    a.  儲存 `current->next` 到 `next_node`。
    b.  將 `current->next` 指向 `prev`（完成反轉）。
    c.  將 `prev` 移到 `current`（`prev = current`）。
    d.  將 `current` 移到 `next_node`（`current = next_node`）。
3.  迴圈結束後，`prev` 將指向反轉後鏈結串列的新頭節點，返回 `prev`。

```cpp
#include <iostream>

struct Node {
    int data;
    Node* next;
    Node(int val) : data(val), next(nullptr) {}
};

void insertAtTail(Node*& head, int data) {
    Node* newNode = new Node(data);
    if (head == nullptr) {
        head = newNode;
        return;
    }
    Node* current = head;
    while (current->next != nullptr) {
        current = current->next;
    }
    current->next = newNode;
}

void printList(Node* head) {
    Node* current = head;
    while (current != nullptr) {
        std::cout << current->data << " -> ";
        current = current->next;
    }
    std::cout << "NULL" << std::endl;
}

// 反轉鏈結串列的函數
Node* reverseList(Node* head) {
    Node* prev = nullptr;
    Node* current = head;
    Node* next_node = nullptr;

    while (current != nullptr) {
        next_node = current->next; // 1. 儲存下一個節點
        current->next = prev;      // 2. 將當前節點的指標指向前一個節點 (反轉)
        prev = current;            // 3. 移動 prev 到當前節點
        current = next_node;       // 4. 移動 current 到下一個節點
    }
    return prev; // prev 現在是反轉後鏈結串列的新頭節點
}

int main() {
    Node* head = nullptr; // 初始化一個空的鏈結串列

    // 建立一個鏈結串列: 1 -> 2 -> 3 -> 4 -> NULL
    insertAtTail(head, 1);
    insertAtTail(head, 2);
    insertAtTail(head, 3);
    insertAtTail(head, 4);

    std::cout << "原始鏈結串列: ";
    printList(head); // 輸出: 1 -> 2 -> 3 -> 4 -> NULL

    head = reverseList(head); // 反轉鏈結串列

    std::cout << "反轉後鏈結串列: ";
    printList(head); // 輸出: 4 -> 3 -> 2 -> 1 -> NULL

    // 釋放記憶體
    Node* current = head;
    while (current != nullptr) {
        Node* nextNode = current->next;
        delete current;
        current = nextNode;
    }
    head = nullptr;

    return 0;
}
```

-----

### 常見錯誤與澄清

1.  **空指標處理 (`nullptr` / `None`)：** 在執行任何操作（遍歷、插入、刪除）前，務必檢查 `head` 或當前節點是否為 `nullptr`。忘記檢查可能導致程式崩潰（Dereferencing a null pointer）。
2.  **邊界條件（Boundary Conditions）：**
    *   **空串列：** 處理 `head == nullptr` 的情況。
    *   **單一節點串列：** 確保操作後仍然正確。
    *   **頭部/尾部操作：** 特殊情況處理，尤其是在刪除操作中。
3.  **指標指向錯誤：**
    *   **遺失節點：** 插入時如果沒有正確地將新節點鏈結到串列中，可能會導致部分串列遺失。
    *   **懸空指標（Dangling Pointer）：** 刪除節點後，如果其他指標仍然指向被刪除的記憶體位置，但該記憶體已被釋放或重新分配，可能導致未定義行為。
    *   **未更新 `head`：** 當在頭部進行插入或刪除操作時，`head` 指標需要被更新，否則串列的起點會不正確。
4.  **記憶體洩漏（Memory Leak）：** 在 C/C++ 等需要手動管理記憶體的語言中，每次 `new` 一個節點後，當該節點不再被使用時，必須 `delete` 它以釋放記憶體。特別是在刪除操作或程式結束時，需要遍歷並釋放所有節點。

-----

### 延伸閱讀

*   **XOR Linked List (異或鏈結串列)：** 一種記憶體最佳化的雙向鏈結串列。每個節點只儲存一個位址欄位，該欄位是前一個節點和下一個節點位址的異或運算結果。這減少了每個節點的指標數量，但代價是遍歷更複雜。
*   **Skip List (跳躍串列)：** 一種基於鏈結串列的資料結構，通過在多層鏈結串列中添加「跳躍」指標，實現了平均 $O(\log N)$ 的搜尋、插入和刪除時間複雜度，與平衡二元搜尋樹相媲美，但實現起來通常更簡單。
*   **垃圾回收與鏈結串列：** 在支援垃圾回收（如 Java, Python）的語言中，記憶體管理由系統自動處理，開發者無需手動 `delete` 節點。這簡化了程式碼，但理解其工作原理對於性能最佳化仍然很重要。
*   **其他資料結構實現：** 鏈結串列是許多其他資料結構（如堆疊、佇列、圖的鄰接表）的基礎構件，深入理解其原理有助於理解這些進階結構。