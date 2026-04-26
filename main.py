import os
import functions_framework
from google.cloud import bigquery
from dotenv import load_dotenv

# 載入 .env 檔案中的環境變數 (本地端測試時使用)
load_dotenv()

# --- 設定區塊 ---
# 從環境變數讀取 PROJECT_ID，以保護機密資料
PROJECT_ID = os.environ.get("PROJECT_ID", "your-project-id")
DATASET_ID = "shopline_data"
TABLE_ID = "products"
TABLE_REF = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"

# 初始化 BigQuery 用戶端 (在 Cloud Functions 的全域範圍初始化，可重複利用連線加速執行)
bq_client = bigquery.Client(project=PROJECT_ID)

# 定義欄位名稱與 BigQuery 資料型態的對應，方便動態生成 SQL
TYPE_MAP = {
    "is_preorder": "BOOL",
    "unlimited_quantity": "BOOL",
    "quantity": "INT64",
    "max_order_quantity": "INT64",
    "total_orderable_quantity": "INT64",
    "preorder_limit": "INT64",
    "price": "FLOAT64",
    "price_sale": "FLOAT64",
    "lowest_price": "FLOAT64",
    "lowest_price_sale": "FLOAT64",
    "member_price": "FLOAT64",
    "cost": "FLOAT64",
    "created_at": "TIMESTAMP",
    "updated_at": "TIMESTAMP",
    "schedule_publish_at": "TIMESTAMP",
    "category_ids": "ARRAY<STRING>",
    "medias": "ARRAY<STRING>",
    "detail_medias": "ARRAY<STRING>",
}

def extract_safe(data, keys, default=None):
    """安全提取多層級字典的值"""
    for key in keys:
        if isinstance(data, dict):
            data = data.get(key)
        else:
            return default
        if data is None:
            return default
    return data

def parse_product_payload(data):
    """
    依照您的需求解析 JSON，回傳 List of dicts (每一筆代表一個 variation 或獨立商品)
    """
    resource = data.get("resource")
    if not resource:
        return []

    records = []
    base_record = {
        "product_id": resource.get("_id") or resource.get("id"),
        "title_translations": extract_safe(resource, ["title_translations", "zh-hant"]),
        "status": resource.get("status"),
        "retail_status": resource.get("retail_status"),
        "location_id": resource.get("location_id"),
        "sku": resource.get("sku"),
        "gtin": resource.get("gtin"),
        "is_preorder": resource.get("is_preorder"),
        "quantity": resource.get("quantity"),
        "max_order_quantity": resource.get("max_order_quantity"),
        "total_orderable_quantity": resource.get("total_orderable_quantity"),
        "unlimited_quantity": resource.get("unlimited_quantity"),
        "preorder_limit": resource.get("preorder_limit"),
        "price": extract_safe(resource, ["price", "dollars"]),
        "price_sale": extract_safe(resource, ["price_sale", "dollars"]),
        "lowest_price": extract_safe(resource, ["lowest_price", "dollars"]),
        "lowest_price_sale": extract_safe(resource, ["lowest_price_sale", "dollars"]),
        "member_price": extract_safe(resource, ["member_price", "dollars"]),
        "cost": extract_safe(resource, ["cost", "dollars"]),
        "category_ids": resource.get("category_ids", []),
        "created_at": resource.get("created_at"),
        "updated_at": resource.get("updated_at"),
        "schedule_publish_at": resource.get("schedule_publish_at"),
        "medias": [m.get("images", {}).get("original", {}).get("url") for m in resource.get("medias", []) if extract_safe(m, ["images", "original", "url"])],
        "detail_medias": [m.get("images", {}).get("original", {}).get("url") for m in resource.get("detail_medias", []) if extract_safe(m, ["images", "original", "url"])],
    }

    variations = resource.get("variations")

    if variations and len(variations) > 0:
        for variation in variations:
            var_record = base_record.copy()
            var_record["product_variation_id"] = variation.get("id") or variation.get("_id")

            # 處理 fields_translations (串接為字串)
            fields_trans = extract_safe(variation, ["fields_translations", "zh-hant"])
            if isinstance(fields_trans, list):
                var_record["fields_translations"] = "-".join([str(x) for x in fields_trans])
            else:
                var_record["fields_translations"] = fields_trans

            var_record["variation_image"] = extract_safe(variation, ["media", "images", "original", "url"])

            # 覆蓋規格專屬屬性
            var_record["location_id"] = variation.get("location_id")
            var_record["gtin"] = variation.get("gtin")

            for price_field in ["price", "price_sale", "cost", "member_price"]:
                val = extract_safe(variation, [price_field, "dollars"])
                if val is not None: var_record[price_field] = val

            for numeric_field in ["preorder_limit", "quantity", "sku", "total_orderable_quantity", "unlimited_quantity"]:
                if numeric_field in variation:
                    var_record[numeric_field] = variation.get(numeric_field)

            records.append(var_record)
    else:
        var_record = base_record.copy()
        var_record["product_variation_id"] = None
        var_record["fields_translations"] = None
        var_record["variation_image"] = None
        records.append(var_record)

    return records

def upsert_records_to_bq(records):
    """
    透過動態生成 MERGE 語句，將資料同步寫入 BigQuery
    """
    if not records:
        return

    query_parameters = []
    structs_sql = []
    all_keys = list(records[0].keys())

    # 將 records 轉換成 SQL 的 STRUCT 結構與參數
    for i, record in enumerate(records):
        row_fields = []
        for k in all_keys:
            v = record.get(k)
            param_name = f"p_{i}_{k}"
            
            # 依據資料型態配置 BigQuery Query Parameter
            if isinstance(v, list):
                # 為了避免 BQ 報錯，確保空陣列有型別，我們傳遞空的字串陣列
                query_parameters.append(bigquery.ArrayQueryParameter(param_name, "STRING", [str(x) for x in v] if v else []))
            elif isinstance(v, bool):
                query_parameters.append(bigquery.ScalarQueryParameter(param_name, "BOOL", v))
            elif isinstance(v, float):
                query_parameters.append(bigquery.ScalarQueryParameter(param_name, "FLOAT64", v))
            elif isinstance(v, int):
                query_parameters.append(bigquery.ScalarQueryParameter(param_name, "INT64", v))
            else:
                # 處理字串或 None
                query_parameters.append(bigquery.ScalarQueryParameter(param_name, "STRING", str(v) if v is not None else None))

            cast_type = TYPE_MAP.get(k, "STRING")
            row_fields.append(f"CAST(@{param_name} AS {cast_type}) AS {k}")
        
        structs_sql.append("STRUCT(" + ", ".join(row_fields) + ")")

    # 組合 UNNEST 語法
    source_sql = "SELECT * FROM UNNEST([\n" + ",\n".join(structs_sql) + "\n])"

    # 組合欄位以便做 UPDATE 和 INSERT
    update_sets = ", ".join([f"{k} = S.{k}" for k in all_keys if k not in ("product_id", "product_variation_id")])
    insert_cols = ", ".join(all_keys)
    insert_vals = ", ".join([f"S.{k}" for k in all_keys])

    # 組合 MERGE 語句 (使用 IFNULL 來處理 product_variation_id 為 NULL 的情況)
    merge_query = f"""
        MERGE `{TABLE_REF}` T
        USING ({source_sql}) S
        ON T.product_id = S.product_id 
           AND IFNULL(T.product_variation_id, '') = IFNULL(S.product_variation_id, '')
        WHEN MATCHED THEN
            UPDATE SET {update_sets}
        WHEN NOT MATCHED THEN
            INSERT ({insert_cols}) VALUES ({insert_vals})
    """

    # 執行查詢
    job_config = bigquery.QueryJobConfig(query_parameters=query_parameters)
    job = bq_client.query(merge_query, job_config=job_config)
    job.result() # 等待執行完成

def delete_product_from_bq(product_id):
    """
    從 BigQuery 刪除特定商品的所有紀錄 (包含 Variations)
    """
    if not product_id:
        return
        
    delete_query = f"DELETE FROM `{TABLE_REF}` WHERE product_id = @product_id"
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("product_id", "STRING", product_id)
        ]
    )
    job = bq_client.query(delete_query, job_config=job_config)
    job.result() # 等待執行完成

# --- Cloud Functions 的 HTTP 進入點 ---
@functions_framework.http
def handle_webhook(request):
    """
    接收 Shopline 傳送來的 Webhook HTTP Request
    """
    try:
        # 1. 取得 JSON 資料
        payload = request.get_json()
        if not payload:
            return {"status": "error", "message": "No JSON payload provided"}, 400

        # 2. 依照 Topic 處理資料
        topic = payload.get("topic", "")
        print(f"收到 Webhook，Topic: {topic}")

        if topic in ("product/create", "product/update"):
            # 解析並存入或更新至 BigQuery
            records = parse_product_payload(payload)
            if records:
                upsert_records_to_bq(records)
                print(f"成功 Upsert {len(records)} 筆商品記錄 (ProductID: {records[0].get('product_id')})")
                
        elif topic in ("product/delete", "product/remove"):
            # 刪除 BigQuery 中的資料
            resource = payload.get("resource", {})
            product_id = resource.get("_id") or resource.get("id")
            if product_id:
                delete_product_from_bq(product_id)
                print(f"成功從 BigQuery 刪除商品 (ProductID: {product_id})")

        return {"message": "Success"}, 200

    except Exception as e:
        # 如果發生非預期錯誤，印出 log 供後續 debug，但依然可以回傳 200，
        # 或者回傳 500 讓 Shopline 知道失敗並嘗試重送。
        print(f"Error handling webhook: {e}")
        return {"status": "error", "message": str(e)}, 500