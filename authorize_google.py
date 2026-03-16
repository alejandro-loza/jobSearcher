"""
Script para autorizar Google APIs (Calendar + Gmail).
Corre este script, abre las URLs en Chrome y pega el código de vuelta.
"""
import os
import sys
from google_auth_oauthlib.flow import InstalledAppFlow

CREDENTIALS_FILE = "config/google_credentials.json"

def authorize(name: str, scopes: list, token_file: str, port: int):
    print(f"\n{'='*50}")
    print(f"Autorizando: {name}")
    print(f"{'='*50}")

    if os.path.exists(token_file):
        print(f"✅ Ya existe token: {token_file}")
        resp = input("¿Re-autorizar? (s/N): ").strip().lower()
        if resp != "s":
            return

    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, scopes)

    print(f"\n⏳ Iniciando servidor en http://localhost:{port}/")
    print(f"   Se abrirá el navegador. Si no abre, copia la URL que aparece y pégala en Chrome.")
    print()

    try:
        creds = flow.run_local_server(port=port, open_browser=True)
    except Exception as e:
        print(f"❌ Error con servidor local: {e}")
        print("\nIntentando modo manual (copia/pega el código)...")
        flow2 = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, scopes)
        flow2.redirect_uri = "urn:ietf:wg:oauth:2.0:oob"
        auth_url, _ = flow2.authorization_url(prompt="consent")
        print(f"\n🔗 Abre esta URL en Chrome:\n{auth_url}\n")
        code = input("Pega el código de autorización aquí: ").strip()
        flow2.fetch_token(code=code)
        creds = flow2.credentials

    with open(token_file, "w") as f:
        f.write(creds.to_json())
    print(f"\n✅ Token guardado en: {token_file}")


if __name__ == "__main__":
    # Calendar
    authorize(
        name="Google Calendar",
        scopes=["https://www.googleapis.com/auth/calendar"],
        token_file="config/calendar_token.json",
        port=8765,
    )

    # Gmail
    authorize(
        name="Gmail",
        scopes=[
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/gmail.modify",
        ],
        token_file="config/gmail_token.json",
        port=8766,
    )

    print("\n🎉 Autorización completada. El sistema ya puede usar Calendar y Gmail.")
