# map_macstb_city

マクドナルド・スターバックス 3km カバーエリアマップ

各店舗から半径 3km のカバーエリアを3種類に色分けして可視化する GitHub Pages プロジェクト。

| 色 | 意味 |
|---|---|
| 🟣 紫 | マクドナルド・スタバ **両方** のカバーエリアが重なる地域 |
| 🔴 赤 | **マクドナルドのみ** のカバーエリア |
| 🟢 緑 | **スターバックスのみ** のカバーエリア |

## データ

- マクドナルド: 3,022 店舗（2026年3月取得）
- スターバックス: 2,123 店舗（2026年5月取得）

## ファイル構成

```
build_geojson.py       # CSVからGeoJSONを生成するスクリプト
docs/
  index.html           # GitHub Pages メインページ
  both.geojson         # 両方カバーエリア
  mcd_only.geojson     # マクドナルドのみ
  sbux_only.geojson    # スターバックスのみ
  mcd_points.geojson   # マクドナルド店舗ポイント
  sbux_points.geojson  # スターバックス店舗ポイント
deploy.sh              # ローカルプレビュー + push スクリプト
```

## 使い方

```sh
# GeoJSON再生成
python3 build_geojson.py

# デプロイ
./deploy.sh "コミットメッセージ"
```
