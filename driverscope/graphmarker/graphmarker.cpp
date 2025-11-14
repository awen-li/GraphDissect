#include <Python.h>
#include "driver.h"
#include "subcg_marker.h"

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


PyObject* markDriver(PyObject *self, PyObject *args) {
    PyObject* drvListObj = nullptr;
    PyObject* symbolMapObj = nullptr;

    if (!subCgMarker) {
        std::cerr << "[markDriver] Module not initialized! Call init() first.\n";
        Py_RETURN_FALSE;
    }

    if (!PyArg_ParseTuple(args, "O|O", &drvListObj, &symbolMapObj)) {
        PyErr_SetString(PyExc_TypeError, "Expected a list of driver paths and optional symbol map");
        Py_RETURN_FALSE;
    }

    map<string, string> symMap;
    if (symbolMapObj && PyDict_Check(symbolMapObj)) {
        PyObject* key;
        PyObject* value;
        Py_ssize_t pos = 0;

        while (PyDict_Next(symbolMapObj, &pos, &key, &value)) {
            if (PyUnicode_Check(key) && PyUnicode_Check(value)) {
                string demangled = PyUnicode_AsUTF8(key);
                string mangled   = PyUnicode_AsUTF8(value);
                symMap[demangled] = mangled;
            }
        }
    }

    if (!PyList_Check(drvListObj)) {
        PyErr_SetString(PyExc_TypeError, "First argument must be a list of driver");
        Py_RETURN_FALSE;
    }

    Py_ssize_t len = PyList_Size(drvListObj);
    for (Py_ssize_t i = 0; i < len; ++i) {
        PyObject* item = PyList_GetItem(drvListObj, i);  // Borrowed reference
        if (!PyUnicode_Check(item)) {
            std::cerr << "Non-string element in input list.\n";
            continue;
        }

        const char* drvPath = PyUnicode_AsUTF8(item);
        if (!drvPath) {
            continue;
        }

        subCgMarker->markSugraph(drvPath, symMap);
    }

    subCgMarker->computeScore();
    subCgMarker->dump();

    subCgMarker->reportGlobalStats();
    subCgMarker->reportPerDriverStats();

    Py_RETURN_TRUE;
}

static PyMethodDef markMethods[] = {
    {"init",          initMaker, METH_VARARGS, "Init graph marker module"},
    {"markDriver",    markDriver, METH_VARARGS, "Mark a driver on CG"},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef markModule = {
    PyModuleDef_HEAD_INIT,
    "graphmarker",
    NULL,
    -1,
    markMethods,
    NULL,
    NULL,
    NULL,
    deinitMarker
};

PyMODINIT_FUNC PyInit_graphmarker(void) {
    return PyModule_Create(&markModule);
}


