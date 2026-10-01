from decimal import Decimal

from django.test import TestCase

from accounting.models import FinancialAccount, LedgerEntry

from finance.models import OperatingExpense


class OperatingExpenseAccountingTests(TestCase):
    def test_operating_expense_posts_out_and_is_profit_deducting_category(self):
        account = FinancialAccount.objects.create(
            name='الصندوق',
            account_type='cashbox',
            opening_balance=Decimal('500.00'),
        )

        expense = OperatingExpense.objects.create(
            name='إيجار',
            category='rent',
            amount=Decimal('100.00'),
            expense_type='operating',
            payment_account=account,
            is_new_accounting_expense=True,
        )

        self.assertEqual(account.current_balance(), Decimal('400.00'))
        self.assertTrue(
            LedgerEntry.objects.filter(
                source_type='operating_expense',
                source_id=expense.pk,
                category='operating_expense',
                is_reversed=False,
            ).exists()
        )

    def test_personal_expense_posts_out_but_uses_personal_category(self):
        account = FinancialAccount.objects.create(
            name='محفظة',
            account_type='wallet',
            opening_balance=Decimal('500.00'),
        )

        expense = OperatingExpense.objects.create(
            name='سحب شخصي',
            category='other',
            amount=Decimal('75.00'),
            expense_type='personal',
            payment_account=account,
            is_new_accounting_expense=True,
        )

        self.assertEqual(account.current_balance(), Decimal('425.00'))
        self.assertTrue(
            LedgerEntry.objects.filter(
                source_type='operating_expense',
                source_id=expense.pk,
                category='personal_expense',
                is_reversed=False,
            ).exists()
        )

    def test_edit_expense_reverses_old_ledger_entry(self):
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
        expense = OperatingExpense.objects.create(
            name='نقل',
            category='transport',
            amount=Decimal('50.00'),
            expense_type='operating',
            payment_account=wallet,
            is_new_accounting_expense=True,
        )

        expense.payment_account = bank
        expense.amount = Decimal('80.00')
        expense.save()

        self.assertEqual(wallet.current_balance(), Decimal('500.00'))
        self.assertEqual(bank.current_balance(), Decimal('420.00'))

    def test_delete_expense_reverses_ledger_entry(self):
        account = FinancialAccount.objects.create(
            name='الصندوق',
            account_type='cashbox',
            opening_balance=Decimal('500.00'),
        )
        expense = OperatingExpense.objects.create(
            name='مواصلات',
            category='transport',
            amount=Decimal('40.00'),
            expense_type='operating',
            payment_account=account,
            is_new_accounting_expense=True,
        )

        expense.delete()

        self.assertEqual(account.current_balance(), Decimal('500.00'))
        self.assertEqual(
            LedgerEntry.objects.filter(source_type='operating_expense', source_id=expense.pk, is_reversed=False).count(),
            0,
        )
