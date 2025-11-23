import logging
from typing import TypedDict, Annotated, List, Dict, Any, Union
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
import operator

# Import specialized agents
from src.agents.specialized.scout_agent import ScoutAgent
from src.agents.specialized.analyst_agent import AnalystAgent
from src.agents.specialized.skeptic_agent import SkepticAgent
from src.agents.specialized.historian_agent import HistorianAgent
from src.agents.specialized.cleaning_agent import CleaningAgent

logger = logging.getLogger(__name__)

class AgentState(TypedDict):
    """
    The shared state of the agent graph.
    """
    messages: Annotated[List[BaseMessage], operator.add]
    current_agent: str
    next_agent: str
    task_status: str
    artifacts: Dict[str, Any]
    errors: List[str]

class AgentGraph:
    """
    Orchestrator for the Multi-Agent System using LangGraph.
    """
    def __init__(self):
        # Initialize agents
        self.scout = ScoutAgent() # Real Scout
        self.analyst = AnalystAgent()
        self.skeptic = SkepticAgent()
        self.historian = HistorianAgent()
        self.cleaner = CleaningAgent()
        
        self.workflow = StateGraph(AgentState)
        self._build_graph()
        self.app = self.workflow.compile()

    def _build_graph(self):
        """
        Define the nodes and edges of the graph.
        """
        # Define Nodes
        self.workflow.add_node("director", self._director_node)
        self.workflow.add_node("scout", self.scout.process) # Use real process method
        self.workflow.add_node("analyst", self.analyst.process)
        self.workflow.add_node("skeptic", self.skeptic.process)
        self.workflow.add_node("historian", self.historian.process)
        self.workflow.add_node("cleaner", self.cleaner.process)

        
        # Define Entry Point
        self.workflow.set_entry_point("director")

        # Define Edges
        self.workflow.add_conditional_edges(
            "director",
            self._route_from_director,
            {
                "scout": "scout",
                "analyst": "analyst",
                "skeptic": "skeptic",
                "historian": "historian",
                "cleaner": "cleaner",
                "end": END
            }
        )
        
        # Return edges (Agents report back to Director)
        self.workflow.add_edge("scout", "director")
        self.workflow.add_edge("analyst", "director")
        self.workflow.add_edge("skeptic", "director")
        self.workflow.add_edge("historian", "director")
        self.workflow.add_edge("cleaner", "director")

    # --- Node Implementations ---
    
    async def _director_node(self, state: AgentState):
        """
        The Director decides what to do next based on the state.
        """
        logger.info(f"🎬 Director analyzing state: {state.get('task_status')}")
        
        task_status = state.get("task_status")
        artifacts = state.get("artifacts", {})

        # If no posts collected yet, call scout
        if task_status == "started" or not artifacts.get("current_post"):
            return {"next_agent": "scout", "task_status": "scouting"}
        
        # If scout finished and we have a post, call analyst
        if task_status == "scouting" and artifacts.get("current_post"):
             return {"next_agent": "analyst", "task_status": "analyzing"}
             
        # If analyst finished, call skeptic
        if task_status == "analysis_complete":
             return {"next_agent": "skeptic", "task_status": "verifying"}
             
        # If skeptic finished, call historian
        if task_status == "verification_complete":
             return {"next_agent": "historian", "task_status": "contextualizing"}
             
        # If historian finished, call cleaner (after verification)
        if task_status == "history_complete":
             return {"next_agent": "cleaner", "task_status": "cleaning"}
        
        # If cleaner finished, we're done
        if task_status == "cleanup_complete":
             return {"next_agent": "end", "task_status": "complete"}
             
        # Fallback: if we don't recognize the status, end the cycle
        return {"next_agent": "end", "task_status": "complete"}



    def _route_from_director(self, state: AgentState):
        """
        Conditional routing logic.
        """
        return state.get("next_agent", "end")

    async def run(self, initial_input: str):
        """
        Run the graph with an initial input.
        """
        initial_state = {
            "messages": [HumanMessage(content=initial_input)],
            "current_agent": "user",
            "next_agent": "director",
            "task_status": "started",
            "artifacts": {},
            "errors": []
        }
        
        async for output in self.app.astream(initial_state):
            for key, value in output.items():
                logger.info(f"Output from {key}: {value}")
