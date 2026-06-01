from django.contrib import admin
from django import forms
from django.http import JsonResponse
from django.urls import path
import uuid
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


class OrderItemInlineForm(forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = ('product', 'quantity', 'unit_price')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['quantity'].required = False
        self.fields['unit_price'].required = False


class ProductPriceSelect(forms.Select):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        product = getattr(value, 'instance', None)

        if value and product is None:
            try:
                product = Product.objects.only('price').get(pk=value)
            except (Product.DoesNotExist, ValueError, TypeError):
                product = None

        if product:
            option['attrs']['data-price'] = str(product.price)

        return option


class CartItemInlineForm(forms.ModelForm):
    unit_price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        disabled=True,
    )
    subtotal = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        disabled=True,
    )

    class Meta:
        model = CartItem
        fields = ('product', 'quantity', 'unit_price', 'subtotal')
        widgets = {
            'product': ProductPriceSelect,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        product = self.instance.product if self.instance and self.instance.pk else None
        quantity = self.instance.quantity if self.instance and self.instance.pk else 1

        if product:
            self.fields['unit_price'].initial = product.price
            self.fields['subtotal'].initial = product.price * quantity


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    form = OrderItemInlineForm
    extra = 1
    fields = ('product', 'quantity', 'unit_price')

    class Media:
        js = ('base/admin/order_item_auto_fill.js',)


class PaymentInline(admin.StackedInline):
    model = Payment
    can_delete = False
    fields = ('transaction_reference', 'payment_method', 'amount', 'payment_status', 'paid_at')


class ShipmentInline(admin.StackedInline):
    model = Shipment
    can_delete = False


class CartItemInline(admin.TabularInline):
    model = CartItem
    form = CartItemInlineForm
    extra = 1
    fields = ('product', 'quantity', 'unit_price', 'subtotal')

    class Media:
        js = ('base/admin/cart_item_auto_fill.js',)

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

    def save_model(self, request, obj, form, change):
        if not obj.order_number:
            obj.order_number = f"ORD-{uuid.uuid4().hex[:8].upper()}"

        if obj.total_amount is None:
            obj.total_amount = 0

        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)

        for deleted_object in formset.deleted_objects:
            deleted_object.delete()

        for instance in instances:
            if isinstance(instance, OrderItem) and instance.product:
                if instance.unit_price is None:
                    instance.unit_price = instance.product.price

                if not instance.quantity:
                    cart_item = CartItem.objects.filter(
                        cart__user=instance.order.user,
                        product=instance.product,
                    ).first()
                    instance.quantity = cart_item.quantity if cart_item else 1

            instance.save()

        formset.save_m2m()
        self.update_order_total(form.instance)

    def update_order_total(self, order):
        order.total_amount = (
            sum(item.quantity * item.unit_price for item in order.items.all())
            + order.tax_amount
            + order.shipping_amount
        )
        order.save(update_fields=['total_amount'])

    def get_urls(self):
        custom_urls = [
            path(
                'product-price/<int:product_id>/',
                self.admin_site.admin_view(self.product_price_view),
                name='base_order_product_price',
            ),
        ]
        return custom_urls + super().get_urls()

    def product_price_view(self, request, product_id):
        try:
            product = Product.objects.only('price').get(pk=product_id)
        except Product.DoesNotExist:
            return JsonResponse({'error': 'Product not found'}, status=404)

        quantity = 1
        user_id = request.GET.get('user_id')

        if user_id:
            cart_item = CartItem.objects.filter(
                cart__user_id=user_id,
                product_id=product_id,
            ).first()
            if cart_item:
                quantity = cart_item.quantity

        return JsonResponse({
            'price': str(product.price),
            'quantity': quantity,
        })


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'updated_at')
    search_fields = ('user__username',)
    inlines = [CartItemInline]

    def get_urls(self):
        custom_urls = [
            path(
                'product-price/<int:product_id>/',
                self.admin_site.admin_view(self.product_price_view),
                name='base_cart_product_price',
            ),
        ]
        return custom_urls + super().get_urls()

    def product_price_view(self, request, product_id):
        try:
            product = Product.objects.only('price').get(pk=product_id)
        except Product.DoesNotExist:
            return JsonResponse({'error': 'Product not found'}, status=404)

        return JsonResponse({'price': str(product.price)})

# ==========================================
# 3. OPTIONAL INDEPENDENT LOOKUPS
# ==========================================
# Allows viewing payments and shipments independent of the main orders screen
admin.site.register(Payment)
admin.site.register(Shipment)
