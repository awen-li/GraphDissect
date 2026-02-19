#ifndef _GRAPHVIZ_H_
#define _GRAPHVIZ_H_
#include <fstream>

using namespace std;

enum
{
    E_ATTR_COLOR_BLACK=0,
    E_ATTR_COLOR_BLUE=1,
    E_ATTR_COLOR_RED=2,

    E_ATTR_COLOR_INVALID=0XFF,
};

template<class NodeTy,class EdgeTy, class GraphType> class GraphViz 
{
protected:
    FILE  *m_File;
    GraphType *m_Graph;
    string m_GraphName;
    string m_GraphLabel;

protected:
    inline VOID WriteHeader (string GraphName) 
    {
        fprintf(m_File, "digraph \"%s\"{\n", GraphName.c_str());
        fprintf(m_File, "\tlabel=\"%s\";\n", GetGraphLabel().c_str()); 
        fprintf(m_File, "\n\n");

        return;
    }

    inline string GetGraphLabel() 
    {
        if (m_GraphLabel != "")
        {
            return m_GraphName + " " + m_GraphLabel; 
        }

        return m_GraphName;
    }

    virtual inline string GetNodeLabel(NodeTy *Node) 
    {
        string str = "";
        str = "N-" + to_string (Node->GetId ());
        return str;
    }

    virtual inline string GetNodeName(NodeTy *Node) 
    {
        string str = "";
        str = "N" + to_string (Node->GetId ());
        return str;
    }
    
    virtual inline string GetNodeAttributes(NodeTy *Node) 
    {
        string str = "color=black";   
        return str;
    }

    virtual inline string GetEdgeLabel(EdgeTy *Edge) 
    {
        return "";
    }

    virtual inline string GetEdgeAttributes(EdgeTy *Edge) 
    {
        string str = "color=black";
        return str;
    }
 
    inline VOID WriteNodes(NodeTy *Node) 
    {
        /* NodeID [color=grey,label="{NodeID: 0}"]; */
        string str;
        str = GetNodeName (Node) + " [" + GetNodeAttributes (Node) + 
              ",label=\"" + GetNodeLabel (Node) + "\"];";

        fprintf(m_File, "\t%s\n", str.c_str());
        return;        
    }
 

    inline VOID WriteEdge(EdgeTy *Edge) 
    {
        /* NodeId -> NodeId[style=solid,color=black, ,label="..."]; */
        string str;

        str = "\t" + GetNodeName (Edge->GetSrcNode()) + " -> " + GetNodeName (Edge->GetDstNode()) +
              "[" + GetEdgeAttributes (Edge) + ",label=\"" + GetEdgeLabel (Edge) + "\"];";
               
        fprintf(m_File, "%s\n", str.c_str());
        return; 
     
    }

    virtual inline BOOL IsEdgeType (EdgeTy *Edge)
    {
        return TRUE;
    }

    virtual inline BOOL IsVizNode (NodeTy *Node)
    {
        fprintf(stderr, "Node: %u \r\n", Node->GetId());
        return TRUE;
    }

    virtual inline BOOL IsVizEdge (EdgeTy *Edge)
    {
        return TRUE;
    }

public:
    GraphViz(string GraphName, GraphType* Graph, string DotFile="") 
    {
        m_GraphName = GraphName;
        if (DotFile == "") DotFile = GraphName;
        m_GraphLabel = "";
        
        DotFile = DotFile + ".dot";
        m_File    = fopen (DotFile.c_str(), "w");
        assert (m_File != NULL);

        m_Graph = Graph;
    }

    ~GraphViz()
    {
        fclose (m_File);
    }

    virtual inline void SetNodeLabel(string GLabel) 
    {
        m_GraphLabel = GLabel;
        return;
    }

    VOID WiteGraph (DWORD EntryId=0) 
    {
        if (EntryId != 0)
        {
            m_GraphName += to_string (EntryId);
        }
        WriteHeader(m_GraphName);

        // write nodes
        fprintf(m_File, "\t// Define the nodes\n");
        for (auto It = m_Graph->begin (), End = m_Graph->end (); It != End; It++)
        {
            NodeTy *Node = It->second;
            if (!IsVizNode (Node))
            {
                continue;
            }
            WriteNodes (Node);
        }

        fprintf(m_File, "\n\n");

        // write edges
        fprintf(m_File, "\t// Define the edges\n");
        for (auto It = m_Graph->begin (), End = m_Graph->end (); It != End; It++)
        {
            NodeTy *Node = It->second;
            if (!IsVizNode (Node))
            {
                continue;
            }

            for (auto ItEdge = Node->OutEdgeBegin (), ItEnd = Node->OutEdgeEnd (); ItEdge != ItEnd; ItEdge++)
            {
                EdgeTy *Edge = *ItEdge;
                if (!IsVizNode (Edge->GetDstNode()))
                {
                    continue;
                }

                if (!IsEdgeType(Edge))
                {
                    continue;
                }
                
                WriteEdge (Edge);
            }
        }

        fprintf(m_File, "}\n");
    }   
};



#endif 
