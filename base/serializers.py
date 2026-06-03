from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Address, Category, Product, ProductImage, Cart, CartItem, Order, OrderItem


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = [
            'id', 'address_type', 'is_default', 'address_line1', 'address_line2',
            'city', 'state', 'postal_code', 'country',
        ]
        read_only_fields = ['id', 'address_type', 'is_default']


class UserSerializer(serializers.ModelSerializer):
    shipping_address = serializers.SerializerMethodField()
    billing_address = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'shipping_address', 'billing_address']

    def get_shipping_address(self, obj):
        address = obj.addresses.filter(address_type='shipping', is_default=True).first()
        return AddressSerializer(address).data if address else None

    def get_billing_address(self, obj):
        address = obj.addresses.filter(address_type='billing', is_default=True).first()
        return AddressSerializer(address).data if address else None


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    shipping_address_line1 = serializers.CharField(required=True)
    shipping_address_line2 = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    shipping_city = serializers.CharField(required=True)
    shipping_state = serializers.CharField(required=True)
    shipping_postal_code = serializers.CharField(required=True)
    shipping_country = serializers.CharField(required=True)

    billing_address_line1 = serializers.CharField(required=True)
    billing_address_line2 = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    billing_city = serializers.CharField(required=True)
    billing_state = serializers.CharField(required=True)
    billing_postal_code = serializers.CharField(required=True)
    billing_country = serializers.CharField(required=True)

    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'first_name', 'last_name',
            'shipping_address_line1', 'shipping_address_line2', 'shipping_city',
            'shipping_state', 'shipping_postal_code', 'shipping_country',
            'billing_address_line1', 'billing_address_line2', 'billing_city',
            'billing_state', 'billing_postal_code', 'billing_country',
        ]

    def create(self, validated_data):
        shipping_data = {
            'address_line1': validated_data.pop('shipping_address_line1'),
            'address_line2': validated_data.pop('shipping_address_line2', ''),
            'city': validated_data.pop('shipping_city'),
            'state': validated_data.pop('shipping_state'),
            'postal_code': validated_data.pop('shipping_postal_code'),
            'country': validated_data.pop('shipping_country'),
            'address_type': 'shipping',
            'is_default': True,
        }
        billing_data = {
            'address_line1': validated_data.pop('billing_address_line1'),
            'address_line2': validated_data.pop('billing_address_line2', ''),
            'city': validated_data.pop('billing_city'),
            'state': validated_data.pop('billing_state'),
            'postal_code': validated_data.pop('billing_postal_code'),
            'country': validated_data.pop('billing_country'),
            'address_type': 'billing',
            'is_default': True,
        }
        password = validated_data.pop('password')
        user = User.objects.create_user(password=password, **validated_data)
        Address.objects.create(user=user, **shipping_data)
        Address.objects.create(user=user, **billing_data)
        return user


# --- PRODUCT CATALOG SERIALIZERS ---
class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'is_primary', 'sort_order']


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'parent']
        
        #  ADD THIS BLOCK RIGHT HERE:
        extra_kwargs = {
            'slug': {'required': False, 'allow_blank': True}
        }


class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'category', 'category_name', 'name', 'slug', 'sku', 
            'description', 'price', 'compare_at_price', 'stock_quantity', 
            'is_active', 'images', 'created_at'
        ]
        
        #  ADD THIS TO PRODUCTS TOO:
        extra_kwargs = {
            'slug': {'required': False, 'allow_blank': True}
        }


# --- CART SERIALIZERS ---
# 1. Individual Product Item Blueprint inside the Cart
class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_price = serializers.DecimalField(source='product.price', max_digits=10, decimal_places=2, read_only=True)
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_name', 'product_price', 'quantity', 'subtotal']

    def get_subtotal(self, obj):
        return obj.quantity * obj.product.price


# 2. Direct Web-Form Input Serializer for Add Item Page
class AddToCartSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(min_value=1, help_text="Enter the numeric ID of the product")
    quantity = serializers.IntegerField(default=1, min_value=1, help_text="Enter quantity (minimum 1)")


#  3. Main Cart Serializer (Your original code handling outputs)
class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    grand_total = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ['id', 'user', 'items', 'grand_total']

    def get_grand_total(self, obj):
        return sum(item.quantity * item.product.price for item in obj.items.all())


# --- ORDER SERIALIZERS ---
class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_name', 'quantity', 'unit_price']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    shipping_address = AddressSerializer(read_only=True)
    billing_address = AddressSerializer(read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'total_amount', 'tax_amount',
            'shipping_amount', 'order_status', 'shipping_address',
            'billing_address', 'created_at', 'items'
        ]




class KhaltiInitiateSerializer(serializers.Serializer):
    order_number = serializers.CharField(max_length=50)

    def validate_order_number(self, value):
        user = self.context['request'].user
        try:
            order = Order.objects.get(order_number=value, user=user)
        except Order.DoesNotExist:
            raise serializers.ValidationError("Order not found or does not belong to you.")
        
        if order.order_status != 'pending':
            raise serializers.ValidationError(f"This order cannot be paid. Status is currently: {order.order_status}")
            
        return value
