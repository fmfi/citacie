### Spustenie

1. Inštalácia prostredia

    virtualenv venv
    source venv/bin/activate
    pip install suds Flask

2. Command-line príklady
    
    python wok.py search 'AU=Masarik J*'
    python wok.py retrieve 'WOS:000308512600015'

3. Spustenie web aplikácie (pre testovacie účely) na localhost:5000

    CITACIE_DEBUG=1 python citacie.py
    