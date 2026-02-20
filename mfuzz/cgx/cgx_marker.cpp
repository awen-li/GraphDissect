#include <Python.h>
#include "cgmarker.h"

CgMarker *g_marker = NULL;


PyObject* initMarker(PyObject *self, PyObject *args) {
    char* benchPath;

    if (!PyArg_ParseTuple(args, "s", &benchPath)) {
        PyErr_SetString(PyExc_TypeError, "Expected a bench path");
        Py_RETURN_FALSE;
    }

    if (g_marker != NULL) {
        delete g_marker;
    }

    g_marker = new CgMarker(benchPath);
    assert(g_marker != NULL);

    Py_RETURN_TRUE;
}

PyObject* getAllFunctions(PyObject *self, PyObject *args) {
    if (g_marker == NULL) {
        PyErr_SetString(PyExc_RuntimeError, "Marker not initialized");
        Py_RETURN_FALSE;
    }

    CGGraph* wCg = g_marker->getWholeCg();
    PyObject* pyList = PyList_New(wCg->GetNodeNum());
    size_t index = 0;
    for (auto itr = wCg->begin(); itr != wCg->end(); ++itr) {
        CGNode* node = itr->second;
        PyList_SetItem(pyList, index++, PyUnicode_FromString(node->GetFName().c_str()));
    }
    return pyList;
}

PyObject* setNodeKey(PyObject *self, PyObject *args) {
    char* FName;
    uint32_t FAddr;

    if (!PyArg_ParseTuple(args, "si", &FName, &FAddr)) {
        PyErr_SetString(PyExc_TypeError, "Expected a function name and address");
        Py_RETURN_FALSE;
    }

    if (g_marker == NULL) {
        PyErr_SetString(PyExc_RuntimeError, "Marker not initialized");
        Py_RETURN_FALSE;
    }

    g_marker->setNodeKey(FName, FAddr);
    Py_RETURN_TRUE;
}

PyObject* setEdgeKey(PyObject *self, PyObject *args) {
    char* SrcFName;
    char* DstFName;
    uint32_t retAddr;

    if (!PyArg_ParseTuple(args, "ssi", &SrcFName, &DstFName, &retAddr)) {
        PyErr_SetString(PyExc_TypeError, "Expected source and destination function names and addresses");
        Py_RETURN_FALSE;
    }

    if (g_marker == NULL) {
        PyErr_SetString(PyExc_RuntimeError, "Marker not initialized");
        Py_RETURN_FALSE;
    }

    g_marker->setEdgeKey(SrcFName, DstFName, retAddr);
    Py_RETURN_TRUE;
}

PyObject* dumpGraph(PyObject *self, PyObject *args) {

    if (g_marker == NULL) {
        PyErr_SetString(PyExc_RuntimeError, "Marker not initialized");
        Py_RETURN_FALSE;
    }

    g_marker->dump();
    Py_RETURN_TRUE;
}

PyObject* getCallees(PyObject *self, PyObject *args) {
    char* FName;

    if (!PyArg_ParseTuple(args, "s", &FName)) {
        PyErr_SetString(PyExc_TypeError, "Expected a function name");
        Py_RETURN_FALSE;
    }

    if (g_marker == NULL) {
        PyErr_SetString(PyExc_RuntimeError, "Marker not initialized");
    }

    CGNode* node = g_marker->getWholeCg()->GetNode(FName);
    if (!node) {
        PyErr_SetString(PyExc_RuntimeError, "Function not found in call graph");
        Py_RETURN_FALSE;
    }
    
    std::vector<CGNode*> callees;
    for (auto eItr = node->OutEdgeBegin(); eItr != node->OutEdgeEnd(); eItr++) {
        CGEdge* edge = *eItr;
        CGNode* callee = edge->GetDstNode();
        callees.push_back(callee);
    }
    
    PyObject* pyList = PyList_New(callees.size());
    for (size_t i = 0; i < callees.size(); i++) {
        PyList_SetItem(pyList, i, PyUnicode_FromString(callees[i]->GetFName().c_str()));
    }
    return pyList;
}

static PyMethodDef markMethods[] = {
    {"initMarker",      initMarker, METH_VARARGS, "Initialize the marker with a bench path"},
    {"getAllFunctions", getAllFunctions, METH_VARARGS, "Get all functions in the call graph"},
    {"setNodeKey",      setNodeKey, METH_VARARGS, "Set node key for profiling"},
    {"setEdgeKey",      setEdgeKey, METH_VARARGS, "Set edge key for profiling"},
    {"getCallees",      getCallees, METH_VARARGS, "Get callees for a function"},
    {"dumpGraph",       dumpGraph, METH_VARARGS, "Dump graph to file"},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef markModule = {
    PyModuleDef_HEAD_INIT,
    "cgxmarker",
    NULL,
    -1,
    markMethods,
    NULL,
    NULL,
    NULL,
    NULL,
};

PyMODINIT_FUNC PyInit_cgxmarker(void) {
    return PyModule_Create(&markModule);
}


