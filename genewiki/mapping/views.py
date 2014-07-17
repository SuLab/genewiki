from django.shortcuts import render

from rest_framework import viewsets
from genewiki.mapping.models import Relationship
from genewiki.mapping.serializers import RelationshipSerializer


class RelationshipViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = Relationship.objects.all()
    serializer_class = RelationshipSerializer




# get '/map/?:id?' do |id|
#   id = id || params[:id]
#   if id.nil?
#     content_type :json
#     Mapping.all().to_json(:only => [:entrez_id, :title_url, :updated])
#   elsif (id =~ /\D/).nil?
#     map = Mapping.first(:entrez_id => id) rescue nil
#       map.update(:hits => map[:hits]+1) if !map.nil?
#     map[:title_url].to_s rescue nil
#   else
#     map = Mapping.first(:title_url => id) rescue nil
#       map.update(:hits => map[:hits]+1) if !map.nil?
#     map[:entrez_id].to_s rescue nil
#   end
# end
# 
# post '/map' do
#   if !params[:entrez_id].nil? && !params[:title_url].nil?
#     (Mapping.first_or_create(:entrez_id => params[:entrez_id]))
#     .update(
#       :entrez_id => params[:entrez_id],
#       :title_url => params[:title_url],
#       :updated => DateTime.now)
#   end
# end
# 
