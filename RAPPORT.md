# Week 2 : Authentification Keycloak (realm bzhcamp)

Projet **DAAM** (fork de [Demo-AppSec-Auth-Moderne](https://github.com/moustaphisene/Demo-AppSec-Auth-Moderne)), stack Keycloak + PostgreSQL + Mailpit + Nginx (Docker Compose), realm `bzhcamp`.

## 1. Connexion admin
Console admin (`localhost:8080/admin`), identifiants **admin / admin** (realm `master`).

## 2. Création de l'utilisateur `mad`
Via **Realm `bzhcamp` > Users > Add user**, nom d'utilisateur `mad` (les autres champs seront complétés à la première connexion).

Confirmation de création :

Dans **Credentials**, mot de passe temporaire défini :

## 3. Première connexion avec `mad`
Connexion avec `mad` et le mot de passe temporaire :

Changement de mot de passe imposé (compte nouvellement créé) :

Puis complétion obligatoire du profil, vide à la création :

Connexion réussie sur la page de compte.

## 4. Diagnostic : bug sur l'app réelle (port 8081)
L'app de démo (`localhost:8081`) renvoie une erreur au clic sur **Se connecter** :

L'inspecteur réseau montre une requête `auth?client_id=myapp` renvoyant **400 Bad Request**, sans redirection. Le fichier `demo/myapp/keycloak.json` confirme que l'app attend un client `myapp`, absent du realm `bzhcamp` (seuls `app-springboot` et `keycloak-angular` existaient).

## 5. Correction : création du client `myapp`
Client public créé via **Clients > Create client** (PKCE, sans secret) :

Même requête retestée : **200 OK**. Connexion réussie avec `mad`.

## 6. Activation de l'OTP
Dans **Users > mad > Required user actions**, ajout de **Configure OTP** :

Sauvegarde confirmée :

Après reconnexion, Keycloak affiche l'écran de configuration OTP :

Code validé. Vérification dans **Credentials** : identifiant OTP « MAD » confirmé :

## 7. Accès à l'application Angular (port 4200)
App Angular d'exemple du client `keycloak-angular` :

```bash
cd demo/keycloak-angular
npm install
npx ng serve --port 4200
```

## 8. Vérification SSO et SLO
**SSO** : session active sur une app, clic sur **Log in** dans l'app Angular, aucune demande d'identifiant (enchaîné directement sur l'action requise) :

Connexion établie sans mot de passe :

Même constat sur la console de compte, accessible sans nouvelle authentification :

**SLO** : déconnexion depuis l'app Angular :

La console de compte redemande une authentification : la session globale est bien terminée partout.

**Conclusion** : SSO et SLO fonctionnent, une seule session Keycloak par realm partagée entre toutes les apps.

## 9. Connexion sociale (Google, GitHub, LinkedIn)
Templates natifs dans **Realm > Identity providers** :

Chaque fournisseur fournit une Redirect URI générée par Keycloak, à déclarer côté plateforme, contre un Client ID et un Client Secret :

| Fournisseur | Redirect URI | Où créer l'app |
|---|---|---|
| Google | `.../broker/google/endpoint` | [Google Cloud Console](https://console.cloud.google.com/apis/credentials) |
| GitHub | `.../broker/github/endpoint` | [GitHub Developer Settings](https://github.com/settings/developers) |
| LinkedIn | `.../broker/linkedin-openid-connect/endpoint` | [LinkedIn Developer Portal](https://www.linkedin.com/developers/apps) |

**GitHub** : OAuth App créée sur [github.com/settings/developers](https://github.com/settings/developers) avec le redirectUri exact. Client ID affiché :

Client Secret généré (confirmation d'identité par email requise), collé avec le Client ID dans Keycloak.

**Google** : projet Google Cloud `bzhcamp-keycloak` créé, écran de consentement OAuth configuré (type Externe), client OAuth Application Web créé avec le redirectUri Keycloak :

**Vérification** : les 3 boutons apparaissent sous le formulaire classique :

Clic sur **GitHub** : redirection vers le vrai écran d'autorisation GitHub, qui reconnaît l'application :

Clic sur **Google** : même constat, écran officiel Google :

**LinkedIn** : page LinkedIn « bzhcamp Keycloak » créée, app OAuth associée (Client ID `77pg6in22j6x2f`), redirectUri Keycloak et produit « Sign In with LinkedIn using OpenID Connect » activé :

Intégration **GitHub, Google et LinkedIn** fonctionnelle de bout en bout : identifiants réels, flux vérifié jusqu'aux écrans d'autorisation officiels.
