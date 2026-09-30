from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounting.models import FinancialAccount
from accounting.services import post_entry, reverse_entries
from accounts.models import WorkerProfile


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
