# Vector Search Implementation Guide

## Overview

This project uses **MongoDB Atlas Vector Search** for RAG (Retrieval-Augmented Generation) functionality. Vector search enables semantic similarity search over document embeddings.

## How It Works

### 1. Document Processing Pipeline

When you upload a document:

1. **Text Extraction**: Text is extracted from PDF/DOCX/TXT/MD files
2. **Chunking**: Text is split into chunks (default: 1000 chars with 250 overlap)
3. **Embedding Generation**: Each chunk is converted to a 768-dimensional vector using Google's `text-embedding-004` model
4. **Storage**: Chunks with embeddings are stored in MongoDB `document_chunks` collection

### 2. Vector Search Index

**CRITICAL**: A vector search index must exist in MongoDB Atlas before vector search will work.

The index:
- **Name**: `vector_index` (configurable via `VECTOR_INDEX_NAME`)
- **Collection**: `document_chunks`
- **Vector Field**: `embedding` (768 dimensions, cosine similarity)
- **Filter Fields**: `department_id`, `tenant_id`, `is_disabled`, etc.

### 3. RAG Retrieval Process

When a user asks a question:

1. **Query Embedding**: The question is converted to a 768-dimensional vector
2. **Vector Search**: MongoDB's `$vectorSearch` aggregation finds similar chunks
3. **Filtering**: Results are filtered by department_id, tenant_id, and is_disabled
4. **Ranking**: Results are ranked by similarity score (cosine distance)
5. **Return**: Top K chunks (default: 5) are returned with metadata

## Verification

### Check if Index Exists

```bash
# Using the verification script
cd backend
uv run python scripts/verify_vector_index.py

# Or via API
curl http://localhost:8000/health/vector-index
```

### Expected Output (Success)

```
✅ Vector index 'vector_index' exists and is ACTIVE
You can now upload documents and use RAG functionality.
```

### Expected Output (Missing Index)

```
❌ Vector index 'vector_index' NOT FOUND
[Instructions for creating the index will be displayed]
```

## Creating the Vector Index

### Option 1: MongoDB Atlas UI (Recommended for MVP)

1. Log in to [MongoDB Atlas](https://cloud.mongodb.com)
2. Navigate to your cluster
3. Go to the **Search** tab
4. Click **Create Search Index**
5. Choose **JSON Editor**
6. Select:
   - Database: `mvp_db` (or your `DB_NAME`)
   - Collection: `document_chunks`
   - Index name: `vector_index`
7. Paste the index definition (see README.md)
8. Click **Create Search Index**
9. Wait for status to become **Active** (may take a few minutes)

### Option 2: Using the Verification Script

The verification script will display detailed instructions if the index is missing.

## Understanding Why We Need This

**See `WHY_VECTOR_INDEX.md` for a detailed explanation of:**
- Why we choose the `document_chunks` collection
- Why we write this specific JSON definition
- How vector search works under the hood

## Index Definition

The vector index definition includes:

```json
{
  "fields": [
    {
      "type": "vector",
      "path": "embedding",
      "numDimensions": 768,
      "similarity": "cosine"
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
```

## Troubleshooting

### "Vector search index not found" Error

- **Cause**: The vector index doesn't exist or isn't active
- **Solution**: Create the index in MongoDB Atlas (see above)
- **Verify**: Run `python scripts/verify_vector_index.py`

### "Failed to execute vector search aggregation" Error

- **Cause**: Index exists but isn't active yet
- **Solution**: Wait for index status to become "Active" in Atlas
- **Check**: Use `/health/vector-index` endpoint

### No Results from RAG Search

- **Cause**: No documents uploaded or embeddings not generated
- **Solution**: 
  1. Upload documents to a department
  2. Verify chunks were created: Check `document_chunks` collection
  3. Verify embeddings exist: Check that chunks have `embedding` field with 768 values

### Embeddings Not Being Generated

- **Cause**: Google API key invalid or quota exceeded
- **Solution**: 
  1. Check `GOOGLE_API_KEY` in `.env`
  2. Verify API key has access to `text-embedding-004` model
  3. Check API quota/limits

## Technical Details

### Embedding Model
- **Model**: `models/text-embedding-004` (Google Generative AI)
- **Dimensions**: 768
- **Similarity Metric**: Cosine similarity

### Chunking Strategy
- **Chunk Size**: 1000 characters (configurable via `CHUNK_SIZE`)
- **Overlap**: 250 characters (configurable via `CHUNK_OVERLAP`)
- **Splitter**: `RecursiveCharacterTextSplitter` from LangChain

### Vector Search Parameters
- **numCandidates**: `k * 5` (searches 5x more candidates than requested)
- **Limit**: `k` (default: 5 chunks)
- **Filter**: Applied before vector search for efficiency

## Files

- **RAG Service**: `app/services/rag.py` - Handles vector search retrieval
- **Embedding Service**: `app/services/embeddings.py` - Generates embeddings
- **Vector Index Service**: `app/services/vector_index_service.py` - Manages index verification
- **Document Processing**: `app/routers/departments.py` - Upload and process documents

## Testing

1. **Verify Index**: `python scripts/verify_vector_index.py`
2. **Upload Document**: POST to `/api/v1/departments/{id}/documents`
3. **Test RAG**: Ask a question via the bot - it should trigger `search_knowledge_base`
4. **Check Results**: RAG results are sent to frontend via RTVI messages

