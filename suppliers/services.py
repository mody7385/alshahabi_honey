from datetime import datetime, time

from django.utils import timezone

from accounting.services import post_entry, reverse_entries


def _date_to_datetime(value):
    if isinstance(value, datetime):
        return value
    return timezone.make_aware(datetime.combine(value, time.min))


def sync_supplier_purchase_ledger(purchase) -> None:
    reverse_entries('supplier_purchase', purchase.pk)
    if purchase.payment_status != purchase.PAYMENT_PAID:
        return

    post_entry(
        account=purchase.payment_account,
        amount=purchase.total_amount,
        direction='out',
        category='supplier_purchase_payment',
        description=f'شراء من مورد - {purchase.supplier.name}',
        source_type='supplier_purchase',
        source_id=purchase.pk,
        occurred_at=_date_to_datetime(purchase.purchase_date),
    )


def sync_supplier_payment_ledger(payment) -> None:
    reverse_entries('supplier_payment', payment.pk)
    post_entry(
        account=payment.payment_account,
        amount=payment.amount,
        direction='out',
        category='supplier_payment',
        description=f'سداد مورد - {payment.supplier.name}',
        source_type='supplier_payment',
        source_id=payment.pk,
        occurred_at=_date_to_datetime(payment.payment_date),
    )
