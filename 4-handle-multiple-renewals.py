# For works with multiple renewals, see if any of the renewals actually
# look like they belong to the book.
from pdb import set_trace
from collections import defaultdict
import json
import re

class Evaluator(object):

    not_alpha = re.compile("[^0-9A-Z ]", re.I)
    
    def __init__(self, data):
        self.registration = data
        title = data['title']
        self.normalized_title = self.normalize(title)
        self.title_words = self.normalized_title.split()
        self.normalized_authors = list(
            set([self.normalize(x) for x in data['authors']])
        )
        self.renewals = data['renewals']
        self.renewal_authors = [self.normalize(x['author']) for x in self.renewals]
        self.renewal_titles = [self.normalize(x['title']) for x in self.renewals]
        
    def normalize(self, v):
        if not v:
            return ""
        return self.not_alpha.sub("", v).lower()

    @property
    def evaluation(self):
        return dict(
            authors=self.normalized_authors,
            title=self.normalized_title,
            renewal_authors=self.renewal_authors,
            renewal_titles=self.renewal_titles
        )
    
    @property
    def renewal(self):
        for renewal in self.renewals:
            if self.date_match(renewal):
                # This is very reliable -- it's just that there were
                # extra renewals in the way.
                return renewal, "Renewed (date match)."
            if self.author_match(renewal):
                return renewal, "Probably renewed (author match)."
            elif self.title_match(renewal):
                return renewal, "Probably renewed (title match)."

        return None, "Probably not renewed (could not confirm match)."

    def date_match(self, renewal):
        if renewal['reg_date'] == self.registration['reg_date']:
            return True
        return False
    
    def author_match(self, renewal):
        author = renewal['author']
        if not author:
            return False
        if self.normalize(author) in self.normalized_authors:
            set_trace()
            return True
        return False
        
    def title_match(self, renewal):
        title = renewal['title']
        if not title:
            return False

        # Check for a perfect title match.
        normalized_renewal_title = self.normalize(title)
        if normalized_renewal_title == self.normalized_title:
            return True

        # Check for a match of 75% of the words in the title.
        renewal_title_words = normalized_renewal_title.split()
        intersection = set(self.title_words).intersection(renewal_title_words)
        bigger_title = max(len(renewal_title_words), len(self.title_words))
        if len(intersection) > (bigger_title * 0.75):
            return True
        return False
        
probably_renewed = open("output/4-probably-renewed.ndjson", "w")
probably_not_renewed = open("output/4-probably-not-renewed.ndjson", "w")
        
for i in open("output/3-registrations-not-yet-matched.ndjson"):
    data = json.loads(i)
    eval = Evaluator(data)
    data['evaluation'] = eval.evaluation
    likely_renewal, disposition = eval.renewal
    if likely_renewal:
        output = probably_renewed
        data['renewals'] = [likely_renewal]
    else:
        output = probably_not_renewed
    data['disposition'] = disposition
    json.dump(data, output)
    output.write("\n")
    
