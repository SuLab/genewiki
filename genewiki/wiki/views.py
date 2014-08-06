from django.template import RequestContext
from django.shortcuts import get_object_or_404, render_to_response, redirect
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.decorators.http import require_http_methods
from django.shortcuts import redirect
from django.http import HttpResponse
from django.conf import settings

from genewiki.mapping.models import Relationship

from genewiki.wiki.models import Article
from genewiki.wiki.tasks import update_articles

from datetime import datetime, timedelta


def home(request, page_num=1):
    article_list = Article.objects.all()

    article_list_paginator = Paginator(article_list, 200)
    try:
        articles = article_list_paginator.page(page_num)
    except PageNotAnInteger:
        articles = article_list_paginator.page(1)
    except EmptyPage:
        articles = article_list_paginator.page(paginator.num_pages)

    updated = {
        'hour': Article.objects.filter(updated__gt = datetime.now() - timedelta(hours = 1)).count(),
        'day': Article.objects.filter(updated__gt = datetime.now() - timedelta(days = 1)).count(),
        'week': Article.objects.filter(updated__gt = datetime.now() - timedelta(weeks = 1)).count(),
        'month': Article.objects.filter(updated__gt = datetime.now() - timedelta(weeks = 4)).count(),
    }
    return render_to_response('wiki/index.jade', {'articles' : articles, 'updated' : updated}, context_instance=RequestContext(request))


@require_http_methods(['POST'])
def update(request):
    limit = request.POST.get('update_count', None)
    if limit:
        update_list = Article.objects.order_by('updated').values_list('pk', flat=True).all()[:int(limit)]
        update_articles.apply_async(args = [update_list,])
    else:
        pass

    return HttpResponse(200)


@require_http_methods(['POST'])
def article_update(request, article_id):
    article = get_object_or_404(Article, pk = article_id)
    article.update()
    return HttpResponse(200)


@require_http_methods(['GET', 'POST'])
def article_create(request, entrez_id):
    uploadopt = request.POST.get('upload', None)
    validuploadopts = ['templatename', 'name', 'symbol', 'altsym']

    # Attempt to create all the wiki pages
    results = create(entrez, True)
    if results:
        titles = results['titles']
        checked = results['checked']

        if request.method == 'POST' and uploadopt in validuploadopts:

            title = titles[uploadopt] if not checked[titles[uploadopt]] else None
            if title:
                Relationship.objects.create(entrez_id = entrez, title_url = title)

                content = results['template'] if title.startswith('Template:PBB/') else results['stub']
                genewiki = GeneWiki()
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
        else:
            # Create a template
            templateExists = checked[titles['templatename']]
            pageAtNameExists = checked[titles['name']]
            pageAtSymExists = checked[titles['symbol']]
            pageAtAltSymExists = checked[titles['altsym']]
            titleExists = (pageAtNameExists or pageAtSymExists or pageAtAltSymExists)
            workingTitle = "{} ({})".format(titles['symbol'], titles['name'])
            existingTitle = titles['altsym'] if pageAtAltSymExists else titles['name'] if pageAtNameExists else titles['symbol'] if pageAtSymExists else titles['altsym']
            vals = {
                'entrez': entrez,
                'temp_status': 'exists' if templateExists else 'missing',
                'temp_status_str': 'exists' if templateExists else 'does not exist',
                'temp_action': 'edit' if templateExists else 'create',
                'temp_view': 'visible' if templateExists else 'hidden',
                'template': results['template'],
                'title': existingTitle,
                'warning_stat': 'visible' if titleExists else 'hidden',
                'gene_name': titles['name'] if pageAtNameExists else titles['name'],
                'name_status': 'exists' if pageAtNameExists else 'missing',
                'gene_sym': titles['symbol'],
                'sym_status': 'exists' if pageAtSymExists else 'missing',
                'gene_sym_2': titles['altsym'],
                'sym2_status': 'exists' if pageAtAltSymExists else 'missing',
                'suggestion': existingTitle if existingTitle else titles['name'],
                'title_stat_vis': 'visible' if not titleExists else 'hidden',
                'title_status': 'exists' if titleExists else 'valid',
                'stub_action': 'edit' if titleExists else 'create',
                'stub_act_status': '',
                'action_title': titles['name'],
                'stub_view': 'visible' if titleExists else 'hidden',
                'stub': results['stub'] }
            print body.format(**vals)
            return render_to_response('wiki/create.jade', vals, context_instance=RequestContext(request))

    else:
        return HttpResponse('Invalid or missing entrez id.')


