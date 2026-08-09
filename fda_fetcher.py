import requests
import urllib.parse
from cache_manager import cache_get, cache_set
from config import FDA_BASE
import time

def fetch_drug_from_fda(drug_name):
    if not drug_name or not drug_name.strip():
        return {}
    cache_key = f"fda_{drug_name.strip()[:40]}"
    cached = cache_get(cache_key)
    if cached:
        return cached
    encoded = urllib.parse.quote(drug_name.strip(), safe="")
    url = f"{FDA_BASE}/drug/label.json"
    for field in [
        "openfda.brand_name",
        "openfda.generic_name",
        "openfda.substance_name"
    ]:
        params = {"search": f'{field}:"{encoded}"', "limit": 1}
        try:
            r = requests.get(url, params=params, timeout=15)
            if r.status_code == 200:
                results = r.json().get("results", [])
                if results:
                    res = results[0]
                    data = {
                        "found": True,
                        "warnings": (
                            res.get("warnings", [""])[0][:500]
                            if res.get("warnings") else ""
                        ),
                        "interactions": (
                            res.get("drug_interactions", [""])[0][:500]
                            if res.get("drug_interactions") else ""
                        ),
                        "food_warnings": (
                            res.get("food_drug_interactions", [""])[0][:300]
                            if res.get("food_drug_interactions") else ""
                        )
                    }
                    cache_set(cache_key, data)
                    return data
            time.sleep(0.3)
        except Exception:
            pass
    return {"found": False}