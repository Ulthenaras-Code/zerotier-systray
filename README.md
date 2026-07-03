# Procédure — ZeroTier Tray (systray GNOME/Ubuntu)

## Contexte

Icône systray (logo ZeroTier fourni) avec les réseaux ZeroTier directement
dans le menu déroulant : case à cocher pour connecter/déconnecter en un
clic, gestion (renommer/détails/oublier) et ajout de nouveaux réseaux
depuis le même menu. Basé sur le script `zerotier-cli-full.sh` d'origine.

Aucun réseau n'est préenregistré : la liste démarre vide, tout se configure
depuis l'application via **Ajouter un réseau...**.

## Fonctionnement du menu

Les réseaux apparaissent directement dans le menu déroulant du tray, sous
forme de cases à cocher natives (rendues par GNOME Shell) : coché = connecté,
décoché = déconnecté. Un simple clic sur une case bascule la connexion.

Les actions secondaires (détails, renommer, oublier) sont dans le sous-menu
**"Gérer les réseaux"**, avec un sous-sous-menu par réseau.

Note : le rendu de la case à cocher (couleur, forme) suit le thème GNOME
du système — ce n'est pas un widget personnalisé coloré, car un menu
d'AppIndicator est reconstruit par GNOME Shell à partir d'une description
texte (protocole `dbusmenu`) qui ne supporte pas de widgets stylés
manuellement. C'est le compromis le plus fiable : pas de fenêtre flottante
à positionner, tout reste dans le menu système standard.

## Prérequis

- Ubuntu 24.04, GNOME/Wayland
- ZeroTier déjà installé (`zerotier-cli` dans `/usr/sbin/`)
- Extension GNOME **AppIndicator and KStatusNotifierItem Support**
  (obligatoire sous GNOME/Wayland, sinon aucune icône de tray tierce ne
  s'affiche) : https://extensions.gnome.org/extension/615/appindicator-support/

## Fichiers fournis

| Fichier | Rôle |
|---|---|
| `zerotier_tray.py` | Application (PyGObject/Gtk3 + AppIndicator3, sans dépendance zenity) |
| `install.sh` | Installe les dépendances, la règle sudoers, l'autostart, copie le logo |
| `assets/zerotier-icon.png` | Logo utilisé pour l'icône de tray |
| `~/.config/zerotier-tray/config.json` | Mapping `network_id -> nom convivial` (vide au premier lancement) |

## Installation

```bash
chmod +x install.sh
./install.sh
```

Le script :
1. installe `python3-gi`, `gir1.2-gtk-3.0`, `gir1.2-ayatanaappindicator3-0.1`, `pillow` ;
2. copie `zerotier_tray.py` dans `~/.local/bin/` et le logo dans `~/.local/share/zerotier-tray/` ;
3. ajoute une règle **sudoers NOPASSWD** limitée à `/usr/sbin/zerotier-cli`
   dans `/etc/sudoers.d/zerotier-tray` (indispensable : un clic dans
   l'interface ne peut pas répondre à un prompt `sudo` interactif) ;
4. ajoute une entrée autostart GNOME.

⚠️ Après l'installation, installe et **active manuellement** l'extension
AppIndicator (lien ci-dessus), puis déconnecte-toi/reconnecte-toi, ou lance
directement :

```bash
python3 ~/.local/bin/zerotier_tray.py
```

## Utilisation

- **Icône du tray** : logo ZeroTier + petit badge rond (vert = tout
  connecté, orange = partiel, rouge = rien de connecté ou aucun réseau).
- **Menu déroulant** (clic sur l'icône) :
  - Au premier lancement : "Aucun réseau configuré"
  - Un réseau par ligne une fois ajouté, case à cocher = connecté/déconnecté
    (clic direct)
  - **Gérer les réseaux** → sous-menu par réseau : Détails / Renommer / Oublier
  - **Ajouter un réseau...** → saisie du Network ID (16 caractères) puis nom
    (obligatoire)
  - **Rafraîchir** : aussi automatique toutes les 15 secondes

## Réinitialiser la liste des réseaux

```bash
rm ~/.config/zerotier-tray/config.json
```

Le fichier est recréé vide au prochain lancement.

## Sécurité

La règle sudoers est restreinte au binaire exact `/usr/sbin/zerotier-cli`
(pas de wildcard sur les sous-commandes) — seules les opérations via cet
exécutable sont concernées, pas d'élévation de privilèges généralisée.

Pour la retirer :

```bash
sudo rm /etc/sudoers.d/zerotier-tray
```

## Limitations connues

- Le renommage est purement local (`config.json`), ne modifie pas le nom
  du réseau côté contrôleur ZeroTier.
- Les appels `zerotier-cli` sont synchrones (timeout 5s) : une commande
  lente bloquerait brièvement l'interface. Non gênant en usage local normal.
