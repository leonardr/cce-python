from pdb import set_trace
import datetime
from dateutil import parser as date_parser
import json
import re

class XMLParser(object):
    """Helper methods for running XPath queries."""

    @classmethod
    def xpath(cls, tag, path):
        """Find all child tags matching `path` and return a list of all
        non-empty text nodes within.
        """
        results = tag.xpath(path)
        return [x.text for x in results if x.text]

    @classmethod
    def xpath1(self, tag, path):
        """Find a single child tag matching `path` and return
        its text node, if any.
        """
        results = tag.xpath(path)
        if not results:
            return None
        return results[0].text

    @classmethod
    def _package(cls, tag):
        """Package a tag as a dictionary.

        The dictionary consists of the attributes of the tag, with
        the text node as a special attribute called '_text'.
        """
        attrib = dict(tag.attrib)
        attrib['_text'] = tag.text
        return attrib

    @classmethod
    def date(cls, tag, path, allow_multiple=False, warnings=None):
        results = tag.xpath(path)
        if not results:
            if allow_multiple:
                return []
            else:
                return None
        dates = []
        for date_tag in results:
            processed = cls._parse_date_tag(date_tag, warnings)
            if processed:
                dates.append(processed)
        if allow_multiple:
            return dates

        # Only one date is allowed.
        if len(dates) > 1:
            raise Exception("Found multiple dates: %r" % dates)
        return dates[0]

    @classmethod
    def _parse_date_tag(cls, date_tag, warnings):
        """Turn a tag containing date information into a dictionary.

        :return: A dictionary with '_text' containing the raw date
                 string and '_normalized' containing the date normalized
                 in %Y-%m-%d format (if it could be parsed).
        """
        data = cls._package(date_tag)
        raw = data.get('date') or date_tag.text
        data['_text'] = raw
        return data

    @classmethod
    def _parse_date(cls, raw, warnings=None):
        parsed = None
        # Try to parse the full date, and parse just the year and
        # month if that fails. In most cases that's all we really
        # need.
        attempts = [raw]
        if len(raw) > 7 and raw[7] == '-':
            attempts.append(raw[:7])
        for attempt in attempts:
            try:
                parsed = date_parser.parse(attempt)
                if not parsed:
                    continue
                if parsed.year > 2000 and len(raw) in (6, 7):
                    # A very common date format is '19Jun58',
                    # which date_parser parses as 2059. Subtract
                    # 100 years and we're in business.
                    parsed = datetime.datetime(
                        parsed.year-100, parsed.month, parsed.day
                    )
                if parsed.year > 1995 or parsed.year < 1900:
                    # This is most likely a totally incorrect date, or
                    # not a date at all.
                    parsed = None
                else:
                    break
            except ValueError, e:
                continue
        if not parsed and warnings is not None:
            msg = "Could not parse date %s" % raw
            warnings.append(msg)
        return parsed

class Publisher(XMLParser):
    """Represents information about the publisher(s) associated with a
    Registration, and the time and circumstances of publication.
    """
    def __init__(self, dates, places, claimants, nonclaimants, extra):
        self.dates = dates
        self.places = places
        self.claimants = claimants
        self.nonclaimants = nonclaimants
        self.extra = extra

    def jsonable(self):
        return dict(
            dates=self.dates,
            places=self.places,
            claimants=self.claimants,
            nonclaimants=self.nonclaimants,
            extra=self.extra
        )

    @classmethod
    def from_json(cls, data):
        return cls(**data)

    @classmethod
    def from_tag(cls, publisher, warnings=None):
        """Parse publisher information from a <publisher> tag."""
        extra = dict(publisher.attrib)
        pub_dates = cls.date(
            publisher, "pubDate", allow_multiple=True,
            warnings=warnings
        )
        places = cls.xpath(publisher, "pubPlace")
        claimants = []
        nonclaimants = []
        for publisher_name_tag in publisher.xpath("pubName"):
            name = publisher_name_tag.text
            is_claimant = publisher_name_tag.attrib.get('claimant')
            if is_claimant == 'yes':
                destination = claimants
            else:
                destination = nonclaimants
            destination.append(name)
        return cls(pub_dates, places, claimants, nonclaimants, extra)


class Places(object):
    """A helper class that knows about places in the real world."""

    # Big foreign publishing cities that are sometimes mentioned
    # without the context of the country.
    FOREIGN_CITIES = set(
        [
            'Paris',
            'London',
            'Berlin',
        ]
    )

    def __init__(self):
        self.foreign_countries = set()
        self.foreign_country_endings = set()
        for i in json.load(open("countries.json"))['countries']:
            if i not in ("United States Of America", "Georgia"):
                self.foreign_countries.add(i)
                self.foreign_country_endings.add(", " + i)
        for name in ('England', 'Scotland'):
            self.foreign_countries.add(i)
            self.foreign_country_endings.add(", " + i)

    def is_foreign(self, place):
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
        return False


class Registration(XMLParser):

    PLACES = Places()

    def __init__(
            self, uuid=None, regnums=None, reg_dates=None,
            title=None, authors=None, notes=None,
            publishers=None, previous_regnums=None, previous_publications=None,
            extra=None, parent=None, children=None,
            xrefs=None, _is_foreign=None, warnings=None,
            error=None, disposition=None, renewals=None
    ):
        self.uuid = uuid
        self.regnums = [x for x in regnums if x] or []
        self.reg_dates = reg_dates or []
        self.title = title
        self.authors = authors or []
        self.notes = notes or []
        self.publishers = publishers or []
        self.previous_regnums = previous_regnums or []
        self.previous_publications = previous_publications or []
        self.extra = extra or {}
        self.parent = parent
        self.children = children or []
        self.xrefs = xrefs or []
        self.warnings = warnings or []
        self.error = error
        self.disposition = disposition
        self.renewals = renewals
        
    def jsonable(self, include_others=True):
        data = dict(
            uuid=self.uuid,
            regnums=self.regnums,
            reg_dates=self.reg_dates,
            title=self.title,
            authors=self.authors,
            notes=self.notes,
            publishers=[self._json(p) for p in self.publishers],
            previous_regnums=self.previous_regnums,
            previous_publications=self.previous_publications,
            extra=self.extra,
            warnings=self.warnings,
            error=self.error,
            disposition=self.disposition,
        )
        if self.renewals:
            data['renewals'] = [self._json(x) for x in self.renewals]
        if include_others and self.parent:
            parent = self._json(self.parent, include_others=False)
        else:
            parent = None
        data['parent'] = parent
        if include_others:
            xrefs = [
                self._json(xref, include_others=False)
                for xref in self.xrefs
            ]
            children = [
                self._json(child, include_others=False)
                for child in self.children
            ]
        else:
            children = []
            xrefs = []
        data['children'] = children
        data['xrefs'] = xrefs
        return data

    def _json(self, x, **kwargs):
        if isinstance(x, dict):
            return x
        return x.jsonable(**kwargs)

    @classmethod
    def from_json(cls, data):
        return cls(**data)

    @classmethod
    def from_tag(cls, tag, parent=None, include_extra=True):

        """Turn a <copyrightEntry> or <additionalEntry> tag into a sequence of
        Registration objects.

        :param tag: An etree Element representing an XML tag.

        :param parent: If `tag` is an <additionalEntry> tag, the
               Registration created for the parent <copyrightEntry>
               tag. Otherwise, None.

        :param include_extra: Parse out information that's not currently
               used in to determine renewal status.

        :yield: A single Registration for an <additionalEntry> tag;
                one or more for a <copyrightEntry> tag.
        """
        warnings = []
        uuid = tag.attrib.get('id', None)
        regnums = tag.attrib.get('regnum', '').split()
        reg_dates = cls.date(
            tag, "regDate", allow_multiple=True, warnings=warnings,
        ) + cls.date(
            tag, 'regdate', allow_multiple=True, warnings=warnings,
        )
        title = cls.xpath1(tag, "title")
        authors = cls.xpath(tag, "author/authorName")
        notes = cls.xpath(tag, 'note')
        publishers = [
            Publisher.from_tag(publisher_tag, warnings)
            for publisher_tag in tag.xpath("publisher")
        ]
        previous_regnums = cls.xpath(tag, "prev-regNum")
        previous_publications = cls.xpath(tag, "prevPub")

        # We'll parse out these items and store the data, but they're
        # not currently important to the clearance process.
        extra = {}
        if include_extra:
            for name in [
                'edition', 'noticedate', 'series', 'newMatterClaimed',
                'vol', 'desc', 'pubDate', 'volumes',
                'claimant', 'copies', 'affDate', 'lccn', 'copyDate', 'role',
                'page', 'copyDate',
            ]:
                tags = []
                for extra_tag in tag.xpath(name):
                    tags.append(cls._package(extra_tag))
                if tags:
                    extra[name] = tags
               
        registration = Registration(
            uuid, regnums, reg_dates, title, authors, notes,
            publishers, previous_regnums, previous_publications,
            extra, parent, warnings=warnings
        )
            
        children = []
        for child_tag in tag.xpath("additionalEntry"):
            for child_registration in cls.from_tag(child_tag, registration):
                registration.children.append(child_registration)

        yield registration
        for child in children:
                yield child

    FOREIGN_PREFIXES = set(["AF", "AFO", "AF0"])
    INTERIM_PREFIXES = set(["AI", "AIO", "AI0"])

    PREVIOUSLY_PUBLISHED_ABROAD = re.compile("[pd]u[bt][.,]? abroad", re.I)
    
    def _regnum_is_foreign(self, regnum):
        if any(regnum.startswith(x) for x in self.FOREIGN_PREFIXES):
            self.warnings.append(
                "Regnum '%s' indicates a foreign registration." % regnum
            )
            return True
        if any(regnum.startswith(x) for x in self.INTERIM_PREFIXES):
            self.warnings.append(
                "Regnum '%s' indicates an interim (and foreign) registration." % regnum
            )
            return True

    @property
    def is_foreign(self):
        """See if it's possible to determine that this registration is for a
        foreign work, based solely on the metadata.
        """
        # Maybe the registration is a foreign or interim registration.
        for regnum in self.regnums:
            if self._regnum_is_foreign(regnum):
                return True

        # Maybe there's a previous registration number that's
        # a foreign or interim registration.
        for prev_regnum in self.previous_regnums:
            if self._regnum_is_foreign(prev_regnum):
                return True

        # Maybe the 'previous publication' information says that
        # the work was previously published abroad, without giving
        # a specific registration number.
        for previous_publication in self.previous_publications:
            if self.PREVIOUSLY_PUBLISHED_ABROAD.search(previous_publication):
                self.warnings.append("Previous publication %r indicates work was previously published abroad." % previous_publication)
                return True
            if 'AI.' in previous_publication or 'AI-' in previous_publication:
                self.warnings.append(
                    "Previous publication '%s' seems to mention an interim registration." % previous_publication
                )
                return True

        # Maybe the book was published in a foreign place.
        for place in self.places:
            if self.PLACES.is_foreign(place):
                self.warnings.append(
                    "Publication place '%s' looks foreign." % place
                )
                return True
       
            
        # TODO: check edition for keywords like '1st American ed.'

        # Maybe a previous publication mentions certain keywords. These
        # are not terribly reliable, so we run this test last.
        for previous_publication in self.previous_publications:
            for keyword in ['abroad']:
                if keyword in previous_publication.lower():
                    self.warnings.append(
                        "Previous publication %r mentions the keyword '%s', which indicates this _may_ be a foreign publication." % (
                            keyword, previous_publication
                        )
                    )
                return True
        return False

    DATE_AND_NUMBER_XREF = re.compile("([0-9]{,2}[A-Z][a-z]{2}[0-9]{2})[;,] ?(A[A-Z]?[0-9-]+)")

    NUMBER_AND_DATE_XREF = re.compile("(A[A-Z]?[0-9-]+)[;,] ?([0-9]{,2}[A-Z][a-z]{2}[0-9]{2})")
    POSSIBLE_NUMBER_XREF = re.compile("(A{1,2}[0-9-]{4,})")

    @property
    def places(self):
        """All places mentioned in the context of where this book was published."""
        for pub in self.publishers:
            for place in pub['places']:
                yield place

    def parse_xrefs(self):
        """Look for cross-references to other registrations in the 'notes'
        field of this registration.

        :yield: A sequence of Registration objects.
        """
        if self.notes:
            for note in self.notes:
                xref = self._xref(note)
                if xref:
                    yield xref

    def _xref(self, note):
        if not note:
            return
        regnum = date = None
        for r in [self.DATE_AND_NUMBER_XREF,
                  self.NUMBER_AND_DATE_XREF]:
            m1 = r.search(note)
            if m1:
                date, regnum = m1.groups()
                date = self._parse_date(date, self.warnings)
                if date:
                    date = date.isoformat()[:10]
                    break
        else:
            m2 = self.POSSIBLE_NUMBER_XREF.search(note)
            if m2:
                [regnum] = m2.groups()
        if not regnum:
            return None
        regnum = regnum.replace("-", "")

        if date:
            reg_dates = [date]
        else:
            reg_dates = []
        return Registration(
            regnums=[regnum], reg_dates=reg_dates, notes=[note]
        )

    def _normalize_date(self, date):
        if not date:
            return None
        parsed = self._parse_date(date['_text'], self.warnings)
        if parsed:
            date['_normalized'] = parsed.isoformat()[:10]
        else:
            date['_error'] =  "Could not parse date."
        return parsed

    @property
    def registration_dates(self):
        for d in self.reg_dates:
            parsed = self._normalize_date(d)
            if parsed:
                yield parsed

    @property
    def publication_dates(self):
        for p in self.publishers:
            for d in p['dates']:
                parsed = self._normalize_date(d)
                if parsed:
                    yield parsed

    @property
    def best_guess_registration_date(self):
        reg = list(self.registration_dates)
        if reg:
            return min(reg)
        pub = list(self.publication_dates)
        if pub:
            return min(pub)

    NOT_ALPHA = re.compile("[^0-9A-Z ]", re.I)
    def _normalize_text(self, v):
        if not v:
            return ""
        return self.NOT_ALPHA.sub("", v).lower()

    def words_match(self, t1, t2, quotient=0.75):
        if not t1 or not t2:
            return False

        norm1 = self._normalize_text(t1)
        norm2 = self._normalize_text(t2)
        if norm1 == norm2:
            return True
        w1 = norm1.split()
        w2 = norm2.split()
        intersection = set(w1).intersection(w2)
        bigger = max(len(w1), len(w2))
        if len(intersection) > (bigger * quotient):
            return True
        return False
        
    def author_match(self, other_author):
        if not other_author:
            return False
        for a in self.authors:
            if self.words_match(a, other_author):
                return True
        return False
            
    def title_match(self, other_title):
        if self.words_match(self.title, other_title):
            return True
        return False
        
class Renewal(object):

    def __init__(self, **data):
        self.data = data

    def jsonable(self):
        return self.data

    def __getattr__(self, k):
        return self.data[k]

    @classmethod
    def from_dict(cls, d):
        uuid = d['entry_id']
        regnum = d['oreg']
        reg_date = d['odat']
        author = d.get('auth', None)
        title = d.get('titl', None) or d.get('title', None)
        renewal_id = d['id']
        renewal_date = d.get('dreg', None)
        new_matter = d['new_matter']
        see_also_renewal = [x for x in d['see_also_ren'].split("|") if x]
        see_also_registration = [x for x in d['see_also_reg'].split("|") if x]
        return cls(
            uuid=uuid, regnum=regnum, reg_date=reg_date,
            renewal_id=renewal_id, renewal_date=renewal_date,
            author=author, title=title, new_matter=new_matter,
            see_also_renewal=see_also_renewal,
            see_also_registration=see_also_registration
        )
