# Por qué no podemos usar GLM (ZhipuAI)

## Contexto

GLM-4.7 era el LLM original planeado para este proyecto. Tiene una API compatible
con OpenAI y el sistema fue diseñado para usarlo. Sin embargo, hay dos bloqueos
que impiden usarlo actualmente.

---

## Problema 1: Sin saldo en la cuenta

Las dos API keys disponibles retornan el mismo error:

```
Error code: 429
Código: 1113
Mensaje: 余额不足或无可用资源包，请充值
(Traducción: Saldo insuficiente o sin paquete de recursos disponible)
```

Keys probadas:
- `6d40423e8e144446ba32ff477b5f28b0.eGOfSzjS4wooE6u1` → sin saldo
- `7cf14a19380048fea80bb5ca11db2333.YiMwTWZuaRmiDv5U` → sin saldo

La plataforma es `open.bigmodel.cn`. Para resolver esto habría que entrar
a esa cuenta y recargar saldo o activar un plan de pago.

---

## Problema 2: Modelo no encontrado (error 1211)

Al intentar usar modelos alternativos gratuitos de ZhipuAI, todos retornan:

```
Error code: 400
Código: 1211
Mensaje: 模型不存在，请检查模型代码
(Traducción: El modelo no existe, verifica el código del modelo)
```

Modelos probados:
- `glm-4-flash` → no encontrado
- `glm-4-flash-250414` → no encontrado
- `glm-4-air` → no encontrado
- `glm-4` → no encontrado
- `glm-3-turbo` → no encontrado
- `glm-z1-flash` → no encontrado

Esto indica que las keys pertenecen a una cuenta que no tiene acceso
a ningún modelo activo, posiblemente porque el plan venció o nunca fue activado.

---

## Por qué no es trivial resolverlo

1. **Requiere acceso a la cuenta de ZhipuAI** (open.bigmodel.cn) con las
   credenciales de Alejandro para recargar saldo.

2. **La plataforma es china** — el sitio está en mandarín, los pagos pueden
   requerir métodos locales (Alipay, WeChat Pay) o tarjeta internacional.

3. **No hay free tier real** — a diferencia de Groq o SambaNova, ZhipuAI
   no ofrece un tier gratuito funcional para estas keys. El free tier inicial
   ya fue consumido.

---

## Solución actual

El sistema usa **rotación automática** entre dos LLMs gratuitos:

| LLM | Modelo | Límite | Estado |
|-----|--------|--------|--------|
| **Groq** | llama-3.3-70b-versatile | 100k tokens/día | ✅ Activo |
| **SambaNova** | Meta-Llama-3.3-70B-Instruct | Sin límite diario | ✅ Activo |

Cuando Groq alcanza su límite diario (se resetea a medianoche),
el sistema automáticamente usa SambaNova sin interrupción.

Ambos usan **Llama 3.3 70B**, un modelo de calidad comparable a GLM-4.

---

## Para reactivar GLM (si se desea en el futuro)

1. Entrar a https://open.bigmodel.cn con las credenciales de la cuenta
2. Recargar saldo (mínimo disponible)
3. Verificar qué modelos están disponibles en esa cuenta
4. Actualizar en `.env`:
   ```
   GLM_API_KEY=nueva_key_o_key_con_saldo
   GLM_MODEL=glm-4-flash  (o el modelo disponible)
   ```
5. El sistema está preparado para usarlo — solo falta la key funcional
