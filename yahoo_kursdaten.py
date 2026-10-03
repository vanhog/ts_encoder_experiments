"""Tageskurse abrufen. Installation: pip install pandas yfinance"""

import re
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf
from curl_cffi import requests
from yfinance.exceptions import YFPricesMissingError


def yahoo_kursdaten(isin: str, zeitraum: str) -> pd.DataFrame:
    """Liefert Yahoo-Tageskurse für einen einschließlich begrenzten Zeitraum.

    Beispiel: yahoo_kursdaten("US0378331005", "01/09/2025-30/09/2025")
    Für einen einzelnen Tag beide Daten gleich angeben.

    Spalten: Open, High, Low, Close, Adj Close, Volume. Der DatetimeIndex
    verwendet die Zeitzone des von Yahoo gewählten Handelsplatzes. Preise
    bleiben in dessen Handelswährung; es erfolgt keine Währungsumrechnung.
    auto_adjust=False erhält die von Yahoo gelieferten OHLC-Kurse und
    zusätzlich den bereinigten Schlusskurs (Adj Close).

    Ohne verfügbare Kurse wird ein leerer DataFrame zurückgegeben, z. B.
    am Wochenende. Das kann auch fehlende Yahoo-Abdeckung bedeuten.
    Ungültige Eingaben lösen ValueError aus; Abruffehler werden weitergegeben.
    Die ISIN bestimmt keinen eindeutigen Handelsplatz: Yahoo wählt das Symbol.
    """
    if not isinstance(isin, str):
        raise ValueError("Die ISIN muss eine Zeichenkette sein.")
    isin = isin.strip().upper()
    if not re.fullmatch(r"[A-Z]{2}[A-Z0-9]{9}[0-9]", isin):
        raise ValueError("Die ISIN muss aus 12 Zeichen bestehen, z. B. US0378331005.")

    if not isinstance(zeitraum, str) or not re.fullmatch(
        r"[0-9]{2}/[0-9]{2}/[0-9]{4}-[0-9]{2}/[0-9]{2}/[0-9]{4}", zeitraum
    ):
        raise ValueError("Zeitraum im Format dd/mm/yyyy-dd/mm/yyyy angeben.")
    try:
        start, ende = (
            datetime.strptime(datum, "%d/%m/%Y").date()
            for datum in zeitraum.split("-")
        )
    except ValueError as exc:
        raise ValueError("Der Zeitraum enthält ein ungültiges Kalenderdatum.") from exc
    if start > ende:
        raise ValueError("Das Startdatum darf nicht nach dem Enddatum liegen.")
    try:
        ende_exklusiv = ende + timedelta(days=1)
    except OverflowError as exc:
        raise ValueError("Das Enddatum muss vor dem 31/12/9999 liegen.") from exc

    # Ein festes Profil vermeidet inkompatible neue "chrome"-Standardprofile.
    # Die Session bleibt offen, da yfinance sie intern auch gemeinsam nutzt.
    session = requests.Session(impersonate="chrome124")
    ticker = yf.Ticker(isin, session=session)
    spalten = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]
    try:
        daten = ticker.history(
            start=start.isoformat(),
            end=ende_exklusiv.isoformat(),
            interval="1d",
            auto_adjust=False,
            actions=False,
            raise_errors=True,
        )
    except YFPricesMissingError:
        daten = pd.DataFrame(
            columns=spalten, index=pd.DatetimeIndex([], name="Date"), dtype=float
        )

    daten = daten.reindex(columns=spalten).sort_index()
    daten.attrs.update(isin=isin, yahoo_symbol=ticker.ticker)
    return daten
