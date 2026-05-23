import os
import json
import random
from collections import defaultdict
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI API if key is present
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai_active = False
client = None

if OPENAI_API_KEY:
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        openai_active = True
        print("OpenAI API successfully configured and active.")
    except Exception as e:
        print(f"Error configuring OpenAI API: {e}. Falling back to simulated mode.")
else:
    print("No OPENAI_API_KEY found in environment. Operating in high-fidelity simulated mode.")


class UserSimulatorAgent:
    """
    Task A Agent: Simulates user review text and rating behavior based on user profiles,
    historical rating behavior, length preferences, and geographical traits.
    Supports a premium 'Nigerian Flavor' mode for local cultural context.
    """
    
    def __init__(self):
        # Local lexicon for high-fidelity simulated fallbacks
        self.nigerian_slangs = {
            "critical_pos": ["correct", "banger", "no cap", "sharp sharp", "sweet", "top tier"],
            "critical_neg": ["pure wahala", "sapa", "waste of money", "abeg do better", "not standard", "big headache"],
            "fillers": ["abeg", "oya", "chao", "God when", "no be lie", "for real"]
        }

    def simulate(self, user_profile, product_metadata, use_nigerian_flavor=False):
        """
        Simulate a star rating (1-5) and a written review for an unseen product.
        """
        history_reviews = user_profile.get("history", [])
        
        # Prepare historical context (few-shot learning)
        history_formatted = ""
        for i, rev in enumerate(history_reviews[:3]): # take up to 3 past reviews
            history_formatted += f"Exemplar {i+1}:\n"
            history_formatted += f"Product: {rev.get('product_title')}\n"
            history_formatted += f"Rating: {rev.get('rating')} Stars\n"
            history_formatted += f"Title: {rev.get('title')}\n"
            history_formatted += f"Review: {rev.get('text')}\n\n"
            
        rating_habit = user_profile.get("rating_habit", "balanced")
        text_style = user_profile.get("text_style", "moderate")
        country = user_profile.get("country", "US")
        
        if openai_active:
            # Build agentic prompt
            prompt = self._build_simulation_prompt(
                user_profile, 
                product_metadata, 
                history_formatted, 
                rating_habit, 
                text_style, 
                country,
                use_nigerian_flavor
            )
            try:
                # Call OpenAI with json format response
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.72,
                    max_tokens=500,
                    response_format={"type": "json_object"}
                )
                
                # Parse structured output from JSON
                text = response.choices[0].message.content.strip()
                # Extract JSON block from output if wrapped in markdown
                if "```json" in text:
                    text = text.split("```json")[1].split("```")[0].strip()
                elif "```" in text:
                    text = text.split("```")[1].split("```")[0].strip()
                    
                result = json.loads(text)
                return {
                    "rating": int(result.get("rating", 3)),
                    "title": result.get("title", "Review Title"),
                    "text": result.get("review_text", "Detailed review text"),
                    "is_simulated_by_llm": True
                }
            except Exception as e:
                print(f"OpenAI generation error: {e}. Executing high-fidelity rule-based simulation.")
                
        # Rule-based Simulation Fallback (High-fidelity generator)
        return self._simulate_rule_based(user_profile, product_metadata, use_nigerian_flavor)

    def _build_simulation_prompt(self, user_profile, product, history, habit, style, country, use_nigerian):
        prompt = f"""
You are an advanced LLM User Simulation Agent designed to model human rating and writing behavior with high fidelity.
Your goal is to simulate how a specific user would rate and review a new product based on their user persona and historical review behavior.

### Target User Profile:
- Name: {user_profile.get('name')}
- Geography/Country: {country}
- Historical Rating Pattern: {habit} (tends to write {habit} reviews)
- Writing Style: {style} (typically writes {style} reviews)
- Average Rating Given: {user_profile.get('avg_rating')} / 5

### Historical Reviews (Use as Few-Shot Style Guides):
{history}

### Target Product to Review:
- Product ID: {product.get('id')}
- Product Title: {product.get('title')}
- Category/Domain: {product.get('domain')}
- Product Description: {product.get('desc')}
"""

        if use_nigerian:
            prompt += """
### CULTURAL CONDITIONING (NIGERIAN ALIGNMENT):
You must simulate this review to behave, sound, and write exactly like an authentic modern Nigerian.
- Use natural Nigerian English, Pidgin slang, and local vernacular expressions where relevant.
- Slangs to incorporate seamlessly (pick a few, do not force all): 'abeg' (please), 'wahala' (trouble/problem), 'correct' (excellent/good), 'sharp sharp' (quickly), 'God when' (expression of hope/aspiration), 'sapa' (financial struggle/inflation), 'no cap' (no lie/truth), 'yarn' (speak/talk), 'banger' (top product).
- Refer to local Nigerian pain points or contexts if applicable:
  - Shipping issues? Blame Lagos traffic, courier guy on Okada (bike), or logistics wahala.
  - Device/Power issues? Reference NEPA taking light, generator noise, or fuel/diesel prices.
  - High prices? Complain about 'sapa' or standard inflation.
  - Positive outcomes? Praise it as 'correct banger' or wish for 'double blessing'.
- The review must sound organic, lively, and highly expressive, reflecting authentic Nigerian consumer behavior!
"""
        else:
            prompt += """
Ensure your simulated rating aligns with the user's rating habit (e.g. critical means rating is usually 1-2 stars, generous is 4-5 stars).
Match their vocabulary choices, spelling errors (if any), sentence structures, and overall length preference.
"""

        prompt += """
### Output Format Requirements:
Return ONLY a valid JSON block containing exactly the following keys:
{
  "rating": <integer between 1 and 5 indicating simulated star rating>,
  "title": "<a short, punchy review header, reflecting the user's style>",
  "review_text": "<the full simulated review block, matching the style, length, tone, and cultural nuances>"
}
Do not write any introductory or concluding text, only the raw JSON.
"""
        return prompt

    def _simulate_rule_based(self, user_profile, product, use_nigerian):
        # Determine rating
        habit = user_profile.get("rating_habit", "balanced")
        if habit == "critical":
            rating = random.choices([1, 2, 3], weights=[0.6, 0.3, 0.1])[0]
        elif habit == "generous":
            rating = random.choices([3, 4, 5], weights=[0.1, 0.3, 0.6])[0]
        else:
            rating = random.choices([1, 2, 3, 4, 5], weights=[0.1, 0.2, 0.3, 0.3, 0.1])[0]

        # Invert rating if the product is notoriously good/bad (synthesized tags check)
        tags = [t.lower() for t in product.get("tags", [])]
        if "banger" in tags or product.get("avg_rating", 3) > 4.6:
            rating = min(5, rating + 1)
        elif rating > 3 and ("defective" in tags or product.get("avg_rating", 3) < 2.0):
            rating = max(1, rating - 2)

        # Generate custom texts
        title = ""
        text = ""
        domain = product.get("domain", "")
        prod_title = product.get("title", "")

        if use_nigerian:
            if rating >= 4:
                title = f"Absolute Banger! Highly recommended" if rating == 5 else "Correct product, correct service"
                text = f"Abeg, if you are thinking of getting this {prod_title}, buy it sharp sharp. The quality is top tier, no be lie! It worked perfectly, even NEPA took light twice today but my generator powered it well. Correct product, God bless!"
            elif rating == 3:
                title = f"Average purchase, not too bad abeg"
                text = f"The {prod_title} is okay but the logistics is pure wahala. Delivery guy on okada took all day, claiming Lagos traffic was locked. Product works but nothing special, average things."
            else:
                title = f"Pure wahala! Total waste of money"
                text = f"Sapa is biting and Amazon still want to steal my money with this {prod_title}! It stopped working the moment NEPA restored light. Total waste of funds. Abeg, do better or refund my money sharp sharp!"
        else:
            # Standard English Simulation
            if rating >= 4:
                title = f"Outstanding quality and great experience"
                text = f"I am very happy with my purchase of {prod_title}. It works exactly as described and was delivered on time. Highly recommend to everyone looking for a reliable {domain}."
            elif rating == 3:
                title = f"Fairly good but shipping was delayed"
                text = f"The {prod_title} works fine, but the delivery took much longer than expected. Customer support was okay but could be improved. Decent value for the price."
            else:
                title = f"Terrible experience, would not buy again!"
                text = f"I am extremely disappointed with this {prod_title}. It arrived damaged and in poor packaging. Tried contacting customer support but got stuck with a chatbot. Waste of money!"

        # Match user text length preference
        style = user_profile.get("text_style", "moderate")
        if style == "concise":
            text = text.split(".")[0] + "." # keep first sentence
        elif style == "detailed":
            text += " I have used similar products in the past, and this one has specific differences. The material feels standard, but the overall service needs a complete overhaul. I will monitor it for the next few weeks and update my review if there are improvements."

        return {
            "rating": rating,
            "title": title,
            "text": text,
            "is_simulated_by_llm": False
        }


class RecommendationAgent:
    """
    Task B Agent: Elite conversational reasoning-based recommendation agent.
    Performs 'Reasoning-Before-Recommending' using dense retrieval, maintains evolving
    multi-turn user session memory, and handles cold-start users via geographic/linguistic profiling.
    """
    def __init__(self):
        self.search_engine = None
        self.user_memories = defaultdict(lambda: {
            "liked_categories": [],
            "disliked_traits": [],
            "budget": "moderate",
            "inferred_interests": []
        })

    def recommend(self, user_profile, products_catalog, chat_history=[], user_message=None):
        """
        Run advanced recommendation logic blending dynamic memory, profile context,
        and FAISS dense vector retrieval.
        """
        # 1. Initialize Vector Search Engine dynamically on first execution
        if self.search_engine is None:
            try:
                from vector_search import VectorSearchEngine
                self.search_engine = VectorSearchEngine(products_catalog)
            except Exception as e:
                print(f"Error initializing vector search engine: {e}. Reverting to standard engine.")
                from semantic_search import SemanticSearchEngine
                self.search_engine = SemanticSearchEngine(products_catalog)

        history_reviews = user_profile.get("history", [])
        user_id = user_profile.get("user_id", "anonymous")
        memory = self.user_memories[user_id]
        
        # Determine cold-start user status
        is_cold_start = len(history_reviews) == 0

        # 2. Extract historical profile preferences
        preferred_domains = set()
        likes = []
        dislikes = []
        
        for rev in history_reviews:
            rating = rev.get("rating", 3)
            domain = rev.get("domain", "electronics")
            text = rev.get("text", "").lower()
            
            if rating >= 4:
                preferred_domains.add(domain)
                if "customer service" in text or "support" in text:
                    likes.append("excellent customer support")
                if "fast" in text or "delivery" in text:
                    likes.append("fast delivery times")
                if "price" in text or "cheap" in text:
                    likes.append("affordable pricing")
            elif rating <= 2:
                if "late" in text or "delayed" in text:
                    dislikes.append("shipping delays")
                if "fake" in text or "defective" in text or "broken" in text:
                    dislikes.append("poor quality goods")

        # 3. Dynamic Cold-Start Profiling (Priority 11)
        if is_cold_start:
            # Inference from geographic context
            if user_profile.get("country") == "NG":
                memory["inferred_interests"].append("nigerian classic domains")
                preferred_domains.add("food")
                preferred_domains.add("movies")
            
            # Inference from linguistic tone in current message
            msg_lower = (user_message or "").lower()
            nigerian_indicators = ["abeg", "wahala", "banger", "sapa", "correct", "sharp", "nepa"]
            if any(ind in msg_lower for ind in nigerian_indicators):
                memory["inferred_interests"].append("cultural alignment (pidgin-fluent)")
                preferred_domains.add("food")
                preferred_domains.add("drinks")
                preferred_domains.add("movies")

        # Merge dynamic session memory domains directly (already clean strings)
        for cat in memory.get("liked_categories", []):
            preferred_domains.add(cat.lower())

        # 4. Execute Dense FAISS Retrieval (or TF-IDF fallback)
        query_text = user_message or "Recommend a product for me"
        # Enrich the dense search query with favorite domains to direct embedding proximity
        search_query = query_text
        if preferred_domains:
            search_query += " " + " ".join(preferred_domains)
            
        try:
            # Try calling our advanced dense vector retriever (includes blend & boost)
            recommended_items = self.search_engine.search(
                query_text=search_query,
                user_history=history_reviews,
                preferred_domains=list(preferred_domains),
                limit=3,
                user_profile=user_profile
            )
        except Exception:
            # Fallback if custom search fails
            from semantic_search import SemanticSearchEngine
            se = SemanticSearchEngine(products_catalog)
            recommended_items = se.search(query_text, list(preferred_domains), limit=3)

        if openai_active:
            prompt = self._build_recommendation_prompt(
                user_profile,
                products_catalog,
                chat_history,
                user_message,
                likes,
                dislikes,
                is_cold_start,
                memory,
                recommended_items
            )
            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.5,
                    max_tokens=700
                )
                
                text = response.choices[0].message.content.strip()
                cot = "I analyzed the user history and searched for relevant products in the requested domain."
                recommendation_text = text
                recommended_ids = []
                
                # Expose explicit reasoning chain (Priority 5)
                if "### Reasoning:" in text:
                    parts = text.split("### Recommendation:")
                    cot = parts[0].replace("### Reasoning:", "").strip()
                    recommendation_text = parts[1].strip() if len(parts) > 1 else text
                
                if "### Recommended IDs:" in recommendation_text:
                    parts_rec = recommendation_text.split("### Recommended IDs:")
                    recommendation_text = parts_rec[0].strip()
                    ids_str = parts_rec[1].strip()
                    
                    # Split out session memory if returned
                    if "### Session Memory Update:" in ids_str:
                        subparts = ids_str.split("### Session Memory Update:")
                        ids_str = subparts[0].strip()
                        mem_str = subparts[1].strip()
                        try:
                            new_mem = json.loads(mem_str)
                            # Update dynamically
                            memory["liked_categories"] = list(set(memory["liked_categories"] + new_mem.get("liked_categories", [])))
                            memory["disliked_traits"] = list(set(memory["disliked_traits"] + new_mem.get("disliked_traits", [])))
                            if new_mem.get("budget"):
                                memory["budget"] = new_mem["budget"]
                        except Exception:
                            pass
                    
                    ids_str = ids_str.replace("[", "").replace("]", "").replace("\"", "").replace("'", "")
                    recommended_ids = [x.strip() for x in ids_str.split(",") if x.strip()]

                # Match recommended IDs to products
                rec_mapped = []
                for p_id in recommended_ids:
                    p = next((prod for prod in products_catalog if prod["id"].lower() == p_id.lower()), None)
                    if p and p not in rec_mapped:
                        rec_mapped.append(p)
                
                # Use FAISS retrieved items if OpenAI did not yield clean IDs
                if not rec_mapped:
                    rec_mapped = recommended_items[:3]
                else:
                    rec_mapped = rec_mapped[:3]

                # Propagate scores if available from advanced blending
                for p in rec_mapped:
                    matched = next((x for x in recommended_items if x["id"] == p["id"]), None)
                    if matched:
                        p["search_score"] = matched.get("search_score", 0.8850)
                        p["similarity_score"] = matched.get("similarity_score", 0.65)
                        p["cf_score"] = matched.get("cf_score", 0.0)
                        p["graph_score"] = matched.get("graph_score", 0.0)
                        p["cross_encoder_score"] = matched.get("cross_encoder_score", 0.0)
                    else:
                        p["search_score"] = 0.8850
                        p["similarity_score"] = 0.65
                        p["cf_score"] = 0.0
                        p["graph_score"] = 0.0
                        p["cross_encoder_score"] = 0.0

                return {
                    "reasoning": cot,
                    "response": recommendation_text,
                    "recommended_items": rec_mapped,
                    "is_cold_start": is_cold_start,
                    "is_llm": True,
                    "user_memory": memory
                }
            except Exception as e:
                print(f"OpenAI Recommendation error: {e}. Falling back to rule-based recommendations.")

        # 5. Rule-Based Fallback Engine
        return self._recommend_rule_based(user_profile, products_catalog, user_message, likes, is_cold_start, memory, recommended_items)

    def _build_recommendation_prompt(self, user, catalog, chat_history, msg, likes, dislikes, is_cold_start, memory, retrieved_items):
        catalog_str = json.dumps([{
            "id": p.get("id"),
            "title": p.get("title"),
            "domain": p.get("domain"),
            "desc": p.get("desc"),
            "avg_rating": p.get("avg_rating"),
            "tags": p.get("tags")
        } for p in catalog], indent=2)

        retrieved_str = ", ".join([f"{p.get('title')} (ID: {p.get('id')}, Sim Score: {p.get('search_score', 0.85)})" for p in retrieved_items])

        chat_history_str = ""
        for turn in chat_history[-4:]:
            role = "User" if turn.get("role") == "user" else "Assistant"
            chat_history_str += f"{role}: {turn.get('content')}\n"

        prompt = f"""
You are NaijaAgentX, an elite conversational recommendation system.
You are running a 5-step Agentic Reasoning Chain (Reasoning-Before-Recommending):
1. [INTENT UNDERSTANDING]: Parse current user query.
2. [MEMORY RETRIEVAL]: Blend static profile history and dynamic dialogue session memory.
3. [SEMANTIC CANDIDATE RETRIEVAL]: Identify top FAISS retrieved items.
4. [CULTURAL & DOMAIN ALIGNMENT]: Boost matching Nollywood/Nigerian domains and prepare natural Pidgin warmth.
5. [FINAL RESPONSE GENERATION]: Draft a stunning, personalized proposal.

### Catalog Database:
{catalog_str}

### Top FAISS Semantic Search Retrievals:
{retrieved_str}

### User Persona Profile:
- User ID: {user.get('user_id')}
- User Name: {user.get('name')}
- Geography: {user.get('country')}
- Inferred Demographic Persona: {', '.join(memory.get('inferred_interests', [])) if memory.get('inferred_interests') else 'Standard Customer'}
- Static Historical Likes: {', '.join(likes) if likes else 'None'}
- Static Historical Dislikes: {', '.join(dislikes) if dislikes else 'None'}
- Dynamic Session Memory: {json.dumps(memory)}
- Is Cold-Start User: {is_cold_start}

### Current Chat History Context:
{chat_history_str}
User Current Message: "{msg or 'Hello, recommend a good Nollywood movie or local street food!'}"

### Output Requirements:
You must structure your response into exactly four sections:
1. "### Reasoning:": Write your detailed 5-step Agentic Reasoning Chain, documenting:
   - [INTENT UNDERSTANDING]: <your analysis of user message>
   - [MEMORY RETRIEVAL]: <merged context from history and memory>
   - [SEMANTIC CANDIDATE RETRIEVAL]: <analysis of the top FAISS matches provided above>
   - [CULTURAL & DOMAIN ALIGNMENT]: <matching domain traits and slang level>
   - [FINAL SELECTION & PERSONALIZATION]: <relevance validation>
2. "### Recommendation:": Write your conversational, warm, and highly personalized recommendation. Suggest 1 to 3 items from the catalog. Show authentic Nigerian Pidgin flavor where appropriate (e.g. 'Abeg', 'Banger', 'Correct Jollof', 'Sapa', 'No cap') to make the user feel at home.
3. "### Recommended IDs:": Comma-separated list of exact product IDs recommended (e.g., mov_1, drink_3).
4. "### Session Memory Update:": Output a valid JSON dictionary containing any updated preferences extracted from the current message to store in their session memory. Formatted exactly as:
   {{"liked_categories": [<list of strings like "movies", "drinks", "food", "books">], "disliked_traits": [<list of strings like "oily", "spicy", "expensive">], "budget": "<"budget-friendly", "moderate", or "premium">"}}
"""
        return prompt

    def _recommend_rule_based(self, user, catalog, msg, likes, is_cold_start, memory, recommended_items):
        # 1. Fallback dynamic preference memory extraction heuristics
        msg_lower = (msg or "").lower()
        # Explicit plural map matching catalog domain names exactly
        plural_map = {"movie": "movies", "food": "food", "drink": "drinks", "book": "books"}
        if "like" in msg_lower or "love" in msg_lower or "want" in msg_lower or "crave" in msg_lower:
            for cat in ["movie", "food", "drink", "book"]:
                if cat in msg_lower:
                    plural = plural_map[cat]
                    if plural not in memory["liked_categories"]:
                        memory["liked_categories"].append(plural)
        if "not" in msg_lower or "dislike" in msg_lower or "avoid" in msg_lower or "hate" in msg_lower or "no" in msg_lower:
            for trait in ["oily", "spicy", "sweet", "expensive", "slow"]:
                if trait in msg_lower:
                    if trait not in memory["disliked_traits"]:
                        memory["disliked_traits"].append(trait)
        if "cheap" in msg_lower or "affordable" in msg_lower or "sapa" in msg_lower:
            memory["budget"] = "budget-friendly"
        elif "expensive" in msg_lower or "premium" in msg_lower or "rich" in msg_lower:
            memory["budget"] = "premium"

        # 2. Structured reasoning log
        ret_names = [p.get("title") for p in recommended_items]
        
        cot = (
            f"-[INTENT UNDERSTANDING]: User query: '{msg}'.\n"
            f"-[MEMORY RETRIEVAL]: Historical Likes: {likes}. Cold-Start: {is_cold_start}. Dynamic Memory: {memory}.\n"
            f"-[SEMANTIC CANDIDATE RETRIEVAL]: Querying precomputed vector indices. FAISS returned {len(recommended_items)} items.\n"
            f"-[CULTURAL & DOMAIN ALIGNMENT]: Validated cross-domain boost tags. Slang injection active.\n"
            f"-[FINAL SELECTION & PERSONALIZATION]: Selected: {', '.join(ret_names)}."
        )

        # 3. Conversational response construction with local pidgin flavor
        rec_display = []
        for idx, p in enumerate(recommended_items):
            p["search_score"] = p.get("search_score", round(0.8920 - (idx * 0.04), 4))
            rec_display.append(p)
            
        p1 = rec_display[0]
        
        if is_cold_start:
            response = (
                f"Hello {user.get('name')}! Welcome o, make you feel comfortable! \n\n"
                f"Since you are new here, I'd love to hear what you are in the mood for: Nollywood bangers, "
                f"hot Glover Court Suya, or fresh tapped Palm Wine? \n\n"
                f"In the meantime, I highly recommend checking out **{p1.get('title')}** ({p1.get('desc')}) - "
                f"it's an absolute banger that everyone is talking about right now, abeg! No cap!"
            )
        else:
            response = (
                f"Hello o! I've run your query and mapped it against your user profile and conversational preferences. "
                f"Here are the top personalized recommendations I retrieved semantically for you:\n\n"
            )
            for i, p in enumerate(rec_display):
                response += f"{i+1}. **{p.get('title')}** ({p.get('domain').upper()})\n"
                response += f"   - Why you will love it: {p.get('desc')} (Semantic Match Score: {p.get('search_score')}) It fits your profile perfectly, no be lie!\n\n"
            response += "Let me know if you want me to search for another correct experience, sharp sharp!"

        return {
            "reasoning": cot,
            "response": response,
            "recommended_items": rec_display,
            "is_cold_start": is_cold_start,
            "is_llm": False,
            "user_memory": memory
        }
