import requests
import bibtexparser
from tqdm import tqdm
from bibtexparser.bwriter import BibTexWriter

def query_crossref(title, author):
    """ Query Crossref API for DOI based on title and author. """
    query = f"{title} {author}".replace(" ", "+")
    url = f"https://api.crossref.org/works?query={query}&rows=1"

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        items = data.get('message', {}).get('items', [])
        if items:
            return items[0].get('DOI')
    except requests.RequestException as e:
        print(f"Error querying Crossref: {e}")
    
    return None

def update_bib_with_doi(input_file, output_file):
    """ Update BibTeX file entries with DOIs from Crossref. """
    processed = 0
    dois = 0

    with open(input_file) as bibtex_file:
        bib_database = bibtexparser.load(bibtex_file)

    for entry in tqdm(bib_database.entries):
        processed += 1
        title = entry.get('title', '')
        author = entry.get('author', '')
        doi = query_crossref(title, author)
        if doi:
            dois += 1
            entry['doi'] = doi

    writer = BibTexWriter()
    with open(output_file, 'w') as bibtex_file:
        bibtexparser.dump(bib_database, bibtex_file, writer)

    print(f'{processed} entries processed, {dois} DOIs retrieved ({float(dois)/float(processed):.0%})')
