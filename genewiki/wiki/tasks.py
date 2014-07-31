from __future__ import absolute_import

from django.conf import settings

from genewiki.wiki.models import Bot, Article

from celery import task


@task()
def collect_template_pages():
    bot = Bot.objects.filter(service_type = 'wiki').first()
    bot.update_articles()


@task()
def update_all_infoboxes():
    for infobox in Article.objects.all(article_type = Article.INFOBOX):
        infobox.update()

