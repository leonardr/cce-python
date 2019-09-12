import datetime
from pdb import set_trace
from dateutil.parser import parse
import json
import sys
import internetarchive as ia

class IAClient(object):

    FIELDS = ["identifier", "date", "year", "creator", "language", "title", "licenseurl", "call_number", "createddate", "imagecount", "stars", "avg_rating", "creatorSorter", "titleSorter", "publicdate"]

    _session = None
                              
    def search(self, title, date):
        query = self.query(title, date)

        results = list(self._search(query))
        return query, results
        
    @classmethod
    def session(cls, set_to=None):
        """Keep one ArchiveSession object for the whole program.

        The session doesn't seem to keep any state so this should be
        fine.
        """
        if set_to:
            cls._session = set_to
        if not cls._session:
            cls._session = ia.session.ArchiveSession()
        return cls._session
           
    @classmethod
    def search(cls, query, cutoff_date=None, *args, **kwargs):
        """Search Internet Archive items."""
        fields = cls.FIELDS
        sorts = ["publicdate desc"]
        query = query + " and mediatype:texts"
        search = ia.search.Search(
            cls.session(), query, *args, fields=fields, sorts=sorts,
            params=dict(count=10000),
            **kwargs
        )
        for i in search.iter_as_results():
            if cutoff_date:
                public_date = parse(i['publicdate'])
                if public_date < cutoff_date:
                    # This item was made public before the cutoff
                    # date. We're all done.
                    return
            yield i

output = open("output/ia-0-texts.ndjson", "w")
client = IAClient()

# We may only want to get books that were scanned after a certain date.
if len(sys.argv) > 1:
    scan_cutoff_date = parse(sys.argv[1])
else:
    scan_cutoff_date = None

# Get 10 years of texts on either side of the cutoff just to be safe.
CUTOFF_YEAR = datetime.datetime.utcnow().year - 95 - 10
START = "%s-01-01" % CUTOFF_YEAR
FINISH = "1973-01-01"
count = 0
for i in client.search("date:[%s TO %s]" % (START, FINISH), scan_cutoff_date):
    json.dump(i, output)
    output.write("\n")
    count += 1
    # print(i.get("year"), i.get('title'), i.get("creator"))
    if not count % 1000:
        print(count)
print("Total items: %d" % count)
