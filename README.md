genewiki
========

The GeneWiki Project



* `./manage.py celeryd -v 2 -B -E -l INFO`


from genewiki.pbb.models import *
bot = Bot.objects.get(pk=2)
bot.update_articles()
