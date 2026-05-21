import csv
import json
import re
import os
from collections import defaultdict

def clean_rating(rating_str):
    if rating_str is None:
        return 3
    # Rating format: "Rated X out of 5 stars"
    match = re.search(r'Rated\s+(\d+)\s+out\s+of', rating_str)
    if match:
        return int(match.group(1))
    # Fallback search for any single digit
    match = re.search(r'\b([1-5])\b', rating_str)
    if match:
        return int(match.group(1))
    return 3 # Default fallback

def parse_date(date_str):
    # Strip Z or milliseconds if present
    if not date_str:
        return "2024-09-01"
    return date_str.split('T')[0]

def run_pipeline(csv_path, output_dir="data"):
    print(f"Starting NaijaAgentX data pipeline. Processing {csv_path}...")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    user_reviews = defaultdict(list)
    products_db = []
    
    # We will synthesize some rich product categories for cross-domain recommendation
    # task requirements (Task B asks for Movies, Food, Drinks, etc.)
    synthetic_domains = {
        "movies": [
            {"id": "mov_1", "title": "A Tribe Called Judah", "domain": "movies", "desc": "A hilarious Nollywood heist comedy drama about family, brotherhood, and extreme Nigerian resilience.", "avg_rating": 4.8, "tags": ["Nollywood", "Comedy", "Family", "Blockbuster"]},
            {"id": "mov_2", "title": "The Black Book", "domain": "movies", "desc": "A gritty Nollywood action thriller focusing on corruption, justice, and a father seeking vengeance for his son's murder.", "avg_rating": 4.6, "tags": ["Action", "Thriller", "Crime", "Nollywood"]},
            {"id": "mov_3", "title": "Dune: Part Two", "domain": "movies", "desc": "Epic science fiction masterpiece following Paul Atreides as he unites with the Fremen to seek revenge on the conspirators.", "avg_rating": 4.9, "tags": ["Sci-Fi", "Epic", "Adventure", "Hollywood"]},
            {"id": "mov_4", "title": "Anikulapo", "domain": "movies", "desc": "A mystical Nollywood fantasy film detailing ancient Yoruba traditions, greed, resurrection, and tragic romance.", "avg_rating": 4.5, "tags": ["Nollywood", "Drama", "Fantasy", "YorubaCulture"]}
        ],
        "food": [
            {"id": "food_1", "title": "Mega Chicken Lagos", "domain": "food", "desc": "Famous Nigerian restaurant chain serving premium Jollof Rice, smoky grilled chicken, moin-moin, and traditional soups.", "avg_rating": 4.4, "tags": ["Local", "JollofRice", "FastFood", "Lagos"]},
            {"id": "food_2", "title": "Yellow Chilli Restaurant", "domain": "food", "desc": "Sophisticated Nigerian dining experience specializing in gourmet local dishes, particularly Seafood Okra and Jollof.", "avg_rating": 4.7, "tags": ["FineDining", "Local", "SeafoodOkra", "Premium"]},
            {"id": "food_3", "title": "Glover Court Suya", "domain": "food", "desc": "The gold standard of Lagos street food. Hot, spicy, smoke-kissed beef and chicken suya seasoned with authentic yaji spice.", "avg_rating": 4.9, "tags": ["StreetFood", "Suya", "Spicy", "Nightlife"]}
        ],
        "drinks": [
            {"id": "drink_1", "title": "Zobo Premium Brew", "domain": "drinks", "desc": "Chilled, spicy hibiscus drink brewed with fresh ginger, sweet pineapple skins, cloves, and a touch of organic honey.", "avg_rating": 4.7, "tags": ["Traditional", "Organic", "NonAlcoholic", "Spicy"]},
            {"id": "drink_2", "title": "Palm Wine (Freshly Tapped)", "domain": "drinks", "desc": "Sweet, bubbly, naturally fermented Nigerian palm wine sourced directly from rural palm groves. Best served ice cold.", "avg_rating": 4.8, "tags": ["Traditional", "Alcoholic", "Organic", "Cultural"]},
            {"id": "drink_3", "title": "Chapman Classic Cocktail", "domain": "drinks", "desc": "The signature Nigerian party mocktail. A blend of Fanta, Sprite, Angostura bitters, blackcurrant cordial, and cucumber slices.", "avg_rating": 4.9, "tags": ["Cocktail", "Sweet", "NonAlcoholic", "Classic"]}
        ],
        "books": [
            {"id": "book_1", "title": "Things Fall Apart", "domain": "books", "desc": "Chinua Achebe's masterpiece detailing pre-colonial life in Igboland and the clash of cultures with British colonial administration.", "avg_rating": 4.9, "tags": ["Classic", "AfricanLiterature", "IgboCulture", "HistoricalFiction"]},
            {"id": "book_2", "title": "Half of a Yellow Sun", "domain": "books", "desc": "Chimamanda Ngozi Adichie's hauntingly beautiful epic novel detailing the Biafran War through the eyes of three characters.", "avg_rating": 4.8, "tags": ["HistoricalFiction", "WarDrama", "NollywoodAdapted", "Classic"]},
            {"id": "book_3", "title": "The Famished Road", "domain": "books", "desc": "Ben Okri's Booker Prize-winning magical realist novel following Azaro, an abiku or spirit child, living in Lagos during a time of political turmoil.", "avg_rating": 4.7, "tags": ["MagicalRealism", "Lagos", "YorubaCulture", "BookerPrize"]}
        ]
    }

    # First load actual Amazon reviews to construct user history and an Amazon products catalog
    amazon_items_map = {}
    amazon_product_counter = 1
    user_names = {}
    
    with open(csv_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            reviewer_name = (row.get("Reviewer Name") or "").strip()
            profile_link = (row.get("Profile Link") or "").strip()
            
            # Skip empty or completely dotted names/IDs
            if not profile_link and (not reviewer_name or re.match(r'^[.\s]+$', reviewer_name)):
                continue
                
            # Unique user key
            user_id = profile_link.split("/")[-1] if profile_link else reviewer_name.lower().replace(" ", "_")
            if not user_id or re.match(r'^[.\s]+$', user_id):
                continue
                
            rating = clean_rating(row.get("Rating"))
            review_text = (row.get("Review Text") or "").strip()
            review_title = (row.get("Review Title") or "").strip()
            country = (row.get("Country") or "").strip()
            review_date = parse_date(row.get("Review Date"))
            
            # Map reviewer name beautifully
            if reviewer_name and not re.match(r'^[.\s]+$', reviewer_name) and not re.match(r'^[a-fA-F0-9]{24}$', reviewer_name):
                # Format to Title Case nicely
                user_names[user_id] = reviewer_name.title()
            else:
                user_names[user_id] = f"{country or 'NG'} Customer"
                
            # Synthesize a specific product based on review keywords or simple mapping
            # This turns the trustpilot feedback into product reviews for realistic simulator inputs!
            text_lower = review_text.lower()
            if "shipping" in text_lower or "delivery" in text_lower or "driver" in text_lower:
                prod_type = "Logistics Service"
                prod_desc = "Standard Amazon shipping and home package delivery service."
            elif "prime" in text_lower or "membership" in text_lower:
                prod_type = "Amazon Prime Subscription"
                prod_desc = "Premium membership service offering free fast shipping, Prime Video, and exclusive deals."
            elif "alexa" in text_lower or "device" in text_lower or "echo" in text_lower:
                prod_type = "Echo Smart Speaker"
                prod_desc = "Voice-activated smart home assistant powered by Alexa."
            elif "card" in text_lower or "refund" in text_lower or "bank" in text_lower or "money" in text_lower:
                prod_type = "Payment & Billing Portal"
                prod_desc = "Amazon digital payment transactions, refund operations, and credit balance management."
            else:
                prod_type = "Electronics & Household Goods"
                prod_desc = "General consumer products fulfilled by third-party sellers."
                
            # Keep a neat product catalog of these synthesized Amazon items
            prod_key = prod_type.replace(" ", "_").lower()
            if prod_key not in amazon_items_map:
                amazon_items_map[prod_key] = {
                    "id": f"amzn_{amazon_product_counter}",
                    "title": prod_type,
                    "domain": "electronics",
                    "desc": prod_desc,
                    "reviews_count": 0,
                    "avg_rating": 0.0,
                    "total_stars": 0,
                    "tags": ["Amazon", "Service", "Retail"]
                }
                amazon_product_counter += 1
                
            amazon_items_map[prod_key]["reviews_count"] += 1
            amazon_items_map[prod_key]["total_stars"] += rating
            amazon_items_map[prod_key]["avg_rating"] = round(amazon_items_map[prod_key]["total_stars"] / amazon_items_map[prod_key]["reviews_count"], 2)
            
            product_id = amazon_items_map[prod_key]["id"]
            product_title = amazon_items_map[prod_key]["title"]
            
            # Save review details to the reviewer's profile
            user_reviews[user_id].append({
                "product_id": product_id,
                "product_title": product_title,
                "domain": "electronics",
                "rating": rating,
                "title": review_title,
                "text": review_text,
                "date": review_date,
                "country": country
            })

    # Prepare user profile store
    user_profiles = {}
    for user_id, reviews in user_reviews.items():
        avg_rating = sum(r["rating"] for r in reviews) / len(reviews)
        
        # Determine user traits
        rating_habit = "balanced"
        if avg_rating <= 2.0:
            rating_habit = "critical"
        elif avg_rating >= 4.0:
            rating_habit = "generous"
            
        # Determine average text length
        avg_len = sum(len(r["text"]) for r in reviews) / len(reviews)
        text_style = "concise" if avg_len < 150 else ("detailed" if avg_len > 400 else "moderate")

        display_name = user_names.get(user_id) or f"{reviews[0]['country'] or 'NG'} Customer"

        user_profiles[user_id] = {
            "user_id": user_id,
            "name": display_name,
            "country": reviews[0]["country"] or "NG",
            "avg_rating": round(avg_rating, 2),
            "rating_habit": rating_habit,
            "text_style": text_style,
            "reviews_count": len(reviews),
            "history": reviews
        }

    # Flatten and finalize products database
    products_db.extend(amazon_items_map.values())
    for domain, items in synthetic_domains.items():
        products_db.extend(items)
        
    # Save files
    with open(os.path.join(output_dir, "user_profiles.json"), "w", encoding="utf-8") as f:
        json.dump(user_profiles, f, indent=2, ensure_ascii=False)
        
    with open(os.path.join(output_dir, "products.json"), "w", encoding="utf-8") as f:
        json.dump(products_db, f, indent=2, ensure_ascii=False)
        
    print(f"Data pipeline complete. Successfully created:")
    print(f" - {len(user_profiles)} user profiles saved to 'data/user_profiles.json'")
    print(f" - {len(products_db)} products catalog saved to 'data/products.json'")

if __name__ == "__main__":
    run_pipeline("Amazon_Reviews.csv")
