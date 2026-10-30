# Ekran powiadomień jako pełnoprawny widok z zabezpieczeniem listy
    def otworz_ekran_powiadomien(e):
        powiadomienia_lista = ft.ListView(expand=True, spacing=10, padding=10)

        def dodaj_testowe(ev):
            istniejace_pow = page.session.get("powiadomienia")
            if not istniejace_pow:
                istniejace_pow = []
            istniejace_pow.append("Zmiana testowa: Sala 105 ➔ MS Teams / Online")
            page.session.set("powiadomienia", istniejace_pow)
            page.client_storage.set("powiadomienia", json.dumps(istniejace_pow))
            otworz_ekran_powiadomien(ev)

        def wyczysc_pow(ev):
            page.session.set("powiadomienia", [])
            page.client_storage.set("powiadomienia", json.dumps([]))
            otworz_ekran_powiadomien(ev)

        powiadomienia_lista.controls.append(
            ft.Row([
                ft.ElevatedButton("➕ Test", on_click=dodaj_testowe),
                ft.ElevatedButton("🗑️ Wyczyść", on_click=wyczysc_pow)
            ], alignment="spaceBetween")
        )

        # Bezpieczne pobranie powiadomień z sesji
        zmiany = page.session.get("powiadomienia")
        if not zmiany:
            zmiany = []

        if zmiany:
            for z in zmiany:
                powiadomienia_lista.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Text("🔔 Zmiana w planie!", weight="bold", color="black", size=13),
                            ft.Divider(height=1, color="#d0e1fd"),
                            ft.Text(str(z), size=12, color="#333333"),
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

        ekran_pow = ft.Column([
            ft.Row([
                ft.Text("Powiadomienia o zmianach", size=18, weight="bold"),
                ft.ElevatedButton("Powrót", on_click=powrot_do_planu)
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

        page.clean()
        page.add(ekran_pow)
        page.update()
