"""Load the demo's local credentials without printing them."""
import os
from pathlib import Path

def load_config():
    path = Path(__file__).parent / '.env'
    if path.exists():
        from dotenv import load_dotenv
        load_dotenv(path, override=False, interpolate=False, encoding='utf-8-sig')

def database_configured():
    return bool(os.environ.get('DATABASE_URL') or os.environ.get('PGHOST')
                or os.environ.get('TIMESCALE_SERVICE_URL'))

def connection_options():
    if os.environ.get('DATABASE_URL'):
        return {'conninfo': os.environ['DATABASE_URL']}
    # Separate PG variables avoid URL encoding problems in passwords.
    if os.environ.get('PGHOST'):
        return {name: os.environ[key] for name, key in
                [('host', 'PGHOST'), ('port', 'PGPORT'), ('dbname', 'PGDATABASE'),
                 ('user', 'PGUSER'), ('password', 'PGPASSWORD'), ('sslmode', 'PGSSLMODE')]
                if os.environ.get(key)}
    if os.environ.get('TIMESCALE_SERVICE_URL'):
        return {'conninfo': os.environ['TIMESCALE_SERVICE_URL']}
    raise ValueError('Database configuration missing. Save the downloaded configuration as .env beside storage.py.')
