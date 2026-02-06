from setuptools import setup, find_packages, Extension


genfid = Extension(
    'genfid',
    sources=[
        'faddr2gid/gen_fid.cpp',
    ],
    include_dirs=['faddr2gid'],
    libraries=['comgraph', 'cgmarker'],
    extra_compile_args=['-std=c++17', '-fPIC'],
    language='c++'
)

setup(
    name="FAddr2Gid",
    version="0.1.0",
    description="Generate faddr_id.map mapping function addresses/offsets to callgraph IDs",
    long_description_content_type="text/markdown",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[],
    ext_modules=[genfid],
    entry_points={
        "console_scripts": [
            # This creates the CLI command: FAddr2Gid
            "FAddr2Gid=faddr2gid.__main__:main",
        ]
    },
    include_package_data=True,
)
