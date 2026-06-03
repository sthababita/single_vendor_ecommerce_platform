import os
import sys

proj_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SVEP.settings')
import django
django.setup()

from base.models import Cart, CartItem

print('CARTS:', Cart.objects.count())
print('CARTITEMS:', CartItem.objects.count())
for c in Cart.objects.all():
    items = list(c.items.select_related('product'))
    print('Cart', c.id, 'user', c.user.username, 'items_count', len(items))
    for it in items:
        print(' -', it.product.id, it.product.name, it.quantity, it.product.price)
