import os
from google.cloud import bigquery
from google.api_core.exceptions import Conflict
from dotenv import load_dotenv

load_dotenv()

# 設定您的 GCP Project ID (從 .env 讀取)
PROJECT_ID = os.environ.get("PROJECT_ID", "your-project-id")
DATASET_ID = "shopline_data"
TABLE_ID = "products"

def initialize_bigquery():
    # 建立 BigQuery 用戶端
    client = bigquery.Client(project=PROJECT_ID)

    # 1. 建立 Dataset
    dataset_ref = f"{PROJECT_ID}.{DATASET_ID}"
    dataset = bigquery.Dataset(dataset_ref)
    dataset.location = "asia-east1" # 您可依據需求調整為台灣 asia-east1 或其他地區
    
    try:
        client.create_dataset(dataset)
        print(f"Dataset {dataset_ref} 建立成功。")
    except Conflict:
        print(f"Dataset {dataset_ref} 已經存在。")

    # 2. 定義 Table Schema
    schema = [
        bigquery.SchemaField("product_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("product_variation_id", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("title_translations", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("fields_translations", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("status", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("retail_status", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("location_id", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("sku", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("gtin", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("is_preorder", "BOOLEAN", mode="NULLABLE"),
        bigquery.SchemaField("quantity", "INTEGER", mode="NULLABLE"),
        bigquery.SchemaField("max_order_quantity", "INTEGER", mode="NULLABLE"),
        bigquery.SchemaField("total_orderable_quantity", "INTEGER", mode="NULLABLE"),
        bigquery.SchemaField("unlimited_quantity", "BOOLEAN", mode="NULLABLE"),
        bigquery.SchemaField("preorder_limit", "INTEGER", mode="NULLABLE"),
        bigquery.SchemaField("price", "FLOAT", mode="NULLABLE"),
        bigquery.SchemaField("price_sale", "FLOAT", mode="NULLABLE"),
        bigquery.SchemaField("lowest_price", "FLOAT", mode="NULLABLE"),
        bigquery.SchemaField("lowest_price_sale", "FLOAT", mode="NULLABLE"),
        bigquery.SchemaField("member_price", "FLOAT", mode="NULLABLE"),
        bigquery.SchemaField("cost", "FLOAT", mode="NULLABLE"),
        bigquery.SchemaField("category_ids", "STRING", mode="REPEATED"),
        bigquery.SchemaField("created_at", "TIMESTAMP", mode="NULLABLE"),
        bigquery.SchemaField("updated_at", "TIMESTAMP", mode="NULLABLE"),
        bigquery.SchemaField("schedule_publish_at", "TIMESTAMP", mode="NULLABLE"),
        bigquery.SchemaField("medias", "STRING", mode="REPEATED"),
        bigquery.SchemaField("detail_medias", "STRING", mode="REPEATED"),
        bigquery.SchemaField("variation_image", "STRING", mode="NULLABLE"),
    ]

    # 3. 建立 Table
    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"
    table = bigquery.Table(table_ref, schema=schema)
    
    # Optional: 加入依據更新時間建立的分區表，可以提升未來查詢效率並節省成本
    # table.time_partitioning = bigquery.TimePartitioning(
    #     type_=bigquery.TimePartitioningType.DAY,
    #     field="updated_at",  
    # )
    
    try:
        client.create_table(table)
        print(f"Table {table_ref} 建立成功。")
    except Conflict:
        print(f"Table {table_ref} 已經存在。")

if __name__ == "__main__":
    print("請確保您已經在終端機執行過: gcloud auth application-default login")
    initialize_bigquery()
