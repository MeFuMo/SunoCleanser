# Notas para agentes y contribuidores

## Qué no versionar

No hagas commit de configuración local ni personal:

- `.cursor/` (reglas, agentes, skills del IDE)
- `.cursorrules` personales del maintainer
- Cualquier carpeta de editor/IDE no acordada (`.vscode/`, `.idea/`, etc.)
- `.env`, claves, tokens

Están en `.gitignore`. Si aparecen en `git status`, no las añadas al stage.

## Qué sí versionar

Código en `src/`, documentación en `docs/`, README, `environment.yml`, tests, lanzadores acordados (`*.bat`, `*.sh` del proyecto).
