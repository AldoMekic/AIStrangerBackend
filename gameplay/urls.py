from django.urls import path, include
from rest_framework.routers import DefaultRouter
# This is a relative import. It looks for api.py in the SAME folder (gameplay)
from .api import GameViewSet 

router = DefaultRouter()
router.register(r'games', GameViewSet, basename='game')

urlpatterns = [
    path('', include(router.urls)),
]