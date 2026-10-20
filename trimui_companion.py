# -*- coding: utf-8 -*-
from __future__ import annotations
import os, sys, json, shutil, hashlib, subprocess, threading, csv
from pathlib import Path
from datetime import datetime
import tkinter.filedialog as fd
import tkinter.messagebox as mb
import customtkinter as ctk

APP = "TrimUI Companion"
APP_VERSION = "0.2.0"
CFG_DIR = Path(os.getenv("APPDATA", str(Path.home()))) / "TrimUICompanion"
CFG_FILE = CFG_DIR / "settings.json"
ROM_EXTS = {".zip",".7z",".rar",".iso",".chd",".cue",".bin",".rom",".nes",".smc",".sfc",".gba",".gbc",".gb",".nds",".3ds",".cia",".n64",".z64",".v64",".md",".gen",".sms",".gg",".pce",".pbp",".cso",".cdi",".gdi",".wad",".wud",".wbfs",".dol",".elf",".m3u",".adf",".dsk",".tap",".prg",".lnx",".j64",".a26",".a78",".ws",".wsc",".mgw"}
SKIP_DIRS = {"imgs","images","covers","screenshots","manuals","videos",".git","lost+found"}

def read_cfg():
    try: return json.loads(CFG_FILE.read_text(encoding="utf-8"))
    except Exception: return {}

def write_cfg(cfg):
    CFG_DIR.mkdir(parents=True, exist_ok=True)
    CFG_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")

def sizefmt(n):
    n=float(n)
    for u in ("B","KB","MB","GB","TB"):
        if n < 1024 or u == "TB": return f"{int(n)} {u}" if u=="B" else f"{n:.1f} {u}"
        n /= 1024

def digest(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green")
        self.title("TrimUI Companion")
        self.geometry("1220x790")
        self.minsize(1050,690)
        self.configure(fg_color="#0b111b")
        self.cfg=read_cfg()
        self.sd=ctk.StringVar(value=self.cfg.get("sd_root",""))
        self.backup=ctk.StringVar(value=self.cfg.get("backup_root",str(Path.home()/"TrimUI Backups")))
        self.roms=ctk.StringVar(value=self.cfg.get("roms_rel","Roms"))
        self.covers=ctk.StringVar(value=self.cfg.get("covers_rel","Imgs"))
        self.themes=ctk.StringVar(value=self.cfg.get("themes_rel","Themes"))
        self.host=ctk.StringVar(value=self.cfg.get("ssh_host",""))
        self.user=ctk.StringVar(value=self.cfg.get("ssh_user","root"))
        self.remote=ctk.StringVar(value=self.cfg.get("ssh_path","/mnt/SDCARD"))
        self.games=[]; self.duplicate_paths=set(); self.page_buttons={}
        self._build()
        self.protocol("WM_DELETE_WINDOW",self.close)
        self.show_page("home")

    def _build(self):
        self.grid_columnconfigure(1,weight=1); self.grid_rowconfigure(0,weight=1)
        self.sidebar=ctk.CTkFrame(self,width=235,corner_radius=0,fg_color="#101a28")
        self.sidebar.grid(row=0,column=0,sticky="nsew"); self.sidebar.grid_propagate(False)
        brand=ctk.CTkFrame(self.sidebar,fg_color="transparent")
        brand.pack(fill="x",padx=20,pady=(24,26))
        ctk.CTkLabel(brand,text="◈",font=ctk.CTkFont(size=31,weight="bold"),text_color="#5ee0b0").pack(side="left",padx=(0,10))
        brandtxt=ctk.CTkFrame(brand,fg_color="transparent"); brandtxt.pack(side="left")
        ctk.CTkLabel(brandtxt,text="TRIMUI",font=ctk.CTkFont(size=18,weight="bold"),text_color="#f1f5f9").pack(anchor="w")
        ctk.CTkLabel(brandtxt,text="COMPANION",font=ctk.CTkFont(size=10,weight="bold"),text_color="#5ee0b0").pack(anchor="w")
        ctk.CTkLabel(self.sidebar,text="УПРАВЛЕНИЕ",font=ctk.CTkFont(size=10,weight="bold"),text_color="#64748b").pack(anchor="w",padx=22,pady=(0,8))
        nav=[("home","⌂","Обзор"),("library","▦","Игровая библиотека"),("backup","◉","Резервные копии"),("art","▧","Обложки и темы"),("network","⌁","Wi-Fi / SSH"),("settings","⚙","Настройки")]
        for key,ico,label in nav:
            b=ctk.CTkButton(self.sidebar,text=f"{ico}    {label}",anchor="w",height=43,corner_radius=10,
                fg_color="transparent",hover_color="#1c2b3d",text_color="#c5d0df",
                font=ctk.CTkFont(size=13),command=lambda k=key:self.show_page(k))
            b.pack(fill="x",padx=12,pady=3); self.page_buttons[key]=b
        ctk.CTkFrame(self.sidebar,fg_color="#243346",height=1).pack(fill="x",padx=18,pady=(22,12))
        ctk.CTkLabel(self.sidebar,text="УСТРОЙСТВО",font=ctk.CTkFont(size=10,weight="bold"),text_color="#64748b").pack(anchor="w",padx=22,pady=(0,8))
        self.device_label=ctk.CTkLabel(self.sidebar,text="●  Карта не выбрана",font=ctk.CTkFont(size=12),text_color="#fbbf24",anchor="w",wraplength=195)
        self.device_label.pack(fill="x",padx=22)
        ctk.CTkLabel(self.sidebar,text=f"Версия {APP_VERSION}",font=ctk.CTkFont(size=10),text_color="#566579").pack(side="bottom",anchor="w",padx=22,pady=18)

        self.main=ctk.CTkFrame(self,fg_color="#0b111b",corner_radius=0)
        self.main.grid(row=0,column=1,sticky="nsew")
        self.main.grid_columnconfigure(0,weight=1); self.main.grid_rowconfigure(1,weight=1)
        top=ctk.CTkFrame(self.main,fg_color="transparent")
        top.grid(row=0,column=0,sticky="ew",padx=28,pady=(22,10)); top.grid_columnconfigure(0,weight=1)
        self.page_title=ctk.CTkLabel(top,text="Обзор",font=ctk.CTkFont(size=27,weight="bold"),text_color="#f1f5f9")
        self.page_title.grid(row=0,column=0,sticky="w")
        self.top_status=ctk.CTkLabel(top,text="ГОТОВ К РАБОТЕ",font=ctk.CTkFont(size=10,weight="bold"),text_color="#5ee0b0",fg_color="#142a28",corner_radius=8,padx=12,pady=8)
        self.top_status.grid(row=0,column=1,sticky="e")
        self.content=ctk.CTkFrame(self.main,fg_color="transparent")
        self.content.grid(row=1,column=0,sticky="nsew",padx=28,pady=(4,12))
        self.content.grid_columnconfigure(0,weight=1); self.content.grid_rowconfigure(0,weight=1)
        bottom=ctk.CTkFrame(self.main,fg_color="#101a28",corner_radius=10,height=42)
        bottom.grid(row=2,column=0,sticky="ew",padx=28,pady=(0,18))
        self.status=ctk.CTkLabel(bottom,text="Выбери microSD, чтобы начать.",font=ctk.CTkFont(size=11),text_color="#94a3b8",anchor="w")
        self.status.pack(fill="x",padx=14,pady=10)

    def card(self,parent,title,value,caption,accent="#5ee0b0"):
        f=ctk.CTkFrame(parent,fg_color="#121e2d",corner_radius=14,border_width=1,border_color="#1d2b3d")
        ctk.CTkLabel(f,text=title.upper(),font=ctk.CTkFont(size=10,weight="bold"),text_color="#7f91a8").pack(anchor="w",padx=17,pady=(15,4))
        v=ctk.CTkLabel(f,text=value,font=ctk.CTkFont(size=27,weight="bold"),text_color=accent)
        v.pack(anchor="w",padx=17)
        ctk.CTkLabel(f,text=caption,font=ctk.CTkFont(size=11),text_color="#91a0b4",wraplength=220).pack(anchor="w",padx=17,pady=(2,15))
        return f,v

    def clear_content(self):
        for w in self.content.winfo_children(): w.destroy()
        self.content.grid_rowconfigure(0,weight=1)

    def show_page(self,key):
        self.current_page=key
        names={"home":"Обзор","library":"Игровая библиотека","backup":"Резервные копии","art":"Обложки и темы","network":"Wi-Fi / SSH","settings":"Настройки"}
        self.page_title.configure(text=names[key])
        for k,b in self.page_buttons.items():
            b.configure(fg_color="#1b3c35" if k==key else "transparent",text_color="#75e7bd" if k==key else "#c5d0df")
        self.clear_content()
        getattr(self,"page_"+key)()

    def root(self):
        return Path(self.sd.get().strip().strip('"')) if self.sd.get().strip() else Path("__no_sd_selected__")

    def choose_sd(self):
        p=fd.askdirectory(title="Выбери корень microSD TrimUI")
        if p:
            self.sd.set(p); self.cfg["sd_root"]=p; write_cfg(self.cfg)
            self.device_label.configure(text="●  microSD подключена",text_color="#5ee0b0")
            self.scan(silent=True); self.show_page(self.current_page)

    def choose_backup(self):
        p=fd.askdirectory(title="Папка для резервных копий")
        if p: self.backup.set(p)

    def page_home(self):
        wrap=ctk.CTkScrollableFrame(self.content,fg_color="transparent")
        wrap.grid(row=0,column=0,sticky="nsew")
        hero=ctk.CTkFrame(wrap,fg_color="#13283a",corner_radius=18)
        hero.pack(fill="x",pady=(0,18))
        left=ctk.CTkFrame(hero,fg_color="transparent"); left.pack(side="left",fill="both",expand=True,padx=24,pady=22)
        ctk.CTkLabel(left,text="Твоя игровая система.\nВ полном порядке.",font=ctk.CTkFont(size=25,weight="bold"),text_color="#f2f7fc",justify="left").pack(anchor="w")
        ctk.CTkLabel(left,text="Управляй библиотекой, сохранениями и файлами консоли из одного приложения.",font=ctk.CTkFont(size=12),text_color="#a9bacd",wraplength=480,justify="left").pack(anchor="w",pady=(8,16))
        ctk.CTkButton(left,text="Выбрать microSD  →",height=39,corner_radius=10,command=self.choose_sd).pack(anchor="w")
        ctk.CTkLabel(hero,text="◈",font=ctk.CTkFont(size=94,weight="bold"),text_color="#2e6d60").pack(side="right",padx=28,pady=15)
        stats=ctk.CTkFrame(wrap,fg_color="transparent"); stats.pack(fill="x",pady=(0,18))
        for i in range(4): stats.grid_columnconfigure(i,weight=1)
        count=len(self.games); total=sum(g["size"] for g in self.games); platforms=len(set(g["platform"] for g in self.games))
        _,self.home_games=self.card(stats,"Игры",str(count),"Файлов в библиотеке")
        _,self.home_size=self.card(stats,"Объём",sizefmt(total),"Общий размер найденных игр")
        _,self.home_platforms=self.card(stats,"Платформы",str(platforms),"Каталогов с играми")
        _,self.home_dupes=self.card(stats,str("Дубликаты"),str(len(self.duplicate_paths)) if self.duplicate_paths else "—","Запусти проверку для анализа","#fbbf24")
        for i,w in enumerate(stats.winfo_children()): w.grid(row=0,column=i,sticky="ew",padx=(0 if i==0 else 8,0))
        section=ctk.CTkFrame(wrap,fg_color="#121e2d",corner_radius=14)
        section.pack(fill="x",pady=(0,12))
        ctk.CTkLabel(section,text="Быстрые действия",font=ctk.CTkFont(size=15,weight="bold"),text_color="#eef4fb").pack(anchor="w",padx=18,pady=(16,10))
        row=ctk.CTkFrame(section,fg_color="transparent"); row.pack(fill="x",padx=14,pady=(0,16))
        for label,cmd in [("▦  Сканировать игры",lambda:self.scan()),("◉  Создать backup",lambda:self.show_page("backup")),("⌁  Подключить по SSH",lambda:self.show_page("network"))]:
            ctk.CTkButton(row,text=label,command=cmd,fg_color="#223348",hover_color="#2c435b",height=38).pack(side="left",fill="x",expand=True,padx=4)
        ctk.CTkLabel(wrap,text="Безопасность прежде всего: приложение не удаляет игры и не прошивает консоль. Проверяй пути и делай резервные копии перед изменениями.",font=ctk.CTkFont(size=11),text_color="#7f91a8",wraplength=850,justify="left").pack(anchor="w",pady=6)

    def page_library(self):
        panel=ctk.CTkFrame(self.content,fg_color="#121e2d",corner_radius=14)
        panel.grid(row=0,column=0,sticky="nsew")
        panel.grid_columnconfigure(0,weight=1); panel.grid_rowconfigure(2,weight=1)
        bar=ctk.CTkFrame(panel,fg_color="transparent"); bar.grid(row=0,column=0,sticky="ew",padx=16,pady=(15,10))
        self.search=ctk.StringVar()
        ctk.CTkEntry(bar,textvariable=self.search,placeholder_text="⌕   Поиск по названию, платформе или пути…",height=38).pack(side="left",fill="x",expand=True,padx=(0,8))
        self.search.trace_add("write",lambda *_:self.refresh_table())
        ctk.CTkButton(bar,text="Сканировать",width=110,command=self.scan).pack(side="left",padx=4)
        ctk.CTkButton(bar,text="Дубликаты",width=100,fg_color="#3a3021",hover_color="#594329",command=self.find_duplicates).pack(side="left",padx=4)
        ctk.CTkButton(bar,text="Экспорт CSV",width=100,fg_color="#223348",command=self.export_csv).pack(side="left",padx=4)
        self.lib_summary=ctk.CTkLabel(panel,text="Сначала выбери корень microSD.",text_color="#8fa0b4",anchor="w")
        self.lib_summary.grid(row=1,column=0,sticky="ew",padx=18,pady=(0,8))
        table=ctk.CTkFrame(panel,fg_color="#0d1622",corner_radius=10)
        table.grid(row=2,column=0,sticky="nsew",padx=14,pady=(0,14))
        table.grid_columnconfigure(0,weight=1); table.grid_rowconfigure(0,weight=1)
        import tkinter.ttk as ttk
        style=ttk.Style()
        try: style.theme_use("clam")
        except: pass
        style.configure("Trim.Treeview",background="#0d1622",fieldbackground="#0d1622",foreground="#e2eaf4",rowheight=29,borderwidth=0,font=("Segoe UI",10))
        style.configure("Trim.Treeview.Heading",background="#1c2b3d",foreground="#b9c8da",relief="flat",font=("Segoe UI",9,"bold"))
        style.map("Trim.Treeview",background=[("selected","#22594c")])
        self.tree=ttk.Treeview(table,columns=("platform","name","size","path"),show="headings",style="Trim.Treeview")
        for col,title,width in [("platform","ПЛАТФОРМА",125),("name","ИГРА / ФАЙЛ",250),("size","РАЗМЕР",95),("path","ПУТЬ",420)]:
            self.tree.heading(col,text=title); self.tree.column(col,width=width,anchor="w")
        y=ttk.Scrollbar(table,orient="vertical",command=self.tree.yview); self.tree.configure(yscrollcommand=y.set)
        self.tree.grid(row=0,column=0,sticky="nsew"); y.grid(row=0,column=1,sticky="ns")
        actions=ctk.CTkFrame(panel,fg_color="transparent"); actions.grid(row=3,column=0,sticky="ew",padx=16,pady=(0,13))
        ctk.CTkButton(actions,text="Открыть расположение",command=self.open_selected,fg_color="#223348").pack(side="left")
        ctk.CTkLabel(actions,text="Дубликаты отмечаются, но не удаляются автоматически.",text_color="#7f91a8",font=ctk.CTkFont(size=11)).pack(side="right")
        self.refresh_table()

    def refresh_table(self):
        if not hasattr(self,"tree") or not self.tree.winfo_exists(): return
        self.tree.delete(*self.tree.get_children())
        q=self.search.get().lower().strip() if hasattr(self,"search") else ""
        shown=0
        for i,g in enumerate(self.games):
            if q and q not in f"{g['name']} {g['platform']} {g['path']}".lower(): continue
            self.tree.insert("","end",iid=str(i),values=(g["platform"],g["name"],sizefmt(g["size"]),str(g["path"])))
            shown+=1
        if hasattr(self,"lib_summary") and self.lib_summary.winfo_exists():
            self.lib_summary.configure(text=f"Найдено: {len(self.games)} игр  •  Показано: {shown}  •  Размер: {sizefmt(sum(g['size'] for g in self.games))}")

    def scan(self,silent=False):
        root=self.root()
        if not root.exists():
            if not silent: mb.showwarning(APP,"Сначала выбери корень microSD.")
            return
        romroot=root/self.roms.get().strip()
        if not romroot.exists():
            # Some firmwares use different capitalization or folder name.
            candidates=[p for p in root.iterdir() if p.is_dir() and p.name.lower()=="roms"] if root.exists() else []
            romroot=candidates[0] if candidates else root
        games=[]; total=0; platforms=set()
        try:
            for current,dirs,files in os.walk(romroot):
                dirs[:]=[d for d in dirs if d.lower() not in SKIP_DIRS and not d.startswith(".")]
                cur=Path(current); rel=cur.relative_to(romroot); platform=rel.parts[0] if rel.parts else "Корень"
                for fn in files:
                    p=cur/fn
                    if p.suffix.lower() not in ROM_EXTS: continue
                    try: sz=p.stat().st_size
                    except OSError: continue
                    games.append({"path":p,"name":p.name,"platform":platform,"size":sz}); total+=sz; platforms.add(platform)
        except Exception as e:
            mb.showerror(APP,f"Ошибка сканирования:\n{e}"); return
        self.games=games; self.duplicate_paths=set()
        self.status.configure(text=f"Сканирование завершено • найдено {len(games)} файлов")
        self.top_status.configure(text="КАРТА ПРОВЕРЕНА",text_color="#5ee0b0")
        if hasattr(self,"tree") and self.tree.winfo_exists(): self.refresh_table()
        if self.current_page=="home": self.show_page("home")
        if not silent: mb.showinfo(APP,f"Сканирование завершено.\n\nИгры: {len(games)}\nПлатформы: {len(platforms)}\nРазмер: {sizefmt(total)}")

    def find_duplicates(self):
        if not self.games: self.scan(silent=True)
        if not self.games: mb.showinfo(APP,"Сначала просканируй библиотеку."); return
        if not mb.askyesno(APP,"Сравнить файлы одинакового размера по SHA-256?\nНа больших библиотеках это может занять время. Ничего не будет удалено."): return
        bysize={}
        for g in self.games: bysize.setdefault(g["size"],[]).append(g)
        duplicates=set()
        for group in bysize.values():
            if len(group)<2: continue
            byhash={}
            for g in group:
                try: byhash.setdefault(digest(g["path"]),[]).append(g)
                except OSError: pass
            for matches in byhash.values():
                if len(matches)>1:
                    duplicates.update(str(g["path"]) for g in matches)
        self.duplicate_paths=duplicates
        self.status.configure(text=f"Проверка завершена • файлов в группах дубликатов: {len(duplicates)}")
        if self.current_page=="home": self.show_page("home")
        if duplicates:
            text="\n".join(sorted(duplicates))
            mb.showinfo("Найдены дубликаты",f"Файлов в группах дубликатов: {len(duplicates)}\n\n{text[:2500]}\n\nНичего не удалено.")
        else: mb.showinfo("Дубликаты","Совпадающих файлов не найдено.")

    def export_csv(self):
        if not self.games: mb.showinfo(APP,"Сначала просканируй библиотеку."); return
        p=fd.asksaveasfilename(title="Экспорт библиотеки",defaultextension=".csv",filetypes=[("CSV","*.csv")],initialfile="trimui_library.csv")
        if not p:return
        try:
            with open(p,"w",newline="",encoding="utf-8-sig") as f:
                w=csv.writer(f,delimiter=";");w.writerow(["Платформа","Название","Размер, байт","Путь"])
                for g in self.games:w.writerow([g["platform"],g["name"],g["size"],str(g["path"])])
            self.status.configure(text=f"CSV сохранён: {p}")
        except Exception as e:mb.showerror(APP,str(e))

    def open_selected(self):
        if not hasattr(self,"tree"):return
        sel=self.tree.selection()
        if not sel:return
        p=self.games[int(sel[0])]["path"].parent
        try: os.startfile(str(p))
        except Exception as e: mb.showerror(APP,str(e))

    def page_backup(self):
        f=ctk.CTkFrame(self.content,fg_color="#121e2d",corner_radius=14)
        f.grid(row=0,column=0,sticky="nsew")
        ctk.CTkLabel(f,text="Твои сохранения — под защитой",font=ctk.CTkFont(size=22,weight="bold"),text_color="#f1f5f9").pack(anchor="w",padx=22,pady=(22,6))
        ctk.CTkLabel(f,text="Создаёт датированную копию выбранных каталогов на компьютере. Исходные файлы на карте не меняются.",text_color="#91a0b4",wraplength=800,justify="left").pack(anchor="w",padx=22,pady=(0,18))
        row=ctk.CTkFrame(f,fg_color="transparent");row.pack(fill="x",padx=22)
        ctk.CTkEntry(row,textvariable=self.backup,placeholder_text="Папка резервных копий").pack(side="left",fill="x",expand=True)
        ctk.CTkButton(row,text="Обзор",width=90,command=self.choose_backup).pack(side="left",padx=8)
        ctk.CTkLabel(f,text="ВЫБЕРИ КАТАЛОГИ ДЛЯ КОПИРОВАНИЯ",font=ctk.CTkFont(size=10,weight="bold"),text_color="#7f91a8").pack(anchor="w",padx=22,pady=(24,10))
        self.backup_checks={}
        for title,rel,default in [("Сохранения эмуляторов","Saves",True),("Состояния (save states)","States",True),("Конфигурация RetroArch","RetroArch/.retroarch",True),("Системные настройки","System",False),("Скриншоты","Pictures/screenshots",False)]:
            v=ctk.BooleanVar(value=default);self.backup_checks[rel]=v
            ctk.CTkCheckBox(f,text=f"{title}    ·    {rel}",variable=v,checkbox_width=20,checkbox_height=20).pack(anchor="w",padx=24,pady=7)
        ctk.CTkButton(f,text="◉   Создать резервную копию",height=44,command=self.backup_now).pack(anchor="w",padx=22,pady=(25,12))
        ctk.CTkButton(f,text="Открыть папку резервных копий",fg_color="#223348",command=self.open_backup).pack(anchor="w",padx=22)
        ctk.CTkLabel(f,text="Пути могут отличаться в зависимости от прошивки. Перед использованием проверь, где твоя система хранит сохранения.",text_color="#7f91a8",font=ctk.CTkFont(size=11),wraplength=800,justify="left").pack(anchor="w",padx=22,pady=(22,18))

    def backup_now(self):
        root=self.root()
        if not root.exists(): mb.showwarning(APP,"Выбери корень microSD.");return
        selected=[r for r,v in self.backup_checks.items() if v.get()]
        found=[(r,root/r) for r in selected if (root/r).exists()]
        if not found:
            mb.showwarning(APP,"Выбранные папки не найдены. Проверь расположение сохранений для своей прошивки.");return
        dest=Path(self.backup.get())/("TrimUI_backup_"+datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
        if not mb.askyesno(APP,f"Создать резервную копию в:\n{dest}\n\nБудут скопированы {len(found)} найденных каталогов."):return
        try:
            dest.mkdir(parents=True,exist_ok=True)
            copied=[]
            for rel,src in found:
                out=dest/rel
                if src.is_dir():shutil.copytree(src,out,dirs_exist_ok=True)
                else:out.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,out)
                copied.append(rel)
            (dest/"backup_manifest.txt").write_text("TrimUI Companion backup\nCreated: "+datetime.now().isoformat()+"\nSource: "+str(root)+"\nFolders:\n"+"\n".join(copied),encoding="utf-8")
            self.status.configure(text=f"Резервная копия создана: {dest}")
            mb.showinfo(APP,f"Готово!\n\n{dest}\n\nСкопировано каталогов: {len(copied)}")
        except Exception as e:mb.showerror(APP,f"Ошибка резервного копирования:\n{e}")

    def open_backup(self):
        p=Path(self.backup.get());p.mkdir(parents=True,exist_ok=True)
        try:os.startfile(str(p))
        except Exception as e:mb.showerror(APP,str(e))

    def page_art(self):
        wrap=ctk.CTkScrollableFrame(self.content,fg_color="transparent")
        wrap.grid(row=0,column=0,sticky="nsew")
        cover=ctk.CTkFrame(wrap,fg_color="#121e2d",corner_radius=14);cover.pack(fill="x",pady=(0,16))
        ctk.CTkLabel(cover,text="Обложки игр",font=ctk.CTkFont(size=20,weight="bold"),text_color="#f1f5f9").pack(anchor="w",padx=20,pady=(18,5))
        ctk.CTkLabel(cover,text="Выбери игру в библиотеке, затем привяжи изображение. Программа скопирует его в настроенную папку по имени игры.",text_color="#91a0b4",wraplength=800,justify="left").pack(anchor="w",padx=20,pady=(0,12))
        ctk.CTkButton(cover,text="Выбрать обложку для игры…",height=39,command=self.add_cover).pack(anchor="w",padx=20,pady=(0,18))
        themes=ctk.CTkFrame(wrap,fg_color="#121e2d",corner_radius=14);themes.pack(fill="x")
        ctk.CTkLabel(themes,text="Темы оформления",font=ctk.CTkFont(size=20,weight="bold"),text_color="#f1f5f9").pack(anchor="w",padx=20,pady=(18,5))
        ctk.CTkLabel(themes,text="Установи файл или папку темы в каталог Themes. Совместимость зависит от прошивки; перед установкой прочитай её документацию.",text_color="#91a0b4",wraplength=800,justify="left").pack(anchor="w",padx=20,pady=(0,12))
        row=ctk.CTkFrame(themes,fg_color="transparent");row.pack(anchor="w",padx=20,pady=(0,18))
        ctk.CTkButton(row,text="Установить тему…",height=39,command=self.install_theme).pack(side="left")
        ctk.CTkButton(row,text="Открыть папку тем",height=39,fg_color="#223348",command=lambda:self.open_path(self.root()/self.themes.get())).pack(side="left",padx=8)
        ctk.CTkLabel(wrap,text="Важно: разные прошивки могут использовать собственные форматы обложек и тем. Копирование файлов не гарантирует, что система их распознает.",text_color="#7f91a8",font=ctk.CTkFont(size=11),wraplength=850,justify="left").pack(anchor="w",pady=15)

    def add_cover(self):
        if not self.games:
            mb.showinfo(APP,"Сначала просканируй библиотеку на вкладке «Игровая библиотека».");return
        # use selection if library tree exists, otherwise offer simple list
        selected_game=None
        if hasattr(self,"tree") and self.tree.winfo_exists() and self.tree.selection():
            selected_game=self.games[int(self.tree.selection()[0])]
        else:
            choices=[f"{g['platform']}  —  {g['name']}" for g in self.games]
            win=ctk.CTkToplevel(self);win.title("Выбрать игру");win.geometry("560x520");win.transient(self)
            ctk.CTkLabel(win,text="Выбери игру для обложки",font=ctk.CTkFont(size=17,weight="bold")).pack(anchor="w",padx=18,pady=14)
            search=ctk.StringVar();ctk.CTkEntry(win,textvariable=search,placeholder_text="Поиск игры…").pack(fill="x",padx=18,pady=(0,10))
            box=ctk.CTkScrollableFrame(win);box.pack(fill="both",expand=True,padx=18,pady=(0,12))
            def fill():
                for w in box.winfo_children():w.destroy()
                for i,g in enumerate(self.games):
                    if search.get().lower() not in f"{g['platform']} {g['name']}".lower():continue
                    ctk.CTkButton(box,text=f"{g['platform']}  ·  {g['name']}",anchor="w",fg_color="#1c2b3d",command=lambda gg=g:(choose(gg))).pack(fill="x",pady=2)
            def choose(g):
                nonlocal selected_game;selected_game=g;win.destroy()
            search.trace_add("write",lambda *_:fill());fill();self.wait_window(win)
        if not selected_game:return
        src=fd.askopenfilename(title="Выбери изображение обложки",filetypes=[("Изображения","*.png *.jpg *.jpeg *.webp *.bmp")])
        if not src:return
        destdir=self.root()/self.covers.get()/selected_game["platform"]
        try:
            destdir.mkdir(parents=True,exist_ok=True);dest=destdir/(selected_game["path"].stem+Path(src).suffix.lower())
            if dest.exists() and not mb.askyesno(APP,f"Обложка уже существует:\n{dest}\n\nЗаменить?"):return
            shutil.copy2(src,dest);self.status.configure(text=f"Обложка скопирована: {dest}")
            mb.showinfo(APP,f"Обложка скопирована:\n{dest}\n\nЕсли прошивка не показывает её, проверь требуемое имя файла и каталог в документации.")
        except Exception as e:mb.showerror(APP,str(e))

    def install_theme(self):
        root=self.root()
        if not root.exists():mb.showwarning(APP,"Сначала выбери корень microSD.");return
        src=fd.askdirectory(title="Выбери папку темы") or fd.askopenfilename(title="Выбери файл темы или архив",filetypes=[("Темы и архивы","*.zip *.7z *.tar *.gz *.png *.jpg *.json *.ini *.conf"),("Все файлы","*.*")])
        if not src:return
        p=Path(src);destdir=root/self.themes.get();destdir.mkdir(parents=True,exist_ok=True);dest=destdir/p.name
        if dest.exists() and not mb.askyesno(APP,f"Уже существует:\n{dest}\n\nЗаменить?"):return
        try:
            if p.is_dir():
                if dest.exists():shutil.rmtree(dest)
                shutil.copytree(p,dest)
            else:shutil.copy2(p,dest)
            self.status.configure(text=f"Тема скопирована: {dest}")
            mb.showinfo(APP,f"Файл темы скопирован:\n{dest}\n\nСовместимость с прошивкой не проверялась.")
        except Exception as e:mb.showerror(APP,str(e))

    def open_path(self,p):
        p=Path(p)
        if not p.exists():mb.showinfo(APP,f"Папка пока не существует:\n{p}");return
        try:os.startfile(str(p))
        except Exception as e:mb.showerror(APP,str(e))

    def page_network(self):
        f=ctk.CTkFrame(self.content,fg_color="#121e2d",corner_radius=14)
        f.grid(row=0,column=0,sticky="nsew")
        ctk.CTkLabel(f,text="Подключение без извлечения карты",font=ctk.CTkFont(size=22,weight="bold"),text_color="#f1f5f9").pack(anchor="w",padx=22,pady=(22,6))
        ctk.CTkLabel(f,text="Использует OpenSSH из Windows. На консоли должен быть включён SSH-сервер, а оба устройства должны быть в одной сети.",text_color="#91a0b4",wraplength=820,justify="left").pack(anchor="w",padx=22,pady=(0,20))
        form=ctk.CTkFrame(f,fg_color="transparent");form.pack(fill="x",padx=22)
        for label,var,hint in [("IP-адрес или имя хоста",self.host,"Например, 192.168.1.45"),("Пользователь",self.user,"Имя пользователя SSH"),("Удалённый каталог",self.remote,"Например, /mnt/SDCARD")]:
            row=ctk.CTkFrame(form,fg_color="transparent");row.pack(fill="x",pady=7)
            ctk.CTkLabel(row,text=label,width=190,anchor="w",text_color="#c5d0df").pack(side="left")
            ctk.CTkEntry(row,textvariable=var,placeholder_text=hint,height=38).pack(side="left",fill="x",expand=True)
        row=ctk.CTkFrame(f,fg_color="transparent");row.pack(anchor="w",padx=22,pady=(20,12))
        ctk.CTkButton(row,text="Проверить подключение",height=40,command=self.test_ssh).pack(side="left",padx=(0,8))
        ctk.CTkButton(row,text="Отправить файл…",height=40,fg_color="#223348",command=self.send_file).pack(side="left",padx=(0,8))
        ctk.CTkButton(row,text="Отправить папку…",height=40,fg_color="#223348",command=self.send_folder).pack(side="left")
        ctk.CTkFrame(f,fg_color="#342b1d",corner_radius=10).pack(fill="x",padx=22,pady=(12,0))
        ctk.CTkLabel(f,text="⚠  Не оставляй SSH включённым в недоверенной публичной сети. Проверь удалённый путь до передачи файлов. Пароли приложение не сохраняет.",text_color="#f4c77c",font=ctk.CTkFont(size=11),wraplength=820,justify="left").pack(anchor="w",padx=34,pady=(0,15))

    def ssh(self,args):
        exe=shutil.which("ssh")
        if not exe:raise RuntimeError("Не найден ssh.exe. Установи компонент Windows OpenSSH Client в настройках Windows.")
        return subprocess.run([exe]+args,capture_output=True,text=True,timeout=25)

    def test_ssh(self):
        if not self.host.get().strip() or not self.user.get().strip():mb.showwarning(APP,"Введи IP-адрес и пользователя.");return
        self.status.configure(text="Проверка SSH…")
        def worker():
            try:
                r=self.ssh(["-o","ConnectTimeout=8",f"{self.user.get().strip()}@{self.host.get().strip()}","echo TRIMUI_SSH_OK"])
                ok=r.returncode==0 and "TRIMUI_SSH_OK" in r.stdout
                msg="Подключение работает." if ok else "SSH не подтвердился.\n\n"+(r.stderr or r.stdout or f"Код: {r.returncode}")
            except Exception as e:ok=False;msg=str(e)
            self.after(0,lambda:(self.status.configure(text="SSH подключён." if ok else "SSH недоступен."),mb.showinfo("Проверка SSH",msg)))
        threading.Thread(target=worker,daemon=True).start()

    def scp_send(self,src,name,recursive):
        exe=shutil.which("scp")
        if not exe:raise RuntimeError("Не найден scp.exe. Установи Windows OpenSSH Client.")
        base=self.remote.get().strip().rstrip("/")
        target=f"{self.user.get().strip()}@{self.host.get().strip()}:{base}/{name}"
        args=[exe]+(["-r"] if recursive else [])+[str(src),target]
        return subprocess.run(args,capture_output=True,text=True,timeout=600)

    def send_file(self):
        p=fd.askopenfilename(title="Выбери файл для отправки")
        if p:self.send(p,Path(p).name,False)

    def send_folder(self):
        p=fd.askdirectory(title="Выбери папку для отправки")
        if p:self.send(p,Path(p).name,True)

    def send(self,src,name,recursive):
        if not self.host.get().strip() or not self.user.get().strip():mb.showwarning(APP,"Заполни адрес и пользователя SSH.");return
        dest=f"{self.user.get()}@{self.host.get()}:{self.remote.get().rstrip('/')}/{name}"
        if not mb.askyesno(APP,f"Передать выбранный объект?\n\n{src}\n\n→ {dest}\n\nПроверь удалённый путь."):return
        self.status.configure(text="Передача по SSH/SCP…")
        def worker():
            try:
                r=self.scp_send(src,name,recursive);ok=r.returncode==0;msg="Передача завершена." if ok else (r.stderr or r.stdout or f"Ошибка {r.returncode}")
            except Exception as e:ok=False;msg=str(e)
            self.after(0,lambda:(self.status.configure(text="Передача завершена." if ok else "Ошибка передачи."),mb.showinfo("Передача по сети",msg)))
        threading.Thread(target=worker,daemon=True).start()

    def page_settings(self):
        f=ctk.CTkFrame(self.content,fg_color="#121e2d",corner_radius=14)
        f.grid(row=0,column=0,sticky="nsew")
        ctk.CTkLabel(f,text="Настрой под свою прошивку",font=ctk.CTkFont(size=22,weight="bold"),text_color="#f1f5f9").pack(anchor="w",padx=22,pady=(22,6))
        ctk.CTkLabel(f,text="Пути зависят от прошивки. Укажи каталоги относительно корня microSD, например Roms, Imgs или Themes.",text_color="#91a0b4",wraplength=820,justify="left").pack(anchor="w",padx=22,pady=(0,20))
        row=ctk.CTkFrame(f,fg_color="transparent");row.pack(fill="x",padx=22,pady=(0,12))
        ctk.CTkLabel(row,text="Корень microSD",width=190,anchor="w").pack(side="left")
        ctk.CTkEntry(row,textvariable=self.sd,placeholder_text="Выбери папку карты").pack(side="left",fill="x",expand=True,padx=(0,8))
        ctk.CTkButton(row,text="Обзор",width=90,command=self.choose_sd).pack(side="left")
        for label,var in [("Папка игр",self.roms),("Папка обложек",self.covers),("Папка тем",self.themes),("Папка backup на ПК",self.backup)]:
            r=ctk.CTkFrame(f,fg_color="transparent");r.pack(fill="x",padx=22,pady=7)
            ctk.CTkLabel(r,text=label,width=190,anchor="w",text_color="#c5d0df").pack(side="left")
            ctk.CTkEntry(r,textvariable=var,height=38).pack(side="left",fill="x",expand=True)
            if var==self.backup:ctk.CTkButton(r,text="Обзор",width=90,command=self.choose_backup).pack(side="left",padx=(8,0))
        ctk.CTkButton(f,text="Сохранить настройки",height=42,command=self.save_settings).pack(anchor="w",padx=22,pady=(22,10))
        ctk.CTkLabel(f,text="TrimUI Companion — неофициальная утилита. Сначала проверяй работу на копии microSD. Программа не прошивает устройство и не удаляет ROM-файлы.",text_color="#7f91a8",font=ctk.CTkFont(size=11),wraplength=830,justify="left").pack(anchor="w",padx=22,pady=(14,20))

    def save_settings(self):
        self.cfg.update({"sd_root":self.sd.get(),"backup_root":self.backup.get(),"roms_rel":self.roms.get(),"covers_rel":self.covers.get(),"themes_rel":self.themes.get(),"ssh_host":self.host.get(),"ssh_user":self.user.get(),"ssh_path":self.remote.get()})
        write_cfg(self.cfg);self.status.configure(text="Настройки сохранены.")
        if self.sd.get() and Path(self.sd.get()).exists():self.device_label.configure(text="●  microSD подключена",text_color="#5ee0b0")
        else:self.device_label.configure(text="●  Карта не выбрана",text_color="#fbbf24")
        mb.showinfo(APP,"Настройки сохранены.")

    def close(self):
        self.save_cfg_silent();self.destroy()

    def save_cfg_silent(self):
        self.cfg.update({"sd_root":self.sd.get(),"backup_root":self.backup.get(),"roms_rel":self.roms.get(),"covers_rel":self.covers.get(),"themes_rel":self.themes.get(),"ssh_host":self.host.get(),"ssh_user":self.user.get(),"ssh_path":self.remote.get()})
        write_cfg(self.cfg)

if __name__=="__main__":
    app=App()
    app.mainloop()
