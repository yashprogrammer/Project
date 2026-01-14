# Sens-AI MVP

A simplified MVP version of the Sens-AI platform featuring a working Pipecat voice bot with RAG (Retrieval-Augmented Generation) integration.

## Features

- **Real-time Voice Bot**: Pipecat-powered voice assistant with Deepgram STT and Groq LLM
- **RAG System**: MongoDB Atlas vector search with Google AI embeddings
- **Document Upload**: Synchronous document processing (PDF, DOCX, TXT, MD)
- **Real-time Chat Interface**: React frontend showing bot responses with RAG results

## Architecture

- **Backend**: FastAPI with Pipecat bot pipeline
- **Frontend**: React + Vite with Pipecat client
- **Database**: MongoDB Atlas with vector search index
- **AI Services**: Deepgram (STT), Groq (LLM), Google AI (Embeddings)

## Prerequisites

1. **MongoDB Atlas**:
   - Create a cluster
   - Create a vector search index named `vector_index` on the `document_chunks` collection
   - Index configuration:
     ```json
     {
       "fields": [
         {
           "type": "vector",
           "path": "embedding",
           "numDimensions": 768,
           "similarity": "cosine"
         }
       ]
     }
     ```

2. **API Keys**:
   - Deepgram API key
   - Groq API key
   - Google AI API key

3. **Runtime**:
   - Python 3.12+
   - Node.js 18+

## Setup

### Backend

1. Navigate to backend directory:
   ```bash
   cd backend
   ```

2. Create virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -e .
   ```

4. Create `.env` file from `.env.example`:
   ```bash
   cp .env.example .env
   ```

5. Edit `.env` with your configuration:
   ```env
   MONGO_URL=mongodb+srv://user:password@cluster.mongodb.net
   DB_NAME=mvp_db
   DEEPGRAM_API_KEY=your-key
   GROQ_API_KEY=your-key
   GOOGLE_API_KEY=your-key
   ```

6. Start the backend:
   ```bash
   python -m app.main
   # Or with uvicorn:
   uvicorn app.main:app --reload --port 8000
   ```

### Frontend

1. Navigate to frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Create `.env` file:
   ```env
   VITE_API_BASE_URL=http://localhost:8000/api/v1
   VITE_PIPECAT_ENDPOINT=/stream/connect
   ```

4. Start the frontend:
   ```bash
   npm run dev
   ```

The frontend will be available at `http://localhost:5173`

## Usage

1. **Create a Department**:
   ```bash
   curl -X POST http://localhost:8000/api/v1/departments/ \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Support",
       "description": "Customer Support Department",
       "tenant_id": "mvp_tenant"
     }'
   ```

2. **Upload Documents**:
   ```bash
   curl -X POST http://localhost:8000/api/v1/departments/{department_id}/documents \
     -F "files=@document.pdf" \
     -F "description=Product manual"
   ```

3. **Use the Chat Interface**:
   - Open `http://localhost:5173` in your browser
   - Select a department
   - Click "Start" to connect to the bot
   - Speak or type messages
   - The bot will search the knowledge base and display results with citations

## Project Structure

```
project/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app
│   │   ├── config.py            # Settings
│   │   ├── database.py          # MongoDB connection
│   │   ├── bot.py               # Pipecat bot pipeline
│   │   ├── routers/
│   │   │   ├── stream.py        # WebSocket endpoint
│   │   │   └── departments.py  # Department + document APIs
│   │   ├── services/
│   │   │   ├── rag.py           # RAG retrieval
│   │   │   ├── embeddings.py    # Google AI embeddings
│   │   │   └── text_extraction.py
│   │   └── models/
│   ├── pyproject.toml
│   └── .env
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   └── Stream.tsx
│   │   ├── components/
│   │   │   ├── RealTimeChatPanel.tsx
│   │   │   ├── BotMessageBubble.tsx
│   │   │   └── BotJsonCard.tsx
│   │   ├── hooks/
│   │   │   └── pipecat-chat-events.ts
│   │   └── types/
│   └── package.json
└── README.md
```

## Key Differences from Production

- **No Kafka**: Direct MongoDB writes
- **No Celery**: Synchronous document processing
- **No Redis**: No caching
- **No Authentication**: Hardcoded tenant/user IDs
- **Single Tenant**: Simplified multi-tenant support

## Troubleshooting

1. **Vector Search Returns No Results**:
   - Verify vector index exists in MongoDB Atlas
   - Check index name matches `VECTOR_INDEX_NAME` in config
   - Ensure documents have `embedding_status: completed`

2. **WebSocket Connection Fails**:
   - Check CORS configuration
   - Verify department exists
   - Review server logs for errors

3. **Document Upload Fails**:
   - Check file format is supported (PDF, DOCX, TXT, MD)
   - Verify Google API key is valid
   - Check MongoDB connection

## License

[Your License Here]
