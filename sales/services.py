from accounting.services import post_entry, reverse_entries


def sync_sale_ledger(sale) -> None:
    reverse_entries('sale', sale.pk)

    if sale.payment_type == 'cash':
        post_entry(
            account=sale.cash_worker_account,
            amount=sale.total_amount,
            direction='in',
            category='sale_cash',
            description=f'بيع نقدي - {sale.product.name}',
            source_type='sale',
            source_id=sale.pk,
            occurred_at=sale.sale_date,
        )
        return

    if sale.payment_type == 'transfer':
        post_entry(
            account=sale.payment_account,
            amount=sale.total_amount,
            direction='in',
            category='sale_transfer',
            description=f'بيع حوالة - {sale.product.name}',
            source_type='sale',
            source_id=sale.pk,
            occurred_at=sale.sale_date,
        )
        return

    if sale.payment_type == 'deferred':
        return
