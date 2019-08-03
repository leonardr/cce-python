# This script converts each copyright registration record from XML to
# JSON, with a minimum of processing.
import json
from pdb import set_trace
from StringIO import StringIO
import os
from collections import defaultdict
from lxml import etree

class Parser(object):

    def __init__(self):
        self.parser = etree.XMLParser(recover=True)
        self.count = 0
        self.seen = set()
        
    def process_directory_tree(self, path):
        for dir, subdirs, files in os.walk(path):
            if 'alto' in subdirs:
                subdirs.remove('alto')
            for i in files:
                if not i.endswith('xml'):
                    continue
                for entry in self.process_file(os.path.join(dir, i)):
                    yield entry

    def process_file(self, path):
        tree = etree.parse(open(path), self.parser)
        for e in tree.xpath("//copyrightEntry"):
            yield self.process_registration(e)

    def xpath(self, tag, path):
        results = tag.xpath(path)
        return [x.text for x in results]
            
    def xpath1(self, tag, path):
        results = tag.xpath(path)
        if not results:
            return None
        return results[0].text

    def _package(self, tag):
        attrib = dict(tag.attrib)
        attrib['_text'] = tag.text
        return attrib
    
    def date(self, tag, path):
        results = tag.xpath(path)
        if not results:
            return None
        return [self._package(x) for x in results]

    def process_registration(self, entry):
        regnum = entry.attrib.get('regnum')
        uuid = entry.attrib.get('id', None)
        authors = self.xpath(entry, "author/authorName")
        reg_date = self.date(entry, "regDate") or self.date(entry, 'regdate')
        pub_date = self.date(entry, "publisher/pubDate")
        title = self.xpath1(entry, "title")
        key = (regnum, reg_date)
        publishers = []
        for publisher in entry.xpath("publisher"):
            package = dict(publisher.attrib)
            pub_date = self.date(publisher, "pubDate")
            publishers = []
            for publisher_name_tag in publisher.xpath("pubName"):                
                name = publisher_name_tag.text
                claimant = publisher_name_tag.attrib.get('claimant')
                publishers.append(dict(name=name, claimant=claimant, pub_date=pub_date))
        children = [
            self.process_registration(child)
            for  child in entry.xpath("additionalEntry")
        ]

        extra = defaultdict(list)
        if children:
            extra['children'] = children
        for name in [
                'edition', 'noticedate', 'series', 'newMatterClaimed',
                'vol', 'desc', 'prev-regNum', 'prevPub', 'pubDate', 'volumes',
                'claimant', 'copies', 'affDate', 'lccn', 'copyDate', 'role',
                'page', 'copyDate',
        ]:
            tags = []
            for extra_tag in entry.xpath(name):
                if extra_tag.attrib:
                    attrib = self._package(extra_tag)
                    tags.append(attrib)
                else:
                    tags.append(extra_tag.text)
            if tags:
                extra[name].extend(tags)
        
        #for subtag in entry.xpath("*"):
        #    if subtag.tag not in self.seen:
        #        print subtag.tag
        #        self.seen.add(subtag.tag)
        value = dict(uuid=uuid, regnum=regnum, reg_date=reg_date, pub_date=pub_date, title=title, authors=authors, publishers=publishers, extra=extra)
        return value

output = open("output/0-parsed-registrations.ndjson", "w")
for parsed in Parser().process_directory_tree("registrations/xml"):
        json.dump(parsed, output)
        output.write("\n")
            
