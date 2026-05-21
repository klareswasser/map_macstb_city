"""
build_geojson.py
マクドナルド・スターバックスの各店舗から半径3kmのバッファを作成し、
以下の3種類のGeoJSONを docs/ フォルダに出力する:
  - both.geojson   : 両チェーンのカバーエリアが重なる部分
  - mcd_only.geojson : マクドナルドのみ
  - sbux_only.geojson: スターバックスのみ
また、個別の店舗ポイントGeoJSONも出力する:
  - mcd_points.geojson
  - sbux_points.geojson
"""

import csv
import json
import os
from pathlib import Path
from shapely.geometry import Point, mapping
from shapely.ops import unary_union
import pyproj
from functools import partial
from shapely.ops import transform

BASE = Path(__file__).parent
DOCS = BASE / "docs"
DOCS.mkdir(exist_ok=True)

MCD_CSV  = Path("/Users/hiroki/Library/Mobile Documents/com~apple~CloudDocs/Projects/DB構築/2025_チェーン店_店舗データ/ハンバーガーチェーン/大手チェーン/マクドナルド/data/マクドナルド_260318.csv")
SBUX_CSV = Path("/Users/hiroki/Library/Mobile Documents/com~apple~CloudDocs/Projects/DB構築/2025_チェーン店_店舗データ/カフェチェーン/スターバックスコーヒー/data/starbucks_stores.csv")

RADIUS_M = 2000  # 2km

# ---- 座標変換ヘルパー ----
wgs84 = pyproj.CRS("EPSG:4326")

# スタバデータは旧日本測地系(Tokyo Datum / EPSG:4301)のため WGS84 に変換
_tokyo_to_wgs84 = pyproj.Transformer.from_crs("EPSG:4301", "EPSG:4326", always_xy=True)

def tokyo_to_wgs84(lon, lat):
    """旧日本測地系(EPSG:4301) → WGS84(EPSG:4326)"""
    lon_w, lat_w = _tokyo_to_wgs84.transform(lon, lat)
    return lon_w, lat_w


def buffer_m(lon, lat, radius_m):
    """WGS84の点に対してメートル単位のバッファを返す（UTM投影使用）"""
    # UTMゾーンを自動選択
    utm_crs = pyproj.CRS(pyproj.CRS.from_dict({
        "proj": "utm",
        "zone": int((lon + 180) / 6) + 1,
        "south": lat < 0,
    }))
    project = pyproj.Transformer.from_crs(wgs84, utm_crs, always_xy=True).transform
    project_back = pyproj.Transformer.from_crs(utm_crs, wgs84, always_xy=True).transform
    pt_utm = transform(project, Point(lon, lat))
    buf_utm = pt_utm.buffer(radius_m)
    return transform(project_back, buf_utm)


def load_mcd(path):
    stores = []
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                lat = float(row["latitude"])
                lon = float(row["longitude"])
                stores.append({
                    "name": row["name"],
                    "lat": lat,
                    "lon": lon,
                    "address": row.get("address", ""),
                })
            except (ValueError, KeyError):
                continue
    return stores


def load_sbux(path):
    stores = []
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                lat = float(row["latitude"])
                lon = float(row["longitude"])
                # APIの座標は旧日本測地系(Tokyo Datum) → WGS84 に変換
                lon, lat = tokyo_to_wgs84(lon, lat)
                stores.append({
                    "name": row["name"],
                    "lat": lat,
                    "lon": lon,
                    "address": (row.get("address_1", "") + row.get("address_2", "") + row.get("address_5", "")),
                })
            except (ValueError, KeyError):
                continue
    return stores


def to_points_geojson(stores, filename):
    features = []
    for s in stores:
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [s["lon"], s["lat"]]},
            "properties": {"name": s["name"], "address": s["address"]},
        })
    gj = {"type": "FeatureCollection", "features": features}
    out = DOCS / filename
    with open(out, "w", encoding="utf-8") as f:
        json.dump(gj, f, ensure_ascii=False, separators=(",", ":"))
    print(f"  → {filename}: {len(features)} points")
    return out


def to_polygon_geojson(geom, filename, props=None):
    if props is None:
        props = {}
    feature = {
        "type": "Feature",
        "geometry": mapping(geom),
        "properties": props,
    }
    gj = {"type": "FeatureCollection", "features": [feature]}
    out = DOCS / filename
    with open(out, "w", encoding="utf-8") as f:
        json.dump(gj, f, ensure_ascii=False, separators=(",", ":"))
    size_kb = out.stat().st_size / 1024
    print(f"  → {filename}: {size_kb:.0f} KB")
    return out


def main():
    print("=== マクドナルド・スタバ 3km カバーエリア GeoJSON 生成 ===\n")

    print("1. CSVを読み込み中...")
    mcd_stores = load_mcd(MCD_CSV)
    sbux_stores = load_sbux(SBUX_CSV)
    print(f"   マクドナルド: {len(mcd_stores)} 件")
    print(f"   スターバックス: {len(sbux_stores)} 件\n")

    print("2. 店舗ポイントGeoJSONを出力...")
    to_points_geojson(mcd_stores, "mcd_points.geojson")
    to_points_geojson(sbux_stores, "sbux_points.geojson")

    print("\n3. 3kmバッファを計算中（マクドナルド）...")
    mcd_buffers = []
    for i, s in enumerate(mcd_stores):
        if i % 500 == 0:
            print(f"   {i}/{len(mcd_stores)}...")
        mcd_buffers.append(buffer_m(s["lon"], s["lat"], RADIUS_M))
    mcd_union = unary_union(mcd_buffers)
    print(f"   → union完了")

    print("\n4. 3kmバッファを計算中（スターバックス）...")
    sbux_buffers = []
    for i, s in enumerate(sbux_stores):
        if i % 500 == 0:
            print(f"   {i}/{len(sbux_stores)}...")
        sbux_buffers.append(buffer_m(s["lon"], s["lat"], RADIUS_M))
    sbux_union = unary_union(sbux_buffers)
    print(f"   → union完了")

    print("\n5. 差集合・積集合を計算中...")
    both     = mcd_union.intersection(sbux_union)
    mcd_only = mcd_union.difference(sbux_union)
    sbux_only = sbux_union.difference(mcd_union)

    # 複雑なポリゴンを簡略化（表示に十分な精度を保ちつつファイルサイズ削減）
    tol = 0.0001  # ~10m
    both      = both.simplify(tol)
    mcd_only  = mcd_only.simplify(tol)
    sbux_only = sbux_only.simplify(tol)

    print("\n6. GeoJSONを出力中...")
    to_polygon_geojson(both,      "both.geojson",      {"type": "both"})
    to_polygon_geojson(mcd_only,  "mcd_only.geojson",  {"type": "mcd_only"})
    to_polygon_geojson(sbux_only, "sbux_only.geojson", {"type": "sbux_only"})

    print("\n=== 完了 ===")


if __name__ == "__main__":
    main()
