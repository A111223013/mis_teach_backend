# 3-1 Libvirt 架構與 API

Libvirt 是一個開源的虛擬化管理 API、守護進程和工具集，它提供了一個統一的介面來管理多種虛擬化技術，如 KVM、Xen、LXC 等。本章將深入探討 Libvirt 的核心架構及其 API，幫助您理解它是如何簡化虛擬化管理的複雜性。

-----

### 1. 核心概念與定義

#### 什麼是 Libvirt？

**核心觀念：** Libvirt 是一個針對虛擬化平台而設計的強大管理工具集，它扮演著**抽象層**的角色，旨在提供一個**標準化且統一的介面**，讓開發者和系統管理員無需關心底層虛擬化技術的具體細節，即可高效地管理虛擬機器、網路、儲存等資源。

**定義：** Libvirt 是一個 C 語言函式庫，同時提供多種語言綁定（如 Python, Java, Ruby 等），並包含一個名為 `libvirtd` 的守護進程和一系列命令行工具（如 `virsh`）。它的主要目標是：

*   **虛擬化抽象化：** 將不同的虛擬化技術（KVM, Xen, VMware ESX, LXC 等）抽象化為統一的模型。
*   **集中管理：** 提供單一管理點，無論虛擬機是在本機還是在遠端伺服器上。
*   **生命週期管理：** 支援虛擬機的建立、啟動、停止、暫停、遷移和刪除等操作。
*   **資源配置：** 允許配置虛擬機的 CPU、記憶體、網路介面、儲存設備等。

#### Libvirt 的主要組成部分

Libvirt 的架構設計模組化，主要包含以下幾個核心組件：

*   **`libvirtd` 守護進程 (Daemon)：**
    *   **定義：** 這是 Libvirt 的核心服務進程，運行在宿主機上。它負責監聽來自 Libvirt API 的請求，並將這些請求轉譯為對應虛擬化技術（例如 KVM/QEMU）的特定操作。
    *   **核心觀念：** 作為 Libvirt 的「大腦」，`libvirtd` 處理所有虛擬化管理任務，並協調與底層 Hypervisor 的通訊。

*   **驅動程式 (Drivers)：**
    *   **定義：** Libvirt 透過一系列的驅動程式來支援不同的虛擬化技術。每個驅動程式都專門負責與特定的 Hypervisor 或容器技術（如 QEMU/KVM、Xen、LXC、VMware ESX、Hyper-V 等）進行通訊。
    *   **核心觀念：** 驅動程式是實現抽象化的關鍵。它們將 Libvirt API 的通用請求轉換為特定虛擬化平台的原生指令。

*   **Libvirt API：**
    *   **定義：** Libvirt API 是一個程式化的介面，允許應用程式以程式碼的方式與 `libvirtd` 進行互動，執行虛擬化管理任務。它提供了一套標準化的函式呼叫，用於管理虛擬機、網路、儲存等。
    *   **核心觀念：** 它是 Libvirt 的「通訊協定」，所有上層工具或雲平台（如 OpenStack）都是透過這個 API 來管理虛擬化資源。

*   **命令行工具 `virsh`：**
    *   **定義：** `virsh` (virtual shell) 是 Libvirt 提供的強大命令行介面工具。它允許系統管理員在終端機中直接執行 Libvirt API 的所有功能。
    *   **核心觀念：** `virsh` 是 Libvirt API 的直接映射，對於腳本化和自動化管理虛擬化環境非常有用。

*   **GUI 工具 (例如 `virt-manager`)：**
    *   **定義：** `virt-manager` 是一個圖形化管理工具，它利用 Libvirt API 來提供一個易於使用的介面，用於創建、管理和監控虛擬機器。
    *   **核心觀念：** `virt-manager` 證明了 Libvirt API 的通用性，可以輕鬆地構建上層應用程式。

#### Libvirt 的設計哲學

Libvirt 的設計哲學圍繞著幾個核心原則：

*   **抽象化 (Abstraction)：** 這是最重要的原則。它將底層複雜多樣的虛擬化技術細節隱藏起來，提供一個統一且簡潔的介面。
*   **擴展性 (Extensibility)：** 透過模組化的驅動程式設計，Libvirt 可以輕鬆地添加對新的虛擬化技術的支援。
*   **遠端管理 (Remote Management)：** Libvirt 支援透過多種安全協定（如 SSH、TLS）遠端連接到 `libvirtd` 實例，實現分散式虛擬化環境的集中管理。
*   **穩定性與安全性 (Stability & Security)：** 作為底層基礎設施管理工具，Libvirt 強調穩定運行和安全的權限控制。

-----

### 2. 典型例子與轉換/推導

#### Libvirt 如何與 QEMU/KVM 協作？

QEMU/KVM 是目前 Linux 環境中最主流的虛擬化解決方案之一。Libvirt 與 QEMU/KVM 的協作是典型的應用範例：

1.  **使用者發出請求：** 管理員使用 `virsh` 命令或 `virt-manager`，甚至透過自定義程式（利用 Libvirt API）發出創建或管理虛擬機的請求。
2.  **請求傳遞給 `libvirtd`：** 這些請求被發送到宿主機上運行的 `libvirtd` 守護進程。
3.  **`libvirtd` 選擇驅動程式：** `libvirtd` 識別出這是一個 QEMU/KVM 虛擬機操作，並調用其內部的 QEMU 驅動程式。
4.  **驅動程式生成 QEMU 命令：** QEMU 驅動程式根據 Libvirt 抽象的虛擬機設定（通常是 XML 格式），生成一個對應的 QEMU 命令行指令，包含所有的虛擬機配置（CPU、記憶體、磁碟、網路等）。
5.  **執行 QEMU 進程：** `libvirtd` 透過其 QEMU 驅動程式啟動一個新的 QEMU 進程，該進程作為虛擬機的模擬器。KVM 模組會被 QEMU 利用，將虛擬機的 CPU 和記憶體操作傳遞給硬體輔助虛擬化功能。
6.  **監控與管理：** `libvirtd` 持續監控 QEMU 進程的狀態，並可以執行關機、暫停、快照等操作，同樣透過生成對應的 QEMU 指令或利用 QEMU 監控器介面。

**例子：** 當您執行 `virsh start my_vm` 時，`libvirtd` 會將這個請求轉換為一個類似 `qemu-system-x86_64 -enable-kvm -m 2048 -smp 2 ...` 的 QEMU 進程啟動命令。

#### XML 設定檔的重要性

Libvirt 虛擬機的配置資訊儲存在結構化的 XML 檔案中。這種方式有幾個優點：

*   **結構化與可讀性：** XML 提供了一種標準化的方式來描述複雜的資料結構，使其易於機器解析和人類閱讀。
*   **平台獨立性：** Libvirt XML 是抽象的，不直接與任何底層虛擬化技術綁定，實現了更好的可移植性。
*   **版本控制友好：** 純文字格式有利於版本控制系統追蹤配置變更。

**典型虛擬機 XML 範例解析：**

這是一個簡化的 KVM 虛擬機 XML 設定檔片段，用於說明其結構。

```xml
<domain type='kvm'>
  <name>my_test_vm</name>             <!-- 虛擬機名稱 -->
  <uuid>a1b2c3d4-e5f6-7890-1234-567890abcdef</uuid> <!-- 唯一識別碼 -->
  <memory unit='GiB'>2</memory>       <!-- 記憶體大小：2 GiB -->
  <currentMemory unit='GiB'>2</currentMemory>
  <vcpu placement='static'>2</vcpu>   <!-- 虛擬 CPU 數量：2 核 -->
  <os>
    <type arch='x86_64' machine='pc-q35-7.1'>hvm</type> <!-- 作業系統類型與架構 -->
    <boot dev='hd'/>                  <!-- 啟動設備：硬碟 -->
  </os>
  <features>
    <acpi/>
    <apic/>
    <pae/>
  </features>
  <cpu mode='host-passthrough' check='none' migratable='on'/> <!-- CPU 模式，直接透傳宿主機 CPU 特性 -->
  <clock offset='utc'/>
  <on_poweroff>destroy</on_poweroff>
  <on_reboot>restart</on_reboot>
  <on_crash>destroy</on_crash>
  <devices>
    <emulator>/usr/bin/qemu-system-x86_64</emulator> <!-- QEMU 模擬器路徑 -->
    <disk type='file' device='disk'>
      <driver name='qemu' type='qcow2'/>
      <source file='/var/lib/libvirt/images/my_test_vm.qcow2'/> <!-- 虛擬磁碟映像檔路徑 -->
      <target dev='vda' bus='virtio'/> <!-- 虛擬磁碟設備名稱與匯流排類型 -->
      <address type='pci' domain='0x0000' bus='0x04' slot='0x00' function='0x0'/>
    </disk>
    <interface type='network'>
      <mac address='52:54:00:c3:a1:b2'/>
      <source network='default'/>    <!-- 連接到名為 'default' 的虛擬網路 -->
      <model type='virtio'/>         <!-- 網路卡模型：virtio -->
      <address type='pci' domain='0x0000' bus='0x01' slot='0x00' function='0x0'/>
    </interface>
    <graphics type='vnc' port='-1' autoport='yes' listen='0.0.0.0'>
      <listen type='address' address='0.0.0.0'/>
    </graphics>
    <console type='pty'>
      <target type='serial' port='0'/>
    </console>
    <channel type='unix'>
      <source mode='bind' path='/var/lib/libvirt/qemu/channel/target/domain-my_test_vm/org.qemu.guest_agent.0'/>
      <target type='virtio' name='org.qemu.guest_agent.0'/>
      <address type='virtio-serial' controller='0' bus='0' port='1'/>
    </channel>
    <!-- 其他設備如滑鼠、鍵盤、USB 等 -->
  </devices>
</domain>
```

每個標籤和屬性都描述了虛擬機的一個特定方面。例如：
*   `<domain type='kvm'>`：指定虛擬化類型。
*   `<name>my_test_vm</name>`：虛擬機的易讀名稱。
*   `<memory unit='GiB'>2</memory>`：設定記憶體大小為 2 GiB。
*   `<vcpu placement='static'>2</vcpu>`：設定 2 個虛擬 CPU。
*   `<disk ...>`：定義虛擬磁碟，包括映像檔路徑、驅動程式和匯流排類型。
*   `<interface ...>`：定義虛擬網路介面，包括 MAC 地址和連接到的網路。

#### `virsh` 命令行工具基本操作

`virsh` 是管理 Libvirt 最常用的命令行工具，以下是一些基本操作：

*   **列出虛擬機：**
    ```bash
    virsh list           # 列出正在運行的虛擬機
    virsh list --all     # 列出所有（運行中和未運行）的虛擬機
    ```

*   **定義虛擬機（從 XML 檔案）：**
    ```bash
    virsh define my_test_vm.xml # 根據 XML 檔案定義虛擬機，但不會立即啟動
    ```
    *定義* 將虛擬機的配置註冊到 Libvirt 中，使其成為已知資源。

*   **建立並啟動虛擬機（不定義）：**
    ```bash
    virsh create my_test_vm.xml # 從 XML 檔案創建並啟動虛擬機（臨時，關機後配置會丟失）
    ```
    通常用於測試，或不希望將 VM 配置永久保存為 Libvirt domain 時。

*   **啟動已定義的虛擬機：**
    ```bash
    virsh start my_test_vm
    ```

*   **關閉虛擬機 (優雅關機)：**
    ```bash
    virsh shutdown my_test_vm # 發送 ACPI 關機信號，需要 Guest OS 支援
    ```

*   **強制關機虛擬機 (斷電)：**
    ```bash
    virsh destroy my_test_vm # 強制停止虛擬機，類似拔電源，可能導致數據丟失
    ```

*   **暫停/恢復虛擬機：**
    ```bash
    virsh suspend my_test_vm   # 暫停虛擬機運行，狀態保留在記憶體中
    virsh resume my_test_vm    # 恢復暫停的虛擬機
    ```

*   ** undefine 虛擬機（刪除定義）：**
    ```bash
    virsh undefine my_test_vm # 刪除虛擬機的定義，但不會刪除磁碟映像檔
    ```
    在執行此操作前，確保虛擬機已停止 (`virsh shutdown` 或 `virsh destroy`)。

*   **連接到虛擬機控制台：**
    ```bash
    virsh console my_test_vm # 連接到虛擬機的序列埠控制台，需要 Guest OS 配置序列埠
    ```
    按下 `Ctrl + ]` 退出控制台。

*   **編輯虛擬機配置：**
    ```bash
    virsh edit my_test_vm # 使用預設編輯器編輯虛擬機的 XML 配置，自動檢查語法
    ```

-----

### 3. 與相鄰概念的關聯

#### 與底層虛擬化技術 (KVM, Xen, LXC) 的關係

*   **Libvirt 作為這些技術的上層抽象：** Libvirt 的核心價值在於提供一個統一的抽象層。它不直接是 Hypervisor，而是管理 Hypervisor 的工具。對於 KVM 來說，Libvirt 管理 QEMU 進程，QEMU 再利用 KVM 核心模組實現硬體加速。對於 Xen，Libvirt 則與 Xen 的 `xl` 或 `xm` 工具互動。對於 LXC，Libvirt 則透過 LXC 函式庫管理容器。
*   **優勢：** 這種關係使得系統管理員和開發者可以使用一套統一的工具和 API 來管理異構的虛擬化環境，大大降低了學習成本和管理複雜性。

#### 與高階雲平台 (OpenStack, oVirt) 的關係

*   **Libvirt 作為這些平台底層虛擬化管理的核心元件：** 許多大型雲計算平台，如 OpenStack 和 oVirt，都將 Libvirt 作為其虛擬化管理堆疊中的關鍵組件。
    *   **OpenStack Nova：** OpenStack 的計算服務 Nova 透過其 Libvirt 驅動程式與 Libvirt 進行通訊。當使用者在 OpenStack 中啟動一個虛擬機時，Nova 會呼叫 Libvirt API，由 Libvirt 進一步協調底層的 KVM/QEMU 來創建和管理虛擬機。
    *   **oVirt：** oVirt 是一個開源的虛擬化管理系統，它直接基於 Libvirt。oVirt Engine 透過 VDSM (Virtual Desktop and Server Manager) 與 Libvirt 互動，VDSM 運行在每個宿主機上，負責將 oVirt Engine 的指令轉發給 Libvirt。
*   **優勢：** 這些雲平台利用 Libvirt 提供的穩定、可擴展且功能豐富的 API，構建自己的高階抽象和自動化功能，如排程、負載平衡、自助服務門戶等。

#### 與容器技術 (Docker, Kubernetes) 的區別與聯繫

*   **區別：**
    *   **虛擬機 (VM)：** 透過 Hypervisor 模擬完整的硬體環境，每個 VM 運行獨立的 Guest OS。提供強隔離性，資源開銷較大。Libvirt 主要用於管理 VM。
    *   **容器 (Container)：** 共享宿主機的作業系統核心，透過命名空間 (namespaces) 和控制組 (cgroups) 實現資源隔離。更輕量級，啟動速度快，資源開銷小。Docker 和 Kubernetes 是管理容器的主流工具。
*   **聯繫：**
    *   儘管 Libvirt 的主要重點是虛擬機管理，但它也支援管理 LXC (Linux Containers)。LXC 是一種早期的容器技術，而 Docker 則在其基礎上提供了更高級的抽象和工具。
    *   在某些情況下，虛擬機和容器會結合使用。例如，在雲環境中，可能在一個 KVM 虛擬機內部運行 Kubernetes 集群，其中每個 Kubernetes 節點本身就是一個虛擬機，而應用程式則以 Docker 容器的形式運行在這些虛擬機內部。Libvirt 在這裡管理外層的虛擬機。
*   **核心觀念：** 虛擬機提供硬體層級的隔離，容器提供作業系統層級的隔離。它們解決的問題層面不同，但可以互補。

-----

### 4. 進階內容

#### Libvirt 的遠端管理能力

Libvirt 支援多種遠端連接方式，允許在管理機器上透過網路管理遠端宿主機上的虛擬化資源。

*   **URI 格式：** Libvirt 使用統一資源標識符 (URI) 來指定連接到哪個 Libvirt 實例，以及使用何種通訊方式。
    *   `qemu:///system`：連接到本機的 QEMU 驅動程式（系統模式）。
    *   `qemu+ssh://user@remote_host/system`：透過 SSH 連接到遠端主機 `remote_host` 的 QEMU 驅動程式。
    *   `xen:///system`：連接到本機的 Xen 驅動程式。
    *   `lxc:///`：連接到本機的 LXC 驅動程式。

*   **範例：**
    ```bash
    virsh -c qemu+ssh://root@192.168.1.100/system list --all
    ```
    這個命令將透過 SSH 以 `root` 使用者身份連接到 IP 地址為 `192.168.1.100` 的遠端宿主機，並列出其上所有的 KVM 虛擬機。

#### 儲存池 (Storage Pools) 和網路 (Networks) 管理

Libvirt 不僅管理虛擬機本身，還抽象化和管理虛擬機所需的儲存和網路資源。

*   **儲存池 (Storage Pools)：**
    *   **定義：** 儲存池是 Libvirt 對於物理儲存（如目錄、LVM 卷組、iSCSI 目標、NFS 共享等）的抽象。它定義了一個區域，Libvirt 可以從中分配和管理虛擬磁碟映像檔。
    *   **優勢：** 簡化了虛擬磁碟的創建和管理，提供統一介面，無論底層儲存類型如何。
    *   **範例：**
        ```xml
        <pool type='dir'>
          <name>default</name>
          <uuid>...</uuid>
          <target>
            <path>/var/lib/libvirt/images</path>
          </target>
        </pool>
        ```
        這是一個類型為 `dir` (目錄) 的儲存池，其路徑指向 `/var/lib/libvirt/images`。

*   **虛擬網路 (Networks)：**
    *   **定義：** 虛擬網路是 Libvirt 對於虛擬交換機、DHCP 服務和網路位址轉換 (NAT) 等網路服務的抽象。它允許虛擬機在彼此之間以及與宿主機和外部網路之間進行通訊。
    *   **優勢：** 提供獨立且隔離的虛擬網路環境，方便管理虛擬機的網路連接。
    *   **範例：**
        ```xml
        <network>
          <name>default</name>
          <uuid>...</uuid>
          <forward mode='nat'/>
          <bridge name='virbr0' stp='on' delay='0'/>
          <ip address='192.168.122.1' netmask='255.255.255.0'>
            <dhcp>
              <range start='192.168.122.100' end='192.168.122.254'/>
            </dhcp>
          </ip>
        </network>
        ```
        這是一個名為 `default` 的虛擬網路，採用 NAT 模式，橋接在 `virbr0` 介面上，並提供 192.168.122.0/24 網段的 DHCP 服務。

#### 事件監聽 (Event Monitoring)

Libvirt API 支援事件監聽機制，允許應用程式訂閱並接收來自 `libvirtd` 的實時通知。這些事件包括虛擬機的啟動、停止、暫停、遷移等狀態變更，以及儲存和網路事件。

*   **核心觀念：** 這是實現自動化管理和監控的關鍵功能。例如，一個雲平台監控服務可以訂閱 VM 狀態變更事件，以便在虛擬機啟動失敗時及時發出警報。
*   **用途：** 雲平台管理、自動化任務、監控系統、資源調度等。

-----

### 5. 常見錯誤與澄清

*   **Libvirt 不是 Hypervisor：**
    *   **常見錯誤：** 認為 Libvirt 就是 KVM 或 Xen。
    *   **澄清：** Libvirt 是一個管理工具和 API 集合，它運行在宿主機的作業系統層級，用於**管理**底層的 Hypervisor (如 KVM) 或虛擬機監控器。KVM 才是實際的 Hypervisor，它利用 CPU 的硬體虛擬化擴展（Intel VT-x/AMD-V）來運行虛擬機。Libvirt 只是作為兩者之間的橋樑。

*   **`virsh` 命令與 QEMU 命令的區別：**
    *   **常見錯誤：** 直接嘗試使用 QEMU 命令來管理 Libvirt 定義的虛擬機，或混淆兩者的輸出。
    *   **澄清：** `virsh` 是 Libvirt 的命令行介面，它操作的是 Libvirt 的抽象概念（Domain、Network、Storage Pool）。當您使用 `virsh` 啟動一個 KVM 虛擬機時，Libvirt 會在後台生成並啟動一個 QEMU 進程。通常不建議直接手動啟動 QEMU 進程來管理由 Libvirt 定義的虛擬機，因為這樣會繞過 Libvirt 的管理層，可能導致狀態不一致或衝突。應始終透過 `virsh` 或 Libvirt API 來管理 Libvirt 控制下的虛擬機。

*   **XML 設定檔語法錯誤導致的問題：**
    *   **常見錯誤：** 編輯虛擬機 XML 時引入語法錯誤或無效配置，導致虛擬機無法啟動或行為異常。
    *   **澄清：** Libvirt XML 設定檔對語法非常嚴格。微小的拼寫錯誤、標籤閉合不正確、或使用了不支援的屬性值都可能導致問題。
        *   **解決方案：** 始終使用 `virsh edit <domain_name>` 來編輯虛擬機配置。`virsh edit` 會在您保存並退出編輯器時自動檢查 XML 語法，並在發現錯誤時提示您重新編輯，直到語法正確。這是一個非常有用的功能，可以避免許多低級錯誤。
        *   對於新的 XML 檔案，可以使用 `virsh define --file <xml_file>` 來定義虛擬機，Libvirt 會在定義時進行語法檢查。
        *   查閱 Libvirt 官方文件中的 XML 格式規範是理解和編寫正確 XML 的最佳方法。

-----

### 6. 小練習（附詳解）

本練習假設您已經在 Linux 系統上安裝了 Libvirt 和 KVM，並且 `libvirtd` 服務正在運行。

#### 小練習 1: 查詢與創建一個簡單的 KVM 虛擬機

目標：熟悉 Libvirt 的基本查詢和虛擬機生命週期管理。

**步驟：**

1.  **檢查 Libvirt 服務狀態並列出所有虛擬機。**
2.  **創建一個基本的虛擬機 XML 設定檔。**
3.  **使用 `virsh define` 定義虛擬機。**
4.  **啟動虛擬機。**
5.  **確認虛擬機正在運行。**
6.  **嘗試連接到虛擬機控制台 (如果虛擬機有配置序列埠)。**
7.  **關閉虛擬機。**
8.  **確認虛擬機已停止。**
9.  **刪除虛擬機的定義。**

**詳解：**

1.  **檢查 Libvirt 服務狀態並列出所有虛擬機。**
    ```bash
    sudo systemctl status libvirtd
    virsh list --all
    ```
    *預期輸出：* `libvirtd` 應為 `active (running)`。`virsh list --all` 可能會顯示一些預設虛擬機或您的歷史虛擬機。

2.  **創建一個基本的虛擬機 XML 設定檔。**
    首先，確保您有一個可用的 KVM 虛擬機映像檔。如果沒有，可以快速創建一個空的 `qcow2` 映像檔用於測試：
    ```bash
    sudo qemu-img create -f qcow2 /var/lib/libvirt/images/test_vm.qcow2 10G
    # 注意：此映像檔是空的，不能啟動操作系統。僅用於驗證 Libvirt 流程。
    ```
    創建檔案 `test_vm.xml`，內容如下：
    ```xml
    <!-- test_vm.xml -->
    <domain type='kvm'>
      <name>test_vm_01</name>
      <uuid>$(uuidgen)</uuid> <!-- 每次創建時替換為新的 UUID -->
      <memory unit='MiB'>512</memory>
      <currentMemory unit='MiB'>512</currentMemory>
      <vcpu placement='static'>1</vcpu>
      <os>
        <type arch='x86_64' machine='pc-q35-7.1'>hvm</type>
        <boot dev='hd'/>
      </os>
      <features>
        <acpi/>
        <apic/>
        <pae/>
      </features>
      <on_poweroff>destroy</on_poweroff>
      <on_reboot>restart</on_reboot>
      <on_crash>destroy</on_crash>
      <devices>
        <emulator>/usr/bin/qemu-system-x86_64</emulator>
        <disk type='file' device='disk'>
          <driver name='qemu' type='qcow2'/>
          <source file='/var/lib/libvirt/images/test_vm.qcow2'/>
          <target dev='vda' bus='virtio'/>
        </disk>
        <interface type='network'>
          <mac address='52:54:00:12:34:56'/> <!-- 確保 MAC 地址唯一 -->
          <source network='default'/>
          <model type='virtio'/>
        </interface>
        <console type='pty'>
          <target type='serial' port='0'/>
        </console>
        <graphics type='vnc' port='-1' autoport='yes' listen='0.0.0.0'/>
      </devices>
    </domain>
    ```
    **重要：** 在 `test_vm.xml` 中，將 `$(uuidgen)` 替換為實際生成的 UUID。您可以在 Linux 終端運行 `uuidgen` 命令來獲取一個新的 UUID。

3.  **使用 `virsh define` 定義虛擬機。**
    ```bash
    virsh define test_vm.xml
    ```
    *預期輸出：* `Domain test_vm_01 defined from test_vm.xml`

4.  **啟動虛擬機。**
    ```bash
    virsh start test_vm_01
    ```
    *預期輸出：* `Domain test_vm_01 started`

5.  **確認虛擬機正在運行。**
    ```bash
    virsh list
    ```
    *預期輸出：* 應該在列表中看到 `test_vm_01`，狀態為 `running`。

6.  **嘗試連接到虛擬機控制台 (如果虛擬機有配置序列埠)。**
    ```bash
    virsh console test_vm_01
    ```
    *預期輸出：* 如果您的映像檔是空的，可能會看到 QEMU 的 BIOS 錯誤或引導失敗信息。按下 `Ctrl + ]` 退出控制台。

7.  **關閉虛擬機。**
    ```bash
    virsh shutdown test_vm_01
    ```
    *預期輸出：* 如果 Guest OS 沒有啟動或沒有 QEMU Agent，這個命令可能會無效。此時您需要使用 `virsh destroy`。對於我們這個空的測試虛擬機，`shutdown` 會因為沒有 Guest OS 響應而超時。
    **如果 `shutdown` 無效，則使用 `destroy`：**
    ```bash
    virsh destroy test_vm_01
    ```
    *預期輸出：* `Domain test_vm_01 destroyed`

8.  **確認虛擬機已停止。**
    ```bash
    virsh list
    ```
    *預期輸出：* `test_vm_01` 不會出現在 `virsh list` 的輸出中。
    ```bash
    virsh list --all
    ```
    *預期輸出：* `test_vm_01` 應該會出現在 `virsh list --all` 的輸出中，狀態為 `shut off`。

9.  **刪除虛擬機的定義。**
    ```bash
    virsh undefine test_vm_01
    ```
    *預期輸出：* `Domain test_vm_01 has been undefined`

    現在 `virsh list --all` 應該不再顯示 `test_vm_01` 了。

#### 小練習 2: 虛擬機資源調整與查看

目標：學習如何修改已定義虛擬機的配置。

**步驟：**

1.  **重新定義小練習 1 中的 `test_vm_01`。**
2.  **使用 `virsh edit` 查看並修改虛擬機的記憶體和 CPU 數量。**
3.  **啟動虛擬機。**
4.  **使用 `virsh dominfo` 查看更新後的配置。**
5.  **關閉並刪除虛擬機定義。**

**詳解：**

1.  **重新定義小練習 1 中的 `test_vm_01`。**
    確保 `test_vm.xml` 檔案存在，並且 UUID 是唯一的。
    ```bash
    virsh define test_vm.xml
    ```
    *預期輸出：* `Domain test_vm_01 defined from test_vm.xml`

2.  **使用 `virsh edit` 查看並修改虛擬機的記憶體和 CPU 數量。**
    ```bash
    virsh edit test_vm_01
    ```
    這將在您預設的編輯器（如 `vi` 或 `nano`）中打開虛擬機的 XML 設定檔。
    找到 `<memory>` 和 `<vcpu>` 標籤，將它們的值修改為：
    ```xml
      <memory unit='MiB'>1024</memory>       <!-- 從 512 MiB 改為 1024 MiB -->
      <currentMemory unit='MiB'>1024</currentMemory>
      <vcpu placement='static'>2</vcpu>     <!-- 從 1 vCPU 改為 2 vCPU -->
    ```
    保存並退出編輯器。Libvirt 會自動檢查語法。
    *預期輸出：* `Domain test_vm_01 XML configuration edited.`

3.  **啟動虛擬機。**
    ```bash
    virsh start test_vm_01
    ```
    *預期輸出：* `Domain test_vm_01 started`

4.  **使用 `virsh dominfo` 查看更新後的配置。**
    ```bash
    virsh dominfo test_vm_01
    ```
    *預期輸出：* 您應該會看到 `CPU(s):         2` 和 `Max memory:     1048576 KiB` (即 1 GiB)。

5.  **關閉並刪除虛擬機定義。**
    ```bash
    virsh destroy test_vm_01 # 如果沒有 Guest OS，shutdown 會超時
    virsh undefine test_vm_01
    ```
    *預期輸出：* `Domain test_vm_01 destroyed` 和 `Domain test_vm_01 has been undefined`

-----

### 7. 延伸閱讀/參考

*   **Libvirt 官方文件：**
    *   [Libvirt Project Home](https://libvirt.org/)
    *   [Libvirt XML Format](https://libvirt.org/formatdomain.html) (虛擬機設定檔的詳細說明)
    *   [Libvirt API Reference](https://libvirt.org/html/index.html) (程式化介面說明)

*   **KVM 官方文件：**
    *   [KVM (Kernel-based Virtual Machine)](https://www.linux-kvm.org/page/Main_Page)
    *   [QEMU Project](https://www.qemu.org/)

*   **相關雲平台：**
    *   [OpenStack Nova Libvirt Driver](https://docs.openstack.org/nova/latest/admin/configuration/hypervisor-drivers/libvirt.html)
    *   [oVirt Project](https://www.ovirt.org/)

*   **命令行工具教學：**
    *   [virsh Command Reference](https://libvirt.org/manpages/virsh.html)

透過這些資源，您可以更深入地了解 Libvirt 的各種功能、XML 配置選項和高級管理技巧。