import os
import json
import time
import shodan
import requests

def search_intelx(term):
    results = []
    try:
        INTELX_API_KEY = os.environ.get("INTELX_API_KEY")
        h = {"x-key": INTELX_API_KEY}
        p = {
            "term": term,
            "buckets": [],
            "lookuplevel": 0,
            "maxresults": 100,
            "timeout": 5,
            "datefrom": "",
            "dateto": "",
            "sort": 4,
            "media": 0,
            "terminate": [],
        }
        r = requests.post("https://2.intelx.io/intelligent/search", headers=h, json=p)
        search_id = r.json()["id"]
        r = requests.get(f"https://2.intelx.io/intelligent/search/result?id={search_id}&limit=20", headers=h)
        for record in r.json()["records"]:
            result = {}
            result["added"] = record["added"]
            result["name"] = record["name"]
            result["tags"] = record["tags"]
            result["data_source"] = record["bucketh"]
            result["type"] = record["typeh"]
            results.append(result)
    except Exception as e:
        print(e)
    return {"total": len(results), "results": results, "status": "ok"}


def shodan_host(host, api_key_shodan=os.environ.get("SHODAN_API_KEY")):
    api = shodan.Shodan(api_key_shodan)
    sh = api.host(host)
    del sh["data"]
    return sh
