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
   sudoedit local_settings.py
   ```

Nastaviť sa dajú nasledovné veci:

### Tajný kľúč

`self.secret` musí byť náhodný tajný reťazec, najlepšie je vygenerovať ho automaticky:

```bash
python -c 'import os; print repr(os.urandom(32))'
```

toto vypíše pythonový string literál, ktorý sa dá použiť ako tajný kľúč.

### Kam posielať e-maily s výnimkami

Chceme zmeniť nastavenie `ADMINS`, čo je pythonovské pole so zoznamom e-mailových adries kam posielať hlásenia:

```python
ADMINS = ['email@example.com']
```

Tiež môžme zmeniť nastavenie SMTP servera v časti, kde sa vyrába SMTP handler:

```python
mail_handler = SMTPHandler('smtp.example.com',
    'citacie@example.com',
    ADMINS, 'Citacie - error')
```

Argumenty SMTPHandler-a sú hostname SMTP servera, adresa odosielateľa, adresy prijímateľa,
predmet správy, prípadne nastavenia zabezpečenia komunikácie, viď [Python dokumentáciu SMTP handlera](https://docs.python.org/2/library/logging.handlers.html#smtphandler).

### HTTP proxy

Pre ScopusWeb sa dá nastaviť aká HTTP proxy sa má používať ([viď nastavenie proxies v requests](http://docs.python-requests.org/en/latest/api/#requests.Session.proxies)) a to v konštruktore, napr.:

```python
ScopusWeb(proxies={'http': 'http://localhost:8001'})
```

prípadne ako premenná prostredia `HTTP_PROXY="http://localhost:8001"`.

> Poznámka: Requests nepodporuje SOCKS proxy, ale dá sa to obísť použitím samostatnej
> HTTP proxy, ktorá vie používať SOCKS, ako napríklad
> [Polipo](http://www.pps.univ-paris-diderot.fr/~jch/software/polipo/).
> `polipo disableLocalInterface=true disableVia=true socksParentProxy=localhost:8000 proxyPort=8001 diskCacheRoot=''`

### Redis cache

Aplikácia má v sebe experimentálnu podporu cachovania dát v redise, aj keď sa dlhšiu
dobu v produkcii nepoužíva (vypli sme redis, lebo boli zapnuté aj logy doň a žralo to priveľa pamäte). Defaultne je redis podpora vypnutá, ak ju chceme zapnúť, treba naimportovať v konfigu na začiatku redis modul:

```python
from redis_integration import RedisCachedDataSource
import redis
```

vyrobiť v `__init__` pripojenie na redis:

```python
self.redis = redis.StrictRedis(host='localhost', port=6379, db=0)
```

a vyrobiť cachovanú inštanciu DataSource obalením skutočného DS, napríklad namiesto

```python
ScopusWeb()
```

písať v konfigu

```python
RedisCachedDataSource(self.redis, 'SCOPUS', ScopusWeb())
```

kde `'SCOPUS'` je namespace kľúčov, ktorý sa v redise používa, pre každý DS by mal byť iný.

## Konfigurácia Apache2

Vzorový konfig pre Apache2.2

```ApacheConf
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
