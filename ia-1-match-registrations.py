import Levenshtein as lev
from pdb import set_trace
from model import Registration
import datetime
import re
import json
from collections import defaultdict

# Ignore CCE entries if they have more than this many matches on the
# IA side.
MATCH_CUTOFF = 50

# Only output potential matches if the quality score is above this level.
QUALITY_CUTOFF = 0

# Stuff published before this year is public domain.
CUTOFF_YEAR = datetime.datetime.today().year - 95

class Comparator(object):

    NON_ALPHABETIC = re.compile("[\W0-9]", re.I + re.UNICODE)
    NON_ALPHANUMERIC = re.compile("[\W_]", re.I + re.UNICODE)
    MULTIPLE_SPACES = re.compile("\s+")

    ALREADY_OPEN = set([
        "http://rightsstatements.org/vocab/NKC/1.0/"
    ])

    # Government authors whose work should either be already public
    # domain or whose work probably wasn't copyrighted, and whose
    # Internet Archive documents clutter up the matching code.
    IGNORE_AUTHORS = set([
        "Central Intelligence Agency"
    ])

    def __init__(self, ia_text_file):
        self.by_title_key = defaultdict(list)
        self._normalized = dict()
        self._normalized_names = dict()
        self._name_words = dict()
        for i, raw in enumerate(open(ia_text_file)):
            data = json.loads(raw)
            license_url = data.get('licenseurl')
            if license_url and (
                    'creativecommons.org' in license_url
                    or license_url in self.ALREADY_OPEN
            ):
                # This is already open-access; don't consider it.
                continue

            year = data.get('year')
            if int(year) > 1963+5 or int(year) < CUTOFF_YEAR:
                # Don't consider works published more than 5 years out
                # of the range we're considering. That's plenty of
                # time to publish the work you registered, or to register
                # the work you published.
                continue

            authors = data.get('creator', [])
            if not isinstance(authors, list):
                authors = [authors]
            if any(author in self.IGNORE_AUTHORS for author in authors):
                continue
            title = data['title']
            title = self.normalize(title)
            if not title:
                continue
            key = self.title_key(title)
            self.by_title_key[key].append(data)

    def normalize(self, text):
        if isinstance(text, list):
            if len(text) == 2:
                # title + subtitle
                text = ": ".join(text)
            else:
                # book just has variant titles.
                text = text[0]

        original = text
        if original in self._normalized:
            return self._normalized[original]
        text = text.lower()

        text = self.NON_ALPHANUMERIC.sub(" ", text)
        text = self.MULTIPLE_SPACES.sub(" ", text)

        # Remove substrings that cause more false positives than
        # they're worth. These books need to be dealt with specially.
        for ignorable in (
            'telephone directory',
            'telephone directories',                
            'annual report',
            'special report',
            'proceedings of',
            'proceedings',
            'general catalog',
            'catalog',
            'report',
            'questions and answers',
            'transactions',
            'yearbook',
            'year book',
            'selected poems',
            'poems',
            'bulletin',
            'papers',
        ):
            # remove "catalog 1955"
            text = re.compile("%s [0-9]+" % ignorable).sub("", text)
            # remove "catalog"
            text = text.replace(ignorable, '')

        # Just ignore these stopwords -- they're commonly missing or
        # duplicated.
        for ignorable in (
            ' the ',
            ' a ',
            ' an ',
        ):
            text = text.replace(ignorable, '')

        text = self.MULTIPLE_SPACES.sub(" ", text)
        text = text.strip()
        self._normalized[original] = text
        return text

    def normalize_name(self, name):
        if not name:
            return None
        # Normalize a person's name.
        original = name
        if original in self._normalized_names:
            return self._normalized_names[original]
        name = name.lower()
        name = self.NON_ALPHABETIC.sub(" ", name)
        name = self.MULTIPLE_SPACES.sub(" ", name)
        name = name.strip()
        self._normalized_names[original] = name
        return name

    def name_words(self, name):
        if not name:
            return None
        original = name
        if original in self._name_words:
            return self._name_words[original]
        words = sorted(name.split())
        self._name_words[original] = words
        return words

    def title_key(self, normalized_title):
        words = [x for x in normalized_title.split(" ") if x]
        longest_words = sorted(words, key= lambda x: (-len(x), x))
        return tuple(longest_words[:2])

    def matches(self, registration):
        if not registration.title:
            return
        registration_title = self.normalize(registration.title)
        key = self.title_key(registration_title)
        key_matches = self.by_title_key[key]
        for ia_data in key_matches:
            quality = self.evaluate_match(ia_data, registration, registration_title)
            if quality > 0:
                yield registration, ia_data, quality

    def evaluate_match(self, ia_data, registration, registration_title):
        # The basic quality evaluation is based on title similarity.
        ia_title = self.normalize(ia_data['title'])
        title_quality = self.evaluate_titles(
            ia_title, registration_title
        )

        # A penalty is applied if the IA publication date is far away from the
        # copyright registration date.
        registration_date = registration.best_guess_registration_date

        # Assume we don't know the registration date; there will be no penalty.
        date_penalty = 0
        if registration_date:
            ia_year = int(ia_data['year'])
            date_penalty = self.evaluate_years(ia_year, registration_date.year)

        # A penalty is applied if the authors are clearly divergent,
        # but it's quite common so we don't make a big deal of it.
        registration_authors = registration.authors or []
        ia_author = ia_data.get('creator')
        if registration_authors and ia_author:
            author_penalty = self.evaluate_authors(
                ia_author, registration_authors
            )
            if ' ' not in registration_title and author_penalty > 0:
                # This is a book with a very short title like "Poems".
                # Author information is relatively more important here,
                author_penalty *= 5
        else:
            # Author data is missing from registration. Ignore it.
            author_penalty = 0

        return title_quality - date_penalty - author_penalty

    def evaluate_titles(self, ia, registration):
        normalized_registration = self.normalize(registration)
        if not normalized_registration:
            return -1
        if ia == normalized_registration:
            # The titles are a perfect match. Give a bonus.
            return 1.2

        # Calculate the Levenshtein distance between the two strings,
        # as a proportion of the length of the longer string.
        #
        # This ~ the quality of the title match.

        # If you have to change half of the characters to get from one
        # string to another, that's a score of 50%, which isn't
        # "okay", it's really bad.  Multiply the distance by a
        # constant to reflect this.
        distance = lev.distance(ia, normalized_registration) * 1.5
        longer_string = max(len(ia), len(normalized_registration))
        proportional_changes = distance / float(longer_string)

        proportional_distance = 1-(proportional_changes)
        return proportional_distance

    def evaluate_years(self, ia, registration):
        if ia == registration:
            # Exact match gets a slight negative penalty -- a bonus.
            return -0.01
        # A 10% penalty for every year of difference between the
        # registration year and the publication year according to IA.
        return abs(ia-registration) * 0.10

    def evaluate_authors(self, ia_authors, registration_authors):
        if not ia_authors or not registration_authors:
            # We don't have the information necessary to match
            # up authors. No penalty.
            return 0

        # Return the smallest penalty for the given list of authors.
        if not isinstance(ia_authors, list):
            ia_authors = [ia_authors]
        if not isinstance(registration_authors, list):
            registration_authors = [registration_authors]

        penalties = []
        for ia in ia_authors:
            for ra in registration_authors:
                penalty = self.evaluate_author(ia, ra)
                if penalty is not None:
                    penalties.append(penalty)
        if not penalties:
            # We couldn't figure it out. No penalty.
            return 0

        # This will find the largest negative penalty (bonus) or the
        # smallest positive penalty.
        return min(penalties)

    def evaluate_author(self, ia_author, registration_author):
        # Determine the size of the rating penalty due to the mismatch
        # between these two authors.
        ia_author = self.normalize_name(ia_author)
        registration_author = self.normalize_name(registration_author)

        if not ia_author or not registration_author:
            # We just don't know.
            return None

        if ia_author == registration_author:
            # Exact match gets a negative penalty -- a bonus.
            return -0.25

        ia_words = self.name_words(ia_author)
        registration_words = self.name_words(registration_author)
        if ia_words == registration_words:
            # These are probably the same author. Return a negative
            # penalty -- a bonus.
            return -0.2

        distance = lev.distance(ia_author, registration_author)
        longer_string = max(len(ia_author), len(registration_author))
        proportional_changes = distance / float(longer_string)
        penalty = 1 - proportional_changes

        if penalty > 0:
            # Beyond "there are a couple of typoes" the Levenshtein
            # distance just means there's no match, so we cap the
            # penalty at a pretty low level.
            penalty = min(penalty, 0.1)
        return penalty

comparator = Comparator("output/ia-0-texts.ndjson")
output = open("output/ia-1-matched.ndjson", "w")

for filename in ("FINAL-not-renewed.ndjson", "FINAL-possibly-renewed.ndjson"):
    for i in open("output/%s" % filename):
        cce = Registration.from_json(json.loads(i))
        title = cce.title
        if not title or not comparator.normalize(title):
            continue
        matches = list(comparator.matches(cce))

        # If there are a huge number of IA matches for a CCE title,
        # penalize them -- it's probably a big mess that must be dealt
        # with separately. Give a slight boost if there's only a single
        # match.
        if len(matches) == 1:
            num_matches_coefficient = 1.1
        elif len(matches) <= MATCH_CUTOFF:
            num_matches_coefficient = 1
        else:
            num_matches_coefficient = 1-(
                len(matches) - MATCH_CUTOFF/float(MATCH_CUTOFF)
            )
        for registration, ia, quality in matches:
            quality = quality * num_matches_coefficient
            if quality <= QUALITY_CUTOFF:
                continue
            output_data = dict(
                quality=quality, ia=ia, cce=registration.jsonable()
            )
            json.dump(output_data, output)
            output.write("\n")
