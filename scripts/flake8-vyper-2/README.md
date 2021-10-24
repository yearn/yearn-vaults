# flake8-vyper

Flake8 wrapper to support Vyper.  This is forked from the original project at https://github.com/mikeshultz/flake8-vyper by @0xbeedao for Yearn.

## Install

Preferably set up a Virtualenv.
    cd flake8-vyper-2
    python -m venv .
    python setup.py install
    
## Usage

    python flake8_vyper.py [options] file1 [file2 ...]

## Configuration

You can use all the same CLI options as flake8, but config should be done in the `flake8-vyper`
section to prevent conflicts.  Here's an example `tox.ini` for a project with python and vyper:

    [flake8]
    exclude = .git,__pycache__,build
    max-line-length = 100
    filename = *.py

    [flake8-vyper]
    exclude = .git,__pycache__,build
    max-line-length = 100
    filename = *.vy
