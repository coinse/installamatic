import argparse
import os
import re
import signal
import subprocess
import sys
import time
import uuid
from difflib import get_close_matches
from io import TextIOWrapper
from typing import List, Optional

from install_test.consts import BUILD_LOGS, FASTAPI
from install_test.utils import notify
from git_scraping import get_repository_language


SETUP_FILE = "resources/setup.sh"
MACHINE_NAME = "ub"
USER_NAME = "machine"
PWD = "123"
HOST_PORT = "3022"
DOCKER_NAME = "lmmilliken"
IMAGE_NAME = "temp_image"
TIMEOUT = 60 * 20


class OutOfStorage(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class VMController:
    def __init__(self, logs: Optional[str] = "STDOUT") -> None:
        self.logs = logs
        if self.logs is not None:
            with open(self.logs, "w") as f:
                f.write("")

    def log(self, msg, flag="a"):
        if self.logs == "STDOUT":
            print(msg)
        elif self.logs is not None:
            with open(self.logs, flag) as f:
                f.write(msg + "\n")

    def get_dockerfile(self, target_repo: str) -> str:
        """returns path to a preset dockerfile based on the langauge of target repo."""
        language = get_repository_language(target_repo).lower()
        dockerfile = os.path.abspath(
            f"resources/default_dockerfiles/{language}/Dockerfile"
        )
        if os.path.exists(dockerfile):
            return dockerfile
        else:
            return ValueError(f"No dockerfile found for langauge: {language}")

    def open_machine(self):
        """Opens the to use for testing, if the machine is already running, does nothing."""

        machines = subprocess.run(
            ["VBoxManage", "list", "vms"], capture_output=True
        ).stdout.decode("utf-8")

        if '"' + MACHINE_NAME + '"' not in machines:
            raise ValueError(f"no machine named {MACHINE_NAME}")
        running_machines = str(
            subprocess.run(
                ["VBoxManage", "list", "runningvms"], capture_output=True
            ).stdout
        )
        if '"' + MACHINE_NAME + '"' not in running_machines:
            response = str(
                subprocess.run(
                    f"VBoxManage startvm {MACHINE_NAME} --type headless".split(" "),
                    capture_output=True,
                ).stdout
            )
            if "successfully started" not in response:
                raise ValueError(f"failed to start machine")
            else:
                self.log("started machine")
        else:
            self.log("machine already started")

    def setup_repo(self, target_repo: str, dockerfile: str, ref: Optional[str] = None):
        """
        Clones target repo in a temporary directory within the vm,
        then sends the dockerfile via scp.
        """
        # make temp directory
        cmd = (
            f"sshpass -p {PWD} ssh -p {HOST_PORT} {USER_NAME}@localhost "
            f"echo $(mktemp -d)"
        )
        tmp_dir = (
            subprocess.run(cmd.split(" "), capture_output=True)
            .stdout.decode("utf-8")
            .strip()
        )
        self.log(f"TEMP DIR: {tmp_dir}")
        # clone target repo in temp directory
        repo_name = target_repo.split("/")[-1][:-4]
        cmd = (
            f"/usr/bin/sshpass -p {PWD} ssh -T -p {HOST_PORT} {USER_NAME}@localhost "
            f"cd {tmp_dir} ; git clone --recursive {target_repo} ; cd {repo_name} ; rm .dockerignore"
        )
        if ref is not None:
            cmd = cmd + f"; git checkout {ref}"
        cmd = cmd.split(" ")

        try:
            resp = subprocess.run(cmd, capture_output=True, timeout=TIMEOUT)
        except subprocess.TimeoutExpired:
            resp = subprocess.run(cmd, capture_output=True, timeout=TIMEOUT)

        self.log(resp.stderr.decode("utf-8").strip())
        self.log(resp.stdout.decode("utf-8").strip())

        # get name of the directory where the repo was cloned to (-4 to remove '.git')
        repo_name = target_repo.split("/")[-1][:-4]
        repo_dir = f"{tmp_dir}/{repo_name}"
        print(repo_dir)
        # send dockerfile to vm
        subprocess.run(
            (
                f"/usr/bin/sshpass -p {PWD} "
                f"scp -P {HOST_PORT} "
                "-oStrictHostKeyChecking=no -oUserKnownHostsFile=/dev/null "
                f"{dockerfile} {USER_NAME}@localhost:{repo_dir}/Dockerfile"
            ).split(" ")
        )
        dockerfile = dockerfile.split("/")[-1]
        return tmp_dir, repo_dir

    def build_project(self, repo_dir: str, logs: str) -> bool:
        """Run docker build in the virtual machine and stream progress."""
        # build dockerfile
        cmd = (
            f"sshpass -p {PWD} ssh -p {HOST_PORT} "
            "-oStrictHostKeyChecking=no -oUserKnownHostsFile=/dev/null "
            f"{USER_NAME}@localhost "
            f"cd {repo_dir} ; docker build --no-cache -t {IMAGE_NAME} ."
        ).split(" ")
        with open(logs, "a") as f:
            progress, timeout = self.monitor_process(cmd, f, TIMEOUT)
        if timeout:
            with open(logs, "a") as f:
                progress, timeout = self.monitor_process(cmd, f, TIMEOUT)

        #     progress = subprocess.Popen(cmd, stdout=f, stderr=f)
        # progress.wait()

        with open(logs, "r") as f:
            output = f.readlines()
        passed = False
        ran = False
        for i, line in enumerate(output):
            if "fatal" in line and "No space left on device" in line:
                raise OutOfStorage()
            if (
                (
                    ("==" in line and " in " in line)
                    or "snapshots" in line
                    or ("tests" in line)
                    or len(output) - i < 30
                )
                and "passed" in line
            ) or (
                ran
                and (
                    len(line.split()) > 0
                    and line.split()[-1].strip() == "OK"
                    or ("(" in line and line.split("(")[0].split()[-1] == "OK")
                )
            ):
                passed = True
            elif "Ran" in line and "tests in" in line:
                ran = True
        if timeout:
            msg = (
                "process timed out twice! "
                f"(took more than {TIMEOUT} seconds) Aborting...\n"
            )
            f.write(msg)
            notify(msg)
            return False
        if not passed:
            try:
                err = "Error running docker build on virtual machine:\n" + "\n".join(
                    [p.decode("utf-8") for p in progress.stderr]
                )
                self.log(err)
                print(err)
            except:
                pass
            return False
        else:
            succ = (
                "At least 1 test passed.\n"
                "Docker build completed successfully on virtual machine."
            )
            self.log(succ)
            print(succ)
            return True

    def monitor_process(self, cmd: List[str], f: TextIOWrapper, timeout_val: int):
        progress = subprocess.Popen(cmd, stdout=f, stderr=f)
        start_time = time.time()
        timeout = False
        interrupted = False
        try:
            while True:
                # get latest output
                if progress.poll() is not None:
                    break
                elif time.time() - start_time > timeout_val:
                    if not interrupted:
                        # First try to cancel the process with an interrupt
                        # os.killpg(os.getpgid(progress.pid), signal.SIGINT)
                        os.kill(progress.pid, signal.SIGINT)
                        notify(f"INTERRUPTING")
                        start_time = time.time()
                        timeout_val = 20
                        interrupted = True
                    else:
                        # If the interrupt did not work, raise a timeout
                        raise subprocess.TimeoutExpired(cmd, timeout_val)

        except subprocess.TimeoutExpired:
            notify("KILLING PROCESS")
            progress.kill()
            timeout = True
        finally:
            progress.wait()
        return progress, timeout

    def clear_cache(self):
        subprocess.run(
            (
                f"/usr/bin/sshpass -p {PWD} ssh -T -p {HOST_PORT} {USER_NAME}@localhost "
                "docker system prune -a -f"
            ).split(" "),
        )

    def cleanup(self, tmp_dir: str, keep_image: bool = False, keep_repo: bool = False):
        """Delete docker image and temporary file after execution."""
        if not keep_image:
            # remove newly created docker image
            self.log("removing docker image...")
            subprocess.run(
                (
                    f"sshpass -p {PWD} ssh -T -p {HOST_PORT} {USER_NAME}@localhost "
                    f"docker image rm {IMAGE_NAME}"
                ).split(" "),
            )
        if not keep_repo:
            # clear temp directory
            self.log("clearing temp directory")
            subprocess.run(
                (
                    f"/usr/bin/sshpass -p {PWD} ssh -T -p {HOST_PORT} {USER_NAME}@localhost "
                    f"rm -rf {tmp_dir}"
                ).split(" "),
            )

    def test_dockerfile(
        self,
        target_repo: str,
        dockerfile: Optional[str] = None,
        keep_image: bool = False,
        keep_repo: bool = False,
        logs: Optional[str] = None,
        ref: Optional[str] = None,
    ):
        """
        Tests a dockerfile by connecting to a virtual machine,
        sending the dockerfile to the vm and then building the docker image inside the vm.
        """

        if dockerfile is None:
            dockerfile = self.get_dockerfile(target_repo)
            self.log(f"using dockerfile: {dockerfile}")

        with open(dockerfile, "r") as f:
            df_contents = f.read()
        self.log(df_contents, "w")

        self.open_machine()

        try:
            tmp_dir, repo_dir = self.setup_repo(target_repo, dockerfile, ref=ref)
            self.log("setup repo.")
            success = self.build_project(repo_dir=repo_dir, logs=logs or self.logs)
        except OutOfStorage:
            self.cleanup(tmp_dir)
            self.clear_cache()
            notify("RAN OUT OF STORAGE!! RESTARTING")
            tmp_dir, repo_dir = self.setup_repo(target_repo, dockerfile, ref=ref)
            self.log("setup repo.")
            success = self.build_project(repo_dir=repo_dir, logs=logs or self.logs)

        except Exception as e:
            success = False
            if __name__ == "__main__":
                raise e
            else:
                print(e)
        except KeyboardInterrupt as e:
            success = False
        self.cleanup(tmp_dir, keep_image=keep_image, keep_repo=keep_repo)

        return success


def test_dockerfile(
    url: str,
    dockerfile: str,
    repo_name: Optional[str] = None,
    vmc: Optional[VMController] = None,
    ref: Optional[str] = None,
) -> bool:
    dockerfile_path = "logs/dockerfiles/Dockerfile"
    name = url.split("/")[-1][:-4]

    with open(dockerfile_path, "w") as f:
        f.write(dockerfile)
    print(dockerfile)

    if vmc is None:
        logs = f"{BUILD_LOGS}/{repo_name or name}.log"
        vmc = VMController(logs)

    (f"\nattempting to build using dockerfile, logs written to {vmc.logs}.")
    return vmc.test_dockerfile(url, dockerfile_path, ref=ref)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dockerfile",
        help="path to a dockerfile you want to test",
        default="resources/working_dockerfiles/20k+/fastapi.dockerfile",
    )
    parser.add_argument(
        "--repo", help="url to a repo you want to test", default=FASTAPI
    )
    args = parser.parse_args()
    controller = VMController()
    controller.test_dockerfile(target_repo=args.repo, dockerfile=args.dockerfile)
