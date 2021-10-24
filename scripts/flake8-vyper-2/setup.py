import setuptools

requires = [
    "flake8>=3.0.0",
    "vyper==0.2.16"
]

long_description = ''
with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="flake8_vyper_2_16",
    license="MIT",
    version="0.2.0",
    description="Plugin for flake8 to support Vyper - supporting Vyper 2.16",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="0xbeedao, formerly Mike Shultz",
    author_email="0xbeedao@protonmail.com",
    url="https://github.com/yearn/yearn-vaults",
    py_modules=['flake8_vyper'],
    install_requires=requires,
    entry_points={
        "console_scripts": [
            'flake8-vyper = flake8_vyper:main',
        ]
    },
    classifiers=[
        "Framework :: Flake8",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: Quality Assurance",
    ],
)
