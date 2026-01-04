#include <cmath>
#include "scheduler.h"
#include "driver.h"

void Scheduler::switchDriver(unsigned drvId) 
{
    // 1: Compute coverage diff between current state and last backup
    //  : Label the call graph with the newly covered set
    // 2: Backup the current fcov state and switch active driver

    if (activeDriver == 0 ) {
        activeDriver = drvId;
        return;
    }

    // 1
    unsigned updatedNodes = 0;
    unsigned newNodes = 0;
    unsigned totalHitNodes = 0;
    for (unsigned i = 0; i < backupFcov.size(); ++i) {
        unsigned hitNum = getNodeHitNum(i);

        if (hitNum != 0) {
            totalHitNodes++;
        }

        if (hitNum == 0 || backupFcov[i] == hitNum) {
            continue;
        }

        if (backupFcov[i] == 0) {
            newNodes++;
        }

        // save it
        backupFcov[i] = hitNum;

        cgmk->markNode(i, activeDriver);
        updatedNodes++;
    }

    // switch to new driver
    activeDriver = drvId;
    std::cout << "[Scheduler] Switched to driver " << drvId
              << "[" <<totalHitNodes<<" / "<<backupFcov.size()<<"]"
              << " (updated " << updatedNodes << " nodes with newly discovered "<<newNodes<<")\n";
    return;
}


void Scheduler::synchronizeGraphs()
{
    if (activeDriver == 0 ) {
        return;
    }

    CGGraph* wCg = cgmk->getWholeCg();
    unsigned cgNodeNum = wCg->GetNodeNum() + 32;
    for (unsigned i = 1; i < cgNodeNum; ++i) {

        unsigned nodeId = i;
        CGNode* node = wCg->GetGNode(nodeId);
        if (node == NULL) {
            continue;
        }

        // update hit num for node
        node->HitNum = getNodeHitNum(nodeId);
        //if (node->HitNum != 0)
        //    printf("[synchronizeGraphs]node:[%u]%s, covered:%u\r\n", 
        //    nodeId, node->GetFName().c_str(), node->HitNum);

        // update hit num for outgoing edges
        for (auto it = node->OutEdgeBegin(); it != node->OutEdgeEnd(); ++it) {
            CGEdge* edge = *it;
            edge->HitNum = fcov_getEdgeHitNum(edge->Key);
        }
    }
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

void Scheduler::setActiveDriver(unsigned driverId, bool init)
{
    string activeDrvPath = sessionPath + "/active_driver.drv";

    if (init == true) {
        driverManger->setActiveDriver(activeDrvPath, driverId);
        activeDriver = driverId;
        return;
    }

    setCovBlock();

    driverManger->setActiveDriver(activeDrvPath, driverId);

    /* syn graph */
    synchronizeGraphs();

    /* switch driver */
    switchDriver(driverId);
    activeDriver = driverId;

    setCovNonBlock();

    std::cout << "[Scheduler::setActiveDriver] SUCCESS @[" << driverId << "]\n";
    return;
}


vector<unsigned> Scheduler::getAllDrvIds()
{
    return driverManger->getAllDrvIds();
}