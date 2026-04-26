# Shopline Webhook to BigQuery

這是一個用來接收 Shopline Webhook (商品異動通知)，並自動將資料同步 (Upsert/Delete) 到 Google BigQuery 的 Cloud Functions 專案。

## 架構特色
- **Serverless (無伺服器)**：部署於 Google Cloud Functions (Python 3.10)，免去伺服器維護煩惱，且計費依實際呼叫次數計算。
- **自動化資料清洗**：
  - 自動拆解多規格 (Variations) 的商品為獨立資料列，符合關聯式資料庫正規化設計。
  - 將多層級的翻譯字串及圖片陣列安全提取並轉換。
- **穩定的同步機制**：
  - 遇到 `product/create` 或 `product/update` 時，會使用 BigQuery 的 `MERGE` 語句自動比對 `product_id` 與 `product_variation_id`，確保資料不重複 (Upsert 邏輯)。
  - 遇到 `product/delete` 則透過 `DELETE` 語句移除 BigQuery 中該商品所有規格資料。

---

## 專案目錄
- `main.py`：Cloud Functions 的主程式 (HTTP 觸發點)。
- `begin.py`：用來初始化建置 BigQuery 資料集 (Dataset) 與資料表 (Table) 的輔助腳本。
- `requirements.txt`：GCP 執行環境的 Python 依賴清單。
- `.env.example`：環境變數範例檔。

---

## 本地端環境設定

1. 安裝所需套件：
   ```bash
   pip install -r requirements.txt
   ```

2. 複製一份 `.env` 檔案並填寫對應的 GCP Project ID：
   ```bash
   cp .env.example .env
   ```
   *請將 `.env` 內的 `PROJECT_ID` 替換為您的 GCP 專案 ID（例如 `dierneas-494509`）。*

3. 登入 Google Cloud 取得本地端憑證 (Application Default Credentials)：
   ```bash
   gcloud auth application-default login
   ```

---

## 初始化資料庫 (一次性執行)

在部署 Cloud Functions 之前，請先確保 BigQuery 已經建構好對應的資料表結構。請在終端機執行：

```bash
python begin.py
```
> 如果出現「Table 建立成功」的訊息，即代表 BigQuery 的資料庫環境已準備完畢。

---

## 部署至 Google Cloud Functions

使用以下指令將程式部署至 Google Cloud Functions。

*(注意：在正式環境中，您也可以透過 `--set-env-vars PROJECT_ID=您的專案ID` 將環境變數直接帶入部署指令中。)*

```bash
gcloud functions deploy shopline-webhook \
  --runtime python310 \
  --trigger-http \
  --allow-unauthenticated \
  --entry-point handle_webhook \
  --region asia-east1 \
  --set-env-vars PROJECT_ID=dierneas-494509 \
  --project dierneas-494509
```

### 參數說明：
- `--trigger-http`：指定此函數透過 HTTP 網址來觸發。
- `--allow-unauthenticated`：允許未經驗證的外部服務 (如 Shopline) 呼叫。
- `--entry-point handle_webhook`：指定 `main.py` 裡的 `handle_webhook` 函數為程式進入點。
- `--set-env-vars PROJECT_ID=dierneas-494509`：將環境變數注入到雲端環境中（不需要把 `.env` 檔上傳）。

部署完成後，主控台會回傳一個 `httpsTrigger: url: https://...` 的網址，這就是您的 **Webhook URL**。

---

## Shopline 後台設定
1. 進入 Shopline 商店後台。
2. 找到 **設定 > Webhook**（或是應用程式的 Webhook 綁定區塊）。
3. 建立三組訂閱，事件分別選擇：
   - `產品建立` (`product/create`)
   - `產品更新` (`product/update`)
   - `產品刪除` (`product/delete`)
4. 回傳網址 (URL) 請填上您剛剛部署完獲得的 Webhook URL。
5. 儲存設定。接下來任何商品變動都會自動同步進 BigQuery 囉！
