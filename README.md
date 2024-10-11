# Beyond pip install: Evaluating LLM agents for the automated installation of Python projects

This is the research artifact for the paper 'Beyond pip install: Evaluating LLM agents for the automated installation of Python projects'.
The contents of this artifact consist of three different supplements to the paper:
1. A dataset of 40 repositories used for evaluating the automatic installation task. This can be found in `resources/dataset`.
2. The agent proposed in the paper, along with the scripts required to perform evaluation using the aforementioned dataset. The main entry point for using the agent both for evaluation and to attempt installation on a single repository is `main.py`.
3. The appendix of the paper, `appendix.pdf`, which contains three tables with additional information.

## Setup/Installation

### Requirements
All dependencies are recorded in `requirements.txt`, which can be installed using
```
pip install -r requirements.txt
```

### Version Specifications
The following are the specific versions of the software used in the experiments found in the paper:
- Python 3.10.12
- Virtual box OS: Ubuntu 22.04.4 LTS
- Docker version: 27.1.2

### Virtual Machine Setup
In order to verify the successful installation of a repository,
a dockerfile is constructed and sent to a virtual machine to be executed. \\
As such, a virtual machine is needed to make use of the code in this repository.
Create an [ubuntu](https://ubuntu.com/download/desktop) machine on [virtual box](https://www.virtualbox.org/) with the following properties:
- MACHINE_NAME = "ub"
- USER_NAME = "machine"
- PWD = "123"

It is recommended to allocate A large amount of storage to the virtual machine. 100Gb was allocated when conducting the experiments found in the paper.

Additionally, port forwarding needs to be enabled.
See [this](https://dev.to/developertharun/easy-way-to-ssh-into-virtualbox-machine-any-os-just-x-steps-5d9i) tutorial for instructions.
The host port should be `3022`.

### Install + setup docker
Docker needs to be installed in the virtual machine, using the steps outlined [here](https://docs.docker.com/engine/install/ubuntu/).

Then the `docker` group needs to be created and the user added to it:
```bash
sudo groupadd docker
sudo usermod -aG docker $USER
sudo systemctl restart docker
newgrp docker
sudo chmod 666 /var/run/docker.sock
```

verify that the setup was successful by running `sudo docker run hello-world`.

### Install openssh and git
To enable ssh connection to the virtual machine, `openssh-server` also needs to be installed:
```bash
sudo apt-get install openssh-server

sudo systemctl start ssh
sudo systemctl enable ssh

```
Git also needs to be installed to clone the taget repositories:
```bash
sudo apt-get install git-all
```


## Usage

### Running experiments
`main.py` is the entry point for running the experiments of the project.\\
When starting a new experiment, a random name will be generated for the run and will be recorded in `logs/eval/`.
Records of all messages sent to and generated by the agent during the experiments are recorded in `logs/messages/<run_name>`.
For reference, the two experiments used in the paper, one with and one without the documentation gathering step, are recorded as `appropriated-pichu` and `balding-seadra`, respectively.

To evaluate the agent on the entire dataset, including the documentation gathering step, execute the following command:
```bash
python main.py --eval --n_eval 10 --n_tries 2 --repo_sets 20k+ 10-20k 5-10k 1-5k
```
To perform the second experiment conducted in the paper, in which the documentation gathering step is skipped, include the `--PR` flag like so:
```bash
python main.py --PR --eval --n_eval 10 --n_tries 2 --repo_sets 20k+ 10-20k 5-10k 1-5k
```

Installation attempts on a single repository can also be attempted:
```bash
python main.py --repo https://github.com/Textualize/rich.git
```
If `repo` is not provided, the default repo, [fastapi](https://github.com/tiangolo/fastapi.git) will be targeted for classification instead.

### Inspecting results

The `plotter.ipynb` notebook contains the scripts used to produce the figures shown in the paper.
To visualise the results of a new experiment, the variables `GATHER_RUN` and `PR_RUN` need to be updated.

`messages.py` contains a script for converting the json format message logs of an experiment into a more human readable format.
To inspect the message logs for a specific repository, you can run:
```bash
python messages.py --run <run_name> --repo <repo_name>
```


### Calculating Heuristics
The script used to calculate the visibility and informativity metrics of the paper can be found in `ground_truth.ipynb`.