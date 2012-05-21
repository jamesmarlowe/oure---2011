from models import *
from django.db.models import get_models, get_app
from django.contrib import admin
from django.contrib.admin.sites import AlreadyRegistered

def autoregister(*app_list):
    for name in app_list:
        models = get_app(name)
        for model in get_models(models):
            try:
                admin.site.register(model)
            except:
                pass
                
            autoregister('gather')
                