#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG系統包初始化文件 (Backend整合版本)
"""

# 版本信息
__version__ = "1.0.0"
__author__ = "RAG Team"

# 導出主要類和函數
__all__ = []

try:
    from .config import *
    __all__.extend(['config'])
except ImportError as e:
    print(f"⚠️ config導入失敗: {e}")

# 從整合的 rag_ai_role 模組導入
try:
    from .rag_ai_role import MultiAITutor
    __all__.append('MultiAITutor')
except ImportError as e:
    print(f"⚠️ MultiAITutor導入失敗: {e}")

try:
    from .rag_ai_role import AIResponder
    __all__.append('AIResponder')
except ImportError as e:
    print(f"⚠️ AIResponder導入失敗: {e}")

try:
    from .rag_ai_role import RAGAssistantService
    __all__.append('RAGAssistantService')
except ImportError as e:
    print(f"⚠️ RAGAssistantService導入失敗: {e}")

# 從 rag_build 模組導入
try:
    from .rag_build import RAGBuilder
    __all__.append('RAGBuilder')
except ImportError as e:
    print(f"⚠️ RAGBuilder導入失敗: {e}")


print(f"✅ RAG系統模組導入完成，可用模組: {__all__}")
