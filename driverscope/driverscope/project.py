import os
import sys
import yaml

class Project():
    def __init__(self, yamlFile):
        try:
            with open(yamlFile) as f:
                yamlData = yaml.safe_load(f)
                projData = yamlData['project']

                self.name     = self.getValue(projData, 'name')
                self.desc     = self.getValue(projData, 'description')
                self.github   = self.getValue(projData, 'github') 
                self.format   = self.getValue(projData, 'format')
                self.encoding = self.getValue(projData, 'encoding')
                self.cmdline  = self.getValue(projData, 'cmdline')
        except Exception as e:
            print(f"[!] Load YAML file error: {yamlFile} --> {e}")
            print(f"Current directory: {os.getcwd()}")
            sys.exit(1)

    def getValue(self, data, key):
        return data.get(key, "")

    def to_string(self):
        return (
            f"Project Name: {self.name}\n"
            f"Description: {self.desc}\n"
            f"GitHub: {self.github}\n"
            f"Format: {self.format}\n"
            f"Encoding: {self.encoding}"
        )

    def is_base64_encoding(self):
        return self.encoding.lower() == "base64"
