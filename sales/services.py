from accounting.services import post_entry, reverse_entries


def sync_sale_ledger(sale) -> None:
    if sale.batch_id and sale.batch.uses_batch_accounting:
        reverse_entries('sale', sale.pk)
        return

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


def sync_sale_batch_ledger(batch) -> None:
    reverse_entries('sale_batch', batch.pk)

    if batch.cash_amount > 0:
        post_entry(
            account=batch.cash_worker_account,
            amount=batch.cash_amount,
            direction='in',
            category='sale_cash',
            description=f'بيع نقدي - {batch.get_store_display()}',
            source_type='sale_batch',
            source_id=batch.pk,
            occurred_at=batch.created_at,
        )

    if batch.transfer_amount > 0:
        post_entry(
            account=batch.payment_account,
            amount=batch.transfer_amount,
            direction='in',
            category='sale_transfer',
            description=f'بيع حوالة - {batch.get_store_display()}',
            source_type='sale_batch',
            source_id=batch.pk,
            occurred_at=batch.created_at,
        )
