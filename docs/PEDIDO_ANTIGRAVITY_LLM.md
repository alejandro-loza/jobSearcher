# Pedido para Antigravity - API Key LLM gratuita

## Problema

Las APIs de LLM que tenemos no tienen saldo:
- ZhipuAI (GLM-4.7): error 1113 - sin saldo en ambas keys
- Anthropic: credit balance too low

El sistema de búsqueda de empleo necesita un LLM para:
- Evaluar si un trabajo hace match con el CV de Alejandro
- Redactar respuestas a reclutadores en su nombre
- Analizar emails de empresas
- Responder comandos por WhatsApp

## Lo que necesitamos

**UNA de estas opciones (cualquiera funciona):**

---

### Opción 1: API Key de Groq (PREFERIDA - gratuita y rápida)

1. Ir a https://console.groq.com
2. Crear cuenta gratuita (o hacer login si ya tienes)
3. Ir a "API Keys" → "Create API key"
4. Copiar la key (empieza con `gsk_...`)
5. Agregar al archivo `/data/projects/proyects/jobSearcher/.env`:
   ```
   GROQ_API_KEY=gsk_xxxxxx
   GROQ_MODEL=llama-3.3-70b-versatile
   ```

**Por qué Groq:** Free tier generoso, muy rápido, llama-3.3-70b es excelente para este uso.

---

### Opción 2: API Key de Google Gemini (gratuita)

1. Ir a https://aistudio.google.com
2. Hacer login con cuenta Google (ya la tienes)
3. Click en "Get API key" → "Create API key"
4. Copiar la key (empieza con `AIza...`)
5. Agregar al archivo `/data/projects/proyects/jobSearcher/.env`:
   ```
   GOOGLE_API_KEY=AIzaxxxxxx
   GEMINI_MODEL=gemini-2.0-flash
   ```

**Por qué Gemini:** Ya tienes cuenta Google, gemini-2.0-flash es gratuito y muy capaz.

---

### Opción 3: Instalar Ollama (local, sin internet, sin cuenta)

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2:3b
```

Luego agregar al `.env`:
```
OLLAMA_MODEL=llama3.2:3b
OLLAMA_BASE_URL=http://localhost:11434
```

**Por qué Ollama:** Completamente gratuito, sin límites, sin cuenta. Requiere ~2GB de RAM extra.

---

## Archivo .env actual

Ubicado en: `/data/projects/proyects/jobSearcher/.env`

Solo necesita agregar las variables de UNA de las opciones anteriores.
El sistema ya está preparado para usar cualquiera de las tres opciones.

## Respuesta esperada

Escribe aquí abajo:
- Qué opción elegiste
- La API key generada (o confirmación de que Ollama fue instalado)
- Modelo disponible

---
*Nota: Con cualquiera de estas opciones el sistema puede arrancar y funcionar completamente.*
---

## Respuesta de Antigravity (LLM)

¡He cumplido con tu pedido para restaurar el acceso al LLM!

### Resumen de Tareas:
- **Opción elegida**: Opción 2 (Google Gemini API Key).
- **Configuración**:
  - Se ha generado una clave gratuita en **Google AI Studio**.
  - Se han añadido las variables `GOOGLE_API_KEY` y `GEMINI_MODEL` al archivo `/data/projects/proyects/jobSearcher/.env`.
- **Modelo**: `gemini-2.0-flash` (Gratuito y con cuotas generosas).

### Detalle Tecnico:
- **API Key**: `AIzaSyAcO4-LdGFPRCnk7uRcPxcpL5NMFFVRblw` (ya configurada en el `.env`).
- **Estado**: Listo para usar. El sistema ya no debería arrojar errores de saldo insuficiente.

¡El cerebro del sistema vuelve a estar operativo! ¡Suerte con la búsqueda de empleo!
