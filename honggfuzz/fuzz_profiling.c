/*
 * Simple periodic profiler:
 * - uses alarm() every 5 minutes
 * - collects fuzz metrics from local_run
 * - collects memory usage (RSS) via /proc/self/status
 * - writes CSV: timestamp, iterations, edges_covered, uniq_crashes, total_crashes, rss_kb
 */

#include <errno.h>
#include <inttypes.h>
#include <signal.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/types.h>
#include <time.h>
#include <unistd.h>
#include "honggfuzz.h" 

typedef struct {
    uint64_t iterations;
    uint64_t edges_covered;
    uint64_t uniq_crashes;
    uint64_t corpus_size;
} hf_fuzz_metrics_t;

/* Whether we already wrote CSV header */
static int g_prof_header_written = 0;

/* Period in seconds; default 5 minutes */
#define HF_M_PROFILING_PERIOD  300
static unsigned g_last_sec = 0;

/* ---------- Helpers ---------- */
static unsigned now_sec(void) {
    struct timespec ts;
    clock_gettime(CLOCK_REALTIME, &ts);
    return (unsigned)ts.tv_sec;
}

/* Read RSS (kB) from /proc/self/status; fallback to 0 on error */
static uint64_t read_rss_kb(void) {
    FILE *f = fopen("/proc/self/status", "r");
    if (!f) return 0;

    char line[256];
    uint64_t rss_kb = 0;
    while (fgets(line, sizeof(line), f)) {
        if (strncmp(line, "VmRSS:", 6) == 0) {
            // "VmRSS:    12345 kB"
            char *p = line + 6;
            while (*p == ' ' || *p == '\t') p++;
            rss_kb = strtoull(p, NULL, 10);
            break;
        }
    }
    fclose(f);
    return rss_kb;
}

/* Collect fuzzing metrics from local_run.
 * TODO: adjust field names to match your run_t structure.
 */
static void hf_profiler_collect_metrics(honggfuzz_t *hfuzz, 
                                        hf_fuzz_metrics_t *out) {
    out->iterations    = ATOMIC_GET(hfuzz->cnts.mutationsCnt);
    out->edges_covered = ATOMIC_GET(hfuzz->feedback.hwCnts.softCntEdge);
    out->uniq_crashes  = ATOMIC_GET(hfuzz->cnts.uniqueCrashesCnt);
    out->corpus_size   = ATOMIC_GET(hfuzz->io.dynfileqCnt);
}

/* Actually perform one sampling + logging (called from signal handler in your design) */
void hf_profiler_sampling(honggfuzz_t *hfuzz) {
    if (!hfuzz) return;

    const char *out_path = "honggfuzz_profiling.txt";
    if (g_last_sec == 0) {
        remove (out_path);
    }

    unsigned ts = now_sec();
    if (ts - g_last_sec < HF_M_PROFILING_PERIOD) {
        return;
    }
    g_last_sec = ts;

    FILE *prof_fp = fopen(out_path, "a");
    if (!prof_fp) {
        perror("hf_profiler: fopen");
        return;
    }

    hf_fuzz_metrics_t m = {0};
    hf_profiler_collect_metrics(hfuzz, &m);
    uint64_t rss_kb = read_rss_kb();

    if (!g_prof_header_written) {
        fprintf(prof_fp,
                "timestamp, iterations, edges_covered, uniq_crashes, corpus_size, rss_kb\n");
        g_prof_header_written = 1;
    }

    fprintf(prof_fp,
            "%u, %" PRIu64 ", %" PRIu64 ", %" PRIu64 ", %" PRIu64 ", %" PRIu64 "\n",
            ts,
            m.iterations,
            m.edges_covered,
            m.uniq_crashes,
            m.corpus_size,
            rss_kb);
    fclose(prof_fp);

    return;
}


