# This script converts each copyright registration record from XML to
# JSON, with a minimum of processing.
import json
from pdb import set_trace
import os
from collections import defaultdict
from lxml import etree

class Parser(object):

    def __init__(self):
        self.parser = etree.XMLParser(recover=True)
        self.count = 0
        self.seen_tags = set()
        self.seen_publisher_tags = set()

    def process_directory_tree(self, path):
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
                        print(self.count)

    def process_file(self, path):
        tree = etree.parse(open(path), self.parser)
        for e in tree.xpath("//copyrightEntry"):
            for registration in self.process_registration(e):
                yield registration

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
        dates = []
        for x in results:
            packaged = self._package(x)
            if packaged:
                dates.append(packaged)
        if len(dates) == 1:
            return dates[0]
        return dates

    def process_publisher_tag(self, publisher):
        base = dict(publisher.attrib)
        date = self.date(publisher, "pubDate")
        if date:
            base['date'] = date
        place = self.xpath1(publisher, "pubPlace")
        if place:
            base['place'] = place
        claimants = []
        other = []
        for publisher_name_tag in publisher.xpath("pubName"):
            name = publisher_name_tag.text
            is_claimant = publisher_name_tag.attrib.get('claimant')
            if is_claimant == 'yes':
                destination = claimants
            else:
                destination = other
            destination.append(name)
        if claimants:
            base['claimants'] = claimants
        if other:
            base['nonclaimants'] = other
        yield base

    def process_registration(self, entry, parent=None):
        regnums = entry.attrib.get('regnum', '').split()

        uuid = entry.attrib.get('id', None)
        authors = self.xpath(entry, "author/authorName")
        notes = self.xpath(entry, 'note')
        
        reg_date = self.date(entry, "regDate") or self.date(entry, 'regdate')
        title = self.xpath1(entry, "title")
        if len(regnums) == 1:
            [regnum] = regnums
        else:
            regnum = None
        publishers = []
        for publisher_tag in entry.xpath("publisher"):
            for publisher in self.process_publisher_tag(publisher_tag):
                publishers.append(publisher)

        extra = defaultdict(list)
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

        if extra['prevPub'] or extra['prev-regNum']:
            print extra['prevPub'], extra['prev-regNum']
                
        #for subtag in entry.xpath("*"):
        #    if subtag.tag not in self.seen:
        #        print(subtag.tag)
        #        self.seen.add(subtag.tag)
        registration = dict(uuid=uuid, regnum=regnum, regnums=regnums, reg_date=reg_date, title=title, authors=authors, publishers=publishers, extra=extra, notes=notes)

        if parent:
            registration['parent'] = dict(
                uuid=parent['uuid'],
                regnum=parent['regnum'],
                reg_date=parent['reg_date'],
                authors=parent['authors'],
                publishers=parent['publishers'],
                title=parent['title'],
            )
            
        children = []
        for child_tag in entry.xpath("additionalEntry"):
            for child_registration in self.process_registration(child_tag, registration):
                children.append(child_registration)
        registration['children'] = children

        yield registration
        for child in children:
                yield child

if not os.path.exists("output"):
    os.mkdir("output")
output = open("output/0-parsed-registrations.ndjson", "w")
for parsed in Parser().process_directory_tree("registrations/xml"):
        json.dump(parsed, output)
        output.write("\n")

