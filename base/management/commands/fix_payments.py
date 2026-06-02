from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from base.models import Payment


class Command(BaseCommand):
    help = 'Fix existing Payment records: mark as completed when paid amount >= order total'

    def add_arguments(self, parser):
        parser.add_argument('--commit', action='store_true', help='Actually save changes (default is dry-run)')

    def handle(self, *args, **options):
        commit = options.get('commit')
        payments = Payment.objects.select_related('order').all()

        changed = 0
        candidates = []

        for p in payments:
            if not p.order:
                continue

            try:
                order_total = Decimal(p.order.total_amount or Decimal('0.00'))
                paid = Decimal(p.amount or Decimal('0.00'))
            except Exception:
                # Skip any malformed values
                continue

            if paid >= order_total and p.payment_status != 'completed':
                candidates.append((p, order_total, paid))

        if not candidates:
            self.stdout.write(self.style.SUCCESS('No payments need updating.'))
            return

        self.stdout.write(f'Found {len(candidates)} payment(s) to update:')
        for p, order_total, paid in candidates:
            self.stdout.write(f' - {p.transaction_reference}: order_total={order_total} paid={paid} current_status={p.payment_status}')
            if commit:
                p.payment_status = 'completed'
                if p.paid_at is None:
                    p.paid_at = timezone.now()
                p.save(update_fields=['payment_status', 'paid_at'])
                changed += 1

        if commit:
            self.stdout.write(self.style.SUCCESS(f'Updated {changed} payment(s).'))
        else:
            self.stdout.write(self.style.WARNING('Dry-run complete. Re-run with --commit to apply changes.'))
