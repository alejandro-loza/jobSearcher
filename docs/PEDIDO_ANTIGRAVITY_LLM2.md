# Pedido para Antigravity - API Keys LLM alternativas

## Situacion

Groq (el LLM que estamos usando) tiene limite de 100,000 tokens por dia en el free tier.
Necesitamos APIs adicionales para rotar cuando se agote el limite.

## Tarea: Registrarse y obtener API keys de estos dos servicios

---

### 1. Cerebras (PRIORITARIO)

1. Ir a https://cloud.cerebras.ai
2. Click en "Sign Up"
3. Registrarse con la cuenta Google de Alejandro
4. Una vez dentro, ir a "API Keys" en el menu lateral
5. Click en "Create API Key"
6. Copiar la key
7. Agregar al archivo `/data/projects/proyects/jobSearcher/.env`:
   ```
   CEREBRAS_API_KEY=csk-xxxxxx
   CEREBRAS_MODEL=llama-3.3-70b
   ```

**Por que Cerebras:** Gratis, sin tarjeta, muy rapido, mismo modelo que Groq (Llama 3.3 70b), limite de 30,000 tokens/minuto.

---

### 2. SambaNova

1. Ir a https://cloud.sambanova.ai
2. Click en "Get Started" o "Sign Up"
3. Registrarse con cuenta Google de Alejandro
4. Ir a "API Keys"
5. Generar una key
6. Copiar la key
7. Agregar al archivo `/data/projects/proyects/jobSearcher/.env`:
   ```
   SAMBANOVA_API_KEY=xxxxxx
   SAMBANOVA_MODEL=Meta-Llama-3.3-70B-Instruct
   ```

**Por que SambaNova:** Gratis, sin tarjeta, tiene Llama 3.3 405b (el mas grande disponible gratis), muy generoso en limites.

---

## Respuesta esperada

Escribe aqui abajo:
- API key de Cerebras (csk-...)
- API key de SambaNova
- Confirmacion de que se agregaron al .env
