from django.dispatch import receiver
from django.db.models.signals import post_save
from django.conf import settings

from genewiki.wiki.models import Article

@receiver(post_save, sender = Article)
def message_post_save(sender, instance, **kwargs):

    article = instance
    pass

