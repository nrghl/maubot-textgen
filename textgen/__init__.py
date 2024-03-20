import json
from typing import Type
from mautrix.util.config import BaseProxyConfig, ConfigUpdateHelper
from maubot import Plugin, MessageEvent
from mautrix.types import EventType, GenericEvent
from maubot.handlers import command, event
import aiohttp

class Config(BaseProxyConfig):
    def do_update(self, helper: ConfigUpdateHelper) -> None:
        helper.copy("api_endpoint")
        helper.copy("generation_settings")

class TextGen(Plugin):
    async def start(self) -> None:
        self.config.load_and_update()
        self.log.info("ChatBot plugin started")
        self.history = []
        self.max_history_length = 10

    async def stop(self) -> None:
        self.log.info("ChatBot plugin stopped")

    def update_history(self, message: str):
        self.history.append(message)
        if len(self.history) > self.max_history_length:
            self.history.pop(0)

    @command.new(name="gpt", help="Interact with the chatbot.")
    @command.argument("message", pass_raw=True, required=False)
    async def ai_command(self, evt: MessageEvent, message: str = "") -> None:
        if message:
            self.update_history(message)
            self.log.info(f"Recent history: {self.history[-min(3, len(self.history)):]}")
            self.log.info(f"Received message: {message}")
            chatbot_response = await self.generate_chat_response(message)
            await evt.respond(chatbot_response)
        else:
            await evt.respond("You didn't provide any input for the chatbot.")

    async def generate_chat_response(self, message):
        request = self.construct_request(message)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"http://{self.config['api_endpoint']}/v1/chat/completions", json=request) as resp:
                    if resp.status == 200:
                        response = await resp.json()
                        return self.extract_response(response)
                    else:
                        self.log.error(f"API request failed with status {resp.status}")
                        return f"Error: Received status code {resp.status}"
        except Exception as e:
            self.log.error(f"An error occurred: {e}")
            return "An error occurred while processing the request."

    def construct_request(self, message: str) -> dict:
        gen_settings = self.config['generation_settings']

        messages = []
        for i, msg in enumerate(reversed(self.history)):
            role = "user" if i % 2 == 0 else "bot"
            messages.append({"role": role, "content": msg})
        messages.append({"role": "user", "content": message})

        return {
            "messages": messages,
            "max_tokens": gen_settings['max_tokens'],
            "max_new_tokens": gen_settings['max_new_tokens'],
            "temperature": gen_settings['temperature'],
            "top_p": gen_settings['top_p'],
            "min_p": gen_settings['min_p'],
            "top_k": gen_settings['top_k'],
            "repetition_penalty": gen_settings['repetition_penalty'],
            "presence_penalty": gen_settings['presence_penalty'],
            "frequency_penalty": gen_settings['frequency_penalty'],
            "typical_p": gen_settings['typical_p'],
            "seed": gen_settings['seed']
        }

    @staticmethod
    def extract_response(response: dict) -> str:
        response_text = ""

        if "choices" in response and response["choices"]:
            response_text = response["choices"][0]["message"]["content"]
            additional_info = {
                "Model": response.get("model", "N/A"),
                "Completion reason": response["choices"][0].get("finish_reason", "N/A"),
                "Prompt tokens": response.get("usage", {}).get("prompt_tokens", "N/A"),
                "Completion tokens": response.get("usage", {}).get("completion_tokens", "N/A"),
                "Total tokens": response.get("usage", {}).get("total_tokens", "N/A")
            }
            # display some extra info in a code block
            info_text = "\n```bash\n"
            for key, value in additional_info.items():
                info_text += f"{key}: {value} \n"
            response_text += info_text
            response_text += "```"
        else:
            response_text = "No response from the AI."
        return response_text

    @classmethod
    def get_config_class(cls) -> Type[BaseProxyConfig]:
        return Config
