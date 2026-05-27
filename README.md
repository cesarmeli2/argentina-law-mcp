# Argentina Legal Law MCP Server

Servidor MCP para profesionales jurídicos argentinos. Sin dependencias de pago.

## Tools disponibles

| Tool | Descripción |
|---|---|
| `buscar_norma` | Búsqueda de normas en Infoleg |
| `obtener_norma` | Texto completo o artículo específico por ID de Infoleg |
| `buscar_jurisprudencia` | Jurisprudencia y legislación en SAIJ |
| `consultar_boletin_oficial` | Búsqueda en Boletín Oficial |
| `explicar_termino` | Glosario jurídico iJudicial (PJN) |
| `analizar_documento` | Análisis de documentos con IA (requiere ANTHROPIC_API_KEY) |
| `normas_frecuentes` | Catálogo de normas por área con IDs Infoleg |

## Deploy en Render (recomendado)

### 1. Crear repositorio en GitHub

```bash
git init
git add .
git commit -m "initial commit"
git remote add origin https://github.com/TU_USUARIO/argentina-law-mcp.git
git push -u origin main
```

### 2. Crear servicio en Render

1. Ir a https://render.com y crear cuenta (gratis)
2. New → Web Service → conectar el repositorio
3. Configuración:
   - **Runtime:** Python
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python main.py`
4. En "Environment Variables" agregar:
   - `ANTHROPIC_API_KEY` = tu API key de Anthropic
5. Deploy

La URL del servidor será: `https://argentina-law-mcp.onrender.com/mcp`

### 3. Registrar en Claude.ai como conector MCP

1. Ir a Claude.ai → Settings → Integrations
2. Add Integration → MCP Server
3. URL: `https://argentina-law-mcp.onrender.com/mcp`
4. Guardar

## Uso local (desarrollo)

```bash
# Instalar dependencias
pip install -r requirements.txt

# Configurar variables
cp .env.example .env
# Editar .env con tu ANTHROPIC_API_KEY

# Iniciar servidor
python main.py
```

El servidor corre en http://localhost:8000/mcp

## Fuentes

- **Infoleg:** https://www.infoleg.gob.ar - normas nacionales oficiales
- **SAIJ:** https://www.saij.gob.ar - jurisprudencia y legislación
- **Boletín Oficial:** https://www.boletinoficial.gob.ar
- **iJudicial:** https://ijudicial.gob.ar - glosario PJN

## Licencia

MIT
