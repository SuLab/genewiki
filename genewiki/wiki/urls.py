from django.conf.urls import patterns, url


urlpatterns = patterns('genewiki.wiki.views',
    url(r'^$', r'home'),
    url(r'^page/(?P<page_num>\d+)/$', r'home'),
    url(r'^update/$', r'update'),

    url(r'^article/create/(?P<entrez_id>\d+)/$', r'article_create'),
    url(r'^article/(?P<article_id>\d+)/update/$', r'article_update'),
)
