"""
RAG 向量資料庫建置模組
負責處理 PDF 文件、建立向量資料庫、知識點提取等功能
"""

import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import fitz  # PyMuPDF
import google.generativeai as genai
from .config import Config

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGBuilder:
    """RAG 向量資料庫建置器"""
    
    def __init__(self, config: Config):
        """初始化建置器"""
        self.config = config
        self.embedding_model = None
        self.chroma_client = None
        self.collection = None
        self._init_components()
    
    def _init_components(self):
        """初始化組件"""
        try:
            # 初始化嵌入模型
            self.embedding_model = SentenceTransformer(
                self.config.EMBEDDING_MODEL_NAME,
                device=self.config.DEVICE
            )
            
            # 初始化 ChromaDB
            self.chroma_client = chromadb.PersistentClient(
                path=self.config.CHROMA_DB_PATH,
                settings=Settings(anonymized_telemetry=False)
            )
            
            # 獲取或創建集合
            try:
                self.collection = self.chroma_client.get_collection(
                    name=self.config.COLLECTION_NAME
                )
            except:
                self.collection = self.chroma_client.create_collection(
                    name=self.config.COLLECTION_NAME,
                    metadata={"description": "MIS教學知識庫"}
                )
            
            # 配置 Gemini API
            if self.config.GEMINI_API_KEY:
                genai.configure(api_key=self.config.GEMINI_API_KEY)
            
        except Exception as e:
            logger.error(f"❌ 初始化組件失敗: {e}")
            raise
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """從 PDF 提取文本"""
        try:
            doc = fitz.open(pdf_path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            return text
        except Exception as e:
            logger.error(f"❌ PDF 文本提取失敗 {pdf_path}: {e}")
            return ""
    
    def extract_knowledge_points(self, text: str, chapter_info: str = "") -> List[Dict]:
        """使用 AI 提取知識點"""
        try:
            prompt = f"""
            請從以下教學材料中提取結構化的知識點。
            
            章節資訊：{chapter_info}
            
            教學內容：
            {text[:3000]}  # 限制長度避免超出 token 限制
            
            請以 JSON 格式返回，包含以下結構：
            {{
                "knowledge_points": [
                    {{
                        "title": "知識點標題",
                        "content": "詳細內容說明",
                        "keywords": ["關鍵詞1", "關鍵詞2"],
                        "difficulty": 1-5,
                        "category": "分類",
                        "examples": ["範例1", "範例2"]
                    }}
                ]
            }}
            
            請確保返回有效的 JSON 格式。
            """
            
            model = genai.GenerativeModel('gemini-2.5-flash')
            response = model.generate_content(prompt)
            
            # 解析 JSON 回應
            try:
                result = json.loads(response.text)
                return result.get('knowledge_points', [])
            except json.JSONDecodeError:
                # 如果 JSON 解析失敗，返回基本結構
                return [{
                    "title": f"知識點 - {chapter_info}",
                    "content": text[:500],
                    "keywords": [],
                    "difficulty": 3,
                    "category": "一般",
                    "examples": []
                }]
                
        except Exception as e:
            logger.error(f"❌ 知識點提取失敗: {e}")
            return []
    
    def process_pdf_files(self, pdf_directory: str) -> Dict[str, Any]:
        """處理 PDF 文件並建立向量資料庫"""
        results = {
            "processed_files": 0,
            "total_knowledge_points": 0,
            "errors": [],
            "start_time": datetime.now().isoformat()
        }
        
        try:
            pdf_files = [f for f in os.listdir(pdf_directory) if f.endswith('.pdf')]
            logger.info(f"🔍 找到 {len(pdf_files)} 個 PDF 文件")
            
            all_knowledge_points = []
            
            for pdf_file in pdf_files:
                try:
                    pdf_path = os.path.join(pdf_directory, pdf_file)
                    logger.info(f"📖 處理文件: {pdf_file}")
                    
                    # 提取文本
                    text = self.extract_text_from_pdf(pdf_path)
                    if not text.strip():
                        logger.warning(f"⚠️ 文件無內容: {pdf_file}")
                        continue
                    
                    # 提取知識點
                    chapter_info = pdf_file.replace('.pdf', '')
                    knowledge_points = self.extract_knowledge_points(text, chapter_info)
                    
                    # 為每個知識點添加元數據
                    for i, kp in enumerate(knowledge_points):
                        kp.update({
                            "source_file": pdf_file,
                            "chapter": chapter_info,
                            "id": f"{chapter_info}_{i}",
                            "processed_time": datetime.now().isoformat()
                        })
                        all_knowledge_points.append(kp)
                    
                    results["processed_files"] += 1
                    results["total_knowledge_points"] += len(knowledge_points)
                    
                    logger.info(f"✅ 完成處理: {pdf_file} ({len(knowledge_points)} 個知識點)")
                    
                except Exception as e:
                    error_msg = f"處理文件 {pdf_file} 時發生錯誤: {e}"
                    logger.error(f"❌ {error_msg}")
                    results["errors"].append(error_msg)
            
            # 建立向量資料庫
            if all_knowledge_points:
                self._build_vector_database(all_knowledge_points)
                
                # 保存知識點到 JSON 文件
                output_path = os.path.join(self.config.OUTPUT_DIR, "knowledge_points.json")
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(all_knowledge_points, f, ensure_ascii=False, indent=2)
                logger.info(f"💾 知識點已保存到: {output_path}")
            
            results["end_time"] = datetime.now().isoformat()
            results["success"] = True
            
        except Exception as e:
            logger.error(f"❌ 處理 PDF 文件失敗: {e}")
            results["success"] = False
            results["error"] = str(e)
        
        return results
    
    def _build_vector_database(self, knowledge_points: List[Dict]):
        """建立向量資料庫"""
        try:
            logger.info("🔄 建立向量資料庫...")
            
            # 準備文本和元數據
            texts = []
            metadatas = []
            ids = []
            
            for kp in knowledge_points:
                # 組合文本用於嵌入
                combined_text = f"{kp['title']} {kp['content']} {' '.join(kp.get('keywords', []))}"
                texts.append(combined_text)
                
                # 準備元數據
                metadata = {
                    "title": kp['title'],
                    "category": kp.get('category', ''),
                    "difficulty": kp.get('difficulty', 3),
                    "source_file": kp.get('source_file', ''),
                    "chapter": kp.get('chapter', '')
                }
                metadatas.append(metadata)
                ids.append(kp['id'])
            
            # 生成嵌入向量
            logger.info("🔄 生成嵌入向量...")
            embeddings = self.embedding_model.encode(texts, show_progress_bar=True)
            
            # 添加到 ChromaDB
            logger.info("🔄 添加到向量資料庫...")
            self.collection.add(
                embeddings=embeddings.tolist(),
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"✅ 向量資料庫建立完成，共 {len(texts)} 個知識點")
            
        except Exception as e:
            logger.error(f"❌ 建立向量資料庫失敗: {e}")
            raise
    
    def search_knowledge(self, query: str, n_results: int = 5) -> List[Dict]:
        """搜索知識庫"""
        try:
            # 生成查詢向量
            query_embedding = self.embedding_model.encode([query])
            
            # 搜索相似知識點
            results = self.collection.query(
                query_embeddings=query_embedding.tolist(),
                n_results=n_results
            )
            
            # 格式化結果
            formatted_results = []
            for i in range(len(results['documents'][0])):
                formatted_results.append({
                    "content": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i],
                    "similarity": 1 - results['distances'][0][i] if 'distances' in results else 0.0
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"❌ 知識搜索失敗: {e}")
            return []
    
    def get_database_stats(self) -> Dict[str, Any]:
        """獲取資料庫統計資訊"""
        try:
            count = self.collection.count()
            return {
                "total_knowledge_points": count,
                "collection_name": self.config.COLLECTION_NAME,
                "embedding_model": self.config.EMBEDDING_MODEL_NAME,
                "database_path": self.config.CHROMA_DB_PATH
            }
        except Exception as e:
            logger.error(f"❌ 獲取統計資訊失敗: {e}")
            return {}
