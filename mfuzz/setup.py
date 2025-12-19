from setuptools import setup, find_packages

setup(
    name="FAddr2Gid",
    version="0.1.0",
    description="Generate faddr_id.map mapping function addresses/offsets to callgraph IDs",
    long_description_content_type="text/markdown",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[],
    entry_points={
        "console_scripts": [
            # This creates the CLI command: FAddr2Gid
            "FAddr2Gid=faddr2gid.__main__:main",
        ]
    },
    include_package_data=True,
)
