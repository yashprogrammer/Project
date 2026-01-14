from typing import Dict, Any
import os
from dotenv import load_dotenv
from loguru import logger
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.services.llm_service import FunctionCallParams
from pipecat.transcriptions.language import Language

print("🚀 Starting Pipecat bot...")
print("⏳ Loading models and imports (20 seconds, first run only)\n")

logger.info("Loading Local Smart Turn Analyzer V3...")
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.audio.turn.smart_turn.local_smart_turn_v3 import LocalSmartTurnAnalyzerV3

logger.info("✅ Local Smart Turn Analyzer V3 loaded")
logger.info("Loading Silero VAD model...")
from pipecat.audio.vad.silero import SileroVADAnalyzer

logger.info("✅ Silero VAD model loaded")

from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.frames.frames import Frame, LLMMessagesAppendFrame, LLMRunFrame, TranscriptionFrame

logger.info("Loading pipeline components...")
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair
from pipecat.processors.frameworks.rtvi import RTVIConfig, RTVIObserver, RTVIProcessor
from pipecat.runner.types import RunnerArguments, WebSocketRunnerArguments
from pipecat.serializers.protobuf import ProtobufFrameSerializer
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.groq.llm import GroqLLMService
from pipecat.transports.base_transport import BaseTransport
from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)
from pipecat.processors.frameworks.rtvi import RTVIServerMessageFrame
from deepgram import LiveOptions
from pipecat.adapters.schemas.function_schema import FunctionSchema
from app.services.rag import RAGService
from app.config import settings

from datetime import datetime

class TextCaptureProcessor(FrameProcessor):
    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        if isinstance(frame, LLMMessagesAppendFrame):
            for message in frame.messages:
                if message.get("role") == "user":
                    await self.push_frame(
                        TranscriptionFrame(
                            text=message.get('content'),
                            user_id="agent",
                            timestamp=datetime.now().isoformat(),
                            language=Language.EN_IN
                        )
                    )
        await self.push_frame(frame, direction)

logger.info("✅ All components loaded successfully!")

load_dotenv(override=True)


async def run_bot(transport: BaseTransport, runner_args: RunnerArguments):
    logger.info(f"Starting bot")
    body: Dict[str, Any] = runner_args.body
    department_id: str = body.get("department_id", "")
    tenant_id: str = body.get("tenant_id", settings.TENANT_ID)
    session_id: str = body.get("session_id", "")
    user_id: str = body.get("user_id", settings.USER_ID)

    live_options = LiveOptions( 
        diarize=True
    )
    stt = DeepgramSTTService(
        api_key=os.getenv("DEEPGRAM_API_KEY"),
        live_options=live_options,
    )

    rtvi = RTVIProcessor(config=RTVIConfig(config=[]))

    async def search_knowledge_base(params: FunctionCallParams):
        try:
            query = params.arguments.get("query", "")
            rag_service = RAGService()
            retrieval_result = await rag_service.retrieve(
                query=query, 
                k=5, 
                department_id=department_id, 
                tenant_id=tenant_id
            )
            
            # Use clean data for LLM (no IDs, just content)
            clean_data = [
                {
                    "id": meta.chunk_id,
                    "content": chunk.text,
                }
                for chunk, meta in zip(retrieval_result.data,
                                    retrieval_result.metadata.chunks)
            ]

            await params.result_callback({"results": clean_data})
            
            # Send RAG results to frontend via RTVI
            await rtvi.push_frame(
                RTVIServerMessageFrame(
                    data={
                        "type": "search_knowledge_base",
                        "chunks": [
                            {
                                "id": meta.chunk_id,
                                "text": chunk.text,
                                "metadata": meta.model_dump()
                            }
                            for chunk, meta in zip(
                                retrieval_result.data,
                                retrieval_result.metadata.chunks
                            )
                        ]
                    }
                )
            )

        except Exception as e:
            logger.error(f"Error in search_knowledge_base: {e}")
            await params.result_callback({"results": []})

    search_tool = FunctionSchema(
        name="search_knowledge_base",
        description="Search the knowledge base for relevant information",
        properties={"query": {"type": "string"}},
        required=["query"]
    )
    
    llm = GroqLLMService(
        api_key=os.getenv("GROQ_API_KEY"),
        model=settings.GROQ_MODEL,
        base_url=settings.GROQ_BASE_URL,
    )

    llm.register_function(
        "search_knowledge_base",
        search_knowledge_base,
        cancel_on_interruption=False,
    )

    messages = [
        {
            "role": "system",
            "content":"""
                You are an AI assistant supporting a human call-center agent.  
                Your output must ALWAYS be a valid JSON object matching the following schema:

                {
                "sentiment": "<sentiment>",
                "intent": "<customer_intent>",
                "suggested_response": "<short_agent_response>",
                "agent_guidance": "<agent_guidance>",
                "facts": ["fact1", "fact2"],
                "sarcasm": {
                    "detected": false,
                    "confidence": 0.0,
                    "reason": null,
                    "type": null
                }
                }

                Strict behavioral rules:
                - Output ONLY a valid JSON object. Do not include explanations or extra text.
                - All fields must always be present.
                - All responses must be extremely concise.  
                - "suggested_response": max 12-15 words  
                - "agent_guidance": max 8-12 words  
                - "intent": max 2-4 words  
                - "sentiment": one word  
                - "sentiment" must be a single word (positive / neutral / negative / angry / frustrated / happy / satisfied / confused).
                - "facts": list of 2-3 most relevant facts from the knowledge base.
                - NEVER generate long paragraphs.

                Knowledge base rules:
                - When the customer asks a question or seeks information, call the `search_knowledge_base` tool.
                - Use ONLY facts returned from the knowledge base.
                - Facts must be listed exactly as found.  
                - If no facts are found: `facts: []`
                - NEVER invent or guess any information.
                - When using retrieved facts, cite the chunk ID(s) in square brackets **inside the `facts` array** exactly as: `[chunk_id]`.
                (Example: "facts": ["Policy covers repairs. [2f1c51...]", "Returns allowed in 7 days. [ab392e...]"])

                Content generation rules:
                - "suggested_response" must be a short, ready-to-speak sentence for the human agent.
                - "agent_guidance" must be a brief instruction for the human agent.
                - If the KB lacks the answer:  
                    - Suggested response must briefly apologize and ask the customer to clarify.
                    - If sentiment is negative: include a brief apology.
                    - If sentiment is positive: include brief appreciation.

                Goal:
                Provide the human agent with fast, efficient guidance suitable for real-time conversation.
            """,
        },
    ]

    context = LLMContext(messages, tools=ToolsSchema(standard_tools=[search_tool]))
    context_aggregator = LLMContextAggregatorPair(context)   

    pipeline = Pipeline([
        transport.input(),
        rtvi,  # RTVI processor
        TextCaptureProcessor(),
        stt,
        context_aggregator.user(),  # User responses
        llm,  # LLM
        transport.output(),  # Transport bot output
        context_aggregator.assistant(),  # Assistant spoken responses
    ])

    # Build observers list
    observers = [
        RTVIObserver(rtvi),
    ]

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
        observers=observers,
        cancel_on_idle_timeout=True,
        idle_timeout_secs=300,
    )

    @rtvi.event_handler("on_client_ready")
    async def on_client_ready(rtvi):
        await rtvi.set_bot_ready()

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info(f"Client connected")
        messages.append({"role": "system", "content": "Say hello and briefly introduce yourself."})
        await task.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info(f"Client disconnected")
        await task.cancel()

    runner = PipelineRunner(handle_sigint=runner_args.handle_sigint)

    try:
        await runner.run(task)
    except Exception as e:
        logger.error(f"Error in bot: {e}")
        raise e


async def bot(runner_args: WebSocketRunnerArguments):
    """Main bot entry point for the bot starter."""
    
    transport = FastAPIWebsocketTransport(
        websocket=runner_args.websocket,
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            add_wav_header=False,
            vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.2)),
            serializer=ProtobufFrameSerializer(),
            turn_analyzer=LocalSmartTurnAnalyzerV3(),
        ),
    )

    try:
        await run_bot(transport, runner_args)
    except Exception as e:
        logger.error(f"Error in bot: {e}")
        raise e


if __name__ == "__main__":
    from pipecat.runner.run import main
    main()

