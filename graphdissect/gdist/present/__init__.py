from .rq1_present import RQ1Present
from .rq2_present import RQ2Present
from .rq3_present import RQ3Present
from .rq4_present import RQ4Present
from .rq6_present import RQ6Present

__all__ = ["runPresent"]


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

    if "rq6" in rqs or len(rqs) == 0:
        p = RQ6Present(benchs, suite_root)
        print(f"Running presenter: {p.name}")
        p.run()
        p.post_run()
    