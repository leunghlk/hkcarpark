# 🅿️ hkcarpark — 港九新界實時停車場 dashboard

Live: https://leunghlk.github.io/hkcarpark/

搵任何一個目的地 → 附近停車場選擇 + 實時車位情況 + 收費（時租／消費免泊）。

## 資料來源
- **實時車位空置**：運輸署（資料一線通 data.gov.hk）開放數據
- **車場資料（地址／坐標／時租）**：運輸署「Car Park Information」資料集
- **商場消費免泊規則**：人工整理（`research/mall_free_parking.json`，各 entry 有 sourceUrl + asOf，以現場為準）

## 結構
- `index.html` — 單頁 dashboard（搜尋目的地 → 附近車場列表 + Leaflet 地圖）
- `build_data.py` — 由運輸署資料集拉取＋正規化，合併商場免泊規則 → `data/carparks.json`
- `data/carparks.json` — 車場主檔（static，隨 repo 部署）
- 實時空置數據由瀏覽器直接向 data.gov.hk 拉取（CORS 允許），每 3 分鐘自動刷新

## 更新車場主檔
```bash
python3 build_data.py   # 重新拉運輸署資料 + merge research/mall_free_parking.json
```
