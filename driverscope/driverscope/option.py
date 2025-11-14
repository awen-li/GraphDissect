class Option:
    def __init__(self, option, arg=None, description="", type_hint="str", comb_failed=True):
        self.option      = option
        self.arg         = arg
        self.description = description.strip()
        self.type        = type_hint
        self.comb_failed = comb_failed
        self.action      = ""

    def __repr__(self):
        return f"Option(option='{self.option}', arg='{self.arg}', type='{self.type}', description='{self.description}')"
    
    def to_string(self):
        return f"{self.option} {self.arg}"
