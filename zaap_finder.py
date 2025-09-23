# -*- coding: utf-8 -*-
"""
Zaap Finder GUI v2.5.8 - Version EXE Stable

Utilitaire pour les joueurs qui surveille le presse-papiers. Dès qu'une
coordonnée est copiée, il la remplace automatiquement par la commande de voyage
`/travel` correspondante. L'interface graphique affiche les détails du Zaap
trouvé et permet de récupérer cette commande manuellement à tout moment.
"""
import re
import threading
import sys
import os
import json
from math import cos, sin, radians

# --- Bibliothèques ---
import pystray
from PIL import Image, ImageDraw, ImageTk
try:
    from matplotlib.path import Path
except ImportError: Path = None
import pyperclip
from win10toast_click import ToastNotifier
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import font

# --- Définition de la version ---
APP_VERSION = "v2.5.8"

# ==============================================================================
# FONCTION ESSENTIELLE POUR PYINSTALLER
# ==============================================================================
def resource_path(relative_path):
    """ Obtenir le chemin absolu vers une ressource, fonctionne pour le dev et pour PyInstaller """
    try:
        # PyInstaller crée un dossier temporaire et y stocke le chemin dans _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# ==============================================================================
# CLASSE TOOLTIP
# ==============================================================================
class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget; self.text = text; self.tooltip_window = None; self.id = None
        self.widget.bind("<Enter>", self.schedule); self.widget.bind("<Leave>", self.unschedule)
    def schedule(self, event=None):
        self.unschedule(); self.id = self.widget.after(500, self.show_tooltip)
    def unschedule(self, event=None):
        if self.id: self.widget.after_cancel(self.id); self.id = None
        if self.tooltip_window: self.tooltip_window.destroy(); self.tooltip_window = None
    def show_tooltip(self, event=None):
        x, y, _, _ = self.widget.bbox("insert"); x += self.widget.winfo_rootx() + 25; y += self.widget.winfo_rooty() + 25
        self.tooltip_window = tk.Toplevel(self.widget); self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
        label = tk.Label(self.tooltip_window, text=self.text, justify='left', background="#2d2d2d", relief='solid',
                         borderwidth=1, foreground="#d4d4d4", font=("Segoe UI", 10, "normal"), padx=5, pady=3)
        label.pack(ipadx=1)

# ==============================================================================
# FENÊTRE DES PARAMÈTRES
# ==============================================================================
class SettingsWindow(tk.Toplevel):
    def __init__(self, parent_app):
        super().__init__(parent_app.root)
        self.parent = parent_app
        self.title("Paramètres")
        self.transient(parent_app.root); self.grab_set()
        
        self.configure(bg=self.parent.colors["background"])
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('Settings.TFrame', background=self.parent.colors["background"])
        style.configure('Settings.TLabel', background=self.parent.colors["background"], foreground=self.parent.colors["text"], font=self.parent.fonts["value"])
        style.configure('Settings.TRadiobutton', background=self.parent.colors["background"], foreground=self.parent.colors["text"], font=self.parent.fonts["value"])
        style.map('Settings.TRadiobutton', background=[('active', self.parent.colors["background"])])
        style.configure('Settings.TCheckbutton', background=self.parent.colors["background"], foreground=self.parent.colors["text"], font=self.parent.fonts["value"])
        style.map('Settings.TCheckbutton', background=[('active', self.parent.colors["background"])])

        main_frame = ttk.Frame(self, padding=(20, 15), style='Settings.TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True)

        theme_frame = ttk.Frame(main_frame, style='Settings.TFrame')
        theme_frame.pack(fill=tk.X, pady=(0, 15))
        ttk.Label(theme_frame, text="Thème visuel :", font=self.parent.fonts["key"], style='Settings.TLabel').pack(side=tk.LEFT)
        self.theme_var = tk.StringVar(value=self.parent.settings["theme"])
        ttk.Radiobutton(theme_frame, text="Sombre", variable=self.theme_var, value="dark", style='Settings.TRadiobutton').pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(theme_frame, text="Clair", variable=self.theme_var, value="light", style='Settings.TRadiobutton').pack(side=tk.LEFT)

        penalty_frame = ttk.Frame(main_frame, style='Settings.TFrame')
        penalty_frame.pack(fill=tk.X, pady=(0, 15))
        ttk.Label(penalty_frame, text="Malus de distance :", font=self.parent.fonts["key"], style='Settings.TLabel').pack(anchor='w')
        self.penalty_vars = {}
        for key, setting in self.parent.settings.items():
            if "penalty" in setting:
                frame = ttk.Frame(penalty_frame, style='Settings.TFrame')
                frame.pack(fill=tk.X, padx=10, pady=2)
                ttk.Label(frame, text=setting["display_name"] + " :", style='Settings.TLabel').pack(side=tk.LEFT)
                var = tk.StringVar(value=str(setting["penalty"]))
                self.penalty_vars[key] = var
                entry = ttk.Entry(frame, textvariable=var, width=5, justify='center')
                entry.pack(side=tk.LEFT, padx=5)

        toggle_frame = ttk.Frame(main_frame, style='Settings.TFrame')
        toggle_frame.pack(fill=tk.X, pady=(0, 15))
        ttk.Label(toggle_frame, text="Activer/Désactiver des options :", font=self.parent.fonts["key"], style='Settings.TLabel').pack(anchor='w')
        self.check_vars = {}
        for key, setting in self.parent.settings.items():
            if "enabled" in setting:
                self.check_vars[key] = tk.BooleanVar(value=setting["enabled"])
                chk = ttk.Checkbutton(toggle_frame, text=setting["display_name"], variable=self.check_vars[key], style='Settings.TCheckbutton')
                chk.pack(anchor='w', padx=10, pady=2)

        button_frame = ttk.Frame(main_frame, style='Settings.TFrame')
        button_frame.pack(pady=(10, 0), fill=tk.X)
        ok_button = ttk.Button(button_frame, text="Appliquer", style="Primary.TButton", command=self.apply_and_close)
        ok_button.pack(side=tk.RIGHT)
        cancel_button = ttk.Button(button_frame, text="Annuler", style="Secondary.TButton", command=self.destroy)
        cancel_button.pack(side=tk.RIGHT, padx=(0, 10))

    def apply_and_close(self):
        try:
            for key, var in self.penalty_vars.items():
                self.parent.settings[key]["penalty"] = int(var.get())
        except ValueError:
            messagebox.showerror("Erreur de Saisie", "Le malus doit être un nombre entier.", parent=self)
            return
        
        for key, var in self.check_vars.items():
            self.parent.settings[key]["enabled"] = var.get()
        self.parent.settings["theme"] = self.theme_var.get()
        
        self.parent.save_settings()
        self.parent.apply_theme()
        self.parent.refresh_ui_after_theme_change()
        print("Paramètres sauvegardés et appliqués.")
        self.destroy()

# ==============================================================================
# DATA ET FONCTIONS UTILITAIRES
# ==============================================================================
ZAAPS_DATA = [
    ("Village d'Amakna","Amakna",-2,0), ("Bord de la forêt maléfique","Amakna",-1,13),
    ("Coin des Bouftous","Amakna",5,7), ("Montagne des Craqueleurs","Amakna",-5,-8), ("Plaine des Scarafeuilles","Amakna",-1,24),
    ("Port de Madrestam","Amakna",7,-4), ("Cité d'Astrub","Astrub",5,-18), ("Diligence d'Astrub", "Astrub", 0, -18),
    ("Taïnela","Astrub",1,-32), ("Cœur immaculé","Bonta",-31,-56), ("Diligence Cimetière de Bonta", "Bonta", -21, -58),
    ("La Cuirasse","Brâkmar",-26,37), ("La Bourgade","Île de Frigost",-78,-41), ("Entrée du château de Harebourg","Île de Frigost",-67,-75),
    ("Village enseveli","Île de Frigost",-77,-73), ("Route des Roulottes","Landes de Sidimote",-25,12),
    ("Diligence des Fungus", "Landes de Sidimote", -12, 29), ("Diligence Baie de Cania", "Plaines de Cania", -29, -12),
    ("Champs de Cania","Plaines de Cania",-27,-36), ("Lac de Cania","Plaines de Cania",-3,-42), ("Massif de Cania","Plaines de Cania",-13,-28),
    ("Plaine des Porkass","Plaines de Cania",-5,-23), ("Plaines Rocheuses","Plaines de Cania",-17,-47),
    ("Routes Rocailleuses","Plaines de Cania",-20,-20), ("Village des Dopeuls","Plaines de Cania",-34,-8),
    ("Village des Kanigs","Plaines de Cania",0,-56), ("Futaie enneigée","Archipel de Valonia",39,-82),
    ("Rivage sufokien","Baie de Sufokia",10,22), ("Sufokia","Baie de Sufokia",13,26),
    ("Foire du Trool","Foire du Trool",-11,-36), ("Village côtier","Île d'Otomaï",-46,18),
    ("Mont des Tombeaux","Île de Grobe",40,44), ("Plage de la Tortue","Île de Moon",35,12),
    ("Village de Pandala","Île de Pandala",20,-29), ("Village des Eleveurs","Montagne des Koalaks",-16,1),
    ("Dunes des ossements","Saharach",15,-58), ("Vulkania (Madrestam)", "Vulkania", -48, 44)
]
SCAEROPLANES_DATA = [
    ("Scaéroplane Côtier", "Île d'Otomaï", -49, 14), ("Scaéroplane Plaine", "Île d'Otomaï", -56, 22),
    ("Scaéroplane éleveur", "Île d'Otomaï", -57, 4)
]
ZAAPIS_SUFOKIA_DATA = [
    ("Quai des Gelées", "Baie de Sufokia", 12, 29), ("Quai du Port", "Baie de Sufokia", 16, 28),
    ("Quai des Marchands", "Baie de Sufokia", 18, 24), ("Quai du Temple", "Baie de Sufokia", 22, 23),
    ("Quai des Bandits", "Baie de Sufokia", 15, 22),
]
COORD_REGEX = re.compile(r"^\[?\s*(-?\d+)\s*,\s*(-?\d+)\s*\]?$")
REFRESH_INTERVAL_MS = 300
def manhattan(a, b): return abs(a[0] - b[0]) + abs(a[1] - b[1])
def find_nearest_zaap(x, y, settings, data):
    target_pos = (x, y); best_option = None; min_dist = float('inf')
    
    for zone in data["rectangle_zones"]:
        if (zone["min_x"] <= x <= zone["max_x"]) and (zone["min_y"] <= y <= zone["max_y"]) and (target_pos not in zone["exclusions"]):
            forced_zaap_name = zone["zaap"]
            for zaap_details in data["zaaps"]:
                if zaap_details[0] == forced_zaap_name: return (*zaap_details, manhattan(target_pos, (zaap_details[2], zaap_details[3])))
    if Path and "complex_zones" in data:
        for zone in data["complex_zones"]:
            if Path(zone["path_coords"]).contains_point(target_pos):
                forced_zaap_name = zone["zaap"]
                for zaap_details in data["zaaps"]:
                    if zaap_details[0] == forced_zaap_name: return (*zaap_details, manhattan(target_pos, (zaap_details[2], zaap_details[3])))

    if settings["zaaps"]["enabled"]:
        for name, region, zx, zy in data["zaaps"]:
            dist = manhattan(target_pos, (zx, zy))
            if dist < min_dist: min_dist = dist; best_option = (name, region, zx, zy, dist)
    if settings["scaeros"]["enabled"]:
        for name, region, sx, sy in data["scaeros"]:
            dist = manhattan(target_pos, (sx, sy)) + settings["scaeros"]["penalty"]
            if dist < min_dist: min_dist = dist; best_option = (f"Canopée -> {name}", region, sx, sy, dist)
    if settings["zaapis"]["enabled"]:
        for name, region, zx, zy in data["zaapis"]:
            dist = manhattan(target_pos, (zx, zy)) + settings["zaapis"]["penalty"]
            if dist < min_dist: min_dist = dist; best_option = (f"Sufokia -> {name}", region, zx, zy, dist)
        zaapi_r = data["zaapi_restricted"]
        if target_pos in {tuple(c) for c in zaapi_r["allowed_coords"]}:
            dist = manhattan(target_pos, (zaapi_r["x"], zaapi_r["y"])) + settings["zaapis"]["penalty"]
            if dist < min_dist: min_dist = dist; best_option = (f"Sufokia -> {zaapi_r['name']}", zaapi_r["region"], zaapi_r["x"], zaapi_r["y"], dist)

    if settings["zaap_cemetery"]["enabled"]:
        cemetery_rect = (-13 <= x <= -10) and (13 <= y <= 21); cemetery_line = (x == -9) and (18 <= y <= 21)
        if cemetery_rect or cemetery_line:
            c_zaap = data["zaap_cemetery"]["data"]; c_dist = manhattan(target_pos, (c_zaap[2], c_zaap[3]))
            if c_dist < min_dist: min_dist = c_dist; best_option = (*c_zaap, c_dist)
    if settings["zaaps_wabbit"]["enabled"]:
        wabbit_zone = (20 <= x <= 31) and (-17 <= y <= -2)
        if wabbit_zone:
            for name, region, zx, zy in data["zaaps_wabbit"]["data"]:
                dist = manhattan(target_pos, (zx, zy))
                if dist < min_dist: min_dist = dist; best_option = (name, region, zx, zy, dist)
    return best_option
def create_portal_icon():
    W, H = 64, 64; CENTER = (W / 2, H / 2); BG_COLOR, STONE_COLOR, PORTAL_COLOR = "#1e1e1e", "#4a4a4a", "#00c0ff"
    image = Image.new('RGB', (W, H), BG_COLOR); draw = ImageDraw.Draw(image)
    draw.ellipse((CENTER[0] - 18, CENTER[1] - 18, CENTER[0] + 18, CENTER[1] + 18), fill=PORTAL_COLOR)
    for i in range(8):
        draw.arc((CENTER[0] - 26, CENTER[1] - 26, CENTER[0] + 26, CENTER[1] + 26), start=i*45, end=i*45+40, fill=STONE_COLOR, width=12)
    return image

# ==============================================================================
# CLASSE PRINCIPALE DE L'APPLICATION
# ==============================================================================
class ZaapFinderApp:
    def __init__(self, root):
        self.root = root; self.root.title("Zaap Finder")
        self.is_running = False; self.last_clip = ""; self.tray_icon = None; self.tray_thread = None
        
        self.portal_icon_pil = create_portal_icon()
        self.portal_icon_tk = ImageTk.PhotoImage(self.portal_icon_pil)
        self.root.iconphoto(True, self.portal_icon_tk)
        
        self.toaster = ToastNotifier()
        self.settings_file = "zaap_finder_settings.json"
        self.load_settings()
        self.apply_theme()
        
        self.create_copy_icon_images()
        
        self.create_widgets()
        self.root.update_idletasks(); base_width = self.root.winfo_reqwidth(); height = self.root.winfo_reqheight()
        self.root.geometry(f"{base_width + 20}x{height}"); self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.quit_app)

    def get_default_settings(self):
        return {
            "theme": "dark",
            "notifications": {"enabled": True, "display_name": "Afficher les notifications"},
            "zaaps": {"enabled": True, "display_name": "Zaaps"},
            "scaeros": {"enabled": True, "display_name": "Scaéroplanes", "penalty": 3},
            "zaapis": {"enabled": True, "display_name": "Zaapis de Sufokia", "penalty": 2},
            "zaap_cemetery": {"enabled": True, "display_name": "Règle Cimetière Koalak"},
            "zaaps_wabbit": {"enabled": True, "display_name": "Règle Île des Wabbits"},
        }
    def get_game_data(self):
        return {
            "zaaps": ZAAPS_DATA, "scaeros": SCAEROPLANES_DATA, "zaapis": ZAAPIS_SUFOKIA_DATA,
            "zaap_cemetery": {"data": ("Cimetière primitif", "Montagne des Koalaks", -12, 19)},
            "zaaps_wabbit": {"data": [("Laboratoires abandonnés", "Île des Wabbits", 27, -14), ("Île de la Cawotte", "Île des Wabbits", 25, -4)]},
            "zaapi_restricted": {"name": "Quai de la Bricole", "region": "Baie de Sufokia", "x": 8, "y": 25, "allowed_coords": [[9,24], [9,25], [8,25], [7,25], [7,26], [6,26], [8,26], [9,26], [9,27], [10,27], [11,27], [10,24], [11,25], [11,26], [10,26]]},
            "rectangle_zones": [{"name": "Zone du Labyrinthe Forêt Maléfique", "min_x": -7, "max_x": -2, "min_y": 2,  "max_y": 12, "exclusions": {(-2,9), (-3,9), (-3,10), (-2,7), (-3,7), (-3,6), (-2,6), (-2,12), (-2,5), (-2,4), (-2,3), (-2,2), (-3,2), (-5,2), (-6,2), (-6,3), (-7,2), (-7,3), (-7,4)}, "zaap": "Bord de la forêt maléfique"}],
            "complex_zones": [{"name": "Canyon Sauvage / Vallée Morh'Kitu", "path_coords": [(-21, 10), (-19, 10), (-19, 9), (-17, 9), (-17, 8), (-12, 8), (-12, 12), (-14, 12), (-14, 15), (-19, 15), (-19, 14), (-20, 14), (-20, 11), (-21, 11), (-21, 10)], "zaap": "Village des Eleveurs"}] if Path else []
        }
    def load_settings(self):
        self.settings = self.get_default_settings()
        try:
            with open(self.settings_file, 'r') as f:
                saved_settings = json.load(f)
                for key, value in saved_settings.items():
                    if key in self.settings:
                        if isinstance(self.settings[key], dict) and isinstance(value, dict): self.settings[key].update(value)
                        else: self.settings[key] = value
        except (FileNotFoundError, json.JSONDecodeError): print("Aucun fichier de paramètres trouvé ou fichier corrompu.")
    def save_settings(self):
        try:
            with open(self.settings_file, 'w') as f: json.dump(self.settings, f, indent=4)
        except Exception as e: print(f"Erreur lors de la sauvegarde des paramètres: {e}")
    def apply_theme(self):
        theme = self.settings.get("theme", "dark")
        dark_colors = {"background": "#1e1e1e", "widget_bg": "#252525", "hover_bg": "#3c3c3c", "text": "#d4d4d4", "text_secondary": "#a0a0a0", "primary_button_bg": "#f0f0f0", "primary_button_fg": "#1e1e1e", "primary_hover_bg": "#bbbbbb", "status_active": "#4CAF50", "status_inactive": "#F44336"}
        light_colors = {"background": "#f0f0f0", "widget_bg": "#e0e0e0", "hover_bg": "#cccccc", "text": "#1e1e1e", "text_secondary": "#555555", "primary_button_bg": "#1e1e1e", "primary_button_fg": "#ffffff", "primary_hover_bg": "#3c3c3c", "status_active": "#009900", "status_inactive": "#cc0000"}
        self.colors = light_colors if theme == "light" else dark_colors
        self.fonts = {"title": font.Font(family="Segoe UI", size=18, weight="bold"), "key": font.Font(family="Segoe UI", size=14, weight="bold"), "value": font.Font(family="Segoe UI", size=14), "button": font.Font(family="Segoe UI", size=11, weight="bold"), "version": font.Font(family="Segoe UI", size=8)}
        self.root.configure(bg=self.colors["background"])
        style = ttk.Style(self.root); style.theme_use('clam')
        style.configure('TFrame', background=self.colors["background"])
        style.configure('TLabel', background=self.colors["background"], foreground=self.colors["text"], font=self.fonts["value"])
        style.configure('Primary.TButton', font=self.fonts["button"], padding=(15, 8), borderwidth=0, background=self.colors["primary_button_bg"], foreground=self.colors["primary_button_fg"])
        style.map('Primary.TButton', background=[('active', self.colors["primary_hover_bg"])])
        style.configure('Secondary.TButton', font=self.fonts["button"], padding=(15, 8), borderwidth=0, background=self.colors["widget_bg"], foreground=self.colors["text"])
        style.map('Secondary.TButton', background=[('active', self.colors["hover_bg"])])
        style.configure('Icon.TButton', padding=0, borderwidth=0, relief="flat", background=self.colors["background"])
        style.map('Icon.TButton', background=[('active', self.colors["hover_bg"])])
    def create_copy_icon_images(self):
        def _create_icon(color, bg_color):
            img = Image.new('RGBA', (16,16), (0,0,0,0)); draw = ImageDraw.Draw(img)
            draw.rectangle([2, 5, 11, 14], outline=color, width=1); draw.rectangle([5, 2, 14, 11], outline=color, width=1, fill=bg_color)
            return ImageTk.PhotoImage(img)
        self.copy_icon_image = _create_icon(self.colors["text"], self.colors["widget_bg"])
        self.copy_icon_disabled_image = _create_icon(self.colors["text_secondary"], self.colors["background"])
    def refresh_ui_after_theme_change(self):
        for widget in self.root.winfo_children(): widget.destroy()
        self.create_copy_icon_images()
        self.create_widgets()

    def create_widgets(self):
        self.main_frame = ttk.Frame(self.root, padding=(30, 20)); self.main_frame.pack(fill=tk.BOTH, expand=True)
        title_frame = ttk.Frame(self.main_frame); title_frame.pack(fill=tk.X, pady=(0, 25))
        title_label = ttk.Label(title_frame, text="Zaap Finder", font=self.fonts["title"], foreground=self.colors["text"]); title_label.pack(side=tk.LEFT, anchor='w')
        
        minimize_button = ttk.Button(title_frame, text="Réduire", style='Secondary.TButton', command=self.hide_to_tray); minimize_button.pack(side=tk.RIGHT)
        Tooltip(minimize_button, "Réduire dans la zone de notification")
        
        settings_icon_image = self.create_settings_icon(self.colors["text_secondary"])
        self.settings_icon_tk = ImageTk.PhotoImage(settings_icon_image)
        settings_button = ttk.Button(title_frame, image=self.settings_icon_tk, style='Icon.TButton', command=self.open_settings_window)
        settings_button.pack(side=tk.RIGHT, padx=(0, 10))
        Tooltip(settings_button, "Ouvrir les paramètres")
        
        control_frame = ttk.Frame(self.main_frame); control_frame.pack(fill=tk.X, pady=(0, 30))
        self.status_label = ttk.Label(control_frame, text="Inactif", font=self.fonts["key"], foreground=self.colors["status_inactive"]); self.status_label.pack(side=tk.LEFT, anchor='w')
        self.toggle_button = ttk.Button(control_frame, text="Activer", style='Primary.TButton', command=self.toggle_script); self.toggle_button.pack(side=tk.RIGHT, anchor='e')
        self.info_labels = {}
        info_data = { "Détecté": "...", "Zaap": "...", "Région": "...", "Position Zaap": "...", "Distance": "...", "Commande": "..."}
        for label_text, value_text in info_data.items():
            row_frame = ttk.Frame(self.main_frame, padding=(0, 8)); row_frame.pack(fill=tk.X)
            key_label = ttk.Label(row_frame, text=label_text, font=self.fonts["key"], foreground=self.colors["text_secondary"]); key_label.grid(row=0, column=0, sticky="w")
            value_label = ttk.Label(row_frame, text=value_text, font=self.fonts["value"], foreground=self.colors["text"]); value_label.grid(row=0, column=1, sticky="w", padx=15)
            self.info_labels[label_text] = value_label
            if label_text == "Commande":
                self.copy_button = ttk.Button(row_frame, image=self.copy_icon_disabled_image, style='Icon.TButton', command=self.copy_command_to_clipboard, state=tk.DISABLED)
                self.copy_button.grid(row=0, column=2, sticky="w", padx=(5,0))
                Tooltip(self.copy_button, "Copier la dernière commande")
        version_label = ttk.Label(self.root, text=APP_VERSION, name="version_label", font=self.fonts["version"], foreground=self.colors["text_secondary"], background=self.colors["background"])
        version_label.place(relx=1.0, rely=1.0, x=-5, y=-5, anchor='se')
    
    def open_settings_window(self): SettingsWindow(self)
    def poll_clipboard(self):
        if not self.is_running: return
        try: clip = pyperclip.paste()
        except pyperclip.PyperclipException: self.root.after(REFRESH_INTERVAL_MS, self.poll_clipboard); return
        if clip != self.last_clip:
            self.last_clip = clip; match = COORD_REGEX.match(clip.strip())
            if match:
                x, y = int(match.group(1)), int(match.group(2))
                result = find_nearest_zaap(x, y, self.settings, self.get_game_data())
                if result:
                    name, region, zx, zy, dist = result; cmd = f"/travel {x},{y}"
                    pyperclip.copy(cmd); self.show_notification(name)
                    self.info_labels["Détecté"].config(text=f"[{x},{y}]")
                    self.info_labels["Zaap"].config(text=name)
                    self.info_labels["Région"].config(text=region)
                    self.info_labels["Position Zaap"].config(text=f"[{zx},{zy}]")
                    self.info_labels["Distance"].config(text=f"{dist} cases")
                    self.info_labels["Commande"].config(text=cmd)
                    if self.copy_button: self.copy_button.config(state=tk.NORMAL, image=self.copy_icon_image)
        self.root.after(REFRESH_INTERVAL_MS, self.poll_clipboard)
    
    def show_notification(self, name):
        if not self.settings["notifications"]["enabled"]:
            return
        def do_toast():
            try:
                # Utilise la fonction resource_path pour trouver l'icône, même dans l'EXE
                icon_path = resource_path("icon.ico")
                self.toaster.show_toast(title=name, msg=" ", icon_path=icon_path, duration=4, threaded=False)
            except Exception as e:
                if "notifications are active" not in str(e): print(f"Erreur de notification: {e}")
        threading.Thread(target=do_toast, daemon=True).start()
    
    def create_settings_icon(self, color):
        HIGH_RES_SIZE = 64; FINAL_SIZE = 18
        img_hr = Image.new('RGBA', (HIGH_RES_SIZE, HIGH_RES_SIZE), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img_hr)
        center = HIGH_RES_SIZE / 2; num_teeth = 6
        outer_radius = center - 8; hole_radius = center / 3.5
        draw.ellipse((center - outer_radius, center - outer_radius, center + outer_radius, center + outer_radius), outline=color, width=8)
        for i in range(num_teeth):
            angle = i * (360 / num_teeth) + 15
            x1 = center + (outer_radius - 4) * cos(radians(angle)); y1 = center + (outer_radius - 4) * sin(radians(angle))
            x2 = center + (outer_radius + 4) * cos(radians(angle)); y2 = center + (outer_radius + 4) * sin(radians(angle))
            draw.line((x1, y1, x2, y2), fill=color, width=12)
        draw.ellipse((center - hole_radius, center - hole_radius, center + hole_radius, center + hole_radius), fill=(0,0,0,0))
        img_resized = img_hr.resize((FINAL_SIZE, FINAL_SIZE), Image.Resampling.LANCZOS)
        return img_resized
        
    def get_toggle_status_text(self, *args): return "Désactiver" if self.is_running else "Activer"
    def toggle_from_tray(self): self.root.after(0, self.toggle_script)
    def run_tray_icon(self):
        menu = pystray.Menu(pystray.MenuItem('Ouvrir', self.show_window, default=True), pystray.MenuItem(self.get_toggle_status_text, self.toggle_from_tray), pystray.Menu.SEPARATOR, pystray.MenuItem('Quitter', self.quit_app))
        self.tray_icon = pystray.Icon("ZaapFinder", self.portal_icon_pil, "Zaap Finder", menu); self.tray_icon.run()
    def hide_to_tray(self):
        if not self.tray_thread or not self.tray_thread.is_alive():
            self.root.withdraw()
            self.tray_thread = threading.Thread(target=self.run_tray_icon, daemon=True)
            self.tray_thread.start()
        else:
            self.root.withdraw()
    def show_window(self):
        if self.tray_icon: self.tray_icon.stop()
        self.tray_thread = None
        self.root.after(0, self.root.deiconify)

    def quit_app(self):
        print("Fermeture de l'application...")
        self.is_running = False
        if self.tray_icon: self.tray_icon.stop()
        self.root.destroy()

    def copy_command_to_clipboard(self):
        command_text = self.info_labels["Commande"].cget("text")
        if command_text not in ["...", "N/A"]: pyperclip.copy(command_text); print(f"Commande '{command_text}' copiée manuellement depuis la GUI.")
    def toggle_script(self):
        if self.is_running:
            self.is_running = False; self.status_label.config(text="Inactif", foreground=self.colors["status_inactive"]); self.toggle_button.config(text="Activer")
            if self.copy_button: self.copy_button.config(state=tk.DISABLED, image=self.copy_icon_disabled_image)
            print("Surveillance du presse-papiers arrêtée.")
        else:
            self.is_running = True; self.status_label.config(text="Actif", foreground=self.colors["status_active"]); self.toggle_button.config(text="Désactiver")
            print("Surveillance du presse-papiers activée."); self.poll_clipboard()

# ==============================================================================
# POINT D'ENTRÉE DU SCRIPT
# ==============================================================================
if __name__ == "__main__":
    if sys.platform == "win32":
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(2); myappid = 'ZaapFinder'
            windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except (ImportError, AttributeError): pass
    root = tk.Tk()
    root.withdraw()
    app = ZaapFinderApp(root)
    root.deiconify()
    root.mainloop()