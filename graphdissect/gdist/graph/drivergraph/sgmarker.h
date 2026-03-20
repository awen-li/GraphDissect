#ifndef __SGMARKER_H__
#define __SGMARKER_H__
#include <unordered_set>
#include <stack>
#include <iomanip>
#include "cgmarker.h"

class SubCgMarker {
private:
    string benchPath;
    CgMarker *cgmk;
    vector<unsigned> drvIDs;

public:
    SubCgMarker() = default;
    SubCgMarker(string benchPath, string graphPath = "final_marked_callgraph.dot") {
        this->benchPath = benchPath;

        cgmk = new CgMarker (benchPath, graphPath);
        assert(cgmk != NULL);
    }

    ~SubCgMarker() {
        delete cgmk;
    }

    void dump();
    void reportGlobalStats();
    void reportPerDriverStats();

    void getDriverGraph(unsigned driverId, set<CGNode*>& drvNodes);
    void getGraphCov(unsigned& covNodes, unsigned& covEdges);

    void getReachableGraph(set<CGNode*>& drvNodes);

    string getNodeName(unsigned nodeId);

};

#endif

