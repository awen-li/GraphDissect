from pathlib import Path
from typing import List, Optional, Any, Dict
import yaml


class Option:
    """
    Option model aligned with the YAML command spec.

    YAML example:

      - id: "11"
        cli: ["-c", "--demangle"]
        kind: "choice"
        metavar: "STYLE"
        choices:
          - "none"
          - "auto"
          - "gnu-v3"
        defaults: ["auto", "gnu-v3"]
        role: "modifier"
        include_in_search: true
        group: "demangle"
        description: "Decode mangled/processed symbol names"

    This class keeps:
      - The full spec fields (id, cli, kind, choices, defaults, role, group, ...)
      - Backwards-compatible properties:
          .option  -> currently selected flag (for your generator)
          .arg     -> currently selected value (or first default)
          .kind    -> kind from YAML ("flag" | "value" | "choice")
          .choices -> choice list from YAML (if any)
    """

    def __init__(
        self,
        opt_id: str,
        cli: List[str],
        kind: str,
        metavar: Optional[str] = None,
        choices: Optional[List[str]] = None,
        defaults: Optional[List[str]] = None,
        role: str = "modifier",
        include_in_search: bool = True,
        in_place_editing: bool = False,
        group: Optional[str] = None,
        output: Optional[str] = "",
        description: str = "",
    ) -> None:
        # Spec fields
        self.id: str = str(opt_id)
        self.cli: List[str] = list(cli)
        self.kind: str = kind           # "flag", "value", "choice"
        self.metavar: Optional[str] = metavar
        self.choices: List[str] = choices or []
        self.defaults: List[str] = defaults or []
        self.role: str = role           # e.g. "mode", "modifier"
        self.include_in_search: bool = bool(include_in_search)
        self.in_place_editing: bool = bool(in_place_editing)
        self.group: Optional[str]  = group
        self.output: Optional[str] = output
        self.description: str = description.strip()

        # Runtime selection (can be adjusted later)
        # By default we pick the first CLI spelling as the active flag.
        self.selected_flag: str = self.cli[0] if self.cli else ""
        self.selected_value: Optional[str] = None  # concrete value/style, if chosen

        # Backward-compat type hint / extra metadata
        self.type: str = "str"  # kept only because old code referenced it
        self.action: str = ""   # placeholder for future use (e.g., "store_true")

    # ------------------------------------------------------------------
    # Backwards-compatible attributes
    # ------------------------------------------------------------------
    @property
    def option(self) -> str:
        """
        The flag string used by the generator, e.g. "-c" or "--demangle".
        Defaults to the first element in `cli` unless overridden.
        """
        return self.selected_flag

    @option.setter
    def option(self, flag: str) -> None:
        if flag not in self.cli:
            raise ValueError(f"Flag '{flag}' is not in CLI aliases {self.cli}")
        self.selected_flag = flag

    @property
    def arg(self) -> Optional[str]:
        """
        The current argument/value associated with this option.

        - If `selected_value` is set, return that.
        - Else for "value"/"choice" kinds, return the first default if any.
        - Else return None (for flags).
        """
        if self.selected_value is not None:
            return self.selected_value
        if self.kind in ("value", "choice") and self.defaults:
            return self.defaults[0]
        return None

    @arg.setter
    def arg(self, value: Optional[str]) -> None:
        self.selected_value = value

    # ------------------------------------------------------------------
    # Loading helpers
    # ------------------------------------------------------------------
    @classmethod
    def from_yaml_dict(cls, data: Dict[str, Any]) -> "Option":
        """
        Construct an Option from a single YAML entry under 'first:' or 'second:'.
        Expects keys like: id, cli, kind, metavar, choices, defaults, role,
        include_in_search, group, description.
        """
        return cls(
            opt_id=data.get("id", ""),
            cli=data.get("cli", []),
            kind=data.get("kind", "flag"),
            metavar=data.get("metavar"),
            choices=data.get("choices"),
            defaults=data.get("defaults"),
            role=data.get("role", "modifier"),
            include_in_search=data.get("include_in_search", True),
            in_place_editing=data.get("in_place_editing", False),
            group=data.get("group"),
            output=data.get("output", ""),
            description=data.get("description", ""),
        )

    @staticmethod
    def load_options_from_yaml(path: Path, section: str) -> List["Option"]:
        """
        Utility to load all options from a YAML file under a given section
        ("first" for primary, "second" for modifiers, etc.).

        Example YAML:

          first:
            - id: "1"
              cli: ["-a"]
              kind: "flag"
              description: "Display archive header"

          second:
            - id: "11"
              cli: ["-c", "--demangle"]
              kind: "choice"
              ...

        Usage:
          opts = Option.load_options_from_yaml(Path("objdump.yaml"), "second")
        """
        with path.open("r", encoding="utf-8") as f:
            doc = yaml.safe_load(f) or {}

        raw_list = doc.get(section, []) or []
        return [Option.from_yaml_dict(entry) for entry in raw_list]

    # ------------------------------------------------------------------
    # Pretty-print helpers
    # ------------------------------------------------------------------
    def __repr__(self) -> str:
        return (
            f"Option(id='{self.id}', cli={self.cli}, kind='{self.kind}', "
            f"arg='{self.arg}', choices={self.choices}, "
            f"defaults={self.defaults}, group={self.group}, "
            f"role={self.role}, description='{self.description}')"
        )

    def to_string(self) -> str:
        """
        Human-readable representation like the old version:
          option + optional arg
        """
        if self.arg:
            return f"{self.option} {self.arg}"
        return self.option
