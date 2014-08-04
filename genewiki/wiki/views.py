from django.template import RequestContext
from django.shortcuts import get_object_or_404, render_to_response, redirect
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.decorators.http import require_http_methods
from django.shortcuts import redirect
from django.http import HttpResponse
from django.conf import settings

from genewiki.wiki.models import Article

def home(request, page_num=1):
    article_list = Article.objects.all()

    article_list_paginator = Paginator(article_list, 200)
    try:
        articles = article_list_paginator.page(page_num)
    except PageNotAnInteger:
        articles = article_list_paginator.page(1)
    except EmptyPage:
        articles = article_list_paginator.page(paginator.num_pages)

    return render_to_response('wiki/index.jade', {'articles' : articles}, context_instance=RequestContext(request))

@require_http_methods(['POST'])
def article_update(request, article_id):
    article = get_object_or_404(Article, pk = article_id)
    article.update()
    return HttpResponse(200)

def article_create(request, entrez_id):
    print entrez_id
    return render_to_response('wiki/create.jade', {}, context_instance=RequestContext(request))

