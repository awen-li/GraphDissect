#ifndef _SCHEDULER_H_
#define _SCHEDULER_H_
#include <thread>
#include <atomic>
#include <chrono>
#include <cassert>
#include <filesystem>
#include "cgmarker.h"
#include "fcov.h"
#include "faddr_id.h"

namespace fs = std::filesystem;

struct NodeFeature 
{
    unsigned funcId;

    // Static
    float inDegree;
    float outDegree;
    float depthNorm;

    // Dynamic (absolute)
    float hitLog;          // log(1 + total calls to this node)
    float inEdgeCovRatio;  // (#covered in-edges / inDegree)
    float outEdgeCovRatio; // (#covered out-edges / outDegree)

    // NEW: edge hit intensity
    float inHitLog;        // log(1 + sum hits over incoming edges)
    float outHitLog;       // log(1 + sum hits over outgoing edges)

    // Dynamic (evolution / frontier)
    float frontierFlag;    // 0 or 1
    float exclusiveFlag;   // 0 or 1
    float newEdgeFrac;     // newIncidentEdges / max(1, inDegree+outDegree)
};

class Scheduler
{
public:
    Scheduler() = default;
    Scheduler(const string& benchPath) {
        this->benchPath  = benchPath;

        cgmk = new CgMarker (benchPath);
        assert(cgmk != NULL);

        string faddrMapPath = benchPath + "/faddr_id.map";
        if (!fs::exists(faddrMapPath)) {
            assert(getFAddrIdMap() == true && "Failed to get faddr_id.map"); 
        }
        fAddrToID = new FaddrID (benchPath + "/faddr_id.map");
        assert(fAddrToID != NULL);
        initEdgeKey();

        // fcov cache
        backupFcov.resize(getGraphNodeNum()+32, 0);

        activeDriver = 0;
        firstRun     = true;
    }

    ~Scheduler () {
        delete cgmk;
        delete fAddrToID;
    }

    void synchronizeGraphs();
    void switchDriver(unsigned drvId);

    void getGraphFeatures(unsigned driverId, 
                          vector<NodeFeature>& nFeatures, 
                          vector<pair<unsigned, unsigned>>& edgeList,
                          unsigned& totalBlocks); 
    
    set<unsigned> getCoveredFuncs();

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

    FaddrID *fAddrToID;
    map<uint64_t, CGEdge*> keyToEdge;

private:
    bool getFAddrIdMap();
    unsigned getNodeBlockNum(set<CGNode*> subgraph);
    vector<NodeFeature> getNodeFeatures(unsigned driverId, set<CGNode*> subgraph);
    vector<pair<unsigned, unsigned>> getSubgraphEdges(set<CGNode*> subgraph);

    inline uint64_t hash64(uint64_t x) 
    {
        x ^= x >> 33;
        x *= 0xff51afd7ed558ccdULL;
        x ^= x >> 33;
        x *= 0xc4ceb9fe1a85ec53ULL;
        x ^= x >> 33;
        return x;
    }
    
    inline uint64_t getEdgeKey(unsigned srcId, unsigned dstId) 
    {
        uint64_t edgeId = srcId;
        return (edgeId<<32 | dstId);
    }

    inline void initEdgeKey() 
    {
        CGGraph* wCg = cgmk->getWholeCg();
        for (auto itr = wCg->begin(); itr != wCg->end(); itr++) {
            CGNode* srcNode = itr->second;
            for (auto itr = srcNode->OutEdgeBegin(); itr != srcNode->OutEdgeEnd(); itr++) {
                CGEdge* edge    = *itr;
                CGNode* dstNode = edge->GetDstNode();
                
                unsigned srcId = srcNode->GetId();
                unsigned dstId = dstNode->GetId();

                unsigned srcFAddr = fAddrToID->idToAddr(srcId);
                unsigned dstFAddr = fAddrToID->idToAddr(dstId);

                // edge key
                uint64_t edgeKey = getEdgeKey(srcFAddr, dstFAddr);
                //printf("[initEdgeKey][%x, %x] --> %lx [hash = %lx]\n", srcFAddr, dstFAddr, edgeKey, hash64(edgeKey)&FCOV_EDGE_TAB_MASK);
                keyToEdge[edgeKey] = edge;
                edge->Key = edgeKey;

                // node key
                dstNode->Key = dstFAddr;
                srcNode->Key = srcFAddr;
            }
        }
    }

    inline unsigned getNodeHitNum(unsigned nodeId) 
    {
        if (nodeId == 0) {
            return 0;
        }

        CGGraph* wCg = cgmk->getWholeCg();
        CGNode* node = wCg->GetGNode(nodeId);
        if (node == nullptr) {
            return 0;
        }

        uint32_t nodeKey = node->Key;
        return fcov_getNodeHitNum(nodeKey);
    }

    inline unsigned getEdgeHitNum(unsigned nodeId) 
    {
        if (nodeId == 0) {
            return 0;
        }

        CGGraph* wCg = cgmk->getWholeCg();
        CGNode* node = wCg->GetGNode(nodeId);
        if (node == nullptr) {
            return 0;
        }

        uint32_t nodeKey = node->Key;
        return fcov_getNodeHitNum(nodeKey);
    }

};


#endif