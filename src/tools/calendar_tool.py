"""
Google Calendar tool: agenda entrevistas, crea recordatorios y busca slots libres.
"""
from datetime import datetime, timedelta, time
from typing import Optional, Dict, Any, List
from loguru import logger

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os

from config import settings

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def _get_calendar_service():
    """Obtiene servicio autenticado de Google Calendar."""
    creds = None
    token_file = settings.calendar_token_file

    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                settings.calendar_credentials_file, SCOPES
            )
            creds = flow.run_local_server(port=8765, open_browser=True)
        with open(token_file, "w") as f:
            f.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def create_interview_event(
    job_title: str,
    company: str,
    start_datetime: datetime,
    duration_minutes: int = 60,
    interviewer_email: Optional[str] = None,
    notes: str = "",
    meeting_link: str = "",
) -> Optional[str]:
    """
    Crea un evento de entrevista en Google Calendar.

    Args:
        job_title: Título del puesto
        company: Nombre de la empresa
        start_datetime: Fecha y hora de inicio
        duration_minutes: Duración en minutos
        interviewer_email: Email del entrevistador (para invitar)
        notes: Notas adicionales
        meeting_link: Link de videollamada si existe

    Returns:
        ID del evento creado o None si falla
    """
    try:
        service = _get_calendar_service()
        end_datetime = start_datetime + timedelta(minutes=duration_minutes)

        description = f"Entrevista para: {job_title} en {company}"
        if notes:
            description += f"\n\nNotas:\n{notes}"
        if meeting_link:
            description += f"\n\nLink de reunion: {meeting_link}"

        event = {
            "summary": f"Entrevista - {job_title} @ {company}",
            "description": description,
            "start": {
                "dateTime": start_datetime.isoformat(),
                "timeZone": "America/Mexico_City",
            },
            "end": {
                "dateTime": end_datetime.isoformat(),
                "timeZone": "America/Mexico_City",
            },
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "email", "minutes": 60},
                    {"method": "popup", "minutes": 30},
                    {"method": "popup", "minutes": 10},
                ],
            },
        }

        if interviewer_email:
            event["attendees"] = [{"email": interviewer_email}]

        created = (
            service.events()
            .insert(calendarId=settings.calendar_id, body=event, sendUpdates="all")
            .execute()
        )

        event_id = created.get("id")
        logger.success(
            f"Evento creado: {event['summary']} el {start_datetime.strftime('%d/%m/%Y %H:%M')}"
        )
        return event_id

    except Exception as e:
        logger.error(f"Error creando evento en Calendar: {e}")
        return None


def create_reminder_event(
    title: str,
    description: str,
    remind_at: datetime,
) -> Optional[str]:
    """Crea un recordatorio puntual (duración 15 min) en Calendar."""
    try:
        service = _get_calendar_service()
        end = remind_at + timedelta(minutes=15)

        event = {
            "summary": title,
            "description": description,
            "start": {
                "dateTime": remind_at.isoformat(),
                "timeZone": "America/Mexico_City",
            },
            "end": {
                "dateTime": end.isoformat(),
                "timeZone": "America/Mexico_City",
            },
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "popup", "minutes": 5},
                ],
            },
        }

        created = (
            service.events()
            .insert(calendarId=settings.calendar_id, body=event)
            .execute()
        )
        return created.get("id")

    except Exception as e:
        logger.error(f"Error creando recordatorio: {e}")
        return None


def get_free_slots(
    days_ahead: int = 7,
    duration_minutes: int = 60,
) -> List[Dict[str, str]]:
    """
    Encuentra slots libres en el horario preferido de Alejandro:
    - 9:00am - 11:00am
    - 3:00pm - 4:00pm
    (hora Mexico City = UTC-6)

    Returns:
        Lista de slots disponibles con: date, start, end, label
    """
    PREFERRED_WINDOWS = [
        (time(9, 0),  time(11, 0)),   # 9am - 11am
        (time(15, 0), time(16, 0)),   # 3pm - 4pm
    ]
    TIMEZONE = "America/Mexico_City"

    try:
        service = _get_calendar_service()
        now = datetime.now()
        end_search = now + timedelta(days=days_ahead)

        # Obtener eventos existentes
        events_result = (
            service.events()
            .list(
                calendarId=settings.calendar_id,
                timeMin=now.isoformat() + "Z",
                timeMax=end_search.isoformat() + "Z",
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        busy_events = events_result.get("items", [])

        # Construir rangos ocupados
        busy_ranges = []
        for event in busy_events:
            start_str = event.get("start", {}).get("dateTime")
            end_str = event.get("end", {}).get("dateTime")
            if start_str and end_str:
                try:
                    s = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                    e = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
                    busy_ranges.append((s, e))
                except Exception:
                    pass

        # Buscar slots libres
        free_slots = []
        current_day = now.date()

        for day_offset in range(days_ahead):
            day = current_day + timedelta(days=day_offset)

            # Saltar fines de semana
            if day.weekday() >= 5:
                continue

            for window_start, window_end in PREFERRED_WINDOWS:
                slot_start = datetime.combine(day, window_start)
                slot_end = slot_start + timedelta(minutes=duration_minutes)
                window_limit = datetime.combine(day, window_end)

                # No proponer slots en el pasado
                if slot_start < now:
                    slot_start = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)

                while slot_end <= window_limit:
                    # Verificar si el slot está libre
                    is_free = True
                    for busy_start, busy_end in busy_ranges:
                        # Comparar naive datetimes
                        bs = busy_start.replace(tzinfo=None)
                        be = busy_end.replace(tzinfo=None)
                        if not (slot_end <= bs or slot_start >= be):
                            is_free = False
                            break

                    if is_free:
                        free_slots.append({
                            "date": day.strftime("%A %d/%m/%Y"),
                            "start": slot_start.strftime("%I:%M %p"),
                            "end": slot_end.strftime("%I:%M %p"),
                            "start_iso": slot_start.isoformat(),
                            "end_iso": slot_end.isoformat(),
                            "label": f"{day.strftime('%A %d/%m')} {slot_start.strftime('%I:%M %p')} - {slot_end.strftime('%I:%M %p')} (México)",
                        })

                    slot_start += timedelta(minutes=30)
                    slot_end += timedelta(minutes=duration_minutes)

                    if len(free_slots) >= 6:
                        break

            if len(free_slots) >= 6:
                break

        logger.info(f"Slots libres encontrados: {len(free_slots)}")
        return free_slots[:3]  # Proponer máximo 3 opciones

    except Exception as e:
        logger.error(f"Error buscando slots libres: {e}")
        # Fallback: proponer horarios estándar para mañana
        tomorrow = datetime.now() + timedelta(days=1)
        if tomorrow.weekday() >= 5:
            tomorrow += timedelta(days=2)
        return [
            {
                "date": tomorrow.strftime("%A %d/%m/%Y"),
                "start": "10:00 AM",
                "end": "11:00 AM",
                "start_iso": datetime.combine(tomorrow.date(), time(10, 0)).isoformat(),
                "label": f"{tomorrow.strftime('%A %d/%m')} 10:00 AM - 11:00 AM (México)",
            }
        ]


def get_upcoming_events(days: int = 7) -> list:
    """Lista los próximos eventos de entrevista."""
    try:
        service = _get_calendar_service()
        now = datetime.utcnow().isoformat() + "Z"
        end = (datetime.utcnow() + timedelta(days=days)).isoformat() + "Z"

        result = (
            service.events()
            .list(
                calendarId=settings.calendar_id,
                timeMin=now,
                timeMax=end,
                singleEvents=True,
                orderBy="startTime",
                q="Entrevista",
            )
            .execute()
        )
        return result.get("items", [])

    except Exception as e:
        logger.error(f"Error obteniendo eventos: {e}")
        return []
