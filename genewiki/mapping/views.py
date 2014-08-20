from django.shortcuts import redirect

from rest_framework import viewsets
from genewiki.mapping.models import Relationship, Lookup
from genewiki.mapping.serializers import RelationshipSerializer


class RelationshipViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = Relationship.objects.all()
    serializer_class = RelationshipSerializer


def wiki_mapping(request, entrez_id):
    relationship = Relationship.objects.filter(entrez_id=entrez_id).first()
    if relationship:
        Lookup.objects.create(relationship=relationship)
        return redirect(u'http://en.wikipedia.org/wiki/{0}'.format(relationship.title))
    else:
        return redirect('genewiki.wiki.views.article_create', entrez_id)

