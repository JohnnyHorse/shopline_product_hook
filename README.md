# Shopline Product Webhook to BigQuery

這是一個用來接收 Shopline product webhook（商品資料變動），並自動將資料同步（Upsert/Delete）到 Google BigQuery 的 Cloud Functions 專案。

## 本地端環境設定

1. 安裝套件：

   ```bash
   pip install -r requirements.txt
   ```

2. 建立 `.env`：

   ```bash
   cp .env.example .env
   ```

   `.env` 內的 `PROJECT_ID` 請使用 GCP project ID，例如 `br-gmail`。不要使用底線，例如 `br_gmail` 是錯的。

3. 登入 Google Cloud：

   ```bash
   gcloud auth application-default login
   ```

## 初始化 BigQuery

部署 Cloud Functions 前，先建立 BigQuery dataset/table：

```bash
python begin.py
```

## 部署 Cloud Function

目前專案 ID 是 `br-gmail`，Cloud Function 名稱是 `shopline-product-webhook`：

```bash
gcloud functions deploy shopline-product-webhook \
  --runtime python310 \
  --trigger-http \
  --allow-unauthenticated \
  --entry-point handle_webhook \
  --region asia-east1 \
  --set-env-vars PROJECT_ID=br-gmail \
  --project br-gmail
```

如果已經部署過但環境變數設錯，也可以只更新環境變數：

```bash
gcloud functions deploy shopline-product-webhook \
  --runtime python310 \
  --trigger-http \
  --allow-unauthenticated \
  --entry-point handle_webhook \
  --region asia-east1 \
  --update-env-vars PROJECT_ID=br-gmail \
  --project br-gmail
```

## Shopline Webhook Address

部署完成後，Shopline webhook address 請填：

```text
https://asia-east1-br-gmail.cloudfunctions.net/shopline-product-webhook
```

使用 curl 建立 webhook 範例：

```bash
curl --request POST \
     --url https://open.shopline.io/v1/webhooks \
     --header 'accept: application/json' \
     --header 'authorization: Bearer YOUR_SHOPLINE_ACCESS_TOKEN' \
     --header 'content-type: application/json' \
     --data '
{
  "webhook_version": "v0",
  "address": "https://asia-east1-br-gmail.cloudfunctions.net/shopline-product-webhook",
  "topics": [
    "product/create",
    "product/update",
    "product/remove",
    "product/back_in_stock"
  ]
}
'
```
