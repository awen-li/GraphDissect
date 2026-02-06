import os
import ctypes
from ctypes import c_char_p

_LIB_PATH = "/usr/lib/libcgmarker.so"
_lib = None

def _load_lib():
    global _lib
    if _lib is None:
        _lib = ctypes.CDLL(_LIB_PATH)
        _lib.genFunctionIDMap.argtypes = [c_char_p]
        _lib.genFunctionIDMap.restype  = None
    return _lib

def genFunctionIDMap(bench_path: str) -> None:
    if not isinstance(bench_path, str) or not bench_path:
        raise ValueError("bench_path must be a non-empty string")

    lib = _load_lib()
    lib.genFunctionIDMap(bench_path.encode("utf-8"))
    print("genFunctionIDMap done")
