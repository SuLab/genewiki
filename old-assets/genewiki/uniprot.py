# -*- coding: utf-8 -*-

import urllib, urllib2

def uniprotAccForEntrezId(entrez):
    '''Returns either one reviewed uniprot id or None.'''
    url = 'http://www.uniprot.org/mapping/'
    params = {
        'from':'P_ENTREZGENEID',
        'to':'ACC',
        'format':'list',
        'reviewed':'',
        'query':entrez
    }

    data = urllib.urlencode(params)
    response = urllib2.urlopen(urllib2.Request(url, data))
    accns = response.read().split('\n')
    for acc in accns:
        if isReviewed(acc): return acc
    return None

def isReviewed(uniprot):
    url = 'http://www.uniprot.org/uniprot/?query=reviewed:yes+AND+accession:{}&format=list'.format(uniprot)
    return bool(urllib.urlopen(url).read().strip('\n'))
