import re
import logging
import requests
import bibtexparser
from bibtexparser.bwriter import BibTexWriter
from tqdm import tqdm
from thefuzz import fuzz

def query_crossref(title, author):
    """ Query Crossref API for DOI based on title and author. """
    query = f"{title}, {author}".replace(" ", "+")
    url = f"https://api.crossref.org/works?query.bibliographic={query}&rows=2&mailto=b.p.allen@uva.nl"

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        items = data.get('message', {}).get('items', [])
        if items: # and len(items) == 1:
            return items[0].get('title')[0], items[0].get('DOI')
    except requests.RequestException as e:
        print(f"Error querying Crossref: {e}")
    
    return None

def update_bib_with_doi(input_file, output_file):
    """ Update BibTeX file entries with DOIs from Crossref. """
    i = 0
    doi_present = 0
    exact_matches = 0
    close_matches = 0
    arxiv_matches = 0
    unmatched = 0
    arxiv_pattern = re.compile('arXiv preprint arXiv:(\d*\.\d*)')

    logging.basicConfig(filename='update_bib.log', encoding='utf-8', level=logging.INFO)

    with open(input_file) as bibtex_file:
        library = bibtexparser.load(bibtex_file)
    
    for entry in tqdm(library.entries):
        i += 1
        id = entry.get('ID', '')
        title = entry.get('title', '')
        author = entry.get('author', '')
        journal = entry.get('journal', '')
        arxiv_match = arxiv_pattern.match(journal)
        doi = entry.get('doi', '')
        if doi != '':
            logging.info(f'{i:4d}, {id}: PRESENT')
            doi_present += 1
        else:
            retrieved_title, retrieved_doi = query_crossref(title, author)
            ratio = fuzz.ratio(title.lower(), retrieved_title.lower())
            partial_ratio = fuzz.partial_ratio(title.lower(), retrieved_title.lower())
            if ratio == 100: # exact title match
                logging.info(f'{i:4d}, {id}: EXACT, ratio={ratio}, partial={partial_ratio}')
                exact_matches += 1
                entry['doi'] = retrieved_doi
            elif ratio > 90 and partial_ratio > 90: # close title match 
                logging.info(f'{i:4d}, {id}: CLOSE, ratio={ratio}, partial={partial_ratio}')
                close_matches += 1
                entry['doi'] = retrieved_doi
            elif arxiv_match:
                logging.info(f'{i:4d}, {id}: ARXIV, ratio={ratio}, partial={partial_ratio}')
                arxiv_matches += 1
                entry['doi'] = f'10.48550/arXiv.{arxiv_match.group(1)}'
            else:
                logging.warning(f'{i:4d}, {id}: UNMATCHED, ratio={ratio}, partial={partial_ratio}')
                logging.warning(f'{i:4d}, {id}: title={title}, retrieved_title={retrieved_title}')
                logging.warning(f'{i:4d}, {id}: retrieved_doi={retrieved_doi}')
                unmatched += 1

    print(f'{doi_present:3d} DOI already present ({float(doi_present)/float(i):.0%}))')
    print(f'{exact_matches:3d} exact title matches ({float(exact_matches)/float(i):.0%})')
    print(f'{close_matches:3d} close title matches ({float(close_matches)/float(i):.0%})')
    print(f'{arxiv_matches:3d} ArXiv matches ({float(arxiv_matches)/float(i):.0%})')
    print(f'{unmatched:3d} unmatched ({float(unmatched)/float(i):.0%})')
    
    writer = BibTexWriter()
    with open(output_file, 'w') as bibtex_file:
        bibtexparser.dump(library, bibtex_file, writer)
