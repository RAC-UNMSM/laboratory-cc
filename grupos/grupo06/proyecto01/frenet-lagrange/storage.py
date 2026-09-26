# -*- coding: utf-8 -*-
"""
storage.py — Persistencia y Almacenamiento de Resultados MCP
============================================================
Módulo encargado de guardar y recuperar consultas, historiales de
cálculos y resultados de geometría diferencial u optimización en disco (JSON).
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, List


class StorageManager:
    """Gestiona el almacenamiento persistente de resultados de cálculos."""

    def __init__(self, ruta_almacenamiento: str = "historial_calculos.json"):
        self.ruta_archivo = os.path.abspath(ruta_almacenamiento)
        self._inicializar_archivo()

    def _inicializar_archivo(self) -> None:
        """Crea el archivo JSON si no existe."""
        if not os.path.exists(self.ruta_archivo):
            with open(self.ruta_archivo, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)

    def guardar_resultado(self, tipo_operacion: str, entrada: Dict[str, Any], resultado: Dict[str, Any]) -> str:
        """Guarda un registro de cálculo con marca de tiempo."""
        timestamp = datetime.utcnow().isoformat()
        registro = {
            "timestamp": timestamp,
            "tipo_operacion": tipo_operacion,
            "entrada": entrada,
            "resultado": resultado
        }

        historial = self.obtener_historial()
        historial.append(registro)

        with open(self.ruta_archivo, "w", encoding="utf-8") as f:
            json.dump(historial, f, ensure_ascii=False, indent=2)

        return timestamp

    def obtener_historial(self) -> List[Dict[str, Any]]:
        """Obtiene la lista completa de resultados almacenados."""
        try:
            with open(self.ruta_archivo, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def buscar_por_operacion(self, tipo_operacion: str) -> List[Dict[str, Any]]:
        """Filtra el historial por tipo de herramienta ejecutada."""
        historial = self.obtener_historial()
        return [item for item in historial if item.get("tipo_operacion") == tipo_operacion]
