"""
CogView Tool: Generación de imágenes usando CogView de ZhipuAI.

Genera imágenes desde descripciones de texto (text-to-image).
Compatible con API de OpenAI format (ZhipuAI soporta compatibilidad).
"""
import base64
import httpx
import os
from typing import Optional, Dict, Any
from pathlib import Path
from loguru import logger

from config import settings


def _get_api_key() -> str:
    """Obtiene API key para CogView (usa GLM_API_KEY por defecto)."""
    return settings.cogview_api_key or settings.glm_api_key


def generate_image(
    prompt: str,
    size: str = "1024x1024",
    quality: str = "standard",
    save_path: Optional[str] = None,
    timeout: int = 60,
) -> Dict[str, Any]:
    """
    Genera una imagen usando CogView vía API compatible con OpenAI.

    Args:
        prompt: Descripción de texto de la imagen a generar
        size: Tamaño de imagen ("1024x1024", "1024x1792", "1792x1024")
        quality: Calidad ("standard" o "hd")
        save_path: Ruta donde guardar la imagen (si None, no guarda)
        timeout: Timeout en segundos para la generación

    Returns:
        Dict con:
        - success: bool
        - url: URL de la imagen generada
        - local_path: Ruta local si se guardó
        - prompt_used: Prompt enviado
        - model: Modelo usado
        - error: Mensaje de error si falló
    """
    api_key = _get_api_key()
    if not api_key:
        return {
            "success": False,
            "error": "No API key configured for CogView (GLM_API_KEY or COGVIEW_API_KEY)",
        }

    # Usamos el endpoint compatible con OpenAI de ZhipuAI
    base_url = "https://open.bigmodel.cn/api/paas/v4/images/generations"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": settings.cogview_model,  # Usa el modelo configurado (cogview-4-250304)
        "prompt": prompt,
        "size": size,
        "n": 1,  # Número de imágenes a generar
    }

    # Solo agregamos quality si no es standard (para evitar errores)
    if quality != "standard":
        payload["quality"] = quality

    try:
        logger.info(f"[cogview] Generando imagen con prompt: {prompt[:100]}...")
        logger.debug(f"[cogview] Request: size={size}, quality={quality}")

        response = httpx.post(
            base_url,
            headers=headers,
            json=payload,
            timeout=timeout,
        )

        if response.status_code != 200:
            error_msg = f"API error {response.status_code}: {response.text[:200]}"
            logger.error(f"[cogview] {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "prompt_used": prompt,
                "model": settings.cogview_model,
            }

        data = response.json()

        if "data" not in data or not data["data"]:
            logger.error(f"[cogview] Invalid response: {data}")
            return {
                "success": False,
                "error": "Invalid API response format",
                "prompt_used": prompt,
                "model": settings.cogview_model,
            }

        image_url = data["data"][0].get("url")
        if not image_url:
            logger.error(f"[cogview] No URL in response: {data}")
            return {
                "success": False,
                "error": "No image URL in response",
                "prompt_used": prompt,
                "model": settings.cogview_model,
            }

        logger.success(f"[cogview] Imagen generada exitosamente: {image_url}")

        result = {
            "success": True,
            "url": image_url,
            "prompt_used": prompt,
            "model": settings.cogview_model,
            "size": size,
            "quality": quality,
            "local_path": None,
        }

        # Descargar y guardar si se especificó ruta
        if save_path:
            local_path = _download_image(image_url, save_path)
            if local_path:
                result["local_path"] = local_path
                logger.success(f"[cogview] Imagen guardada en: {local_path}")
            else:
                logger.warning(f"[cogview] No se pudo guardar la imagen en: {save_path}")

        return result

    except httpx.TimeoutException:
        error_msg = f"Timeout después de {timeout} segundos"
        logger.error(f"[cogview] {error_msg}")
        return {
            "success": False,
            "error": error_msg,
            "prompt_used": prompt,
            "model": settings.cogview_model,
        }
    except Exception as e:
        logger.error(f"[cogview] Error inesperado: {e}")
        return {
            "success": False,
            "error": str(e)[:200],
            "prompt_used": prompt,
            "model": settings.cogview_model,
        }


def _download_image(url: str, save_path: str) -> Optional[str]:
    """
    Descarga una imagen desde URL y la guarda localmente.

    Args:
        url: URL de la imagen
        save_path: Ruta donde guardar (incluye filename)

    Returns:
        Ruta local o None si falló
    """
    try:
        # Crear directorio si no existe
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)

        response = httpx.get(url, timeout=30)
        response.raise_for_status()

        with open(save_path, "wb") as f:
            f.write(response.content)

        return save_path

    except Exception as e:
        logger.error(f"[cogview] Error descargando imagen: {e}")
        return None


def generate_linkedin_infographic(
    topic: str,
    content_summary: str,
    style: str = "professional",
    save_dir: str = "data/linkedin_images",
) -> Dict[str, Any]:
    """
    Genera una infografía para LinkedIn usando CogView.

    Args:
        topic: Título o tema de la infografía
        content_summary: Resumen del contenido a visualizar
        style: Estilo ("professional", "modern", "minimalist", "bold")
        save_dir: Directorio donde guardar la imagen

    Returns:
        Dict con resultado de la generación
    """
    timestamp = __import__("datetime").datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"infographic_{topic[:30].replace(' ', '_')}_{timestamp}.png"
    save_path = os.path.join(save_dir, filename)

    # Prompt optimizado para infografías de LinkedIn
    prompt = f"""Create a professional LinkedIn infographic about: {topic}

Content to visualize:
{content_summary}

Style: {style}, clean design, business professional, high contrast text,
readable fonts, infographic layout with icons/charts, white or light background,
vertical format optimized for LinkedIn feed.

Make it visually appealing with good information hierarchy."""

    result = generate_image(
        prompt=prompt,
        size="1024x1792",  # Vertical para LinkedIn
        quality="hd",
        save_path=save_path,
    )

    return result


def batch_generate_images(
    prompts: list[str],
    save_dir: str = "data/generated_images",
    delay_seconds: float = 1.0,
) -> list[Dict[str, Any]]:
    """
    Genera múltiples imágenes en batch.

    Args:
        prompts: Lista de prompts
        save_dir: Directorio donde guardar
        delay_seconds: Delay entre requests (rate limiting)

    Returns:
        Lista de resultados de generación
    """
    results = []
    import time

    Path(save_dir).mkdir(parents=True, exist_ok=True)

    for i, prompt in enumerate(prompts):
        logger.info(f"[cogview] Generando imagen {i+1}/{len(prompts)}")

        timestamp = __import__("datetime").datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_prompt = "".join(c for c in prompt if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_prompt = safe_prompt[:50].replace(' ', '_')
        filename = f"img_{i+1}_{safe_prompt}_{timestamp}.png"
        save_path = os.path.join(save_dir, filename)

        result = generate_image(prompt=prompt, save_path=save_path)
        results.append(result)

        # Rate limiting delay
        if i < len(prompts) - 1:
            time.sleep(delay_seconds)

    return results


if __name__ == "__main__":
    # Test rápido
    test_result = generate_image(
        prompt="A professional software engineer working at a modern desk with multiple monitors, coffee cup, clean minimalist office, warm lighting, high quality",
        save_path="test_cogview.png",
    )

    print(f"Resultado: {test_result['success']}")
    if test_result["success"]:
        print(f"URL: {test_result['url']}")
        print(f"Guardada en: {test_result['local_path']}")
    else:
        print(f"Error: {test_result.get('error')}")