from setuptools import setup, find_packages

setup(
    name="graphdissect",
    version="0.1.0",
    description="GraphDissect (gdist): driver-subgraph analysis for fuzzing campaigns",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "pandas>=2.0",
        "numpy>=1.23",
        "networkx>=3.2",
        "pyyaml>=6.0",
        "tqdm>=4.66",
    ],
    entry_points={
        "console_scripts": [
            "gdist=gdist.cli:main",
        ]
    },
)
