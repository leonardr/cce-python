# Identifying Public Domain Works with Python

This set of Python scripts combines [copyright registration
data](https://github.com/NYPL/catalog_of_copyright_entries_project)
with [copyright renewal data](https://github.com/NYPL/cce-renewals/)
to identify works whose copyright has lapsed because a registration
was not renewed.

The data comes from datasets provided by the New York Public
Library. These datasets build on work done by [the Internet
Archive](https://archive.org/details/copyrightrecords), [Stanford
Libraries](https://exhibits.stanford.edu/copyrightrenewals), and
[Project Gutenberg](https://www.gutenberg.org/ebooks/author/141).

Thanks are due to [Sean Redmond](https://github.com/seanredmond),
[Josh Hadro](https://github.com/hadro), and Greg Cram.

# Statistics

* There are about 730,000 books where a single renewal record would be
  necessary for the work to still be in copyright today.
* Of these, about 19% definitely have that renewal record and are still
  in copyright.
* About 10% _may_ have a renewal record, but a manual inspection is
  necessary to make sure.
* About 71% definitely have no renewal record.

# Getting the Data

The best way to get this data is to generate it yourself by following
the instructions below.

If you just want a quick overview listing renewed and unrenewed books,
you can find a simplified version of these results in the
[cce-spreadsheets](https://github.com/leonardr/cce-spreadsheets)
project.

# Generating the Data

First, clone this repository and initialize the submodules. This will
bring in the raw registration and renewal data; it'll take a long
time.

```
git submodule init
git submodule update
```

Make sure the lxml XML parser is installed:

```
pip install -r requirements.txt
```

Then run the scripts, one after another:

```
python 0-parse-registrations.py
python 1-parse-renewals.py
python 2-match-renewals.py
python 3-filter.py
python 4-sort-it-out.py
```

The final script's output will look something like this:

```
Among all publications:
output/FINAL-foreign.ndjson: 193732 (12.95%)
output/FINAL-previously-published.ndjson: 77950 (5.21%)
output/FINAL-too-late.ndjson: 429869 (28.72%)
output/FINAL-too-early.ndjson: 7374 (0.49%)
output/FINAL-renewed.ndjson: 136669 (9.13%)
output/FINAL-probably-renewed.ndjson: 976 (0.07%)
output/FINAL-possibly-renewed.ndjson: 70980 (4.74%)
output/FINAL-not-renewed.ndjson: 521499 (34.85%)
output/FINAL-not-books-proper.ndjson: 36408 (2.43%)
output/FINAL-error.ndjson: 21048 (1.41%)
Total: 1496505

Among first US publications in renewal range:
output/FINAL-renewed.ndjson: 136669 (18.72%)
output/FINAL-probably-renewed.ndjson: 976 (0.13%)
output/FINAL-possibly-renewed.ndjson: 70980 (9.72%)
output/FINAL-not-renewed.ndjson: 521499 (71.43%)
Total: 730124
```

You'll see a number of large files in the `output` directory. These
files represent the work product of each step in the process. The
files you're most likely interested in are the `FINAL-` series,
mentioned above. These files represent this project's final
conclusions about which books were renewed and which weren't; which
books were published in the US and which weren't.

If you think there's been a mistake or a bad assumption somewhere in
this process, it's easy to fix. Change the corresponding script,
re-run it, then re-run the subsequent scripts to get a new set of
`FINAL-` files.

# How it works

I'll cover each script in order.

## `0-parse-registrations.py`

This script converts each copyright registration record from XML to
JSON, with a minimum of processing.

Outputs:

* `0-parsed-registrations.ndjson` - A list of registration records, each in
  JSON format.

## `1-parse-renewals.py`

This script converts each copyright renewal record from CSV to JSON,
with a minimum of processing.

Outputs:

* `1-parsed-renewals.ndjson` - A list of renewal records, each in JSON
  format.

## `2-match-renewals.py`

Match up registrations with their renewals.

Outputs:

* `2-registrations-with-renewals.ndjson` - A list of the same
  registrations from `0-parsed-registrations.ndjson`, except that
  every registration with one or more renewals has been combined with
  its renewal information.

* `2-cross-references-in-foreign-registrations.ndjson` - A list of
  non-obvious potential foreign registrations, to be used in the next
  step.

* `2-renewals-with-registrations.ndjson` - A list of renewals that
  could be matched to a registration.

* `2-renewals-with-no-registrations.ndjson` - A list of renewals that
  couldn't be matched to a registration. Some of these are renewals
  for pamphlets and such -- works other than "books proper" -- so
  although their registrations exist, they aren't in this
  dataset. Others may represent missing data or errors in matching a
  book to its registration.

## `3-filter.py`

For each registration, make a decision about the quality of the
registrations found for it, where it was published, and so on.

Outputs:

* `3-registrations-foreign.ndjson` - Registrations for foreign works,
  interim registrations (used while foreign works were looking for a
  US publisher), and registrations where the place of publication
  looks like a place outside the United States. Foreign works had
  their copyright renewed by treaty, so the absence of a renewal
  doesn't prove anything.

* `3-registrations-previously-published.ndjson` - Registrations for
  works that seem to have been previously published _in the US_. Even
  if the copyright has lapsed on this work, there may be a renewed
  copyright on a previous edition -- in that case, only the _new_
  material might be in the public domain. These need to be checked
  manually.

* `3-registrations-too-early.ndjson` - Registrations that are moot
  because they happened more than 95 years ago. These books are in the
  public domain regardless of whether the copyright was
  renewed, so renewals probably aren't relevant.

* `3-registrations-too-late.ndjson`: Copyright registrations that
  happened after 1963. These were renewed automatically, so renewals
  probably aren't relevant.

* `3-registrations-in-range.ndjson` - Registrations where the absence
  of a renewal record could make the difference between still being
  in-copyright and being in the public domain.

* `3-registrations-error.ndjson` - Contains about 20,000 registrations
  which can't be processed because they're missing essential
  information. This information might be missing from the original
  registrations, it might be missing from the transcription, or the
  information might be represented in a form that these scripts can't
  understand.

## `4-sort-it-out.py`

This simple script takes the output files generated by steps 2 and 3,
and consolidates them into a number of files:

* `FINAL-not-renewed.ndjson`: These books were almost certainly not
  renewed and are now in the public domain.
* `FINAL-probably-renewed.ndjson`: These books were probably renewed,
  but a manual check is necessary to make sure.
* `FINAL-possibly-renewed.ndjson`: These books had one or more renewal
  records, but none of them seemed like a good match. A manual check
  is necessary to see whether the renewals are legit. In particular,
  this script will count a tentative match for a book if there's a
  renewal record for _any_ book with the same title.
* `FINAL-foreign.ndjson`: These books appear to be foreign
   publications, or were mentioned in a foreign publication, so
   their renewal status probably isn't relevant.
* `FINAL-previously-published.ndjson`: These books seem to have been
  previously published _in the US_. Part or all of the work may still
  be in copyright -- it depends on whether the previous publications
  were registered, and whether the registrations were renewed. This
  must be checked manually.
* `FINAL-not-books-proper.ndjson`: These works are not "books proper"
   -- they're periodicals or something else. Their renewal status
   can only be determined once the rest of the CCE is made
   machine-readable.
* `FINAL-error.ndjson`: These books couldn't be processed because of
   errors in the data.


These files represent the final work product. At this point you can take
one or more of them and use them in your own research.

## `5-make-tsv.py`

Generates some tab-separated files that summarize the main results:

* `FINAL-not-renewed.tsv` - Works that needed a renewal to be
    under copyright today, but for which no renewal could be found.
* `FINAL-renewed.tsv` - Works  that needed a renewal to be under
    copyright today, and for which a renewal was (probably) found.
* `FINAL-foreign.tsv` - Works that appear to be foreign publications,
    for which renewal is now irrelevant. (But any of these works that
    _were_ renewed are matched to their renewals.)

# Dispositions

Each JSON object in the `FINAL-` files has a `disposition` key that
explains this script's final conclusion about its renewal status. Here
are the possible dispositions:

* `Not renewed.` - No renewal record was found, and we saw no
   complicating factors. The copyright on this book has
   almost certainly lapsed.

* `Renewed (date match).` - A renewal was found which has a date match
  with the original registration. That's almost certainly the 'real'
  renewal, and if so, this book is still in copyright.

* `Probably renewed (author match).` - There was no date match, but
  one of the renewals has the same author as the one mentioned in this
  registration. That's probably the 'real' renewal, and if so, this
  book is still in copyright.

* `Probably renewed (title match).` - There was no date or author
  match, but one of the renewals has a similar title to the one
  mentioned in the registration. That's probably the 'real' renewal,
  and if so, this book is still in copyright.

* `Possibly renewed, but none of these renewals seem like a good
   match.` - One or more renewals was found based on the registration
   ID, but the other data doesn't match. Since renewal IDs were reused
   over time, this may or may not mean that this particular
   publication had its copyright renewed. It needs to be checked
   manually.

* `Foreign publication.` - There's strong evidence that this work is a
  foreign publication. If so, then its copyright was restored by
  treaty and the presence or absence of a renewal is irrelevant.

* `Possible foreign publication -- mentioned in a registration for a
  likely foreign publication.` - This work was mentioned in the
  registration record for a foreign publication. This may mean that
  it, itself, is a foreign publication. It needs to be checked
  manually.

* `Classified with parent.` - This work was grouped beneath another
  registration, and the parent registration was removed from
  consideration -- probably because it was post-1963 or because it was
  a foreign work. In the absence of strong evidence to the contrary,
  all of its children were also removed from consideration, but they
  were given a different `disposition` in case you want to check them
  manually.

* `Not a book proper.` - This registration is for something other than
  a 'book proper' -- a pamphlet or serial, for instance. These can be
  renewed and can fall into the public domain, just like books, but we
  don't have complete data for them, so we can't draw any conclusions
  about them, and they're excluded.

* `Published before cutoff year.` - This registration happened more
  than 95 years ago, so the question of renewal is moot -- the
  copyright has expired.

* `Published after cutoff year.` - This registration happened after
  1963, so the question of renewal is moot -- the copyright was
  renewed automatically.

* `Error.` - The data associated with this registration was missing
  essential information, and it couldn't be processed.

# Matching scripts

This repository includes two more sets of scripts, which do
quick-and-dirty matching of unrenewed registrations against two large
sources of scanned books: the Internet Archive and Hathi Trust.

This scripts take `FINAL-not-renewed.ndjson` as their input, so you'll
need to run the entire main sequence first.

The final output of each script sequence is a TSV file designed to
make it easy to compare a registration against its supposed online
scan. Each supposed match is given a quality score. A higher score
indicates a higher degree of confidence that the two records are
referring to the same publication of the same book.

This scripts are less polished than the main script sequence.

## Internet Archive matching scripts

### `ia-0-list-texts.py`

This script uses the Internet Archive API to download basic
information about every scanned book in the system.

### `ia-1-match-registrations.py`

This script does its best to match copyright registrations against the
Internet Archive metadata downloaded by the previous script.

### `ia-2-output.py`

This script writes a report on likely matches in tab-separated
format.

It takes a single command-line argument: the quality cutoff
point. Quality scores range from zero to about 1.6, with higher
numbers being better. The default value of 0.2 will give you most
likely matches, but you can raise it higher or lower.

## Hathi Trust matching scripts

### `hathi-0-match-registrations.py`

This script does its best to match copyright registrations against
Hathi Trust metadata. This script takes a single command-line
argument: the path to an unzipped
[Hathifile](https://www.hathitrust.org/hathifiles).

### `hathi-1-output.py`

This script writes a report on likely matches in tab-separated
format. It works exactly the same way as `ia-1-output.py`.
