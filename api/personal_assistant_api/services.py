"""
Service layer for interacting with the Personal Assistant orchestrator.
"""
import asyncio
import sys
import os
import time
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

# Add parent project to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

logger = logging.getLogger(__name__)


class BehaviourAnalystService:
    """Service to interact with the Main Orchestrator Graph (PersonalAssistant routing)."""
    
    def __init__(self):
        """Initialize the service and load the main orchestrator graph."""
        self.orchestrator = None
        self._agent_initialization_failed = False
        self._agent_error = None
        self._initialize_agent()
    
    def _initialize_agent(self):
        """
        Initialize the main orchestrator graph.
        
        This is wrapped with error handling to allow the API server to start
        even if agent initialization fails (e.g., due to async event loop issues).
        """
        try:
            logger.info("Attempting to import main_orchestrator_graph...")
            from graphs.main_graph import main_orchestrator_graph
            self.orchestrator = main_orchestrator_graph
            logger.info("✅ Main Orchestrator Graph initialized successfully")
        except RuntimeError as e:
            # Handle async event loop errors gracefully
            if "no current event loop" in str(e).lower() or "no running event loop" in str(e).lower():
                logger.warning(f"⚠️ Async event loop error during initialization (will retry on first use): {str(e)}")
                self._agent_initialization_failed = True
                self._agent_error = e
            else:
                logger.error(f"❌ Failed to initialize Main Orchestrator Graph: {str(e)}")
                self._agent_initialization_failed = True
                self._agent_error = e
        except ImportError as e:
            logger.error(f"❌ Import Error - Parent project not accessible: {str(e)}", exc_info=True)
            logger.error(f"   Current sys.path: {sys.path}")
            self._agent_initialization_failed = True
            self._agent_error = e
        except Exception as e:
            logger.error(f"❌ Failed to initialize Main Orchestrator Graph: {str(e)}", exc_info=True)
            self._agent_initialization_failed = True
            self._agent_error = e
            self._agent_initialization_failed = True
            self._agent_error = e
    
    def generate_request_id(self) -> str:
        """Generate a unique request ID."""
        return f"analysis_{uuid.uuid4().hex[:12]}"
    
    async def run_analysis(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run analysis through the main orchestrator graph.
        
        Args:
            query: The user's query/message
            filters: Optional filters for analysis
            metadata: Optional metadata about the request
            request_id: Optional request ID (generated if not provided)
            
        Returns:
            Dictionary containing orchestrator results
        """
        if not request_id:
            request_id = self.generate_request_id()
        start_time = time.time()
        
        try:
            # If orchestrator wasn't initialized at startup (e.g., due to transient import error), try again now
            if self.orchestrator is None and self._agent_initialization_failed:
                logger.info("Re-attempting orchestrator initialization on first use…")
                self._initialize_agent()
                if self.orchestrator is None:
                    raise RuntimeError(f"Main Orchestrator not initialized: {self._agent_error}")
            # Prepare the input for the orchestrator according to OrchestratorState
            user_id = metadata.get("user_id", "3") if metadata else "3"
            user_name = metadata.get("user_name", "User") if metadata else "User"
            orchestrator_input = {
                "user_id": user_id,
                "user_name": user_name,
                "user_message": query,
                "next_step": "conversation",  # Will be set by personal_assistant_orchestrator
                "agent_result": {},
                "routing_decision": "",
                "routing_message": "",
                "is_awaiting_data": False,
            }
            
            logger.info(f"Starting orchestrator for request {request_id}: {query}")
            logger.info(f"Orchestrator input: user_id={user_id}, user_name={user_name}")
            
            # Run the orchestrator with higher recursion limit for LangGraph
            config = {'recursion_limit': 500}
            
            if hasattr(self.orchestrator, 'ainvoke'):
                result = await self.orchestrator.ainvoke(orchestrator_input, config=config)
            else:
                # Fallback to sync invoke in thread pool
                def sync_invoke():
                    return self.orchestrator.invoke(orchestrator_input, config=config)
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, sync_invoke)
            
            processing_time = int((time.time() - start_time) * 1000)
            
            # Format the response from OrchestratorState
            response = {
                "request_id": request_id,
                "status": "completed",
                "query": query,
                "user_id": user_id,
                "user_name": user_name,
                "processing_time_ms": processing_time,
                "completed_at": datetime.now().isoformat(),
                "routing_decision": result.get("routing_decision", ""),
                "routing_message": result.get("routing_message", ""),
                "agent_result": result.get("agent_result", {}),
                "is_awaiting_data": result.get("is_awaiting_data", False),
                "raw_response": result
            }
            
            logger.info(f"Orchestrator completed for request {request_id} in {processing_time}ms")
            logger.info(f"Routing: {response.get('routing_decision')}, Response: {response.get('final_response', '')[:100]}")
            return response
            
        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            logger.error(f"Orchestrator failed for request {request_id}: {str(e)}", exc_info=True)
            
            return {
                "request_id": request_id,
                "status": "failed",
                "query": query,
                "processing_time_ms": processing_time,
                "error": str(e),
                "completed_at": datetime.now().isoformat()
            }
    
    async def run_bulk_analysis(
        self,
        queries: List[str],
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run multiple queries through the orchestrator in parallel.
        
        Args:
            queries: List of queries to process
            filters: Optional filters for all queries
            
        Returns:
            Dictionary containing bulk orchestrator results
        """
        batch_id = f"batch_{uuid.uuid4().hex[:12]}"
        start_time = time.time()
        
        try:
            logger.info(f"Starting bulk orchestrator batch {batch_id} with {len(queries)} queries")
            
            # Run all queries concurrently through the orchestrator
            tasks = [
                self.run_analysis(query, filters)
                for query in queries
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle exceptions in results
            successful_results = []
            failed_results = []
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    failed_results.append({
                        "query": queries[i],
                        "error": str(result)
                    })
                elif result.get("status") == "failed":
                    failed_results.append(result)
                else:
                    successful_results.append(result)
            
            processing_time = int((time.time() - start_time) * 1000)
            
            response = {
                "batch_id": batch_id,
                "status": "completed",
                "total_requests": len(queries),
                "successful": len(successful_results),
                "failed": len(failed_results),
                "processing_time_ms": processing_time,
                "completed_at": datetime.now().isoformat(),
                "results": successful_results,
                "errors": failed_results if failed_results else None
            }
            
            logger.info(f"Bulk orchestrator completed for batch {batch_id}: {len(successful_results)}/{len(queries)} successful")
            return response
            
        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            logger.error(f"Bulk orchestrator failed for batch {batch_id}: {str(e)}", exc_info=True)
            
            return {
                "batch_id": batch_id,
                "status": "failed",
                "error": str(e),
                "processing_time_ms": processing_time,
                "completed_at": datetime.now().isoformat()
            }


# Global service instance
_service_instance = None


def get_analyst_service() -> BehaviourAnalystService:
    """Get or create the global service instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = BehaviourAnalystService()
    return _service_instance
