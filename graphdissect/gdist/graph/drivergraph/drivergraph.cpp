#include <Python.h>
#include "sgmarker.h"

static SubCgMarker* subCgMarker = NULL;

static void deinitMarker(void *module) {
    if (subCgMarker != NULL)
        delete subCgMarker;
}

PyObject* initMaker(PyObject *self, PyObject *args) {
    const char *benchPath;
    if (!PyArg_ParseTuple(args, "s", &benchPath)) {
        Py_RETURN_FALSE;
    }

    subCgMarker = new SubCgMarker(benchPath);
    assert(subCgMarker != NULL);

    Py_RETURN_TRUE;
}

static PyMethodDef markMethods[] = {
    {"init",          initMaker, METH_VARARGS, "Init graph marker module"},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef markModule = {
    PyModuleDef_HEAD_INIT,
    "sgmarker",
    NULL,
    -1,
    markMethods,
    NULL,
    NULL,
    NULL,
    deinitMarker
};

PyMODINIT_FUNC PyInit_sgmarker(void) {
    return PyModule_Create(&markModule);
}


