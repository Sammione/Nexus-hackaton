import math
import re
from collections import Counter

class SemanticSearchEngine:
    """
    A pure Python, zero-dependency Semantic Search and RAG matching engine.
    Computes term frequency-inverse document frequency (TF-IDF) and cosine
    similarity to perform highly accurate semantic product retrieval.
    """
    
    def __init__(self, catalog):
        self.catalog = catalog
        self.documents = []
        self.product_map = {}
        
        # Build text representation for each product
        for p in catalog:
            p_id = p.get("id")
            # Concatenate fields to build rich metadata documents
            text = f"{p.get('title')} {p.get('domain')} {p.get('desc')} {' '.join(p.get('tags', []))}"
            self.product_map[p_id] = {
                "product": p,
                "tokens": self._tokenize(text)
            }
            self.documents.append(self.product_map[p_id]["tokens"])
            
        # Fit IDF across the whole catalog
        self.idf = self._compute_idf(self.documents)
        
        # Precompute TF-IDF vectors for all products in catalog
        for p_id, item in self.product_map.items():
            item["vector"] = self._compute_tfidf(item["tokens"], self.idf)

    def _tokenize(self, text):
        # Convert to lowercase and find word tokens
        return re.findall(r'\b[a-zA-Z0-9_]{2,}\b', (text or "").lower())

    def _compute_tf(self, tokens):
        tf = Counter(tokens)
        num_tokens = len(tokens)
        if num_tokens == 0:
            return {}
        return {word: count / num_tokens for word, count in tf.items()}

    def _compute_idf(self, documents):
        n = len(documents)
        idf = {}
        if n == 0:
            return idf
        all_words = set(word for doc in documents for word in doc)
        for word in all_words:
            # Count documents containing this word
            doc_count = sum(1 for doc in documents if word in doc)
            # Standard smoothed IDF formula to prevent division-by-zero
            idf[word] = math.log((1 + n) / (1 + doc_count)) + 1
        return idf

    def _compute_tfidf(self, tokens, idf):
        tf = self._compute_tf(tokens)
        return {word: tf_val * idf.get(word, 0.0) for word, tf_val in tf.items()}

    def _cosine_similarity(self, v1, v2):
        common_words = set(v1.keys()) & set(v2.keys())
        dot_product = sum(v1[w] * v2[w] for w in common_words)
        
        mag1 = math.sqrt(sum(val ** 2 for val in v1.values()))
        mag2 = math.sqrt(sum(val ** 2 for val in v2.values()))
        
        if mag1 == 0.0 or mag2 == 0.0:
            return 0.0
        return dot_product / (mag1 * mag2)

    def search(self, query_text, preferred_domains=None, limit=3, **kwargs):
        """
        Rank catalog items based on cosine similarity to the query.
        Boosts items if they match the user's historical preferred domains.
        """
        query_tokens = self._tokenize(query_text)
        query_vector = self._compute_tfidf(query_tokens, self.idf)
        
        results = []
        for p_id, item in self.product_map.items():
            product = item["product"]
            prod_vector = item["vector"]
            
            # Base semantic score
            score = self._cosine_similarity(query_vector, prod_vector)
            
            # Boost score if the product domain is in the user's historical preferences
            if preferred_domains and product.get("domain") in preferred_domains:
                # Add a gentle additive boost to prioritize matching domains semantically
                score += 0.15
                
            results.append((product, score))
            
        # Sort by similarity score in descending order
        results.sort(key=lambda x: x[1], reverse=True)
        
        # Return top ranked products
        return [res[0] for res in results[:limit]]
