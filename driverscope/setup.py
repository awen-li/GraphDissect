from setuptools import setup, find_packages, Extension

graphmarker = Extension(
    'graphmarker',
    sources=[
        'graphmarker/driver.cpp',
        'graphmarker/subcg_marker.cpp',
        'graphmarker/subcg_profiler.cpp',
        'graphmarker/graphmarker.cpp'
    ],
    include_dirs=['graphmarker'],
    libraries=['comgraph', 'cgmarker'],
    extra_compile_args=['-std=c++17', '-fPIC'],
    language='c++'
)

setup(
    name="driverscope",
    version="0.1.0",
    description="A modular driver extraction tool for benchmarking",
    author="Your Name",
    packages=find_packages(),
    ext_modules=[graphmarker],
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
