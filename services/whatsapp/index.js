/**
 * WhatsApp Bridge - JobSearcher
 * Puente entre WhatsApp (whatsapp-web.js) y el orchestrator Python (FastAPI)
 */
require("dotenv").config();
const { Client, LocalAuth } = require("whatsapp-web.js");
const qrcode = require("qrcode-terminal");
const QRCode = require("qrcode");
const express = require("express");
const axios = require("axios");
const fs = require("fs");
const path = require("path");

const PORT = process.env.BRIDGE_PORT || 3001;
const ORCHESTRATOR_URL = process.env.ORCHESTRATOR_URL || "http://localhost:8000";
const MY_NUMBER = process.env.WHATSAPP_MY_NUMBER || "";

// Formato de chatId: numero@c.us (sin + ni espacios)
const MY_CHAT_ID = MY_NUMBER.replace(/\D/g, "") + "@c.us";

// --- CLIENTE WHATSAPP ---

const client = new Client({
  authStrategy: new LocalAuth({ dataPath: ".wwebjs_auth" }),
  puppeteer: {
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
  },
});

let currentQR = null;

client.on("qr", (qr) => {
  currentQR = qr;
  console.log("\n[WhatsApp Bridge] QR listo. Abre http://localhost:3001/qr en tu navegador");
  qrcode.generate(qr, { small: true });
});

client.on("ready", () => {
  console.log("[WhatsApp Bridge] Cliente listo!");
  console.log(`[WhatsApp Bridge] Número autorizado: ${MY_NUMBER}`);
});

client.on("auth_failure", (msg) => {
  console.error("[WhatsApp Bridge] Fallo de autenticación:", msg);
});

client.on("disconnected", (reason) => {
  console.log("[WhatsApp Bridge] Desconectado:", reason);
  client.initialize();
});

// Recibir mensajes del usuario y reenviar al orchestrator
client.on("message", async (msg) => {
  const from = msg.from;

  // Solo procesar mensajes del número autorizado
  if (from !== MY_CHAT_ID) {
    console.log(`[WhatsApp Bridge] Mensaje ignorado de: ${from}`);
    return;
  }

  console.log(`[WhatsApp Bridge] Mensaje recibido: ${msg.body}`);

  try {
    await axios.post(`${ORCHESTRATOR_URL}/webhook/whatsapp`, {
      message: msg.body,
      from: from,
      timestamp: Date.now(),
    });
  } catch (err) {
    console.error("[WhatsApp Bridge] Error enviando al orchestrator:", err.message);
    await msg.reply("Error interno. El orchestrator no responde.");
  }
});

client.initialize();

// --- API EXPRESS para que Python envíe mensajes ---

const app = express();
app.use(express.json());

// Enviar mensaje al usuario
app.post("/send", async (req, res) => {
  const { number, message } = req.body;

  if (!message) {
    return res.status(400).json({ error: "message requerido" });
  }

  const chatId = number
    ? number.replace(/\D/g, "") + "@c.us"
    : MY_CHAT_ID;

  try {
    // Resolver el chatId correcto (necesario para versiones nuevas de WhatsApp)
    let resolvedChatId = chatId;
    try {
      const numberId = await client.getNumberId(chatId.replace("@c.us", ""));
      if (numberId) resolvedChatId = numberId._serialized;
    } catch (e) {
      // usar chatId original si no se puede resolver
    }
    await client.sendMessage(resolvedChatId, message);
    console.log(`[WhatsApp Bridge] Enviado a ${resolvedChatId}: ${message.substring(0, 60)}...`);
    res.json({ ok: true });
  } catch (err) {
    console.error("[WhatsApp Bridge] Error enviando:", err.message);
    res.status(500).json({ error: err.message });
  }
});

// QR en HTML - abrir en navegador para escanear
app.get("/qr", async (req, res) => {
  if (!currentQR) {
    if (client.info) {
      return res.send(`<html><body style="font-family:sans-serif;text-align:center;padding:50px">
        <h2 style="color:green">✅ WhatsApp ya está conectado!</h2>
        <p>El agente está activo.</p>
      </body></html>`);
    }
    return res.send(`<html><body style="font-family:sans-serif;text-align:center;padding:50px">
      <h2>⏳ Generando QR...</h2>
      <p>Espera unos segundos y recarga la página.</p>
      <script>setTimeout(()=>location.reload(), 3000)</script>
    </body></html>`);
  }

  const qrDataUrl = await QRCode.toDataURL(currentQR, { width: 400 });
  res.send(`<html>
  <head>
    <title>JobSearcher - Conectar WhatsApp</title>
    <meta charset="utf-8">
    <style>
      body { font-family: sans-serif; text-align: center; padding: 40px; background: #f0f0f0; }
      .card { background: white; border-radius: 16px; padding: 40px; display: inline-block; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }
      h1 { color: #128C7E; }
      img { border: 4px solid #128C7E; border-radius: 8px; }
      p { color: #555; font-size: 16px; }
      .steps { text-align: left; margin-top: 20px; }
    </style>
  </head>
  <body>
    <div class="card">
      <h1>📱 Conectar WhatsApp</h1>
      <img src="${qrDataUrl}" width="300" height="300" /><br><br>
      <div class="steps">
        <b>Pasos:</b>
        <ol>
          <li>Abre WhatsApp en tu teléfono</li>
          <li>Menú → <b>Dispositivos vinculados</b></li>
          <li>Toca <b>Vincular un dispositivo</b></li>
          <li>Escanea este QR</li>
        </ol>
      </div>
      <p style="color:#999;font-size:13px">El QR expira en ~60 segundos. Si expira, recarga la página.</p>
    </div>
    <script>setTimeout(()=>location.reload(), 55000)</script>
  </body>
  </html>`);
});

// Health check
app.get("/health", (req, res) => {
  res.json({
    status: "ok",
    client_ready: client.info ? true : false,
    my_number: MY_NUMBER,
  });
});

app.listen(PORT, () => {
  console.log(`[WhatsApp Bridge] API escuchando en puerto ${PORT}`);
});
