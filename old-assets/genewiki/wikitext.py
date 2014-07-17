# -*- coding: utf-8 -*-

'''
  Utility methods for parsing and extracting infobox templates.
'''

import re, copy

try: import settings
except ImportError:
    print('''
Could not import settings: have you edited settings.example.py and saved it as
settings.py in the genewiki folder? For info, see settings.example.py.
''')
    raise

import proteinbox


def contains_template(source, templatename):
    '''
      Returns the index of the start of the template if found, or None elsewise
    '''
    for match in re.finditer(r'\{\{\s?([\w\s]*)\s?(\||\})', source):
        if templatename in match.group(1):
            return match.start(1)
    # If we've gone through all the matches and haven't found the template
    return None


def bots_allowed(source):
    '''
      Returns true if the deny_bots regex finds no matches.
    '''
    return not (re.search(r'\{\{(nobots|bots\|(allow=none|deny=.*?' +
                          "ProteinBoxBot" + r'.*?|optout=all|deny=all))\}\}',
                          source))


def isolate_template(source, templatename):
    '''
      Returns the start and end of the specified template content in the source
      as a tuple (start, end).
    '''
    start = contains_template(source, templatename)
    if not start:
        raise ValueError("The source does not appear to contain the template.")
    opened = closed = -1
    level = 0
    subsource = source[start-2:]
    for i, char in enumerate(subsource):
        prev = subsource[i-1] if i > 0 else ''
        if char == '{' and prev == '{':
            level = level + 1
            if opened is -1:
                opened = i+1
        elif char == '}' and prev == '}':
            level = level - 1
            if closed < i:
                closed = i+1

        if level is 0 and opened is not -1:
            break

    if opened is not -1 and closed is not -1:
        return opened+start-2, closed+start-2, subsource[opened:closed]
    else: return None


def postprocess(fieldvalues):
    '''
      Returns a ProteinBox from a dictionary of field:value pairs.

      Splits the multiple-value fields up so that they can be inspected atomically
      during updates or comparisons. This is not meant to be used independently.
    '''
    pbox = proteinbox.ProteinBox()
    #print "DEBUG: "+str(fieldvalues.keys())
    #for val in fieldvalues: print "DEBUG: {}:{}".format(val, fieldvalues[val])
    for field in pbox.fields:
        # Handle splitting up multiple value fields
        if field in pbox.multivalue:
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
                ecs = filter(lambda x:x, ecs)
                pbox.setField(field, ecs)
            elif fieldvalues[field]: # One of the GO fields
                # this regex isolates the GO term and the description into group 1 and 2
                # we do this to avoid any junk or invalid markup in these fields
                regex = r'\{\{GNF_GO\s?\|\s?id=(GO:[\d]*)\s?\|\s?text\s?=\s?([^\}]*)\}\}'
                goterms = []
                for match in re.finditer(regex, fieldvalues[field]):
                    goterms.append({match.group(1):match.group(2)})
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
    UNIQ           = "x7fUNIQ"
    while UNIQ in source:
        UNIQ       = UNIQ+'f'
    # Then we do the replacements
    reftags        = []
    refcount       = 0
    for match in re.finditer(r'<ref\b[^>]*>(.*?)</ref>', source):
        reftags.append(match.group())
        source     = source.replace(match.group(), UNIQ+str(refcount))
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
        ref_id = int(restored[restored.index(salt)+len(salt)])
        restored = restored.replace(salt+str(ref_id), references[ref_id])

    return restored


def parse(page_source):
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

    ## PREPROCESSING ##

    # Temporary storage for all the field:value pairs we find for later
    fieldvalues = {}

    # Throws a ValueError if source does not contain template, extracts the
    # template content, and stores the before and after content
    start, end, source = isolate_template(page_source, settings.template_name)
    before             = page_source[:start-2]
    after              = page_source[end:]
    fieldvalues['before_text'] = before
    fieldvalues['after_text']  = after

    # Remove all ref tags, replacing them with an unique salt + id string and
    # storing their contents in a list.
    source, references, salt = strip_references(source)

    # Bugfix: removing an error message inserted by a previous run...
    source = source.replace("{{PDB2|Problem creating Query from XML: Problem with parms! }}, {{PDB2|<orgPdbQuery><queryType>org.pdb.query.simple.UpAccessionIdQuery</queryType><accessionIdList></accessionIdList></orgPdbQuery>}}", '')

    # Finally, we remove any leading and trailing newlines and curly braces
    source = source.strip('\n').strip('{}')

    ## MAIN LOOP ##

    fNameStart = 0
    fNameEnd   = 0
    fValStart  = 0
    fValEnd    = 0

    nameParsed  = False;
    valueParsed = False;
    inBrackets  = False;
    inTag       = False;
    inField     = False;

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
        nx = source[i+1] if i < len(source)-1 else None

        if ch == '{' and nx =='{' or ch == '[' and nx == '[' or ch == '<':
            level += 1
            inBrackets = True
            i += 1
        elif ch == '}' and nx == '}' or ch == ']' and nx == ']' or ch == '>':
            level = level-1
            if level is 0:
                inBrackets  = False
            i += 1
        elif ch == '|' and not inBrackets:
            if not inField:
                inField     = True
                fNameStart  = i+1
            else:
                inField     = False
                fValEnd     = i
                valueParsed = True
                i           = i - 1
        elif ch == '=' and not inBrackets and inField and not nameParsed:
            fNameEnd        = i;
            fValStart       = i+1
            nameParsed      = True

        if i == len(source)-1:
            fValEnd = i+1;
            valueParsed = True;


        if nameParsed and valueParsed:
            try:
                name  = source[fNameStart:fNameEnd].strip()
                if (fValStart > fValEnd):
                    raise ValueError();
                value = source[fValStart:fValEnd].strip()

                # Replace the reftags we removed in preprocessing step 2
                value = restore_references(value, references, salt)

                # We don't add the name and values to the box yet because we
                # want to do some post-processing.
                # Also, ensure we're storing everything as unicode internally.
                if isinstance(value, str):
                    value = unicode(value, 'utf-8')
                fieldvalues[name] = value

                nameParsed  = False
                valueParsed = False
            except ValueError:
                raise ParseError("Malformed wikitext- parsing failed.")
            except TypeError as e:
                print value
                raise e

        # Increment index and move on
        i += 1

    # splits up multiple value fields properly
    pbox = postprocess(fieldvalues)
    return pbox

class ParseError(Exception):
    '''
      Thrown when the parser gets confused or encounteres malformed wikitext.
    '''
    pass
