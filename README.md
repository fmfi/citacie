### Spustenie

1. Inštalácia prostredia

   ```bash
   virtualenv venv
   source venv/bin/activate
   pip install suds Flask defusedxml xmlbuilder
   ```

   Pre testovacie účely sa dá použiť aj fake zdroj dát, ten potrebuje ďaľšie závislosti:

   ```bash
   pip install names
   ```

2. Command-line príklady
    
   ```bash
   python wok.py search 'AU=Masarik J*'
   python wok.py retrieve 'WOS:000308512600015'
   ```

3. Spustenie web aplikácie (pre testovacie účely) na localhost:5000

   ```bash
   CITACIE_DEBUG=1 python citacie.py
   ```
    
