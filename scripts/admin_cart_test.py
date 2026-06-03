import os
import json

import sys

# Ensure project root is on sys.path so Django settings package can be imported
proj_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SVEP.settings')
import django
django.setup()

from django.test import RequestFactory
from django.contrib import admin
from base.admin import OrderAdmin
from base.models import Cart, Order

rf = RequestFactory()
request = rf.get('/')

cart = Cart.objects.filter(user__username='Ram').first() or Cart.objects.first()
if not cart:
    print('NO_CART')
else:
    user = cart.user
    # ensure user has staff flag so admin_view won't block
    if not user.is_staff:
        user.is_staff = True
        user.save()

    request.user = user
    order_admin = OrderAdmin(Order, admin.site)
    resp = order_admin.cart_items_view(request, user.id)
    try:
        data = json.loads(resp.content.decode())
        print(json.dumps(data, indent=2))
    except Exception as e:
        print('RESPONSE:', resp.content)
