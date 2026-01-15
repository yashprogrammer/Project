"""
Service for managing MongoDB Atlas Vector Search indexes.

For MVP, provides index verification and instructions for manual creation.
"""
from typing import Dict, Any, Optional
from pymongo import MongoClient
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings
from loguru import logger


class VectorIndexService:
    """
    Service to verify and manage MongoDB Atlas Vector Search indexes.
    
    Note: Vector Search indexes are only available in MongoDB Atlas.
    For MVP, we verify the index exists and provide instructions for manual creation.
    """
    
    def __init__(self, mongo_url: str = None):
        """
        Initialize the vector index service.
        
        Args:
            mongo_url: MongoDB connection URL (defaults to settings.MONGO_URL)
        """
        self.mongo_url = mongo_url or settings.MONGO_URL
        # Use sync client for index operations
        self.client = MongoClient(self.mongo_url)
        self.db_name = settings.DB_NAME
        self.collection_name = settings.DOCUMENT_CHUNKS_COLLECTION
    
    def get_vector_index_definition(
        self,
        dimensions: int = 768,
        similarity: str = "cosine"
    ) -> Dict[str, Any]:
        """
        Get the vector index definition for the configured chunks collection.
        This format is used for MongoDB Atlas Vector Search UI (JSON Editor).
        
        Args:
            dimensions: Embedding vector dimensions (768 for text-embedding-004)
            similarity: Similarity metric (cosine, euclidean, or dotProduct)
            
        Returns:
            Index definition dictionary in Vector Search format
        """
        return {
            "fields": [
                {
                    "type": "vector",
                    "path": "embedding",
                    "numDimensions": dimensions,
                    "similarity": similarity
                },
                {
                    "type": "filter",
                    "path": "department_id"
                },
                {
                    "type": "filter",
                    "path": "tenant_id"
                },
                {
                    "type": "filter",
                    "path": "is_disabled"
                }
            ]
        }
    
    def list_search_indexes(self) -> Dict[str, Any]:
        """
        List all search indexes for the chunks collection.
        
        Returns:
            Dictionary with status and list of indexes
        """
        db = self.client[self.db_name]
        collection = db[self.collection_name]
        
        try:
            indexes = list(collection.list_search_indexes())
            return {
                "status": "success",
                "indexes": indexes
            }
        except Exception as e:
            logger.error(f"Failed to list search indexes: {e}")
            return {
                "status": "error",
                "message": str(e),
                "indexes": []
            }
    
    def verify_index_exists(self, index_name: str = None) -> Dict[str, Any]:
        """
        Verify if the vector search index exists and is active.
        
        Args:
            index_name: Name of the index (defaults to settings.VECTOR_INDEX_NAME)
            
        Returns:
            Dictionary with verification result
        """
        if index_name is None:
            index_name = settings.VECTOR_INDEX_NAME
        
        try:
            result = self.list_search_indexes()
            
            if result.get("status") != "success":
                return {
                    "status": "error",
                    "index_name": index_name,
                    "exists": False,
                    "message": result.get("message", "Failed to check indexes"),
                    "note": "Unable to verify index. Please check MongoDB Atlas connection."
                }
            
            indexes = result.get("indexes", [])
            
            # Find the target index
            target_index = next(
                (idx for idx in indexes if idx.get("name") == index_name),
                None
            )
            
            if not target_index:
                return {
                    "status": "not_found",
                    "index_name": index_name,
                    "exists": False,
                    "message": f"Vector search index '{index_name}' not found",
                    "instructions": self.get_creation_instructions()
                }
            
            # Check index status
            status = target_index.get("status", "UNKNOWN")
            
            if status == "ACTIVE":
                return {
                    "status": "success",
                    "index_name": index_name,
                    "exists": True,
                    "active": True,
                    "message": f"Vector search index '{index_name}' exists and is active"
                }
            elif status in ("BUILDING", "PENDING"):
                return {
                    "status": "building",
                    "index_name": index_name,
                    "exists": True,
                    "active": False,
                    "status_detail": status,
                    "message": f"Vector search index '{index_name}' exists but is still {status.lower()}. Please wait for it to become active."
                }
            else:
                return {
                    "status": "error",
                    "index_name": index_name,
                    "exists": True,
                    "active": False,
                    "status_detail": status,
                    "message": f"Vector search index '{index_name}' exists but has status: {status}"
                }
                
        except Exception as e:
            logger.error(f"Error verifying index: {e}")
            return {
                "status": "error",
                "index_name": index_name,
                "exists": False,
                "message": str(e),
                "note": "Failed to verify index. Vector Search indexes are only available in MongoDB Atlas."
            }
    
    def get_creation_instructions(self) -> str:
        """
        Get instructions for creating the vector index manually.
        
        Returns:
            Formatted instruction string
        """
        index_def = self.get_vector_index_definition()
        import json
        
        instructions = f"""
╔══════════════════════════════════════════════════════════════════════════╗
║          MONGODB ATLAS VECTOR SEARCH INDEX SETUP INSTRUCTIONS            ║
╚══════════════════════════════════════════════════════════════════════════╝

1. Log in to MongoDB Atlas (https://cloud.mongodb.com)
2. Navigate to your cluster: {self.db_name}
3. Go to the 'Search' tab
4. Click 'Create Search Index'
5. Choose 'JSON Editor'
6. Select database: {self.db_name}
7. Select collection: {self.collection_name}
8. Name the index: {settings.VECTOR_INDEX_NAME}
9. Paste the following JSON definition:

{json.dumps(index_def, indent=2)}

10. Click 'Create Search Index'
11. Wait for the index to become 'Active' (may take a few minutes)

╔══════════════════════════════════════════════════════════════════════════╗
║  NOTE: Vector Search indexes are only available in MongoDB Atlas.       ║
║  They cannot be created in local MongoDB instances.                      ║
╚══════════════════════════════════════════════════════════════════════════╝
"""
        return instructions
    
    def print_creation_instructions(self):
        """Print instructions to console."""
        print(self.get_creation_instructions())

