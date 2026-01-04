#include "mfuzz.h"

int main (int argc, char** argv)
{
    char *bench_path = NULL;
    int time_budget  = 3600 * 24; // Default 24 hours

    int opt;
    while ((opt = getopt(argc, argv, "b:t:")) != -1) 
    {
        switch (opt) 
        {
            case 'b':
            {
                bench_path = optarg;
                break;
            }
            case 't':
            {
                time_budget = atoi(optarg);
                break;
            }
            default:
            {
                printf("Unknown option\n");
                exit (0);
            }
        }
    }

    MFuzz mfuzz(bench_path, "honggfuzz");
    mfuzz.start_fuzzer(bench_path, time_budget);
    return 0;
}