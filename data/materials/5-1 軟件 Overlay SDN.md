# 5-1 軟件定義網路 (SDN) Overlay 技術

本章將深入探討軟件定義網路 (SDN) 中的 Overlay 技術。Overlay 網路在現代資料中心、雲端運算以及大規模企業網路中扮演著關鍵角色，它允許在現有物理網路基礎設施之上，建立靈活、可程式化且隔離的虛擬網路。我們將從 Overlay 的核心概念出發，逐步解析其運作機制，並探討其在 SDN 環境下的應用。

### #### 1. 核心概念與定義

本節將介紹 SDN、Overlay 網路以及兩者結合形成的「軟件 Overlay SDN」的核心概念。

-----

### ##### 1.1 SDN (Software-Defined Networking) 回顧

在深入探討 Overlay SDN 之前，讓我們先快速回顧 SDN 的核心理念：

*   **控制平面與資料平面分離 (Separation of Control Plane and Data Plane)**：這是 SDN 的基石。傳統網路設備的控制邏輯（路由協定、安全策略）與資料轉發邏輯（封包轉發）緊密耦合。SDN 將這些控制邏輯抽象化並集中到一個中央控制器，而網路設備（交換機、路由器）則只負責按照控制器下發的指令進行資料轉發。
*   **集中式控制 (Centralized Control)**：SDN 控制器提供了一個網路的全局視圖，能夠基於網路整體狀況做出最佳決策，例如流量工程、負載均衡和安全策略部署。
*   **可程式化 (Programmability)**：網路管理員或應用程式可以透過標準 API (如 OpenFlow) 直接與 SDN 控制器互動，動態地修改網路行為，實現網路的自動化和靈活性。

-----

### ##### 1.2 Overlay Network 定義

Overlay Network，中文常譯為「疊加網路」或「覆蓋網路」，是一種在現有物理網路（稱為 Underlay Network）之上，透過軟體模擬或建立的邏輯網路。

*   **核心觀念**：
    *   **邏輯網路而非物理網路**：Overlay 網路由虛擬鏈路和虛擬節點組成，這些虛擬元素與底層的物理拓撲無關。
    *   **在 Underlay 之上運行**：Overlay 網路的流量會被「封裝」成 Underlay 網路可以理解的封包格式（通常是 IP 封包），然後透過 Underlay 網路進行傳輸。對於 Underlay 網路而言，這些 Overlay 流量只是普通的 IP 封包。
    *   **封裝 (Encapsulation)**：這是 Overlay 網路的核心技術。它將 Overlay 網路的原始資料幀（如乙太網路幀）加上額外的標頭，使其能夠透過 Underlay 網路進行路由和傳輸。在目的地，這些額外標頭會被移除，還原原始資料幀。
*   **典型例子**：VPN (Virtual Private Network) 就是一種常見的 Overlay 網路，它在公共網際網路（Underlay）之上建立了一個安全的私有網路。

-----

### ##### 1.3 軟件 Overlay SDN 定義

軟件 Overlay SDN 是將 SDN 的控制平面與 Overlay 網路的資料平面能力相結合的技術。

*   **定義**：它利用 SDN 控制器的集中式控制和可程式化能力，來動態地建立、管理和調整 Overlay 網路。在這種架構中，Underlay 網路提供基本的 IP 連通性，而 Overlay 網路的邏輯拓撲、流量轉發路徑和隔離策略，則完全由 SDN 控制器透過軟體進行定義和控制。
*   **為什麼需要 Overlay SDN？**
    *   **靈活性與敏捷性**：能夠快速部署、修改和銷毀虛擬網路，以適應不斷變化的業務需求，特別是在雲端環境中。
    *   **多租戶隔離 (Multi-Tenancy Isolation)**：為不同的租戶或應用程式提供完全隔離的虛擬網路，即使它們共享相同的物理基礎設施。
    *   **擴展性 (Scalability)**：克服傳統 VLAN 2 層隔離技術的限制（如 VLAN ID 數量上限），支援更大規模的虛擬網路。
    *   **地理分散**：允許跨越不同物理資料中心或園區的伺服器，被納入同一個邏輯 Overlay 網路中。
    *   **與物理網路解耦**：網路管理員無需修改底層物理網路配置，即可部署新的邏輯網路服務。
*   **核心技術元素**：
    *   **隧道技術 (Tunneling Protocols)**：如 VXLAN (Virtual Extensible LAN)、NVGRE (Network Virtualization using Generic Routing Encapsulation)、Geneve (Generic Network Virtualization Encapsulation)。這些協定定義了封裝格式。
    *   **虛擬交換機 (Virtual Switches)**：例如 Open vSwitch (OVS)，它們運行在物理主機上，充當虛擬網路的接入點和隧道端點 (VTEP)。
    *   **SDN 控制器**：負責計算和下發隧道端點之間的轉發規則，以及虛擬網路的策略。

-----

### #### 2. 典型例子與運作推導

本節將以 VXLAN 作為典型的 Overlay 技術，並結合 Open vSwitch (OVS) 的角色，深入探討其運作機制。

-----

### ##### 2.1 VXLAN 作為典型 Overlay 技術

VXLAN (Virtual eXtensible LAN) 是目前最廣泛採用的 Overlay 網路封裝技術之一。它透過在 UDP/IP 封包中封裝乙太網路幀，實現跨越 IP 網路的 Layer 2 網路延伸。

*   **原理**：
    *   VXLAN 將原始的 L2 乙太網路幀（包含 VM 的 MAC 地址和 IP 地址）封裝進一個 UDP 封包。
    *   這個 UDP 封包會被進一步封裝成一個 IP 封包，並透過底層的 Underlay IP 網路進行路由。
    *   在目的地，VXLAN 標頭和 UDP/IP 標頭被移除，還原原始的乙太網路幀，並交付給目標 VM。
*   **VXLAN 封包結構**：
    ```
    | Outer Ethernet Header | Outer IP Header | Outer UDP Header | VXLAN Header | Inner Ethernet Header | Inner IP Header | Payload |
    <----------------- Underlay 網路部分 -----------------> <--------- Overlay 網路部分 --------->
    ```
    *   **Outer Ethernet/IP/UDP Header**：這是 Underlay 網路用來路由封包的資訊。Outer IP Header 中的源 IP 是發送端 VTEP 的 IP，目標 IP 是接收端 VTEP 的 IP。Outer UDP Header 的目標埠通常是 4789 (VXLAN)。
    *   **VXLAN Header**：
        *   **VNI (VXLAN Network Identifier)**：一個 24-bit 的識別符，用來唯一標識一個 VXLAN 網路（類似於 VLAN ID，但規模更大，可支援高達 1600 萬個虛擬網路）。只有擁有相同 VNI 的 VM 才能在同一個 VXLAN 網路上通訊。
        *   其他旗標和保留位。
    *   **Inner Ethernet/IP Header & Payload**：這是原始的 Layer 2 乙太網路幀和其承載的 Layer 3 封包內容。
*   **組成要素**：
    *   **VTEP (VXLAN Tunnel Endpoint)**：VXLAN 隧道的起點和終點。它通常是一個運行在物理主機上的虛擬交換機（如 Open vSwitch）或物理網路設備。VTEP 負責對 Overlay 流量進行封裝和解封裝。每個 VTEP 都有一個唯一的 Underlay IP 地址。
    *   **VNI (VXLAN Network Identifier)**：如上所述，用於隔離和識別不同的虛擬網路。
*   **工作流程推導 (VM1 到 VM2 跨子網通訊)**：
    假設 VM1 (IP: 192.168.1.10, MAC: A, VNI: 100) 和 VM2 (IP: 192.168.1.20, MAC: B, VNI: 100) 位於不同的物理主機 Host A 和 Host B 上，並透過 VXLAN VNI 100 進行通訊。

    1.  **VM1 發送封包**：VM1 發送一個 IP 封包到 VM2 (目的 IP: 192.168.1.20)。此封包的目的 MAC 地址是 VM2 的 MAC 地址 B。
    2.  **Host A 上的 VTEP 接收**：VM1 的虛擬網卡連接到 Host A 上的 VTEP (例如 OVS)。VTEP 接收到這個 L2 乙太網路幀。
    3.  **VTEP 查詢轉發表**：VTEP (OVS) 會查詢其內部轉發表，查找 MAC 地址 B 對應的 VXLAN 隧道端點 (即 Host B 的 VTEP 的 Underlay IP 地址)。這個轉發表資訊通常由 SDN 控制器提前下發。
    4.  **封裝**：VTEP 對 VM1 發出的乙太網路幀進行 VXLAN 封裝：
        *   添加 VXLAN Header (包含 VNI=100)。
        *   添加 UDP Header (目的埠 4789)。
        *   添加 Outer IP Header (源 IP: Host A 的 VTEP IP, 目的 IP: Host B 的 VTEP IP)。
        *   添加 Outer Ethernet Header (源 MAC: Host A 網卡 MAC, 目的 MAC: Host A 到 Host B 路徑上的下一跳路由器 MAC)。
    5.  **Underlay 網路傳輸**：封裝後的 IP 封包被 Host A 發送到 Underlay 網路。Underlay 網路將其視為普通 IP 封包，基於 Outer IP Header 進行路由，直到達到 Host B。
    6.  **Host B 上的 VTEP 接收**：Host B 的 VTEP 接收到這個封裝後的 IP 封包。
    7.  **解封裝**：VTEP 檢查 UDP 目的埠是否為 VXLAN 埠，然後移除 Outer Ethernet/IP/UDP Header 和 VXLAN Header。它會確認 VNI 是否匹配（VNI=100）。
    8.  **交付**：解封裝後，還原出原始的 L2 乙太網路幀。VTEP 根據其內部轉發表，將這個乙太網路幀轉發給連接到它的 VM2 的虛擬網卡。VM2 接收到來自 VM1 的封包。

*   **與傳統 VLAN 比較**：
    *   **擴展性**：VXLAN 使用 24-bit 的 VNI，支援高達 $2^{24}$ (約 1600 萬) 個虛擬網路。而傳統 VLAN ID 只有 12-bit，最大支援 4094 個 VLAN，嚴重限制了大型雲端資料中心的規模。
    *   **跨三層網路**：VLAN 只能在同一個二層廣播域內工作。VXLAN 透過 IP 封裝，可以在任何可路由的 IP 網路之上延伸二層網路，突破了物理網路拓撲的限制。

-----

### ##### 2.2 Open vSwitch (OVS) 在 Overlay SDN 中的角色

Open vSwitch (OVS) 是一個開源的多層虛擬交換機，廣泛應用於虛擬化環境和 SDN 解決方案中。在 Overlay SDN 中，OVS 扮演著至關重要的角色。

*   **作為 VTEP**：
    *   OVS 能夠配置為一個或多個 VXLAN 隧道的端點 (VTEP)。
    *   它負責執行 VXLAN 流量的封裝和解封裝操作。
    *   OVS 可以透過 `ovs-vsctl` 命令或 SDN 控制器的 OpenFlow 指令來創建和管理 VXLAN 隧道介面。
    *   例如，一個 OVS 橋接器可以配置一個 `vxlan` 類型的埠，並指定遠端 VTEP 的 IP 地址，從而建立 VXLAN 隧道。
*   **Flow Table 管理 (OpenFlow)**：
    *   OVS 完全支援 OpenFlow 協定。SDN 控制器可以透過 OpenFlow 向 OVS 下發精細的轉發規則（Flow Entries）。
    *   這些規則決定了如何處理傳入的流量，包括：
        *   將來自 VM 的流量封裝到特定的 VXLAN 隧道 (根據目的 MAC/IP 和 VNI)。
        *   將從 VXLAN 隧道解封裝的流量轉發到正確的 VM。
        *   處理 ARP 請求，廣播封包等。
    *   **例子**：
        1.  當 VM1 發送封包到 VM2 (MAC B, IP 192.168.1.20) 時，OVS 上的 OpenFlow 規則可能會這樣：
            *   `match (in_port=VM1_port, dl_dst=MAC_B)`
            *   `action (set_field=vni:100, tunnel_dst=HostB_VTEP_IP, output=VXLAN_port)`
            2.  當從 VXLAN 隧道接收到目的為 VM2 的封包時：
            *   `match (in_port=VXLAN_port, vni=100, dl_dst=MAC_B)`
            *   `action (strip_tunnel, output=VM2_port)`
    *   透過 SDN 控制器動態管理這些 Flow Table，可以實現 Overlay 網路的快速部署、故障轉移和流量工程。

-----

### #### 3. 與相鄰概念的關聯

本節將探討軟件 Overlay SDN 與 Underlay Network、SDN 控制器以及 NFV 之間的關係。

-----

### ##### 3.1 與 Underlay Network 的關聯

Overlay 和 Underlay 網路是相輔相成的。

*   **Underlay 提供底層物理連通性**：Underlay 網路是物理基礎設施，負責所有網路設備之間的 IP 可達性。它確保了任何一個 VTEP 能夠透過 IP 網路與另一個 VTEP 進行通訊。Underlay 通常基於傳統路由協定（如 OSPF, BGP）運行。
*   **Overlay 在 Underlay 之上建立邏輯網路**：Overlay 網路利用 Underlay 提供的 IP 可達性來傳輸其封裝後的流量。
*   **Underlay 不需感知 Overlay 流量的內部細節**：對 Underlay 網路而言，Overlay 流量只是普通的 IP 封包（包含 Outer IP Header）。Underlay 路由器和交換機只需要根據這些 IP 封包的源 IP 和目的 IP 進行轉發，無需知道封包內部承載的是哪個 VXLAN 網路的流量，也無需關心 VNI 等 Overlay 特有的資訊。這使得 Underlay 網路的設計可以相對簡單和穩定。
*   **Underlay 的性能影響 Overlay**：Underlay 網路的帶寬、延遲、丟包率和穩定性直接影響 Overlay 網路的性能。一個健康的、性能良好的 Underlay 是 Overlay 網路高效運作的基礎。

-----

### ##### 3.2 與 SDN 控制器的關聯

SDN 控制器是軟件 Overlay SDN 的「大腦」。

*   **SDN 控制器負責管理 Overlay 網路**：
    *   **VTEP 發現與註冊**：控制器可以自動發現或手動註冊網路中的 VTEP（例如 OVS 實例）。
    *   **虛擬網路配置**：根據管理員或應用程式的需求，控制器負責分配 VNI，並為虛擬網路中的 VM 配置 IP 地址和 MAC 地址。
    *   **路由資訊分發**：控制器維護一個集中式的「虛擬 MAC-IP-VTEP 映射表」。當 VM1 (VNI X, MAC A) 要與 VM2 (VNI X, MAC B) 通訊時，控制器知道 VM2 位於哪個 VTEP 上。
    *   **Flow Table 下發**：控制器將這些路由和轉發策略轉化為具體的 OpenFlow 規則，並下發給相關的 VTEP (例如 OVS)。這些規則指示 VTEP 如何封裝和解封裝流量，以及如何將流量轉發給正確的 VM。
    *   **動態調整**：當虛擬機遷移、新增或刪除時，控制器能夠動態更新 VTEP 上的轉發規則，確保 Overlay 網路的連通性不受影響。
*   **實現 Overlay 網路的動態配置和管理**：SDN 控制器將複雜的網路配置抽象化，讓管理員可以透過高階介面定義網路策略，而無需直接操作底層設備。這大大提高了網路的自動化和敏捷性。

-----

### ##### 3.3 與 NFV (Network Functions Virtualization) 的關聯

NFV (Network Functions Virtualization) 是將傳統的硬體網路設備功能（如防火牆、負載平衡器、路由器等）虛擬化為運行在標準伺服器上的軟體實例。

*   **NFV 虛擬化網路功能**：NFV 將網路功能從專用硬體中解耦，使其能夠作為虛擬機 (VM) 或容器 (Container) 運行。
*   **Overlay SDN 提供彈性網路基礎設施**：
    *   **隔離與連接**：Overlay SDN 可以為這些虛擬化的網路功能提供隔離且可程式化的網路連接。例如，一個虛擬防火牆可以部署在一個特定的 Overlay 網路上，只處理來自該網路的流量。
    *   **服務鏈 (Service Chaining)**：Overlay SDN 允許靈活地將多個虛擬化網路功能串聯起來，形成一個服務鏈。例如，所有進入某個虛擬網路的流量，可以先被導向虛擬防火牆，然後再導向虛擬入侵檢測系統，最後再導向虛擬負載平衡器，整個過程都由 SDN 控制器在 Overlay 層次進行編排。
    *   **自動化部署**：結合 SDN 控制器，NFV 功能的部署、擴展和管理可以高度自動化，無需手動配置物理網路。
*   **協同效應**：Overlay SDN 和 NFV 共同推動了軟體定義資料中心和雲端運算的發展，實現了網路資源的彈性、高效和自動化管理。

-----

### #### 4. 進階內容

本節將探討 Overlay 網路中路由與閘道的實現方式，以及控制平面的不同模式。

-----

### ##### 4.1 路由與閘道

在 Overlay 網路中，實現虛擬網路內部、虛擬網路之間以及虛擬網路與外部實體網路之間的路由是關鍵。

*   **Overlay 網路內部路由**：
    *   對於同一個 VXLAN (相同 VNI) 內的 VM 通訊，通常是 Layer 2 橋接行為，VTEP 透過封裝/解封裝完成。
    *   如果同一個 VNI 內部有不同的 IP 子網，通常會部署一個虛擬路由器 (Virtual Router)，該虛擬路由器本身也是一個 VM，連接到該 VNI。
*   **Overlay 網路間路由 (Inter-VNI Routing)**：
    *   當不同 VNI 的 VM 需要通訊時，需要 Layer 3 路由。
    *   這通常透過一個「VXLAN 閘道 (VXLAN Gateway)」實現。這個閘道可以是：
        *   **虛擬路由器**：一個運行在物理主機上的虛擬機，配有多個虛擬網卡，每個網卡連接到不同的 VNI，並配置相應的 IP 地址。它負責在不同 VNI 之間進行 IP 路由。SDN 控制器會將流量路由到此虛擬路由器。
        *   **分布式 VXLAN 閘道**：一些現代的 VTEP（如運行在物理設備上的 VTEP）本身就可以充當 Layer 3 閘道，直接在 VTEP 內部實現不同 VNI 之間的 IP 路由功能，而無需將流量發送給一個獨立的虛擬路由器。SDN 控制器會配置這些 VTEP 的路由表。
*   **Overlay 網路與外部網路路由 (North-South Routing)**：
    *   虛擬網路內的 VM 需要訪問網際網路或公司內部其他實體網路時，需要一個連接 Overlay 網路與 Underlay 網路的「外部閘道 (External Gateway)」。
    *   這個閘道將 Overlay 流量解封裝並路由到實體網路，反之亦然。它可能是一個物理路由器、防火牆，或是專門配置來處理這種流量的 VTEP。
    *   SDN 控制器負責配置路由規則，引導流量進出這個外部閘道。

-----

### ##### 4.2 控制平面（Control Plane）模式

SDN Overlay 網路的控制平面可以採取不同的模式來管理 VTEP 之間的映射資訊和路由。

*   **集中式控制平面 (Centralized Control Plane)**：
    *   **SDN 控制器作為唯一控制點**：如前所述，SDN 控制器維護所有 VM 的 MAC-IP-VTEP 映射資訊，以及 VNI 分配。
    *   **主動推送 (Proactive Push)**：控制器監聽虛擬機的生命週期事件 (如啟動、遷移)，並主動計算並下發 OpenFlow 規則給所有相關的 VTEP。
    *   **反應式查詢 (Reactive Query)**：當 VTEP 收到一個目的 MAC 地址未知（例如 ARP 請求或目的 MAC 不在轉發表中）的流量時，它會將封包發送給控制器。控制器查詢其全局知識庫，然後回覆 VTEP 應採取的行動（例如廣播 ARP 請求到所有相關 VTEP，或下發新的轉發規則）。
    *   **優點**：易於管理和調試，全局優化。
    *   **缺點**：控制器可能成為單點故障，可擴展性可能受限於控制器的處理能力。
*   **分散式控制平面 (Distributed Control Plane)**：
    *   **BGP EVPN (Border Gateway Protocol Ethernet VPN)**：這是一個常見的 Overlay 控制平面協定，特別是在大型資料中心中。
    *   **原理**：Underlay 網路的路由器 (或 VTEP 本身) 使用 BGP 協定的 EVPN 擴展來交換虛擬機的 MAC 地址和 IP 地址資訊，以及它們所在的 VTEP IP 地址和 VNI。
    *   **運作方式**：
        1.  每個 VTEP（或其連接的路由設備）將其本地 VM 的 MAC/IP 資訊透過 BGP EVPN 廣播給其他 VTEP。
        2.  每個 VTEP 都維護一個局部視圖的 MAC-IP-VTEP 映射表，並根據接收到的 BGP EVPN 路由更新自己的轉發資訊。
        3.  當 VM 遷移時，相關的 VTEP 會發送更新的 BGP EVPN 路由，所有 VTEP 會迅速更新其轉發表。
    *   **優點**：高度可擴展，控制平面分散化，避免單點故障。
    *   **缺點**：配置相對複雜，需要 Underlay 設備支援 BGP EVPN。
    *   **與 SDN 結合**：SDN 控制器可以在更上層編排 BGP EVPN，簡化其配置和管理，或者作為 BGP EVPN 的路由反射器 (Route Reflector)。

-----

### #### 5. 常見錯誤與澄清

本節將針對軟件 Overlay SDN 的一些常見誤解進行澄清。

-----

### ##### 5.1 誤解一：Overlay 網路不需要 Underlay 網路。

*   **澄清**：這是最常見的誤解之一。Overlay 網路絕非獨立存在，它必須依賴一個健壯的 Underlay 網路來提供底層的物理連通性和 IP 可達性。Overlay 流量被封裝成 Underlay 網路可以處理的 IP 封包，並透過 Underlay 網路進行傳輸。Underlay 網路的任何故障或性能問題都會直接影響到 Overlay 網路的運作。想像一下， Overlay 就像在高速公路（Underlay）上行駛的貨櫃車（封裝後的流量），沒有高速公路，貨櫃車就無法通行。

-----

### ##### 5.2 誤解二：Overlay 網路就是 VLAN。

*   **澄清**：雖然 Overlay 網路和 VLAN 都用於網路隔離，但它們的原理和能力有本質區別。
    *   **VLAN (Virtual Local Area Network)**：是一種二層 (Layer 2) 隔離技術，透過在乙太網路幀中添加 802.1Q 標籤來區分不同的廣播域。VLAN 的主要限制是：
        *   **規模限制**：只有 12-bit VLAN ID，最多支援 4094 個 VLAN，不足以滿足大型雲端環境的多租戶需求。
        *   **跨越限制**：VLAN 只能在同一個二層廣播域內延伸。跨越三層網路的 VLAN 需要複雜的路由配置。
    *   **Overlay Network (例如 VXLAN)**：是一種基於封裝的技術，在三層 IP 網路之上建立邏輯二層網路。
        *   **擴展性**：VXLAN 使用 24-bit VNI，支援 1600 萬個虛擬網路。
        *   **跨越三層網路**：由於是 IP 封裝，Overlay 網路可以無縫地跨越任何可路由的 IP 網路，無論物理拓撲如何。
    *   總結來說，Overlay 網路提供了比 VLAN 更高的擴展性、靈活性和跨網路能力。

-----

### ##### 5.3 誤解三：SDN 控制器負責轉發 Overlay 流量。

*   **澄清**：SDN 控制器是 Overlay 網路的「大腦」，負責「控制平面」的工作，即計算、管理和下發流量轉發的策略和規則。然而，實際的 Overlay 流量轉發工作，即封裝和解封裝，仍然由「資料平面」的設備（如 VTEP，通常是虛擬交換機 Open vSwitch 或支援 VXLAN 的物理網路設備）來完成。控制器不會接收和轉發用戶資料流量，它只負責告訴 VTEP 應該如何轉發。

-----

### #### 6. 小練習 (附詳解)

本節提供兩個小練習，幫助讀者鞏固對軟件 Overlay SDN 的理解。

-----

### ##### 6.1 小練習一：VXLAN 封裝與解封裝分析

**情境**：
假設有兩台虛擬機 VM1 和 VM2，它們都屬於 VXLAN 網路 VNI 101，並且分別運行在兩台不同的物理主機 Host A 和 Host B 上。Host A 和 Host B 的 VTEP IP 地址分別為 `10.0.0.10` 和 `10.0.0.20`。VM1 的 IP 地址為 `192.168.10.5`，MAC 地址為 `AA:AA:AA:AA:AA:AA`；VM2 的 IP 地址為 `192.168.10.6`，MAC 地址為 `BB:BB:BB:BB:BB:BB`。現在 VM1 向 VM2 發送一個 IP 封包。

**問題**：
請詳細描述這個 IP 封包從 VM1 發出，經過 Host A 的 VTEP 封裝，透過 Underlay 網路傳輸，到 Host B 的 VTEP 解封裝，最終到達 VM2 的過程中，封包各層標頭的變化。

**詳解**：

1.  **VM1 發送原始 IP 封包 (Overlay 網路內部)**：
    *   **內層乙太網路頭 (Inner Ethernet Header)**：
        *   源 MAC: `AA:AA:AA:AA:AA:AA` (VM1)
        *   目的 MAC: `BB:BB:BB:BB:BB:BB` (VM2)
    *   **內層 IP 頭 (Inner IP Header)**：
        *   源 IP: `192.168.10.5` (VM1)
        *   目的 IP: `192.168.10.6` (VM2)
    *   **數據部分 (Payload)**：VM1 發送的實際應用數據。

2.  **Host A 上的 VTEP (例如 OVS) 接收並封裝**：
    *   Host A 的 VTEP 接收到上述原始 IP 封包。根據其轉發表（由 SDN 控制器下發或學習而來），它知道目的 MAC `BB:BB:BB:BB:BB:BB` 屬於 VNI 101，且位於遠端 VTEP `10.0.0.20`。
    *   **VXLAN 頭 (VXLAN Header) 添加**：
        *   VNI: `101`
        *   其他 VXLAN 標誌位。
    *   **UDP 頭 (Outer UDP Header) 添加**：
        *   源埠: (任意高位埠，由 VTEP 動態分配)
        *   目的埠: `4789` (VXLAN 標準埠)
    *   **外層 IP 頭 (Outer IP Header) 添加**：
        *   源 IP: `10.0.0.10` (Host A 的 VTEP IP)
        *   目的 IP: `10.0.0.20` (Host B 的 VTEP IP)
    *   **外層乙太網路頭 (Outer Ethernet Header) 添加**：
        *   源 MAC: (Host A 物理網卡的 MAC 地址)
        *   目的 MAC: (Underlay 網路中 Host A 到達 `10.0.0.20` 的下一跳路由器或交換機的 MAC 地址)

3.  **封裝後的封包在 Underlay 網路中傳輸**：
    *   Underlay 網路中的路由器和交換機只會根據**外層 IP 頭**（源 `10.0.0.10`，目的 `10.0.0.20`）進行路由轉發，它們不關心封包內部是 VXLAN 流量，也不讀取內層的 IP 或 MAC 地址。

4.  **Host B 上的 VTEP 接收並解封裝**：
    *   Host B 的 VTEP 接收到從 Underlay 網路傳輸來的封包。
    *   它首先檢查外層 UDP 目的埠 `4789`，確認這是 VXLAN 流量。
    *   **移除外層乙太網路頭、IP 頭、UDP 頭**。
    *   **移除 VXLAN 頭**：VTEP 檢查 VNI 是否為 `101`，確認這是發往本地 VNI 的流量。
    *   此時，還原出原始的**內層乙太網路頭**和**內層 IP 頭**：
        *   源 MAC: `AA:AA:AA:AA:AA:AA`
        *   目的 MAC: `BB:BB:BB:BB:BB:BB`
        *   源 IP: `192.168.10.5`
        *   目的 IP: `192.168.10.6`

5.  **VTEP 將解封裝的封包交付給 VM2**：
    *   Host B 的 VTEP 根據內層乙太網路頭的目的 MAC `BB:BB:BB:BB:BB:BB`，將封包轉發給連接到它的 VM2 的虛擬網卡。
    *   VM2 最終收到來自 VM1 的 IP 封包。

-----

### ##### 6.2 小練習二：SDN 控制器如何配置 OVS 實現 Overlay 轉發

**情境**：
你正在使用一個基於 OpenDaylight 的 SDN 控制器，管理兩個運行 Open vSwitch (OVS) 的物理主機 Host A 和 Host B。Host A 上的 OVS 名為 `br-int`，其 VTEP IP 為 `10.0.0.10`；Host B 上的 OVS 名為 `br-int`，其 VTEP IP 為 `10.0.0.20`。
VM1 (MAC `AA:AA:AA:AA:AA:AA`, VNI 200) 連接到 Host A 的 OVS 上的埠 `vnet1`。
VM2 (MAC `BB:BB:BB:BB:BB:BB`, VNI 200) 連接到 Host B 的 OVS 上的埠 `vnet2`。

**問題**：
請描述 SDN 控制器需要向 Host A 上的 OVS (`br-int`) 下發哪些 OpenFlow 規則，以確保 VM1 發往 VM2 的流量能夠正確地透過 VXLAN 隧道進行封裝和轉發。假設控制器已經知道 VM2 位於 `10.0.0.20`。

**詳解**：

SDN 控制器需要向 Host A 上的 OVS (`br-int`) 下發至少以下兩條主要的 OpenFlow 規則（可能還有其他輔助規則如 ARP 處理、未知目的 MAC 處理等，這裡只關注核心轉發邏輯）：

1.  **規則 1：將來自 VM1 (連接埠 `vnet1`) 發往 VM2 (MAC `BB:BB:BB:BB:BB:BB`) 的流量，封裝到 VXLAN 隧道**

    *   **目的**：匹配從 VM1 虛擬網卡 (`vnet1`) 發出、目的 MAC 地址為 VM2 的流量，然後將其封裝成 VXLAN 封包，並透過 VXLAN 隧道發送出去。
    *   **OpenFlow 規則示例**：
        ```
        flow-mod {
            table_id: 0,
            priority: 100,
            match: {
                in_port: "vnet1",                              // 匹配輸入埠為 VM1 連接埠
                ethernet_match: {
                    ethernet_destination: { address: "BB:BB:BB:BB:BB:BB" } // 匹配目的 MAC 為 VM2
                }
            },
            instructions: [
                {
                    apply_actions: {
                        action: [
                            {
                                set_field: {                                // 設置 VXLAN 隧道識別碼
                                    nxm_0x8000000_field: "vni_200"          // OpenFlow 通常使用 NXM 字段來表示 VXLAN VNI
                                }
                            },
                            {
                                set_field: {                                // 設置外層 IP 目的地址為 Host B 的 VTEP IP
                                    ipv4_destination: "10.0.0.20"
                                }
                            },
                            {
                                output: {                                   // 將封包輸出到 VXLAN 埠
                                    port_id: "VXLAN_TUNNEL_PORT_ID"         // 這裡需要 OVS 預先創建好一個連接到遠端 VTEP 的 VXLAN 埠
                                }
                            }
                        ]
                    }
                }
            ]
        }
        ```
        *   **說明**：`VXLAN_TUNNEL_PORT_ID` 是一個邏輯埠 ID，代表 Host A OVS 上為 VXLAN 隧道創建的埠。這個埠本身在 OVS 配置中已經定義了其類型為 `vxlan`，並指向遠端 VTEP 的 IP 地址 (`10.0.0.20`)。控制器只需指示流量從這個邏輯埠輸出即可。

2.  **規則 2：將從 VXLAN 隧道 (VNI 200) 接收到、目的為本地 VM1 (MAC `AA:AA:AA:AA:AA:AA`) 的流量，進行解封裝並轉發**

    *   **目的**：匹配從 VXLAN 隧道輸入、VNI 為 200、且目的 MAC 地址為本地 VM1 的流量，然後移除 VXLAN 封裝，並將原始流量轉發給 VM1。
    *   **OpenFlow 規則示例**：
        ```
        flow-mod {
            table_id: 0,
            priority: 100,
            match: {
                in_port: "VXLAN_TUNNEL_PORT_ID",                // 匹配輸入埠為 VXLAN 隧道埠
                tunnel_id: "200",                               // 匹配 VXLAN VNI 為 200 (表示來自 VNI 200 的流量)
                ethernet_match: {
                    ethernet_destination: { address: "AA:AA:AA:AA:AA:AA" } // 匹配目的 MAC 為 VM1
                }
            },
            instructions: [
                {
                    apply_actions: {
                        action: [
                            {
                                pop_mpls: { ether_type: 2048 }  // 假設 VTEP 處理 VXLAN 解封裝的 action
                            },
                            {
                                output: {                       // 將封包輸出到 VM1 連接埠
                                    port_id: "vnet1"
                                }
                            }
                        ]
                    }
                }
            ]
        }
        ```
        *   **說明**：在 OpenFlow/OVS 中，`pop_mpls` 或 `strip_vlan` 等指令通常用於移除特定標籤。對於 VXLAN，OVS 內部有能力根據其埠類型進行自動解封裝。這裡的 `pop_mpls` 是一個抽象示例，實際操作可能更為複雜或由 OVS 內部機制處理。關鍵是控制器指示 OVS 解封裝並將原始乙太網路幀轉發到正確的本地埠。`tunnel_id` 在 OpenFlow 中用於匹配 VXLAN 的 VNI 字段。

這些規則確保了 VM1 發送的流量能被正確封裝並送達遠端 VTEP，以及從遠端 VTEP 發來的流量能被正確解封裝並交付給本地的 VM1。

-----

### #### 7. 延伸閱讀與參考

*   **RFC 7348 - Virtual eXtensible Local Area Network (VXLAN)**：VXLAN 協定的官方標準文檔。
    *   [https://tools.ietf.org/html/rfc7348](https://tools.ietf.org/html/rfc7348)
*   **Open vSwitch (OVS) 官方文檔**：了解 Open vSwitch 的詳細功能、配置和 OpenFlow 支援。
    *   [https://www.openvswitch.org/](https://www.openvswitch.org/)
*   **SDN 控制器平台文檔**：
    *   **OpenDaylight (ODL)**：一個大型的開源 SDN 控制器框架。
        *   [https://www.opendaylight.org/](https://www.opendaylight.org/)
    *   **ONOS (Open Network Operating System)**：另一個開源 SDN 控制器，專注於電信級應用。
        *   [https://onosproject.org/](https://onosproject.org/)
*   **雲端平台網路服務**：
    *   **OpenStack Neutron**：OpenStack 的網路服務組件，廣泛使用 VXLAN 等 Overlay 技術。
        *   [https://docs.openstack.org/neutron/latest/](https://docs.openstack.org/neutron/latest/)
    *   **VMware NSX**：VMware 的網路虛擬化平台，大量運用 Overlay SDN 技術。
        *   [https://www.vmware.com/products/nsx.html](https://www.vmware.com/products/nsx.html)
*   **BGP EVPN 相關文獻**：深入了解分散式控制平面技術。
    *   [RFC 7432 - BGP MPLS-Based Ethernet VPN](https://tools.ietf.org/html/rfc7432)

透過這些資源，您可以更深入地研究軟件 Overlay SDN 的理論、實踐和最新發展。