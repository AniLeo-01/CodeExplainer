import os
import uuid
import logging
from typing import Dict, Any, Optional

from fastmcp import FastMCP

from app.routing.router import route
from app.memory.store import ConversationStore
from app.memory.models import RoutingDecision, UserContext
from app.synthesis.synthesizer import synthesize
from app.llm import extract_entities

from app.clients.graph_agent import (
    find_entity, 
    query_graph, 
    get_dependencies, 
    get_dependents, 
    find_related,
)
from app.clients.code_agent import analyze_function, explain
from app.clients.errors import AgentCallError

# Setup logging with explicit format and force=True to override any existing config
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True
)
logger = logging.getLogger(__name__)
# Also ensure it outputs to stdout
import sys
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# ---------------------------------------------------------
# MCP Setup
# ---------------------------------------------------------
mcp = FastMCP(name="Orchestrator Agent")

# Single source of truth for conversation memory
memory = ConversationStore()

# ---------------------------------------------------------
# MCP TOOL: analyze_query
# ---------------------------------------------------------
@mcp.tool
async def analyze_query(query: str) -> dict:
    """
    Classify query intent and determine candidate agents.
    """
    return await route(query)


# ---------------------------------------------------------
# MCP TOOL: route_to_agents
# ---------------------------------------------------------
@mcp.tool
async def route_to_agents(query: str, session_id: Optional[str] = None) -> dict:
    """
    Determine which agents should handle the query and
    persist routing decision.
    """
    session_id = session_id or str(uuid.uuid4())
    analysis = await route(query)

    memory.add_routing_decision(
        session_id,
        RoutingDecision(
            query=query,
            intent=analysis["intent"],
            agents=analysis["agents"],
        ),
    )

    return {
        "session_id": session_id,
        "query": query,
        "intent": analysis["intent"],
        "agents": analysis["agents"],
    }


# ---------------------------------------------------------
# MCP TOOL: get_conversation_context
# ---------------------------------------------------------
@mcp.tool
async def get_conversation_context(session_id: str) -> dict:
    """
    Retrieve full conversation context for a session.
    """
    return {
        "session_id": session_id,
        "history": memory.get_history(session_id),
        "routing": memory.get_routing_history(session_id),
        "user_context": memory.get_user_context(session_id),
    }


# ---------------------------------------------------------
# MCP TOOL: synthesize_response
# ---------------------------------------------------------
@mcp.tool
async def synthesize_response(
    query: str,
    session_id: Optional[str] = None,
    user_context: Optional[Dict[str, Any]] = None,
) -> dict:
    """
    Orchestrate agent calls and synthesize final response.
    """
    session_id = session_id or str(uuid.uuid4())
    analysis = await route(query)
    
    # Log routing decision (both logger and print for visibility)
    routing_msg = f"[ROUTING] Query: '{query}' | Intent: {analysis.get('intent')} | Agents: {analysis.get('agents')}"
    logger.info(routing_msg)
    print(routing_msg, flush=True)

    # ---------------------------------------------
    # Handle simple greetings without agent calls
    # ---------------------------------------------
    if analysis.get("intent") == "greeting" or not analysis.get("agents"):
        greeting_responses = {
            "hi": "Hello! I'm a codebase assistant. How can I help you explore the indexed repository?",
            "hello": "Hi there! I can help you understand the indexed codebase. What would you like to know?",
            "hey": "Hey! Ready to help you explore the codebase. What are you curious about?",
            "thanks": "You're welcome! Let me know if you have more questions.",
            "thank you": "Happy to help! Feel free to ask more questions about the codebase.",
            "bye": "Goodbye! Come back anytime you have questions.",
            "goodbye": "See you later! Happy coding!",
            "ok": "Got it! What would you like to know about the codebase?",
            "okay": "Alright! Feel free to ask me anything about the indexed repository.",
            "yes": "Great! What would you like to explore in the repository?",
            "no": "No problem. Let me know when you have questions!",
            "sure": "Perfect! What can I help you with?",
        }
        query_lower = query.lower().strip().rstrip('!?.')
        response = greeting_responses.get(query_lower, "Hi! I'm here to help you explore the indexed codebase. Ask me about classes, functions, or how things work!")
        
        memory.add_turn(session_id=session_id, query=query, response=response)
        return {"session_id": session_id, "response": response}

    # ---------------------------------------------
    # Persist user context (if provided)
    # ---------------------------------------------
    if user_context:
        memory.set_user_context(
            session_id,
            UserContext(**user_context),
        )

    agent_outputs: Dict[str, Any] = {}

    # ---------------------------------------------
    # Extract entities from natural language query
    # ---------------------------------------------
    extracted = await extract_entities(query)
    entity_name = extracted.get("entity_name")
    secondary_entity = extracted.get("secondary_entity")
    query_type = extracted.get("query_type", "find_entity")
    relationship = extracted.get("relationship")

    # ---------------------------------------------
    # Graph Query Agent
    # ---------------------------------------------
    if "graph_query" in analysis["agents"]:
        try:
            if query_type == "general_query":
                # For general queries, skip graph query - let LLM synthesize from knowledge
                agent_outputs["graph_query"] = {"info": "General query - no specific entity to look up"}
            elif query_type == "find_entity" and entity_name:
                # Look up specific entity
                agent_outputs["graph_query"] = await find_entity(entity_name)
                # If comparing two entities, look up the second one too
                if secondary_entity:
                    second_result = await find_entity(secondary_entity)
                    agent_outputs["graph_query_secondary"] = second_result
            elif query_type == "get_dependencies" and entity_name:
                # Find what entity depends on
                agent_outputs["graph_query"] = await get_dependencies(entity_name)
            elif query_type == "get_dependents" and entity_name:
                # Find what depends on entity
                agent_outputs["graph_query"] = await get_dependents(entity_name)
            elif query_type == "find_related" and entity_name and relationship:
                # Find related entities by relationship
                agent_outputs["graph_query"] = await find_related(entity_name, relationship)
            elif entity_name:
                # Fallback: if we have an entity name, try finding it
                agent_outputs["graph_query"] = await find_entity(entity_name)
            else:
                # No entity found, skip graph query for this type
                agent_outputs["graph_query"] = {"info": "No specific entity identified in query"}
        except AgentCallError as e:
            agent_outputs["graph_query"] = {"error": str(e)}

    # ---------------------------------------------
    # Code Analyst Agent
    # ---------------------------------------------
    if "code_analyst" in analysis["agents"]:
        try:
            # Use extracted entity name if available
            search_term = entity_name if entity_name else query
            call_msg = f"[CODE_ANALYST] Calling code_analyst agent with search_term: '{search_term}'"
            logger.info(call_msg)
            print(call_msg, flush=True)
            agent_outputs["code_analyst"] = await explain(search_term)
            response_msg = f"[CODE_ANALYST] Received response: {str(agent_outputs['code_analyst'])[:200]}..."
            logger.info(response_msg)
            print(response_msg, flush=True)
        except AgentCallError as e:
            error_msg = f"[CODE_ANALYST] Error calling code_analyst agent: {str(e)}"
            logger.error(error_msg)
            print(error_msg, flush=True)
            agent_outputs["code_analyst"] = {"error": str(e)}
    else:
        skip_msg = f"[CODE_ANALYST] NOT CALLED - code_analyst not in agents list: {analysis.get('agents')}"
        logger.info(skip_msg)
        print(skip_msg, flush=True)

    # ---------------------------------------------
    # Cache agent responses
    # ---------------------------------------------
    for agent_name, output in agent_outputs.items():
        memory.cache_agent_response(
            session_id=session_id,
            agent_name=agent_name,
            agent_input={"query": query},
            agent_output=output,
        )

    # ---------------------------------------------
    # Synthesize final answer
    # ---------------------------------------------
    final_response = await synthesize(query, agent_outputs)

    # ---------------------------------------------
    # Store conversation turn
    # ---------------------------------------------
    memory.add_turn(
        session_id=session_id,
        query=query,
        response=final_response,
    )

    return {
        "session_id": session_id,
        "response": final_response,
    }


# ---------------------------------------------------------
# Run MCP Server
# ---------------------------------------------------------
if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport == "http":
        port = int(os.environ.get("MCP_PORT", "8004"))
        mcp.run(transport="http", host="0.0.0.0", port=port)
    else:
        mcp.run()  # Default stdio for subprocess mode
