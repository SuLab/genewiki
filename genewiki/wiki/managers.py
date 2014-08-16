from django.db import models

class BotManager(models.Manager):

    def get_random_bot(self):
        '''
          This is documented as being potentially expensive, we may want to do something like
          http://stackoverflow.com/a/6405601 instead
        '''
        return self.filter(service_type='wiki').order_by('?')[0]


class ArticleManager(models.Manager):

    def get_infobox_for_entrez(self, entrez):
        '''
            Returns the current infobox for given entrez, or None if it does not
            exist.
        '''
        Article = self.model
        title = 'Template:PBB/{0}'.format(entrez)
        return self.filter(title=title).first()

