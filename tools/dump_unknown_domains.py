from pathlib import Path
import yaml

PROFILES_DIR = Path("profiles")  # adjust if needed

def main() -> None:
    items = []
    for path in sorted(PROFILES_DIR.glob("*.yaml")):
        data = yaml.safe_load(path.read_text())
        project = data.get("project")
        main_repo = data.get("main_repo")
        language = data.get("language")
        domain = data.get("domain")

        if not project:
            continue

        # Treat "", null, or "unknown" as unknown
        if not domain or str(domain).strip().lower() in ("unknown", "null", ""):
            items.append(
                {
                    "project": project,
                    "main_repo": main_repo,
                    "language": language,
                    "domain": domain,
                }
            )

    # Print as YAML list so you can paste it here
    print(yaml.safe_dump(items, sort_keys=False))

if __name__ == "__main__":
    main()
