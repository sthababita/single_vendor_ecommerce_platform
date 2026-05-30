from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Address, Category, Product, ProductImage, Cart, CartItem, Order, OrderItem

# --- USER SERIALIZER ---
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


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
class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), source='product', write_only=True
    )
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_id', 'quantity', 'total_price']

    def get_total_price(self, obj):
        return obj.quantity * obj.product.price


from rest_framework import serializers
from .models import Cart, CartItem, Product

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


# 🆕 2. Direct Web-Form Input Serializer for Add Item Page
class AddToCartSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(min_value=1, help_text="Enter the numeric ID of the product")
    quantity = serializers.IntegerField(default=1, min_value=1, help_text="Enter quantity (minimum 1)")


# 🛒 3. Main Cart Serializer (Your original code handling outputs)
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

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'total_amount', 'tax_amount', 
            'shipping_amount', 'order_status', 'created_at', 'items'
        ]


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'product', 'image', 'is_primary', 'sort_order'] # 'product' is the ID of the product this image belongs to



