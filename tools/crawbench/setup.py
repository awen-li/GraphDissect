from setuptools import setup, find_packages

setup(
    name="ossbench",
    version="0.1.0",
    description="Benchmark collector for OSS-Fuzz C projects",
    author="",
    packages=find_packages(),
    package_data={
        "ossbench": ["domains.yml"],
    },
    include_package_data=True,
    python_requires=">=3.8",
    install_requires=[
        "PyYAML>=6.0",
    ],
    entry_points={
        "console_scripts": [
            "ossbench=ossbench.cli:main",
        ]
    },
)

