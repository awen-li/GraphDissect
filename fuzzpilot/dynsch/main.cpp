#include "dynsch.h"

extern bool dynsch_genFidMap(const char *benchPath);


int main (int argc, char** argv)
{
    char *benchPath = NULL;

    int opt;
    while ((opt = getopt(argc, argv, "b:")) != -1) 
    {
        switch (opt) 
        {
            case 'b':
            {
                dynsch_genFidMap (optarg);
                break;
            }
            default:
            {
                printf("Unknown option\n");
                exit (0);
            }
        }
    }

    return 0;
}