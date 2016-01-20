from django.conf import settings
from django.db import models

from genewiki.bio.g2p_redis import get_pmids, init_redis

import re, copy, json, datetime, urllib, PBB_Core, PBB_login


def check(titles):
    '''
        Tries, as fast as possible, to check the presence of titles passed to it as
        the first command-line argument.
    '''
    titles = [titles] if isinstance(titles, str) else titles
    qtitles = [urllib.quote(x) for x in titles]
    querystr = '|'.join(qtitles)
    api = 'http://en.wikipedia.org/w/api.php?action=query&titles={title}&prop=info&redirects&format=json'
    j = json.loads(urllib.urlopen(api.format(title=querystr)).read())
    results = {}
    pages = j['query']['pages']
    if 'redirects' in j['query']:
        redirects = j['query']['redirects']
        for r in redirects:
            results[r['from']] = r['to']
    for pid in pages:
        title = pages[pid]['title']
        results[title] = title if int(pid) > 0 else ''
    return results


def create_stub(gene_id):
    '''
        Contains templates and functions for generating article stubs for the Gene Wiki
        Project on Wikipedia.
    '''

    try:
        from genewiki.bio.mygeneinfo import get_response
        root, meta, homolog, entrez, uniprot = get_response(gene_id)
    except Exception, e:
        print e
        return None

    summary = root.get('summary', '')
    footer = ''
    if summary != '':
        summary = '==Function==\n\n' + summary
        footer = '{{NLM content}}'

    genomic_pos = root.get('genomic_pos')[0] if isinstance(root.get('genomic_pos'), list) else root.get('genomic_pos')
    if genomic_pos:
         chromo = genomic_pos.get('chr')
    else:
         chromo = ''
    values = {
        'id': root.get('entrezgene'),
        'name': root.get('name')[0].capitalize() + root.get('name')[1:],
        'symbol': root.get('symbol'),
        'summary': summary,
        'chromosome': chromo,
        'currentdate': datetime.date.today().isoformat(),  # adjust if not in CA
        'citations': '',
        'footer': footer
    }
    values['entrezcite'] = settings.ENTREZ_CITE.format(**values)

    # build out the citations
    pmids = get_pmids(gene_id, init_redis(), 100)
    limit = 9 if len(pmids) > 9 else len(pmids)
    citations = ''
    for pmid in pmids[:limit]:
        citations = '{}*{{{{Cite pmid|{} }}}}\n'.format(citations, pmid)
    values['citations'] = citations

    stub = settings.STUB_SKELETON.format(**values)
    return stub


def create(entrez, force=False):
    results = {'titles': {}, 'template': '', 'stub': ''}

    try:
        from genewiki.bio.mygeneinfo import get_response
        root, meta, homolog, entrez, uniprot = get_response(entrez)
    except ValueError:
        # invalid entrez
        return None
 
    # Query wikidata for existance of entrez_id don't create new pages for entrez_ids not in wikidata

    entrez_query = """
        SELECT ?entrez_id  WHERE {
        ?cid wdt:P351 ?entrez_id  .
        FILTER(?entrez_id ='"""+str(entrez)+"""') .
    }
    """

    wikidata_results = PBB_Core.WDItemEngine.execute_sparql_query(prefix=settings.PREFIX, query=entrez_query)['results']['bindings']
    entrez_id = ''
    for x in wikidata_results:
	entrez_id = x['entrez_id']['value']
    if entrez_id != str(entrez):
        return None
    else:
       # Dictionary of each title key and tuple of it's (STR_NAME, IF_CREATED_ON_WIKI)
       titles = {'name': (root['name'].capitalize(), False),
                 'symbol': (root['symbol'], False),
                 'test': (entrez_id, False),
                 'altsym': ('{0} (gene)'.format(root['symbol']), False),
                 'templatename': ('Template:PBB/{0}'.format(entrez), False)}

       # For each of the titles, build out the correct names and
       # corresponding Boolean for if they're on Wikipedia
       checked = check([titles[key][0] for key in titles.keys()])
       for key, value in titles.iteritems():
           if checked.get(value[0]):
               titles[key] = (value[0], True)
       results['titles'] = titles

       # Generate the Stub code if the Page (for any of the possible names) isn't on Wikipedia
       if not (titles['name'][1] or titles['symbol'][1] or titles['altsym'][1]) or force:
           results['stub'] = create_stub(entrez)

       return results

def interwiki_link(entrez, name):
    # Query wikidata for Q-item id (cid)

    cid_query = """
        SELECT ?cid  WHERE {
        ?cid wdt:P351 ?entrez_id  .
        FILTER(?entrez_id ='"""+str(entrez)+"""') .
    }
    """

    wikidata_results = PBB_Core.WDItemEngine.execute_sparql_query(prefix=settings.PREFIX, query=cid_query)['results']['bindings']
    cid = ''
    for x in wikidata_results:
        cid = x['cid']['value'].split('/')[-1]

    #create interwiki link
    username = models.CharField(max_length=200, blank=False)
    password = models.CharField(max_length=200, blank=False)
    # create your login object with your user and password (or the ProteinBoxBot account?)
    login_obj = PBB_login.WDLogin(user=username, pwd=password)
    # load the gene Wikidata object
    wd_gene_item = PBB_Core.WDItemEngine(wd_item_id=cid)
    # set the interwiki link to the correct Wikipedia page
    wd_gene_item.set_sitelink(site='enwiki', title=name)
    # write the changes to the item
    wd_gene_item.write(login_obj)

class ProteinBox(object):
    '''
      The fields and values of a GNF_Protein_box and methods to view/edit them.
      Calling str() or printing this object returns its wikitext representation.
      To access individual field values, use proteinBox.fieldsdict (field:value).
      To merge ProteinBox objects, call proteinBox.updateWith(otherProteinBox),
      which returns a new ProteinBox with the combined data.
    '''

    # this regex matches only latin characters and arabic numerals,
    # underscores, and hyphenations. Suitable for most standardized accn numbers,
    # i.e. from HUGO Nomenclature guidelines
    generic = r'^[\w-]+$'

    # nonspecific regex
    default = r'.*'

    # only numbers
    digits = r'^\d+$'

    # All possible fields in a Protein Box.
    # The keys define the field names, while their values provide a regex that must
    # match (through re.match) to validate a potential value. For fields that can contain
    # multiple values, the regex should match each value. For field values in the form of a
    # dict, the regex should match the keys.
    fields = {
        'Name': default,
        'image': default,
        'image_source': default,
        'PDB': r'^\w{4}$',
        'HGNCid': generic,
        'MGIid': generic,
        'Symbol': generic,
        'AltSymbols': default,
        'IUPHAR': default,
        'ChEMBL': default,
        'OMIM': r'^\d{6}$',
        # 'ECnumber': r'^(\d+\.?){4}$',
        'ECnumber': default,
        'Homologene': default,    # could not find source for this
        'GeneAtlas_image1': default,
        'GeneAtlas_image2': default,
        'GeneAtlas_image3': default,
        'Protein_domain_image': default,
        'Function': (r'^GO:\d+$', default),
        'Component': (r'^GO:\d+$', default),
        'Process': (r'^GO:\d+$', default),
        'Hs_EntrezGene': digits,
        'Hs_Ensembl': generic,
        'Hs_RefseqmRNA': r'NM_\d+(\.\d+)?$',
        'Hs_RefseqProtein': r'NP_\d+(\.\d+)?$',
        'Hs_GenLoc_db': r'(?i)hg\d+$',
        'Hs_GenLoc_chr': default,
        'Hs_GenLoc_start': digits,
        'Hs_GenLoc_end': digits,
        'Hs_Uniprot': r'^(?i)[a-z0-9]{6}$',
        'Mm_EntrezGene': digits,
        'Mm_Ensembl': generic,
        'Mm_RefseqmRNA': r'NM_\d+(\.\d+)?$',
        'Mm_RefseqProtein': r'NP_\d+(\.\d+)?$',
        'Mm_GenLoc_db': r'(?i)mm\d+$',
        'Mm_GenLoc_chr': default,
        'Mm_GenLoc_start': digits,
        'Mm_GenLoc_end': digits,
        'Mm_Uniprot': r'^(?i)[a-z0-9]{6}$',
        'path': r'^PBB\/\d+$',
        'before_text': default,
        'after_text': default}

    # Fields that can hold multiple values
    multivalue = ['PDB',
                  'AltSymbols',
                  'ECnumber',
                  'Function',
                  'Component',
                  'Process']

    def validate(self, field, value):

        if not value:
            return True

        if field in self.multivalue:
            for entry in value:
                if field in ['Function', 'Component', 'Process']:
                    if not re.match(self.fields[field][0], entry):
                        return False
                elif not re.match(self.fields[field], entry):
                    return False
            return True
        else:
            if re.match(self.fields[field], value):
                return True
            else:
                return False

    def __init__(self):
        self.fieldsdict = {}

        for field in self.fields:
            if field in self.multivalue:
                self.fieldsdict[field] = u''
            else:
                self.fieldsdict[field] = u''

    def coerce_unicode(self, obj):
        if isinstance(obj, str):
            return unicode(obj, 'utf8')
        elif isinstance(obj, int):
            return unicode(str(obj), 'utf8')
        else:
            return obj

    def setField(self, field_name, field_value):
        '''
          Sets a field in the fieldsdict using the fields as a validity check.
          Checks the field against a regex. These aren't foolproof- if
          there are problems, this should be disabled.

          The field value must be a unicode object (some coercion will be tried,
          but may fail).

          Obviously can be bypassed by changing fieldsdict directly, but this is
          not encouraged since it'll be ignored if it's incorrect.
        '''

        fieldsdict = self.fieldsdict
        field_value = self.coerce_unicode(field_value)

        if field_name in self.fields:
            if field_name not in self.multivalue and not self.validate(field_name, field_value):
                print 'validation failed: ', field_name, field_value
                return fieldsdict

            if field_name in self.multivalue:
                if isinstance(field_value, list):
                    fieldsdict[field_name] = field_value
                elif field_value:
                    fieldsdict[field_name] = [field_value]

            else:
                if not isinstance(field_value, int):
                    pass
                fieldsdict[field_name] = field_value
        else:
            raise NameError('Specified field does not exist. Reference the fields list for valid names.')

        self.fieldsdict = fieldsdict
        return fieldsdict

    def updateWith(self, targetbox):
        '''
          Takes the fields from the target ProteinBox and this ProteinBox and selectively builds a new
          ProteinBox from the merger of the two. It decides which field to use to build the new object
          using the following rule:

          If the target's field value is missing or equal to this one's, this one's value is used. Otherwise,
          the target's value is used. (Easy enough). 

          Returns the new ProteinBox with the new fields and a summary message describing the fields updated.
          Also returns a updatedFields dict, which stores data as such: {field_changed:(old, new), ...}
        '''
        # Current field dictionary for the Proteinbox
        src = self.fieldsdict

        try:
            tgt = targetbox.fieldsdict
        except AttributeError:
            raise TypeError('Cannot update with target (missing fieldsdict attribute). Ensure target is a ProteinBox.')

        new = ProteinBox()
        updatedFields = {}

        # Perform the merge by comparing the src and target dictionary
        for field in self.fields:
            srcval = src[field]
            tgtval = tgt[field]

	    #First check if field is an image and don't overwrite
            if field == 'image' and srcval:
                new.setField(field,srcval)
            else:
                if tgtval and srcval != tgtval:
                    updatedFields[field] = (srcval, tgtval)
                    new.setField(field, tgtval)
                else:
                    new.setField(field, srcval)

        # Default summary message; changes if fields were updated
        summary = 'Minor aesthetic updates.'
        if updatedFields:
            summary = 'Updated {} fields: '.format(len(updatedFields))
            for field in updatedFields:
                summary = summary + field + ', '
            summary = summary.rstrip(', ')

        return new, summary, updatedFields

    def linkImage(self):
        '''
          If a pdb structure and hugo symbol are available, but no image field set,
          we can attempt to find or render an image for the ProteinBox.
        '''
        if (self.fieldsdict['PDB'] and self.fieldsdict['Symbol'] and not self.fieldsdict['image']):
            from genewiki.bio.images import get_image
            image, caption = get_image(self, use_experimental=True)
            self.setField('image', image)
            self.setField('image_source', caption)

    def wikitext(self):
        '''
          Returns the unicode wikitext representation of the fields in this box.
        '''
        fieldsdict = copy.deepcopy(self.fieldsdict)
        # We have to handle each multivalue field specially- can't be outputting
        # bracketed array representations into the final wikitext :)
        for field in self.multivalue:
            if field == 'PDB':
                pdbstr = ''
                for i in fieldsdict[field]:
                    # Make sure we actually have something
                    if i.strip():
                        pdbstr = pdbstr + '{{PDB2|' + i + '}}, '
                pdbstr = pdbstr.strip().strip(',')
                fieldsdict[field] = pdbstr

            elif field == 'AltSymbols':
                if fieldsdict[field]:
                    altsym = '; '
                    altsym = altsym + '; '.join(fieldsdict[field])
                    fieldsdict[field] = altsym

            elif field == 'ECnumber':
                ecnum = ', '.join(fieldsdict[field])
                fieldsdict[field] = ecnum

            else:
                goterms = ''
                for entry in fieldsdict[field]:
                    for term in entry:
                        text = entry[term]
                        formatted = '{{{{GNF_GO|id={} |text = {}}}}} '.format(term, text)
                        goterms = goterms + formatted
                goterms = goterms.rstrip(' ')
                fieldsdict[field] = goterms

        output = u'''{before_text}{{{{GNF_Protein_box
 | Name = {Name}
 | image = {image}
 | image_source = {image_source}
 | PDB = {PDB}
 | HGNCid = {HGNCid}
 | MGIid = {MGIid}
 | Symbol = {Symbol}
 | AltSymbols ={AltSymbols}
 | IUPHAR = {IUPHAR}
 | ChEMBL = {ChEMBL}
 | OMIM = {OMIM}
 | ECnumber = {ECnumber}
 | Homologene = {Homologene}
 | GeneAtlas_image1 = {GeneAtlas_image1}
 | GeneAtlas_image2 = {GeneAtlas_image2}
 | GeneAtlas_image3 = {GeneAtlas_image3}
 | Protein_domain_image = {Protein_domain_image}
 | Function = {Function}
 | Component = {Component}
 | Process = {Process}
 | Hs_EntrezGene = {Hs_EntrezGene}
 | Hs_Ensembl = {Hs_Ensembl}
 | Hs_RefseqmRNA = {Hs_RefseqmRNA}
 | Hs_RefseqProtein = {Hs_RefseqProtein}
 | Hs_GenLoc_db = {Hs_GenLoc_db}
 | Hs_GenLoc_chr = {Hs_GenLoc_chr}
 | Hs_GenLoc_start = {Hs_GenLoc_start}
 | Hs_GenLoc_end = {Hs_GenLoc_end}
 | Hs_Uniprot = {Hs_Uniprot}
 | Mm_EntrezGene = {Mm_EntrezGene}
 | Mm_Ensembl = {Mm_Ensembl}
 | Mm_RefseqmRNA = {Mm_RefseqmRNA}
 | Mm_RefseqProtein = {Mm_RefseqProtein}
 | Mm_GenLoc_db = {Mm_GenLoc_db}
 | Mm_GenLoc_chr = {Mm_GenLoc_chr}
 | Mm_GenLoc_start = {Mm_GenLoc_start}
 | Mm_GenLoc_end = {Mm_GenLoc_end}
 | Mm_Uniprot = {Mm_Uniprot}
 | path = {path}
}}}}{after_text}'''
        output = output.format(**fieldsdict)
        return output

    def __str__(self):
        '''
          Returns a binary str representation of the wikitext.

          This is critical for getting this object as a string to give to mwclient
        '''
        return self.wikitext().encode('utf-8')

    def __unicode__(self):
        return self.wikitext()


'''
  Utility methods for parsing and extracting infobox templates.
'''


def contains_template(source, templatename):
    '''
      Returns the index of the start of the template if found, or None elsewise
    '''
    for match in re.finditer(r'\{\{\s?([\w\s]*)\s?(\||\})', source):
        if templatename in match.group(1):
            return match.start(1)
    # If we've gone through all the matches and haven't found the template
    return None


def isolate_template(source, templatename):
    '''
      Returns the start and end of the specified template content in the source
      as a tuple (start, end).
    '''
    start = contains_template(source, templatename)
    if not start:
        raise ValueError('The source does not appear to contain the template.')
    opened = closed = -1
    level = 0
    subsource = source[start - 2:]
    for i, char in enumerate(subsource):
        prev = subsource[i - 1] if i > 0 else ''
        if char == '{' and prev == '{':
            level = level + 1
            if opened is -1:
                opened = i + 1
        elif char == '}' and prev == '}':
            level = level - 1
            if closed < i:
                closed = i + 1

        if level is 0 and opened is not -1:
            break

    if opened is not -1 and closed is not -1:
        return opened + start - 2, closed + start - 2, subsource[opened:closed]
    else:
        return None


def postprocess(fieldvalues):
    '''
      Returns a ProteinBox from a dictionary of field:value pairs.

      Splits the multiple-value fields up so that they can be inspected atomically
      during updates or comparisons. This is not meant to be used independently.
    '''
    pbox = ProteinBox()
    # print 'DEBUG: '+str(fieldvalues.keys())
    # for val in fieldvalues: print 'DEBUG: {}:{}'.format(val, fieldvalues[val])
    for field in pbox.fields:
        # Handle splitting up multiple value fields
        if field in pbox.multivalue:
            print field, fieldvalues[field]
            if field == 'PDB' and fieldvalues[field]:
                regex = r'\{\{PDB2\|([\w\d]*)\}\}'
                pdbs = []
                for match in re.finditer(regex, fieldvalues[field]):
                    # appends individual PBD identifiers
                    pdbs.append(match.group(1))
                    pbox.setField(field, pdbs)

            elif field == 'AltSymbols' and fieldvalues[field]:
                if not re.search(r'[\w\d]+', fieldvalues[field]):
                    # there's only junk in here; set the value as None
                    pbox.setField(field, None)
                else:
                    alts = fieldvalues[field].split('; ')
                    # Filters any empty strings ('' evals to False)
                    alts = filter(lambda x: x, alts)
                    alts = filter(lambda x: x != ';', alts)
                    pbox.setField(field, alts)

            elif field == 'ECnumber' and fieldvalues[field]:
                ecs = fieldvalues[field].split(', ')
                ecs = filter(lambda x: x, ecs)
                pbox.setField(field, ecs)

            elif fieldvalues[field]:  # One of the GO fields
                # this regex isolates the GO term and the description into group 1 and 2
                # we do this to avoid any junk or invalid markup in these fields
                regex = r'\{\{GNF_GO\s?\|\s?id=(GO:[\d]*)\s?\|\s?text\s?=\s?([^\}]*)\}\}'
                goterms = []
                print '/ / / / / / / / / /'
                print field, fieldvalues[field]
                for match in re.finditer(regex, fieldvalues[field]):
                    goterms.append({match.group(1): match.group(2)})
                pbox.setField(field, goterms)

        # Import the rest of the fields into the new ProteinBox
        elif field in fieldvalues and fieldvalues[field]:
            pbox.setField(field, fieldvalues[field])

    pbox.setField('path', 'PBB/{}'.format(pbox.fieldsdict['Hs_EntrezGene']))
    return pbox


def strip_references(wikitext):
    '''
      Strips the references from wikitext, replacing them with a unique id.
      Returns both the stripped wikitext and a list of the references in order by
      which they were removed, usually left-right, top-down.

      Arguments:
        - `wikitext`: the wikitext to be stripped of references.
    '''

    source = copy.copy(wikitext)
    # First we ensure that UNIQ really is unique by appending characters
    UNIQ = 'x7fUNIQ'
    while UNIQ in source:
        UNIQ = UNIQ + 'f'

    # Then we do the replacements
    reftags = []
    refcount = 0
    for match in re.finditer(r'<ref\b[^>]*>(.*?)</ref>', source):
        reftags.append(match.group())
        source = source.replace(match.group(), UNIQ + str(refcount))
        refcount += 1

    # Finally, return the stripped wikitext, the list of references, and the
    # unique salt used to mark them
    return source, reftags, UNIQ


def restore_references(wikitext, references, salt):
    '''
      Restores the references removed by strip_references().
      Can be used on a fragment of the original, as long as the salt representing
      the reference location remains intact.

      Arguments:
        - `wikitext`: wikitext where the references have been stripped
        - `references`: a list of references in order of removal
        - `salt`: the unique salt used to replace the references
    '''

    restored = wikitext
    while salt in restored:
        ref_id = int(restored[restored.index(salt) + len(salt)])
        restored = restored.replace(salt + str(ref_id), references[ref_id])

    return restored


def generate_protein_box_for_existing_article(page_source):
    '''
      Parses a page containing a GNF_Protein_box template and returns a ProteinBox
      object with field values corresponding to the template's.

      It is generally safe to pass a raw page to the parser as it will perform a
      number of preprocessing steps before the main parse loop. Specifically, it
      will verify that the page contains the template, ignore any text above or
      below the template, and quarantine any reftags. It will fail if there is any
      particularly unusual or invalid wikitext (raises a wikitext.ParseError), or
      if the source does not contain a valid template (ValueError).
    '''

    # PREPROCESSING

    # Temporary storage for all the field:value pairs we find for later
    fieldvalues = {}

    # Throws a ValueError if source does not contain template, extracts the
    # template content, and stores the before and after content
    start, end, source = isolate_template(page_source, settings.TEMPLATE_NAME)
    before = page_source[:start - 2]
    after = page_source[end:]
    fieldvalues['before_text'] = before
    fieldvalues['after_text'] = after

    # Remove all ref tags, replacing them with an unique salt + id string and
    # storing their contents in a list.
    source, references, salt = strip_references(source)

    # Bugfix: removing an error message inserted by a previous run...
    source = source.replace('{{PDB2|Problem creating Query from XML: Problem with parms! }}, {{PDB2|<orgPdbQuery><queryType>org.pdb.query.simple.UpAccessionIdQuery</queryType><accessionIdList></accessionIdList></orgPdbQuery>}}', '')

    # Finally, we remove any leading and trailing newlines and curly braces
    source = source.strip('\n').strip('{}')

    fNameStart = 0
    fNameEnd = 0
    fValStart = 0
    fValEnd = 0

    nameParsed = False
    valueParsed = False
    inBrackets = False
    inField = False

    level = 0

    '''
      The parser attempts to keep track of the bracket depth (level)
      and the context for its position in the text (i.e. in a field, inside brackets,
      etc). This determines whether it will parse a name or field value from the text
      (if at level 0) or ignore (if deeper than 0- i.e. nested templates). It also
      ignores anything inside < or > as it assumes it is HTML, not wikitext.
    '''
    i = 0
    while i < len(source):
        ch = source[i]
        nx = source[i + 1] if i < len(source) - 1 else None

        if ch == '{' and nx == '{' or ch == '[' and nx == '[' or ch == '<':
            level += 1
            inBrackets = True
            i += 1
        elif ch == '}' and nx == '}' or ch == ']' and nx == ']' or ch == '>':
            level = level - 1
            if level is 0:
                inBrackets = False
            i += 1
        elif ch == '|' and not inBrackets:
            if not inField:
                inField = True
                fNameStart = i + 1
            else:
                inField = False
                fValEnd = i
                valueParsed = True
                i = i - 1
        elif ch == '=' and not inBrackets and inField and not nameParsed:
            fNameEnd = i
            fValStart = i + 1
            nameParsed = True

        if i == len(source) - 1:
            fValEnd = i + 1
            valueParsed = True

        if nameParsed and valueParsed:
            try:
                name = source[fNameStart:fNameEnd].strip()
                if (fValStart > fValEnd):
                    raise ValueError()
                value = source[fValStart:fValEnd].strip()

                # Replace the reftags we removed in preprocessing step 2
                value = restore_references(value, references, salt)

                # We don't add the name and values to the box yet because we
                # want to do some post-processing.
                # Also, ensure we're storing everything as unicode internally.
                if isinstance(value, str):
                    value = unicode(value, 'utf-8')
                fieldvalues[name] = value

                nameParsed = False
                valueParsed = False
            except ValueError:
                raise ParseError('Malformed wikitext- parsing failed.')
            except TypeError as e:
                print value
                raise e

        # Increment index and move on
        i += 1

    # splits up multiple value fields properly
    return postprocess(fieldvalues)


class ParseError(Exception):
    '''
      Thrown when the parser gets confused or encounteres malformed wikitext.
    '''
    pass
