# necessary imports
from dataclasses import dataclass
import os
import sys

# Configuration for the RAG system
class Config:
    # Ollama models
    chat_model: str = "gemma3:latest"          # the main chat model
    embedding_model: str = "nomic-embed-text"  # embedding model
    # Model parameters
    temperature: float = 0.1 # Controls creativity of the model outputs
    max_tokens: int = 500   # Max tokens for chat responses
    # Data paths
    knowledge_dir: str = os.path.join("data", "knowledge")
    scenarios_dir: str = os.path.join("data", "scenarios")
    cache_dir: str = os.path.join("data", "_cache")

    # Chunking for knowledge docs
    chunk_size: int = 250         # characters per chunk (context window)
    chunk_overlap: int = 50      # characters overlap between chunks

    # Retrieval size, returns k relevant chunks
    top_k: int = 4

    # Debug
    show_retrieved_chunks: bool = False