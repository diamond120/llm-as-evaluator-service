from pydantic import BaseModel
from typing import Any, List, Optional, Dict, AsyncIterator, Iterator, TypeVar, Callable, Union, Awaitable, Sequence, cast

from langchain_core.language_models import BaseChatModel, LanguageModelInput
from langchain_core.outputs import ChatResult, ChatGeneration
from langchain_core.messages import BaseMessage, BaseMessageChunk
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.runnables import Runnable, RunnableConfig
from langchain_core.tools import BaseTool

from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_anthropic import ChatAnthropic

from llm_failover.key_manager import key_manager
from llm_failover.config import logger, WRONG_API_KEY_ERRORS, ChatGoogleGenerativeAIError, TEMPORARY_KEY_ERRORS, TEMPORARY_PROVIDER_ERRORS

T = TypeVar('T')  # Generic type for return value
ModelFunc = Callable[..., Union[T, Awaitable[T]]]  # Type for model functions

class ChatFailoverLLM(BaseChatModel):
    initial_provider: str
    initial_model: str
    initial_key: str
    last_provider: str
    last_model: str
    params: Dict[str, Any]
    method_calls: List[Callable[[BaseChatModel], BaseChatModel]]

    def __init__(
        self,
        initial_provider: str,
        initial_model: str,
        initial_key: str = "",
        **params: Any
    ):
        super().__init__(
            initial_provider=initial_provider,
            initial_model=initial_model,
            initial_key=initial_key,
            last_provider="",
            last_model="",
            params=params,
            method_calls=[]
        )
    
    @property
    def _llm_type(self) -> str:
        return "chat_failover_llm"

    @property
    def _identifying_params(self) -> Dict[str, Any]:
        return {
            "initial_model": self.initial_model,
            "initial_provider": self.initial_provider,
            **self.params
        }
    
    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        raise NotImplementedError

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        raise NotImplementedError

    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Iterator[ChatGeneration]:
        raise NotImplementedError

    async def _astream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatGeneration]:
        raise NotImplementedError

    def _create_model(
        self,
        provider: str,
        api_key: str,
        model_name: str
    ) -> BaseChatModel:
        match provider:
            case "openai_api":
                return ChatOpenAI(
                    **self.params,
                    openai_api_key=api_key,
                    model=model_name,
                )
            case "google_api":
                return ChatGoogleGenerativeAI(
                    **self.params,
                    google_api_key=api_key,
                    model=model_name,
                )
            case "anthropic_api":
                return ChatAnthropic(
                    **{k: v for k, v in self.params.items() if k != 'seed'},
                    anthropic_api_key=api_key,
                    model=model_name,
                )
            case _:
                raise ValueError(f"Unsupported provider in ChatFailoverLLM: {provider}")

    def _execute_with_failover(
        self,
        func: ModelFunc[T],
    ) -> T:
        key_manager.log_status(f"Started with provider: {self.initial_provider}, model: {self.initial_model}")
        
        for attempt in range(key_manager.get_api_retries()):
            try:
                if self.initial_key and attempt == 0:
                    provider, model_name, key_info = self.initial_provider, self.initial_model, self.initial_key
                else:
                    provider, default_model, key_info = key_manager.get_api_info(self.initial_provider)
                    model_name = self.initial_model if provider == self.initial_provider else default_model

                model = self._create_model(provider, key_info.key, model_name)

                for method_call in self.method_calls:
                    model = method_call(model)

                logger.debug(f"Generating... provider: {provider}, model: {model_name}, details: {key_info}, params: {self.params}")

                result = func(model)
                
                self.last_provider = provider
                self.last_model = model_name
                key_manager.log_status(f"Finished with provider: {self.last_provider}, model: {self.last_model}, details: {key_info}")
                return result
                
            except WRONG_API_KEY_ERRORS as e:
                if isinstance(e, ChatGoogleGenerativeAIError):
                    if str(e.args[0]).find("API_KEY_INVALID") < 0:
                        logger.debug("Ignore Invalid Argument Error which doesn't contain 'API_KEY_INVALID'")
                        raise
                logger.warning(f"Catched Wrong API Key Error. provider: {provider}, details: {key_info}, error: {e}")
                key_manager.remove_key(provider, key_info)

            except TEMPORARY_KEY_ERRORS as e:
                logger.warning(f"Catched Rate Limit Error. provider: {provider}, details: {key_info}, error: {e}")
                key_manager.pause_key(provider, key_info)

            except TEMPORARY_PROVIDER_ERRORS as e:
                logger.warning(f"Catched Service Error. provider: {provider}, details: {key_info}, error: {e}")
                key_manager.pause_provider(provider)

        key_manager.log_status(f"Something went wrong with KeyManager")
        raise Exception("Something went wrong with Failover Logic")
    
    def bind_tools(
        self,
        tools: Sequence[
            Union[Dict[str, Any], type, Callable, BaseTool]
        ],
        **kwargs: Any,
    ) -> Runnable[LanguageModelInput, BaseMessage]:
        self.method_calls.append(lambda model: model.bind_tools(
            tools,
            **kwargs
        ))
        return self
    
    def with_structured_output(
        self,
        schema: Union[Dict, type],
        *,
        include_raw: bool = False,
        **kwargs: Any,
    ) -> Runnable[LanguageModelInput, Union[Dict, BaseModel]]:
        self.method_calls.append(lambda model: model.with_structured_output(
            schema,
            include_raw=include_raw,
            **kwargs
        ))
        return self
    
    def invoke(
        self,
        input: LanguageModelInput,
        config: Optional[RunnableConfig] = None,
        *,
        stop: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> BaseMessage:
        return self._execute_with_failover(
            func=lambda model: model.invoke(
                input,
                config,
                stop=stop,
                **kwargs
            )
        )

    async def ainvoke(
        self,
        input: LanguageModelInput,
        config: Optional[RunnableConfig] = None,
        *,
        stop: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> BaseMessage:
        return self._execute_with_failover(
            func=lambda model: model.invoke(
                input,
                config,
                stop=stop,
                **kwargs
            )
        )
    
    def stream(
        self,
        input: LanguageModelInput,
        config: Optional[RunnableConfig] = None,
        **kwargs: Any,
    ) -> Iterator[BaseMessageChunk]:
        raise NotImplementedError
    
    async def astream(
        self,
        input: LanguageModelInput,
        config: Optional[RunnableConfig] = None,
        **kwargs: Any,
    ) -> AsyncIterator[BaseMessageChunk]:
        raise NotImplementedError
    