# ADR-0001 · Motor de calendario independiente y perfiles versionados

Estado: implementado para primera publicación. Fecha: 2026-11-25 UTC.

## Contexto

Calendar Studio ya separa un motor Pandas de su interfaz Streamlit. Se requiere reutilización en notebooks, servicios y proyectos ajenos a MAC; Model Arena se integrará después. El export legado tiene 246 columnas y Observatorio consume su vista hábil de 244 columnas. El usuario corrigió el festivo 2026-11-02.

## Decisión

Publicar `calendar-studio`, import `calendar_studio`, con configuración Pydantic, reglas polimórficas y artefactos Parquet/JSON. El motor genérico tiene reglas inyectadas y contexto alrededor del rango; el perfil mac_legacy_v1 conserva el motor y semánticas históricas, incluidos sus límites de año. Los festivos se pasan explícitamente. El fixture de proyecto corregido se ofrece mediante una función explícita, sin afirmar cobertura oficial. Streamlit es un extra y usa la misma API. No se añade dependencia ni cambio a Model Arena.

## Alternativas y consecuencias

Copiar reglas dentro de Model Arena introduciría acoplamiento. Sustituir silenciosamente las reglas del motor legado cambiaría entradas de modelos entrenados. Mantener sólo funciones globales ligadas al directorio actual no permite configuración y trazabilidad robustas.

El usuario debe mantener los festivos y describir/versionar plugins. Las entradas son fechas civiles, no sesiones intradía. Las reglas de pago son reglas del proyecto, no afirmaciones legales. El perfil legado mantiene nombres históricos ambiguos para compatibilidad; las nuevas reglas genéricas usan nombres explícitos del usuario.

## Validación y recuperación

Conservar los cinco tests originales y añadir pruebas independientes de fechas, offsets, perfiles, datos inválidos, artefactos, plugins y UI. Verificar el wheel instalado en Python 3.11/3.12. No reescribir corridas de Observatorio; sus snapshots no cambian con esta publicación. Un consumidor puede fijar versión del paquete y conservar el artefacto junto con su manifiesto. Los esquemas futuros deberán tener un perfil o versión explícitos.
