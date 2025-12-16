#include <cmath>
#include "scheduler.h"

void Scheduler::getGraphFeatures(unsigned driverId, 
                          vector<NodeFeature>& nFeatures, 
                          vector<pair<unsigned, unsigned>>& edgeList,
                          unsigned& totalBlocks)
{
    set<CGNode*> subgraph;
    cgmk->getDriverGraph(driverId, subgraph);

    nFeatures   = getNodeFeatures(driverId, subgraph);
    edgeList    = getSubgraphEdges(subgraph);
    totalBlocks = getNodeBlockNum(subgraph);

    return;
}

vector<NodeFeature> Scheduler::getNodeFeatures(unsigned driverId, set<CGNode*> subgraph) 
{
    vector<NodeFeature> features;

    if (subgraph.empty()) {
        return features;
    }

    // 1) Compute maxDepth for normalization
    unsigned maxDepth = 0;
    for (CGNode* node : subgraph) {
        if (node->Depth > maxDepth) {
            maxDepth = node->Depth;
        }
    }

    // 2) Build features per node
    for (CGNode* node : subgraph) {
        NodeFeature nf{};
        unsigned nodeId = node->GetId();

        nf.funcId   = nodeId;
        unsigned inDeg  = node->GetIncomingEdgeNum();
        unsigned outDeg = node->GetOutgoingEdgeNum();

        // Static
        nf.inDegree  = static_cast<float>(inDeg);
        nf.outDegree = static_cast<float>(outDeg);
        nf.depthNorm = (maxDepth ? static_cast<float>(node->Depth) /
                                   static_cast<float>(maxDepth)
                                 : 0.0f);

        // Dynamic accumulators
        unsigned inCovered      = 0;
        unsigned outCovered     = 0;
        uint64_t inHitSum       = 0;
        uint64_t outHitSum      = 0;
        unsigned newIncident    = 0;

        // Incoming edges: u -> node
        for (auto it = node->InEdgeBegin(); it != node->InEdgeEnd(); ++it) {
            CGEdge* edge = *it;
            unsigned prevHit = edge->HitNum;
            unsigned curHit  = fcov_getEdgeHitNum(edge->Key);
            edge->HitNum     = curHit;  // cache current for next round

            if (curHit > 0) {
                ++inCovered;
                inHitSum += curHit;
                if (!firstRun && prevHit == 0) {
                    ++newIncident;
                }
            }
        }

        // Outgoing edges: node -> w
        for (auto it = node->OutEdgeBegin(); it != node->OutEdgeEnd(); ++it) {
            CGEdge* edge = *it;
            unsigned prevHit = edge->HitNum;
            unsigned curHit  = fcov_getEdgeHitNum(edge->Key);
            edge->HitNum     = curHit;

            if (curHit > 0) {
                ++outCovered;
                outHitSum += curHit;
                if (!firstRun && prevHit == 0) {
                    ++newIncident;
                }
            }
        }

        // Dynamic (absolute)
        uint64_t totalHitSum = inHitSum + outHitSum;
        nf.hitLog = std::log1p(static_cast<float>(totalHitSum));

        nf.inEdgeCovRatio  = (inDeg  ? static_cast<float>(inCovered)  /
                                      static_cast<float>(inDeg)
                                    : 0.0f);
        nf.outEdgeCovRatio = (outDeg ? static_cast<float>(outCovered) /
                                      static_cast<float>(outDeg)
                                    : 0.0f);

        // Dynamic (evolution / frontier)
        bool hasUncoveredSucc = (outDeg > outCovered);
        bool isCoveredNode    = (totalHitSum > 0);

        nf.frontierFlag = (isCoveredNode && hasUncoveredSucc) ? 1.0f : 0.0f;

        nf.exclusiveFlag =
            (node->GetDriverIdMask().count() == 1 && node->HasDriverId(driverId))
            ? 1.0f
            : 0.0f;

        unsigned totalDeg = inDeg + outDeg;
        nf.newEdgeFrac =
            (!firstRun && totalDeg
                 ? static_cast<float>(newIncident) /
                   static_cast<float>(totalDeg)
                 : 0.0f);

        features.push_back(nf);
    }

    // After the first call, we can start using "new edge" signals
    firstRun = false;

    return features;
}


unsigned Scheduler::getNodeBlockNum(set<CGNode*> subgraph) 
{
        unsigned totalBlocks = 0;
    for (const auto& node : subgraph) {
        totalBlocks += node->BlockNum;
    }
    return totalBlocks;
}


vector<pair<unsigned, unsigned>> Scheduler::getSubgraphEdges(set<CGNode*> subgraph) 
{
    vector<pair<unsigned, unsigned>> edges;
    if (subgraph.empty()) {
        return edges;
    }

    // Traverse subgraph edges
    for (auto* srcNode : subgraph) {
        unsigned srcId = srcNode->GetId();

        for (auto itr = srcNode->OutEdgeBegin(); itr != srcNode->OutEdgeEnd(); itr++) {
            CGNode* dstNode = (*itr)->GetDstNode();
            unsigned dstId  = dstNode->GetId();

            edges.emplace_back(srcId, dstId);
        }
    }

    return edges;
}


void Scheduler::switchDriver(unsigned drvId) {
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
    firstRun     = false;

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
