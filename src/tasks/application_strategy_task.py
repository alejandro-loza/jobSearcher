from crewai import Task
from typing import Dict, Any


class ApplicationStrategyTask:
    """Tarea para diseñar estrategia de postulación"""
    
    @staticmethod
    def create(
        resume_data: Dict[str, Any],
        job_details: Dict[str, Any],
        matching_score: int
    ) -> Task:
        """
        Crea una tarea de estrategia de postulación
        
        Args:
            resume_data: Datos del CV del usuario
            job_details: Detalles del puesto de trabajo
            matching_score: Score de matching (0-100)
            
        Returns:
            Task: Tarea configurada de CrewAI
        """
        job_title = job_details.get("title", "Unknown")
        company = job_details.get("company", "Unknown")
        
        description = f"""
        Diseña una estrategia personalizada para postular a "{job_title}" en {company}.
        
        Perfil del candidato:
        - Experiencia: {resume_data.get('experience_summary', '')}
        - Habilidades: {', '.join(resume_data.get('technical_skills', []))}
        - Logros destacados: {resume_data.get('achievements', [])}
        
        Detalles del puesto:
        - Título: {job_title}
        - Empresa: {company}
        - Descripción: {job_details.get('description', '')}
        - Requisitos: {job_details.get('requirements', '')}
        
        Matching score: {matching_score}%
        
        Genera una estrategia que incluya:
        
        1. **Análisis de la empresa**: Qué valores de la compañía debería resaltar
        2. **Mejoras sugeridas para el CV**: Cómo adaptar el CV para este puesto específico
        3. **Cover Letter**: Propuesta de carta de presentación personalizada
        4. **Message de conexión**: Mensaje para conectar con reclutadores
        5. **Timing**: Cuándo aplicar para maximizar chances
        6. **Enfoque**: Cómo posicionarse (seniority, especialización, etc.)
        7. **Keywords**: Keywords importantes a incluir
        """
        
        expected_output = """
        Una estrategia completa que incluya:
        - Análisis de la compañía y cultura
        - CV adaptado (secciones a modificar/enfatizar)
        - Cover Letter personalizada
        - Mensaje de LinkedIn para reclutadores
        - Checklist de antes/después de aplicar
        - Contingency plan (si no hay respuesta)
        """
        
        return Task(
            description=description,
            expected_output=expected_output
        )
    
    @staticmethod
    def create_resume_optimization(
        current_resume: Dict[str, Any],
        target_jobs: list[Dict[str, Any]]
    ) -> Task:
        """
        Crea una tarea para optimizar el CV para múltiples puestos
        
        Args:
            current_resume: CV actual del usuario
            target_jobs: Lista de puestos objetivo
            
        Returns:
            Task: Tarea configurada de CrewAI
        """
        job_titles = [job.get("title", "Unknown") for job in target_jobs]
        
        description = f"""
        Optimiza el CV del usuario para roles: {', '.join(job_titles)}.
        
        CV actual:
        - Título profesional: {current_resume.get('professional_title', '')}
        - Resumen: {current_resume.get('summary', '')}
        - Experiencia: {current_resume.get('experience', [])}
        - Habilidades: {current_resume.get('skills', [])}
        - Educación: {current_resume.get('education', [])}
        
        Puestos objetivo:
        {ApplicationStrategyTask._format_jobs_for_prompt(target_jobs)}
        
        Tu objetivo es crear una versión optimizada del CV que:
        1. Use ATS-friendly keywords
        2. Destaque logros cuantificables
        3. Alinee la experiencia con requisitos de los puestos
        4. Mejore el resumen profesional
        5. Reorganice habilidades por relevancia
        6. Sugiera proyectos/certificaciones a añadir
        """
        
        expected_output = """
        Un CV optimizado que incluya:
        - Resumen profesional mejorado
        - Experiencia reestructurada con logros destacados
        - Sección de habilidades organizada por categoría
        - Palabras clave ATS-friendly
        - Lista de proyectos/sertificaciones a añadir
        - Before/After comparación
        """
        
        return Task(
            description=description,
            expected_output=expected_output
        )
    
    @staticmethod
    def _format_jobs_for_prompt(jobs: list) -> str:
        """Formatea lista de puestos para el prompt"""
        formatted = []
        for job in jobs:
            formatted.append(f"""
            - {job.get('title', 'Unknown')}: {job.get('requirements', '')}
            """)
        return "\n".join(formatted)
