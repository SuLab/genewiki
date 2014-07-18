from django.conf import settings

import sys, json, urllib, re

from genewiki.wiki.textutils import ProteinBox
from genewiki.bio.uniprot import uniprot_acc_for_entrez_id
from genewiki.bio.rcsb import pdbs_for_uniprot
import mygene

MOUSE_TAXON_ID = 10090

def getJson(url):

    ufile = None
    try:
        ufile = urllib.urlopen(url)
        contents = ufile.read()
        if not isinstance(contents, unicode):
            contents = contents.decode('utf-8')
        return json.loads(contents)
    except IOError as e:
        print("Network error: are you connected to the internet?")
        raise e
    finally:
        ufile.close()

def get(json, key):
    """
      Provides the element at the specified key in the given JSON.
      If the json object is a dict and the key is valid, returns that element.
      If it's a list and has an element at json[0], it calls itself with json[0]
      as its first argument (recursive).
      If it's a unicode or normal string, it returns the unicode representation.
      In all other cases, it returns an empty unicode string.

      Example:
      To access json['refseq']['protein'][0], you would write:
      get(get(get(root, 'refseq'), 'protein'), 0))

      Arguments:
      - `json`: The JSON tree to parse from
      - `node`: The top-level node to attempt to return.
    """

    result = u''
    if isinstance(json, dict):
        result = json[key] if key in json else u''
    elif isinstance(json, list):
        result = get(json[0], key) if (len(json)>0) else u''
    elif isinstance(json, unicode):
        result = json
    elif isinstance(json, str):
        result = json.decode('utf8')
    return result


def parse_go_category(entry):

    # single term:
    if 'term' in entry:
        return {entry['id']:entry['term']}
    # multiple terms
    else:
      terms = []
      results = []
      for x in entry:
        if x['term'] not in terms:
          results.append( {x['id']:x['term']} )
        terms.append(x['term'])
      return results


def _queryUniprot(entrez):
    return uniprot_acc_for_entrez_id(entrez)


def findReviewedUniprotEntry(entries, entrez):
    """
      Attempts to return the first reviewed entry in a given dict of dbname:id
      pairs for a gene's UniProt entries.
      If a reviewed entry is not found, it attempts to query Uniprot directly for one.
      If this still is unsuccessful, it returns one from TrEMBL at random.

      Arguments:
      - `entries`: a dict of entries, e.g {'Swiss-Prot':'12345', 'TrEMBL':'67890'}
    """
    if not isinstance(entries, dict) and not entrez:
        return u''
    elif entrez:
        return _queryUniprot(entrez)

    if 'Swiss-Prot' in entries:
        entry = entries['Swiss-Prot']
    else:
        entry = entries['TrEMBL']

    if isinstance(entry, list):
        for acc in entry:
            if uniprot.isReviewed(acc): return acc
        # if no reviewed entries, check Uniprot directly
        canonical = _queryUniprot(entrez)
        if canonical: return canonical
        else: return entry[0]
    else:
        canonical = _queryUniprot(entrez)
        if canonical: return canonical
        else: return entry


def get_homolog(gene, taxon, json):
    """
      Returns the homologous gene for a given gene in a given taxon.

      Arguments:
      - `gene`:  the original gene
      - `taxon`: the taxon of the species in which to find a homolog
      - `json`:  the mygene.info json document for original gene
    """
    homologs = get(get(json, 'homologene'), 'genes')
    # isolate our particular taxon (returns [[taxon, gene]])
    if homologs:
        pair  = filter(lambda x: x[0]==taxon, homologs)
        if pair:
            return pair[0][1]
        else: return None
    else: return None


def get_json_documents(entrez):
    """
      Returns the three JSON documents needed to construct a ProteinBox.
      Dict structure: {gene:json, meta:json, homolog:json}
      For use as a helper method for the parse_json() method.

      Arguments:
      - `entrez`: human gene entrez id
    """
    gene_json = getJson( settings.MYGENE_BASE + entrez )
    meta_json = getJson( settings.MYGENE_META )

    homolog = get_homolog(entrez, MOUSE_TAXON_ID, gene_json)
    homolog_json = getJson( settings.MYGENE_BASE + str(homolog) ) if homolog else None

    return {'gene_json':gene_json, 'meta_json':meta_json, 'homolog_json':homolog_json}


def parse_json(gene_json, meta_json, homolog_json):
    """
      Returns a ProteinBox based on the provided JSON documents.

      Arguments:
      - `json_document`: mygene.info json document for any given gene
      - `meta_json`: mygene.info metadata document
      - `homolog_json`: mygene.info json document for corresponding mouse gene
    """
    box = ProteinBox()
    root = gene_json
    meta = meta_json

    name = get(root, 'name')
    if re.match(r'\w', name):
        name = name[0].capitalize()+name[1:]
    box.setField("Name", name)

    entrez = get(root, 'entrezgene')
    box.setField("Hs_EntrezGene", entrez)

    uniprot = findReviewedUniprotEntry(get(root, 'uniprot'), entrez)
    box.setField("Hs_Uniprot", uniprot)

    # Currently mygene.info uses the out-of-date Ensembl to pull pdb
    # structures. Until it's patched to use RCSB, we do it ourselves.
    #box.setField("PDB", get(root, 'pdb'))
    pdbs = pdbs_for_uniprot(uniprot)
    if not pdbs:
        pdbs = get(root, 'pdb') # backup plan
    box.setField("PDB", pdbs)
    box.setField("HGNCid", get(root, 'HGNC'))
    box.setField("Symbol", get(root, 'symbol'))
    box.setField("AltSymbols", get(root, 'alias'))
    box.setField("OMIM", get(root, 'MIM'))
    box.setField("ECnumber", get(root, 'ec'))
    box.setField("Homologene", get(get(root, 'homologene'), 'id'))

    box.setField("Hs_Ensembl", get(get(root, 'ensembl'), 'gene'))
    box.setField("Hs_RefseqProtein", get(get(get(root, 'refseq'), 'protein'), 0))
    box.setField("Hs_RefseqmRNA", get(get(get(root, 'refseq'), 'rna'), 0))
    box.setField("Hs_GenLoc_db", get(get(meta, 'GENOME_ASSEMBLY'), 'human'))
    box.setField("Hs_GenLoc_chr", get(get(root, 'genomic_pos'), 'chr'))
    box.setField("Hs_GenLoc_start", get(get(root, 'genomic_pos'), 'start'))
    box.setField("Hs_GenLoc_end", get(get(root, 'genomic_pos'), 'end'))
    box.setField("path", "PBB/{}".format(box.fieldsdict['Hs_EntrezGene']))
    homologs = get(get(root, 'homologene'), 'genes')

    if get(root, 'go'):
        box.setField("Component", parse_go_category(get(root['go'], 'CC')))
        box.setField("Function", parse_go_category(get(root['go'], 'MF')))
        box.setField("Process", parse_go_category(get(root['go'], 'BP')))

    if homolog_json:
        root = homolog_json
        box.setField("Mm_EntrezGene", get(root, 'entrezgene'))
        box.setField("Mm_Ensembl", get(get(root, 'ensembl'), 'gene'))
        box.setField("Mm_RefseqProtein", get(get(get(root, 'refseq'), 'protein'), 0))
        box.setField("Mm_RefseqmRNA", get(get(get(root, 'refseq'), 'rna'), 0))
        box.setField("Mm_GenLoc_db", get(get(meta, 'GENOME_ASSEMBLY'), 'mouse'))
        box.setField("Mm_GenLoc_chr", get(get(root, 'genomic_pos'), 'chr'))
        box.setField("Mm_GenLoc_start", get(get(root, 'genomic_pos'), 'start'))
        box.setField("Mm_GenLoc_end", get(get(root, 'genomic_pos'), 'end'))

        mouse_uniprot = findReviewedUniprotEntry( get(root, 'uniprot'), get(root, 'entrezgene') )
        box.setField("Mm_Uniprot", mouse_uniprot )

    return box

def parse(entrez):
    '''
      Returns a ProteinBox object from a given Entrez id.

      Arguments:
        - `entrez`: a human entrez gene id
    '''
    #print "MYGENE :: ", get_json_documents(entrez)
    #print '\n- - - - - - - - - - - -  -\n'
    return parse_json(**get_json_documents(entrez))
