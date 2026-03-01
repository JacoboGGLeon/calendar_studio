# Fase 3: Analítica, Exportación y Refinamiento del Motor (Propuestas)

Habiendo completado exitosamente la refactorización de datos base (Fase 1) y el refinamiento de la interfaz de usuario con controles de edición y estilos corporativos (Fase 2), esta guía plantea los posibles siguientes pasos naturales para evolucionar y fortalecer la plataforma de "Calendar Studio".

## 1. Módulo Analítico y Gráficas
Actualmente, los indicadores se visualizan a nivel métrica de día individual (Inspector). Para la siguiente fase, introduciremos un Tabulador Analítico para observar el impacto macro anual/mensual de las reglas.
- **KPIs Agrupados:** Calcular métricas como "Total de días hábiles al mes" o "Número de días festivos en el Año".
- **Visualización (Gráficas):** Integrar `st.bar_chart` o librerías dinámicas (Plotly/Altair) para mostrar la distribución de días hábiles versus asuetos en los años seleccionados.
- **Resumen Financiero:** Proyectar impactos según días de nómina (quincenas) contra días laborados y descansos.

## 2. Robustecimiento del Engine
A medida que la aplicación escala, la lógica estática actual debe prepararse para flujos más complejos.
- **Reglas Recursivas o Relacionales:** Dar la habilidad al engine para prever reglas dependientes. Ej. "Si la quincena cae en fin de semana y/o festivo, mover a un offset negativo de día hábil".
- **Ponderación/Prioridad en Eventos:** Evitar choques. Si múltiples eventos caen en la misma fecha (ej. día festivo y pago de nómina), crear un sistema de prioridades que determine cuál se sobreescribe o cuál prevalece durante la jerarquía de pintado/evaluación.

## 3. Experiencia de Usuario y Empaquetado
Aumentar la comodidad y la personalización para el flujo de trabajo del analista.
- **Exportación a XLSX e Integración con BD:** Añadir una descarga en formato nativo `.xlsx` pre-formateado (colores en celdas, filtros), e interconectar vía conector SQL si la base original de calendarios reside en una infraestructura propia en la nube.
- **Modo Oscuro/Claro (Theme Toggling):** Enriquecer `ui_components.py` para reescribir variables dinámicamente y permitirle al usuario escoger entre modos Dark, Ligth o Automático.

## 4. Pruebas y CI/CD
Asegurar que cualquier alteración al calendario empresarial jamás repercuta pasivamente de manera equivocada.
- **Suite Ampliada de Pruebas Unitarias (`pytest`):** Expandir el escrutinio sobre el script `tests/test_validation.py` para abarcar todos los offsets dinámicos.
- **Validaciones en UI (Errores Amigables):** Si un usuario intenta "pintar" o alterar un dato crítico incorrecto en `st.data_editor`, lanzar validaciones (toasts) a prueba de "dedazos" y mantener la consistencia de archivos.

---

> **Nota:** La dirección exacta y prioridad de estos objetivos deben validarse en sintonía con las necesidades emergentes del de negocio. Esta etapa se encargaría de pasar la aplicación de un "prototipo funcional y vistoso" a una "herramienta robusta empresarial".
