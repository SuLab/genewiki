from django.db import models
from django.conf import settings

from genewiki.wiki.managers import BotManager, ArticleManager
from genewiki.wiki.textutils import generate_protein_box_for_existing_article
from genewiki.bio.mygeneinfo import generate_protein_box_for_entrez

from raven.contrib.django.raven_compat.models import client

import mwclient, re, logging
from mwclient.errors import *
logger = logging.getLogger(__name__)


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


    def previous_actions(self, limit = 500):
        '''
            Prints the last 500 actions (title) the bot has taken
        '''
        connection = self.connection()
        lists = connection.usercontributions(self.username, start=None, end=None, dir='older', namespace=None, prop=None, show=None, limit=limit)
        for item in lists:
            print item['title']


    def update_articles(self):
        connection = self.connection()
        gpb = connection.Pages['Template:GNF_Protein_box']
        for page in gpb.embeddedin('10'):
            if 'Template:PBB/' in page.name:
                article, created = Article.objects.get_or_create(title = page.name, article_type = Article.INFOBOX)
                article.text = page.edit()
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

    class Meta:
        ordering = ('-updated',)


    def url_for_article(self):
        return u'http://{0}/wiki/{1}'.format( settings.BASE_SITE, self.title )


    def get_entrez(self):
        entrez_regex = r'Template:PBB/([\d]*)'
        match = re.search(entrez_regex, self.title)
        if match and match.group(1):
            return int(match.group(1))
        else: return None


    def get_page(self):
        bot = Bot.objects.filter(service_type = 'wiki').first()
        connection = bot.connection()
        return connection.Pages[self.title]


    def generate_protein_box(self):
        entrez = self.get_entrez()
        return get_protein_box_for_entrez(entrez)


    def bots_allowed(self):
        '''
          Returns true if the deny_bots regex finds no matches.
        '''
        return not (re.search(r'\{\{(nobots|bots\|(allow=none|deny=.*?' +
                              "ProteinBoxBot" + r'.*?|optout=all|deny=all))\}\}',
                              self.text))



    def update(self):
        '''
          Returns an updated infobox and summary from data gathered from the
          specified page.
        '''
        # Dictionary of fields to build a ProteinBox from
        mgibox = generate_protein_box_for_entrez( self.get_entrez() )

        # Returns processed ProteinBox object
        current_box = generate_protein_box_for_existing_article( self.text )

        # Run the comparision between the current box online
        # and the dictionary just generated from mygene
        print self.url_for_article()
        try:
            updated, summary, updatedfields = current_box.updateWith( mgibox )
        except Exception as err:
            client.captureException()

        res = self.write(updated, summary)
        logger.info('Page Updated', exc_info=True, extra={'updated': updated, 'summary': summary, 'updatedfields': updatedfields});


    def write(self, proteinbox, summary):
        '''
          Writes the wikitext representation of the protein box to MediaWiki.

          Returns (result, None) if successful, or (None, Error) if not.

          Arguments:
          - `proteinbox`: an updated proteinbox to write
        '''
        error = None
        page = self.get_page()

        if not self.bots_allowed():
            logger.warn('Bots Blocked', exc_info=True, extra={'page': page, 'bot': self});
            return (None, Exception('Bot edits prohibited.'))

        try:
            result = page.save(str(proteinbox), summary, minor=True)

            self.text = page.edit()
            self.save()

            return (result, None)
        except MwClientError as e:
            client.captureException()
            error = e
        return (None, error)



