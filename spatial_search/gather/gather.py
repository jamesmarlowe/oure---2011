#
## gather.py
## screen scrape yellow pages for data to store
#

from models import *
from excel import *
from django.http import HttpResponse, HttpResponseRedirect
import random
import urllib2
import re
from django.contrib.gis.geos import Point
import contextlib
from django.db.models import get_model, get_models, get_app
from django.shortcuts import render_to_response
import itertools
import operator
import zcurve
import sys
import hashlib
from time import time
try:
    import cPickle as pickle
except:
    import pickle
import pprint
from ZODB import FileStorage, DB
import database
import transaction
from nltk.corpus import wordnet as wn

def fix_database(request):
    
    for i in Building.objects.all():
        Listing.objects.create(name=i.name,number=i.number,street=i.street,city=i.city,state=i.state,latitude=i.location.y,longitude=i.location.x,zip=i.zipcode.code,category=None if not i.category.all() else i.category.all()[0],keyword=None if not i.keywords.all( ) else i.keywords.all()[0])
    #Listing.objects.all().delete()
    i = Listing.objects.all().count()
    return HttpResponse(i)

def output_database_to_excel(request):
    results = Listing.objects.select_related().values('name','number','street','city','state','latitude','longitude','category__category','keyword__keyword')
    writeToFile(results,'BetterListings')
    return HttpResponse("Success writing to file")

def output_categories_to_excel(request):
    results = Categories.objects.all().values()
    writeToFile(results,'categories')
    return HttpResponse("Success writing to file")

def output_keywords_to_excel(request):
    results = Keywords.objects.all().values()
    writeToFile(results,'keywords')
    return HttpResponse("Success writing to file")

def testwordnet(request,search):
    results = wn.synsets(search)[0]
    return HttpResponse(results.definition)

def wordnetcompare(request, word1, word2):
    word1 = wn.synsets(word1)[0]
    word2 = wn.synsets(word2)[0]
    lchresults1 = word1.lch_similarity(word2)
    lchresults2 = word2.lch_similarity(word1)
    wupresults1 = word1.wup_similarity(word2)
    wupresults2 = word2.wup_similarity(word1)
    pathresults1 = word1.path_similarity(word2)
    pathresults2 = word2.path_similarity(word1)
    #return HttpResponse(results1)
    return HttpResponse("<table border='1'><tr><td>wup_results-1:"+str(wupresults1)+"</td><td>wup_results-2:"+str(wupresults2)+"</td></tr><tr><td>lch_results-1:"+str(lchresults1)+"</td><td>lch_results-2:"+str(lchresults2)+"</td></tr><tr><td>path_results-1:"+str(pathresults1)+"</td><td>path_results-2:"+str(pathresults2)+"</td></tr></table>")

def testdb(request):
    storage = FileStorage.FileStorage('listingsc.fs')
    db = DB(storage)
    conn = db.open()
    dbroot = conn.root()
    
    # Ensure that a 'listingdb' key is present
    # in the root
    if not dbroot.has_key('listingdb'):
        from BTrees.OOBTree import OOBTree
        dbroot['listingdb'] = OOBTree()
        
    userdb = dbroot['listingdb']

    lists = Listing.objects.all().values()
    minlat = min([l['latitude'] for l in lists])
    minlng = min([l['longitude'] for l in lists])
    for l in lists:
        #return HttpResponse(l)
        key1 = int(l['latitude']*1000000-minlat*1000000)
        key2 = int(l['longitude']*1000000-minlng*1000000)
        #userdb[hashlib.sha224(str(l['keyword_id'])).hexdigest()[:8]+str(zcurve.interleave2(key1,key2)).zfill(9)]=l
        userdb[hashlib.sha224(str(l['category_id'])).hexdigest()[:8]]=l
        # Commit the change
    transaction.commit()
    db.close()
    return HttpResponse("woo i guess")

def testzcurve(request):
    
    zcurvevals = [[{str(i)+','+str(j):zcurve.interleave2(i,j)} for i in range(0,11)] for j in range(0,11)]

    return HttpResponse(zcurvevals)

def testPickle(request):
    listing = database.Listing()
    listing.name = Building.objects.all()[0].name
    listing.number = Building.objects.all()[0].number
    listing.street = Building.objects.all()[0].street
    listing.city = Building.objects.all()[0].city
    listing.state = Building.objects.all()[0].state
    listing.location = zcurve.interleave2(int(Building.objects.all()[0].location.x*10000000),int(Building.objects.all()[0].location.y*10000000))
    listing.zipcode = Building.objects.all()[0].zipcode
    #for key, value in :
    #    listing.key = value
    #listing.location = zcurve.interleave2(listing.location.x, listing.location.y)
    pickle.dump( listing, open( "save.p", "wb" ), -1 )
    
    return HttpResponse(sys.maxint)

#
## \brief query yahooapis for the city/state given a lat/long
## \return a city and state
#
def findCityState(latitude, longitude):#rate limit of 50,000 per day
    #http://where.yahooapis.com/geocode?q=38.898717,+-77.035974&gflags=R&appid=[yourappidhere]
    url = 'http://where.yahooapis.com/geocode?q='
    url += str(latitude)+',+'+str(longitude)
    url += '&gflags=R&appid=mXhIP762'

    response = urllib2.urlopen(url)
    vals = response.read()
    city = re.search("<city>(.*)</city>",vals)
    state = re.search("<statecode>(.*)</statecode>",vals)
    return city.groups(1)[0], state.groups(1)[0]

#
## \brief query yahooapis for the lat/long given a address/city/state
## \return latitude and longitude
#
def findLatLong(number, street, city, state):#rate limit of 50,000 per day
    #http://where.yahooapis.com/geocode?q=1600+Pennsylvania+Avenue,+Washington,+DC&appid=[yourappidhere]
    url = 'http://where.yahooapis.com/geocode?q='
    url += str(number)+'+'+str(street)+',+'+str(city)+',+'+str(state)
    url += '&appid=mXhIP762'
    
    response = urllib2.urlopen(url)
    vals = response.read()
    latitude = re.search("<latitude>(.*)</latitude>",vals)
    longitude = re.search("<longitude>(.*)</longitude>",vals)
    return latitude.groups(1)[0], longitude.groups(1)[0]

#
## \brief adds categories to database with their similar categories
## \return nothing
#
def AddCategories(categorylist):
    for c in categorylist:
        category = Categories.objects.get_or_create(category=str(c))[0]
        for c2 in categorylist:
            if not Categories.objects.filter(similar=Categories.objects.get_or_create(category=str(c2))[0]).exists():
                category.similar.add(Categories.objects.get_or_create(category=str(c2))[0])

#
## \brief gets the infomation about locations matching the keyword from yellowpages for city/state from first <pages> pages of results
## \return a dictionary of all the location's infomation
#
def GetAddresses(city, statecode, keyword, pages):
    
    #<h3 class="business-name fn org">
    #<span class="inaccuracy">
    outer_regex = re.compile('<h3 class="business-name fn org">(.*?)<span class="inaccuracy">',re.DOTALL)

    if pages > 0:
        #http://www.yellowpages.com/chicago-il/auto-insurance
        with contextlib.closing(urllib2.urlopen("http://www.yellowpages.com/"+str(city)+"-"+str(statecode)+'/'+str(keyword))) as content:
            content = content.read()
        #content = urllib2.urlopen("http://www.yellowpages.com/"+str(city)+"-"+str(statecode)+'/'+str(keyword)).read()
            listings = outer_regex.findall(content)

    for n in range(2,pages+1):
        #http://www.yellowpages.com/chicago-il/auto-insurance?page=2
        with contextlib.closing(urllib2.urlopen("http://www.yellowpages.com/"+str(city)+"-"+str(statecode)+'/'+str(keyword)+'?page='+str(n))) as urlcontent:
            content = urlcontent.read()
            urlcontent.close()
        #content = urllib2.urlopen("http://www.yellowpages.com/"+str(city)+"-"+str(statecode)+'/'+str(keyword)+'?page='+str(n)).read()
            listings += outer_regex.findall(content)

    #<span class="street-address">311 W Superior St Ste 500,</span>
    #<span class="city-state"><span class="locality">Chicago</span>,
    #<span class="region">IL</span>
    #<span class="postal-code">60654</span></span>
    #<span class="latitude">41.93803</span>
    #<span class="longitude">-87.806763</span>
    name_regex = re.compile('>(.*?)<',re.DOTALL)
    number_regex = re.compile('class="street-address">.*?(\d{1,5}).*?<',re.DOTALL)
    street_regex = re.compile('class="street-address">.*?\d{1,5}(.*?)<',re.DOTALL)
    city_regex = re.compile('class="locality".*?>(.*?)<',re.DOTALL)
    state_regex = re.compile('class="region".*?>(.*?)<',re.DOTALL)
    lat_regex = re.compile('class="latitude">(.*?)<',re.DOTALL)
    long_regex = re.compile('class="longitude">(.*?)<',re.DOTALL)
    zip_regex = re.compile('class="postal-code".*?>(.*?)<',re.DOTALL)
    #<ul class="business-categories">
    #<li><a href="/chicago-il/auto-insurance?refinements%5Bheadingtext%5D=Auto+Insurance" rel="nofollow">Auto Insurance</a>, </li>
    #<li><a href="/chicago-il/auto-insurance?refinements%5Bheadingtext%5D=Homeowners+Insurance" rel="nofollow">Homeowners Insurance</a>, </li>
    #<li><a href="/chicago-il/auto-insurance?refinements%5Bheadingtext%5D=Insurance" rel="nofollow">Insurance</a>
    #</div>
    categories_regex = re.compile('class="business-categories".*?>(.*?)</div>',re.DOTALL)
    category_regex = re.compile('<li><a.*?>(.*?)</a>',re.DOTALL)

    locations = []
    if listings:
        for listing in listings:
            categories = None
            try:
                categories = categories_regex.search(listing).group(1)
            except:
                pass
            category = list()
            if categories:
                category = list(category_regex.findall(categories))
                AddCategories(category)
                    
            #if one of these fails, don't add the record, just skip it
            try:
                name = name_regex.search(listing).group(1).rstrip('\n')[:100]
                number = number_regex.search(listing).group(1).rstrip('\n')
                street = street_regex.search(listing).group(1).rstrip('\n').replace(",", "")[:100]
                city = city_regex.search(listing).group(1).rstrip('\n')
                state = state_regex.search(listing).group(1).rstrip('\n')
                latitude = lat_regex.search(listing).group(1).rstrip('\n')
                longitude = long_regex.search(listing).group(1).rstrip('\n')
                zipcode = zip_regex.search(listing).group(1).rstrip('\n')
                locations += [{'name':name,'number':number, 'street':street, 'city':city, 'state':state, 'latitude':latitude, 'longitude':longitude, 'zipcode':zipcode, 'category':category}]
            except:
                pass

    return locations
    
#
## \brief gets the trending keywords from yellowpages for city/state from first <pages> pages of results
## \return a list of all the categories
#
def GetKeywords(city, statecode, pages):
    
    #<li class="category"><a href="/chicago-il/florists">Florists Chicago</a></li>
    #<li class="category"><a href="/chicago-il/auto-insurance">Auto Insurance Chicago</a></li>
    regex = re.compile('class="category".*?/.*?/(.*?)\"')

    #http://www.yellowpages.com/chicago-il
    content = urllib2.urlopen("http://www.yellowpages.com/"+str(city)+"-"+str(statecode)).read()
    keywords = regex.findall(content)

    #<ul class="categories-list">
    #<div class="pagination clearfix">
    outer_regex = re.compile('class="categories-list"(.*?)<div class="pagination clearfix">',re.DOTALL)

    #<li><a href="/chicago-il/dating-services">Dating Services Chicago</a></li>
    #<li><a href="/chicago-il/self-storage">Self Storage Chicago</a></li>
    inner_regex = re.compile('li.*?/.*?/(.*?)\".*?\/li')

    for n in range(1,pages):
        #http://www.yellowpages.com/chicago-il/trends/1
        content = urllib2.urlopen("http://www.yellowpages.com/"+str(city)+"-"+str(statecode)+"/trends/"+str(n)).read()
        outer = outer_regex.search(content)
        if outer:
            try:
                keywords += inner_regex.findall(outer.group(1))
            except:
                pass

    return keywords

#
## \brief userfacing function mapped to url that uses the other functions to gather the information I need
## \return a response to the user so that it is obvious if it fails
#
def gather(request):
    keywords = GetKeywords("chicago","il", 5)
    random.shuffle(keywords)
    #[Categories(category=str(c)).save() for c in categories if not Categories.objects.filter(category=c).exists()]
    for c in keywords:
        for b in GetAddresses("chicago", "il", str(c), 5):
            #current = Building.objects.get_or_create(name=str(b['name']),number=b['number'],street=str(b['street']),city=str("chicago"),state=str("il"),location=Point(float(b['longitude']),float(b['latitude'])))
            zipcode = Zipcode.objects.get_or_create(code=b['zipcode'])[0]
            #zipcode = Zipcode.objects.get(code=b['zipcode'])
            current = Building.objects.get_or_create(name=str(b['name']),number=b['number'],street=str(b['street']),city=str("chicago"),state=str("il"),location=Point(float(b['longitude']),float(b['latitude'])),zipcode = zipcode)[0]
            #current = Building.objects.get(name=str(b['name']),number=b['number'],street=str(b['street']),city=str("chicago"),state=str("il"),location=Point(float(b['longitude']),float(b['latitude'])),zipcode = zipcode)
            keyword = Keywords.objects.get_or_create(keyword=str(c))[0]
            #keyword = Keywords.objects.get(keyword=str(c))
            current.keywords.add(keyword)
            for c2 in b['category']:
                current.category.add(Categories.objects.get_or_create(category=str(c2))[0])
    #[[Building(name=b['name'],number=b['number'],street=b['street'],city='chicago',state='mo',location=[x=b['longitude'],y=b['latitude']],category=str(c),zipcode=Zipcode.objects.get_or_create(code=b['zipcode'])).save() for b in GetAddresses("chicago", "il", str(c), 1)] for c in categories]
    #return HttpResponse([str(c)+' ' for c in categories])
    #buildings = []
    #buildings = [GetAddresses("chicago", "il", str(c), 1) for c in categories]
    return HttpResponse([c for c in keywords])

def listModels(request):
    return render_to_response('map2.html', locals())
    
def listModels2(request):
    import collections

    data = []
    data += [{'firstname': 'John', 'lastname': 'Smith'}]
    data += [{'firstname': 'Samantha', 'lastname': 'Smith'}]
    data += [{'firstname': 'shawn', 'lastname': 'Spencer'}]
    
    
    list1 = [{'name':m._meta.object_name,'field':[f.name for f in m._meta.fields]} for m in get_models(get_app("gather"))]

    return HttpResponse([l for l in list1])

def makeMap(request):
    listings = Building.objects.order_by('?')[:1000]
    keywords = Keywords.objects.order_by('keyword')
    allcategories = Categories.objects.order_by('category').values('category')
    zipcodes = Zipcode.objects.order_by('code')
    if request.method == 'GET':
        try:
            lat = request.GET['lat']
            lng = request.GET['lng']
            lists = Listing.objects.all().values()
            minlat = min([l['latitude'] for l in lists])
            minlng = min([l['longitude'] for l in lists])

            key1 = int(float(lat)*1000000-minlat*1000000)
            key2 = int(float(lng)*1000000-minlng*1000000)
            search = zcurve.interleave2(key1,key2)
            storage = FileStorage.FileStorage('listings2.fs')
            db = DB(storage)
            conn = db.open()
            dbroot = conn.root()
            userdb = dbroot['listingdb']
            listings = []

            for i in range(search-100000,search+10000):
                try:
                    listings.append(userdb[int(i)])
                except:
                    pass

            db.close()
            return render_to_response('map2.html', locals())
        except:
            pass
    return render_to_response('map.html', locals())

def mapSearch(request, search):
    keywords = Keywords.objects.order_by('keyword')
    categories = Categories.objects.order_by('category')
    zipcodes = Zipcode.objects.order_by('code')
    listings = []
    timings = []
    for i in range(1,10):
        start = time()
        #try:
            #isearch = int(search)
            #storage = FileStorage.FileStorage('listings.fs')
            #db = DB(storage)
            #conn = db.open()
            #dbroot = conn.root()
            #userdb = dbroot['listingdb']
            #listings.append(userdb[isearch])
            #search = isearch
            #db.close()
        #except:
            #pass
        #try:
            #csearch = Categories.objects.filter(category=search)[0].id
            #storage = FileStorage.FileStorage('listingsc.fs')
            #db = DB(storage)
            #conn = db.open()
            #dbroot = conn.root()
            #userdb = dbroot['listingdb']
            #listings.append(userdb[hashlib.sha224(str(csearch)).hexdigest()[:8]])
            #search = csearch
            #db.close()
        #except:
            #pass
        try:
            ksearch = Keywords.objects.filter(keyword=search)[0].id
            storage = FileStorage.FileStorage('listingsk.fs')
            db = DB(storage)
            conn = db.open()
            dbroot = conn.root()
            userdb = dbroot['listingdb']
            listings.append(userdb[hashlib.sha224(str(ksearch)).hexdigest()[:8]])
            search = ksearch
            db.close()
        except:
            pass
        T = time() - start
        start = time()
        try:
            ksearch = Keywords.objects.filter(keyword=search)[0].id
        except:
            pass
        l = Building.objects.filter(number=612)
        listings.append(l[:0])
        search = 612
        N = time() - start
        timings +=[{'Tree-Time:':T, 'MYSQL-Time:':N}]
    writeToFile(timings,'search_times')
    
    listings = listings[:1000]

    return render_to_response('map2.html', locals())

def timestuff(request, search):
    start = time()
    (A)
    T = time() - start
    return T