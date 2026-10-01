from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from accounting.models import FinancialAccount, LedgerEntry
from accounts.models import WorkerProfile
from inventory.models import Inventory
from products.models import Product
from warehouses.models import Warehouse

from suppliers.models import Supplier, SupplierPayment, SupplierPurchase


class SupplierAccountingTests(TestCase):
    def setUp(self):
        self.warehouse = Warehouse.objects.create(name='حضرموت', city='المكلا')
        self.product = Product.objects.create(
            warehouse=self.warehouse,
            name='سدر',
            purchase_price_per_kg=Decimal('10.00'),
            default_sale_price_per_dabba=Decimal('100.00'),
            default_sale_price_per_kg=Decimal('20.00'),
        )
        self.inventory = Inventory.objects.create(
            product=self.product,
            full_dabba_count=Decimal('0.00'),
            open_kg=Decimal('0.00'),
        )
        self.supplier = Supplier.objects.create(name='مورد العسل')

    def make_purchase(self, **overrides):
        values = {
            'supplier': self.supplier,
            'product': self.product,
            'quantity_dabba': Decimal('1.00'),
            'quantity_kg': Decimal('0.00'),
            'price_per_dabba': Decimal('100.00'),
            'price_per_kg': Decimal('0.00'),
            'add_to_inventory': False,
            'is_new_accounting_purchase': True,
            'payment_status': 'unpaid',
        }
        values.update(overrides)
        return SupplierPurchase.objects.create(**values)

    def test_paid_purchase_requires_payment_account_and_posts_purchase_out(self):
        with self.assertRaises(ValidationError):
            self.make_purchase(payment_status='paid')

        account = FinancialAccount.objects.create(
            name='الصندوق',
            account_type='cashbox',
            opening_balance=Decimal('500.00'),
        )

        purchase = self.make_purchase(payment_status='paid', payment_account=account)

        self.assertEqual(account.current_balance(), Decimal('400.00'))
        self.assertTrue(
            LedgerEntry.objects.filter(
                source_type='supplier_purchase',
                source_id=purchase.pk,
                category='supplier_purchase_payment',
                is_reversed=False,
            ).exists()
        )

    def test_paid_purchase_does_not_leave_supplier_balance_due(self):
        user = User.objects.create_user(username='balance-manager', password='pass')
        WorkerProfile.objects.create(
            user=user,
            full_name='المدير',
            role=WorkerProfile.ROLE_MANAGER,
        )
        self.client.force_login(user)
        account = FinancialAccount.objects.create(
            name='الصندوق',
            account_type='cashbox',
            opening_balance=Decimal('500.00'),
        )
        self.make_purchase(payment_status='paid', payment_account=account)

        response = self.client.get(reverse('supplier-detail', args=[self.supplier.pk]))

        self.assertEqual(response.context['total_purchases'], Decimal('100.00'))
        self.assertEqual(response.context['total_payments'], Decimal('100.00'))
        self.assertEqual(response.context['balance'], Decimal('0.00'))

    def test_unpaid_purchase_posts_no_ledger_entry(self):
        purchase = self.make_purchase(payment_status='unpaid')

        self.assertEqual(
            LedgerEntry.objects.filter(source_type='supplier_purchase', source_id=purchase.pk).count(),
            0,
        )

    def test_supplier_payment_posts_out_from_selected_account(self):
        self.make_purchase(payment_status='unpaid')
        account = FinancialAccount.objects.create(
            name='البنك',
            account_type='bank',
            opening_balance=Decimal('500.00'),
        )

        payment = SupplierPayment.objects.create(
            supplier=self.supplier,
            amount=Decimal('40.00'),
            payment_account=account,
            is_new_accounting_payment=True,
        )

        self.assertEqual(account.current_balance(), Decimal('460.00'))
        self.assertTrue(
            LedgerEntry.objects.filter(
                source_type='supplier_payment',
                source_id=payment.pk,
                category='supplier_payment',
                is_reversed=False,
            ).exists()
        )

    def test_purchase_with_add_to_inventory_updates_inventory(self):
        self.make_purchase(add_to_inventory=True)

        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.full_dabba_count, Decimal('1.00'))

    def test_edit_purchase_reverses_old_ledger_and_inventory_impact(self):
        wallet = FinancialAccount.objects.create(
            name='محفظة',
            account_type='wallet',
            opening_balance=Decimal('500.00'),
        )
        bank = FinancialAccount.objects.create(
            name='بنك',
            account_type='bank',
            opening_balance=Decimal('500.00'),
        )
        purchase = self.make_purchase(
            payment_status='paid',
            payment_account=wallet,
            add_to_inventory=True,
        )

        purchase.payment_account = bank
        purchase.quantity_dabba = Decimal('2.00')
        purchase.price_per_dabba = Decimal('90.00')
        purchase.save()

        self.inventory.refresh_from_db()
        self.assertEqual(wallet.current_balance(), Decimal('500.00'))
        self.assertEqual(bank.current_balance(), Decimal('320.00'))
        self.assertEqual(self.inventory.full_dabba_count, Decimal('2.00'))

    def test_delete_purchase_reverses_ledger_and_inventory_impact(self):
        account = FinancialAccount.objects.create(
            name='صندوق',
            account_type='cashbox',
            opening_balance=Decimal('500.00'),
        )
        purchase = self.make_purchase(
            payment_status='paid',
            payment_account=account,
            add_to_inventory=True,
        )

        purchase.delete()

        self.inventory.refresh_from_db()
        self.assertEqual(account.current_balance(), Decimal('500.00'))
        self.assertEqual(self.inventory.full_dabba_count, Decimal('0.00'))


class SupplierAccountingViewTests(SupplierAccountingTests):
    def setUp(self):
        super().setUp()
        from django.contrib.auth.models import User

        self.user = User.objects.create_user(username='manager', password='pass')
        WorkerProfile.objects.create(
            user=self.user,
            full_name='المدير',
            role=WorkerProfile.ROLE_MANAGER,
        )
        self.client.force_login(self.user)

    def test_manager_can_delete_supplier_purchase_and_reverse_effects(self):
        account = FinancialAccount.objects.create(
            name='صندوق',
            account_type='cashbox',
            opening_balance=Decimal('500.00'),
        )
        purchase = self.make_purchase(
            payment_status='paid',
            payment_account=account,
            add_to_inventory=True,
        )

        response = self.client.post(reverse('supplier-purchase-delete', args=[purchase.pk]))

        self.assertRedirects(response, reverse('supplier-detail', args=[self.supplier.pk]))
        self.assertFalse(SupplierPurchase.objects.filter(pk=purchase.pk).exists())
        self.inventory.refresh_from_db()
        self.assertEqual(account.current_balance(), Decimal('500.00'))
        self.assertEqual(self.inventory.full_dabba_count, Decimal('0.00'))

    def test_manager_can_delete_supplier_payment_and_reverse_effects(self):
        account = FinancialAccount.objects.create(
            name='صندوق',
            account_type='cashbox',
            opening_balance=Decimal('500.00'),
        )
        payment = SupplierPayment.objects.create(
            supplier=self.supplier,
            amount=Decimal('50.00'),
            payment_account=account,
            is_new_accounting_payment=True,
        )

        response = self.client.post(reverse('supplier-payment-delete', args=[payment.pk]))

        self.assertRedirects(response, reverse('supplier-detail', args=[self.supplier.pk]))
        self.assertFalse(SupplierPayment.objects.filter(pk=payment.pk).exists())
        self.assertEqual(account.current_balance(), Decimal('500.00'))
