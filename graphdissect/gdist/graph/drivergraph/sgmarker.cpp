#include <cmath>
#include "sgmarker.h"


void SubCgMarker::dump() {
    cgmk->dump();
}

void SubCgMarker::reportGlobalStats() {
    std::ofstream ofs("global_driver_stats.txt");
    cgmk->reportGlobalStats(ofs);
    ofs.close();
}
    
void SubCgMarker::reportPerDriverStats() {
    std::ofstream ofs("per_driver_stats.txt");
    cgmk->reportPerDriverStats(ofs, "");
    ofs.close();
}

void SubCgMarker::getDriverGraph(unsigned driverId, set<CGNode*>& drvNodes) {
    cgmk->getDriverGraph(driverId, drvNodes);
}