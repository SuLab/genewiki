from django.template import RequestContext
from django.shortcuts import get_object_or_404, render_to_response
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse

from genewiki.mapping.models import Relationship

from genewiki.wiki.models import Article
from genewiki.wiki.tasks import update_articles

from genewiki.wiki.textutils import create

from datetime import datetime, timedelta


def home(request, page_num=1):
    article_list = Article.objects.all()

    article_list_paginator = Paginator(article_list, 200)
    try:
        articles = article_list_paginator.page(page_num)
    except PageNotAnInteger:
        articles = article_list_paginator.page(1)
    except EmptyPage:
        articles = article_list_paginator.page(article_list_paginator.num_pages)

    updated = {
        'hour': Article.objects.filter(updated__gt=datetime.now() - timedelta(hours=1)).count(),
        'day': Article.objects.filter(updated__gt=datetime.now() - timedelta(days=1)).count(),
        'week': Article.objects.filter(updated__gt=datetime.now() - timedelta(weeks=1)).count(),
        'month': Article.objects.filter(updated__gt=datetime.now() - timedelta(weeks=4)).count(),
    }
    return render_to_response('wiki/index.jade', {'articles': articles, 'updated': updated}, context_instance=RequestContext(request))


@require_http_methods(['POST'])
def update(request):
    limit = request.POST.get('update_count', None)
    if limit:
        update_list = Article.objects.order_by('updated').values_list('pk', flat=True).all()[:int(limit)]
        update_articles.apply_async(args=[update_list, ])
    else:
        pass

    return HttpResponse(200)


@require_http_methods(['POST'])
def article_update(request, article_id):
    article = get_object_or_404(Article, pk=article_id)
    article.update()
    return HttpResponse(200)


@require_http_methods(['GET', 'POST'])
def article_create(request, entrez_id):
    results = create(entrez_id, True)

    if request.method == 'GET' and results:
        titles = results.get('titles')
        return render_to_response('wiki/create.jade', {
            'templateExists': titles['templatename'],
            'titleExists': (titles.get('name') or titles.get('symbol') or titles.get('altsym')),
            'existingTitle': titles['altsym'] if titles.get('altsym') else titles['name'] if titles.get('name') else titles['symbol'] if titles.get('symbol') else titles['altsym'],
            'results': results,
            'titles': titles,
            'entrez': entrez_id,}, context_instance=RequestContext(request))


    if request.method == 'POST':
        uploadopt = request.POST.get('upload', None)
        validuploadopts = ['templatename', 'name', 'symbol', 'altsym']
        titles = results.get('titles')
        checked = results.get('checked')

        if uploadopt in validuploadopts:
            title = titles[uploadopt] if not checked[titles[uploadopt]] else None
            if title:
                Relationship.objects.create(entrez_id=entrez_id, title_url=title)
                content = results['template'] if title.startswith('Template:PBB/') else results['stub']
                retcode = genewiki.upload(title, content)
                # create corresponding talk page with appropriate project banners
                if not title.startswith('Template:PBB/'):
                    talk_title = "Talk:" + title
                    talk_content = """{{WikiProjectBannerShell|
                                      {{WikiProject Gene Wiki|class=stub|importance=low}}
                                      {{Wikiproject MCB|class=stub|importance=low}}
                                    }}"""
                    talk_retcode = genewiki.upload(talk_title, talk_content)
                else:
                    talk_retcode = 0
                # return code is 0 if both page and talk page write was successful; 1 if either failed
                print (retcode or talk_retcode)
            else:
                return HttpResponse('Article or template already exists.')

        elif uploadopt:
            return HttpResponse('Invalid upload option.')



    # If no conditions met
    return HttpResponse('No good :(')

