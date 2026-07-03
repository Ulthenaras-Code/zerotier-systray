#!/bin/bash
# Installation de ZeroTier Tray (GNOME/Ubuntu 24.04)
set -e

echo "==== Installation des dependances systeme ===="
sudo apt update
sudo apt install -y python3-gi gir1.2-gtk-3.0 gir1.2-ayatanaappindicator3-0.1 python3-pip

echo "==== Installation des dependances Python ===="
pip3 install --break-system-packages --user pillow

echo "==== Copie du script et du logo ===="
mkdir -p "$HOME/.local/bin"
mkdir -p "$HOME/.local/share/zerotier-tray"
cp "$(dirname "$0")/zerotier_tray.py" "$HOME/.local/bin/zerotier_tray.py"
chmod +x "$HOME/.local/bin/zerotier_tray.py"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOGO_CANDIDATES=(
    "$SCRIPT_DIR/assets/zerotier-icon.png"
    "$SCRIPT_DIR/zerotier-icon.png"
    "$SCRIPT_DIR/zerotier.png"
)
LOGO_FOUND=""
for candidate in "${LOGO_CANDIDATES[@]}"; do
    if [ -f "$candidate" ]; then
        LOGO_FOUND="$candidate"
        break
    fi
done

if [ -n "$LOGO_FOUND" ]; then
    cp "$LOGO_FOUND" "$HOME/.local/share/zerotier-tray/icon.png"
    echo "Logo copie depuis : $LOGO_FOUND"
else
    echo "ATTENTION : logo introuvable (cherche dans assets/zerotier-icon.png,"
    echo "zerotier-icon.png, zerotier.png a cote de install.sh)."
    echo "L'application utilisera une icone de secours generee automatiquement."
    echo "Tu peux le copier manuellement plus tard avec :"
    echo "  cp /chemin/vers/ton-logo.png $HOME/.local/share/zerotier-tray/icon.png"
fi

echo "==== Regle sudoers NOPASSWD pour zerotier-cli ===="
USERNAME="$(whoami)"
SUDOERS_FILE="/etc/sudoers.d/zerotier-tray"
LINE="$USERNAME ALL=(ALL) NOPASSWD: /usr/sbin/zerotier-cli"

if [ ! -f "$SUDOERS_FILE" ] || ! sudo grep -qF "$LINE" "$SUDOERS_FILE" 2>/dev/null; then
    echo "$LINE" | sudo tee "$SUDOERS_FILE" > /dev/null
    sudo chmod 440 "$SUDOERS_FILE"
    sudo visudo -c -f "$SUDOERS_FILE" > /dev/null && echo "Regle sudoers ajoutee et validee."
else
    echo "Regle sudoers deja presente."
fi

echo "==== Entree autostart ===="
mkdir -p "$HOME/.config/autostart"
cat > "$HOME/.config/autostart/zerotier-tray.desktop" << EOF
[Desktop Entry]
Type=Application
Name=ZeroTier Tray
Comment=Icone systray pour gerer les reseaux ZeroTier
Exec=python3 $HOME/.local/bin/zerotier_tray.py
Icon=network-wired
Terminal=false
X-GNOME-Autostart-enabled=true
EOF

echo ""
echo "==== IMPORTANT ===="
echo "Sur GNOME/Wayland, le tray n'existe pas nativement."
echo "Installe et ACTIVE l'extension GNOME Shell 'AppIndicator and KStatusNotifierItem Support' :"
echo "  https://extensions.gnome.org/extension/615/appindicator-support/"
echo ""
echo "Installation terminee. Lance-le maintenant avec :"
echo "  python3 $HOME/.local/bin/zerotier_tray.py"
echo "Ou deconnecte-toi/reconnecte-toi pour qu'il demarre automatiquement."
