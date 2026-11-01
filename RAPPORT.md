# Week 2 : Authentification Keycloak (realm bzhcamp)

Projet **DAAM** (fork de [Demo-AppSec-Auth-Moderne](https://github.com/moustaphisene/Demo-AppSec-Auth-Moderne)), stack Keycloak + PostgreSQL + Mailpit + Nginx (Docker Compose), realm `bzhcamp`.

## 1. Connexion admin
Console admin (`localhost:8080/admin`), identifiants **admin / admin** (realm `master`).

![Page de connexion de la console admin Keycloak](report-images/01-admin-login.jpg)

## 2. Création de l'utilisateur `mad`
Via **Realm `bzhcamp` > Users > Add user**, nom d'utilisateur `mad` (les autres champs seront complétés à la première connexion).

![Formulaire de création de l'utilisateur mad](report-images/02-create-user-form.jpg)

Confirmation de création :

![Utilisateur mad créé avec succès](report-images/03-user-created.jpg)

Dans **Credentials**, mot de passe temporaire défini :

![Boite de dialogue de définition du mot de passe](report-images/04-set-password-dialog.jpg)

![Mot de passe défini avec succès](report-images/05-password-set-success.jpg)

## 3. Première connexion avec `mad`
Connexion avec `mad` et le mot de passe temporaire :

![Formulaire de connexion rempli avec mad](report-images/06-mad-login-filled.jpg)

Changement de mot de passe imposé (compte nouvellement créé) :

![Écran de mise à jour du mot de passe](report-images/07-password-update-screen.jpg)

Puis complétion obligatoire du profil, vide à la création :

![Écran de complétion du profil, vide](report-images/08-profile-empty.jpg)

![Écran de complétion du profil, rempli](report-images/09-profile-filled.jpg)

Connexion réussie sur la page de compte.

## 4. Diagnostic : bug sur l'app réelle (port 8081)
L'app de démo (`localhost:8081`) renvoie une erreur au clic sur **Se connecter** :

![Erreur Client inconnu reproduite sur localhost:8081](report-images/10-myapp-error-reproduced.jpg)

L'inspecteur réseau montre une requête `auth?client_id=myapp` renvoyant **400 Bad Request**, sans redirection. Le fichier `demo/myapp/keycloak.json` confirme que l'app attend un client `myapp`, absent du realm `bzhcamp` (seuls `app-springboot` et `keycloak-angular` existaient).

## 5. Correction : création du client `myapp`
Client public créé via **Clients > Create client** (PKCE, sans secret) :

![Étape 1 : saisie du Client ID myapp](report-images/11-client-wizard-general.jpg)

![Étape 2 : configuration des capacités du client](report-images/12-client-wizard-capability.jpg)

![Étape 3 : URIs de redirection et origine web](report-images/13-client-wizard-login-settings.jpg)

![Client myapp créé avec succès](report-images/14-client-created-success.jpg)

Même requête retestée : **200 OK**. Connexion réussie avec `mad`.

## 6. Activation de l'OTP
Dans **Users > mad > Required user actions**, ajout de **Configure OTP** :

![Menu déroulant Required user actions avec Configure OTP](report-images/15-required-action-dropdown.jpg)

![Configure OTP ajouté comme action requise](report-images/16-configure-otp-selected.jpg)

Sauvegarde confirmée :

![The user has been saved](report-images/17-required-action-saved.jpg)

Après reconnexion, Keycloak affiche l'écran de configuration OTP :

![Écran de configuration OTP avec QR code](report-images/18-otp-setup-qrcode.jpg)

Code validé. Vérification dans **Credentials** : identifiant OTP « MAD » confirmé :

![Vérification de l'identifiant OTP MAD dans la console admin](report-images/19-admin-otp-MAD-confirmed.jpg)

## 7. Accès à l'application Angular (port 4200)
App Angular d'exemple du client `keycloak-angular` :

```bash
cd demo/keycloak-angular
npm install
npx ng serve --port 4200
```

![Page d'accueil de l'app Angular](report-images/20-angular-home.jpg)

## 8. Vérification SSO et SLO
**SSO** : session active sur une app, clic sur **Log in** dans l'app Angular, aucune demande d'identifiant (enchaîné directement sur l'action requise) :

![Aucune demande de login](report-images/21-sso-no-login-prompt.jpg)

Connexion établie sans mot de passe :

![Connexion établie dans l'app Angular via SSO](report-images/22-angular-logged-in.jpg)

Même constat sur la console de compte, accessible sans nouvelle authentification :

![Console de compte accessible sans re-authentification](report-images/23-account-sso-no-login.jpg)

**SLO** : déconnexion depuis l'app Angular :

![Déconnexion effectuée depuis l'app Angular](report-images/24-angular-logged-out.jpg)

La console de compte redemande une authentification : la session globale est bien terminée partout.

![SLO confirmé](report-images/25-slo-confirmed.jpg)

**Conclusion** : SSO et SLO fonctionnent, une seule session Keycloak par realm partagée entre toutes les apps.

## 9. Connexion sociale (Google, GitHub, LinkedIn)
Templates natifs dans **Realm > Identity providers** :

![Liste des fournisseurs d'identité disponibles](report-images/26-idp-list.jpg)

![Google, GitHub, LinkedIn dans la liste des providers sociaux](report-images/27-idp-social-list.jpg)

Chaque fournisseur fournit une Redirect URI générée par Keycloak, à déclarer côté plateforme, contre un Client ID et un Client Secret :

| Fournisseur | Redirect URI | Où créer l'app |
|---|---|---|
| Google | `.../broker/google/endpoint` | [Google Cloud Console](https://console.cloud.google.com/apis/credentials) |
| GitHub | `.../broker/github/endpoint` | [GitHub Developer Settings](https://github.com/settings/developers) |
| LinkedIn | `.../broker/linkedin-openid-connect/endpoint` | [LinkedIn Developer Portal](https://www.linkedin.com/developers/apps) |

![Formulaire Google](report-images/28-idp-google-form.jpg)

![Formulaire GitHub](report-images/29-idp-github-form.jpg)

![Formulaire LinkedIn OpenID Connect](report-images/30-idp-linkedin-form.jpg)

**GitHub** : OAuth App créée sur [github.com/settings/developers](https://github.com/settings/developers) avec le redirectUri exact. Client ID affiché :

![OAuth App GitHub créée avec succès](report-images/31-github-provider-created.jpg)

Client Secret généré (confirmation d'identité par email requise), collé avec le Client ID dans Keycloak.

**Google** : projet Google Cloud `bzhcamp-keycloak` créé, écran de consentement OAuth configuré (type Externe), client OAuth Application Web créé avec le redirectUri Keycloak :

![Provider Google créé avec succès dans Keycloak](report-images/32-google-provider-created.jpg)

**Vérification** : les 3 boutons apparaissent sous le formulaire classique :

![Les 3 boutons GitHub, Google et LinkedIn sur l'écran de login](report-images/33-login-3-social-buttons.jpg)

Clic sur **GitHub** : redirection vers le vrai écran d'autorisation GitHub, qui reconnaît l'application :

![GitHub reconnaît l'application bzhcamp Keycloak](report-images/34-github-oauth-confirmed.jpg)

Clic sur **Google** : même constat, écran officiel Google :

![Google reconnaît l'application bzhcamp Keycloak](report-images/35-google-oauth-confirmed.jpg)

**LinkedIn** : page LinkedIn « bzhcamp Keycloak » créée, app OAuth associée (Client ID `77pg6in22j6x2f`), redirectUri Keycloak et produit « Sign In with LinkedIn using OpenID Connect » activé :

![Provider LinkedIn créé avec succès dans Keycloak](report-images/36-linkedin-provider-created.jpg)

Intégration **GitHub, Google et LinkedIn** fonctionnelle de bout en bout : identifiants réels, flux vérifié jusqu'aux écrans d'autorisation officiels.
