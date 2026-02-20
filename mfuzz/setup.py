from setuptools import setup, find_packages, Extension


cgxmarker = Extension(
    'cgxmarker',
    sources=[
        'cgx/cgx_marker.cpp',
    ],
    include_dirs=['cgx'],
    libraries=['comgraph', 'cgmarker'],
    extra_compile_args=['-std=c++17', '-fPIC'],
    language='c++'
)

setup(
    name="cgx",
    version="0.1.0",
    description="building mapping between callgraph and binary",
    long_description_content_type="text/markdown",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=["angr"],
    ext_modules=[cgxmarker],
    entry_points={
        "console_scripts": [
            "cgx=cgx.__main__:main",
        ]
    },
    include_package_data=True,
)
