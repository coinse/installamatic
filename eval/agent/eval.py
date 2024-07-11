import os
from pprint import pprint
import sys
import json
from doc_test.agent.repair_agent import RepairAgent
from doc_test.utils import generate_name, log_eval, notify
from doc_test.consts import (
    DEFAULT_MODEL,
    DOCKERFILE_REPAIR_SYSTEM_PROMPT_PATH,
    NL_PROMPT_PATH,
    SYSTEM_PROMPT_PATH,
)
from typing import Dict, List, Union
from doc_test.agent import Agent
from doc_test.agent.agent import Agent
from vm_control import VMController

sys.path.append(os.getcwd())


def load_test_cases(filename: str) -> List[Dict[str, Union[str, List[int]]]]:
    with open(filename, "r") as f:
        return json.load(f)


def load_agent(model: str, url: str, categories_path: str) -> RepairAgent:
    agent = RepairAgent(
        model=model,
        system=Agent.init_system_message(url, categories_path=categories_path),
        verbose=False,
    )
    return agent


def eval(
    categories_path: str,
    followup_path: str,
    repos: str,
    n_eval: int,
    repair_attempts: int,
    run_name: str,
    model: str = DEFAULT_MODEL,
    dockerfile_step: bool = False,
    nl_step: bool = False,
):
    print(f"RUN NAME: {run_name}")
    print(f"EVALUATING WITH MODEL: {model}")
    test_cases = load_test_cases(repos)
    test_cases = list(filter(lambda x: x["test_type"] == "pytest", test_cases))
    with open(categories_path, "r") as f:
        category_descriptions = json.load(f)
    score = 0
    records = []
    # record[repo]:
    #   - correct:          whether classification was successful
    #   - categories        the correct categories for the repo
    #   - targets           the files targeted by the agent during classification
    #   - build_status     whether a working dockerfile was able to be built
    notify("starting eval")
    messages_dir = f"logs/messages/{run_name}"

    for i in range(n_eval):

        records.append({})
        record = records[-1]
        for test in test_cases:
            url = test["url"]
            repo_name = url.split("/")[-1][:-4]
            categories = test["categories"]
            print(f"\n\nREPO: {url}")
            notify(f"REPO: {url}")
            messages_fname = f"{model}-{repo_name}-{i}.json"
            agent = load_agent(model, url, categories_path)
            correct = eval_classify_repo(
                agent,
                url,
                categories_path,
                category_descriptions,
                categories,
                followup_path,
                record,
                repo_name,
            )
            score += correct
            agent.save_messages(messages_fname, messages_dir)
            print(agent.targets)

            if correct and dockerfile_step:
                if nl_step:
                    with open(NL_PROMPT_PATH, "r") as f:
                        nl_prompt = f.read()
                        resp = agent.query(nl_prompt, None)
                        print(resp)
                eval_build_project(
                    agent, repo_name, record, url, repair_attempts, run_name, model, i
                )

        build_results = [
            r["build_status"] == "success"
            for r in record.values()
            if "build_status" in r
        ]

        notify(
            (
                f"EVAL ROUND {i}:\n"
                f" - built {sum(build_results)} / {len(build_results)} successfully"
            )
        )
        if (i + 1) % 3 == 0:
            VMController().clear_cache()

        # summary = {
        #     repo: [record[repo]["build_status"] for record in records] for repo in test
        # }
        with open(f"logs/eval/{run_name}_{agent.model}.json", "w") as f:
            json.dump(records, f)
    pprint(records)
    return records


def eval_classify_repo(
    agent: Agent,
    url: str,
    categories_path: str,
    category_descriptions: List[str],
    categories,
    followup_path: str,
    record,
    repo_name,
):
    try:
        prediction = agent.classify_repo(
            url,
            followup_path=followup_path,
            categories_path=categories_path,
        )
        print(f" - PREDICTION: {prediction} {category_descriptions[prediction-1]}")
    except Exception as e:
        print(e)
        prediction = "X"
        exception = True
        # raise e
    print(
        f" - {'O' if prediction in categories else 'X'} ({categories}: {category_descriptions[categories[0]-1]})"
    )
    print(f" - {agent.calls} calls")
    correct = prediction in categories
    record[repo_name] = {
        "correct": correct,
        "categories": categories,
        "targets": agent.targets,
    }
    return correct


def eval_build_project(
    agent: Agent, repo_name, record, url, repair_attempts, run_name, model_name, n
):
    messages_dir = f"logs/messages/{run_name}"
    messages_fname = f"{model_name}-{repo_name}-{n}.json"
    print("eval build")
    n_tries = 0
    try:
        agent.gen_nl_description()
        dockerfile = agent.gen_dockerfile(url, repo_name=repo_name)
        agent.save_messages(messages_fname, messages_dir)
        print("test_repair")
        with open(DOCKERFILE_REPAIR_SYSTEM_PROMPT_PATH, "r") as f:
            system = f.read().replace("<DOCKERFILE>", dockerfile)
        agent = RepairAgent(agent.model, system)
        # agent.verbose = True
        build_status, n_tries = agent.repair_dockerfile(
            url, dockerfile, repo_name, repair_attempts
        )
        notify(
            f"BUILD STATUS: {build_status.upper()} after {n_tries} repair attempt(s)"
        )
    except Exception as e:
        print(agent.messages)
        print(e)
        build_status = "failure"
        agent.save_messages(messages_fname, messages_dir)
        # raise e
    except KeyboardInterrupt:
        build_status = "failure"

    agent.save_messages(messages_fname, messages_dir)
    record[repo_name]["build_status"] = build_status
    record[repo_name]["n_tries"] = n_tries
