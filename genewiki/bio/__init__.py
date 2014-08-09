# Make sure redis is started on app load
from genewiki.bio.g2p_redis import init_redis
init_redis()

