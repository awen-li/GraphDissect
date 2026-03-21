from .rq1_present import RQ1Present
from .rq2_present import RQ2Present
from .rq3_present import RQ3Present
from .rq4_present import RQ4Present
from .rq5_present import RQ5Present
from .region_study import RegionStudyGenerator

__all__ = ["runPresent"]

def runCaseStudy(suite_root, bench, exe, top_regions=5):
    gen = RegionStudyGenerator(
        benchdir=suite_root,
        bench=bench,
        exe=exe,
        top_k_gap_regions=top_regions,
    )
    gen.run()


def runPresent (rqs, benchs, suite_root):
    if "rq1" in rqs or len(rqs) == 0:
        p = RQ1Present(benchs, suite_root)
        print(f"Running presenter: {p.name}")
        p.run()
        p.post_run()

    if "rq2" in rqs or len(rqs) == 0:
        p = RQ2Present(benchs, suite_root)
        print(f"Running presenter: {p.name}")
        p.run()
        p.post_run()

    if "rq3" in rqs or len(rqs) == 0:
        p = RQ3Present(benchs, suite_root)
        print(f"Running presenter: {p.name}")
        p.run()
        p.post_run()

    if "rq4" in rqs or len(rqs) == 0:
        p = RQ4Present(benchs, suite_root)
        print(f"Running presenter: {p.name}")
        p.run()
        p.post_run()

    if "rq5" in rqs or len(rqs) == 0:
        p = RQ5Present(benchs, suite_root)
        print(f"Running presenter: {p.name}")
        p.run()
        p.post_run()

    if "case" in rqs or len(rqs) == 0:
        runCaseStudy(suite_root, "ffmpeg", "ffmpeg")
        runCaseStudy(suite_root, "libxml2", "xmllint")
        runCaseStudy(suite_root, "lua", "lua")