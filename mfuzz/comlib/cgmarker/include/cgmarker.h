#ifndef __CGMARKER_H__
#define __CGMARKER_H__
#include <unordered_set>
#include <stack>
#include <iomanip>
#include <mutex>
#include "comgraph/CallGraph.h"

class CgMarker {
private:
    string benchPath;
    CGGraph wholeCg;
    std::mutex cg_mutex;

public:
    CgMarker() = default;
    CgMarker(string benchPath, string cgName="callgraph_final.dot") {
        this->benchPath = benchPath;

        string wCgDot = benchPath + "/" + cgName;
        initWholeCg(wCgDot);
    }

    ~CgMarker() {}

    CGGraph* getWholeCg();

    void getDriverGraph(unsigned driverId, set<CGNode*>& drvNodes);

    void reportGlobalStats(std::ostream& os = std::cout);
    void reportPerDriverStats(std::ostream& os = std::cout, std::string drvIDs="");
    void reportDriverGraph(std::ostream& os,
                           const std::string& outDir=".");

    void dump(string markGraph="marked_callgraph");

    void markGraph(CGGraph* drvCg, unsigned drvId);
    void markNode(unsigned nodeId, unsigned drvId);
    float computeDriverScore(CGGraph* drvCg, unsigned drvId);
private:
    unsigned countPrivateNodes(unsigned driverId);

    inline void initWholeCg (const string& cgDotPath) {
        cout<<"CG path --> "<<cgDotPath<<endl;
        CgDotParser dotParser (cgDotPath);
        dotParser.Dot2Graph (wholeCg);
        assert(wholeCg.GetNodeNum () != 0);
        wholeCg.ComputeNodeDepths();
    }
};

#endif

