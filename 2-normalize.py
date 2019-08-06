# Remove from consideration:
# * Foreign and interim registrations, which are not subject to the
#   renewal requirements.
# * Registrations for books that were published more than 95 years ago
#   -- those are already in the public domain.
# * Registrations for post-1964 books.
# * Registrations with no ID.
#
# Normalize the data so that a best guess at registration date is
# easily accesible.

from pdb import set_trace
import json
import datetime
import re
from collections import Counter

class Processor(object):

    FOREIGN_PREFIXES = set(["AF", "AFO", "AF0"])
    INTERIM_PREFIXES = set(["AI", "AIO", "AI0"])

    DATE_AND_NUMBER_XREF = re.compile("([0-9]{,2}[A-Z][a-z]{2}[0-9]{2})[;,] ([A-Z]{1,2}[0-9-]+)")
    POSSIBLE_NUMBER_XREF = re.compile("([A-Z]{1,2}[0-9-]{4,})")
    
    # Big foreign publishing cities that are sometimes mentioned
    # without the context of the country.
    FOREIGN_CITIES = set(
        [
            'Paris',
            'London',
            'Berlin',
        ]
    )

    # Before this year, everything published in the US is public
    # domain.
    CUTOFF_YEAR = datetime.datetime.utcnow().year - 95

    def __init__(self):
        self.interim = open("output/2-registrations-interim.ndjson", "w")
        self.foreign = open("output/2-registrations-foreign.ndjson", "w")
        self.too_old = open("output/2-registrations-before-%s.ndjson" % self.CUTOFF_YEAR, "w")
        self.too_new = open("output/2-registrations-after-1963.ndjson", "w")
        self.usable = open("output/2-registrations-in-range.ndjson", "w")
        self.errors = open("output/2-registrations-error.ndjson", "w")
        self.cross_references_in_foreign_registrations = open(
            "output/2-cross-references-in-foreign-registrations.ndjson", "w"
        )
        self.cross_references_from_renewals = json.load(open(
            "output/1-renewal-cross-references.json"
        ))
        
        self.places = Counter()

        self.foreign_countries = set()
        self.foreign_country_endings = set()
        for i in json.load(open("countries.json"))['countries']:
            if i not in ("United States Of America", "Georgia"):
                self.foreign_countries.add(i)
                self.foreign_country_endings.add(", " + i)
        for name in ('England', 'Scotland'):
            self.foreign_countries.add(i)
            self.foreign_country_endings.add(", " + i)

    def parse_date(self, date):
        if not date:
            return None
        if isinstance(date, list):
            dates = date
        else:
            dates = [date]
        parsed_dates = []
        for _date in dates:
            if isinstance(_date, dict):
                _date = _date['date']
            for format in ('%Y-%m-%d', '%Y-%m', '%Y', '%d%b%y', '%b%y'):
                try:
                    parsed = datetime.datetime.strptime(_date, format)
                    parsed_dates.append(parsed)
                except:
                    continue
        if not parsed_dates:
            return None
        if len(parsed_dates) == 1 or len(set(parsed_dates)) == 1:
            return parsed_dates[0]
        raise Exception("Multiple dates? in %r" % date)

    def place_is_foreign(self, place):
        """Make a best guess as to whether a place name is in
        another country.
        """
        if place.endswith('.'):
            place = place[:1]
        if place in self.FOREIGN_CITIES:
            return True
        if place in self.foreign_countries:
            return True
        if any(place.endswith(x) for x in self.foreign_country_endings):
            return True

    def process_date_list(self, registration, dates):
        # Parse all dates, record any parsing failures.
        # Return (earliest date, all dates if more thna one)
        if not dates:
            return None, []
        if not isinstance(dates, list):
            dates = [dates]
        parsed_dates = []
        for date in dates:
            if isinstance(date, dict):
                date = date.get('date', date.get('_text', None))
            parsed = self.parse_date(date)
            if parsed:
                parsed_dates.append(parsed)
            else:
                registration.setdefault('warnings', []).append(
                    "Could not parse date %r" % date
                )

        formatted = [x.isoformat()[:10] for x in parsed_dates]
        if formatted:
            earliest = min(formatted)
        else:
            earliest = None
        if len(formatted) < 2:
            formatted = None
        return earliest, formatted

    def _publisher_info(self, registration):
        pub_dates = []
        claimants = []
        places = []
        for info in registration.get('publishers', []):
            this_claimants = info.get('claimants', [])
            claimants.extend(this_claimants)
            date = info.get('date')
            if isinstance(date, dict):
                date = [date]
            if date:
                for _date in date:
                    pub_dates.append(_date)
            place = info.get('place')
            if place:
                places.append(place)
        return pub_dates, claimants, places
                
    def pre_process(self, registration):
        # Consolidate multiple sets of publisher information
        # into best guess at publication date and claimants.
        pub_dates, claimants, places = self._publisher_info(registration)
        if 'parent' in registration:
            registration['parent'] = self.pre_process(registration['parent'])
            parent_reg_date = registration['parent']['reg_date']            
            parent_pub_dates, parent_claimants, parent_places = self._publisher_info(
                registration['parent']
            )
        else:
            parent_reg_date = None
            parent_pub_dates = []
            parent_claimants = []
            parent_places = []
        if places or parent_places:
            registration['publication_place'] = places + parent_places
        pub_dates = pub_dates + parent_pub_dates
        reg_date = registration.get('reg_date') or parent_reg_date
        registration['claimants'] = claimants
        earliest_pub_date, pub_dates = self.process_date_list(
            registration, pub_dates,
        )
        earliest_reg_date, reg_dates = self.process_date_list(
            registration, registration.get('reg_date')
        )

        registration['pub_date'] = earliest_pub_date
        if not earliest_reg_date and earliest_pub_date:
            registration.setdefault('warnings',[]).append("No registration date found; assumed earliest publication date.")
            earliest_reg_date = earliest_pub_date
        registration['reg_date'] = earliest_reg_date
        if pub_dates:
            registration['pub_dates'] = pub_dates
        if reg_dates:
            registration['reg_dates'] = reg_dates

        if places:
            registration['places'] = places
        xrefs = list(self.xrefs(registration))
        if xrefs:
            registration['xrefs'] = xrefs
        return registration

    def xrefs(self, registration):
        """Find other registrations referred to in the notes of this registration."""
        if not 'notes' in registration:
            return
        for note in registration['notes']:
            xref = self._xref(note)
            if xref:
                yield xref

    def _xref(self, note):
        if not note:
            return
        regnum = date = None
        m1 = self.DATE_AND_NUMBER_XREF.search(note)
        if m1:
            date, regnum = m1.groups()
            date = self.parse_date(date)
            if date:
                if date.year > 2000:
                    date = datetime.datetime(date.year - 100, date.month, date.day)
                date = date.isoformat()[:10]
        else:
            m2 = self.POSSIBLE_NUMBER_XREF.search(note)
            if m2:
                [regnum] = m2.groups()
        if not regnum:
            return None
        regnum = regnum.replace("-", "")
        return dict(regnum=regnum, reg_date=date, note=note)
    
    def process(self, registration):
        registration = json.loads(i.strip())
        registration['warnings'] = []
        self.pre_process(registration)
        output = self.disposition(registration)
        if output == self.foreign:
            # Write all references from this registration to the list of
            # foreign cross-references. This may provide evidence that some other
            # registration is for a book with an original foreign publication.
            for xref in registration.get('xrefs', []):
                xref = dict(xref)
                xref['original_registration'] = registration
                json.dump(xref, self.cross_references_in_foreign_registrations)
                self.cross_references_in_foreign_registrations.write("\n")
        if not registration['warnings']:
            del registration['warnings']
        json.dump(registration, output)
        output.write("\n")

    def error(self, registration, error):
        registration['error'] = error
        return self.errors

    def disposition(self, registration):
        regnums = registration.get('regnums')
        if not regnums:
            return self.error(registration, "No registration number")
        for regnum in regnums:
            if any(regnum.startswith(x) for x in self.FOREIGN_PREFIXES):
                return self.foreign
            if any(regnum.startswith(x) for x in self.INTERIM_PREFIXES):
                return self.interim
        places = registration.get('places', [])
        for place in places:
            if self.place_is_foreign(place):
                for cross_reference in self.cross_references_from_renewals.get(
                        regnum, []
                ):
                    # All regnums mentioned in renewals for this regnum are suspect.
                    # All publications with those regnums need to be checked to make
                    # sure they're not foreign.
                    xref = dict(
                        regnum=cross_reference,
                        note="Mentioned in a renewal record for %s, which turned out to be a foreign publication." % regnum
                    )
                    json.dump(xref, self.cross_references_in_foreign_registrations)
                    self.cross_references_in_foreign_registrations.write("\n")

                return self.foreign
            else:
                for cross_reference in self.cross_references_from_renewals.get(
                        regnum, []
                ):
                    print("%s was mentioned in a renewal record for %s, but it's cool, because %s wasn't a foreign publication." % (cross_reference, regnum))

        for place in places:
            self.places[place] += 1

        reg_date = registration['reg_date']
        if not reg_date:
            return self.error(
                registration, "No registration or publication date."
            )

        parsed = datetime.datetime.strptime(reg_date, '%Y-%m-%d')
        if parsed.year < self.CUTOFF_YEAR:
            return self.too_old
        if parsed.year > 1963:
            return self.too_new

        return self.usable

processor = Processor()
for i in open("output/0-parsed-registrations.ndjson"):
    processor.process(i)
