import asyncio

from sources.utility import pretty_print, animate_thinking
from sources.agents.agent import Agent
from sources.tools.searxSearch import searxSearch
from sources.tools.flightSearch import FlightSearch
from sources.tools.fileFinder import FileFinder
from sources.tools.BashInterpreter import BashInterpreter
from sources.memory import Memory

LANG_INSTRUCTIONS = {
    'sk': '\n\nCRITICAL: User wrote in Slovak. Respond ONLY in Slovak. Use Slovak words only.',
    'cs': '\n\nCRITICAL: User wrote in Czech. Respond ONLY in Czech. Use Czech words only.',
    'hr': '\n\nCRITICAL: User wrote in Croatian. Respond ONLY in Croatian. Use Croatian words only.',
    'en': '\n\nCRITICAL: User wrote in English. Respond ONLY in English. Use English words only.',
}

class CasualAgent(Agent):
    def __init__(self, name, prompt_path, provider, verbose=False):
        """
        The casual agent is a special for casual talk to the user without specific tasks.
        """
        super().__init__(name, prompt_path, provider, verbose, None)
        self.tools = {
        } # No tools for the casual agent
        self.role = "talk"
        self.type = "casual_agent"
        self.memory = Memory(self.load_prompt(prompt_path),
                                recover_last_session=False, # session recovery in handled by the interaction class
                                memory_compression=False,
                                model_provider=provider.get_model_name())
    
    async def process(self, prompt, speech_module, force_lang=None) -> str:
        if force_lang and force_lang in LANG_INSTRUCTIONS:
            system_prompt = self.load_prompt("prompts/base/casual_agent.txt") + LANG_INSTRUCTIONS[force_lang]
            self.memory = Memory(system_prompt,
                                recover_last_session=False,
                                memory_compression=False,
                                model_provider=self.llm.get_model_name())
        
        self.memory.push('user', prompt)
        animate_thinking("Thinking...", color="status")
        answer, reasoning = await self.llm_request()
        self.last_answer = answer
        self.status_message = "Ready"
        return answer, reasoning

if __name__ == "__main__":
    pass