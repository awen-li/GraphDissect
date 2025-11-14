#ifndef _C_EXE_
#include <Python.h>
#endif
#include <filesystem>
#include "dynsch.h"

static DynSch dynsch = {
    .sessionId    = 0,
    .sessionPath  = "",
    .fcovMapPath  = "",
    .activeDrvPath= "",

    .benchPath = "",
    .driverManger = NULL,
    .sch = NULL
};

static void dynsch_deinit(void *module) {
    fcov_deinit();

    if (dynsch.sch != NULL)
        delete dynsch.sch;

    if (dynsch.driverManger != NULL)
        delete dynsch.driverManger;
}

static inline Scheduler* dynsch_getScheduler(const char *benchPath) {
    if (dynsch.sch == NULL) {
        dynsch.sch = new Scheduler(benchPath);
    }
    return dynsch.sch;
}

static inline Scheduler* dynsch_getScheduler() {
    return dynsch.sch;
}

static inline DriverMng* dynsch_getDrvMng(const char *benchPath, int sessionId) {
    if (dynsch.driverManger == NULL) {
        dynsch.driverManger = new DriverMng(benchPath, sessionId);
    }
    return dynsch.driverManger;
}

#ifdef _C_EXE_

bool dynsch_genFidMap(const char *benchPath) {

    Scheduler* sch = dynsch_getScheduler(benchPath);
    if (!sch) {
        return false;
    }
    sch->sch_dumpFidMap();

    return true;
}

#else

PyObject* dynsch_initSession(PyObject *self, PyObject *args) {
    const char *sessionPath;
    unsigned sessionId;
    if (!PyArg_ParseTuple(args, "is", &sessionId, &sessionPath)) {
        Py_RETURN_FALSE;
    }

    dynsch.sessionId     = sessionId;
    dynsch.sessionPath   = sessionPath;
    dynsch.fcovMapPath   = string(sessionPath) + "/fcov.map";
    dynsch.activeDrvPath = string(sessionPath) + "/active_driver.drv";

    Py_RETURN_TRUE;
}

PyObject* dynsch_deinitSession(PyObject *self, PyObject *args) {
    Scheduler* sch = dynsch_getScheduler();
    if (sch) {
        sch->dump();
    }

    filesystem::remove_all("dynsch.sessionPath");
    Py_RETURN_TRUE;
}

PyObject* dynsch_initScheduler(PyObject *self, PyObject *args) {
    const char *benchPath;
    if (!PyArg_ParseTuple(args, "s", &benchPath)) {
        Py_RETURN_FALSE;
    }

    DriverMng* driverManger = dynsch_getDrvMng (benchPath, dynsch.sessionId);
    assert (driverManger != NULL);
    bool success = driverManger->loadDrivers();
    if(!success) {
        Py_RETURN_FALSE;
    }

    Scheduler* sch = dynsch_getScheduler(benchPath);
    if (!sch) {
        Py_RETURN_FALSE;
    }

    dynsch.benchPath = benchPath;
    Py_RETURN_TRUE;
}

PyObject* dynsch_getCoveredFuncs(PyObject *self, PyObject *args) {
    Scheduler* sch = dynsch_getScheduler();
    if (!sch) {
        Py_RETURN_NONE;
    }

    PyObject *id_list = PyList_New(0);
    if (!id_list) {
        Py_RETURN_NONE;
    }

    unsigned maxFuncId = sch->getGraphNodeNum() + 32;
    for (unsigned i = 1; i <= maxFuncId; i++) {
        unsigned hitNum = fcov_getFuncHitNum(i);
        if (hitNum != 0) {
            PyObject *py_id = PyLong_FromUnsignedLong(i);
            if (!py_id) {
                Py_DECREF(id_list);
                Py_RETURN_NONE;
            }
            PyList_Append(id_list, py_id);
            Py_DECREF(py_id);
        }
    }

    return id_list;
}


PyObject* dynsch_getDriverNum(PyObject *self, PyObject *args) {
    if (dynsch.sessionId == 0) {
        Py_RETURN_NONE;
    }

    DriverMng* driverManager = dynsch.driverManger;
    assert(driverManager != NULL);
    
    unsigned drvNum = driverManager->getDriverNum();
    return PyLong_FromUnsignedLong(drvNum);
}

PyObject* dynsch_getAllDrivers(PyObject *self, PyObject *args) {
    if (dynsch.sessionId == 0) {
        Py_RETURN_FALSE;
    }

    DriverMng* driverManager = dynsch.driverManger;
    assert(driverManager != NULL);
    vector<unsigned> allDrvIds = driverManager->getAllDrvIds();

    PyObject *id_list = PyList_New(0);
    if (!id_list) {
        Py_RETURN_NONE;
    }

    for (auto itr = allDrvIds.begin(); itr != allDrvIds.end(); itr++) {
        PyObject *py_id = PyLong_FromUnsignedLong(*itr);
        if (!py_id) {
            Py_DECREF(id_list);
            Py_RETURN_NONE;
        }
        PyList_Append(id_list, py_id);
        Py_DECREF(py_id);
    }

    return id_list; 
}

PyObject* dynsch_setActiveDriver(PyObject *self, PyObject *args) {
    if (dynsch.sessionId == 0) {
        Py_RETURN_FALSE;
    }

    unsigned driverId;
    if (!PyArg_ParseTuple(args, "i", &driverId)) {
        Py_RETURN_FALSE;
    }

    setCovBlock(); // here block the writes to shared map
    DriverMng* driverManger = dynsch.driverManger;
    assert(driverManger != NULL);
    driverManger->setActiveDriver(dynsch.activeDrvPath, driverId);
     
    Scheduler* sch = dynsch.sch;
    if (sch != NULL) {
        sch->switchDriver(driverId);
    }

    setCovNonBlock(); // here release the block to write to shared map

    std::cout << "[dynsch_setActiveDriver] SUCCESS @[" << driverId <<"] \n";
    Py_RETURN_TRUE;
}


PyObject* dynsch_setInitDriver(PyObject *self, PyObject *args) {
    if (dynsch.sessionId == 0) {
        Py_RETURN_FALSE;
    }

    unsigned driverId;
    if (!PyArg_ParseTuple(args, "i", &driverId)) {
        Py_RETURN_FALSE;
    }

    DriverMng* driverManger = dynsch.driverManger;
    assert(driverManger != NULL);
    driverManger->setActiveDriver(dynsch.activeDrvPath, driverId);

    fcov_setPath(dynsch.fcovMapPath.c_str());

    Scheduler* sch = dynsch.sch;
    if (sch != NULL) {
        sch->switchDriver(driverId);
    }

    std::cout << "[dynsch_setInitDriver] SUCCESS @[" << driverId <<"] \n";
    Py_RETURN_TRUE;
}


PyObject* dynsch_getPriorDriver(PyObject *self, PyObject *args) {
    if (dynsch.sessionId == 0) {
        Py_RETURN_NONE;
    }

    DriverMng* driverManager = dynsch.driverManger;
    assert(driverManager != NULL);
    
    unsigned driverId = driverManager->getPriorDriver();
    return PyLong_FromUnsignedLong(driverId);
}

PyObject* dynsch_setDriverPriority(PyObject *self, PyObject *args) {
    if (dynsch.sessionId == 0) {
        Py_RETURN_FALSE;
    }

    unsigned driverId;
    float priority;

    if (!PyArg_ParseTuple(args, "If", &driverId, &priority)) {
        PyErr_SetString(PyExc_TypeError, "Expected arguments: (unsigned int driverId, float priority)");
        Py_RETURN_FALSE;
    }

    DriverMng* driverManager = dynsch.driverManger;
    assert(driverManager != NULL);

    bool success = driverManager->setDriverPriority(driverId, priority);
    if (!success) {
        PyErr_SetString(PyExc_ValueError, "Invalid driverId or priority set failure.");
        Py_RETURN_FALSE;
    }

    Py_RETURN_TRUE;
}

static PyObject* dynsch_getSubgraphNodes(PyObject* self, PyObject* args) {
    Scheduler *sch = dynsch.sch;
    if (sch == NULL) {
        Py_RETURN_NONE;
    }

    unsigned int driverId;
    if (!PyArg_ParseTuple(args, "I", &driverId)) {
        Py_RETURN_NONE;
    }

    // Get internal C++ data for this driver
    vector<NodeFeature> features = sch->getNodeFeatures(driverId);
    if (features.size() == 0) {
        Py_RETURN_NONE; 
    }

    PyObject* list = PyList_New(features.size());
    //cout << "@@dynsch_getSubgraphNodes: driverId = " << driverId << ", subgraph size = "<<features.size()<<"\n";
    for (size_t i = 0; i < features.size(); ++i) {
        const NodeFeature& nf = features[i];

        PyObject* dict = Py_BuildValue(
            "{sI, sI, sI, sI, sI, sI, sI}",

            "funcId", nf.funcId,         

            "coverCount", nf.coverCount, // 0
            "callDepth", nf.callDepth,   // 1

            "inDegree", nf.inDegree,     // 2
            "outDegree", nf.outDegree,   // 3

            "isFrontier", nf.isFrontier,// 4
            "isExclusive", nf.isExclusive// 5
        );

        //cout << "funcId=" << nf.funcId
        //     << ", coverCount=" << nf.coverCount
        //     << ", callDepth=" << nf.callDepth
        //     << ", inDegree=" << nf.inDegree
        //     << ", outDegree=" << nf.outDegree
        //     << ", isFrontier=" << nf.isFrontier
        //     << ", isExclusive=" << nf.isExclusive << std::endl;
        
        PyList_SetItem(list, i, dict);
    }

    return list;
}


static PyObject* dynsch_getSubgraphEdges(PyObject* self, PyObject* args) {
    Scheduler* sch = dynsch.sch;
    if (sch == NULL) {
        Py_RETURN_NONE;
    }

    unsigned int driverId;
    if (!PyArg_ParseTuple(args, "I", &driverId)) {
        Py_RETURN_NONE;
    }

    vector<pair<unsigned, unsigned>> edges = sch->getSubgraphEdges(driverId);
    if (edges.empty()) {
        Py_RETURN_NONE;
    }

    PyObject* edgeList = PyList_New(edges.size());
    for (size_t i = 0; i < edges.size(); ++i) {
        const auto& edge = edges[i];
        PyObject* tuple = Py_BuildValue("(II)", edge.first, edge.second);
        PyList_SetItem(edgeList, i, tuple);
    }

    return edgeList;
}


static PyObject* dynsch_synchronizeGraphs(PyObject* self, PyObject* args) {
    Scheduler* sch = dynsch.sch;
    if (sch == NULL) {
        Py_RETURN_NONE;
    }

    sch->synchronizeGraphs();
    Py_RETURN_NONE;
}


static PyObject* dynsch_getWGraphSize(PyObject* self, PyObject* args) {
    Scheduler* sch = dynsch.sch;
    if (sch == NULL) {
        Py_RETURN_NONE;
    }

    unsigned wCgSize = sch->getWCgSize();
    return PyLong_FromUnsignedLong(wCgSize);
}


static PyObject* dynsch_getDriverRTStat(PyObject* self, PyObject* args) {
    Scheduler* sch = dynsch.sch;
    if (sch == NULL) {
        Py_RETURN_NONE;
    }

    unsigned int driverId;
    if (!PyArg_ParseTuple(args, "I", &driverId)) {
        Py_RETURN_NONE;
    }

    DriverMng* driverManger = dynsch_getDrvMng ("", 0);
    assert (driverManger != NULL);

    Driver& drv = driverManger->getDriver(driverId);
    drv.loadRuntimeStat();

     PyObject* dict = Py_BuildValue(
            "{sI, sI, sI, sI}",

            "edges",         drv.getEdges(),
            "delta_edges",   drv.getEdgeDelta(),
            "crashes",       drv.getCrashes(),
            "delta_crashes", drv.getCrashDelta()
        );

    return dict;
}


static PyObject* dynsch_sliceMarkedGraph(PyObject* self, PyObject* args) {
    unsigned int maxDepth;
    if (!PyArg_ParseTuple(args, "I", &maxDepth)) {
        Py_RETURN_NONE;
    }
    std::cout << "[dynsch_sliceMarkedGraph] Slice the CG by depth = " << maxDepth << "\n";

    // "final_marked_callgraph.dot" by default
    CGGraph wholeCg;
    CgDotParser dotParser ("final_marked_callgraph.dot");

    dotParser.Dot2Graph (wholeCg);
    assert(wholeCg.GetNodeNum () != 0);

    unsigned graphDepth = wholeCg.ComputeNodeDepths(true);
    std::cout << "[dynsch_sliceMarkedGraph] Whole CG depth = " << graphDepth << "\n";
    CGViz gv ("sliced-callgraph", &wholeCg, "sliced_marked_callgraph", maxDepth);
    gv.WiteGraph();
    Py_RETURN_TRUE;
}

static PyObject* dynsch_getDriverStatistic(PyObject* self, PyObject* args) {
    const char* bench_path = ".";
    const char* drv_ids = ""; 

    // Optional string argument: output directory
    if (!PyArg_ParseTuple(args, "ss", &bench_path, &drv_ids)) {
        return nullptr;  // Python will set a TypeError
    }

    CgMarker marker(bench_path, "final_marked_callgraph.dot");

    // Report to stdout (or any other stream you want)
    marker.reportGlobalStats(std::cout);
    marker.reportPerDriverStats(std::cout, drv_ids);
    marker.reportDriverGraph(std::cout);

    Py_RETURN_TRUE;
}

static PyMethodDef dynschMethods[] = {
    {"initSession",       dynsch_initSession, METH_VARARGS, "Init fuzzing session"},
    {"initScheduler",     dynsch_initScheduler, METH_VARARGS, "Init dynamic scheduler"},
    {"deinitSession",     dynsch_deinitSession, METH_VARARGS, "Deinit fuzzing session"},

    {"getCoveredFuncs",   dynsch_getCoveredFuncs, METH_VARARGS, "Reads visited function IDs from fcov mmap file"},

    {"getDriverNum",      dynsch_getDriverNum, METH_VARARGS, "Get the total driver number for a benchmark"},
    {"getAllDrivers",     dynsch_getAllDrivers, METH_VARARGS, "Get all the driver IDs"},
    {"setInitDriver",     dynsch_setInitDriver, METH_VARARGS, "Set initial driver for honggfuzz"},
    {"setActiveDriver",   dynsch_setActiveDriver, METH_VARARGS, "Set active driver for honggfuzz"},
    {"getPriorDriver",    dynsch_getPriorDriver, METH_VARARGS, "Get the driver with highest priority for fuzzing"},
    {"setDriverPriority", dynsch_setDriverPriority, METH_VARARGS, "Set a driver's priority after fuzzing"},

    {"getWGraphSize",     dynsch_getWGraphSize, METH_VARARGS, "Get size of whole call graph"},
    {"synGraphs",         dynsch_synchronizeGraphs, METH_VARARGS, "Synchronize the graph: coverage and hitnum"},
    {"getSubgraphNodes",  dynsch_getSubgraphNodes, METH_VARARGS, "Get graph node features for learning"},
    {"getSubgraphEdges",  dynsch_getSubgraphEdges, METH_VARARGS, "Get graph edge features for learning"},

    {"getDriverRTStat",   dynsch_getDriverRTStat, METH_VARARGS, "Get drvier runtime state during fuzzing"},

    {"sliceMarkedGraph",  dynsch_sliceMarkedGraph, METH_VARARGS, "Slice the CG by marked nodes and depth"},
    {"getDriverStatistic",  dynsch_getDriverStatistic, METH_VARARGS, "Slice the CG by marked nodes and depth"},
    
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef dynschModule = {
    PyModuleDef_HEAD_INIT,
    "dynsch",
    NULL,
    -1,
    dynschMethods,
    NULL,
    NULL,
    NULL,
    dynsch_deinit
};

PyMODINIT_FUNC PyInit_dynsch(void) {
    return PyModule_Create(&dynschModule);
}

#endif
