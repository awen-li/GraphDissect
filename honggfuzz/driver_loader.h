#ifndef _DRIVER_LOADER_H_
#define _DRIVER_LOADER_H_
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include <errno.h>
#include <sys/stat.h>
#include <assert.h>
#include <json-c/json.h>
#include <unistd.h>


#define MAX_ARGC   32
#define MAX_PATH   256
#define MAX_DRIVER 8192
#define MAX_SEED_HASHES 4096

typedef struct driver_prof
{
    int id;
    char name[MAX_PATH];
    char driver[MAX_PATH];
    char seed_dir[MAX_PATH];
    float priority;

    int argc;
    const char *argv[MAX_ARGC];

    char output[MAX_ARGC];

    int current_phase;
    int in_place_edit; // 0: disable, 1: enable
}driver_prof_t;

typedef struct fuzz_driver 
{
    driver_prof_t drv_prof;

    unsigned start_time;
    unsigned total_time;

    unsigned start_crashes;
    unsigned total_crashes;
    unsigned delta_crashes;

    unsigned start_edges;
    unsigned delta_edges;
    unsigned total_edges;

    unsigned total_exes;
    bool     initialized;

    struct fuzz_driver* next;
    struct fuzz_driver* pre;
} fuzz_driver_t;

typedef struct fuzz_driver_table 
{
    const char *dir_of_bench;
    const char *session_path;

    char active_drv_path[MAX_PATH];
    char driver_runtime_path[MAX_PATH];
    
    fuzz_driver_t *active_driver;
    fuzz_driver_t *driver_list_head;
    unsigned driver_count;

    fuzz_driver_t *driver_map[MAX_DRIVER];

    uint64_t seed_hashes[MAX_SEED_HASHES];
    size_t seed_hash_count;

    int current_phase; // 0: pilot phase, 1: dynsch phase, 2: fallback phase
    int inPlaceEdit;   // 0: disable, 1: enable
    int independentQueue; // 0: shared corpus, 1: active-driver corpus only
} fuzz_driver_table_t;

bool drive_loadDriver(fuzz_driver_table_t *drv_table);
fuzz_driver_t* drive_getInitDriver(fuzz_driver_table_t *drv_table);

void driver_saveGlobalStats(void *hfuzz);

char** drive_getArgv (fuzz_driver_t *driver, int *argc_num);

#endif
