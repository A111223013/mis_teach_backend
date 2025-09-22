### 第二章：QEMU-KVM 核心運作機制與基礎應用

-----

#### 1.1 QEMU 與 KVM 的核心概念

本章將深入探討 QEMU 與 KVM 這兩大基石如何協同合作，實現高效能的虛擬化。

##### 1.1.1 KVM (Kernel-based Virtual Machine)

*   **定義/核心觀念**：
    KVM 是一個適用於 Linux 核心的虛擬化模組。它將 Linux 核心轉換為一個 Type-1（或稱 Type-0.5）的 Hypervisor。KVM 本身不執行任何模擬，而是提供底層的硬體虛擬化介面，讓使用者空間的程式可以利用處理器的虛擬化擴展（如 Intel VT-x 或 AMD-V）來直接執行客體作業系統的指令。換句話說，KVM 負責 CPU 和記憶體的虛擬化。
*   **工作原理**：
    當客體作業系統嘗試執行需要特權的指令時（例如 I/O 操作或修改記憶體映射），這些指令會被 KVM 截獲。KVM 會將這些操作從客體模式切換到主機模式，並交由主機 Linux 核心處理，然後再將結果返回給客體。對於非特權指令，客體作業系統可以直接在處理器上執行，幾乎沒有性能損耗。
*   **與相鄰概念的關聯**：
    *   **Hypervisor**：KVM 是 Linux 核心的一部分，使其成為一個輕量級的 Type-1 Hypervisor。然而，由於它仍然依賴於主機 Linux 核心的完整功能，有時也被視為 Type-2 Hypervisor 的高效能變體。
    *   **處理器虛擬化擴展**：KVM 的存在與否直接取決於處理器是否支援 Intel VT-x 或 AMD-V。沒有這些硬體輔助，KVM 無法運作。

##### 1.1.2 QEMU (Quick EMUlator)

*   **定義/核心觀念**：
    QEMU 是一個開源的機器模擬器和虛擬器。在沒有 KVM 的情況下，QEMU 可以完全模擬一台電腦的所有硬體元件（CPU、記憶體、硬碟控制器、網路卡等），讓客體作業系統運行在完全虛擬的環境中，即使客體與主機的 CPU 架構不同。然而，這種純軟體模擬的性能非常低。
*   **與 KVM 的協同運作**：
    當 KVM 模組可用時，QEMU 會作為一個使用者空間的進程，負責模擬客體機的所有周邊硬體（如網路卡、顯示卡、硬碟控制器等），並將 CPU 和記憶體的虛擬化「委託」給 KVM 核心模組處理。這樣，客體作業系統的 CPU 指令可以直接在物理 CPU 上執行，而 KVM 則負責管理這些指令的特權級別和記憶體訪問，從而大幅提升虛擬機的性能。
*   **與相鄰概念的關聯**：
    *   **Hypervisor**：在 KVM 的協助下，QEMU 扮演著虛擬機器管理器（VMM, Virtual Machine Monitor）的角色，負責協調硬體資源。
    *   **VirtIO**：QEMU 支援 VirtIO 半虛擬化驅動，客體作業系統安裝 VirtIO 驅動後，可以直接與 QEMU 交互，繞過傳統的硬體模擬層，進一步提升 I/O 效能。

##### 1.1.3 QEMU-KVM 協同架構總覽

簡單來說，KVM 提供了硬體輔助的 CPU 和記憶體虛擬化能力，而 QEMU 則負責模擬所有其他硬體。QEMU 作為前端介面，將客體機的需求傳遞給 KVM 處理，並將 KVM 的結果回傳給客體機。這種分工合作模式，結合了 QEMU 的靈活性和 KVM 的高性能，使得 QEMU-KVM 成為 Linux 上最主流的虛擬化解決方案。

```mermaid
graph TD
    A[Host OS (Linux Kernel)] --> B{KVM Kernel Module};
    B --> C[QEMU Process (Userspace)];
    C --> D[Simulated Hardware Devices];
    D --> E[Guest OS (Virtual Machine)];

    subgraph Host Hardware
        F[Physical CPU (with VT-x/AMD-V)] -- KVM 提供硬件加速 --> B;
        G[Physical RAM] -- KVM 管理 --> B;
        H[Physical I/O Devices] -- QEMU 模擬 --> D;
    end

    E -- CPU指令 --> C;
    C -- 轉發 CPU/Memory指令 --> B;
    B -- 直接執行 CPU 指令 / 管理 Memory --> F;
    B -- 返回結果 --> C;
    C -- 模擬 I/O --> D;
    D -- 返回 I/O 結果 --> E;
```

-----

#### 1.2 QEMU-KVM 協同架構與運作流程

##### 1.2.1 系統架構

QEMU-KVM 的架構可以分為幾個層次：

1.  **實體硬體 (Physical Hardware)**：包含 CPU (必須支援 Intel VT-x 或 AMD-V 虛擬化擴展)、記憶體、網路卡、儲存裝置等。
2.  **主機作業系統 (Host OS)**：通常是 Linux 發行版。
3.  **KVM 核心模組 (KVM Kernel Module)**：作為 Linux 核心的一部分，利用實體 CPU 的虛擬化擴展提供 CPU 和記憶體的硬體輔助虛擬化介面。
    *   核心會暴露 `/dev/kvm` 介面供使用者空間程式操作。
4.  **QEMU 進程 (QEMU Process)**：在使用者空間運行，負責模擬虛擬機的所有周邊硬體（例如：虛擬顯示卡、虛擬網路卡、虛擬硬碟控制器等）。當 KVM 可用時，QEMU 會透過 `/dev/kvm` 介面將客體 CPU 和記憶體操作交給 KVM 處理。
5.  **客體作業系統 (Guest OS)**：運行在 QEMU 模擬的硬體和 KVM 提供的 CPU/記憶體虛擬化之上。

##### 1.2.2 運作流程

1.  **啟動虛擬機**：當你執行一個 `qemu-system-*` 命令並帶上 `--enable-kvm` 參數時，QEMU 會首先嘗試打開 `/dev/kvm` 裝置。
2.  **建立 VM 實例**：QEMU 會向 KVM 請求建立一個新的虛擬機實例。KVM 會在核心中為這個虛擬機分配資源，並設定相關的虛擬 CPU (vCPU) 和記憶體映射。
3.  **硬體模擬**：QEMU 進程開始模擬虛擬機所需的各種硬體設備。
4.  **客體執行**：客體作業系統啟動，QEMU 指示 KVM 將 vCPU 執行權切換到客體模式。
    *   **非特權指令**：客體作業系統的絕大部分指令（如一般計算、數據移動）都是非特權指令，這些指令會直接在實體 CPU 上以較低的權限級別執行，幾乎沒有性能損失。
    *   **特權指令或 I/O 操作**：當客體作業系統執行如 I/O 操作、系統呼叫等需要特權的指令時，這些操作會被 KVM 截獲（VM-exit）。KVM 會將控制權返回給使用者空間的 QEMU 進程。
5.  **QEMU 處理**：QEMU 收到 KVM 的控制權後，會根據客體作業系統請求的類型（例如，寫入虛擬硬碟）來模擬相應的硬體行為，並將其轉換為主機作業系統的實際 I/O 操作。
6.  **結果返回**：QEMU 完成模擬操作後，將結果透過 KVM 返回給客體作業系統，KVM 再將執行權交還給客體，循環往復。

-----

#### 1.3 啟動 QEMU-KVM 虛擬機的典型範例

在啟動 QEMU-KVM 虛擬機之前，需要確保你的系統支援 KVM 並已載入相關模組。

##### 1.3.1 前置條件檢查

1.  **檢查 CPU 是否支援虛擬化**：
    *   對於 Intel 處理器：`grep -E "(vmx|svm)" /proc/cpuinfo`
    *   對於 AMD 處理器：`grep -E "(svm|vmx)" /proc/cpuinfo`
    如果輸出包含 `vmx` (Intel) 或 `svm` (AMD)，則表示 CPU 支援虛擬化。
2.  **檢查 KVM 模組是否載入**：
    ```bash
    lsmod | grep kvm
    ```
    應能看到 `kvm_intel` 或 `kvm_amd` 以及 `kvm` 模組。如果沒有，請嘗試載入：
    ```bash
    sudo modprobe kvm_intel # 或 kvm_amd
    sudo modprobe kvm
    ```
    並確保你的使用者帳戶屬於 `kvm` 群組：
    ```bash
    sudo adduser $USER kvm
    ```
    加入後可能需要重新登入才能生效。
3.  **安裝 QEMU**：
    ```bash
    sudo apt update && sudo apt install qemu-kvm # Debian/Ubuntu
    sudo dnf install qemu-kvm # Fedora/CentOS
    ```

##### 1.3.2 建立磁碟映像檔

QEMU 支援多種磁碟映像檔格式，其中 `qcow2` 是最常用的，它支援快照、CoW (Copy-on-Write) 和稀疏儲存 (sparse storage)。

```bash
qemu-img create -f qcow2 my_ubuntu_vm.qcow2 20G
```
*   `-f qcow2`：指定映像檔格式為 qcow2。
*   `my_ubuntu_vm.qcow2`：映像檔的名稱。
*   `20G`：映像檔的最大容量為 20GB。實際佔用空間會根據內容增長。

##### 1.3.3 啟動基本虛擬機 (逐步推導)

我們將從一個最基本的 QEMU 命令開始，逐步增加選項，構建一個完整的虛擬機啟動命令。假設我們已經下載了一個 Ubuntu Server 的 ISO 檔案 (`ubuntu-22.04-live-server-amd64.iso`)。

1.  **最簡模式（不啟用 KVM，純軟體模擬，非常慢）**：
    ```bash
    qemu-system-x86_64 -cdrom ubuntu-22.04-live-server-amd64.iso -m 1G -boot d
    ```
    *   `qemu-system-x86_64`：啟動一個 x86-64 架構的虛擬機。
    *   `-cdrom ubuntu-22.04-live-server-amd64.iso`：將 ISO 檔案掛載為虛擬光碟機。
    *   `-m 1G`：為虛擬機分配 1GB 記憶體。
    *   `-boot d`：從光碟機啟動。

2.  **啟用 KVM 加速（提升性能）**：
    ```bash
    qemu-system-x86_64 -cdrom ubuntu-22.04-live-server-amd64.iso -m 1G -boot d --enable-kvm
    ```
    *   `--enable-kvm`：指示 QEMU 使用 KVM 模組進行硬體加速。這是 QEMU-KVM 的核心。

3.  **添加虛擬硬碟**：
    ```bash
    qemu-system-x86_64 \
        -cdrom ubuntu-22.04-live-server-amd64.iso \
        -m 1G \
        -boot d \
        --enable-kvm \
        -drive file=my_ubuntu_vm.qcow2,format=qcow2,if=virtio
    ```
    *   `-drive file=my_ubuntu_vm.qcow2,format=qcow2,if=virtio`：將之前建立的 `qcow2` 檔案作為虛擬硬碟掛載。
        *   `file`：指定映像檔路徑。
        *   `format`：指定映像檔格式。
        *   `if=virtio`：使用 VirtIO 介面。這是一種半虛擬化介面，需要客體作業系統安裝 VirtIO 驅動以獲得最佳性能。對於現代 Linux 發行版，VirtIO 驅動通常已內建。

4.  **配置 CPU 核心數**：
    ```bash
    qemu-system-x86_64 \
        -cdrom ubuntu-22.04-live-server-amd64.iso \
        -m 1G \
        -smp 2 \
        -boot d \
        --enable-kvm \
        -drive file=my_ubuntu_vm.qcow2,format=qcow2,if=virtio
    ```
    *   `-smp 2`：為虛擬機分配 2 個 CPU 核心。

5.  **配置網路 (user 模式)**：
    `user` 模式是最簡單的網路配置，它在 QEMU 內部建立一個 NAT (Network Address Translation) 網路，客體機可以訪問外部網路，但外部無法直接訪問客體機。
    ```bash
    qemu-system-x86_64 \
        -cdrom ubuntu-22.04-live-server-amd64.iso \
        -m 1G \
        -smp 2 \
        -boot d \
        --enable-kvm \
        -drive file=my_ubuntu_vm.qcow2,format=qcow2,if=virtio \
        -net nic,model=virtio -net user
    ```
    *   `-net nic,model=virtio`：添加一個虛擬網路卡，使用 VirtIO 模型以獲得更好性能。
    *   `-net user`：啟用使用者模式網路。

6.  **配置圖形介面 (VNC)**：
    預設 QEMU 會在當前終端顯示圖形介面，這對於伺服器安裝可能不方便。VNC 允許你透過遠端桌面連接。
    ```bash
    qemu-system-x86_64 \
        -cdrom ubuntu-22.04-live-server-amd64.iso \
        -m 1G \
        -smp 2 \
        -boot d \
        --enable-kvm \
        -drive file=my_ubuntu_vm.qcow2,format=qcow2,if=virtio \
        -net nic,model=virtio -net user \
        -vnc :0 # 或者 -vnc 127.0.0.1:0
    ```
    *   `-vnc :0`：在主機的 VNC 埠 5900 上啟動 VNC 伺服器 (`:0` 表示埠 5900，`:1` 表示埠 5901，以此類推)。你可以使用 VNC 客戶端（如 TightVNC Viewer, RealVNC Viewer）連接 `localhost:5900`。

7.  **後台運行虛擬機**：
    如果你不希望 QEMU 佔用當前終端，可以讓它在後台運行。
    ```bash
    qemu-system-x86_64 \
        -cdrom ubuntu-22.04-live-server-amd64.iso \
        -m 1G \
        -smp 2 \
        -boot d \
        --enable-kvm \
        -drive file=my_ubuntu_vm.qcow2,format=qcow2,if=virtio \
        -net nic,model=virtio -net user \
        -vnc :0 \
        -daemonize # 或者將整個命令放在 `nohup ... &` 中
    ```
    *   `-daemonize`：讓 QEMU 進程在後台運行。

**完成安裝後，移除 `-cdrom` 和 `-boot d` 參數，直接從硬碟啟動虛擬機：**
```bash
qemu-system-x86_64 \
    -m 1G \
    -smp 2 \
    --enable-kvm \
    -drive file=my_ubuntu_vm.qcow2,format=qcow2,if=virtio \
    -net nic,model=virtio -net user \
    -vnc :0 \
    -daemonize
```

-----

#### 1.4 與相鄰概念的關聯

##### 1.4.1 Linux Kernel

*   **核心模組**: KVM 本身就是一個 Linux 核心模組 (`kvm.ko`, `kvm_intel.ko`, `kvm_amd.ko`)。這意味著 KVM 深度整合於 Linux 核心中，可以利用核心的記憶體管理、排程器和設備驅動等功能。
*   **系統呼叫**: QEMU 透過 `/dev/kvm` 介面（一個字元設備）向 KVM 核心模組發出系統呼叫（ioctl），請求建立虛擬機、設定記憶體映射、執行 vCPU 指令等操作。

##### 1.4.2 硬體虛擬化技術 (Intel VT-x / AMD-V)

*   **基礎**: KVM 的高效能虛擬化能力完全依賴於現代 CPU 提供的硬體虛擬化擴展。
    *   **Intel VT-x (Virtualization Technology)**: Intel 處理器上的虛擬化技術，包含 VMX (Virtual Machine Extensions) 操作。
    *   **AMD-V (AMD Virtualization)**: AMD 處理器上的虛擬化技術，包含 SVM (Secure Virtual Machine) 操作。
*   **VMX Non-Root 和 VMX Root 模式**: 這些擴展允許 CPU 在兩種模式之間切換。
    *   **VMX Non-Root 模式**: 客體作業系統在此模式下運行，其大部分指令可以直接在 CPU 上執行。
    *   **VMX Root 模式**: 當客體執行特權指令時，CPU 會觸發 VMX-exit，切換到 VMX Root 模式，此時 KVM（作為 Hypervisor 的一部分）介入處理。
*   **加速原理**: 硬體虛擬化技術消除了純軟體虛擬化中耗費大量資源的二進制翻譯（Binary Translation）過程，使得客體 CPU 的執行效率接近原生。

##### 1.4.3 半虛擬化裝置 (VirtIO)

*   **定義**: VirtIO 是一套標準化的半虛擬化（Paravirtualization）I/O 裝置介面。它不是模擬真實的硬體裝置，而是提供一個優化的介面，讓客體作業系統可以直接與 Hypervisor（這裡指 QEMU-KVM）通信。
*   **作用**: 由於它不需要 Hypervisor 進行完整的硬體模擬，因此可以大幅降低 I/O 延遲並提升吞吐量。
*   **常見 VirtIO 裝置**:
    *   `virtio-blk`: 虛擬區塊裝置（硬碟）。
    *   `virtio-net`: 虛擬網路卡。
    *   `virtio-scsi`: 虛擬 SCSI 控制器。
    *   `virtio-gpu`: 虛擬 GPU (用於 VNC/SPICE 等)。
*   **要求**: 客體作業系統需要安裝 VirtIO 驅動才能利用這些裝置。現代 Linux 發行版通常已內建 VirtIO 驅動。Windows 客體則需要額外安裝 VirtIO 驅動。

-----

#### 1.5 常見錯誤與澄清

##### 1.5.1 「KVM acceleration can NOT be used」或「CPU is not KVM capable」

*   **錯誤原因**：
    1.  **CPU 不支援虛擬化**：你的實體 CPU 沒有 Intel VT-x 或 AMD-V 功能。
    2.  **BIOS/UEFI 中未啟用虛擬化功能**：即使 CPU 支援，BIOS/UEFI 中可能預設是關閉的。
    3.  **KVM 核心模組未載入**：`kvm_intel` 或 `kvm_amd` 模組沒有被加載到 Linux 核心。
    4.  **當前使用者沒有權限訪問 `/dev/kvm`**：使用者不在 `kvm` 群組中。
*   **澄清與解決**：
    1.  檢查 `grep -E "(vmx|svm)" /proc/cpuinfo` 確認 CPU 支援。
    2.  重啟電腦，進入 BIOS/UEFI 設定介面，尋找 "Virtualization Technology" 或 "Intel VT-x" / "AMD-V" 等選項並啟用。
    3.  手動載入模組：`sudo modprobe kvm_intel` (或 `kvm_amd`) `&& sudo modprobe kvm`。
    4.  將使用者加入 `kvm` 群組：`sudo adduser $USER kvm`，然後重新登出登入或重啟系統。
    5.  確認 QEMU 命令中包含了 `--enable-kvm` 參數。

##### 1.5.2 「無圖形輸出」或「無法連接 VNC」

*   **錯誤原因**：
    1.  **未指定圖形輸出選項**：QEMU 預設可能嘗試在 SDL 視窗或當前終端顯示，如果環境不支援，會導致無輸出。
    2.  **VNC 服務未啟動或埠被佔用**：`-vnc` 參數指定錯誤或指定埠已被其他應用佔用。
    3.  **VNC 客戶端連接地址/埠錯誤**。
*   **澄清與解決**：
    1.  確保命令中包含 `-vnc :0` (或 `127.0.0.1:0` 等) 或 `-display sdl` 等圖形輸出選項。
    2.  檢查系統是否有其他應用佔用 VNC 埠 (預設 5900)。可以嘗試使用 `-vnc :1` (即埠 5901) 等其他埠。
    3.  使用 `ss -tlnp | grep 5900` 檢查 VNC 埠是否監聽成功。
    4.  確保 VNC 客戶端連接的 IP 地址和埠與 QEMU 中設定的一致。如果使用 `127.0.0.1:0` 則只能從本機連接。若要從其他機器連接，需要綁定到公共 IP `-vnc 0.0.0.0:0` (注意安全風險)。

##### 1.5.3 「網路無法連線」

*   **錯誤原因**：
    1.  **網路模式選擇錯誤**：`user` 模式提供 NAT，客體機可以出網，但外部無法直接訪問客體機。`bridge` 模式允許客體機獲得與主機同等級的網路存取能力，但需要額外的配置。
    2.  **客體作業系統中未配置網路**：即使 QEMU 網路設定正確，客體 OS 內部也需要正確配置 IP 地址、DNS 等。
    3.  **橋接網路未正確設定**：如果使用 `bridge` 模式，主機上的網路橋接裝置（例如 `br0`）必須存在且配置正確。
    4.  **防火牆阻擋**：主機或客體 OS 的防火牆可能阻擋了網路流量。
*   **澄清與解決**：
    1.  對於簡單的網路訪問，優先使用 `-net nic,model=virtio -net user`。
    2.  如果需要外部直接訪問虛擬機（例如運行網頁伺服器），則考慮使用 `bridge` 模式。這要求主機建立一個網路橋接裝置（例如 `br0`），並將物理網卡加入橋接。QEMU 命令中需使用 `-net nic,model=virtio -net bridge,br=br0`。
    3.  進入客體作業系統，確認網路介面已啟動並獲得 IP 地址（例如 `ip a` 或 `ifconfig`）。
    4.  檢查主機和客體的防火牆規則，確保沒有阻擋必要的埠或流量。

##### 1.5.4 QEMU 參數混淆

*   **錯誤原因**：QEMU 參數眾多，容易混淆。
*   **澄清與解決**：
    1.  **`--enable-kvm`**：這是啟用 KVM 加速的關鍵參數，絕對不能忘記。
    2.  **記憶體 (`-m`) 與 CPU (`-smp`)**：直接影響虛擬機性能。合理分配，不要超過主機資源。
    3.  **磁碟 (`-drive`)**：
        *   `file=`：指定磁碟映像檔路徑。
        *   `format=`：指定格式（`qcow2` 最常用）。
        *   `if=`：指定虛擬介面類型，`virtio` 性能最佳。
    4.  **網路 (`-net`)**：
        *   `nic,model=virtio`：添加虛擬網卡並指定模型為 `virtio`。
        *   `user`：簡單的 NAT 模式。
        *   `bridge,br=br0`：橋接模式，需要主機預先配置 `br0` 橋接介面。
    5.  **啟動順序 (`-boot`)**：`c` 從硬碟、`d` 從光碟、`n` 從網路啟動。通常用於安裝系統。安裝完成後應移除此參數，讓虛擬機從硬碟啟動。
    6.  **圖形輸出 (`-vnc`, `-display`)**：選擇適合你的圖形輸出方式。

使用 `man qemu` 或 `qemu-system-x86_64 --help` 可以查看所有參數及其說明。

-----

#### 1.6 小練習（附詳解）

##### 1.6.1 練習一：建立並啟動一個 Ubuntu 虛擬機

**目標**：在 QEMU-KVM 上建立一個 Ubuntu Server 虛擬機，配置 2GB RAM、2 個 CPU 核心、一個 30GB 的虛擬硬碟，並透過 VNC 進行安裝。

**準備**：
1.  確保你的系統已安裝 `qemu-kvm`。
2.  下載 Ubuntu Server 22.04 LTS ISO 檔案，例如 `ubuntu-22.04.3-live-server-amd64.iso`，並將其放置在你的工作目錄。

**步驟**：

1.  **建立磁碟映像檔**：
    打開終端機，執行以下命令建立一個 30GB 的 qcow2 格式虛擬硬碟。
    ```bash
    qemu-img create -f qcow2 ubuntu_vm_disk.qcow2 30G
    ```
2.  **啟動虛擬機進行安裝**：
    使用以下 QEMU 命令啟動虛擬機。請替換 `ubuntu-22.04.3-live-server-amd64.iso` 為你實際下載的 ISO 檔名。
    ```bash
    qemu-system-x86_64 \
        -name ubuntu-server-vm \
        -m 2G \
        -smp 2 \
        --enable-kvm \
        -cpu host \
        -drive file=ubuntu_vm_disk.qcow2,format=qcow2,if=virtio \
        -cdrom ubuntu-22.04.3-live-server-amd64.iso \
        -boot d \
        -net nic,model=virtio -net user,hostfwd=tcp::2222-:22 \
        -vnc :0 \
        -daemonize
    ```
    *   `-name ubuntu-server-vm`: 為虛擬機設定一個名稱。
    *   `-m 2G`: 分配 2GB 記憶體。
    *   `-smp 2`: 分配 2 個 CPU 核心。
    *   `--enable-kvm`: 啟用 KVM 硬體加速。
    *   `-cpu host`: 讓客體機使用與主機相同的 CPU 模型，可提供最佳性能。
    *   `-drive ...`: 掛載虛擬硬碟，使用 `virtio` 介面。
    *   `-cdrom ...`: 掛載 Ubuntu ISO 檔案作為光碟機。
    *   `-boot d`: 優先從光碟啟動。
    *   `-net nic,model=virtio -net user,hostfwd=tcp::2222-:22`: 設定網路。`nic,model=virtio` 是建立一個 VirtIO 網卡。`user` 是 NAT 模式，`hostfwd=tcp::2222-:22` 將主機的 2222 埠轉發到客體機的 22 埠 (SSH 埠)，方便安裝後 SSH 連接。
    *   `-vnc :0`: 啟動 VNC 伺服器在主機的 5900 埠。
    *   `-daemonize`: 讓 QEMU 進程在後台運行。

3.  **連接 VNC 客戶端**：
    打開你的 VNC 客戶端軟體（如 TightVNC Viewer, RealVNC Viewer），連接到 `localhost:5900`。你將看到 Ubuntu Server 的安裝介面。

4.  **完成 Ubuntu 安裝**：
    依照螢幕指示完成 Ubuntu Server 的安裝。在安裝過程中，請確保選擇將系統安裝到 `virtio` 磁碟上。安裝完成後，系統會提示你重啟。

5.  **重啟虛擬機（從硬碟）**：
    安裝完成後，首先關閉 VNC 客戶端。你需要找到 QEMU 進程並殺死它，或者在 VNC 介面中選擇關機。
    然後，使用以下命令重新啟動虛擬機，這次不再從 ISO 啟動：
    ```bash
    qemu-system-x86_64 \
        -name ubuntu-server-vm \
        -m 2G \
        -smp 2 \
        --enable-kvm \
        -cpu host \
        -drive file=ubuntu_vm_disk.qcow2,format=qcow2,if=virtio \
        -net nic,model=virtio -net user,hostfwd=tcp::2222-:22 \
        -vnc :0 \
        -daemonize
    ```
    現在，連接 VNC 客戶端到 `localhost:5900`，你應該能看到 Ubuntu Server 的登入提示。

6.  **測試 SSH 連接**：
    在主機的終端，嘗試 SSH 連接到虛擬機：
    ```bash
    ssh -p 2222 <你的Ubuntu使用者名稱>@localhost
    ```
    如果一切順利，你應該能成功登入虛擬機。

##### 1.6.2 練習二：增加虛擬磁碟與網路模式切換

**目標**：在練習一的基礎上，為已安裝的 Ubuntu 虛擬機新增一個 10GB 的虛擬資料磁碟，並將網路模式從 `user` 切換到 `bridge`。

**準備**：
1.  完成練習一，有一個運作中的 Ubuntu 虛擬機。
2.  **配置主機的網路橋接**：
    *   這部分操作因 Linux 發行版而異，通常涉及 `netplan` (Ubuntu)、`NetworkManager` 或手動配置 `/etc/network/interfaces`。以下為一個通用的 `netplan` 範例，你需要根據實際情況調整你的物理網卡名稱 (例如 `enp0s3`)。
    *   建立或修改 `/etc/netplan/01-netcfg.yaml` (或類似名稱)：
        ```yaml
        network:
          version: 2
          renderer: networkd
          ethernets:
            enp0s3: # 替換為你的物理網卡名稱
              dhcp4: no
              dhcp6: no
          bridges:
            br0:
              interfaces: [enp0s3] # 將你的物理網卡加入橋接
              dhcp4: yes # 讓橋接介面通過 DHCP 獲取 IP
              # 或配置靜態 IP：
              # addresses: [192.168.1.100/24]
              # gateway4: 192.168.1.1
              # nameservers:
              #   addresses: [8.8.8.8, 8.8.4.4]
        ```
    *   應用 netplan 配置：
        ```bash
        sudo netplan try
        sudo netplan apply
        ```
    *   檢查橋接介面：`ip a | grep br0`。應能看到 `br0` 介面已啟用並獲得 IP。

**步驟**：

1.  **停止運作中的虛擬機**：
    如果虛擬機仍在運行，請先關閉它。你可以透過 VNC 介面在客體 OS 內部關機，或找到 QEMU 進程 ID 並使用 `kill <PID>`。

2.  **建立新的虛擬磁碟映像檔**：
    ```bash
    qemu-img create -f qcow2 ubuntu_data_disk.qcow2 10G
    ```

3.  **啟動虛擬機（新增磁碟，切換橋接網路）**：
    修改練習一的啟動命令，添加新的磁碟和更改網路參數：
    ```bash
    qemu-system-x86_64 \
        -name ubuntu-server-vm \
        -m 2G \
        -smp 2 \
        --enable-kvm \
        -cpu host \
        -drive file=ubuntu_vm_disk.qcow2,format=qcow2,if=virtio \
        -drive file=ubuntu_data_disk.qcow2,format=qcow2,if=virtio \
        -net nic,model=virtio -net bridge,br=br0 \
        -vnc :0 \
        -daemonize
    ```
    *   新增了一行 `-drive file=ubuntu_data_disk.qcow2,format=qcow2,if=virtio`。
    *   網路參數從 `-net user,hostfwd=tcp::2222-:22` 變為 `-net nic,model=virtio -net bridge,br=br0`。
        *   `br=br0` 假設你的橋接介面名稱為 `br0`。

4.  **登入虛擬機並配置新磁碟**：
    連接 VNC 到 `localhost:5900`（或直接 SSH 到虛擬機的新 IP）。登入 Ubuntu Server 後：
    *   **檢查磁碟**：
        ```bash
        sudo fdisk -l
        ```
        你應該會看到 `/dev/vda` (原來的 30GB 系統碟) 和 `/dev/vdb` (新的 10GB 資料碟)。
    *   **格式化並掛載新磁碟**：
        ```bash
        sudo mkfs.ext4 /dev/vdb
        sudo mkdir /mnt/data
        sudo mount /dev/vdb /mnt/data
        ```
    *   **查看掛載結果**：
        ```bash
        df -h
        ```
        你應該能看到 `/dev/vdb` 掛載在 `/mnt/data`。
    *   **設定開機自動掛載**：
        取得新磁碟的 UUID：
        ```bash
        sudo blkid /dev/vdb
        ```
        假設 UUID 為 `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`。
        編輯 `/etc/fstab`：
        ```bash
        sudo nano /etc/fstab
        ```
        在檔案末尾添加一行（替換為你實際的 UUID）：
        ```
        UUID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx /mnt/data ext4 defaults 0 0
        ```
        保存並退出。重啟虛擬機後，新磁碟將會自動掛載。

5.  **驗證網路連接**：
    *   在虛擬機內部執行 `ip a`，確認虛擬機已獲得一個與主機橋接網段相同的 IP 地址。
    *   嘗試 `ping google.com` 檢查網路連線。
    *   現在，主機以及其他同網段的機器應該可以直接透過新 IP 地址 SSH 到虛擬機（預設埠 22，不再需要埠轉發）。

-----

#### 1.7 延伸閱讀/參考

*   **QEMU 官方文件**:
    [QEMU Documentation](https://qemu.readthedocs.io/en/latest/)
    這是了解 QEMU 各種參數、功能和進階用法的最權威來源。
*   **KVM 維基百科條目**:
    [Kernel-based Virtual Machine - Wikipedia](https://en.wikipedia.org/wiki/Kernel-based_Virtual_Machine)
    提供 KVM 的歷史、架構和相關概念的概覽。
*   **VirtIO 介紹**:
    [VirtIO: An I/O virtualization framework for Linux](https://www.linux-kvm.org/page/Virtio)
    詳細介紹 VirtIO 技術如何提升虛擬機的 I/O 性能。
*   **Linux 核心虛擬化文檔**:
    [`Documentation/virt/kvm/api.rst` in Linux Kernel Source](https://www.kernel.org/doc/Documentation/virt/kvm/api.rst)
    深入了解 KVM 核心模組提供的 API 介面。
*   **libvirt**:
    儘管本章主要介紹直接使用 QEMU 命令，但在生產環境中，`libvirt` 是管理 QEMU-KVM 虛擬機的首選工具。它提供了一個穩定、易用的 API 和管理工具（如 `virsh`、`virt-manager`），大大簡化了虛擬機的管理。建議在學習 QEMU 基礎後，進一步探索 `libvirt`。
    [Libvirt Official Website](https://libvirt.org/)

-----