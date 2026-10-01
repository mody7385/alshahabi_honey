from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import FinancialAccount, LedgerEntry


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
