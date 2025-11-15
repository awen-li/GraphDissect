#ifndef _SCHEDULER_H_
#define _SCHEDULER_H_
#include <thread>
#include <atomic>
#include <chrono>
#include <cassert>
#include "cgmarker.h"

struct NodeFeature
{
    unsigned funcId;

    unsigned coverCount;
    unsigned callDepth;
    
    unsigned inDegree;
    unsigned outDegree;

    unsigned isFrontier;
    unsigned isExclusive;
};

struct SubgraphResult {
    unsigned driverId;
    set<CGNode*> subgraph;
};

class Scheduler
{
public:
    Scheduler() = default;
    Scheduler(const string& benchPath) {
        this->benchPath  = benchPath;

        cgmk = new CgMarker (benchPath, "marked_callgraph.dot");
        assert(cgmk != NULL);

        // fcov cache
        backupFcov.resize(getGraphNodeNum()+32, 0);

        activeDriver = 0;
        firstRun     = true;
    }

    ~Scheduler () {
        delete cgmk;
    }

    void synchronizeGraphs();

    void switchDriver(unsigned drvId);
    
    vector<NodeFeature> getNodeFeatures(unsigned driverId);
    vector<pair<unsigned, unsigned>> getSubgraphEdges(unsigned driverId);

    inline unsigned getGraphNodeNum() {
        CGGraph* wCg = cgmk->getWholeCg();
        return wCg->GetNodeNum();
    }

    inline void dump() {
        cgmk->dump("final_marked_callgraph");
    }

    inline unsigned getWCgSize () {
        return getGraphNodeNum();
    }

private:
    unsigned firstRun;
    unsigned activeDriver;
    string benchPath;
    CgMarker* cgmk;

    vector<unsigned> backupFcov;

    SubgraphResult subg;
};


#endif