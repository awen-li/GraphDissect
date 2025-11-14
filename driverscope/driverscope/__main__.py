import os
import argparse
from .faddr import FaddrMap
from driverscope.stracehound import StraceHound
from driverscope.graphmark import GraphMark

def main():
    parser = argparse.ArgumentParser(description="Option-based Driver Generator")
    parser.add_argument("benchmark", help="Path to the benchmark directory (e.g., ./libxml2)")
    parser.add_argument("--binary", help="Binary name within the benchmark (e.g., xmllint)")
    parser.add_argument("--faddr", action="store_true", help="Generate mapping from function addr to id")
    parser.add_argument("--mark", action="store_true", help="Mark subgraphs for drivers")
    args = parser.parse_args()

    if args.mark == True:

        gm = GraphMark(args.benchmark, args.binary)
        gm.markGraph()

    elif args.binary:

        hound = StraceHound(args.benchmark, args.binary)
        hound.run()

        gm = GraphMark(args.benchmark, args.binary)
        gm.markGraph()

        # generate mapping: graph-nod --- function 
        fadd2Id = FaddrMap(args.benchmark)
        fadd2Id.genFddrIdMap()

    elif args.faddr == True:
        fadd2Id = FaddrMap(args.benchmark)
        fadd2Id.genFddrIdMap()
        
    else:
        pass

if __name__ == "__main__":
    main()
