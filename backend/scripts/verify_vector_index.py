#!/usr/bin/env python3
"""
Script to verify that the MongoDB Atlas Vector Search index exists and is active.

This script checks if the vector index required for RAG functionality is properly set up.
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.vector_index_service import VectorIndexService
from app.config import settings
from loguru import logger


def main():
    """Verify vector index exists and is active."""
    logger.info("Verifying MongoDB Atlas Vector Search index...")
    logger.info(f"Database: {settings.DB_NAME}")
    logger.info(f"Collection: {settings.DOCUMENT_CHUNKS_COLLECTION}")
    logger.info(f"Index name: {settings.VECTOR_INDEX_NAME}")
    print()
    
    service = VectorIndexService()
    result = service.verify_index_exists()
    
    if result.get("status") == "success" and result.get("active"):
        logger.success(f"✅ Vector index '{settings.VECTOR_INDEX_NAME}' exists and is ACTIVE")
        logger.info("You can now upload documents and use RAG functionality.")
        return 0
    elif result.get("status") == "building":
        logger.warning(f"⏳ Vector index '{settings.VECTOR_INDEX_NAME}' exists but is still {result.get('status_detail')}")
        logger.info("Please wait for the index to become active before uploading documents.")
        return 1
    elif result.get("status") == "not_found":
        logger.error(f"❌ Vector index '{settings.VECTOR_INDEX_NAME}' NOT FOUND")
        print()
        print(service.get_creation_instructions())
        return 1
    else:
        logger.error(f"❌ Error verifying index: {result.get('message')}")
        if result.get("instructions"):
            print()
            print(result.get("instructions"))
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

