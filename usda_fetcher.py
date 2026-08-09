import requests
import re
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from cache_manager import cache_get, cache_set
from utils import usda_limiter
from config import USDA_BASE, USDA_API_KEY

def _matches(nutrient_name, target):
    if not nutrient_name or not target:
        return False
    t = re.escape(target.lower())
    # Handle hyphens in targets like omega-3
    pattern = r'(?:^|\s|,)' + t + r'(?:\s|,|$)'
    return bool(re.search(pattern, nutrient_name.lower()))

def fetch_foods_for_nutrients(nutrient_list, max_per=15):
    all_rows = []
    for nutrient in nutrient_list:
        if not nutrient or len(str(nutrient)) < 3:
            continue
        cache_key = f"usda_{str(nutrient)[:40]}"
        cached = cache_get(cache_key)
        if cached:
            all_rows.extend(cached)
            continue
        usda_limiter.wait()
        params = {
            "query": f"high {nutrient}",
            "api_key": USDA_API_KEY,
            "pageSize": max_per,
            "dataType": ["Foundation", "SR Legacy"]
        }
        try:
            r = requests.get(
                f"{USDA_BASE}/foods/search",
                params=params, timeout=30
            )
            r.raise_for_status()
            foods = r.json().get("foods", [])
            rows = []
            for food in foods:
                for nut in food.get("foodNutrients", []):
                    nut_name = nut.get("nutrientName", "")
                    if _matches(nut_name, str(nutrient)):
                        rows.append({
                            "food_name": food.get("description", ""),
                            "category": food.get("foodCategory", ""),
                            "target_nutrient": nutrient,
                            "amount": nut.get("value", 0),
                            "unit": nut.get("unitName", "")
                        })
            cache_set(cache_key, rows)
            all_rows.extend(rows)
        except Exception as e:
            print(f"[USDA] Error for {nutrient}: {e}")
    df = pd.DataFrame(all_rows)
    if df.empty:
        return df
    return df[df["amount"] > 0].dropna(subset=["amount","food_name"])

def rank_foods_by_nutrients(df, nutrient_list):
    if df.empty:
        return pd.DataFrame()
    try:
        pivot = df.pivot_table(
            index="food_name",
            columns="target_nutrient",
            values="amount",
            aggfunc="mean"
        ).fillna(0)
        if pivot.empty or pivot.shape[1] == 0:
            return pd.DataFrame()
        scaler = MinMaxScaler()
        scaled = pd.DataFrame(
            scaler.fit_transform(pivot),
            index=pivot.index,
            columns=pivot.columns
        )
        scaled["composite_score"] = scaled.mean(axis=1)
        return scaled[["composite_score"]].sort_values(
            by="composite_score", ascending=False
        ).reset_index()
    except Exception as e:
        print(f"[Rank] Error: {e}")
        return pd.DataFrame()

def fetch_food_openfoodfacts(food_name):
    cache_key = f"off_{food_name[:30]}"
    cached = cache_get(cache_key)
    if cached:
        return cached
    try:
        url = "https://world.openfoodfacts.org/cgi/search.pl"
        params = {
            "search_terms": food_name,
            "search_simple": 1,
            "action": "process",
            "json": 1, "page_size": 3
        }
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        products = r.json().get("products", [])
        if products:
            p = products[0]
            n = p.get("nutriments", {})
            result = {
                "name": p.get("product_name",""),
                "calories": n.get("energy-kcal_100g","N/A"),
                "protein": n.get("proteins_100g","N/A"),
                "fiber": n.get("fiber_100g","N/A"),
                "sodium": n.get("sodium_100g","N/A"),
                "nutriscore": p.get("nutriscore_grade","N/A")
            }
            cache_set(cache_key, result)
            return result
    except Exception:
        pass
    return {}