import asyncio
from typing import Any, Optional
from bson import ObjectId
from loguru import logger
from pydantic import BaseModel, Field

from app.database import get_database
from app.services.embeddings import EmbeddingService
from app.config import settings


class ChunkContent(BaseModel):
    """Clean chunk content for LLM consumption - no IDs or metadata"""
    text: str = Field(..., description="The actual text content of the chunk")
    file_name: Optional[str] = Field(None, description="Source file name for context")
    score: Optional[float] = Field(None, description="Relevance score (0-1)")


class ChunkMetadata(BaseModel):
    """Metadata about a retrieved chunk - IDs and technical details"""
    chunk_id: str = Field(..., description="Unique chunk identifier")
    document_id: str = Field(..., description="Parent document identifier")
    department_id: str = Field(..., description="Department identifier")
    tenant_id: Optional[str] = Field(None, description="Tenant identifier")
    chunk_index: int = Field(..., description="Index of chunk within document")
    score: float = Field(..., description="Similarity/relevance score from vector search")
    file_name: str = Field(..., description="Source file name")


class RetrievalMetadata(BaseModel):
    """Metadata about the retrieval operation"""
    query: str = Field(..., description="The search query used")
    k: int = Field(..., description="Number of chunks requested")
    chunks_retrieved: int = Field(..., description="Actual number of chunks retrieved")
    department_id: Optional[str] = Field(None, description="Department filter applied")
    tenant_id: Optional[str] = Field(None, description="Tenant filter applied")
    chunks: list[ChunkMetadata] = Field(default_factory=list, description="Metadata for each retrieved chunk")


class RetrievalResult(BaseModel):
    """Complete retrieval result with clean data and metadata"""
    data: list[ChunkContent] = Field(..., description="Clean chunk content for LLM consumption")
    metadata: RetrievalMetadata = Field(..., description="Metadata about the retrieval operation")


embeddings_service = EmbeddingService()


class RAGService:
    def __init__(self, index_name: str = None):
        self.index_name = index_name or settings.VECTOR_INDEX_NAME
        logger.debug("RAGService initialized", index_name=self.index_name)

    async def retrieve(
        self,
        query: str,
        k: int = 5,
        department_id: str | None = None,
        tenant_id: str | None = None,
        extra_filters: dict[str, Any] | None = None,
    ) -> RetrievalResult:
        """
        Perform vector search directly using MongoDB's $vectorSearch aggregation.
        
        Returns:
            RetrievalResult: Contains:
                - data: Clean chunk content for LLM (text, file_name, score)
                - metadata: Technical metadata (IDs, indices, query info)
        """
        db = get_database()
        collection = db[settings.DOCUMENT_CHUNKS_COLLECTION]
        
        try:
            logger.info(f"Starting retrieval for query: '{query[:50]}...' (k={k})")
            
            # Check if collection is available
            if collection is None:
                raise ConnectionError("MongoDB collection is not initialized. Database connection failed.")
            
            # 1. Generate vector embedding
            try:
                logger.debug("Generating query embedding...")
                query_embedding = embeddings_service.embed_text(query)
                logger.debug("Query embedding generated successfully")
            except Exception as e:
                logger.error(f"Failed to generate query embedding: {e}")
                raise

            # 2. Build filters
            filters = {}
            
            # Always filter out disabled chunks
            filters["is_disabled"] = {"$ne": True}

            if department_id:
                try:
                    filters["department_id"] = ObjectId(department_id)
                    logger.debug(f"Added department_id filter: {department_id}")
                except Exception as e:
                    logger.warning(f"Invalid department_id '{department_id}'; skipping filter. Error: {e}")

            if tenant_id:
                filters["tenant_id"] = tenant_id
                logger.debug(f"Added tenant_id filter: {tenant_id}")

            if extra_filters:
                filters.update(extra_filters)
                logger.debug(f"Added extra filters: {extra_filters}")

            # 3. Build vector search aggregation
            vector_query = {
                "$vectorSearch": {
                    "index": self.index_name,
                    "path": "embedding",
                    "queryVector": query_embedding,
                    "numCandidates": k * 5,
                    "limit": k,
                }
            }

            # Add filter if not empty
            if filters:
                vector_query["$vectorSearch"]["filter"] = filters

            pipeline = [
                vector_query,
                {
                    "$project": {
                        "_id": 1,
                        "chunk_id": 1,
                        "document_id": 1,
                        "file_name": 1,
                        "text": 1,
                        "chunk_index": 1,
                        "department_id": 1,
                        "tenant_id": 1,
                        "score": {"$meta": "vectorSearchScore"}
                    }
                }
            ]

            # 4. Run aggregation
            try:
                logger.debug(f"Executing vector search with index: {self.index_name}")
                cursor = collection.aggregate(pipeline)
                results = await cursor.to_list(length=k)
                logger.info(f"Retrieved {len(results)} results from vector search")
            except Exception as e:
                logger.error(f"Failed to execute vector search aggregation: {e}")
                raise

            # 5. Convert to output structure - separate clean data from metadata
            chunk_data = []
            chunk_metadata = []
            
            try:
                for res in results:
                    # Clean data for LLM (no IDs, just content)
                    chunk_data.append(ChunkContent(
                        text=res.get("text", ""),
                        file_name=res.get("file_name"),
                        score=res.get("score"),
                    ))
                    
                    # Metadata (all IDs and technical details)
                    chunk_metadata.append(ChunkMetadata(
                        chunk_id=res.get("chunk_id", ""),
                        document_id=str(res.get("document_id", "")),
                        department_id=str(res.get("department_id", "")),
                        tenant_id=res.get("tenant_id"),
                        chunk_index=res.get("chunk_index", 0),
                        score=res.get("score", 0.0),
                        file_name=res.get("file_name", ""),
                    ))
                
                logger.success(f"Successfully processed {len(chunk_data)} chunks")
            except Exception as e:
                logger.error(f"Failed to process search results: {e}")
                raise

            # Build the result with clean data and metadata
            result = RetrievalResult(
                data=chunk_data,
                metadata=RetrievalMetadata(
                    query=query,
                    k=k,
                    chunks_retrieved=len(chunk_data),
                    department_id=department_id,
                    tenant_id=tenant_id,
                    chunks=chunk_metadata,
                ),
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error during retrieval operation: {e}")
            raise

