# ============================================================
# gui/pesaje/corte_view.py — Corte de Pesadas
# ============================================================

import customtkinter as ctk
from tkinter import messagebox
from services.pesaje_service import realizar_corte, get_kardex
from datetime import datetime
from database.engine import SessionLocal
from database.models import Corte
from config import UI


class CorteView(ctk.CTkFrame):
    """Pantalla para realizar y consultar cortes de pesadas."""

    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._construir()

    def _construir(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ---- Panel izquierdo: resumen y acción ----
        left = ctk.CTkFrame(
            self,
            fg_color=UI["color_card"],
            border_color=UI["color_border"],
            border_width=1,
            corner_radius=12
        )
        left.grid(row=0, column=0, sticky="nsew", padx=(20, 10), pady=20)

        ctk.CTkLabel(
            left, text="✂️  CORTE DE PESADAS",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=UI["color_warning"]
        ).pack(padx=20, pady=(20, 5), anchor="w")

        ctk.CTkLabel(
            left,
            text="Un corte cierra el período actual y genera\n"
                 "un resumen de todas las pesadas completadas\n"
                 "desde el último corte.",
            font=ctk.CTkFont(size=12),
            text_color=UI["color_muted"],
            justify="left"
        ).pack(padx=20, pady=(5, 15), anchor="w")

        ctk.CTkFrame(left, height=1, fg_color=UI["color_border"]).pack(
            fill="x", padx=15, pady=(0, 15))

        # Resumen del período actual
        resumen = self._calcular_resumen()

        info_frame = ctk.CTkFrame(left, fg_color=UI["color_bg"], corner_radius=10)
        info_frame.pack(fill="x", padx=20, pady=(0, 15))

        self._lbl_desde = self._item_info(
            info_frame, "📅 Desde:", resumen["desde"])
        self._item_info(info_frame, "📅 Hasta:",
                        datetime.now().strftime("%d/%m/%Y %H:%M"))
        self._item_info(info_frame, "✅ Pesadas completas:",
                        str(resumen["total_pesadas"]))
        self._item_info(info_frame, "⚖️ Total neto:",
                        f"{resumen['total_neto']:,.2f} KG")
        self._item_info(info_frame, "✂️ Último corte:",
                        str(resumen["ultimo_numero"]))

        # Observaciones
        ctk.CTkLabel(
            left, text="Observaciones del corte:",
            font=ctk.CTkFont(size=12), text_color=UI["color_muted"], anchor="w"
        ).pack(fill="x", padx=20, pady=(0, 4))

        self._txt_obs = ctk.CTkTextbox(left, height=80, font=ctk.CTkFont(size=12))
        self._txt_obs.pack(fill="x", padx=20, pady=(0, 15))

        # Botón de corte
        ctk.CTkButton(
            left,
            text="✂️  REALIZAR CORTE AHORA",
            command=self._hacer_corte,
            height=52,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color=UI["color_warning"],
            hover_color=UI["color_accent_hover"],
            corner_radius=10
        ).pack(fill="x", padx=20, pady=(0, 20))

        # ---- Panel derecho: historial de cortes ----
        right = ctk.CTkFrame(
            self,
            fg_color=UI["color_card"],
            border_color=UI["color_border"],
            border_width=1,
            corner_radius=12
        )
        right.grid(row=0, column=1, sticky="nsew", padx=(10, 20), pady=20)
        right.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            right, text="📜 Historial de Cortes",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=UI["color_text"]
        ).grid(row=0, column=0, padx=18, pady=(15, 5), sticky="w")

        self._scroll_cortes = ctk.CTkScrollableFrame(
            right, fg_color="transparent")
        self._scroll_cortes.grid(row=1, column=0, sticky="nsew",
                                  padx=10, pady=(0, 10))
        self._scroll_cortes.grid_columnconfigure(0, weight=1)
        right.grid_columnconfigure(0, weight=1)

        self._cargar_historial()

    def _item_info(self, parent, etiqueta, valor):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(fill="x", padx=12, pady=4)
        ctk.CTkLabel(f, text=etiqueta, font=ctk.CTkFont(size=11),
                     text_color=UI["color_muted"], width=150, anchor="w").pack(side="left")
        lbl = ctk.CTkLabel(f, text=valor, font=ctk.CTkFont(size=12, weight="bold"),
                            text_color=UI["color_text"])
        lbl.pack(side="left")
        return lbl

    def _calcular_resumen(self) -> dict:
        """Calcula el resumen del período pendiente de corte."""
        db = SessionLocal()
        try:
            ultimo = db.query(Corte).order_by(Corte.id.desc()).first()
            desde = ultimo.fecha_fin if ultimo else datetime(2000, 1, 1)
            desde_str = desde.strftime("%d/%m/%Y %H:%M") if ultimo else "Inicio"
            num = ultimo.numero_corte if ultimo else 0

            pesadas = get_kardex(fecha_inicio=desde, estado="completada")
            total_neto = sum(float(p.peso_neto or 0) for p in pesadas)

            return {
                "desde": desde_str,
                "total_pesadas": len(pesadas),
                "total_neto": total_neto,
                "ultimo_numero": num
            }
        finally:
            db.close()

    def _cargar_historial(self):
        """Carga el historial de cortes previos."""
        for w in self._scroll_cortes.winfo_children():
            w.destroy()

        db = SessionLocal()
        try:
            cortes = db.query(Corte).order_by(Corte.id.desc()).limit(20).all()

            if not cortes:
                ctk.CTkLabel(
                    self._scroll_cortes,
                    text="No hay cortes realizados aún",
                    font=ctk.CTkFont(size=12),
                    text_color=UI["color_muted"]
                ).pack(pady=30)
                return

            for c in cortes:
                card = ctk.CTkFrame(
                    self._scroll_cortes,
                    fg_color=UI["color_bg"], corner_radius=8
                )
                card.pack(fill="x", pady=3, padx=5)

                ctk.CTkLabel(
                    card,
                    text=f"✂️ Corte #{c.numero_corte}",
                    font=ctk.CTkFont(size=13, weight="bold"),
                    text_color=UI["color_warning"]
                ).pack(anchor="w", padx=12, pady=(8, 2))

                desde = c.fecha_inicio.strftime("%d/%m/%Y %H:%M") if c.fecha_inicio else "—"
                hasta = c.fecha_fin.strftime("%d/%m/%Y %H:%M") if c.fecha_fin else "—"

                ctk.CTkLabel(
                    card,
                    text=f"📅 {desde} → {hasta}",
                    font=ctk.CTkFont(size=11),
                    text_color=UI["color_muted"]
                ).pack(anchor="w", padx=12)

                ctk.CTkLabel(
                    card,
                    text=f"✅ {c.total_pesadas} pesadas  |  ⚖️ {float(c.total_neto_kg or 0):,.2f} KG",
                    font=ctk.CTkFont(size=12),
                    text_color=UI["color_success"]
                ).pack(anchor="w", padx=12, pady=(0, 8))
        finally:
            db.close()

    def _hacer_corte(self):
        """Ejecuta el corte."""
        resumen = self._calcular_resumen()

        if resumen["total_pesadas"] == 0:
            messagebox.showwarning(
                "Sin pesadas",
                "No hay pesadas completadas en el período actual.\n"
                "No es necesario realizar un corte."
            )
            return

        confirmacion = messagebox.askyesno(
            "Confirmar Corte",
            f"¿Realizar corte del período?\n\n"
            f"Pesadas: {resumen['total_pesadas']}\n"
            f"Total neto: {resumen['total_neto']:,.2f} KG\n\n"
            f"¿Confirmar?"
        )
        if not confirmacion:
            return

        obs = self._txt_obs.get("1.0", "end").strip()
        resultado = realizar_corte(obs)

        if resultado["exito"]:
            messagebox.showinfo(
                "✅ Corte Realizado",
                f"{resultado['mensaje']}\n\n"
                f"Total pesadas: {resultado['total_pesadas']}\n"
                f"Total neto: {resultado['total_neto_kg']:,.2f} KG"
            )
            # Recargar historial
            self._cargar_historial()
        else:
            messagebox.showerror("Error", resultado["mensaje"])
