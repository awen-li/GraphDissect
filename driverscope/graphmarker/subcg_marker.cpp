#include <cmath>  // for std::sqrt
#include "driver.h"
#include "subcg_marker.h"

void SubCgMarker::computeScore() {
    for (auto itr = profiler->begin(); itr != profiler->end(); ++itr) {
        unsigned driverId = itr->first;
        CGGraph* drvCg = itr->second;

        float score = cgmk->computeDriverScore(drvCg, driverId);

        auto itrDrv = id2Driver.find(driverId);
        assert(itrDrv != id2Driver.end());

        Driver *drv = itrDrv->second;
        drv->setPriority(score);

        string drvPath = benchPath + "/drivers/" + drv->getName() + "/" + drv->getName() + ".json";
        drv->dump(drvPath);
        cout<<"@computeScore: update score for " + drv->getName() + " -> "<<score<<"\n";
    }
}


void SubCgMarker::dump() {
    dumpFidMap();
    
    cgmk->dump();
}


void SubCgMarker::markSugraph(string drvName, map<string, string>& symMap) {
    string drvPath = benchPath + "/drivers/" + drvName + "/" + drvName + ".json";

    // 1. load driver
    Driver *drv = new Driver();
    if (drv->load(drvPath) == false) {
        cerr << "markSugraph: load driver " << drv->getName() <<" failed\n";
        return;
    }
    id2Driver[drv->getId()] = drv;

    // 2. get initial subgraph for the driver
    CGGraph* drvCg = profiler->getDrvSubgraph(drv, symMap);
    if (drvCg == NULL) {
        cerr << "markSugraph: getDrvSubgraph for " << drv->getName() <<" failed\n";
        return; 
    }

    // 3. mark the subgraph to the whole CG
    cgmk->markGraph(drvCg, drv->getId());

    return;
}

void SubCgMarker::reportGlobalStats() {
    std::ofstream ofs("global_driver_stats.txt");
    cgmk->reportGlobalStats(ofs);
    ofs.close();
}
    
void SubCgMarker::reportPerDriverStats() {
    std::ofstream ofs("per_driver_stats.txt");
    cgmk->reportPerDriverStats(ofs);
    ofs.close();
}

void SubCgMarker::dumpFidMap(const string FID) {
    string fIdPath = benchPath + "/" + FID;
    std::ofstream ofs(fIdPath);
    if (!ofs.is_open()) {
        cerr << "Failed to open output file: " << fIdPath << "\n";
        return;
    }

    CGGraph* wholeCg = cgmk->getWholeCg();
    for (auto itr = wholeCg->begin(); itr != wholeCg->end(); itr++) {
        CGNode *node = itr->second;
        ofs << node->GetFName() << ":" << node->GetId() << "\n";
    }

    ofs.close();
}