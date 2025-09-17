import os
import json
import logging
from datetime import datetime, timezone
from google.cloud import storage
from config.database import get_client
from config.setting import MONGO_DB as DEFAULT_DB
from config.logging_config import setup_logger, log_performance
from dotenv import load_dotenv

# Load .env for local execution
load_dotenv()

# Setup centralized logger
logger = setup_logger("main")

BATCH_SIZE = 1000

def export_to_gcs(
    db_name: str | None = None,
    collection_name: str | None = None,
    bucket_name: str | None = None,
    gcs_path: str | None = None,
):
    try:
        # 1. Connect to MongoDB via config.database
        client = get_client()
        if client is None:
            raise RuntimeError("Cannot get MongoDB client from config.database")
        effective_db = (db_name or os.getenv("DB_NAME") or DEFAULT_DB)
        effective_collection = (collection_name or os.getenv("COLLECTION_NAME"))
        effective_bucket = (bucket_name or os.getenv("GCS_BUCKET"))
        effective_path = (gcs_path or os.getenv("GCS_PATH", ""))

        if not effective_collection:
            raise ValueError("Missing collection name (set COLLECTION_NAME in .env or pass argument)")
        if not effective_bucket:
            raise ValueError("Missing GCS bucket (set GCS_BUCKET in .env or pass argument)")

        db = client[effective_db]
        collection = db[effective_collection]
        logger.info("Connected to MongoDB: %s/%s", effective_db, effective_collection)

        # 2. Extract data in batches
        cursor = collection.find({})
        batch = []
        file_name = f"{effective_collection}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.jsonl"
        local_file = f"/tmp/{file_name}"

        with open(local_file, "w", encoding="utf-8") as f:
            for i, doc in enumerate(cursor, start=1):
                # 3. Convert to JSONL (remove _id if needed)
                doc["_id"] = str(doc["_id"])
                f.write(json.dumps(doc, ensure_ascii=False) + "\n")

                # batching just for logging
                if i % BATCH_SIZE == 0:
                    logger.info("Exported %d documents", i)

        logger.info("Finished writing local file: %s", local_file)

        # 4. Upload to GCS
        storage_client = storage.Client()
        bucket = storage_client.bucket(effective_bucket)
        blob_path = f"{effective_path}/{file_name}" if effective_path else file_name
        blob = bucket.blob(blob_path)
        blob.upload_from_filename(local_file)
        logger.info("Uploaded file to GCS: gs://%s/%s", effective_bucket, blob_path)

    except Exception as e:
        logger.error("Error in export_to_gcs: %s", e, exc_info=True)
    finally:
        client.close()
        logger.info("MongoDB connection closed")


if __name__ == "__main__":
    export_to_gcs()
