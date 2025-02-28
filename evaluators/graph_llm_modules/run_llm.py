import dotenv
dotenv.load_dotenv(dotenv.find_dotenv(), override=True)


from langchain_core.prompts import ChatPromptTemplate
from llm_failover import ChatFailoverLLM
from langchain_openai.output_parsers import JsonOutputToolsParser


class Chain:

    def __init__(self, model, temperature, seed):
        self.model = model
        self.temperature = temperature
        self.seed = seed

    def run(self, messages, output_model, inputs):
        prompt = ChatPromptTemplate.from_messages(messages)
        llm = ChatFailoverLLM(initial_provider="openai_api", initial_model=self.model, temperature=self.temperature, seed=self.seed)
        llm_with_tools = llm.bind_tools(
            [output_model],
            tool_choice=output_model.model_json_schema()["title"],
            strict=True,
        )
        chain = prompt | llm_with_tools | JsonOutputToolsParser()
        return chain.invoke(inputs)[0]["args"]
    
MAIN_CHAIN = Chain("gpt-4o", temperature=0.3, seed=10)
MULTI_CHAINS = [Chain("gpt-4o", temperature=temp, seed=10) for temp in [0.1, 0.3, 0.5]]
