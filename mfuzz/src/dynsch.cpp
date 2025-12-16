#include <filesystem>
#include "dynsch.h"

namespace fs = std::filesystem;

struct DynSch 
{
    unsigned    sessionId    = 0;
    std::string sessionPath  = "";
    std::string fcovMapPath  = "";
    std::string activeDrvPath= "";
    std::string benchPath    = "";
    DriverMng*  driverManger = nullptr;
    Scheduler*  sch          = nullptr;

    DynSch() = default;
};

static DynSch dynsch;

static void dynsch_deinit() 
{
    fcov_deinit();

    if (dynsch.sch != NULL)
        delete dynsch.sch;

    if (dynsch.driverManger != NULL)
        delete dynsch.driverManger;
}

static inline Scheduler* dynsch_getScheduler(const char *benchPath) 
{
    if (dynsch.sch == NULL) {
        dynsch.sch = new Scheduler(benchPath);
    }
    return dynsch.sch;
}

static inline Scheduler* dynsch_getScheduler() 
{
    return dynsch.sch;
}

static inline DriverMng* dynsch_getDrvMng(const char *benchPath, int sessionId) 
{
    if (dynsch.driverManger == NULL) {
        dynsch.driverManger = new DriverMng(benchPath, sessionId);
    }
    return dynsch.driverManger;
}

void dynsch_initSession(const char *sessionPath, unsigned sessionId) 
{
    dynsch.sessionId     = sessionId;
    dynsch.sessionPath   = sessionPath;
    dynsch.fcovMapPath   = string(sessionPath) + "/fcov.map";
    dynsch.activeDrvPath = string(sessionPath) + "/active_driver.drv";

    return;
}

void dynsch_deinitSession(void) 
{
    Scheduler* sch = dynsch_getScheduler();
    if (sch) {
        sch->dump();
    }

    if (!dynsch.sessionPath.empty()) {
        std::error_code ec;
        fs::remove_all(dynsch.sessionPath, ec);
        if (ec) {
            std::cerr << "[dynsch_deinitSession] remove_all(" << dynsch.sessionPath
                      << ") failed: " << ec.message() << "\n";
        }
    }

    dynsch_deinit();
}


bool dynsch_initScheduler(const char *benchPath) 
{
    DriverMng* driverManger = dynsch_getDrvMng (benchPath, dynsch.sessionId);
    assert (driverManger != NULL);
    bool success = driverManger->loadDrivers();
    if(!success) {
        return false;
    }

    Scheduler* sch = dynsch_getScheduler(benchPath);
    if (!sch) {
        return false;
    }

    dynsch.benchPath = benchPath;
    return true;
}

std::vector<unsigned> dynsch_getCoveredFuncs() 
{
    std::vector<unsigned> covered_list;

    Scheduler* sch = dynsch_getScheduler();
    if (!sch) {
        return covered_list;
    }

    unsigned maxFuncId = sch->getGraphNodeNum() + 32;
    for (unsigned i = 1; i <= maxFuncId; i++) {
        unsigned hitNum = fcov_getNodeHitNum(i);
        if (hitNum != 0) {
            covered_list.push_back(i);
        }
    }

    return covered_list;
}


unsigned dynsch_getDriverNum() 
{
    if (dynsch.sessionId == 0) {
        return 0;
    }

    DriverMng* driverManager = dynsch.driverManger;
    assert(driverManager != NULL);
    
    return driverManager->getDriverNum();
}

vector<unsigned> dynsch_getAllDrivers() 
{
    vector<unsigned> allDrvIds;
    if (dynsch.sessionId == 0) {
        return allDrvIds;
    }

    DriverMng* driverManager = dynsch.driverManger;
    assert(driverManager != NULL);
    
    allDrvIds = driverManager->getAllDrvIds();
    return allDrvIds; 
}


bool dynsch_setActiveDriver(unsigned driverId)
{
    if (dynsch.sessionId == 0) {
        return false;
    }

    setCovBlock(); // block writes to shared map

    DriverMng* driverManger = dynsch.driverManger;
    assert(driverManger != NULL);
    driverManger->setActiveDriver(dynsch.activeDrvPath, driverId);

    Scheduler* sch = dynsch.sch;
    if (sch != NULL) {
        sch->switchDriver(driverId);
    }

    setCovNonBlock(); // release block

    std::cout << "[dynsch_setActiveDriver] SUCCESS @[" << driverId << "]\n";
    return true;
}


bool dynsch_setInitDriver(unsigned driverId)
{
    if (dynsch.sessionId == 0) {
        return false;
    }

    DriverMng* driverManger = dynsch.driverManger;
    assert(driverManger != NULL);
    driverManger->setActiveDriver(dynsch.activeDrvPath, driverId);

    fcov_setPath(dynsch.fcovMapPath.c_str());

    Scheduler* sch = dynsch.sch;
    if (sch != NULL) {
        sch->switchDriver(driverId);
    }

    std::cout << "[dynsch_setInitDriver] SUCCESS @[" << driverId << "]\n";
    return true;
}

unsigned dynsch_getWGraphSize()
{
    Scheduler* sch = dynsch.sch;
    if (sch == NULL) {
        return 0;
    }

    return sch->getWCgSize();
}


DrvRTStat dynsch_getDriverRTStat(unsigned driverId)
{
    DrvRTStat stat;

    Scheduler* sch = dynsch.sch;
    if (sch == NULL) {
        return stat;
    }

    DriverMng* driverManger = dynsch_getDrvMng("", 0);
    assert(driverManger != NULL);

    Driver& drv = driverManger->getDriver(driverId);
    drv.loadRuntimeStat();

    stat.edges         = drv.getEdges();
    stat.delta_edges   = drv.getEdgeDelta();
    stat.crashes       = drv.getCrashes();
    stat.delta_crashes = drv.getCrashDelta();

    return stat;
}

bool dynsch_sliceMarkedGraph(unsigned maxDepth)
{
    std::cout << "[dynsch_sliceMarkedGraph] Slice the CG by depth = "
              << maxDepth << "\n";

    // "final_marked_callgraph.dot" by default
    CGGraph wholeCg;
    CgDotParser dotParser("final_marked_callgraph.dot");

    dotParser.Dot2Graph(wholeCg);
    assert(wholeCg.GetNodeNum() != 0);

    unsigned graphDepth = wholeCg.ComputeNodeDepths(true);
    std::cout << "[dynsch_sliceMarkedGraph] Whole CG depth = "
              << graphDepth << "\n";

    CGViz gv("sliced-callgraph", &wholeCg, "sliced_marked_callgraph", maxDepth);
    gv.WiteGraph();
    return true;
}

bool dynsch_getDriverStatistic(const char* bench_path, const char* drv_ids)
{
    if (!bench_path) bench_path = ".";
    if (!drv_ids)    drv_ids    = "";

    CgMarker marker(bench_path, "final_marked_callgraph.dot");

    marker.reportGlobalStats(std::cout);
    marker.reportPerDriverStats(std::cout, drv_ids);
    marker.reportDriverGraph(std::cout);

    return true;
}
