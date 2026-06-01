

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import KhaltiPaymentViewSet, ProductViewSet, CategoryViewSet, CartViewSet, OrderViewSet,ProductImageViewSet

# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'cart', CartViewSet, basename='cart')
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'product-images', ProductImageViewSet, basename='product-image')
router.register(r'khalti-payment', KhaltiPaymentViewSet, basename='khalti-payment')

# The API URLs are now determined automatically by the router.
urlpatterns = [
    path('', include(router.urls)),
]