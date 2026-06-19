"""Baut sources/data/schmieder_full.csv aus der Kliniken-Schmieder-Preisliste
(Anlage 1 RV 19110252_4, 2025-2027). Verifiziert gegen die PDF-Zwischensummen.

Spalten: klinik, haus, standort_im_betrieb, gewerk_rv, gewerk_info, eq,
turnus_jahre, einzelpreis_eur, anteil_jahr_eur, in_scope_elektro, kommentar
"""
import csv
import os

# (klinik, haus, standort, gewerk_rv, gewerk_info, eq, turnus, einzel, jahr, kommentar)
ROWS = [
    # ── Allensbach ──
    ("Allensbach","Bodan","Haus Bodan groß","Aufzugsanlagen","Personenaufzug","1333863",1,382,382,""),
    ("Allensbach","Säntis","Haus Arlberg","Aufzugsanlagen","Personenaufzug","1388121",1,382,382,""),
    ("Allensbach","Bodan","Haus Bodan klein","Aufzugsanlagen","Personenaufzug","1395761",1,382,382,""),
    ("Allensbach","Bodan","Haus Bodan klein","Aufzugsanlagen AwSV","Personenaufzug","1395761",2.5,1026,411,""),
    ("Allensbach","Höri","Haus Höri klein","Aufzugsanlagen","Personenaufzug","1395791",1,382,382,""),
    ("Allensbach","Höri","Haus Höri klein","Aufzugsanlagen AwSV","Personenaufzug","1395791",2.5,1026,411,""),
    ("Allensbach","Säntis","Haus Säntis groß","Aufzugsanlagen","Personenaufzug","1395808",1,382,382,""),
    ("Allensbach","Säntis","Haus Säntis klein","Aufzugsanlagen","Personenaufzug","1395825",1,382,382,""),
    ("Allensbach","Thurgau","Haus Thurgau","Aufzugsanlagen","Personenaufzug","1395839",1,382,382,""),
    ("Allensbach","Mainau","Haus Mainau, Lasten groß","Aufzugsanlagen","Personenaufzug","1395854",1,382,382,""),
    ("Allensbach","Mainau","Haus Mainau klein","Aufzugsanlagen","Personenaufzug","1395869",1,382,382,""),
    ("Allensbach","Säntis","Haus Säntis, Anbau West","Aufzugsanlagen","Personenaufzug","1402118",1,382,382,""),
    ("Allensbach","Höri","Hau Höri / Werkstatt","Aufzugsanlagen","Personenaufzug","1426818",1,382,382,""),
    ("Allensbach","Lindau","Haus Lindau groß","Aufzugsanlagen","Personenaufzug","1446632",1,382,382,""),
    ("Allensbach","Lindau","Haus Lindau klein","Aufzugsanlagen","Personenaufzug","1446642",1,382,382,""),
    ("Allensbach","Davos","Haus Davos","Aufzugsanlagen","Personenaufzug","2560471",1,382,382,""),
    ("Allensbach","Säntis","Haus Säntis Druckluftzentrale","Druckgerät","Druckluftbehälter","2643532",5,720,144,""),
    ("Allensbach","Säntis","Haus Säntis Druckluftzentrale","Druckanlage","Druckanlage zu EQ 2643532 + 1910278","2643533",5,138,28,"Ab 2025: Preis inkl. Abfrage Cybersicherheit-Doku"),
    ("Allensbach","Säntis","Haus Säntis Druckluftzentrale","Druckbehälter","Druckbehälter","1910278",5,720,144,""),
    ("Allensbach","Bodan","Haus Bodan Nordseite Erdtank","Heizölverb","Heizölverb","1088144",2.5,321,128,""),
    ("Allensbach","Thurgau","Haus Thurgau","Kraftbetät. Tor","Rollgittertor","2063103",1,197,197,""),
    ("Allensbach","alle Häuser","Gesamter Standort","el. Anlage 3602 VdS","el. Anlage 3602 VdS","1268824",4,5880,1470,""),
    ("Allensbach","Lindau/Davos/Thurgau","Treppenräume Lindau/Davos/Thurgau (6 Anlagen)","Nat.Rauchabzug","Nat.Rauchabzug","2508630",3,2184,728,""),
    ("Allensbach","Bodan","Bodan","Brandmeldeanlage","BMA","3127515",3,1414,471,"Prüfung gemäß Baurecht"),
    ("Allensbach","Bodan","Bodan","Sicherheitsbeleuchtung","SiBe","2650790",3,1218,406,"Prüfung gemäß Baurecht"),
    ("Allensbach","Davos","Davos","Brandmeldeanlage","BMA","2445724",3,1414,471,"Prüfung gemäß Baurecht"),
    ("Allensbach","Davos","Davos","Sicherheitsbeleuchtung","SiBe","3225322",3,1218,406,"Prüfung gemäß Baurecht"),
    ("Allensbach","Mainau","Mainau","Brandmeldeanlage","BMA","3249928",3,1665,555,"Prüfung gemäß Baurecht"),
    ("Allensbach","Mainau","Mainau","Sicherheitsbeleuchtung","SiBe","3225324",3,1414,471,"Prüfung gemäß Baurecht"),
    # ── Gailingen ──
    ("Gailingen","alle Häuser","Gesamter Standort","el. Anlage 3602 VdS","el. Anlage 3602 VdS","1267027",4,5445,1361,"Master-EQ 1267027 (WK VdS); EQ 3019427 = einmalig Inbetriebnahme"),
    ("Gailingen","Tirol","Haus Tirol klein","Aufzugsanlagen","Personenaufzug","1405411",1,382,382,""),
    ("Gailingen","Tirol","Haus Tirol groß","Aufzugsanlagen","Personenaufzug","1405426",1,382,382,""),
    ("Gailingen","Tirol","Haus Tirol","Aufzugsanlagen","Personenaufzug","1405440",1,382,382,""),
    ("Gailingen","Württemberg","HAUS WÜRTTEMBERG","Aufzugsanlagen","Personenaufzug","1405500",1,382,382,""),
    ("Gailingen","Österreich","Haus Österreich","Aufzugsanlagen","Personenaufzug","1405514",1,382,382,""),
    ("Gailingen","Bayern","HAUS BAYERN","Aufzugsanlagen","Personenaufzug","1405528",1,382,382,""),
    ("Gailingen","Schwarzwald","Haus Schwarzwald","Aufzugsanlagen","Personenaufzug","1405542",1,382,382,""),
    ("Gailingen","Baden","Haus Baden","Aufzugsanlagen","Personenaufzug","3126087",1,382,382,""),
    ("Gailingen","Hohentwiel","","Heizöltank","20.000 l","2956553",5,321,64,""),
    ("Gailingen","Tirol","Haus Tirol (mit Explosionszünder)","Nat.Rauchabzug","Nat.Rauchabzug","2508624",3,759,253,""),
    ("Gailingen","Baden","Foyer und Speisesaal","Nat.Rauchabzug","Nat.Rauchabzug","3355480",3,1363,454,""),
    ("Gailingen","Hohentwiel","Energiezentrale UG","Brandschutzklappe","Brandschutzklappe","2894773",3,1810,603,""),
    ("Gailingen","Baden","Baden","Brandmeldeanlage","BMA","3019424",3,1414,471,"Prüfung gemäß Baurecht"),
    ("Gailingen","Baden","Baden","Sicherheitsbeleuchtung","SiBe","3019426",3,1414,471,"Prüfung gemäß Baurecht"),
    ("Gailingen","Hohentwiel","Energiezentrale UG","Brandmeldeanlage","BMA","2890010",3,820,273,"Prüfung gemäß Baurecht"),
    ("Gailingen","Hohentwiel","Energiezentrale UG","Sicherheitsbeleuchtung","SiBe","2890012",3,580,193,"Prüfung gemäß Baurecht"),
    # ── Gerlingen ──
    ("Gerlingen","Gerlingen","im Klinikgebäude","Aufzugsanlagen","Personenaufzug","2135634",1,382,382,""),
    ("Gerlingen","Gerlingen","Links, Groß","Aufzugsanlagen","Personenaufzug","1378086",1,382,382,""),
    ("Gerlingen","Gerlingen","Rechts, Klein","Aufzugsanlagen","Personenaufzug","1378106",1,382,382,""),
    ("Gerlingen","S28","Fabrik Nr. 1810011","Aufzugsanlagen","Personenaufzug","2973316",1,382,382,""),
    ("Gerlingen","S28","Fabrik Nr. 1810012","Aufzugsanlagen","Personenaufzug","2973317",1,382,382,""),
    ("Gerlingen","alle Häuser","Gesamter Standort","el. Anlage 3602 VdS","el. Anlage 3602 VdS","2122745",4,2129,532,"Master-EQ 2122745 (WK VdS); EQ 2798427 = einmalig Inbetriebnahme"),
    ("Gerlingen","Gerlingen","3 Treppenräume + Aufzugsschacht + Haus Bärensee","Nat.Rauchabzug","Nat.Rauchabzug","3047347",3,3800,1267,""),
    ("Gerlingen","alle Häuser","Gesamter Standort","Brandmeldeanlage","BMA","3033107",3,3227,1076,"Prüfung gemäß Baurecht"),
    ("Gerlingen","alle Häuser","Gesamter Standort","Sicherheitsbeleuchtung","SiBe","3033105",3,2151,717,"Prüfung gemäß Baurecht"),
    # ── Heidelberg ──
    ("Heidelberg","alle Häuser","Gesamter Standort","el. Anlage 3602 VdS","el. Anlage 3602 VdS","1879930",4,5880,1470,"Master-EQ 1879930 (WK VdS); EQ 2805355 = einmalig Inbetriebnahme"),
    ("Heidelberg","Heidelberg","Haus Heidelberg","Aufzugsanlagen","Personenaufzug","1214122",1,382,382,""),
    ("Heidelberg","Heidelberg","Haus Heidelberg","Aufzugsanlagen","Personenaufzug","1359792",1,382,382,""),
    ("Heidelberg","Odenwald","Haus Odenwald","Aufzugsanlagen","Personenaufzug","1314965",1,382,382,""),
    ("Heidelberg","Neckar","Küche","Aufzugsanlagen","Personenaufzug","1214135",1,382,382,""),
    ("Heidelberg","Odenwald","Haus Odenwald","Aufzugsanlagen","Personenaufzug","1446237",1,382,382,""),
    ("Heidelberg","Mannheim","Haus Mannheim","Aufzugsanlagen","Personenaufzug","2355357",1,382,382,""),
    ("Heidelberg","Mannheim","Erweiterung Speyerer Hof","Aufzugsanlagen","Personenaufzug","2760531",1,382,382,""),
    ("Heidelberg","Technikzentrale","Haus Odenwald, Technikzentrale","Druckbehälter","Druckbehälter","1911031",5,720,144,""),
    ("Heidelberg","Neckar","Stations- und Zentralbau","Druckanlage","Druckanlage zu EQ 1911031","",5,138,28,"Ab 2025: Preis inkl. Abfrage Cybersicherheit-Doku"),
    ("Heidelberg","Odenwald","Haus Odenwald, Technikzentrale","Druckbehälter","Druckbehälter","1911033",5,720,144,""),
    ("Heidelberg","Odenwald","Haus Odenwald, Technikzentrale","Druckanlage","Druckanlage zu EQ 1911033","",5,138,28,"Ab 2025: Preis inkl. Abfrage Cybersicherheit-Doku"),
    ("Heidelberg","Neckar","Scherenhubtisch","Hebebühne","Hebebühne","2147461",2,255,127,""),
    ("Heidelberg","Mannheim","Haus Mannheim","Lüft.Garage","bis 75 Stellplätze","2508618",3,945,315,""),
    ("Heidelberg","Mannheim","Treppenhaus 2 - Bestand","Nat.Rauchabzug","Nat.Rauchabzug","3178371",3,609,203,"EQ 3178371 (4 TRH-Anlagen gebündelt)"),
    ("Heidelberg","Mannheim","Treppenhaus 3 - TRH Mitte","Nat.Rauchabzug","Nat.Rauchabzug","3178371",3,609,203,"EQ 3178371 (4 TRH-Anlagen gebündelt)"),
    ("Heidelberg","Mannheim","Treppenhaus 3 - TRH Nord","Nat.Rauchabzug","Nat.Rauchabzug","3178371",3,609,203,"EQ 3178371 (4 TRH-Anlagen gebündelt)"),
    ("Heidelberg","Mannheim","Lüftungszentrale im 4. OG","Nat.Rauchabzug","Nat.Rauchabzug","3178371",3,609,203,"EQ 3178371 (4 TRH-Anlagen gebündelt)"),
    ("Heidelberg","Mannheim","1. und 2. Bauabschnitt","Brandmeldeanlage","BMA","2809691",3,4612,1537,"Prüfung gemäß Baurecht"),
    ("Heidelberg","Mannheim","1. und 2. Bauabschnitt","Sicherheitsbeleuchtung","SiBe","2809692",3,3689,1230,"Prüfung gemäß Baurecht; inkl. Garage unter Haus Mannheim"),
    # ── Konstanz ──
    ("Konstanz","alle Häuser","Tiefgarage","Lüft.Garage","bis 75 Stellplätze","1233900",3,945,315,""),
    ("Konstanz","alle Häuser","Gesamter Standort","el. Anlage 3602 VdS","el. Anlage 3602 VdS","1268813",4,2151,538,""),
    ("Konstanz","alle Häuser","Treppenräume Bauteil A und B","Nat.Rauchabzug","Nat.Rauchabzug","2508627",3,846,282,""),
    ("Konstanz","Bauteil A","Gebäude Wandelhalle Östlich","Aufzugsanlagen","Personenaufzug","1303803",1,382,382,""),
    ("Konstanz","Bauteil A","Gebäude Wandelhalle Östlich","Aufzugsanlagen","Personenaufzug","1303825",1,382,382,""),
    ("Konstanz","Bauteil A","Küche Anlieferung","Aufzugsanlagen","Güteraufzug","1303846",1,382,382,""),
    ("Konstanz","Bauteil D","Aufzug","Aufzugsanlagen","Personenaufzug","2774267",1,382,382,""),
    ("Konstanz","Bauteil D","Treppenräume Bauteil D (1 Großanlage)","Nat.Rauchabzug","Nat.Rauchabzug","2954841",3,846,282,""),
    ("Konstanz","alle Häuser","Erdtank Nordseite","Heizölverb","Heizölverb","988337",5,321,64,""),
    ("Konstanz","alle Häuser","Tiefgarage","Kraftbetät. Tor","Kraftbetät. Tor","2165412",1,197,197,""),
    ("Konstanz","Bettenhaus","Neubau","Lüftung","Lüftung","2807546",3,3090,1030,""),
    ("Konstanz","Bauteil D","Bauteil D","Brandmeldeanlage","BMA","2817680",3,1665,555,"Prüfung gemäß Baurecht"),
    ("Konstanz","Bauteil D","Bauteil D","Sicherheitsbeleuchtung","SiBe","2817679",3,1665,555,"Prüfung gemäß Baurecht"),
    # ── Stuttgart ──
    ("Stuttgart","alle Häuser","Gesamter Standort","el. Anlage 3602 VdS","el. Anlage 3602 VdS","2122743",4,655,164,""),
    ("Stuttgart","alle Häuser","Durchgang zu Anbau Röteslberg","Aufzugsanlagen","Personenaufzug","1404661",1,382,382,""),
]

# PDF-Zwischensummen je Standort (Einzelpreis-Summe, Jahres-Summe) zur Verifikation
PDF_SUBTOTAL = {
    "Allensbach": (25901, 11786), "Gailingen": (16980, 7200),
    "Gerlingen": (13217, 5501), "Heidelberg": (22207, 8508),
    "Konstanz": (13255, 5346), "Stuttgart": (1036, 545),
}
PDF_TOTAL = (92597, 38886)

HEADER = ["klinik","haus","standort_im_betrieb","gewerk_rv","gewerk_info",
          "eq","turnus_jahre","einzelpreis_eur","anteil_jahr_eur",
          "in_scope_elektro","kommentar"]

def main():
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schmieder_full.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        for (k,h,s,gr,gi,eq,t,e,j,c) in ROWS:
            in_scope = "ja" if "3602" in gr else "nein"
            w.writerow([k,h,s,gr,gi,eq,t,e,j,in_scope,c])
    print(f"geschrieben: {out}  ({len(ROWS)} Zeilen)")

    # Verifikation gegen PDF-Zwischensummen.
    # Toleranz: die PDF zeigt €-gerundete Zellen, summiert aber die Cent-Werte
    # → ±wenige € je Standort sind Rundung, kein Transkriptionsfehler
    # (Beweis: Stuttgart 655+382=1037 eindeutig, PDF-Summe 1036).
    TOL_SITE, TOL_TOTAL = 5, 12
    print("\n=== Verifikation gegen PDF-Zwischensummen (Toleranz = PDF-Rundung) ===")
    ok = True
    tot_e = tot_j = 0
    for ort,(pe,pj) in PDF_SUBTOTAL.items():
        rows = [r for r in ROWS if r[0]==ort]
        se = sum(r[7] for r in rows); sj = sum(r[8] for r in rows)
        tot_e += se; tot_j += sj
        de, dj = se-pe, sj-pj
        within = abs(de) <= TOL_SITE and abs(dj) <= TOL_SITE
        flag = f"✓ (Rundung Δ{de:+d}/{dj:+d})" if within else f"✗ Δeinzel={de} Δjahr={dj}"
        if not within: ok = False
        print(f"  {ort:12} Einzel {se:>6} (PDF {pe}) · Jahr {sj:>6} (PDF {pj})  {flag}")
    dt_e, dt_j = tot_e-PDF_TOTAL[0], tot_j-PDF_TOTAL[1]
    tot_ok = abs(dt_e) <= TOL_TOTAL and abs(dt_j) <= TOL_TOTAL
    if not tot_ok: ok = False
    print(f"  {'GESAMT':12} Einzel {tot_e:>6} (PDF {PDF_TOTAL[0]}) · Jahr {tot_j:>6} (PDF {PDF_TOTAL[1]})  "
          f"{'✓ (Rundung Δ%+d/%+d)' % (dt_e, dt_j) if tot_ok else '✗'}")

    # VdS-Elektro-Anker (in scope)
    print("\n=== VdS-Elektro-Anker (in_scope_elektro=ja) ===")
    for r in ROWS:
        if "3602" in r[3]:
            print(f"  {r[0]:12} EQ {r[5]:>8}  {r[7]:>6} €/Prüf  {r[8]:>5} €/J")
    print("\nOK — alle Standorte innerhalb PDF-Rundungstoleranz (Transkription verifiziert)."
          if ok else "\nABWEICHUNG > Toleranz — Transkription prüfen!")

if __name__ == "__main__":
    main()
