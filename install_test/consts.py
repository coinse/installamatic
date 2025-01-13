import os

NL_STEP = True
DOCKERFILE_STEP = True

# model hparams
PER_MESSAGE_TOKEN_LIMIT = 10_000

CATEGORIES_PATH = "resources/python_categories_limited.json"
REPOS_20K_GTE_PATH = "resources/dataset/tags/20k+.json"
REPOS_10_20K_PATH = "resources/dataset/tags/10-20k.json"
REPOS_5_10K_PATH = "resources/dataset/tags/5-10k.json"
REPOS_1_5K_PATH = "resources/dataset/tags/1-5k.json"


REPO_SETS = {
    "20k+": REPOS_20K_GTE_PATH,
    "10-20k": REPOS_10_20K_PATH,
    "5-10k": REPOS_5_10K_PATH,
    "1-5k": REPOS_1_5K_PATH,
}


# prompts
PROMPTS_DIR = os.path.join("resources", "prompts")

## documentation gathering prompts
GATHER_SYSTEM_PROMPT_PATH = os.path.join(PROMPTS_DIR, "gather", "system.md")
GATHER_FOLLOWUP_PROMPT_PATH = os.path.join(PROMPTS_DIR, "gather", "followup.md")
GATHER_SUMMARISE_PROMPT_PATH = os.path.join(PROMPTS_DIR, "gather", "summarise.md")
GATHER_SUMMARISE_FOLLOWUP_PROMPT_PATH = os.path.join(
    PROMPTS_DIR, "gather", "summarise_followup.md"
)
GATHER_SYSTEM_PERFECT_RECALL_PROMPT_PATH = os.path.join(
    PROMPTS_DIR, "gather", "system_perfect_recall.md"
)
GATHER_SUMMARISE_PERFECT_RECALL_PROMPT_PATH = os.path.join(
    PROMPTS_DIR, "gather", "summarise.md"
)

## summarization/dockerfile generation prompts
NO_SEARCH_SYSTEM_PROMPT_PATH = os.path.join(
    PROMPTS_DIR, "no_search", "no_search_system.md"
)
DOCKERFILE_PROMPT_PATH = os.path.join(PROMPTS_DIR, "gen", "dockerfile_gen.md")
NL_PROMPT_PATH = os.path.join(PROMPTS_DIR, "gen", "installation_nl.md")

## repair prompts
DOCKERFILE_REPAIR_SYSTEM_PROMPT_PATH = os.path.join(
    PROMPTS_DIR, "repair", "dockerfile_repair_system.md"
)
DOCKERFILE_DIAGNOSIS_PROMPT_PATH = os.path.join(
    PROMPTS_DIR, "repair", "dockerfile_diagnosis.md"
)
DOCKERFILE_FAILURE_FOLLOWUP_PROMPT_PATH = os.path.join(
    PROMPTS_DIR, "repair", "dockerfile_failure_followup.md"
)
DOCKERFILE_FAILURE_PROMPT_PATH = os.path.join(
    PROMPTS_DIR, "repair", "dockerfile_failure.md"
)
DOCKERFILE_REPAIR_PROMPT_PATH = os.path.join(
    PROMPTS_DIR, "repair", "dockerfile_repair.md"
)
DOCKERFILE_REPAIR_HINTS_PATH = os.path.join(
    PROMPTS_DIR, "repair", "dockerfile_repair_hints.md"
)

# misc
DEFAULT_REPAIR_TARGET = "resources/fastapi.dockerfile"
FASTAPI = "https://github.com/tiangolo/fastapi.git"
DEFAULT_MODEL = "gpt-4o-mini"
MODELS = ["gpt-3.5-turbo-1106", "gpt-4o", "gpt-4o-mini"]
EVAL_LOGS = "logs/eval/_runs.csv"
BUILD_LOGS = "logs/build_logs"

## Cost per 1mil tokens
INPUT_COST_4O = 5.0
OUTPUT_COST_4O = 15.0

INPUT_COST_4O_MINI = 0.15
OUTPUT_COST_4O_MINI = 0.6
