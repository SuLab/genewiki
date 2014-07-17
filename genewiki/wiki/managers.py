from django.db import models

class BotManager(models.Manager):

    def get_random_bot(self):
        '''
          This is documented as being potentially expensive, we may want to do something like
          http://stackoverflow.com/a/6405601 instead
        '''
        return self.filter(service_type = 'wiki').order_by('?')[0]



class ArticleManager(models.Manager):

  def get_infobox(self, entrez):
          '''
            Returns the current infobox for given entrez, or None if it does not
            exist.
          '''
          title = 'Template:PBB/'+entrez

          res = self.filter(title = title).first()
          if res:
            return res

          else:
            bot = Bot.objects.get_random_bot()
            conn = bot.connection()
            for page in conn.Pages[title]:
                article, created = Article.objects.get_or_create(title = page.page_title, article_type = 'template', bot = self)
                article.save()
                return article

