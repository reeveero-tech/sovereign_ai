import os

from smolagents import Tool

from libs.utils.tavily_search import SearchResults, tavily_search


class SmolAgentsTavilySearchTool(Tool):
    name = "tavily_web_search"
    description = (
        """Performs a Tavily web search based on your query (similar to a Google search) and returns the top search results."""
    )
    inputs = {"query": {"type": "string",
                        "description": "The search query to perform."}}
    output_type = "string"

    def __init__(self, max_results=3, include_raw=True, **kwargs):
        super().__init__()
        self.max_results = max_results
        self.include_raw = include_raw

        if not os.getenv("TAVILY_API_KEY"):
            raise ValueError("TAVILY_API_KEY environment variable is not set")

    def forward(self, query: str) -> str:
        try:
            results: SearchResults = tavily_search(
                query=query, max_results=self.max_results, include_raw=self.include_raw)

            if len(results.results) == 0:
                raise Exception(
                    "No results found! Try a less restrictive/shorter query.")

            postprocessed_results = []
            for result in results.results:
                postprocessed_results.append(
                    f"[{result.title}]({result.link})\n{result.content}")

            return "## Search Results\n\n" + "\n\n".join(postprocessed_results)
        except Exception as e:
            return f"Error performing search: {str(e)}"


if __name__ == "__main__":
    from smolagents import CodeAgent, LiteLLMModel

    model = LiteLLMModel(model_id="together_ai/meta-llama/Llama-3.3-70B-Instruct-Turbo",
                         api_key=os.environ["TOGETHER_API_KEY"])
    agent = CodeAgent(tools=[SmolAgentsTavilySearchTool()], model=model)

    result = agent.run(
        "How many seconds would it take for a leopard at full speed to run through the Eiffel Tower?")
    print(result)
