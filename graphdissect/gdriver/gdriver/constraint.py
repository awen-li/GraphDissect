from .option import Option


class Constraints:
    """
    Wrapper for constraint rules from the YAML.

    Currently supports:
      - type: "at_most_one_from_group", group: "<group_name>"
    You can extend this later (requires_role, etc.).
    """
    def __init__(self, rules: list[dict]):
        self.rules = rules or []

        # Pre-index some common constraint types
        self.at_most_one_groups = {
            rule["group"]
            for rule in self.rules
            if rule.get("type") == "at_most_one_from_group"
        }

    def is_valid(self, options: list[Option]) -> bool:
        # group -> count
        group_counts = {}
        for opt in options:
            group = getattr(opt, "group", None)
            if not group:
                continue
            group_counts[group] = group_counts.get(group, 0) + 1

        # at_most_one_from_group
        for g in self.at_most_one_groups:
            if group_counts.get(g, 0) > 1:
                return False

        # placeholder: future constraint types could go here

        return True

