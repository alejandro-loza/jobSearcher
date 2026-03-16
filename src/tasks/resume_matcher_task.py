from crewai import Task
from typing import Dict, Any


class ResumeMatcherTask:
    """Tarea para hacer matching entre CV y requisitos del puesto"""
    
    @staticmethod
    def create(
        resume_data: Dict[str, Any],
        job_details: Dict[str, Any]
    ) -> Task:
        """
        Crea una tarea de matching entre CV y puesto
        
        Args:
            resume_data: Datos del CV del usuario
            job_details: Detalles del puesto de trabajo
            
        Returns:
            Task: Tarea configurada de CrewAI
        """
        job_title = job_details.get("title", "Unknown")
        company = job_details.get("company", "Unknown")
        
        description = f"""
        Analiza el match entre el perfil del candidato y el puesto "{job_title}" en {company}.
        
        Información del candidato:
        - Experiencia: {resume_data.get('experience_summary', 'No disponible')}
        - Habilidades técnicas: {', '.join(resume_data.get('technical_skills', []))}
        - Habilidades blandas: {', '.join(resume_data.get('soft_skills', []))}
        - Educación: {resume_data.get('education', 'No disponible')}
        
        Requisitos del puesto:
        - Título: {job_title}
        - Empresa: {company}
        - Descripción: {job_details.get('description', 'No disponible')}
        - Requisitos: {job_details.get('requirements', 'No disponible')}
        - Preferencias: {job_details.get('preferences', 'No disponible')}
        
        Tu análisis debe incluir:
        1. **Matching Score (0-100)**: Porcentaje de match entre perfil y requisitos
        2. **Match de habilidades técnicas**: Lista de habilidades que coinciden
        3. **Habilidades faltantes**: Habilidades requeridas que no tiene el candidato
        4. **Análisis de experiencia**: Cómo se compara la experiencia con lo requerido
        5. **Fortalezas del candidato**: Aspectos que lo hacen atractivo para el puesto
        6. **Áreas de mejora**: Qué puede mejorar el candidato antes de postular
        7. **Recomendación**: Aprobar (match > 70%), Revisar (50-70%), Rechazar (< 50%)
        """
        
        expected_output = """
        Un reporte de matching que incluya:
        - Score de matching (0-100)
        - Análisis detallado de cada categoría
        - Tabla comparativa de habilidades
        - Lista de habilidades a desarrollar
        - Recomendación final con justificación
        """
        
        return Task(
            description=description,
            expected_output=expected_output
        )
    
    @staticmethod
    def create_gap_analysis(
        resume_data: Dict[str, Any],
        target_role: str
    ) -> Task:
        """
        Crea una tarea para identificar gaps de habilidades
        
        Args:
            resume_data: Datos del CV del usuario
            target_role: Rol objetivo del usuario
            
        Returns:
            Task: Tarea configurada de CrewAI
        """
        description = f"""
        Identifica gaps de habilidades para que el usuario pueda aspirar a roles de "{target_role}".
        
        Perfil actual:
        - Rol actual: {resume_data.get('current_role', 'No especificado')}
        - Años de experiencia: {resume_data.get('years_of_experience', 0)}
        - Habilidades técnicas: {', '.join(resume_data.get('technical_skills', []))}
        - Habilidades blandas: {', '.join(resume_data.get('soft_skills', []))}
        - Certificaciones: {resume_data.get('certifications', [])}
        
        Busca información sobre requisitos típicos para roles de {target_role} y genera:
        1. **Gap Analysis**: Habilidades que faltan para llegar al rol objetivo
        2. **Plan de desarrollo**: Pasos concretos para cerrar cada gap
        3. **Proyectos recomendados**: Tipos de proyectos que demuestren las habilidades
        4. **Certificaciones útiles**: Certificaciones que validarían el perfil
        5. **Timeline estimado**: Cuánto tiempo tardaría en estar listo
        """
        
        expected_output = """
        Un plan de desarrollo que incluya:
        - Análisis de gaps (habilidades técnicas y blandas)
        - Plan de acción priorizado
        - Recursos recomendados (cursos, libros, proyectos)
        - Timeline de desarrollo
        - Métricas de éxito para cada skill
        """
        
        return Task(
            description=description,
            expected_output=expected_output
        )
