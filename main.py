import sys
from doc_test import vm_control
from doc_test.agent import OpenAIAgent
from doc_test.agent.tool_using_agent import ToolUsingOpenAIAgent
from eval.agent.eval_classify_repo import eval_python
from pprint import pprint

LIMITED = True
NL_STEP = False
DOCKERFILE_STEP = True

if LIMITED:
    categories_path = "resources/python_categories_limited.json"
    repos = "eval/resources/python_repos_limited.json"
else:
    categories_path = "resources/python_categories.json"
    repos = "eval/resources/python_repos.json"


def classify_repo(
    repo_url: str, model: str = "gpt-3.5-turbo-1106", use_tools: bool = True
):

    if use_tools:
        followup_path = "resources/followup_prompt_tool_use.md"
        agent = ToolUsingOpenAIAgent(
            model=model,
            system=OpenAIAgent.init_system_message(
                repo_url, categories_path=categories_path
            ),
        )
    else:
        followup_path = "resources/followup_prompt.md"
        agent = OpenAIAgent(
            model=model,
            system=OpenAIAgent.init_system_message(
                repo_url, categories_path=categories_path
            ),
        )
    category = agent.classify_repo(
        repo_url=repo_url, followup_path=followup_path, categories_path=categories_path
    )
    if NL_STEP:
        with open("resources/installation_prompt_nl.md", "r") as f:
            installation = f.read()
        resp = agent.query(installation, None)
        print(resp)
    if DOCKERFILE_STEP:
        with open("resources/dockerfile_prompt.md", "r") as f:
            dockerfile_instruction = f.read()
        resp = agent.query(dockerfile_instruction, None)
        print(resp)

    pprint(agent.targets)


if len(sys.argv) > 1:
    url = sys.argv[1]
else:
    url = "https://github.com/tiangolo/fastapi.git"
use_tools = len(sys.argv) <= 2 or sys.argv[2] == "tool"
if url == "eval":
    eval_python(
        categories_path=categories_path,
        followup_path=f"resources/followup_prompt{'_tool_use' if use_tools else ''}.md",
        repos=repos,
        use_tools=use_tools,
        nl_step=NL_STEP,
        dockerfile_step=DOCKERFILE_STEP,
    )
else:
    print(f"classifying repo: {'/'.join(url.split('/')[-2:])[:-4]}")
    classify_repo(url, use_tools=use_tools)
