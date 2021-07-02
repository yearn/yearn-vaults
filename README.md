# Yearn Vault Contracts

Please read and be familiar with the [Specification](SPECIFICATION.md).

This repository is the set of smart contracts that are used for the Yearn Vaults.
It contains the requirements, code, deployment scripts, and tests necessary for the
core protocol, including a inheritable template strategy for use with Solidity-based
strategies that interact with Yearn Vaults. These contracts are used to create a simple
way to generate high risk-adjusted returns for depositors of various assets via best-
in-class lending protocols, liquidity pools, and community-made yield farming strategies
on Ethereum.

## Requirements

To run the project you need:

- Python 3.8 local development environment and Node.js 10.x development environment for Ganache.
- Brownie local environment setup. See instructions for how to install it
  [here](https://eth-brownie.readthedocs.io/en/stable/install.html).
- Local env variables for [Etherscan API](https://etherscan.io/apis) and
  [Infura](https://infura.io/) (`ETHERSCAN_TOKEN`, `WEB3_INFURA_PROJECT_ID`).
- Local Ganache environment installed with `npm install -g ganache-cli@6.12.1`.

## Installation

To use the tools that this project provides, please pull the repository from GitHub
and install its dependencies as follows.
You will need [yarn](https://yarnpkg.com/lang/en/docs/install/) installed.
It is recommended to use a Python virtual environment.

```bash
git clone https://github.com/yearn/yearn-vaults
cd yearn-vaults
yarn install --lock-file
```

Compile the Smart Contracts:

```bash
brownie compile # add `--size` to see contract compiled sizes
```

### Extended Instructions

The below guide covers installation on Mac, Linux, Windows, and Windows using the Windows Subsystem for Linux.

Any command `in code blocks` is meant to be executed from a Mac/Linux terminal or Windows command prompt.

0. _Note for Windows users:_ if you want to use the Windows Subsystem for Linux (WSL), go ahead and [install it now](https://docs.microsoft.com/en-us/windows/wsl/install-win10)
   - After it's installed, launch your chosen Linux subsystem
   - Follow the Linux instructions below from within your terminal, except for VSCode. Any VSCode installation happens in Windows, not the Linux subsystem.
1. Install [VSCode](https://code.visualstudio.com/docs/setup/setup-overview)
2. Install VSCode Extensions
   - [Solidity](https://marketplace.visualstudio.com/items?itemName=JuanBlanco.solidity)
   - [Python](https://marketplace.visualstudio.com/items?itemName=ms-python.python)
   - [Vyper](https://marketplace.visualstudio.com/items?itemName=tintinweb.vscode-vyper)
   - If you're using the WSL
     - Wait to install Solidity & Vyper, you'll do this in a later step
     - Install [Remote - WSL](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-wsl)
3. Install [Python 3.8](https://www.python.org/downloads/release/python-380/)
   - Linux: Refer to your distro documentation
   - [Mac installer](https://www.python.org/ftp/python/3.8.0/python-3.8.0-macosx10.9.pkg)
   - [Windows installer](https://www.python.org/ftp/python/3.8.0/python-3.8.0-amd64.exe)
4. [Setup Brownie](https://github.com/eth-brownie/brownie)
   - `python3 -m pip install --user pipx`
     - Note, if get you an error to the effect of python3 not being installed or recognized, run `python --version`, if it returns back something like `Python 3.8.x` then just replace `python3` with `python` for all python commands in these instructions
   - `python3 -m pipx ensurepath`
   - `pipx install eth-brownie`
     - If you're on Windows (pure Windows, not WSL), you'll need to install the [C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) before executing this
5. Install Node.js 10.x
   - Linux or Mac: via your [package manager](https://nodejs.org/en/download/package-manager/)
   - Windows: [x64 installer](https://nodejs.org/dist/latest-v12.x/node-v12.13.0-x64.msi)
   - Other [10.x downloads](https://nodejs.org/dist/latest-v12.x)
6. Install [Ganache](https://github.com/trufflesuite/ganache-cli)
   - `npm install -g ganache-cli@6.12.1`
7. [Install Yarn](https://classic.yarnpkg.com/en/docs/install)
8. [Install Black](https://pypi.org/project/black/)
   - `python3 -m pip install black`
9. Setup an account on [Etherscan](https://etherscan.io) and create an API key
   - Set `ETHERSCAN_TOKEN` environment variable to this key's value
     - Windows: `setx ETHERSCAN_TOKEN yourtokenvalue`
     - Mac/Linux: `echo "export ETHERSCAN_TOKEN=\"yourtokenvalue\"" | sudo tee -a ~/.bash_profile`
10. Setup an account on [Infura](https://infura.io) and create an API key
    - Set `WEB3_INFURA_PROJECT_ID` environment variable to this key's value
      - Windows: `setx WEB3_INFURA_PROJECT_ID yourtokenvalue`
      - Mac/Linux: `echo "export WEB3_INFURA_PROJECT_ID=\"yourtokenvalue\"" | sudo tee -a ~/.bash_profile`
11. Close & re-open your terminal before proceeding (to get the new environment variable values)
12. If you don't have git yet, go [set it up](https://docs.github.com/en/free-pro-team@latest/github/getting-started-with-github/set-up-git)
13. Pull the repository from GitHub and install its dependencies
    - `git clone https://github.com/yearn/yearn-vaults`
    - `cd yearn-vaults`
    - `yarn install --lock-file`
      - You may have to install with `--ignore-engines` (try this if you get an error)
14. Compile the Smart Contracts:
    - `brownie compile`
15. `brownie test tests/functional/ -s -n auto` \* If everything worked, you'll see something like the following:
    ![Console](https://i.imgur.com/wGSmCrY.png)
16. Launch VSCode
    - If you're in Windows using WSL, type `code .` to launch VSCode
      - At this point install [Solidity Compiler](https://marketplace.visualstudio.com/items?itemName=JuanBlanco.solidity) - be sure to _Install in WSL_
      - Install [Vyper](https://marketplace.visualstudio.com/items?itemName=tintinweb.vscode-vyper) as well on WSL
    - Open one of the .sol files, right click the code and click _Soldity: Change Workspace compiler version (Remote)_, Change to 0.6.12
      - Alternatively, go to File -> Preferences -> Settings
      - If you’re using WSL, go to the Remote [WSL] tab
      - Otherwise choose the Workspace tab
        - Search for _Solidity_ and copy and paste _v0.6.12+commit.27d51765_ into the _Solidity: Compile Using Remote Version_ textbox
    - Set Black as the linter.
      - You'll see a toast notification the bottom right asking about linting, choose _black_
      - If you don't see this, just go to _File_ -> _Preferences_ -> _Settings_
        - If you're using WSL, go to the _Remote [WSL]_ tab.
        - Otherwise choose the _Workspace_ tab
        - Search for _python formatting provider_ and choose _black_.
        - Search for _format on save_ and check the box
17. Lastly, you'll want to add .vscode to to your global .gitignore
    - Use a terminal on Mac / Linux, use Git Bash on Windows
    - `touch ~/.gitignore_global`
    - use your favorite editor and add `.vscode/` to the ignore file
      - Using vi:
        - `vi ~/.gitignore_global`
        - copy `.vscode/` and hit `p` in vi
        - type `:x` and hit enter
    - `git config --global core.excludesfile ~/.gitignore_global`
18. Congratulations! You're all set up.
    - Use `git pull` to stay up to date with any changes made to the source code

## Tests

If you're not familiar with brownie, see the [quickstart](https://eth-brownie.readthedocs.io/en/stable/quickstart.html).

The fastest way to run the tests is:

```bash
brownie test tests/functional/ -n auto
```

Run tests with coverage and gas profiling:

```bash
brownie test tests/functional/ --coverage --gas -n auto
```

A brief explanation of flags:

- `-s` - provides iterative display of the tests being executed
- `-n auto` - parallelize the tests, letting brownie choose the degree of parallelization
- `--gas` - generates a gas profile report
- `--coverage` - generates a test coverage report

## Formatting

Check linter rules for `*.json` and `*.sol` files:

```bash
yarn lint:check
```

Fix linter errors for `*.json` and `*.sol` files:

```bash
yarn lint:fix
```

Check linter rules for `*.py` files:

```bash
black . --check
```

Fix linter errors for `*.py` files:

```bash
black .
```

## Security

For security concerns, please visit [Bug Bounty](https://github.com/yearn/yearn-vaults/security/policy).

## Documentation

You can read more about Yearn Finance on our documentation [webpage](https://docs.yearn.finance).

## Discussion

For questions not covered in the docs, please visit [our Discord server](http://discord.yearn.finance).
