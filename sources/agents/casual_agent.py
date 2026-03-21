import asyncio

from sources.utility import pretty_print, animate_thinking
from sources.agents.agent import Agent
from sources.tools.searxSearch import searxSearch
from sources.tools.flightSearch import FlightSearch
from sources.tools.fileFinder import FileFinder
from sources.tools.BashInterpreter import BashInterpreter
from sources.tools.web_analyzer import WebAnalyzer
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
        Now includes web tools for analysis and browsing.
        """
        super().__init__(name, prompt_path, provider, verbose, None)
        
        # Initialize tools
        self.web_analyzer = WebAnalyzer()
        self.searx_search = searxSearch()
        self.web_analyzer_tool = {
            "name": "analyze_website",
            "description": "Analyzes a website URL and extracts: product name, description, price, images, and domain. Use this when user wants to analyze a specific website or URL.",
            "function": self.web_analyzer.execute
        }
        self.web_search_tool = {
            "name": "search_web",
            "description": "Searches the web for information. Use this when user wants to find information, compare products, or research topics. Returns search results with titles, snippets, and URLs.",
            "function": self.searx_search.execute
        }
        
        self.tools = {
            "analyze_website": self.web_analyzer_tool,
            "search_web": self.web_search_tool,
        }
        
        self.role = "talk"
        self.type = "casual_agent"
        self.memory = Memory(self.load_prompt(prompt_path),
                                recover_last_session=False,
                                memory_compression=False,
                                model_provider=provider.get_model_name())
    
    def analyze_website(self, url: str) -> dict:
        """Analyze a website and return product information."""
        return self.web_analyzer.execute(url)
    
    def search_web(self, query: str) -> dict:
        """Search the web and return results."""
        return self.searx_search.execute(query)
    
    async def process(self, prompt, speech_module, force_lang=None) -> str:
        # Check if this is a web analysis request
        if any(keyword in prompt.lower() for keyword in ['analyzuj', 'analyzovat', 'analyze', 'analiziraj', 'pozri sa na', 'skontroluj web', 'www.', 'http']):
            # Try to extract URL and analyze
            import re
            url_match = re.search(r'https?://[^\s]+', prompt)
            if url_match:
                url = url_match.group(0)
                animate_thinking(f"Analyzing website: {url}", color="status")
                try:
                    result = self.web_analyzer.execute(url)
                    if 'error' in result:
                        web_context = f"Could not analyze the website: {result['error']}"
                    else:
                        web_context = f"""Website Analysis Results:
- Product Name: {result.get('product_name', 'N/A')}
- Description: {result.get('description', 'N/A')}
- Price: {result.get('price', 'N/A')}
- Domain: {result.get('domain', 'N/A')}
- Images found: {len(result.get('images', []))}"""
                except Exception as e:
                    web_context = f"Error analyzing website: {str(e)}"
                
                # Add context to prompt
                prompt = f"{prompt}\n\n[WEB ANALYSIS CONTEXT]:\n{web_context}"
        
        # Check if this is a search request
        if any(keyword in prompt.lower() for keyword in ['vyhľadaj', 'najdi', 'prehľadaj', 'search', 'find', 'search for', 'potrebujem info', 'co je', 'co su', 'who is', 'what is', 'search for']):
            # Extract search query
            import re
            search_keywords = ['vyhľadaj', 'najdi', 'prehľadaj', 'search', 'find', 'search for', 'potrebujem info', 'co je', 'co su', 'who is', 'what is', 'search for', 'konkurencia', 'competitor', 'konkurent', 'analizuj trh', 'analyze market']
            for kw in search_keywords:
                if kw in prompt.lower():
                    query = prompt.lower().split(kw)[-1].strip()
                    query = re.sub(r'^[^\w]+', '', query)
                    if query:
                        animate_thinking(f"Searching web for: {query}", color="status")
                        try:
                            search_result = self.searx_search.execute(query)
                            if isinstance(search_result, list) and len(search_result) > 0:
                                results_text = "Web Search Results:\n"
                                for i, r in enumerate(search_result[:5], 1):
                                    if isinstance(r, dict):
                                        results_text += f"{i}. {r.get('title', 'N/A')}\n   {r.get('content', 'N/A')}\n   URL: {r.get('url', 'N/A')}\n"
                                    else:
                                        results_text += f"{i}. {str(r)[:200]}\n"
                                prompt = f"{prompt}\n\n[SEARCH RESULTS]:\n{results_text}"
                        except Exception as e:
                            pass
                        break
        
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
