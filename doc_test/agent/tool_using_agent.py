from copy import deepcopy
import json
from typing import Any, Dict, List, Tuple
from doc_test.agent.agent import OpenAIAgent
from doc_test.agent.functions import (
    check_presence,
    get_directory_contents,
    get_file_contents,
    inspect_header,
)
from doc_test.agent.functions_json import (
    FUNC_DIR,
    FUNC_FILE,
    FUNC_GUESS,
    FUNC_PRESENCE,
    FUNC_DOCKERFILE,
)
from doc_test.agent.utils import classify_output, print_output


class ToolUsingOpenAIAgent(OpenAIAgent):

    def query(self, message, tools, **kwargs):
        print_output(message, ">", self.verbose)

        self.messages.append({"role": "user", "content": message})
        response = (
            self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                tools=tools,
                tool_choice="auto" if tools is not None else None,
                **kwargs,
            )
            .choices[0]
            .message
        )

        if tools is None:
            response = response.content
            self.messages.append({"role": "assistant", "content": response})

        elif response.tool_calls is None or len(response.tool_calls) == 0:
            raise ValueError("No tools were used")
        else:
            function_name = response.tool_calls[0].function.name
            function_args = response.tool_calls[0].function.arguments
            response = {
                "id": response.tool_calls[0].id,
                "type": "function",
                "function": {
                    "name": function_name,
                    "arguments": function_args,
                },
            }
            self.messages.append(
                {
                    "role": "assistant",
                    "tool_calls": [response],
                }
            )

        print_output(str(response), "<", self.verbose)

        self.calls += 1

        if self.tokens is not None:
            if self.tokens == 0:
                self.tokens = len(self.encoder.encode(self.system))
            self.tokens += len(self.encoder.encode(message["content"])) + len(
                self.encoder.encode(response)
            )
        return response

    def query_and_classify(self, message, tools, **kwargs):
        response = self.query(message, tools, **kwargs)
        command = response["function"]["name"]
        response_class = classify_output(
            command,
            [tool["function"]["name"] for tool in tools],
        )
        return response, response_class

    def classify_repo_setup(
        self,
        repo_url: str,
        followup_path: str,
        categories_path: str,
    ):
        followup, root_dir, api_url, categories = super().classify_repo_setup(
            repo_url, followup_path, categories_path
        )
        func_guess = deepcopy(FUNC_GUESS)
        func_guess["function"]["parameters"]["properties"]["category"]["enum"] = [
            i + 1 for i in range(len(categories))
        ]
        func_guess["function"]["parameters"]["properties"]["category"][
            "description"
        ] = func_guess["function"]["parameters"]["properties"]["category"][
            "description"
        ] + "\n".join(
            [f" - [{i + 1}] {category}" for i, category in enumerate(categories)]
        )
        tools = [FUNC_DIR, FUNC_FILE, FUNC_PRESENCE, func_guess]
        return followup, root_dir, api_url, categories, tools

    def classify_repo_loop(
        self,
        followup: str,
        root_dir: List[Tuple[str, str]],
        api_url: str,
        categories: List[str],
        tools: List[Dict[str, Any]],
    ):
        directories = [i[0] for i in root_dir if i[1] == "dir"] + [".", "/"]
        files = [i[0] for i in root_dir if i[1] == "file"]
        file_contents = {}
        self.query(followup, None)
        response, response_class = self.query_and_classify("", tools)

        while response_class != "classify_repo":
            function_response = self.use_tool(
                response=response,
                response_class=response_class,
                directories=directories,
                files=files,
                file_contents=file_contents,
                tools=tools,
                api_url=api_url,
            )

            print_output(function_response, "^", self.verbose)

            function_response = {
                "tool_call_id": response["id"],
                "role": "tool",
                "name": response["function"]["name"],
                "content": function_response,
            }
            self.messages.append(function_response)
            self.query(followup, None)
            response, response_class = self.query_and_classify("", tools)

        function_response = {
            "tool_call_id": response["id"],
            "role": "tool",
            "name": response["function"]["name"],
            "content": "ok!",
        }
        self.messages.append(function_response)
        categories_dict = {
            i: [str(i), f"[{i}]", category] for i, category in enumerate(categories, 1)
        }
        guess = classify_output(
            str(json.loads(response["function"]["arguments"])["category"]),
            categories_dict,
        )
        return guess

    def use_tool(
        self,
        response: str,
        response_class: str,
        directories: List[str],
        files: List[str],
        file_contents: Dict[str, Dict[str, str]],
        tools: List[Dict[str, Any]],
        api_url: str,
    ) -> str:
        match response_class:
            case "get_directory_contents":
                function_response = get_directory_contents(
                    response, directories, files, api_url, self.targets
                )
            case "get_file_contents":
                function_response = get_file_contents(
                    response, files, tools, file_contents, api_url, self.targets
                )
            case "check_presence":
                function_response = check_presence(response, api_url, self.targets)
            case "inspect_header":
                function_response = inspect_header(
                    response, files, file_contents, self.targets
                )
        return (
            function_response
            + "\n"
            + (
                "use the tools to either get more information "
                "or make a guess once you are confident."
            )
        )

    def gen_dockerfile(self, prompt: str, fname: str = None) -> str:
        response = self.query(message=prompt, tools=[FUNC_DOCKERFILE])
        dockerfile = str(json.loads(response["function"]["arguments"])["dockerfile"])

        if fname is not None:
            with open(f"logs/dockerfiles/dockerfile.{fname}", "w") as f:
                f.write(dockerfile)

        return dockerfile