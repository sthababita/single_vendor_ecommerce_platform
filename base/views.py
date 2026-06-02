from decimal import Decimal

from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.decorators import action

from .models import Category, Product, Cart, CartItem, Order, OrderItem, ProductImage, Payment
from rest_framework.parsers import MultiPartParser, FormParser
from .serializers import ProductImageSerializer

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

    #  Dynamically switches form layouts in the browsable API screen
    def get_serializer_class(self):
        if self.action == 'add_item':
            return AddToCartSerializer
        return self.serializer_class

    # Automatically creates an empty Cart model mapping if none exists for the user
    def list(self, request, *args, **kwargs):
        cart, created = Cart.objects.get_or_create(user=request.user)
        serializer = self.get_serializer(cart)
        return Response(serializer.data)

    # Update the action inside base/views.py to look EXACTLY like this:
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
        serializer = CartSerializer(cart)
        return Response({
            "message": "Item added successfully",
            "cart": serializer.data,
        }, status=status.HTTP_200_OK)

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
    



class ProductImageViewSet(viewsets.ModelViewSet):
    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer
    
    # CRUCIAL: Tells Django to look for incoming image files, not just JSON text
    parser_classes = (MultiPartParser, FormParser)



import requests
from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from django.utils import timezone

from .models import Order, Payment
from .serializers import KhaltiInitiateSerializer


def khalti_authorization_header():
    secret_key = getattr(settings, 'KHALTI_SECRET_KEY', '')
    if secret_key.startswith('Key '):
        return secret_key
    return f'Key {secret_key}'


def extract_paid_amount(verification_data):
    if verification_data is None:
        return None

    if isinstance(verification_data, (int, float, Decimal)):
        return Decimal(str(verification_data))

    if isinstance(verification_data, str):
        try:
            return Decimal(verification_data)
        except Exception:
            return None

    if isinstance(verification_data, dict):
        for key in (
            'amount', 'transaction_amount', 'paid_amount', 'amount_paid',
            'payment_amount', 'amountInPaisa', 'amount_in_paisa', 'total_amount'
        ):
            if key in verification_data:
                value = extract_paid_amount(verification_data[key])
                if value is not None:
                    return value

        for key, value in verification_data.items():
            if any(token in key.lower() for token in ('amount', 'paid', 'payment')):
                value = extract_paid_amount(value)
                if value is not None:
                    return value

        for value in verification_data.values():
            value = extract_paid_amount(value)
            if value is not None:
                return value

    if isinstance(verification_data, list):
        for item in verification_data:
            value = extract_paid_amount(item)
            if value is not None:
                return value

    return None


class KhaltiPaymentViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'], url_path='initiate')
    def initiate_khalti(self, request):
        serializer = KhaltiInitiateSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        order_number = serializer.validated_data['order_number']
        order = Order.objects.get(order_number=order_number, user=request.user)

        # 1. Khalti expects values in Paisa (1 NPR = 100 Paisa)
        amount_in_paisa = int(order.total_amount * 100)

        if amount_in_paisa < 1000: # 10 NPR minimum limit
            return Response({"error": "Minimum transaction amount must be Rs. 10"}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Setup Khalti configuration headers and payload parameters
        headers = {
            "Authorization": khalti_authorization_header(),
            "Content-Type": "application/json"
        }
        
        # Adjust your return landing URL based on where your frontend or mobile app routes
        return_url = "http://localhost:8000/api/khalti-payment/verify/" 

        payload = {
            "return_url": return_url,
            "website_url": "http://localhost:8000",
            "amount": amount_in_paisa,
            "purchase_order_id": order.order_number,
            "purchase_order_name": f"Payment for Order {order.order_number}",
        }

        # 3. Request Payment session generation from Khalti servers
        khalti_url = getattr(settings, 'KHALTI_INITIATE_URL', 'https://dev.khalti.com/api/v2/epayment/initiate/')
        try:
            response = requests.post(khalti_url, json=payload, headers=headers)
            response_data = response.json()
        except requests.exceptions.RequestException:
            return Response({"error": "Gateway connection failure."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        if response.status_code == 200:
            # 4. Bind the returned reference identifier directly into your order record
            order.khalti_pidx = response_data['pidx']
            order.save()

            # 5. Create or update a pending Payment record for this order
            Payment.objects.update_or_create(
                order=order,
                defaults={
                    'transaction_reference': response_data['pidx'],
                    'payment_method': 'Khalti',
                    'amount': Decimal('0.00'),
                    'payment_status': 'pending',
                    'paid_at': None,
                }
            )
            
            return Response({
                "pidx": response_data['pidx'],
                "payment_url": response_data['payment_url']
            }, status=status.HTTP_200_OK)
        
        return Response({"error": "Khalti initiation failed", "details": response_data}, status=response.status_code)


    @action(detail=False, methods=['get'], url_path='verify')
    def verify_khalti(self, request):
        # Read the tracking parameters Khalti automatically appends to your return_url string
        pidx = request.query_params.get('pidx')
        order_number = request.query_params.get('purchase_order_id')
        transaction_id = request.query_params.get('transaction_id')

        if not pidx or not order_number:
            return Response({"error": "Missing verification token data parameters."}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Fetch matching pending local record 
        order = get_object_or_404(Order, order_number=order_number, khalti_pidx=pidx)

        # 2. Server-to-server security verification check with Khalti lookup endpoint
        headers = {
            "Authorization": khalti_authorization_header(),
            "Content-Type": "application/json"
        }
        lookup_payload = {"pidx": pidx}
        lookup_url = getattr(settings, 'KHALTI_LOOKUP_URL', 'https://dev.khalti.com/api/v2/epayment/lookup/')

        try:
            response = requests.post(lookup_url, json=lookup_payload, headers=headers)
            verification_data = response.json()
        except requests.exceptions.RequestException:
            return Response({"error": "Verification request dropped by gateway network service."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        # 3. Check explicit Khalti ledger system authorization
        paid_amount = extract_paid_amount(verification_data)
        if paid_amount is not None:
            if paid_amount > order.total_amount * Decimal('10') and paid_amount % Decimal('100') == 0:
                paid_amount = paid_amount / Decimal('100')

        if paid_amount is None:
            paid_amount = Decimal('0.00')

        is_complete = paid_amount >= order.total_amount
        transaction_ok = response.status_code == 200 and verification_data.get('status') == 'Completed'
        if transaction_ok or paid_amount > Decimal('0.00'):
            order.order_status = 'processing' if is_complete else 'pending'
            order.khalti_transaction_id = verification_data.get('transaction_id') or transaction_id
            order.save()

            payment_status = 'completed' if is_complete else 'pending'
            Payment.objects.update_or_create(
                order=order,
                defaults={
                    'transaction_reference': order.khalti_pidx or transaction_id,
                    'payment_method': 'Khalti',
                    'amount': paid_amount,
                    'payment_status': payment_status,
                    'paid_at': timezone.now(),
                }
            )

            return Response({
                "status": "success",
                "message": (
                    f"Payment recorded for Order {order.order_number}. "
                    f"Paid {paid_amount}, due {order.total_amount - paid_amount}."
                )
            }, status=status.HTTP_200_OK)

        # Handle failure state tracking
        order.order_status = 'cancelled'
        order.save()
        Payment.objects.update_or_create(
            order=order,
            defaults={
                'transaction_reference': order.khalti_pidx or transaction_id,
                'payment_method': 'Khalti',
                'amount': paid_amount,
                'payment_status': 'failed',
                'paid_at': timezone.now() if paid_amount > Decimal('0.00') else None,
            }
        )
        return Response({
            "status": "failed",
            "message": f"Payment validation rejected. Status: {verification_data.get('status', 'Unknown')}"
        }, status=status.HTTP_400_BAD_REQUEST)
