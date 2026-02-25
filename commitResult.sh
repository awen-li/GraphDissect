find benchmarks -type d -name tables -print0 | xargs -0 git add
git commit -m "Add per-benchmark result tables"
git push origin main
