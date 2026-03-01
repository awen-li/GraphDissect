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

void SubCgMarker::getGraphCov(unsigned& covNodes, unsigned& covEdges) {
    CGGraph* cg = cgmk->getWholeCg();
    
    covNodes = 0;
    covEdges = 0;
    for (auto itr = cg->begin(); itr != cg->end(); ++itr) {
        CGNode* node = itr->second;

        const auto& mask = node->GetDriverIdMask();
        if (mask.count() > 0) {
            covNodes++;
        }

       for (auto edgeIt = node->OutEdgeBegin(); edgeIt != node->OutEdgeEnd(); ++edgeIt) {
            CGEdge* edge = *edgeIt;
            const auto& mask = node->GetDriverIdMask();
            if (mask.count() > 0) {
                covEdges++;
            }
        }
    }

    return;
}


void SubCgMarker::getReachableGraph(set<CGNode*>& cgNodes) {
    queue<CGNode*> worklist;

    CGGraph* cg = cgmk->getWholeCg();
    CGNode* entry = cg->GetNode("main");
    assert (entry != NULL);

    worklist.push(entry);
    while (!worklist.empty()) 
    {
        auto node = worklist.front();
        worklist.pop();
        cgNodes.insert(node);

        for (auto itr = node->OutEdgeBegin(); itr != node->OutEdgeEnd(); ++itr) 
        {
            CGNode* callee = (*itr)->GetDstNode();
            if (cgNodes.find(callee) != cgNodes.end())
            {
                continue;
            }

            worklist.push(callee);
            cgNodes.insert(callee);
        }
    }
    
    return;
}