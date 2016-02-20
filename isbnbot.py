#!/usr/bin/python

import pywikibot
import isbnlib
from SPARQLWrapper import SPARQLWrapper, JSON

site = pywikibot.Site("wikidata", "wikidata")
repo = site.data_repository()

# Change this to True to actually edit Wikidata
make_actual_change = True

# Set the error page
error_page = u'User:Ash_Crow/ISBN'

def wikidata_sparql_query(query):
    """
    Queries WDQS and returns the result
    """

    sparql = SPARQLWrapper("https://query.wikidata.org/bigdata/namespace/wdq/sparql")
    sparql.setQuery(query)
    
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    return results

def get_qid(url):
    """
    Returns the Qid from the entity url
    """
    return url.split('/')[-1]

def set_mask(qid, prop, old_isbn, new_isbn):
    """
    Replaces the ISBN-10 or -13 value on Wikidata with the correct hyphenation
    """
    mask_set = 0
    if new_isbn:
        item = pywikibot.ItemPage(repo, qid)
        item_dict = item.get() #Get the item dictionary
        claim_list = item_dict["claims"][prop] # Get the claim dictionary
        for claim in claim_list:
            target = claim.getTarget()
            if target == old_isbn:
                print("Correcting {} to {}".format(old_isbn, new_isbn))
                mask_set = 1
                if make_actual_change:
                    claim.changeTarget(new_isbn)
    return mask_set

def get_isbn_list(prop):
    results = wikidata_sparql_query(
    """
    PREFIX wd: <http://www.wikidata.org/entity/>
    PREFIX wdt: <http://www.wikidata.org/prop/direct/>

    SELECT DISTINCT ?book ?isbn {{
      ?book wdt:{} ?isbn .
      }}
    """.format(prop)
    )
    return results["results"]["bindings"]

def fix_isbn(prop, isbn_version, is_isbnversion):
    """
    1. Gets the ISBNs list
    2. checks if the ISBN is valid
    2.1. If valid but not hyphenated, fixes it
    2.2. If not valid, adds it to an error list.
    """
    print(u'\n== Fixing {}s =='.format(isbn_version))
    wrong_isbn = []
    isbn_list = get_isbn_list(prop)
    wrong_hyphenation = 0
    for r in isbn_list:
        wd_isbn = r['isbn']['value']
        qid = get_qid(r['book']['value'])
        if is_isbnversion(wd_isbn):
            isbn_mask = isbnlib.mask(wd_isbn)
            if isbn_mask != wd_isbn:
                wrong_hyphenation += set_mask(qid, prop, wd_isbn, isbn_mask)
        else:
            wrong_isbn.append((qid, wd_isbn))
    
    print('{} wrong ISBN hyphenation(s) fixed.'.format(wrong_hyphenation))
    return wrong_isbn

def format_isbn_list(isbn_list, isbn_version):
    """
    Formats the  list for on-wiki publication
    """
    text = ""
    if len(isbn_list):
        isbn_list = sorted(isbn_list)
        text += u'== Wrong {}s ==\n'.format(isbn_version)
        for t in isbn_list:
            text += u'# {{{{Q|{}}}}}: {}\n'.format(t[0], t[1])
    return text

### Main program
wrong_isbn13 = fix_isbn('P212', 'ISBN-13', isbnlib.is_isbn13)
wrong_isbn10 = fix_isbn('P957', 'ISBN-10', isbnlib.is_isbn10)

### Post_treatment
error_report = ""
error_report += format_isbn_list(wrong_isbn13,'ISBN-13')
error_report += '\n' + format_isbn_list(wrong_isbn10,'ISBN-10')

if make_actual_change:
    print('\n= Error report =\n')
    page = pywikibot.Page(site, error_page)
    oldcontent = page.get()
    if oldcontent != error_report:
        page.put(error_report, "Update")

print('\n' + error_report)