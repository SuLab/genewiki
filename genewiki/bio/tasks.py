from __future__ import absolute_import

from genewiki.bio.g2p_redis import init_redis, import_to_redis, download_g2p

from celery import task


@task()
def update_gene2pubmed():
    '''
        Downloads the most recent gene2pubmed file and imports into redis.
        Returns a connection to the redis server used (uses default options).
    '''

    r = init_redis()
    import_to_redis(download_g2p(), r)

