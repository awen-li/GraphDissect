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

PyObject* getDriverGraph(PyObject *self, PyObject *args) {
    int drvId;
    if (!PyArg_ParseTuple(args, "i", &drvId)) {
        Py_RETURN_NONE;
    }

    if (subCgMarker == NULL) {
        Py_RETURN_NONE;
    }

    set<CGNode*> drvNodes;
    subCgMarker->getDriverGraph(drvId, drvNodes);

    // nodes are represented as a list of ints (Node IDs)
    PyObject* node_list = PyList_New(0);
    for (auto it = drvNodes.begin(); it != drvNodes.end(); ++it) {
        CGNode* node = *it;
        PyList_Append(node_list, PyLong_FromLong(node->GetId()));
    }

    // edges are represented as a list of tuples (src_id, dst_id)
    PyObject* edge_list = PyList_New(0);
    for (auto it = drvNodes.begin(); it != drvNodes.end(); ++it) {
        CGNode* node = *it;
        for (auto edge_it = node->OutEdgeBegin(); edge_it != node->OutEdgeEnd(); ++edge_it) {
            CGEdge* edge = *edge_it;

            unsigned src_id = edge->GetSrcID();
            unsigned dst_id = edge->GetDstID();
            PyObject* edge_tuple = PyTuple_Pack(2, PyLong_FromLong(src_id), PyLong_FromLong(dst_id));
            PyList_Append(edge_list, edge_tuple);
            Py_DECREF(edge_tuple);
        }
    }

    // Return a tuple of (node_list, edge_list)
    PyObject* result = PyTuple_New(2);
    PyTuple_SetItem(result, 0, node_list);
    PyTuple_SetItem(result, 1, edge_list);

    return result;
}

static PyMethodDef markMethods[] = {
    {"init",          initMaker, METH_VARARGS, "Init graph marker module"},
    {"getDriverGraph",getDriverGraph, METH_VARARGS, "Get driver graph for a given driver ID"},
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


