from setuptools import setup, Extension

dynsch = Extension(
    'dynsch',
    sources=['dynsch/fcov.cpp', 'dynsch/driver.cpp', 'dynsch/dynsch.cpp', 'dynsch/scheduler.cpp'],
    extra_compile_args=['-std=c++17'],
    extra_link_args=['-lcomgraph', '-lcgmarker'],
    language='c++',
)

setup(
    name='FuzzPilot',
    version='0.1.0',
    description='Graph-driven driver scheduler for AFL++',
    packages=['fuzzpilot'],
    ext_modules=[dynsch],
    install_requires=[
        'torch>=1.10',
        'torch_geometric>=2.0.0',
        'numpy>=1.20',
        'setuptools',
    ],
    entry_points={
        'console_scripts': [],
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'Operating System :: POSIX :: Linux',
    ],
)

