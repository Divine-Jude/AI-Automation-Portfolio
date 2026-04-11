"""ORM models — client profile (static) + quarterly report (balances)."""

from __future__ import annotations

from datetime import date

from database import db


class Client(db.Model):
    __tablename__ = "clients"

    id = db.Column(db.Integer, primary_key=True)
    is_married = db.Column(db.Boolean, nullable=False, default=True)

    c1_first_name = db.Column(db.String(120), nullable=False, default="")
    c1_last_name = db.Column(db.String(120), nullable=False, default="")
    c1_dob = db.Column(db.Date, nullable=True)
    c1_ssn_last4 = db.Column(db.String(4), nullable=True)

    c2_first_name = db.Column(db.String(120), nullable=True)
    c2_last_name = db.Column(db.String(120), nullable=True)
    c2_dob = db.Column(db.Date, nullable=True)
    c2_ssn_last4 = db.Column(db.String(4), nullable=True)

    monthly_salary_after_tax = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    agreed_monthly_expense_budget = db.Column(db.Numeric(14, 2), nullable=False, default=0)

    trust_property_address = db.Column(db.String(500), nullable=True)

    quarterly_reports = db.relationship(
        "QuarterlyReport", backref="client", lazy="dynamic", cascade="all, delete-orphan"
    )

    def age_on(self, d: date | None, dob: date | None) -> int | None:
        if dob is None:
            return None
        today = d or date.today()
        a = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        return a


class QuarterlyReport(db.Model):
    __tablename__ = "quarterly_reports"

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=False)
    period_label = db.Column(db.String(64), nullable=False, default="")

    inflow = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    outflow = db.Column(db.Numeric(14, 2), nullable=False, default=0)

    # JSON strings: {"IRA": "120000", ...} per spouse
    retirement_c1_json = db.Column(db.Text, nullable=False, default="{}")
    retirement_c2_json = db.Column(db.Text, nullable=False, default="{}")
    # [{"name": "Joint Brokerage", "balance": "75000"}, ...]
    non_retirement_json = db.Column(db.Text, nullable=False, default="[]")
    # [{"name": "Mortgage", "balance": "320000", "rate": "6.25"}, ...]
    liabilities_json = db.Column(db.Text, nullable=False, default="[]")

    trust_zillow_value = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    private_reserve_balance = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    schwab_balance = db.Column(db.Numeric(14, 2), nullable=False, default=0)
