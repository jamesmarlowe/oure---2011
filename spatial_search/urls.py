from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    # (r'^spatial_search/', include('spatial_search.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    (r'^admin/', include(admin.site.urls)),

    url(r'^models/$','gather.gather.listModels2', name='models'),

    url(r'^gather/$','gather.gather.gather', name='gather'),
    
    url(r'^test/$','gather.gather.listModels', name='test'),

    url(r'^map/$','gather.gather.makeMap', name='map'),

    url(r'^map/(?P<search>\w+)$','gather.gather.mapSearch', name='mapsearch'),

    #url(r'^map/?lat=(-?\d+\.\d)&lng=(-?\d+\.\d)$','gather.gather.mapSearch2', name='mapsearch2'),

    url(r'^pickle/$','gather.gather.testPickle', name='picklepage'),

    url(r'^zcurve/$','gather.gather.testzcurve', name='zcurvepage'),

    url(r'^database/$','gather.gather.testdb', name='databasepage'),

    url(r'^wordnet/(?P<search>\w+)$','gather.gather.testwordnet', name='wordnetpage'),

    url(r'^wordnet/(?P<word1>\w+)/(?P<word2>\w+)$','gather.gather.wordnetcompare', name='wordnetcomparepage'),

    url(r'^output/excel$','gather.gather.output_database_to_excel', name='output_excel'),

    url(r'^outputc/excel$','gather.gather.output_categories_to_excel', name='outputc_excel'),

    url(r'^outputk/excel$','gather.gather.output_keywords_to_excel', name='outputk_excel'),

    url(r'^fix$','gather.gather.fix_database', name='fixdatabase'),
)
