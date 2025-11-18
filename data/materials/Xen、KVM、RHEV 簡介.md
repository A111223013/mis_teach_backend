# 1-2 Xen、KVM、RHEV 簡介

## 前言：虛擬化技術的基石

隨著資訊技術的發展，虛擬化（Virtualization）已成為現代資料中心和雲端運算不可或缺的技術。它允許在單一實體伺服器上執行多個獨立的虛擬機器（Virtual Machine, VM），藉此提升硬體資源利用率、簡化管理、增強系統彈性與高可用性。本章節將深入介紹三種關鍵的虛擬化技術：Xen、KVM，以及基於KVM的企業級虛擬化管理平台RHEV（Red Hat Enterprise Virtualization）。

-----

### 1. 核心概念與定義

#### 1.1 Hypervisor（虛擬機器監視器）

*   **定義/核心觀念：** Hypervisor 是一種軟體、韌體或硬體，用於建立和執行虛擬機器。它將客體作業系統與底層硬體資源分離，為每個虛擬機器提供一個模擬的硬體環境。Hypervisor 通常分為兩種主要類型：
    *   **Type-1 Hypervisor（裸機型或原生型）：** 直接執行在實體硬體上，在硬體和客體作業系統之間提供虛擬化層。它擁有最高的效能，因為沒有底層作業系統的開銷。
    *   **Type-2 Hypervisor（託管型）：** 執行在傳統作業系統之上，將客體作業系統作為一個應用程式來運行。其效能通常略低於 Type-1，因為需要經過宿主作業系統的排程和資源管理。

-----

#### 1.2 Xen

*   **定義/核心觀念：** Xen 是一個開源的 Type-1 Hypervisor。它直接安裝在硬體之上，負責管理 CPU、記憶體等資源，並在上面運行一個特殊的虛擬機器 (Dom0) 和多個客體虛擬機器 (DomU)。
    *   **Dom0 (Domain 0)：** 這是第一個啟動的虛擬機器，擁有管理整個 Xen 系統的特權。它負責與硬體驅動程式互動，並管理所有其他 DomU 的生命週期。
    *   **DomU (Domain U)：** 這是普通的客體虛擬機器，由 Dom0 創建和管理。

*   **主要虛擬化模式：**
    *   **半虛擬化 (Para-virtualization, PV)：** 客體作業系統會被修改（例如，安裝 Xen 專屬的核心），使其「意識」到自己運行在虛擬化環境中，並直接與 Hypervisor 溝通，以實現更高效能的 I/O 操作。
    *   **全虛擬化 (Hardware-assisted Virtualization, HVM)：** 利用 CPU 的硬體虛擬化擴展（如 Intel VT-x 或 AMD-V），無需修改客體作業系統。這使得任何未修改的作業系統（如 Windows）都能在 Xen 上運行。HVM 通常結合了半虛擬化驅動（PV Drivers 或 PVHVM）以提升 I/O 效能。

*   **典型例子：** 當我們在 Xen 環境中啟動一個 Linux VM，如果該 Linux 核心支援半虛擬化，它會運行在 PV 模式，直接調用 Xen Hypervisor 的介面來完成操作，而不是模擬所有的硬體。如果是一個 Windows VM，則必須使用 HVM 模式，並可能安裝 PV Drivers 來加速磁碟和網路。

*   **與相鄰概念的關聯：**
    *   **與 KVM 比較：** Xen 是一個獨立的 Hypervisor，而 KVM 則是 Linux 核心模組。在設計上，Xen 的核心較為精簡，將許多功能（如設備驅動）交給 Dom0 處理。

-----

#### 1.3 KVM (Kernel-based Virtual Machine)

*   **定義/核心觀念：** KVM 是 Linux 核心的一部分，它將 Linux 核心轉換為一個 Type-1 Hypervisor。KVM 本身是一個核心模組 (`kvm.ko`)，它利用硬體虛擬化擴展（Intel VT-x 或 AMD-V）來實現虛擬化。KVM 藉由結合 `QEMU`（一個開源的硬體模擬器）來提供完整的虛擬機器功能。
    *   **KVM 模組：** 負責虛擬機器的 CPU 和記憶體虛擬化。
    *   **QEMU：** 提供虛擬機器所需的 BIOS、顯示卡、網路卡、磁碟控制器等週邊硬體模擬。當 KVM 模組啟用時，QEMU 可以利用 KVM 的高效能虛擬化能力，大幅提升模擬速度。

*   **典型例子：** 在安裝了 KVM 模組的 Linux 伺服器上，我們可以使用 `virt-manager` 或 `virsh` 命令工具創建並管理虛擬機器。例如，當你啟動一個 Ubuntu VM，KVM 模組會負責其 CPU 的執行和記憶體的管理，而 QEMU 則會模擬出一個虛擬的網卡和硬碟給 Ubuntu 使用。如果 Ubuntu 核心支援 `virtio`（一種半虛擬化 I/O 驅動），則 I/O 效能將會非常接近實體機。

*   **與相鄰概念的關聯：**
    *   **與 Xen 比較：** KVM 緊密整合於 Linux 核心，不需要一個單獨的 Dom0 來管理硬體驅動，而是直接使用 Linux 核心自身的功能。這使得 KVM 的維護和開發與 Linux 生態系統保持一致。
    *   **與 RHEV 關聯：** KVM 是 RHEV 的底層虛擬化技術。RHEV 提供了一個集中化的管理平台來協調和管理多個 KVM 主機和其上的虛擬機器。

-----

#### 1.4 RHEV (Red Hat Enterprise Virtualization) / RHV (Red Hat Virtualization)

*   **定義/核心觀念：** RHEV（已更名為 Red Hat Virtualization, RHV）是一個企業級的虛擬化管理平台。它基於 KVM 技術，旨在為資料中心提供一套完整的虛擬化解決方案，包括虛擬機器的生命週期管理、高可用性、即時遷移、儲存管理、網路管理等。
    *   **RHEV Manager (Engine)：** 這是 RHV 的核心管理組件，通常運行在一個獨立的 VM 上。它提供 Web 管理介面，用於配置、監控和管理所有虛擬化資源。
    *   **RHEV Hypervisor (Node)：** 這是運行 KVM 虛擬機器的實體主機，通常是一個輕量級的、基於 Red Hat Enterprise Linux 的作業系統，專為運行虛擬機器而優化。

*   **典型例子：** 在一個大型企業的資料中心裡，IT 管理員可能部署了數十台 KVM 主機。如果沒有 RHEV，管理員需要逐一登錄每台主機來管理 VM。但有了 RHEV，他們只需登錄 RHEV Manager 的 Web 介面，就能集中管理所有主機上的 VM，例如一鍵部署新的 VM、將運行中的 VM 從一台主機遷移到另一台、設定 VM 自動故障轉移等。

*   **與相鄰概念的關聯：**
    *   **與 KVM 關聯：** RHEV 是 KVM 的「上層建築」。KVM 提供了底層的虛擬化能力，而 RHEV 則將這些能力整合並提供企業級的管理功能和自動化工具。可以說，RHEV 是 KVM 在企業環境中實現規模化部署和高效管理的關鍵。
    *   **與 VMware vSphere 比較：** RHEV 與 VMware 的 vSphere 在功能上有很多相似之處，都是企業級的虛擬化管理平台。主要區別在於底層的 Hypervisor（RHEV 使用 KVM，vSphere 使用 ESXi）以及其生態系統。

-----

### 2. 典型例子與推導

#### 2.1 虛擬化 I/O 效能的演進

*   **全虛擬化（HVM）模擬：** 早期虛擬化透過完全模擬硬體設備，如一個舊式的 Realtek 網路卡。客體作業系統會認為自己在跟真實硬體溝通，但 Hypervisor 需要截獲所有這些指令，並將它們轉換為對實際硬體的指令。這導致了大量的開銷，效能較差。
    *   `Guest OS` $\xrightarrow{\text{模擬硬體驅動}}$ `Hypervisor` $\xrightarrow{\text{轉換指令}}$ `實體硬體驅動` $\xrightarrow{\text{I/O 操作}}$ `硬體`

*   **半虛擬化（PV）：** 客體作業系統安裝特殊的驅動程式，這些驅動程式知道自己運行在虛擬環境中，可以直接調用 Hypervisor 提供的介面（Hypercall），而不是模擬硬體。這減少了轉換的開銷，顯著提升了 I/O 效能。
    *   `Guest OS (PV Driver)` $\xrightarrow{\text{Hypercall}}$ `Hypervisor` $\xrightarrow{\text{直接操作}}$ `實體硬體驅動` $\xrightarrow{\text{I/O 操作}}$ `硬體`

*   **KVM/QEMU 的 Virtio：** KVM 結合 QEMU 時，推薦使用 `virtio` 驅動。`virtio` 是一種開放標準的半虛擬化 I/O 框架，它在客體作業系統中提供了一個通用的虛擬設備介面。QEMU 作為 Hypervisor 側的實現，將 `virtio` 請求轉換為宿主機上的實際 I/O 操作。這提供了接近原生的 I/O 效能，同時保持了通用性和標準化。
    *   `Guest OS (Virtio Driver)` $\xrightarrow{\text{Virtio 介面}}$ `KVM/QEMU` $\xrightarrow{\text{宿主機 I/O}}$ `實體硬體驅動` $\xrightarrow{\text{I/O 操作}}$ `硬體`

-----

### 3. 常見錯誤與澄清

*   **KVM 是 Type-1 還是 Type-2 Hypervisor？**
    *   **澄清：** KVM 本身是一個 Linux 核心模組，它將 Linux 核心轉換為 Type-1 Hypervisor。這意味著 KVM 讓 Linux 系統能夠直接管理虛擬機器的 CPU 和記憶體，而不是像 Type-2 Hypervisor 那樣在另一個宿主作業系統的「應用程式」層運行。從客體作業系統的角度看，它直接運行在 KVM 之上，與 Type-1 Hypervisor 無異。`QEMU` 則是在用戶空間，提供硬體模擬和管理功能，並利用 KVM 模組來加速。因此，通常將 KVM 視為 Type-1 Hypervisor。

*   **RHEV 就是 KVM 嗎？**
    *   **澄清：** RHEV（或 RHV）不是 KVM 本身，它是基於 KVM 技術之上構建的企業級管理平台。KVM 提供了核心的虛擬化能力，而 RHEV 則提供了一套用於大規模部署、管理和自動化 KVM 環境的工具和服務。就像 Windows 是作業系統，而 VMware vSphere 是基於 ESXi Hypervisor 的管理套件一樣。

*   **Xen 的半虛擬化 (PV) 和全虛擬化 (HVM) 差異？**
    *   **澄清：** PV 需要修改客體作業系統的核心，使其「知道」自己運行在虛擬化環境中，並直接與 Hypervisor 溝通，效能較高但相容性有限。HVM 則利用硬體虛擬化功能，無需修改客體作業系統，相容性好但初始效能可能略低，通常需要安裝 PV Drivers 來彌補 I/O 效能。現代 Xen 通常會使用 HVM 搭配 PV Drivers 的組合，稱之為 PVHVM。

-----

### 4. 小練習（附詳解）

#### 小練習 1：辨識虛擬化技術

**題目：**
某公司有以下兩種虛擬化部署需求，請判斷哪種情況更適合使用 Xen 的半虛擬化（PV）模式，哪種情況更適合 KVM，並簡述理由：

1.  需要在一台專用伺服器上運行多個高度優化的 Linux 應用伺服器，對 I/O 效能要求極高，且可接受修改作業系統核心。
2.  需要在一台現有 Linux 伺服器上快速部署多個虛擬機器，其中包含 Windows 和未經修改的 Linux 發行版，且希望利用 Linux 系統現有的管理工具。

**詳解：**

1.  **適合 Xen 半虛擬化（PV）模式。**
    *   **理由：** Xen 的半虛擬化模式設計初衷就是為了提供極致的 I/O 效能，透過客體作業系統直接與 Hypervisor 溝通，避免了硬體模擬的開銷。對於對 I/O 效能要求極高且可接受修改 Linux 核心的場景，Xen PV 是非常理想的選擇。

2.  **適合 KVM。**
    *   **理由：** KVM 是 Linux 核心的一部分，可以直接利用現有的 Linux 伺服器作為虛擬化主機，並且與 QEMU 結合後，可以透過硬體虛擬化擴展（Intel VT-x/AMD-V）運行未經修改的客體作業系統，包括 Windows 和標準的 Linux 發行版。同時，由於 KVM 與 Linux 深度整合，可以利用 `virt-manager`、`virsh` 等 Linux 生態系統中的工具進行管理，符合「利用 Linux 系統現有的管理工具」的需求。

-----

#### 小練習 2：RHEV 功能應用

**題目：**
假設你是一個大型資料中心的管理員，負責管理數十台運行 KVM 虛擬機器的實體伺服器。最近，公司計畫將部分重要的應用程式虛擬化，並要求這些應用程式必須具備高可用性，即使底層實體伺服器故障也能自動切換。此外，你需要一個集中化的平台來監控所有虛擬機器的狀態和資源使用情況。

請說明 RHEV 在此情境中能提供哪些關鍵功能來滿足這些需求，並簡述其運作原理。

**詳解：**

在此情境中，RHEV（Red Hat Virtualization）能提供以下關鍵功能：

1.  **集中式管理與監控：**
    *   **RHEV Manager (Engine)：** 作為管理核心，提供一個統一的 Web 介面。你只需登錄 Manager，就能看到所有 KVM 主機的狀態、所有虛擬機器的運行情況、CPU/記憶體/儲存/網路的使用率等。這大大簡化了管理複雜性和監控難度。
    *   **運作原理：** 各個 KVM 主機上運行的代理程式（如 VDSM）會將監控數據回報給 RHEV Manager，Manager 將這些數據彙總並展示。

2.  **高可用性 (High Availability)：**
    *   **功能：** RHEV 允許你為虛擬機器配置高可用性策略。當一台 KVM 實體主機發生故障時（例如斷電、硬體損壞），RHEV 會自動檢測到故障，並在集群中的其他健康主機上重新啟動受影響的虛擬機器。
    *   **運作原理：** RHEV Manager 持續監控 KVM 主機和 VM 的心跳。一旦某個主機或 VM 失去響應，Manager 會觸發故障轉移流程，自動在集群內尋找可用資源，並啟動受影響的 VM。這通常需要共享儲存來確保 VM 的磁碟映像在不同主機間可存取。

3.  **即時遷移 (Live Migration)：**
    *   **功能：** 即使實體主機沒有故障，你也可以在不中斷虛擬機器運行的情況下，將其從一台 KVM 主機遷移到另一台。這對於進行主機維護（如硬體升級、系統補丁）而無需停機服務來說至關重要。
    *   **運作原理：** RHEV Manager 協調源主機將 VM 的記憶體內容逐步複製到目標主機，同時保持 VM 在源主機上運行。在最後的同步階段，VM 會在極短的時間內暫停（毫秒級），完成記憶體剩餘部分的複製，然後在目標主機上恢復運行。這個過程對外部使用者幾乎是無感的。

總之，RHEV 將底層 KVM 的能力進行包裝和強化，提供了企業級資料中心所需的各種管理、自動化和高可用性功能，從而滿足了高效、穩定的虛擬化部署需求。

-----

### 5. 延伸閱讀/參考

*   **Xen Project 官方網站：** [https://xenproject.org/](https://xenproject.org/)
*   **KVM 官方網站：** [https://www.linux-kvm.org/](https://www.linux-kvm.org/)
*   **Red Hat Virtualization (RHV) 產品頁面：** [https://www.redhat.com/zh-tw/technologies/virtualization](https://www.redhat.com/zh-tw/technologies/virtualization)
*   **Linux KVM 虛擬化實戰** (書籍或線上資源，例如鳥哥的 Linux 私房菜中關於虛擬化的章節)
*   **Understanding KVM and QEMU:** A technical deep dive into how KVM and QEMU work together. (可搜尋相關技術文章)