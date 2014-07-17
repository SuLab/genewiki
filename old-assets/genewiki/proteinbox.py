# -*- coding: utf-8 -*-

import re, copy

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
        "Name":         default,
        "image":        default,
        "image_source": default,
        "PDB":          r'^\w{4}$',
        "HGNCid":       generic,
        "MGIid":        generic,
        "Symbol":       generic,
        "AltSymbols":   default,
        "IUPHAR":       default,
        "ChEMBL":       default,
        "OMIM":         r'^\d{6}$',
        # "ECnumber":     r'^(\d+\.?){4}$',
        "ECnumber":     default,
        "Homologene":   default,    # could not find source for this
        "GeneAtlas_image1":     default,
        "GeneAtlas_image2":     default,
        "GeneAtlas_image3":     default,
        "Protein_domain_image": default,
        "Function":         (r'^GO:\d+$', default),
        "Component":        (r'^GO:\d+$', default),
        "Process":          (r'^GO:\d+$', default),
        "Hs_EntrezGene":    digits,
        "Hs_Ensembl":       generic,
        "Hs_RefseqmRNA":    r'NM_\d+(\.\d+)?$',
        "Hs_RefseqProtein": r'NP_\d+(\.\d+)?$',
        "Hs_GenLoc_db":     r'(?i)hg\d+$',
        "Hs_GenLoc_chr":    default,
        "Hs_GenLoc_start":  digits,
        "Hs_GenLoc_end":    digits,
        "Hs_Uniprot":       r'^(?i)[a-z0-9]{6}$',
        "Mm_EntrezGene":    digits,
        "Mm_Ensembl":       generic,
        "Mm_RefseqmRNA":    r'NM_\d+(\.\d+)?$',
        "Mm_RefseqProtein": r'NP_\d+(\.\d+)?$',
        "Mm_GenLoc_db":     r'(?i)mm\d+$',
        "Mm_GenLoc_chr":    default,
        "Mm_GenLoc_start":  digits,
        "Mm_GenLoc_end":    digits,
        "Mm_Uniprot":       r'^(?i)[a-z0-9]{6}$',
        "path":             r'^PBB\/\d+$',
        "before_text":      default,
        "after_text":       default}

    # Fields that can hold multiple values
    multivalue = ["PDB",
                  "AltSymbols",
                  "ECnumber",
                  "Function",
                  "Component",
                  "Process"]

    def validate(self, field, value):

        if not value:
            return True

        if field in self.multivalue:
            for entry in value:
                if field in ['Function', 'Component', 'Process']:
                    if not re.match(self.fields[field][0], entry.keys()[0]):
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
        elif isinstance(obj, list):
            uni_obj = []
            for item in obj:
                item = self.coerce_unicode(item)
                uni_obj.append(item)
            return uni_obj
        else:
            return obj

    def setField(self, field_name, field_value, strict=True):
        '''
          Sets a field in the fieldsdict using the fields as a validity check.
          If 'strict' is True (default), checks the field against a regex. These
          aren't foolproof- if there are problems, this should be disabled.

          The field value must be a unicode object (some coercion will be tried,
          but may fail).

          Obviously can be bypassed by changing fieldsdict directly, but this is
          not encouraged since it'll be ignored if it's incorrect.
        '''

        fieldsdict = self.fieldsdict
        field_value = self.coerce_unicode(field_value)

        if field_name in self.fields:
            if strict:
                if not self.validate(field_name, field_value):
                    print "validation failed: ", field_name, field_value
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
            raise NameError("Specified field does not exist. Reference the fields list for valid names.")

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
            raise TypeError("Cannot update with target (missing fieldsdict attribute). Ensure target is a ProteinBox.")

        new = ProteinBox()
        updatedFields = {}

        # Perform the merge by comparing the src and target dictionary
        for field in self.fields:
            srcval = src[field]
            tgtval = tgt[field]

            if tgtval and srcval != tgtval:
                updatedFields[field] = (srcval, tgtval)
                new.setField(field, tgtval)
            else:
                new.setField(field, srcval)

        # Default summary message; changes if fields were updated
        summary = "Minor aesthetic updates."
        if updatedFields:
            summary = "Updated {} fields: ".format(len(updatedFields))
            for field in updatedFields:
                summary = summary + field + ", "
            summary = summary.rstrip(", ")

        return new, summary, updatedFields

    def linkImage(self):
        '''
          If a pdb structure and hugo symbol are available, but no image field set,
          we can attempt to find or render an image for the ProteinBox.
        '''
        if (self.fieldsdict['PDB'] and self.fieldsdict['Symbol']
            and not self.fieldsdict['image']):
            from genewiki import images
            pdb = self.fieldsdict['PDB'][0]
            sym = self.fieldsdict['Symbol']
            image, caption = images.getImage(self, use_experimental=True)
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
            if field == "PDB":
                pdbstr = ""
                for i in fieldsdict[field]:
                    # Make sure we actually have something
                    if i.strip():
                        pdbstr = pdbstr + "{{PDB2|" + i + "}}, "
                pdbstr = pdbstr.strip().strip(',')
                fieldsdict[field] = pdbstr
            elif field == "AltSymbols":
                if fieldsdict[field]:
                    altsym = "; "
                    altsym = altsym + "; ".join(fieldsdict[field])
                    fieldsdict[field] = altsym
            elif field == "ECnumber":
                ecnum = ', '.join(fieldsdict[field])
                fieldsdict[field] = ecnum
            else:
                goterms = ""
                for entry in fieldsdict[field]:
                    for term in entry:
                        text = entry[term]
                        formatted = "{{{{GNF_GO|id={} |text = {}}}}} ".format(term, text)
                        goterms = goterms + formatted
                goterms = goterms.rstrip(' ')
                fieldsdict[field] = goterms

        output = u"""{before_text}{{{{GNF_Protein_box
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
}}}}{after_text}"""
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
