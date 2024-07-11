import argparse
import json
import sys
from doc_test.agent.gen_agent import GenAgent
from doc_test.agent.repair_agent import RepairAgent
from doc_test.consts import (
    CATEGORIES_PATH,
    DEFAULT_MODEL,
    DOCKERFILE_STEP,
    FASTAPI,
    FOLLOWUP_PROMPT_PATH,
    NL_PROMPT_PATH,
    NL_STEP,
    REPOS_PATH,
)
from doc_test.utils import generate_name
from vm_control import VMController
from doc_test.agent import Agent
from doc_test.agent.agent import Agent
from eval.agent.eval import eval
from pprint import pprint


def classify_repo(repo_url: str, model: str = DEFAULT_MODEL) -> Agent:

    agent = RepairAgent(
        model=model,
        system=Agent.init_system_message(repo_url, categories_path=CATEGORIES_PATH),
    )
    category = agent.classify_repo(
        repo_url=repo_url,
        followup_path=FOLLOWUP_PROMPT_PATH,
        categories_path=CATEGORIES_PATH,
    )
    pprint(agent.targets)
    return agent


def main(args, run_name):
    url = args.repo
    repo_name = url.split("/")[-1][:-4]

    if args.eval:
        success = {}
        record = eval(
            categories_path=CATEGORIES_PATH,
            followup_path=FOLLOWUP_PROMPT_PATH,
            repos=REPOS_PATH,
            dockerfile_step=DOCKERFILE_STEP,
            nl_step=NL_STEP,
            n_eval=int(args.n_eval),
            repair_attempts=args.n_tries,
            model=args.model,
            run_name=run_name,
        )

    elif args.messages is not None:
        with open(args.messages, "r") as f:
            dockerfile = json.load(f)

        agent = RepairAgent(args.model, None, dockerfile, verbose=True)
        dockerfile = args.dockerfile or agent.gen_dockerfile(url, repo_name)

        agent.repair_dockerfile(url=url, dockerfile=dockerfile, repo_name=repo_name)

    else:
        url = args.repo
        name = url.split("/")[-1][:-4]
        agent = classify_repo(url)
        agent.gen_nl_description()
        dockerfile = agent.gen_dockerfile(url, name)
        agent.repair_dockerfile(url, dockerfile, name)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--eval",
        action="store_true",
        help="whether to perform evaluation on the stored set of example repos.",
    )
    parser.add_argument(
        "--repo",
        default=FASTAPI,
        help="if not performing evaluation, specifies the repo to attempt to build.",
    )
    parser.add_argument(
        "--n_tries",
        default=2,
        help="Number of repair attempts to make before giving up.",
    )
    parser.add_argument(
        "--n_eval",
        default=3,
        help="Number of times to repeat evaluation.",
    )
    parser.add_argument(
        "--messages",
        help=(
            "Path to a json file containing the logs from classification step. "
            "Providing this will skip classification and will attempt repair"
            "based on these messages. (--dockerfile must also be provided)"
        ),
    )
    parser.add_argument(
        "--model",
        help="name of the openai model to use as the agent.",
        default=DEFAULT_MODEL,
    )
    # HERE HERE HERE
    # IF MESSAGES AND NO DOCKERFILE, GEN DOCKERFILE
    # ELSE, YKNOW, USE THE DOCKERFILE
    parser.add_argument(
        "--dockerfile",
        help="Path to a dockerfile to be repaired.",
    )
    args = parser.parse_args()
    run_name = generate_name()
    print(f"RUN:    {run_name}")
    try:
        main(args, run_name)
    except Exception as e:
        raise e
    except KeyboardInterrupt as e:
        raise e
    finally:
        print("clearing cache...")
        VMController().clear_cache()
        print(f"FINISHED:   {run_name}")
