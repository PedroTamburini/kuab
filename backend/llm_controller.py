import os
import json
import httpx
import re
from config import logger, OLLAMA_URL

class LLMController:
    def __init__(self):
        # Conversational generation parameters
        self.temperature = 0.7
        self.top_p = 0.9
        
        # Load initialization prompt
        self.system_prompt = ""
        prompt_path = os.path.join(os.path.dirname(__file__), "src", "initialize_prompt.md")
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                self.system_prompt = f.read().strip()
        except Exception as e:
            logger.error(f"Failed to load initialize_prompt.md: {e}")

        # Load simulated translation for video transcriptions
        self.simulated_translation = ""
        sim_path = os.path.join(os.path.dirname(__file__), "src", "simulated_translation.md")
        try:
            if os.path.exists(sim_path):
                with open(sim_path, "r", encoding="utf-8") as f:
                    self.simulated_translation = f.read().strip()
        except Exception as e:
            logger.error(f"Failed to load simulated_translation.md: {e}")


    async def get_models(self):
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{OLLAMA_URL}/api/tags", timeout=5.0)
            response.raise_for_status()
            data = response.json()
            return data.get("models", [])

    async def stream_chat(self, model: str, messages: list):
        # Inject system prompt at the beginning of the messages if not present
        formatted_messages = []
        
        system_content = self.system_prompt
        directive = ""
        if self.simulated_translation:
            directive = f"\n\nATENÇÃO: Se a mensagem do usuário pedir para explicar, resumir ou traduzir a transcrição de um vídeo, você DEVE iniciar sua resposta apresentando a seguinte tradução em Marubo da aula (exatamente como está abaixo):\n\n---\n{self.simulated_translation}\n---\n\nSomente após apresentar a tradução acima, você deve fornecer o resumo explicativo da transcrição do vídeo."
            system_content += directive

        if system_content:
            if not messages or messages[0].get("role") != "system":
                formatted_messages.append({"role": "system", "content": system_content})
            else:
                messages = list(messages)
                # If there's already a system message, append the directive
                if directive and "tradução em Marubo" not in messages[0]["content"]:
                    messages[0]["content"] += directive
        
        formatted_messages.extend(messages)



        payload = {
            "model": model,
            "messages": formatted_messages,
            "stream": True,
            "options": {
                "temperature": self.temperature,
                "top_p": self.top_p
            }
        }
        
        try:
            async with httpx.AsyncClient() as client:
                async with client.stream("POST", f"{OLLAMA_URL}/api/chat", json=payload, timeout=None) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        logger.error(f"Ollama chat error: {error_text}")
                        yield json.dumps({"error": "Failed to communicate with Ollama during chat."}) + "\n"
                        return

                    async for line in response.aiter_lines():
                        if line:
                            yield line + "\n"
        except Exception as e:
            logger.error(f"Error during streaming chat: {str(e)}")
            yield json.dumps({"error": "An unexpected error occurred during chat."}) + "\n"
