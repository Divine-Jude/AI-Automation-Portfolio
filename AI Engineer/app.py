"""AW Client Report Portal — Flask application."""

from __future__ import annotations

import json
import os
from datetime import date
from decimal import Decimal
from pathlib import Path

from flask import Flask, redirect, render_template, request, send_file, url_for
from io import BytesIO

from calculations import INSURANCE_DEDUCTIBLES_DEMO, metrics_for_client_report
from database import db
from models import Client, QuarterlyReport


def create_app() -> Flask:
    base = Path(__file__).resolve().parent
    instance = base / "instance"
    instance.mkdir(exist_ok=True)

    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-demo-change-me")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{instance / 'app.db'}",
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    with app.app_context():
        db.create_all()
        _seed_demo_if_empty()

    @app.route("/")
    def home():
        return redirect(url_for("clients_list"))

    @app.route("/clients")
    def clients_list():
        clients = Client.query.order_by(Client.id).all()
        return render_template("index.html", clients=clients)

    @app.route("/clients/new", methods=["GET", "POST"])
    def client_new():
        if request.method == "POST":
            c = _client_from_form(request.form)
            db.session.add(c)
            db.session.commit()
            return redirect(url_for("report_form", client_id=c.id))
        return render_template("client_form.html", client=None, report=None, today=date.today())

    @app.route("/clients/<int:client_id>/edit", methods=["GET", "POST"])
    def client_edit(client_id: int):
        c = Client.query.get_or_404(client_id)
        if request.method == "POST":
            _update_client_from_form(c, request.form)
            db.session.commit()
            return redirect(url_for("report_form", client_id=c.id))
        return render_template("client_form.html", client=c, today=date.today())

    @app.route("/clients/<int:client_id>/report", methods=["GET", "POST"])
    def report_form(client_id: int):
        c = Client.query.get_or_404(client_id)
        r = c.quarterly_reports.order_by(QuarterlyReport.id.desc()).first()
        if r is None:
            r = QuarterlyReport(client_id=c.id, period_label="Current quarter")
            db.session.add(r)
            db.session.commit()
        if request.method == "POST":
            _report_from_form(r, request.form)
            db.session.commit()
            if request.headers.get("HX-Request"):
                return _preview_fragment(c, r)
            return redirect(url_for("report_form", client_id=c.id))
        metrics = metrics_for_client_report(c, r)
        ins = float(INSURANCE_DEDUCTIBLES_DEMO)
        return render_template(
            "report_form.html",
            client=c,
            report=r,
            metrics=metrics,
            insurance_ded=ins,
            today=date.today(),
        )

    @app.route("/clients/<int:client_id>/preview", methods=["POST"])
    def report_preview(client_id: int):
        c = Client.query.get_or_404(client_id)
        r = c.quarterly_reports.order_by(QuarterlyReport.id.desc()).first()
        if r is None:
            r = QuarterlyReport(client_id=c.id, period_label="Current quarter")
        _report_from_form(r, request.form)
        return _preview_fragment(c, r)

    @app.route("/clients/<int:client_id>/pdf/sacs")
    def pdf_sacs(client_id: int):
        c = Client.query.get_or_404(client_id)
        r = (
            QuarterlyReport.query.filter_by(client_id=c.id)
            .order_by(QuarterlyReport.id.desc())
            .first_or_404()
        )
        metrics = metrics_for_client_report(c, r)
        html = render_template(
            "sacs_template.html",
            client=c,
            report=r,
            metrics=metrics,
            insurance_ded=float(INSURANCE_DEDUCTIBLES_DEMO),
            today=date.today(),
        )
        from weasyprint import HTML as WeasyHTML

        pdf = WeasyHTML(string=html, base_url=request.url_root).write_pdf()
        return send_file(
            BytesIO(pdf),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"SACS_{c.c1_last_name or 'Client'}_{r.period_label or 'report'}.pdf".replace(" ", "_"),
        )

    @app.route("/clients/<int:client_id>/pdf/tcc")
    def pdf_tcc(client_id: int):
        c = Client.query.get_or_404(client_id)
        r = (
            QuarterlyReport.query.filter_by(client_id=c.id)
            .order_by(QuarterlyReport.id.desc())
            .first_or_404()
        )
        metrics = metrics_for_client_report(c, r)
        ret_c1 = json.loads(r.retirement_c1_json or "{}")
        ret_c2 = json.loads(r.retirement_c2_json or "{}")
        non_ret = json.loads(r.non_retirement_json or "[]")
        liabs = json.loads(r.liabilities_json or "[]")
        html = render_template(
            "tcc_template.html",
            client=c,
            report=r,
            metrics=metrics,
            ret_c1=ret_c1,
            ret_c2=ret_c2,
            non_ret=non_ret,
            liabilities=liabs,
            today=date.today(),
        )
        from weasyprint import HTML as WeasyHTML

        pdf = WeasyHTML(string=html, base_url=request.url_root).write_pdf()
        return send_file(
            BytesIO(pdf),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"TCC_{c.c1_last_name or 'Client'}_{r.period_label or 'report'}.pdf".replace(" ", "_"),
        )

    return app


def _preview_fragment(client: Client, report: QuarterlyReport):
    metrics = metrics_for_client_report(client, report)
    return render_template(
        "partials/_calc_preview.html",
        client=client,
        report=report,
        metrics=metrics,
        insurance_ded=float(INSURANCE_DEDUCTIBLES_DEMO),
    )


def _client_from_form(form) -> Client:
    c = Client()
    _update_client_from_form(c, form)
    return c


def _update_client_from_form(c: Client, form):
    c.is_married = form.get("is_married") == "1"
    c.c1_first_name = form.get("c1_first_name", "").strip()
    c.c1_last_name = form.get("c1_last_name", "").strip()
    c.c1_dob = _parse_date(form.get("c1_dob"))
    c.c1_ssn_last4 = (form.get("c1_ssn_last4") or "").strip()[:4]
    c.c2_first_name = (form.get("c2_first_name") or "").strip() or None
    c.c2_last_name = (form.get("c2_last_name") or "").strip() or None
    c.c2_dob = _parse_date(form.get("c2_dob"))
    c.c2_ssn_last4 = (form.get("c2_ssn_last4") or "").strip()[:4] or None
    c.monthly_salary_after_tax = _dec(form.get("monthly_salary_after_tax"))
    c.agreed_monthly_expense_budget = _dec(form.get("agreed_monthly_expense_budget"))
    c.trust_property_address = (form.get("trust_property_address") or "").strip() or None


def _report_from_form(r: QuarterlyReport, form):
    r.period_label = (form.get("period_label") or "").strip() or r.period_label
    r.inflow = _dec(form.get("inflow"))
    r.outflow = _dec(form.get("outflow"))
    r.trust_zillow_value = _dec(form.get("trust_zillow_value"))
    r.private_reserve_balance = _dec(form.get("private_reserve_balance"))
    r.schwab_balance = _dec(form.get("schwab_balance"))
    r.retirement_c1_json = _safe_json_obj(form.get("retirement_c1_json"), "{}")
    r.retirement_c2_json = _safe_json_obj(form.get("retirement_c2_json"), "{}")
    r.non_retirement_json = _safe_json_arr(form.get("non_retirement_json"), "[]")
    r.liabilities_json = _safe_json_arr(form.get("liabilities_json"), "[]")


def _parse_date(s: str | None):
    if not s:
        return None
    try:
        y, m, d = s.split("-")
        return date(int(y), int(m), int(d))
    except (ValueError, AttributeError):
        return None


def _safe_json_obj(raw: str | None, fallback: str) -> str:
    try:
        json.loads(raw or fallback)
        return raw or fallback
    except (json.JSONDecodeError, TypeError):
        return fallback


def _safe_json_arr(raw: str | None, fallback: str) -> str:
    try:
        v = json.loads(raw or fallback)
        if not isinstance(v, list):
            return fallback
        return raw or fallback
    except (json.JSONDecodeError, TypeError):
        return fallback


def _dec(v) -> Decimal:
    if v is None or v == "":
        return Decimal("0")
    try:
        return Decimal(str(v).replace(",", "").strip())
    except Exception:
        return Decimal("0")


def _seed_demo_if_empty():
    if Client.query.first():
        return

    c = Client(
        is_married=True,
        c1_first_name="Jordan",
        c1_last_name="Ashford",
        c1_dob=date(1984, 5, 12),
        c1_ssn_last4="4821",
        c2_first_name="Morgan",
        c2_last_name="Ashford",
        c2_dob=date(1986, 11, 3),
        c2_ssn_last4="9033",
        monthly_salary_after_tax=Decimal("18500.00"),
        agreed_monthly_expense_budget=Decimal("9500.00"),
        trust_property_address="428 Maple Avenue, Austin, TX 78701",
    )
    db.session.add(c)
    db.session.flush()

    r = QuarterlyReport(
        client_id=c.id,
        period_label="2026 Q1",
        inflow=Decimal("15000.00"),
        outflow=Decimal("11000.00"),
        retirement_c1_json=json.dumps(
            {"Traditional IRA": "122000", "Roth IRA": "52000", "401(k)": "98000"}
        ),
        retirement_c2_json=json.dumps(
            {"Traditional IRA": "88000", "Roth IRA": "76000", "401(k)": "105000"}
        ),
        non_retirement_json=json.dumps(
            [
                {"name": "Joint brokerage (taxable)", "balance": "78000"},
                {"name": "High-yield savings", "balance": "31000"},
            ]
        ),
        trust_zillow_value=Decimal("842000.00"),
        private_reserve_balance=Decimal("41500.00"),
        schwab_balance=Decimal("172500.00"),
        liabilities_json=json.dumps(
            [
                {"name": "Primary mortgage", "balance": "318000", "rate": "6.125"},
                {"name": "Auto loan", "balance": "16800", "rate": "5.49"},
            ]
        ),
    )
    db.session.add(r)
    db.session.commit()


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
