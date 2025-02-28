import os
from dotenv import load_dotenv
from typing import Any, Dict
import time
import json
from llm_failover.config import logger, AVAILABLE_PROVIDERS, API_KEY_VISIBLE_PREFIX, API_KEY_VISIBLE_SUFFIX, API_KEY_VISIBLE_MINIMUM

class KeyInfo:
    def __init__(self, key: str, last_used: float = 0, paused: bool = False):
        self.key = key
        self.last_used = last_used
        self.paused = paused

    def masked_key(self) -> str:
        prefix = API_KEY_VISIBLE_PREFIX
        suffix = API_KEY_VISIBLE_SUFFIX
        if len(self.key) <= prefix + suffix:
            prefix = suffix = API_KEY_VISIBLE_MINIMUM
        return f"{self.key[:prefix]}{'*' * (len(self.key) - prefix - suffix)}{self.key[-suffix:]}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.masked_key(),
            "last_used": self.last_used,
            "paused": self.paused
        }

    def __repr__(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, KeyInfo):
            return NotImplemented
        return self.key == other.key

    def __hash__(self) -> int:
        return hash(self.key)

class KeyManager:
    def __init__(self, env_vars: dict):
        self.api_key_refresh_interval = int(env_vars["API_KEY_REFRESH_INTERVAL"])
        self.provider_refresh_interval = int(env_vars["PROVIDER_REFRESH_INTERVAL"])

        self.provider_details = {}
        # Load providers and keys from environment variable
        for provider_config in AVAILABLE_PROVIDERS:
            provider = provider_config["provider"]
            ENV_API_KEY = provider_config["api_key"]
            ENV_DEFAULT_MODEL = provider_config["default_model"]
            if ENV_API_KEY in env_vars:
                self.provider_details[provider] = {
                    "default_model": env_vars[ENV_DEFAULT_MODEL],
                    "last_used": 0,
                    "paused": False,
                    "keys": [ KeyInfo(key, 0, False) for key in env_vars[ENV_API_KEY].split(",") ]
                }

        self.log_status("KeyManager loaded providers and keys from environment variables")
        
    def log_status(self, message: str):
        logger.info(message)
        logger.debug(f"KeyManager status: {self.provider_details}")

    def remove_key(self, provider: str, key_info: KeyInfo):
        self.provider_details[provider]["keys"].remove(key_info)
        self.log_status(f"KeyManager removed the key. provider: {provider}, {key_info}")

    def pause_key(self, provider: str, key_info: KeyInfo):
        key_info.paused = True
        self.log_status(f"KeyManager paused the key. provider: {provider}, {key_info}")

    def resume_key(self, provider: str, key_info: KeyInfo):
        key_info.paused = False
        self.log_status(f"KeyManager resumed the key. provider: {provider} {key_info}")

    def pause_provider(self, provider: str):
        self.provider_details[provider]["paused"] = True
        self.log_status(f"KeyManager paused the provider: {provider}")

    def resume_provider(self, provider: str):
        self.provider_details[provider]["paused"] = False
        self.log_status(f"KeyManager resumed the provider: {provider}")

    def get_api_retries(self) -> int:
        return sum([ len(provider_info["keys"]) for provider_info in self.provider_details.values() ]) + 1

    def get_api_info(self, initial_provider: str) -> tuple[str, str, KeyInfo]:
        # Iterate all providers by priority but suggested one as the first
        for provider in dict.fromkeys([initial_provider, *self.provider_details.keys()]):
            # Skip unconfigured providers
            if provider not in self.provider_details:
                continue
            provider_info = self.provider_details[provider]

            # Check and refresh paused status
            if provider_info["paused"]:
                if time.time() - provider_info["last_used"] < self.provider_refresh_interval:
                    continue
                self.resume_provider(provider)
            
            # Load and find the first valid key
            keys = provider_info["keys"]
            #keys.sort(key=lambda x: x["last_used"])
            for key_info in keys:
                # Check and refresh paused status
                if key_info.paused:
                    if time.time() - key_info.last_used < self.api_key_refresh_interval:
                        continue
                    self.resume_key(provider, key_info)
                
                key_info.last_used = time.time()
                provider_info["last_used"] = time.time()
                return (provider, provider_info["default_model"], key_info)
            
        self.log_status("No valid keys available in KeyManager")
        raise Exception(f"No valid keys available at the moment")
    
# Create global KeyManager instance from environment variables
load_dotenv(override=True)
key_manager = KeyManager(os.environ)
