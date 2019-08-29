import Levenshtein as lev
from pdb import set_trace
from model import Registration
import re
import json
from collections import defaultdict

# Ignore CCE entries if they have more than this many matches on the
# IA side.
MATCH_CUTOFF = 50

class Comparator(object):

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
        for i, raw in enumerate(open(ia_text_file)):
            data = json.loads(raw)
            license_url = data.get('licenseurl')
            if license_url and (
                    'creativecommons.org' in license_url
                    or license_url in self.ALREADY_OPEN
            ):
                # This is already open-access; don't consider it.
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
        # they're worth.
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
        ):
            # remove "catalog 1955"
            text = re.compile("%s [0-9]+" % ignorable).sub("", text)
            # remove "catalog"
            text = text.replace(ignorable, '')

        text = self.MULTIPLE_SPACES.sub(" ", text)
        text = text.strip()
        self._normalized[original] = text
        return text

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
            registration_author = registration_authors[0]
            author_penalty = self.evaluate_authors(
                ia_author, registration_author
            )
            if ' ' not in registration_title:
                # This is a book with a very short title like "Poems".
                # Author information is relatively more important here,
                author_penalty *= 2
        else:
            # Author data is missing from registration. Ignore it.
            author_penalty = 0

        return title_quality - date_penalty - author_penalty

    def _set_similarity(self, s1, s2):
        s1 = self.normalize(s1)
        s2 = self.normalize(s2)
        set1 = set(s1.split())
        set2 = set(s2.split())
        difference = set1.symmetric_difference(set2)
        if not set1 and not set2:
            # Empty sets are identical
            return 1
        return 1 - (float(len(difference)) / (len(set1) + len(set2)))

    def evaluate_titles(self, ia, registration):
        normalized_registration = self.normalize(registration)
        if not normalized_registration:
            return -1
        if ia == normalized_registration:
            # The titles are a perfect match. Give a bonus.
            return 1.2
        if normalized_registration in ia and ' ' in normalized_registration:
            # This may be a scenario where the IA book is volume 3 of 
            # the original book.
            return 1

        distance = lev.distance(ia, normalized_registration)
        longer_string = len(ia), len(normalized_registration))
        proportion_of_changes = 1-(distance / float(longer_string))
        return proportion_of_changes
        #return self._set_similarity(ia, registration)

    def evaluate_years(self, ia, registration):
        if ia == registration:
            # Exact match gets a slight negative penalty -- a bonus.
            return -0.01
        # A 15% penalty for every year of difference between the
        # registration year and the publication year according to IA.
        return abs(ia-registration) * 0.15

    def evaluate_authors(self, ia, registration):
        # We don't expect authors to match at all, so we don't
        # weight the penalty very highly
        return (1 - self._set_similarity(ia, registration)) * 0.2

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
            output_data = dict(
                quality=quality, ia=ia, cce=registration.jsonable()
            )
            json.dump(output_data, output)
            output.write("\n")
