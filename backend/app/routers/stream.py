import uuid
from typing import Dict, Any
from fastapi import APIRouter, WebSocket, Request, WebSocketDisconnect, HTTPException, status
from loguru import logger
from bson import ObjectId

from app.bot import bot
from pipecat.runner.types import WebSocketRunnerArguments
from app.database import get_database
from app.config import settings

router = APIRouter()


@router.post("/connect")
async def bot_connect(request: Request) -> Dict[str, Any]:
    """
    Get WebSocket URL for connecting to the bot.
    For MVP, we use hardcoded tenant/user IDs.
    """
    body: Dict[str, Any] = await request.json()
    department_id: str = body.get("department_id", "")
    
    if not department_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="department_id is required"
        )
    
    # Verify department exists
    db = get_database()
    try:
        department = await db.departments.find_one({"_id": ObjectId(department_id)})
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid department_id format"
        )
    
    if not department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Department {department_id} not found"
        )
    
    ws_scheme = "wss" if request.url.scheme == "https" else "ws"
    ws_url = f"{ws_scheme}://{request.url.netloc}/api/v1/stream/ws/{department_id}"
    
    return {"ws_url": ws_url}


@router.websocket("/ws/{department_id}")
async def websocket_endpoint(websocket: WebSocket, department_id: str):
    """
    WebSocket endpoint for real-time bot interaction.
    For MVP, uses hardcoded tenant_id and user_id from config.
    """
    await websocket.accept()
    
    logger.info(f"WebSocket connection accepted for department: {department_id}")
    
    try:
        # Verify department exists
        db = get_database()
        department = await db.departments.find_one({"_id": ObjectId(department_id)})
        
        if not department:
            logger.error(f"Department {department_id} not found")
            await websocket.close(code=4004, reason="Department not found")
            return

        # Prepare body for bot
        body = {
            "department_id": department_id,
            "tenant_id": settings.TENANT_ID,
            "session_id": str(uuid.uuid4()),
            "user_id": settings.USER_ID,
        }

        # Start bot (this blocks until connection ends)
        await bot(WebSocketRunnerArguments(
            websocket=websocket,
            body=body,
        ))
        
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"Error in stream handler: {e}")
        try:
            await websocket.close(code=1011, reason=str(e))
        except:
            pass

