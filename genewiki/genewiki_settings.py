STRICT = True

'''
    Template Settings:
    The page_prefix is the 'namespace' of the infoboxes. All the respective pages are
    in <base_site>/wiki/<page_prefix><entrez id>.
    The template_name is the name of the template that the parser attempts to find
    when parsing raw wikitext. It immediately follows the opening brackets.
'''
BASE_SITE = 'en.wikipedia.org'
PAGE_PREFIX = 'Template:PBB/'
TEMPLATE_NAME = 'GNF_Protein_box'

'''
    Pymol Configuration:
    Directs to the installation path of pymol (www.pymol.org) molecular rendering
    system. Value should be an absolute path to the pymol binary.
'''
PYMOL = '/usr/bin/pymol'

'''
    MyGene.Info Configuration
    These are fairly static and should not need to be changed.
'''
MYGENE_BASE = 'http://mygene.info/gene/'
MYGENE_META = 'http://mygene.info/metadata'

