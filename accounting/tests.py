from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from customers.models import Customer
from inventory.models import Inventory
from products.models import Product
from sales.models import Sale
from warehouses.models import Warehouse

from accounting.models import CustomerPayment, FinancialAccount, MoneyTransfer
from accounting.services import (
    get_account_balances,
    get_cashflow_summary,
    get_comprehensive_report,
    get_customer_deferred_balance,
    get_personal_expense_summary,
    get_profit_summary,
    get_worker_balances,
    post_entry,
    reverse_entries,
)
from accounts.models import WorkerProfile
from sales.models import SaleBatch
from sales.services import sync_sale_batch_ledger


class AccountingLedgerTests(TestCase):
    def test_financial_account_balance_includes_opening_and_ledger_entries(self):
        account = FinancialAccount.objects.create(
            name="Cash",
            account_type="cashbox",
            opening_balance=Decimal("100.00"),
        )

        post_entry(account, Decimal("50.00"), "in", "manual_deposit", "deposit", "test", 1)
        post_entry(account, Decimal("20.00"), "out", "manual_withdrawal", "withdrawal", "test", 2)

        self.assertEqual(account.current_balance(), Decimal("130.00"))

    def test_reverse_entries_voids_source_entries(self):
        account = FinancialAccount.objects.create(
            name="Cash",
            account_type="cashbox",
            opening_balance=Decimal("0.00"),
        )
        post_entry(account, Decimal("50.00"), "in", "manual_deposit", "deposit", "test", 1)

        self.assertEqual(reverse_entries("test", 1), 1)
        self.assertEqual(account.current_balance(), Decimal("0.00"))


class AccountingViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="manager", password="pass")
        WorkerProfile.objects.create(
            user=self.user,
            full_name="Manager",
            role=WorkerProfile.ROLE_MANAGER,
        )
        self.client.login(username="manager", password="pass")

    def test_manager_can_create_financial_account(self):
        response = self.client.post(reverse("accounting-account-create"), {
            "name": "محفظة الكريمي",
            "account_type": "wallet",
            "opening_balance": "250.00",
            "is_active": "on",
            "notes": "",
        })

        self.assertRedirects(response, reverse("accounting-account-list"))
        account = FinancialAccount.objects.get(name="محفظة الكريمي")
        self.assertEqual(account.current_balance(), Decimal("250.00"))

    def test_manager_can_add_manual_deposit_to_account(self):
        account = FinancialAccount.objects.create(
            name="الصندوق",
            account_type="cashbox",
            opening_balance=Decimal("100.00"),
        )

        response = self.client.post(reverse("accounting-manual-adjustment"), {
            "account": account.pk,
            "direction": "in",
            "amount": "75.00",
            "category": "manual_deposit",
            "description": "إضافة رصيد",
        })

        self.assertRedirects(response, reverse("accounting-account-detail", args=[account.pk]))
        account.refresh_from_db()
        self.assertEqual(account.current_balance(), Decimal("175.00"))

    def test_manager_can_create_transfer_between_accounts(self):
        source = FinancialAccount.objects.create(
            name="محفظة",
            account_type="wallet",
            opening_balance=Decimal("1000.00"),
        )
        target = FinancialAccount.objects.create(
            name="بنك",
            account_type="bank",
            opening_balance=Decimal("0.00"),
        )

        response = self.client.post(reverse("accounting-transfer-create"), {
            "source_account": source.pk,
            "target_account": target.pk,
            "amount": "300.00",
            "fee_amount": "5.00",
            "description": "تحويل للبنك",
        })

        self.assertRedirects(response, reverse("accounting-account-detail", args=[source.pk]))
        self.assertEqual(source.current_balance(), Decimal("695.00"))
        self.assertEqual(target.current_balance(), Decimal("300.00"))

    def test_manager_can_delete_transfer_and_reverse_entries(self):
        source = FinancialAccount.objects.create(
            name="محفظة",
            account_type="wallet",
            opening_balance=Decimal("1000.00"),
        )
        target = FinancialAccount.objects.create(
            name="بنك",
            account_type="bank",
            opening_balance=Decimal("0.00"),
        )
        transfer = MoneyTransfer.objects.create(
            source_account=source,
            target_account=target,
            amount=Decimal("300.00"),
            fee_amount=Decimal("5.00"),
            description="تحويل للبنك",
        )

        response = self.client.post(reverse("accounting-transfer-delete", args=[transfer.pk]))

        self.assertRedirects(response, reverse("accounting-account-detail", args=[source.pk]))
        self.assertEqual(source.current_balance(), Decimal("1000.00"))
        self.assertEqual(target.current_balance(), Decimal("0.00"))

    def test_manager_can_void_manual_adjustment(self):
        account = FinancialAccount.objects.create(
            name="الصندوق",
            account_type="cashbox",
            opening_balance=Decimal("100.00"),
        )
        entry = post_entry(
            account=account,
            amount=Decimal("75.00"),
            direction="in",
            category="manual_deposit",
            description="إضافة رصيد",
            source_type="manual_adjustment",
            source_id=0,
        )
        entry.source_id = entry.pk
        entry.save(update_fields=["source_id"])

        response = self.client.post(reverse("accounting-manual-adjustment-void", args=[entry.pk]))

        self.assertRedirects(response, reverse("accounting-account-detail", args=[account.pk]))
        self.assertEqual(account.current_balance(), Decimal("100.00"))


class MoneyTransferTests(TestCase):
    def test_transfer_moves_money_between_accounts_and_fee_counts_as_operating_expense(self):
        source = FinancialAccount.objects.create(
            name="Wallet",
            account_type="wallet",
            opening_balance=Decimal("1000.00"),
        )
        target = FinancialAccount.objects.create(
            name="Bank",
            account_type="bank",
            opening_balance=Decimal("0.00"),
        )

        MoneyTransfer.objects.create(
            source_account=source,
            target_account=target,
            amount=Decimal("500.00"),
            fee_amount=Decimal("10.00"),
            description="تحويل إلى البنك",
        )

        self.assertEqual(source.current_balance(), Decimal("490.00"))
        self.assertEqual(target.current_balance(), Decimal("500.00"))


class DeferredCustomerAccountingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="manager2", password="pass")
        self.manager = WorkerProfile.objects.create(
            user=self.user,
            full_name="Manager",
            role=WorkerProfile.ROLE_MANAGER,
        )
        self.customer = Customer.objects.create(name="عميل آجل", phone="777")
        self.warehouse = Warehouse.objects.create(name="حضرموت", city="المكلا")
        self.product = Product.objects.create(
            warehouse=self.warehouse,
            name="سدر",
            purchase_price_per_kg=Decimal("10.00"),
            default_sale_price_per_dabba=Decimal("100.00"),
            default_sale_price_per_kg=Decimal("20.00"),
        )
        Inventory.objects.create(
            product=self.product,
            full_dabba_count=Decimal("10.00"),
            open_kg=Decimal("0.00"),
        )

    def make_deferred_sale(self, amount="100.00"):
        return Sale.objects.create(
            warehouse=self.warehouse,
            worker=self.manager,
            customer=self.customer,
            product=self.product,
            quantity_dabba=Decimal("1.00"),
            price_per_dabba=Decimal(amount),
            quantity_kg=Decimal("0.00"),
            price_per_kg=Decimal("0.00"),
            payment_type="deferred",
            is_new_accounting_sale=True,
        )

    def test_deferred_sale_increases_customer_receivable_report(self):
        self.make_deferred_sale("100.00")

        balance = get_customer_deferred_balance(self.customer)

        self.assertEqual(balance["total_deferred"], Decimal("100.00"))
        self.assertEqual(balance["total_payments"], Decimal("0.00"))
        self.assertEqual(balance["remaining"], Decimal("100.00"))

    def test_customer_payment_posts_money_and_decreases_remaining_customer_balance(self):
        self.make_deferred_sale("100.00")
        account = FinancialAccount.objects.create(name="بنك", account_type="bank")

        CustomerPayment.objects.create(
            customer=self.customer,
            account=account,
            amount=Decimal("40.00"),
            notes="سداد جزئي",
        )

        balance = get_customer_deferred_balance(self.customer)
        self.assertEqual(account.current_balance(), Decimal("40.00"))
        self.assertEqual(balance["total_payments"], Decimal("40.00"))
        self.assertEqual(balance["remaining"], Decimal("60.00"))

    def test_edit_customer_payment_reverses_old_ledger_entry(self):
        self.make_deferred_sale("100.00")
        wallet = FinancialAccount.objects.create(name="محفظة", account_type="wallet")
        bank = FinancialAccount.objects.create(name="بنك", account_type="bank")
        payment = CustomerPayment.objects.create(
            customer=self.customer,
            account=wallet,
            amount=Decimal("40.00"),
        )

        payment.account = bank
        payment.amount = Decimal("70.00")
        payment.save()

        self.assertEqual(wallet.current_balance(), Decimal("0.00"))
        self.assertEqual(bank.current_balance(), Decimal("70.00"))
        self.assertEqual(get_customer_deferred_balance(self.customer)["remaining"], Decimal("30.00"))

    def test_delete_customer_payment_reverses_ledger_entry(self):
        self.make_deferred_sale("100.00")
        account = FinancialAccount.objects.create(name="بنك", account_type="bank")
        payment = CustomerPayment.objects.create(
            customer=self.customer,
            account=account,
            amount=Decimal("40.00"),
        )

        payment.delete()

        self.assertEqual(account.current_balance(), Decimal("0.00"))
        self.assertEqual(get_customer_deferred_balance(self.customer)["remaining"], Decimal("100.00"))


class AccountingReportTests(TestCase):
    def test_account_balances_report_matches_ledger_balances(self):
        cash = FinancialAccount.objects.create(
            name="الصندوق",
            account_type="cashbox",
            opening_balance=Decimal("100.00"),
        )
        wallet = FinancialAccount.objects.create(
            name="محفظة",
            account_type="wallet",
            opening_balance=Decimal("0.00"),
        )
        post_entry(cash, Decimal("50.00"), "in", "manual_deposit", "إضافة", "test", 1)
        post_entry(wallet, Decimal("20.00"), "in", "manual_deposit", "إضافة", "test", 2)

        balances = get_account_balances()

        self.assertEqual(balances[0]["balance"], Decimal("150.00"))
        self.assertEqual(balances[1]["balance"], Decimal("20.00"))

    def test_profit_summary_includes_sales_minus_operating_expenses_and_excludes_personal(self):
        account = FinancialAccount.objects.create(name="الصندوق", account_type="cashbox")
        user = User.objects.create_user(username="profit-manager", password="pass")
        manager = WorkerProfile.objects.create(
            user=user,
            full_name="Manager",
            role=WorkerProfile.ROLE_MANAGER,
        )
        customer = Customer.objects.create(name="عميل آجل")
        warehouse = Warehouse.objects.create(name="حضرموت", city="المكلا")
        product = Product.objects.create(
            warehouse=warehouse,
            name="سدر",
            purchase_price_per_kg=Decimal("10.00"),
            default_sale_price_per_dabba=Decimal("100.00"),
            default_sale_price_per_kg=Decimal("20.00"),
        )
        Inventory.objects.create(product=product, full_dabba_count=Decimal("10.00"))
        Sale.objects.create(
            warehouse=warehouse,
            worker=manager,
            customer=customer,
            product=product,
            quantity_dabba=Decimal("1.00"),
            price_per_dabba=Decimal("100.00"),
            quantity_kg=Decimal("0.00"),
            price_per_kg=Decimal("0.00"),
            payment_type="deferred",
            is_new_accounting_sale=True,
        )
        CustomerPayment.objects.create(customer=customer, account=account, amount=Decimal("100.00"))
        post_entry(account, Decimal("10.00"), "out", "operating_expense", "تشغيل", "expense", 1)
        post_entry(account, Decimal("5.00"), "out", "personal_expense", "شخصي", "expense", 2)

        summary = get_profit_summary(None, None)

        self.assertEqual(summary["sales_total"], Decimal("100.00"))
        self.assertEqual(summary["purchase_total"], Decimal("65.00"))
        self.assertEqual(summary["gross_profit"], Decimal("35.00"))
        self.assertEqual(summary["operating_expenses"], Decimal("10.00"))
        self.assertEqual(summary["personal_expenses"], Decimal("5.00"))
        self.assertEqual(summary["net_profit"], Decimal("25.00"))

    def test_cashflow_summary_groups_money_by_category(self):
        account = FinancialAccount.objects.create(name="الصندوق", account_type="cashbox")
        post_entry(account, Decimal("100.00"), "in", "sale_cash", "بيع", "sale", 1)
        post_entry(account, Decimal("30.00"), "out", "supplier_payment", "سداد", "supplier_payment", 1)

        summary = get_cashflow_summary(None, None)

        self.assertEqual(summary["in"]["sale_cash"], Decimal("100.00"))
        self.assertEqual(summary["out"]["supplier_payment"], Decimal("30.00"))

    def test_worker_balances_report_lists_worker_accounts(self):
        FinancialAccount.objects.create(
            name="عامل 1",
            account_type="worker",
            opening_balance=Decimal("10.00"),
        )
        FinancialAccount.objects.create(
            name="بنك",
            account_type="bank",
            opening_balance=Decimal("50.00"),
        )

        balances = get_worker_balances()

        self.assertEqual(len(balances), 1)
        self.assertEqual(balances[0]["name"], "عامل 1")

    def test_personal_expense_summary_counts_only_personal_expenses(self):
        account = FinancialAccount.objects.create(name="محفظة", account_type="wallet")
        post_entry(account, Decimal("25.00"), "out", "personal_expense", "شخصي", "expense", 1)
        post_entry(account, Decimal("50.00"), "out", "operating_expense", "تشغيل", "expense", 2)

        summary = get_personal_expense_summary(None, None)

        self.assertEqual(summary["total"], Decimal("25.00"))

    def test_comprehensive_report_page_shows_sales_expenses_collection_and_store_totals(self):
        user = User.objects.create_user(username="comprehensive-manager", password="pass")
        manager = WorkerProfile.objects.create(
            user=user,
            full_name="Manager",
            role=WorkerProfile.ROLE_MANAGER,
        )
        customer = Customer.objects.create(name="عميل مختلط")
        warehouse = Warehouse.objects.create(name="حضرموت", city="المكلا")
        product = Product.objects.create(
            warehouse=warehouse,
            name="سدر",
            purchase_price_per_kg=Decimal("10.00"),
            default_sale_price_per_dabba=Decimal("100.00"),
            default_sale_price_per_kg=Decimal("20.00"),
        )
        Inventory.objects.create(product=product, full_dabba_count=Decimal("10.00"))
        worker_account = FinancialAccount.objects.create(name="عهدة المدير", account_type="worker")
        wallet = FinancialAccount.objects.create(name="محفظة سمرة", account_type="wallet")
        batch = SaleBatch.objects.create(
            warehouse=warehouse,
            worker=manager,
            customer=customer,
            store=SaleBatch.STORE_SAMRA,
            payment_type="mixed",
            uses_batch_accounting=True,
            cash_amount=Decimal("30.00"),
            transfer_amount=Decimal("50.00"),
            deferred_amount=Decimal("20.00"),
            cash_worker_account=worker_account,
            payment_account=wallet,
        )
        Sale.objects.create(
            batch=batch,
            warehouse=warehouse,
            worker=manager,
            customer=customer,
            store=SaleBatch.STORE_SAMRA,
            product=product,
            quantity_dabba=Decimal("1.00"),
            price_per_dabba=Decimal("100.00"),
            quantity_kg=Decimal("0.00"),
            price_per_kg=Decimal("0.00"),
            payment_type="mixed",
            is_new_accounting_sale=True,
        )
        sync_sale_batch_ledger(batch)
        post_entry(wallet, Decimal("10.00"), "out", "operating_expense", "تشغيل", "expense", 1)
        post_entry(wallet, Decimal("5.00"), "out", "personal_expense", "شخصي", "expense", 2)
        self.client.force_login(user)

        response = self.client.get(reverse("accounting-comprehensive-report"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "التقرير الشامل")
        self.assertContains(response, "100.00")
        self.assertContains(response, "80.00")
        self.assertContains(response, "20.00")
        self.assertContains(response, "سمرة")
        self.assertContains(response, "طباعة")
