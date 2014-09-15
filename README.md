# Quick start

## Inštalácia

   ```bash
   # Ak neexistuje používateľ ka, vytvorme ho
   sudo adduser --system --group ka

   # Vytvorme adresár pre aplikáciu
   sudo mkdir -p /var/www-apps/citacie
   sudo chown ka:ka /var/www-apps/citacie

   # Ak nemáme nainštalovaný git, doinštalujme ho
   sudo apt-get install git

   # Stiahnime zdrojové kódy (všimnime si bodku na konci v druhom príkaze)
   cd /var/www-apps/citacie
   sudo -u ka -H git clone https://github.com/fmfi/citacie.git .

   # Nainštalujme systémové závislosti
   sudo apt-get install python-dev python-virtualenv libxml2-dev libxslt-dev zlib1g-dev

   # Vytvorme virtual environment pre python (pod používateľom ka, t.j. sudo -u ka -H -s)
   cd /var/www-apps/citacie
   virtualenv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

## Konfigurácia aplikácie

Najprv skopírujme príklad konfiguračného súboru na správne miesto:

   ```bash
   cd /var/www-apps/citacie
   sudo -u ka -H cp local_settings.py.example local_settings.py
   sudo -u ka -H chmod go= local_settings.py
   ```

Teraz ho môžeme upraviť

   ```bash
   sudoedit /local_settings.py
   ```

Nastaviť sa dajú nasledovné veci:

### TODO zoznam veci co sa daju nastavit

## Konfigurácia Apache2

Vzorový konfig pre Apache2.2

```apache2
WSGIScriptAlias /ka/citacie /var/www-apps/citacie/wsgi.py
Alias /ka/citacie/static /var/www-apps/citacie/static
WSGIDaemonProcess kacitacie user=ka group=ka processes=2 threads=15 display-name={%GROUP} python-path=/var/www-apps/citacie:/var/www-apps/citacie/venv/lib/python2.7/site-packages home=/var/www-apps/citacie
<Directory /var/www-apps/citacie/>
	WSGIProcessGroup kacitacie
	# Kvoli chunked response vypnime gzip (inak mod_deflate zrusi chunky)
	SetEnv no-gzip
	Order deny,allow
	Deny from all
	Allow from 158.195
</Directory>
<Location /ka/citacie/admin>
	CosignAllowPublicAccess Off
	AuthType Cosign
	Require user vinar1
</Location>
```

# Vývoj aplikácie

## Spustenie aplikácie pre vývojára

   ```bash
   CITACIE_DEBUG=1 python citacie.py
   ```

   Alebo ak chceme testovať streaming response (zas nereloaduje automaticky):

   ```bash
   CITACIE_DEBUG=1 python citacie.py cherry
   ```

## CLI príkazy na testovanie:

   ```bash
   python wok.py search 'AU=Masarik J*'
   python wok.py retrieve 'WOS:000308512600015'
   ```
