#include <Python.h>
#include <cxxabi.h>
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

PyObject* getGraphCov(PyObject *self, PyObject *args) {
    if (subCgMarker == NULL) {
        Py_RETURN_NONE;
    }

    unsigned covNodes = 0;
    unsigned covEdges = 0;
    subCgMarker->getGraphCov(covNodes, covEdges);

    // Return a tuple of (covNodes, covEdges)
    PyObject* result = PyTuple_New(2);
    PyTuple_SetItem(result, 0, PyLong_FromUnsignedLong(covNodes));
    PyTuple_SetItem(result, 1, PyLong_FromUnsignedLong(covEdges));

    return result;
}


PyObject* getWholeGraph(PyObject *self, PyObject *args) {
    if (subCgMarker == NULL) {
        Py_RETURN_NONE;
    }

    set<CGNode*> cgNodes;
    subCgMarker->getReachableGraph(cgNodes);

    // nodes are represented as a list of ints (Node IDs)
    PyObject* node_list = PyList_New(0);
    for (auto it = cgNodes.begin(); it != cgNodes.end(); ++it) {
        CGNode* node = *it;
        PyList_Append(node_list, PyLong_FromLong(node->GetId()));
    }

    // edges are represented as a list of tuples (src_id, dst_id)
    PyObject* edge_list = PyList_New(0);
    for (auto it = cgNodes.begin(); it != cgNodes.end(); ++it) {
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

static string getClassFunctionName(const string &name) {
    int status = 0;
    std::unique_ptr<char, void (*)(void *)> demangled(
        abi::__cxa_demangle(name.c_str(), nullptr, nullptr, &status),
        std::free
    );

    string s = (status == 0 && demangled) ? string(demangled.get()) : name;

    // Remove parameter list
    size_t lparen = s.find('(');
    if (lparen != string::npos) {
        s = s.substr(0, lparen);
    }

    // Keep only "Class::func" or just "func"
    size_t last = s.rfind("::");
    if (last != string::npos) {
        size_t prev = s.rfind("::", last - 1);
        string cls = (prev != string::npos) ? s.substr(prev + 2, last - (prev + 2))
                                            : s.substr(0, last);
        string func = s.substr(last + 2);
        return cls + "_" + func;
    }

    return s;
}

PyObject* getNodeName(PyObject *self, PyObject *args) {
    int nodeId;
    if (!PyArg_ParseTuple(args, "i", &nodeId)) {
        Py_RETURN_NONE;
    }
    
    string rawName = subCgMarker->getNodeName(nodeId);
    string outName = getClassFunctionName(rawName);
    return PyUnicode_FromString(outName.c_str());
}

static PyMethodDef markMethods[] = {
    {"init",          initMaker, METH_VARARGS, "Init graph marker module"},
    {"getDriverGraph",getDriverGraph, METH_VARARGS, "Get driver graph for a given driver ID"},
    {"getWholeGraph", getWholeGraph,  METH_VARARGS, "Get whole graph"},
    {"getGraphCov",   getGraphCov, METH_VARARGS, "Get overall graph coverage"},
    {"getNodeName",   getNodeName, METH_VARARGS, "Get node name by id"},
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


