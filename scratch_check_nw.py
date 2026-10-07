import urllib.request
import urllib.parse
import json

query = """[out:json][timeout:35];
(
  way["highway"](-6.1915, 106.9635, -6.1806, 106.9740);
);
out body;
>;
out skel qt;
"""

url = "https://overpass-api.de/api/interpreter"
payload = ("data=" + urllib.parse.quote(query)).encode("utf-8")

req = urllib.request.Request(
    url,
    data=payload,
    headers={
        "User-Agent": "PuskesmasPlacementSimulator/2.0 (educational research)",
        "Content-Type": "application/x-www-form-urlencoded"
    }
)

print("Sending request to overpass-api.de...")
try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        ways = [e for e in res["elements"] if e["type"] == "way"]
        nodes = {e["id"]: (e["lat"], e["lon"]) for e in res["elements"] if e["type"] == "node"}
        print(f"Success! Found {len(ways)} ways and {len(nodes)} nodes.")
        
        with open("scratch_nw_osm.json", "w") as f:
            json.dump(res, f)
        print("Saved to scratch_nw_osm.json")
except Exception as e:
    print("Error:", e)
