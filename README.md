# Shopline Product Webhook to BigQuery

這是一個用來接收 Shopline product webhook（商品資料變動），並自動將資料同步（Upsert/Delete）到 Google BigQuery 的 Cloud Functions 專案。

## 架構特色

- **自動化資料清洗**：
  - 自動拆解多規格（Variations）的商品為獨立資料列，符合正規化設計。
  - 將多層級的翻譯字串及圖片陣列安全提取並轉換。
- **穩定的同步機制**：
  - 遇到 `product/create`、`product/update` 或 `product/back_in_stock` 時，會使用 BigQuery 的 `MERGE` 語句自動比對 `product_id` 與 `product_variation_id`，確保資料不重複（Upsert 邏輯）。
  - 遇到 `product/delete` 時，會透過 `DELETE` 語句移除 BigQuery 中該商品所有規格資料。
- **複合主鍵**：
  - Shopline 原本使用 `id` 作為主鍵，但商品規格內的資料較難查詢，因此將 `product_id` 與 `product_variation_id` 的組合作為複合主鍵，確保資料不重複，也方便瀏覽商品規格資料。

## 專案目錄

- `main.py`：Cloud Functions 的主程式（HTTP 觸發點）。
- `begin.py`：用來初始化 BigQuery 資料集（Dataset）與資料表（Table）的輔助腳本。
- `requirements.txt`：GCP 執行環境的 Python 依賴清單。
- `.env.example`：環境變數範例檔。

## 本地端環境設定

1. 安裝所需套件：

   ```bash
   pip install -r requirements.txt
   ```

2. 建立 `.env` 檔案（供本地端執行 `begin.py` 時使用）：

   ```bash
   cp .env.example .env
   ```

   請將 `.env` 內的 `PROJECT_ID` 設為您的 GCP 專案 ID。

3. 登入 Google Cloud 並取得本地端憑證（Application Default Credentials）：

   ```bash
   gcloud auth application-default login
   ```

## 初始化資料庫（一次性執行）

在部署 Cloud Functions 之前，請先確保 BigQuery 已經建立好對應的資料表結構：

```bash
python begin.py
```

如果出現「Table 建立成功」的訊息，即代表 BigQuery 的資料庫環境已準備完成。

## 部署至 Google Cloud Functions

使用以下指令將程式部署至 Google Cloud Functions：

```bash
gcloud functions deploy shopline-product-webhook \
  --runtime python310 \
  --trigger-http \
  --allow-unauthenticated \
  --entry-point handle_webhook \
  --region asia-east1 \
  --set-env-vars PROJECT_ID=YOUR_PROJECT_ID  \
```

### 參數說明

- `--trigger-http`：指定此函式透過 HTTP 網址觸發。
- `--allow-unauthenticated`：允許未經驗證的外部服務（例如 Shopline）呼叫。
- `--entry-point handle_webhook`：指定 `main.py` 裡的 `handle_webhook` 函式作為程式進入點。
- `--set-env-vars PROJECT_ID=YOUR_PROJECT_ID`：因為 `.env` 檔案預設不會被上傳到雲端，所以部署時必須透過此指令將專案 ID 注入給 Cloud Functions 使用。

部署完成後，主控台會回傳一個 `httpsTrigger: url: https://...` 的網址，這就是您的 **Webhook URL**。

## Shopline 後台設定

### 方式一：使用 SHOPLINE API Reference

因為只需要建立一個 webhook，可以直接在 SHOPLINE API Reference 設定：

https://open-api.docs.shoplineapp.com/reference/post_webhooks

輸入 credentials 與 address，topics 選擇 `product/create`、`product/update`、`product/remove`、`product/back_in_stock`，然後點選 try it 即可。

### 方式二：使用 curl

```bash
curl --request POST \
     --url https://open.shopline.io/v1/webhooks \
     --header 'accept: application/json' \
     --header 'authorization: Bearer YOUR_SHOPLINE_ACCESS_TOKEN' \
     --header 'content-type: application/json' \
     --data '
{
  "webhook_version": "v0",
  "address": "https://asia-east1-YOUR_PROJECT_ID.cloudfunctions.net/shopline-product-webhook",
  "topics": [
    "product/create",
    "product/update",
    "product/remove",
    "product/back_in_stock"
  ]
}
'
```
