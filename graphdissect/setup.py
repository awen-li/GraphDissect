from setuptools import setup, find_packages, Extension

sgmarker = Extension(
    'sgmarker',
    sources=[
        'gdist/graph/drivergraph/drivergraph.cpp',
        'gdist/graph/drivergraph/sgmarker.cpp',
    ],
    include_dirs=['gdist/graph/drivergraph'],
    libraries=['comgraph', 'cgmarker'],
    extra_compile_args=['-std=c++17', '-fPIC'],
    language='c++'
)

setup(
    name="graphdissect",
    version="0.1.0",
    description="GraphDissect (gdist): driver-subgraph analysis for fuzzing campaigns",
    packages=find_packages(),
    ext_modules=[sgmarker],
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
