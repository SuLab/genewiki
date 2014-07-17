from __future__ import absolute_import

from django.conf import settings

from genewiki.wiki.models import Bot, Article

from celery import task


@task()
def collect_template_pages():
    bot = Bot.objects.filter(service_type = 'wiki').first()
    connection = bot.connection()
    pages = connection.Pages['Template:GNF_Protein_box']
    for page in pages.embeddedin('10'):
        print page.name
        if 'Template:PBB/' in page.name:
            article, created = Article.objects.get_or_create(title = page.name)
            article.text = page.edit()
            article.article_type = Article.INFOBOX
            article.save()

@task()
def run():

    for infobox in Article.objects.all():
        try:
            # 1) The updated ProteinBox object
            # 2) the delta message
            # 3) the delta dictionary
            updated, summary, updatedfields = self.update(infobox)
        except Exception as err:
            message = 'Failed to edit {title}. Error: {error}'.format(
                    title=infobox.name, error=err)

        # This is where data is written
        result, err = infobox.write(updated, summary)
        message = ''
        if result:
            if 'oldrevid' in result:
                message = (
                    '''Successfully edited {title}:
Old revision: {old}
New revision: {new}'''
                    .format(title = result['title'],
                            old = result['oldrevid'],
                            new = result['newrevid']))
                for field in updatedfields:
                    message = (message+"\n{}: '{}' => '{}'"
                               .format(field,
                                       updatedfields[field][0],
                                       updatedfields[field][1]))
            else:
                message = ('''No change was made to {title}.'''
                           .format(title=result['title']))



