from __future__ import annotations

import json
import logging
import pickle
import re
from pathlib import Path
from typing import Final, Any

import redis
import numpy as np
import faiss
from redis import RedisError
from sentence_transformers import SentenceTransformer

from app.services.llm import LLMService
from app.config import settings


llm_service = LLMService()


logger = logging.getLogger(__name__)

DEFAULT_TTL: Final = 60  # 1 minute

MIN_TTL: Final = 60          # 1 minute
MAX_TTL: Final = 86400       # 24 hours

# Semantic search constants
SIMILARITY_THRESHOLD: Final = 0.85
INDEX_PATH: Final = Path("faiss_index.pkl")
EMBEDDING_MODEL: Final = "all-MiniLM-L6-v2"


class CacheService:
    def __init__(self) -> None:
        self.redis: redis.Redis | None = None
        self.model: SentenceTransformer | None = None
        self.index: faiss.IndexIDMap2 | None = None
        self.next_id = 0
        self.id_to_key: dict[int, str] = {}
        self.key_to_id: dict[str, int] = {}

        try:
            client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )

            # Verify connection
            client.ping()

            self.redis = client
            logger.info("Connected to Redis.")

        except RedisError:
            logger.exception("Unable to connect to Redis. Cache disabled.")

        # Initialize semantic search
        try:
            self.model = SentenceTransformer(EMBEDDING_MODEL, token=settings.hf_token)
            logger.info("Loaded sentence transformer model.")

            # Load existing FAISS index if available
            if INDEX_PATH.exists():
                self._load_index()
                logger.info(f"Loaded FAISS index.")
            else:
                # Initialize empty index
                base_index = faiss.IndexFlatIP(384)
                self.index = faiss.IndexIDMap2(base_index)
                logger.info("Initialized empty FAISS index.")

        except Exception as e:
            logger.exception(f"Failed to initialize semantic search: {e}")
            self.model = None
            self.index = None

    def get(self, key: str | None = None, *, question: str | None = None) -> str | None:
        if self.redis is None:
            return None

        # Legacy exact key lookup
        if key is not None:
            return self.redis.get(key)

        # Semantic search
        if question is not None and self.model is not None and self.index is not None:
            return self._semantic_get(question)

        return None

    def _semantic_get(self, question: str) -> str | None:
        """Perform semantic search for similar cached question."""
        try:
            # Generate embedding for the question
            embedding = self.model.encode([question], normalize_embeddings=True)
            
            if self.index.ntotal == 0:
                return None

            # Search FAISS index
            distances, indices = self.index.search(embedding.astype(np.float32), k=1)
            
            # Check if most similar question exceeds threshold
            if len(distances[0]) > 0 and distances[0][0] >= SIMILARITY_THRESHOLD:
                vector_id = int(indices[0][0])
                key = self.id_to_key.get(vector_id)
                if key is None:
                    return None
                
                cached_value = self.redis.get(key)

                if cached_value is None:
                    self.index.remove_ids(
                        np.array([vector_id], dtype=np.int64)
                    )

                    del self.id_to_key[vector_id]
                    del self.key_to_id[key]

                    self._save_index()

                    return None
                
                semantic_question: str = CacheMetadata.get_question(redis_client=self.redis, key=key)
                logger.info(f"Semantic cache hit for question: {question[:50]}... (similarity: {distances[0][0]:.3f})")
                logger.info(f"Existing semantic Question: {semantic_question}")
                return cached_value
            
            logger.info(f"Semantic cache miss for question: {question[:50]}...")
            return None

        except Exception as e:
            logger.exception(f"Semantic search failed: {e}")
            return None

    def set(self, *, key: str | None = None, value: str, question: str, response: str,) -> int:

        if self.redis is None:
            return DEFAULT_TTL

        # Auto-generate key from question if not provided (backward compatibility)
        if key is None:
            key = self._generate_key(question)

        ttl = self._determine_ttl(
            question=question,
            response=response,
        )

        # Store in Redis
        self.redis.setex(
            name=key,
            time=ttl,
            value=value,
        )

        # Add to semantic index
        if self.model is not None and self.index is not None:
            self._add_to_index(key, question)

        CacheMetadata.store_question(redis_client=self.redis, key=key, question=question)
        return ttl

    def _add_to_index(self, key: str, question: str) -> None:
        """Add a new entry to the FAISS index."""
        try:
            # Generate embedding
            embedding = self.model.encode([question], normalize_embeddings=True)
            
            # Add to FAISS index
            vector_id = self.next_id
            self.next_id += 1

            self.index.add_with_ids(
                embedding.astype(np.float32),
                np.array([vector_id], dtype=np.int64),
            )

            self.id_to_key[vector_id] = key
            self.key_to_id[key] = vector_id
            
            # Persist to disk
            self._save_index()
            logger.info(f"Added to semantic index: {question[:50]}...")
            
        except Exception as e:
            logger.exception(f"Failed to add to semantic index: {e}")

    def clear(self) -> None:
        """Clear all cached data including semantic index."""
        if self.redis is not None:
            self.redis.flushdb()
        
        # Reset semantic index
        if self.model is not None:
            self.index = faiss.IndexFlatIP(384)
            self.next_id = 0
            self.id_to_key.clear()
            self.key_to_id.clear()
            self._save_index()
            logger.info("Cleared semantic index.")

    def _generate_key(self, question: str) -> str:
        """Generate a deterministic key from question."""
        # Simple hash-based key (keeps backward compatibility)
        import hashlib
        return f"cache:{hashlib.md5(question.encode()).hexdigest()}"

    def _determine_ttl(
        self,
        *,
        question: str,
        response: str,
    ) -> int:
        """
        Ask the LLM how long this answer should remain cached.

        Returns seconds.
        """
        prompt = f"""
            You are deciding cache TTL for an AI response.

            Question:
            {question}

            Response:
            {response}

            Return ONLY JSON.

            Example:

            {{"ttl": 300}}

            Rules:

            - Live weather -> 5 minutes
            - Stock prices -> 1 minute
            - Sports scores -> 2 minutes
            - Breaking news -> 5 minutes
            - Flight status -> 2 minutes
            - Current traffic -> 2 minutes

            Long-lived:

            - Python programming -> 30 days
            - Educational concepts -> 30 days
            - Mathematics -> 30 days
            - History -> 365 days
            - Recipes -> 365 days
            - Algorithms -> 365 days
            - Redis documentation -> 30 days

            Choose an appropriate TTL in seconds.
            """

        try:
            result = llm_service.generate_reply(prompt)

            logger.info("TTL LLM response: %r", result)

            match = re.search(r"\{.*\}", result, re.DOTALL)

            if not match:
                raise ValueError("No JSON found in LLM response")

            ttl = int(json.loads(match.group())["ttl"])

            return self._validate_ttl(ttl)

        except Exception:
            logger.exception("Failed to determine cache TTL from LLM.")
            return DEFAULT_TTL

    @staticmethod
    def _validate_ttl(ttl: int) -> int:
        """
        Ensure TTL is within acceptable bounds.
        """
        if ttl < MIN_TTL:
            return MIN_TTL
        if ttl > MAX_TTL:
            return MAX_TTL
        return ttl

    def _save_index(self) -> None:
        """Save FAISS index and keys to disk."""
        try:
            with open(INDEX_PATH, 'wb') as f:
                pickle.dump(
                    {
                        "index": self.index,
                        "next_id": self.next_id,
                        "id_to_key": self.id_to_key,
                        "key_to_id": self.key_to_id,
                    },
                    f,
                )
            logger.info(f"Saved semantic index to {INDEX_PATH}")
        except Exception as e:
            logger.exception(f"Failed to save semantic index: {e}")

    def _load_index(self) -> None:
        """Load FAISS index and keys from disk."""
        try:
            with open(INDEX_PATH, 'rb') as f:
                data = pickle.load(f)
                self.index = data["index"]
                self.next_id = data["next_id"]
                self.id_to_key = data["id_to_key"]
                self.key_to_id = data["key_to_id"]

            logger.info(f"Loaded semantic index from {INDEX_PATH}")
        except Exception as e:
            logger.exception(f"Failed to load semantic index: {e}")
            # Re-initialize on failure
            base_index = faiss.IndexFlatIP(384)
            self.index = faiss.IndexIDMap2(base_index)


#metadata storage to track questions
class CacheMetadata:
    
    @staticmethod
    def store_question(redis_client: redis.Redis, key: str, question: str) -> None:
        """Store question for future index rebuilds."""
        try:
            redis_client.setex(
                name=f"meta:{key}",
                time=86400 * 30,  # 30 days
                value=question
            )
        except Exception as e:
            logger.exception(f"Failed to store question metadata: {e}")
    
    @staticmethod
    def get_question(redis_client: redis.Redis, key: str) -> str | None:
        """Get question from metadata."""
        try:
            return redis_client.get(f"meta:{key}")
        except Exception as e:
            logger.exception(f"Failed to get question metadata: {e}")
            return None