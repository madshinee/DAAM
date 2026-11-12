# Import du realm Keycloak (`realm-export.json`)

> **Pourquoi ce fichier contient `myapp` et `mad` :** c'est pour éviter que les configs partent.
> Tout ce qui est créé à la main dans la console Keycloak vit seulement dans la base PostgreSQL.
> Si la base est recréée (volume Docker supprimé, `docker compose down -v`, nouveau poste), le realm
> repart de ce fichier et ce qui n'y figure pas est perdu. Ce fichier est la copie de sauvegarde.

(Le format JSON n'accepte pas de commentaires : l'explication est donc ici, à côté du fichier.)

## Ce que le fichier recrée

| Élément | Détail |
|---|---|
| Client `app-springboot` | confidentiel (secret généré à l'import, à relire dans Credentials) |
| Client `keycloak-angular` | public, PKCE, redirection `http://localhost:4200/*` |
| Client `myapp` | public, redirection `http://localhost:8090/*` |
| Utilisateur `testuser` | mot de passe `password`, rôle `user` |
| Utilisateur `mad` | mot de passe **temporaire** `madmad` (changement imposé), actions requises : changer le mot de passe et configurer l'OTP |

## Ce que le fichier ne recrée pas

- **Le secret TOTP (OTP) de `mad`** : propre à chaque application d'authentification, à refaire au premier login.
- **Les connexions Google, GitHub et LinkedIn** : leurs secrets OAuth ne sont pas stockés ici, à ressaisir dans *Identity providers*.
- **Le secret client de `app-springboot`** : regénéré, à recopier dans les credentials Jenkins (`keycloak-client-secret-uat` et `-preprod`).

## Quand est-il lu ?

- Le `Dockerfile` copie ce fichier dans l'image à la construction, et Keycloak démarre avec `--import-realm`.
- Keycloak **ignore l'import si le realm `bzhcamp` existe déjà** : il ne sert que sur une base vide.
- Après une modification du fichier, il faut reconstruire l'image (`docker compose -f demo/docker-compose.yml build keycloak`) **et** repartir d'une base vide pour que l'import s'applique.
