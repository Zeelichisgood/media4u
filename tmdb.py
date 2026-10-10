"""Petit client TMDB (bibliothèque standard uniquement)."""
import json
import os
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

from config import LANGUAGE, ROOT

BASE_URL = "https://api.themoviedb.org/3"
SYSTEM_CA_BUNDLE = "/etc/ssl/cert.pem"


def ssl_context() -> ssl.SSLContext:
    """Le Python de python.org sur macOS n'embarque pas de certificats racine :
    on retombe sur ceux du système, sans jamais désactiver la vérification."""
    paths = ssl.get_default_verify_paths()
    if (paths.cafile and os.path.exists(paths.cafile)) or not os.path.exists(SYSTEM_CA_BUNDLE):
        return ssl.create_default_context()
    return ssl.create_default_context(cafile=SYSTEM_CA_BUNDLE)


def load_env(path=ROOT / ".env") -> None:
    """Charge KEY=VALUE depuis .env sans écraser l'environnement existant."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


class TMDBError(RuntimeError):
    pass


class TMDB:
    def __init__(self, pause: float = 0.1, retries: int = 3):
        load_env()
        self.api_key = os.environ.get("TMDB_API_KEY")
        if not self.api_key:
            raise TMDBError("TMDB_API_KEY introuvable : renseigne-la dans .env")
        self.pause = pause
        self.retries = retries
        self.calls = 0
        self.context = ssl_context()

    def get(self, path: str, **params) -> dict:
        params = {"api_key": self.api_key, "language": LANGUAGE, **params}
        url = f"{BASE_URL}{path}?{urllib.parse.urlencode(params)}"
        # On ne met jamais l'URL (donc la clé) dans les messages d'erreur.
        for attempt in range(1, self.retries + 1):
            time.sleep(self.pause)
            self.calls += 1
            try:
                with urllib.request.urlopen(url, timeout=20, context=self.context) as response:
                    return json.load(response)
            except urllib.error.HTTPError as error:
                if error.code == 429 and attempt < self.retries:
                    time.sleep(float(error.headers.get("Retry-After", 2)))
                    continue
                if error.code >= 500 and attempt < self.retries:
                    time.sleep(2 * attempt)
                    continue
                raise TMDBError(f"TMDB {path} -> HTTP {error.code}") from None
            except (urllib.error.URLError, TimeoutError) as error:
                if attempt < self.retries:
                    time.sleep(2 * attempt)
                    continue
                reason = getattr(error, "reason", error)
                raise TMDBError(f"TMDB {path} -> réseau indisponible ({reason})") from None
        raise TMDBError(f"TMDB {path} -> échec")
