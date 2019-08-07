# This script converts each copyright renewal record from CSV to
# a JSON format similar to (but much simpler than) that created by
# 0-parse-registrations.py.
import json
from pdb import set_trace
import os
from csv import DictReader
from collections import defaultdict
from model import Renewal

class Parser(object):

    def __init__(self):
        self.count = 0
        self.cross_references = defaultdict(list)
        
    def process_directory_tree(self, path):
        for i in os.listdir(path):
            if not i.endswith('tsv'):
                continue
            if i == 'TOC.tsv':
                continue
            for entry in self.process_file(os.path.join(path, i)):
                yield entry
                self.count += 1
        print(self.count)

    def process_file(self, path):
        for line in DictReader(open(path), dialect='excel-tab'):
            yield Renewal.from_dict(line)
            
output = open("output/1-parsed-renewals.ndjson", "w")
parser = Parser()
for parsed in parser.process_directory_tree("renewals/data"):
        json.dump(parsed.jsonable(), output)
        output.write("\n")

