import os
import re
import itertools
from typing import List, Optional, Tuple
from driverscope.option import Option
from abc import ABC, abstractmethod
from itertools import combinations

class OptParser(ABC):
    def __init__(self, name: str, regex: str = "", comb_failed=True):
        self.name = name
        self.pattern = re.compile(regex) if regex else None
        self.except_opts = ['--help', '-help', '-h', '-?', '-v', '-V', '-version', '--version']
        self.output_opts = ['--output', '-o']

        self.comb_failed = comb_failed

    @abstractmethod
    def parse(self, line: str):
        """
        Parse a line of help text.

        Returns:
            - A tuple (opt, arg, desc) if single-level.
            - A list of such tuples if multi_level is True.
            - None if the line is not matched.
        """
        pass
    
    def parse_all(self, text: str) -> List[Option]:
        """
        Parse all help text.

        Returns:
            - options
        """
        """
        Extracts Option objects from help output.
        Delegates multilevel parsing to specialized handler if detected.
        """
        options = []

        line_no   = 0
        all_lines = text.splitlines()
        while line_no < len(all_lines):
            line = all_lines[line_no]
            line_no += 1
        
            if len(line.strip()) < 4:
                continue

            print(f"@[{self.name}]parse_all: {line}")
            opt, arg, desc = None, None, None
            opt, arg, desc = self.parse(line)    

            if opt is None or opt in self.except_opts:
                continue

            print(f"\t--> {opt}:{arg}:{desc}")
            self._add_option(options, opt, arg, desc)

        return options

    def infer_type(self, arg: Optional[str]) -> str:
        if not arg:
            return "str"
        arg_l = arg.lower()
        if any(kw in arg_l for kw in ["file", "path", "name", "img"]):
            return "str"
        elif any(kw in arg_l for kw in ["num", "count", "value", "size", "ampl", "max", "min", "limit", "idx", "id"]):
            return "int"
        return "str"

    def _add_option(self, options, opt, arg, desc):
        inferred_type = self.infer_type(arg)
        if opt in self.output_opts:
            arg = "/dev/null"
        opt = Option(option=opt, arg=arg, description=desc, type_hint=inferred_type, comb_failed=self.comb_failed)
        options.append(opt)
        return opt
    

################################################################
# OPTION PARSER for benchmarks
#
################################################################

class OptParseXML(OptParser):
    def __init__(self, regex=r'\s*(--\S+)(?:\s+(\S+))?\s*:\s*(.+)'):
        super().__init__("OptParseXML1", regex)
        self.except_opts.append("--shell")
        self.pattern_long = re.compile(r'\s*(--[a-zA-Z0-9_\-]+)(?:=([A-Z]+))?,?\s*(-\S+)?\s+(.*)')

    def parse(self, line: str):
        match = self.pattern.match(line)
        if match:
            opt = match.group(1).strip()
            arg = match.group(2).strip() if match.group(2) else None
            desc = match.group(3).strip()
            return opt, arg, desc
        else:
            match = self.pattern_long.match(line)
            if match:
                long_opt = match.group(1).strip()                 # e.g., '--base'
                arg = match.group(2).strip() if match.group(2) else None  # e.g., 'NAME'
                alias = match.group(3).strip() if match.group(3) else None
                desc = match.group(4).strip()
                return long_opt, arg, desc
        return None, None, None
    
    def parse_all(self, text: str) -> List[Option]:
        return super().parse_all(text)
    
class OptParseXPDF(OptParser):
    def __init__(self, regex=r'^\s*(--?\S+)(?:\s+<[^>]+>)?\s*[:]{0,1}\s+(.*)$'):
        """
        Matches:
          - '-o <string> : output file'
          - '--save <int>      : save file'
          - '--help     show help'
        """
        super().__init__("OptParseXPDF", regex)

    def parse(self, line: str):
        match = self.pattern.match(line)
        if match:
            opt = match.group(1).strip()
            # Try to infer argument (e.g., <int>, <string>) manually
            arg_match = re.search(r'<([^>]+)>', line)
            arg = arg_match.group(1) if arg_match else None
            desc = match.group(2).strip()
            return opt, arg, desc
        return None, None, None
    
    def parse_all(self, text: str) -> List[Option]:
        return super().parse_all(text)

class OptParseAvprobe(OptParser):
    def __init__(self):
        # Matches patterns like:
        # -option               description
        # -option arg           description
        # -option    arg        description
        regex = r'^\s*(-{1,2}[a-zA-Z0-9_?]+)(?:\s+([a-zA-Z0-9_<>|]+))?\s{2,}(.*)'
        super().__init__("OptParseAvprobeMain", regex)

        self.main_opt_re = re.compile(
            r'^-(\S+)\s+(?:<(\w+)>|\(\w+\))?\s+([ED\.]+)(?:\s+(.*))?'
        )
        self.sub_opt_re = re.compile(
            r'^\s{0,4}(\w+)\s+[ED\.]+\s+(.*)'
        )

    def parse(self, line: str):
        match = self.pattern.match(line)
        if match:
            opt = match.group(1).strip()                     # e.g., '-v', '--help'
            arg = match.group(2).strip() if match.group(2) else None  # e.g., 'format'
            desc = match.group(3).strip()
            return opt, arg, desc
        return None, None, None
    
    def parse_ml_main(self, line: str):
        """
        Parses a main option line.
        Example: "-fflags <flags> ED..... description"
        Returns: (option, arg, description)
        """
        match = self.main_opt_re.match(line)
        if match:
            opt = f"-{match.group(1).strip()}"
            arg = match.group(2).strip() if match.group(2) else None
            desc = match.group(4).strip() if match.group(4) else ""
            return opt, arg, desc
        return None, None, None

    def parse_ml_sub(self, line: str):
        """
        Parses a sub-option line.
        Example: "  flush_packets .D..... description"
        Returns: (subopt, None, description)
        """
        match = self.sub_opt_re.match(line)
        if match:
            subopt = match.group(1).strip()
            desc = match.group(2).strip()
            return subopt, None, desc
        return None, None, None
    
    def _parse_multilevel(self, lines: list[str], start_index: int) -> list[Option]:
        """
        Parse multilevel options starting from the detected main option index.
        """
        options = []
        i = start_index

        while i < len(lines):
            line = lines[i]
            i += 1

            if len(line.strip()) < 4:
                continue
            
            print(f"@[{self.name}]_parse_multilevel: {line}")
            main_opt, maim_arg, main_desc = self.parse_ml_main(line)
            if main_opt is None:
                continue
            
            cached_subs = []
            while i < len(lines):
                sub_line = lines[i]
                print(f"@[{self.name}]_parse_multilevel: sub_line - {sub_line}")
                sub_opt, _, sub_desc = self.parse_ml_sub(sub_line)
                if sub_opt != None:
                    cached_subs.append(sub_opt)
                    i += 1
                else:
                    break

            if len(cached_subs) != 0:
                print(f"@[{self.name}]_parse_multilevel: cached_subs - {cached_subs}")
                for r in range(1, len(cached_subs) + 1):
                    for subset in itertools.combinations(cached_subs, r):
                        combo = '+'.join(subset)
                        full_opt = f"{main_opt}+{combo}"
                        print(f"\t[{self.name}]-->main_subs - {full_opt}:None:{main_desc} with {combo}")
                        self._add_option(options, full_opt, None, f"{main_desc} with {combo}")
            else:
                print(f"\t[{self.name}]-->only_main - {main_opt}:{maim_arg}:{main_desc}")
                self._add_option(options, main_opt, maim_arg, main_desc)

        return options

    def parse_all(self, text: str) -> List[Option]:
        """
        Parse all help text.

        Returns:
            - options
        """
        """
        Extracts Option objects from help output.
        Delegates multilevel parsing to specialized handler if detected.
        """
        options = []
        mode    = ""

        line_no   = 0
        all_lines = text.splitlines()
        while line_no < len(all_lines):
            line = all_lines[line_no]
            line_no += 1
        
            if len(line.strip()) < 4:
                continue

            if "Main options" in line:
                # parse main options
                mode = "main"
            elif "AVOptions" in line:
                mode = "sub"

            if mode == "main":
                print(f"@[{self.name}]parse_all: {line}")
                opt, arg, desc = None, None, None
                opt, arg, desc = self.parse(line)    

                if opt is None or opt in self.except_opts:
                    continue

                print(f"\t--> {opt}:{arg}:{desc}")
                self._add_option(options, opt, arg, desc)

            elif mode == "sub":
                options.extend(self._parse_multilevel(all_lines, line_no))
            
            else:
                continue

        return options
    

class OptParseAvconv(OptParser):
    def __init__(self):
        super().__init__("OptParseAvconv", regex=r'^(-{1,2}[\w?]+)(?:\s+([\w\-]+))?\s{2,}(.*)$')

    def parse(self, line: str):
        """
        Parses a single line of avconv help output.
        Returns: (option, arg, description) or None
        """
        match = self.pattern.match(line)
        if match and match.lastindex > 2:
            opt = match.group(1).strip()
            arg = match.group(2).strip() if match.group(2) else None
            desc = match.group(3).strip()
            return opt, arg, desc
        return None, None, None
    
    def parse_all(self, text: str) -> List[Option]:
        return super().parse_all(text)


class SabcmdOptParser(OptParser):
    def __init__(self):
        # Matches: --long, -s        description
        # or      --long=ARG, -s     description
        super().__init__("SabcmdOptParser", regex=r'^\s*(--[\w-]+(?:=[\w<>-]+)?)(?:,\s*(-\w))?\s{2,}(.*)')     

    def parse(self, line: str):
        match = self.pattern.match(line)
        if not match:
            return None, None, None
        
        opt_full, short_opt, desc = match.groups()

        # Split --long=ARG into opt and arg
        if '=' in opt_full:
            opt, arg = opt_full.split('=', 1)
        else:
            opt, arg = opt_full, None

        return opt, arg, desc

    def parse_all(self, text: str) -> List[Option]:
        return super().parse_all(text)
    

class TippecanoeOptParser(OptParser):
    def __init__(self):
        # Only match options inside brackets: [--opt=...] or [--opt]
        super().__init__("TippecanoeOptParser", regex=r'\[(--[\w-]+)(?:=([^\]]+))?\]')

    def parse(self, line: str):
        matches = self.pattern.findall(line)
        if not matches:
            return None

        results = []
        for opt, arg in matches:
            # Normalize arg
            if arg and "..." in arg:
                arg = "ARG"
                if opt == "--output-to-directory":
                    arg = None
            elif not arg:
                arg = None
            results.append((opt, arg, ""))
        return results  # List of (opt, arg, desc)

    def parse_all(self, text: str) -> List[Option]:
        options = []
        lines = text.splitlines()

        for line in lines:
            if len(line.strip()) < 4:
                continue

            print(f"@[{self.name}]parse_all: {line}")
            parsed = self.parse(line)

            if not parsed:
                continue

            for opt, arg, desc in parsed:
                if opt in self.except_opts:
                    continue
                print(f"\t--> {opt}:{arg}:{desc}")
                self._add_option(options, opt, arg, desc)

        return options



class ObjdumpOptParser(OptParser):
    def __init__(self):
        # Match optional short opt and required long opt with optional =ARG
        super().__init__(
            "ObjdumpOptParser",
            regex=r'^\s*(?:-\w+,\s*)?(--[\w\-]+)(?:=([\w\-]+))?\s*(.*)?$'
        )

    def parse(self, text: str) -> List[Option]:
        match = self.pattern.match(text)
        if match:
            opt = match.group(1)
            arg = match.group(2)
            desc = match.group(3).strip() if match.group(3) else ""
            return opt, arg, desc
        return None, None, None

    def parse_all(self, text: str) -> List[Option]:
        return super().parse_all(text)
    
    
class ReadelfOptParser(OptParser):
    def __init__(self):
        super().__init__(
            "ReadelfOptParser",
            regex=r'^\s*(?:-\w[\w-]*\s*)?(--[\w\-]+)(?:[= ]<([\w|]+)>)?\s*(.*?)\s*$'
        )

    def parse(self, line: str) -> List[Option]:
        match = self.pattern.match(line)
        if not match:
            return None, None, None

        opt = match.group(1).strip()
        arg_raw = match.group(2).strip() if match.group(2) else None
        desc = match.group(3).strip() if match.group(3) else ""
        return opt, arg_raw, desc
        
    def parse_all(self, text: str) -> List[Option]:
        options = []

        line_no   = 0
        all_lines = text.splitlines()
        while line_no < len(all_lines):
            line = all_lines[line_no]
            line_no += 1
        
            if len(line.strip()) < 4:
                continue

            print(f"@[{self.name}]parse_all: {line}")
            opt, arg, desc = None, None, None
            opt, arg, desc = self.parse(line)    

            if opt is None or opt in self.except_opts:
                continue

            if arg and "|" in arg:
                # Split arg by "|" and add one Option for each
                for sub_arg in arg.split("|"):
                    sub_arg = sub_arg.strip()
                    print(f"\t--> {opt}:{sub_arg}:{desc}")
                    self._add_option(options, opt, sub_arg, desc)
            else:
                print(f"\t--> {opt}:{arg}:{desc}")
                self._add_option(options, opt, arg, desc)

        return options
    

class RanlibOptParser(OptParser):
    def __init__(self):
        super().__init__("RanlibOptParser", regex=r'^\s*(-\w)\s+(.*)$')

    def parse(self, line: str):
        match = self.pattern.match(line)
        if not match:
            return None, None, None
        opt, desc = match.groups()
        return opt, None, desc.strip()
    
    
class StringsOptParser(OptParser):
    def __init__(self):
        super().__init__("StringsOptParser",
                         regex=r'^\s*((?:-\w(?:\s+[<{][^>\]}]+[>\]}])?\s*)*)'   # short options
                               r'(--[\w-]+(?:[=<{][^>\]}]+[>\]}]?)?)?\s*'       # optional long option
                               r'(.*)$'                                         # description
                        )

    def _split_option_arg(self, token: str) -> Tuple[str, Optional[str]]:
        token = token.strip()
        if '=' in token:
            opt, arg = token.split('=', 1)
        elif '<' in token or '{' in token:
            opt = token[:token.find('<')] if '<' in token else token[:token.find('{')]
            arg = token[token.find('<'):].strip() if '<' in token else token[token.find('{'):].strip()
        else:
            opt, arg = token, None
        return opt.strip(), arg

    def parse(self, line: str):
        match = self.pattern.match(line)
        if not match:
            return None

        short_part, long_part, desc = match.groups()
        entries = []

        # Extract short options manually (e.g., -a, -b <arg>, -U {x|y})
        if short_part:
            tokens = re.findall(r'(-\w)(?:\s+([<{][^>\]}]+[>\]}]))?', short_part)
            for opt, arg in tokens:
                entries.append((opt, arg.strip() if arg else None, desc.strip()))

        # Extract long option
        if long_part and long_part.strip().startswith("--"):
            opt, arg = self._split_option_arg(long_part.strip())
            entries.append((opt, arg, desc.strip()))

        return entries if entries else None

    def parse_all(self, text: str) -> List[Option]:
        options = []
        seen_opts = set()
        all_lines = text.splitlines()

        for line in all_lines:
            if len(line.strip()) < 4:
                continue

            print(f"@[{self.name}]parse_all: {line}")
            result = self.parse(line)
            if not result:
                continue

            # Prefer long options if available
            longs = [r for r in result if r[0].startswith("--")]
            shorts = [r for r in result if r[0].startswith("-") and not r[0].startswith("--")]
            targets = longs if longs else shorts

            for opt, arg, desc in targets:
                if opt in seen_opts or opt in self.except_opts:
                    continue
                seen_opts.add(opt)

                # Expand long option with brace values like --opt={a,b}
                if opt.startswith("--") and arg and "{" in arg and "}" in arg:
                    for val in re.split(r'[|,]', arg.strip("{} ")):
                        full_opt = f"{opt}={val.strip()}"
                        print(f"\t--> {full_opt}:None:{desc}")
                        self._add_option(options, full_opt, None, desc)

                # Expand short option with brace values like -U {a|b}
                elif opt.startswith("-") and arg and "{" in arg and "}" in arg:
                    for val in re.split(r'[|,]', arg.strip("{} ")):
                        full_opt = f"{opt} {val.strip()}"
                        print(f"\t--> {full_opt}:None:{desc}")
                        self._add_option(options, full_opt, None, desc)

                # Clean angled args like <arg>
                elif arg and (arg.startswith("<") or arg.startswith("{")):
                    clean_arg = arg.strip("<>{} ")
                    print(f"\t--> {opt}:{clean_arg}:{desc}")
                    self._add_option(options, opt, clean_arg, desc)

                else:
                    print(f"\t--> {opt}:{arg}:{desc}")
                    self._add_option(options, opt, arg, desc)

        return options


class ElfeditOptParser(OptParser):
    def __init__(self):
        super().__init__("ElfeditOptParser",
                        regex=r'^\s*(?:-\w\s+)?'              # optional short option
                              r'(--[\w-]+)'                   # long option
                              r'(?:\s+\[([^\]]+)\])?'         # optional bracketed values [a|b|c]
                              r'\s*(.*)$'                     # description
                        )    

    def parse(self, line: str):
        match = self.pattern.match(line)
        if not match:
            return None, None, None

        opt, valset, desc = match.groups()
        if valset:
            return f"{opt}=[{valset.strip()}]", None, desc.strip()
        return opt.strip(), None, desc.strip()

    def parse_all(self, text: str):
        options = []
        all_lines = text.splitlines()
        seen = set()

        for line in all_lines:
            if len(line.strip()) < 2:
                continue

            print(f"@[{self.name}]parse_all: {line}")
            opt, arg, desc = self.parse(line)
            if not opt or opt in self.except_opts or opt in seen:
                continue
            seen.add(opt)

            # Expand [a|b|c] inside the option string
            if opt.endswith("]") and "[" in opt:
                base = opt[:opt.find("[")].rstrip(" =")
                vals = re.split(r'[|,]', opt[opt.find("[")+1 : opt.find("]")])
                for v in vals:
                    full_opt = f"{base}={v.strip()}"
                    print(f"\t--> {full_opt}:None:{desc}")
                    self._add_option(options, full_opt, None, desc)
            else:
                print(f"\t--> {opt}:{arg}:{desc}")
                self._add_option(options, opt, arg, desc)

        return options
    

class Exiv2OptParser(OptParser):
    def __init__(self):
        super().__init__("Exiv2OptParser", regex=r'', comb_failed=False)
        self.action_pattern = re.compile(r'^\s*(\w{2})\s*\|\s*(\w+)\s+(.*)')
        self.option_pattern = re.compile(r'^\s*(-\w)(?: (\S+))?\s{2,}(.*)$')
        self.multi_mode_header = re.compile(r'^\s*(-\w)\s+(\S+)\s+(.*?)$')
        self.mode_entry_pattern = re.compile(r'^\s{13}(\S+)\s*:\s*(.*)$')

    def parse(self, line: str):
        return None, None, None

    def parse_all(self, text: str) -> List[Option]:
        options = []
        mode = None
        cached_options = []
        cached_actions = []

        lines = text.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if len(line) < 2:
                i += 1
                continue

            print(f"@[{self.name}]parse_all: {line}")
            if line.startswith("Actions:"):
                mode = "ACTION"
                i += 1
                continue
            elif line.startswith("Options:"):
                mode = "OPTION"
                i += 1
                continue

            if mode == "ACTION":
                match = self.action_pattern.match(line)
                if match:
                    abbr, name, desc = match.groups()
                    cached_actions.append((name, desc))
                    print(f"\t[ACTION] {name}: {desc}")

            elif mode == "OPTION":
                match = self.multi_mode_header.match(line)
                if match and i + 1 < len(lines):
                    flag, arg, desc = match.groups()
                    modes = []
                    j = i + 1
                    while j < len(lines):
                        mode_line = lines[j]
                        mode_match = self.mode_entry_pattern.match(mode_line)
                        if not mode_match:
                            break
                        mode_val, mode_desc = mode_match.groups()
                        modes.append((mode_val.strip(), mode_desc.strip()))
                        j += 1
                    if modes:
                        for mode_val, mode_desc in modes:
                            opt_str = f"{flag} {mode_val}"
                            cached_options.append((opt_str, None, desc.strip(), []))
                            print(f"\t[MULTI-MODE] {opt_str}:None:{desc.strip()} + {mode_desc}")
                        i = j
                        continue

                match = self.option_pattern.match(line)
                if match:
                    flag, arg, desc = match.groups()
                    if flag not in self.except_opts:
                        cached_options.append((flag, arg, desc.strip(), []))
                        print(f"\t[OPTION] {flag}:{arg}:{desc.strip()}")

            i += 1

        # Then add each option to each action, doing combinations only per option
        for flag, arg, desc, modes in cached_options:
            if modes:
                for mode_val, mode_desc in modes:
                    for action_name, _ in cached_actions:
                        full_flag = f"{flag} {mode_val} {action_name}"
                        full_desc = f"{desc} + {mode_desc.strip()} (for {action_name})"
                        self._add_option(options, full_flag, None, full_desc)
                        print(f"\t[MULTI-MODE] {full_flag}: {full_desc}")
            else:
                if arg != None:
                    for action_name, _ in cached_actions:
                        combo = f"{flag}"
                        opt   = self._add_option(options, combo, arg, f"{desc} (for {action_name})")
                        opt.action = action_name
                        print(f"\t[PAIR-arg] {combo}: {desc}")
                else:
                    for action_name, _ in cached_actions:
                        combo = f"{flag} {action_name}"
                        self._add_option(options, combo, None, f"{desc} (for {action_name})")
                        print(f"\t[PAIR] {combo}: {desc}")

        return options
