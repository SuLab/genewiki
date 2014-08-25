from __future__ import absolute_import

from raven.contrib.django.raven_compat.models import client

from genewiki.wiki.models import Bot, Article

from celery import task


@task()
def collect_template_pages():
    bot = Bot.objects.get_pbb()
    bot.fetch_update_articles()


@task()
def update_all_infoboxes():
    for infobox in Article.objects.all_infoboxes():
        infobox.update()


@task()
def update_articles(update_list):
    for pk in update_list:
        try:
            article = Article.objects.get(pk=pk)
            article.update()
        except Exception:
            client.captureException()

