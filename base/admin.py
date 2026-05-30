from django.contrib import admin
from .models import (
    Address, Category, Product, ProductImage, 
    Cart, CartItem, Order, OrderItem, Payment, Shipment
)

# ==========================================
# 1. INLINES (Manage related records inline)
# ==========================================

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1  # Provides 1 empty slot to upload a picture right away


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0  # Do not display empty rows for historic logs
    readonly_fields = ('product', 'quantity', 'unit_price')  # Safeguards history
    can_delete = False


class PaymentInline(admin.StackedInline):
    model = Payment
    can_delete = False
    readonly_fields = ('transaction_reference', 'payment_method', 'amount', 'paid_at')


class ShipmentInline(admin.StackedInline):
    model = Shipment
    can_delete = False


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0

# ==========================================
# 2. MODEL ADMIN CONFIGURATIONS
# ==========================================

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('user', 'address_type', 'city', 'state', 'country', 'is_default')
    list_filter = ('address_type', 'country', 'is_default')
    search_fields = ('user__username', 'city', 'postal_code')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'slug')
    prepopulated_fields = {'slug': ('name',)}  # Auto-types slug as you type the name
    search_fields = ('name',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'price', 'compare_at_price', 'stock_quantity', 'is_active', 'updated_at')
    list_filter = ('is_active', 'category')
    search_fields = ('name', 'sku', 'description')
    prepopulated_fields = {'slug': ('name',)}  # Auto-types product slug
    inlines = [ProductImageInline]             # Upload images directly on product page
    list_editable = ('price', 'stock_quantity', 'is_active')  # Quick changes from list view


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'user', 'total_amount', 'order_status', 'created_at')
    list_filter = ('order_status', 'created_at')
    search_fields = ('order_number', 'user__username', 'user__email')
    readonly_fields = ('order_number', 'total_amount', 'tax_amount', 'shipping_amount', 'created_at')
    
    # Places items, payments, and shipping info inside the main Order details page
    inlines = [OrderItemInline, PaymentInline, ShipmentInline]
    
    # Organizes page fields into clear collapsible dropdown sections
    fieldsets = (
        ('Order Details', {
            'fields': ('order_number', 'user', 'order_status', 'created_at')
        }),
        ('Financial Breakdowns', {
            'fields': ('tax_amount', 'shipping_amount', 'total_amount'),
        }),
        ('Shipping & Billing Addresses', {
            'fields': ('shipping_address', 'billing_address'),
        }),
    )


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'updated_at')
    search_fields = ('user__username',)
    inlines = [CartItemInline]

# ==========================================
# 3. OPTIONAL INDEPENDENT LOOKUPS
# ==========================================
# Allows viewing payments and shipments independent of the main orders screen
admin.site.register(Payment)
admin.site.register(Shipment)