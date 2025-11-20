#!/usr/bin/env python3
"""
RAG System for Persona Example Retrieval
Implements vector similarity search for intelligent example selection
"""

import json
import logging
import numpy as np
import os
import uuid
import hashlib
import threading
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows fallback
    fcntl = None

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logging.warning("sentence-transformers not available. Using fallback similarity.")

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logging.warning("FAISS not available. Using fallback vector storage.")

logger = logging.getLogger(__name__)


class VectorExample:
    """Represents a single example with vector embedding"""

    def __init__(self,
                 example_id: str,
                 persona_id: str,
                 content: str,
                 embedding: Optional[np.ndarray] = None,
                 metadata: Optional[Dict] = None):
        self.example_id = example_id
        self.persona_id = persona_id
        self.content = content
        self.embedding = embedding
        self.metadata = metadata or {}
        self.created_at = datetime.now().isoformat()


class ExampleVectorDatabase:
    """Vector database for persona examples with semantic search"""

    def __init__(self, storage_path: str = "data/vector_db"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.lock_file = self.storage_path / ".lock"
        self.lock_file.touch(exist_ok=True)
        self._mutex = threading.Lock()
        self._persona_hashes: Dict[str, set] = defaultdict(set)
        self._max_per_persona = int(os.getenv("RAG_MAX_EXAMPLES_PER_PERSONA", "400"))

        # Initialize model
        self.model = None
        self.embedding_dim = 384  # Default for all-MiniLM-L6-v2

        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self.model = SentenceTransformer('all-MiniLM-L6-v2')
                self.embedding_dim = self.model.get_sentence_embedding_dimension()
                logger.info(f"Loaded sentence transformer with {self.embedding_dim} dimensions")
            except Exception as e:
                logger.warning(f"Failed to load sentence transformer: {e}")

        # Vector storage
        self.examples: Dict[str, VectorExample] = {}
        self.index = None
        self.id_to_index: Dict[str, int] = {}

        # Initialize FAISS if available
        if FAISS_AVAILABLE:
            self.index = faiss.IndexFlatIP(self.embedding_dim)
            logger.info("Using FAISS for vector indexing")
        else:
            logger.info("Using fallback vector storage")

        # Load existing data
        self._load_examples()

    @contextmanager
    def _file_lock(self):
        """Cross-platform file lock to protect vector DB writes"""
        if fcntl is None:
            self._mutex.acquire()
            try:
                yield
            finally:
                self._mutex.release()
            return

        with open(self.lock_file, "w") as lock_handle:
            fcntl.flock(lock_handle, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_handle, fcntl.LOCK_UN)

    def _content_hash(self, content: str) -> str:
        normalized = (content or "").strip().lower()
        if not normalized:
            normalized = content or ""
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def _register_hash(self, persona_id: Optional[str], content_hash: str):
        persona_key = persona_id or "default"
        self._persona_hashes[persona_key].add(content_hash)

    def _has_hash(self, persona_id: Optional[str], content_hash: str) -> bool:
        persona_key = persona_id or "default"
        return content_hash in self._persona_hashes.get(persona_key, set())

    def _prune_persona_examples(self, persona_id: Optional[str]):
        """Trim persona examples to stay within configured limit"""
        if not self._max_per_persona:
            return

        persona_key = persona_id or "default"
        persona_examples = [
            ex for ex in self.examples.values() if ex.persona_id == persona_key
        ]

        if len(persona_examples) <= self._max_per_persona:
            return

        try:
            persona_examples.sort(
                key=lambda ex: datetime.fromisoformat(ex.created_at)
                if ex.created_at
                else datetime.min
            )
        except Exception:
            persona_examples.sort(key=lambda ex: ex.created_at or "")

        to_remove = len(persona_examples) - self._max_per_persona
        remove_targets = persona_examples[:to_remove]

        for ex in remove_targets:
            self.examples.pop(ex.example_id, None)
            self._persona_hashes[persona_key].discard(self._content_hash(ex.content))

        # Rebuild index after removal
        if self.examples and FAISS_AVAILABLE:
            self._rebuild_index()

    def _load_examples(self):
        """Load examples from storage"""
        try:
            examples_file = self.storage_path / "examples.json"
            if not examples_file.exists():
                return

            with self._file_lock():
                with open(examples_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

            for example_data in data.get('examples', []):
                # Handle legacy data format
                example_kwargs = {
                    'example_id': example_data['example_id'],
                    'persona_id': example_data['persona_id'],
                    'content': example_data['content'],
                    'metadata': example_data.get('metadata', {})
                }

                example = VectorExample(**example_kwargs)

                # Convert embedding back to numpy array
                if example_data.get('embedding'):
                    example.embedding = np.array(example_data['embedding'], dtype=np.float32)

                # Set created_at from legacy data if available
                if example_data.get('created_at'):
                    example.created_at = example_data['created_at']

                # Restore stored hash or recompute for backwards compatibility
                stored_hash = example_data.get('content_hash') or example.metadata.get('content_hash')
                if not stored_hash:
                    stored_hash = self._content_hash(example.content)
                example.metadata.setdefault('content_hash', stored_hash)
                self._register_hash(example.persona_id, stored_hash)

                self.examples[example.example_id] = example

            # Rebuild index
            if self.examples and self.index:
                self._rebuild_index()

            logger.info(f"Loaded {len(self.examples)} examples from storage")
        except Exception as e:
            logger.error(f"Failed to load examples: {e}")

    def _save_examples(self):
        """Save examples to storage with locking"""
        try:
            with self._file_lock():
                self._write_examples()
        except Exception as e:
            logger.error(f"Failed to save examples: {e}")

    def _write_examples(self):
        """Write examples to disk (caller must hold lock)"""
        examples_file = self.storage_path / "examples.json"
        data = {
            'examples': [],
            'last_updated': datetime.now().isoformat()
        }

        for example in self.examples.values():
            content_hash = example.metadata.get('content_hash') or self._content_hash(example.content)
            example.metadata['content_hash'] = content_hash
            example_data = {
                'example_id': example.example_id,
                'persona_id': example.persona_id,
                'content': example.content,
                'metadata': example.metadata,
                'created_at': example.created_at,
                'embedding': example.embedding.tolist() if example.embedding is not None else None,
                'content_hash': content_hash
            }
            data['examples'].append(example_data)

        with open(examples_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _rebuild_index(self):
        """Rebuild the FAISS index from examples"""
        if not FAISS_AVAILABLE or not self.examples:
            return

        # Clear existing index
        self.index = faiss.IndexFlatIP(self.embedding_dim)
        self.id_to_index.clear()

        # Add all examples with embeddings
        for i, example in enumerate(self.examples.values()):
            if example.embedding is not None:
                # Normalize embedding for cosine similarity
                normalized_embedding = example.embedding / np.linalg.norm(example.embedding)
                self.index.add(normalized_embedding.reshape(1, -1))
                self.id_to_index[example.example_id] = i

        logger.info(f"Rebuilt index with {len(self.id_to_index)} examples")

    def _create_embedding(self, content: str) -> Optional[np.ndarray]:
        """Create embedding for content"""
        try:
            if self.model:
                embedding = self.model.encode(content, convert_to_numpy=True)
                return embedding.astype(np.float32)
            else:
                # Fallback: use simple hash-based embedding
                logger.warning("Using fallback embedding method")
                return self._fallback_embedding(content)
        except Exception as e:
            logger.error(f"Failed to create embedding: {e}")
            return None

    def _fallback_embedding(self, content: str) -> np.ndarray:
        """Fallback embedding using simple hashing"""
        # Simple character-level embedding as fallback
        embedding = np.zeros(self.embedding_dim, dtype=np.float32)

        # Create hash-based features
        for i, char in enumerate(content[:100]):  # Limit to first 100 chars
            hash_val = hash(char + str(i))
            embedding[hash_val % self.embedding_dim] += 1

        # Normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm

        return embedding

    def add_example(self, persona_id: str, content: str, metadata: Optional[Dict] = None) -> str:
        """Add a new example to the vector database"""
        content = (content or "").strip()
        if not content:
            logger.debug("Skipping empty example content for persona %s", persona_id)
            return None

        content_hash = self._content_hash(content)
        if self._has_hash(persona_id, content_hash):
            logger.debug(
                "Skipping duplicate example for persona %s (hash=%s)", persona_id, content_hash[:8]
            )
            return None

        embedding = self._create_embedding(content)
        if embedding is None:
            logger.error("Failed to create embedding for example")
            return None

        example_id = str(uuid.uuid4())
        example_metadata = dict(metadata or {})
        example_metadata["content_hash"] = content_hash
        example_metadata.setdefault("source", "ingested")

        example = VectorExample(
            example_id=example_id,
            persona_id=persona_id or "default",
            content=content,
            embedding=embedding,
            metadata=example_metadata,
        )

        with self._file_lock():
            self.examples[example_id] = example
            self._register_hash(example.persona_id, content_hash)

            if FAISS_AVAILABLE and self.index:
                norm = np.linalg.norm(embedding)
                if norm == 0:
                    logger.debug("Embedding norm is zero, skipping FAISS insert for %s", example_id)
                else:
                    normalized_embedding = embedding / norm
                    self.id_to_index[example_id] = self.index.ntotal
                    self.index.add(normalized_embedding.reshape(1, -1))

            self._prune_persona_examples(example.persona_id)
            self._write_examples()

        logger.info(f"Added example {example_id} for persona {persona_id}")
        return example_id

    def add_examples_batch(self, persona_id: str, examples: List[str],
                          metadata: Optional[Dict] = None) -> List[str]:
        """Add multiple examples efficiently"""
        example_ids = []
        for content in examples:
            example_id = self.add_example(persona_id=persona_id, content=content, metadata=metadata)
            if example_id:
                example_ids.append(example_id)

        logger.info(f"Added {len(example_ids)} examples for persona {persona_id}")
        return example_ids

    def search_similar(self, query: str, persona_id: Optional[str] = None,
                       k: int = 5, threshold: float = 0.1) -> List[Dict]:
        """Search for similar examples"""
        try:
            # Create query embedding
            query_embedding = self._create_embedding(query)
            if query_embedding is None:
                return []

            # Filter by persona if specified
            candidates = list(self.examples.values())
            if persona_id:
                candidates = [ex for ex in candidates if ex.persona_id == persona_id]

            if not candidates:
                return []

            # Use FAISS if available
            if FAISS_AVAILABLE and self.index:
                # Normalize query
                query_normalized = query_embedding / np.linalg.norm(query_embedding)

                # Search
                scores, indices = self.index.search(query_normalized.reshape(1, -1),
                                                  min(k * 2, len(candidates)))

                results = []
                for score, idx in zip(scores[0], indices[0]):
                    if score < threshold or idx >= len(candidates):
                        continue

                    # Find example by index
                    for example in candidates:
                        if self.id_to_index.get(example.example_id) == idx:
                            results.append({
                                'example': example,
                                'score': float(score),
                                'content': example.content,
                                'metadata': example.metadata
                            })
                            break

                    if len(results) >= k:
                        break

                return results

            else:
                # Fallback: simple similarity search
                results = []
                for example in candidates:
                    if example.embedding is None:
                        continue

                    # Cosine similarity
                    similarity = np.dot(query_embedding, example.embedding) / (
                        np.linalg.norm(query_embedding) * np.linalg.norm(example.embedding)
                    )

                    if similarity >= threshold:
                        results.append({
                            'example': example,
                            'score': float(similarity),
                            'content': example.content,
                            'metadata': example.metadata
                        })

                # Sort by similarity and return top k
                results.sort(key=lambda x: x['score'], reverse=True)
                return results[:k]

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def get_persona_examples(self, persona_id: str) -> List[VectorExample]:
        """Get all examples for a specific persona"""
        return [ex for ex in self.examples.values() if ex.persona_id == persona_id]

    def delete_persona_examples(self, persona_id: str):
        """Delete all examples for a specific persona"""
        persona_key = persona_id or "default"
        with self._file_lock():
            examples_to_delete = [
                ex_id
                for ex_id, ex in self.examples.items()
                if ex.persona_id == persona_key
            ]

            for example_id in examples_to_delete:
                example = self.examples.pop(example_id, None)
                if example:
                    self._persona_hashes[persona_key].discard(
                        example.metadata.get("content_hash", self._content_hash(example.content))
                    )

            if self.examples and FAISS_AVAILABLE:
                self._rebuild_index()

            self._write_examples()

        logger.info(f"Deleted {len(examples_to_delete)} examples for persona {persona_id}")

    def get_stats(self) -> Dict:
        """Get database statistics"""
        return {
            'total_examples': len(self.examples),
            'unique_personas': len(set(ex.persona_id for ex in self.examples.values())),
            'storage_path': str(self.storage_path),
            'faiss_available': FAISS_AVAILABLE,
            'sentence_transformers_available': SENTENCE_TRANSFORMERS_AVAILABLE,
            'embedding_dimension': self.embedding_dim,
            'index_size': self.index.ntotal if FAISS_AVAILABLE and self.index else 0
        }