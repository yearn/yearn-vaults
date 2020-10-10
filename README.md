# yEarn Vault Contracts

Please read and be familiar with the [Specificaton](SPECIFICATION.md).

This repository is the set of smart contracts that are used for the Yearn Vaults.
It contains the requirements, code, deployment scripts, and tests necessary for the
core protocol, including a inheritable template strategy for use with Solidity-based
strategies that interact with yEarn Vaults. These contracts are used to create a simple
way to generate high risk-adjusted returns for depositors of various assets via best-
in-class lending protocols, liquidity pools, and community-made yield farming strategies
on Ethereum.


### Requirements

To run the project you need:

-   Python 3.8 local development environment and Node.js 10.x development environment for Ganache.
-   Brownie local environment setup. See instructions for how to install it
    [here](https://eth-brownie.readthedocs.io/en/stable/install.html).
-   Local env variables for [Etherscan API](https://etherscan.io/apis) and
    [Infura](https://infura.io/) (`ETHERSCAN_TOKEN`, `WEB3_INFURA_PROJECT_ID`).
-   Local Ganache environment installed with `npm install -g ganache-cli@6.11`.

### Installation

To use the tools that this project provides, please pull the repository from GitHub
and install its dependencies as follows.
You will need [yarn](https://yarnpkg.com/lang/en/docs/install/) installed.
It is recommended to use a Python virtual environment.

```bash
git clone https://github.com/iearn-finance/yearn-vaults
cd yearn-vaults
yarn install --lock-file
```

Compile the Smart Contracts:

```bash
brownie compile # add `--size` to see contract compiled sizes
```

### Tests

Run tests:

```bash
brownie test
```

Run tests with coverage and gas profiling:

```bash
brownie test --coverage --gas
```

### Formatting

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

### Security

For security concerns, please visit [Bug Bounty](https://github.com/iearn-finance/yearn-vaults/security/policy).

### Documentation

You can read more about yearn finance on our documentation [webpage](https://docs.yearn.finance).

### Discussion

For questions not covered in the docs, please visit [our Discord server](http://discord.yearn.finance).
