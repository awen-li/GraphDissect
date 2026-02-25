from setuptools import setup, find_packages

setup(
    name="gdriver",
    version="0.1.0",
    description="A modular driver extraction tool for benchmarking",
    author="Your Name",
    packages=find_packages(),
    ext_modules=[],
    python_requires='>=3.6',
    entry_points={
        "console_scripts": [
            # Optional CLI alias (not required for python -m usage)
        ]
    },
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: POSIX :: Linux",
    ],
)
