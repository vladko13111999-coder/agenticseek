import asyncio
import configparser
from sources.interaction import Interaction
from sources.agents.planner_agent import PlannerAgent
from sources.agents.coder_agent import CoderAgent
from sources.agents.file_agent import FileAgent
from sources.agents.browser_agent import BrowserAgent
from sources.agents.casual_agent import CasualAgent
from sources.provider import Provider

class AgentHandler:
    def __init__(self):
        # Načítame konfiguráciu
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')
        # Inicializujeme providera (Ollama)
        self.provider = Provider(self.config)
        # Vytvoríme agentov
        agents = {
            "planner": PlannerAgent("planner", "prompts/planner_agent.txt", self.provider, verbose=False),
            "coder": CoderAgent("coder", "prompts/coder_agent.txt", self.provider, verbose=False),
            "file": FileAgent("file", "prompts/file_agent.txt", self.provider, verbose=False),
            "browser": BrowserAgent("browser", "prompts/browser_agent.txt", self.provider, verbose=False),
            "casual": CasualAgent("casual", "prompts/casual_agent.txt", self.provider, verbose=False)
        }
        self.interaction = Interaction(agents, self.config)

    async def process(self, query: str) -> str:
        """Spracuje otázku a vráti odpoveď agenta."""
        self.interaction.last_query = query
        await self.interaction.think()
        return self.interaction.last_answer
