#include <atomic>
#include <csignal>
#include "mfuzz.h"

MFuzz *mfuzz = NULL;

extern "C" void on_sigint(int) 
{
    if (mfuzz == NULL) {
        return;
    }
    delete mfuzz;
    mfuzz = NULL;
}

int main (int argc, char** argv)
{
    char *bench_path = NULL;
    int time_budget  = 3600 * 24; // Default 24 hours
    std::signal(SIGINT, on_sigint);

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

    mfuzz = new MFuzz(bench_path, "honggfuzz");
    if (mfuzz == NULL) {
        return 0;
    }
    mfuzz->start_fuzzer(time_budget);
    delete mfuzz;

    return 0;
}