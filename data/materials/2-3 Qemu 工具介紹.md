主題：2-3 Qemu 工具介紹

-----

### 1. 核心概念與定義：Qemu 是什麼？

Qemu (Quick Emulator) 是一個開源的虛擬化與模擬器軟體，它允許您在不同的硬體架構上運行作業系統或程式。它以其高度的靈活性和廣泛的硬體支援而聞名。

#### 1.1 Qemu 的定義與雙重角色

Qemu 扮演著兩種主要角色：

*   **完整系統模擬器 (System Emulator)**：當您的 Guest OS (客戶作業系統) 所設計的 CPU 架構與 Host OS (主機作業系統) 的 CPU 架構不同時，Qemu 會動態地將 Guest OS 的 CPU 指令翻譯成 Host OS 可執行的指令。例如，在 x86 架構的電腦上運行 ARM 架構的 Android 系統。這種模式下，Qemu 會模擬整個電腦系統，包括 CPU、記憶體、硬碟、網路卡等。
*   **虛擬化器 (Virtualizer)**：當 Guest OS 的 CPU 架構與 Host OS 的 CPU 架構相同時，Qemu 可以利用 Host CPU 的硬體虛擬化擴展（如 Intel VT-x 或 AMD-V）來直接執行 Guest OS 的指令，從而大幅提升性能。這種模式通常與 KVM (Kernel-based Virtual Machine) 核心模組結合使用，此時 Qemu 負責模擬週邊硬體設備，而 KVM 則處理 CPU 和記憶體的虛擬化。

**核心觀念：** Qemu 的獨特之處在於它能無縫地切換於「完全模擬」和「硬體加速虛擬化」之間，取決於 Guest/Host 的架構匹配程度及硬體虛擬化支援。

#### 1.2 Qemu 的主要功能

Qemu 提供了一系列強大的功能，使其成為虛擬化領域的重要工具：

*   **硬體模擬 (Hardware Emulation)**：能夠模擬多種 CPU 架構（x86、ARM、PowerPC、MIPS、SPARC 等）及各式週邊硬體設備（IDE、SCSI、SATA、網路卡、USB 等）。
*   **系統虛擬化 (System Virtualization)**：能夠運行完整的客戶作業系統，如 Linux、Windows、BSD 等。
*   **使用者模式虛擬化 (User-mode Virtualization)**：可以在一個 CPU 架構上執行為另一個 CPU 架構編譯的單一使用者空間程式（較少用於一般虛擬機器）。
*   **快照 (Snapshots)**：允許用戶在虛擬機器運行的任何時刻保存其狀態，並隨時恢復。
*   **網路與儲存**：提供多種網路模式（NAT、橋接等）和儲存接口（IDE、SATA、VirtIO 等）。
*   **開源與跨平台**：Qemu 是開源軟體，可在 Linux、macOS、Windows 等多個作業系統上運行。

#### 1.3 Qemu 的工作原理概觀

Qemu 的工作原理可以簡化為以下兩種情境：

*   **純模擬模式 (當 `-enable-kvm` 不可用或 Guest/Host 架構不匹配時)**
    *   Qemu 透過動態二進位翻譯 (Dynamic Binary Translation, DBT) 技術，將 Guest OS 發出的每一條 CPU 指令即時翻譯成 Host OS 可執行的指令序列。
    *   同時，Qemu 模擬 Guest OS 所需的所有硬體設備。
    *   **優點：** 靈活性高，可跨架構運行。
    *   **缺點：** 性能開銷大，因為每個指令都需要翻譯。

*   **KVM 虛擬化模式 (當 Guest/Host 架構匹配且 `-enable-kvm` 啟用時)**
    *   Qemu 作為一個用戶空間進程，與 KVM 核心模組協同工作。
    *   **KVM 核心模組：** 利用 Host CPU 的硬體虛擬化功能（VT-x/AMD-V），直接執行 Guest OS 的 CPU 指令，並處理記憶體管理。Guest OS 的敏感指令（如訪問特權資源）會觸發 Host CPU 的虛擬化擴展，KVM 會截獲並處理這些指令。
    *   **Qemu 進程：** 負責模擬除了 CPU 和記憶體之外的所有週邊硬體設備（如網路卡、硬碟控制器、顯示卡等）。它將 Guest OS 對這些設備的訪問請求轉換為 Host OS 的實際操作。
    *   **優點：** 性能接近原生，因為大部分 CPU 指令直接執行。
    *   **缺點：** 只能在相同 CPU 架構下運行，且需要 Host CPU 支援硬體虛擬化。

**與相鄰概念的關聯：** KVM 是 Linux 核心的一個模組，它提供了底層的硬體虛擬化介面。Qemu 則是一個用戶空間的應用程式，它利用 KVM 提供的介面來實現高性能的虛擬化，同時補充 KVM 無法直接處理的硬體模擬部分。可以說，KVM 是「引擎」，而 Qemu 則是「車身」，兩者結合才構成一輛完整的「高性能虛擬機器」。

-----

### 2. 典型例子與基本指令介紹

Qemu 的操作通常透過命令列進行。以下介紹兩個最常用的工具：`qemu-img` 用於管理磁碟映像檔，`qemu-system-ARCH` 用於啟動虛擬機器。

#### 2.1 Qemu 的基本元件

*   **`qemu-img`**：這是 Qemu 的磁碟映像檔管理工具，用於建立、轉換、檢查和修改虛擬磁碟映像檔。
*   **`qemu-system-ARCH`**：這是 Qemu 系統模擬器的主程式，`ARCH` 代表目標 CPU 架構，例如 `qemu-system-x86_64` 用於模擬 64 位元 x86 系統，`qemu-system-arm` 用於模擬 ARM 系統。

#### 2.2 建立虛擬磁碟映像檔

虛擬機器需要一個虛擬硬碟來安裝作業系統和儲存資料。`qemu-img` 命令用於管理這些磁碟映像檔。

**核心指令：** `qemu-img create -f <格式> <檔名> <大小>`

**範例：**
建立一個名為 `my_vm_disk.qcow2`、大小為 10GB 的 qcow2 格式虛擬磁碟。`qcow2` 是 Qemu 推薦的格式，支援快照、CoW (Copy-on-Write) 等特性，並且是稀疏檔案 (Sparse File)，即初始時只佔用實際寫入的空間，而不是預分配全部空間。

```bash
qemu-img create -f qcow2 my_vm_disk.qcow2 10G
```

*   `-f qcow2`：指定映像檔格式為 qcow2。
*   `my_vm_disk.qcow2`：指定映像檔的名稱。
*   `10G`：指定虛擬磁碟的最大大小為 10 GB。

**推導：** 您也可以使用 `raw` 格式，它是一個簡單的位元組流，與實際物理磁碟的映像相同。然而，`qcow2` 由於其高級特性，通常是更好的選擇。

```bash
qemu-img create -f raw my_raw_disk.img 5G
```

#### 2.3 啟動一個虛擬機器

啟動 Qemu 虛擬機器涉及多個參數，用於指定虛擬機器的硬體配置。

**核心指令：** `qemu-system-x86_64 [選項] ...`

**範例：**
假設您有一個名為 `tinycore.iso` 的 Linux 安裝映像檔，並且已經建立了 `my_vm_disk.qcow2`。以下指令將啟動一個具有 1GB 記憶體、2 個 CPU 核心，並從 ISO 啟動的虛擬機器，同時啟用 KVM 加速。

```bash
qemu-system-x86_64 \
    -enable-kvm \                      # 啟用 KVM 硬體加速，若不支持則會自動降級為純模擬
    -m 1024 \                          # 設定虛擬機器記憶體為 1024 MB (1GB)
    -smp 2 \                           # 設定虛擬機器為 2 個 CPU 核心
    -cpu host \                        # 讓 Qemu 虛擬出與 Host CPU 相同的功能，以獲得最佳兼容性和性能
    -hda my_vm_disk.qcow2 \            # 掛載虛擬磁碟映像檔作為主硬碟 (hda)
    -cdrom tinycore.iso \              # 掛載 ISO 映像檔作為 CD-ROM
    -boot d \                          # 設定開機順序，'d' 代表從 CD-ROM 開機
    -vnc :0 \                          # 啟用 VNC 伺服器，並監聽 Host 的 5900 端口（:0 代表端口 5900）
    -netdev user,id=vnet0 \            # 設定使用者模式網路，ID 為 vnet0
    -device virtio-net-pci,netdev=vnet0 # 虛擬網路卡使用 VirtIO 驅動，連接到 vnet0
```

*   **主要參數解釋：**
    *   `-enable-kvm`: 啟用 KVM 硬體加速。如果您的系統支援並已啟用 KVM，這將大大提高性能。
    *   `-m <記憶體大小>`: 設定虛擬機器的記憶體大小，單位可以是 `M` 或 `G`。
    *   `-smp <核心數>`: 設定虛擬機器的 CPU 核心數量。
    *   `-cpu host`: 讓 Qemu 模擬一個與主機 CPU 型號和功能最匹配的 CPU，這通常能提供最佳性能和兼容性。
    *   `-hda <磁碟映像檔>`: 指定一個磁碟映像檔作為虛擬機器的第一個硬碟。您也可以使用 `-hdd`, `-hdc` 等。
    *   `-cdrom <ISO 檔>`: 掛載一個 ISO 檔案作為虛擬機器的 CD-ROM。
    *   `-boot <順序>`: 設定虛擬機器的開機順序。`a` (軟碟), `c` (硬碟), `d` (CD-ROM), `n` (網路)。
    *   `-vnc :<顯示號碼>`: 啟用 VNC 伺服器，允許您透過 VNC 客戶端連接到虛擬機器的圖形界面。`:0` 表示監聽 Host 的 5900 端口，`:1` 表示 5901 端口，依此類推。
    *   `-nographic`: 如果您不需要圖形界面，只想在終端中查看虛擬機器的控制台輸出，可以使用此選項。
    *   `-netdev user,id=vnet0`: 配置使用者模式網路。這是最簡單的網路配置，VM 內部會自動獲得一個 IP (通常是 10.0.2.15)，並可以透過 Host 進行 NAT 訪問外部網路。
    *   `-device virtio-net-pci,netdev=vnet0`: 將一個 `virtio-net-pci` 網路設備附加到虛擬機器，並連接到 ID 為 `vnet0` 的網路設定。`virtio-net-pci` 是一種高性能的半虛擬化網路驅動，需要 Guest OS 支援 VirtIO 驅動。

#### 2.4 Qemu 提供的裝置類型

Qemu 提供了多種模擬裝置，您可以根據性能需求選擇。

*   **儲存控制器：**
    *   **IDE (如 `-hda`)**：通用，兼容性最佳，但性能一般。
    *   **SATA (如 `-device ide-drive,drive=disk1`)**：較新的通用接口。
    *   **VirtIO-BLK (如 `-device virtio-blk-pci,drive=disk1`)**：半虛擬化接口，性能最佳，需要 Guest OS 支援 VirtIO 驅動。
*   **網路卡：**
    *   **e1000 (如 `-device e1000,netdev=net0`)**：模擬 Intel E1000 網路卡，兼容性好。
    *   **VirtIO-Net (如 `-device virtio-net-pci,netdev=net0`)**：半虛擬化接口，性能最佳，需要 Guest OS 支援 VirtIO 驅動。
*   **顯示卡：**
    *   **VGA (預設)**：基本顯示，兼容性最佳。
    *   **virtio-gpu**：半虛擬化顯示卡，性能較好，通常搭配 SPICE 協定使用。

**關聯：** 為了獲得最佳性能，強烈建議在 Guest OS 中安裝並使用 **VirtIO** 系列驅動程式，這些驅動可以讓 Guest OS 直接與 Qemu/KVM 介面溝通，減少模擬層的開銷。

-----

### 3. 與相鄰概念的關聯

#### 3.1 Qemu 與 KVM 的關係

如前所述，Qemu 和 KVM 經常一起提及，但它們扮演的角色不同。

*   **Qemu (用戶空間)**：一個通用的虛擬機器監視器 (VMM, Virtual Machine Monitor) 和模擬器。它提供虛擬機器的 BIOS、周邊設備（如網路卡、硬碟控制器、顯示卡等）的模擬，以及客戶作業系統的管理功能。
*   **KVM (核心空間)**：一個 Linux 核心模組，它將 Linux 核心變為一個 Hypervisor（Type-1 或 Type-2，取決於如何定義），利用 CPU 的硬體虛擬化擴展 (Intel VT-x, AMD-V) 來直接運行客戶作業系統的 CPU 指令，並處理記憶體管理。

**關聯：** Qemu 在沒有 KVM 的情況下可以獨立運行，作為一個純粹的模擬器，但性能較差。當 Qemu 結合 KVM 運行時（使用 `-enable-kvm` 選項），Qemu 負責硬體模擬和管理，而 KVM 則負責提供接近原生的 CPU 和記憶體虛擬化性能。這種組合被稱為「KVM/Qemu」，是 Linux 上主流且高效的虛擬化解決方案。

#### 3.2 Qemu 與其他虛擬化技術

*   **與 VirtualBox/VMware Workstation**：
    *   **Qemu**：通常是命令行驅動，提供更底層、更細粒度的控制，支援更廣泛的硬體模擬和 CPU 架構。它是一個組件化的工具，可以被其他更上層的管理工具（如 virt-manager）整合。
    *   **VirtualBox/VMware Workstation**：提供圖形化界面，用戶體驗更友好，通常針對桌面級虛擬化設計。它們是更完整的產品，內建了自己的 Hypervisor。底層也可能利用 KVM (在 Linux 上) 或自己的虛擬化技術。
    **關聯：** Qemu 提供了這些商業產品所依賴的許多核心虛擬化能力。對於需要高度客製化、自動化或伺服器環境的用戶，Qemu 更具優勢。

*   **與 Docker/LXC (容器化技術)**：
    *   **Qemu**：實現的是**硬體層級的虛擬化 (Hardware Virtualization)**，每個虛擬機器都有自己的獨立核心和完整的作業系統環境。這提供了最高的隔離性。
    *   **Docker/LXC**：實現的是**作業系統層級的虛擬化 (OS-level Virtualization)** 或稱為容器化。所有容器共用主機的 Linux 核心，僅隔離了應用程式的運行環境、檔案系統和網路。
    **關聯：** 兩者解決的問題和提供的隔離級別不同。Qemu 適用於需要運行不同作業系統或需要強隔離性的場景（例如測試不同核心版本，或運行 Windows VM），而容器適用於輕量級、快速部署應用程式的場景，性能開銷極低。

-----

### 4. 進階內容：網路配置與遠端連接

Qemu 的網路配置是其複雜但強大的功能之一，遠端連接也至關重要。

#### 4.1 簡單網路配置：使用者模式網路 (User-mode Networking)

這是最簡單的 Qemu 網路模式，無需複雜的 Host 網路配置。

**核心觀念：** Qemu 在 Host 上為虛擬機器建立一個內建的 NAT (Network Address Translation) 路由器。Guest VM 透過這個路由器連接到外部網路。

**範例：**
在啟動指令中加入：
```bash
-netdev user,id=vnet0,hostfwd=tcp::2222-:22 \ # 啟用使用者模式網路，並將 Host 的 2222 端口轉發到 Guest 的 22 端口 (SSH)
-device virtio-net-pci,netdev=vnet0         # 使用 VirtIO 網路卡連接到此網路
```
*   `user,id=vnet0`：啟動使用者模式網路，並給它一個 ID。
*   `hostfwd=tcp::2222-:22`：這是端口轉發規則。它表示將 Host 機器的 TCP 2222 端口收到的流量，轉發到 Guest 機器的 TCP 22 端口。這使得您可以從 Host 透過 SSH 連接到 Guest VM。

**優點：** 設定簡單，無需 Host 上的特權權限。
**缺點：** Guest VM 無法直接從 Host 的外部網路被訪問；Guest VM 之間預設無法直接通訊；性能一般。

#### 4.2 遠端連接：VNC 與 SSH

*   **VNC (Virtual Network Computing)**：用於遠端連接虛擬機器的圖形界面。
    *   在 Qemu 啟動指令中加入 `-vnc :<顯示號碼>`。例如 `-vnc :0` 將在 Host 的 5900 端口啟動 VNC 伺服器。
    *   之後，您可以使用任何 VNC 客戶端（如 `Remmina`, `TightVNC Viewer`）連接到 `localhost:5900`。
*   **SSH (Secure Shell)**：用於遠端命令行連接 Guest VM。
    *   需要在 Guest OS 內部安裝並啟用 SSH 伺服器。
    *   透過使用者模式網路的端口轉發 (`hostfwd=tcp::2222-:22`)，您可以從 Host 透過 `ssh -p 2222 user@localhost` 連接到 Guest VM。

**推導：** 對於無圖形界面的伺服器 VM，SSH 是最常見的遠端管理方式。對於有圖形界面的桌面 VM，VNC 提供了完整的圖形體驗。

-----

### 5. 常見錯誤與澄清

#### 5.1 KVM 無法啟用 (`-enable-kvm` 失敗)

**現象：** 執行 Qemu 時，報錯「KVM is not available. Emulation is slower.」或類似錯誤。

**原因與澄清：**
1.  **Host CPU 不支援硬體虛擬化：** 您的 CPU (Intel 或 AMD) 可能不支援 Intel VT-x 或 AMD-V 技術。您可以檢查 `/proc/cpuinfo` 中的 `vmx` (Intel) 或 `svm` (AMD) 標誌。
2.  **BIOS/UEFI 中未啟用：** 即使 CPU 支援，也可能在 BIOS/UEFI 設定中被禁用。您需要進入 BIOS/UEFI 啟用相關選項（通常在 "Virtualization Technology" 或 "VT-x/AMD-V" ）。
3.  **KVM 核心模組未載入：** 在 Linux 上，KVM 需要對應的核心模組載入才能使用。
    *   檢查：`lsmod | grep kvm`
    *   載入：`sudo modprobe kvm_intel` 或 `sudo modprobe kvm_amd` (取決於 CPU)。
4.  **其他虛擬化軟體佔用：** 某些情況下，其他 Hypervisor (如 VirtualBox, VMware) 可能已經佔用了硬體虛擬化資源，導致 Qemu 無法使用。

#### 5.2 虛擬機器性能不佳

**現象：** 虛擬機器運行緩慢，響應遲鈍。

**原因與澄清：**
1.  **未啟用 KVM：** 這是最常見的原因。如果 KVM 未啟用，Qemu 將使用純軟體模擬，性能會非常差。確保 `-enable-kvm` 參數被正確使用，且 KVM 正常工作。
2.  **未使用 VirtIO 驅動：** Qemu 支援半虛擬化裝置 (VirtIO)，它們能顯著提升磁碟 I/O 和網路性能。如果 Guest OS 安裝了通用驅動 (如 IDE/e1000)，性能會受限。在 Guest OS 中安裝 VirtIO 驅動（通常作為 `virtio-win` 或 Linux 核心內建）。
3.  **分配資源不足：** 虛擬機器分配的記憶體 (`-m`) 或 CPU 核心數 (`-smp`) 太少。
4.  **Host 資源不足：** Host 系統本身的記憶體或 CPU 負載過高。

#### 5.3 網路連接問題

**現象：** 虛擬機器無法上網，或無法從 Host 連接到 Guest。

**原因與澄清：**
1.  **使用者模式網路的限制：** 預設使用者模式網路 (NAT) 模式下，Guest VM 只能主動訪問 Host 外部網路，外部網路或 Host 上的其他機器無法直接訪問 Guest VM。如果您需要從外部訪問 Guest，需要配置端口轉發 (`hostfwd`) 或使用橋接網路。
2.  **Guest OS 內部網路配置問題：** 確認 Guest OS 內部 DHCP 客戶端正常工作，或者靜態 IP 設定正確。
3.  **橋接網路配置錯誤：** 橋接網路需要 Host OS 上正確配置網橋 (bridge)。這通常涉及 `brctl` 或 `nmcli` 等工具，且需要 root 權限。對於初學者，建議先從使用者模式網路入手。
4.  **防火牆問題：** Host 或 Guest OS 的防火牆可能阻擋了流量。

-----

### 6. 小練習（附詳解）

#### 練習 1：建立並啟動一個簡單的 Linux VM (TinyCore Linux)

**目標：** 使用 Qemu 建立一個虛擬磁碟，並從 TinyCore Linux 的 ISO 映像檔啟動一個虛擬機器。

**步驟：**

1.  **下載 TinyCore Linux ISO**：
    進入 [TinyCore Linux 官方網站](http://www.tinycorelinux.net/downloads.html)，下載最新的 "CorePlus" 或 "TinyCore" ISO 映像檔。例如，下載 `CorePlus-current.iso`。將其保存到您的工作目錄，例如 `~/qemu_vm/`。

2.  **建立虛擬磁碟映像檔**：
    打開終端機，導航到您的工作目錄，然後執行以下命令建立一個 5GB 的 qcow2 虛擬磁碟。

    ```bash
    mkdir -p ~/qemu_vm
    cd ~/qemu_vm
    qemu-img create -f qcow2 tinycore_disk.qcow2 5G
    ```

3.  **啟動虛擬機器**：
    使用 `qemu-system-x86_64` 命令啟動虛擬機器，分配 512MB 記憶體和 1 個 CPU 核心，並從 ISO 啟動。啟用 KVM 加速和 VNC 界面。

    ```bash
    qemu-system-x86_64 \
        -enable-kvm \
        -m 512 \
        -smp 1 \
        -cpu host \
        -hda tinycore_disk.qcow2 \
        -cdrom CorePlus-current.iso \
        -boot d \
        -vnc :0
    ```
    *   **注意**：請將 `CorePlus-current.iso` 替換為您實際下載的 ISO 檔名。
    *   執行命令後，Qemu 會啟動。您需要使用 VNC 客戶端（例如 `Remmina`、`TightVNC Viewer` 或 `Vinagre`）連接到 `localhost:5900` (如果 `-vnc` 選項是 `:0`) 才能看到虛擬機器的畫面。

**詳解：**
成功執行後，您會看到 VNC 客戶端顯示 TinyCore Linux 的啟動界面。您可以選擇啟動選項，進入 Live CD 環境。這證明您已成功啟動一個 Qemu 虛擬機器。如果您在 VNC 客戶端看到畫面，並且能夠與 VM 互動（例如，在 TinyCore 啟動菜單中選擇選項），則練習成功。

-----

#### 練習 2：為 VM 配置網路並嘗試連線

**目標：** 在練習 1 的基礎上，為 TinyCore Linux VM 配置使用者模式網路，並透過 Host 機器測試 Guest VM 的網路連線能力。

**步驟：**

1.  **修改啟動指令，加入網路配置**：
    在前一個練習的啟動指令中，加入使用者模式網路設定和 VirtIO 網路卡，並設定 SSH 端口轉發。

    ```bash
    cd ~/qemu_vm # 確保您在正確的工作目錄
    qemu-system-x86_64 \
        -enable-kvm \
        -m 512 \
        -smp 1 \
        -cpu host \
        -hda tinycore_disk.qcow2 \
        -cdrom CorePlus-current.iso \
        -boot d \
        -vnc :0 \
        -netdev user,id=vnet0,hostfwd=tcp::2222-:22 \ # 添加此行
        -device virtio-net-pci,netdev=vnet0            # 添加此行
    ```
    *   啟動後，使用 VNC 連接到 `localhost:5900`。

2.  **在 Guest OS (TinyCore Linux) 中確認網路設定**：
    TinyCore Linux 通常會自動配置 DHCP。在 VM 的控制台或終端中，輸入以下命令檢查網路狀態。

    ```bash
    ifconfig
    ```
    您應該會看到一個網路介面 (例如 `eth0` 或 `ens3`) 被分配了 IP 地址，通常是 `10.0.2.15`。您可以嘗試 `ping 8.8.8.8` 或 `ping google.com` 測試外部網路連線。

3.  **在 Guest OS 中啟用 SSH 伺服器**：
    TinyCore Linux 預設可能沒有安裝或啟用 SSH 伺服器。您需要安裝它。

    ```bash
    # 更新軟體包列表
    tce-load -wi openssh
    # 啟動 ssh 服務
    /usr/local/etc/init.d/openssh start
    # 設定 root 密碼（如果沒有）
    passwd root
    ```
    請確保您設定了 `root` 密碼，因為 `sshd` 通常不允許沒有密碼的用戶登入。

4.  **在 Host OS 中測試連線**：
    從 Host OS 的終端，嘗試透過 SSH 連接到 Guest VM。由於我們設定了端口轉發，您應該可以連接到 `localhost:2222`。

    ```bash
    ssh -p 2222 root@localhost
    ```
    輸入您在 TinyCore VM 中設定的 `root` 密碼。

**詳解：**
如果成功連線，您將看到類似 `The authenticity of host '[localhost]:2222 ([::1]:2222)' can't be established.` 的提示，輸入 `yes` 後再輸入密碼，即可進入 TinyCore VM 的命令行界面。這表明您的 Qemu VM 已成功配置網路，並可透過端口轉發進行遠端連接。

-----

### 7. 延伸閱讀/參考

*   **Qemu 官方網站**：[https://www.qemu.org/](https://www.qemu.org/)
    *   Qemu 官方文件是了解所有選項和功能的最佳資源。
*   **KVM 官方網站**：[https://www.linux-kvm.org/](https://www.linux-kvm.org/)
    *   了解 KVM 的核心概念和如何在 Linux 系統上進行配置。
*   **VirtIO 介紹**：[https://www.qemu.org/docs/master/system/devices/virtio.html](https://www.qemu.org/docs/master/system/devices/virtio.html)
    *   深入了解 VirtIO 半虛擬化驅動，以及它們如何提升虛擬機器性能。
*   **Arch Linux Wiki - QEMU**：[https://wiki.archlinux.org/title/QEMU](https://wiki.archlinux.org/title/QEMU)
    *   Arch Linux Wiki 提供了非常詳盡和實用的 Qemu 設定指南，是學習和查閱的絕佳資源。