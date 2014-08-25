from datetime import timedelta


CELERYBEAT_SCHEDULE = {
    'update-template-pages-index': {
        'task': 'genewiki.wiki.tasks.collect_template_pages',
        'schedule': timedelta(days=1)
    },
    'update-articles': {
        'task': 'genewiki.wiki.tasks.update_all_infoboxes',
        'schedule': timedelta(days=2)
    },
    'update-g2p': {
        'task': 'genewiki.wiki.tasks.update_gene2pubmed',
        'schedule': timedelta(days=7)
    }
}
