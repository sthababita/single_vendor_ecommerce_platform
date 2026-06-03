from decimal import Decimal

from django.contrib import admin
from django import forms
from django.http import JsonResponse
from django.urls import path
import uuid
from .models import (
    Address, Category, Product, ProductImage, 
    Cart, CartItem, Order, OrderItem, Payment, Shipment
)
from django.contrib.auth.models import User
from django.shortcuts import redirect

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


SHIPPING_AMOUNT_CHOICES = (
    (Decimal('100.00'), 'Kathmandu Valley (100)'),
    (Decimal('200.00'), 'Outside Valley (200)'),
)


class OrderAdminForm(forms.ModelForm):
    total_amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        disabled=True,
        label='Total amount',
    )
    shipping_amount = forms.TypedChoiceField(
        choices=(('', 'Select shipping amount'),) + SHIPPING_AMOUNT_CHOICES,
        coerce=Decimal,
        empty_value=Decimal('0.00'),
        required=False,
        label='Shipping amount',
    )

    class Meta:
        model = Order
        fields = '__all__'

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
    form = OrderAdminForm
    list_display = ('order_number', 'user', 'total_amount', 'order_status', 'created_at')
    list_filter = ('order_status', 'created_at')
    search_fields = ('order_number', 'user__username', 'user__email')
    readonly_fields = ('order_number', 'total_amount', 'created_at')
    
    # Places items inside the main Order details page
    inlines = [OrderItemInline]

    class Media:
        js = ('base/admin/order_item_auto_fill.js', 'base/admin/order_items_reorder.js')
    
    # Organizes page fields into clear collapsible dropdown sections
    fieldsets = (
        ('Order', {
            'fields': ('order_number', 'user', 'order_status', 'created_at')
        }),
        ('Shipment', {
            'fields': ('shipping_address', 'billing_address'),
        }),
        ('Finance', {
            'fields': ('shipping_amount', 'total_amount'),
        }),
    )

    def save_model(self, request, obj, form, change):
        if not obj.order_number:
            obj.order_number = f"ORD-{uuid.uuid4().hex[:8].upper()}"

        def to_decimal(value):
            if isinstance(value, Decimal):
                return value
            if value is None:
                return Decimal('0.00')
            return Decimal(str(value))

        order_items_total = sum(
            to_decimal(item.quantity) * to_decimal(item.unit_price) for item in obj.items.all()
        ) if obj.pk else Decimal('0.00')

        tax_amount = to_decimal(obj.tax_amount)
        shipping_amount = to_decimal(obj.shipping_amount)

        obj.total_amount = order_items_total + tax_amount + shipping_amount

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
        def to_decimal(value):
            if isinstance(value, Decimal):
                return value
            if value is None:
                return Decimal('0.00')
            return Decimal(str(value))

        order_items_total = sum(
            to_decimal(item.quantity) * to_decimal(item.unit_price)
            for item in order.items.all()
        )

        order.total_amount = (
            order_items_total
            + to_decimal(order.tax_amount)
            + to_decimal(order.shipping_amount)
        )
        order.save(update_fields=['total_amount'])

    def get_urls(self):
        custom_urls = [
            path(
                'product-price/<int:product_id>/',
                self.admin_site.admin_view(self.product_price_view),
                name='base_order_product_price',
            ),
            path(
                'cart-items/<int:user_id>/',
                self.admin_site.admin_view(self.cart_items_view),
                name='base_order_cart_items',
            ),
            path(
                'prefill-from-cart/',
                self.admin_site.admin_view(self.prefill_from_cart_view),
                name='base_order_prefill_from_cart',
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

    def cart_items_view(self, request, user_id):
        try:
            cart = Cart.objects.filter(user_id=user_id).first()
        except Exception:
            cart = None

        shipping_address = Address.objects.filter(user_id=user_id, address_type='shipping', is_default=True).first() or \
            Address.objects.filter(user_id=user_id, address_type='shipping').first()
        billing_address = Address.objects.filter(user_id=user_id, address_type='billing', is_default=True).first() or \
            Address.objects.filter(user_id=user_id, address_type='billing').first()

        items = []
        if cart:
            for ci in cart.items.select_related('product').all():
                items.append({
                    'product_id': ci.product_id,
                    'product_name': ci.product.name,
                    'quantity': ci.quantity,
                    'price': str(ci.product.price),
                })

        return JsonResponse({
            'items': items,
            'shipping_address_id': shipping_address.id if shipping_address else None,
            'billing_address_id': billing_address.id if billing_address else None,
        })

    def prefill_from_cart_view(self, request):
        user_id = request.GET.get('user_id')
        if not user_id:
            return JsonResponse({'error': 'user_id required'}, status=400)

        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return JsonResponse({'error': 'user not found'}, status=404)

        # pick default addresses if available
        shipping_address = Address.objects.filter(user=user, address_type='shipping', is_default=True).first() or \
            Address.objects.filter(user=user, address_type='shipping').first()
        billing_address = Address.objects.filter(user=user, address_type='billing', is_default=True).first() or \
            Address.objects.filter(user=user, address_type='billing').first()

        # create order and items from cart
        import uuid
        order = Order.objects.create(
            user=user,
            order_number=f"ORD-{uuid.uuid4().hex[:8].upper()}",
            total_amount=0,
            order_status='pending',
            shipping_address=shipping_address,
            billing_address=billing_address,
        )

        total = Decimal('0.00')
        for ci in CartItem.objects.filter(cart__user=user).select_related('product'):
            unit_price = ci.product.price
            quantity = ci.quantity or 1
            OrderItem.objects.create(
                order=order,
                product=ci.product,
                quantity=quantity,
                unit_price=unit_price,
            )
            total += Decimal(str(unit_price)) * Decimal(str(quantity))

        order.total_amount = total + (order.tax_amount or Decimal('0.00')) + (order.shipping_amount or Decimal('0.00'))
        order.save()

        # Redirect admin to the change page for the created order so items are visible
        change_url = f"{self.admin_site.name}:{self.model._meta.app_label}_{self.model._meta.model_name}_change"
        from django.urls import reverse
        return redirect(reverse('admin:base_order_change', args=[order.pk]))


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

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('order', 'transaction_reference', 'payment_method', 'payment_status', 'get_total_amount', 'get_paid_amount', 'get_due_amount')
    list_filter = ('payment_status', 'payment_method')
    search_fields = ('transaction_reference', 'order__order_number')
    readonly_fields = ('transaction_reference', 'get_total_amount', 'get_paid_amount', 'get_due_amount')

    def get_total_amount(self, obj):
        return obj.order.total_amount if obj.order else '-'
    get_total_amount.short_description = 'Total Amount'

    def get_paid_amount(self, obj):
        return obj.amount if obj.amount else '-'
    get_paid_amount.short_description = 'Paid Amount'

    def get_due_amount(self, obj):
        if obj.order and obj.amount:
            due = obj.order.total_amount - obj.amount
            return due if due > 0 else 0
        elif obj.order:
            return obj.order.total_amount
        return '-'
    get_due_amount.short_description = 'Due Amount'


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = ('order', 'shipment_status', 'shipped_at', 'estimated_delivery')
    fields = ('order', 'shipment_status', 'shipped_at', 'estimated_delivery')
    list_filter = ('shipment_status',)
    search_fields = ('order__order_number',)
