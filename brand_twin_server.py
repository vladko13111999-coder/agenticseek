import os
import litserve as ls
import httpx


class BrandTwinAPI(ls.LitAPI):
    def setup(self, device):
        self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.model = "gemma3:12b"

    def decode_request(self, request):
        return request["query"]

    def predict(self, query):
        try:
            import requests

            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": f"Respond as TvojTon, a helpful AI assistant. User: {query}",
                    "stream": False,
                },
                timeout=60,
            )
            result = response.json()
            return {
                "done": "true",
                "answer": result.get("response", "No response"),
                "reasoning": "",
                "agent_name": "TvojTon",
                "success": "true",
                "blocks": {},
                "status": "Ready",
            }
        except Exception as e:
            return {
                "done": "true",
                "answer": f"Error: {str(e)}",
                "reasoning": "",
                "agent_name": "TvojTon",
                "success": "false",
                "blocks": {},
                "status": "Error",
            }

    def encode_response(self, prediction):
        return prediction


if __name__ == "__main__":
    server = ls.LitServer(BrandTwinAPI(), api_path="/query")
    server.run(host="0.0.0.0", port=7777)
