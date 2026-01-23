# necessary imports
import numpy as np
import ollama
from typing import List
from config import Config
# -----------------------------
# UTIL: Ollama connectivity
# -----------------------------

def ollama_chat(model: str, system: str, user: str) -> str:
    resp = ollama.chat(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        options = {
            'temperature': Config.temperature,
            'num_predict': Config.max_tokens,
        }
    )
    return resp["message"]["content"].strip()


def ollama_embed(model: str, text: str) -> np.ndarray:
    resp = ollama.embeddings(model=model, prompt=text)
    return np.array(resp["embedding"], dtype=np.float32)

# Text chunking function
def chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    """
    Simple overlapping character chunker.
    Keeps enough context while keeping chunks focused for retrieval.
    """
    text = text.replace("\r\n", "\n")
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == len(text):
            break
        start = max(0, end - overlap)
    return chunks