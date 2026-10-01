from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from accounting.models import FinancialAccount, LedgerEntry
from accounting.services import get_customer_deferred_balance
from accounts.models import WorkerProfile
from customers.models import Customer
from inventory.models import Inventory
from products.models import Product
from warehouses.models import Warehouse

from sales.models import Sale, SaleBatch


class AccountingSaleTests(TestCase):
    def setUp(self):
        self.warehouse = Warehouse.objects.create(name='حضرموت', city='المكلا')
        user = User.objects.create_user(username='worker', password='pass')
        self.worker = WorkerProfile.objects.create(
            user=user,
            full_name='عامل النقد',
            role='worker',
            warehouse=self.warehouse,
        )
        self.product = Product.objects.create(
            warehouse=self.warehouse,
            name='سدر ملكي',
            honey_type='سدر',
            purchase_price_per_kg=Decimal('10.00'),
            default_sale_price_per_dabba=Decimal('100.00'),
            default_sale_price_per_kg=Decimal('20.00'),
        )
        self.inventory = Inventory.objects.create(
            product=self.product,
            full_dabba_count=Decimal('10.00'),
            open_kg=Decimal('0.00'),
        )

    def make_sale(self, **overrides):
        values = {
            'warehouse': self.warehouse,
            'worker': self.worker,
            'product': self.product,
            'quantity_dabba': Decimal('1.00'),
            'price_per_dabba': Decimal('100.00'),
            'quantity_kg': Decimal('0.00'),
            'price_per_kg': Decimal('0.00'),
            'payment_type': 'cash',
            'is_new_accounting_sale': True,
        }
        values.update(overrides)
        return Sale.objects.create(**values)

    def test_cash_sale_requires_worker_financial_account_and_posts_money_to_worker(self):
        with self.assertRaises(ValidationError):
            self.make_sale()

        worker_account = FinancialAccount.objects.create(
            name='عهدة عامل النقد',
            account_type='worker',
        )

        sale = self.make_sale(cash_worker_account=worker_account)

        self.assertEqual(worker_account.current_balance(), Decimal('100.00'))
        self.assertTrue(
            LedgerEntry.objects.filter(
                source_type='sale',
                source_id=sale.pk,
                category='sale_cash',
                account=worker_account,
                is_reversed=False,
            ).exists()
        )

    def test_transfer_sale_requires_payment_account_and_posts_money_to_selected_account(self):
        with self.assertRaises(ValidationError):
            self.make_sale(payment_type='transfer')

        wallet = FinancialAccount.objects.create(name='محفظة الكريمي', account_type='wallet')

        sale = self.make_sale(payment_type='transfer', payment_account=wallet)

        self.assertEqual(wallet.current_balance(), Decimal('100.00'))
        self.assertTrue(
            LedgerEntry.objects.filter(
                source_type='sale',
                source_id=sale.pk,
                category='sale_transfer',
                account=wallet,
                is_reversed=False,
            ).exists()
        )

    def test_deferred_sale_requires_customer_and_posts_no_ledger_entry(self):
        with self.assertRaises(ValidationError):
            self.make_sale(payment_type='deferred')

        customer = Customer.objects.create(name='عميل آجل', phone='777')

        sale = self.make_sale(payment_type='deferred', customer=customer)

        self.assertEqual(
            LedgerEntry.objects.filter(source_type='sale', source_id=sale.pk, is_reversed=False).count(),
            0,
        )

    def test_edit_sale_reverses_old_ledger_entry_and_posts_new_entry(self):
        wallet = FinancialAccount.objects.create(name='محفظة', account_type='wallet')
        bank = FinancialAccount.objects.create(name='بنك', account_type='bank')
        sale = self.make_sale(payment_type='transfer', payment_account=wallet)

        sale.payment_account = bank
        sale.price_per_dabba = Decimal('120.00')
        sale.save()

        self.assertEqual(wallet.current_balance(), Decimal('0.00'))
        self.assertEqual(bank.current_balance(), Decimal('120.00'))
        self.assertEqual(
            LedgerEntry.objects.filter(source_type='sale', source_id=sale.pk, is_reversed=False).count(),
            1,
        )

    def test_delete_sale_reverses_ledger_entries(self):
        worker_account = FinancialAccount.objects.create(name='عهدة عامل', account_type='worker')
        sale = self.make_sale(cash_worker_account=worker_account)

        sale.delete()

        self.assertEqual(worker_account.current_balance(), Decimal('0.00'))
        self.assertEqual(
            LedgerEntry.objects.filter(source_type='sale', source_id=sale.pk, is_reversed=False).count(),
            0,
        )

    def test_manager_sale_create_posts_accounting_sale_from_formset(self):
        manager_user = User.objects.create_user(username='manager', password='pass')
        WorkerProfile.objects.create(
            user=manager_user,
            full_name='المدير',
            role='manager',
        )
        wallet = FinancialAccount.objects.create(name='محفظة', account_type='wallet')
        self.client.force_login(manager_user)

        response = self.client.post(reverse('manager-sale-create'), {
            'customer_name': 'عميل حوالة',
            'customer_phone': '700',
            'payment_type': 'transfer',
            'payment_account': wallet.pk,
            'notes': 'بيع من المدير',
            'form-TOTAL_FORMS': '1',
            'form-INITIAL_FORMS': '0',
            'form-MIN_NUM_FORMS': '0',
            'form-MAX_NUM_FORMS': '1000',
            'form-0-product': self.product.pk,
            'form-0-quantity_dabba': '1',
            'form-0-price_per_dabba': '100',
            'form-0-quantity_kg': '0',
            'form-0-price_per_kg': '0',
        })

        self.assertRedirects(response, reverse('manager-sales-list'))
        sale = Sale.objects.get(customer__name='عميل حوالة')
        self.assertTrue(sale.is_new_accounting_sale)
        self.assertEqual(sale.payment_account, wallet)
        self.assertEqual(wallet.current_balance(), Decimal('100.00'))

    def test_manager_can_update_accounting_sale_payment_account(self):
        manager_user = User.objects.create_user(username='manager-edit', password='pass')
        manager = WorkerProfile.objects.create(
            user=manager_user,
            full_name='المدير',
            role='manager',
        )
        wallet = FinancialAccount.objects.create(name='محفظة', account_type='wallet')
        bank = FinancialAccount.objects.create(name='بنك', account_type='bank')
        sale = self.make_sale(
            worker=manager,
            payment_type='transfer',
            payment_account=wallet,
        )
        self.client.force_login(manager_user)

        response = self.client.post(reverse('sale-update', args=[sale.pk]), {
            'customer_name': '',
            'customer_phone': '',
            'product': self.product.pk,
            'quantity_dabba': '1',
            'price_per_dabba': '120',
            'quantity_kg': '0',
            'price_per_kg': '0',
            'payment_type': 'transfer',
            'payment_account': bank.pk,
            'notes': '',
        })

        self.assertRedirects(response, reverse('manager-sales-list'))
        self.assertEqual(wallet.current_balance(), Decimal('0.00'))
        self.assertEqual(bank.current_balance(), Decimal('120.00'))

    def test_manager_sale_create_accepts_store_and_split_payment(self):
        manager_user = User.objects.create_user(username='manager-split', password='pass')
        WorkerProfile.objects.create(
            user=manager_user,
            full_name='المدير',
            role='manager',
        )
        worker_account = FinancialAccount.objects.create(name='عهدة المدير', account_type='worker')
        wallet = FinancialAccount.objects.create(name='محفظة سمرة', account_type='wallet')
        self.client.force_login(manager_user)

        response = self.client.post(reverse('manager-sale-create'), {
            'store': 'samra',
            'customer_name': 'عميل مختلط',
            'customer_phone': '711',
            'cash_amount': '30.00',
            'transfer_amount': '50.00',
            'deferred_amount': '20.00',
            'cash_worker_account': worker_account.pk,
            'payment_account': wallet.pk,
            'notes': 'بيع موزع',
            'form-TOTAL_FORMS': '1',
            'form-INITIAL_FORMS': '0',
            'form-MIN_NUM_FORMS': '0',
            'form-MAX_NUM_FORMS': '1000',
            'form-0-product': self.product.pk,
            'form-0-quantity_dabba': '1',
            'form-0-price_per_dabba': '100',
            'form-0-quantity_kg': '0',
            'form-0-price_per_kg': '0',
        })

        self.assertRedirects(response, reverse('manager-sales-list'))
        batch = SaleBatch.objects.get(customer__name='عميل مختلط')
        sale = batch.sales.get()
        self.assertEqual(batch.store, 'samra')
        self.assertEqual(sale.store, 'samra')
        self.assertEqual(batch.cash_amount, Decimal('30.00'))
        self.assertEqual(batch.transfer_amount, Decimal('50.00'))
        self.assertEqual(batch.deferred_amount, Decimal('20.00'))
        self.assertEqual(worker_account.current_balance(), Decimal('30.00'))
        self.assertEqual(wallet.current_balance(), Decimal('50.00'))
        self.assertEqual(
            LedgerEntry.objects.filter(source_type='sale_batch', source_id=batch.pk, is_reversed=False).count(),
            2,
        )
        self.assertEqual(get_customer_deferred_balance(batch.customer)['remaining'], Decimal('20.00'))

    def test_manager_sale_create_rejects_split_payment_that_does_not_match_total(self):
        manager_user = User.objects.create_user(username='manager-split-invalid', password='pass')
        WorkerProfile.objects.create(
            user=manager_user,
            full_name='المدير',
            role='manager',
        )
        worker_account = FinancialAccount.objects.create(name='عهدة المدير', account_type='worker')
        self.client.force_login(manager_user)

        response = self.client.post(reverse('manager-sale-create'), {
            'store': 'alshahabi',
            'customer_name': '',
            'customer_phone': '',
            'cash_amount': '90.00',
            'transfer_amount': '0.00',
            'deferred_amount': '0.00',
            'cash_worker_account': worker_account.pk,
            'payment_account': '',
            'notes': '',
            'form-TOTAL_FORMS': '1',
            'form-INITIAL_FORMS': '0',
            'form-MIN_NUM_FORMS': '0',
            'form-MAX_NUM_FORMS': '1000',
            'form-0-product': self.product.pk,
            'form-0-quantity_dabba': '1',
            'form-0-price_per_dabba': '100',
            'form-0-quantity_kg': '0',
            'form-0-price_per_kg': '0',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'مبالغ الدفع يجب أن تساوي إجمالي البيع')
        self.assertFalse(SaleBatch.objects.exists())
