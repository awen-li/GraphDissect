#include "dynsch.h"

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