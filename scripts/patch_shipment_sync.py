from pathlib import Path

path = Path(r'e:/Single_Vendor/single_vendor_ecommerce_platform/base/models.py')
text = path.read_text()
old = '        return f"Shipment for Order {self.order.order_number}"\n'
if old not in text:
    raise SystemExit('old string not found')
new = old + '''

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
'''
path.write_text(text.replace(old, new))
print('patched')
