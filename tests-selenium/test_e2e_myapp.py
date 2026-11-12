"""Tests E2E : application myapp + Keycloak (realm bzhcamp, Authorization Code + PKCE S256).

Prérequis : Keycloak sur :8080, myapp servie sur http://localhost:8090,
service REST sur :8093, Chrome.

Lancement :
    python test_e2e_myapp.py                 # tous les scénarios (A, C, D)
    python test_e2e_myapp.py --only A         # parcours fonctionnel (navigateur)
    python test_e2e_myapp.py --only C         # sécurité côté application (navigateur + API)
    python test_e2e_myapp.py --only D         # protocole OAuth2/OIDC (requests, sans navigateur)
    python test_e2e_myapp.py --headless       # scénarios A/C sans fenêtre Chrome

Captures dans ./captures (scénarios A et C uniquement ; D n'ouvre pas de navigateur).
Chaque étape d'un scénario est indépendante : un échec au milieu n'empêche pas les suivantes.
"""
import base64
import hashlib
import html
import pathlib
import re
import secrets
import sys
import time
import urllib.parse as urlparse

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

KEYCLOAK = "http://localhost:8080"
REALM = "bzhcamp"
CLIENT_ID = "myapp"
APP = "http://localhost:8090/"
SERVICE = "http://localhost:8093"
USER, PWD = "testuser", "password"
TOKEN_URL = f"{KEYCLOAK}/realms/{REALM}/protocol/openid-connect/token"

OUT = pathlib.Path(__file__).parent / "captures"
OUT.mkdir(exist_ok=True)
results = []


def new_driver():
    o = webdriver.ChromeOptions()
    o.add_argument("--window-size=1400,900")
    if "--headless" in sys.argv:
        o.add_argument("--headless=new")
    return webdriver.Chrome(options=o)


def wait(d, cond, t=30):
    return WebDriverWait(d, t).until(cond)


def shot(d, name):
    time.sleep(0.6)
    try:
        d.save_screenshot(str(OUT / f"{name}.png"))
    except Exception as exc:
        print(f"(capture ratée pour {name} : {exc})")


def check(label, is_ok):
    results.append((label, bool(is_ok)))
    print(("PASS" if is_ok else "FAIL"), "-", label, flush=True)


def run(name, func, *args):
    """Exécute une étape : une exception est enregistrée comme échec, sans arrêter les suivantes."""
    try:
        func(*args)
    except Exception as exc:
        short = str(exc).strip().splitlines()[0] if str(exc).strip() else ""
        check(f"{name} : exception inattendue ({exc.__class__.__name__} {short})", False)


def kc_login(d, user, pwd):
    wait(d, EC.presence_of_element_located((By.ID, "username")))
    d.find_element(By.ID, "username").clear()
    d.find_element(By.ID, "username").send_keys(user)
    d.find_element(By.ID, "password").send_keys(pwd)
    d.find_element(By.ID, "kc-login").click()


def logged_in(d):
    return d.find_element(By.ID, "btnLogout").is_displayed()


def wait_logged_in(d):
    wait(d, lambda x: x.current_url.startswith(APP) and x.find_element(By.ID, "btnLogout").is_displayed())


def wait_logged_out(d):
    wait(d, lambda x: x.current_url.startswith(APP) and x.find_element(By.ID, "btnLogin").is_displayed())


# ===================== A : parcours fonctionnel (navigateur) =====================
def _a1_ouverture(d):
    d.get(APP)
    wait(d, EC.element_to_be_clickable((By.ID, "btnLogin")))
    shot(d, "A1-01-app-non-connectee")
    check("A1 App ouverte : bouton « Se connecter » visible, pas de déconnexion", not logged_in(d))


def _a1_redirection(d):
    d.find_element(By.ID, "btnLogin").click()
    wait(d, EC.presence_of_element_located((By.ID, "kc-login")))
    shot(d, "A1-02-redirection-keycloak")
    url = d.current_url
    check("A1 Redirection vers Keycloak (realm bzhcamp)", f"localhost:8080/realms/{REALM}" in url)
    check("A1 PKCE : code_challenge_method=S256 dans l'URL", "code_challenge_method=S256" in url and "code_challenge=" in url)
    check("A1 state et nonce présents dans l'URL d'autorisation", "state=" in url and "nonce=" in url)


def _a1_connexion(d):
    kc_login(d, USER, PWD)
    wait_logged_in(d)
    shot(d, "A1-03-connecte")
    check("A1 Retour sur l'app, connecté (bouton Déconnexion visible)", logged_in(d))
    check("A1 URL propre après connexion (pas de code ni de token dans la barre d'adresse)",
          "code=" not in d.current_url and "access_token" not in d.current_url)
    body = d.find_element(By.TAG_NAME, "body").text
    check("A1 Les infos de l'utilisateur testuser sont affichées", USER in body or "Test User" in body)


def _a1_stockage(d):
    local_keys = d.execute_script("return Object.keys(window.localStorage || {});")
    session_keys = d.execute_script("return Object.keys(window.sessionStorage || {});")
    check("A1 Aucun token dans localStorage (gardés en mémoire JS)",
          not any("token" in k.lower() for k in local_keys))
    check("A1 Aucun token dans sessionStorage",
          not any("token" in k.lower() for k in session_keys))


def _a1_onglet(d, tab_id, shot_name, label):
    d.find_element(By.ID, tab_id).click()
    wait(d, lambda x: x.find_element(By.ID, tab_id).get_attribute("aria-selected") == "true")
    shot(d, shot_name)
    check(f"A1 Onglet {label} sélectionné", d.find_element(By.ID, tab_id).get_attribute("aria-selected") == "true")


def _a1_userinfo(d):
    d.find_element(By.XPATH, "//button[contains(.,'User Info')]").click()
    wait(d, EC.text_to_be_present_in_element((By.ID, "output"), USER))
    shot(d, "A1-07-user-info")
    check("A1 Bouton « User Info » : réponse affichée", USER in d.find_element(By.ID, "output").text)


def _a1_deconnexion(d):
    d.find_element(By.ID, "btnLogout").click()
    wait_logged_out(d)
    shot(d, "A1-08-deconnecte")
    check("A1 Après déconnexion : retour à l'état non connecté", not logged_in(d))


def a1_parcours_complet():
    d = new_driver()
    try:
        run("A1 ouverture", _a1_ouverture, d)
        run("A1 redirection", _a1_redirection, d)
        run("A1 connexion", _a1_connexion, d)
        run("A1 stockage", _a1_stockage, d)
        run("A1 onglet ID Token", _a1_onglet, d, "tab-id", "A1-04-id-token", "ID Token")
        run("A1 onglet Refresh Token", _a1_onglet, d, "tab-refresh", "A1-05-refresh-token", "Refresh Token")
        run("A1 onglet Access Token", _a1_onglet, d, "tab-access", "A1-06-access-token", "Access Token")
        run("A1 user info", _a1_userinfo, d)
        run("A1 déconnexion", _a1_deconnexion, d)
    finally:
        d.quit()


# ===================== C : sécurité côté application =====================
def c1_mauvais_mot_de_passe():
    d = new_driver()
    try:
        d.get(APP)
        wait(d, EC.element_to_be_clickable((By.ID, "btnLogin"))).click()
        kc_login(d, USER, "mauvais-mot-de-passe")
        wait(d, EC.presence_of_element_located((By.ID, "kc-login")))
        shot(d, "C1-mauvais-mot-de-passe")
        still_on_keycloak = "localhost:8080" in d.current_url
        error_shown = "invalide" in d.page_source.lower() or "invalid" in d.page_source.lower()
        check("C1 Mauvais mot de passe : on reste sur Keycloak et une erreur s'affiche",
              still_on_keycloak and error_shown)
    finally:
        d.quit()


def _c2_rechargement(d):
    d.get(APP)
    wait(d, EC.element_to_be_clickable((By.ID, "btnLogin"))).click()
    kc_login(d, USER, PWD)
    wait_logged_in(d)
    d.find_element(By.ID, "btnLogout").click()
    wait_logged_out(d)
    d.get(APP)
    wait(d, EC.element_to_be_clickable((By.ID, "btnLogin")))
    shot(d, "C2-rechargement-apres-logout")
    check("C2 Après déconnexion puis rechargement : toujours non connecté", not logged_in(d))


def _c2_session_keycloak(d):
    d.get(f"{KEYCLOAK}/realms/{REALM}/account")
    wait(d, EC.presence_of_element_located((By.ID, "kc-login")))
    shot(d, "C2-session-keycloak-fermee")
    check("C2 La session Keycloak est fermée (login redemandé)", "openid-connect/auth" in d.current_url)


def c2_session_apres_deconnexion():
    d = new_driver()
    try:
        run("C2 rechargement", _c2_rechargement, d)
        run("C2 session Keycloak", _c2_session_keycloak, d)
    finally:
        d.quit()


def c3_acces_api_sans_login():
    # Vérification fiable (pas de parsing fragile de page) : on interroge l'API directement.
    r = requests.get(f"{SERVICE}/planets", timeout=5)
    check("C3 API /planets sans token : HTTP 401", r.status_code == 401)

    r2 = requests.get(f"{SERVICE}/planets", headers={"Authorization": "Bearer token-invalide"}, timeout=5)
    check("C3 bis API /planets avec un token invalide : HTTP 401", r2.status_code == 401)

    # Capture visuelle pour la documentation uniquement (n'influence pas le résultat des tests)
    d = new_driver()
    try:
        d.get(f"{SERVICE}/planets")
        shot(d, "C3-api-sans-token")
    finally:
        d.quit()


# ===================== D : protocole OAuth2/OIDC (requests, sans navigateur) =====================
def _pkce_pair():
    verifier = secrets.token_urlsafe(64)[:64]
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


def _login_via_requests(session, redirect_uri):
    """Rejoue le flux Authorization Code + PKCE avec `requests`, sans navigateur.
    Retourne (code, info) ; code est None si Keycloak refuse avant d'afficher le formulaire
    (ex: redirect_uri non enregistrée), et info contient alors le statut HTTP."""
    verifier, challenge = _pkce_pair()
    state = secrets.token_urlsafe(16)
    nonce = secrets.token_urlsafe(16)
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "response_mode": "query",
        "scope": "openid",
        "state": state,
        "nonce": nonce,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    auth_url = f"{KEYCLOAK}/realms/{REALM}/protocol/openid-connect/auth"
    r = session.get(auth_url, params=params, timeout=5)
    if r.status_code != 200 or 'id="kc-form-login"' not in r.text:
        return None, {"status": r.status_code, "body": r.text[:500]}

    m = re.search(r'id="kc-form-login"[^>]*action="([^"]+)"', r.text) or \
        re.search(r'action="([^"]+)"[^>]*id="kc-form-login"', r.text)
    if not m:
        return None, {"status": r.status_code, "body": "formulaire de login introuvable"}
    action_url = html.unescape(m.group(1))

    r2 = session.post(action_url, data={"username": USER, "password": PWD}, allow_redirects=False, timeout=5)
    location = r2.headers.get("Location", "")
    query = location.split("?", 1)[1] if "?" in location else location.split("#", 1)[-1]
    qs = urlparse.parse_qs(query)
    code = qs.get("code", [None])[0]
    returned_state = qs.get("state", [None])[0]
    return code, {"verifier": verifier, "state": state, "returned_state": returned_state, "location": location}


def _echange(code, verifier=None):
    data = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "redirect_uri": APP,
        "code": code,
    }
    if verifier is not None:
        data["code_verifier"] = verifier
    return requests.post(TOKEN_URL, data=data, timeout=5)


def d1_redirect_uri_non_autorisee():
    code, info = _login_via_requests(requests.Session(), "http://evil.example.com/callback")
    check("D1 redirect_uri non enregistrée : aucun code émis", code is None)
    check("D1 redirect_uri non enregistrée : Keycloak répond HTTP 400", info.get("status") == 400)


def d2_code_rejoue():
    code, info = _login_via_requests(requests.Session(), APP)
    check("D2 Obtention d'un code d'autorisation valide", bool(code))
    if not code:
        return
    check("D2 Le state retourné correspond à celui envoyé", info["returned_state"] == info["state"])

    r1 = _echange(code, info["verifier"])
    check("D2 Premier échange du code : HTTP 200 (token obtenu)", r1.status_code == 200)

    r2 = _echange(code, info["verifier"])
    check("D2 Réutilisation du même code : refusée (HTTP 400, invalid_grant)",
          r2.status_code == 400 and "invalid_grant" in r2.text)


def d3_revocation_apres_logout():
    code, info = _login_via_requests(requests.Session(), APP)
    if not code:
        check("D3 Obtention d'un token pour le test de révocation", False)
        return

    r1 = _echange(code, info["verifier"])
    check("D3 Obtention d'un token pour le test de révocation", r1.status_code == 200)
    if r1.status_code != 200:
        return
    refresh_token = r1.json().get("refresh_token")

    logout_url = f"{KEYCLOAK}/realms/{REALM}/protocol/openid-connect/logout"
    r2 = requests.post(logout_url, data={"client_id": CLIENT_ID, "refresh_token": refresh_token}, timeout=5)
    check("D3 Déconnexion (logout) acceptée par Keycloak", r2.status_code in (200, 204))

    r3 = requests.post(TOKEN_URL, data={
        "grant_type": "refresh_token",
        "client_id": CLIENT_ID,
        "refresh_token": refresh_token,
    }, timeout=5)
    check("D3 Refresh token refusé après logout (révoqué)", r3.status_code == 400)


def d4_pkce_verifier_incorrect():
    # PKCE doit être appliqué côté serveur : un mauvais ou un absent code_verifier est refusé.
    code, info = _login_via_requests(requests.Session(), APP)
    check("D4 Obtention d'un code (test du mauvais code_verifier)", bool(code))
    if code:
        r = _echange(code, secrets.token_urlsafe(64)[:64])
        check("D4 Échange avec un mauvais code_verifier : refusé (HTTP 400)", r.status_code == 400)

    code2, _ = _login_via_requests(requests.Session(), APP)
    check("D4 Obtention d'un code (test sans code_verifier)", bool(code2))
    if code2:
        r = _echange(code2, None)
        check("D4 Échange sans code_verifier : refusé (HTTP 400)", r.status_code == 400)


if __name__ == "__main__":
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    if only in (None, "A"):
        run("A1", a1_parcours_complet)
    if only in (None, "C"):
        run("C1", c1_mauvais_mot_de_passe)
        run("C2", c2_session_apres_deconnexion)
        run("C3", c3_acces_api_sans_login)
    if only in (None, "D"):
        run("D1", d1_redirect_uri_non_autorisee)
        run("D2", d2_code_rejoue)
        run("D3", d3_revocation_apres_logout)
        run("D4", d4_pkce_verifier_incorrect)
    ok = sum(r for _, r in results)
    print(f"\n{ok}/{len(results)} tests réussis")
    sys.exit(0 if ok == len(results) else 1)
