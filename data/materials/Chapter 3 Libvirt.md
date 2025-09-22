# Chapter 3 Libvirt：虛擬化管理的核心介面

-----

本章將深入探討 Libvirt，一個強大且廣泛使用的開源工具集，它為虛擬化平台提供了統一的管理介面。無論您是使用 KVM/QEMU、Xen 還是其他虛擬化技術，Libvirt 都能幫助您簡化虛擬機的創建、配置、監控和維護。理解 Libvirt 的工作原理和常用工具，是成為一名優秀虛擬化管理員的必經之路。

## 1. 核心概念與定義

### 什麼是 Libvirt？

Libvirt 是一個提供虛擬化管理功能的開源 API、守護進程（Daemon）和工具集。它的主要目標是提供一個單一、穩定的層，讓開發者和系統管理員能夠以一致的方式與多種虛擬化技術（Hypervisors）進行互動。

#### 定義

*   **Libvirt (Library for Virtualization)**: 一個用於管理各種虛擬化技術的開源管理平台。它提供了一套通用的 API，使得上層應用可以不區分底層 Hypervisor 類型來管理虛擬機。

#### 核心功能

1.  **虛擬機生命週期管理**：包括創建、啟動、停止、暫停、恢復、重啟、刪除虛擬機。
2.  **資源管理**：管理虛擬機的 CPU、記憶體、磁碟、網路等資源配置。
3.  **儲存管理**：管理儲存池（Storage Pools）和儲存卷（Storage Volumes），支援各種儲存後端（例如目錄、LVM、iSCSI、NFS 等）。
4.  **網路管理**：管理虛擬網路（Virtual Networks），包括橋接、NAT 等。
5.  **設備熱插拔**：支援在虛擬機運行時動態添加或移除設備。
6.  **虛擬機快照**：創建、恢復和刪除虛擬機快照。
7.  **實時遷移（Live Migration）**：將運行中的虛擬機從一個物理主機遷移到另一個，而無需停機。
8.  **監控與統計**：獲取虛擬機的運行狀態和資源使用情況。

#### 架構

Libvirt 採用客戶端/伺服器（C/S）架構：
*   **libvirtd (Hypervisor Daemon)**：這是 Libvirt 的核心，作為一個守護進程運行在虛擬化主機上。它負責與底層 Hypervisor（如 KVM/QEMU）直接互動，執行管理操作。
*   **Libvirt API (程式庫)**：提供給上層應用程式調用的 API 介面。這使得像 `virsh`、`virt-manager`、OpenStack 等工具能夠與 `libvirtd` 進行通訊。
*   **virsh (Command-line tool)**：這是 Libvirt 提供的一個功能強大的命令列工具，用於手動管理虛擬化資源。
*   **XML 格式**：Libvirt 使用標準化的 XML 格式來定義虛擬機、儲存池、網路等資源的配置。

### 為什麼需要 Libvirt？

在沒有 Libvirt 的情況下，管理虛擬化環境可能會非常複雜。每個 Hypervisor 都可能有自己的命令列工具和配置格式。Libvirt 解決了這些痛點：

1.  **統一管理介面**：它為多種 Hypervisor 提供了一致的抽象層，讓管理員只需學習一套工具和概念，就能管理異構的虛擬化環境。
2.  **簡化虛擬機生命週期管理**：從創建到刪除，所有的管理操作都透過 Libvirt 進行，大大簡化了流程。
3.  **支援多種虛擬化技術**：Libvirt 不僅支援 KVM/QEMU，還支援 Xen、LXC、VirtualBox 等，提供了廣泛的兼容性。
4.  **API 支援程式化管理**：其提供的 API 介面使得自動化腳本和上層管理平台（如 OpenStack、oVirt）能夠輕鬆地與虛擬化基礎設施集成，實現大規模管理。

-----

## 2. 典型例子與操作流程

本節將帶您了解如何安裝 Libvirt，並透過 `virsh` 命令列工具進行基本的虛擬機管理。

### 2.1 安裝 Libvirt

以 CentOS 和 Ubuntu 為例：

**CentOS/RHEL:**

```bash
sudo dnf install qemu-kvm qemu-img libvirt libvirt-daemon-kvm libvirt-client virt-install bridge-utils -y
sudo systemctl enable --now libvirtd
sudo systemctl status libvirtd
```

**Ubuntu/Debian:**

```bash
sudo apt update
sudo apt install qemu-kvm libvirt-daemon-system libvirt-clients bridge-utils virt-manager -y
sudo systemctl enable --now libvirtd
sudo systemctl status libvirtd
sudo adduser $(id -un) libvirt # 將當前用戶添加到 libvirt 組，以便無需 sudo 即可使用 virsh
```

安裝完成後，確認 `libvirtd` 服務已啟動並運行。

### 2.2 `virsh` 命令列工具基本操作

`virsh` 是與 `libvirtd` 守護進程互動的主要命令列工具。

#### 連線到 Hypervisor

在大多數情況下，`virsh` 會自動連線到本機的預設 Hypervisor。如果需要指定，可以使用 `connect` 命令。
*   **`qemu:///system`**: 連接到本機 KVM/QEMU 系統模式的 Hypervisor。
*   **`qemu:///session`**: 連接到本機 KVM/QEMU 會話模式的 Hypervisor（不常用）。
*   **`xen:///`**: 連接到本機 Xen Hypervisor。

```bash
virsh connect qemu:///system
```

#### 列出虛擬機

*   **`virsh list`**: 列出所有正在運行的虛擬機。
*   **`virsh list --all`**: 列出所有虛擬機，包括正在運行、已關閉或暫停的。
*   **`virsh list --inactive`**: 列出所有未運行的虛擬機。

```bash
virsh list --all
```

#### 建立虛擬機：使用 XML 定義檔

Libvirt 使用 XML 格式來定義虛擬機的配置。這是建立和管理虛擬機最靈活和推薦的方式。

**步驟：**

1.  **準備虛擬機磁碟映像檔**：
    通常我們會使用 `qemu-img` 來創建一個空的磁碟映像檔，或複製一個現有的系統映像檔。

    ```bash
    # 創建一個 10G 的 qcow2 格式磁碟映像檔
    sudo qemu-img create -f qcow2 /var/lib/libvirt/images/my_vm.qcow2 10G
    ```
    或者，從一個現有的系統映像檔（例如 cloud-init 鏡像）複製並擴展：
    ```bash
    # 假設您下載了一個 CentOS-Stream-GenericCloud-8-20210928.1.x86_64.qcow2
    # cp CentOS-Stream-GenericCloud-8-20210928.1.x86_64.qcow2 /var/lib/libvirt/images/my_cloud_vm.qcow2
    # sudo qemu-img resize /var/lib/libvirt/images/my_cloud_vm.qcow2 10G
    ```

2.  **創建虛擬機 XML 定義檔**：
    以下是一個簡單的 KVM 虛擬機 XML 定義檔範例 (`my_vm.xml`)：

    ```xml
    <domain type='kvm'>
      <name>my_vm</name>
      <uuid>$(uuidgen)</uuid> <!-- 每次創建請生成一個新的 UUID -->
      <memory unit='MiB'>1024</memory>
      <currentMemory unit='MiB'>1024</currentMemory>
      <vcpu placement='static'>1</vcpu>
      <os>
        <type arch='x86_64' machine='pc-i440fx-rhel7.6.0'>hvm</type>
        <boot dev='hd'/>
      </os>
      <features>
        <acpi/>
        <apic/>
        <pae/>
      </features>
      <clock offset='utc'/>
      <on_poweroff>destroy</on_poweroff>
      <on_reboot>restart</on_reboot>
      <on_crash>destroy</on_crash>
      <devices>
        <emulator>/usr/bin/qemu-kvm</emulator>
        <disk type='file' device='disk'>
          <driver name='qemu' type='qcow2'/>
          <source file='/var/lib/libvirt/images/my_vm.qcow2'/>
          <target dev='vda' bus='virtio'/>
          <address type='pci' domain='0x0000' bus='0x00' slot='0x07' function='0x0'/>
        </disk>
        <controller type='usb' index='0' model='ich9-ehci1'>
          <address type='pci' domain='0x0000' bus='0x00' slot='0x07' function='0x7'/>
        </controller>
        <controller type='usb' index='0' model='ich9-uhci1'>
          <address type='pci' domain='0x0000' bus='0x00' slot='0x07' function='0x0' multifunction='on'/>
        </controller>
        <controller type='usb' index='0' model='ich9-uhci2'>
          <address type='pci' domain='0x0000' bus='0x00' slot='0x07' function='0x1'/>
        </controller>
        <controller type='usb' index='0' model='ich9-uhci3'>
          <address type='pci' domain='0x0000' bus='0x00' slot='0x07' function='0x2'/>
        </controller>
        <interface type='network'>
          <mac address='52:54:00:xx:xx:xx'/> <!-- 請替換為您自己的 MAC 地址或刪除讓 Libvirt 自動生成 -->
          <source network='default'/>
          <model type='virtio'/>
          <address type='pci' domain='0x0000' bus='0x00' slot='0x03' function='0x0'/>
        </interface>
        <serial type='pty'>
          <target type='system-serial' port='0'/>
        </serial>
        <console type='pty'>
          <target type='serial' port='0'/>
        </console>
        <channel type='unix'>
          <target type='virtio' name='org.qemu.guest_agent.0'/>
        </channel>
        <input type='tablet' bus='usb'/>
        <graphics type='vnc' port='-1' autoport='yes' listen='0.0.0.0'>
          <listen type='address' address='0.0.0.0'/>
        </graphics>
        <video>
          <model type='qxl' vram='16384' heads='1' primary='yes'/>
          <address type='pci' domain='0x0000' bus='0x00' slot='0x02' function='0x0'/>
        </video>
        <memballoon model='virtio'>
          <address type='pci' domain='0x0000' bus='0x00' slot='0x08' function='0x0'/>
        </memballoon>
      </devices>
    </domain>
    ```

    *   `<name>`: 虛擬機的名稱。
    *   `<uuid>`: 虛擬機的唯一標識符，可以使用 `uuidgen` 命令生成。
    *   `<memory>`: 虛擬機分配的記憶體量。
    *   `<vcpu>`: 虛擬機分配的 vCPU 數量。
    *   `<os>`: 作業系統配置，包括架構、機器類型和啟動設備。
    *   `<disk>`: 虛擬機的磁碟配置，`source file` 指定磁碟映像檔的路徑。
    *   `<interface>`: 虛擬機的網路介面配置，`source network` 指定連接到的虛擬網路。`default` 是 Libvirt 預設的 NAT 網路。
    *   `<graphics type='vnc'>`: 配置 VNC 遠端圖形界面。

3.  **定義虛擬機**：將 XML 定義檔導入到 Libvirt。

    ```bash
    virsh define my_vm.xml
    ```

4.  **啟動虛擬機**：

    ```bash
    virsh start my_vm
    ```

5.  **查看虛擬機狀態**：

    ```bash
    virsh list --all
    ```

6.  **連接虛擬機控制台**：
    如果虛擬機配置了 `serial` 或 `console`，可以使用 `virsh console`。

    ```bash
    virsh console my_vm
    ```
    對於圖形界面，可以使用 `virt-viewer` 或 VNC 客戶端連接到 Libvirt 自動分配的 VNC 端口（`virsh vncdisplay my_vm` 可查看端口）。

#### 虛擬機生命週期管理

*   **`virsh shutdown <domain-name>`**: 正常關閉虛擬機（發送 ACPI shutdown 信號）。
*   **`virsh reboot <domain-name>`**: 正常重啟虛擬機（發送 ACPI reboot 信號）。
*   **`virsh suspend <domain-name>`**: 暫停虛擬機運行，狀態保存在記憶體中。
*   **`virsh resume <domain-name>`**: 恢復被暫停的虛擬機。
*   **`virsh destroy <domain-name>`**: 強制關閉虛擬機（類似於拔掉電源）。請謹慎使用，可能導致數據損壞。
*   **`virsh undefine <domain-name>`**: 從 Libvirt 中移除虛擬機的定義。**這不會刪除磁碟映像檔。**

```bash
virsh shutdown my_vm
virsh start my_vm
virsh destroy my_vm # 強制關閉
virsh undefine my_vm # 移除定義
```

### 2.3 儲存池與網路管理

Libvirt 不僅管理虛擬機本身，也管理其依賴的儲存和網路資源。

#### 儲存池（Storage Pools）

儲存池是邏輯上組織儲存卷的容器。Libvirt 支援多種類型的儲存池，如 `dir` (目錄)、`lvm` (LVM 卷組)、`iscsi` (iSCSI 目標) 等。

*   **`virsh pool-list --all`**: 列出所有儲存池。
*   **`virsh pool-define-as <pool-name> <type> - -source-path <path>`**: 定義一個新的儲存池。
*   **`virsh pool-start <pool-name>`**: 啟動一個儲存池。
*   **`virsh pool-build <pool-name>`**: 格式化/初始化一個儲存池（例如目錄類型會創建目錄）。
*   **`virsh pool-autostart <pool-name>`**: 設定儲存池隨 Libvirt 服務啟動而自動啟動。

**範例：創建一個目錄儲存池**

1.  準備目錄：
    ```bash
    sudo mkdir -p /data/libvirt/images
    ```
2.  創建儲存池 XML (`mypool.xml`):
    ```xml
    <pool type='dir'>
      <name>mypool</name>
      <target>
        <path>/data/libvirt/images</path>
      </target>
    </pool>
    ```
3.  定義、構建、啟動並設置自動啟動：
    ```bash
    virsh pool-define mypool.xml
    virsh pool-build mypool
    virsh pool-start mypool
    virsh pool-autostart mypool
    virsh pool-list --all
    ```

#### 儲存卷（Storage Volumes）

儲存卷是儲存池中的實際磁碟映像檔。

*   **`virsh vol-list <pool-name>`**: 列出指定儲存池中的所有儲存卷。
*   **`virsh vol-create-as <pool-name> <vol-name> <size> [--format <format>]`**: 在指定儲存池中創建一個新的儲存卷。

**範例：在 `mypool` 中創建一個 5G 的 QCOW2 儲存卷**

```bash
virsh vol-create-as mypool new_disk.qcow2 5G --format qcow2
virsh vol-list mypool
```

#### 虛擬網路（Virtual Networks）

Libvirt 可以創建和管理虛擬網路，為虛擬機提供網路連接。預設通常有一個 `default` NAT 網路。

*   **`virsh net-list --all`**: 列出所有虛擬網路。
*   **`virsh net-define <xml-file>`**: 定義一個新的虛擬網路。
*   **`virsh net-start <network-name>`**: 啟動一個虛擬網路。
*   **`virsh net-autostart <network-name>`**: 設定虛擬網路隨 Libvirt 服務啟動而自動啟動。

**範例：創建一個橋接網路 (需要物理主機上有一個橋接網卡，或者使用現有的 `br0`)**

```xml
<!-- my_bridge_net.xml -->
<network>
  <name>my_bridge_net</name>
  <forward mode='bridge'/>
  <bridge name='br0'/> <!-- 假設您已經配置了 br0 橋接網卡 -->
</network>
```
```bash
virsh net-define my_bridge_net.xml
virsh net-start my_bridge_net
virsh net-autostart my_bridge_net
virsh net-list --all
```

-----

## 3. 與相鄰概念的關聯

### 3.1 與 KVM/QEMU 的關係

*   **Libvirt 是 KVM/QEMU 的上層管理工具**：KVM 是 Linux 內核的一個模組，提供了硬體虛擬化能力；QEMU 是一個通用的開源機器模擬器和虛擬化器。KVM 藉助 QEMU 實現對虛擬機的完整模擬。然而，直接使用 QEMU 命令非常複雜。
*   Libvirt 提供了一個抽象層，將底層複雜的 QEMU/KVM 命令封裝起來，通過簡單的 XML 配置和 `virsh` 命令來管理虛擬機。它處理了記憶體分配、磁碟掛載、網路配置等一系列細節，極大地簡化了 KVM/QEMU 的使用。

### 3.2 與 `virt-manager` 的關係

*   **`virt-manager` 是 Libvirt 的圖形化前端**：`virt-manager` 是一個桌面應用程式，提供了友好的圖形用戶介面（GUI），用於管理 Libvirt 控制的虛擬機。
*   它透過 Libvirt API 與 `libvirtd` 守護進程通訊，實現虛擬機的創建、編輯、監控等操作。如果您更喜歡圖形界面，`virt-manager` 是管理 Libvirt 環境的絕佳選擇。

### 3.3 與雲端平台（OpenStack、oVirt）的關係

*   **Libvirt 是雲端平台的核心虛擬化驅動**：許多大型雲端管理平台，如 OpenStack 和 Red Hat 的 oVirt，都使用 Libvirt 作為其虛擬化層的基礎。
*   當您在 OpenStack 中啟動一個虛擬機時，底層的 Nova 計算服務會透過 Libvirt API，指示物理主機上的 `libvirtd` 守護進程創建並啟動 KVM 虛擬機。這使得這些平台能夠有效地管理成千上萬的虛擬機。

### 3.4 與容器化技術（LXC、Docker）的關係

*   **Libvirt 也能管理 LXC 容器**：LXC（Linux Containers）是一種基於 Linux 內核 Cgroups 和 Namespace 技術的輕量級虛擬化方案。Libvirt 提供了對 LXC 容器的管理支援。
*   然而，對於 Docker、Kubernetes 等新一代容器化技術，它們通常有自己的管理工具和生態系統，不再透過 Libvirt 進行管理。儘管底層某些概念（如 Cgroups）有重疊，但從管理層面看，它們是獨立的系統。

-----

## 4. 進階內容

### 4.1 虛擬機快照（Snapshots）

Libvirt 支援虛擬機的快照功能，這對於備份、測試和回滾虛擬機狀態非常有用。

*   **內部快照 (Internal Snapshots)**：將虛擬機的狀態（磁碟、記憶體、設備狀態）保存到原始磁碟映像檔中。只支援 QCOW2 格式。
*   **外部快照 (External Snapshots)**：為虛擬機的磁碟創建一個新的增量盤，並在新的檔案中記錄更改。這通常用於生產環境，因為它對原始磁碟的影響較小。

**常用命令：**

*   **`virsh snapshot-create-as <domain-name> <snapshot-name> --description "..."`**: 創建一個快照。
*   **`virsh snapshot-list <domain-name>`**: 列出指定虛擬機的所有快照。
*   **`virsh snapshot-revert <domain-name> <snapshot-name>`**: 將虛擬機恢復到指定的快照狀態。
*   **`virsh snapshot-delete <domain-name> <snapshot-name>`**: 刪除一個快照。

### 4.2 虛擬機遷移（Live Migration）

實時遷移允許在不中斷服務的情況下，將一個運行中的虛擬機從一個物理主機移動到另一個物理主機。

**前提條件：**

*   兩個主機都需要安裝 Libvirt。
*   兩個主機都可以訪問相同的虛擬機磁碟（例如，透過 NFS 或 iSCSI 共享儲存）。
*   兩個主機的 CPU 類型兼容。
*   兩個主機之間有足夠的網路頻寬。

**命令：**

```bash
virsh migrate --live <domain-name> qemu+ssh://<destination-host>/system
```
這條命令會將 `domain-name` 虛擬機從當前主機實時遷移到 `destination-host`。`--live` 參數表示實時遷移。

### 4.3 儲存卷管理

除了創建儲存卷，Libvirt 還提供了更細粒度的儲存卷操作：

*   **`virsh vol-delete <vol-name> --pool <pool-name>`**: 刪除儲存卷。
*   **`virsh vol-resize <vol-name> <new-size> --pool <pool-name>`**: 調整儲存卷大小。
*   **`virsh vol-upload <vol-name> <source-file> --pool <pool-name>`**: 將本地檔案上傳為儲存卷。
*   **`virsh vol-download <vol-name> <destination-file> --pool <pool-name>`**: 將儲存卷下載到本地檔案。

-----

## 5. 常見錯誤與澄清

1.  **錯誤：嘗試直接操作 QEMU 命令來管理 Libvirt 定義的虛擬機。**
    *   **澄清**：Libvirt 會在內部生成 QEMU 命令。一旦虛擬機被 Libvirt 定義，所有的生命週期管理都應透過 Libvirt (`virsh` 或其 API) 進行。直接操作 QEMU 命令可能會導致 Libvirt 的狀態與實際虛擬機狀態不同步，造成混亂。

2.  **錯誤：XML 定義檔語法錯誤或引用了不存在的資源（如磁碟檔案、網路）。**
    *   **澄清**：Libvirt 的 XML 語法嚴格。在 `virsh define` 之前，可以使用 `virsh define --validate <xml-file>` 來檢查 XML 檔案的語法正確性。虛擬機啟動失敗時，請仔細檢查 XML 檔案中引用的路徑和名稱是否正確。

3.  **錯誤：虛擬機啟動失敗，但沒有明確的錯誤訊息。**
    *   **澄清**：當 `virsh start` 失敗時，通常會在 `libvirtd` 的日誌中找到更詳細的錯誤資訊。檢查系統日誌：
        ```bash
        sudo journalctl -u libvirtd -f # 實時查看 libvirtd 日誌
        ```
        常見原因包括記憶體不足、磁碟映像檔路徑錯誤或權限問題、網路配置錯誤、SELinux 或 AppArmor 限制等。

4.  **錯誤：遠端連接 Libvirt 失敗（例如使用 `virt-manager` 或 `virsh -c qemu+ssh://host/system`）。**
    *   **澄清**：
        *   確認遠端主機的 `libvirtd` 服務正在運行。
        *   確認 SSH 服務可正常連接。
        *   檢查防火牆（`firewalld` 或 `ufw`）是否阻擋了連接。通常需要開放 SSH 端口 (22)，對於更直接的 Libvirt TCP 連接（如果配置了的話），預設端口是 16509。
        *   確認用戶是否有足夠的權限遠端連接，通常需要被添加到 `libvirt` 組。

5.  **錯誤：虛擬機網路不通。**
    *   **澄清**：
        *   檢查虛擬機 XML 配置中的 `<interface>` 部分，確保 `source network` 指定的虛擬網路 (`virsh net-list`) 正在運行。
        *   如果使用的是預設的 `default` NAT 網路，確認宿主機的 IP 轉發已啟用，且 `firewalld` 或 `iptables` 配置允許 NAT 流量。
        *   如果使用的是橋接網路，確認宿主機上的橋接網卡 (`br0`) 已正確配置，且物理網卡已加入橋接。
        *   檢查虛擬機內部的網路配置是否正確（例如 IP 地址、網關、DNS）。

-----

## 6. 小練習（附詳解）

### 小練習 1: 建立一個基本虛擬機

**目標**：透過 XML 定義檔建立一個 KVM 虛擬機，設定 1 CPU, 1024MB RAM, 一個基於 QCOW2 映象檔的磁碟，並將其啟動，最後清理。

**步驟**：

1.  在 `/var/lib/libvirt/images/` 路徑下創建一個 2GB 的 QCOW2 格式磁碟映像檔，命名為 `test_vm_disk.qcow2`。
2.  創建一個名為 `test_vm.xml` 的虛擬機定義檔，配置如上所述的 CPU、記憶體、磁碟（使用剛剛創建的映像檔），並連接到 Libvirt 的 `default` 虛擬網路。
3.  定義並啟動這個虛擬機。
4.  確認虛擬機正在運行。
5.  將虛擬機關閉並從 Libvirt 中移除定義，但保留磁碟映像檔。

**詳解**：

1.  **創建磁碟映像檔**：
    ```bash
    sudo qemu-img create -f qcow2 /var/lib/libvirt/images/test_vm_disk.qcow2 2G
    ```

2.  **創建 `test_vm.xml` 檔**：
    ```xml
    <domain type='kvm'>
      <name>test_vm</name>
      <uuid>$(uuidgen)</uuid>
      <memory unit='MiB'>1024</memory>
      <currentMemory unit='MiB'>1024</currentMemory>
      <vcpu placement='static'>1</vcpu>
      <os>
        <type arch='x86_64' machine='pc-i440fx-rhel7.6.0'>hvm</type>
        <boot dev='hd'/>
      </os>
      <features>
        <acpi/>
        <apic/>
        <pae/>
      </features>
      <clock offset='utc'/>
      <on_poweroff>destroy</on_poweroff>
      <on_reboot>restart</on_reboot>
      <on_crash>destroy</on_crash>
      <devices>
        <emulator>/usr/bin/qemu-kvm</emulator>
        <disk type='file' device='disk'>
          <driver name='qemu' type='qcow2'/>
          <source file='/var/lib/libvirt/images/test_vm_disk.qcow2'/>
          <target dev='vda' bus='virtio'/>
          <address type='pci' domain='0x0000' bus='0x00' slot='0x07' function='0x0'/>
        </disk>
        <interface type='network'>
          <source network='default'/>
          <model type='virtio'/>
          <address type='pci' domain='0x0000' bus='0x00' slot='0x03' function='0x0'/>
        </interface>
        <graphics type='vnc' port='-1' autoport='yes' listen='0.0.0.0'>
          <listen type='address' address='0.0.0.0'/>
        </graphics>
        <video>
          <model type='qxl' vram='16384' heads='1' primary='yes'/>
          <address type='pci' domain='0x0000' bus='0x00' slot='0x02' function='0x0'/>
        </video>
        <memballoon model='virtio'>
          <address type='pci' domain='0x0000' bus='0x00' slot='0x08' function='0x0'/>
        </memballoon>
      </devices>
    </domain>
    ```
    *請務必替換 `$(uuidgen)` 為您執行 `uuidgen` 命令實際生成的 UUID。*

3.  **定義並啟動虛擬機**：
    ```bash
    virsh define test_vm.xml
    virsh start test_vm
    ```

4.  **確認虛擬機狀態**：
    ```bash
    virsh list
    ```
    您應該會看到 `test_vm` 狀態為 `running`。

5.  **關閉並移除定義**：
    ```bash
    virsh shutdown test_vm # 如果虛擬機沒有作業系統，可能無法正常關閉，此時可使用 virsh destroy
    sleep 5 # 等待關閉
    virsh list --all # 確認已關閉
    virsh undefine test_vm
    ```
    此時 `test_vm_disk.qcow2` 檔案仍然存在於 `/var/lib/libvirt/images/`。

-----

### 小練習 2: 管理儲存池與儲存卷

**目標**：建立一個名為 `my_data_pool` 的目錄類型儲存池，並在其中創建一個 1GB 的 `qcow2` 格式儲存卷 `data_disk.qcow2`。

**步驟**：

1.  創建一個用於儲存池的物理目錄 `/opt/libvirt_data/`。
2.  創建一個 `my_data_pool.xml` 檔來定義 `my_data_pool`。
3.  定義、構建、啟動並設置 `my_data_pool` 自動啟動。
4.  在 `my_data_pool` 中創建一個 1GB 的 QCOW2 格式儲存卷 `data_disk.qcow2`。
5.  確認儲存池和儲存卷都已成功創建。
6.  最後清理儲存池和儲存卷。

**詳解**：

1.  **創建儲存目錄**：
    ```bash
    sudo mkdir -p /opt/libvirt_data
    ```

2.  **創建 `my_data_pool.xml` 檔**：
    ```xml
    <pool type='dir'>
      <name>my_data_pool</name>
      <target>
        <path>/opt/libvirt_data</path>
      </target>
    </pool>
    ```

3.  **定義、構建、啟動並設置自動啟動儲存池**：
    ```bash
    virsh pool-define my_data_pool.xml
    virsh pool-build my_data_pool
    virsh pool-start my_data_pool
    virsh pool-autostart my_data_pool
    ```

4.  **創建儲存卷**：
    ```bash
    virsh vol-create-as my_data_pool data_disk.qcow2 1G --format qcow2
    ```

5.  **確認儲存池和儲存卷**：
    ```bash
    virsh pool-list --all
    virsh vol-list my_data_pool
    ```
    您應該會看到 `my_data_pool` 處於 `running` 狀態，並且在其中列出了 `data_disk.qcow2`。

6.  **清理儲存池和儲存卷**：
    ```bash
    virsh vol-delete data_disk.qcow2 --pool my_data_pool # 刪除儲存卷
    virsh pool-destroy my_data_pool                     # 停止儲存池
    virsh pool-undefine my_data_pool                    # 移除儲存池定義
    sudo rm -rf /opt/libvirt_data                       # 刪除實際目錄
    ```

-----

## 7. 延伸閱讀/參考

*   **Libvirt 官方網站**：[https://libvirt.org/](https://libvirt.org/)
    *   Libvirt 的官方文檔是學習其功能和 API 的最佳資源。
*   **KVM 官方網站**：[https://www.linux-kvm.org/](https://www.linux-kvm.org/)
    *   了解 KVM 虛擬化技術的更多細節。
*   **virt-manager 官方網站**：[https://virt-manager.org/](https://virt-manager.org/)
    *   如果您偏好圖形界面管理，`virt-manager` 是必不可少的工具。
*   **Red Hat Enterprise Linux 虛擬化部署和管理指南**
    *   Red Hat 提供了大量關於 Libvirt 和 KVM 的詳細文檔和最佳實踐。
*   **書籍**
    *   `KVM Virtualization Book` (多個版本和作者)
    *   `Mastering KVM Virtualization` (多個版本和作者)

這些資源將幫助您更深入地理解 Libvirt 的各個方面，並在實際環境中有效地利用它來管理您的虛擬化基礎設施。