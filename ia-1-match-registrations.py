from pdb import set_trace
import re
import json
from collections import defaultdict

class Comparator(object):

    NON_ALPHANUMERIC = re.compile("[^a-z0-9]", re.I)
    MULTIPLE_SPACES = re.compile("\s+")

    def __init__(self, ia_text_file):
        self.by_exact_title = defaultdict(list)
        self.by_title_key = defaultdict(list)
        for i, raw in enumerate(open(ia_text_file)):
            data = json.loads(raw)
            title = data['title']
            title = self.normalize(title)
            key = self.title_key(title)
            self.by_exact_title[title].append(data)
            self.by_title_key[key].append(data)

    def normalize(self, text):
        if isinstance(text, list):
            if len(text) == 2:
                # title + subtitle
                text = ": ".join(text)
            else:
                # book just has variant titles.
                text = text[0]
        text = text.lower()
        text = self.NON_ALPHANUMERIC.sub(" ", text)
        text = self.MULTIPLE_SPACES.sub(" ", text)
        return text

    def title_key(self, normalized_title):
        words = [x for x in normalized_title.split(" ") if x]
        longest_words = sorted(words, key= lambda x: (-len(x), x))
        return tuple(longest_words[:2])

    def matches(self, registration_data):
        if not 'title' in registration_data:
            return
        registration_title = self.normalize(registration_data['title'])
        key = self.title_key(registration_title)
        key_matches = self.by_title_key[key]
        for ia_data in key_matches:
            quality = self.evaluate_match(ia_data, registration_data, registration_title)
            if quality > 0.6:
                yield registration_data, ia_data, quality

    def evaluate_match(self, ia_data, registration_data, registration_title):
        # The basic quality evaluation is based on title similarity.
        ia_title = self.normalize(ia_data['title'])
        title_quality = self.evaluate_titles(
            ia_title, registration_title
        )

        # A penalty is applied if the IA publication date is far away from the
        # copyright registration date.
        reg_dates = registration_data.get('reg_dates', [])

        # Assume we don't know the registration date; there will be no penalty.
        date_penalty = 0
        if reg_dates:
            ia_year = int(ia_data['year'])
            reg_date = registration_data['reg_dates'][0]
            if '_normalized' in reg_date:
                registration_year = int(reg_date['_normalized'][:4])
                date_penalty = self.evaluate_years(
                    ia_year, registration_year
                )

        # A penalty is applied if the authors are clearly divergent.
        registration_authors = registration_data.get('authors', [])
        ia_author = ia_data.get('creator')
        if registration_authors and ia_author:
            registration_author = registration_authors[0]
            author_penalty = self.evaluate_authors(
                ia_author, registration_author
            )
        else:
            # Author data is missing from registration. Ignore it.
            author_penalty = 0

        return title_quality - date_penalty - author_penalty

    def evaluate_titles(self, ia, registration):
        # Same rules as for titles, but weighted less because author data is less reliable.
        ia_words = set(ia.split())
        registration_words = set(self.normalize(registration).split())
        difference = ia_words.symmetric_difference(registration_words)
        if not ia_words and not registration_words:
            return 0 # avoid dividing by zero
        v = (1 - float(len(difference)) / (len(ia_words) + len(registration_words)))
        return v

    def evaluate_years(self, ia, registration):
        # A 10% penalty for every year of difference between the
        # registration year and the publication year according to IA.
        return abs(ia-registration) * 0.1

    def evaluate_authors(self, ia, registration):
        ia_words = set(self.normalize(ia).split())
        registration_words = set(self.normalize(registration).split())
        difference = ia_words.symmetric_difference(registration_words)
        if not ia_words and not registration_words:
            return 0 # avoid dividing by zero
        v = 1 - float(len(difference)) / (len(ia_words) + len(registration_words)) * 0.2
        return v

comparator = Comparator("output/ia-0-texts.ndjson")
for i in open("output/FINAL-not-renewed.ndjson"):
    data = json.loads(i)
    for registration, ia, quality in comparator.matches(data):
        print(quality)
        print(ia)
        print(registration)
        print("-" * 80)

