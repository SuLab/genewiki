from django.db import models
from django.conf import settings

from genewiki.wiki.managers import BotManager, ArticleManager

import mwclient, re

class Bot(models.Model):
    username = models.CharField(max_length = 200, blank = False)
    password = models.CharField(max_length = 200, blank = False)

    SERVICE_TYPE_CHOICE = (
      ('wiki', 'Wikipedia User'),
      ('commons', 'Wikimedia Commons User'),
      ('data', 'Wikidata User'),
    )
    service_type = models.CharField(max_length = 10, choices = SERVICE_TYPE_CHOICE, blank = True, default = 'wiki')

    updated = models.DateTimeField(auto_now = True)
    created = models.DateTimeField(auto_now_add = True)


    def connection(self):
      connection = mwclient.Site(settings.BASE_SITE)
      connection.login(self.username, self.password)
      return connection


    def update_articles(self):
        connection = self.connection()

        for page in connection.Pages['Category:Human_proteins']:
          page_text = page.edit()
          if '{{PBB|geneid=' in page_text:
            article, created = Article.objects.get_or_create(title = page.page_title, bot = self)
            article.text = page_text
            article.save()

        gpb = self.wp.Pages['Template:GNF_Protein_box']
        for page in gpb.embeddedin('10'):
            if 'Template:PBB/' in page.name:
                article, created = Article.objects.get_or_create(title = page.page_title, article_type = 'template', bot = self)
                article.save()


    def __unicode__(self):
        return u'{0} ({1})'.format( self.username, self.service_type )



class Article(models.Model):
    title = models.CharField(max_length = 200, blank = False)
    text = models.TextField()

    PAGE = 0
    INFOBOX = 1
    TEMPLATE = 2
    ARTICLE_TYPE_CHOICE = (
      (PAGE, 'Standard Page'),
      (INFOBOX, 'Infobox'),
      (TEMPLATE, 'Template'),
    )
    article_type = models.IntegerField(max_length = 1, choices = ARTICLE_TYPE_CHOICE, blank = True, default = PAGE)

    updated = models.DateTimeField(auto_now = True)
    created = models.DateTimeField(auto_now_add = True)

    objects = ArticleManager()

    def __unicode__(self):
        return u'{0}'.format( self.title )


    def get_entreze(self):
        entrez_regex = r'Template:PBB/([\d]*)'
        match = re.search(entrez_regex, self.title)
        if match and match.group(1):
            return int(match.group(1))
        else: return None


    def get_page(self):
        bot = Bot.objects.filter(service_type = 'wiki').first()
        connection = bot.connection()
        return connection.Pages[self.title]


    def bots_allowed(self):
        '''
          Returns true if the deny_bots regex finds no matches.
        '''
        return not (re.search(r'\{\{(nobots|bots\|(allow=none|deny=.*?' +
                              "ProteinBoxBot" + r'.*?|optout=all|deny=all))\}\}',
                              self.text))



    def update(self, page):
        '''
          Returns an updated infobox and summary from data gathered from the
          specified page.

          Arguments:
          - `page`: a mwclient Page
        '''
        entrez = self.extractEntrezFromPageName(page)
        # Dictionary of fields to build a ProteinBox from
        mgibox = mygeneinfo.parse(entrez)

        # Returns processed ProteinBox object
        wptext = wikitext.parse(page.edit())
        # Run the comparision between the current box online
        # and the dictionary just generated from mygene
        return wptext.updateWith(mgibox)


    def write(self, proteinbox, summary):
        '''
          Writes the wikitext representation of the protein box to MediaWiki.

          Returns (result, None) if successful, or (None, Error) if not.

          Arguments:
          - `proteinbox`: an updated proteinbox to write
        '''
        error = None
        page = this.get_page()

        if not wikitext.bots_allowed(page.edit()):
            return (None, Exception('Bot edits prohibited.'))

        try:
            result = page.save(str(proteinbox), summary, minor=True)
            return (result, None)
        except MwClientError as e:
            error = e
        return (None, error)




#
#    class Meta:
#        abstract = True
#

# class GenePage(Article):
# p.backlinks         p.embeddedin        p.images            p.name              p.redirect          p.templates
# p.can               p.exists            p.langlinks         p.namespace         p.revision          p.touched
# p.categories        p.extlinks          p.last_rev_time     p.normalize_title   p.revisions
# p.delete            p.get_expanded      p.length            p.page_title        p.save
# p.edit              p.get_token         p.links             p.protection        p.site
# p.edit_time         p.handle_edit_error p.move              p.purge             p.strip_namespace

    # gene_id = models.CharField(max_length=200, blank = False)
    # name = models.CharField(max_length=200, blank = False)
    # symbol = models.CharField(max_length=200, blank = False)
    # summary = models.CharField(max_length=200, blank = False)
    # chromosome = models.CharField(max_length=200, blank = False)
    # currentdate = models.CharField(max_length=200, blank = False)
    # citations = models.CharField(max_length=200, blank = False)
    # footer = models.CharField(max_length=200, blank = False)

