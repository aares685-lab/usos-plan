import flet as ft
import urllib.request
import ssl
from icalendar import Calendar
import datetime
import os
from collections import defaultdict
import re

def pobierz_kalendarz_z_linku(link_ical):
    try:
        ctx = ssl._create_unverified_context()
        req = urllib.request.Request(
            link_ical, 
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req, timeout=15, context=ctx) as response:
            cal_data = response.read()
        
        if b"BEGIN:VCALENDAR" not in cal_data:
            return None
        return cal_data
    except Exception as ex:
        print(f"Błąd pobierania kalendarza: {ex}")
        return None

def porownaj_kalendarze(stara_data, nowa_data):
    zmiany = []
    try:
        stary_cal = Calendar.from_ical(stara_data)
        nowy_cal = Calendar.from_ical(nowa_data)

        stare_zdarzenia = {}
        for comp in stary_cal.walk('vevent'):
            uid = str(comp.get('uid', ''))
            summary = str(comp.get('summary', ''))
            dtstart = comp.get('dtstart')
            location = str(comp.get('location', ''))
            description = str(comp.get('description', ''))
            if uid:
                stare_zdarzenia[uid] = (summary, dtstart.dt if dtstart else None, location, description)

        for comp in nowy_cal.walk('vevent'):
            uid = str(comp.get('uid', ''))
            summary = str(comp.get('summary', ''))
            dtstart = comp.get('dtstart')
            location = str(comp.get('location', ''))
            description = str(comp.get('description', ''))
            
            nowy_start = dtstart.dt if dtstart else None

            pelny_tekst = (location + " " + description).lower()
            czy_online = any(x in pelny_tekst for x in ["teams", "zoom", "online", "zdalnie"])
            tryb_str = "MS Teams / Online" if czy_online else ("Jagiellońska 59, 10-283 Olsztyn" if location.strip() else "Brak")

            if uid in stare_zdarzenia:
                stary_summary, stary_start, stara_lokalizacja, stary_opis = stare_zdarzenia[uid]
                stary_pelny = (stara_lokalizacja + " " + stary_opis).lower()
                stary_online = any(x in stary_pelny for x in ["teams", "zoom", "online", "zdalnie"])
                stary_tryb = "MS Teams / Online" if stary_online else ("Jagiellońska 59, 10-283 Olsztyn" if stara_lokalizacja.strip() else "Brak")

                roznice = []
                if stary_summary != summary:
                    roznice.append(f"Przedmiot: '{stary_summary}' ➔ '{summary}'")
                if stary_start != nowy_start:
                    stary_czas = stary_start.strftime('%d.%m %H:%M') if isinstance(stary_start, datetime.datetime) else str(stary_start)
                    nowy_czas = nowy_start.strftime('%d.%m %H:%M') if isinstance(nowy_czas, datetime.datetime) else str(nowy_czas)
                    roznice.append(f"Godzina: {stary_czas} ➔ {nowy_czas}")
                if stary_tryb != tryb_str:
                    roznice.append(f"Miejsce: {stary_tryb} ➔ {tryb_str}")

                if roznice:
                    zmiany.append(f"Zmiana w '{summary}': " + " | ".join(roznice))
            else:
                czas_nowy = nowy_start.strftime('%d.%m o %H:%M') if isinstance(nowy_start, datetime.datetime) else ""
                zmiany.append(f"Nowe zajęcia: {summary} ({czas_nowy}) – {tryb_str}")
    except Exception as e:
        print(f"Błąd porównywania: {e}")
    
    return zmiany

def main(page: ft.Page):
    aktualny_offset_tygodnia = 0
    tryb_ciemny = True

    page.title = "Vistula USOS Mobile"
    page.vertical_alignment = "center"
    page.horizontal_alignment = "center"
    page.bgcolor = "#121212"
    page.padding = 10

    tytul_tygodnia = ft.Text("Tydzień", size=13, weight="bold", color="#64b5f6")
    zawartosc_osi_czasu = ft.Column(spacing=0)

    scrollable_plan = ft.Row(
        [
            ft.Column(
                [zawartosc_osi_czasu],
                scroll=ft.ScrollMode.AUTO,
            )
        ],
        scroll=ft.ScrollMode.AUTO,
        expand=True
    )

    def powrot_do_planu(e):
        page.clean()
        page.add(ekran_glowny)
        wczytaj_i_wyswietl_tydzien()
        page.update()

    def pokaz_szczegoly_zajec(zajecie):
        elementy_szczegolow = [
            ft.Text(zajecie["summary"], size=16, weight="bold", color="#64b5f6"),
            ft.Divider(height=15, color="grey"),
            ft.Row([ft.Text("📌", size=14), ft.Text(f"Typ: {zajecie['typ']}", size=13, weight="bold", color="white" if tryb_ciemny else "black")], spacing=8),
            ft.Container(height=3),
            ft.Row([ft.Text("👥", size=14), ft.Text(f"Grupa: {zajecie['grupa']}", size=13, weight="bold", color="white" if tryb_ciemny else "black")], spacing=8),
            ft.Container(height=3),
            ft.Row([ft.Text("🏫", size=14), ft.Text(f"Miejsce: {zajecie['miejsce']}", size=13, weight="bold", color="white" if tryb_ciemny else "black")], spacing=8),
        ]

        if zajecie['miejsce'] != "MS Teams / Online":
            elementy_szczegolow.extend([
                ft.Container(height=3),
                ft.Row([ft.Text("📍", size=14), ft.Text(f"Sala: {zajecie['sala']}", size=13, weight="bold", color="white" if tryb_ciemny else "black")], spacing=8),
            ])

        elementy_szczegolow.extend([
            ft.Container(height=3),
            ft.Row([ft.Text("⏰", size=14), ft.Text(f"Godzina: {zajecie['g_start']} – {zajecie['g_koniec']}", size=13, weight="bold", color="white" if tryb_ciemny else "black")], spacing=8),
        ])

        ekran_szczegolow = ft.Column([
            ft.Row([
                ft.Text("Szczegóły zajęć", size=18, weight="bold"),
                ft.ElevatedButton("Powrót", on_click=powrot_do_planu)
            ], alignment="spaceBetween", width=380),
            ft.Container(height=10),
            ft.Container(
                content=ft.Column(elementy_szczegolow, spacing=6),
                width=380,
                bgcolor="#1e1e1e" if tryb_ciemny else "#fafafa",
                border_radius=10,
                padding=20
            )
        ], alignment="center", horizontal_alignment="center")

        page.clean()
        page.add(ekran_szczegolow)
        page.update()

    def zwroc_poniedzialek_i_niedziele(offset):
        dzis = datetime.date.today()
        poniedzialek = dzis - datetime.timedelta(days=dzis.weekday())
        poniedzialek_szukany = poniedzialek + datetime.timedelta(weeks=offset)
        niedziela_szukana = poniedzialek_szukany + datetime.timedelta(days=6)
        return poniedzialek_szukany, niedziela_szukana

    def wczytaj_i_wyswietl_tydzien():
        zawartosc_osi_czasu.controls.clear()

        cal_data = page.session.get("cal_data")
        if not cal_data:
            zawartosc_osi_czasu.controls.append(ft.Text("Brak pobranego planu. Kliknij 'Odśwież'.", color="red"))
            page.update()
            return

        try:
            cal = Calendar.from_ical(cal_data)
            p_pon, p_nied = zwroc_poniedzialek_i_niedziele(aktualny_offset_tygodnia)
            tytul_tygodnia.value = f"{p_pon.strftime('%d.%m')} - {p_nied.strftime('%d.%m.%Y')}"

            dni_zajecia = defaultdict(list)
            
            for component in cal.walk('vevent'):
                summary = str(component.get('summary', 'Zajęcia'))
                dtstart_comp = component.get('dtstart')
                dtend_comp = component.get('dtend')
                location = str(component.get('location', ''))
                description = str(component.get('description', ''))
                
                pelny_tekst_analiza = (summary + " " + description).lower()
                if "wykład" in pelny_tekst_analiza or summary.startswith("W "):
                    typ_zajec = "Wykład"
                elif "lab" in pelny_tekst_analiza:
                    typ_zajec = "Laboratorium"
                elif "ćwiczenia" in pelny_tekst_analiza or "cw" in pelny_tekst_analiza:
                    typ_zajec = "Ćwiczenia"
                else:
                    typ_zajec = "Zajęcia"

                grupa_str = "gr. 1"
                match_gr = re.search(r'(gr\.?\s*\d+|grupa\s*\d+)', pelny_tekst_analiza)
                if match_gr:
                    grupa_str = match_gr.group(0)

                pelny_lok_tekst = (location + " " + description).lower()
                czy_online = any(x in pelny_lok_tekst for x in ["teams", "zoom", "online", "zdalnie"])
                
                if czy_online:
                    miejsce_str = "MS Teams / Online"
                    sala_str = ""
                    kolor_miejsca = "#ce93d8" if tryb_ciemny else "#7b1fa2"
                    tekst_na_kafelku = "MS Teams / Online"
                else:
                    miejsce_str = "Jagiellońska 59, 10-283 Olsztyn"
                    sala_str = ""
                    szukany_tekst_sali = description + " " + location
                    nawiasy = re.findall(r'\(([0-9]+[a-zA-Z]?)\)', szukany_tekst_sali)
                    if nawiasy:
                        sala_str = nawiasy[0]
                    else:
                        match_sala = re.search(r'(?:sala[:\s]*)?\(?([0-9]+[a-zA-Z]?)\)?', szukany_tekst_sali, re.IGNORECASE)
                        if match_sala:
                            kandydat = match_sala.group(1)
                            if "10-283" not in kandydat:
                                sala_str = kandydat
                    
                    if not sala_str:
                        parts = [p.strip() for p in location.split(',') if p.strip()]
                        if parts and not any(x in parts[-1].lower() for x in ["jagiellońska", "olsztyn", "10-283"]):
                            sala_str = parts[-1]
                        else:
                            sala_str = "105"

                    kolor_miejsca = "#81c784" if tryb_ciemny else "#2e7d32"
                    tekst_na_kafelku = f"Sala: {sala_str}"
                
                if dtstart_comp:
                    dtstart = dtstart_comp.dt
                    if isinstance(dtstart, datetime.datetime):
                        data_zajec = dtstart.date()
                        start_min = dtstart.hour * 60 + dtstart.minute
                        g_start_str = dtstart.strftime("%H:%M")
                    else:
                        data_zajec = dtstart
                        start_min = 7 * 60
                        g_start_str = "07:00"

                    if dtend_comp:
                        dtend = dtend_comp.dt
                        if isinstance(dtend, datetime.datetime):
                            end_min = dtend.hour * 60 + dtend.minute
                            g_koniec_str = dtend.strftime("%H:%M")
                        else:
                            end_min = start_min + 90
                            g_koniec_str = ""
                    else:
                        end_min = start_min + 90
                        g_koniec_str = ""

                    duration_mins = max(45, end_min - start_min)
                    
                    if p_pon <= data_zajec <= p_nied:
                        dzien_indeks = data_zajec.weekday()
                        dni_zajecia[dzien_indeks].append({
                            "start_min": start_min,
                            "duration": duration_mins,
                            "g_start": g_start_str,
                            "g_koniec": g_koniec_str,
                            "summary": summary,
                            "typ": typ_zajec,
                            "grupa": grupa_str,
                            "miejsce": miejsce_str,
                            "sala": sala_str,
                            "tekst_kafelek": tekst_na_kafelku,
                            "kolor": kolor_miejsca
                        })

            nazwy_dni = ["Pon", "Wt", "Śr", "Cz", "Pt", "Sob", "Ndz"]
            
            nagłówek_row = [
                ft.Container(content=ft.Text("Godz", size=10, weight="bold", color="#888888"), width=45, padding=4)
            ]
            for i in range(7):
                data_dnia = p_pon + datetime.timedelta(days=i)
                nagłówek_row.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Text(nazwy_dni[i], size=11, weight="bold", color="#64b5f6"),
                            ft.Text(data_dnia.strftime("%d.%m"), size=9, color="#aaaaaa"),
                        ], spacing=1, horizontal_alignment="center"),
                        width=85,
                        padding=6,
                        bgcolor="#1e1e1e" if tryb_ciemny else "#e0e0e0",
                        border_radius=4
                    )
                )
            zawartosc_osi_czasu.controls.append(ft.Row(nagłówek_row, spacing=2))
            zawartosc_osi_czasu.controls.append(ft.Divider(height=5, color="transparent"))

            START_MINUTY = 7 * 60
            WYSOKOSC_OSI = 870
            PIKSELI_NA_MINUTE = 1.0

            kolumny_dni_stacks = []
            kolor_lini = "#262626" if tryb_ciemny else "#e5e5e5"

            godziny_kontrola = []
            for h in range(7, 22):
                godziny_kontrola.append(
                    ft.Container(
                        content=ft.Text(f"{h:02d}:00", size=9, weight="bold", color="#888888"),
                        padding=4,
                        height=60,
                        border=ft.Border(bottom=ft.BorderSide(1, kolor_lini))
                    )
                )
            
            lewa_kolumna_godzin = ft.Container(
                content=ft.Column(godziny_kontrola, spacing=0),
                width=45,
                height=WYSOKOSC_OSI
            )
            kolumny_dni_stacks.append(lewa_kolumna_godzin)

            kolor_tla_karty = "#2d2d2d" if tryb_ciemny else "#fff9c4"
            kolor_tla_komorki = "#161616" if tryb_ciemny else "#f8f9fa"
            kolor_tekstu = "#ffffff" if tryb_ciemny else "#000000"

            for dzien_idx in range(7):
                stack_kontrola = []
                
                tło_kolumny_kontrola = []
                for h in range(7, 22):
                    tło_kolumny_kontrola.append(
                        ft.Container(
                            height=60,
                            bgcolor=kolor_tla_komorki,
                            border=ft.Border(bottom=ft.BorderSide(1, kolor_lini), right=ft.BorderSide(1, kolor_lini))
                        )
                    )
                stack_kontrola.append(ft.Column(tło_kolumny_kontrola, spacing=0))

                for zajecie in dni_zajecia[dzien_idx]:
                    top_px = (zajecie["start_min"] - START_MINUTY) * PIKSELI_NA_MINUTE
                    wysokosc_px = zajecie["duration"] * PIKSELI_NA_MINUTE

                    kafelek = ft.Container(
                        content=ft.Column([
                            ft.Text(zajecie["summary"], size=9, weight="bold", color=kolor_tekstu, max_lines=3, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(zajecie["tekst_kafelek"], size=8, weight="w500", color=zajecie["kolor"]),
                            ft.Row([
                                ft.Text(f"⏰ {zajecie['g_start']}", size=7, color="#ffb74d"),
                                ft.Text(zajecie["g_koniec"], size=8, weight="bold", color="#ffb74d")
                            ], alignment="spaceBetween")
                        ], spacing=2, alignment="spaceBetween", expand=True),
                        top=top_px,
                        left=2,
                        width=81,
                        height=wysokosc_px,
                        bgcolor=kolor_tla_karty,
                        border_radius=5,
                        padding=6,
                        on_click=lambda e, z=zajecie: pokaz_szczegoly_zajec(z)
                    )
                    stack_kontrola.append(kafelek)

                dzien_stack = ft.Container(
                    content=ft.Stack(stack_kontrola, width=85, height=WYSOKOSC_OSI),
                    width=85,
                    height=WYSOKOSC_OSI,
                    clip_behavior=ft.ClipBehavior.NONE
                )
                kolumny_dni_stacks.append(dzien_stack)

            zawartosc_osi_czasu.controls.append(
                ft.Row(kolumny_dni_stacks, spacing=0, vertical_alignment="start")
            )

        except Exception as ex:
            zawartosc_osi_czasu.controls.append(ft.Text(f"Błąd ładowania planu: {ex}", color="red"))
        
        page.update()

    def nastepny_tydzien(e):
        nonlocal aktualny_offset_tygodnia
        aktualny_offset_tygodnia += 1
        wczytaj_i_wyswietl_tydzien()

    def poprzedni_tydzien(e):
        nonlocal aktualny_offset_tygodnia
        aktualny_offset_tygodnia -= 1
        wczytaj_i_wyswietl_tydzien()

    def wyloguj(e):
        page.client_storage.remove("usos_link")
        page.session.clear()
        page.clean()
        page.add(ekran_konfiguracji)
        page.update()

    def odswiez_plan_klikniety(e):
        link = page.client_storage.get("usos_link")
        if link:
            nowa_data = pobierz_kalendarz_z_linku(link)
            if nowa_data:
                stara_data = page.session.get("cal_data")
                if stara_data and stara_data != nowa_data:
                    zmiany = porownaj_kalendarze(stara_data, nowa_data)
                    if zmiany:
                        istniejace_pow = page.session.get("powiadomienia", [])
                        page.session.set("powiadomienia", istniejace_pow + zmiany)

                page.session.set("cal_data", nowa_data)
                wczytaj_i_wyswietl_tydzien()
            else:
                page.clean()
                page.add(ekran_konfiguracji)
                page.update()
        else:
            page.clean()
            page.add(ekran_konfiguracji)
            page.update()

    def przelacz_tryb_graficzny(e):
        nonlocal tryb_ciemny
        tryb_ciemny = not tryb_ciemny
        page.bgcolor = "#121212" if tryb_ciemny else "#ffffff"
        wczytaj_i_wyswietl_tydzien()
        page.update()

    powiadomienia_lista = ft.ListView(expand=True, spacing=10, padding=10)

    def dodaj_testowe_powiadomienie(e):
        istniejace_pow = page.session.get("powiadomienia", [])
        istniejace_pow.append("Zmiana testowa: Sala 105 ➔ MS Teams / Online")
        page.session.set("powiadomienia", istniejace_pow)
        otworz_ekran_powiadomien(e)

    def wyczysc_powiadomienia(e):
        page.session.set("powiadomienia", [])
        otworz_ekran_powiadomien(e)

    def otworz_ekran_powiadomien(e):
        powiadomienia_lista.controls.clear()
        powiadomienia_lista.controls.append(
            ft.Row([
                ft.ElevatedButton("➕ Test", on_click=dodaj_testowe_powiadomienie),
                ft.ElevatedButton("🗑️ Wyczyść", on_click=wyczysc_powiadomienia)
            ], alignment="spaceBetween")
        )

        zmiany = page.session.get("powiadomienia", [])
        if zmiany:
            for z in zmiany:
                powiadomienia_lista.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Text("🔔 Zmiana w planie!", weight="bold", color="black", size=13),
                            ft.Divider(height=1, color="#d0e1fd"),
                            ft.Text(z, size=12, color="#333333"),
                        ], spacing=4),
                        padding=10,
                        bgcolor="#e3f2fd",
                        border_radius=8
                    )
                )
        else:
            powiadomienia_lista.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Text("✅ Brak zmian", weight="bold", color="black", size=13),
                        ft.Divider(height=1, color="#d0d0d0"),
                        ft.Text("Wszystkie terminy i sale są aktualne.", size=12, color="grey"),
                    ], spacing=4),
                    padding=10,
                    bgcolor="#f1f8e9",
                    border_radius=8
                )
            )

        page.clean()
        page.add(
            ft.Column([
                ft.Row([
                    ft.Text("Powiadomienia o zmianach", size=18, weight="bold"),
                    ft.ElevatedButton("Powrót", on_click=powrot_do_planu_z_powiadomien)
                ], alignment="spaceBetween", width=380),
                ft.Container(height=10),
                ft.Container(
                    content=powiadomienia_lista,
                    width=380,
                    height=450,
                    bgcolor="#1e1e1e" if tryb_ciemny else "#fafafa",
                    border_radius=10,
                    padding=5
                )
            ], alignment="center", horizontal_alignment="center")
        )
        page.update()

    def powrot_do_planu_z_powiadomien(e):
        page.clean()
        page.add(ekran_glowny)
        wczytaj_i_wyswietl_tydzien()

    ical_input = ft.TextField(
        label="Wklej link iCal z USOSweb",
        width=330,
        hint_text="https://usosweb.vistula.edu.pl/ical/..."
    )
    info_link = ft.Text("", color="red", size=12)

    def zapisz_i_przejdz(e):
        link = ical_input.value.strip()
        if not link:
            info_link.value = "Najpierw wklej link!"
            page.update()
        else:
            cal_data = pobierz_kalendarz_z_linku(link)
            if cal_data:
                page.client_storage.set("usos_link", link)
                page.session.set("cal_data", cal_data)
                page.session.set("powiadomienia", [])
                page.clean()
                page.add(ekran_glowny)
                wczytaj_i_wyswietl_tydzien()
            else:
                info_link.value = "Błąd pobierania (sprawdź link)"
                page.update()

    ekran_konfiguracji = ft.Column([
        ft.Text("Vistula USOS - Konfiguracja", size=18, weight="bold"),
        ft.Text("Wklej swój link iCal (prywatny):", size=12, color="grey"),
        ft.Container(height=10),
        ical_input,
        info_link,
        ft.Container(height=10),
        ft.ElevatedButton("Zapisz i pobierz plan", on_click=zapisz_i_przejdz)
    ], alignment="center", horizontal_alignment="center", spacing=10)

    global ekran_glowny
    ekran_glowny = ft.Column([
        ft.Row([
            ft.ElevatedButton("◄", on_click=poprzedni_tydzien),
            tytul_tygodnia,
            ft.ElevatedButton("►", on_click=nastepny_tydzien),
        ], alignment="center", spacing=20, width=380),

        ft.Container(height=5),
        
        ft.Container(
            content=scrollable_plan,
            width=380,
            height=530,
            border_radius=8,
            padding=5
        ),

        ft.Container(height=5),

        ft.Row([
            ft.ElevatedButton("🔄", on_click=odswiez_plan_klikniety, tooltip="Odśwież"),
            ft.ElevatedButton("🌙/☀️", on_click=przelacz_tryb_graficzny),
            ft.ElevatedButton("🔔", on_click=otworz_ekran_powiadomien),
            ft.ElevatedButton("🚪 Wyloguj", on_click=wyloguj, color="red")
        ], alignment="spaceBetween", width=380)
    ], alignment="center", horizontal_alignment="center", expand=True)

    # Automatyczne logowanie przy starcie z zapisanego linku w pamięci przeglądarki
    zapisany_link = page.client_storage.get("usos_link")
    if zapisany_link:
        cal_data = pobierz_kalendarz_z_linku(zapisany_link)
        if cal_data:
            page.session.set("cal_data", cal_data)
            page.add(ekran_glowny)
            wczytaj_i_wyswietl_tydzien()
        else:
            page.add(ekran_konfiguracji)
    else:
        page.add(ekran_konfiguracji)

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8080))
    ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=port)
