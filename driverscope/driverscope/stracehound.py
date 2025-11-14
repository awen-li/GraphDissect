import os
import subprocess
import itertools
from typing import List
from driverscope.opthound import OptHound
from driverscope.option import Option
from driverscope.optparser import *


class StraceHound(OptHound):
    def __init__(self, benchmark_path, binary_path):
        super().__init__(benchmark_path, binary_path)

        # Mapping from binary names to parser classes
        parser_registry = {
            # libxml
            "xmllint": OptParseXML(),

            # xpdf
            "pdfdetach": OptParseXPDF(),
            "pdffonts":  OptParseXPDF(),
            "pdfimages": OptParseXPDF(),
            "pdfinfo":   OptParseXPDF(),
            "pdftohtml": OptParseXPDF(),
            "pdftopng":  OptParseXPDF(),
            "pdftoppm":  OptParseXPDF(),
            "pdftops":   OptParseXPDF(),
            "pdftotext": OptParseXPDF(),

            # avconv
            "avconv": OptParseAvconv(),
            "avprobe":OptParseAvprobe(),

            # sablot
            "sabcmd": SabcmdOptParser(),

            # Tippecanoe
            "tippecanoe": TippecanoeOptParser(),

            #binutils
            "objdump": ObjdumpOptParser(),
            "readelf": ReadelfOptParser(),
            "addr2line": ReadelfOptParser(),
            "nm-new":  ObjdumpOptParser(),
            "ranlib": RanlibOptParser(),   
            "strings": StringsOptParser(),
            "strip-new": ReadelfOptParser(),
            "elfedit": ElfeditOptParser(),

            #exiv2
            "exiv2": Exiv2OptParser()
        }

        # Use just the binary name (no path) for matching
        binary_name  = os.path.basename(binary_path)
        self.parsers = parser_registry.get(binary_name)
        if self.parsers is None:
            raise ValueError(f"No parsers registered for binary: {binary_name}")
        print(self.parsers)

    def run_help(self):
        """Runs the binary with --help using strace and captures the output."""
        try:
            cmd = os.path.abspath(self.binary_path)
            result = subprocess.run(
                [cmd, '--help'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
                universal_newlines=True
            )
            print(result.stdout)
            # We parse from stderr as strace writes system call logs to stderr
            return result.stdout
        except subprocess.CalledProcessError as e:
            print(f"[!] Failed to run strace on {self.binary_path}: {e}")
            return ""
    
    def parse_help_output(self, text):
        """
        Extracts Option objects from help output.
        Delegates multilevel parsing to specialized handler if detected.
        """
        options = self.parsers.parse_all(text)
        return options

    def deduplicate_options(self, opt_list: list) -> list:
        """
        Removes duplicate options from the list based on the 'option' field.
        Keeps the first occurrence of each unique option string.
        """
        seen = set()
        unique_opts = []
        for opt in opt_list:
            if opt.option not in seen:
                seen.add(opt.option)
                unique_opts.append(opt)
        return unique_opts


    def extract_options(self) -> List[Option]:
        """
        Extracts available options and their descriptions from the binary.
        Returns:
            A dictionary mapping option strings to their descriptions.
        """

        if self.parsers == None:
            print("No parser supported!")
            return []
        
        raw_output  = self.run_help()
        opt_list    = self.parse_help_output(raw_output)
        unique_opts = self.deduplicate_options(opt_list)

        #print(f"@extract_options --> {len(unique_opts)}: {unique_opts}")
        return unique_opts
