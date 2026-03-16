from crewai import Task
from typing import Dict, Any, List


class InterviewPrepTask:
    """Tarea para preparar entrevistas"""
    
    @staticmethod
    def create(job_details: Dict[str, Any]) -> Task:
        """
        Crea una tarea de preparación para entrevista
        
        Args:
            job_details: Detalles del puesto de trabajo
            
        Returns:
            Task: Tarea configurada de CrewAI
        """
        job_title = job_details.get("title", "Unknown")
        company = job_details.get("company", "Unknown")
        
        description = f"""
        Prepara al usuario para una entrevista de "{job_title}" en {company}.
        
        Detalles del puesto:
        - Título: {job_title}
        - Empresa: {company}
        - Descripción: {job_details.get('description', '')}
        - Requisitos técnicos: {job_details.get('requirements', '')}
        - Responsabilidades: {job_details.get('responsibilities', '')}
        
        Genera un plan de preparación que incluya:
        
        1. **Preguntas de entrevista**: 
           - Preguntas técnicas esperadas
           - Preguntas de comportamiento
           - Preguntas sobre cultura de la empresa
        
        2. **Respuestas sugeridas**:
           - Para cada pregunta técnica, da una respuesta modelo
           - Incluye STAR method para preguntas de comportamiento
        
        3. **Preguntas para hacer al entrevistador**:
           - Lista de preguntas estratégicas
           - Explicación de por qué hacer cada pregunta
        
        4. **Investigación de la empresa**:
           - Qué investigar sobre la compañía
           - Puntos clave a mencionar
        
        5. **Tips específicos**:
           - Dress code (si aplica)
           - Formato de entrevista
           - Qué esperar del proceso
        """
        
        expected_output = """
        Un guide completo de entrevista que incluya:
        - 15-20 preguntas probables con respuestas
        - 10 preguntas estratégicas para el entrevistador
        - Checklist de preparación (24h antes, 1h antes)
        - Research guide de la empresa
        - Tips de éxito para esta empresa específica
        """
        
        return Task(
            description=description,
            expected_output=expected_output
        )
    
    @staticmethod
    def create_technical_prep(
        job_details: Dict[str, Any],
        user_skills: List[str]
    ) -> Task:
        """
        Crea una tarea de preparación técnica
        
        Args:
            job_details: Detalles del puesto de trabajo
            user_skills: Lista de habilidades del usuario
            
        Returns:
            Task: Tarea configurada de CrewAI
        """
        job_title = job_details.get("title", "Unknown")
        
        description = f"""
        Prepara al usuario para la entrevista técnica de "{job_title}".
        
        Habilidades del usuario:
        {', '.join(user_skills)}
        
        Requisitos del puesto:
        {job_details.get('requirements', '')}
        
        Genera:
        
        1. **Código de práctica**:
           - 3-5 problemas de código que podrían pedir
           - Soluciones en Python
           - Análisis de complejidad
           - Explicaciones paso a paso
        
        2. **Conceptos técnicos**:
           - Definiciones clave a conocer
           - Trade-offs comunes
           - Patrones de diseño relevantes
        
        3. **System Design** (si aplica):
           - Arquitectura a conocer
           - Preguntas probables
           - Diagramas sugeridos
        
        4. **Quiz rápido**:
           - 20 preguntas de selección múltiple
           - Soluciones con explicaciones
        """
        
        expected_output = """
        Un pack de preparación técnica que incluya:
        - 5 ejercicios de código con soluciones
        - 15 definiciones conceptuales clave
        - 2 problemas de system design
        - 20 preguntas de quiz con respuestas
        """
        
        return Task(
            description=description,
            expected_output=expected_output
        )
    
    @staticmethod
    def create_behavioral_prep(
        user_experience: str
    ) -> Task:
        """
        Crea una tarea de preparación de entrevistas comportamentales
        
        Args:
            user_experience: Resumen de experiencia del usuario
            
        Returns:
            Task: Tarea configurada de CrewAI
        """
        description = f"""
        Prepara al usuario para entrevistas comportamentales usando su experiencia.
        
        Experiencia del usuario:
        {user_experience}
        
        Basado en su experiencia, genera:
        
        1. **Historias STAR**:
           - 8-10 historias usando el método STAR (Situation, Task, Action, Result)
           - Categorizadas por competencias (leadership, problem-solving, teamwork, etc.)
           - Adaptadas a su experiencia real
        
        2. **Preguntas difíciles**:
           - Preguntas "gotcha" que podrían hacer
           - Cómo manejarlas
           - Respuestas diplomáticas
        
        3. **Weakness handling**:
           - 3 debilidades reales a mencionar
           - Cómo presentarlas como áreas de mejora
           - Plan de mitigación
        
        4. **Success stories**:
           - 3 logros más impactantes
           - Cómo contarlos de forma memorable
        """
        
        expected_output = """
        Un set de historias STAR que incluya:
        - 10 historias categorizadas
        - Guía para adaptarlas a diferentes preguntas
        - Cómo manejar preguntas difíciles
        - Framework para hablar de debilidades
        """
        
        return Task(
            description=description,
            expected_output=expected_output
        )
