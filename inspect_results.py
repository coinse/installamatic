import argparse
import json
import os
from pprint import pprint
from typing import Any, Dict, List, Optional, Union

import matplotlib.pyplot as plt
import numpy as np

from doc_test.consts import MODELS

SUCCESS = "✅"
FAIL = "❌"
INSUFFICIENT = "➖"
MISSING = "❓"
status_dict = {"success": SUCCESS, "failure": FAIL, "insufficient": INSUFFICIENT}


def array_to_markdown_table(array):
    if not array or not array[0]:
        return ""

    header = array[0]
    rows = array[1:]

    # Create header row
    header_row = "| " + " | ".join(header) + " |"

    # Create separator row
    separator_row = "| " + " | ".join(["---"] * len(header)) + " |"

    # Create data rows
    data_rows = "\n".join("| " + " | ".join(map(str, row)) + " |" for row in rows)

    # Combine all parts
    markdown_table = "\n".join([header_row, separator_row, data_rows])

    return markdown_table


def get_rows(repo_data: Dict[str, Dict[str, Any]], cols: List[str]):
    rows = [
        [repo_name] + [repo_dict[col] if col in repo_dict else MISSING for col in cols]
        for repo_name, repo_dict in repo_data.items()
    ]
    ret = [["repo"] + cols]
    ret.extend(rows)
    return ret


def get_data(runs) -> str:
    runs_dir = "logs/eval"
    contents = os.listdir(runs_dir)
    run_paths = []
    for run in runs:
        run_paths.extend([run_path for run_path in contents if run in run_path])
    print(run_paths)
    data = []
    for run_path in run_paths:
        with open(os.path.join(runs_dir, run_path), "r") as f:

            data.extend(json.load(f))

    repos = set(item for round in data for item in round.keys())
    pprint(repos)
    print(f"### {', '.join(runs)}:")
    repo_data = {repo: get_repo_data(data, repo) for repo in repos}
    rows = get_rows(
        repo_data,
        [
            "build_succ",
            "avg_tries",
            "avg_duration",
            "avg_retrieved",
            "avg_recall",
            "n_relevant",
            "avg_irrelevant",
            "build_status",
            "n_tries",
        ],
    )
    return rows


def get_repo_data(data: List[Dict[str, Any]], repo: str):
    build = [
        (
            FAIL
            if "build_status" not in rnd[repo]
            else status_dict[rnd[repo]["build_status"]]
        )
        for rnd in data
        if repo in rnd and "build_status" in rnd[repo]
    ]

    build_succ = f"{len([b for b in build if b == SUCCESS])}/{len(build)}"

    n_tries = [
        (
            -1
            if "build_status" not in rnd[repo] or "n_tries" not in rnd[repo]
            else rnd[repo]["n_tries"]
        )
        for rnd in data
        if repo in rnd
    ]
    avg_tries = [
        rnd[repo]["n_tries"] + 1
        for rnd in data
        if repo in rnd and "n_tries" in rnd[repo]
    ]
    avg_tries = round(sum(avg_tries) / len(avg_tries), 3) if len(avg_tries) > 0 else -1
    durations = [
        rnd[repo]["duration"] if "duration" in rnd[repo] else 0
        for rnd in data
        if repo in rnd
    ]
    avg_durations = (
        round(sum(durations) / len(durations), 3) if len(durations) > 0 else -1
    )

    repo_data = {
        "build_status": "".join(build),
        "build_succ": build_succ,
        "n_tries": n_tries,
        "avg_tries": avg_tries,
        "avg_duration": avg_durations,
    }

    if any(["retrieved" in repo for repo in data[0].values()]):
        repo_data = table_gather(data, repo, repo_data)
    elif any(["categories" in repo for repo in data[0].values()]):
        repo_data = table_class(data, repo, repo_data)
    return repo_data


def table_gather(data, repo, repo_data):
    recall = [
        rnd[repo]["recall"] for rnd in data if repo in rnd and "recall" in rnd[repo]
    ]
    n_retrieved = [
        len(list(set(rnd[repo]["retrieved"])))
        for rnd in data
        if repo in rnd and "retrieved" in rnd[repo]
    ]
    n_irrelevant = [
        len(list(set(rnd[repo]["retrieved"]).difference(set(rnd[repo]["relevant"]))))
        for rnd in data
        if repo in rnd and "retrieved" in rnd[repo]
    ]
    n_relevant = [
        len(rnd[repo]["relevant"])
        for rnd in data
        if repo in rnd and "relevant" in rnd[repo]
    ]
    if len(n_relevant) > 0:
        n_relevant = max(n_relevant)
    else:
        n_relevant = -1
    avg_recall = round(sum(recall) / len(recall), 3) if len(recall) > 0 else 0
    avg_retrieved = (
        round(sum(n_retrieved) / len(n_retrieved), 3) if len(recall) > 0 else 0
    )
    avg_irrelevant = (
        round(sum(n_irrelevant) / len(n_irrelevant), 3) if len(recall) > 0 else 0
    )
    repo_data["recall"] = recall
    repo_data["n_relevant"] = n_relevant
    repo_data["avg_irrelevant"] = avg_irrelevant
    repo_data["avg_recall"] = avg_recall
    repo_data["avg_retrieved"] = avg_retrieved
    return repo_data


def table_class(data, repo, repo_data) -> str:
    repo_data["classification"] = "".join(
        [SUCCESS if rnd[repo]["correct"] else FAIL for rnd in data]
    )
    # data = [("repo", "classification status", "build status", "n_tries")]
    # data.extend(list(zip(repos, classification, build, n_tries)))
    return repo_data


def get_repo_tags():
    repos = [
        "eval/resources/python_repos_5k-1k.json",
        "eval/resources/python_repos_10k-5k.json",
        "eval/resources/python_repos_20k+.json",
    ]
    ret = []
    for r in repos:
        ret.extend(json.load(open(r, "r")))
    ret = {r["url"].split("/")[-1][:-4]: r for r in ret}
    return ret


def group_by_tags(data: List[Any], tags: List[str], repos: Dict[str, Any]):
    ret = []
    for tag in tags:
        ret.append(list(filter(lambda x: tag in repos[x[0]]["tags"], data)))
    ret.append(
        list(
            filter(lambda x: not any(tag in repos[x[0]]["tags"] for tag in tags), data)
        )
    )
    return ret


def scatter(
    x_data: List[Union[int, float]],
    y_data: List[Union[int, float]],
    x_label: str = "x",
    y_label: str = "y",
    title: str = "title",
    lobf: bool = True,
):

    plt.scatter(x_data, y_data)

    if lobf:
        x = np.array(x_data)
        y = np.array(y_data)
        m, b = np.polyfit(x, y, 1)
        plt.plot(x, m * x + b, color="red")
    plt.title(title)
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    save_show(title)


def multi_scatter(
    x_data: List[List[Union[int, float]]],
    y_data: List[List[Union[int, float]]],
    group_labels: List[str],
    x_label: str = "x",
    y_label: str = "y",
    title: str = "title",
    lobf: bool = False,
):
    colors = plt.colormaps["Dark2"]
    for i, (xd, yd, label) in enumerate(zip(x_data, y_data, group_labels)):
        plt.scatter(xd, yd, color=colors(i), label=label)
        if lobf:
            x = np.array(xd)
            y = np.array(yd)
            m, b = np.polyfit(x, y, 1)
            plt.plot(x, m * x + b, color=colors(i))
    # plt.scatter(x_data, y_data)

    plt.title(title)
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.legend()
    save_show(title)


def bar(
    values: List[Union[float, int]],
    categories: List[str],
    x_label: str = "x",
    y_label: str = "y",
    title: str = "title",
    avg: Optional[float] = None,
):
    categories, values = zip(*sorted(zip(categories, values), key=lambda x: x[1]))
    plt.bar(categories, values)
    if avg is not None:
        plt.axhline(avg, color="red", label="average build rate")
        plt.legend()
    plt.xlabel(x_label)
    plt.xticks(rotation=90)
    plt.ylabel(y_label)
    plt.title(title)
    plt.tight_layout()
    save_show(title)


def save_show(fname):
    if fname is not None:
        plt.savefig(f"{run_dir}/{fname.replace(' ', '_')}")
    plt.show()


def inspect(
    data,
    do_table: bool = False,
    do_scatter: bool = False,
    do_bar: bool = False,
    groups=None,
    group_labels=None,
    title=None,
    lobf=True,
):
    if do_table:
        print(array_to_markdown_table(data))
    if do_scatter:
        if groups is not None:
            recall = [[row[5] for row in group] for group in groups]
            accuracy = [[1 - (row[7] / row[4]) for row in group] for group in groups]
            f1 = [
                [2 * ((r * a) / (r + a)) if r + a > 0 else 0 for r, a in zip(r_s, a_s)]
                for r_s, a_s in zip(recall, accuracy)
            ]
            # f1 = []
            # for r_s, a_s in zip(recall, accuracy):
            #     f1.append([])
            #     for r, a in zip(r_s, a_s):

            build_rate = [
                [int(row[1].split("/")[0]) / int(row[1].split("/")[1]) for row in group]
                for group in groups
            ]
            multi_scatter(
                recall,
                build_rate,
                group_labels,
                "recall",
                "build_rate",
                title=f"recall by {title}" if title is not None else None,
                lobf=lobf,
            )
            multi_scatter(
                accuracy,
                build_rate,
                group_labels,
                "accuracy",
                "build_rate",
                title=f"accuracy by {title}" if title is not None else None,
                lobf=lobf,
            )
        else:
            recall = [row[5] for row in data[1:]]
            irrelevant = [row[7] / row[4] for row in data[1:]]
            accuracy = [1 - (row[7] / row[4]) for row in data[1:]]
            retrieved = [row[4] for row in data[1:]]
            build_rate = [
                int(row[1].split("/")[0]) / int(row[1].split("/")[1])
                for row in data[1:]
            ]
            f1 = [
                2 * ((r * a) / (r + a)) if r + a > 0 else 0
                for r, a in zip(recall, accuracy)
            ]
            scatter(
                recall,
                build_rate,
                "recall",
                "build_rate",
                lobf=lobf,
                title="recall-build_rate",
            )
            scatter(
                accuracy,
                build_rate,
                "accuracy",
                "build_rate",
                lobf=lobf,
                title="accuracy-build_rate",
            )
    if do_bar:
        build_rate = [
            int(row[1].split("/")[0]) / int(row[1].split("/")[1]) for row in data[1:]
        ]
        avg_build_rate = sum(build_rate) / len(build_rate)
        groups = group_by_tags(data[1:], repo_tags, repos)[:-1]
        build_rate_by_tag = [
            [int(row[1].split("/")[0]) / int(row[1].split("/")[1]) for row in group]
            for group in groups
        ]
        avg_build_rate_by_tag = [sum(g) / len(g) for g in build_rate_by_tag]
        print(len(avg_build_rate_by_tag))
        print(len(groups))
        pprint(list(zip(repo_tags, avg_build_rate_by_tag)))
        bar(
            avg_build_rate_by_tag,
            repo_tags,
            "tag",
            "build_rate",
            title="average build rate for each tag",
            avg=avg_build_rate,
        )


DEFAULT_RUN = "trapped-mawile"
DEFAULT_GROUP = False

try:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--run",
        nargs="+",
        default=[DEFAULT_RUN],
        help="path to the run to visualise",
    )
    parser.add_argument(
        "--group",
        action="store_true",
        help="whether to group results when inspecting",
    )
    args = parser.parse_args()
    run = args.run
    do_group = args.group
except:
    run = [DEFAULT_RUN]
    do_group = DEFAULT_GROUP
data = get_data(run)
print(len(data))
repos = get_repo_tags()
repo_tags = list(set([t for repo in repos.values() for t in repo["tags"]]))
groups = group_by_tags(data[1:], ["requirements", "poetry"], get_repo_tags())
group_sets = [["requirements", "poetry"], ["pytest", "unittest"]]
group_data = [group_by_tags(data[1:], group, repos) for group in group_sets]
group_titles = ["installation method", "test method"]
run_dir = f"figs/{'-'.join(run)}"
os.makedirs(run_dir, exist_ok=True)
if __name__ == "__main__":
    if do_group:
        for group, group_labels, group_title in zip(
            group_data, group_sets, group_titles
        ):
            inspect(
                data,
                do_table=False,
                do_scatter=True,
                groups=group,
                group_labels=group_labels + ["other"],
                title=group_title,
                lobf=True,
            )
    else:
        inspect(data, do_bar=True, lobf=True)
# for group in groups:
#     print(len(group))
#     inspect([data[0]] + group, do_scatter=True)
