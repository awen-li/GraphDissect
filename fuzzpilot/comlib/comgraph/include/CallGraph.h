
#ifndef _CALLGRAPH_H_
#define _CALLGRAPH_H_
#include "GenericGraph.h"
#include "GraphViz.h"
#include <algorithm>
#include <iostream>
#include <vector>
#include <queue>
#include <boost/dynamic_bitset.hpp>
#include "DotParser.h"


using namespace std;
class CGNode;
class CGViz;

class CGEdge : public GenericEdge<CGNode> 
{
public:
    CGEdge(CGNode* s, CGNode* d):GenericEdge<CGNode>(s, d)                       
    {
    }

    virtual ~CGEdge() 
    {
    }
};


class CGNode : public GenericNode<CGEdge> 
{
public:
    unsigned HitNum;
    unsigned lastHit;
    unsigned Depth;
    
public:
    CGNode(DWORD Id, string FName): GenericNode<CGEdge>(Id), FuncName(FName)
    {
        Depth = 0;
    }

    inline string GetFName ()
    {
        return FuncName;
    }

    inline void SetDriverIdMask(unsigned DriverId)
    {
        if (DriverId == 0) return;

        if (DriverIdMask.size() < DriverId) 
        {
            DriverIdMask.resize(DriverId);
        }
        DriverIdMask.set(DriverId - 1);
    }

    inline void SetDriverIdMask(boost::dynamic_bitset<>& drvIdMask)
    {
        if (DriverIdMask.size() != drvIdMask.size()) 
        {
            DriverIdMask.resize(drvIdMask.size());
        }
        DriverIdMask = drvIdMask;
    }

    inline bool HasDriverId(unsigned DriverId) const
    {
        if (DriverId == 0 || DriverId > DriverIdMask.size())
        {
            return false;
        }

        return DriverIdMask.test(DriverId - 1);
    }

    inline boost::dynamic_bitset<> GetDriverIdMask() const
    {
        return DriverIdMask;
    }

protected:
    string FuncName;
    boost::dynamic_bitset<> DriverIdMask;
};


class CGGraph : public GenericGraph<CGNode, CGEdge> 
{
protected:
    map<string, CGNode*> m_FName2Node;
    CGNode *m_Entry;

public:
    CGGraph() { m_Entry = NULL; }
    
    virtual ~CGGraph() { }

    inline void UpdateEntry(string entryName="main") 
    {
        if (m_Entry != NULL) 
        {
            return;
        }

        CGNode* Cn = GetNode (entryName);
        if (Cn == NULL)
        {
            cout<<"@@UpdateEntry: "<<entryName<<" does not exist!"<<endl;
            return;
        }

        m_Entry = Cn;
        return;
    }

    inline string GetEntry ()
    {
        return m_Entry->GetFName ();
    }

    inline void ResetNodeMap ()
    {
        m_FName2Node.clear ();
    }

    inline void UpdateNodeMap (string FName, CGNode* Cn)
    {
        m_FName2Node [FName] = Cn;
        return;
    }

    inline CGNode* AddNode (string FName)
    {
        CGNode* Cn = GetNode (FName);
        if (Cn == NULL)
        {
            unsigned Id = GetNodeNum() + 1;
            Cn = new CGNode (Id, FName);
            assert (Cn != NULL);

            m_FName2Node[FName] = Cn;
            GenericGraph::AddNode (Id, Cn);
        }
        
        return Cn;
    }

    inline CGNode* GetNode (string FName) const
    {
        auto Itr = m_FName2Node.find (FName);
        if (Itr == m_FName2Node.end ())
        {
            return NULL;
        }
        else
        {
            return Itr->second;
        }
    }

    inline bool AddEdge (CGEdge *Edge)
    {
        return GenericGraph::AddEdge (Edge);
    }

    inline bool AddEdge (CGNode* S, CGNode* N)
    {
        CGEdge *Edge = new CGEdge (S, N);
        assert (Edge != NULL);

        return GenericGraph::AddEdge (Edge);
    }

    inline vector<CGNode*> GetZeroInDegreeNodes() const 
    {
        vector<CGNode*> zeroInNodes;
        for (const auto& nodePair : m_IDToNodeMap) {
            CGNode* node = nodePair.second;
            if (node->GetIncomingEdgeNum() == 0) 
            {
                zeroInNodes.push_back(node);
            }
        }
        return zeroInNodes;
    }

    vector<CGNode*> GetNodesWithinDepth(unsigned maxDepth=3)
    {
        vector<CGNode*> result;
        UpdateEntry();
        if (m_Entry == NULL)
        {
            return result;
        }

        unordered_set<CGNode*> visited;
        queue<pair<CGNode*, unsigned>> worklist;

        worklist.push({m_Entry, 0});
        visited.insert(m_Entry);

        while (!worklist.empty()) 
        {
            auto [curr, depth] = worklist.front();
            worklist.pop();

            if (depth > maxDepth) continue;
            result.push_back(curr);

            for (auto itr = curr->OutEdgeBegin(); itr != curr->OutEdgeEnd(); ++itr) 
            {
                CGNode* callee = (*itr)->GetDstNode();
                if (visited.insert(callee).second) 
                {
                    worklist.push({callee, depth + 1});
                }
            }
        }

        return result;
    }

    unsigned ComputeNodeDepths(bool dumpUnreached=false) 
    {
        set<CGNode*>visited;
        queue<CGNode*> worklist;

        UpdateEntry();
        if (m_Entry == NULL)
        {
            return 0;
        }
        std::cout<<"[ComputeNodeDepths] Entry: " << m_Entry->GetFName() << "\n";
        
        unsigned graphDepth = 0;
        m_Entry->Depth = 0;
        worklist.push(m_Entry);

        while (!worklist.empty()) 
        {
            auto node = worklist.front();
            worklist.pop();
            visited.insert(node);

            if (node->Depth > graphDepth)
            {
                graphDepth = node->Depth;
            }

            for (auto itr = node->OutEdgeBegin(); itr != node->OutEdgeEnd(); ++itr) 
            {
                CGNode* callee = (*itr)->GetDstNode();
                if (visited.find(callee) != visited.end())
                {
                    continue;
                }

                callee->Depth = node->Depth+1;
                worklist.push(callee);
                visited.insert(callee);
            }
        }

        std::cout<<"[ComputeNodeDepths] Total reachable nodes: " << visited.size() << "\n";
        if (dumpUnreached)
        {
            DumpUnreached(visited);
        } 

        return graphDepth;
    }

    void setHitTime (unsigned funcId, unsigned timeStamp)
    {
        CGNode* node = GetGNode (funcId);
        if (node == NULL) 
        {
            return;
        }
        node->lastHit = timeStamp;
        return;
    }

    void DumpUnreached(const std::set<CGNode*>& visited,
                       const std::string& out_path = "unreached_by_main.txt",
                       const std::string& zero_indegree_path = "unreached_zero_indegree.txt") 
    {
        std::ofstream out(out_path);
        if (!out) 
        {
            std::cerr << "[DumpUnreached] Failed to open " << out_path << "\n";
            return;
        }

        std::ofstream zerodg(zero_indegree_path);
        if (!out) 
        {
            std::cerr << "[DumpUnreached] Failed to open " << zero_indegree_path << "\n";
            return;
        }

        size_t cnt = 0;
        size_t zerodgcnt = 0;
        for (auto it = begin(); it != end(); ++it) 
        {
            CGNode* n = it->second;
            if (visited.find(n) == visited.end()) 
            {
                out << n->GetFName() << '\n';
                if (n->GetIncomingEdgeNum() == 0 && n->GetFName() != "main")
                {
                    zerodg << n->GetFName() << '\n';
                    zerodgcnt++;
                }
                ++cnt;
            }
        }
        out.close();
        zerodg.close();
        
        std::cout << "[DumpUnreached] Wrote " << cnt
                  << " unreached nodes to " << out_path << "\n"
                  << "[DumpUnreached] Wrote " << zerodgcnt
                  << " unreached zero-indegree nodes to " << zero_indegree_path << "\n";
    }

};


class CgDotParser: public DotParser <CGNode, CGEdge, CGGraph>
{
public:
    CgDotParser (string DotFile): DotParser (DotFile) {}
    ~CgDotParser () {}

};


class CGViz: public GraphViz <CGNode, CGEdge, CGGraph>
{

public:
    CGViz(string GraphName, CGGraph *Graph, string DotFile, unsigned MaxDepth=-1U, bool MaskOnly=false)
        :GraphViz<CGNode, CGEdge, CGGraph>(GraphName, Graph, DotFile)
    {
        Attr2Color[E_ATTR_COLOR_BLACK] = "color=black";
        Attr2Color[E_ATTR_COLOR_BLUE]  = "color=blue";
        Attr2Color[E_ATTR_COLOR_RED]   = "color=red";

        this->MaskOnly = MaskOnly;
        this->MaxDepth = MaxDepth;
    }

    ~CGViz ()
    {
    }

    inline BOOL IsVizNode (CGNode *Node)
    {
        if (MaxDepth != -1U) 
        {
            if (Node->Depth == 0 && Node->GetFName() != "main")
            {
                return FALSE;
            } 

            if (Node->Depth > MaxDepth) 
            {
                return FALSE;
            }
        }

        if (MaskOnly) 
        {
            return (Node->GetDriverIdMask().count() != 0);
        }
        else 
        {
            return TRUE;
        }    
    }

    inline string GetNodeLabel(CGNode* Node) 
    {
        string NdLabel;
        const auto& mask = Node->GetDriverIdMask();

        if (mask.none()) 
        {
            NdLabel = Node->GetFName() + " (mask=0)";
        } else 
        {
            // Convert bitmask to string
            stringstream ss;
            ss << " (mask=" << mask << ")";
            NdLabel = Node->GetFName() + ss.str();
        }

        return NdLabel;
    }

    inline string GetNodeName(CGNode *Node) 
    {
        return Node->GetFName ();
    }

    inline string GetNodeAttributes(CGNode *Node) 
    {
        string str = "color=black";
        return str;
    }

    inline string GetEdgeAttributes(CGNode *Edge) 
    {
        string str = "color=black";
        return str;
    }

private:
    map<unsigned, string> Attr2Color;
    bool MaskOnly;
    unsigned MaxDepth;
};


#endif 
