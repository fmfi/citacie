# Quick start

## Inštalácia

   ```bash
   sudo apt-get install python-dev libxml2-dev libxslt-dev zlib1g-dev
   virtualenv venv
   source venv/bin/activate
   pip install suds Flask defusedxml xmlbuilder mechanize html5lib lxml
   ```

   Pre testovacie účely sa dá použiť aj fake zdroj dát, ten potrebuje ďaľšie závislosti:

   ```bash
   pip install names
   ```

## Konfigurácia

   1. Skopírujte `local_settings.py.example` do `local_settings.py`
   2. Upravte nastavenia

## Spustenie

   Aplikácia sa dá spustiť pomocou WSGI, alebo testovací server z príkazového riadku:

   ```bash
   CITACIE_DEBUG=1 python citacie.py
   ```

## CLI príkazy na testovanie:

   ```bash
   python wok.py search 'AU=Masarik J*'
   python wok.py retrieve 'WOS:000308512600015'
   ```
