import json
from typing import Dict, Any
from openai import AsyncOpenAI
from app.config import settings

# Lazy initialization - client created on first use
_client: AsyncOpenAI | None = None

def get_client() -> AsyncOpenAI:
    """Get or create the AsyncOpenAI client."""
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _client

# ---------------------------------------------------------
# Intent Classification
# ---------------------------------------------------------
INTENT_SYSTEM_PROMPT = """You are an intent classifier for a code repository chat agent.

Analyze the user's query and return a JSON object with:
- "intent": one of "greeting", "explain", "compare", "lookup", "patterns", or "general"
- "agents": a list of agents to use, chosen from ["graph_query", "code_analyst"], or [] for greetings

Guidelines:
- "greeting" (hi, hello, thanks, bye, how are you, etc.): use [] (no agents needed)
- "explain" (how something works, why something exists): use ["graph_query", "code_analyst"]
- "compare" (differences, comparisons): use ["graph_query", "code_analyst"]
- "lookup" (find, where, list items): use ["graph_query"]
- "patterns" (design patterns, code patterns): use ["code_analyst"]
- "general" (substantive questions about the codebase): use ["graph_query", "code_analyst"]

IMPORTANT: Simple conversational messages like "hi", "hello", "thanks", "ok", "bye" should be classified as "greeting" with agents: []

Return ONLY valid JSON, no other text."""


async def classify_intent(query: str) -> dict:
    """Classify the user's query intent and determine which agents to use."""
    # Quick check for obvious greetings (skip LLM call)
    greeting_words = {'hi', 'hello', 'hey', 'thanks', 'thank you', 'bye', 'goodbye', 'ok', 'okay', 'yes', 'no', 'sure'}
    if query.lower().strip().rstrip('!?.') in greeting_words:
        return {"intent": "greeting", "agents": []}
    
    client = get_client()
    response = await client.chat.completions.create(
        model=settings.LLM_MODEL_ID,
        messages=[
            {"role": "system", "content": INTENT_SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ],
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


# ---------------------------------------------------------
# Entity Extraction
# ---------------------------------------------------------
ENTITY_EXTRACTION_PROMPT = """You are an entity extractor for a code repository query system.

Given a natural language query about code, extract:
- "entity_name": The specific class, function, module, or file name being asked about (or null if none)
- "secondary_entity": A second entity if the query involves relationships (or null)
- "query_type": one of:
  - "find_entity": looking up a specific named entity
  - "get_dependencies": what does X depend on / call / import
  - "get_dependents": what depends on / uses / calls X
  - "find_related": find entities related by a relationship (specify relationship)
  - "general_query": broad question requiring LLM synthesis (no graph query needed)
- "relationship": if query_type is "find_related", one of: CONTAINS, IMPORTS, CALLS, INHERITS_FROM, DECORATED_BY (or null)

Examples:
- "Find the App class" → {"entity_name": "App", "secondary_entity": null, "query_type": "find_entity", "relationship": null}
- "What does the Router class do?" → {"entity_name": "Router", "secondary_entity": null, "query_type": "find_entity", "relationship": null}
- "What classes inherit from BaseClass?" → {"entity_name": "BaseClass", "secondary_entity": null, "query_type": "find_related", "relationship": "INHERITS_FROM"}
- "Find all decorators used in routing module" → {"entity_name": "routing", "secondary_entity": null, "query_type": "find_related", "relationship": "DECORATED_BY"}
- "What does MyClass depend on?" → {"entity_name": "MyClass", "secondary_entity": null, "query_type": "get_dependencies", "relationship": null}
- "What uses the helper function?" → {"entity_name": "helper", "secondary_entity": null, "query_type": "get_dependents", "relationship": null}
- "How does dependency injection work?" → {"entity_name": null, "secondary_entity": null, "query_type": "general_query", "relationship": null}
- "What design patterns are used in the core?" → {"entity_name": null, "secondary_entity": null, "query_type": "general_query", "relationship": null}
- "Explain the complete lifecycle of a request" → {"entity_name": null, "secondary_entity": null, "query_type": "general_query", "relationship": null}
- "Compare how Path and Query are implemented" → {"entity_name": "Path", "secondary_entity": "Query", "query_type": "find_entity", "relationship": null}

Return ONLY valid JSON, no other text."""


async def extract_entities(query: str) -> dict:
    """Extract entity names and query type from natural language query."""
    client = get_client()
    response = await client.chat.completions.create(
        model=settings.LLM_MODEL_ID,
        messages=[
            {"role": "system", "content": ENTITY_EXTRACTION_PROMPT},
            {"role": "user", "content": query},
        ],
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


# ---------------------------------------------------------
# Response Synthesis
# ---------------------------------------------------------
SYNTHESIS_SYSTEM_PROMPT = """You are a helpful assistant that answers questions about a code repository.

When given query results from a code repository:
- If results contain actual code entities (classes, functions, files), explain them clearly with file paths
- If results show "info" messages or "no specific entity", use your general programming knowledge to answer
- If results contain errors, acknowledge them briefly and provide your best answer from general knowledge
- For general/conceptual questions (design patterns, lifecycles, comparisons), provide comprehensive explanations
- Be informative and include code examples when helpful
- Structure long answers with clear sections

You have deep knowledge of Python, software architecture, and common frameworks."""


async def synthesize_response(query: str, agent_outputs: Dict[str, Any]) -> str:
    """Synthesize multiple agent outputs into a single coherent response."""
    # Check if we have any meaningful data from agents
    has_real_data = False
    for key, value in agent_outputs.items():
        if isinstance(value, dict):
            results = value.get("results", [])
            if results and len(results) > 0:
                has_real_data = True
                break
            # Check if there's actual data (not just info/error/empty results)
            if "error" not in value and "info" not in value and results != []:
                has_real_data = True
                break
    
    # If only one agent with direct data and non-empty results, return it
    if len(agent_outputs) == 1 and has_real_data:
        result = next(iter(agent_outputs.values()))
        if isinstance(result, dict) and "results" in result and len(result.get("results", [])) > 0:
            return result  # Return raw results for simple lookups
    
    # Format agent outputs for the prompt
    formatted_outputs = json.dumps(agent_outputs, indent=2, default=str)
    
    # Determine if we should rely on LLM knowledge
    needs_llm_knowledge = not has_real_data
    
    if needs_llm_knowledge:
        prompt = f"""User query:
{query}

The codebase search returned no specific results. Please provide a comprehensive answer
based on your general programming knowledge and Python best practices.
Include specific examples and implementation details where relevant.
"""
    else:
        prompt = f"""User query:
{query}

Agent outputs from codebase search:
{formatted_outputs}

Based on the above query and results, provide a comprehensive answer.
Explain the findings and add context from your programming knowledge where helpful.
"""

    client = get_client()
    response = await client.chat.completions.create(
        model=settings.LLM_MODEL_ID,
        messages=[
            {"role": "system", "content": SYNTHESIS_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content
