# necessary imports
import os
import glob
import json
from typing import List, Dict, Tuple, Optional
import numpy as np
from rag_utils import ollama_embed, chunk_text
from config import Config

# Help class for building/loading a local RAG index
class RagIndex:
    """
    Minimal local vector store:
    - Reads knowledge .txt files
    - Chunks them
    - Embeds each chunk using Ollama embedding model
    - Stores embeddings + metadata in a local .npz cache for fast reload
    """

    def __init__(self, cfg: Config):
        self.cfg = cfg
        os.makedirs(self.cfg.cache_dir, exist_ok=True)
        self.cache_path = os.path.join(
            self.cfg.cache_dir,
            f"knowledge_index_{self.cfg.embedding_model.replace(':','_')}.npz"
        )

        self.chunks: List[str] = []
        self.meta: List[Dict] = []
        self.embeddings: Optional[np.ndarray] = None  # shape (N, D)

    def build_or_load(self) -> None:
        if self._cache_is_valid():
            self._load_cache()
            return

        self._build_index()
        self._save_cache()

    def _cache_is_valid(self) -> bool:
        if not os.path.exists(self.cache_path):
            return False

        # Invalidate cache if any knowledge file changed since cache created
        cache_mtime = os.path.getmtime(self.cache_path)
        files = glob.glob(os.path.join(self.cfg.knowledge_dir, "*.txt"))
        if not files:
            return False
        for f in files:
            if os.path.getmtime(f) > cache_mtime:
                return False
        return True

    def _build_index(self) -> None:
        files = sorted(glob.glob(os.path.join(self.cfg.knowledge_dir, "*.txt")))
        if not files:
            raise FileNotFoundError(
                f"No .txt knowledge files found in: {self.cfg.knowledge_dir}"
            )

        all_chunks = []
        all_meta = []

        for fp in files:
            with open(fp, "r", encoding="utf-8") as f:
                raw = f.read().strip()

            # Chunk
            chunks = chunk_text(raw, self.cfg.chunk_size, self.cfg.chunk_overlap)

            # Store
            for i, ch in enumerate(chunks):
                all_chunks.append(ch)
                all_meta.append({
                    "source_file": os.path.basename(fp),
                    "chunk_index": i,
                })

        # Embed
        embs = []
        for i, ch in enumerate(all_chunks):
            emb = ollama_embed(self.cfg.embedding_model, ch)
            embs.append(emb)
            if (i + 1) % 10 == 0:
                pass  # keep quiet; remove if you want progress logs

        self.chunks = all_chunks
        self.meta = all_meta
        self.embeddings = np.vstack(embs)

        # Normalize for cosine similarity
        self.embeddings = self._normalize(self.embeddings)

    def _save_cache(self) -> None:
        assert self.embeddings is not None
        meta_json = json.dumps(self.meta, ensure_ascii=False)
        np.savez_compressed(
            self.cache_path,
            embeddings=self.embeddings,
            chunks=np.array(self.chunks, dtype=object),
            meta=meta_json,
        )

    def _load_cache(self) -> None:
        data = np.load(self.cache_path, allow_pickle=True)
        self.embeddings = data["embeddings"]
        self.chunks = list(data["chunks"])
        self.meta = json.loads(str(data["meta"]))

    def _normalize(mat: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(mat, axis=1, keepdims=True) + 1e-12
        return mat / norms

    def retrieve(self, query: str, top_k: int) -> List[Tuple[float, str, Dict]]:
        """
        Returns list of (score, chunk_text, meta) sorted by score desc.
        Uses cosine similarity on normalized vectors.
        """
        if self.embeddings is None:
            raise RuntimeError("Index not loaded/built.")

        q = ollama_embed(self.cfg.embedding_model, query)
        q = q / (np.linalg.norm(q) + 1e-12)

        scores = self.embeddings @ q  # cosine similarity
        idx = np.argsort(scores)[::-1][:top_k]

        results = []
        for i in idx:
            results.append((float(scores[i]), self.chunks[i], self.meta[i]))
        return results