from django.conf import settings
import urllib, subprocess, os, sys, datetime, mwclient


'''
  Handles linking PDB structure images to ProteinBox templates.
'''

description_skeleton = '''== {{{{int:filedesc}} ==
{{{{Information
| Description={{{{en | 1=Structure of protein {symbol}.
Based on [[w:PyMol | PyMol]] rendering of PDB {{{{PDB2|{pdb}}}}}.}}}}
| Source = {{{{own}}}}
| Author = [[User:{username}|{username}]]
| Date = {date}
| Permission =
| other_versions =
}}}}
{{{{PD-self}}}}
{{{{Category:Protein_structures}}}}'''

caption_skeleton = 'Rendering based on [[Protein_Data_Bank | PDB]] {{{{PDB2|{pdb}}}}}.'

rcsb_skeleton = 'http://www.rcsb.org/pdb/files/{}.pdb'

# A dev server at EBI that provides 'chosen' PDB structures and images based
# on homologene ID
ebiserver = 'http://wwwdev.ebi.ac.uk/pdbe-apps/jsonizer/homologene/{}/'

title_skeleton = 'File:Protein_{hugo_sym}_PDB_{pdb_id}.png'


def get_image(proteinbox, use_experimental=True):
    '''Attempts to find a suitable image given a gene. Returns the image filename as
    it exists on Wikipedia commons, along with a suitable caption.

    Arguments:
    - `proteinbox`: a ProteinBox object representing known information about a gene
    - `use_experimental`: use a dev server at EBI to provide chosen PDB structures and
    images.'''
    fields = proteinbox.fieldsdict
    pdbid = ''
    if use_experimental and fields['Homologene']:
        import json
        homologene = fields['Homologene']
        try:
            req = urllib.urlopen(ebiserver.format(homologene))
            rawj = req.read()
            rawj = rawj.replace(' ', '').replace('\n', '')
            info = json.loads(rawj)
            if 'best_structure' in info:
                pdbid = info['best_structure']['pdbid']
                pdb = PDB(pdbid, fields['Symbol'])
                # They often have images, but we're going to render them again anyway.
                imagefile, caption = pdb.render()
                pdb.uploadToCommons()
                return image, caption
        finally:
            req.close()
    else:
        # Try to find one on Commons
        commons = mwclient.Site('commons.wikimedia.org')
        title1 = title_skeleton.format(hugo_sym=fields['Symbol'], pdb_id=fields['PDB'][0].upper())
        title2 = title_skeleton.format(hugo_sym=fields['Symbol'], pdb_id=fields['PDB'][0].lower())
        page1 = commons.Pages[title1]
        page2 = commons.Pages[title2]
        if page1.exists:
            return page1.name, caption_skeleton.format(pdb=fields['PDB'][0])
        elif page2.exists:
            return page2.name, caption_skeleton.format(pdb=fields['PDB'][0])
        elif len(fields['PDB']) > 1:
            titles = [title_skeleton.format(hugo_sym=fields['Symbol'], pdb_id=pdb) for pdb in fields['PDB']]
            for title in titles:
                page = commons.Pages[title]
                if page.exists:
                    import re
                    pdb = re.search(r'PDB[ _]([\d\w]*).png', title)
                    return page.name, caption_skeleton.format(pdb=pdb)

        # otherwise render a new one
        else:
            pdb = PDB(fields['PDB'][0], fields['Symbol'])
            image, caption = pdb.render()
            return image, caption


class PDB(object):

    def __init__(self, pdbid, hugosym, pdbpath=None, pymolpath=None, commons=None):
        self.pdbid = pdbid
        self.hugosym = hugosym
        self.pdbpath = pdbpath if pdbpath else settings.pbbhome + 'pdb/'
        if not self.pdbpath.endswith(os.sep):
            self.pdbpath = self.pdbpath + os.sep

        # ensure that pdb path exists

        if not os.path.exists(self.pdbpath):
            try:
                os.makedirs(self.pdbpath)
            except OSError:
                raise ValueError('Could not access pdb path at {} nor create it.'.format(self.pdbpath))

        # ensure that we can write in it
        try:
            open(self.pdbpath + 'test', 'w').close()
            os.remove(self.pdbpath + 'test')
        except IOError:
            raise ValueError(
                'Could not write in pdb path {}: permission denied.'.format(
                    self.pdbpath))

        self.pymolpath = pymolpath if pymolpath else settings.pymol
        self.pdbfile = None
        self.pngfile = None
        self.commons = commons
        self.__closed = False

    def download(self, pdb_id=None):
        '''
            Downloads a PDB file from rcsb.org and returns the filename if
            successful (or None if failed).
        '''
        if not pdb_id:
            pdb_id = self.pdbid

        try:
            remote = urllib.urlopen(rcsb_skeleton.format(pdb_id))
        except IOError:
            sys.stderr.write('pdb: error downloading pdb file from {}\n'
                             .format(rcsb_skeleton.format(pdb_id)))
            return None

        filename = self.pdbpath + pdb_id + '.pdb'
        with open(filename, 'wb') as local:
            local.write(remote.read())
            remote.close()
        self.pdbfile = filename
        return filename

    def render(self, pdb_id=None, hugo_sym=None, pdb_file=None):
        '''
            Render and return the filename of the image given a pdb id
            and hugo symbol.
            If the pdb file is already present, it can be passed as a parameter;
            otherwise it will be downloaded from rcsb.org.
        '''

        if not pdb_id:
            pdb_id = self.pdbid
        if not hugo_sym:
            hugo_sym = self.hugosym

        # Attempt to download the pdb file if not explicitly passed
        if not pdb_file:
            pdb_file = self.pdbfile
        if not pdb_file:
            pdb_file = self.download(pdb_id)
        if not pdb_file:
            return None

        # Set up the future location of the image
        if pdb_id is None:
            return None
        png_file = '{pdbpath}Protein_{hugo_sym}_PDB_{pdb_id}.png'.format(pdbpath=self.pdbpath, hugo_sym=hugo_sym, pdb_id=pdb_id)

        # Launch pymol as a subprocess and wait for return
        rendercmd = "cmd.png('{png_file}', 1200, 1000)".format(png_file=png_file)
        pymolcmd = [self.pymolpath, '-c', pdb_file, settings.PROJECT_PATH.format('commands.pml'), '-d', rendercmd]
        print ' '.join(pymolcmd)
        try:
            subprocess.check_call(pymolcmd)
        except CalledProcessError:
            print 'pdb: error rendering pdb file for id {}'.format(pdb_id)
            return None
        self.pngfile = png_file
        return png_file, caption_skeleton.format(pdb=pdb_id)

    def uploadToCommons(self, description=None, png_file=None, commons=None):
        if not png_file:
            raise ValueError('No .png file specified.')

        self.commons = commons
        self.commons = mwclient.Site('commons.wikimedia.org')
        if hasattr(settings, 'commons_user'):
            cuser = settings.commons_user
            cpass = settings.commons_pass
        else:
            cuser = settings.wiki_user
            cpass = settings.wiki_pass

        self.commons.login(cuser, cpass)

        if not description:
            description = description_skeleton.format(symbol=self.hugosym,
                                                      pdb=self.pdbid, username=cuser,
                                                      date=str(datetime.datetime.now()))

        try:
            self.commons.upload(open(png_file),
                                png_file.split(os.sep).pop(),
                                description)

        except mwclient.errors.LoginError:
            self.commons.login()

