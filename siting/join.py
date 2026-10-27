"""Assign Aqueduct 4.0 baseline water stress to point locations.
Points inside a sub-basin polygon take its values; points just outside
(coastlines) take the nearest polygon within 0.1 degrees."""
import sys, warnings
import geopandas as gpd, pandas as pd
warnings.filterwarnings("ignore")
GDB = sys.argv[1]; out_dir = sys.argv[2]
cols = ["string_id", "pfaf_id", "gid_0", "name_0", "name_1", "area_km2",
        "bws_raw", "bws_score", "bws_cat", "bws_label"]
poly = gpd.read_file(GDB, layer="baseline_annual", columns=cols, engine="pyogrio")
print("polygons", len(poly), poly.crs, flush=True)

def assign(pts, name):
    pts = pts.set_crs(4326, allow_override=True)
    j = gpd.sjoin(pts, poly, how="left", predicate="within")
    j = j[~j.index.duplicated(keep="first")]
    miss = j["bws_cat"].isna()
    if miss.any():
        near = gpd.sjoin_nearest(pts[miss], poly, how="left", max_distance=0.1)
        near = near[~near.index.duplicated(keep="first")]
        for c in cols:
            j.loc[near.index, c] = near[c]
        j.loc[near.index, "matched"] = "nearest"
    j["matched"] = j.get("matched").fillna("within") if "matched" in j else "within"
    j.loc[j["bws_cat"].isna(), "matched"] = "none"
    j.drop(columns=["geometry", "index_right"], errors="ignore").to_csv(f"{out_dir}/{name}_water.csv", index=False)
    print(name, len(j), j["matched"].value_counts().to_dict(), flush=True)

# PeeringDB facilities
p = pd.read_csv(sys.argv[3])
p = p.dropna(subset=["latitude", "longitude"])
p = p[(p.latitude.abs() <= 90) & (p.longitude.abs() <= 180) & ~((p.latitude == 0) & (p.longitude == 0))]
assign(gpd.GeoDataFrame(p, geometry=gpd.points_from_xy(p.longitude, p.latitude)), "peeringdb")

# Natural Earth populated places (reference distribution)
c = gpd.read_file(sys.argv[4])[["name", "adm0name", "iso_a2", "pop_max", "geometry"]]
assign(c, "cities")

# Epoch AI frontier sites (optional; may not exist yet)
if len(sys.argv) > 5:
    e = pd.read_csv(sys.argv[5])
    assign(gpd.GeoDataFrame(e, geometry=gpd.points_from_xy(e.lon, e.lat)), "epoch")
