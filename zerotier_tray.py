#!/usr/bin/env python3
"""
ZeroTier Tray v4 - Icone systray (logo perso) avec les reseaux directement
dans le menu deroulant : case a cocher native pour connecter/deconnecter
en un clic, plus un sous-menu "Gerer les reseaux" pour renommer/details/
oublier.

Dependances systeme (Ubuntu/GNOME) :
    sudo apt install python3-gi gir1.2-gtk-3.0 gir1.2-ayatanaappindicator3-0.1
    (voir install.sh pour le detail complet + regle sudoers + autostart)
"""

import json
import subprocess
import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
try:
    gi.require_version("AyatanaAppIndicator3", "0.1")
    from gi.repository import AyatanaAppIndicator3 as AppIndicator3
except (ValueError, ImportError):
    gi.require_version("AppIndicator3", "0.1")
    from gi.repository import AppIndicator3

from gi.repository import Gtk, GLib

ZTCLI = "/usr/sbin/zerotier-cli"
CONFIG_DIR = Path.home() / ".config" / "zerotier-tray"
CONFIG_FILE = CONFIG_DIR / "config.json"
REFRESH_SECONDS = 15

ICON_DIR_INSTALLED = Path.home() / ".local" / "share" / "zerotier-tray" / "icons"
ASSET_LOGO_LOCAL = Path(__file__).resolve().parent / "assets" / "zerotier-icon.png"

DEFAULT_NETWORKS = {}


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

def load_config() -> dict:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.exists():
        save_config(DEFAULT_NETWORKS)
        return dict(DEFAULT_NETWORKS)
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULT_NETWORKS)


def save_config(networks: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(networks, f, indent=2, ensure_ascii=False)


# --------------------------------------------------------------------------- #
# zerotier-cli
# --------------------------------------------------------------------------- #

def zt_list_status() -> dict:
    try:
        out = subprocess.run(
            ["sudo", "-n", ZTCLI, "-j", "listnetworks"],
            capture_output=True, text=True, timeout=5, check=True,
        )
        data = json.loads(out.stdout)
        return {
            entry["nwid"]: {
                "status": entry.get("status", "UNKNOWN"),
                "ips": entry.get("assignedAddresses", []),
                "iface": entry.get("portDeviceName", "?"),
            }
            for entry in data
        }
    except Exception:
        return {}


def zt_join(network_id: str) -> bool:
    return subprocess.run(
        ["sudo", "-n", ZTCLI, "join", network_id],
        capture_output=True, text=True, timeout=5,
    ).returncode == 0


def zt_leave(network_id: str) -> bool:
    return subprocess.run(
        ["sudo", "-n", ZTCLI, "leave", network_id],
        capture_output=True, text=True, timeout=5,
    ).returncode == 0


# --------------------------------------------------------------------------- #
# Petites boites de dialogue GTK natives
# --------------------------------------------------------------------------- #

def text_entry_dialog(title: str, message: str, initial: str = "") -> str | None:
    dialog = Gtk.Dialog(title=title, modal=True)
    dialog.set_position(Gtk.WindowPosition.MOUSE)
    dialog.add_buttons(
        Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
        Gtk.STOCK_OK, Gtk.ResponseType.OK,
    )
    box = dialog.get_content_area()
    box.set_spacing(8)
    box.set_border_width(10)
    box.add(Gtk.Label(label=message, xalign=0))
    entry = Gtk.Entry()
    entry.set_text(initial)
    entry.set_activates_default(True)
    box.add(entry)
    dialog.set_default_response(Gtk.ResponseType.OK)
    dialog.show_all()
    response = dialog.run()
    value = entry.get_text().strip() if response == Gtk.ResponseType.OK else None
    dialog.destroy()
    return value


def info_dialog(title: str, message: str) -> None:
    dialog = Gtk.MessageDialog(
        modal=True, message_type=Gtk.MessageType.INFO,
        buttons=Gtk.ButtonsType.OK, text=title,
    )
    dialog.set_position(Gtk.WindowPosition.MOUSE)
    dialog.format_secondary_text(message)
    dialog.run()
    dialog.destroy()


def error_dialog(message: str) -> None:
    dialog = Gtk.MessageDialog(
        modal=True, message_type=Gtk.MessageType.ERROR,
        buttons=Gtk.ButtonsType.OK, text="Erreur",
    )
    dialog.set_position(Gtk.WindowPosition.MOUSE)
    dialog.format_secondary_text(message)
    dialog.run()
    dialog.destroy()


def confirm_dialog(message: str) -> bool:
    dialog = Gtk.MessageDialog(
        modal=True, message_type=Gtk.MessageType.QUESTION,
        buttons=Gtk.ButtonsType.YES_NO, text=message,
    )
    dialog.set_position(Gtk.WindowPosition.MOUSE)
    response = dialog.run()
    dialog.destroy()
    return response == Gtk.ResponseType.YES


# --------------------------------------------------------------------------- #
# Icones (3 variantes precalculees : vert / orange / rouge)
# --------------------------------------------------------------------------- #

def prepare_icon_files() -> Path:
    """Genere logo+badge (vert/orange/rouge) dans le dossier d'icones et
    retourne ce dossier. Utilise Pillow si dispo, sinon copie le logo brut.
    Ne leve jamais d'exception : retombe sur une icone generee si le
    logo fourni est introuvable."""
    icon_dir = ICON_DIR_INSTALLED
    icon_dir.mkdir(parents=True, exist_ok=True)

    candidates = [
        ICON_DIR_INSTALLED.parent / "icon.png",
        ASSET_LOGO_LOCAL,
        Path(__file__).resolve().parent / "zerotier-icon.png",
    ]
    logo_path = next((p for p in candidates if p.exists()), None)

    try:
        from PIL import Image, ImageDraw

        if logo_path is not None:
            base = Image.open(logo_path).convert("RGBA").resize((64, 64), Image.LANCZOS)
        else:
            base = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
            d = ImageDraw.Draw(base)
            d.ellipse((4, 4, 60, 60), fill=(243, 156, 18, 255))
            d.ellipse((16, 16, 48, 48), outline="white", width=4)

        colors = {
            "green": (46, 204, 113, 255),
            "orange": (243, 156, 18, 255),
            "red": (231, 76, 60, 255),
        }
        for key, color in colors.items():
            img = base.copy()
            draw = ImageDraw.Draw(img)
            bx, by, r = 50, 50, 12
            draw.ellipse((bx - r, by - r, bx + r, by + r), fill=(255, 255, 255, 255))
            draw.ellipse((bx - r + 2, by - r + 2, bx + r - 2, by + r - 2), fill=color)
            img.save(icon_dir / f"zerotier-tray-{key}.png")
    except ImportError:
        for key in ("green", "orange", "red"):
            dest = icon_dir / f"zerotier-tray-{key}.png"
            if not dest.exists() and logo_path is not None:
                dest.write_bytes(logo_path.read_bytes())
    except Exception as exc:
        print(f"[zerotier-tray] Avertissement : generation d'icone echouee ({exc})", file=sys.stderr)

    return icon_dir


# --------------------------------------------------------------------------- #
# Application
# --------------------------------------------------------------------------- #

class ZeroTierTrayApp:
    def __init__(self):
        self.networks = load_config()   # {id: nom}
        self.status = {}                # {id: {status, ips, iface}}
        self._refreshing = False        # evite les allers-retours toggled<->refresh

        icon_dir = prepare_icon_files()
        self.indicator = AppIndicator3.Indicator.new(
            "zerotier-tray", "zerotier-tray-red",
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS,
        )
        self.indicator.set_icon_theme_path(str(icon_dir))
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        self.indicator.set_title("ZeroTier Tray")

        self.refresh()
        GLib.timeout_add_seconds(REFRESH_SECONDS, self._on_timer)

    # --- construction du menu ------------------------------------------- #

    def _build_menu(self) -> Gtk.Menu:
        menu = Gtk.Menu()

        if not self.networks:
            item = Gtk.MenuItem(label="Aucun reseau configure")
            item.set_sensitive(False)
            menu.append(item)
        else:
            for nwid, name in self.networks.items():
                info = self.status.get(nwid, {})
                connected = info.get("status") == "OK"

                check = Gtk.CheckMenuItem(label=name)
                check.set_active(connected)
                check.connect("toggled", self._on_toggle, nwid)
                menu.append(check)

        menu.append(Gtk.SeparatorMenuItem())

        manage_item = Gtk.MenuItem(label="Gerer les reseaux")
        manage_item.set_submenu(self._build_manage_submenu())
        manage_item.set_sensitive(bool(self.networks))
        menu.append(manage_item)

        add_item = Gtk.MenuItem(label="Ajouter un reseau...")
        add_item.connect("activate", lambda i: self.add_network())
        menu.append(add_item)

        refresh_item = Gtk.MenuItem(label="Rafraichir")
        refresh_item.connect("activate", lambda i: self.refresh())
        menu.append(refresh_item)

        menu.append(Gtk.SeparatorMenuItem())

        quit_item = Gtk.MenuItem(label="Quitter")
        quit_item.connect("activate", lambda i: Gtk.main_quit())
        menu.append(quit_item)

        menu.show_all()
        return menu

    def _build_manage_submenu(self) -> Gtk.Menu:
        submenu = Gtk.Menu()
        for nwid, name in self.networks.items():
            entry = Gtk.MenuItem(label=name)
            entry_sub = Gtk.Menu()

            details_item = Gtk.MenuItem(label="Details...")
            details_item.connect("activate", lambda i, n=nwid, nm=name: self.show_details(n, nm))
            entry_sub.append(details_item)

            rename_item = Gtk.MenuItem(label="Renommer...")
            rename_item.connect("activate", lambda i, n=nwid: self.rename_network(n))
            entry_sub.append(rename_item)

            forget_item = Gtk.MenuItem(label="Oublier ce reseau")
            forget_item.connect("activate", lambda i, n=nwid: self.forget_network(n))
            entry_sub.append(forget_item)

            entry.set_submenu(entry_sub)
            submenu.append(entry)

        submenu.show_all()
        return submenu

    # --- toggle direct depuis le menu principal -----------------------------

    def _on_toggle(self, check_item: Gtk.CheckMenuItem, nwid: str):
        if self._refreshing:
            # Changement programmatique (rebuild du menu) : ne rien faire.
            return
        desired_state = check_item.get_active()
        ok = zt_join(nwid) if desired_state else zt_leave(nwid)
        if not ok:
            error_dialog(
                f"Echec de l'operation sur {nwid}.\n"
                "Verifie la regle sudoers NOPASSWD pour zerotier-cli."
            )
        self.refresh()

    # --- cycle de rafraichissement ------------------------------------------

    def _on_timer(self):
        self.refresh()
        return True

    def refresh(self):
        self._refreshing = True
        try:
            self.status = zt_list_status()
            connected_states = [self.status.get(n, {}).get("status") == "OK" for n in self.networks]
            all_connected = bool(connected_states) and all(connected_states)
            any_connected = any(connected_states)

            if all_connected and any_connected:
                self.indicator.set_icon_full("zerotier-tray-green", "Tous connectes")
            elif any_connected:
                self.indicator.set_icon_full("zerotier-tray-orange", "Partiellement connecte")
            else:
                self.indicator.set_icon_full("zerotier-tray-red", "Deconnecte")

            self.indicator.set_menu(self._build_menu())
        finally:
            self._refreshing = False

    # --- actions de gestion --------------------------------------------------

    def show_details(self, nwid, name):
        info = self.status.get(nwid, {})
        status = info.get("status", "INCONNU")
        ips = ", ".join(info.get("ips", [])) or "aucune"
        iface = info.get("iface", "?")
        info_dialog(
            name,
            f"Network ID : {nwid}\nStatut : {status}\nAdresses IP : {ips}\nInterface : {iface}",
        )

    def rename_network(self, nwid):
        new_name = text_entry_dialog(
            "Renommer le reseau", "Nouveau nom :",
            initial=self.networks.get(nwid, ""),
        )
        if new_name:
            self.networks[nwid] = new_name
            save_config(self.networks)
            self.refresh()

    def forget_network(self, nwid):
        if confirm_dialog(f"Oublier le reseau '{self.networks.get(nwid, nwid)}' ?"):
            self.networks.pop(nwid, None)
            save_config(self.networks)
            self.refresh()

    def add_network(self):
        nwid = text_entry_dialog("Ajouter un reseau", "Network ID ZeroTier (16 caracteres) :")
        if not nwid:
            return
        nwid = nwid.strip()
        if len(nwid) != 16:
            error_dialog("Un Network ID ZeroTier fait 16 caracteres hexadecimaux.")
            return

        name = None
        while not name:
            name = text_entry_dialog("Nom du reseau", "Nom convivial (obligatoire) :", initial=nwid)
            if name is None:
                return
            name = name.strip()

        self.networks[nwid] = name
        save_config(self.networks)
        self.refresh()


def main():
    ZeroTierTrayApp()
    Gtk.main()


if __name__ == "__main__":
    main()
