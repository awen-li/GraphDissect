#include <Python.h>
#include "cgmarker.h"


PyObject* genFuncIdMap(PyObject *self, PyObject *args) {
    char* benchPath;

    if (!PyArg_ParseTuple(args, "s", &benchPath)) {
        PyErr_SetString(PyExc_TypeError, "Expected a bench path");
        Py_RETURN_FALSE;
    }

    CgMarker marker (benchPath);
    Py_RETURN_TRUE;
}

static PyMethodDef markMethods[] = {
    {"genFuncIdMap",    genFuncIdMap, METH_VARARGS, "Generate function ID map for a bench path"},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef markModule = {
    PyModuleDef_HEAD_INIT,
    "genfid",
    NULL,
    -1,
    markMethods,
    NULL,
    NULL,
    NULL,
    NULL,
};

PyMODINIT_FUNC PyInit_genfid(void) {
    return PyModule_Create(&markModule);
}


