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
from collections import Counter

class Processor(object):

    FOREIGN_PREFIXES = set(["AF", "AFO", "AF0"])
    INTERIM_PREFIXES = set(["AI", "AIO", "AI0"])

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
            for format in ('%Y-%m-%d', '%Y-%m', '%Y', '%d%b%y'):
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
                registration['warnings'].append(
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

    def pre_process(self, registration):
        # Consolidate multiple sets of publisher information
        # into best guess at publication date and claimants.
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
        if places:
            registration['publication_place'] = places
        registration['claimants'] = claimants
        earliest_pub_date, pub_dates = self.process_date_list(
            registration, pub_dates
        )
        earliest_reg_date, reg_dates = self.process_date_list(
            registration, registration.get('reg_date')
        )

        registration['pub_date'] = earliest_pub_date
        if not earliest_reg_date and earliest_pub_date:
            registration['warnings'].append("No registration date found; assumed earliest publication date.")
            earliest_reg_date = earliest_pub_date
        registration['reg_date'] = earliest_reg_date
        if pub_dates:
            registration['pub_dates'] = pub_dates
        if reg_dates:
            registration['reg_dates'] = reg_dates

        if places:
            registration['places'] = places

    def process(self, registration):
        registration = json.loads(i.strip())
        registration['warnings'] = []
        self.pre_process(registration)
        output = self.disposition(registration)
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
                return self.foreign

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
