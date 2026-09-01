#ifndef _SCHEDULER_H_
#define _SCHEDULER_H_
#include <thread>
#include <atomic>
#include <chrono>
#include <cassert>
#include <filesystem>
#include "driver.h"
#include "util.h"
#include "cgmarker.h"
#include "fcov.h"
#include "faddr_id.h"

namespace fs = std::filesystem;

struct SyncStats {
    unsigned newNodes = 0;
    unsigned newEdges = 0;
    unsigned totalNodes = 0;
};

class Scheduler
{
public:
    Scheduler() = default;
    Scheduler(const string& benchPath, const string& sessionPath) 
    {
        this->benchPath   = benchPath;
        this->sessionPath = sessionPath;

        cgmk = new CgMarker (benchPath, "marked_callgraph.dot");
        assert(cgmk != NULL);

        driverManger = new DriverMng(benchPath);
        assert(driverManger != NULL);

        fcovPath = sessionPath + "/fcov.map";
        fcov_setPath(fcovPath.c_str());

        activeDriver = 0;
    }

    ~Scheduler () 
    {
        dump();
        delete cgmk;
        delete driverManger;
    }

    SyncStats setActiveDriver(unsigned driverId, bool init=false);
    SyncStats synchronizeGraphs();
    set<unsigned> getCoveredFuncs();
    vector<unsigned> getAllDrvIds();

    inline void dump() 
    {
        cgmk->dump("final_marked_callgraph");
    }

private:
    unsigned activeDriver;

    string benchPath;
    string sessionPath;
    string fcovPath;
    CgMarker* cgmk;

    DriverMng*  driverManger;

private:
    bool getFAddrIdMap();

    inline unsigned getGraphSize() {
        CGGraph* wCg = cgmk->getWholeCg();
        return wCg->GetNodeNum();
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

    inline vector<unsigned> synchronizeNodes(unsigned drvId, 
                                             unsigned& newHitNodes, 
                                             unsigned& totalHitNodes) 
    {
        vector<unsigned> updatedNodes;

        CGGraph* wCg = cgmk->getWholeCg();
        for (auto itr = wCg->begin(); itr != wCg->end(); itr++) {
            CGNode* node = itr->second;

            unsigned nodeId = node->GetId();
            unsigned hitNum = getNodeHitNum(nodeId);

            if (hitNum != 0) {
                totalHitNodes++;
            }
    
            if (hitNum == 0 || node->HitNum == hitNum) {
                continue;
            }
    
            if (node->HitNum == 0) {
                newHitNodes++;
            }

            node->HitNum = hitNum;
            node->SetDriverIdMask(drvId);
            updatedNodes.push_back(nodeId);
        }
    
        return updatedNodes;
    }

    inline unsigned getEdgeHitNum(unsigned srcId, unsigned dstId) 
    {
        CGGraph* wCg = cgmk->getWholeCg();
        CGNode* srcNode = wCg->GetGNode(srcId);
        CGNode* dstNode = wCg->GetGNode(dstId);
        if (srcNode == nullptr || dstNode == nullptr) {
            return 0;
        }

        for (auto eItr = srcNode->OutEdgeBegin(); eItr != srcNode->OutEdgeEnd(); eItr++) {
            CGEdge* edge = *eItr;
            if (edge->GetDstNode() == dstNode) {
                return getEdgeHitNum(edge);
            }
        }

        return 0;
    }

    inline unsigned getEdgeHitNum(CGEdge* edge) 
    {
        unsigned hitNum = 0;
        for (uint64_t edgeKey : edge->Keys) {
            hitNum += fcov_getEdgeHitNum(edgeKey);
        }
        return hitNum;
    }

    inline unsigned synchronizeEdges(unsigned drvId) 
    {
        unsigned newHitEdges = 0;
        CGGraph* wCg = cgmk->getWholeCg();
        for (auto itr = wCg->begin(); itr != wCg->end(); itr++) {
            CGNode* srcNode = itr->second;
            for (auto eItr = srcNode->OutEdgeBegin(); eItr != srcNode->OutEdgeEnd(); eItr++) {
                CGEdge* edge    = *eItr;

                unsigned hitNum = getEdgeHitNum(edge);
                if (hitNum == 0 || edge->HitNum == hitNum) {
                    continue;
                }

                if (edge->HitNum == 0) {
                    newHitEdges++;
                }

                edge->HitNum = hitNum;
                edge->SetDriverIdMask(drvId);
            }
        }

        return newHitEdges;
    }

    inline unsigned synchronizeEdges(vector<unsigned>& newHitNodes, unsigned drvId) 
    {
        unsigned newHitEdges = 0;

        CGGraph* wCg = cgmk->getWholeCg();
        for (auto it = newHitNodes.begin(); it != newHitNodes.end(); ++it) {
            unsigned nodeId = *it;       
            CGNode* node = wCg->GetGNode(nodeId);
            if (node == nullptr) {
                continue;
            }

            // outgoing edges
            for (auto eItr = node->OutEdgeBegin(); eItr != node->OutEdgeEnd(); eItr++) {
                CGEdge* edge = *eItr;

                unsigned hitNum = getEdgeHitNum(edge);
                //std::cout << "[OutEdge][UpdateEdgesHitNum] Edge (" 
                //          << edge->GetSrcNode()->GetFName() << " -> " 
                //          << edge->GetDstNode()->GetFName() 
                //          << ") Key = " << edge->Key
                //          << ", Hit num: " << hitNum << "\n";

                if (hitNum == 0 || edge->HitNum == hitNum) {
                    continue;
                }

                if (edge->HitNum == 0) {
                    newHitEdges++;
                }

                edge->HitNum = hitNum;
                edge->SetDriverIdMask(drvId);
            }

            // incoming edges
            for (auto eItr = node->InEdgeBegin(); eItr != node->InEdgeEnd(); eItr++) {
                CGEdge* edge = *eItr;

                unsigned hitNum = getEdgeHitNum(edge);
                //std::cout << "[InEdge][UpdateEdgesHitNum] Edge (" 
                //          << edge->GetSrcNode()->GetFName() << " -> " 
                //          << edge->GetDstNode()->GetFName() 
                //          << ") Key = " << edge->Key
                //          << ", Hit num: " << hitNum << "\n";

                if (hitNum == 0 || edge->HitNum == hitNum) {
                    continue;
                }

                if (edge->HitNum == 0) {
                    newHitEdges++;
                }

                edge->HitNum = hitNum;
                edge->SetDriverIdMask(drvId);
            }
        }
   
        return newHitEdges;
    }

};


#endif
