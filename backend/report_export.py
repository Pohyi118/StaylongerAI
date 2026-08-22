"""Static executive-report rendering for the Analytics PDF download.

The source of truth is a print-oriented HTML document. Chrome renders that
document to a searchable PDF, so the exported report stays sharp and readable
instead of relying on a screenshot of the responsive dashboard.
"""

from __future__ import annotations

import base64
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from html import escape
from io import BytesIO
from pathlib import Path
from typing import Final
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from backend._embedded_logo import EMBEDDED_LOGO_BASE64


REPORT_PERIODS: Final = ("Last 7 Days", "Last 30 Days", "Last 90 Days")
BRAND_LOGO_PATH: Final = (
    Path.cwd() / "frontend" / "public" / "staylonger-logo.png"
)
BRAND_LOGO_MAX_BYTES: Final = 5 * 1024 * 1024
PNG_SIGNATURE: Final = b"\x89PNG\r\n\x1a\n"

REVENUE_SERIES: Final = (
    {"label": "W1", "protected": 12000, "lost": 4000},
    {"label": "W2", "protected": 18000, "lost": 3000},
    {"label": "W3", "protected": 24000, "lost": 5000},
    {"label": "W4", "protected": 45000, "lost": 2000},
    {"label": "W5", "protected": 85320, "lost": 1000},
)

SEGMENTS: Final = (
    {"name": "Persuadables", "rate": 74, "color": "#0f766e"},
    {"name": "Sure Things", "rate": 98, "color": "#167a5a"},
    {"name": "Sleeping Dogs", "rate": 22, "color": "#b7791f"},
    {"name": "Lost Causes", "rate": 4, "color": "#94a3b8"},
)

INTERVENTIONS: Final = (
    {
        "customer": "Nexora Solutions",
        "action": "WhatsApp rescue",
        "segment": "Persuadable",
        "value": "RM4,800",
        "result": "Recovered",
        "time": "Today, 09:42",
    },
    {
        "customer": "Lumina Tech",
        "action": "Reverse onboarding",
        "segment": "Persuadable",
        "value": "RM8,600",
        "result": "In progress",
        "time": "Today, 08:18",
    },
    {
        "customer": "OrbitWorks",
        "action": "Value Vault credit",
        "segment": "Sleeping Dogs",
        "value": "RM2,100",
        "result": "Recovered",
        "time": "Yesterday",
    },
    {
        "customer": "ScaleForge",
        "action": "Human CSM follow-up",
        "segment": "Persuadable",
        "value": "RM3,200",
        "result": "Awaiting reply",
        "time": "Yesterday",
    },
)


class ReportExportError(RuntimeError):
    """Raised when a report cannot be rendered as a valid PDF."""


def _dashboard_base_url() -> str:
    """Resolve a configured dashboard URL or a managed production URL."""
    configured_url = os.getenv("DASHBOARD_BASE_URL", "").strip().rstrip("/")
    if configured_url:
        return configured_url

    render_url = os.getenv("RENDER_EXTERNAL_URL", "").strip().rstrip("/")
    parsed_render_url = urlparse(render_url)
    if (
        parsed_render_url.scheme == "https"
        and parsed_render_url.netloc
        and not parsed_render_url.path
    ):
        return render_url

    for variable_name in ("VERCEL_PROJECT_PRODUCTION_URL", "VERCEL_URL"):
        domain = os.getenv(variable_name, "").strip().strip("/")
        parsed = urlparse(f"https://{domain}")
        if domain and parsed.scheme == "https" and parsed.netloc == domain:
            return f"https://{domain}"

    return ""


def _brand_logo_bytes() -> bytes:
    """Load the canonical logo locally, from the dashboard, or the bundle.

    Vercel deploys the backend independently from the Vite application, so the
    report keeps an embedded copy for serverless rendering without a network
    round trip. Other runtimes can still use the deployed dashboard as the
    canonical fallback asset host.
    """
    def embedded_logo() -> bytes:
        try:
            return base64.b64decode(EMBEDDED_LOGO_BASE64, validate=True)
        except (ValueError, TypeError):
            return b""

    try:
        logo = BRAND_LOGO_PATH.read_bytes()
    except OSError:
        logo = b""

    if not logo and os.getenv("VERCEL") == "1":
        logo = embedded_logo()

    if not logo:
        dashboard_base_url = _dashboard_base_url()
        parsed_base_url = urlparse(dashboard_base_url)
        if (
            parsed_base_url.scheme in {"http", "https"}
            and parsed_base_url.netloc
        ):
            logo_url = urljoin(
                f"{dashboard_base_url.rstrip('/')}/", "staylonger-logo.png"
            )
            request = Request(
                logo_url,
                headers={"User-Agent": "StayLongerAI-report-export/1.0"},
            )
            try:
                with urlopen(request, timeout=5) as response:
                    logo = response.read(BRAND_LOGO_MAX_BYTES + 1)
            except OSError:
                logo = b""

    if not logo:
        logo = embedded_logo()

    if len(logo) > BRAND_LOGO_MAX_BYTES or not logo.startswith(PNG_SIGNATURE):
        raise ReportExportError("The report logo is unavailable.")
    return logo


def _brand_logo_data_uri() -> str:
    """Return the canonical brand mark as a self-contained report image."""
    encoded_logo = base64.b64encode(_brand_logo_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded_logo}"


def _format_money(value: int) -> str:
    return f"RM{value:,.0f}"


def _format_compact_money(value: int) -> str:
    return f"RM{value / 1000:.1f}k"


def _chrome_executable() -> str | None:
    """Return a local Chromium executable without requiring a new dependency."""
    configured = os.getenv("REPORT_CHROME_BIN") or os.getenv("CHROME_BIN")
    if configured and Path(configured).is_file():
        return configured

    for command in ("chrome", "google-chrome", "chromium", "chromium-browser", "msedge"):
        discovered = shutil.which(command)
        if discovered:
            return discovered

    program_roots = (
        os.getenv("PROGRAMFILES"),
        os.getenv("PROGRAMFILES(X86)"),
        os.getenv("LOCALAPPDATA"),
    )
    suffixes = (
        Path("Google/Chrome/Application/chrome.exe"),
        Path("Microsoft/Edge/Application/msedge.exe"),
    )
    for root in filter(None, program_roots):
        for suffix in suffixes:
            candidate = Path(root) / suffix
            if candidate.is_file():
                return str(candidate)
    return None


def _render_revenue_chart() -> str:
    highest_value = max(entry["protected"] for entry in REVENUE_SERIES)
    bars = []
    for entry in REVENUE_SERIES:
        protected_height = max(4, round(entry["protected"] / highest_value * 100))
        lost_height = max(4, round(entry["lost"] / highest_value * 100))
        bars.append(
            f"""
            <div class=\"weekly-column\">
              <div class=\"weekly-bars\" aria-label=\"{entry['label']}: {_format_money(entry['protected'])} protected and {_format_money(entry['lost'])} lost\">
                <span class=\"weekly-bar protected\" style=\"height:{protected_height}%\"></span>
                <span class=\"weekly-bar lost\" style=\"height:{lost_height}%\"></span>
              </div>
              <span class=\"weekly-label\">{entry['label']}</span>
              <span class=\"weekly-values\">{_format_compact_money(entry['protected'])}</span>
            </div>
            """
        )
    return "".join(bars)


def _render_segment_chart() -> str:
    rows = []
    for segment in SEGMENTS:
        rows.append(
            f"""
            <div class=\"segment-row\">
              <span class=\"segment-name\">{escape(segment['name'])}</span>
              <span class=\"segment-track\"><span class=\"segment-fill\" style=\"width:{segment['rate']}%;background:{segment['color']}\"></span></span>
              <strong>{segment['rate']}%</strong>
            </div>
            """
        )
    return "".join(rows)


def _render_intervention_rows() -> str:
    outcome_class = {
        "Recovered": "outcome-recovered",
        "In progress": "outcome-progress",
        "Awaiting reply": "outcome-awaiting",
    }
    rows = []
    for intervention in INTERVENTIONS:
        rows.append(
            "<tr>"
            f"<td><strong>{escape(intervention['customer'])}</strong></td>"
            f"<td>{escape(intervention['action'])}</td>"
            f"<td>{escape(intervention['segment'])}</td>"
            f"<td class=\"value-cell\">{escape(intervention['value'])}</td>"
            f"<td><span class=\"outcome {outcome_class[intervention['result']]}\">{escape(intervention['result'])}</span></td>"
            f"<td class=\"time-cell\">{escape(intervention['time'])}</td>"
            "</tr>"
        )
    return "".join(rows)


def build_report_html(period: str, generated_at: datetime | None = None) -> str:
    """Build the printable report source for a supported reporting period."""
    if period not in REPORT_PERIODS:
        raise ReportExportError("Unsupported report period.")

    generated_at = generated_at or datetime.now(timezone.utc)
    generated_label = generated_at.strftime("%d %B %Y, %H:%M UTC")
    safe_period = escape(period)
    logo_data_uri = _brand_logo_data_uri()

    return f"""<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>StayLongerAI Retention Performance Report — {safe_period}</title>
    <style>
      @page {{ size: A4; margin: 12mm 11mm 13mm; }}
      * {{ box-sizing: border-box; }}
      html {{ color: #0f172a; background: #fff; }}
      body {{ margin: 0; font-family: Arial, Helvetica, sans-serif; font-size: 10px; line-height: 1.45; color: #243044; background: #fff; }}
      h1, h2, h3, p {{ margin: 0; }}
      .report-header {{ display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #dbe5e5; padding-bottom: 12px; }}
      .brand {{ display: flex; align-items: center; gap: 9px; }}
      .brand-logo {{ display: block; width: 32px; height: 32px; border: 1px solid #dbeafe; border-radius: 8px; object-fit: contain; box-shadow: 0 3px 8px rgba(37, 99, 235, 0.12); }}
      .brand-name {{ color: #0f172a; font-size: 12px; font-weight: 800; letter-spacing: -0.35px; }}
      .brand-kicker {{ margin-top: 1px; color: #64748b; font-size: 8px; font-weight: 700; letter-spacing: 0.85px; text-transform: uppercase; }}
      .document-tag {{ border: 1px solid #b8d9d5; border-radius: 999px; padding: 5px 8px; color: #0f766e; font-size: 8px; font-weight: 800; letter-spacing: 0.6px; text-transform: uppercase; }}
      .title-block {{ padding: 24px 0 18px; }}
      .eyebrow {{ color: #0f766e; font-size: 8px; font-weight: 800; letter-spacing: 1.25px; text-transform: uppercase; }}
      h1 {{ margin-top: 5px; color: #0f172a; font-size: 27px; line-height: 1.08; letter-spacing: -1.15px; }}
      .title-copy {{ max-width: 600px; margin-top: 8px; color: #526176; font-size: 11px; line-height: 1.55; }}
      .metadata {{ display: flex; gap: 15px; margin-top: 14px; color: #64748b; font-size: 8.5px; }}
      .metadata strong {{ color: #334155; }}
      .section {{ margin-top: 16px; break-inside: avoid; }}
      .section-heading {{ margin-bottom: 9px; color: #0f172a; font-size: 13px; letter-spacing: -0.25px; }}
      .section-description {{ margin: -3px 0 10px; color: #64748b; font-size: 9px; }}
      .summary-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 9px; }}
      .summary-card {{ min-height: 88px; border: 1px solid #dce7e6; border-radius: 10px; padding: 11px; background: #fbfefd; }}
      .summary-card h3 {{ color: #0f172a; font-size: 10px; line-height: 1.25; }}
      .summary-card p {{ margin-top: 5px; color: #536176; font-size: 9px; line-height: 1.5; }}
      .summary-card strong {{ color: #0f766e; }}
      .kpi-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }}
      .kpi-card {{ min-height: 80px; border: 1px solid #e1e8ef; border-radius: 10px; padding: 10px; background: #fff; }}
      .kpi-label {{ color: #64748b; font-size: 8px; font-weight: 700; letter-spacing: 0.4px; text-transform: uppercase; }}
      .kpi-value {{ margin-top: 7px; color: #0f172a; font-size: 18px; font-weight: 800; letter-spacing: -0.6px; }}
      .kpi-detail {{ margin-top: 3px; color: #0f766e; font-size: 8.5px; font-weight: 700; }}
      .two-column {{ display: grid; grid-template-columns: 1.28fr 1fr; gap: 11px; }}
      .panel {{ min-height: 222px; border: 1px solid #e1e8ef; border-radius: 10px; padding: 12px; background: #fff; break-inside: avoid; }}
      .panel-title {{ color: #0f172a; font-size: 11px; font-weight: 800; }}
      .panel-subtitle {{ margin-top: 3px; color: #64748b; font-size: 8.5px; }}
      .legend {{ display: flex; gap: 9px; margin-top: 9px; color: #64748b; font-size: 8px; font-weight: 700; }}
      .legend i {{ display: inline-block; width: 7px; height: 7px; margin-right: 4px; border-radius: 2px; vertical-align: -1px; }}
      .weekly-chart {{ display: grid; grid-template-columns: repeat(5, 1fr); align-items: end; gap: 5px; height: 137px; margin-top: 7px; border-bottom: 1px solid #cbd5e1; }}
      .weekly-column {{ display: grid; grid-template-rows: 102px auto auto; justify-items: center; min-width: 0; }}
      .weekly-bars {{ display: flex; align-items: end; justify-content: center; gap: 3px; width: 100%; height: 102px; }}
      .weekly-bar {{ display: block; width: 13px; min-height: 3px; border-radius: 3px 3px 0 0; }}
      .weekly-bar.protected {{ background: #0f766e; }}
      .weekly-bar.lost {{ background: #f2a9b5; }}
      .weekly-label {{ margin-top: 4px; color: #475569; font-size: 8px; font-weight: 800; }}
      .weekly-values {{ margin-top: 1px; color: #64748b; font-size: 7px; white-space: nowrap; }}
      .segment-chart {{ margin-top: 20px; }}
      .segment-row {{ display: grid; grid-template-columns: 78px 1fr 26px; align-items: center; gap: 7px; margin: 10px 0; }}
      .segment-name {{ color: #475569; font-size: 8.5px; font-weight: 700; }}
      .segment-track {{ display: block; height: 9px; overflow: hidden; border-radius: 999px; background: #edf2f7; }}
      .segment-fill {{ display: block; height: 100%; border-radius: inherit; }}
      .segment-row strong {{ color: #0f172a; font-size: 8.5px; text-align: right; }}
      .insight {{ display: flex; gap: 7px; margin-top: 14px; border-radius: 8px; padding: 9px; background: #f0fdfa; color: #334155; font-size: 8.5px; line-height: 1.45; }}
      .insight b {{ color: #0f766e; }}
      .next-steps {{ display: grid; grid-template-columns: 1fr 1fr; gap: 11px; }}
      .callout {{ border-radius: 10px; padding: 12px; background: #0f172a; color: #e8f3f2; break-inside: avoid; }}
      .callout h2 {{ color: #fff; font-size: 12px; }}
      .callout ol {{ margin: 8px 0 0; padding-left: 17px; }}
      .callout li {{ margin: 4px 0; font-size: 8.5px; line-height: 1.45; }}
      .scope-note {{ border: 1px solid #e1e8ef; border-radius: 10px; padding: 12px; break-inside: avoid; }}
      .scope-note h2 {{ color: #0f172a; font-size: 12px; }}
      .scope-note p {{ margin-top: 7px; color: #64748b; font-size: 8.5px; line-height: 1.5; }}
      .table-wrap {{ overflow: hidden; border: 1px solid #e1e8ef; border-radius: 10px; }}
      table {{ width: 100%; border-collapse: collapse; }}
      thead {{ display: table-header-group; background: #f8fafc; }}
      th {{ padding: 8px 8px; color: #64748b; font-size: 7.5px; font-weight: 800; letter-spacing: 0.55px; text-align: left; text-transform: uppercase; }}
      td {{ padding: 9px 8px; border-top: 1px solid #edf2f7; color: #475569; font-size: 8.5px; vertical-align: middle; }}
      tr {{ break-inside: avoid; }}
      td strong {{ color: #0f172a; }}
      .value-cell {{ color: #0f766e; font-weight: 800; white-space: nowrap; }}
      .time-cell {{ color: #64748b; text-align: right; white-space: nowrap; }}
      .outcome {{ display: inline-block; border-radius: 999px; padding: 3px 5px; font-size: 7.5px; font-weight: 800; white-space: nowrap; }}
      .outcome-recovered {{ background: #dcfce7; color: #167a5a; }}
      .outcome-progress {{ background: #ccfbf1; color: #0f766e; }}
      .outcome-awaiting {{ background: #fef3c7; color: #9a5b12; }}
      .footer {{ display: flex; justify-content: space-between; gap: 12px; margin-top: 14px; padding-top: 8px; border-top: 1px solid #dbe5e5; color: #94a3b8; font-size: 7.5px; }}
      @media print {{ .section, .panel, .summary-card, .kpi-card, .callout, .scope-note {{ break-inside: avoid; }} }}
    </style>
  </head>
  <body>
    <main>
      <header class=\"report-header\">
        <div class=\"brand\">
          <img class=\"brand-logo\" src=\"{logo_data_uri}\" alt=\"\" />
          <div><div class=\"brand-name\">StayLongerAI</div><div class=\"brand-kicker\">Retention intelligence</div></div>
        </div>
        <span class=\"document-tag\">Executive report</span>
      </header>

      <section class=\"title-block\">
        <p class=\"eyebrow\">Retention performance</p>
        <h1>Revenue protection, made visible.</h1>
        <p class=\"title-copy\">A decision-ready view of the retention work that protected revenue, the segments responding to intervention, and the accounts that need the next human touch.</p>
        <div class=\"metadata\"><span><strong>Reporting period:</strong> {safe_period}</span><span><strong>Prepared:</strong> {generated_label}</span><span><strong>Audience:</strong> Leadership team</span></div>
      </section>

      <section class=\"section\">
        <h2 class=\"section-heading\">Executive Summary</h2>
        <div class=\"summary-grid\">
          <article class=\"summary-card\"><h3><strong>Revenue protection accelerated.</strong></h3><p>RM184,320 is protected this period, up 24% from the comparison period and led by the final two reporting weeks.</p></article>
          <article class=\"summary-card\"><h3><strong>AI-led work is producing leverage.</strong></h3><p>Interventions are returning 8.4x for every RM1 invested, with 47 accounts rescued across automated and human-led plays.</p></article>
          <article class=\"summary-card\"><h3><strong>Prioritize persuadable accounts.</strong></h3><p>Persuadables continue to respond to targeted outreach; their next CSM follow-up should be protected from delay.</p></article>
        </div>
      </section>

      <section class=\"section\">
        <h2 class=\"section-heading\">Current retention position</h2>
        <div class=\"kpi-grid\">
          <article class=\"kpi-card\"><p class=\"kpi-label\">Revenue protected</p><p class=\"kpi-value\">RM184,320</p><p class=\"kpi-detail\">+24% vs last period</p></article>
          <article class=\"kpi-card\"><p class=\"kpi-label\">Intervention ROI</p><p class=\"kpi-value\">8.4x</p><p class=\"kpi-detail\">Per RM1 invested</p></article>
          <article class=\"kpi-card\"><p class=\"kpi-label\">At-risk revenue</p><p class=\"kpi-value\">RM91,200</p><p class=\"kpi-detail\">-12.6% vs last period</p></article>
          <article class=\"kpi-card\"><p class=\"kpi-label\">Accounts rescued</p><p class=\"kpi-value\">47</p><p class=\"kpi-detail\">38 AI-led · 9 human-led</p></article>
        </div>
      </section>

      <section class=\"section two-column\">
        <article class=\"panel\">
          <h2 class=\"panel-title\">Revenue outcome by reporting week</h2>
          <p class=\"panel-subtitle\">Protected and lost revenue in Malaysian ringgit.</p>
          <div class=\"legend\"><span><i style=\"background:#0f766e\"></i>Protected</span><span><i style=\"background:#f2a9b5\"></i>Lost</span></div>
          <div class=\"weekly-chart\">{_render_revenue_chart()}</div>
        </article>
        <article class=\"panel\">
          <h2 class=\"panel-title\">Retention rate by customer segment</h2>
          <p class=\"panel-subtitle\">Share of segment accounts retained after intervention.</p>
          <div class=\"segment-chart\">{_render_segment_chart()}</div>
          <p class=\"insight\"><span><b>Key insight:</b></span><span>Persuadables are the strongest near-term opportunity for targeted rescue work; combine AI prompts with CSM availability.</span></p>
        </article>
      </section>

      <section class=\"section next-steps\">
        <article class=\"callout\"><h2>Recommended next steps</h2><ol><li>Assign named owners to the highest-value persuadable accounts within one business day.</li><li>Keep Value Vault credits focused on accounts showing a credible recovery signal.</li><li>Review the weekly protected-versus-lost trend in the next operating meeting.</li></ol></article>
        <article class=\"scope-note\"><h2>Data scope</h2><p>This export reflects the retention data currently shown in the StayLongerAI workspace. Connect production event and billing sources before using it as the basis for an external financial commitment.</p></article>
      </section>

      <section class=\"section\">
        <h2 class=\"section-heading\">Intervention outcomes</h2>
        <p class=\"section-description\">Representative actions included in this reporting period, with current outcome status and protected value.</p>
        <div class=\"table-wrap\"><table><thead><tr><th>Customer</th><th>AI action</th><th>Segment</th><th>Value impact</th><th>Outcome</th><th style=\"text-align:right\">Recorded</th></tr></thead><tbody>{_render_intervention_rows()}</tbody></table></div>
      </section>

      <footer class=\"footer\"><span>StayLongerAI · Confidential retention performance report</span><span>Generated {generated_label}</span></footer>
    </main>
  </body>
</html>"""


def _render_report_pdf_with_chrome(period: str, chrome: str) -> bytes:
    """Render the static report HTML to a PDF through local Chrome/Chromium."""
    with tempfile.TemporaryDirectory(prefix="staylongerai-report-") as workspace:
        workspace_path = Path(workspace)
        html_path = workspace_path / "retention-report.html"
        pdf_path = workspace_path / "retention-report.pdf"
        profile_path = workspace_path / "chrome-profile"
        html_path.write_text(build_report_html(period), encoding="utf-8")

        command = [
            chrome,
            "--headless=new",
            "--disable-gpu",
            "--no-first-run",
            "--no-default-browser-check",
            "--no-pdf-header-footer",
            "--allow-file-access-from-files",
            "--run-all-compositor-stages-before-draw",
            "--virtual-time-budget=500",
            f"--user-data-dir={profile_path}",
            f"--print-to-pdf={pdf_path}",
            html_path.resolve().as_uri(),
        ]
        run_options: dict[str, object] = {
            "capture_output": True,
            "text": True,
            "timeout": 45,
            "check": False,
        }
        if os.name == "nt":
            run_options["creationflags"] = subprocess.CREATE_NO_WINDOW

        try:
            result = subprocess.run(command, **run_options)
        except (OSError, subprocess.TimeoutExpired) as error:
            raise ReportExportError("The PDF renderer could not start.") from error

        if result.returncode != 0 or not pdf_path.is_file() or pdf_path.stat().st_size < 1024:
            raise ReportExportError("The PDF renderer did not produce a valid report.")
        return pdf_path.read_bytes()


def _render_report_pdf_with_reportlab(period: str) -> bytes:
    """Render a branded PDF when Chromium is unavailable in a serverless runtime."""
    if period not in REPORT_PERIODS:
        raise ReportExportError("Unsupported report period.")

    try:
        from reportlab.graphics.shapes import Drawing, Line, Rect, String
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_RIGHT
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            HRFlowable,
            Image,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError as error:
        raise ReportExportError(
            "The serverless PDF renderer is unavailable. Install reportlab."
        ) from error

    generated_at = datetime.now(timezone.utc)
    generated_label = generated_at.strftime("%d %B %Y, %H:%M UTC")
    safe_period = escape(period)

    ink = colors.HexColor("#0F172A")
    slate = colors.HexColor("#475569")
    muted = colors.HexColor("#64748B")
    border = colors.HexColor("#DCE7E6")
    teal = colors.HexColor("#0F766E")
    soft_slate = colors.HexColor("#F8FAFC")
    rose = colors.HexColor("#F2A9B5")
    green = colors.HexColor("#167A5A")
    amber = colors.HexColor("#9A5B12")

    page_width, _ = A4
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        title=f"StayLongerAI Retention Performance Report - {period}",
        author="StayLongerAI",
        leftMargin=11 * mm,
        rightMargin=11 * mm,
        topMargin=12 * mm,
        bottomMargin=16 * mm,
    )
    content_width = page_width - document.leftMargin - document.rightMargin

    style_sheet = getSampleStyleSheet()
    styles = {
        "brand": ParagraphStyle(
            "ReportBrand",
            parent=style_sheet["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=13,
            textColor=ink,
            spaceAfter=0,
        ),
        "brand_kicker": ParagraphStyle(
            "ReportBrandKicker",
            parent=style_sheet["Normal"],
            fontName="Helvetica-Bold",
            fontSize=6.8,
            leading=9,
            textColor=muted,
            spaceAfter=0,
        ),
        "tag": ParagraphStyle(
            "ReportTag",
            parent=style_sheet["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=9,
            textColor=teal,
            alignment=TA_RIGHT,
            spaceAfter=0,
        ),
        "eyebrow": ParagraphStyle(
            "ReportEyebrow",
            parent=style_sheet["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=9,
            textColor=teal,
            spaceAfter=3,
        ),
        "title": ParagraphStyle(
            "ReportTitle",
            parent=style_sheet["Normal"],
            fontName="Helvetica-Bold",
            fontSize=24,
            leading=27,
            textColor=ink,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "ReportBody",
            parent=style_sheet["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=slate,
            spaceAfter=0,
        ),
        "metadata": ParagraphStyle(
            "ReportMetadata",
            parent=style_sheet["Normal"],
            fontName="Helvetica",
            fontSize=7,
            leading=9,
            textColor=muted,
            spaceAfter=0,
        ),
        "section": ParagraphStyle(
            "ReportSection",
            parent=style_sheet["Normal"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=14,
            textColor=ink,
            spaceAfter=5,
        ),
        "section_description": ParagraphStyle(
            "ReportSectionDescription",
            parent=style_sheet["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=10,
            textColor=muted,
            spaceAfter=6,
        ),
        "card_title": ParagraphStyle(
            "ReportCardTitle",
            parent=style_sheet["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            textColor=ink,
            spaceAfter=3,
        ),
        "card_body": ParagraphStyle(
            "ReportCardBody",
            parent=style_sheet["Normal"],
            fontName="Helvetica",
            fontSize=7.3,
            leading=10,
            textColor=slate,
            spaceAfter=0,
        ),
        "kpi_label": ParagraphStyle(
            "ReportKpiLabel",
            parent=style_sheet["Normal"],
            fontName="Helvetica-Bold",
            fontSize=6.4,
            leading=8,
            textColor=muted,
            spaceAfter=4,
        ),
        "kpi_value": ParagraphStyle(
            "ReportKpiValue",
            parent=style_sheet["Normal"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=18,
            textColor=ink,
            spaceAfter=2,
        ),
        "kpi_detail": ParagraphStyle(
            "ReportKpiDetail",
            parent=style_sheet["Normal"],
            fontName="Helvetica-Bold",
            fontSize=6.8,
            leading=8,
            textColor=teal,
            spaceAfter=0,
        ),
        "panel_title": ParagraphStyle(
            "ReportPanelTitle",
            parent=style_sheet["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9.5,
            leading=11,
            textColor=ink,
            spaceAfter=2,
        ),
        "panel_subtitle": ParagraphStyle(
            "ReportPanelSubtitle",
            parent=style_sheet["Normal"],
            fontName="Helvetica",
            fontSize=6.8,
            leading=9,
            textColor=muted,
            spaceAfter=0,
        ),
        "white_title": ParagraphStyle(
            "ReportWhiteTitle",
            parent=style_sheet["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10.5,
            leading=13,
            textColor=colors.white,
            spaceAfter=4,
        ),
        "white_body": ParagraphStyle(
            "ReportWhiteBody",
            parent=style_sheet["Normal"],
            fontName="Helvetica",
            fontSize=7.4,
            leading=10.5,
            textColor=colors.HexColor("#E8F3F2"),
            spaceAfter=0,
        ),
        "table_header": ParagraphStyle(
            "ReportTableHeader",
            parent=style_sheet["Normal"],
            fontName="Helvetica-Bold",
            fontSize=6.2,
            leading=7.5,
            textColor=muted,
            spaceAfter=0,
        ),
        "table_cell": ParagraphStyle(
            "ReportTableCell",
            parent=style_sheet["Normal"],
            fontName="Helvetica",
            fontSize=7.1,
            leading=9,
            textColor=slate,
            spaceAfter=0,
        ),
        "table_customer": ParagraphStyle(
            "ReportTableCustomer",
            parent=style_sheet["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.1,
            leading=9,
            textColor=ink,
            spaceAfter=0,
        ),
        "table_value": ParagraphStyle(
            "ReportTableValue",
            parent=style_sheet["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.1,
            leading=9,
            textColor=teal,
            spaceAfter=0,
        ),
    }

    def revenue_chart() -> Drawing:
        width = 96 * mm
        height = 58 * mm
        baseline = 10 * mm
        chart_height = 37 * mm
        left = 6 * mm
        column_width = 17 * mm
        bar_width = 5 * mm
        chart = Drawing(width, height)
        chart.add(
            Line(
                left,
                baseline,
                width - 4 * mm,
                baseline,
                strokeColor=colors.HexColor("#CBD5E1"),
                strokeWidth=0.7,
            )
        )
        highest_value = max(entry["protected"] for entry in REVENUE_SERIES)
        for index, entry in enumerate(REVENUE_SERIES):
            x = left + index * column_width + 2 * mm
            protected_height = max(
                3 * mm, entry["protected"] / highest_value * chart_height
            )
            lost_height = max(2 * mm, entry["lost"] / highest_value * chart_height)
            chart.add(
                Rect(
                    x,
                    baseline,
                    bar_width,
                    protected_height,
                    fillColor=teal,
                    strokeColor=None,
                )
            )
            chart.add(
                Rect(
                    x + 6 * mm,
                    baseline,
                    bar_width,
                    lost_height,
                    fillColor=rose,
                    strokeColor=None,
                )
            )
            chart.add(
                String(
                    x,
                    5 * mm,
                    entry["label"],
                    fontName="Helvetica-Bold",
                    fontSize=6,
                    fillColor=slate,
                )
            )
            chart.add(
                String(
                    x - 1 * mm,
                    1.5 * mm,
                    _format_compact_money(entry["protected"]),
                    fontName="Helvetica",
                    fontSize=5.2,
                    fillColor=muted,
                )
            )
        return chart

    def segment_chart() -> Drawing:
        width = 70 * mm
        height = 58 * mm
        label_width = 29 * mm
        track_width = 31 * mm
        chart = Drawing(width, height)
        for index, segment in enumerate(SEGMENTS):
            y = height - (10 + index * 12) * mm
            chart.add(
                String(
                    0,
                    y,
                    segment["name"],
                    fontName="Helvetica-Bold",
                    fontSize=6.1,
                    fillColor=slate,
                )
            )
            chart.add(
                Rect(
                    label_width,
                    y - 1 * mm,
                    track_width,
                    3.2 * mm,
                    fillColor=colors.HexColor("#EDF2F7"),
                    strokeColor=None,
                )
            )
            chart.add(
                Rect(
                    label_width,
                    y - 1 * mm,
                    track_width * segment["rate"] / 100,
                    3.2 * mm,
                    fillColor=colors.HexColor(segment["color"]),
                    strokeColor=None,
                )
            )
            chart.add(
                String(
                    label_width + track_width + 2 * mm,
                    y,
                    f"{segment['rate']}%",
                    fontName="Helvetica-Bold",
                    fontSize=6.1,
                    fillColor=ink,
                )
            )
        return chart

    def page_footer(canvas, _document) -> None:
        canvas.saveState()
        canvas.setStrokeColor(border)
        canvas.setLineWidth(0.4)
        canvas.line(
            document.leftMargin,
            10 * mm,
            page_width - document.rightMargin,
            10 * mm,
        )
        canvas.setFillColor(muted)
        canvas.setFont("Helvetica", 6.5)
        canvas.drawString(
            document.leftMargin,
            6.5 * mm,
            "StayLongerAI - Confidential retention performance report",
        )
        canvas.drawRightString(
            page_width - document.rightMargin,
            6.5 * mm,
            f"Page {canvas.getPageNumber()}",
        )
        canvas.restoreState()

    logo = Image(BytesIO(_brand_logo_bytes()), width=13 * mm, height=13 * mm)
    brand = Table(
        [
            [
                logo,
                [
                    Paragraph("StayLongerAI", styles["brand"]),
                    Paragraph("RETENTION INTELLIGENCE", styles["brand_kicker"]),
                ],
            ]
        ],
        colWidths=[16 * mm, 104 * mm],
    )
    brand.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    header = Table(
        [[brand, Paragraph("EXECUTIVE REPORT", styles["tag"])]],
        colWidths=[128 * mm, content_width - 128 * mm],
    )
    header.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    story = [
        header,
        Spacer(1, 3 * mm),
        HRFlowable(width="100%", thickness=0.6, color=border, spaceAfter=8 * mm),
        Paragraph("RETENTION PERFORMANCE", styles["eyebrow"]),
        Paragraph("Revenue protection, made visible.", styles["title"]),
        Paragraph(
            "A decision-ready view of the retention work that protected revenue, "
            "the segments responding to intervention, and the accounts that need "
            "the next human touch.",
            styles["body"],
        ),
        Spacer(1, 4 * mm),
        Paragraph(
            f"<b>Reporting period:</b> {safe_period} &nbsp;&nbsp;&nbsp; "
            f"<b>Prepared:</b> {generated_label} &nbsp;&nbsp;&nbsp; "
            "<b>Audience:</b> Leadership team",
            styles["metadata"],
        ),
        Spacer(1, 7 * mm),
        Paragraph("Executive Summary", styles["section"]),
    ]

    summary_cards = Table(
        [
            [
                [
                    Paragraph(
                        "<font color='#0F766E'>Revenue protection accelerated.</font>",
                        styles["card_title"],
                    ),
                    Paragraph(
                        "RM184,320 is protected this period, up 24% from the comparison period and led by the final two reporting weeks.",
                        styles["card_body"],
                    ),
                ],
                [
                    Paragraph(
                        "<font color='#0F766E'>AI-led work is producing leverage.</font>",
                        styles["card_title"],
                    ),
                    Paragraph(
                        "Interventions are returning 8.4x for every RM1 invested, with 47 accounts rescued across automated and human-led plays.",
                        styles["card_body"],
                    ),
                ],
                [
                    Paragraph(
                        "<font color='#0F766E'>Prioritize persuadable accounts.</font>",
                        styles["card_title"],
                    ),
                    Paragraph(
                        "Persuadables continue to respond to targeted outreach; their next CSM follow-up should be protected from delay.",
                        styles["card_body"],
                    ),
                ],
            ]
        ],
        colWidths=[content_width / 3] * 3,
    )
    summary_cards.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.6, border),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FBFEFD")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 4 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4 * mm),
            ]
        )
    )
    story.extend(
        [
            summary_cards,
            Spacer(1, 6 * mm),
            Paragraph("Current retention position", styles["section"]),
        ]
    )

    kpi_values = (
        ("REVENUE PROTECTED", "RM184,320", "+24% vs last period"),
        ("INTERVENTION ROI", "8.4x", "Per RM1 invested"),
        ("AT-RISK REVENUE", "RM91,200", "-12.6% vs last period"),
        ("ACCOUNTS RESCUED", "47", "38 AI-led / 9 human-led"),
    )
    kpi_cards = Table(
        [
            [
                [
                    Paragraph(label, styles["kpi_label"]),
                    Paragraph(value, styles["kpi_value"]),
                    Paragraph(detail, styles["kpi_detail"]),
                ]
                for label, value, detail in kpi_values
            ]
        ],
        colWidths=[content_width / 4] * 4,
    )
    kpi_cards.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E1E8EF")),
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3.5 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3.5 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 3.5 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5 * mm),
            ]
        )
    )
    story.extend([kpi_cards, Spacer(1, 6 * mm)])

    chart_panels = Table(
        [
            [
                [
                    Paragraph("Revenue outcome by reporting week", styles["panel_title"]),
                    Paragraph(
                        "Protected and lost revenue in Malaysian ringgit.",
                        styles["panel_subtitle"],
                    ),
                    Spacer(1, 2 * mm),
                    revenue_chart(),
                ],
                [
                    Paragraph("Retention rate by customer segment", styles["panel_title"]),
                    Paragraph(
                        "Share of segment accounts retained after intervention.",
                        styles["panel_subtitle"],
                    ),
                    Spacer(1, 2 * mm),
                    segment_chart(),
                    Spacer(1, 2 * mm),
                    Paragraph(
                        "<b>Key insight:</b> Persuadables are the strongest near-term opportunity for targeted rescue work; combine AI prompts with CSM availability.",
                        styles["card_body"],
                    ),
                ],
            ]
        ],
        colWidths=[content_width * 0.58, content_width * 0.42],
    )
    chart_panels.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E1E8EF")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 4 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4 * mm),
            ]
        )
    )
    story.extend([chart_panels, Spacer(1, 6 * mm)])

    next_steps = Table(
        [
            [
                [
                    Paragraph("Recommended next steps", styles["white_title"]),
                    Paragraph(
                        "1. Assign named owners to the highest-value persuadable accounts within one business day.<br/>"
                        "2. Keep Value Vault credits focused on accounts showing a credible recovery signal.<br/>"
                        "3. Review the weekly protected-versus-lost trend in the next operating meeting.",
                        styles["white_body"],
                    ),
                ],
                [
                    Paragraph("Data scope", styles["panel_title"]),
                    Paragraph(
                        "This export reflects the retention data currently shown in the StayLongerAI workspace. Connect production event and billing sources before using it as the basis for an external financial commitment.",
                        styles["card_body"],
                    ),
                ],
            ]
        ],
        colWidths=[content_width * 0.53, content_width * 0.47],
    )
    next_steps.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E1E8EF")),
                ("BACKGROUND", (0, 0), (0, 0), ink),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 4 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4 * mm),
            ]
        )
    )
    story.extend(
        [
            next_steps,
            Spacer(1, 7 * mm),
            Paragraph("Intervention outcomes", styles["section"]),
            Paragraph(
                "Representative actions included in this reporting period, with current outcome status and protected value.",
                styles["section_description"],
            ),
        ]
    )

    header_cells = [
        "CUSTOMER",
        "AI ACTION",
        "SEGMENT",
        "VALUE IMPACT",
        "OUTCOME",
        "RECORDED",
    ]
    intervention_rows = [
        [Paragraph(label, styles["table_header"]) for label in header_cells]
    ]
    outcome_styles = {
        "Recovered": ParagraphStyle(
            "ReportOutcomeRecovered",
            parent=styles["table_cell"],
            textColor=green,
            fontName="Helvetica-Bold",
        ),
        "In progress": ParagraphStyle(
            "ReportOutcomeProgress",
            parent=styles["table_cell"],
            textColor=teal,
            fontName="Helvetica-Bold",
        ),
        "Awaiting reply": ParagraphStyle(
            "ReportOutcomeAwaiting",
            parent=styles["table_cell"],
            textColor=amber,
            fontName="Helvetica-Bold",
        ),
    }
    for intervention in INTERVENTIONS:
        intervention_rows.append(
            [
                Paragraph(escape(intervention["customer"]), styles["table_customer"]),
                Paragraph(escape(intervention["action"]), styles["table_cell"]),
                Paragraph(escape(intervention["segment"]), styles["table_cell"]),
                Paragraph(escape(intervention["value"]), styles["table_value"]),
                Paragraph(
                    escape(intervention["result"]),
                    outcome_styles[intervention["result"]],
                ),
                Paragraph(escape(intervention["time"]), styles["table_cell"]),
            ]
        )
    interventions = Table(
        intervention_rows,
        colWidths=[34 * mm, 29 * mm, 28 * mm, 23 * mm, 31 * mm, 42 * mm],
        repeatRows=1,
    )
    interventions.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#E5EDF2")),
                ("BACKGROUND", (0, 0), (-1, 0), soft_slate),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 2.5 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2.5 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 2.5 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5 * mm),
            ]
        )
    )
    story.append(interventions)

    try:
        document.build(story, onFirstPage=page_footer, onLaterPages=page_footer)
    except (OSError, ValueError) as error:
        raise ReportExportError("The serverless PDF renderer could not build the report.") from error

    pdf = buffer.getvalue()
    if not pdf.startswith(b"%PDF-") or len(pdf) < 1024:
        raise ReportExportError("The serverless PDF renderer did not produce a valid report.")
    return pdf


def render_report_pdf(period: str) -> bytes:
    """Render a report with Chrome locally and ReportLab in serverless runtimes."""
    chrome = _chrome_executable()
    if chrome:
        return _render_report_pdf_with_chrome(period, chrome)
    return _render_report_pdf_with_reportlab(period)
