# -*- coding: utf-8 -*-
"""
GeoVista V3.0: Profesyonel CBS (GIS) Platformu
Geliştirici: Derya Güzey (deryaguzey2@gmail.com)
Lisans: MIT
Versiyon: 3.0.0 (Scientific Edition)
GitHub: https://github.com/deryaguzey/GeoVista.git
"""
import math, json, threading, webbrowser, os, tempfile, queue, pathlib, http.server, socketserver
from datetime import datetime
import customtkinter as ctk
import requests
from PIL import Image, ImageTk
import folium
import utm
import geopandas as gpd
from shapely.geometry import Point, mapping
from tkinter import filedialog, messagebox

_G_Q = queue.Queue()

C = {
    "bg":       "#0A1628",
    "sidebar":  "#0D1F3C",
    "card":     "#112240",
    "card2":    "#1A2F4A",
    "border":   "#1E3A5F",
    "primary":  "#4FC3F7",
    "pbtn":     "#0288D1",
    "hl":       "#1565C0",
    "sec":      "#26C6DA",
    "accent":   "#FF6B6B",
    "success":  "#66BB6A",
    "warn":     "#FFA726",
    "t1":       "#E8F4FD",
    "t2":       "#90A4AE",
    "t3":       "#546E7A",
}

NAV = [
    ("🏠", "Ana Sayfa",        "dashboard"),
    ("🧪", "Spatial Lab",      "spatial"),
    ("🔍", "Coğrafi Kodlama",  "geocoding"),
    ("🗺️", "İnteraktif Harita","map"),
    ("🌐", "Ülke Bilgileri",   "countries"),
    ("📐", "Koordinat Araçları","tools"),
    ("🌡️", "Hava & İklim",     "weather"),
    ("🌋", "Safet Lab",        "safet"), # NEW V3
    ("⛰️", "Yükseklik Analizi","elevation"),
    ("ℹ️", "Hakkında",         "about"),
]

API = {
    "nom_s":   "https://nominatim.openstreetmap.org/search",
    "nom_r":   "https://nominatim.openstreetmap.org/reverse",
    "rc_name": "https://restcountries.com/v3.1/name/{n}",
    "rc_all":  "https://restcountries.com/v3.1/all",
    "ip":      "http://ip-api.com/json",
    "elev":    "https://api.open-elevation.com/api/v1/lookup",
    "wx":      "https://api.open-meteo.com/v1/forecast",
    "aq":      "https://air-quality-api.open-meteo.com/v1/air-quality",
}
HDR = {"User-Agent": "GeoVista/1.0 (educational CBS tool)"}

def haversine(la1, lo1, la2, lo2):
    R = 6371.0
    la1,lo1,la2,lo2 = map(math.radians,[la1,lo1,la2,lo2])
    a = math.sin((la2-la1)/2)**2 + math.cos(la1)*math.cos(la2)*math.sin((lo2-lo1)/2)**2
    return R * 2 * math.asin(math.sqrt(a))

def bearing(la1,lo1,la2,lo2):
    la1,lo1,la2,lo2 = map(math.radians,[la1,lo1,la2,lo2])
    x = math.sin(lo2-lo1)*math.cos(la2)
    y = math.cos(la1)*math.sin(la2)-math.sin(la1)*math.cos(la2)*math.cos(lo2-lo1)
    return (math.degrees(math.atan2(x,y))+360)%360

def midpoint(la1,lo1,la2,lo2):
    la1,lo1,la2,lo2 = map(math.radians,[la1,lo1,la2,lo2])
    Bx = math.cos(la2)*math.cos(lo2-lo1)
    By = math.cos(la2)*math.sin(lo2-lo1)
    ml = math.atan2(math.sin(la1)+math.sin(la2), math.sqrt((math.cos(la1)+Bx)**2+By**2))
    mlo = lo1 + math.atan2(By, math.cos(la1)+Bx)
    return math.degrees(ml), math.degrees(mlo)

def dd_to_dms(dd):
    d=int(abs(dd)); m=int((abs(dd)-d)*60); s=((abs(dd)-d)*60-m)*60
    return d,m,s

def dms_to_dd(d,m,s,hem):
    dd=d+m/60+s/3600
    return -dd if hem in ('S','W') else dd

def brg_label(b):
    dirs=["K","KKD","KD","DKD","D","DGD","GD","GGD","G","GGB","GB","BGB","B","BKB","KB","KKB"]
    return dirs[round(b/22.5)%16]

_G_PORT = 18030 # Özel GeoVista Portu

def start_server():
    tmp_dir = os.path.join(os.getcwd(), "gv_maps")
    if not os.path.exists(tmp_dir): os.makedirs(tmp_dir)
    handler = http.server.SimpleHTTPRequestHandler
    handler.log_message = lambda *a: None
    try:
        with socketserver.TCPServer(("", _G_PORT), handler) as httpd:
            print(f"🌍 GeoVista V3 Sunucusu Başlatıldı: http://localhost:{_G_PORT}")
            httpd.serve_forever()
    except: pass

# Sunucuyu arka planda başlat
threading.Thread(target=start_server, daemon=True).start()

def tmp_map():
    tmp_dir = os.path.join(os.getcwd(), "gv_maps")
    if not os.path.exists(tmp_dir): os.makedirs(tmp_dir)
    fname = f"gv_{int(datetime.now().timestamp())}.html"
    return os.path.join(tmp_dir, fname), fname

class API_M:
    @staticmethod
    def geocode(q):
        try:
            r=requests.get(API["nom_s"],params={"q":q,"format":"json","limit":5,"addressdetails":1},headers=HDR,timeout=10)
            return r.json()
        except Exception as e: return {"error":str(e)}

    @staticmethod
    def reverse(lat,lon):
        try:
            r=requests.get(API["nom_r"],params={"lat":lat,"lon":lon,"format":"json","addressdetails":1},headers=HDR,timeout=10)
            return r.json()
        except Exception as e: return {"error":str(e)}

    @staticmethod
    def country(name):
        try:
            r=requests.get(API["rc_name"].format(n=name),timeout=10)
            return r.json()
        except Exception as e: return {"error":str(e)}

    @staticmethod
    def ip_loc():
        try:
            r=requests.get(API["ip"],timeout=8)
            return r.json()
        except Exception as e: return {"error":str(e)}

    @staticmethod
    def elevation(lat,lon):
        try:
            r=requests.get(API["elev"],params={"locations":f"{lat},{lon}"},headers=HDR,timeout=10)
            data=r.json()
            return data["results"][0]["elevation"] if "results" in data else None
        except: return None

    @staticmethod
    def weather(lat,lon):
        try:
            p={"latitude":lat,"longitude":lon,"current_weather":True,
               "daily":"temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode",
               "hourly":"temperature_2m,relativehumidity_2m,windspeed_10m",
               "timezone":"auto","forecast_days":7}
            r=requests.get(API["wx"],params=p,timeout=10)
            return r.json()
        except Exception as e: return {"error":str(e)}

    @staticmethod
    def air(lat,lon):
        try:
            p={"latitude":lat,"longitude":lon,
               "hourly":"pm10,pm2_5,european_aqi","timezone":"auto","forecast_days":1}
            r=requests.get(API["aq"],params=p,timeout=10)
            return r.json()
        except Exception as e: return {"error":str(e)}

class Card(ctk.CTkFrame):
    def __init__(self, p, title="", **kw):
        kw.setdefault("fg_color", C["card"]); kw.setdefault("corner_radius",12)
        super().__init__(p,**kw)
        if title:
            ctk.CTkLabel(self,text=title,font=ctk.CTkFont("Segoe UI",13,"bold"),
                         text_color=C["primary"],anchor="w").pack(padx=16,pady=(14,4),fill="x")
            ctk.CTkFrame(self,height=1,fg_color=C["border"]).pack(fill="x",padx=16,pady=(0,8))

class IRow(ctk.CTkFrame):
    def __init__(self,p,key,val,icon="",**kw):
        kw.setdefault("fg_color","transparent"); super().__init__(p,**kw)
        ctk.CTkLabel(self,text=f"{icon} {key}:" if icon else f"{key}:",
                     font=ctk.CTkFont("Segoe UI",12),text_color=C["t2"],width=155,anchor="w").pack(side="left")
        self.v=ctk.CTkLabel(self,text=str(val),font=ctk.CTkFont("Segoe UI",12,"bold"),
                            text_color=C["t1"],anchor="w",wraplength=420)
        self.v.pack(side="left",padx=(6,0))
    def set(self,v): self.v.configure(text=str(v))

class Stat(ctk.CTkFrame):
    def __init__(self,p,icon,label,value,color=None,**kw):
        kw.setdefault("fg_color",C["card"]); kw.setdefault("corner_radius",12)
        super().__init__(p,**kw); color=color or C["primary"]
        ctk.CTkLabel(self,text=icon,font=ctk.CTkFont(size=26)).pack(pady=(16,4))
        ctk.CTkLabel(self,text=str(value),font=ctk.CTkFont("Segoe UI",20,"bold"),text_color=color).pack()
        ctk.CTkLabel(self,text=label,font=ctk.CTkFont("Segoe UI",11),text_color=C["t2"]).pack(pady=(2,16))

class Spinner(ctk.CTkLabel):
    _F=["⣾","⣽","⣻","⢿","⡿","⣟","⣯","⣷"]
    def __init__(self,p,text="Yükleniyor...",**kw):
        kw.setdefault("font",ctk.CTkFont("Segoe UI",12))
        kw.setdefault("text_color",C["primary"])
        super().__init__(p,text=f"{self._F[0]}  {text}",**kw)
        self._run=False; self._i=0; self._t=text
    def start(self): self._run=True; self.configure(text=f"{self._F[0]}  {self._t}"); self._tick()
    def stop(self):  self._run=False; self.configure(text="")
    def _tick(self):
        if self._run: self._i=(self._i+1)%8; self.configure(text=f"{self._F[self._i]}  {self._t}"); self.after(120,self._tick)

class Page(ctk.CTkScrollableFrame):
    def __init__(self,p,**kw):
        kw.setdefault("fg_color",C["bg"])
        kw.setdefault("scrollbar_button_color",C["card"])
        kw.setdefault("scrollbar_button_hover_color",C["primary"])
        super().__init__(p,**kw)
        self._api=API_M()

    def async_call(self,fn,*a,cb=None):
        def _w():
            r=fn(*a)
            if cb: _G_Q.put((cb,r))
        threading.Thread(target=_w,daemon=True).start()

    def page_hdr(self,icon,title,sub=""):
        f=ctk.CTkFrame(self,fg_color="transparent"); f.pack(fill="x",padx=24,pady=(20,8))
        ctk.CTkLabel(f,text=f"{icon}  {title}",font=ctk.CTkFont("Segoe UI",24,"bold"),text_color=C["t1"]).pack(anchor="w")
        if sub: ctk.CTkLabel(f,text=sub,font=ctk.CTkFont("Segoe UI",13),text_color=C["t2"]).pack(anchor="w",pady=(2,0))
        ctk.CTkFrame(self,height=1,fg_color=C["border"]).pack(fill="x",padx=24,pady=(6,14))

    def mk_btn(self,p,text,cmd,primary=True,**kw):
        kw.setdefault("height",38); kw.setdefault("corner_radius",8)
        kw.setdefault("font",ctk.CTkFont("Segoe UI",13))
        fg=C["pbtn"] if primary else C["card"]
        hv=C["hl"] if primary else C["border"]
        return ctk.CTkButton(p,text=text,command=cmd,fg_color=fg,hover_color=hv,text_color=C["t1"],**kw)

    def mk_entry(self,p,ph,**kw):
        kw.setdefault("height",40); kw.setdefault("corner_radius",8)
        kw.setdefault("font",ctk.CTkFont("Segoe UI",13))
        kw.setdefault("fg_color",C["card"]); kw.setdefault("border_color",C["border"])
        kw.setdefault("text_color",C["t1"]); kw.setdefault("placeholder_text_color",C["t3"])
        return ctk.CTkEntry(p,placeholder_text=ph,**kw)

    def open_map(self,lat,lon,name="",zoom=13):
        m=folium.Map(location=[lat,lon],zoom_start=zoom,tiles="CartoDB dark_matter")
        folium.Marker([lat,lon],
            popup=folium.Popup(f"<b>{name}</b><br>📍 {lat:.5f}, {lon:.5f}",max_width=220),
            icon=folium.Icon(color="blue",icon="map-marker",prefix="fa")).add_to(m)
        p, fname = tmp_map(); m.save(p); webbrowser.open(f"http://localhost:{_G_PORT}/gv_maps/{fname}")

    def export_geojson(self, data, filename_hint="geovista_export"):
        """Exports a list of (lat, lon, label) tuples or a single dict to GeoJSON."""
        path = filedialog.asksaveasfilename(defaultextension=".geojson",
                                              filetypes=[("GeoJSON files", "*.geojson")],
                                              initialfile=f"{filename_hint}.geojson")
        if not path: return
        try:
            features = []
            if isinstance(data, list):
                for la, lo, lb in data:
                    features.append({
                        "type": "Feature",
                        "geometry": {"type": "Point", "coordinates": [lo, la]},
                        "properties": {"name": lb}
                    })
            else:
                features.append({
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [data['lon'], data['lat']]},
                    "properties": data.get('props', {})
                })

            gj = {"type": "FeatureCollection", "features": features}
            with open(path, "w", encoding="utf-8") as f:
                json.dump(gj, f, indent=2, ensure_ascii=False)
            messagebox.showinfo("Başarılı", f"Veri dışa aktarıldı:\n{os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Hata", f"Dışa aktarma başarısız: {e}")

class DashboardPage(Page):
    def __init__(self,p,app,**kw):
        super().__init__(p,**kw); self._app=app; self._build(); self._load_ip()

    def _build(self):
        self.page_hdr("🏠","Ana Sayfa","Merhaba! GeoVista CBS Asistanına hoş geldiniz 🌍")

        sf=ctk.CTkFrame(self,fg_color="transparent"); sf.pack(fill="x",padx=24,pady=(0,16))
        sf.columnconfigure((0,1,2,3),weight=1,uniform="s")
        stats=[("🌍","Dünya Ülkeleri","195",C["primary"]),
               ("🏙️","Büyük Şehirler","10 000+",C["sec"]),
               ("🌊","Dünya Okyanusu","5",C["warn"]),
               ("⛰️","8000m+ Zirve","14",C["accent"])]
        for i,(ic,lb,vl,co) in enumerate(stats):
            Stat(sf,ic,lb,vl,co).grid(row=0,column=i,padx=6,pady=6,sticky="nsew")

        r2=ctk.CTkFrame(self,fg_color="transparent"); r2.pack(fill="x",padx=24,pady=(0,16))
        r2.columnconfigure(0,weight=1); r2.columnconfigure(1,weight=1)
        self.loc_card=Card(r2,title="📍 Mevcut Konumunuz (IP Tabanlı)")
        self.loc_card.grid(row=0,column=0,padx=(0,8),sticky="nsew")
        self.spin=Spinner(self.loc_card,"Konum tespit ediliyor...")
        self.spin.pack(padx=16,pady=10,anchor="w"); self.spin.start()
        self.loc_inner=ctk.CTkFrame(self.loc_card,fg_color="transparent")

        tc=Card(r2,title="⚡ Hızlı Araçlar"); tc.grid(row=0,column=1,padx=(8,0),sticky="nsew")
        for txt,pg in [("🔍 Adres Ara","geocoding"),("🌐 Ülke Bilgisi","countries"),
                       ("📐 Mesafe Hesapla","tools"),("🌡️ Hava Durumu","weather"),
                       ("⛰️ Yükseklik Sor","elevation"),("🗺️ Harita Oluştur","map")]:
            b=ctk.CTkButton(tc,text=txt,fg_color=C["card2"],hover_color=C["pbtn"],
                            text_color=C["t1"],anchor="w",height=36,corner_radius=8,
                            font=ctk.CTkFont("Segoe UI",13))
            b.configure(command=lambda p=pg:self._app.show(p)); b.pack(fill="x",padx=12,pady=3)

        cc=Card(self,title="📚 CBS Nedir?"); cc.pack(fill="x",padx=24,pady=(0,16))
        ctk.CTkLabel(cc,text="Coğrafi Bilgi Sistemi (CBS/GIS), mekânsal verileri toplamak, depolamak, analiz etmek "
                    "ve görselleştirmek için kullanılan bir bilgisayar sistemidir. Kentsel planlama, çevre yönetimi, "
                    "afet yönetimi, tarım, sağlık coğrafyası ve daha pek çok alanda kullanılmaktadır.",
                    font=ctk.CTkFont("Segoe UI",12),text_color=C["t2"],wraplength=900,
                    justify="left",anchor="w").pack(padx=16,pady=(0,14),fill="x")

        kc=Card(self,title="📖 Temel CBS Kavramları"); kc.pack(fill="x",padx=24,pady=(0,20))
        terms=[("📍","Koordinat Sistemi","Yeryüzündeki konumları sayısal olarak tanımlayan sistem (Enlem/Boylam, UTM vb.)."),
               ("📊","Projeksiyon","3-boyutlu Dünya yüzeyini 2-boyutlu haritaya dönüştürme yöntemi."),
               ("🗃️","Vektör Veri","Nokta, çizgi ve poligon olarak temsil edilen coğrafi nesneler."),
               ("🖼️","Raster Veri","Izgara (piksel) yapısında saklanan coğrafi bilgi — uydu görüntüleri gibi."),
               ("🔗","Topoloji","Coğrafi nesneler arasındaki uzamsal ilişkiler: komşuluk, bağlantı vb."),
               ("📡","Uzaktan Algılama","Uydu veya hava araçlarıyla yeryüzü hakkında veri toplama yöntemi.")]
        for ic,nm,ds in terms:
            row=ctk.CTkFrame(kc,fg_color=C["card2"],corner_radius=8); row.pack(fill="x",padx=12,pady=4)
            ctk.CTkLabel(row,text=ic,font=ctk.CTkFont(size=18)).pack(side="left",padx=(12,8),pady=10)
            tf=ctk.CTkFrame(row,fg_color="transparent"); tf.pack(side="left",fill="both",expand=True,pady=8)
            ctk.CTkLabel(tf,text=nm,font=ctk.CTkFont("Segoe UI",12,"bold"),text_color=C["primary"],anchor="w").pack(anchor="w")
            ctk.CTkLabel(tf,text=ds,font=ctk.CTkFont("Segoe UI",11),text_color=C["t2"],anchor="w",wraplength=800).pack(anchor="w")

    def _load_ip(self):
        def _cb(d):
            self.spin.stop(); self.spin.pack_forget()
            if d.get("status")=="success":
                self.loc_inner.pack(fill="x",padx=16,pady=(0,12))
                for ic,k,v in [("🌆","Şehir",d.get("city","-")),("🏛️","Bölge",d.get("regionName","-")),
                                ("🌍","Ülke",d.get("country","-")),("🌐","IP",d.get("query","-")),
                                ("🕐","Saat Dilimi",d.get("timezone","-")),("📡","ISP",d.get("isp","-"))]:
                    IRow(self.loc_inner,k,v,icon=ic).pack(fill="x",pady=2)
                lat,lon=d.get("lat"),d.get("lon")
                if lat and lon:
                    self.mk_btn(self.loc_card,"🗺️ Haritada Göster",
                                lambda:self.open_map(lat,lon,d.get("city","Konumunuz"))).pack(padx=16,pady=(0,12),anchor="w")
            else:
                ctk.CTkLabel(self.loc_card,text="⚠️ Konum tespit edilemedi",
                             text_color=C["warn"],font=ctk.CTkFont("Segoe UI",12)).pack(padx=16,pady=8)
        self.async_call(self._api.ip_loc,cb=_cb)

class GeocodingPage(Page):
    def __init__(self,p,**kw):
        super().__init__(p,**kw); self._build()

    def _build(self):
        self.page_hdr("🔍","Coğrafi Kodlama","Adres → Koordinat ve Koordinat → Adres dönüşümü")
        tabs=ctk.CTkTabview(self,fg_color=C["card"],corner_radius=12,
                            segmented_button_fg_color=C["card2"],
                            segmented_button_selected_color=C["pbtn"],
                            segmented_button_selected_hover_color=C["hl"],
                            text_color=C["t1"])
        tabs.pack(fill="both",padx=24,pady=(0,20),expand=True)
        t1=tabs.add("📍 İleri Kodlama (Adres → Koordinat)")
        t2=tabs.add("🔄 Ters Kodlama (Koordinat → Adres)")
        fi=ctk.CTkFrame(t1,fg_color=C["card2"],corner_radius=10); fi.pack(fill="x",padx=12,pady=14)
        ctk.CTkLabel(fi,text="Adres veya Yer Adı:",font=ctk.CTkFont("Segoe UI",13,"bold"),
                     text_color=C["t1"]).pack(padx=14,pady=(12,6),anchor="w")
        self.fe=self.mk_entry(fi,"Örn: Eyfel Kulesi, Paris   veya   Ankara, Türkiye")
        self.fe.pack(fill="x",padx=14,pady=(0,8)); self.fe.bind("<Return>",lambda e:self._fwd())
        br=ctk.CTkFrame(fi,fg_color="transparent"); br.pack(fill="x",padx=14,pady=(0,12))
        self.mk_btn(br,"🔍  Ara",self._fwd).pack(side="left",padx=(0,8))
        self.mk_btn(br,"🧹  Temizle",self._clr_f,primary=False).pack(side="left")
        self.fsp=Spinner(fi); self.fsp.pack(padx=14,pady=(0,8),anchor="w")
        self.fres=ctk.CTkScrollableFrame(t1,fg_color="transparent",height=380)
        self.fres.pack(fill="both",padx=12,expand=True)
        ri=ctk.CTkFrame(t2,fg_color=C["card2"],corner_radius=10); ri.pack(fill="x",padx=12,pady=14)
        ctk.CTkLabel(ri,text="Koordinatlar:",font=ctk.CTkFont("Segoe UI",13,"bold"),
                     text_color=C["t1"]).pack(padx=14,pady=(12,6),anchor="w")
        cr=ctk.CTkFrame(ri,fg_color="transparent"); cr.pack(fill="x",padx=14,pady=(0,8))
        ctk.CTkLabel(cr,text="Enlem:",text_color=C["t2"],font=ctk.CTkFont("Segoe UI",12)).pack(side="left")
        self.rlat=self.mk_entry(cr,"Örn: 41.0082",width=160); self.rlat.pack(side="left",padx=(8,18))
        ctk.CTkLabel(cr,text="Boylam:",text_color=C["t2"],font=ctk.CTkFont("Segoe UI",12)).pack(side="left")
        self.rlon=self.mk_entry(cr,"Örn: 28.9784",width=160); self.rlon.pack(side="left",padx=8)
        rb=ctk.CTkFrame(ri,fg_color="transparent"); rb.pack(fill="x",padx=14,pady=(0,12))
        self.mk_btn(rb,"🔄  Ters Kodla",self._rev).pack(side="left",padx=(0,8))
        self.mk_btn(rb,"🧹  Temizle",self._clr_r,primary=False).pack(side="left")
        self.rsp=Spinner(ri); self.rsp.pack(padx=14,pady=(0,8),anchor="w")
        self.rres=ctk.CTkFrame(t2,fg_color="transparent"); self.rres.pack(fill="both",padx=12,expand=True)

    def _fwd(self):
        q=self.fe.get().strip()
        if not q: return
        for w in self.fres.winfo_children(): w.destroy()
        self.fsp.start()
        def _cb(data):
            self.fsp.stop()
            if isinstance(data,dict) and "error" in data:
                ctk.CTkLabel(self.fres,text=f"❌ {data['error']}",text_color=C["accent"]).pack(pady=8,anchor="w"); return
            if not data:
                ctk.CTkLabel(self.fres,text="❌ Sonuç bulunamadı.",text_color=C["accent"],
                             font=ctk.CTkFont("Segoe UI",13)).pack(pady=8,anchor="w"); return
            ctk.CTkLabel(self.fres,text=f"✅ {len(data)} sonuç:",
                         font=ctk.CTkFont("Segoe UI",12,"bold"),text_color=C["success"]).pack(pady=(8,4),anchor="w")
            for res in data:
                lat,lon=float(res.get("lat",0)),float(res.get("lon",0))
                c=Card(self.fres); c.pack(fill="x",pady=5)
                ctk.CTkLabel(c,text=res.get("display_name","")[:100],
                             font=ctk.CTkFont("Segoe UI",12,"bold"),text_color=C["t1"],
                             anchor="w",wraplength=700).pack(padx=14,pady=(10,6),fill="x")
                d2=ctk.CTkFrame(c,fg_color=C["card2"],corner_radius=8); d2.pack(fill="x",padx=14,pady=(0,6))
                for k,v in [("📍 Enlem",f"{lat:.6f}°"),("📍 Boylam",f"{lon:.6f}°"),
                            ("🏷️ Tür",res.get("type","-").capitalize()),("📊 Sınıf",res.get("class","-"))]:
                    IRow(d2,k,v).pack(fill="x",padx=12,pady=2)
                br=ctk.CTkFrame(c,fg_color="transparent"); br.pack(fill="x",padx=14,pady=(0,10))
                self.mk_btn(br,"🗺️ Haritada Göster",
                            lambda la=lat,lo=lon,n=res.get("display_name","")[:50]:self.open_map(la,lo,n),
                            height=30,corner_radius=6,font=ctk.CTkFont("Segoe UI",11)).pack(side="left",padx=(0,8))
                self.mk_btn(br,"📋 Koordinatları Kopyala",
                            lambda la=lat,lo=lon:(self.clipboard_clear(),self.clipboard_append(f"{la}, {lo}")),
                            primary=False,height=30,corner_radius=6,font=ctk.CTkFont("Segoe UI",11)).pack(side="left",padx=(0,8))
                self.mk_btn(br,"💠 GeoJSON",
                            lambda la=lat,lo=lon,n=res.get("display_name","")[:30]:self.export_geojson({'lat':la,'lon':lo,'props':{'name':n}}, f"coord_{n[:10]}"),
                            primary=False,height=30,corner_radius=6,font=ctk.CTkFont("Segoe UI",11)).pack(side="left")
        self.async_call(self._api.geocode,q,cb=_cb)

    def _rev(self):
        try: lat,lon=float(self.rlat.get()),float(self.rlon.get())
        except: ctk.CTkLabel(self.rres,text="❌ Geçersiz koordinat!",text_color=C["accent"]).pack(pady=8,anchor="w"); return
        for w in self.rres.winfo_children(): w.destroy()
        self.rsp.start()
        def _cb(d):
            self.rsp.stop()
            if "error" in d:
                ctk.CTkLabel(self.rres,text=f"❌ {d['error']}",text_color=C["accent"]).pack(pady=8,anchor="w"); return
            c=Card(self.rres,title="📍 Bulunan Adres"); c.pack(fill="x",pady=8)
            ctk.CTkLabel(c,text=d.get("display_name",""),font=ctk.CTkFont("Segoe UI",12),
                         text_color=C["t1"],wraplength=780,anchor="w").pack(padx=14,pady=(0,8),fill="x")
            ad=d.get("address",{})
            df=ctk.CTkFrame(c,fg_color=C["card2"],corner_radius=8); df.pack(fill="x",padx=14,pady=(0,8))
            for k,v in [("Sokak/Cadde",ad.get("road",ad.get("street","-"))),
                        ("Mahalle/İlçe",ad.get("suburb",ad.get("neighbourhood","-"))),
                        ("Şehir",ad.get("city",ad.get("town",ad.get("village","-")))),
                        ("İl",ad.get("state","-")),("Ülke",ad.get("country","-")),
                        ("Posta Kodu",ad.get("postcode","-"))]:
                if v and v!="-": IRow(df,k,v).pack(fill="x",padx=12,pady=2)
            self.mk_btn(c,"🗺️ Haritada Göster",lambda:self.open_map(lat,lon,d.get("display_name","")[:50]),
                        height=30,corner_radius=6,font=ctk.CTkFont("Segoe UI",11)).pack(padx=14,pady=(0,12),anchor="w")
        self.async_call(self._api.reverse,lat,lon,cb=_cb)

    def _clr_f(self):
        self.fe.delete(0,"end")
        for w in self.fres.winfo_children(): w.destroy()

    def _clr_r(self):
        self.rlat.delete(0,"end"); self.rlon.delete(0,"end")
        for w in self.rres.winfo_children(): w.destroy()

class MapPage(Page):
    def __init__(self,p,**kw):
        super().__init__(p,**kw); self._markers=[]; self._build()

    def _build(self):
        self.page_hdr("🗺️","İnteraktif Harita","Özel haritalar oluştur, işaretleyiciler ekle ve tarayıcıda görüntüle")

        cc=Card(self,"⚙️ Harita Ayarları"); cc.pack(fill="x",padx=24,pady=(0,14))
        r1=ctk.CTkFrame(cc,fg_color="transparent"); r1.pack(fill="x",padx=14,pady=(0,8))
        ctk.CTkLabel(r1,text="Harita Stili:",text_color=C["t2"],font=ctk.CTkFont("Segoe UI",12)).pack(side="left")
        self.tile=ctk.CTkComboBox(r1,values=["CartoDB dark_matter","OpenStreetMap","ESRI World Imagery (HD)","NASA Blue Marble","NASA Night Lights","Satellite Hybrid"],
                                   width=240,fg_color=C["card"],border_color=C["border"],text_color=C["t1"],
                                   button_color=C["pbtn"],dropdown_fg_color=C["card"],dropdown_text_color=C["t1"],
                                   font=ctk.CTkFont("Segoe UI",12))
        self.tile.pack(side="left",padx=(10,20))
        ctk.CTkLabel(r1,text="Yakınlaştırma (1-18):",text_color=C["t2"],font=ctk.CTkFont("Segoe UI",12)).pack(side="left")
        self.zoom=self.mk_entry(r1,"12",width=70); self.zoom.pack(side="left",padx=(8,0))

        mc=Card(self,"📍 İşaretleyici Ekle"); mc.pack(fill="x",padx=24,pady=(0,14))
        mr=ctk.CTkFrame(mc,fg_color="transparent"); mr.pack(fill="x",padx=14,pady=(0,8))
        ctk.CTkLabel(mr,text="Enlem:",text_color=C["t2"],font=ctk.CTkFont("Segoe UI",12)).pack(side="left")
        self.mlat=self.mk_entry(mr,"Örn: 41.0082",width=140); self.mlat.pack(side="left",padx=(8,16))
        ctk.CTkLabel(mr,text="Boylam:",text_color=C["t2"],font=ctk.CTkFont("Segoe UI",12)).pack(side="left")
        self.mlon=self.mk_entry(mr,"Örn: 28.9784",width=140); self.mlon.pack(side="left",padx=(8,16))
        ctk.CTkLabel(mr,text="Etiket:",text_color=C["t2"],font=ctk.CTkFont("Segoe UI",12)).pack(side="left")
        self.mlbl=self.mk_entry(mr,"Yer adı...",width=180); self.mlbl.pack(side="left",padx=8)
        br=ctk.CTkFrame(mc,fg_color="transparent"); br.pack(fill="x",padx=14,pady=(0,12))
        self.mk_btn(br,"➕ Ekle",self._add_marker).pack(side="left",padx=(0,8))
        self.mk_btn(br,"🗑️ Tümünü Sil",self._clr_markers,primary=False).pack(side="left",padx=(0,8))
        self.mk_btn(br,"🌍 Haritayı Aç",self._open,primary=True).pack(side="left")

        self.mlist_card=Card(self,"📋 İşaretleyiciler"); self.mlist_card.pack(fill="x",padx=24,pady=(0,14))
        self.mlist=ctk.CTkFrame(self.mlist_card,fg_color="transparent"); self.mlist.pack(fill="x",padx=14,pady=(0,12))
        ctk.CTkLabel(self.mlist,text="Henüz işaretleyici eklenmedi.",text_color=C["t3"],
                     font=ctk.CTkFont("Segoe UI",12)).pack(anchor="w",pady=4)

        pc=Card(self,"⭐ Hazır Konumlar"); pc.pack(fill="x",padx=24,pady=(0,20))
        presets=[("🇹🇷 Ankara",39.9334,32.8597),("🗼 Eyfel Kulesi",48.8584,2.2945),
                 ("🏔️ Everest",27.9881,86.9250),("🗽 Özgürlük Heykeli",40.6892,-74.0445),
                 ("🏛️ Atina Akropolü",37.9715,23.7267),("🌋 Fuji Dağı",35.3606,138.7274)]
        pg=ctk.CTkFrame(pc,fg_color="transparent"); pg.pack(fill="x",padx=14,pady=(0,12))
        pg.columnconfigure((0,1,2),weight=1,uniform="p")
        for i,(nm,la,lo) in enumerate(presets):
            ctk.CTkButton(pg,text=nm,fg_color=C["card2"],hover_color=C["pbtn"],text_color=C["t1"],
                          corner_radius=8,height=36,font=ctk.CTkFont("Segoe UI",12),
                          command=lambda la=la,lo=lo,nm=nm:(self.mlat.delete(0,"end"),self.mlat.insert(0,str(la)),
                                                            self.mlon.delete(0,"end"),self.mlon.insert(0,str(lo)),
                                                            self.mlbl.delete(0,"end"),self.mlbl.insert(0,nm))
                          ).grid(row=i//3,column=i%3,padx=5,pady=4,sticky="nsew")

    def _add_marker(self):
        try: lat,lon=float(self.mlat.get()),float(self.mlon.get())
        except: return
        lbl=self.mlbl.get().strip() or f"{lat:.4f},{lon:.4f}"
        self._markers.append((lat,lon,lbl))
        for w in self.mlist.winfo_children(): w.destroy()
        for i,(la,lo,lb) in enumerate(self._markers):
            row=ctk.CTkFrame(self.mlist,fg_color=C["card2"],corner_radius=8); row.pack(fill="x",pady=3)
            ctk.CTkLabel(row,text=f"📍 {lb}  ({la:.4f}, {lo:.4f})",
                         font=ctk.CTkFont("Segoe UI",12),text_color=C["t1"]).pack(side="left",padx=12,pady=8)
        self.mlat.delete(0,"end"); self.mlon.delete(0,"end"); self.mlbl.delete(0,"end")

    def _clr_markers(self):
        self._markers.clear()
        for w in self.mlist.winfo_children(): w.destroy()
        ctk.CTkLabel(self.mlist,text="Henüz işaretleyici eklenmedi.",text_color=C["t3"],
                     font=ctk.CTkFont("Segoe UI",12)).pack(anchor="w",pady=4)

    def _open(self):
        try: z=int(self.zoom.get())
        except: z=12
        tile=self.tile.get()

        wms = None
        if tile == "NASA Blue Marble":
            # NASA GIBS REST API - En stabil XYZ formatı
            tile = "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/BlueMarble_ShadedRelief_Bathymetry/default/default/GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpg"
            attr = "NASA GIBS"
        elif tile == "NASA Night Lights":
            tile = "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/VIIRS_CityLights_2012/default/2013-12-01/GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpg"
            attr = "NASA GIBS"
        elif tile == "ESRI World Imagery (HD)":
            tile = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
            attr = "Esri Satellite"
        elif tile == "Satellite Hybrid":
            tile = "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}"
            attr = "Google Maps"
        else:
            attr = None

        center=[self._markers[0][0],self._markers[0][1]] if self._markers else [39.9334,32.8597]
        
        # NASA Zoom Sınırlandırması
        if "NASA" in tile:
            if z > 8: z = 8 # NASA GIBS 250m max zoom is 8-9
            
        m=folium.Map(location=center,zoom_start=z,tiles=tile,attr=attr)
        colors=["blue","red","green","purple","orange","darkblue","pink"]
        for i,(la,lo,lb) in enumerate(self._markers):
            folium.Marker([la,lo],popup=folium.Popup(f"<b>{lb}</b><br>{la:.5f}, {lo:.5f}",max_width=220),
                          tooltip=lb,icon=folium.Icon(color=colors[i%len(colors)],icon="map-marker",prefix="fa")).add_to(m)
        p, fname = tmp_map(); m.save(p); webbrowser.open(f"http://localhost:{_G_PORT}/gv_maps/{fname}")

class CountriesPage(Page):
    def __init__(self,p,**kw):
        super().__init__(p,**kw); self._build()

    def _build(self):
        self.page_hdr("🌐","Ülke Bilgileri","Herhangi bir ülke hakkında detaylı bilgi al")
        si=ctk.CTkFrame(self,fg_color=C["card2"],corner_radius=10); si.pack(fill="x",padx=24,pady=(0,14))
        ctk.CTkLabel(si,text="Ülke Adı:",font=ctk.CTkFont("Segoe UI",13,"bold"),text_color=C["t1"]).pack(padx=14,pady=(12,6),anchor="w")
        self.ce=self.mk_entry(si,"Örn: Germany, France, Türkiye, Japan...")
        self.ce.pack(fill="x",padx=14,pady=(0,8)); self.ce.bind("<Return>",lambda e:self._search())
        br=ctk.CTkFrame(si,fg_color="transparent"); br.pack(fill="x",padx=14,pady=(0,12))
        self.mk_btn(br,"🔍  Ara",self._search).pack(side="left",padx=(0,8))
        self.mk_btn(br,"🧹  Temizle",self._clr,primary=False).pack(side="left")
        self.csp=Spinner(si); self.csp.pack(padx=14,pady=(0,8),anchor="w")

        qc=Card(self,"⭐ Hızlı Ülke Seç"); qc.pack(fill="x",padx=24,pady=(0,14))
        qf=ctk.CTkFrame(qc,fg_color="transparent"); qf.pack(fill="x",padx=14,pady=(0,12))
        qf.columnconfigure((0,1,2,3,4),weight=1,uniform="q")
        for i,(fl,nm) in enumerate([("🇹🇷","Turkey"),("🇩🇪","Germany"),("🇺🇸","United States"),
                                    ("🇯🇵","Japan"),("🇫🇷","France"),("🇧🇷","Brazil"),
                                    ("🇨🇳","China"),("🇮🇳","India"),("🇷🇺","Russia"),("🇬🇧","United Kingdom")]):
            ctk.CTkButton(qf,text=f"{fl} {nm}",fg_color=C["card2"],hover_color=C["pbtn"],
                          text_color=C["t1"],corner_radius=8,height=34,font=ctk.CTkFont("Segoe UI",11),
                          command=lambda n=nm:(self.ce.delete(0,"end"),self.ce.insert(0,n),self._search())
                          ).grid(row=i//5,column=i%5,padx=4,pady=3,sticky="nsew")
        self.cres=ctk.CTkFrame(self,fg_color="transparent"); self.cres.pack(fill="both",padx=24,expand=True)

    def _search(self):
        q=self.ce.get().strip()
        if not q: return
        for w in self.cres.winfo_children(): w.destroy()
        self.csp.start()
        def _cb(data):
            self.csp.stop()
            if isinstance(data,dict) and "error" in data:
                ctk.CTkLabel(self.cres,text=f"❌ {data['error']}",text_color=C["accent"]).pack(pady=8,anchor="w"); return
            if isinstance(data,dict) and "status" in data:
                ctk.CTkLabel(self.cres,text="❌ Ülke bulunamadı.",text_color=C["accent"]).pack(pady=8,anchor="w"); return
            for c in data[:3]:
                card=Card(self.cres); card.pack(fill="x",pady=8)

                hf=ctk.CTkFrame(card,fg_color="transparent"); hf.pack(fill="x",padx=14,pady=(10,8))
                nm=c.get("name",{}).get("common","?")
                fl=c.get("flag","")
                ctk.CTkLabel(hf,text=f"{fl}  {nm}",font=ctk.CTkFont("Segoe UI",20,"bold"),text_color=C["t1"]).pack(side="left")
                region=c.get("region","")
                ctk.CTkLabel(hf,text=region,font=ctk.CTkFont("Segoe UI",12),text_color=C["t2"]).pack(side="left",padx=12)

                df=ctk.CTkFrame(card,fg_color=C["card2"],corner_radius=8); df.pack(fill="x",padx=14,pady=(0,8))
                df.columnconfigure((0,1),weight=1,uniform="d")
                left=ctk.CTkFrame(df,fg_color="transparent"); left.grid(row=0,column=0,padx=12,pady=8,sticky="nsew")
                right=ctk.CTkFrame(df,fg_color="transparent"); right.grid(row=0,column=1,padx=12,pady=8,sticky="nsew")
                cap=c.get("capital",["?"]); cap=cap[0] if cap else "-"
                pop=c.get("population",0)
                area=c.get("area",0)
                langs=", ".join(c.get("languages",{}).values()) if c.get("languages") else "-"
                curr=", ".join([f"{v.get('name',k)} ({v.get('symbol','')})" for k,v in c.get("currencies",{}).items()]) if c.get("currencies") else "-"
                latlng=c.get("latlng",["-","-"])
                borders=", ".join(c.get("borders",[]))
                cont=", ".join(c.get("continents",[]))
                for k,v in [("🏛️ Başkent",cap),("👥 Nüfus",f"{pop:,}"),("📐 Alan",f"{area:,.0f} km²"),("🌍 Kıta",cont)]:
                    IRow(left,k,v).pack(fill="x",pady=2)
                for k,v in [("💬 Diller",langs[:60]),("💰 Para Birimi",curr[:60]),
                            ("📍 Koord.",f"{latlng[0]:.2f}°, {latlng[1]:.2f}°" if len(latlng)>=2 else "-"),
                            ("🤝 Sınırlar",borders[:50] or "Yok")]:
                    IRow(right,k,v).pack(fill="x",pady=2)

                if len(latlng)>=2:
                    self.mk_btn(card,"🗺️ Haritada Göster",
                                lambda la=float(latlng[0]),lo=float(latlng[1]),n=nm:self.open_map(la,lo,n,zoom=5),
                                height=30,corner_radius=6,font=ctk.CTkFont("Segoe UI",11)).pack(padx=14,pady=(0,12),anchor="w")
        self.async_call(self._api.country,q,cb=_cb)

    def _clr(self):
        self.ce.delete(0,"end")
        for w in self.cres.winfo_children(): w.destroy()

class CoordToolsPage(Page):
    def __init__(self,p,**kw):
        super().__init__(p,**kw); self._build()

    def _build(self):
        self.page_hdr("📐","Koordinat Araçları","Mesafe, yön, dönüşüm ve orta nokta hesaplamaları")
        tabs=ctk.CTkTabview(self,fg_color=C["card"],corner_radius=12,
                            segmented_button_fg_color=C["card2"],segmented_button_selected_color=C["pbtn"],
                            segmented_button_selected_hover_color=C["hl"],text_color=C["t1"])
        tabs.pack(fill="both",padx=24,pady=(0,20),expand=True)
        t1=tabs.add("📏 Mesafe & Yön"); t2=tabs.add("🔢 DD ↔ DMS"); t3=tabs.add("📍 Orta Nokta"); t4=tabs.add("📐 UTM Dönüşümü")

        def _two_point_input(parent):
            for lbl,ab in [("📍 Nokta A","a"),("📍 Nokta B","b")]:
                r=ctk.CTkFrame(parent,fg_color=C["card2"],corner_radius=8); r.pack(fill="x",pady=5)
                ctk.CTkLabel(r,text=lbl,font=ctk.CTkFont("Segoe UI",12,"bold"),text_color=C["primary"]).pack(padx=12,pady=(8,4),anchor="w")
                row=ctk.CTkFrame(r,fg_color="transparent"); row.pack(fill="x",padx=12,pady=(0,10))
                ctk.CTkLabel(row,text="Enlem:",text_color=C["t2"],font=ctk.CTkFont("Segoe UI",12)).pack(side="left")
                lat=self.mk_entry(row,f"{lbl} enlem",width=140); lat.pack(side="left",padx=(8,16))
                ctk.CTkLabel(row,text="Boylam:",text_color=C["t2"],font=ctk.CTkFont("Segoe UI",12)).pack(side="left")
                lon=self.mk_entry(row,f"{lbl} boylam",width=140); lon.pack(side="left",padx=8)
                if ab=="a": self.d_alat,self.d_alon=lat,lon
                else: self.d_blat,self.d_blon=lat,lon
        _two_point_input(t1)
        br=ctk.CTkFrame(t1,fg_color="transparent"); br.pack(fill="x",pady=8)
        self.mk_btn(br,"📏  Hesapla",self._calc_dist).pack(side="left",padx=(0,8))
        self.mk_btn(br,"🧹  Temizle",lambda:(self.d_alat.delete(0,"end"),self.d_alon.delete(0,"end"),
                                            self.d_blat.delete(0,"end"),self.d_blon.delete(0,"end"),
                                            [w.destroy() for w in self.dist_res.winfo_children()]),primary=False).pack(side="left")
        self.dist_res=ctk.CTkFrame(t1,fg_color="transparent"); self.dist_res.pack(fill="x",pady=8)

        sub2=ctk.CTkTabview(t2,fg_color=C["card2"],corner_radius=10,
                            segmented_button_fg_color=C["card"],segmented_button_selected_color=C["pbtn"],
                            segmented_button_selected_hover_color=C["hl"],text_color=C["t1"])
        sub2.pack(fill="x",pady=6)
        s2a=sub2.add("DD → DMS"); s2b=sub2.add("DMS → DD")
        ctk.CTkLabel(s2a,text="Ondalık Derece:",text_color=C["t2"],font=ctk.CTkFont("Segoe UI",12)).pack(anchor="w",padx=12,pady=(10,4))
        self.dd_in=self.mk_entry(s2a,"Örn: 41.0082",width=200); self.dd_in.pack(padx=12,pady=(0,8),anchor="w")
        self.mk_btn(s2a,"🔄 Dönüştür",self._dd2dms).pack(padx=12,pady=(0,8),anchor="w")
        self.dms_out=ctk.CTkLabel(s2a,text="",font=ctk.CTkFont("Segoe UI",14,"bold"),text_color=C["success"])
        self.dms_out.pack(padx=12,pady=(0,12),anchor="w")
        row2=ctk.CTkFrame(s2b,fg_color="transparent"); row2.pack(fill="x",padx=12,pady=(10,4))
        for lbl,attr in [("Derece°","dms_d"),("Dakika'","dms_m"),("Saniye\"","dms_s")]:
            ctk.CTkLabel(row2,text=lbl,text_color=C["t2"],font=ctk.CTkFont("Segoe UI",12)).pack(side="left")
            e=self.mk_entry(row2,"0",width=80); e.pack(side="left",padx=(6,14)); setattr(self,attr,e)
        self.dms_hem=ctk.CTkComboBox(s2b,values=["N","S","E","W"],width=80,fg_color=C["card"],border_color=C["border"],
                                     text_color=C["t1"],button_color=C["pbtn"],dropdown_fg_color=C["card"],dropdown_text_color=C["t1"])
        self.dms_hem.pack(padx=12,pady=(0,8),anchor="w")
        self.mk_btn(s2b,"🔄 Dönüştür",self._dms2dd).pack(padx=12,pady=(0,8),anchor="w")
        self.dd_out=ctk.CTkLabel(s2b,text="",font=ctk.CTkFont("Segoe UI",14,"bold"),text_color=C["success"])
        self.dd_out.pack(padx=12,pady=(0,12),anchor="w")

        def _two_point_input_m(parent):
            for lbl,ab in [("📍 Nokta A","a"),("📍 Nokta B","b")]:
                r=ctk.CTkFrame(parent,fg_color=C["card2"],corner_radius=8); r.pack(fill="x",pady=5)
                ctk.CTkLabel(r,text=lbl,font=ctk.CTkFont("Segoe UI",12,"bold"),text_color=C["primary"]).pack(padx=12,pady=(8,4),anchor="w")
                row=ctk.CTkFrame(r,fg_color="transparent"); row.pack(fill="x",padx=12,pady=(0,10))
                ctk.CTkLabel(row,text="Enlem:",text_color=C["t2"],font=ctk.CTkFont("Segoe UI",12)).pack(side="left")
                lat=self.mk_entry(row,f"{lbl} enlem",width=140); lat.pack(side="left",padx=(8,16))
                ctk.CTkLabel(row,text="Boylam:",text_color=C["t2"],font=ctk.CTkFont("Segoe UI",12)).pack(side="left")
                lon=self.mk_entry(row,f"{lbl} boylam",width=140); lon.pack(side="left",padx=8)
                if ab=="a": self.m_alat,self.m_alon=lat,lon
                else: self.m_blat,self.m_blon=lat,lon
        _two_point_input_m(t3)
        self.mk_btn(t3,"📍  Orta Noktayı Bul",self._calc_mid).pack(pady=8,anchor="w")
        self.mid_res=ctk.CTkFrame(t3,fg_color="transparent"); self.mid_res.pack(fill="x",pady=8)

        ui=ctk.CTkFrame(t4,fg_color=C["card2"],corner_radius=10); ui.pack(fill="x",padx=12,pady=10)
        u_row=ctk.CTkFrame(ui,fg_color="transparent"); u_row.pack(fill="x",padx=12,pady=10)
        ctk.CTkLabel(u_row,text="Easting (Sağa):",text_color=C["t2"]).pack(side="left")
        self.ue=self.mk_entry(u_row,"Örn: 484465",width=130); self.ue.pack(side="left",padx=(8,16))
        ctk.CTkLabel(u_row,text="Northing (Yukarı):",text_color=C["t2"]).pack(side="left")
        self.un=self.mk_entry(u_row,"Örn: 4417614",width=130); self.un.pack(side="left",padx=(8,16))
        ctk.CTkLabel(u_row,text="Zon:",text_color=C["t2"]).pack(side="left")
        self.uz=self.mk_entry(u_row,"35",width=50); self.uz.pack(side="left",padx=(8,0))
        self.uzl=ctk.CTkComboBox(u_row,values=["T","S","R","Q"],width=60); self.uzl.pack(side="left",padx=8)

        ub=ctk.CTkFrame(ui,fg_color="transparent"); ub.pack(fill="x",padx=12,pady=(0,10))
        self.mk_btn(ub,"📐 UTM → WGS84",self._utm2wgs).pack(side="left",padx=(0,8))
        self.mk_btn(ub,"📍 WGS84 → UTM",self._wgs2utm,primary=False).pack(side="left")
        self.utm_res=ctk.CTkLabel(t4,text="",font=ctk.CTkFont("Segoe UI",14,"bold"),text_color=C["success"])
        self.utm_res.pack(padx=12,pady=10,anchor="w")

    def _utm2wgs(self):
        try:
            e, n = float(self.ue.get()), float(self.un.get())
            z, zl = int(self.uz.get()), self.uzl.get()
            lat, lon = utm.to_latlon(e, n, z, zl)
            self.utm_res.configure(text=f"✅ Enlem: {lat:.6f}°, Boylam: {lon:.6f}°")
            self.clipboard_clear(); self.clipboard_append(f"{lat}, {lon}")
        except Exception as ex: self.utm_res.configure(text=f"❌ Hata: {ex}")

    def _wgs2utm(self):
        try:

            lat, lon = float(self.d_alat.get()), float(self.d_alon.get())
            e, n, z, zl = utm.from_latlon(lat, lon)
            self.utm_res.configure(text=f"✅ E: {int(e)}, N: {int(n)}, Zon: {z}{zl}")
            self.ue.delete(0, 'end'); self.ue.insert(0, str(int(e)))
            self.un.delete(0, 'end'); self.un.insert(0, str(int(n)))
            self.uz.delete(0, 'end'); self.uz.insert(0, str(z))
        except Exception as ex: self.utm_res.configure(text="❌ Nokta A koordinatlarını kontrol edin.")

    def _calc_dist(self):
        try:
            la1,lo1=float(self.d_alat.get()),float(self.d_alon.get())
            la2,lo2=float(self.d_blat.get()),float(self.d_blon.get())
        except: return
        dist=haversine(la1,lo1,la2,lo2); brg=bearing(la1,lo1,la2,lo2)
        for w in self.dist_res.winfo_children(): w.destroy()
        rc=Card(self.dist_res,title="📊 Hesaplama Sonuçları"); rc.pack(fill="x",pady=6)
        for k,v in [("📏 Mesafe (km)",f"{dist:.3f} km"),("📏 Mesafe (mil)",f"{dist*0.621371:.3f} mil"),
                    ("📏 Mesafe (deniz mili)",f"{dist*0.539957:.3f} nmi"),
                    ("🧭 Yön Açısı",f"{brg:.2f}° ({brg_label(brg)})"),
                    ("🌍 Nokta A",f"{la1:.5f}°, {lo1:.5f}°"),("🌍 Nokta B",f"{la2:.5f}°, {lo2:.5f}°")]:
            IRow(rc,k,v).pack(fill="x",padx=14,pady=3)
        self.mk_btn(rc,"🗺️ Haritada Göster",lambda:self._dist_map(la1,lo1,la2,lo2),
                    height=30,corner_radius=6,font=ctk.CTkFont("Segoe UI",11)).pack(padx=14,pady=(0,12),anchor="w")

    def _dist_map(self,la1,lo1,la2,lo2):
        clat,clon=(la1+la2)/2,(lo1+lo2)/2
        m=folium.Map(location=[clat,clon],zoom_start=5,tiles="CartoDB dark_matter")
        folium.Marker([la1,lo1],popup="Nokta A",icon=folium.Icon(color="blue",icon="circle",prefix="fa")).add_to(m)
        folium.Marker([la2,lo2],popup="Nokta B",icon=folium.Icon(color="red",icon="circle",prefix="fa")).add_to(m)
        folium.PolyLine([(la1,lo1),(la2,lo2)],color=C["primary"],weight=3,opacity=0.8).add_to(m)
        p, fname = tmp_map(); m.save(p); webbrowser.open(f"http://localhost:{_G_PORT}/gv_maps/{fname}")

    def _dd2dms(self):
        try: dd=float(self.dd_in.get())
        except: self.dms_out.configure(text="❌ Geçersiz değer!"); return
        d,mi,s=dd_to_dms(dd)
        hem="K" if dd>=0 else "G"
        self.dms_out.configure(text=f"{d}° {mi}' {s:.4f}\" {hem}   ({abs(dd):.6f}°)")

    def _dms2dd(self):
        try:
            d=float(self.dms_d.get()); m=float(self.dms_m.get()); s=float(self.dms_s.get())
            hem=self.dms_hem.get()
        except: self.dd_out.configure(text="❌ Geçersiz değer!"); return
        dd=dms_to_dd(d,m,s,hem)
        self.dd_out.configure(text=f"{dd:.6f}°")

    def _calc_mid(self):
        try:
            la1,lo1=float(self.m_alat.get()),float(self.m_alon.get())
            la2,lo2=float(self.m_blat.get()),float(self.m_blon.get())
        except: return
        ml,mlo=midpoint(la1,lo1,la2,lo2)
        for w in self.mid_res.winfo_children(): w.destroy()
        rc=Card(self.mid_res,title="📍 Orta Nokta Sonucu"); rc.pack(fill="x",pady=6)
        for k,v in [("📍 Orta Nokta",f"{ml:.6f}°, {mlo:.6f}°"),
                    ("📏 Toplam Mesafe",f"{haversine(la1,lo1,la2,lo2):.3f} km"),
                    ("📏 Yarı Mesafe",f"{haversine(la1,lo1,la2,lo2)/2:.3f} km")]:
            IRow(rc,k,v).pack(fill="x",padx=14,pady=3)
        self.mk_btn(rc,"🗺️ Haritada Göster",lambda:self.open_map(ml,mlo,"Orta Nokta"),
                    height=30,corner_radius=6,font=ctk.CTkFont("Segoe UI",11)).pack(padx=14,pady=(0,12),anchor="w")

class SpatialLabPage(Page):
    def __init__(self,p,app,**kw):
        super().__init__(p,**kw); self._app=app; self._gdf=None; self._build()

    def _build(self):
        self.page_hdr("🧪","Spatial Lab","Profesyonel Vektör Veri Analizi (GeoPandas)")

        lc=Card(self,"📂 Veri Seti Yükle (Shapefile / GeoJSON)"); lc.pack(fill="x",padx=24,pady=(0,14))
        lr=ctk.CTkFrame(lc,fg_color="transparent"); lr.pack(fill="x",padx=14,pady=(0,12))
        self.mk_btn(lr,"📁 Dosya Seç",self._load_data).pack(side="left",padx=(0,8))
        self.mk_btn(lr,"🧹 Temizle",self._clr,primary=False).pack(side="left")
        self.lsp=Spinner(lc,"Veri işleniyor..."); self.lsp.pack(padx=14,pady=(0,8),anchor="w")

        self.ac=ctk.CTkFrame(self,fg_color="transparent"); self.ac.pack(fill="both",padx=24,expand=True)

    def _load_data(self):
        p=filedialog.askopenfilename(filetypes=[("GIS Files","*.shp *.geojson *.json")])
        if not p: return
        for w in self.ac.winfo_children(): w.destroy()
        self.lsp.start()
        def _job():
            try:
                gdf = gpd.read_file(p)
                if gdf.crs is None: gdf.set_crs("EPSG:4326", inplace=True)
                elif gdf.crs != "EPSG:4326": gdf = gdf.to_crs("EPSG:4326")
                return gdf
            except Exception as e: return {"error":str(e)}

        def _done(res):
            self.lsp.stop()
            if isinstance(res, dict) and "error" in res:
                messagebox.showerror("Hata", f"Veri yüklenemedi: {res['error']}"); return
            self._gdf = res
            self._show_info()

        self.async_call(_job, cb=_done)

    def _show_info(self):
        c=Card(self.ac, title="📊 Veri Seti Özeti"); c.pack(fill="x", pady=8)
        cols = ", ".join(list(self._gdf.columns)[:8])
        for k,v in [("📝 Satır Sayısı", len(self._gdf)), ("🏷 Sütunlar", cols),
                    ("🌐 Geometri Tipi", str(self._gdf.geom_type.unique())),
                    ("🗺 CRS", str(self._gdf.crs))]:
            IRow(c,k,v).pack(fill="x",padx=14,pady=2)

        bc=Card(self.ac, title="⚙️ Vektör Analizleri"); bc.pack(fill="x", pady=8)
        br=ctk.CTkFrame(bc,fg_color="transparent"); br.pack(fill="x",padx=14,pady=(0,12))
        ctk.CTkLabel(br,text="Tampon (Buffer) Metre:",text_color=C["t2"]).pack(side="left")
        self.buf_val=self.mk_entry(br,"500",width=80); self.buf_val.pack(side="left",padx=8)
        self.mk_btn(br,"🔘 Buffer Oluştur",self._run_buffer).pack(side="left",padx=8)
        self.mk_btn(br,"🗺 Haritada Göster",self._view_on_map,primary=False).pack(side="left")

    def _run_buffer(self):
        if self._gdf is None: return
        try: dist = float(self.buf_val.get())
        except: return
        self.lsp.start()
        def _job():

            gdf_m = self._gdf.to_crs("EPSG:3857")
            gdf_m['geometry'] = gdf_m.buffer(dist)
            return gdf_m.to_crs("EPSG:4326")
        def _done(res):
            self.lsp.stop(); self._gdf = res
            messagebox.showinfo("Analiz", f"{dist}m Tampon bölge hesaplandı."); self._show_info()
        self.async_call(_job, cb=_done)

    def _view_on_map(self):
        if self._gdf is None: return
        m = folium.Map(location=[self._gdf.geometry.centroid.y.mean(), self._gdf.geometry.centroid.x.mean()],
                       zoom_start=6, tiles="CartoDB dark_matter")
        folium.GeoJson(self._gdf).add_to(m)
        p = tmp_map(); m.save(p); webbrowser.open(os.path.abspath(p))

    def _clr(self):
        self._gdf = None
        for w in self.ac.winfo_children(): w.destroy()

WX_CODES={0:"☀️ Açık",1:"🌤️ Çoğunlukla Açık",2:"⛅ Parçalı Bulutlu",3:"☁️ Bulutlu",
           45:"🌫️ Sisli",48:"🌫️ Buzlanma Sisi",51:"🌦️ Hafif Çisenti",53:"🌦️ Çisenti",
           55:"🌧️ Yoğun Çisenti",61:"🌧️ Hafif Yağmur",63:"🌧️ Yağmur",65:"🌧️ Şiddetli Yağmur",
           71:"🌨️ Hafif Kar",73:"❄️ Kar",75:"❄️ Yoğun Kar",80:"🌦️ Sağanak",
           81:"⛈️ Kuvvetli Sağanak",82:"⛈️ Çok Kuvvetli Sağanak",95:"⛈️ Fırtına",99:"⛈️ Dolu Fırtınası"}

class WeatherPage(Page):
    def __init__(self,p,**kw):
        super().__init__(p,**kw); self._build()

    def _build(self):
        self.page_hdr("🌡️","Hava & İklim","Open-Meteo & NASA GIBS Otomatize Veri Akışı")
        si=ctk.CTkFrame(self,fg_color=C["card2"],corner_radius=10); si.pack(fill="x",padx=24,pady=(0,14))
        ctk.CTkLabel(si,text="Koordinat Gir:",font=ctk.CTkFont("Segoe UI",13,"bold"),text_color=C["t1"]).pack(padx=14,pady=(12,6),anchor="w")
        cr=ctk.CTkFrame(si,fg_color="transparent"); cr.pack(fill="x",padx=14,pady=(0,8))
        ctk.CTkLabel(cr,text="Enlem:",text_color=C["t2"],font=ctk.CTkFont("Segoe UI",12)).pack(side="left")
        self.wlat=self.mk_entry(cr,"Örn: 41.0082",width=160); self.wlat.pack(side="left",padx=(8,18))
        ctk.CTkLabel(cr,text="Boylam:",text_color=C["t2"],font=ctk.CTkFont("Segoe UI",12)).pack(side="left")
        self.wlon=self.mk_entry(cr,"Örn: 28.9784",width=160); self.wlon.pack(side="left",padx=8)
        br=ctk.CTkFrame(si,fg_color="transparent"); br.pack(fill="x",padx=14,pady=(0,12))
        self.mk_btn(br,"🌡️  Hava Durumunu Al",self._fetch).pack(side="left",padx=(0,8))
        self.mk_btn(br,"📍 IP Konumumu Kullan",self._use_ip,primary=False).pack(side="left")
        self.wsp=Spinner(si); self.wsp.pack(padx=14,pady=(0,8),anchor="w")

        qc=Card(self,"🏙️ Hızlı Şehir Seç"); qc.pack(fill="x",padx=24,pady=(0,14))
        qf=ctk.CTkFrame(qc,fg_color="transparent"); qf.pack(fill="x",padx=14,pady=(0,12))
        qf.columnconfigure((0,1,2,3,4),weight=1,uniform="wq")
        for i,(nm,la,lo) in enumerate([("🇹🇷 Ankara",39.92,32.86),("🇹🇷 İstanbul",41.01,28.98),
                                        ("🇹🇷 İzmir",38.42,27.13),("🇩🇪 Berlin",52.52,13.41),
                                        ("🇫🇷 Paris",48.86,2.35),("🇬🇧 Londra",51.51,-0.13),
                                        ("🇺🇸 New York",40.71,-74.01),("🇯🇵 Tokyo",35.68,139.69),
                                        ("🇦🇪 Dubai",25.20,55.27),("🇦🇺 Sidney",-33.87,151.21)]):
            ctk.CTkButton(qf,text=nm,fg_color=C["card2"],hover_color=C["pbtn"],text_color=C["t1"],
                          corner_radius=8,height=34,font=ctk.CTkFont("Segoe UI",11),
                          command=lambda la=la,lo=lo:(self.wlat.delete(0,"end"),self.wlat.insert(0,str(la)),
                                                     self.wlon.delete(0,"end"),self.wlon.insert(0,str(lo)),self._fetch())
                          ).grid(row=i//5,column=i%5,padx=4,pady=3,sticky="nsew")
        self.wres=ctk.CTkFrame(self,fg_color="transparent"); self.wres.pack(fill="both",padx=24,expand=True)

    def _use_ip(self):
        self.wsp.configure(text="IP konumu alınıyor...")
        self.wsp.start()
        def _cb(d):
            self.wsp.stop()
            if d.get("status")=="success":
                lat,lon=d.get("lat"),d.get("lon")
                self.wlat.delete(0,"end"); self.wlat.insert(0,str(lat))
                self.wlon.delete(0,"end"); self.wlon.insert(0,str(lon))
                self._fetch()
        self.async_call(self._api.ip_loc,cb=_cb)

    def _fetch(self):
        try: lat,lon=float(self.wlat.get()),float(self.wlon.get())
        except: return
        for w in self.wres.winfo_children(): w.destroy()
        self.wsp.configure(text="Hava durumu alınıyor..."); self.wsp.start()
        def _cb(d):
            self.wsp.stop()
            if "error" in d:
                ctk.CTkLabel(self.wres,text=f"❌ {d['error']}",text_color=C["accent"]).pack(pady=8,anchor="w"); return
            cw=d.get("current_weather",{})

            cc=Card(self.wres,title="☀️ Anlık Hava Durumu"); cc.pack(fill="x",pady=8)
            cf=ctk.CTkFrame(cc,fg_color="transparent"); cf.pack(fill="x",padx=14,pady=(0,12))
            wcode=int(cw.get("weathercode",0))
            wdesc=WX_CODES.get(wcode,"❓ Bilinmiyor")
            ctk.CTkLabel(cf,text=f"{wdesc}",font=ctk.CTkFont("Segoe UI",22,"bold"),text_color=C["t1"]).pack(anchor="w")
            for k,v in [("🌡️ Sıcaklık",f"{cw.get('temperature','?')}°C"),
                        ("💨 Rüzgar Hızı",f"{cw.get('windspeed','?')} km/s"),
                        ("🧭 Rüzgar Yönü",f"{cw.get('winddirection','?')}°"),
                        ("📅 Zaman",cw.get("time","?"))]:
                IRow(cf,k,v).pack(fill="x",pady=2)

            daily=d.get("daily",{})
            if daily:
                fc=Card(self.wres,title="📅 7 Günlük Tahmin"); fc.pack(fill="x",pady=8)
                ff=ctk.CTkFrame(fc,fg_color="transparent"); ff.pack(fill="x",padx=14,pady=(0,12))
                ff.columnconfigure(list(range(7)),weight=1,uniform="day")
                dates=daily.get("time",[])
                maxT=daily.get("temperature_2m_max",[]); minT=daily.get("temperature_2m_min",[])
                prec=daily.get("precipitation_sum",[]); codes=daily.get("weathercode",[])
                for i in range(min(7,len(dates))):
                    dc=ctk.CTkFrame(ff,fg_color=C["card2"],corner_radius=8)
                    dc.grid(row=0,column=i,padx=4,pady=4,sticky="nsew")
                    d_str=dates[i][5:] if i>0 else "Bugün"
                    w_icon=WX_CODES.get(int(codes[i]) if i<len(codes) else 0,"☁️")[:2]
                    ctk.CTkLabel(dc,text=d_str,font=ctk.CTkFont("Segoe UI",11,"bold"),text_color=C["primary"]).pack(pady=(8,2))
                    ctk.CTkLabel(dc,text=w_icon,font=ctk.CTkFont(size=20)).pack()
                    if i<len(maxT): ctk.CTkLabel(dc,text=f"{maxT[i]:.0f}°",font=ctk.CTkFont("Segoe UI",13,"bold"),text_color=C["accent"]).pack()
                    if i<len(minT): ctk.CTkLabel(dc,text=f"{minT[i]:.0f}°",font=ctk.CTkFont("Segoe UI",11),text_color=C["t2"]).pack()
                    if i<len(prec): ctk.CTkLabel(dc,text=f"🌧{prec[i]:.1f}mm",font=ctk.CTkFont("Segoe UI",10),text_color=C["t3"]).pack(pady=(2,8))
        self.async_call(self._api.weather,lat,lon,cb=_cb)

class ElevationPage(Page):
    def __init__(self,p,app,**kw):
        super().__init__(p,**kw); self._app=app; self._build()

    def _build(self):
        self.page_hdr("⛰️","Yükseklik Analizi","Herhangi bir koordinat için deniz seviyesinden yükseklik")
        si=ctk.CTkFrame(self,fg_color=C["card2"],corner_radius=10); si.pack(fill="x",padx=24,pady=(0,14))
        ctk.CTkLabel(si,text="Koordinat Gir:",font=ctk.CTkFont("Segoe UI",13,"bold"),text_color=C["t1"]).pack(padx=14,pady=(12,6),anchor="w")
        cr=ctk.CTkFrame(si,fg_color="transparent"); cr.pack(fill="x",padx=14,pady=(0,8))
        ctk.CTkLabel(cr,text="Enlem:",text_color=C["t2"],font=ctk.CTkFont("Segoe UI",12)).pack(side="left")
        self.elat=self.mk_entry(cr,"Örn: 27.9881",width=160); self.elat.pack(side="left",padx=(8,18))
        ctk.CTkLabel(cr,text="Boylam:",text_color=C["t2"],font=ctk.CTkFont("Segoe UI",12)).pack(side="left")
        self.elon=self.mk_entry(cr,"Örn: 86.9250",width=160); self.elon.pack(side="left",padx=8)
        br=ctk.CTkFrame(si,fg_color="transparent"); br.pack(fill="x",padx=14,pady=(0,12))
        self.mk_btn(br,"⛰️  Yüksekliği Sorgula",self._fetch).pack(side="left",padx=(0,8))
        self.mk_btn(br,"🧹  Temizle",self._clr,primary=False).pack(side="left")
        self.esp=Spinner(si); self.esp.pack(padx=14,pady=(0,8),anchor="w")

        pc=Card(self,"🏔️ Ünlü Zirveler"); pc.pack(fill="x",padx=24,pady=(0,14))
        pf=ctk.CTkFrame(pc,fg_color="transparent"); pf.pack(fill="x",padx=14,pady=(0,12))
        pf.columnconfigure((0,1,2),weight=1,uniform="pk")
        peaks=[("🏔️ Everest",27.9881,86.9250,8848),("🌋 Elbrus",43.3499,42.4453,5642),
               ("🏔️ Mont Blanc",45.8326,6.8652,4808),("🏔️ Kilimanjaro",-3.0674,37.3556,5895),
               ("🌋 Füji",35.3606,138.7274,3776),("🏔️ Ağrı Dağı",39.7021,44.2982,5137)]
        for i,(nm,la,lo,alt) in enumerate(peaks):
            f=ctk.CTkFrame(pf,fg_color=C["card2"],corner_radius=8)
            f.grid(row=i//3,column=i%3,padx=5,pady=5,sticky="nsew")
            ctk.CTkLabel(f,text=nm,font=ctk.CTkFont("Segoe UI",12,"bold"),text_color=C["t1"]).pack(pady=(10,2))
            ctk.CTkLabel(f,text=f"📐 {alt:,} m",font=ctk.CTkFont("Segoe UI",11),text_color=C["primary"]).pack()
            ctk.CTkButton(f,text="Sorgula",fg_color=C["pbtn"],hover_color=C["hl"],text_color=C["t1"],
                          height=28,corner_radius=6,font=ctk.CTkFont("Segoe UI",11),
                          command=lambda la=la,lo=lo:(self.elat.delete(0,"end"),self.elat.insert(0,str(la)),
                                                     self.elon.delete(0,"end"),self.elon.insert(0,str(lo)),self._fetch())
                          ).pack(pady=(4,10),padx=8,fill="x")
        self.eres=ctk.CTkFrame(self,fg_color="transparent"); self.eres.pack(fill="both",padx=24,expand=True)

        ic=Card(self,"ℹ️ Yükseklik Hakkında"); ic.pack(fill="x",padx=24,pady=(0,20))
        ctk.CTkLabel(ic,text="Yükseklik, bir noktanın deniz seviyesinden olan dikey mesafesidir. "
                    "Coğrafya ve CBS'de arazi analizi, su havzası tespiti, iklim çalışmaları ve "
                    "uçuş planlaması gibi birçok alanda kritik öneme sahiptir. SRTM (Shuttle Radar "
                    "Topography Mission) verileri, dünya genelinde yükseklik haritalamasının temel kaynağıdır.",
                    font=ctk.CTkFont("Segoe UI",12),text_color=C["t2"],wraplength=880,anchor="w",
                    justify="left").pack(padx=14,pady=(0,14),fill="x")

    def _fetch(self):
        try: lat,lon=float(self.elat.get()),float(self.elon.get())
        except: return
        for w in self.eres.winfo_children(): w.destroy()
        self.esp.start()
        def _cb(elev):
            self.esp.stop()
            rc=Card(self.eres,title="⛰️ Yükseklik Sonucu"); rc.pack(fill="x",pady=8)
            if elev is None:
                ctk.CTkLabel(rc,text="❌ Yükseklik verisi alınamadı",text_color=C["accent"]).pack(padx=14,pady=12); return
            ctk.CTkLabel(rc,text=f"{elev:,.1f} m",font=ctk.CTkFont("Segoe UI",36,"bold"),
                         text_color=C["primary"]).pack(padx=14,pady=(10,4))
            ctk.CTkLabel(rc,text="deniz seviyesinden yükseklik",font=ctk.CTkFont("Segoe UI",12),
                         text_color=C["t2"]).pack(padx=14,pady=(0,6))
            for k,v in [("📍 Koordinat",f"{lat:.5f}°, {lon:.5f}°"),
                        ("📏 Metre",f"{elev:,.1f} m"),("📏 Feet",f"{elev*3.28084:,.1f} ft"),
                        ("📏 Km",f"{elev/1000:.3f} km")]:
                IRow(rc,k,v).pack(fill="x",padx=14,pady=2)
            self.mk_btn(rc,"🗺️ Haritada Göster",lambda:self.open_map(lat,lon,f"Yükseklik: {elev:.0f}m"),
                        height=30,corner_radius=6,font=ctk.CTkFont("Segoe UI",11)).pack(padx=14,pady=(6,12),anchor="w")
        self.async_call(self._api.elevation,lat,lon,cb=_cb)

    def _clr(self):
        self.elat.delete(0,"end"); self.elon.delete(0,"end")
        for w in self.eres.winfo_children(): w.destroy()

class SafetyLabPage(Page):
    def __init__(self,p,app,**kw):
        super().__init__(p,**kw); self._app=app; self._run_sim=False; self._build()
    def _build(self):
        self.page_hdr("🌋","Safet Lab","Afet Simülasyon ve Risk Analiz Motoru")
        c=Card(self,"🎯 Simülasyon Senaryosu & Koordinat"); c.pack(fill="x",padx=24,pady=(0,14))
        cr=ctk.CTkFrame(c,fg_color="transparent"); cr.pack(fill="x",padx=14,pady=(12,0))
        ctk.CTkLabel(cr,text="Riskli Bölge/Senaryo:",text_color=C["t2"]).pack(side="left")
        self.risk_zone=ctk.CTkComboBox(cr,values=["- Manuel Seçim -",
                                                 "Deprem: İstanbul (Marmara Fayı)",
                                                 "Deprem: Bingöl (Yedisu Segmenti)",
                                                 "Deprem: Pazarcık (Ölü Deniz Fayı)",
                                                 "Sel: Kastamonu (Bozkurt Havzası)",
                                                 "Sel: Rize (Merkez/Dereyatağı)",
                                                 "Sel: İzmir (Kıyı Taşkın Riski)"],
                                       width=250,command=self._set_risk_zone)
        self.risk_zone.pack(side="left",padx=8)
        
        cr2=ctk.CTkFrame(c,fg_color="transparent"); cr2.pack(fill="x",padx=14,pady=(8,12))
        ctk.CTkLabel(cr2,text="Enlem:",text_color=C["t2"]).pack(side="left")
        self.sl_lat=self.mk_entry(cr2,"36.897",width=90); self.sl_lat.pack(side="left",padx=(8,16))
        ctk.CTkLabel(cr2,text="Boylam:",text_color=C["t2"]).pack(side="left")
        self.sl_lon=self.mk_entry(cr2,"30.647",width=90); self.sl_lon.pack(side="left",padx=8)
        
        # 🌊 TAŞKIN
        tc=Card(self,"🌊 Taşkın & Sel Simülasyonu"); tc.pack(fill="x",padx=24,pady=(0,14))
        tr=ctk.CTkFrame(tc,fg_color="transparent"); tr.pack(fill="x",padx=14,pady=(0,10))
        ctk.CTkLabel(tr,text="Su Seviyesi:",text_color=C["t2"]).pack(side="left")
        self.flood_lvl=self.mk_entry(tr,"1.0",width=80); self.flood_lvl.pack(side="left",padx=8)
        self.mk_btn(tr,"▶️ Animasyonu Başlat",self._flood_anim).pack(side="left",padx=8)
        self.mk_btn(tr,"⏹️ Durdur",self._stop_sim,primary=False).pack(side="left")

        # 💥 DEPREM
        dc=Card(self,"💥 Deprem Hassasiyet Analizi"); dc.pack(fill="x",padx=24,pady=(0,14))
        dr=ctk.CTkFrame(dc,fg_color="transparent"); dr.pack(fill="x",padx=14,pady=(0,10))
        ctk.CTkLabel(dr,text="Şiddet (Mw):",text_color=C["t2"]).pack(side="left")
        self.eq_mw=self.mk_entry(dr,"7.0",width=80); self.eq_mw.pack(side="left",padx=8)
        ctk.CTkLabel(dr,text="AFAD Zemin (Soil):",text_color=C["t2"]).pack(side="left",padx=(8,0))
        self.eq_soil=ctk.CTkComboBox(dr,values=["ZA (Sağlam Kaya)","ZB (Az Ayrışmış Kaya)","ZC (Sert Kum/Kil)","ZD (Orta Sıkı Kum/Kil)","ZE (Yumuşak/Alüvyon)"],
                                     width=180,fg_color=C["card"],border_color=C["border"],text_color=C["t1"],
                                     button_color=C["pbtn"],dropdown_fg_color=C["card"],dropdown_text_color=C["t1"])
        self.eq_soil.set("ZB (Az Ayrışmış Kaya)")
        self.eq_soil.pack(side="left",padx=8)
        self.mk_btn(dr,"🔥 Şok Dalgası Simüle Et",self._eq_anim).pack(side="left",padx=8)

        # 🌿 HEYELAN
        hc=Card(self,"🌿 Heyelan & Eğim Analizi"); hc.pack(fill="x",padx=24,pady=(0,14))
        hr=ctk.CTkFrame(hc,fg_color="transparent"); hr.pack(fill="x",padx=14,pady=(0,10))
        self.mk_btn(hr,"📐 Eğim (Topo) Haritası",self._slope_analiz).pack(side="left")
        self.mk_btn(hr,"⛰️ Heyelan Risk Haritası",self._heyelan_analiz,primary=False).pack(side="left",padx=8)

        # 💾 ÇIKTI
        ec=Card(self,"💾 Analiz Çıktısı"); ec.pack(fill="x",padx=24,pady=(0,14))
        er=ctk.CTkFrame(ec,fg_color="transparent"); er.pack(fill="x",padx=14,pady=(0,10))
        self.mk_btn(er,"💠 Sonuçları ArcGIS İçin Dışa Export",self._export_disaster).pack(side="left")
        
        self.sim_status=ctk.CTkLabel(self,text="",font=ctk.CTkFont("Segoe UI",11,slant="italic"),text_color=C["sec"])
        self.sim_status.pack(pady=10)
        self._last_res=None

    def _set_risk_zone(self, choice):
        zones = {
            "Deprem: İstanbul (Marmara Fayı)": ("40.850", "28.750", "7.5", "ZE (Yumuşak/Alüvyon)", "1.0"),
            "Deprem: Bingöl (Yedisu Segmenti)": ("39.420", "40.550", "7.2", "ZB (Az Ayrışmış Kaya)", "1.0"),
            "Deprem: Pazarcık (Ölü Deniz Fayı)": ("37.450", "37.250", "7.8", "ZE (Yumuşak/Alüvyon)", "1.0"),
            "Sel: Kastamonu (Bozkurt Havzası)": ("41.954", "33.992", "5.0", "ZD (Orta Sıkı Kum/Kil)", "5.5"),
            "Sel: Rize (Merkez/Dereyatağı)": ("41.025", "40.517", "4.5", "ZE (Yumuşak/Alüvyon)", "4.0"),
            "Sel: İzmir (Kıyı Taşkın Riski)": ("38.423", "27.142", "5.0", "ZE (Yumuşak/Alüvyon)", "2.5")
        }
        if choice in zones:
            lat, lon, mw, soil, flood = zones[choice]
            self.sl_lat.delete(0, "end"); self.sl_lat.insert(0, lat)
            self.sl_lon.delete(0, "end"); self.sl_lon.insert(0, lon)
            self.eq_mw.delete(0, "end"); self.eq_mw.insert(0, mw)
            self.eq_soil.set(soil)
            self.flood_lvl.delete(0, "end"); self.flood_lvl.insert(0, flood)
            
            type_str = "Sismik" if "Deprem" in choice else "Hidrolojik"
            self.sim_status.configure(text=f"📍 {choice} Yüklendi. {type_str} risk verileri hazır.")

    def _flood_anim(self):
        try: lat,lon=float(self.sl_lat.get()),float(self.sl_lon.get())
        except: lat,lon=36.897,30.647
        max_h=30.0
        self.sim_status.configure(text="🌊 Taşkın Analizi Başlatılıyor...")
        self._last_res = {
            "type": "FeatureCollection",
            "features": [
                {"type":"Feature","properties":{"Zon":"GÜVENLİ","Risk":"Düşük"},"geometry":{"type":"Polygon","coordinates":[[[lon-0.08,lat+0.08],[lon+0.08,lat+0.08],[lon+0.08,lat-0.08],[lon-0.08,lat-0.08],[lon-0.08,lat+0.08]]]}},
                {"type":"Feature","properties":{"Zon":"YÜKSEK RİSK","Risk":"Kritik"},"geometry":{"type":"Polygon","coordinates":[[[lon-0.018,lat-0.007],[lon-0.004,lat-0.007],[lon-0.004,lat+0.007],[lon-0.018,lat+0.007],[lon-0.018,lat-0.007]]]}},
                {"type":"Feature","properties":{"Zon":"ORTA RİSK","Risk":"Orta"},"geometry":{"type":"Polygon","coordinates":[[[lon+0.006,lat-0.013],[lon+0.022,lat-0.013],[lon+0.022,lat+0.005],[lon+0.006,lat+0.005],[lon+0.006,lat-0.013]]]}}
            ]
        }
        html = f"""
<!DOCTYPE html><html><head><meta charset='utf-8'><title>GeoVista Sel v3.0</title>
<script src='https://unpkg.com/maplibre-gl@4.1.2/dist/maplibre-gl.js'></script>
<link href='https://unpkg.com/maplibre-gl@4.1.2/dist/maplibre-gl.css' rel='stylesheet' />
<style>
body{{margin:0;overflow:hidden;background:#000}}
#map{{position:absolute;top:0;bottom:0;width:100%}}
#rc{{position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:5}}
.hud{{position:absolute;top:20px;left:20px;background:rgba(0,8,25,0.97);padding:22px;border-radius:14px;color:#00E5FF;font-family:'Segoe UI',sans-serif;border:2px solid #00E5FF;z-index:90;width:300px;box-shadow:0 0 35px rgba(0,229,255,0.35)}}
.hud h1{{margin:0 0 3px;font-size:20px}}.hud p{{margin:0 0 10px;opacity:0.5;font-size:11px}}
.leg{{font-size:11px;margin-top:12px;border-top:1px solid #1a3a5c;padding-top:10px}}
.li{{display:flex;align-items:center;margin-bottom:5px}}
.bx{{width:14px;height:14px;margin-right:8px;border-radius:3px;flex-shrink:0}}
button{{background:linear-gradient(135deg,#FF5252,#b71c1c);border:none;padding:11px;border-radius:8px;cursor:pointer;font-weight:bold;width:100%;margin-top:10px;color:#FFF;font-size:13px}}
input[type=range]{{width:100%;margin-top:8px;accent-color:#00E5FF}}
.row{{display:flex;justify-content:space-between;margin:5px 0;font-size:13px}}
</style></head><body>
<canvas id='rc'></canvas><div id='map'></div>
<div class='hud'>
  <h1>🌊 SEL &amp; TAŞKIN ANALİZİ</h1><p>Kampüs Alçak Alan Risk Modeli v3.0</p>
  <div class='row'><span>Su Seviyesi</span><b><span id='v'>0.0</span> m</b></div>
  <div class='row'><span>Risk</span><b id='rsk' style='color:#27ae60'>🟢 GÜVENLİ</b></div>
  <input id='sld' type='range' min='0' max='30' step='0.1' value='0'>
  <button id='stop'>⏹ DURDUR</button>
    <div class='leg'>
    <b style='color:#00E5FF'>TAŞKIN RİSK ZONLARI:</b><br><br>
    <div class='li'><div class='bx' style='background:#B71C1C'></div><b style='color:#FF5252'>YÜKSEK RİSK</b> – Dere Yatağı (Su Altı!)</div>
    <div class='li'><div class='bx' style='background:#0277BD'></div><b style='color:#29B6F6'>ORTA RİSK</b> – Alçak Zemin (Kısmen!)</div>
    <div class='li'><div class='bx' style='background:#1B5E20'></div><b style='color:#66BB6A'>GÜVENLİ</b> – Yüksek Zemin (Etkilenmez)</div>
  </div>
</div>
<script>
const cv=document.getElementById('rc'),ctx=cv.getContext('2d');
function rsz(){{cv.width=innerWidth;cv.height=innerHeight;}}rsz();window.addEventListener('resize',rsz);
const drops=[];
for(let i=0;i<500;i++) drops.push({{x:Math.random()*innerWidth,y:Math.random()*innerHeight,
  len:5+Math.random()*22,spd:8+Math.random()*18,ang:0.2+Math.random()*0.55,
  op:0.12+Math.random()*0.6,w:0.4+Math.random()*1.1}});
let rStop=false;
(function rd(){{ctx.clearRect(0,0,cv.width,cv.height);
  if(!rStop) drops.forEach(d=>{{ctx.save();ctx.globalAlpha=d.op;ctx.strokeStyle='rgba(130,195,255,1)';
    ctx.lineWidth=d.w;ctx.beginPath();ctx.moveTo(d.x,d.y);
    ctx.lineTo(d.x+d.len*Math.sin(d.ang),d.y+d.len*Math.cos(d.ang));ctx.stroke();ctx.restore();
    d.y+=d.spd;d.x+=d.spd*Math.sin(d.ang)*0.65;
    if(d.y>cv.height+30){{d.y=-20;d.x=Math.random()*cv.width;}}
    if(d.x>cv.width+30) d.x=-30;}});
  requestAnimationFrame(rd);}})();

try{{
const map=new maplibregl.Map({{container:'map',pitch:65,bearing:-10,zoom:15.6,
  center:[{lon},{lat}],style:'https://tiles.basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json'}});
map.on('error', (e) => console.error('MapLibre Error:', e));
let wh=0,stopped=false;

map.on('load',()=>{{
  const src='carto';
  map.addLayer({{'id':'bld','source':src,'source-layer':'building','type':'fill-extrusion',
    'paint':{{'fill-extrusion-color':'#1a2535','fill-extrusion-height':['coalesce',['get','render_height'],10],'fill-extrusion-opacity':0.88}}}});

  // GÜVENLİ BÖLGE (Yeşil)
  const safeZone={{type:'Feature',geometry:{{type:'Polygon',coordinates:[[
       [{lon}-0.08,{lat}+0.08],[{lon}+0.08,{lat}+0.08],[{lon}+0.08,{lat}-0.08],[{lon}-0.08,{lat}-0.08],[{lon}-0.08,{lat}+0.08]
  ]]}}}};
  map.addSource('safe',{{type:'geojson',data:safeZone}});
  map.addLayer({{id:'safe2d',type:'fill',source:'safe',paint:{{'fill-color':'#1B5E20','fill-opacity':0.3}}}});

  // YÜKSEK RİSK (Hafif Engebeli Su Kenarı - Kırmızı)
  const highZone={{type:'Feature',geometry:{{type:'Polygon',coordinates:[[
    [{lon}-0.018,{lat}-0.007],[{lon}-0.011,{lat}-0.008],[{lon}-0.004,{lat}-0.007],
    [{lon}-0.003,{lat}-0.002],[{lon}-0.004,{lat}+0.007],[{lon}-0.011,{lat}+0.008],
    [{lon}-0.018,{lat}+0.007],[{lon}-0.019,{lat}+0.001],[{lon}-0.018,{lat}-0.007]
  ]]}}}};
  map.addSource('high',{{type:'geojson',data:highZone}});
  map.addLayer({{id:'high3d',type:'fill-extrusion',source:'high',paint:{{
    'fill-extrusion-height':0.1,'fill-extrusion-opacity':0.75,'fill-extrusion-color':'#B71C1C'
  }}}});

  // ORTA RİSK (Hafif Engebeli Su Kenarı - Mavi)
  const midZone={{type:'Feature',geometry:{{type:'Polygon',coordinates:[[
    [{lon}+0.006,{lat}-0.013],[{lon}+0.014,{lat}-0.014],[{lon}+0.022,{lat}-0.013],
    [{lon}+0.023,{lat}-0.004],[{lon}+0.022,{lat}+0.005],[{lon}+0.014,{lat}+0.006],
    [{lon}+0.006,{lat}+0.005],[{lon}+0.005,{lat}-0.004],[{lon}+0.006,{lat}-0.013]
  ]]}}}};
  map.addSource('mid',{{type:'geojson',data:midZone}});
  map.addLayer({{id:'mid3d',type:'fill-extrusion',source:'mid',paint:{{
    'fill-extrusion-height':0.1,'fill-extrusion-opacity':0.75,'fill-extrusion-color':'#0277BD'
  }}}});

  // AJANLAR (Sadece Riskli Bölgelerde Doğarlar)
  const agents={{type:'FeatureCollection',features:[]}};
  for(let i=0;i<30;i++){{
    let startLon, startLat;
    if(i < 15) {{ // Kırmızı Bölge İçi (Yaklaşık)
        startLon = {lon} - 0.011 + (Math.random()-0.5)*0.006;
        startLat = {lat} + (Math.random()-0.5)*0.006;
    }} else {{ // Mavi Bölge İçi (Yaklaşık)
        startLon = {lon} + 0.014 + (Math.random()-0.5)*0.008;
        startLat = {lat} - 0.004 + (Math.random()-0.5)*0.008;
    }}
    agents.features.push({{
      type:'Feature',
      geometry:{{type:'Point',coordinates:[startLon, startLat]}},
      properties:{{id:i, state:'normal', speed:0.012 + Math.random()*0.008, safe:false}}
    }});
  }}
  map.addSource('agents',{{type:'geojson',data:agents}});
  
  // İnsan Silueti İkonu (Canvas)
  const canvas = document.createElement('canvas');
  canvas.width = 32; canvas.height = 32;
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = '#FFF'; ctx.beginPath(); ctx.arc(16, 6, 5, 0, Math.PI*2); ctx.fill();
  ctx.strokeStyle = '#FFF'; ctx.lineWidth = 3;
  ctx.beginPath(); ctx.moveTo(16, 11); ctx.lineTo(16, 23); 
  ctx.moveTo(16, 14); ctx.lineTo(8, 20); ctx.moveTo(16, 14); ctx.lineTo(24, 20);
  ctx.moveTo(16, 23); ctx.lineTo(10, 31); ctx.moveTo(16, 23); ctx.lineTo(22, 31); ctx.stroke();
  const imgData = ctx.getImageData(0,0,32,32);
  if(!map.hasImage('human-flood')) map.addImage('human-flood', imgData);

  map.addLayer({{ 
        id:'agent-layer',type:'symbol',source:'agents',
        layout:{{ 
          'icon-image':'human-flood', 'icon-size':0.6, 'icon-allow-overlap':true,
          'text-field':['case',['get','safe'],'✅',''], 'text-offset':[0,-1.5], 'text-size':12
        }},
        paint:{{ 
            'icon-color':['match',['get','state'],'normal','#FFF','risk','#FFEB3B','safe','#4CAF50','#F44336']
        }}
  }});

  // AFET TOPLANMA ALANI GÖRSELLEŞTİRME
  const floodTarget = [{lon} + 0.0015, {lat} - 0.002];
  map.addSource('safe_point', {{ type: 'geojson', data: {{ type: 'Feature', geometry: {{ type: 'Point', coordinates: floodTarget }} }} }});
  map.addLayer({{ id: 'safe_circle', type: 'circle', source: 'safe_point', paint: {{ 'circle-radius': 12, 'circle-color': '#00E5FF', 'circle-stroke-width': 3, 'circle-stroke-color': '#FFF' }} }});
  map.addLayer({{ 
    id: 'safe_label', type: 'symbol', source: 'safe_point', 
    layout: {{ 'text-field': 'AFET TOPLANMA ALANI', 'text-size': 14, 'text-offset': [0, 2], 'text-anchor': 'top' }},
    paint: {{ 'text-color': '#00E5FF', 'text-halo-color': '#000', 'text-halo-width': 2 }}
  }});

  // HUD Güncelleme (Tahliye Sayacı)
  const hud = document.createElement('div');
  hud.id = 'evac-hud';
  hud.style = 'position:absolute;bottom:20px;right:20px;background:rgba(0,20,40,0.9);padding:15px;border-radius:12px;color:white;font-family:sans-serif;border:1px solid #00f2ff;box-shadow:0 0 15px rgba(0,242,255,0.3);z-index:999;';
  hud.innerHTML = `<h4 style="margin:0 0 10px 0;color:#00f2ff;border-bottom:1px solid #333;padding-bottom:5px;">TAHLİYE DURUMU</h4>
    <div style="font-size:14px;">Tahliye Edilen: <span id="safe-count" style="color:#4CAF50;font-weight:bold;">0</span></div>
    <div style="font-size:14px;">Risk Altında: <span id="risk-count" style="color:#FFEB3B;font-weight:bold;">0</span></div>
    <div style="font-size:14px;">Normal: <span id="norm-count" style="color:#FFF;">30</span></div>`;
  document.body.appendChild(hud);

  const loop=setInterval(()=>{{
    if(stopped) return;
    if(wh < {max_h}){{
      wh += 0.08;
      map.setPaintProperty('high3d','fill-extrusion-height', wh);
      map.setPaintProperty('mid3d','fill-extrusion-height', wh * 0.55);
      
      document.getElementById('v').innerText = wh.toFixed(1);
      document.getElementById('sld').value = wh;
      const r = document.getElementById('rsk');
      if(wh>20){{r.innerText='🔴 YÜKSEK RİSK'; r.style.color='#FF5252';}}
      else if(wh>8){{r.innerText='🔵 ORTA RİSK'; r.style.color='#29B6F6';}}
      else{{r.innerText='🟢 GÜVENLİ'; r.style.color='#66BB6A';}}

      // Ajan Tahliye Mantığı (ANINDA VE HIZLI)
      let s=0, rs=0, n=0;
      agents.features.forEach(f => {{
          const [alon, alat] = f.geometry.coordinates;
          const target = [{lon} + 0.0015, {lat} - 0.002]; 
          
          const dist = Math.sqrt(Math.pow(alon-target[0],2) + Math.pow(alat-target[1],2));
          if (dist > 0.0008) {{
              f.geometry.coordinates[0] += (target[0]-alon) * f.properties.speed;
              f.geometry.coordinates[1] += (target[1]-alat) * f.properties.speed;
              f.properties.state = 'risk';
              rs++;
          }} else {{
              f.properties.state = 'safe';
              s++;
          }}
      }});
      document.getElementById('safe-count').innerText = s;
      document.getElementById('risk-count').innerText = rs;
      document.getElementById('norm-count').innerText = n;
      map.getSource('agents').setData(agents);
    }}
  }}, 50);

  document.getElementById('sld').oninput=(e)=>{{
    wh=parseFloat(e.target.value); stopped=true;
    map.setPaintProperty('high3d','fill-extrusion-height',wh);
    map.setPaintProperty('mid3d','fill-extrusion-height',wh*0.6);
    document.getElementById('v').innerText=wh.toFixed(1);
  }};
  document.getElementById('stop').onclick=()=>{{stopped=true;rStop=true;clearInterval(loop);}};
  map.on('idle',()=>{{if(!stopped) map.setBearing(map.getBearing()+0.04);}});
}});
}}catch(e){{alert('Hata: '+e.message);}}
</script></body></html>"""
        p, fname = tmp_map(); f=open(p,"w",encoding="utf-8"); f.write(html); f.close(); webbrowser.open(f"http://localhost:{_G_PORT}/gv_maps/{fname}")
        self.sim_status.configure(text="✅ Taşkın Simülasyonu Aktif!")

    def _eq_anim(self):
        try: lat,lon=float(self.sl_lat.get()),float(self.sl_lon.get())
        except: lat,lon=36.897,30.647
        mw=self.eq_mw.get() or "7.5"
        self.sim_status.configure(text=f"⚡ Sismik {mw} Mw - Güvenlik Analizi...")
        # ArcGIS Export için Poligon Verisi Üret (Çemberler)
        def _get_py_circle(clon, clat, r_deg):
            pts = []
            import math
            rad = math.pi / 180
            for i in range(41):
                a = 2 * math.pi * i / 40
                dx = r_deg * math.cos(a) / math.cos(clat * rad)
                dy = r_deg * math.sin(a)
                pts.append([clon + dx, clat + dy])
            return [pts]

        try: m_val = float(mw)
        except: m_val = 7.5
        
        soil = self.eq_soil.get()
        # AFAD Zemin Sınıfı Katsayıları (PGA Scalars)
        soil_f = 0.8  # ZA: Kaya
        if "ZB" in soil: soil_f = 1.0 # Referans
        elif "ZC" in soil: soil_f = 1.3 # Sert Kum
        elif "ZD" in soil: soil_f = 1.6 # Orta Sıkı
        elif "ZE" in soil: soil_f = 2.2 # Kritik (Alüvyon)
        
        scale = math.pow(m_val / 5.0, 3) * soil_f
        r1 = 0.002 + scale * 0.004
        r2, r3 = r1 * 2.2, r1 * 4.0

        self._last_res = {
            "type": "FeatureCollection",
            "features": [
                {"type":"Feature","properties":{"Risk":"DÜŞÜK","Zon":"Yeşil"},"geometry":{"type":"Polygon","coordinates":_get_py_circle(lon,lat,r3)}},
                {"type":"Feature","properties":{"Risk":"ORTA","Zon":"Turuncu"},"geometry":{"type":"Polygon","coordinates":_get_py_circle(lon,lat,r2)}},
                {"type":"Feature","properties":{"Risk":"YÜKSEK","Zon":"Kırmızı"},"geometry":{"type":"Polygon","coordinates":_get_py_circle(lon,lat,r1)}},
                {"type":"Feature","properties":{"Tip":"Merkez","Mw":m_val},"geometry":{"type":"Point","coordinates":[lon,lat]}}
            ]
        }

        html = f"""
<!DOCTYPE html><html><head><meta charset='utf-8'><title>GeoVista Deprem v3.0</title>
<script src='https://unpkg.com/maplibre-gl@4.1.2/dist/maplibre-gl.js'></script>
<link href='https://unpkg.com/maplibre-gl@4.1.2/dist/maplibre-gl.css' rel='stylesheet' />
<style>
body{{margin:0;overflow:hidden;background:#000}}
#map{{position:absolute;top:0;bottom:0;width:100%;transform-origin:center}}
.hud{{position:absolute;top:20px;left:20px;background:rgba(10,10,10,0.85);backdrop-filter:blur(10px);padding:24px;border-radius:16px;color:#FFF;font-family:'Segoe UI',sans-serif;border:1px solid rgba(255,23,68,0.4);z-index:100;width:280px;box-shadow:0 8px 32px rgba(0,0,0,0.6)}}
.hud h1{{margin:0 0 5px;font-size:22px;color:#FF1744;text-transform:uppercase;letter-spacing:1.5px}}
.leg{{font-size:11px;margin-top:15px;border-top:1px solid rgba(255,255,255,0.1);padding-top:12px}}
button{{background:linear-gradient(135deg,#FF1744,#D50000);border:none;padding:12px;border-radius:8px;cursor:pointer;font-weight:bold;width:100%;margin-top:15px;color:#FFF;font-size:13px;text-transform:uppercase;transition:0.3s}}
button:hover{{transform:translateY(-2px);box-shadow:0 5px 15px rgba(255,23,68,0.4)}}
.li{{display:flex;align-items:center;margin-bottom:6px}}
.bx{{width:14px;height:14px;margin-right:8px;border-radius:3px;flex-shrink:0}}
input[type=range]{{width:100%;margin-top:8px;accent-color:#FF1744}}
.row{{display:flex;justify-content:space-between;margin:5px 0;font-size:13px}}
.q1{{opacity:1}}
.q2{{opacity:1}}
.q3{{opacity:1}}
</style></head><body>
<div id='map'></div>
<div class='hud'>
  <div class='row' style='margin-bottom:15px;border-bottom:1px solid rgba(255,23,68,0.3);padding-bottom:10px'>
    <span style='font-size:12px;letter-spacing:1px'>SİSTEM DURUMU</span>
    <b id='st' style='color:#FF1744;text-shadow:0 0 10px #FF1744'>🔴 KRİTİK</b>
  </div>
  <div class='row'><span>🏃‍♂️ Toplam Nüfus</span><b style='color:#FFF'>30</b></div>
  <div class='row'><span>✅ Güvenli Tahliye</span><b id='evc' style='color:#00E676'>0</b></div>
  <div class='row'><span>⚠️ Panik Alanı</span><b id='pnc' style='color:#FFD600'>0</b></div>
  <div class='row'><span>⏳ Kalan Süre</span><b id='tmr' style='color:#FFF'>15s</b></div>
  
  <div style='margin-top:20px'>
    <span style='font-size:11px;opacity:0.7'>SARSINTI ŞİDDETİ (Mw)</span>
    <input id='sld' type='range' min='4.0' max='9.5' step='0.1' value='{mw}'>
    <div style='text-align:center;font-weight:bold;font-size:18px;color:#FF1744' id='mv'>{mw}</div>
  </div>
  <button id='stp'>🛑 PROTOKOLÜ DURDUR</button>
  <div class='leg'>
    <b style='color:#FFD600'>GÜVENLİK ZONU HARİTASI:</b><br><br>
    <div class='li'><div class='bx' style='background:#2E7D32'></div><b style='color:#4CAF50'>GÜVENLİ</b> – Toplanma Alanı (Dış Bölge)</div>
    <div class='li'><div class='bx' style='background:#E65100'></div><b style='color:#FF9800'>ORTA RİSK</b> – Hasar / Çatlak Beklentisi</div>
    <div class='li'><div class='bx' style='background:#B71C1C'></div><b style='color:#FF1744'>YÜKSEK RİSK</b> – Yıkım Riski / Tahliye</div>
    <div class='li' style='margin-top:6px;border-top:1px solid #333;padding-top:6px'><div class='bx' style='background:#FF1744;border-radius:50%'></div>Episantr: {lon:.4f}°E, {lat:.4f}°N</div>
  </div>
</div>
<script>
try{{
const map=new maplibregl.Map({{container:'map',pitch:65,bearing:12,zoom:15.5,
  center:[{lon},{lat}],style:'https://tiles.basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json'}});
map.on('error', (e) => console.error('MapLibre Error:', e));
let mag={mw}, sf={soil_f}, active=true, rd=0, agents=[], targetPos;

function getCircle(clon, clat, r_deg) {{
  const pts = [];
  const rad = Math.PI / 180;
  for(let i=0; i<=40; i++) {{
    const a = 2 * Math.PI * i / 40;
    const dx = r_deg * Math.cos(a) / Math.cos(clat * rad);
    const dy = r_deg * Math.sin(a);
    pts.push([clon + dx, clat + dy]);
  }}
  return [pts];
}}

function getZonesData(m) {{
  const scale = Math.pow(m / 5.0, 3) * sf;
  const r1 = 0.002 + scale * 0.004; 
  const r2 = r1 * 2.2;
  const r3 = r1 * 4.0;
  targetPos = [{lon} + r1 * 2.4, {lat} + r1 * 2.2]; // Hedef: Yeşil Bölgenin İyice İçinde
  return {{
    type:'FeatureCollection', features:[
      {{type:'Feature',properties:{{z:'safe'}},geometry:{{type:'Polygon',coordinates:getCircle({lon},{lat},r3)}}}},
      {{type:'Feature',properties:{{z:'mod'}}, geometry:{{type:'Polygon',coordinates:getCircle({lon},{lat},r2)}}}},
      {{type:'Feature',properties:{{z:'high'}},geometry:{{type:'Polygon',coordinates:getCircle({lon},{lat},r1)}}}}
    ]
  }};
}}
const zones = getZonesData(mag);
function initAgents() {{
  agents = [];
  const scale = Math.pow(mag / 5.0, 3) * sf;
  const distRadius = 0.002 + scale * 0.004; // Kırmızı zon yarıçapı (r1)
  
  // Tüm binaları al
  const allBuildings = map.queryRenderedFeatures({{ layers: ['bld'] }});
  
  // Sadece kırmızı bölge içindeki binaları filtrele
  const redZoneBuildings = allBuildings.filter(b => {{
    let bLon, bLat;
    if(b.geometry.type === 'Point') {{
      bLon = b.geometry.coordinates[0]; bLat = b.geometry.coordinates[1];
    }} else {{
      const coords = b.geometry.type === 'Polygon' ? b.geometry.coordinates[0][0] : b.geometry.coordinates[0][0][0];
      bLon = coords[0]; bLat = coords[1];
    }}
    const dist = Math.sqrt(Math.pow(bLon - {lon}, 2) + Math.pow(bLat - {lat}, 2));
    return dist <= distRadius;
  }});

  for(let i=0; i<30; i++) {{
    const r = Math.random() * distRadius * 0.8; // Kırmızı bölgenin iyice içinde başlasınlar
    const a = Math.random() * 2 * Math.PI;
    const startLon = {lon} + r * Math.cos(a);
    const startLat = {lat} + r * Math.sin(a);

    agents.push({{
      id: i,
      lon: startLon, lat: startLat,
      safe: false, angle: Math.random() * 2 * Math.PI,
      speed: 0.00012 + Math.random() * 0.0001, bob: 0
    }});
  }}
}}

map.on('load',()=>{{
  const src=Object.keys(map.getStyle().sources).find(s=>s.includes('openmaptiles')||s.includes('carto'));

  // 1) ZEMIN GÜVENLİK ZONLARI (her zaman görünür, 2D)
  map.addSource('zones',{{type:'geojson',data:zones}});
  map.addLayer({{id:'zfill',type:'fill',source:'zones',paint:{{
    'fill-color':['match',['get','z'],'safe','#1B5E20','mod','#E65100','high','#B71C1C','#333'],
    'fill-opacity':0.35
  }}}});
  map.addLayer({{id:'zline',type:'line',source:'zones',paint:{{
    'line-color':['match',['get','z'],'safe','#4CAF50','mod','#FF9800','high','#FF1744','#fff'],
    'line-width':2,'line-opacity':0.9
  }}}});

  map.addLayer({{id:'zfill',type:'fill',source:'zones',paint:{{'fill-color':['match',['get','z'],'safe','#1B5E20','mod','#E65100','high','#B71C1C','#333'],'fill-opacity':0.35}}}});
  map.addLayer({{id:'zline',type:'line',source:'zones',paint:{{'line-color':['match',['get','z'],'safe','#4CAF50','mod','#FF9800','high','#FF1744','#fff'],'line-width':2,'line-opacity':0.9}}}});

  if(src) map.addLayer({{
    'id':'bld','source':src,'source-layer':'building','type':'fill-extrusion',
    'paint':{{'fill-extrusion-color':'#2E4A1E','fill-extrusion-height':['coalesce',['get','render_height'],12],'fill-extrusion-base':0,'fill-extrusion-opacity':0.92}}
  }});

  map.addSource('epi',{{type:'geojson',data:{{type:'Feature',geometry:{{type:'Point',coordinates:[{lon},{lat}]}}}}}});
  map.addLayer({{id:'ering',type:'circle',source:'epi',paint:{{'circle-radius':0,'circle-color':'rgba(255,23,68,0.1)','circle-stroke-width':2,'circle-stroke-color':'#FF1744'}}}});
  map.addLayer({{id:'edot',type:'circle',source:'epi',paint:{{'circle-radius':10,'circle-color':'#FF1744','circle-stroke-width':3,'circle-stroke-color':'#FFF'}}}});

  map.addSource('agt', {{ type: 'geojson', data: {{ type: 'FeatureCollection', features: [] }} }});
  initAgents(); 
  
  // AFET TOPLANMA ALANI GÖRSELLEŞTİRME (Yeşil Bölge İçine)
  map.addSource('safe_point', {{ type: 'geojson', data: {{ type: 'Feature', geometry: {{ type: 'Point', coordinates: targetPos }} }} }});
  map.addLayer({{ id: 'safe_circle', type: 'circle', source: 'safe_point', paint: {{ 'circle-radius': 15, 'circle-color': '#4CAF50', 'circle-stroke-width': 4, 'circle-stroke-color': '#FFF', 'circle-opacity': 0.8 }} }});
  map.addLayer({{ 
    id: 'safe_label', type: 'symbol', source: 'safe_point', 
    layout: {{ 'text-field': 'AFET TOPLANMA ALANI', 'text-size': 16, 'text-offset': [0, -2.5], 'text-anchor': 'bottom', 'text-allow-overlap': true }},
    paint: {{ 'text-color': '#4CAF50', 'text-halo-color': '#000', 'text-halo-width': 3 }}
  }});

  const canvas = document.createElement('canvas');
  canvas.width = 32; canvas.height = 32;
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = '#FFF'; ctx.beginPath(); ctx.arc(16, 6, 5, 0, Math.PI*2); ctx.fill(); 
  ctx.strokeStyle = '#FFF'; ctx.lineWidth = 3;
  ctx.beginPath(); ctx.moveTo(16, 11); ctx.lineTo(16, 23); 
  ctx.moveTo(16, 14); ctx.lineTo(8, 20); ctx.moveTo(16, 14); ctx.lineTo(24, 20);
  ctx.moveTo(16, 23); ctx.lineTo(10, 31); ctx.moveTo(16, 23); ctx.lineTo(22, 31); ctx.stroke();
  const imgData = ctx.getImageData(0,0,32,32);
  if(!map.hasImage('human-run')) map.addImage('human-run', imgData);
  map.addLayer({{
    id: 'agt-layer', type: 'symbol', source: 'agt',
    layout: {{ 'icon-image': 'human-run', 'icon-size': 0.7, 'icon-allow-overlap': true, 'text-field': ['case', ['get', 'safe'], '✅', ''], 'text-offset': [0, -1.8], 'text-size': 14 }}
  }});

  let frame=0;
  const loop=setInterval(()=>{{
    if(!active) return;
    frame++;
    rd=(rd+4)%120;
    map.setPaintProperty('ering','circle-radius',rd*mag*0.16);
    const el=document.getElementById('map');
    el.className = mag>=7.5 ? 'q3' : (mag>=5.5 ? 'q2' : 'q1');

    if(map.getLayer('bld')){{
      const jitter = mag * 2.2 * sf, hRand = (Math.random()-0.5) * jitter;
      let saved = 0, panic = 0;
      const sLon = targetPos[0], sLat = targetPos[1]; 
      const features = agents.map(a => {{
        if(!a.safe) {{
          a.angle = Math.atan2(sLat - a.lat, sLon - a.lon);
          a.lon += Math.cos(a.angle) * a.speed * 1.0;
          a.lat += Math.sin(a.angle) * a.speed * 1.0;
          const dSafe = Math.sqrt(Math.pow(sLon-a.lon,2) + Math.pow(sLat-a.lat,2));
          if(dSafe < 0.0006) a.safe = true;
          panic++;
        }} else saved++;
        return {{ type: 'Feature', geometry: {{ type: 'Point', coordinates: [a.lon, a.lat] }}, properties: {{ safe: a.safe }} }};
      }});
      map.getSource('agt').setData({{ type: 'FeatureCollection', features: features }});
      document.getElementById('evc').innerText = saved;
      document.getElementById('pnc').innerText = panic;

      const baseJitter = Math.random() * (mag>7 ? 12.0 : mag>5 ? 6.0 : 2.5) * sf;
      map.setPaintProperty('bld','fill-extrusion-base', baseJitter);

      // Bina rengi: zone bazlı (kırmızı zone = kırmızı), dinamik
      const t = Math.random();
      let col = '#2E4A1E'; // güvenli - yeşil
      if(mag >= 7.5) {{
        if(t < 0.45) col = '#B71C1C';
        else if(t < 0.70) col = '#E65100';
        else col = '#2E4A1E';
      }} else if(mag >= 5.5) {{
        if(t < 0.25) col = '#B71C1C';
        else if(t < 0.55) col = '#E65100';
        else col = '#2E4A1E';
      }} else {{
        if(t < 0.10) col = '#E65100';
        else col = '#2E4A1E';
      }}
      map.setPaintProperty('bld','fill-extrusion-color', col);

      // !! YIKILMA: Binalar sarsıntıya göre tepki verir (3.0+ başlar) !!
      if(mag >= 6.5) {{
        // Devasa sarsıntı
        const tiltX = (Math.random()-0.5) * mag * 15.0 * sf;
        const tiltY = (Math.random()-0.5) * mag * 15.0 * sf;
        map.setPaintProperty('bld','fill-extrusion-translate', [tiltX, tiltY]);
        // Kamera titremesi
        map.getContainer().style.transform = 'translate(' + ((Math.random()-0.5)*8) + 'px, ' + ((Math.random()-0.5)*8) + 'px)';
      }} else if(mag >= 3.0) {{
        // Orta/Hafif sarsıntı (3.0'dan itibaren başlar)
        const intensity = (mag - 3.0) * 2.0;
        const tiltX = (Math.random()-0.5) * intensity * 5.0 * sf;
        const tiltY = (Math.random()-0.5) * intensity * 5.0 * sf;
        map.setPaintProperty('bld','fill-extrusion-translate', [tiltX, tiltY]);
        map.getContainer().style.transform = 'translate(' + ((Math.random()-0.5)*intensity) + 'px, ' + ((Math.random()-0.5)*intensity) + 'px)';
      }} else {{
        map.setPaintProperty('bld','fill-extrusion-translate', [0, 0]);
        map.getContainer().style.transform = 'translate(0,0)';
      }}
    }}
  }}, 35);

  document.getElementById('sld').oninput=(e)=>{{
    mag=parseFloat(e.target.value);
    document.getElementById('mv').innerText=mag.toFixed(1);
    if(map.getSource('zones')) map.getSource('zones').setData(getZonesData(mag));
  }};
  let tl = 15;
  const tRing = setInterval(()=>{{
    if(!active) return;
    tl--;
    const tEl = document.getElementById('tmr');
    if(tEl) tEl.innerText = tl;
    if(tl <= 0) {{
      active=false; clearInterval(loop); clearInterval(tRing);
      document.getElementById('map').className='';
      document.getElementById('st').innerHTML='🟢 BİTTİ';
      document.getElementById('st').style.color='#4CAF50';
      if(map.getLayer('bld')) map.setPaintProperty('bld','fill-extrusion-translate',[0,0]);
    }}
  }}, 1000);

  document.getElementById('stp').onclick=()=>{{
    active=false;clearInterval(loop);clearInterval(tRing);
    document.getElementById('map').className='';
    document.getElementById('st').innerText='✅ DEPREM DURDURULDU';
    document.getElementById('st').style.color='#4CAF50';
    document.getElementById('stp').textContent='✅ DURDURULDU';
    document.getElementById('stp').style.background='#1B5E20';
    map.setPaintProperty('ering','circle-radius',0);
    if(map.getLayer('bld')){{
      map.setPaintProperty('bld','fill-extrusion-height',['coalesce',['get','render_height'],12]);
      map.setPaintProperty('bld','fill-extrusion-base',0);
      map.setPaintProperty('bld','fill-extrusion-color','#2E4A1E');
    }}
  }};
  map.on('idle',()=>{{if(active) map.setBearing(map.getBearing()+0.07);}});
}});
}}catch(e){{alert('Hata: '+e.message);}}
</script></body></html>"""
        p, fname = tmp_map(); f=open(p,"w",encoding="utf-8"); f.write(html); f.close(); webbrowser.open(f"http://localhost:{_G_PORT}/gv_maps/{fname}")
        self.sim_status.configure(text="✅ Deprem & Güvenlik Zonları Aktif!")

    def _slope_analiz(self):
        lat,lon=36.897,30.647
        self.sim_status.configure(text="🏔️ 3D İrtifa Analizi...")
        html = f"""
<!DOCTYPE html><html><head><meta charset='utf-8'><title>GeoVista Topo v3.0</title>
<script src='https://unpkg.com/maplibre-gl@4.1.2/dist/maplibre-gl.js'></script>
<link href='https://unpkg.com/maplibre-gl@4.1.2/dist/maplibre-gl.css' rel='stylesheet' />
<style>body{{margin:0;overflow:hidden}}#map{{position:absolute;top:0;bottom:0;width:100%}}
.hud{{position:absolute;top:20px;left:20px;background:rgba(10,35,15,0.95);padding:24px;border-radius:12px;color:#FFF;font-family:'Segoe UI';border:1px solid #4CAF50;z-index:100;width:280px}}
.leg div{{margin:8px 0;font-size:13px;display:flex;align-items:center}}
.leg span{{width:14px;height:14px;margin-right:8px;border-radius:2px}}
</style></head><body><div id='map'></div>
<div class='hud'><h1>🏔️ 3D TOPO</h1><p>v3.0 Stabil</p>
    <div><span style='background:#FFF'></span>Kar Hattı</div>
    <div><span style='background:#795548'></span>Heyelan Riski</div>
    <div><span style='background:#66BB6A'></span>Ova Hattı</div>
</div>
</div>
<script>
try {{
const map = new maplibregl.Map({{ container: 'map', pitch: 80, bearing: 45, zoom: 12.5, center: [{lon}, {lat}], style: 'https://tiles.basemaps.cartocdn.com/gl/voyager-gl-style/style.json' }});
map.on('error', (e) => console.error('MapLibre Error:', e));
map.on('load', () => {{
    map.addSource('tr', {{ type: 'raster-dem', tiles: ['https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{{z}}/{{x}}/{{y}}.png'], encoding: 'terrarium', tileSize: 256 }});
    map.setTerrain({{ source: 'tr', exaggeration: 30.0 }});
    map.addLayer({{ id: 'hs', type: 'hillshade', source: 'tr' }});
    setInterval(() => {{ map.setBearing(map.getBearing() + 0.05); }}, 100);
}});
}} catch(e) {{ alert('Hata: ' + e.message); }}
</script></body></html>"""
        p, fname = tmp_map()
        with open(p,"w",encoding="utf-8") as f: f.write(html)
        webbrowser.open(f"http://localhost:{_G_PORT}/gv_maps/{fname}")
        self.sim_status.configure(text="✅ İrtifa Analizi Yayında!")

    def _heyelan_analiz(self):
        try: lat,lon=float(self.sl_lat.get()),float(self.sl_lon.get())
        except: lat,lon=36.897,30.647
        self.sim_status.configure(text="⛰️ Heyelan Risk Haritası Yükleniyor...")
        # Heyelan Poligonu (Temsili risk alanı)
        self._last_res = {
            "type": "FeatureCollection",
            "features": [
                {"type":"Feature","properties":{"Risk":"ÇOK YÜKSEK","Eğim":">35°"},"geometry":{"type":"Polygon","coordinates":[[[lon-0.012,lat+0.005],[lon+0.008,lat+0.01],[lon+0.015,lat-0.005],[lon-0.005,lat-0.01],[lon-0.012,lat+0.005]]]}},
                {"type":"Feature","properties":{"Sınıf":"Analiz Merkezi","Koor":f"{lat},{lon}"},"geometry":{"type":"Point","coordinates":[lon,lat]}}
            ]
        }
        html = f"""
<!DOCTYPE html><html><head><meta charset='utf-8'><title>GeoVista Heyelan Risk v3.0</title>
<script src='https://unpkg.com/maplibre-gl@4.1.2/dist/maplibre-gl.js'></script>
<link href='https://unpkg.com/maplibre-gl@4.1.2/dist/maplibre-gl.css' rel='stylesheet' />
<style>
body{{margin:0;overflow:hidden;background:#0a1a0a}}
#map{{position:absolute;top:0;bottom:0;width:100%}}
.hud{{position:absolute;top:20px;left:20px;background:rgba(5,20,5,0.97);padding:22px;border-radius:14px;color:#66BB6A;font-family:'Segoe UI',sans-serif;border:2px solid #4CAF50;z-index:100;width:300px;box-shadow:0 0 35px rgba(76,175,80,0.4)}}
.hud h1{{margin:0 0 3px;font-size:20px}}.hud p{{margin:0 0 10px;opacity:0.5;font-size:11px}}
.leg{{font-size:11px;margin-top:12px;border-top:1px solid #1a3a1a;padding-top:10px}}
.li{{display:flex;align-items:center;margin-bottom:6px}}
.bx{{width:14px;height:14px;margin-right:8px;border-radius:3px;flex-shrink:0}}
.row{{display:flex;justify-content:space-between;margin:5px 0;font-size:13px}}
.bar{{height:6px;border-radius:3px;margin-top:4px;background:linear-gradient(90deg,#1B5E20,#FFEB3B,#FF6F00,#B71C1C);width:100%}}
</style></head><body>
<div id='map'></div>
<div class='hud'>
  <h1>⛰️ HEYELAN RİSK HARİTASI</h1><p>3D Eğim & Toprak Kayması Analizi v3.0</p>
  <div class='row'><span>Eğim Riski</span><b id='rsk' style='color:#4CAF50'>● ANALİZ EDİLİYOR</b></div>
  <div class='row'><span>Yükseklik</span><b id='elv'>---</b></div>
  <div class='bar'></div>
  <div class='leg'>
    <b style='color:#4CAF50'>EĞİM RİSK SINIFLARI:</b><br><br>
    <div class='li'><div class='bx' style='background:#B71C1C'></div><b style='color:#FF5252'>ÇOK YÜKSEK</b> – &gt;35° Kritik Eğim</div>
    <div class='li'><div class='bx' style='background:#E65100'></div><b style='color:#FF9800'>YÜKSEK</b> – 25-35° Heyelan Riski</div>
    <div class='li'><div class='bx' style='background:#F9A825'></div><b style='color:#FFD600'>ORTA</b> – 15-25° Dikkat Bölgesi</div>
    <div class='li'><div class='bx' style='background:#1B5E20'></div><b style='color:#66BB6A'>GÜVENLİ</b> – &lt;15° Stabil Zemin</div>
    <div class='li' style='margin-top:8px;border-top:1px solid #1a3a1a;padding-top:8px'>
      <div class='bx' style='background:#795548'></div><b style='color:#BCAAA4'>KAYALIK</b> – Taş/Kaya Düşme Riski
    </div>
  </div>
</div>
<script>
try{{
const map = new maplibregl.Map({{
  container:'map', pitch:70, bearing:30, zoom:14.2,
  center:[{lon},{lat}], style:'https://tiles.basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json'
}});

map.on('load', ()=>{{
  // Binalar (Karanlık Mod)
  map.addLayer({{
    'id':'bld','source':'carto','source-layer':'building','type':'fill-extrusion',
    'paint':{{
      'fill-extrusion-color':'#1a2535',
      'fill-extrusion-height':['coalesce',['get','render_height'],12],
      'fill-extrusion-opacity':0.85
    }}
  }});

  // Arazi Verisi
  map.addSource('terr', {{
    type:'raster-dem',
    tiles:['https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{{z}}/{{x}}/{{y}}.png'],
    encoding:'terrarium', tileSize:256
  }});
  map.setTerrain({{ source:'terr', exaggeration:3.5 }});
  
  // Risk Bölgeleri (Kesin Ayrılmış)
  const riskZones = {{type:'FeatureCollection',features:[
    // ÇOK YÜKSEK (Kırmızı)
    {{type:'Feature',properties:{{r:'critical',name:'ÇOK YÜKSEK RİSK',slope:42,elv:740}},
      geometry:{{type:'Polygon',coordinates:[[
        [{lon}+0.015,{lat}+0.005],[{lon}+0.025,{lat}+0.015],[{lon}+0.035,{lat}+0.005],[{lon}+0.025,{lat}-0.005],[{lon}+0.015,{lat}+0.005]
      ]]}}}},
    // YÜKSEK (Turuncu)
    {{type:'Feature',properties:{{r:'high',name:'YÜKSEK RİSK',slope:32,elv:520}},
      geometry:{{type:'Polygon',coordinates:[[
        [{lon}-0.01,{lat}+0.005],[{lon}+0.005,{lat}+0.012],[{lon}+0.015,{lat}+0.002],[{lon}-0.005,{lat}-0.005],[{lon}-0.01,{lat}+0.005]
      ]]}}}},
    // ORTA (Sarı)
    {{type:'Feature',properties:{{r:'mid',name:'ORTA RİSK',slope:22,elv:340}},
      geometry:{{type:'Polygon',coordinates:[[
        [{lon}-0.02,{lat}-0.015],[{lon}-0.01,{lat}-0.010],[{lon}-0.005,{lat}-0.018],[{lon}-0.02,{lat}-0.022],[{lon}-0.02,{lat}-0.015]
      ]]}}}}
  ]}};

  const safeBase = {{type:'Feature', geometry:{{type:'Polygon',coordinates:[[
    [{lon}-0.1,{lat}-0.1],[{lon}+0.1,{lat}-0.1],[{lon}+0.1,{lat}+0.1],[{lon}-0.1,{lat}+0.1],[{lon}-0.1,{lat}-0.1]
  ]]}}}};

  map.addSource('safe-base', {{type:'geojson', data:safeBase}});
  map.addLayer({{id:'safe-bg', type:'fill', source:'safe-base', paint:{{'fill-color':'#1B5E20','fill-opacity':0.25}}}});

  map.addSource('risk', {{type:'geojson', data:riskZones}});
  map.addLayer({{id:'rfill',type:'fill-extrusion',source:'risk',paint:{{
    'fill-extrusion-height':20,
    'fill-extrusion-color':['match',['get','r'],'critical','#B71C1C', 'high','#E65100', 'mid','#FFD600', '#333'],
    'fill-extrusion-opacity':0.7
  }}}});

  map.on('mousemove', 'rfill', (e)=>{{
    const p = e.features[0].properties;
    document.getElementById('rsk').innerText = p.name;
    const colors = {{'critical':'#FF5252','high':'#FF9100','mid':'#FFD600'}};
    document.getElementById('rsk').style.color = colors[p.r] || '#FFF';
    document.getElementById('elv').innerText = p.elv + ' m (Eğim: ' + p.slope + '°)';
  }});
  
  map.on('mousemove', 'safe-bg', ()=>{{
    document.getElementById('rsk').innerText = 'GÜVENLİ ALAN';
    document.getElementById('rsk').style.color = '#66BB6A';
    document.getElementById('elv').innerText = '--';
  }});

  let b = 30;
  setInterval(()=>{{ map.setBearing(b+=0.06); }}, 100);
}});
}}catch(e){{alert('Hata: ' + e.message);}}
</script></body></html>"""
        p, fname = tmp_map()
        with open(p,"w",encoding="utf-8") as f: f.write(html)
        webbrowser.open(f"http://localhost:{_G_PORT}/gv_maps/{fname}")
        self.sim_status.configure(text="✅ Heyelan Risk Haritası Aktif!")

    def _export_disaster(self):
        if not self._last_res: 
            messagebox.showwarning("Uyarı","Dışa aktarılacak analiz sonucu bulunamadı!")
            return
            
        p = filedialog.asksaveasfilename(
            defaultextension=".shp",
            filetypes=[
                ("ESRI Shapefile (ArcGIS)","*.shp"),
                ("Keyhole Markup Language (KML)","*.kml"),
                ("GeoJSON","*.geojson")
            ]
        )
        if not p: return

        try:
            import geopandas as gpd
            from shapely.geometry import shape
            
            # Veriyi GeoDataFrame'e dönüştür
            features = self._last_res.get("features", [])
            geoms = [shape(f["geometry"]) for f in features]
            props = [f["properties"] for f in features]
            
            # Shapefile için kolon isimlerini 10 karakterle sınırla (ArcGIS standardı)
            clean_props = []
            for item in props:
                clean_item = {str(k)[:10]: str(v) for k, v in item.items()}
                clean_props.append(clean_item)

            gdf = gpd.GeoDataFrame(clean_props, geometry=geoms, crs="EPSG:4326")
            
            if p.endswith(".shp"):
                gdf.to_file(p, driver="ESRI Shapefile")
            elif p.endswith(".kml"):
                import fiona
                if 'KML' not in fiona.supported_drivers:
                    fiona.supported_drivers['KML'] = 'rw'
                gdf.to_file(p, driver='KML')
            else:
                gdf.to_file(p, driver='GeoJSON')
                
            messagebox.showinfo("Başarılı", f"Analiz sonucu ArcGIS uyumlu ({p.split('.')[-1].upper()}) kaydedildi.")
        except Exception as e:
            # Geopandas hatası durumunda düz JSON/GeoJSON kaydetme (Fallback)
            if not p.endswith(".geojson"):
                p = p.rsplit(".",1)[0] + ".geojson"
            with open(p,"w",encoding="utf-8") as f: 
                json.dump(self._last_res,f,ensure_ascii=False,indent=2)
            messagebox.showwarning("Başarılı (Kısıtlı)","Gelişmiş formatta kaydedilemedi (Kütüphane eksik), GeoJSON olarak kaydedildi.")
    
    def _stop_sim(self): self._run_sim=False

class AboutPage(Page):
    def __init__(self,p,**kw):
        super().__init__(p,**kw); self._build()

    def _build(self):
        self.page_hdr("ℹ️","GeoVista Hakkında","CBS Profesyonel Analiz Motoru v3.0.0")
        ac=Card(self,title="🌍 GeoVista Nedir?"); ac.pack(fill="x",padx=24,pady=(0,14))
        ctk.CTkLabel(ac,text="GeoVista, coğrafya ve CBS (Coğrafi Bilgi Sistemi) öğrencileri için "
                    "geliştirilmiş ücretsiz, açık kaynaklı bir masaüstü uygulamasıdır. Tamamen ücretsiz "
                    "API'ler kullanılarak geliştirilmiştir.",
                    font=ctk.CTkFont("Segoe UI",12),text_color=C["t2"],wraplength=880,anchor="w"
                    ).pack(padx=14,pady=(0,14),fill="x")
        fc=Card(self,title="🔌 Kullanılan Ücretsiz API'ler"); fc.pack(fill="x",padx=24,pady=(0,14))
        apis=[("🗺️","Nominatim (OpenStreetMap)","İleri/Ters Coğrafi Kodlama — nominatim.openstreetmap.org"),
              ("🌐","RestCountries","Ülke verileri — restcountries.com"),
              ("📡","ip-api.com","IP Konum Belirleme — ip-api.com"),
              ("⛰️","Open-Elevation","Yükseklik Verisi — api.open-elevation.com"),
              ("🌡️","Open-Meteo","Hava Durumu & İklim — api.open-meteo.com"),
              ("🌎","MapLibre GL JS","Extreme 3D Render Motoru"),
              ("🗺️","Folium + Leaflet.js","İnteraktif Harita Gösterimi")]
        for ic,nm,desc in apis:
            row=ctk.CTkFrame(fc,fg_color=C["card2"],corner_radius=8); row.pack(fill="x",padx=12,pady=4)
            ctk.CTkLabel(row,text=ic,font=ctk.CTkFont(size=20)).pack(side="left",padx=(12,8),pady=10)
            tf=ctk.CTkFrame(row,fg_color="transparent"); tf.pack(side="left",fill="both",expand=True,pady=8)
            ctk.CTkLabel(tf,text=nm,font=ctk.CTkFont("Segoe UI",12,"bold"),text_color=C["primary"],anchor="w").pack(anchor="w")
            ctk.CTkLabel(tf,text=desc,font=ctk.CTkFont("Segoe UI",11),text_color=C["t2"],anchor="w").pack(anchor="w")
        tc=Card(self,title="🧰 Teknolojiler"); tc.pack(fill="x",padx=24,pady=(0,20))
        for k,v in [("💻 Dil","Python 3.8+"),("🎨 Arayüz","CustomTkinter"),
                    ("🗺️ Harita","Folium + Leaflet.js"),("📡 İstekler","Requests"),("🖼️ Görsel","Pillow")]:
            IRow(tc,k,v).pack(fill="x",padx=14,pady=3)
        ctk.CTkLabel(self,text=f"💙 Coğrafyaya duyulan sevgiyle yapıldı  |  GeoVista v3.0.0  |  {datetime.now().year}",
                     font=ctk.CTkFont("Segoe UI",11),text_color=C["t3"]).pack(pady=16)

class GeoVista(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("GeoVista — Pro GIS Platform v3.0")
        self.geometry("1350x850")
        self.minsize(1150,750)
        self.configure(fg_color=C["bg"])
        self._nav_btns={}
        self._pages={}
        self._build_sidebar()
        self._build_content()
        self._check_q()
        self.show("dashboard")

    def _check_q(self):
        while True:
            try: item = _G_Q.get_nowait()
            except queue.Empty: break
            if isinstance(item, tuple) and len(item) == 2:
                cb, res = item; cb(res)
        self.after(50, self._check_q)

    def _build_sidebar(self):
        sb=ctk.CTkFrame(self,width=230,fg_color=C["sidebar"],corner_radius=0); sb.pack(side="left",fill="y")
        sb.pack_propagate(False)

        logo=ctk.CTkFrame(sb,fg_color="transparent"); logo.pack(fill="x",pady=(20,8),padx=16)
        ctk.CTkLabel(logo,text="💠",font=ctk.CTkFont(size=40)).pack(anchor="w")
        ctk.CTkLabel(logo,text="GeoVista v3",font=ctk.CTkFont("Segoe UI",22,"bold"),text_color=C["primary"]).pack(anchor="w")
        ctk.CTkLabel(logo,text="V3 Professional GIS",font=ctk.CTkFont("Segoe UI",10,"bold"),text_color=C["sec"]).pack(anchor="w")
        ctk.CTkFrame(sb,height=1,fg_color=C["border"]).pack(fill="x",padx=16,pady=(10,14))

        for icon,label,key in NAV:
            btn=ctk.CTkButton(sb,text=f"  {icon}  {label}",anchor="w",
                              fg_color="transparent",hover_color=C["card2"],text_color=C["t2"],
                              font=ctk.CTkFont("Segoe UI",13),height=42,corner_radius=8,
                              command=lambda k=key:self.show(k))
            btn.pack(fill="x",padx=10,pady=1)
            self._nav_btns[key]=btn

        ctk.CTkFrame(sb,height=1,fg_color=C["border"]).pack(fill="x",padx=16,pady=10)
        self.mk_btn(sb,"💾 Projeyi Kaydet",self._save_proj,primary=False).pack(fill="x",padx=15,pady=5)
        self.mk_btn(sb,"📂 Proje Yükle",self._load_proj,primary=False).pack(fill="x",padx=15,pady=5)

        ctk.CTkLabel(sb,text="GeoVista v3.0.0",font=ctk.CTkFont("Segoe UI",10),text_color=C["t3"]).pack(side="bottom",pady=12)

    def _build_content(self):
        self._content=ctk.CTkFrame(self,fg_color=C["bg"],corner_radius=0)
        self._content.pack(side="left",fill="both",expand=True)
        builders={
            "dashboard": lambda: DashboardPage(self._content,self),
            "spatial":   lambda: SpatialLabPage(self._content,self),
            "geocoding": lambda: GeocodingPage(self._content),
            "map":       lambda: MapPage(self._content),
            "countries": lambda: CountriesPage(self._content),
            "tools":     lambda: CoordToolsPage(self._content),
            "weather":   lambda: WeatherPage(self._content),
            "elevation": lambda: ElevationPage(self._content,self),
            "safet":     lambda: SafetyLabPage(self._content,self),
            "about":     lambda: AboutPage(self._content),
        }
        for key,fn in builders.items():
            pg=fn(); pg.place(relx=0,rely=0,relwidth=1,relheight=1)
            self._pages[key]=pg

    def show(self,key):
        for k,pg in self._pages.items():
            pg.place_forget() if k!=key else pg.place(relx=0,rely=0,relwidth=1,relheight=1)
        for k,btn in self._nav_btns.items():
            if k==key:
                btn.configure(fg_color=C["card2"],text_color=C["primary"])
            else:
                btn.configure(fg_color="transparent",text_color=C["t2"])

    def mk_btn(self,p,text,cmd,primary=True,**kw):
        kw.setdefault("height",36); kw.setdefault("corner_radius",8)
        kw.setdefault("font",ctk.CTkFont("Segoe UI",12))
        fg=C["pbtn"] if primary else C["card2"]
        hv=C["hl"] if primary else C["border"]
        return ctk.CTkButton(p,text=text,command=cmd,fg_color=fg,hover_color=hv,text_color=C["t1"],**kw)

    def _save_proj(self):
        p=filedialog.asksaveasfilename(defaultextension=".gvproj", filetypes=[("GeoVista Project","*.gvproj")])
        if not p: return

        state = {"saved_at": str(datetime.now()), "pages_state": {}}
        try:
            with open(p,"w",encoding="utf-8") as f: json.dump(state,f)
            messagebox.showinfo("Proje","Proje başarıyla kaydedildi.")
        except: pass

    def _load_proj(self):
        p=filedialog.askopenfilename(filetypes=[("GeoVista Project","*.gvproj")])
        if not p: return
        messagebox.showinfo("Proje","Proje yüklendi.")

if __name__=="__main__":
    app=GeoVista(); app.mainloop()
