/*
 *
 * honggfuzz - load multiple drivers
 * -----------------------------------------
 *
 * Author: *****************
 *
 * Copyright ***********************.
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License. You may obtain
 * a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
 * implied. See the License for the specific language governing
 * permissions and limitations under the License.
 *
 */
#include <unistd.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <dirent.h>
#include "driver_loader.h"
#include "honggfuzz.h"
#include "input.h"
#include "libhfcommon/log.h"
#include "display.h"

#define PRINT(...) printf(__VA_ARGS__)

void drive_printDrivers(fuzz_driver_table_t *drv_table) {
    fuzz_driver_t *driver = drv_table->driver_list_head;
    while (driver != NULL) {
        driver_prof_t *d = &driver->drv_prof;
        PLOG_W("Driver[%d]: name=%s, bin=%s, argv[0]=%s, seeds=%s, priority=%.2f\n",
               d->id, d->name, d->driver, d->argv[0], d->seed_dir, d->priority);
        driver = driver->next;
    }
}


/*
{
    "id": 1,
    "name": "html",
    "driver": "xmllint",
    "args": ["--html", "-s"],
    "seed_dir": "seeds",
    "priority": 1.0
}
*/
static inline bool drive_parseArgs(struct json_object *root, driver_prof_t *prof) {
    struct json_object *args = NULL;
    if (!json_object_object_get_ex(root, "args", &args) || 
        !json_object_is_type(args, json_type_array)) {
        LOG_F("'args' field missing or not an array\n");
        return false;
    }

    int argc = json_object_array_length(args);
    if (argc > MAX_ARGC - 1) argc = MAX_ARGC - 1;

    int actual_argc = 0;
    for (int i = 0; i < argc; i++) {
        json_object *arg = json_object_array_get_idx(args, i);
        if (!json_object_is_type(arg, json_type_string)) {
            LOG_F("Skipping non-string arg at index %d\n", i);
            continue;
        }

        prof->argv[actual_argc++] = strdup(json_object_get_string(arg));
    }

    prof->argc = actual_argc;
    prof->argv[actual_argc] = NULL;

    return true;
}


static inline bool drive_parseDriverProfile(const char *json_str, driver_prof_t *out) {
    struct json_object *root = json_tokener_parse(json_str);
    if (!root) return false;

    struct json_object *id, *name, *driver, *args, *seed_dir, *priority, *output, *phase, *in_place_edit;

    if (!json_object_object_get_ex(root, "id", &id) ||
        !json_object_object_get_ex(root, "name", &name) ||
        !json_object_object_get_ex(root, "driver", &driver) ||
        !json_object_object_get_ex(root, "args", &args) ||
        !json_object_object_get_ex(root, "seed_dir", &seed_dir) ||
        !json_object_object_get_ex(root, "priority", &priority) ||
        !json_object_object_get_ex(root, "output", &output) ||
        !json_object_object_get_ex(root, "phase", &phase)) {
        json_object_put(root);
        return false;
    }

    if (json_object_object_get_ex(root, "in_place_editing", &in_place_edit)) {
        int inPlaceEditVal = json_object_get_int(in_place_edit);
        if (inPlaceEditVal == 0) {
            out->in_place_edit = 0; // disable
        } else {
            out->in_place_edit = 1; // enable
        }
    }

    out->id = json_object_get_int(id);
    out->priority = (float)json_object_get_double(priority);
    strncpy(out->name, json_object_get_string(name), sizeof(out->name) - 1);

    /* absolute path of driver */
    snprintf(out->driver, sizeof(out->driver), 
             "drivers/%s/%s", 
             out->name, json_object_get_string(driver));      

    /* absolute path of seeds directory */
    snprintf(out->seed_dir, sizeof(out->seed_dir), 
             "drivers/%s/%s", 
             out->name, json_object_get_string(seed_dir));

    /* output */
    strncpy(out->output, json_object_get_string(output), sizeof(out->output) - 1);

    /* current phase */
    out->current_phase = json_object_get_int(phase);

    if (!drive_parseArgs (root, out)) {
        LOG_F("parse_args failed\n");
        return false;
    }

    //PLOG_W ("Parsed: id=%d, name=%s, bin=%s, argv[0]=%s, output=%s, seeds=%s, priority=%.2f",
    //        out->id, out->name, out->driver, out->argv[0], out->output, out->seed_dir, out->priority);

    json_object_put(root);
    return true;
}

static inline bool drive_addDriver(fuzz_driver_table_t *drv_table, fuzz_driver_t *fdrv){
    fuzz_driver_t *exist_drv = drv_table->driver_map[fdrv->drv_prof.id];
    if (exist_drv == NULL) {
        fuzz_driver_t *new_drv = (fuzz_driver_t*)malloc(sizeof(fuzz_driver_t));
        if (new_drv == NULL){
            LOG_F("malloc failed");
            return false;
        }
        memset(new_drv, 0, sizeof(fuzz_driver_t));
        memcpy (new_drv, fdrv, sizeof(fuzz_driver_t));

        drv_table->driver_map[new_drv->drv_prof.id] = new_drv;
        if (drv_table->driver_list_head == NULL) {
            drv_table->driver_list_head  = new_drv;
            new_drv->next = new_drv->pre = NULL;
        }
        else {
            new_drv->pre = NULL;
            new_drv->next = drv_table->driver_list_head;

            drv_table->driver_list_head->pre = new_drv;
            drv_table->driver_list_head = new_drv;
        }
        drv_table->driver_count += 1;
    }
    else {
        /* only priority is allowed to revise */
        exist_drv->drv_prof.priority = fdrv->drv_prof.priority;
        if (exist_drv != drv_table->driver_list_head){
            /* by default, move this driver to the head */
            fuzz_driver_t *exist_drv_pre = exist_drv->pre;

            exist_drv_pre->next = exist_drv->next;
            if (exist_drv->next != NULL) {
                exist_drv->next->pre = exist_drv_pre;
            }

            exist_drv->pre  = NULL;
            exist_drv->next = drv_table->driver_list_head;
            drv_table->driver_list_head->pre = exist_drv;
            drv_table->driver_list_head = exist_drv;
        }
    }

    return true;
}

bool drive_loadDriver(fuzz_driver_table_t *drv_table) {

    int fd = open(drv_table->active_drv_path, O_RDONLY | O_NONBLOCK);
    if (fd == -1) {
        return false;
    }

    //PLOG_W("@drive_loadDriver: starting loading....");
    char dv_buffer[1024] = {0};
    unsigned try_no    = 3;
    do {       
        ssize_t read_size = read(fd, dv_buffer, sizeof(dv_buffer) - 1);
        if (read_size < 0) {
            LOG_F("read from %s failed: %s", drv_table->active_drv_path, strerror(errno));
            close(fd);
            return false; 
        }
        else if (read_size == 0) {
            try_no--;
            if (try_no == 0) {
                LOG_F("[try_no:%u]read from %s failed, readsize = %ld", try_no, drv_table->active_drv_path, read_size);
                close(fd);
                return false; 
            }

            usleep(100*1000); 
            continue;
        }
        else {
            close(fd);
            break;
        }
    }while(true);   

    fuzz_driver_t drv;
    memset(&drv, 0, sizeof(drv));
    if (drive_parseDriverProfile(dv_buffer, &drv.drv_prof) == false) {
        LOG_F("drive_parseDriverProfile failed: \n%s\n", dv_buffer);
        return false;
    }

    if (drv.drv_prof.id == 0 || drv.drv_prof.id > MAX_DRIVER){
        LOG_F("unexpeced driver ID: %d [1, %d]", drv.drv_prof.id, MAX_DRIVER);
        return false;
    }

    if (drive_addDriver(drv_table, &drv) == false) {
        LOG_F("drive_addDriver ID: [%d, %s] failed", drv.drv_prof.id, drv.drv_prof.name);
        return false;
    } 
    
    drv_table->current_phase = drv.drv_prof.current_phase;
    drv_table->inPlaceEdit   = drv.drv_prof.in_place_edit;
    //PLOG_W("@drive_loadDriver: load success....");
    return true;
}

fuzz_driver_t* drive_getInitDriver(fuzz_driver_table_t *drv_table) {
    return drv_table->driver_list_head;
}

static inline bool drive_initOutput(run_t* run, fuzz_driver_t* driver) {
    driver_prof_t* prof = &driver->drv_prof;

    // Build per-driver output directory: "fuzz/out/<driver_name>"
    char out_path[MAX_PATH];
    snprintf(out_path, sizeof(out_path), "fuzz/out/%s", prof->name);

    // Ensure output directory exists
    struct stat st = {0};
    if (stat(out_path, &st) == -1) {
        if (mkdir(out_path, 0700) < 0) {
            LOG_F("Failed to create directory %s: %s\n", out_path, strerror(errno));
        }
    }

    // Update Honggfuzz runtime state
    if (run->global->io.outputDir) {
        free((void*)run->global->io.outputDir);
    }
    run->global->io.outputDir = strdup(out_path);  // Now all coverage output goes here

    // Optional: log driver details
    //PLOG_W("[init_driver] Switched to driver: %s", prof->name);
    //PLOG_W("  -> Input dir : %s", prof->seed_dir);
    //PLOG_W("  -> Output dir: %s", out_path);
    //PLOG_W("  -> Target bin: %s", prof->driver);

    return true;
}


char** drive_getArgv (fuzz_driver_t *driver, int *argc_num) {
    // Tokenize args
    char **argv = (char **)calloc(_HF_ARGS_MAX, sizeof(char *));
    assert (argv != NULL);
    
    // [0] = binary
    argv[0] = driver->drv_prof.driver;
    //PLOG_W ("drive_getArgv:[0]%s", argv[0]);

    // Tokenize driver->args into argv[]
    int argc = 0;
    while (argc < (_HF_ARGS_MAX - 4) && argc < driver->drv_prof.argc) {
        argv[argc+1] = (char*)driver->drv_prof.argv[argc];
        //PLOG_W ("drive_getArgv:[%d]%s -- %s",argc+1, argv[argc+1], driver->drv_prof.argv[argc]);
        argc++;
    }

    // input
    argv[++argc] = "___FILE___";

    // output
    if (driver->drv_prof.output[0] !=0) {
        argv[++argc] = (char*)driver->drv_prof.output;
    }

    //PLOG_W ("drive_getArgv:[%d]%s",argc, argv[argc]);
    argv[++argc]   = NULL;
    *argc_num    = argc;

    return argv;
}


static inline uint8_t* driver_readData(const char* seedPath, size_t *seedSize) {
    int fd = open(seedPath, O_RDONLY);
    if (fd == -1) {
        LOG_E("Failed to open seed file: %s", seedPath);
        return NULL;
    }

    struct stat st;
    if (fstat(fd, &st) == -1 || st.st_size <= 0 || st.st_size > (long)_HF_INPUT_MAX_SIZE) {
        LOG_E("Invalid file size for seed: %s", seedPath);
        close(fd);
        return NULL;
    }

    uint8_t* buf = (uint8_t*)util_Calloc(st.st_size);
    ssize_t rlen = read(fd, buf, st.st_size);
    close(fd);

    if (rlen != st.st_size) {
        LOG_E("Failed to fully read seed: %s", seedPath);
        free(buf);
        return NULL;
    }

    *seedSize = st.st_size;
    return buf;
}


static inline uint64_t fnv1a_hash(const uint8_t* data, size_t size) {
    uint64_t hash = 14695981039346656037ULL;
    for (size_t i = 0; i < size; ++i) {
        hash ^= data[i];
        hash *= 1099511628211ULL; 
    }
    return hash;
}


static inline bool driver_isSeedExist(run_t* run, const uint8_t* data, size_t size) {
    honggfuzz_t *hfuzz = run->global;
    fuzz_driver_table_t *drv_table = &hfuzz->drv_table;

    uint64_t hash = fnv1a_hash(data, size);
    for (size_t i = 0; i < drv_table->seed_hash_count; ++i) {
        if (drv_table->seed_hashes[i] == hash) {
            return false;
        }
    }

    // Add to hash set
    if (drv_table->seed_hash_count < MAX_SEED_HASHES) {
        drv_table->seed_hashes[drv_table->seed_hash_count++] = hash;
    } else {
        LOG_W("Seed hash table full, cannot check duplicates");
    }

    return true;
}


void driver_addDriverSeed(run_t* run, driver_prof_t* drvPrifile, const char* seedPath, const char* seedName) {
    size_t seedSize = 0;
    uint8_t* buf = driver_readData(seedPath, &seedSize);
    if (buf == NULL) {
        return;
    }

    if (driver_isSeedExist(run, buf, seedSize) == false) {
        free(buf);
        return;
    }

    dynfile_t* dynfile = (dynfile_t*)util_Calloc(sizeof(dynfile_t));
    dynfile->phase     = _HF_STATE_DYNAMIC_MAIN;
    dynfile->data      = buf;
    dynfile->size      = seedSize;
    dynfile->imported  = true;
    dynfile->driver_id = drvPrifile->id;
    dynfile->idx       = ATOMIC_PRE_INC(run->global->io.dynfileqCnt);
    snprintf(dynfile->path, sizeof(dynfile->path), "%s", seedName);

    MX_SCOPED_RWLOCK_WRITE(&run->global->mutex.dynfileq);
    TAILQ_INSERT_HEAD(&run->global->io.dynfileq, dynfile, pointers);
    run->global->io.dynfileqCurrent = dynfile;

    //LOG_I("Injected driver seed (HEAD): %s [%zu bytes]", seedPath, dynfile->size);
    return;
}


void driver_addDriverSeedDir(run_t* run, driver_prof_t* drvPrifile) {

    const char* seedDir = drvPrifile->seed_dir;
    DIR* dir = opendir(seedDir);
    if (!dir) {
        LOG_E("Cannot open seed directory: %s", seedDir);
        return;
    }

    struct dirent* entry;
    while ((entry = readdir(dir)) != NULL) {
        char fullPath[PATH_MAX];
        snprintf(fullPath, sizeof(fullPath), "%s/%s", seedDir, entry->d_name);

        struct stat sb;
        if (stat(fullPath, &sb) != 0 || !S_ISREG(sb.st_mode)) {
            continue;
        }

        driver_addDriverSeed(run, drvPrifile, fullPath, entry->d_name);
    }

    closedir(dir);
    return;
}


#ifndef TAILQ_FOREACH_SAFE
#define TAILQ_FOREACH_SAFE(var, head, field, tvar)                  \
    for ((var) = TAILQ_FIRST((head));                               \
         (var) && ((tvar) = TAILQ_NEXT((var), field), 1);           \
         (var) = (tvar))
#endif

void driver_prioritizeSeeds(run_t* run, uint32_t driver_id) {
    MX_SCOPED_RWLOCK_WRITE(&run->global->mutex.dynfileq);

    dynfile_t* curr;
    dynfile_t* tmp;

    TAILQ_FOREACH_SAFE(curr, &run->global->io.dynfileq, pointers, tmp) {
        if (curr->driver_id == driver_id) {
            TAILQ_REMOVE(&run->global->io.dynfileq, curr, pointers);
            TAILQ_INSERT_HEAD(&run->global->io.dynfileq, curr, pointers);
        }
    }

    run->global->io.dynfileqCurrent = TAILQ_FIRST(&run->global->io.dynfileq);
}


static inline void driver_initStat(honggfuzz_t *hfuzz, fuzz_driver_t *driver) {
    driver->start_edges   = hfuzz->feedback.hwCnts.softCntEdge;
    driver->start_crashes = hfuzz->cnts.uniqueCrashesCnt;
    driver->start_time    = time(NULL);

    return;
}


static inline void driver_updateDrvStat(honggfuzz_t *hfuzz, fuzz_driver_table_t *drv_table) {
    fuzz_driver_t *driver = drv_table->active_driver;
    if (driver == NULL) {
        return;
    }

    driver->delta_edges    = hfuzz->feedback.hwCnts.softCntEdge - driver->start_edges;
    driver->total_edges   += driver->delta_edges;

    driver->delta_crashes  = hfuzz->cnts.uniqueCrashesCnt - driver->start_crashes;
    driver->total_crashes += driver->delta_crashes;

    driver->total_time    += time(NULL) - driver->start_time;
    driver->total_exes    += 1;

    char stat_path[MAX_PATH];
    snprintf(stat_path, sizeof(stat_path), "%s/%u", drv_table->driver_runtime_path, driver->drv_prof.id);

    FILE *fp = fopen(stat_path, "w");
    if (!fp) {
        PLOG_E("Failed to open driver stat file: %s", stat_path);
        return;
    }

    fprintf(fp, "edges:%u(+%u), crashes:%u(+%u), time:%u, exes:%u\n", 
            driver->total_edges,
            driver->delta_edges,
            driver->total_crashes,
            driver->delta_crashes,
            driver->total_time,
            driver->total_exes);
    fclose(fp);
    return;
}


void driver_saveGlobalStats(void *hf) {

    honggfuzz_t *hfuzz = (honggfuzz_t*)hf;
    fuzz_driver_table_t *drv_table = &hfuzz->drv_table;

    char stat_path[MAX_PATH];
    snprintf(stat_path, sizeof(stat_path), "%s/overview.stat", drv_table->driver_runtime_path);

    FILE *fp = fopen(stat_path, "w");
    if (!fp) {
        PLOG_W("Failed to write global stats to %s", stat_path);
        return;
    }

    fprintf(fp, "edges:%lu, crashes:%lu, pc:%lu, cmp:%lu, time:%lu, total_edges:%lu\n",
        hfuzz->feedback.hwCnts.softCntEdge,
        hfuzz->cnts.uniqueCrashesCnt,
        hfuzz->feedback.hwCnts.softCntPc,
        hfuzz->feedback.hwCnts.softCntCmp,
        time(NULL) - hfuzz->timing.timeStart,
        ATOMIC_GET(hfuzz->feedback.covFeedbackMap->guardNb));

    fclose(fp);
}


void driver_switchDriver(run_t* run) {

    honggfuzz_t *hfuzz = run->global;
    fuzz_driver_table_t *drv_table = &hfuzz->drv_table;

    // update coverage info for the previous active driver
    driver_updateDrvStat(hfuzz, drv_table);

    // check whether still the same
    if (drv_table->active_driver == drv_table->driver_list_head) {
        PLOG_W("STILL focus on [%u][%s]", 
               drv_table->active_driver->drv_prof.id, 
               drv_table->active_driver->drv_prof.name);
    }
    else {
        // switch to the first driver (load to head!)
        fuzz_driver_t *driver = drv_table->driver_list_head;

        if (!drive_initOutput(run, driver)) {
            LOG_F("init_driver failed");
        }

        // Set cmdline and argc
        free ((void*)hfuzz->exe.cmdline);
        hfuzz->exe.cmdline = (const char* const*)drive_getArgv (driver, &hfuzz->exe.argc);

        if (driver->initialized == false) {
            // load the driver seeds
            driver_addDriverSeedDir(run, &driver->drv_prof);
            driver->initialized = true;
        }
        else {
            driver_prioritizeSeeds(run, driver->drv_prof.id);
        }

        // change the display
        display_createTargetStr(run->global);

        /* set */
        drv_table->active_driver =  driver;

        PLOG_W("Selected driver: %s (exe: %s, seed: %s)", driver->drv_prof.name,
           hfuzz->exe.cmdline[0], driver->drv_prof.seed_dir);
    }

    // init driver-level coverage
    driver_initStat(hfuzz, drv_table->active_driver);

    // remove the cache
    remove (drv_table->active_drv_path);
    return;
}



