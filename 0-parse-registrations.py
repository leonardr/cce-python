# This script converts each copyright registration record from XML to
# JSON, with a minimum of processing.
import json
from pdb import set_trace
import os
from collections import defaultdict
from lxml import etree
from model import Registration
import time

class Parser(object):

    def __init__(self):
        self.parser = etree.XMLParser(recover=True)
        self.count = 0
        self.seen_tags = set()
        self.seen_publisher_tags = set()

    def process_directory_tree(self, path):
        before = time.time()
        for dir, subdirs, files in os.walk(path):
            if 'alto' in subdirs:
                subdirs.remove('alto')
            for i in files:
                if not i.endswith('xml'):
                    continue
                for entry in self.process_file(os.path.join(dir, i)):
                    yield entry
                    self.count += 1
                    if not (self.count % 10000):
                        after = time.time()
                        print("%d %.2fsec" % (self.count, after-before))
                        before = after
                        after = None

    def process_file(self, path):
        tree = etree.parse(open(path), self.parser)
        for e in tree.xpath("//copyrightEntry"):
            for registration in Registration.from_tag(e, include_extra=False):
                yield registration.jsonable()

if not os.path.exists("output"):
    os.mkdir("output")
output = open("output/0-parsed-registrations.ndjson", "w")
for parsed in Parser().process_directory_tree("registrations/xml"):
        json.dump(parsed, output)
        output.write("\n")
