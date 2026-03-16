from crewai import Task
from typing import List, Dict, Any


class JobSearchTask:
    """Tarea para buscar empleos en LinkedIn"""
    
    @staticmethod
    def create(
        search_params: Dict[str, Any],
        context: str = ""
    ) -> Task:
        """
        Crea una tarea de búsqueda de empleo
        
        Args:
            search_params: Parámetros de búsqueda (keywords, location, job_type, limit)
            context: Contexto adicional para la búsqueda
            
        Returns:
            Task: Tarea configurada de CrewAI
        """
        keywords = search_params.get("keywords", "software engineer")
        location = search_params.get("location", "remote")
        job_type = search_params.get("job_type", "full-time")
        limit = search_params.get("limit", 10)
        
        description = f"""
        Busca empleos en LinkedIn con los siguientes criterios:
        - Keywords: {keywords}
        - Ubicación: {location}
        - Tipo de trabajo: {job_type}
        - Límite de resultados: {limit}
        
        Usa la herramienta LinkedInMCPTool.search_jobs para encontrar empleos.
        Para cada empleo encontrado, obtén los detalles completos usando LinkedInMCPTool.get_job_details.
        
        Contexto adicional:
        {context}
        
        Genera un reporte con:
        1. Lista de empleos encontrados (título, empresa, ubicación)
        2. Requisitos principales de cada puesto
        3. Salary range si está disponible
        4. URL de la oferta
        5. Score de relevancia (1-10) basado en la descripción
        """
        
        expected_output = """
        Un reporte estructurado con los empleos encontrados que incluya:
        - Resumen de búsqueda (número de resultados, parámetros usados)
        - Detalles de cada empleo relevante
        - Análisis de requisitos y habilidades
        - Recomendación de cuáles son más prometedores
        """
        
        return Task(
            description=description,
            expected_output=expected_output,
            async_execution=True
        )
    
    @staticmethod
    def create_company_analysis(company_name: str) -> Task:
        """
        Crea una tarea para analizar una compañía específica
        
        Args:
            company_name: Nombre de la compañía a analizar
            
        Returns:
            Task: Tarea configurada de CrewAI
        """
        description = f"""
        Analiza la compañía "{company_name}" en LinkedIn.
        
        Usa la herramienta LinkedInMCPTool.get_company_info para obtener:
        - Tamaño de la empresa
        - Industria
        - Ubicaciones
        - Cultura empresarial
        - Empleados clave
        - Noticias recientes
        
        Genera un análisis completo que incluya:
        1. Perfil de la compañía
        2. Ventajas y desventajas de trabajar allí
        3. Estabilidad financiera (si se puede inferir)
        4. Oportunidades de crecimiento
        5. Recomendación para postular
        """
        
        expected_output = """
        Un análisis detallado de la compañía que incluya:
        - Perfil corporativo
        - Análisis de cultura y valores
        - Pros y contras como empleador
        - Nivel de competitividad del proceso de selección
        - Recomendaciones para maximizar chances de éxito
        """
        
        return Task(
            description=description,
            expected_output=expected_output
        )
