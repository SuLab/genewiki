
'''
  Methods for retrieving information about PDB structures from RCSB.
'''

import urllib2, re

url = 'http://www.rcsb.org/pdb/rest/search'

querytxt = """

<orgPdbQuery>

<queryType>org.pdb.query.simple.UpAccessionIdQuery</queryType>
<accessionIdList>{uniprot_id}</accessionIdList>

</orgPdbQuery>
"""

def pdbs_for_uniprot(uniprot):
    """
      Returns a list of PDB structures associated with the Uniprot id given.

      Arguments:
      - `uniprot`: a uniprot id
    """

    query = urllib2.Request(url, data=querytxt.format(uniprot_id=uniprot))
    _raw = urllib2.urlopen(query)
    results = [x.strip('\n') for x in _raw.readlines()]
    # sometimes there's an error returned in xml format; we should definitely not
    # insert it into the template

    if results:
        ''' We should only return valid PDB ids. If a returned result has anything besides 4
        [a-z, A-Z, 0-9] characters, it may be XML/HTML and we should return nothing.'''
        for result in results:
            if not re.match(r'[\w]{4}$', result):
                return []
        return results

    if results and 'Problem' in results[0]:
        return []
    else:
        return results
