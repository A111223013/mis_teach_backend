#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG處理器 - 核心PDF處理和向量資料庫建立模組
支援批量處理PDF教材，自動建立知識點向量資料庫
"""

import os
import re
import json
import uuid
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

# PDF處理相關
from unstructured.partition.pdf import partition_pdf
from unstructured.documents.elements import Title, NarrativeText, ListItem, Table, Text

# 向量化和嵌入
from sentence_transformers import SentenceTransformer
import numpy as np
import torch

# 向量資料庫
import chromadb
from chromadb.config import Settings

# 進度條和工具
from tqdm import tqdm
# 智能導入config模組
def _import_config():
    """智能導入config模組，處理不同的執行環境"""
    import sys
    import os

    # 獲取當前文件所在目錄
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # 方法1: 嘗試從當前目錄直接導入
    try:
        sys.path.insert(0, current_dir)
        import config as config
        # 驗證是否是正確的config（檢查關鍵屬性）
        if hasattr(config, 'EMBEDDING_MODEL') and hasattr(config, 'LOGGING_CONFIG'):
            return config
    except ImportError:
        pass

    # 方法2: 嘗試相對導入
    try:
        from . import config
        if hasattr(config, 'EMBEDDING_MODEL') and hasattr(config, 'LOGGING_CONFIG'):
            return config
    except ImportError:
        pass

    # 方法3: 嘗試絕對導入
    try:
        import rag_system.config as config
        if hasattr(config, 'EMBEDDING_MODEL') and hasattr(config, 'LOGGING_CONFIG'):
            return config
    except ImportError:
        pass

    # 如果都失敗，拋出詳細錯誤
    raise ImportError(
        "無法導入正確的config模組。請確認:\n"
        "1. rag_system/config.py 文件存在\n"
        "2. config.py 包含 EMBEDDING_MODEL 和 LOGGING_CONFIG\n"
        "3. 當前工作目錄正確"
    )

# 導入config
config = _import_config()

# 設定日誌
try:
    logging.basicConfig(
        level=getattr(logging, config.LOGGING_CONFIG['level']),
        format=config.LOGGING_CONFIG['format'],
        handlers=[
            logging.FileHandler(config.LOGGING_CONFIG['file'], encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
except (AttributeError, KeyError) as e:
    # 如果配置有問題，使用默認配置
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
logger = logging.getLogger(__name__)

class RAGProcessor:
    """
    RAG處理器 - 負責PDF處理和向量資料庫建立

    主要功能:
    1. 批量處理PDF教材檔案
    2. 提取和結構化知識點
    3. 建立向量資料庫
    4. 支援中英文混合內容
    """

    def __init__(self,
                 embedding_model: str = None,
                 use_chromadb: bool = True,
                 verbose: bool = None,
                 use_gpu: bool = None):
        """
        初始化RAG處理器

        Args:
            embedding_model: 向量化模型名稱，預設使用config中的設定
            use_chromadb: 是否使用ChromaDB，預設True
            verbose: 是否顯示詳細資訊，預設使用config中的設定
            use_gpu: 是否使用GPU，預設使用config中的設定
        """
        # 載入配置
        self.embedding_model_name = embedding_model or config.EMBEDDING_MODEL
        self.use_chromadb = use_chromadb
        self.verbose = verbose if verbose is not None else config.VERBOSE_MODE
        self.use_gpu = use_gpu if use_gpu is not None else config.GPU_CONFIG['enable_gpu']

        # 檢查GPU可用性
        self.gpu_info = config.check_gpu_availability()
        self.device = self._setup_device()

        # 初始化向量化模型 (GPU優化)
        logger.info(f"🔄 正在載入向量化模型: {self.embedding_model_name}")
        logger.info(f"🖥️ 使用設備: {self.device}")
        try:
            # 使用GPU優化配置載入模型
            self.embedding_model = SentenceTransformer(
                self.embedding_model_name,
                device=self.device
            )

            # 設定GPU優化參數
            if self.device == 'cuda':
                # 設定模型為半精度模式 (FP16) 以加速和節省記憶體
                if config.EMBEDDING_CONFIG.get('precision') == 'float16':
                    self.embedding_model.half()
                    logger.info("🚀 啟用FP16半精度模式，提升GPU處理速度")

                # 設定最大序列長度
                max_seq_length = config.EMBEDDING_CONFIG.get('max_seq_length', 512)
                self.embedding_model.max_seq_length = max_seq_length
                logger.info(f"📏 設定最大序列長度: {max_seq_length}")

            logger.info("✅ 向量化模型載入成功 (GPU優化)")
        except Exception as e:
            logger.error(f"❌ 向量化模型載入失敗: {e}")
            raise

        # 初始化資料存儲
        self.structured_data = []      # 結構化內容數據
        self.knowledge_points = []     # 知識點數據

        # 初始化向量資料庫
        if self.use_chromadb:
            self._init_chromadb()
        else:
            # 如果沒有FAISS-GPU，仍然可以使用CPU FAISS
            self.faiss_index = None
            self.faiss_metadata = []
            if self.use_gpu:
                logger.info("💡 建議安裝 faiss-gpu 以獲得更好的GPU加速效果")

        logger.info("🚀 RAG處理器初始化完成")

    def _setup_device(self):
        """
        設定計算設備 (GPU/CPU)

        Returns:
            str: 設備名稱
        """
        if self.use_gpu and self.gpu_info['available']:
            device = config.GPU_CONFIG['device']
            logger.info(f"🚀 使用GPU: {self.gpu_info['device_name']}")
            logger.info(f"💾 GPU記憶體: {self.gpu_info['memory_total']}GB 總計, {self.gpu_info['memory_free']}GB 可用")

            # 設定GPU記憶體使用比例
            if device == 'cuda':
                try:
                    import torch
                    torch.cuda.set_per_process_memory_fraction(config.GPU_CONFIG['gpu_memory_fraction'])
                    logger.info(f"🔧 GPU記憶體使用比例設定為: {config.GPU_CONFIG['gpu_memory_fraction']}")
                except Exception as e:
                    logger.warning(f"⚠️ 設定GPU記憶體比例失敗: {e}")

            return device
        else:
            if self.use_gpu:
                logger.warning("⚠️ GPU不可用，回退到CPU模式")
            else:
                logger.info("🖥️ 使用CPU模式")
            return 'cpu'

    def _init_chromadb(self):
        """初始化ChromaDB"""
        try:
            self.chroma_client = chromadb.PersistentClient(path=config.CHROMA_DB_PATH)
            self.collection = None
            logger.info(f"✅ ChromaDB初始化成功，路徑: {config.CHROMA_DB_PATH}")

            # 嘗試載入現有的collection
            try:
                self.collection = self.chroma_client.get_collection(config.COLLECTION_NAME)
                count = self.collection.count()
                logger.info(f"✅ 成功載入現有向量資料庫，包含 {count} 個知識點")
            except Exception:
                logger.info("💡 未找到現有向量資料庫，需要先建立知識庫")

        except Exception as e:
            logger.error(f"❌ ChromaDB初始化失敗: {e}")
            raise

    def process_multiple_pdfs(self,
                            pdf_paths: List[str],
                            output_json: str = None) -> bool:
        """
        批量處理多個PDF檔案

        Args:
            pdf_paths: PDF檔案路徑列表
            output_json: 輸出JSON檔案路徑，預設使用config中的設定

        Returns:
            bool: 處理是否成功
        """
        if not pdf_paths:
            logger.warning("⚠️ 沒有提供PDF檔案路徑")
            return False

        # 設定輸出路徑
        if output_json is None:
            output_json = config.OUTPUT_DIR / config.OUTPUT_FILES['structured_content']

        logger.info(f"📚 開始批量處理 {len(pdf_paths)} 個PDF檔案")

        # 清空之前的數據
        self.structured_data = []

        # 處理每個PDF檔案
        successful_files = 0
        failed_files = []

        for pdf_path in tqdm(pdf_paths, desc="處理PDF檔案", disable=not self.verbose):
            try:
                if self._process_single_pdf(pdf_path):
                    successful_files += 1
                    logger.info(f"✅ 成功處理: {os.path.basename(pdf_path)}")
                else:
                    failed_files.append(pdf_path)
                    logger.warning(f"⚠️ 處理失敗: {os.path.basename(pdf_path)}")
            except Exception as e:
                failed_files.append(pdf_path)
                logger.error(f"❌ 處理 {os.path.basename(pdf_path)} 時發生錯誤: {e}")

        # 保存結構化數據
        if self.structured_data:
            self._save_structured_data(output_json)
            logger.info(f"📊 批量處理完成: 成功 {successful_files} 個，失敗 {len(failed_files)} 個")

            if failed_files:
                logger.warning(f"❌ 失敗的檔案: {[os.path.basename(f) for f in failed_files]}")

            return successful_files > 0
        else:
            logger.error("❌ 沒有成功處理任何PDF檔案")
            return False

    def _process_single_pdf(self, pdf_path: str) -> bool:
        """
        處理單個PDF檔案

        Args:
            pdf_path: PDF檔案路徑

        Returns:
            bool: 處理是否成功
        """
        if not os.path.exists(pdf_path):
            logger.error(f"❌ 檔案不存在: {pdf_path}")
            return False

        logger.info(f"📖 正在處理: {os.path.basename(pdf_path)}")

        try:
            # 使用unstructured解析PDF
            elements = partition_pdf(
                filename=pdf_path,
                strategy=config.PDF_PROCESSING['strategy'],
                infer_table_structure=config.PDF_PROCESSING['infer_table_structure'],
                chunking_strategy=config.PDF_PROCESSING['chunking_strategy'],
                max_characters=config.PDF_PROCESSING['max_characters'],
                new_after_n_chars=config.PDF_PROCESSING['new_after_n_chars'],
                languages=config.PDF_PROCESSING['languages']
            )

            # 初始化章節追蹤變數
            current_chapter = "前言"
            current_section = "無小節"
            current_subsection = "無副標題"

            # 處理每個元素
            processed_count = 0
            for element in tqdm(elements, desc="解析內容元素", leave=False, disable=not self.verbose):
                content = str(element).strip()

                # 過濾太短的內容
                if not content or len(content) < config.PDF_PROCESSING['min_content_length']:
                    continue

                # 獲取元數據
                page_num = getattr(element.metadata, 'page_number', 0) if hasattr(element, 'metadata') else 0
                source_file = os.path.basename(pdf_path)
                element_type = type(element).__name__

                # 章節識別和更新
                if isinstance(element, Title):
                    chapter_info = self._identify_chapter_structure(content)
                    if chapter_info['type'] == 'chapter':
                        current_chapter = content
                        current_section = "無小節"
                        current_subsection = "無副標題"
                        if self.verbose:
                            logger.info(f"  📚 發現章節: {current_chapter}")
                    elif chapter_info['type'] == 'section':
                        current_section = content
                        current_subsection = "無副標題"
                        if self.verbose:
                            logger.info(f"    📝 發現小節: {current_section}")
                    elif chapter_info['type'] == 'subsection':
                        current_subsection = content
                        if self.verbose:
                            logger.info(f"      🔸 發現副標題: {current_subsection}")

                # 建立結構化數據項目
                structured_item = {
                    "id": str(uuid.uuid4()),
                    "content": content,
                    "metadata": {
                        "source_file": source_file,
                        "page_number": page_num,
                        "chapter": current_chapter,
                        "section": current_section,
                        "subsection": current_subsection,
                        "element_type": element_type,
                        "content_length": len(content),
                        "language": self._detect_language(content)
                    }
                }

                self.structured_data.append(structured_item)
                processed_count += 1

            logger.info(f"✅ 成功處理 {processed_count} 個內容元素")
            return processed_count > 0

        except Exception as e:
            logger.error(f"❌ 處理PDF時發生錯誤: {e}")
            return False

    def _identify_chapter_structure(self, content: str) -> Dict[str, str]:
        """
        識別章節結構

        Args:
            content: 內容文本

        Returns:
            Dict: 包含章節類型和資訊的字典
        """
        # 章節模式匹配
        patterns = {
            'chapter': [
                r'(?:Chapter|第|章)\s*(\d+)[:\s]*(.*)',
                r'Part\s+(\w+)[:\s]*(.*)',
                r'第[一二三四五六七八九十\d]+章[:\s]*(.*)'
            ],
            'section': [
                r'^(\d+\.\d+)\s+(.*)',
                r'^(\d+\.\d+\.\d+)\s+(.*)',
                r'§\s*(\d+\.\d+)\s+(.*)'
            ],
            'subsection': [
                r'^(\d+\.\d+\.\d+)\s+(.*)',
                r'^(\d+\.\d+\.\d+\.\d+)\s+(.*)'
            ]
        }

        for structure_type, pattern_list in patterns.items():
            for pattern in pattern_list:
                if re.match(pattern, content, re.IGNORECASE):
                    return {'type': structure_type, 'content': content}

        return {'type': 'content', 'content': content}

    def _detect_language(self, content: str) -> str:
        """
        檢測內容語言

        Args:
            content: 內容文本

        Returns:
            str: 語言代碼 ('zh', 'en', 'mixed')
        """
        # 簡單的語言檢測
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', content))
        english_chars = len(re.findall(r'[a-zA-Z]', content))
        total_chars = chinese_chars + english_chars

        if total_chars == 0:
            return 'unknown'

        chinese_ratio = chinese_chars / total_chars

        if chinese_ratio > 0.7:
            return 'zh'
        elif chinese_ratio < 0.3:
            return 'en'
        else:
            return 'mixed'

    def _save_structured_data(self, output_path: str):
        """
        保存結構化數據到JSON檔案

        Args:
            output_path: 輸出檔案路徑
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.structured_data, f, ensure_ascii=False, indent=2)
            logger.info(f"✅ 結構化數據已保存到: {output_path}")
            logger.info(f"📊 總共提取了 {len(self.structured_data)} 個內容塊")
        except Exception as e:
            logger.error(f"❌ 保存結構化數據失敗: {e}")

    def create_knowledge_points(self, min_content_length: int = None) -> bool:
        """
        從結構化數據創建知識點

        Args:
            min_content_length: 最小內容長度閾值

        Returns:
            bool: 創建是否成功
        """
        if not self.structured_data:
            logger.error("❌ 沒有結構化數據，請先處理PDF檔案")
            return False

        min_length = min_content_length or config.KNOWLEDGE_POINT_CONFIG['min_content_length']
        logger.info(f"🧠 正在創建知識點 (最小長度: {min_length})")

        self.knowledge_points = []

        for item in tqdm(self.structured_data, desc="處理知識點", disable=not self.verbose):
            content = item["content"]
            metadata = item["metadata"]

            # 過濾太短的內容
            if len(content) < min_length:
                continue

            # 創建知識點
            knowledge_point = {
                "id": item["id"],
                "title": self._generate_title(content, metadata),
                "content": content,
                "summary": self._generate_summary(content),
                "keywords": self._extract_keywords(content),
                "metadata": metadata
            }

            self.knowledge_points.append(knowledge_point)

        logger.info(f"✅ 創建了 {len(self.knowledge_points)} 個知識點")
        return len(self.knowledge_points) > 0

    def _generate_title(self, content: str, metadata: Dict) -> str:
        """
        生成知識點標題

        Args:
            content: 內容文本
            metadata: 元數據

        Returns:
            str: 生成的標題
        """
        max_length = config.KNOWLEDGE_POINT_CONFIG['max_title_length']

        # 如果是標題元素，直接使用
        if metadata.get("element_type") == "Title":
            return content[:max_length]

        # 否則從內容生成標題
        sentences = content.split('.')
        if sentences and len(sentences[0].strip()) > 10:
            return sentences[0].strip()[:max_length] + ("..." if len(sentences[0]) > max_length else "")

        # 備選方案：使用章節資訊
        chapter = metadata.get('chapter', '')
        section = metadata.get('section', '')
        if chapter != "前言" and section != "無小節":
            return f"{chapter} - {section}"[:max_length]

        return content[:max_length] + "..."

    def _generate_summary(self, content: str) -> str:
        """
        生成內容摘要

        Args:
            content: 內容文本

        Returns:
            str: 生成的摘要
        """
        max_length = config.KNOWLEDGE_POINT_CONFIG['max_summary_length']

        if len(content) <= max_length:
            return content

        # 簡單的摘要生成：取前幾句話
        sentences = content.split('.')
        summary = ""
        for sentence in sentences:
            sentence = sentence.strip()
            if len(summary + sentence) <= max_length - 3:  # 留空間給省略號
                summary += sentence + ". "
            else:
                break

        return summary.strip() + "..." if summary else content[:max_length] + "..."

    def _extract_keywords(self, content: str) -> List[str]:
        """
        提取關鍵詞

        Args:
            content: 內容文本

        Returns:
            List[str]: 關鍵詞列表
        """
        max_keywords = config.KNOWLEDGE_POINT_CONFIG['max_keywords']

        # 提取中英文詞彙
        words = re.findall(r'\b[a-zA-Z\u4e00-\u9fff]{3,}\b', content)
        word_freq = {}

        # 統計詞頻
        for word in words:
            word_lower = word.lower()
            # 過濾常見停用詞
            if word_lower not in ['the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by']:
                word_freq[word_lower] = word_freq.get(word_lower, 0) + 1

        # 排序並返回前N個
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_words[:max_keywords]]

    def build_knowledge_database(self, collection_name: str = None) -> bool:
        """
        建立知識點向量資料庫

        Args:
            collection_name: 集合名稱（ChromaDB用）

        Returns:
            bool: 建立是否成功
        """
        if not self.knowledge_points:
            logger.error("❌ 沒有知識點可以建立向量資料庫，請先執行 create_knowledge_points()")
            return False

        collection_name = collection_name or config.COLLECTION_NAME
        logger.info(f"🔧 正在建立向量資料庫 ({'ChromaDB' if self.use_chromadb else 'FAISS'})")

        # 準備文本數據
        texts = [kp["content"] for kp in self.knowledge_points]

        try:
            if self.use_chromadb:
                return self._build_chromadb(texts, collection_name)
            else:
                return self._build_faiss(texts)
        except Exception as e:
            logger.error(f"❌ 建立向量資料庫失敗: {e}")
            return False

    def _build_chromadb(self, texts: List[str], collection_name: str) -> bool:
        """
        建立ChromaDB向量資料庫 (支援GPU加速)

        Args:
            texts: 文本列表
            collection_name: 集合名稱

        Returns:
            bool: 建立是否成功
        """
        try:
            # 創建或獲取集合
            self.collection = self.chroma_client.get_or_create_collection(
                name=collection_name,
                metadata={"description": "教材知識點向量資料庫"}
            )

            # 準備數據
            ids = [kp["id"] for kp in self.knowledge_points]
            metadatas = []

            # 處理元數據，確保所有值都是字符串或數字
            for kp in self.knowledge_points:
                metadata = {}
                for key, value in kp["metadata"].items():
                    if isinstance(value, (str, int, float)):
                        metadata[key] = value
                    else:
                        metadata[key] = str(value)

                # 添加額外的知識點資訊
                metadata.update({
                    "title": kp["title"],
                    "summary": kp["summary"],
                    "keywords": ", ".join(kp["keywords"])
                })
                metadatas.append(metadata)

            # 根據設備選擇批量大小
            if self.device == 'cuda':
                batch_size = config.PERFORMANCE_CONFIG['gpu_batch_size']
                logger.info(f"🚀 使用GPU批量處理，批量大小: {batch_size}")
            else:
                batch_size = config.PERFORMANCE_CONFIG['cpu_batch_size']
                logger.info(f"🖥️ 使用CPU批量處理，批量大小: {batch_size}")

            total_batches = (len(texts) + batch_size - 1) // batch_size

            # 預先生成所有嵌入向量 (GPU加速)
            logger.info("🔄 正在生成嵌入向量...")
            all_embeddings = []

            for i in tqdm(range(0, len(texts), batch_size),
                         desc="生成向量",
                         total=total_batches,
                         disable=not self.verbose):
                batch_texts = texts[i:i+batch_size]

                # 使用GPU/CPU生成嵌入向量 (優化版)
                try:
                    if self.device == 'cuda':
                        # GPU模式：使用混合精度和優化參數
                        with torch.cuda.amp.autocast(enabled=config.GPU_CONFIG['mixed_precision']):
                            batch_embeddings = self.embedding_model.encode(
                                batch_texts,
                                device=self.device,
                                batch_size=config.EMBEDDING_CONFIG['batch_size'],
                                show_progress_bar=config.EMBEDDING_CONFIG['show_progress_bar'],
                                convert_to_numpy=True,
                                normalize_embeddings=config.EMBEDDING_CONFIG['normalize_embeddings'],
                                convert_to_tensor=False  # 轉為numpy以節省GPU記憶體
                            )
                    else:
                        # CPU模式
                        batch_embeddings = self.embedding_model.encode(
                            batch_texts,
                            batch_size=config.PERFORMANCE_CONFIG['cpu_batch_size'],
                            show_progress_bar=False,
                            convert_to_numpy=True,
                            normalize_embeddings=config.EMBEDDING_CONFIG['normalize_embeddings']
                        )

                    all_embeddings.extend(batch_embeddings.tolist())

                    # GPU記憶體清理
                    if self.device == 'cuda':
                        torch.cuda.empty_cache()

                except Exception as e:
                    logger.error(f"❌ 批量 {i//batch_size + 1} 向量生成失敗: {e}")
                    return False

            # 批量添加到ChromaDB
            logger.info("🔄 正在添加到ChromaDB...")
            for i in tqdm(range(0, len(texts), batch_size),
                         desc="添加到ChromaDB",
                         total=total_batches,
                         disable=not self.verbose):
                batch_texts = texts[i:i+batch_size]
                batch_ids = ids[i:i+batch_size]
                batch_metadatas = metadatas[i:i+batch_size]

                self.collection.add(
                    documents=batch_texts,
                    ids=batch_ids,
                    metadatas=batch_metadatas
                )

            logger.info(f"✅ ChromaDB建立完成，包含 {len(texts)} 個向量")
            logger.info(f"🖥️ 使用設備: {self.device}")
            return True

        except Exception as e:
            logger.error(f"❌ 建立ChromaDB時發生錯誤: {e}")
            return False

    def _build_faiss(self, texts: List[str]) -> bool:
        """
        建立FAISS向量資料庫 (支援GPU加速)

        Args:
            texts: 文本列表

        Returns:
            bool: 建立是否成功
        """
        try:
            import faiss

            # 根據設備選擇批量大小
            if self.device == 'cuda':
                batch_size = config.PERFORMANCE_CONFIG['gpu_batch_size']
                logger.info(f"🚀 使用GPU生成FAISS向量，批量大小: {batch_size}")
            else:
                batch_size = config.PERFORMANCE_CONFIG['cpu_batch_size']
                logger.info(f"🖥️ 使用CPU生成FAISS向量，批量大小: {batch_size}")

            # 批量生成嵌入向量
            logger.info("🔄 正在生成嵌入向量...")
            all_embeddings = []
            total_batches = (len(texts) + batch_size - 1) // batch_size

            for i in tqdm(range(0, len(texts), batch_size),
                         desc="生成FAISS向量",
                         total=total_batches,
                         disable=not self.verbose):
                batch_texts = texts[i:i+batch_size]

                try:
                    if self.device == 'cuda':
                        # GPU模式：使用混合精度和優化參數
                        with torch.cuda.amp.autocast(enabled=config.GPU_CONFIG['mixed_precision']):
                            batch_embeddings = self.embedding_model.encode(
                                batch_texts,
                                device=self.device,
                                batch_size=config.EMBEDDING_CONFIG['batch_size'],
                                show_progress_bar=False,
                                convert_to_numpy=True,
                                normalize_embeddings=config.EMBEDDING_CONFIG['normalize_embeddings']
                            )
                    else:
                        # CPU模式
                        batch_embeddings = self.embedding_model.encode(
                            batch_texts,
                            batch_size=config.PERFORMANCE_CONFIG['cpu_batch_size'],
                            show_progress_bar=False,
                            convert_to_numpy=True,
                            normalize_embeddings=config.EMBEDDING_CONFIG['normalize_embeddings']
                        )

                    all_embeddings.append(batch_embeddings)

                    # GPU記憶體清理
                    if self.device == 'cuda':
                        torch.cuda.empty_cache()

                except Exception as e:
                    logger.error(f"❌ 批量 {i//batch_size + 1} FAISS向量生成失敗: {e}")
                    return False

            # 合併所有嵌入向量
            embeddings = np.vstack(all_embeddings)

            # 建立FAISS索引
            dimension = embeddings.shape[1]

            if self.device == 'cuda' and self.gpu_info['available']:
                # 嘗試使用GPU FAISS
                try:
                    # 創建GPU資源
                    res = faiss.StandardGpuResources()

                    # 創建CPU索引然後轉移到GPU
                    cpu_index = faiss.IndexFlatL2(dimension)
                    self.faiss_index = faiss.index_cpu_to_gpu(res, 0, cpu_index)

                    logger.info("🚀 使用GPU FAISS索引")
                except Exception as e:
                    logger.warning(f"⚠️ GPU FAISS初始化失敗，使用CPU FAISS: {e}")
                    self.faiss_index = faiss.IndexFlatL2(dimension)
            else:
                # 使用CPU FAISS
                self.faiss_index = faiss.IndexFlatL2(dimension)
                logger.info("🖥️ 使用CPU FAISS索引")

            # 添加向量到索引
            self.faiss_index.add(embeddings.astype('float32'))

            # 保存元數據
            self.faiss_metadata = self.knowledge_points.copy()

            logger.info(f"✅ FAISS索引建立完成，包含 {self.faiss_index.ntotal} 個向量")
            logger.info(f"🖥️ 使用設備: {self.device}")
            return True

        except Exception as e:
            logger.error(f"❌ 建立FAISS時發生錯誤: {e}")
            return False

    def save_knowledge_points(self, output_path: str = None) -> bool:
        """
        保存知識點到JSON檔案

        Args:
            output_path: 輸出檔案路徑

        Returns:
            bool: 保存是否成功
        """
        if not self.knowledge_points:
            logger.warning("⚠️ 沒有知識點可以保存")
            return False

        if output_path is None:
            output_path = config.OUTPUT_DIR / config.OUTPUT_FILES['knowledge_points']

        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.knowledge_points, f, ensure_ascii=False, indent=2)
            logger.info(f"✅ 知識點已保存到: {output_path}")
            return True
        except Exception as e:
            logger.error(f"❌ 保存知識點失敗: {e}")
            return False

    def get_processing_summary(self) -> Dict[str, Any]:
        """
        獲取處理摘要資訊

        Returns:
            Dict: 處理摘要
        """
        return {
            "structured_data_count": len(self.structured_data),
            "knowledge_points_count": len(self.knowledge_points),
            "embedding_model": self.embedding_model_name,
            "database_type": "ChromaDB" if self.use_chromadb else "FAISS",
            "database_path": config.CHROMA_DB_PATH if self.use_chromadb else config.FAISS_INDEX_PATH,
            "device": self.device,
            "gpu_available": self.gpu_info['available'],
            "gpu_name": self.gpu_info.get('device_name', 'N/A'),
            "gpu_memory": f"{self.gpu_info.get('memory_total', 0)}GB",
            "collection_available": self.collection is not None
        }

    def search_knowledge(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        搜索相關知識點

        Args:
            query: 搜索查詢
            top_k: 返回結果數量

        Returns:
            List[Dict]: 搜索結果列表
        """
        if not self.collection:
            logger.warning("⚠️ 向量資料庫未初始化")
            return []

        try:
            # 使用ChromaDB搜索
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k
            )

            # 格式化結果
            formatted_results = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    metadata = results['metadatas'][0][i] if results['metadatas'] and results['metadatas'][0] else {}
                    distance = results['distances'][0][i] if results['distances'] and results['distances'][0] else 0

                    formatted_results.append({
                        'content': doc,
                        'metadata': metadata,
                        'similarity': 1 - distance,  # 轉換為相似度
                        'title': metadata.get('title', '相關知識'),
                        'source': metadata.get('source_file', '教學資料'),
                        'chapter': metadata.get('chapter', '相關章節'),
                        'keywords': metadata.get('keywords', [])
                    })
            logger.info(f"🔍 原始搜索結果: {results['documents'][0]}")
            logger.info(f"🔍 搜索到 {len(formatted_results)} 個相關結果")
            return formatted_results

        except Exception as e:
            logger.error(f"❌ 搜索知識點時發生錯誤: {e}")
            return []
