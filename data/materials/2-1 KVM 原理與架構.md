# 主題：2-1 KVM 原理與架構

-----

### 1. 核心概念與定義

#### 什麼是虛擬化？
*   **核心觀念：** 虛擬化是一種技術，允許在單一實體硬體上運行多個獨立的作業系統（稱為「虛擬機」或「Guest OS」）。它透過抽象化底層硬體資源，為每個虛擬機提供一個獨立的虛擬硬體環境，使它們認為自己擁有專屬的硬體。
*   **例子：** 想像你有一台強大的電腦，但你既想運行 Windows 軟體，又想體驗 Linux 環境。虛擬化技術可以讓你同時在同一台電腦上安裝並運行 Windows 和 Linux，而無需重啟電腦或分割硬碟。
*   **與相鄰概念的關聯：** 虛擬化是雲端運算、資料中心整合和軟體開發測試環境的基石。它是 Hypervisor 技術的實作目標。

#### 什麼是 Hypervisor (虛擬機器監視器)？
*   **核心觀念：** Hypervisor 是一種軟體、韌體或硬體，用於建立和運行虛擬機。它負責管理虛擬機對實體硬體的訪問，並確保各虛擬機之間的隔離。
*   **類型：**
    *   **Type-1 (裸機型/原生型 Hypervisor)：** 直接運行在實體硬體上，位於作業系統之下。它對硬體有完全的控制權，效能通常較高。
        *   **例子：** VMware ESXi, Microsoft Hyper-V, Xen。KVM 嚴格來說是一種 Type-2 Hypervisor 的核心模組，但其性能接近 Type-1，常被視為介於兩者之間或類 Type-1。
    *   **Type-2 (託管型 Hypervisor)：** 作為傳統作業系統上的應用程式運行。它依賴主機作業系統來管理硬體資源。
        *   **例子：** Oracle VirtualBox, VMware Workstation。KVM 在其架構中，KVM 模組是 Type-1 的功能，但需要 Linux 作業系統作為 Host OS 來提供完整的環境，因此可以說它是利用 Linux 核心實現 Type-1 功能的一種特殊 Type-2 協作模式。
*   **與相鄰概念的關聯：** Hypervisor 是實現虛擬化的核心元件。KVM 就是 Linux 核心中的一個 Hypervisor 模組。

#### 什麼是 KVM？
*   **核心觀念：** KVM (Kernel-based Virtual Machine) 是一個針對 Linux 的開源虛擬化解決方案。它將 Linux 核心轉變為一個 Type-1 (或稱類 Type-1) Hypervisor，允許 Linux 系統作為主機來運行多個虛擬機。KVM 本身是一個 Linux 核心模組 (`kvm.ko`)，它利用了現代處理器提供的硬體虛擬化擴展功能 (Intel VT-x 或 AMD-V)。
*   **例子：** 當你在 Ubuntu 或 CentOS 上使用 KVM 建立虛擬機時，實際上是透過 QEMU 等工具呼叫 KVM 核心模組的功能來運行虛擬機。
*   **與相鄰概念的關聯：** KVM 是實現 Linux 上高效能虛擬化的關鍵，它與 QEMU、Libvirt 等工具緊密協作，共同構成完整的虛擬化堆疊。

#### CPU 硬體輔助虛擬化技術 (Intel VT-x / AMD-V)
*   **核心觀念：** 為了提高虛擬化效率和安全性，現代處理器內建了專門的硬體擴展，如 Intel 的 VT-x (Virtualization Technology) 和 AMD 的 AMD-V (AMD Virtualization)。這些技術允許 Hypervisor 直接在硬體層面管理虛擬機的特權指令和記憶體訪問，從而減少了傳統軟體虛擬化中的效能開銷。
*   **推導：** 在沒有硬體輔助虛擬化的時代，Hypervisor 必須模擬或截獲虛擬機的特權指令，這會導致大量的「VM Exit」（從虛擬機模式切換到 Hypervisor 模式）和「VM Entry」（從 Hypervisor 模式切換回虛擬機模式）開銷。硬體虛擬化技術引入了新的 CPU 操作模式（如 Intel 的 VMX root 和 non-root 模式），使得 Hypervisor 可以直接控制 CPU 的模式切換，大幅簡化了這個過程，提高了效率。
*   **與相鄰概念的關聯：** KVM 的高效能正是建立在充分利用 Intel VT-x 或 AMD-V 之上。如果沒有這些硬體支持，KVM 將無法運行或只能運行在效能較差的軟體模擬模式下。

#### KVM 的主要組件
*   **KVM Kernel Module (`kvm.ko`, `kvm_intel.ko`/`kvm_amd.ko`)**
    *   **核心觀念：** 這是 KVM 的核心，一個 Linux 核心模組。它提供了虛擬化所需的底層功能，如 CPU 和記憶體虛擬化，並將這些功能暴露給用戶空間。
    *   **作用：** 負責虛擬機的 CPU 執行、記憶體管理 (MMU 虛擬化) 以及對虛擬機的特權指令進行截獲和處理。
*   **QEMU (Quick EMUlator)**
    *   **核心觀念：** QEMU 是一個通用的開源機器模擬器和虛擬器。在 KVM 環境中，QEMU 主要扮演兩個角色：
        1.  **管理工具：** QEMU 負責虛擬機的啟動、停止、配置，並為虛擬機提供虛擬硬體（如虛擬網卡、虛擬磁碟、虛擬顯示卡等）。
        2.  **用戶空間程序：** QEMU 程式在用戶空間運行，它透過 `/dev/kvm` 介面與 KVM 核心模組溝通，將虛擬機的非特權指令直接傳遞給 KVM 模組執行，而將需要模擬虛擬設備的 I/O 操作處理掉。
    *   **關聯：** KVM 提供了底層虛擬化能力，QEMU 則將這些能力整合並暴露為一個完整的虛擬機平台。KVM 負責「CPU和記憶體虛擬化」，QEMU 負責「I/O虛擬化」。
*   **Libvirt**
    *   **核心觀念：** Libvirt 是一個開源的虛擬化管理 API、守護程序和工具集。它提供了一個通用的介面來管理多種虛擬化技術，包括 KVM、Xen、VirtualBox 等。
    *   **作用：** Libvirt 抽象了底層虛擬化技術的複雜性，允許用戶和管理工具（如 `virsh` 命令列工具、 virt-manager 圖形化工具或 OpenStack 等雲平台）透過統一的介面來創建、配置、啟動、停止和監控虛擬機。
    *   **關聯：** Libvirt 使得管理 KVM 虛擬機變得更加簡單和自動化，它是 KVM 虛擬化管理生態系統中不可或缺的一部分。

-----

### 2. KVM 運作原理與架構

#### KVM 架構圖解
KVM 的架構可以簡化為以下層次：

```
+-------------------------------------------------------------+
|              Guest Operating System (VMs)                   |
|   +-------------------+  +-------------------+  +----------+
|   |   Guest OS (Linux)|  |   Guest OS (Win)  |  |   ...    |
|   |   Application     |  |   Application     |  |          |
|   |   (User Space)    |  |   (User Space)    |  |          |
|   |-------------------|  |-------------------|  |----------|
|   |   Guest Kernel    |  |   Guest Kernel    |  |          |
|   |   (Kernel Space)  |  |   (Kernel Space)  |  |          |
|   +-------------------+  +-------------------+  +----------+
|            ^       |               ^       |
|            |       v               |       v
+-------------------------------------------------------------+
|          QEMU (User Space Program for each VM)              |
|          Provides Virtual Hardware (NIC, Disk, VGA, etc.)   |
|                 Handles I/O Emulation                       |
+-------------------------------------------------------------+
|                            ^                                |
|                            |  (/dev/kvm interface)          |
+-------------------------------------------------------------+
|        KVM Kernel Modules (kvm.ko, kvm_intel/amd.ko)        |
|        CPU & Memory Virtualization, VM-Exit/Entry Handling  |
|        (Resides within the Host Linux Kernel)               |
+-------------------------------------------------------------+
|                  Host Operating System (Linux)              |
|                  (Manages other system resources)           |
+-------------------------------------------------------------+
|             Physical Hardware (CPU with VT-x/AMD-V)         |
|             (Memory, Storage, Network Interface)            |
+-------------------------------------------------------------+
```

*   **說明：**
    *   **Physical Hardware (實體硬體):** 最底層是 CPU (必須支援 VT-x/AMD-V)、記憶體、儲存、網路卡等實體資源。
    *   **Host Operating System (主機作業系統):** 通常是 Linux 發行版，KVM 模組是其核心的一部分。它負責管理整個實體機器及其資源。
    *   **KVM Kernel Modules:** 內建於 Linux 核心中，負責底層的 CPU 和記憶體虛擬化。當虛擬機需要執行特權指令時，KVM 模組會截獲並處理。
    *   **QEMU:** 運行在主機的用戶空間，為每個虛擬機提供一套虛擬硬體（如虛擬網卡、虛擬磁碟、虛擬顯示卡等）。它處理虛擬機的所有 I/O 操作，並透過 `/dev/kvm` 介面與 KVM 模組溝通，將虛擬機的 CPU 指令傳遞給 KVM 模組執行。
    *   **Guest Operating System (客戶機作業系統):** 運行在虛擬機內部，對其而言，它認為自己運行在一個專屬的硬體上。

#### 虛擬機啟動流程
1.  **管理工具發送指令：** 使用者透過 `virsh`、`virt-manager` 或直接使用 `qemu-system-x86_64` 命令來啟動一個虛擬機。
2.  **QEMU 進程啟動：** QEMU 作為一個用戶空間進程啟動。它會解析虛擬機的配置（如 CPU 數量、記憶體大小、虛擬磁碟路徑等）。
3.  **KVM 模組初始化：** QEMU 透過 `/dev/kvm` 介面向 Linux 核心中的 KVM 模組發出請求，創建一個新的虛擬機上下文。KVM 模組會利用硬體虛擬化技術 (VT-x/AMD-V) 初始化虛擬機的 CPU 和記憶體。
4.  **Guest OS 啟動：** QEMU 將虛擬機的指令指針設定為 Guest OS 的啟動地址（例如 BIOS 或 EFI），並將 CPU 控制權交給 KVM 模組。KVM 模組利用硬體虛擬化功能，讓 Guest OS 在一個隔離的環境中直接運行。
5.  **指令執行與切換：**
    *   **非特權指令：** Guest OS 中的大部分非特權指令會直接在實體 CPU 上執行，幾乎沒有效能損耗。
    *   **特權指令與 I/O 請求：** 當 Guest OS 嘗試執行特權指令（例如修改 CPU 模式、訪問 I/O 埠）或進行 I/O 操作時，硬體會觸發「VM Exit」，CPU 控制權會從 Guest OS 模式切換回 KVM 模組（Host OS 核心空間）。
    *   **KVM 處理：** KVM 模組截獲這些請求，並轉交給 QEMU 進程處理。
    *   **QEMU 模擬：** QEMU 根據虛擬機的配置，模擬出對應的虛擬硬體行為，並將結果返回給 KVM 模組。
    *   **VM Entry：** KVM 模組接收到 QEMU 的處理結果後，會再次觸發「VM Entry」，將 CPU 控制權切換回 Guest OS 模式，讓 Guest OS 繼續執行。

#### 虛擬機 I/O 處理
*   **核心觀念：** 虛擬機的 I/O 操作（如磁碟讀寫、網路通訊）無法直接訪問實體硬體。KVM 依賴 QEMU 來模擬這些虛擬設備。
*   **I/O 虛擬化方式：**
    1.  **完全虛擬化 (Full Virtualization):**
        *   **機制：** QEMU 完全模擬標準的硬體設備（如 Realtek 網卡、IDE 磁碟控制器）。Guest OS 不需要任何修改，它可以安裝標準的驅動程式。
        *   **缺點：** 效能開銷較大，因為 QEMU 需要在軟體層面模擬硬體的每個細節。
    2.  **半虛擬化 (Paravirtualization) - VirtIO：**
        *   **核心觀念：** VirtIO 是一套標準化的半虛擬化 I/O 裝置介面，專為虛擬化環境設計。它要求 Guest OS 安裝特殊的 VirtIO 驅動程式。
        *   **機制：** 當 Guest OS 使用 VirtIO 驅動時，它會直接透過一個定義好的介面與 QEMU 溝通，而不是模擬傳統的硬體設備。這大大減少了 I/O 虛擬化的開銷，因為 Guest OS 知道自己運行在虛擬機中，可以直接與 Hypervisor 協作。
        *   **優點：** 顯著提升 I/O 效能，接近原生硬體效能。
        *   **與相鄰概念的關聯：** VirtIO 是 KVM 實現高效能 I/O 的關鍵。它模糊了 Type-1 和 Type-2 Hypervisor 的界限，使得 KVM 即使作為 Type-2 的模組，也能提供接近 Type-1 的 I/O 效能。

#### 記憶體管理
*   **核心觀念：** KVM 負責將虛擬機的「客戶實體位址 (Guest Physical Address, GPA)」映射到主機的「主機實體位址 (Host Physical Address, HPA)」。
*   **推導：**
    1.  **Guest OS 視角：** 虛擬機內部的作業系統認為自己擁有連續的實體記憶體空間（GPA）。
    2.  **主機 OS 視角：** 這些 GPA 實際上只是主機作業系統中由 QEMU 進程分配的一段記憶體區域。
    3.  **MMU 虛擬化：**
        *   **軟體模擬 (早期或無硬體輔助)：** KVM 和 QEMU 需要維護從虛擬機的虛擬位址 (GVA) -> 虛擬機的實體位址 (GPA) -> 主機的實體位址 (HPA) 的多層映射，效率低下。
        *   **硬體輔助 (EPT/RVI)：** 現代 CPU 提供「擴展頁表 (Extended Page Tables, EPT)」（Intel VT-x）或「快速虛擬化索引 (Rapid Virtualization Indexing, RVI)」（AMD-V，又稱 Nested Page Tables, NPT）。這些技術允許硬體直接處理 GPA 到 HPA 的映射，大幅加速了記憶體訪問，減少了虛擬化開銷。Hypervisor 只需要設定一次 EPT/NPT，之後大部分記憶體訪問都無需 VM Exit。
*   **與相鄰概念的關聯：** 硬體輔助的記憶體管理技術與 CPU 硬體輔助虛擬化技術相輔相成，共同構成了 KVM 高效能的基石。

-----

### 3. 與相鄰概念的關聯

#### KVM 與其他 Hypervisor 的比較
*   **KVM vs. Xen:**
    *   **KVM：** 深度整合於 Linux 核心，利用現有的 Linux 生態系統。通常結合 QEMU 提供虛擬硬體，並透過 VirtIO 實現高效能 I/O。
    *   **Xen：** 早期是一個獨立的 Type-1 Hypervisor，有其獨立的 Domain 0 (特權虛擬機) 來管理其他虛擬機。它也支援半虛擬化 (Xen PV) 和完全虛擬化 (Xen HVM)。
    *   **關聯：** 兩者都是開源虛擬化技術。KVM 的優勢在於其與 Linux 核心的緊密結合，受益於 Linux 社區的龐大開發力量和驅動支援。Xen 則有其獨立的 Hypervisor 層，在某些場景下提供不同的管理模式。
*   **KVM vs. VMware ESXi / Microsoft Hyper-V:**
    *   **KVM：** 開源，基於 Linux。
    *   **ESXi/Hyper-V：** 專有閉源產品，通常提供更完善的企業級管理工具和生態系統。它們是典型的 Type-1 Hypervisor。
    *   **關聯：** KVM 提供了與這些商業產品類似的 Type-1 虛擬化性能，但具備開源和高度客製化的優勢，因此在雲端服務供應商和大規模資料中心中廣受歡迎。
*   **KVM vs. VirtualBox / VMware Workstation:**
    *   **KVM：** Linux 核心模組，主要用於伺服器虛擬化。
    *   **VirtualBox/Workstation：** Type-2 Hypervisor，通常作為桌面應用程式運行，在開發和測試環境中更常用。
    *   **關聯：** KVM 與 VirtualBox/Workstation 的主要區別在於其定位和架構：KVM 追求接近原生的伺服器效能，而後者則提供更方便的桌面級虛擬化體驗。

#### KVM 與 Docker/容器化技術的差異
*   **KVM (虛擬機)：**
    *   **隔離性：** 強，每個虛擬機都有獨立的 Guest OS 核心、獨立的檔案系統和資源。虛擬機之間完全隔離，互不影響。
    *   **資源消耗：** 較高，每個虛擬機都需要完整的作業系統核心和一套虛擬硬體。
    *   **用途：** 運行不同作業系統、提供強隔離性、承載複雜應用服務。
*   **Docker (容器)：**
    *   **隔離性：** 較弱，所有容器共享主機的 Linux 核心。它們在用戶空間層面進行隔離（Cgroups, Namespaces）。
    *   **資源消耗：** 較低，共享主機核心，啟動快，佔用資源少。
    *   **用途：** 應用程式的輕量級封裝和部署、微服務架構。
*   **關聯：** 兩者都是實現資源隔離的技術。虛擬機提供「作業系統級別」的隔離，而容器提供「應用程式級別」的隔離。在許多雲原生環境中，虛擬機（由 KVM 提供）作為基礎設施層，其上再運行容器化應用，形成一個強大且彈性的堆疊。例如，OpenStack 常常使用 KVM 作為虛擬化底層，然後在虛擬機上部署 Kubernetes 集群來運行 Docker 容器。

#### KVM 與雲端計算的關係
*   **核心觀念：** KVM 是許多開源雲端計算平台（如 OpenStack）首選的虛擬化引擎。其穩定性、高效能、開源特性以及與 Linux 的深度整合，使其成為構建彈性、可擴展雲端基礎設施的理想選擇。
*   **例子：** 在 OpenStack 中，Nova 計算服務負責管理虛擬機實例。Nova 通常會配置為使用 KVM 作為底層的 Hypervisor。當使用者請求一個新的虛擬機時，Nova 會透過 Libvirt API 在底層的 KVM 主機上啟動一個 QEMU 進程來創建虛擬機。
*   **與相鄰概念的關聯：** KVM 為雲端計算提供了必要的虛擬化能力，使得雲平台能夠將實體硬體資源抽象化並按需分配給租戶。

-----

### 4. 進階內容

#### Nested Virtualization (巢狀虛擬化)
*   **核心觀念：** 巢狀虛擬化允許在一個虛擬機內部運行另一個 Hypervisor，並在該內部 Hypervisor 上再創建虛擬機。簡而言之，就是「虛擬機中的虛擬機」。
*   **例子：** 你在 KVM 主機上創建了一個 Linux 虛擬機，然後在這個 Linux 虛擬機內部安裝了 VirtualBox 或另一個 KVM，並在 VirtualBox/內部 KVM 中再運行一個 Guest OS。
*   **推導：** 為了實現巢狀虛擬化，底層的 Hypervisor (Host KVM) 必須將其硬體虛擬化功能 (VT-x/AMD-V) 暴露給其 Guest OS。這樣，Guest OS 才能「感覺」到自己擁有硬體虛擬化能力，進而能夠充當 Hypervisor 來創建自己的虛擬機。
*   **用途：** 雲端環境中的測試、教育、或提供虛擬化服務給使用者等情境。例如，一些雲服務商會提供支援 Nested Virtualization 的 VM，讓你在雲端 VM 中運行 Docker Desktop (它內部使用 Hyper-V 或 KVM)。

#### Live Migration (熱遷移)
*   **核心觀念：** Live Migration 是一種技術，允許在不中斷虛擬機服務的情況下，將一個運行中的虛擬機從一台實體主機遷移到另一台實體主機。這對於維護、負載平衡和災難恢復非常重要。
*   **推導：** Live Migration 的實現通常涉及以下步驟：
    1.  **預遷移檢查：** 確認目標主機有足夠資源且與源主機兼容。
    2.  **記憶體同步：** 虛擬機的記憶體內容會以迭代的方式從源主機複製到目標主機。第一次會複製所有記憶體，之後只複製在複製過程中發生變化的「髒頁面」。這個過程會重複進行，直到髒頁面數量減少到一個可接受的閾值。
    3.  **停止並最終同步：** 當髒頁面數量很低時，虛擬機在源主機上會暫停一小段時間（通常是毫秒級別），最終的記憶體差異會被複製到目標主機。
    4.  **切換控制：** 虛擬機在目標主機上恢復執行。此時網路連接會被重新導向到目標主機。
    5.  **源主機清理：** 源主機上的虛擬機資源被釋放。
*   **與相鄰概念的關聯：** Live Migration 是 KVM 作為企業級虛擬化解決方案的關鍵特性之一，它與 Libvirt 緊密集成，方便雲平台進行自動化管理。

-----

### 5. 常見錯誤與澄清

#### KVM 不是一個獨立的 Hypervisor
*   **常見錯誤：** 認為 KVM 是一個獨立的軟體包或作業系統，可以直接安裝運行。
*   **澄清：** KVM 是一個 **Linux 核心模組**。它本身不提供用戶介面或虛擬硬體模擬。它需要 Linux 作業系統作為其宿主 (Host OS)，並透過 `/dev/kvm` 介面提供虛擬化能力。QEMU 或 Libvirt 才是用戶與 KVM 模組交互的橋樑。

#### KVM 不等於 QEMU
*   **常見錯誤：** 混淆 KVM 和 QEMU，認為它們是同一個東西。
*   **澄清：** 
    *   **KVM：** 提供 CPU 和記憶體的硬體輔助虛擬化。它是底層的虛擬化「引擎」。
    *   **QEMU：** 是一個虛擬機器模擬器，它提供虛擬機的虛擬硬體（磁碟、網卡、顯示卡等）並處理 I/O 操作。當 QEMU 配合 KVM 使用時，QEMU 將 CPU 和記憶體操作交給 KVM 處理，從而獲得接近原生的性能。
    *   **關係：** KVM 提供了「速度」，QEMU 提供了「功能」。兩者協同工作，缺一不可（通常）。

#### KVM 虛擬化不總是全虛擬化
*   **常見錯誤：** 認為 KVM 只能做全虛擬化。
*   **澄清：** KVM 本身是基於硬體輔助的全虛擬化。然而，透過使用 **VirtIO** 驅動程式，Guest OS 可以意識到自己運行在虛擬機中，並直接透過優化後的介面與 Hypervisor 溝通，這就是 **半虛擬化**。因此，KVM 支援全虛擬化（當 Guest OS 不加修改，使用模擬的標準設備驅動時）和半虛擬化（當 Guest OS 安裝 VirtIO 驅動時）。為了最佳性能，推薦使用 VirtIO。

#### 開啟硬體虛擬化功能的重要性
*   **常見錯誤：** 忽略 BIOS/UEFI 中虛擬化選項的啟用。
*   **澄清：** KVM 的高效能仰賴於 CPU 的硬體虛擬化擴展 (Intel VT-x 或 AMD-V)。如果這些功能未在主機的 BIOS/UEFI 設定中啟用，KVM 將無法正常工作或只能降級到效率極低的軟體模擬模式。因此，在部署 KVM 之前，務必檢查並啟用這些選項。

-----

### 6. 小練習（附詳解）

#### 小練習 1: 檢查 KVM 支援性與核心模組狀態

**目標：** 確認你的 Linux 主機是否支援 KVM 虛擬化，並檢查 KVM 核心模組是否已載入。

**步驟：**

1.  **檢查 CPU 是否支援硬體虛擬化：**
    執行以下命令：
    ```bash
    grep -E --color 'vmx|svm' /proc/cpuinfo
    ```
    *   如果輸出中包含 `vmx` (Intel) 或 `svm` (AMD)，則表示你的 CPU 支援硬體虛擬化。
    *   如果沒有輸出，則可能不支援，或者需要在 BIOS/UEFI 中啟用。
2.  **檢查 KVM 模組是否已載入：**
    執行以下命令：
    ```bash
    lsmod | grep kvm
    ```
    *   如果輸出中包含 `kvm_intel` 或 `kvm_amd` 以及 `kvm`，則表示 KVM 模組已經載入。
3.  **確認 `/dev/kvm` 設備是否存在：**
    執行以下命令：
    ```bash
    ls -l /dev/kvm
    ```
    *   如果顯示 `/dev/kvm` 設備文件，則 KVM 核心模組已成功載入並運行。
4.  **如果 KVM 模組未載入，嘗試手動載入 (僅限 Intel/AMD)：**
    *   對於 Intel CPU：
        ```bash
        sudo modprobe kvm_intel
        sudo modprobe kvm
        ```
    *   對於 AMD CPU：
        ```bash
        sudo modprobe kvm_amd
        sudo modprobe kvm
        ```
    *   載入後，再次執行步驟 2 和 3 進行確認。

**詳解：**

*   `grep -E --color 'vmx|svm' /proc/cpuinfo`：這個命令用於檢查 CPU 資訊文件 `/proc/cpuinfo` 中是否存在 `vmx` (Intel Virtualization Technology) 或 `svm` (Secure Virtual Machine，AMD Virtualization 的別名) 標誌。這些標誌的存在是 KVM 能夠運行在高效能模式下的先決條件。如果沒有這些標誌，需要檢查 BIOS/UEFI 設定，確保虛擬化選項 (如 "Intel VT-x" 或 "AMD-V") 已啟用。
*   `lsmod | grep kvm`：`lsmod` 命令列出所有已載入的 Linux 核心模組。透過 `grep kvm` 過濾，我們可以確認 `kvm.ko` 以及特定於 CPU 的模組（`kvm_intel.ko` 或 `kvm_amd.ko`）是否已在運行中。這些模組提供了 KVM 的核心功能。
*   `ls -l /dev/kvm`： `/dev/kvm` 是一個字符設備文件，是用戶空間程式 (如 QEMU) 與 KVM 核心模組溝通的介面。它的存在標誌著 KVM 虛擬化環境已準備就緒，並且有足夠的權限可以訪問。
*   `sudo modprobe kvm_intel`/`kvm_amd` 和 `sudo modprobe kvm`：這些命令用於手動載入 KVM 核心模組。在大多數現代 Linux 發行版中，當安裝 KVM 相關套件時，這些模組會自動載入。但如果出現問題，手動載入是診斷的第一步。

#### 小練習 2: 使用 QEMU + KVM 啟動一個簡單的虛擬機

**目標：** 透過直接使用 QEMU 命令，理解 KVM 與 QEMU 如何協同工作來啟動一個虛擬機。我們將使用一個輕量級的 Linux ISO 映像檔 (例如 Tiny Core Linux)。

**預備：**
1.  完成小練習 1，確保 KVM 環境就緒。
2.  下載一個輕量級 Linux ISO，例如 Tiny Core Linux (`CorePlus-current.iso` 或類似版本)。你可以從其官方網站下載：`http://www.tinycorelinux.net/downloads.html`。將其保存到 `/tmp/CorePlus-current.iso`。
3.  安裝 QEMU 套件：`sudo apt update && sudo apt install qemu-system-x86` (Ubuntu/Debian) 或 `sudo yum install qemu-kvm` (CentOS/RHEL)。

**步驟：**

1.  **創建一個虛擬硬碟映像檔：**
    ```bash
    qemu-img create -f qcow2 /tmp/tinycore_vm.qcow2 10G
    ```
    這會創建一個 10GB 的 QCOW2 格式虛擬硬碟文件。
2.  **使用 QEMU 啟動虛擬機，並啟用 KVM：**
    ```bash
    qemu-system-x86_64 -enable-kvm \
      -m 1024 \
      -cpu host \
      -smp 2 \
      -hda /tmp/tinycore_vm.qcow2 \
      -cdrom /tmp/CorePlus-current.iso \
      -boot d \
      -vnc :0 \
      -monitor stdio
    ```
3.  **觀察虛擬機啟動：**
    QEMU 會打開一個 VNC 服務（通常在 `localhost:5900`），你可以使用 VNC 客戶端連接查看虛擬機的圖形介面，或者直接在終端看到部分啟動日誌。
    虛擬機將從 ISO 映像檔啟動。你應該能看到 Tiny Core Linux 的啟動畫面。
4.  **退出虛擬機：**
    在 QEMU 的 monitor 介面 (如果你使用 `stdio` 參數)，輸入 `quit` 然後按 Enter。或者直接關閉 VNC 客戶端。

**詳解：**

*   `qemu-img create -f qcow2 /tmp/tinycore_vm.qcow2 10G`：
    *   `qemu-img` 是 QEMU 提供的虛擬磁碟管理工具。
    *   `create` 指令用於創建一個新的虛擬磁碟映像檔。
    *   `-f qcow2` 指定映像檔格式為 QCOW2 (QEMU Copy-On-Write)，這是一種靈活的格式，支持快照、精簡配置等特性。
    *   `/tmp/tinycore_vm.qcow2` 是創建的虛擬磁碟映像檔的路徑。
    *   `10G` 指定虛擬磁碟的最大容量為 10 GB。
*   `qemu-system-x86_64 -enable-kvm ...`：
    *   `qemu-system-x86_64` 是 QEMU 用於模擬 x86-64 架構的系統。
    *   `-enable-kvm`：這是關鍵參數，告訴 QEMU 啟用 KVM 加速。如果沒有這個參數，QEMU 將會使用純軟體模擬，效能會非常差。這個參數要求 `/dev/kvm` 設備可用。
    *   `-m 1024`：為虛擬機分配 1024 MB (1GB) 的記憶體。
    *   `-cpu host`：將虛擬機的 CPU 型號設定為主機 CPU 的型號，這樣虛擬機可以使用主機 CPU 提供的所有特性和擴展，包括虛擬化擴展。
    *   `-smp 2`：為虛擬機分配 2 個虛擬 CPU 核心。
    *   `-hda /tmp/tinycore_vm.qcow2`：將創建的 QCOW2 文件作為虛擬機的第一個硬碟 (hd**a**)。
    *   `-cdrom /tmp/CorePlus-current.iso`：將 ISO 映像檔掛載為虛擬機的 CD-ROM。
    *   `-boot d`：設定虛擬機從 CD-ROM (d) 啟動。
    *   `-vnc :0`：啟用 VNC 伺服器，讓你可以透過 VNC 客戶端（例如 `vncviewer localhost:0` 或 `localhost:5900`）連接到虛擬機的圖形介面。
    *   `-monitor stdio`：在當前終端中顯示 QEMU monitor 介面，你可以透過這個介面輸入命令（例如 `info kvm`、`quit` 等）。

這個練習展示了 KVM 模組提供底層加速，而 QEMU 負責提供完整的虛擬硬體和管理功能。

-----

### 7. 延伸閱讀/參考

*   **KVM 官方網站：** [https://www.linux-kvm.org/](https://www.linux-kvm.org/)
    *   KVM 專案的官方首頁，包含最新資訊、文件和開發資源。
*   **QEMU 官方網站：** [https://www.qemu.org/](https://www.qemu.org/)
    *   QEMU 專案的官方首頁，提供 QEMU 的詳細資訊、文件和下載。
*   **Libvirt 官方網站：** [https://libvirt.org/](https://libvirt.org/)
    *   Libvirt 專案的官方首頁，包含 API 文檔、工具介紹和使用指南。
*   **維基百科 - KVM：** [https://zh.wikipedia.org/wiki/KVM](https://zh.wikipedia.org/wiki/KVM)
    *   提供 KVM 的概覽、歷史和技術細節。
*   **Red Hat Enterprise Linux 虛擬化部署指南：** (搜尋 "Red Hat KVM virtualization")
    *   Red Hat 作為 KVM 的主要貢獻者之一，其官方文檔對於理解和部署 KVM 提供了權威且詳細的指南。
*   **VirtIO 規格：** [https://docs.oasis-open.org/virtio/virtio/v1.1/virtio-v1.1.html](https://docs.oasis-open.org/virtio/virtio/v1.1/virtio-v1.1.html)
    *   如果想深入了解半虛擬化 I/O 的原理，可以查閱 VirtIO 的官方規格。