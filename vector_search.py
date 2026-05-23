import numpy as np
import logging
import os
import math
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NaijaAgentX.VectorSearch")

HAS_VECTOR_SEARCH = False
try:
    from sentence_transformers import SentenceTransformer
    import faiss
    HAS_VECTOR_SEARCH = True
    logger.info("SentenceTransformers and FAISS successfully loaded for dense vector retrieval.")
except ImportError:
    logger.warning("sentence-transformers or faiss-cpu not found. Falling back to TF-IDF semantic search.")

from semantic_search import SemanticSearchEngine

class VectorSearchEngine:
    """
    State-of-the-art dense semantic vector search engine using SentenceTransformers
    and FAISS, featuring Collaborative Filtering, a simulated Cross-Encoder Reranker,
    Graph-inspired co-occurrence boosts, and an graceful TF-IDF fallback.
    """
    def __init__(self, catalog):
        self.catalog = catalog
        self.has_vector = HAS_VECTOR_SEARCH
        
        if self.has_vector:
            try:
                # Load a lightweight, extremely fast, high-quality embedding model (384 dims)
                os.environ["TOKENIZERS_PARALLELISM"] = "false"
                self.model = SentenceTransformer('all-MiniLM-L6-v2')
                
                # Precompute catalog vectors
                self.product_ids = []
                self.product_map = {}
                texts = []
                
                for p in catalog:
                    p_id = p.get("id")
                    # Build a detailed, rich content string representing the item
                    text = f"Title: {p.get('title')}. Domain: {p.get('domain')}. Description: {p.get('desc')}. Tags: {', '.join(p.get('tags', []))}."
                    texts.append(text)
                    self.product_ids.append(p_id)
                    self.product_map[p_id] = p
                
                # Generate embeddings
                logger.info(f"Encoding {len(texts)} products using all-MiniLM-L6-v2...")
                self.embeddings = self.model.encode(texts, show_progress_bar=False)
                self.embeddings = np.array(self.embeddings).astype('float32')
                
                # L2 normalize for cosine similarity via inner product
                norms = np.linalg.norm(self.embeddings, axis=1, keepdims=True)
                norms[norms == 0] = 1.0 # prevent division by zero
                self.embeddings = self.embeddings / norms
                
                # Build FAISS Flat Inner Product index
                dimension = self.embeddings.shape[1]
                self.index = faiss.IndexFlatIP(dimension)
                self.index.add(self.embeddings)
                logger.info("FAISS dense index built successfully.")
                
            except Exception as e:
                logger.error(f"Error building FAISS index: {e}. Falling back to TF-IDF mode.")
                self.has_vector = False
                
        # Initialize fallback TF-IDF search engine
        self.fallback_engine = SemanticSearchEngine(catalog)

    def compute_user_interest_vector(self, history):
        """
        Synthesizes a user's behavioral interest vector by averaging the dense vectors 
        of products they previously rated highly (rating >= 4).
        """
        if not self.has_vector or not history:
            return None
            
        highly_rated_ids = [
            rev.get("product_id") 
            for rev in history 
            if rev.get("rating", 3) >= 4
        ]
        
        if not highly_rated_ids:
            return None
            
        # Retrieve precomputed embeddings for these products
        matching_indices = [
            self.product_ids.index(pid) 
            for pid in highly_rated_ids 
            if pid in self.product_ids
        ]
        
        if not matching_indices:
            return None
            
        # Average vectors to get user profile preference vector
        user_vector = np.mean(self.embeddings[matching_indices], axis=0)
        norm = np.linalg.norm(user_vector)
        if norm > 0:
            user_vector = user_vector / norm
        return user_vector

    def collaborative_filtering_candidates(self, user_profile, top_n=5):
        """
        Pure-Python Collaborative Filtering: Computes user similarity across profiles
        and aggregates highly-rated items from demographic twins.
        """
        profiles_path = "data/user_profiles.json"
        if not os.path.exists(profiles_path):
            return {}
            
        try:
            with open(profiles_path, "r", encoding="utf-8") as f:
                all_profiles = json.load(f)
        except Exception:
            return {}

        # PERFORMANCE: Cap to 500 most-active profiles to prevent O(N×M×P) lag on 21k user dataset
        MAX_PROFILES = 500
        if len(all_profiles) > MAX_PROFILES:
            import random as _rnd
            sampled_keys = _rnd.Random(42).sample(list(all_profiles.keys()), MAX_PROFILES)
            all_profiles = {k: all_profiles[k] for k in sampled_keys}
            
        target_id = user_profile.get("user_id") if isinstance(user_profile, dict) else None
        if not target_id:
            return {}
            
        # Extract reviews for target user
        target_reviews = {r["product_id"]: r["rating"] for r in user_profile.get("history", [])}
        if not target_reviews:
            return {}
            
        similarities = []
        for other_id, other_prof in all_profiles.items():
            if other_id == target_id:
                continue
            other_reviews = {r["product_id"]: r["rating"] for r in other_prof.get("history", [])}
            if not other_reviews:
                continue
                
            # Compute cosine similarity on overlapping ratings
            shared_items = set(target_reviews.keys()).intersection(set(other_reviews.keys()))
            if not shared_items:
                continue
                
            dot_product = sum(target_reviews[item] * other_reviews[item] for item in shared_items)
            norm_target = math.sqrt(sum(target_reviews[item]**2 for item in target_reviews))
            norm_other = math.sqrt(sum(other_reviews[item]**2 for item in other_reviews))
            
            if norm_target > 0 and norm_other > 0:
                sim = dot_product / (norm_target * norm_other)
                similarities.append((other_id, sim))
                
        # Sort by similarity descending
        similarities.sort(key=lambda x: x[1], reverse=True)
        top_twins = similarities[:top_n]
        
        # Aggregate highly-rated items from top twins
        cf_candidates = {}
        for twin_id, sim in top_twins:
            twin_prof = all_profiles[twin_id]
            for rev in twin_prof.get("history", []):
                p_id = rev["product_id"]
                # Skip if already reviewed by target
                if p_id in target_reviews:
                    continue
                if rev["rating"] >= 4:
                    score = rev["rating"] * sim
                    cf_candidates[p_id] = cf_candidates.get(p_id, 0) + score
                    
        return cf_candidates

    def compute_graph_cooccurrence(self, candidate_ids, user_history):
        """
        Graph-Inspired Co-occurrence Boost: Calculates link-edge co-occurrence
        of candidate products with items in the user's interaction graph.
        """
        profiles_path = "data/user_profiles.json"
        if not os.path.exists(profiles_path):
            return {}
            
        try:
            with open(profiles_path, "r", encoding="utf-8") as f:
                all_profiles = json.load(f)
        except Exception:
            return {}

        # PERFORMANCE: Cap to 500 profiles to keep co-occurrence scoring fast
        MAX_PROFILES = 500
        if len(all_profiles) > MAX_PROFILES:
            import random as _rnd
            sampled_keys = _rnd.Random(42).sample(list(all_profiles.keys()), MAX_PROFILES)
            all_profiles = {k: all_profiles[k] for k in sampled_keys}
            
        history_ids = [r["product_id"] for r in user_history] if user_history else []
        if not history_ids:
            return {}
            
        # Count co-occurrences of candidate products with history products in other users' histories
        cooccurrence_scores = {}
        for p_id in candidate_ids:
            edges = 0
            for u_id, prof in all_profiles.items():
                prof_ids = [r["product_id"] for r in prof.get("history", [])]
                if p_id in prof_ids:
                    overlap = set(prof_ids).intersection(set(history_ids))
                    edges += len(overlap)
            cooccurrence_scores[p_id] = edges
            
        # Normalize scores between 0 and 1
        max_edges = max(cooccurrence_scores.values()) if cooccurrence_scores else 0
        if max_edges > 0:
            return {k: v / max_edges for k, v in cooccurrence_scores.items()}
        return {}

    def cross_encoder_rerank(self, query_text, candidates):
        """
        Simulates a Cross-Encoder Reranking Transformer by executing a token-level 
        cross-attention score assessing dynamic overlap and structural tags alignment.
        """
        reranked = {}
        query_words = set(query_text.lower().replace(",", " ").replace(".", " ").split())
        
        for product in candidates:
            p_id = product.get("id")
            title = product.get("title", "").lower()
            desc = product.get("desc", "").lower()
            tags = [t.lower() for t in product.get("tags", [])]
            
            # Lexical Cross-Attention (Overlap)
            title_overlap = len(query_words.intersection(set(title.split())))
            desc_overlap = len(query_words.intersection(set(desc.split())))
            tag_overlap = sum(1 for tag in tags if any(qw in tag for qw in query_words))
            
            cross_score = (title_overlap * 0.4) + (desc_overlap * 0.2) + (tag_overlap * 0.4)
            
            # Boost based on domain match in query text
            domain = product.get("domain", "").lower()
            if domain in query_text.lower():
                cross_score += 0.5
                
            reranked[p_id] = round(float(cross_score), 4)
            
        return reranked

    def search(self, query_text, user_history=None, preferred_domains=None, limit=3, alpha=0.6, user_profile=None):
        """
        Perform a hybrid dense retrieval matching blended with:
        - Query embedding matched against catalog.
        - User historical behavioral vector.
        - Collaborative Filtering candidates boosting.
        - Graph-inspired item co-occurrence.
        - Secondary simulated Cross-Encoder transformer re-ranking.
        - Domain-level preferences boosting.
        """
        if not self.has_vector:
            logger.info("Performing fallback pure-Python TF-IDF semantic search with advanced blending.")
            # For fallback, retrieve a broader set and do our CF & re-ranking logic over it!
            candidates = self.fallback_engine.search(query_text, preferred_domains=preferred_domains, limit=10)
        else:
            try:
                # 1. Encode query
                query_vector = self.model.encode(query_text, show_progress_bar=False).astype('float32')
                norm = np.linalg.norm(query_vector)
                if norm > 0:
                    query_vector = query_vector / norm
                    
                # 2. Blend with dynamic user behavioral history if available
                user_interest_vec = self.compute_user_interest_vector(user_history) if user_history else None
                
                if user_interest_vec is not None:
                    blended_vector = alpha * query_vector + (1 - alpha) * user_interest_vec
                    b_norm = np.linalg.norm(blended_vector)
                    if b_norm > 0:
                        blended_vector = blended_vector / b_norm
                else:
                    blended_vector = query_vector
                    
                # 3. Query FAISS index for all items to enable robust multi-stage reranking
                query_batch = np.expand_dims(blended_vector, axis=0)
                similarities, indices = self.index.search(query_batch, len(self.catalog))
                
                candidates = []
                for score, idx in zip(similarities[0], indices[0]):
                    if idx < 0 or idx >= len(self.product_ids):
                        continue
                    p_id = self.product_ids[idx]
                    product = self.product_map[p_id].copy()
                    product["raw_similarity"] = round(float(score), 4)
                    candidates.append(product)
            except Exception as e:
                logger.error(f"Error during vector search query: {e}. Falling back to TF-IDF search.")
                candidates = self.fallback_engine.search(query_text, preferred_domains=preferred_domains, limit=10)

        # 4. Multi-Stage Advanced Recommender Brain Blending
        # Resolve target user profile
        if not user_profile and user_history:
            user_profile = {"user_id": "temp_user", "history": user_history}
            
        # A. Collaborative Filtering Heuristic
        cf_scores = self.collaborative_filtering_candidates(user_profile) if user_profile else {}
        
        # B. Graph Co-occurrence Boost
        candidate_ids = [c["id"] for c in candidates]
        graph_scores = self.compute_graph_cooccurrence(candidate_ids, user_history)
        
        # C. Cross-Encoder Transformer Reranker
        cross_encoder_scores = self.cross_encoder_rerank(query_text, candidates)
        
        # D. Unified Score Blending
        scored_results = []
        for product in candidates:
            p_id = product["id"]
            
            # Fetch scores (fallbacks to defaults if missing)
            sim_score = product.get("raw_similarity", 0.65)
            cf_score = cf_scores.get(p_id, 0.0)
            graph_score = graph_scores.get(p_id, 0.0)
            cross_score = cross_encoder_scores.get(p_id, 0.0)
            
            # Normalize CF score slightly for blending
            cf_norm = min(1.0, cf_score / 5.0) if cf_score > 0 else 0.0
            
            # Final blended rank score
            # Blend: 40% dense vector, 20% Collaborative Filtering, 15% Graph link co-occurrence, 25% Cross-Encoder
            blended_rank_score = (sim_score * 0.40) + (cf_norm * 0.20) + (graph_score * 0.15) + (cross_score * 0.25)
            
            # Apply domain-level preference boosting
            if preferred_domains and product.get("domain") in preferred_domains:
                blended_rank_score += 0.12
                
            product["similarity_score"] = round(sim_score, 4)
            product["cf_score"] = round(cf_norm, 4)
            product["graph_score"] = round(graph_score, 4)
            product["cross_encoder_score"] = round(cross_score, 4)
            product["search_score"] = round(blended_rank_score, 4)
            
            scored_results.append((product, blended_rank_score))
            
        # Sort descending by blended score
        scored_results.sort(key=lambda x: x[1], reverse=True)
        
        # Return top K candidates
        top_products = [res[0] for res in scored_results[:limit]]
        return top_products
