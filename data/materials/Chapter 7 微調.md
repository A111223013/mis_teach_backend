# Chapter 7 微調 (Fine-tuning)

-----

### 7.1 核心概念與定義

#### 7.1.1 什麼是微調？

微調 (Fine-tuning) 是一種機器學習技術，特別是在深度學習領域中廣泛應用，用於將一個已經在大量通用資料上預訓練 (pre-trained) 的模型，進一步調整以適應特定下游任務 (downstream task) 或特定領域的資料。其核心思想是利用預訓練模型已經學到的豐富知識（如特徵提取能力、語言模式等），而不是從頭開始訓練一個全新的模型。

**核心觀念：**

*   **知識遷移 (Knowledge Transfer):** 預訓練模型在預訓練階段（通常是自監督學習，例如 BERT 的遮罩語言模型、圖片分類模型的 ImageNet 訓練）已經學習到了資料中豐富的通用模式和表示。微調的目標是將這些通用知識遷移到新的、通常資料量較小或領域更為特定的任務上。
*   **參數更新 (Parameter Updates):** 在微調階段，預訓練模型的全部或部分參數會根據新的任務資料和目標進行梯度下降更新。與從頭訓練不同，微調通常使用較小的學習率和較少的訓練步數，以避免破壞預訓練模型已經學到的通用知識。

#### 7.1.2 為何需要微調？

微調技術的出現主要解決了以下幾個挑戰：

1.  **資料稀缺性 (Data Scarcity):** 許多專業領域或特定任務的標註資料非常有限。從頭訓練一個大型深度學習模型需要大量的標註資料，這在許多情況下是不可行的。微調允許我們在小規模資料集上也能達到良好的性能。
2.  **計算資源限制 (Computational Constraints):** 訓練一個大型深度學習模型（如大型語言模型或大型圖像模型）需要巨大的計算資源和時間。微調則只需要較少的資源，因為模型已經具備了大部分基礎能力，只需要進行少量的調整。
3.  **加快開發週期 (Accelerated Development Cycle):** 藉由利用預訓練模型，我們可以快速地為新的任務建立高效能的模型，大幅縮短了模型開發和部署的時間。

#### 7.1.3 微調的應用場景

微調廣泛應用於各種深度學習領域：

*   **自然語言處理 (NLP):**
    *   將預訓練的語言模型（如 BERT, GPT, T5）微調用於情感分析、命名實體識別、問答系統、文字摘要等特定任務。
    *   將通用語言模型微調成特定領域的聊天機器人或翻譯模型。
*   **電腦視覺 (Computer Vision):**
    *   將預訓練的圖像分類模型（如 ResNet, Vision Transformer）微調用於醫學影像診斷、物體檢測、圖像分割等任務。
    *   將預訓練的檢測模型微調以識別特定種類的商品或缺陷。
*   **語音處理 (Speech Processing):**
    *   將預訓練的語音模型微調用於特定語言的語音辨識、語音合成或說話者識別。

-----

### 7.2 典型例子與轉換/推導

#### 7.2.1 預訓練 (Pre-training) 與微調 (Fine-tuning) 的流程

**1. 預訓練階段：**

*   **目標：** 讓模型學習資料的通用、抽象表示和模式。
*   **資料：** 大規模、通用且通常是未標註的資料集（例如，百萬張圖片、數十億文字語料）。
*   **任務：** 通常是自監督任務，如：
    *   **NLP:** 遮罩語言模型 (Masked Language Modeling, MLM)、下一句預測 (Next Sentence Prediction, NSP)、因果語言模型 (Causal Language Modeling, CLM)。
    *   **CV:** 圖像分類 (ImageNet)、對比學習 (Contrastive Learning)。
*   **結果：** 獲得一個具有強大通用能力和豐富知識的預訓練模型參數 $\theta_P$。

**2. 微調階段：**

*   **目標：** 調整預訓練模型 $\theta_P$ 以適應特定的下游任務 $T_{downstream}$。
*   **資料：** 規模較小、特定於任務且已標註的資料集 $D_{task}$。
*   **任務：** 實際的應用任務，如情感分類、物體檢測、語音辨識等。
*   **流程：**
    1.  載入預訓練模型 $\theta_P$。
    2.  根據下游任務的輸出層需求，可能需要修改或替換模型的頂部層 (e.g., 將通用分類層替換為特定類別數量的分類層)。
    3.  使用任務 $T_{downstream}$ 的標註資料 $D_{task}$ 訓練模型。在訓練過程中，模型的所有或部分參數會被更新。
    4.  通常使用較小的學習率和較少的訓練週期 (epochs)，以避免過度擬合和「災難性遺忘」(catastrophic forgetting)。
*   **結果：** 獲得一個針對特定任務 $T_{downstream}$ 優化的模型參數 $\theta_F$。

#### 7.2.2 微調策略

微調策略有多種，主要取決於可用的計算資源、資料量以及任務的相似性。

1.  **全量微調 (Full Fine-tuning):**
    *   更新預訓練模型的所有層的參數。
    *   適用於下游任務與預訓練任務差異較大，或下游資料集足夠大的情況。
    *   計算成本和記憶體開銷較大。

2.  **凍結部分層 (Feature Extraction / Freezing Layers):**
    *   凍結 (Freeze) 預訓練模型的部分底層（如特徵提取層），只更新頂部層或新添加的層。
    *   特別適用於下游資料集非常小，或下游任務與預訓練任務非常相似的情況。
    *   可以避免過度擬合，同時減少計算量。
    *   **推導：**
        假設預訓練模型由 $L$ 層組成，參數為 $\{\mathbf{W}_1, \dots, \mathbf{W}_L\}$。
        在微調時，我們凍結前 $k$ 層，即 $\frac{\partial \mathcal{L}}{\partial \mathbf{W}_i} = 0$ for $i=1, \dots, k$。
        只有後 $L-k$ 層和可能新增的輸出層的參數會被更新。
        梯度下降更新規則變為：
        $$ \mathbf{W}_i^{new} = \mathbf{W}_i^{old} - \eta \frac{\partial \mathcal{L}}{\partial \mathbf{W}_i} \quad \text{for } i=k+1, \dots, L \text{ 和新層} $$
        其中 $\eta$ 是學習率，$\mathcal{L}$ 是任務損失函數。

3.  **微調不同層次 (Layer-wise Fine-tuning / Discriminative Fine-tuning):**
    *   對模型的不同層次設定不同的學習率。通常，底層的學習率較小，頂層的學習率較大。
    *   基於假設：底層學習到的通用特徵更穩定，不應大幅改變；頂層學習到的任務特定特徵需要更多調整。
    *   **例子：** 使用 NLP 模型時，對嵌入層 (embedding layer) 使用最小學習率，對 Transformer 塊的底層使用較小學習率，對頂層和分類頭使用較大學習率。

-----

### 7.3 與相鄰概念的關聯

微調是遷移學習 (Transfer Learning) 的一種具體實現方式，並與其他相關概念有著緊密的聯繫。

#### 7.3.1 遷移學習 (Transfer Learning)

*   **關聯：** 微調是遷移學習最常見且最有效的策略之一。遷移學習的廣義定義是將從一個任務學到的知識應用到另一個不同但相關的任務上。預訓練模型的建立和其知識被「遷移」到下游任務的過程，正是遷移學習的核心。
*   **區別：** 遷移學習是一個更廣泛的概念，除了微調，還包括特徵提取 (Feature Extraction)（即只用預訓練模型作為特徵提取器，不更新其參數，只訓練新的分類器）、領域適應 (Domain Adaptation) 等。微調特指通過梯度下降更新預訓練模型參數的過程。

#### 7.3.2 從頭訓練 (Training from Scratch)

*   **關聯：** 微調是「從頭訓練」的反義詞或替代方案。
*   **區別：**
    *   **從頭訓練：** 模型參數從隨機值開始初始化，完全依賴目標任務的資料進行學習。需要大量標註資料和計算資源，適用於有足夠資源且任務與現有預訓練模型差異極大的情況。
    *   **微調：** 模型參數從預訓練模型的參數開始初始化，利用了預訓練階段學習到的通用知識。在資料有限和計算資源受限的情況下，通常能取得更好的性能和更快的收斂速度。

#### 7.3.3 領域適應 (Domain Adaptation)

*   **關聯：** 領域適應旨在解決訓練資料 (源域) 和測試資料 (目標域) 分佈不一致的問題。微調在某種程度上也可以視為一種領域適應，因為它將模型從通用領域適應到特定任務領域。
*   **區別：** 領域適應通常更強調解決源域和目標域之間的統計分佈差異，可能涉及更複雜的技術，如域不變特徵學習、對抗性訓練等。微調是其中一種直接調整模型參數以適應新域的方法。

#### 7.3.4 Few-shot Learning (少樣本學習)

*   **關聯：** 微調和 Few-shot Learning 都旨在解決資料稀缺問題。
*   **區別：**
    *   **微調：** 仍然需要一定量的（即使是少量）帶標籤的目標任務資料來更新模型參數。
    *   **Few-shot Learning：** 旨在讓模型在幾乎不更新自身參數的情況下，僅憑極少數（如 1-5 個）的範例就能學會新概念或任務。這通常通過元學習 (Meta-learning) 或強大的預訓練模型（如大型語言模型透過提示學習）實現，模型已經學會了「如何學習」或具有很強的泛化能力。微調是 Few-shot Learning 的一個常見後處理步驟，當 Few-shot Learning 效果不佳時，可以嘗試在少量樣本上進行微調以進一步提升性能。

-----

### 7.4 進階內容：參數高效微調 (Parameter-Efficient Fine-Tuning, PEFT)

隨著模型規模的爆炸式成長，全量微調大型模型（如 GPT-3, LLaMA）變得極其昂貴，甚至不可行。參數高效微調 (PEFT) 應運而生，它旨在僅微調少量參數，同時保持與全量微調相近的性能。

#### 7.4.1 PEFT 的動機與優勢

*   **動機：**
    *   大型模型參數數量龐大，全量微調需要巨大的記憶體和計算資源。
    *   每個新任務都需要儲存一份完整的微調模型，儲存成本高昂。
    *   避免災難性遺忘的風險。
*   **優勢：**
    *   **記憶體效率 (Memory Efficiency):** 只需更新和儲存少量參數，大幅降低記憶體需求。
    *   **計算效率 (Computational Efficiency):** 減少需要參與梯度計算的參數數量，加速訓練。
    *   **儲存效率 (Storage Efficiency):** 對於每個任務，只需儲存原始模型和少量增量參數。
    *   **避免災難性遺忘 (Mitigate Catastrophic Forgetting):** 由於大部分預訓練參數被凍結，核心知識得以保留。

#### 7.4.2 典型的 PEFT 方法

PEFT 方法種類繁多，以下介紹幾種主流技術：

1.  **LoRA (Low-Rank Adaptation):**
    *   **核心思想：** 凍結預訓練模型權重，並在 Transformer 架構的自注意力層和前饋網路層中注入小的、可訓練的低秩適應矩陣。
    *   **推導：**
        對於預訓練模型中的任意權重矩陣 $\mathbf{W}_0 \in \mathbb{R}^{d \times k}$，LoRA 引入了兩個較小的矩陣 $\mathbf{A} \in \mathbb{R}^{d \times r}$ 和 $\mathbf{B} \in \mathbb{R}^{r \times k}$，其中 $r$ 是遠小於 $d, k$ 的秩 (rank)。
        更新後的權重矩陣表示為 $\mathbf{W}_0 + \Delta \mathbf{W}$，其中 $\Delta \mathbf{W} = \mathbf{BA}$。
        訓練時，只有 $\mathbf{A}$ 和 $\mathbf{B}$ 的參數被更新，而 $\mathbf{W}_0$ 保持凍結。
        在推理時，可以直接計算 $\mathbf{W}_0 + \mathbf{BA}$ 作為新的權重矩陣，或者動態地將 $\mathbf{BA}$ 的輸出加到 $\mathbf{W}_0$ 的輸出上。
        需要訓練的參數數量從 $d \times k$ 大幅減少到 $d \times r + r \times k$。
    *   **優點：** 訓練參數極少，性能接近全量微調，推理時可合併權重。

2.  **Prompt Tuning (提示詞微調):**
    *   **核心思想：** 凍結整個預訓練模型，只訓練一系列「軟提示」(soft prompts) token，將其加到輸入序列的開頭或中間，引導模型完成特定任務。
    *   **推導：**
        輸入序列 $X = [x_1, \dots, x_n]$。
        軟提示 $P = [p_1, \dots, p_m]$，其中 $p_i$ 是可訓練的嵌入向量。
        模型輸入變為 $[P, X]$ 或 $[X_{pre}, P, X_{post}]$。
        在訓練過程中，只有 $P$ 的嵌入向量被更新，預訓練模型的其他參數保持凍結。
    *   **優點：** 訓練參數最少（僅數千個），特別適用於超大型模型。

3.  **Adapter Tuning (適配器微調):**
    *   **核心思想：** 在預訓練模型的每一層（例如 Transformer 塊的每個子層）之間插入小型、專門設計的適配器模組 (Adapter Module)。這些適配器包含少量可訓練參數，而預訓練模型的主體保持凍結。
    *   **架構：** 一個典型的 Adapter 模組由一個降維層、一個非線性激活函數和一個升維層組成，形成一個瓶頸結構。
    *   **推導：**
        對於一個 Transformer 子層的輸出 $\mathbf{h}$，經過 Adapter 後的輸出為 $\mathbf{h} + Adapter(\mathbf{h})$。
        其中 $Adapter(\mathbf{h}) = \mathbf{W}_{up}(\text{ReLU}(\mathbf{W}_{down}(\mathbf{h})))$。
        只有 $\mathbf{W}_{down}$ 和 $\mathbf{W}_{up}$ 的參數被訓練。
    *   **優點：** 比 Prompt Tuning 靈活，比 LoRA 參數略多但有時表現更好，可堆疊多個 Adapter 處理多任務。

4.  **QLoRA (Quantized LoRA):**
    *   **核心思想：** 在 LoRA 的基礎上，進一步將預訓練模型量化到 4-bit 精度，以大幅減少記憶體佔用。
    *   **優點：** 允許在消費級 GPU 上微調數百億甚至上千億參數的模型，是目前微調大型語言模型的熱門方法。

-----

### 7.5 常見錯誤與澄清

#### 7.5.1 過度擬合 (Overfitting)

*   **錯誤：** 使用預訓練模型在小型資料集上進行全量微調，且學習率過大或訓練步數過多。這會導致模型過度擬合訓練資料，在未見過的新資料上表現不佳。
*   **澄清：** 預訓練模型已經具備強大的泛化能力，過度微調會讓其失去通用性。
    *   **解決方案：**
        1.  **使用較小的學習率：** 通常比從頭訓練時的學習率小 1 到 2 個數量級 (e.g., $10^{-5}$)。
        2.  **減少訓練週期 (Epochs):** 幾十個 epoch 通常已足夠，甚至只需幾個 epoch。
        3.  **凍結底層：** 如果資料集非常小，可以凍結大部分預訓練層，只訓練頂部層或 PEFT 模組。
        4.  **早停 (Early Stopping):** 監控驗證集性能，當性能不再提升時停止訓練。
        5.  **正規化 (Regularization):** 雖然微調中通常較少直接應用 Dropout 等強正規化，但可以作為備選項。

#### 7.5.2 災難性遺忘 (Catastrophic Forgetting)

*   **錯誤：** 在微調過程中，模型完全「忘記」了預訓練階段學到的通用知識，導致在通用任務上性能急劇下降。這通常發生在微調資料與預訓練資料差異極大，或訓練過於激進時。
*   **澄清：** 微調的目標是適應新任務，而非完全抹除舊知識。
*   **解決方案：**
    1.  **凍結部分層：** 凍結底層是有效避免災難性遺忘的方法。
    2.  **使用 PEFT 方法：** PEFT 方法由於只調整少量參數，能夠更好地保留預訓練知識。
    3.  **較小的學習率和少量訓練：** 溫和地調整參數。
    4.  **排練 (Rehearsal) 或知識蒸餾 (Knowledge Distillation):** 在微調時加入少量預訓練資料或使用知識蒸餾讓模型在微調的同時也考慮通用知識。

#### 7.5.3 預訓練模型選擇不當

*   **錯誤：** 選擇與下游任務或資料領域完全不相關的預訓練模型。例如，使用在英文文本上預訓練的模型來處理日文影像分類任務。
*   **澄清：** 預訓練模型的有效性高度依賴於其預訓練資料與目標任務的相關性。
*   **解決方案：**
    1.  **語言匹配：** NLP 任務務必選擇在目標語言上預訓練的模型。
    2.  **領域匹配：** 如果有特定領域的預訓練模型（例如醫學影像模型、金融文本模型），優先選擇。
    3.  **任務匹配：** 儘可能選擇在相似任務上預訓練的模型（例如，圖片分類模型用於圖像分類，檢測模型用於物體檢測）。

#### 7.5.4 評估指標選擇不當

*   **錯誤：** 在微調後僅使用訓練集準確度作為評估指標，或使用不適合任務的指標。
*   **澄清：** 應始終在獨立的驗證集和測試集上評估模型性能，並選擇最能反映任務目標的指標。
*   **解決方案：**
    1.  **標準指標：**
        *   **分類任務：** 準確度 (Accuracy)、精確度 (Precision)、召回率 (Recall)、F1 分數 (F1-score)、混淆矩陣 (Confusion Matrix)。
        *   **回歸任務：** 均方誤差 (Mean Squared Error, MSE)、平均絕對誤差 (Mean Absolute Error, MAE)。
        *   **自然語言生成：** BLEU, ROUGE, METEOR。
        *   **物體檢測：** 平均精確度 (mAP)。
    2.  **跨驗證集和測試集：** 確保模型在未見過的資料上也能保持良好性能。

-----

### 7.6 小練習（附詳解）

#### 小練習 1: 微調策略選擇

你是一家小型創業公司的機器學習工程師，需要為一個新的產品開發情感分析模型。你們現有的數據集非常小，只有 1000 條帶情感標籤的評論資料。你決定利用一個在大量英文文本上預訓練的 BERT 模型。

請說明你會選擇哪種微調策略，以及為什麼？並列出你實施這個策略的簡要步驟。

**詳解：**

**選擇策略：**
考慮到資料集非常小（1000 條），全量微調預訓練的 BERT 模型很可能會導致嚴重的過度擬合和災難性遺忘。因此，最合適的策略是**凍結 BERT 模型的大部分底層參數，只微調頂部的新增分類器層**，或者考慮使用 **PEFT 方法（如 LoRA 或 Prompt Tuning）**。

**原因：**

1.  **資料量小：** 凍結底層參數可以有效減少可訓練參數的數量，降低過度擬合的風險。BERT 預訓練模型已經學習了豐富的通用語言知識，這些知識在底層特徵中表現穩定，不需要大幅度改變。
2.  **計算資源：** 凍結部分層或使用 PEFT 可以大幅減少訓練所需的計算資源和時間。
3.  **知識保留：** 保留預訓練模型的通用知識，只調整與特定任務相關的頂部層，能更好地利用遷移學習的優勢。

**實施步驟（以凍結底層並新增分類器為例）：**

1.  **載入預訓練模型：**
    *   載入一個預訓練的 BERT 模型（例如 `bert-base-uncased`）及其對應的 tokenizer。
    *   ```python
        from transformers import BertModel, BertTokenizer
        model_name = 'bert-base-uncased'
        tokenizer = BertTokenizer.from_pretrained(model_name)
        bert_model = BertModel.from_pretrained(model_name)
        ```
2.  **凍結模型層：**
    *   迭代 BERT 模型的所有參數，將其 `requires_grad` 屬性設置為 `False`，凍結大部分預訓練層。
    *   你也可以選擇性地只凍結前面 N 層，而讓後面的幾層（例如 Transformer 的最後 2-4 層）和池化層可訓練。對於極小的數據集，完全凍結並只訓練新加的分類頭是更安全的選擇。
    *   ```python
        for param in bert_model.parameters():
            param.requires_grad = False
        # 或者，如果想解凍最後幾層：
        # for param in bert_model.encoder.layer[-2:].parameters(): # 解凍最後兩層 Transformer
        #     param.requires_grad = True
        # for param in bert_model.pooler.parameters(): # 解凍池化層
        #     param.requires_grad = True
        ```
3.  **添加任務特定的輸出層：**
    *   在 BERT 模型之上添加一個或多個全連接層 (Dense layers) 作為情感分類器。
    *   這個新的分類器層的參數將會被初始化並在微調過程中更新。
    *   ```python
        import torch.nn as nn
        class SentimentClassifier(nn.Module):
            def __init__(self, bert_model, num_labels):
                super(SentimentClassifier, self).__init__()
                self.bert = bert_model
                # BERT 的池化輸出通常是 768 維
                self.dropout = nn.Dropout(0.1)
                self.classifier = nn.Linear(bert_model.config.hidden_size, num_labels)

            def forward(self, input_ids, attention_mask):
                outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
                pooled_output = outputs.pooler_output # 使用 [CLS] token 的表示
                pooled_output = self.dropout(pooled_output)
                logits = self.classifier(pooled_output)
                return logits

        num_labels = 2 # 假設是正面/負面兩種情感
        model = SentimentClassifier(bert_model, num_labels)
        ```
4.  **準備資料：**
    *   使用 tokenizer 將 1000 條評論資料轉換為模型可接受的輸入格式（`input_ids`, `attention_mask`）。
    *   將資料分為訓練集、驗證集。
5.  **訓練模型：**
    *   使用訓練集對模型進行訓練。只訓練新增分類器層和任何解凍的 BERT 層。
    *   使用較小的學習率（例如 $10^{-4}$ 或 $10^{-5}$），並密切監控驗證集上的性能，以進行早停。
    *   ```python
        # 訓練循環 (簡化示意)
        optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4) # 學習率可以更高一些，因為大多是新層
        criterion = nn.CrossEntropyLoss()

        for epoch in range(num_epochs):
            # 訓練步
            for batch in train_dataloader:
                input_ids, attention_mask, labels = batch
                optimizer.zero_grad()
                logits = model(input_ids, attention_mask)
                loss = criterion(logits, labels)
                loss.backward()
                optimizer.step()
            # 驗證步 (用於早停和性能監控)
        ```

#### 小練習 2: PEFT 的效益分析

假設你正在嘗試微調一個擁有 70 億參數的 LLaMA 語言模型，用於一個新的對話生成任務。你有一個包含數萬條對話記錄的數據集。

請解釋為什麼在這種情況下，PEFT 方法（如 LoRA）會比全量微調更有優勢。並量化 LoRA 如何減少參數數量。

**詳解：**

**PEFT（如 LoRA）比全量微調更有優勢的原因：**

1.  **記憶體限制：** 70 億參數的模型在全精度 (FP32) 下需要約 $70 \times 10^8 \times 4 \text{ bytes} \approx 28 \text{ GB}$ 的記憶體來儲存模型參數。如果還要加上優化器狀態（通常是模型參數的 2 倍或更多），那麼訓練一個這樣的模型至少需要 $28 \text{ GB} \times 3 \approx 84 \text{ GB}$ 或更多的 VRAM。這對於大多數消費級 GPU 甚至一些專業級 GPU 都是一個巨大的挑戰。LoRA 透過凍結主模型參數並只訓練少量低秩適應器，大幅降低了訓練所需的記憶體。
2.  **計算成本：** 全量微調需要計算所有 70 億參數的梯度並更新它們，這是一個計算密集型的過程。LoRA 只需要計算和更新少量適配器參數的梯度，顯著減少了浮點運算次數和訓練時間。
3.  **儲存成本：** 如果每個新任務都需要一個完整的 70 億參數模型的副本，那麼儲存這些模型將會非常昂貴。LoRA 允許我們儲存原始的 LLaMA 模型一次，然後為每個任務只儲存一個小的 LoRA 權重集（通常只有幾十 MB），極大地節省了儲存空間。
4.  **避免災難性遺忘：** 由於 LoRA 保持了 LLaMA 大部分預訓練參數的凍結，模型更不容易「忘記」其在預訓練階段學到的通用語言知識和能力，這有助於保持其泛化能力。

**LoRA 如何量化減少參數數量：**

假設 LLaMA 模型中，我們選擇在 Transformer 的自注意力層中的查詢 (Query, $\mathbf{W}_Q$)、鍵 (Key, $\mathbf{W}_K$)、值 (Value, $\mathbf{W}_V$) 和輸出投影 (Output Projection, $\mathbf{W}_O$) 矩陣上應用 LoRA。

考慮一個典型的 Transformer 模型，其中每個權重矩陣的維度可能是 $d_{model} \times d_{model}$ (例如，對於 LLaMA 7B， $d_{model}$ 可能約為 4096)。

1.  **全量微調的參數數量：**
    如果我們考慮在四個投影矩陣（Q, K, V, O）上進行全量微調，每個矩陣的參數數量約為 $d_{model} \times d_{model}$。
    總參數數 $\approx 4 \times d_{model} \times d_{model}$。
    若 $d_{model} = 4096$，則每個投影矩陣有 $4096 \times 4096 \approx 1.68 \times 10^7$ 個參數。
    四個投影矩陣就有 $4 \times 1.68 \times 10^7 \approx 6.7 \times 10^7$ 個參數。
    LLaMA 7B 模型的總參數是 70 億，這只是其中一部分。

2.  **LoRA 的參數數量：**
    對於一個權重矩陣 $\mathbf{W}_0 \in \mathbb{R}^{d \times k}$，LoRA 引入兩個低秩矩陣 $\mathbf{A} \in \mathbb{R}^{d \times r}$ 和 $\mathbf{B} \in \mathbb{R}^{r \times k}$。
    可訓練參數為 $d \times r + r \times k$。
    假設我們選擇秩 $r = 8$（LoRA 常用的值）。
    對於每個 $d_{model} \times d_{model}$ 的權重矩陣：
    可訓練參數 $\approx d_{model} \times r + r \times d_{model} = 2 \times d_{model} \times r$。
    若 $d_{model} = 4096, r = 8$：
    每個矩陣的可訓練參數 $\approx 2 \times 4096 \times 8 = 65536$。
    在四個投影矩陣上應用 LoRA：
    總 LoRA 參數 $\approx 4 \times 65536 = 262144$。

3.  **對比與量化：**
    *   全量微調這四個投影矩陣：約 $6.7 \times 10^7$ 個參數。
    *   LoRA 微調這四個投影矩陣：約 $2.6 \times 10^5$ 個參數。

    參數減少的比例是 $2.6 \times 10^5 / (6.7 \times 10^7) \approx 0.0039$，即 LoRA 只需要訓練約 **0.39%** 的參數。
    如果我們將 LoRA 應用於模型中更多的權重矩陣，總 LoRA 參數可能會增加，但相對於整個模型的 70 億參數而言，總訓練參數佔比仍然會非常小（通常在 0.1% 到 1% 之間）。

因此，LoRA 通過將每個大權重矩陣的更新分解為兩個小矩陣的乘積，極大地減少了需要訓練和儲存的參數數量，使得在有限資源下微調大型語言模型成為可能。

-----

### 7.7 延伸閱讀/參考

1.  **Understanding Transfer Learning and Fine-Tuning:**
    *   Sebastian Ruder, "Neural Network Transfer Learning - A Comprehensive Guide": [https://ruder.io/transfer-learning/](https://ruder.io/transfer-learning/)
    *   Jeremy Howard and Sylvain Gugger, "Deep Learning for Coders with fastai & PyTorch: AI Applications Without a PhD" (Chapter 1, Transfer Learning section).

2.  **Original BERT Paper (for Pre-training and Fine-tuning context in NLP):**
    *   Jacob Devlin, Ming-Wei Chang, Kenton Lee, Kristina Toutanova, "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding." (2018). arXiv:1810.04805.

3.  **LoRA Paper (for Parameter-Efficient Fine-Tuning):**
    *   Edward J. Hu, Yelong Shen, Phillip Wallis, Zeyuan Allen-Zhu, Yuanzhi Li, Lu Wang, Caiming Xiong, Tom B. Brown, "LoRA: Low-Rank Adaptation of Large Language Models." (2021). arXiv:2106.09685.

4.  **Prompt Tuning Paper:**
    *   Lester Kurtz, Josh Sanh, Benjamin Schmid, "The Power of Scale for Parameter-Efficient Prompt Tuning." (2021). arXiv:2104.08691.

5.  **Adapter Tuning Paper:**
    *   Neil Houlsby, Andrei Giurgiu, Stanislaw Padlewski, Quentin de Laroussilhe, Marcin Ritter, Jonas W. Kuetten, Julian Simon, Marcin Taraszkiewicz, Aaron Buchholz, Andrea Ruoss, Klaus Greff, "Parameter-Efficient Transfer Learning for NLP." (2019). arXiv:1902.00751.

6.  **QLoRA Paper:**
    *   Tim Dettmers, Artidoro Pagnoni, Ari Garcez, Luke Zettlemoyer, "QLoRA: Efficient Finetuning of Quantized LLMs on Consumer GPUs." (2023). arXiv:2305.14314.

7.  **Hugging Face PEFT Library Documentation:**
    *   [https://huggingface.co/docs/peft/en/index](https://huggingface.co/docs/peft/en/index) (實作 PEFT 方法的優秀資源)