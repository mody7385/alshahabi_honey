from datetime import datetime, time

from django.utils import timezone

from accounting.services import post_entry, reverse_entries


def _date_to_datetime(value):
    if isinstance(value, datetime):
        return value
    return timezone.make_aware(datetime.combine(value, time.min))


def sync_expense_ledger(expense) -> None:
    reverse_entries('operating_expense', expense.pk)
    category = 'personal_expense' if expense.expense_type == expense.EXPENSE_PERSONAL else 'operating_expense'
    post_entry(
        account=expense.payment_account,
        amount=expense.amount,
        direction='out',
        category=category,
        description=f'{expense.get_expense_type_display()} - {expense.name}',
        source_type='operating_expense',
        source_id=expense.pk,
        occurred_at=_date_to_datetime(expense.expense_date),
    )
