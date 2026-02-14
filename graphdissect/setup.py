from setuptools import setup, find_packages

setup(
    name="graphdissect",
    version="0.1.0",
    description="GraphDissect: driver-subgraph analysis for fuzzing campaigns",
    long_description=open("README.md", "r", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="Wen Li",
    python_requires=">=3.9",
    packages=find_packages(exclude=("tests*", "examples*")),
    include_package_data=True,
    install_requires=[
        "pandas>=2.0",
        "numpy>=1.23",
        "networkx>=3.2",
        "pyyaml>=6.0",
        "tqdm>=4.66",
    ],
    extras_require={
        "dev": ["pytest>=7.0", "ruff>=0.4", "mypy>=1.5"],
        "plots": ["matplotlib>=3.8"],
    },
    entry_points={
        "console_scripts": [
            "graphdissect=graphdissect.cli:main",
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
    ],
)

