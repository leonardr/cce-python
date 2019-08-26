import datetime
from dateutil import parser as date_parser
from pdb import set_trace
import internetarchive as ia
import os
import json
from model import Registration

class IAClient(object):

    FIELDS = ["identifier", "date", "year", "creator", "language", "title", "licenseurl", "call_number", "createddate", "imagecount", "stars", "avg_rating", "creatorSorter", "titleSorter", "publicdate"]

    _session = None
    
    def __init__(self, output_file):
        self.done = set()
        if os.path.exists(output_file):
            for i in open(output_file):
                data = json.loads(i)
                self.done.add(data['uuid'])
        self.out = open(output_file, "a")
                
    def process(self, input_file):
        for i in open(input_file):
            data = json.loads(i)
            self.process_data(data)
            json.dump(data, self.out)
            self.out.write("\n")
            
    def process_data(self, data):
            uuid = data['uuid']
            if uuid in self.done:
                return
            title, authors = data['title'], data['authors']
            if not title:
                return
            reg_dates = [
                date_parser.parse(x['_normalized']) for x in data['reg_dates']
            ]
            reg_dates = reg_dates or [None]
            #title = Registration._normalize_text(title)            
            search_data = dict()
            data['ia_search'] = search_data
                
            # First, try a normal title search with no date. These are
            # quick and most of the time they return nothing.
            query, results = self.search(title, None)
            search_data[query] = results
            print ("%s: %s" % (query, len(results)))
            
            # If we got results, try to zoom in by searching within 10 years of
            # the registration date.            
            if results:
                for reg_date in reg_dates:
                    query, results = self.search(title, reg_date)
                    search_data[query] = results
                    print ("%s: %s" % (query, len(results)))
                
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
    def query(cls, title, reg_date):
        query = 'title:("%s")' % title
        if reg_date:
            fmt = "%Y-%m-%d"
            interval = datetime.timedelta(days=365*5)
            before = (reg_date - interval).strftime(fmt)
            after = (reg_date + interval).strftime(fmt)
            query += " AND date:[%s TO %s]" % (before, after)
        return query
            
    @classmethod
    def _search(cls, query, *args, **kwargs):
        """Search Internet Archive items."""
        fields = cls.FIELDS
        sorts = ["date asc"]
        query = query + " and mediatype:texts"
        search = ia.search.Search(
            cls.session(), query, *args, fields=fields, sorts=sorts,
            params=dict(count=100, page=1),
            **kwargs
        )
        try:
            for i in search.iter_as_results():
                yield i
        except Exception as e:
            print(e)
            return
                
client = IAClient("output/6-ia-searches.ndjson")
client.process("output/3-registrations-in-range.ndjson")
