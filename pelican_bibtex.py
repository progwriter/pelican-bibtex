"""
Pelican BibTeX
==============

A Pelican plugin that populates the context with a list of formatted
citations, loaded from a BibTeX file at a configurable path.

The use case for now is to generate a ``Publications'' page for academic
websites.
"""

# Author: Victor Heorhiadi <v@victorh.net>
# Based on code from: Vlad Niculae <vlad@vene.ro>
# Unlicense (see UNLICENSE for details)

import logging
from operator import itemgetter

from pelican import signals
from pybtex.style.formatting.unsrt import pages, date
from pybtex.style.template import first_of, join

logger = logging.getLogger(__name__)
__version__ = '0.2.1'


def add_publications(generator):
    """
    Populates context with a list of BibTeX publications.

    Configuration
    -------------
    generator.settings['PUBLICATIONS_SRC']:
        local path to the BibTeX file to read.

    Output
    ------
    generator.context['publications']:
        List of tuples (key, year, text, bibtex, pdf, slides, poster).
        See Readme.md for more details.
    """
    if 'PUBLICATIONS_SRC' not in generator.settings:
        return
    try:
        from StringIO import StringIO
    except ImportError:
        from io import StringIO
    try:
        from pybtex.database.input.bibtex import Parser
        from pybtex.database.output.bibtex import Writer
        from pybtex.database import BibliographyData, PybtexError
        from pybtex.backends import html
        from pybtex.style.formatting import plain, toplevel
        from pybtex.style.template import (sentence, words,
                                           optional, optional_field, field, tag)
        from pybtex.richtext import Symbol
    except ImportError:
        logger.warn('`pelican_bibtex` failed to load dependency `pybtex`')
        return

    refs_file = generator.settings['PUBLICATIONS_SRC']
    try:
        bibdata_all = Parser().parse_file(refs_file)
    except PybtexError as e:
        logger.warning('`pelican_bibtex` failed to parse file %s: %s' % (
            refs_file,
            str(e)))
        return

    class CustomStyle(plain.Style):

        def format_bold_title(self, e, which_field, as_sentence=True):
            formatted_title = tag('strong')[field(which_field)]
            if as_sentence:
                return sentence[formatted_title]
            else:
                return formatted_title

        def format_inproceedings(self, e):
            template = toplevel[
                self.format_bold_title(e, 'title'),
                Symbol('newline'),
                sentence[self.format_names('author')],
                Symbol('newline'),
                words[
                    'In',
                    sentence[
                        optional[self.format_editor(e, as_sentence=False)],
                        self.format_btitle(e, 'booktitle', as_sentence=False),
                        self.format_volume_and_series(e, as_sentence=False),
                    ],
                    self.format_address_organization_publisher_date(e),
                ],
                sentence[optional_field('note')],
                self.format_web_refs(e),
            ]
            return template.format_data(e)

        def format_article(self, e):
            volume_and_pages = first_of[
                # volume and pages, with optional issue number
                optional[
                    join[
                        field('volume'),
                        optional['(', field('number'), ')'],
                        ':', pages
                    ],
                ],
                # pages only
                words['pages', pages],
            ]
            template = toplevel[
                self.format_bold_title(e, 'title'),
                Symbol('newline'),
                self.format_names('author'),
                Symbol('newline'),
                sentence[
                    tag('em')[field('journal')],
                    optional[volume_and_pages],
                    date],
                sentence[optional_field('note')],
                self.format_web_refs(e),
            ]
            return template.format_data(e)

        def format_techreport(self, e):
            template = toplevel[
                self.format_bold_title(e, 'title'),
                Symbol('newline'),
                sentence[self.format_names('author')],
                Symbol('newline'),
                sentence[
                    words[
                        first_of[
                            optional_field('type'),
                            'Technical Report',
                        ],
                        optional_field('number'),
                    ],
                    field('institution'),
                    optional_field('address'),
                    date,
                ],
                sentence[optional_field('note')],
                self.format_web_refs(e),
            ]
            return template.format_data(e)

    publications = []

    # format entries
    my_style = CustomStyle()
    html_backend = html.Backend()
    html_backend.symbols.update({'newline': '<br>'})
    formatted_entries = my_style.format_entries(bibdata_all.entries.values())

    for formatted_entry in formatted_entries:
        key = formatted_entry.key
        entry = bibdata_all.entries[key]
        year = entry.fields.get('year')
        # This shouldn't really stay in the field dict
        # but new versions of pybtex don't support pop
        pdf = entry.fields.get('pdf', None)
        slides = entry.fields.get('slides', None)
        poster = entry.fields.get('poster', None)
        entrytype = entry.fields.get('type', None)

        # render the bibtex string for the entry
        bib_buf = StringIO()
        bibdata_this = BibliographyData(entries={key: entry})
        Writer().write_stream(bibdata_this, bib_buf)
        text = formatted_entry.text.render(html_backend)

        publications.append((key,
                             year,
                             text,
                             bib_buf.getvalue(),
                             pdf,
                             slides,
                             poster,
                             entrytype))
    publications.sort(key=itemgetter(1), reverse=True)

    generator.context['publications'] = publications


def register():
    signals.generator_init.connect(add_publications)
