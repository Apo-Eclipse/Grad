"""Service layer for the Personal Assistant API."""
import asyncio
import sys
import os
import time
from typing import Dict, Any, Optional
from datetime import datetime
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
logger = logging.getLogger(__name__)


class PersonalAssistantService:
    def __init__(self):
        self.orchestrator = None
        self._init_error = None
        self._initialize()
    
    def _initialize(self):
        try:
            from graphs.main_graph import main_orchestrator_graph
            self.orchestrator = main_orchestrator_graph
            logger.info("Orchestrator initialized")
        except ImportError as ie:
            if "Discriminator" in str(ie):
                logger.error(f"Pydantic version incompatibility: {ie}")
                logger.error("Make sure Pydantic v2.x is installed")
            else:
                logger.error(f"Failed to initialize orchestrator: {ie}")
            self._init_error = ie
        except Exception as e:
            logger.error(f"Failed to initialize orchestrator: {e}")
            self._init_error = e
    
    async def run_analysis(self, query: str, filters: Optional[Dict] = None, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        start_time = time.time()
        
        try:
            if self.orchestrator is None:
                if self._init_error:
                    self._initialize()
                if self.orchestrator is None:
                    raise RuntimeError("Orchestrator not initialized")
            
            user_id = metadata.get("user_id", "3") if metadata else "3"
            user_name = metadata.get("user_name", "User") if metadata else "User"
            conversation_id = metadata.get("conversation_id", "") if metadata else ""
            
            orchestrator_input = {
                "user_id": user_id,
                "conversation_id": conversation_id,
                "user_name": user_name,
                "user_message": query,
            }
            
            if hasattr(self.orchestrator, 'ainvoke'):
                result = await self.orchestrator.ainvoke(orchestrator_input, config={'recursion_limit': 500})
            else:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, lambda: self.orchestrator.invoke(orchestrator_input, config={'recursion_limit': 500}))
            
            processing_time = int((time.time() - start_time) * 1000)
            
            return {
                "status": "completed",
                "query": query,
                "processing_time_ms": processing_time,
                "final_output": result.get("final_output") or result.get("message", ""),
                "data": result.get("data"),
                "has_data": result.get("has_data", False),
                "agents_used": result.get("agents_used", ""),
            }
        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            logger.error(f"Error: {e}", exc_info=True)
            return {"status": "failed", "query": query, "error": str(e), "processing_time_ms": processing_time}


_service = None

def get_analyst_service() -> PersonalAssistantService:
    global _service
    if _service is None:
        _service = PersonalAssistantService()
    return _service
