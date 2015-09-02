from django.conf import settings

from genewiki.wiki.textutils import ProteinBox
from genewiki.bio.uniprot import uniprot_acc_for_entrez_id
from raven.contrib.django.raven_compat.models import client

import re, mygene


def parse_go_category(entry):
    if entry is None:
        return []

    # single term:
    if 'term' in entry:
        return {entry['id']: entry['term']}

    # multiple terms
    else:
        terms = []
        results = []
        for x in entry:
            if x['term'] not in terms:
                results.append({x['id']: x['term']})
            terms.append(x['term'])
        return results


def findReviewedUniprotEntry(entries, entrez):
    '''
      Attempts to return the first reviewed entry in a given dict of dbname:id
      pairs for a gene's UniProt entries.
      If a reviewed entry is not found, it attempts to query Uniprot directly for one.
      If this still is unsuccessful, it returns one from TrEMBL at random.

      Arguments:
      - `entries`: a dict of entries, e.g {'Swiss-Prot':'12345', 'TrEMBL':'67890'}
    '''
    if not isinstance(entries, dict) and not entrez:
        return u''
    elif entrez:
        return uniprot_acc_for_entrez_id(entrez)

    if 'Swiss-Prot' in entries:
        entry = entries['Swiss-Prot']
    else:
        entry = entries['TrEMBL']

    if isinstance(entry, list):
        for acc in entry:
            if uniprot.isReviewed(acc):
                return acc
        # if no reviewed entries, check Uniprot directly
        canonical = uniprot_acc_for_entrez_id(entrez)
        if canonical:
            return canonical
        else:
            return entry[0]
    else:
        canonical = uniprot_acc_for_entrez_id(entrez)
        if canonical:
            return canonical
        else:
            return entry


def get_homolog(json_res):
    '''
      Returns the homologous gene for a given gene for the mouse taxon

      Arguments:
      - `json_res`:  the mygene.info json document for original gene
    '''
    if json_res.get('genes') == None:
        return None
    else:
       homologs = json_res.get('homologene').get('genes')
       # isolate our particular taxon (returns [[taxon, gene]])
       if homologs:
           pair = filter(lambda x: x[0] == settings.MOUSE_TAXON_ID, homologs)
           if pair:
               return pair[0][1]
           else:
               return None
       else:
           return None


def get_response(entrez):
    mg = mygene.MyGeneInfo()
    try:
        root = mg.getgene(entrez, 'name,summary,entrezgene,uniprot,pdb,HGNC,symbol,alias,MIM,ec,homologene,ensembl,refseq,genomic_pos,go', species='human')
        meta = mg.metadata
        homolog = get_homolog(root)
        homolog = mg.getgene(homolog, 'name,summary,entrezgene,uniprot,pdb,HGNC,symbol,alias,MIM,ec,homologene,ensembl,refseq,genomic_pos,go') if homolog else None
        entrez = root.get('entrezgene')
        uniprot = findReviewedUniprotEntry(root.get('uniprot'), entrez)
        return root, meta, homolog, entrez, uniprot
    except Exception as e:
        client.captureException()
        return e

def generate_protein_box_for_entrez(entrez):
    '''
      Returns a ProteinBox based on the provided JSON documents.

    '''
    root, meta, homolog, entrez, uniprot = get_response(entrez)
    box = ProteinBox()

    name = root.get('name')
    if re.match(r'\w', name):
        name = name[0].capitalize() + name[1:]
    box.setField('Name', name)
    box.setField('Hs_EntrezGene', entrez)
    box.setField('Hs_Uniprot', uniprot)
    box.setField('PDB', root.get('pdb'))
    box.setField('HGNCid', root.get('HGNC'))
    box.setField('Symbol', root.get('symbol'))
    box.setField('AltSymbols', root.get('alias'))
    box.setField('OMIM', root.get('MIM'))
    box.setField('ECnumber', root.get('ec'))
    if homolog:
         box.setField('Homologene', root.get('homologene').get('id'))
    ensembl = root.get('ensembl')
    if ensembl:
         box.setField('Hs_Ensembl', ensembl[0].get('gene') if isinstance(ensembl, list) else ensembl.get('gene'))

    refseq = root.get('refseq')
    if refseq == None:
        box.setField('Hs_RefseqProtein', '')
        box.setField('Hs_RefseqmRNA', '')
    else:
        box.setField('Hs_RefseqProtein', refseq.get('protein')[0] if isinstance(refseq.get('protein'), list) else refseq.get('protein'))
        box.setField('Hs_RefseqmRNA', refseq.get('rna')[0] if isinstance(refseq.get('rna'), list) else refseq.get('rna'))

    box.setField('Hs_GenLoc_db', meta.get('genome_assembly').get('human'))

    genomic_pos = root.get('genomic_pos')[0] if isinstance(root.get('genomic_pos'), list) else root.get('genomic_pos')
    if genomic_pos:
         box.setField('Hs_GenLoc_chr', genomic_pos.get('chr'))
         box.setField('Hs_GenLoc_start', genomic_pos.get('start'))
         box.setField('Hs_GenLoc_end', genomic_pos.get('end'))
    box.setField('path', 'PBB/{}'.format(entrez))

    go = root.get('go', None)
    if go:
        box.setField('Component', parse_go_category(go.get('CC')))
        box.setField('Function', parse_go_category(go.get('MF')))
        box.setField('Process', parse_go_category(go.get('BP')))

    if homolog:
        mouse_uniprot = findReviewedUniprotEntry(homolog.get('uniprot'), homolog.get('entrezgene'))

        box.setField('Mm_EntrezGene', homolog.get('entrezgene'))
        ensembl = homolog.get('ensembl')
        box.setField('Mm_Ensembl', ensembl[0].get('gene') if isinstance(ensembl, list) else ensembl.get('gene'))

        refseq = homolog.get('refseq')
        box.setField('Mm_RefseqProtein', refseq.get('protein')[0] if isinstance(refseq.get('protein'), list) else refseq.get('protein'))
        box.setField('Mm_RefseqmRNA', refseq.get('rna')[0] if isinstance(refseq.get('rna'), list) else refseq.get('rna'))

        box.setField('Mm_GenLoc_db', meta.get('genome_assembly').get('mouse'))

        genomic_pos = homolog.get('genomic_pos')[0] if isinstance(homolog.get('genomic_pos'), list) else homolog.get('genomic_pos')
        box.setField('Mm_GenLoc_chr', genomic_pos.get('chr'))
        box.setField('Mm_GenLoc_start', genomic_pos.get('start'))
        box.setField('Mm_GenLoc_end', genomic_pos.get('end'))

        box.setField('Mm_Uniprot', mouse_uniprot)

    return box

