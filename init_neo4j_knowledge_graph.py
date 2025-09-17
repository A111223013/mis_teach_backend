#!/usr/bin/env python3
"""
Neo4j 知識圖譜初始化腳本
用於從 MongoDB 數據創建知識點節點和關係

使用方法:
1. 確保 Neo4j 服務運行 (bolt://localhost:7687)
2. 設置環境變數 NEO4J_PASSWORD
3. 運行: python init_neo4j_knowledge_graph.py
"""

import os
import sys
import logging
from datetime import datetime

# 添加 src 目錄到路徑
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from accessories import mongo
from neo4j_knowledge_graph import Neo4jKnowledgeGraph
from app import app

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_neo4j_knowledge_graph():
    """初始化 Neo4j 知識圖譜"""
    
    # 使用 Flask 應用上下文
    with app.app_context():
        # 檢查 MongoDB 連接
        if mongo.db is None:
            logger.error("MongoDB 連接失敗")
            return False
        
        # 初始化 Neo4j
        kg = Neo4jKnowledgeGraph()
        if not kg.driver:
            logger.error("Neo4j 連接失敗")
            return False
        
        try:
            # 1. 清空現有數據（可選）
            logger.info("清空現有知識圖譜數據...")
            with kg.driver.session() as session:
                session.run("MATCH (n) DETACH DELETE n")
            
            # 2. 從 MongoDB 創建知識點節點
            logger.info("從 MongoDB 創建知識點節點...")
            create_all_nodes_from_mongodb(kg, mongo.db)
            
            # 3. 創建示例關係（用於測試）
            logger.info("創建示例關係...")
            kg.create_sample_relationships()
            
            # 4. 基於領域創建關係
            logger.info("基於領域創建知識點關係...")
            create_domain_relationships(kg)
            
            # 5. 基於 MongoDB 集合結構創建關係
            logger.info("基於 MongoDB 集合結構創建關係...")
            create_question_based_relationships(kg)
            
            logger.info("Neo4j 知識圖譜初始化完成！")
            return True
            
        except Exception as e:
            logger.error(f"初始化失敗: {e}")
            return False
        finally:
            kg.close()

def create_all_nodes_from_mongodb(kg: Neo4jKnowledgeGraph, mongo_db):
    """從 MongoDB 創建所有類型的節點"""
    try:
        # 1. 創建 Domain 節點
        logger.info("創建 Domain 節點...")
        domains = list(mongo_db.domain.find())
        for domain in domains:
            domain_name = domain.get("name")
            kg.create_concept_node(domain_name, "Domain", {
                "description": domain.get("description", ""),
                "domain_id": str(domain.get("_id"))
            })
        
        # 2. 創建 Block 節點
        logger.info("創建 Block 節點...")
        blocks = list(mongo_db.block.find())
        for block in blocks:
            block_name = block.get("title")  # 修正：使用 title 而不是 name
            if block_name:  # 確保名稱不為空
                kg.create_concept_node(block_name, "Block", {
                    "description": block.get("description", ""),
                    "block_id": str(block.get("_id")),
                    "domain_id": str(block.get("domain_id"))  # 修正：使用 domain_id
                })
        
        # 3. 創建 Micro Concept 節點
        logger.info("創建 Micro Concept 節點...")
        concepts = list(mongo_db.micro_concept.find())
        for concept in concepts:
            concept_name = concept.get("name")
            kg.create_concept_node(concept_name, "Concept", {
                "description": concept.get("description", ""),
                "concept_id": str(concept.get("_id")),
                "block_id": str(concept.get("block_id"))
            })
        
        logger.info(f"創建節點完成: {len(domains)} 個 Domain, {len(blocks)} 個 Block, {len(concepts)} 個 Concept")
        
    except Exception as e:
        logger.error(f"創建節點失敗: {e}")

def create_domain_relationships(kg: Neo4jKnowledgeGraph):
    """基於領域創建知識點關係"""
    try:
        # 獲取所有領域
        domains = list(mongo.db.domain.find({}, {"_id": 1, "name": 1}))
        
        for domain in domains:
            domain_id = str(domain["_id"])
            domain_name = domain["name"]
            
            # 獲取此領域的所有知識點
            concepts = list(mongo.db.micro_concept.find(
                {"domain_id": domain_id},
                {"name": 1, "description": 1}
            ))
            
            # 創建領域內知識點的相關關係
            for i, concept1 in enumerate(concepts):
                for j, concept2 in enumerate(concepts):
                    if i != j:
                        # 基於描述相似度創建關係
                        similarity = calculate_text_similarity(
                            concept1.get("description", ""),
                            concept2.get("description", "")
                        )
                        
                        if similarity > 0.3:  # 相似度閾值
                            kg.create_relationship(
                                concept1["name"],
                                concept2["name"],
                                "RELATED_TO",
                                {"similarity": similarity, "domain": domain_name}
                            )
        
        logger.info(f"基於 {len(domains)} 個領域創建了關係")
        
    except Exception as e:
        logger.error(f"創建領域關係失敗: {e}")

def create_question_based_relationships(kg: Neo4jKnowledgeGraph):
    """基於 MongoDB 三個集合的層級關係創建知識圖譜"""
    try:
        relationship_count = 0
        
        # 1. 創建 Domain -> Block 關係
        logger.info("創建 Domain -> Block 關係...")
        domains = list(mongo.db.domain.find())
        for domain in domains:
            domain_name = domain.get("name")
            block_ids = domain.get("blocks", [])
            
            for block_id in block_ids:
                # 查找 block 名稱
                block = mongo.db.block.find_one({"_id": block_id})
                if block:
                    block_name = block.get("title")  # 修正：使用 title 而不是 name
                    kg.create_relationship(
                        domain_name, block_name, "INCLUDES",
                        {"source": "domain_structure", "level": "domain_to_block"}
                    )
                    relationship_count += 1
        
        # 2. 創建 Block -> Micro Concept 關係
        logger.info("創建 Block -> Micro Concept 關係...")
        blocks = list(mongo.db.block.find())
        for block in blocks:
            block_name = block.get("title")  # 修正：使用 title
            block_id = block.get("_id")
            
            # 查找屬於此 block 的 micro_concepts
            concepts = list(mongo.db.micro_concept.find({"block_id": block_id}))
            for concept in concepts:
                concept_name = concept.get("name")
                kg.create_relationship(
                    block_name, concept_name, "INCLUDES",
                    {"source": "domain_structure", "level": "block_to_concept"}
                )
                relationship_count += 1
        
        # 3. 創建 Block 之間的順序關係（基於章節順序）
        logger.info("創建 Block 順序關係...")
        for domain in domains:
            domain_name = domain.get("name")
            block_ids = domain.get("blocks", [])
            
            # 按順序創建 Block 之間的 LEADS_TO 關係
            for i in range(len(block_ids) - 1):
                current_block = mongo.db.block.find_one({"_id": block_ids[i]})
                next_block = mongo.db.block.find_one({"_id": block_ids[i + 1]})
                
                if current_block and next_block:
                    current_name = current_block.get("title")
                    next_name = next_block.get("title")
                    kg.create_relationship(
                        current_name, next_name, "LEADS_TO",
                        {"source": "domain_structure", "level": "block_to_block", "order": i + 1}
                    )
                    relationship_count += 1
        
        # 4. 創建 Micro Concept 之間的順序關係（基於同一個 Block 內的順序）
        logger.info("創建 Micro Concept 順序關係...")
        for block in blocks:
            block_name = block.get("title")
            subtopic_ids = block.get("subtopics", [])
            
            # 按順序創建 Micro Concept 之間的 LEADS_TO 關係
            for i in range(len(subtopic_ids) - 1):
                current_concept = mongo.db.micro_concept.find_one({"_id": subtopic_ids[i]})
                next_concept = mongo.db.micro_concept.find_one({"_id": subtopic_ids[i + 1]})
                
                if current_concept and next_concept:
                    current_name = current_concept.get("name")
                    next_name = next_concept.get("name")
                    kg.create_relationship(
                        current_name, next_name, "LEADS_TO",
                        {"source": "domain_structure", "level": "concept_to_concept", "order": i + 1}
                    )
                    relationship_count += 1
        
        # 5. 創建 Block 之間的依賴關係（如果有 dependencies）
        logger.info("創建 Block 依賴關係...")
        for block in blocks:
            block_name = block.get("title")
            dependencies = block.get("dependencies", [])
            
            for dep_id in dependencies:
                dep_block = mongo.db.block.find_one({"_id": dep_id})
                if dep_block:
                    dep_name = dep_block.get("title")
                    kg.create_relationship(
                        dep_name, block_name, "PREREQUISITE",
                        {"source": "domain_structure", "level": "block_dependency"}
                    )
                    relationship_count += 1
        
        # 6. 創建 Micro Concept 之間的依賴關係（如果有 dependencies）
        logger.info("創建 Micro Concept 依賴關係...")
        concepts = list(mongo.db.micro_concept.find())
        for concept in concepts:
            concept_name = concept.get("name")
            dependencies = concept.get("dependencies", [])
            
            for dep_id in dependencies:
                dep_concept = mongo.db.micro_concept.find_one({"_id": dep_id})
                if dep_concept:
                    dep_name = dep_concept.get("name")
                    kg.create_relationship(
                        dep_name, concept_name, "PREREQUISITE",
                        {"source": "domain_structure", "level": "concept_dependency"}
                    )
                    relationship_count += 1
        
        logger.info(f"基於 MongoDB 集合結構創建了 {relationship_count} 個關係")
        
    except Exception as e:
        logger.error(f"創建知識圖譜關係失敗: {e}")

def calculate_text_similarity(text1: str, text2: str) -> float:
    """計算文本相似度"""
    if not text1 or not text2:
        return 0.0
    
    # 簡單的詞彙重疊相似度
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    
    if not words1 or not words2:
        return 0.0
    
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    
    return len(intersection) / len(union) if union else 0.0

def verify_knowledge_graph(kg: Neo4jKnowledgeGraph):
    """驗證知識圖譜"""
    try:
        with kg.driver.session() as session:
            # 統計節點數量
            result = session.run("MATCH (n:Concept) RETURN count(n) as count")
            node_count = result.single()["count"]
            
            # 統計關係數量
            result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
            rel_count = result.single()["count"]
            
            logger.info(f"知識圖譜統計:")
            logger.info(f"  - 節點數量: {node_count}")
            logger.info(f"  - 關係數量: {rel_count}")
            
            # 顯示一些示例關係
            result = session.run("""
                MATCH (a:Concept)-[r]->(b:Concept)
                RETURN a.name, type(r), b.name
                LIMIT 10
            """)
            
            logger.info("示例關係:")
            for record in result:
                logger.info(f"  {record['a.name']} -[{record['type(r)']}]-> {record['b.name']}")
            
    except Exception as e:
        logger.error(f"驗證知識圖譜失敗: {e}")

if __name__ == "__main__":
    print("開始初始化 Neo4j 知識圖譜...")
    print(f"時間: {datetime.now()}")
    print("-" * 50)
    
    success = init_neo4j_knowledge_graph()
    
    if success:
        print("-" * 50)
        print("✅ Neo4j 知識圖譜初始化成功！")
        
        # 驗證結果
        kg = Neo4jKnowledgeGraph()
        if kg.driver:
            verify_knowledge_graph(kg)
            kg.close()
    else:
        print("-" * 50)
        print("❌ Neo4j 知識圖譜初始化失敗！")
        sys.exit(1)
