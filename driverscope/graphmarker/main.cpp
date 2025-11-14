#include <getopt.h>
#include "subcg_expander.h"

int main(int argc, char** argv)
{
    char *benchPath   = nullptr;

    int opt;
    while ((opt = getopt(argc, argv, "b:")) != -1) 
    {
        switch (opt) 
        {
            case 'b':
                benchPath = strdup(optarg);
                break;
            default:
                std::cerr << "Usage: " << argv[0] << " -b <benchmark-dir>\n";
                exit(EXIT_FAILURE);
        }
    }

    if (!benchPath) {
        std::cerr << "Missing required arguments.\n";
        exit(EXIT_FAILURE);
    }

    SubCGExpander cgExpander (benchPath);
    cgExpander.expandDrvSugraph();

    cgExpander.ReportGlobalStats();
    cgExpander.ReportPerDriverStats();

    free(benchPath);
    return 0;
}
