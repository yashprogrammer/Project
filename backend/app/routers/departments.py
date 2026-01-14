import os
import tempfile
import uuid
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, UploadFile, File, Form
from loguru import logger
from bson import ObjectId

from app.database import get_database
from app.models.department import Department
from app.models.document import Document
from app.services.text_extraction import TextExtractionService
from app.services.embeddings import EmbeddingService
from app.config import settings

router = APIRouter()


@router.post("/", response_model=Department, status_code=status.HTTP_201_CREATED)
async def create_department(department: Department):
    """Create a new department"""
    db = get_database()
    
    # Check if department name already exists
    existing = await db.departments.find_one({"name": department.name, "tenant_id": department.tenant_id})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Department with this name already exists"
        )
    
    # Add timestamps
    from datetime import datetime
    now = datetime.utcnow()
    department_dict = department.model_dump(exclude={"id"}, exclude_none=True)
    department_dict["created_at"] = now
    department_dict["updated_at"] = now
    
    # Insert into database
    result = await db.departments.insert_one(department_dict)
    department_dict["_id"] = result.inserted_id
    
    return Department(**department_dict)


@router.get("/", response_model=List[Department], status_code=status.HTTP_200_OK)
async def get_departments():
    """Get all departments"""
    db = get_database()
    departments = await db.departments.find({}).to_list(length=None)
    return [Department(**dept) for dept in departments]


@router.get("/{department_id}", response_model=Department, status_code=status.HTTP_200_OK)
async def get_department(department_id: str):
    """Get a department by ID"""
    db = get_database()
    department = await db.departments.find_one({"_id": ObjectId(department_id)})
    if not department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found"
        )
    return Department(**department)


@router.post("/{department_id}/documents", status_code=status.HTTP_201_CREATED)
async def upload_department_documents(
    department_id: str,
    files: List[UploadFile] = File(...),
    description: Optional[str] = Form(None),
):
    """
    Upload documents to a department and process them synchronously.
    For MVP, processes embeddings immediately (no background tasks).
    """
    db = get_database()
    
    # Verify department exists
    department = await db.departments.find_one({"_id": ObjectId(department_id)})
    if not department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found"
        )
    
    text_extractor = TextExtractionService()
    embedding_service = EmbeddingService()
    tenant_id = settings.TENANT_ID
    
    created_docs = []
    
    for file in files:
        try:
            # Read file content
            data = await file.read()
            size = len(data)
            original_name = file.filename or "upload.bin"
            content_type = file.content_type or "application/octet-stream"
            
            logger.info(f"Processing file: {original_name} ({size} bytes)")
            
            # Check if format is supported
            if not text_extractor.is_supported(content_type, original_name):
                logger.warning(f"Unsupported file format: {content_type}")
                continue
            
            # Save to temp file for processing
            temp_file_path = None
            try:
                _, ext = os.path.splitext(original_name)
                with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                    tmp.write(data)
                    temp_file_path = tmp.name
                
                # Extract text
                extracted_text = text_extractor.extract_text(temp_file_path, content_type)
                
                if not extracted_text or not extracted_text.strip():
                    logger.warning(f"No text extracted from {original_name}")
                    continue
                
                # Split into chunks
                chunks = embedding_service.split_text(extracted_text)
                logger.info(f"Split into {len(chunks)} chunks")
                
                if not chunks:
                    logger.warning(f"No chunks created from {original_name}")
                    continue
                
                # Generate embeddings for all chunks
                embeddings = embedding_service.embed_texts(chunks)
                logger.info(f"Generated {len(embeddings)} embeddings")
                
                # Create document metadata
                storage_key = f"{tenant_id}/departments/{department_id}/{uuid.uuid4().hex}-{original_name}"
                from datetime import datetime
                now = datetime.utcnow()
                
                doc_dict = {
                    "department_id": ObjectId(department_id),
                    "tenant_id": tenant_id,
                    "file_name": original_name,
                    "content_type": content_type,
                    "size": size,
                    "storage_key": storage_key,
                    "uploaded_by": settings.USER_ID,
                    "description": description,
                    "document_type": "knowledge",
                    "embedding_status": "processing",
                    "created_at": now,
                    "updated_at": now,
                }
                
                # Insert document
                doc_result = await db.documents_metadata.insert_one(doc_dict)
                document_id = doc_result.inserted_id
                logger.info(f"Document inserted: {document_id}")
                
                # Insert chunks with embeddings
                chunk_documents = []
                for index, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
                    chunk_doc = {
                        "document_id": document_id,
                        "department_id": ObjectId(department_id),
                        "tenant_id": tenant_id,
                        "file_name": original_name,
                        "chunk_id": str(uuid.uuid4()),
                        "chunk_index": index,
                        "text": chunk_text,
                        "embedding": embedding,
                        "is_disabled": False,
                    }
                    chunk_documents.append(chunk_doc)
                
                # Bulk insert chunks
                if chunk_documents:
                    await db[settings.DOCUMENT_CHUNKS_COLLECTION].insert_many(chunk_documents)
                    logger.info(f"Inserted {len(chunk_documents)} chunks")
                
                # Update document status to completed
                await db.documents_metadata.update_one(
                    {"_id": document_id},
                    {"$set": {"embedding_status": "completed", "updated_at": datetime.utcnow()}}
                )
                
                doc_dict["_id"] = document_id
                created_docs.append(doc_dict)
                
                logger.success(f"Successfully processed {original_name}")
                
            finally:
                # Clean up temp file
                if temp_file_path and os.path.exists(temp_file_path):
                    try:
                        os.remove(temp_file_path)
                    except Exception as e:
                        logger.warning(f"Failed to delete temp file: {e}")
                        
        except Exception as e:
            logger.error(f"Error processing file {file.filename}: {e}", exc_info=True)
            continue
    
    return {"documents": created_docs, "count": len(created_docs)}


@router.get("/{department_id}/documents", status_code=status.HTTP_200_OK)
async def list_department_documents(department_id: str):
    """List all documents for a department"""
    db = get_database()
    
    # Verify department exists
    department = await db.departments.find_one({"_id": ObjectId(department_id)})
    if not department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found"
        )
    
    documents = await db.documents_metadata.find({
        "department_id": ObjectId(department_id),
        "is_disabled": {"$ne": True}
    }).to_list(length=1000)
    
    return {"documents": documents, "count": len(documents)}

