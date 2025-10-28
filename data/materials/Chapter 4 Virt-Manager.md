# Chapter 4 Virt-Manager

本章將深入探討 Virt-Manager，一個用於管理 KVM/QEMU 虛擬機器的圖形化介面工具。我們將從其核心概念、安裝與基本操作開始，逐步學習如何建立、配置和管理虛擬機器，並探討其與其他相關技術的關聯及進階功能。

---

### 4.1 核心概念與定義

#### 4.1.1 什麼是 Virt-Manager？

**定義：** Virt-Manager (Virtual Machine Manager) 是一個輕量級的開源圖形化使用者介面 (GUI) 應用程式，用於管理基於 libvirt 服務的虛擬機器。它主要設計來管理 KVM (Kernel-based Virtual Machine) 虛擬機，但也能支援 QEMU、Xen 等其他虛擬化方案。

**核心觀念：**
*   **圖形化介面：** 提供直觀的視覺化操作，簡化虛擬機器的建立、配置和監控過程。
*   **libvirt 前端：** Virt-Manager 本身不直接與 KVM/QEMU 互動，而是透過 libvirt 庫進行操作。libvirt 是一個虛擬化管理工具集，提供一個通用的 API 來管理各種虛擬化技術。
*   **專為 KVM 優化：** 儘管支援多種虛擬化技術，但其設計和功能深度上與 KVM 的結合最為緊密。

**例子：** 想像你在廚房做飯，Virt-Manager 就是一個配備了各種按鈕和顯示幕的現代電磁爐，而 libvirt 則是控制電磁爐加熱、計時等功能的內部電路板，KVM/QEMU 則是實際產生熱量的加熱線圈。你透過電磁爐的介面（Virt-Manager）輕鬆地控制烹飪過程，而無需直接接觸或理解底層的電路和發熱原理。

#### 4.1.2 Virt-Manager 的運作原理

Virt-Manager 透過客戶端-伺服器模型工作。它作為客戶端應用程式運行在你的桌面上，然後透過 libvirt API 連接到一個或多個虛擬化主機（伺服器）。

**運作流程：**
1.  **使用者操作：** 你在 Virt-Manager 介面中點擊按鈕或輸入配置。
2.  **Virt-Manager -> libvirt：** Virt-Manager 將這些操作翻譯成 libvirt API 呼叫。
3.  **libvirt -> KVM/QEMU：** libvirt 守護程式 (libvirtd) 接收到呼叫後，會根據請求與底層的 KVM/QEMU 虛擬化層進行互動，執行如建立虛擬機、啟動、停止、分配資源等操作。
4.  **KVM/QEMU 執行：** KVM 核心模組在 Linux 核心中與 QEMU 程式協同工作，實際運行虛擬機器。
5.  **結果回饋：** 操作結果和虛擬機狀態會經由 libvirt 返回給 Virt-Manager，顯示在介面上。

**與相鄰概念的關聯：**
*   **與 libvirt 的關係：** Virt-Manager 是 libvirt 最受歡迎的圖形化前端之一。libvirt 提供底層的虛擬化管理抽象層，而 Virt-Manager 則提供使用者友善的介面。沒有 libvirt，Virt-Manager 就無法工作。
*   **與 KVM/QEMU 的關係：** KVM 是 Linux 核心中的虛擬化模組，負責 CPU 和記憶體的虛擬化。QEMU 則是一個通用的開源機器模擬器和虛擬化器。在 KVM 環境下，QEMU 作為一個前端，利用 KVM 的硬體虛擬化能力來提升效能。Virt-Manager 則是在這兩者之上提供了一個便利的管理層。

-----

### 4.2 典型例子與操作

#### 4.2.1 安裝 Virt-Manager

Virt-Manager 通常可以透過各 Linux 發行版的套件管理器進行安裝。

**範例：**
*   **在 Debian/Ubuntu 系統上：**
    ```bash
    sudo apt update
    sudo apt install virt-manager
    ```
*   **在 Fedora/CentOS/RHEL 系統上：**
    ```bash
    sudo dnf install virt-manager
    ```
安裝完成後，您可能需要將您的使用者帳戶加入 `libvirt` 群組，以便無需 `sudo` 即可管理虛擬機器：
```bash
sudo usermod -a -G libvirt $(whoami)
# 重新登入或重啟會話以使變更生效
```
確保 libvirt 服務正在運行：
```bash
sudo systemctl enable libvirtd --now
sudo systemctl status libvirtd
```

#### 4.2.2 連線到虛擬化主機

啟動 Virt-Manager 後，預設會自動連線到本地的 KVM/QEMU 實例。

*   **本地連線：**
    通常會自動連線到 `QEMU/KVM` 類型的 `qemu:///system`。這是最常見的連線方式，用於管理本機的虛擬機器。

*   **遠端連線：**
    Virt-Manager 支援透過 SSH 連線到遠端虛擬化主機。
    1.  點擊「檔案 (File)」->「新增連線 (Add connection)」。
    2.  選擇「超管理器 (Hypervisor)」為 `QEMU/KVM`。
    3.  勾選「遠端主機 (Remote host)」。
    4.  「方法 (Method)」選擇 `SSH`。
    5.  輸入「使用者名稱 (Username)」和「主機名稱 (Hostname)」。
    6.  點擊「連線 (Connect)」。
    **URI 範例：** `qemu+ssh://user@remotehost/system`
    這使得你可以從一台機器管理多台遠端伺服器上的虛擬機器。

#### 4.2.3 建立新的虛擬機器

這是 Virt-Manager 最核心的功能之一。

1.  **啟動新建 VM 精靈：**
    點擊主介面左上角的「建立新的虛擬機器 (Create a new virtual machine)」按鈕 (通常是一個電腦螢幕圖示)。

2.  **選擇安裝方式：**
    *   **本地安裝媒體 (ISO 映像)：** 最常用，從 ISO 檔案安裝作業系統。
    *   網路安裝 (Network Install)：透過網路啟動協定 (如 PXE)。
    *   匯入現有磁碟映像：使用已有的虛擬磁碟檔案。

3.  **指定 ISO 映像：**
    如果選擇本地安裝，瀏覽並選擇您的作業系統 ISO 檔案。精靈會嘗試根據 ISO 自動偵測作業系統類型。

4.  **設定記憶體與 CPU：**
    *   **記憶體 (RAM)：** 分配給虛擬機器的記憶體大小。
    *   **CPU 數量：** 分配給虛擬機器的虛擬處理器核心數。
    **提示：** 不建議分配超過物理主機一半的記憶體或 CPU 核心數，以免影響主機效能。

5.  **設定儲存空間：**
    *   **建立新的虛擬磁碟：** 推薦，指定磁碟大小。Virt-Manager 預設使用 QCOW2 格式，此格式支援快照和空間自動擴展。
    *   **選擇或自訂儲存：** 您也可以選擇已有的磁碟映像檔案或指定物理分區。

6.  **網路與名稱：**
    *   **網路選擇：** 預設通常是 `NAT (Virtual network 'default')`，讓 VM 可以上網，但外部網路無法直接訪問。
    *   **完成名稱：** 給虛擬機器一個有意義的名稱。

7.  **開始安裝：**
    點擊「完成 (Finish)」。Virt-Manager 會啟動虛擬機器，並顯示其控制台，您可以像在實體機器上一樣進行作業系統安裝。

#### 4.2.4 管理虛擬機器生命週期與資源

在 Virt-Manager 主介面中，你可以看到所有虛擬機器的列表。右鍵點擊虛擬機器或在選中後使用工具列按鈕，可以執行以下操作：

*   **啟動 (Start/Run)：** 開啟虛擬機器。
*   **關閉 (Shutdown)：** 正常關閉作業系統（如果 Guest Agent 安裝）。
*   **強制關機 (Force Off)：** 直接切斷電源，類似實體機斷電。
*   **暫停 (Pause)：** 暫停虛擬機器運行，保存其當前狀態於記憶體。
*   **恢復 (Resume)：** 從暫停狀態恢復運行。
*   **重啟 (Reboot)：** 重啟虛擬機器。
*   **刪除 (Delete)：** 從 libvirt 註冊中移除虛擬機器，並可選擇刪除其磁碟映像檔案。
*   **快照管理 (Snapshots)：**
    在選中虛擬機器後，點擊「詳細資訊 (Details)」視窗中的「快照 (Snapshots)」分頁。您可以建立、恢復和刪除虛擬機器的快照，這對於測試和回溯非常有用。
*   **編輯 VM 硬體 (Edit VM Hardware)：**
    選中虛擬機器後，點擊「詳細資訊 (Details)」按鈕，可以修改其硬體配置，如增加記憶體、CPU、添加或移除儲存設備、網卡、USB 裝置等。

-----

### 4.3 與相鄰概念的關聯

#### 4.3.1 Virt-Manager vs. `virsh` (命令列工具)

| 特性       | Virt-Manager (GUI)                       | `virsh` (CLI)                                  |
| :--------- | :--------------------------------------- | :--------------------------------------------- |
| **操作方式** | 圖形化介面，直觀易用                     | 命令列操作，需記憶指令與參數                   |
| **學習曲線** | 較低，適合新手或不常操作的場景           | 較高，但一旦熟悉後效率極高                     |
| **自動化** | 不適合直接自動化，需手動點擊             | 非常適合腳本編寫與自動化任務                   |
| **遠端管理** | 支援 SSH 遠端連線，操作與本地一致        | 可直接 SSH 到遠端主機執行，或使用 `virsh -c qemu+ssh://user@host/system ...` |
| **適用場景** | 單機管理、快速配置、監控、故障排除       | 大規模部署、自動化測試、批次操作、無頭伺服器管理 |

**關聯：** Virt-Manager 和 `virsh` 都是 libvirt 的前端工具。它們可以協同工作，例如你可以在 Virt-Manager 中建立虛擬機後，再使用 `virsh` 進行自動化管理或更精細的配置。了解 `virsh` 能幫助你更深入理解 Virt-Manager 背後的機制。

#### 4.3.2 Virt-Manager vs. Web 介面 (如 Cockpit、Proxmox VE)

| 特性       | Virt-Manager (桌面應用)                  | Web 介面 (瀏覽器)                              |
| :--------- | :--------------------------------------- | :--------------------------------------------- |
| **部署**   | 作為桌面應用安裝在管理工作站             | 作為服務安裝在虛擬化主機或獨立伺服器上         |
| **存取方式** | 需要在安裝了 Virt-Manager 的機器上運行   | 任何有瀏覽器的設備皆可存取                     |
| **功能範圍** | 主要專注於 KVM/QEMU 的單機或遠端管理     | 通常提供更廣泛的系統管理功能 (如 Cockpit)，或專為集群設計 (如 Proxmox VE) |
| **擴展性** | 較適合管理數台遠端主機                   | 更適合管理大型虛擬化集群，多主機統一視圖       |

**關聯：** Virt-Manager 是一個專為桌面使用者設計的工具，提供精細的單機虛擬機管理。而 Cockpit 這樣的 Web 介面則旨在提供更全面的伺服器管理，其中包含了虛擬化管理模組。Proxmox VE 則是一個完整的、基於 Debian 的虛擬化平台，自帶其強大的 Web 介面，更側重於集群管理和企業級應用。三者各有優勢，適用於不同的管理需求和環境。

#### 4.3.3 Virt-Manager vs. 底層 KVM/QEMU

**關聯：** Virt-Manager 透過 libvirt 提供了一個高階的抽象層，將 KVM/QEMU 的複雜性隱藏起來。這讓使用者可以透過圖形化介面來配置 CPU 型號、記憶體、硬碟類型、網路卡等參數，而無需手動編寫 QEMU 命令列參數或直接操作 KVM 模組。它極大地降低了使用 KVM/QEMU 的門檻，但同時也保留了在虛擬機詳細資訊中查看或編輯底層 XML 配置的能力，讓有經驗的使用者能進行更深度的客製化。

-----

### 4.4 進階內容

#### 4.4.1 網路設定詳解

在 Virt-Manager 中，虛擬機器的網路配置是其與外部世界互動的關鍵。

*   **NAT (預設虛擬網路 'default')：**
    *   **核心觀念：** 虛擬機在一個由 libvirt 管理的私有網路中，透過主機進行網路位址轉換 (NAT) 才能訪問外部網路。外部網路無法主動連線到虛擬機。
    *   **優點：** 配置簡單，無需主機額外設定，即可讓虛擬機上網。
    *   **缺點：** 虛擬機沒有獨立的外部 IP，無法作為伺服器被外部網路直接存取。
    *   **適用場景：** 大多數桌面虛擬機、需要單純上網的測試環境。

*   **橋接模式 (Bridge Mode)：**
    *   **核心觀念：** 虛擬機的網路介面卡直接連接到主機的物理網路介面卡所連接的橋接 (bridge) 裝置上。虛擬機與主機在同一個物理網段中，擁有與物理機同等地位的獨立 IP 位址。
    *   **優點：** 虛擬機擁有獨立 IP，可以被外部網路直接訪問，適合部署伺服器。
    *   **缺點：** 需要在主機上建立和配置橋接介面（例如 `br0`），相對複雜。
    *   **適用場景：** 虛擬伺服器、需要外部網路直接訪問的服務。

*   **隔離網路 (Isolated Network)：**
    *   **核心觀念：** 僅限於特定虛擬機器之間或主機與虛擬機器之間通訊的私有網路，不連接到任何物理網路介面。
    *   **優點：** 提供高安全性的隔離環境。
    *   **適用場景：** 建立內部實驗室環境，或需要多個虛擬機相互通訊而不接觸外部網路的情況。

**配置路徑：**
1.  在 Virt-Manager 主介面點擊「編輯 (Edit)」->「連線詳細資訊 (Connection Details)」。
2.  選擇「虛擬網路 (Virtual Networks)」分頁，可以查看、建立或修改虛擬網路。
3.  在 VM 的「詳細資訊 (Details)」視窗中，選擇「網卡 (NIC)」設備，可以將其連接到不同的虛擬網路或橋接介面。

#### 4.4.2 儲存管理

Virt-Manager 透過 libvirt 的儲存池 (Storage Pools) 和卷 (Volumes) 概念來管理虛擬機器的磁碟。

*   **儲存池 (Storage Pools)：**
    *   **定義：** 一個抽象的儲存空間，可以是目錄、LVM 卷組、iSCSI 目標、NFS 共享等。libvirt 在此儲存池中建立、管理虛擬磁碟檔案。
    *   **範例：**
        *   `default` 儲存池：通常指向 `/var/lib/libvirt/images` 目錄，用於存放虛擬磁碟映像檔案。
        *   建立一個新的「目錄 (dir)」類型儲存池，指定一個新的路徑，例如 `/data/vm_disks`。
    *   **管理：** 在「編輯 (Edit)」->「連線詳細資訊 (Connection Details)」->「儲存 (Storage)」分頁。

*   **卷 (Volumes)：**
    *   **定義：** 在儲存池中分配的具體儲存單元，即虛擬機器使用的磁碟檔案或邏輯卷。
    *   **磁碟格式：**
        *   **QCOW2 (QEMU Copy-On-Write)：** 預設且推薦的格式。支援快照、空間精簡配置 (thin provisioning, 按需分配空間)、加密等功能。
        *   **RAW：** 原始格式，效能略高，但不支援上述進階功能。
    *   **管理：** 在儲存池中建立新的卷，或在 VM 的「詳細資訊 (Details)」視窗中「新增硬體 (Add Hardware)」->「儲存 (Storage)」來掛載。

#### 4.4.3 USB 裝置傳遞 (USB Passthrough)

Virt-Manager 允許您將主機上的 USB 裝置直接傳遞給虛擬機器使用。

**步驟：**
1.  確保 USB 裝置已連接到主機。
2.  開啟虛擬機器的「詳細資訊 (Details)」視窗。
3.  點擊左下角的「新增硬體 (Add Hardware)」。
4.  在左側選擇「USB 主機裝置 (USB Host Device)」。
5.  從列表中選擇要傳遞的 USB 裝置。
6.  點擊「完成 (Finish)」。
此後，該 USB 裝置將從主機上「消失」，並出現在虛擬機器中。

**注意事項：**
*   同一時間只能有一個系統（主機或虛擬機）擁有該 USB 裝置的控制權。
*   某些 USB 裝置在傳遞後可能需要重新插入才能被虛擬機識別。

-----

### 4.5 常見錯誤與澄清

#### 4.5.1 無法連線到 `qemu:///system`

**問題：** 啟動 Virt-Manager 後，顯示無法連線到預設的 KVM/QEMU 實例。
**原因與澄清：**
*   **libvirtd 服務未運行：** libvirt 守護程式 `libvirtd` 是 Virt-Manager 溝通的橋樑，如果它沒有運行，連線會失敗。
    *   **解決方案：** 檢查服務狀態並啟動它：`sudo systemctl status libvirtd`，如果未運行則 `sudo systemctl start libvirtd` 或 `sudo systemctl enable libvirtd --now`。
*   **使用者權限不足：** 您的使用者帳戶沒有足夠的權限訪問 libvirt socket。
    *   **解決方案：** 確保您的使用者帳戶已加入 `libvirt` 群組，並重新登入：`sudo usermod -a -G libvirt $(whoami)`。
*   **防火牆阻擋：** 如果是遠端連線，主機防火牆可能阻擋了 SSH 連線。
    *   **解決方案：** 確保 SSH 埠 (預設 22) 在防火牆中是開放的。

#### 4.5.2 虛擬機器網路不通或無法上網

**問題：** 虛擬機器啟動後無法上網或與其他機器通訊。
**原因與澄清：**
*   **NAT 模式下 DNS 或 IP 問題：**
    *   **解決方案：** 檢查虛擬機內部網路設定，確保 DHCP 正常工作，或者手動設定 DNS 伺服器 (如 8.8.8.8)。
*   **橋接模式配置錯誤：**
    *   **解決方案：**
        1.  確認主機上已正確建立橋接介面（例如 `br0`），並且該橋接介面已關聯到物理網卡。
        2.  確認虛擬機的網卡已正確連接到該橋接介面。
        3.  檢查主機防火牆規則，確保沒有阻擋橋接介面的流量。
        4.  確認虛擬機內的網路設定與所在網段相符，例如是否取得了正確的 IP 位址。
*   **虛擬機內防火牆：** 有時虛擬機器作業系統本身的防火牆（如 Windows Firewall, `ufw` on Linux）會阻擋連線。
    *   **解決方案：** 暫時關閉虛擬機內部防火牆進行測試，若解決則需配置防火牆規則。

#### 4.5.3 虛擬機器啟動失敗或效能低下

**問題：** 虛擬機器無法啟動，或啟動後運行非常緩慢。
**原因與澄清：**
*   **主機未啟用硬體虛擬化：** KVM 虛擬化要求 CPU 支援 Intel VT-x 或 AMD-V 技術，並且在 BIOS/UEFI 中啟用。
    *   **解決方案：** 進入主機的 BIOS/UEFI 設定，找到並啟用「Intel Virtualization Technology」或「AMD-V」。
*   **KVM 模組未載入：** KVM 核心模組可能沒有載入。
    *   **解決方案：** 檢查：`lsmod | grep kvm`。如果沒有輸出，嘗試 `sudo modprobe kvm_intel` 或 `sudo modprobe kvm_amd`。
*   **資源不足：** 分配給虛擬機器的記憶體或 CPU 超過主機可用資源。
    *   **解決方案：** 減少虛擬機器的記憶體或 CPU 分配。
*   **ISO 映像或磁碟映像損壞：**
    *   **解決方案：** 重新下載 ISO 檔案，或檢查磁碟映像檔案的完整性。
*   **Guest Tools 未安裝：** 在 Windows 虛擬機中，未安裝 `virtio` 驅動和 `qemu-guest-agent` 可能導致滑鼠/鍵盤延遲、解析度不對、Guest Shut Down 無法使用等問題。
    *   **解決方案：** 下載並安裝 `virtio-win-guest-tools` 套件。

-----

### 4.6 小練習（附詳解）

#### 小練習一：使用 Virt-Manager 建立一個新的 Linux 虛擬機器

**目標：** 透過 Virt-Manager 建立一個新的虛擬機器，並準備好安裝一個 Linux 作業系統（例如 Ubuntu Server）。

**步驟：**

1.  **準備 ISO 映像：**
    下載一個 Ubuntu Server 的 ISO 映像檔案，例如 `ubuntu-22.04.3-live-server-amd64.iso`。將其放置在主機上的易於存取的目錄，例如 `~/Downloads`。

2.  **啟動 Virt-Manager：**
    在您的 Linux 桌面上啟動 Virtual Machine Manager 應用程式。

3.  **建立新的虛擬機器：**
    點擊主介面左上角的「建立新的虛擬機器」按鈕。

4.  **選擇安裝方式：**
    選擇「本地安裝媒體 (ISO 映像)」。點擊「前進 (Forward)」。

5.  **指定 ISO 映像：**
    *   點擊「瀏覽 (Browse)」。
    *   在「定位或建立儲存卷 (Locate or create storage volume)」對話框中，點擊「瀏覽本地 (Browse Local)」。
    *   導航到您存放 ISO 檔案的目錄，選擇 `ubuntu-22.04.3-live-server-amd64.iso`。
    *   「作業系統類型 (OS Type)」和「版本 (Version)」會自動偵測為「Linux」和「Ubuntu 22.04」。如果沒有，請手動選擇。
    點擊「前進」。

6.  **配置記憶體與 CPU：**
    *   **記憶體 (RAM)：** 輸入 `2048` (2 GB)。
    *   **CPU 數量：** 輸入 `2`。
    點擊「前進」。

7.  **配置儲存空間：**
    *   選擇「為虛擬機器建立一個磁碟映像 (Create a disk image for the virtual machine)」。
    *   **磁碟大小：** 輸入 `20` (20 GB)。
    *   確保「啟用儲存空間」被勾選。
    點擊「前進」。

8.  **命名與網路設定：**
    *   **名稱：** 輸入 `Ubuntu-Server-Test`。
    *   **網路選擇：** 保持預設的「虛擬網路 'default'：NAT」。
    *   勾選「安裝前自訂配置 (Customize configuration before install)」。
    點擊「完成 (Finish)」。

9.  **檢查並調整硬體配置（可選）：**
    此時會打開一個「Ubuntu-Server-Test (正在關閉)」的視窗。你可以檢視和調整硬體配置。
    *   **CPU：** 檢查是否已設定為 2 核心。
    *   **記憶體：** 檢查是否已設定為 2048 MiB。
    *   **網卡：** 預設為 `VirtIO` 類型，連接到 `default` 虛擬網路。
    *   **BIOS：** 建議將其更改為「UEFI x86_64」。點擊「韌體 (Firmware)」選項，選擇 `UEFI x86_64: /usr/share/OVMF/OVMF_CODE.fd`。
    *   **啟動選項 (Boot Options)：** 勾選「啟用啟動選單 (Enable boot menu)」，並將「CDROM」拖曳到第一個啟動裝置。

10. **開始安裝：**
    點擊左上角的「開始安裝 (Begin Installation)」按鈕 (綠色箭頭)。虛擬機器將啟動，並顯示 Ubuntu Server 的安裝介面。

---

#### 小練習二：將虛擬機器網路模式從 NAT 更改為橋接模式

**目標：** 將現有虛擬機器的網路介面從預設的 NAT 模式更改為橋接模式，使其能夠從外部網路直接存取。

**前置準備：在主機上建立一個橋接介面**
本練習假設您的主機系統為 Ubuntu/Debian，並且您已了解如何配置橋接網路。以下提供一個簡單的 `netplan` 配置範例。
1.  **編輯 Netplan 配置檔：**
    ```bash
    sudo vim /etc/netplan/01-netcfg.yaml
    ```
    範例內容（請根據您實際的網路介面名稱 `enpXsY` 和 IP 配置修改）：
    ```yaml
    network:
      version: 2
      renderer: networkd
      ethernets:
        enp0s3: # 這是您的物理網卡名稱，請替換
          dhcp4: no
      bridges:
        br0:
          interfaces: [enp0s3] # 將物理網卡加入橋接
          dhcp4: yes         # 或靜態 IP 配置
          # 或者配置靜態 IP
          # addresses: [192.168.1.10/24]
          # gateway4: 192.168.1.1
          # nameservers:
          #   addresses: [8.8.8.8, 8.8.4.4]
    ```
2.  **應用 Netplan 配置：**
    ```bash
    sudo netplan apply
    ip a # 檢查 br0 是否已建立並獲得 IP
    ```
    **注意：** 確保橋接介面 `br0` 已成功建立並獲取 IP。如果遇到問題，請先解決主機的橋接網路配置。

**步驟：**

1.  **關閉虛擬機器：**
    在 Virt-Manager 中，找到您要修改的虛擬機器（例如小練習一建立的 `Ubuntu-Server-Test`），確保其處於「已關閉 (Shutoff)」狀態。如果正在運行，請先關機。

2.  **開啟虛擬機器詳細資訊：**
    選中虛擬機器，點擊工具列上的「開啟 (Open)」按鈕，或者雙擊虛擬機器列表中的項目，開啟虛擬機器的詳細資訊視窗。

3.  **導航到硬體列表：**
    在詳細資訊視窗的左側硬體列表，找到並點擊「網卡 (NIC)」裝置。

4.  **修改網路設定：**
    *   **網絡源 (Network source)：** 將選項從「虛擬網路 (Virtual network)」改為「主機裝置：橋接 (Host device: Bridge)」。
    *   **裝置名稱 (Device name)：** 在下拉列表中選擇您剛才在主機上建立的橋接介面，例如 `br0`。
    *   **裝置模型 (Device model)：** 建議保持 `virtio` 以獲得最佳效能。
    *   點擊「應用 (Apply)」。

5.  **啟動虛擬機器並驗證：**
    *   點擊「開始虛擬機器 (Start virtual machine)」按鈕。
    *   進入虛擬機器的控制台。
    *   在虛擬機器內部，檢查其網路配置，例如使用 `ip a` 命令（Linux）或 `ipconfig` 命令（Windows）。
    *   驗證虛擬機器是否已獲得與主機橋接介面同網段的 IP 位址，並且能夠訪問外部網路，同時也可以從外部網路 SSH 或 ping 到該虛擬機器的 IP。

**詳解與驗證：**
*   **成功後的觀察：** 虛擬機器的 IP 位址將會與主機的 `br0` 介面位於同一個子網內。例如，如果您的 `br0` 是 `192.168.1.10/24`，那麼虛擬機器可能會獲得 `192.168.1.x/24` 的 IP。
*   **測試連線：**
    *   從虛擬機內部：`ping google.com` (測試對外連線)。
    *   從主機或外部網路：`ping <虛擬機器IP>` 或 `ssh <使用者@虛擬機器IP>` (測試對內連線)。
*   **常見問題排除：** 如果虛擬機沒有獲得 IP，檢查虛擬機內部是否設定為 DHCP，或檢查主機防火牆是否阻擋了流量。

-----

### 4.7 延伸閱讀/參考

*   **Virt-Manager 官方文件：** [https://virt-manager.org/](https://virt-manager.org/)
*   **libvirt 官方文件：** [https://libvirt.org/](https://libvirt.org/)
*   **KVM 官方網站：** [https://www.linux-kvm.org/](https://www.linux-kvm.org/)
*   **QEMU 官方網站：** [https://www.qemu.org/](https://www.qemu.org/)
*   **Red Hat Virtualization 文件：** (提供大量 KVM/libvirt 的實務操作指南)
    *   例如：[https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/8/html/configuring_and_managing_virtualization/index](https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/8/html/configuring_and_managing_virtualization/index)
*   **鳥哥的 Linux 私房菜 – KVM 虛擬機管理：** (繁體中文資源，深入淺出)
    *   您可以搜尋該網站相關章節以獲取更多資訊。