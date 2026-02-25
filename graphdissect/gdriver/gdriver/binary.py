import os
import sys
import yaml
import copy
from pathlib import Path
from textwrap import indent
from .option import Option
from .constraint import Constraints
from .profile import BinProfile
from typing import List, Dict, Any

class Binary:
    """
    Represents one benchmark binary (e.g., objdump) with:
      - BinProfile
      - primary_options (list[Option])  # atomic variants
      - second_options  (list[Option])  # atomic variants
      - constraints     (Constraints)
    """
    def __init__(self, bench_path: str):
        profile_path = bench_path + f"/cmdspec.yaml"
        profile_path = Path(profile_path)

        try:
            with open(profile_path, "r") as f:
                data = yaml.safe_load(f)
        except Exception as e:
            print(f"{e}")
            sys.exit(0)

        # --- Load top-level profile ---
        self.profile = BinProfile.from_dict(data["profile"])

        # --- Load and expand primary / second options ---
        raw_primary = data.get("primary", [])
        raw_second  = data.get("second", [])
        raw_constraints = data.get("constraints", [])

        self.primary_options = self._expand_option_list(raw_primary, is_primary=True)
        self.second_options  = self._expand_option_list(raw_second,  is_primary=False)

        # Expand any multi-output options into multiple options
        self.primary_options = self._expand_output_variants(self.primary_options)
        self.second_options  = self._expand_output_variants(self.second_options)

        # --- Constraints ---
        self.constraints = Constraints(raw_constraints)

    # ---------- internal helpers ----------
    def _expand_option_list(self, entries: List[Dict[str, Any]], is_primary: bool) -> List[Option]:
        """
        Turn YAML option entries into Option instances compatible with the new spec-based
        Option class.

        Behavior:
        - Skip entries with include_in_search: false.
        - For kind == "choice":
            * Keep a single Option instance per YAML entry.
            * If defaults are provided, restrict .choices to that subset;
                otherwise use the full choices list.
            * Your existing build_args_for_option(...) will then expand these
                choices into multiple "<flag> <value>" chunks.
        - For kind in {"flag", "value", "path", "int", "float"}:
            * Keep one Option instance per entry, with .arg exposing the first
                default (if any) through Option.arg.
        - Unknown kinds fall back to a simple flag Option.
        """
        out: List[Option] = []

        for entry in entries:
            if not entry.get("include_in_search", True):
                # Present in spec but not to be used automatically
                continue

            kind = entry.get("kind", "flag")

            # Build a base Option from the YAML dict
            opt = Option.from_yaml_dict(entry)

            # Restrict or adjust according to kind
            if kind == "choice":
                # If defaults are given, we only want to enumerate those;
                # otherwise we use all choices from the YAML.
                values = entry.get("defaults") or entry.get("choices") or []
                opt.choices = [str(v) for v in values]
                # Keep kind == "choice" so build_args_for_option will expand opt.choices.

            elif kind in ("value", "path", "int", "float"):
                # For value-like options, we typically want a single Option whose .arg
                # is derived from defaults. Option.arg property already returns the
                # first default if no selected_value is set, so we don't need to
                # manually duplicate per default here.
                pass  # opt.defaults is already populated by from_yaml_dict

            else:
                # "flag" or unknown kinds: nothing extra to do.
                pass

            # Attach any internal metadata like opt_id, role, group, is_primary, etc.
            # Assuming your existing helper still works with the new Option object.
            self._attach_meta(opt, entry, is_primary=is_primary)

            # Debug printing, still using the old-style representation
            #print(opt.to_string())

            out.append(opt)

        return out

    def _suffix_from_output(self, output: str) -> str:
        """
        Derive a short, id-friendly suffix from an output filename.
        Examples:
        'out.wav'  -> 'wav'
        'frame.png'-> 'png'
        'dump'     -> 'dump'
        """
        base = os.path.basename(output)
        root, ext = os.path.splitext(base)
        if ext:
            return ext.lstrip(".")  # 'wav', 'mkv', ...
        return root or "out"

    def _expand_output_variants(self, options):
        """
        Expand options with a comma-separated 'output' string into multiple options.

        Rules:
        - No 'output' field          -> keep as-is
        - 'output' == ""             -> keep as-is
        - 'output' == "out.x"        -> keep as-is (normalized)
        - 'output' == "a, b, c, ..." -> clone into multiple options, one per output
        """
        expanded = []
        for opt in options:
            # output is an attribute on Option, or may not exist
            out_spec = getattr(opt, "output", None)

            # 1) No output field -> keep as-is
            if out_spec is None:
                expanded.append(opt)
                continue

            # output is always a string in your design
            cleaned = out_spec.strip()

            # 2) No comma -> single (or empty) output, keep as-is (normalized)
            #    Covers: "", "out.x"
            if "," not in cleaned:
                setattr(opt, "output", cleaned)
                expanded.append(opt)
                continue

            # 3) Comma-separated -> split into multiple outputs
            outputs = [s.strip() for s in cleaned.split(",") if s.strip()]

            if len(outputs) <= 1:
                # Degenerate case: only one effective output
                if outputs:
                    setattr(opt, "output", outputs[0])
                expanded.append(opt)
                continue

            # 4) True multi-output case -> clone per output
            base_id = getattr(opt, "id", "")

            for idx, out in enumerate(outputs):
                new_opt = copy.deepcopy(opt)
                setattr(new_opt, "output", out)

                suffix = self._suffix_from_output(out)
                if base_id:
                    new_id = f"{base_id}_{suffix}"
                else:
                    new_id = f"opt_{suffix}_{idx}"

                setattr(new_opt, "id", new_id)
                expanded.append(new_opt)

        return expanded


    def _attach_meta(self, opt: Option, entry: dict, is_primary: bool, arg_value=None):
        """
        Attach spec metadata to an Option instance without changing its constructor.
        """
        opt.opt_id       = entry["id"]
        opt.role         = entry.get("role", "modifier")
        opt.group        = entry.get("group")
        opt.metavar      = entry.get("metavar")
        opt.value_template = entry.get("value_template")
        opt.choices      = entry.get("choices") or []
        opt.defaults     = entry.get("defaults") or []
        opt.is_primary   = is_primary
        opt.arg_value    = arg_value  # logical value (before str())
        opt.cli_aliases  = entry.get("cli", [])
        opt.include_in_search = entry.get("include_in_search", True)

    # ---------- convenience ----------
    def __repr__(self):
        return (f"Binary(profile={self.profile!r}, "
                f"primary_options={len(self.primary_options)}, "
                f"second_options={len(self.second_options)})")
    
    def get_binary_name(self):
        return self.profile.binary

    # ============================================================
    # Debug helper
    # ============================================================
    def debug_print(self, stream=sys.stdout):
        """
        Pretty-print all parsed info for this Binary:
          - profile
          - primary options (atomic variants)
          - secondary options (atomic variants)
          - constraints
        """
        def w(line=""):
            print(line, file=stream)

        w("=== Binary Profile ===")
        w(f"  name            : {self.profile.name}")
        w(f"  binary          : {self.profile.binary}")
        w(f"  domain          : {self.profile.domain}")
        w(f"  seed_dir        : {self.profile.seed_dir}")
        w(f"  max_combination : {self.profile.max_combination}")
        w()

        # -------- primary options --------
        w(f"=== Primary Options (atomic variants) [count={len(self.primary_options)}] ===")
        for idx, opt in enumerate(self.primary_options):
            # opt.option = flag; opt.arg = argument; opt.description; plus meta
            group = getattr(opt, "group", None)
            role = getattr(opt, "role", None)
            opt_id = getattr(opt, "opt_id", None)
            defaults = getattr(opt, "defaults", [])
            choices = getattr(opt, "choices", [])
            cli_aliases = getattr(opt, "cli_aliases", [])

            w(f"- [{idx}] id={opt_id!r}")
            w(f"    flag        : {opt.option!r}")
            w(f"    arg         : {opt.arg!r}")
            w(f"    role        : {role!r}")
            w(f"    group       : {group!r}")
            w(f"    type_hint   : {opt.type!r}")
            w(f"    is_primary  : {getattr(opt, 'is_primary', False)}")
            w(f"    cli_aliases : {cli_aliases}")
            if choices:
                w(f"    choices     : {choices}")
            if defaults:
                w(f"    defaults    : {defaults}")
            if opt.description:
                w(f"    desc        : {opt.description}")
            w()

        # -------- secondary options --------
        w(f"=== Secondary Options (atomic variants) [count={len(self.second_options)}] ===")
        for idx, opt in enumerate(self.second_options):
            group = getattr(opt, "group", None)
            role = getattr(opt, "role", None)
            opt_id = getattr(opt, "opt_id", None)
            defaults = getattr(opt, "defaults", [])
            choices = getattr(opt, "choices", [])
            cli_aliases = getattr(opt, "cli_aliases", [])

            w(f"- [{idx}] id={opt_id!r}")
            w(f"    flag        : {opt.option!r}")
            w(f"    arg         : {opt.arg!r}")
            w(f"    role        : {role!r}")
            w(f"    group       : {group!r}")
            w(f"    type_hint   : {opt.type!r}")
            w(f"    is_primary  : {getattr(opt, 'is_primary', False)}")
            w(f"    cli_aliases : {cli_aliases}")
            if choices:
                w(f"    choices     : {choices}")
            if defaults:
                w(f"    defaults    : {defaults}")
            if opt.description:
                w(f"    desc        : {opt.description}")
            w()

        # -------- constraints --------
        w("=== Constraints ===")
        if not getattr(self.constraints, "rules", None):
            w("  (none)")
        else:
            for i, rule in enumerate(self.constraints.rules):
                w(f"  [{i}] type={rule.get('type')!r}, data={rule}")
        w()
