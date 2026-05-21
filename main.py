import os
import json
import random
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
from agents import UserSimulatorAgent, RecommendationAgent

app = FastAPI(
    title="NaijaAgentX - DSN x BCT LLM Agent Platform",
    description="Culturally Nuanced User Modeling & Intelligent Recommendation",
    version="1.0.0"
)

# Load data helper
DATA_DIR = "data"
user_profiles = {}
products_catalog = []
ablation_results = {}

def load_data():
    global user_profiles, products_catalog, ablation_results
    
    # Create DATA_DIR if missing
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        
    db_missing = not os.path.exists(os.path.join(DATA_DIR, "user_profiles.json")) or not os.path.exists(os.path.join(DATA_DIR, "products.json"))
    if db_missing:
        print("Data files not found. Running data pipeline automatically...")
        try:
            import data_pipeline
            csv_path = "Amazon_Reviews.csv"
            if os.path.exists(csv_path):
                data_pipeline.run_pipeline(csv_path, output_dir=DATA_DIR)
            else:
                print(f"Warning: {csv_path} not found. Cannot run pipeline.")
        except Exception as ex:
            print(f"Error running data pipeline on startup: {ex}")
            
    ablation_missing = not os.path.exists(os.path.join(DATA_DIR, "ablation_results.json"))
    if ablation_missing:
        print("Ablation results not found. Running evaluator automatically...")
        try:
            import evaluator
            evaluator.run_evaluation(num_samples=10, output_file=os.path.join(DATA_DIR, "ablation_results.json"))
        except Exception as ex:
            print(f"Error running evaluator on startup: {ex}")

    try:
        with open(os.path.join(DATA_DIR, "user_profiles.json"), "r", encoding="utf-8") as f:
            user_profiles = json.load(f)
        with open(os.path.join(DATA_DIR, "products.json"), "r", encoding="utf-8") as f:
            products_catalog = json.load(f)
        with open(os.path.join(DATA_DIR, "ablation_results.json"), "r", encoding="utf-8") as f:
            ablation_results = json.load(f)
        print("Data stores loaded successfully.")
    except Exception as e:
        print(f"Error loading data stores: {e}.")

# Run initial load
load_data()

# Instantiate agents
simulator_agent = UserSimulatorAgent()
recommendation_agent = RecommendationAgent()

# Custom input sub-schemas
class ReviewHistoryItem(BaseModel):
    product_id: str
    product_title: str
    domain: str
    rating: int
    title: str
    text: str
    date: Optional[str] = None
    country: Optional[str] = None

class UserPersonaSchema(BaseModel):
    user_id: Optional[str] = None
    name: str
    country: str
    avg_rating: float
    rating_habit: str # 'generous', 'critical', 'balanced'
    text_style: str # 'concise', 'moderate', 'detailed'
    history: List[ReviewHistoryItem] = []

class ProductDetailsSchema(BaseModel):
    id: str
    title: str
    domain: str
    desc: str
    tags: List[str] = []

# Updated request schemas
class SimulationRequest(BaseModel):
    user_id: Optional[str] = None
    user_persona: Optional[UserPersonaSchema] = None
    product_id: Optional[str] = None
    product_details: Optional[ProductDetailsSchema] = None
    use_nigerian_flavor: bool = False

class ChatMessage(BaseModel):
    role: str # 'user' or 'assistant'
    content: str

class RecommendationRequest(BaseModel):
    user_id: Optional[str] = None
    user_persona: Optional[UserPersonaSchema] = None
    message: Optional[str] = None
    chat_history: List[ChatMessage] = []

@app.on_event("startup")
def startup_event():
    load_data()

@app.get("/api/users")
def get_users(limit: int = 100):
    """
    Returns a selected list of users, prioritizing active ones with reviews.
    """
    if not user_profiles:
        return []
    # Sort active users to let the user choose interesting personas
    sorted_users = sorted(
        user_profiles.values(), 
        key=lambda u: (u.get("reviews_count", 0), u.get("avg_rating", 3)),
        reverse=True
    )
    return sorted_users[:limit]

@app.get("/api/products")
def get_products():
    """
    Returns all product domains.
    """
    return products_catalog

@app.get("/api/ablation")
def get_ablation():
    """
    Returns the ablation experiment metrics.
    """
    return ablation_results

@app.post("/api/simulate")
def post_simulate(req: SimulationRequest):
    """
    Task 1: Simulates user reviews and star rating behavior.
    Supports either database ID lookups or complete custom user/product JSON objects.
    """
    # 1. Resolve user persona
    if req.user_persona:
        user = req.user_persona.dict()
        user["history"] = [h.dict() for h in req.user_persona.history]
    elif req.user_id:
        user = user_profiles.get(req.user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User profile not found in database")
    else:
        raise HTTPException(status_code=400, detail="Either user_id or user_persona must be provided")
        
    # 2. Resolve product details
    if req.product_details:
        product = req.product_details.dict()
    elif req.product_id:
        product = next((p for p in products_catalog if p["id"] == req.product_id), None)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found in database")
    else:
        raise HTTPException(status_code=400, detail="Either product_id or product_details must be provided")

    try:
        result = simulator_agent.simulate(user, product, req.use_nigerian_flavor)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/recommend")
def post_recommend(req: RecommendationRequest):
    """
    Task 2: Intelligent Reasoning Recommendation Engine.
    Supports either database ID lookups or complete custom user JSON objects.
    """
    # 1. Resolve user persona
    if req.user_persona:
        user = req.user_persona.dict()
        user["history"] = [h.dict() for h in req.user_persona.history]
    elif req.user_id:
        user = user_profiles.get(req.user_id)
        if not user:
            # Default fallback context for unknown cold-start users
            user = {
                "user_id": req.user_id,
                "name": "Cold Start User",
                "country": "NG",
                "avg_rating": 5.0,
                "rating_habit": "generous",
                "text_style": "moderate",
                "history": []
            }
    else:
        user = {
            "user_id": "new_user",
            "name": "Cold Start User",
            "country": "NG",
            "avg_rating": 5.0,
            "rating_habit": "generous",
            "text_style": "moderate",
            "history": []
        }

    try:
        history_list = [{"role": t.role, "content": t.content} for t in req.chat_history]
        result = recommendation_agent.recommend(
            user, 
            products_catalog, 
            chat_history=history_list, 
            user_message=req.message
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class PersonalizeRequest(BaseModel):
    user_id: str
    product_id: str
    action: str # 'like' or 'dislike'

@app.post("/api/personalize")
def post_personalize(req: PersonalizeRequest):
    """
    Endpoint for active personalization learning loop. Dynamically record user 
    upvotes/downvotes, updating session memory weights in real-time.
    """
    user_id = req.user_id or "anonymous"
    prod = next((p for p in products_catalog if p["id"] == req.product_id), None)
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found")
        
    memory = recommendation_agent.user_memories[user_id]
    domain = prod.get("domain", "")
    
    if req.action == "like":
        if domain and domain not in memory["liked_categories"]:
            memory["liked_categories"].append(domain)
        # Remove matching tags from dislikes
        for tag in prod.get("tags", []):
            if tag in memory["disliked_traits"]:
                memory["disliked_traits"].remove(tag)
    elif req.action == "dislike":
        for tag in prod.get("tags", []):
            if tag not in memory["disliked_traits"]:
                memory["disliked_traits"].append(tag)
        if domain in memory["liked_categories"]:
            memory["liked_categories"].remove(domain)
            
    return {"status": "success", "user_memory": memory}

@app.get("/api/human_eval")
def get_human_eval():
    """
    Returns the human study evaluation statistics.
    """
    path = os.path.join(DATA_DIR, "human_eval_results.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"status": "missing", "detail": "Human evaluation results not found. Run evaluator.py first."}

# Serve static files from React build assets
try:
    app.mount("/assets", StaticFiles(directory="dist/assets", check_dir=False), name="assets")
except Exception as e:
    print(f"Warning: could not mount assets directory: {e}")

@app.get("/")
def get_index():
    """
    Serve the main premium Web Dashboard page.
    """
    # Try serving compiled React app first
    react_index = "dist/index.html"
    if os.path.exists(react_index):
        return FileResponse(react_index)
        
    # Fallback to serving the backup index.html
    fallback_path = "index.html.bak"
    if os.path.exists(fallback_path):
        with open(fallback_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), status_code=200)
            
    return HTMLResponse(content="<h1>NaijaAgentX UI Loading... Please run npm run build!</h1>", status_code=200)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
