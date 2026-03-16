import httpx
import json
from typing import Dict, Any, List, Optional
from loguru import logger
from config import settings


class LinkedInMCPTool:
    """Herramienta para interactuar con LinkedIn MCP Server"""
    
    def __init__(self, server_url: Optional[str] = None):
        self.server_url = server_url or settings.linkedin_mcp_server_url
        self.enabled = settings.linkedin_mcp_enabled
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def _send_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Envía una petición al servidor MCP"""
        if not self.enabled:
            logger.warning("LinkedIn MCP está deshabilitado")
            return {"error": "LinkedIn MCP no está habilitado"}
        
        url = f"{self.server_url}/{endpoint}"
        
        try:
            response = await self.client.request(
                method=method,
                url=url,
                json=data,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Error en petición MCP: {e}")
            return {"error": str(e)}
        except json.JSONDecodeError as e:
            logger.error(f"Error decodificando respuesta: {e}")
            return {"error": "Error al decodificar respuesta"}
    
    async def search_jobs(
        self, 
        keywords: str, 
        location: str = "remote",
        job_type: str = "full-time",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Busca empleos en LinkedIn"""
        data = {
            "keywords": keywords,
            "location": location,
            "job_type": job_type,
            "limit": limit
        }
        result = await self._send_request("POST", "search/jobs", data)
        
        if "error" in result:
            logger.error(f"Error buscando empleos: {result['error']}")
            return []
        
        return result.get("jobs", [])
    
    async def get_job_details(self, job_id: str) -> Dict[str, Any]:
        """Obtiene detalles de un empleo específico"""
        result = await self._send_request("GET", f"jobs/{job_id}")
        return result
    
    async def get_profile_details(self, profile_url: str) -> Dict[str, Any]:
        """Obtiene detalles de un perfil de LinkedIn"""
        data = {"profile_url": profile_url}
        result = await self._send_request("POST", "profile/analyze", data)
        return result
    
    async def apply_to_job(self, job_id: str, message: Optional[str] = None) -> Dict[str, Any]:
        """Aplica a un empleo"""
        data = {
            "job_id": job_id,
            "message": message
        }
        result = await self._send_request("POST", "jobs/apply", data)
        return result
    
    async def search_profiles(
        self, 
        keywords: str, 
        location: str = "",
        company: str = "",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Busca perfiles en LinkedIn"""
        data = {
            "keywords": keywords,
            "location": location,
            "company": company,
            "limit": limit
        }
        result = await self._send_request("POST", "search/profiles", data)
        
        if "error" in result:
            logger.error(f"Error buscando perfiles: {result['error']}")
            return []
        
        return result.get("profiles", [])
    
    async def get_company_info(self, company_name: str) -> Dict[str, Any]:
        """Obtiene información de una compañía"""
        data = {"company_name": company_name}
        result = await self._send_request("POST", "company/analyze", data)
        return result
    
    async def close(self):
        """Cierra el cliente HTTP"""
        await self.client.aclose()
