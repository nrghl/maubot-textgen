import json
from typing import Type
from mautrix.util.config import BaseProxyConfig, ConfigUpdateHelper
from maubot import Plugin, MessageEvent
from mautrix.types import EventType, GenericEvent
from maubot.handlers import command, event

class Config(BaseProxyConfig):
    def do_update(self, helper: ConfigUpdateHelper) -> None:
        helper.copy("api_endpoint")

class TextGen(Plugin):
    async def start(self) -> None:
        self.config.load_and_update()
        self.log.info("ChatBot plugin started")

    async def stop(self) -> None:
        self.log.info("ChatBot plugin stopped")

    @command.new(name="gpt", help="Interact with the chatbot.")
    @command.argument("message", pass_raw=True, required=False)
    async def ai_command(self, evt: MessageEvent, message: str = "") -> None:
        user_input = message
        if message:
            chatbot_response = await self.generate_chat_response(message)
            await evt.reply(chatbot_response)
        else:
            await evt.reply("You didn't provide any input for the chatbot.")

    async def generate_chat_response(self, message):
        history = {'internal': [], 'visible': []}
        request = {
            'user_input': message,
            'max_new_tokens': 2000,
            'history': history,
            'mode': 'chat',
            'character': 'Example',
            'instruction_template': 'WizardLM',
            'your_name': 'AI:',
            'regenerate': False,
            '_continue': False,
            'stop_at_newline': False,
            'chat_generation_attempts': 1,
            'chat-instruct_command': 'Continue the chat dialogue below. Write a single reply for the character "<|character|>".\\n\\n<|prompt|>',
            'preset': 'LLaMA-Precise',
            'stopping_strings': []
        }

        async with self.http.post(f"http://{self.config['api_endpoint']}/api/v1/chat", json=request) as resp:
            if resp.status == 200:
                response = await resp.json()
                result = response['results'][0]['history']
                return str(result['visible'][-1][1])
            else:
                return "Sorry, I couldn't process your request."

    @classmethod
    def get_config_class(cls) -> Type[BaseProxyConfig]:
        return Config
