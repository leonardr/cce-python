# This script converts each copyright registration record from CSV to
# a JSON format similar to (but much simpler than) that created by
# 0-parse-registrations.py.
import json
from pdb import set_trace
import os
from csv import DictReader
from collections import defaultdict

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
            yield self.process_entry(line)

    def process_entry(self, entry):
        uuid = entry['entry_id']
        regnum = entry['oreg']
        reg_date = entry['odat']
        author = entry.get('auth', None)
        title = entry.get('titl', entry.get('title', None))
        renewal_id = entry['id']
        renewal_date = entry.get('dreg', None)
        new_matter = entry['new_matter']
        see_also_renewal = [x for x in entry['see_also_ren'].split("|") if x]
        see_also_registration = [x for x in entry['see_also_reg'].split("|") if x]
        data = dict(uuid=uuid, regnum=regnum, reg_date=reg_date, renewal_id=renewal_id,
                    renewal_date=renewal_date, author=author, title=title, new_matter=new_matter,
                    see_also_renewal=see_also_renewal,
                    see_also_registration=see_also_registration,
        )
        if see_also_registration:
            self.cross_references[regnum].extend(see_also_registration)
        return data
            
output = open("output/1-parsed-renewals.ndjson", "w")
parser = Parser()
for parsed in parser.process_directory_tree("renewals/data"):
        json.dump(parsed, output)
        output.write("\n")

output = open("output/1-renewal-cross-references.json", "w")
json.dump(parser.cross_references, output)

