# Why We Create a Vector Search Index

## Understanding the Big Picture

### The Problem We're Solving

When a user asks a question like "What is your return policy?", we need to:
1. Find the most relevant information from thousands of document chunks
2. Do this quickly (milliseconds, not seconds)
3. Only search within the right department/tenant

**Without a vector index**: MongoDB would have to scan every single document chunk and calculate similarity for each one. This is **extremely slow** (could take minutes for large datasets).

**With a vector index**: MongoDB uses optimized algorithms (like HNSW - Hierarchical Navigable Small World) to find similar vectors **very quickly** (milliseconds).

---

## Part 1: Why Choose a Specific Collection?

### Collection = Where Your Data Lives

Think of a MongoDB collection like a **table in a database** or a **folder with files**:

```
MongoDB Database (mvp_db)
├── departments (collection)
│   └── Stores department info
├── documents_metadata (collection)
│   └── Stores document info (file names, upload dates, etc.)
└── document_chunks (collection)  ← THIS IS WHERE WE CREATE THE INDEX
    └── Stores:
        - Chunk text: "Our return policy allows returns within 30 days..."
        - Embedding: [0.123, -0.456, 0.789, ...] (768 numbers)
        - Metadata: department_id, tenant_id, file_name, etc.
```

### Why `document_chunks` Collection?

1. **This is where embeddings are stored**
   - When you upload a document, it gets split into chunks
   - Each chunk gets an embedding (vector of 768 numbers)
   - These chunks with embeddings are stored in `document_chunks`

2. **This is what we need to search**
   - When a user asks a question, we convert it to an embedding
   - We need to find similar embeddings in this collection
   - The index makes this search fast

3. **One index per collection**
   - MongoDB Atlas creates indexes on specific collections
   - You can't create one index that searches across multiple collections
   - So we create the index on the collection that has the data we need to search

### Example Flow:

```
User asks: "What is your return policy?"

1. Convert question to embedding: [0.1, -0.2, 0.3, ...]
2. Search in document_chunks collection (using vector index)
3. Find chunks with similar embeddings
4. Return those chunks to the LLM
```

---

## Part 2: Why This Specific JSON Definition?

The JSON tells MongoDB Atlas **HOW** to build the index. Let's break it down:

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

### Field 1: The Vector Field (The Main One)

```json
{
  "type": "vector",
  "path": "embedding",
  "numDimensions": 768,
  "similarity": "cosine"
}
```

**What it means:**
- `"type": "vector"` → "This field contains vector embeddings (arrays of numbers)"
- `"path": "embedding"` → "The field name in your documents is `embedding`"
- `"numDimensions": 768` → "Each embedding has exactly 768 numbers"
- `"similarity": "cosine"` → "Use cosine similarity to measure how similar vectors are"

**Why it's needed:**
- This tells MongoDB: "Build a special index on the `embedding` field that can quickly find similar vectors"
- Without this, MongoDB doesn't know that `embedding` contains vectors that need special handling
- The 768 dimensions must match your embedding model (Google's text-embedding-004 produces 768-dimensional vectors)

**Example document in collection:**
```json
{
  "_id": ObjectId("..."),
  "text": "Our return policy allows returns within 30 days...",
  "embedding": [0.123, -0.456, 0.789, ...],  // 768 numbers
  "department_id": ObjectId("..."),
  "tenant_id": "mvp_tenant"
}
```

### Fields 2-4: Filter Fields (For Fast Filtering)

```json
{
  "type": "filter",
  "path": "department_id"
}
```

**What it means:**
- `"type": "filter"` → "This field is used for filtering, not vector search"
- `"path": "department_id"` → "The field name is `department_id`"

**Why it's needed:**
- When searching, we often want to filter: "Find similar chunks, but ONLY from department X"
- By including these in the index, MongoDB can filter **before** doing the expensive vector search
- This makes queries much faster

**Example query:**
```javascript
// Find similar chunks, but only from department "abc123"
{
  "$vectorSearch": {
    "index": "vector_index",
    "path": "embedding",
    "queryVector": [0.1, -0.2, 0.3, ...],
    "filter": {
      "department_id": ObjectId("abc123"),  // ← Filter applied BEFORE vector search
      "is_disabled": false
    }
  }
}
```

**Without filter fields in index:**
- MongoDB would find all similar vectors first
- Then filter out unwanted ones
- **Slower** because it searches more data than needed

**With filter fields in index:**
- MongoDB filters first (fast)
- Then searches only the relevant subset
- **Much faster**

---

## Real-World Analogy

Think of it like a **library**:

### Without Index:
- You want books about "cooking"
- Librarian checks every single book one by one
- Takes hours/days

### With Index (like our vector index):
- You want books about "cooking"
- Librarian uses a catalog (index) that's organized by topic
- Finds relevant books in seconds

### The Collection Choice:
- You choose which **section** of the library to index
- We choose `document_chunks` because that's where all our "books" (chunks) are stored

### The JSON Definition:
- Tells the librarian **how to organize the catalog**
- "Organize by topic (vector similarity)"
- "Also note which department (filter field) each book belongs to"
- "And note if a book is disabled (filter field)"

---

## Summary

1. **Why choose `document_chunks` collection?**
   - Because that's where we store chunks with embeddings
   - That's what we need to search
   - Indexes are collection-specific

2. **Why this JSON?**
   - `"vector"` type tells MongoDB to build a fast similarity search index
   - `"filter"` types tell MongoDB which fields to use for fast filtering
   - The dimensions (768) must match your embedding model
   - The similarity metric (cosine) determines how "similarity" is calculated

3. **What happens without the index?**
   - Vector search queries would be extremely slow (scanning all documents)
   - Or they might not work at all (depending on MongoDB version)

4. **What happens with the index?**
   - Vector search queries are fast (milliseconds)
   - Filtering is efficient
   - Your RAG system can respond quickly to user questions

---

## Technical Deep Dive

### How Vector Search Works (Simplified)

1. **Index Creation:**
   - MongoDB reads all embeddings from `document_chunks`
   - Builds a special data structure (like a tree or graph)
   - Organizes vectors so similar ones are "close" in the structure

2. **Query Time:**
   - You provide a query embedding: `[0.1, -0.2, 0.3, ...]`
   - MongoDB uses the index structure to quickly find "nearby" vectors
   - Returns the most similar ones

3. **Filtering:**
   - If you specify filters (department_id, etc.), MongoDB applies them
   - This happens efficiently because those fields are also indexed

### Why 768 Dimensions?

- Google's `text-embedding-004` model produces 768-dimensional vectors
- Each dimension captures some aspect of meaning
- More dimensions = more nuanced understanding, but also more storage/compute
- 768 is a good balance for text embeddings

### Why Cosine Similarity?

- Measures the angle between two vectors (not distance)
- Good for text embeddings because it focuses on direction, not magnitude
- Values range from -1 (opposite) to 1 (identical)
- 0 means orthogonal (unrelated)

---

## Next Steps

Once you understand this:
1. Create the index in MongoDB Atlas using the JSON definition
2. Upload documents - they'll be chunked and embedded
3. Ask questions - the system will use the index to find relevant chunks quickly

The index is the "magic" that makes semantic search fast!

