from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from sales.models import Sale

from .models import CustomerPayment, FinancialAccount, LedgerEntry


def _money(value):
    return Decimal(value).quantize(Decimal('0.01'))


@transaction.atomic
def post_entry(
    account: FinancialAccount,
    amount,
    direction: str,
    category: str,
    description: str,
    source_type: str,
    source_id: int,
    occurred_at=None,
) -> LedgerEntry:
    amount = _money(amount)

    if amount <= 0:
        raise ValidationError('مبلغ الحركة يجب أن يكون أكبر من صفر.')

    if direction not in {'in', 'out'}:
        raise ValidationError('اتجاه الحركة يجب أن يكون in أو out.')

    entry = LedgerEntry.objects.create(
        account=account,
        amount=amount,
        direction=direction,
        category=category,
        description=description,
        source_type=source_type,
        source_id=source_id,
        occurred_at=occurred_at or timezone.now(),
    )
    return entry


@transaction.atomic
def reverse_entries(source_type: str, source_id: int) -> int:
    entries = LedgerEntry.objects.filter(
        source_type=source_type,
        source_id=source_id,
        is_reversed=False,
    )
    count = entries.count()
    entries.update(is_reversed=True)
    return count


@transaction.atomic
def post_transfer(transfer) -> None:
    reverse_entries('money_transfer', transfer.pk)
    post_entry(
        account=transfer.source_account,
        amount=transfer.amount,
        direction='out',
        category='transfer_out',
        description=transfer.description,
        source_type='money_transfer',
        source_id=transfer.pk,
        occurred_at=transfer.occurred_at,
    )
    post_entry(
        account=transfer.target_account,
        amount=transfer.amount,
        direction='in',
        category='transfer_in',
        description=transfer.description,
        source_type='money_transfer',
        source_id=transfer.pk,
        occurred_at=transfer.occurred_at,
    )
    if transfer.fee_amount > 0:
        post_entry(
            account=transfer.source_account,
            amount=transfer.fee_amount,
            direction='out',
            category='transfer_fee',
            description=f'عمولة تحويل - {transfer.description}',
            source_type='money_transfer',
            source_id=transfer.pk,
            occurred_at=transfer.occurred_at,
        )


@transaction.atomic
def sync_customer_payment(payment: CustomerPayment) -> None:
    reverse_entries('customer_payment', payment.pk)
    post_entry(
        account=payment.account,
        amount=payment.amount,
        direction='in',
        category='customer_payment',
        description=f'سداد عميل - {payment.customer.name}',
        source_type='customer_payment',
        source_id=payment.pk,
        occurred_at=payment.payment_date,
    )


def get_customer_deferred_balance(customer) -> dict:
    total_deferred = Sale.objects.filter(
        customer=customer,
        payment_type='deferred',
        is_new_accounting_sale=True,
    ).aggregate(total=Sum('total_amount')).get('total') or Decimal('0.00')
    total_payments = CustomerPayment.objects.filter(
        customer=customer,
    ).aggregate(total=Sum('amount')).get('total') or Decimal('0.00')

    total_deferred = _money(total_deferred)
    total_payments = _money(total_payments)
    return {
        'customer': customer,
        'total_deferred': total_deferred,
        'total_payments': total_payments,
        'remaining': _money(total_deferred - total_payments),
    }


def get_deferred_customer_balances():
    from customers.models import Customer

    customer_ids = set(
        Sale.objects.filter(
            payment_type='deferred',
            is_new_accounting_sale=True,
            customer__isnull=False,
        ).values_list('customer_id', flat=True)
    )
    customer_ids.update(CustomerPayment.objects.values_list('customer_id', flat=True))

    customers = Customer.objects.filter(id__in=customer_ids).order_by('name')
    return [get_customer_deferred_balance(customer) for customer in customers]
