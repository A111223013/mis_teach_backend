# 4-2 WebVirtMgr 管理平臺

## ### 核心概念：WebVirtMgr 是什麼？

WebVirtMgr 是一個基於網頁的 KVM 虛擬化管理介面，它透過 Libvirt API 來管理 KVM 虛擬機器。對於希望透過直觀的圖形使用者介面 (GUI) 來建立、配置和監控 KVM 虛擬機器，而不必完全依賴命令列工具 `virsh` 的系統管理員和開發者來說，WebVirtMgr 提供了一個便利的解決方案。

#### #### 定義與核心觀念

*   **定義**：WebVirtMgr 是一個開源的 Web 應用程式，旨在提供一個基於瀏覽器的 KVM 虛擬化管理控制台。它允許使用者遠端管理多個 KVM 主機及其上運行的虛擬機器。
*   **核心目標**：
    1.  **簡化管理**：將複雜的 `virsh` 命令轉換為易於操作的點擊介面。
    2.  **遠端存取**：允許透過任何具備網頁瀏覽器的設備遠端管理 KVM 虛擬化環境。
    3.  **多主機支援**：可以連接並管理多個 KVM Hypervisor 主機。
    4.  **資源可視化**：提供虛擬機器狀態、資源使用情況（CPU、記憶體、網路、儲存）的概覽。

-----

## ### 典型例子與運作模式

WebVirtMgr 的運作模式是作為一個客戶端，透過 Libvirt 的遠端協定連接到 KVM 主機上的 Libvirt daemon。這意味著 WebVirtMgr 本身可以安裝在獨立的伺服器上，也可以與 KVM 主機安裝在同一台伺服器上。

#### #### WebVirtMgr 的整合與工作流程

1.  **安裝 WebVirtMgr**：通常涉及 Python 環境、Django 框架以及相關的 Python Libvirt 綁定庫 (`libvirt-python`)。
2.  **連接 KVM 主機**：在 WebVirtMgr 介面中，使用者需配置連接到一個或多個 KVM Hypervisor 主機的 Libvirt URI (例如：`qemu:///system` for 本地連接, `qemu+ssh://user@kvm-host/system` for 遠端 SSH 連接)。
3.  **管理虛擬機器**：
    *   **建立**：透過表單填寫虛擬機器名稱、CPU 核心數、記憶體大小、硬碟影像檔、網路設定、作業系統 ISO 檔等參數，WebVirtMgr 會產生相應的 Libvirt XML 配置並提交給 KVM 主機上的 Libvirt daemon，由其建立虛擬機器。
    *   **操作**：對已建立的虛擬機器執行啟動、關閉、暫停、恢復、重啟等操作。
    *   **監控**：查看虛擬機器的即時狀態、資源使用率，並透過內建的 VNC/SPICE 客戶端存取虛擬機器控制台。
    *   **配置**：修改虛擬機器的硬體配置（例如，增加記憶體、更改網路介面卡）。
4.  **管理儲存與網路**：WebVirtMgr 也提供介面來管理 Libvirt 定義的儲存池（Storage Pools）和網路（Networks），例如建立新的磁碟影像、配置網路橋接。

#### #### 範例：使用 WebVirtMgr 建立虛擬機器

1.  **登入 WebVirtMgr 介面**：在瀏覽器中輸入 WebVirtMgr 的 URL。
2.  **新增 KVM 主機**：如果尚未連接，點擊「Hosts」或「連接主機」，輸入 KVM 主機的 Libvirt URI 和認證資訊。
3.  **導航至虛擬機器管理**：在左側導航欄選擇「虛擬機器」或「VMs」。
4.  **點擊「新增虛擬機器」**：一個配置精靈會彈出。
5.  **填寫虛擬機器資訊**：
    *   **名稱**：為虛擬機器命名（例如：`my-web-server`）。
    *   **CPU / 記憶體**：設定虛擬機器的處理器核心數和記憶體大小。
    *   **硬碟**：選擇現有的磁碟影像或建立新的磁碟影像，並指定大小。
    *   **安裝介質**：選擇 ISO 檔案作為光碟機，用於安裝作業系統。
    *   **網路**：選擇虛擬網路（例如：`default` 橋接網路）。
    *   **顯示**：選擇 VNC 或 SPICE 協定進行控制台連接。
6.  **完成建立**：點擊「建立」或「完成」，WebVirtMgr 會向 KVM 主機發送指令，KVM 主機上的 Libvirt daemon 隨即建立虛擬機器。
7.  **啟動與存取**：建立完成後，可以在虛擬機器列表中找到它，點擊啟動，然後點擊「Console」按鈕存取其圖形控制台進行作業系統安裝。

-----

## ### 與相鄰概念的關聯

WebVirtMgr 不是獨立的虛擬化解決方案，它依賴於 KVM 和 Libvirt。理解它與其他 KVM 管理工具的關係非常重要。

#### #### WebVirtMgr 與 Libvirt

*   **基石**：Libvirt 是 KVM、QEMU 等虛擬化技術的標準化管理介面。它提供了一個跨平台、跨 Hypervisor 的 API 介面，允許應用程式透過統一的方式管理虛擬化資源。
*   **WebVirtMgr 的角色**：WebVirtMgr 是一個 Libvirt 的「上層應用」。它將使用者在網頁介面上的操作轉換為 Libvirt API 呼叫，由 Libvirt 執行實際的虛擬機器管理操作。這使得 WebVirtMgr 無需直接與 KVM/QEMU 互動，而只與 Libvirt 互動。

#### #### WebVirtMgr 與 `virsh`

*   **`virsh`**：是 Libvirt 提供的官方命令列工具 (CLI)。系統管理員經常使用 `virsh` 來精確控制 KVM 虛擬機器，執行批次操作，或在沒有圖形介面的環境中進行管理。
*   **比較**：
    *   **`virsh`**：強大、靈活、精細控制、適合腳本自動化，但學習曲線較陡峭，需要熟悉命令語法。
    *   **WebVirtMgr**：直觀、易於學習、遠端圖形化操作、適合日常管理，但功能可能不如 `virsh` 全面（例如，某些高級的 XML 配置可能需要直接編輯或透過 `virsh` 實現）。
*   **互補關係**：兩者並非互相取代，而是互補。日常操作可使用 WebVirtMgr 提高效率，而複雜的診斷、自動化或特定情境下的配置則可藉助 `virsh`。

#### #### WebVirtMgr 與 `virt-manager`

*   **`virt-manager`**：是另一個由 Red Hat 開發的 KVM 圖形化管理工具，通常作為桌面應用程式運行。它也使用 Libvirt API。
*   **比較**：
    *   **`virt-manager`**：桌面應用程式，通常需要 X 視窗系統或 VNC 轉發來遠端顯示，功能較為全面，使用者體驗良好。
    *   **WebVirtMgr**：Web 應用程式，可在任何具備瀏覽器的設備上直接存取，無需額外桌面環境，更適合多使用者或無頭伺服器環境。
*   **使用場景**：如果管理員習慣在自己的桌面上直接操作，`virt-manager` 可能是首選。如果需要團隊成員透過網頁瀏覽器進行遠端協同管理，WebVirtMgr 更具優勢。

-----

## ### 進階內容：配置與管理

WebVirtMgr 除了基礎的 VM 管理外，也提供一些進階功能來管理底層資源。

#### #### 儲存池管理

Libvirt 的儲存池 (Storage Pools) 是用於組織和管理虛擬機器磁碟影像的邏輯容器。WebVirtMgr 允許管理這些儲存池：

*   **支援類型**：目錄 (directory)、LVM 卷組、NFS 共享、iSCSI 等。
*   **操作**：
    *   **建立儲存池**：指定類型和路徑。
    *   **啟動/停止/自動啟動**：管理儲存池的生命週期。
    *   **建立卷 (Volume)**：在儲存池中建立虛擬磁碟影像，可以是 qcow2、raw 等格式，並指定大小。
    *   **刪除卷**：從儲存池中移除磁碟影像。
*   **應用**：在建立虛擬機器時，可以從這些儲存池中選擇可用的磁碟卷作為其硬碟。

#### #### 網路管理

Libvirt 虛擬網路允許虛擬機器之間、虛擬機器與主機之間、以及虛擬機器與外部網路之間進行通訊。

*   **支援類型**：
    *   **NAT 模式**：虛擬機器透過主機的網路位址轉換 (NAT) 訪問外部網路，最簡單且安全。
    *   **橋接模式 (Bridge)**：虛擬機器直接連接到主機的物理網路，獲得獨立的 IP 位址，仿佛是物理網路中的一台獨立主機。
*   **操作**：
    *   **建立虛擬網路**：配置網段、DHCP 範圍、以及是否啟用 NAT。
    *   **修改/啟動/停止**：管理虛擬網路的狀態。
*   **應用**：在建立虛擬機器時，為其分配一個虛擬網路介面卡 (NIC)，並連接到這些虛擬網路之一。

-----

## ### 常見錯誤與澄清

1.  **錯誤：無法連接 KVM 主機 (Connection Refused)**
    *   **澄清**：
        *   檢查 KVM 主機上的 Libvirt daemon (通常是 `libvirtd` 服務) 是否正在運行。使用 `systemctl status libvirtd`。
        *   檢查防火牆設定：KVM 主機的防火牆可能阻擋了來自 WebVirtMgr 的連接請求。Libvirt 通常使用 TCP 16509 (TLS) 或 16514 (非 TLS) 端口。確保這些端口在 KVM 主機上開放，或者允許 WebVirtMgr 伺服器的 IP 存取。
        *   檢查 Libvirt 配置：`libvirtd.conf` 和 `qemu.conf` 檔案中是否允許 TCP 或 SSH 遠端連接。
        *   SSH 連接問題：如果是透過 SSH 連接，確保 WebVirtMgr 伺服器可以無密碼或透過密碼/金鑰連接到 KVM 主機的 SSH 服務。

2.  **錯誤：虛擬機器控制台無法顯示 (VNC/SPICE Client Failed)**
    *   **澄清**：
        *   檢查 KVM 主機的防火牆：VNC 和 SPICE 預設使用 5900 端口起跳。確保虛擬機器分配的控制台端口 (例如 5900, 5901 等) 在 KVM 主機上對 WebVirtMgr 伺服器或使用者開放。
        *   瀏覽器支援：確保您的瀏覽器支援 HTML5 VNC/SPICE 客戶端所需的 WebSocket 技術。
        *   端口衝突：確認虛擬機器未嘗試使用已被佔用的 VNC/SPICE 端口。
        *   虛擬機器狀態：確保虛擬機器正在運行。

3.  **錯誤：磁碟影像或 ISO 檔案找不到**
    *   **澄清**：
        *   確保您在 WebVirtMgr 中指定的檔案路徑在 KVM 主機上實際存在且路徑正確。
        *   檢查檔案權限：Libvirt daemon (通常以 `qemu` 或 `libvirt-qemu` 使用者運行) 需要對這些檔案有讀寫權限。

4.  **錯誤：網路設定後虛擬機器無法上網**
    *   **澄清**：
        *   **NAT 模式**：確保 KVM 主機已啟用 IP 轉發 (`net.ipv4.ip_forward=1`)，並且 `iptables` 規則正確配置了 MASQUERADE。
        *   **橋接模式**：確保 KVM 主機上的橋接介面 (例如 `br0`) 配置正確，並且虛擬機器連接到了該橋接。檢查橋接介面是否已將物理網卡加入，以及橋接自身是否有 IP 位址。

-----

## ### 小練習

#### #### 練習一：建立一個新的虛擬機器 (CentOS 7)

**目標**：透過 WebVirtMgr 介面，建立一個配置為 1 vCPU、1GB RAM、20GB 硬碟，並準備從 CentOS 7 ISO 檔案啟動的虛擬機器。

**假設條件**：
*   您已成功登入 WebVirtMgr。
*   您已連接到一個 KVM 主機。
*   KVM 主機上已有一個儲存池（例如 `default`），並且其中已上傳了 `CentOS-7-x86_64-Minimal-2009.iso` 檔案。
*   KVM 主機上已存在一個 Libvirt 虛擬網路（例如 `default`），類型為 NAT。

**步驟**：

1.  在 WebVirtMgr 介面左側導航欄，點擊 **「VMs」**。
2.  點擊右上角的 **「+ Add VM」** 按鈕。
3.  在彈出的建立虛擬機器精靈中，依序填寫以下資訊：
    *   **Name**：`CentOS-WebVirtMgr-Test`
    *   **CPUs**：`1`
    *   **Memory (MB)**：`1024`
    *   **Bridge**：`default` (選擇您的虛擬網路)
    *   **Video**：`VNC`
    *   **Graphics Password**：設定一個安全密碼 (例如：`YourSecurePassword`)
    *   **ISO Image**：選擇 `CentOS-7-x86_64-Minimal-2009.iso` (在「Choose Storage Volume」彈窗中選擇您的儲存池及 ISO 檔案)
    *   **Disk**：
        *   點擊 **「+ Add Disk」**。
        *   選擇 **「Create new disk」**。
        *   **Storage Pool**：選擇您的預設儲存池 (例如 `default`)。
        *   **Format**：`qcow2`
        *   **Size (GB)**：`20`
        *   點擊 **「Add」**。
4.  檢查所有設定是否正確。
5.  點擊底部的 **「Add」** 按鈕完成虛擬機器的建立。

**詳解**：

完成上述步驟後，WebVirtMgr 會向 KVM 主機發送指令。KVM 主機上的 Libvirt 會在 `default` 儲存池中建立一個 20GB 的 `CentOS-WebVirtMgr-Test.qcow2` 磁碟影像，然後建立一個名為 `CentOS-WebVirtMgr-Test` 的虛擬機器配置，該配置包含 1 vCPU、1GB 記憶體、連接到 `default` 虛擬網路的網卡，以及一個從 `CentOS-7-x86_64-Minimal-2009.iso` 啟動的光碟機。虛擬機器建立後，您可以在 `VMs` 列表中看到它，此時狀態應為 `Shutdown`。

---

#### #### 練習二：管理現有的虛擬機器與存取控制台

**目標**：啟動練習一中建立的 `CentOS-WebVirtMgr-Test` 虛擬機器，並透過 WebVirtMgr 的內建控制台進行互動。

**假設條件**：
*   您已完成練習一，`CentOS-WebVirtMgr-Test` 虛擬機器已建立。

**步驟**：

1.  在 WebVirtMgr 介面左側導航欄，點擊 **「VMs」**。
2.  在虛擬機器列表中找到 `CentOS-WebVirtMgr-Test`。
3.  點擊 `CentOS-WebVirtMgr-Test` 虛擬機器名稱，進入其詳細資訊頁面。
4.  在頁面頂部或右側的操作區，點擊 **「Power On」** 或 **「Start」** 按鈕啟動虛擬機器。
5.  等待虛擬機器啟動。啟動完成後，狀態會從 `Shutdown` 變為 `Running`。
6.  在操作區找到並點擊 **「Console」** 按鈕。
7.  一個新的瀏覽器視窗或標籤頁將會打開，顯示虛擬機器的 VNC 控制台。如果提示輸入密碼，請輸入您在練習一中設定的 Graphics Password (例如 `YourSecurePassword`)。
8.  在控制台內，您可以看到 CentOS 7 的安裝畫面。按照提示進行操作，例如選擇語言、鍵盤佈局，並開始安裝過程。
9.  完成安裝後，您可以回到虛擬機器詳細資訊頁面，點擊 **「Power Off」** 或 **「Shutdown」** 按鈕來關閉虛擬機器。

**詳解**：

點擊「Power On」後，WebVirtMgr 會呼叫 Libvirt API 啟動虛擬機器。當虛擬機器運行時，點擊「Console」會建立一個基於 WebSocket 的 VNC 連接，將虛擬機器的圖形輸出串流到您的瀏覽器。這使得您可以在不依賴任何外部 VNC 客戶端的情況下，直接從網頁瀏覽器管理虛擬機器的安裝和操作。安裝完成並關閉虛擬機器後，您可以移除 ISO 映像，並將其配置為從硬碟啟動。

-----

## ### 延伸閱讀/參考

*   **WebVirtMgr 官方 GitHub 專案**：[https://github.com/retspen/webvirtmgr](https://github.com/retspen/webvirtmgr) (包含安裝指南和最新資訊)
*   **Libvirt 官方文件**：[https://libvirt.org/](https://libvirt.org/) (深入了解 Libvirt API 和虛擬化概念)
*   **KVM 官方網站**：[https://www.linux-kvm.org/](https://www.linux-kvm.org/) (關於 KVM 虛擬化技術的基礎知識)
*   **Django 官方文件**：[https://docs.djangoproject.com/](https://docs.djangoproject.com/) (WebVirtMgr 所基於的 Web 框架)
*   **`virt-manager` 官方文件**：[https://virt-manager.org/](https://virt-manager.org/) (另一個受歡迎的 KVM GUI 管理工具)