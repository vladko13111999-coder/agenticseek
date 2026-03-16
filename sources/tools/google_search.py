from googlesearch import search

class GoogleSearchTool:
    def __init__(self):
        self.name = "google_search"
        self.description = "Searches Google and returns top results."

    def execute(self, query, num_results=5):
        try:
            results = list(search(query, num_results=num_results))
            # Spojíme výsledky do jedného reťazca, každý na nový riadok
            return "\n".join(results) if results else "No results found."
        except Exception as e:
            return f"Error during search: {str(e)}"
