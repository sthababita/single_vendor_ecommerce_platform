from decimal import Decimal

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.text import slugify


class Address(models.Model):
    ADDRESS_TYPES = (
        ('shipping', 'Shipping Address'),
        ('billing', 'Billing Address'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    address_type = models.CharField(max_length=10, choices=ADDRESS_TYPES, default='shipping')
    is_default = models.BooleanField(default=False)
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)

    class Meta:
        verbose_name_plural = "Addresses"

    def __str__(self):
        return f"{self.user.username} - {self.address_type} ({self.city})"


class Category(models.Model):
    # self-referencing relationship for subcategories
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children')
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=150, unique=True)
    sku = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    compare_at_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stock_quantity = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

 
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/') 
    is_primary = models.BooleanField(default=False)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ['sort_order']



class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart of {self.user.username}"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"


class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    )
    
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='orders')
    order_number = models.CharField(max_length=50, unique=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    shipping_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    order_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    shipping_address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True, related_name='order_shippings')
    billing_address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True, related_name='order_billings')
    created_at = models.DateTimeField(auto_now_add=True)

    # 🆕 KHALTI INTEGRATION TRACKING FIELDS
    khalti_pidx = models.CharField(max_length=255, null=True, blank=True, unique=True)
    khalti_transaction_id = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"Order {self.order_number}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT) # Prevent deletion of bought items
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2) # Snapshot price at purchase

    def __str__(self):
        return f"{self.quantity} x {self.product.name} (Order {self.order.order_number})"



class Payment(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    )

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
    transaction_reference = models.CharField(max_length=100, unique=True)
    payment_method = models.CharField(max_length=50) # e.g., 'Stripe', 'PayPal'
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    paid_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Payment {self.transaction_reference} for Order {self.order.order_number}"

    def save(self, *args, **kwargs):
        if self.order is not None and self.amount is not None:
            # Automatically complete a payment when amount covers the order total
            if self.amount >= self.order.total_amount:
                self.payment_status = 'completed'
                if self.paid_at is None:
                    self.paid_at = timezone.now()
            elif self.payment_status not in ('completed', 'refunded'):
                # Keep manual pending/failed state for partial or placeholder payments
                self.payment_status = 'pending'

        super().save(*args, **kwargs)


class Shipment(models.Model):
    STATUS_CHOICES = (
        ('manifest', 'Manifest Created'),
        ('in_transit', 'In Transit'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
    )

    SHIPMENT_TO_ORDER_STATUS = {
        'manifest': 'processing',
        'in_transit': 'shipped',
        'out_for_delivery': 'shipped',
        'delivered': 'delivered',
    }

    ORDER_STATUS_RANK = {
        'pending': 0,
        'processing': 1,
        'shipped': 2,
        'delivered': 3,
        'cancelled': -1,
        'refunded': -1,
    }

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='shipment')
    carrier = models.CharField(max_length=50)
    tracking_number = models.CharField(max_length=100, blank=True, null=True)
    shipment_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='manifest')
    shipped_at = models.DateTimeField(null=True, blank=True)
    estimated_delivery = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"Shipment for Order {self.order.order_number}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if not self.order_id:
            return

        target_order_status = self.SHIPMENT_TO_ORDER_STATUS.get(self.shipment_status)
        if not target_order_status:
            return

        current_order_status = self.order.order_status
        if current_order_status in ('cancelled', 'refunded'):
            return

        if self.ORDER_STATUS_RANK.get(target_order_status, 0) > self.ORDER_STATUS_RANK.get(current_order_status, 0):
            self.order.order_status = target_order_status
            self.order.save(update_fields=['order_status'])
