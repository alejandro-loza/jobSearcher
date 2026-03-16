# Pedido para Antigravity - API Key Groq

## Situacion actual

Todos los LLMs disponibles tienen cuota agotada o sin creditos:
- ZhipuAI (GLM): error 1113 - sin saldo
- Anthropic: credit balance too low
- Google Gemini (AIzaSyAcO4...): proyecto con billing habilitado pero sin creditos (free tier = 0)

## Lo que necesitamos AHORA

**Crear una cuenta gratuita en Groq y generar una API key.**

Groq tiene un free tier real y generoso (sin tarjeta de credito requerida).

### Pasos exactos:

1. Abre https://console.groq.com en el navegador
2. Click en "Sign Up" (o "Log in" si ya tienes cuenta)
3. Puedes registrarte con cuenta Google de Alejandro
4. Una vez dentro, ve al menu lateral: **"API Keys"**
5. Click en **"Create API Key"**
6. Dale un nombre (ej: "jobsearcher")
7. Copia la key completa (empieza con `gsk_...`)
8. Abre el archivo `/data/projects/proyects/jobSearcher/.env`
9. Agrega estas dos lineas al final:
   ```
   GROQ_API_KEY=gsk_PEGA_LA_KEY_AQUI
   GROQ_MODEL=llama-3.3-70b-versatile
   ```
10. Guarda el archivo

## Por que Groq

- Free tier real: 14,400 requests/dia, 500,000 tokens/minuto
- No requiere tarjeta de credito
- llama-3.3-70b-versatile es muy capaz para evaluar empleos y redactar mensajes
- Compatible con el sistema existente (API OpenAI-compatible)

## Respuesta esperada

Escribe aqui abajo:
- La API key generada (gsk_...)
- Confirmacion de que se agrego al .env
