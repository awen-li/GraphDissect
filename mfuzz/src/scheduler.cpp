#include <cmath>
#include "scheduler.h"
#include "driver.h"


SyncStats Scheduler::synchronizeGraphs()
{
    SyncStats stats;
    if (activeDriver == 0 ) {
        return stats;
    }
    
    // 1. sync node hit num to graph
    unsigned newHitNodes = 0;
    unsigned totalHitNodes = 0;
    vector<unsigned> updatedNodes = synchronizeNodes(activeDriver, newHitNodes, totalHitNodes);

    // 2. sync edge hit num to graph
    unsigned newHitEdges = synchronizeEdges(updatedNodes, activeDriver);
    stats.newNodes = newHitNodes;
    stats.newEdges = newHitEdges;
    stats.totalNodes = totalHitNodes;

    std::cout << "[Scheduler] Switched to driver " << activeDriver
              << "[" <<totalHitNodes<<" / "<<getGraphSize()<<"]"
              << " (updated " << updatedNodes.size() 
              << " nodes with newly discovered "<<newHitNodes<<" nodes and "<<newHitEdges<<" edges)\n";
    return stats;
}


set<unsigned> Scheduler::getCoveredFuncs()
{
    set<unsigned> covFuncs;

    CGGraph* wCg = cgmk->getWholeCg();
    for (auto itr = wCg->begin(); itr != wCg->end(); itr++) {
        CGNode* node = itr->second;
        
        node->HitNum = getNodeHitNum(node->GetId());
        if (node->HitNum == 0) {
            continue;
        }

        covFuncs.insert(node->GetId());
    }

    return covFuncs;
}

bool Scheduler::getFAddrIdMap() 
{
    fs::path absBenchPath(benchPath);
    const std::string binaryName = absBenchPath.filename().string();
    std::string cmd =
        "FAddr2Gid --bench " + UTIL::shell_quote(absBenchPath.string()) +
        " --binary " + UTIL::shell_quote(binaryName);
    std::cout<< "[Scheduler] getFAddrIdMap cmd: " << cmd << "\n";

    int status = std::system(cmd.c_str());
    return (status != -1) && WIFEXITED(status) && (WEXITSTATUS(status) == 0);
}

SyncStats Scheduler::setActiveDriver(unsigned driverId, bool init)
{
    string activeDrvPath = sessionPath + "/active_driver.drv";

    if (init == true) {
        driverManger->setActiveDriver(activeDrvPath, driverId);
        activeDriver = driverId;
        return {};
    }

    setCovBlock();

    /* syn graph */
    SyncStats stats = synchronizeGraphs();

    /* switch driver */
    activeDriver = driverId;
    driverManger->setActiveDriver(activeDrvPath, activeDriver);

    setCovNonBlock();

    std::cout << "[Scheduler::setActiveDriver] SUCCESS @[" << driverId << "]\n";
    return stats;
}


vector<unsigned> Scheduler::getAllDrvIds()
{
    return driverManger->getAllDrvIds();
}
