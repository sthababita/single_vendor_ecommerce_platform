from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.decorators import action

from .models import Category, Product, Cart, CartItem, Order, OrderItem
from .serializers import (
    CategorySerializer, ProductSerializer, 
    CartSerializer, CartItemSerializer, OrderSerializer, AddToCartSerializer
)

# 1. PRODUCT VIEWSET (Publicly readable, writeable only by Admin/Staff)
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.filter(is_active=True).order_by('-created_at')
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    lookup_field = 'slug' # Keeps API endpoints URL SEO-friendly via slugs instead of IDs!


# 2. CATEGORY VIEWSET (Publicly readable)
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    lookup_field = 'slug'


# 3. SHOPPING CART VIEWSET (Private per active log-in session)
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Cart, CartItem, Product
from .serializers import CartSerializer, AddToCartSerializer

class CartViewSet(viewsets.ModelViewSet):
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]

    # Guarantees users can only access their personal cart ecosystem
    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user)

    # 🔄 Dynamically switches form layouts in the browsable API screen
    def get_serializer_class(self):
        if self.action == 'add_item':
            return AddToCartSerializer
        return self.serializer_class

    # Automatically creates an empty Cart model mapping if none exists for the user
    def list(self, request, *args, **kwargs):
        cart, created = Cart.objects.get_or_create(user=request.user)
        serializer = self.get_serializer(cart)
        return Response(serializer.data)

    # 🛒 Update the action inside base/views.py to look EXACTLY like this:
    @action(detail=False, methods=['post'], serializer_class=AddToCartSerializer) # 👈 ADD serializer_class HERE!
    def add_item(self, request):
        serializer = AddToCartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        cart, _ = Cart.objects.get_or_create(user=request.user)
        product_id = serializer.validated_data['product_id']
        quantity = serializer.validated_data['quantity']

        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)

        cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
        if not created:
            cart_item.quantity += quantity
        else:
            cart_item.quantity = quantity
        
        cart_item.save()
        return Response({"message": "Item added successfully"}, status=status.HTTP_200_OK)

# 4. ORDER VIEWSET (Handles checkouts and transaction logging)
class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).order_by('-created_at')

    # Converts Cart entries into an absolute checkout order record invoice
    def create(self, request, *args, **kwargs):
        user = request.user
        try:
            cart = Cart.objects.get(user=user)
        except Cart.DoesNotExist:
            return Response({"error": "No active cart found"}, status=status.HTTP_400_BAD_REQUEST)

        if not cart.items.exists():
            return Response({"error": "Cart is empty"}, status=status.HTTP_400_BAD_REQUEST)

        # Generate unique reference token properties
        import uuid
        order_number = f"ORD-{uuid.uuid4().hex[:8].upper()}"

        # Initialize Order
        order = Order.objects.create(
            user=user,
            order_number=order_number,
            total_amount=sum(item.quantity * item.product.price for item in cart.items.all()),
            order_status='pending'
        )

        # Move snapshot items from CartItem entries to OrderItem models
        for item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                unit_price=item.product.price # Captures structural transaction price snapshot
            )
            
            # Reduce inventory product stock count
            item.product.stock_quantity -= item.quantity
            item.product.save()

        # Flush out cart tracking elements once checkout processing registers
        cart.items.all().delete()

        serializer = self.get_serializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    

from rest_framework.parsers import MultiPartParser, FormParser
from .models import ProductImage
from .serializers import ProductImageSerializer

class ProductImageViewSet(viewsets.ModelViewSet):
    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer
    
    # 🔌 CRUCIAL: Tells Django to look for incoming image files, not just JSON text
    parser_classes = (MultiPartParser, FormParser)


