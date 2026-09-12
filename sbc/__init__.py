"""Sarvatobhadra Chakra market prediction engine."""

from .confluence import build_confluence_report
from .trade_setups import TRADE_SETUPS, get_setup, list_setups, setups_for_confluence, format_setup_for_display
from .crash_analyzer import analyze_crash_risk, daily_crash_briefing, backtest_crashes, CrashAnalysis
from .astro_plot import generate_astro_plot, serialize_plot_data, AstroPlotData
from .cgsp_framework import compute_cgsp_score, generate_cgsp_report, get_price_levels, get_sector_bias, check_panchaka, backtest_cgsp
from .fmcg_signals import check_fmcg_syntax, scan_fmcg_signals, get_fmcg_summary, get_fmcg_price_levels
from .tourism_signals import check_tourism_syntax, scan_tourism_signals, get_tourism_summary, get_tourism_price_levels
from .chemical_signals import check_chemical_syntax, scan_chemical_signals, get_chemical_summary, get_chemical_price_levels
from .alcohol_signals import check_alcohol_syntax, scan_alcohol_signals, get_alcohol_summary, get_alcohol_price_levels
from .lunar_forecast import generate_lunar_sector_forecast, generate_infographic_card, format_card_for_clipboard, format_card_for_social_media
from .market_data import get_nifty_ohlc, moon_rashi, RASHI_TREND
from .metrics import _bias_scale, _western_bias, _WESTERN_EXALT, _WESTERN_DEBIL
from .db import get_db, _bootstrap, PROFILES_DB_PATH

__version__ = "1.0.0"
__all__ = [
    "build_confluence_report",
    "TRADE_SETUPS",
    "get_setup",
    "list_setups",
    "setups_for_confluence",
    "format_setup_for_display",
    "analyze_crash_risk",
    "daily_crash_briefing",
    "backtest_crashes",
    "CrashAnalysis",
    "generate_astro_plot",
    "serialize_plot_data",
    "AstroPlotData",
    "compute_cgsp_score",
    "generate_cgsp_report",
    "get_price_levels",
    "get_sector_bias",
    "check_panchaka",
    "backtest_cgsp",
    "check_fmcg_syntax",
    "scan_fmcg_signals",
    "get_fmcg_summary",
    "get_fmcg_price_levels",
    "check_tourism_syntax",
    "scan_tourism_signals",
    "get_tourism_summary",
    "get_tourism_price_levels",
    "check_chemical_syntax",
    "scan_chemical_signals",
    "get_chemical_summary",
    "get_chemical_price_levels",
    "check_alcohol_syntax",
    "scan_alcohol_signals",
    "get_alcohol_summary",
    "get_alcohol_price_levels",
    "generate_lunar_sector_forecast",
    "generate_infographic_card",
    "format_card_for_clipboard",
    "format_card_for_social_media",
    "get_nifty_ohlc",
    "moon_rashi",
    "RASHI_TREND",
    "_bias_scale",
    "_western_bias",
    "_WESTERN_EXALT",
    "_WESTERN_DEBIL",
    "get_db",
    "_bootstrap",
    "PROFILES_DB_PATH",
]
