"""Service layer for the Personal Assistant API."""
import asyncio
import os
import sys
import time
import logging
from typing import Any, Dict, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
logger = logging.getLogger(__name__)


class PersonalAssistantService:
    def __init__(self):
        self.orchestrator = None
        self._init_error: Optional[Exception] = None
        self._initialize()

    def _initialize(self) -> None:
        try:
            from graphs.main_graph import main_orchestrator_graph

            self.orchestrator = main_orchestrator_graph
            logger.info("Orchestrator initialized")
        except ImportError as ie:
            if "Discriminator" in str(ie):
                logger.error("Pydantic version incompatibility detected: %s", ie)
                logger.error("Make sure Pydantic v2.x is installed")
            else:
                logger.error("Failed to initialize orchestrator: %s", ie)
            self._init_error = ie
        except Exception as ex:
            logger.error("Failed to initialize orchestrator: %s", ex)
            self._init_error = ex

    def _ensure_orchestrator(self):
        if self.orchestrator is None and self._init_error:
            self._initialize()
        if self.orchestrator is None:
            raise RuntimeError("Orchestrator not initialized")
        return self.orchestrator

    async def run_analysis(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        start_time = time.perf_counter()
        metadata = metadata or {}

        try:
            orchestrator = self._ensure_orchestrator()

            orchestrator_input = {
                "user_id": metadata.get("user_id", "3"),
                "conversation_id": metadata.get("conversation_id", ""),
                "user_name": metadata.get("user_name", "User"),
                "user_message": query,
            }
            if filters:
                orchestrator_input["filters"] = filters

            if hasattr(orchestrator, "ainvoke"):
                result = await orchestrator.ainvoke(
                    orchestrator_input,
                    config={"recursion_limit": 500},
                )
            else:
                loop = asyncio.get_running_loop()
                result = await loop.run_in_executor(
                    None,
                    lambda: orchestrator.invoke(
                        orchestrator_input,
                        config={"recursion_limit": 500},
                    ),
                )

            processing_time = int((time.perf_counter() - start_time) * 1000)

            return {
                "status": "completed",
                "query": query,
                "processing_time_ms": processing_time,
                "final_output": result.get("final_output") or result.get("message", ""),
                "data": result.get("data"),
                "has_data": result.get("has_data", False),
                "agents_used": result.get("agents_used", ""),
            }
        except Exception as exc:
            processing_time = int((time.perf_counter() - start_time) * 1000)
            logger.error("Error during run_analysis: %s", exc, exc_info=True)
            return {
                "status": "failed",
                "query": query,
                "error": str(exc),
                "processing_time_ms": processing_time,
            }


_service: Optional[PersonalAssistantService] = None


def get_analyst_service() -> PersonalAssistantService:
    global _service
    if _service is None:
        _service = PersonalAssistantService()
    return _service
