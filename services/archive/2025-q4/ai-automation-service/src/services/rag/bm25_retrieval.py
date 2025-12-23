"""
BM25 Keyword-Based Retrieval for Hybrid Search

Implements sparse retrieval using BM25 algorithm for keyword matching.
Complements dense retrieval (embeddings) for hybrid search.
"""

import logging
import math
import re
from collections import Counter
from typing import Any

logger = logging.getLogger(__name__)


class BM25Retriever:
    """
    BM25 (Best Matching 25) keyword-based retrieval.
    
    BM25 is a ranking function used to rank documents based on query terms.
    It's particularly good for exact name matching and handling typos.
    
    Parameters:
        k1: Term frequency saturation parameter (default: 1.5)
        b: Length normalization parameter (default: 0.75)
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        """
        Initialize BM25 retriever.
        
        Args:
            k1: Term frequency saturation parameter (higher = more weight to term frequency)
            b: Length normalization parameter (higher = more penalty for long documents)
        """
        self.k1 = k1
        self.b = b
        self.documents: list[dict[str, Any]] = []
        self.doc_freqs: dict[str, int] = {}  # Document frequency for each term
        self.idf: dict[str, float] = {}  # Inverse document frequency
        self.avg_doc_length: float = 0.0
        self._indexed = False

    def index(self, documents: list[dict[str, Any]], text_field: str = 'text'):
        """
        Index documents for BM25 retrieval.
        
        Args:
            documents: List of document dictionaries
            text_field: Field name containing text to index
        """
        self.documents = documents

        if not documents:
            self._indexed = False
            return

        # Tokenize all documents
        doc_tokens: list[list[str]] = []
        total_length = 0

        for doc in documents:
            text = doc.get(text_field, '')
            tokens = self._tokenize(text)
            doc_tokens.append(tokens)
            total_length += len(tokens)

        # Calculate average document length
        self.avg_doc_length = total_length / len(documents) if documents else 0.0

        # Calculate document frequencies
        self.doc_freqs = {}
        for tokens in doc_tokens:
            unique_tokens = set(tokens)
            for token in unique_tokens:
                self.doc_freqs[token] = self.doc_freqs.get(token, 0) + 1

        # Calculate IDF (Inverse Document Frequency)
        n_docs = len(documents)
        for token, df in self.doc_freqs.items():
            # IDF = log((N - df + 0.5) / (df + 0.5))
            # Add 0.5 for smoothing
            self.idf[token] = math.log((n_docs - df + 0.5) / (df + 0.5) + 1.0)

        self._indexed = True
        logger.debug(f"Indexed {len(documents)} documents for BM25 retrieval")

    def _tokenize(self, text: str) -> list[str]:
        """
        Tokenize text into words (lowercase, alphanumeric).
        
        Args:
            text: Text to tokenize
            
        Returns:
            List of tokens
        """
        if not text:
            return []

        # Extract words (alphanumeric sequences)
        tokens = re.findall(r'\b\w+\b', text.lower())
        return tokens

    def search(
        self,
        query: str,
        top_k: int = 10,
        min_score: float = 0.0,
        text_field: str = 'text'
    ) -> list[dict[str, Any]]:
        """
        Search documents using BM25 scoring.
        
        Args:
            query: Query text
            top_k: Number of results to return
            min_score: Minimum BM25 score threshold
            text_field: Field name containing text to search
            
        Returns:
            List of documents with BM25 scores, sorted by score (descending)
        """
        if not self._indexed or not self.documents:
            logger.warning("BM25 index not built or empty")
            return []

        # Tokenize query
        query_tokens = self._tokenize(query)

        if not query_tokens:
            return []

        # Calculate BM25 scores for each document
        scores: list[tuple] = []

        for i, doc in enumerate(self.documents):
            doc_text = doc.get(text_field, '')
            doc_tokens = self._tokenize(doc_text)
            doc_length = len(doc_tokens)

            # Calculate BM25 score
            score = 0.0

            # Count term frequencies in document
            term_freqs = Counter(doc_tokens)

            for token in query_tokens:
                if token not in self.idf:
                    continue  # Skip tokens not in vocabulary

                tf = term_freqs.get(token, 0)
                if tf == 0:
                    continue

                # BM25 formula:
                # score = IDF * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * (doc_length / avg_doc_length)))
                idf = self.idf[token]
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * (doc_length / self.avg_doc_length))
                score += idf * (numerator / denominator)

            if score >= min_score:
                scores.append((score, i))

        # Sort by score (descending) and return top_k
        scores.sort(key=lambda x: x[0], reverse=True)

        results = []
        for score, doc_idx in scores[:top_k]:
            doc = self.documents[doc_idx].copy()
            doc['bm25_score'] = float(score)
            results.append(doc)

        logger.debug(f"BM25 search returned {len(results)} results for query: {query[:50]}...")
        return results

    def search_hybrid(
        self,
        query: str,
        dense_results: list[dict[str, Any]],
        top_k: int = 10,
        dense_weight: float = 0.6,
        sparse_weight: float = 0.4,
        text_field: str = 'text'
    ) -> list[dict[str, Any]]:
        """
        Hybrid search combining dense (embedding) and sparse (BM25) results.
        
        Args:
            query: Query text
            dense_results: Results from dense retrieval (with 'similarity' scores)
            top_k: Number of results to return
            dense_weight: Weight for dense retrieval scores (default: 0.6)
            sparse_weight: Weight for sparse retrieval scores (default: 0.4)
            text_field: Field name containing text
            
        Returns:
            Combined and reranked results
        """
        if not dense_results:
            return []

        # Get BM25 scores for dense results
        sparse_results = self.search(query, top_k=len(dense_results) * 2, text_field=text_field)

        # Create score lookup for sparse results
        sparse_scores: dict[str, float] = {}
        for result in sparse_results:
            # Use text as key (or id if available)
            key = result.get('id') or result.get(text_field, '')
            sparse_scores[key] = result.get('bm25_score', 0.0)

        # Normalize scores to [0, 1] range
        max_dense_score = max((r.get('similarity', 0.0) for r in dense_results), default=1.0)
        max_sparse_score = max((r.get('bm25_score', 0.0) for r in sparse_results), default=1.0)

        # Combine scores
        combined_results = []
        seen_ids = set()

        # Process dense results
        for result in dense_results:
            result_id = result.get('id') or result.get(text_field, '')
            dense_score = result.get('similarity', 0.0)
            sparse_score = sparse_scores.get(result_id, 0.0)

            # Normalize scores
            norm_dense = dense_score / max_dense_score if max_dense_score > 0 else 0.0
            norm_sparse = sparse_score / max_sparse_score if max_sparse_score > 0 else 0.0

            # Weighted combination
            combined_score = (dense_weight * norm_dense) + (sparse_weight * norm_sparse)

            combined_result = result.copy()
            combined_result['hybrid_score'] = combined_score
            combined_result['bm25_score'] = sparse_score
            combined_results.append(combined_result)
            seen_ids.add(result_id)

        # Add sparse-only results (if any)
        for result in sparse_results:
            result_id = result.get('id') or result.get(text_field, '')
            if result_id not in seen_ids:
                sparse_score = result.get('bm25_score', 0.0)
                norm_sparse = sparse_score / max_sparse_score if max_sparse_score > 0 else 0.0

                combined_result = result.copy()
                combined_result['hybrid_score'] = sparse_weight * norm_sparse
                combined_result['similarity'] = 0.0  # No dense score
                combined_results.append(combined_result)

        # Sort by hybrid score and return top_k
        combined_results.sort(key=lambda x: x.get('hybrid_score', 0.0), reverse=True)

        logger.debug(
            f"Hybrid search: {len(dense_results)} dense + {len(sparse_results)} sparse → "
            f"{len(combined_results)} combined results"
        )

        return combined_results[:top_k]

