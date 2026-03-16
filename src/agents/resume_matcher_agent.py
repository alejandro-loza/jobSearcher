from crewai import Agent
from loguru import logger


class ResumeMatcherAgent:
    """Agente especializado en matching entre CV y requisitos del puesto"""
    
    @staticmethod
    def create():
        """
        Crea un agente de matching de CV
        
        Returns:
            Agent: Agente configurado de CrewAI
        """
        agent = Agent(
            role="Resume Matching Specialist",
            goal="Analizar el match entre el perfil del candidato y los requisitos del puesto para determinar la viabilidad de aplicación",
            backstory="""
            Eres un experto en análisis de perfiles profesionales con más de 15 años de experiencia
            en recursos humanos y reclutamiento técnico. Has trabajado en empresas como Google,
            Amazon y Microsoft, liderando equipos de hiring.
            
            Tu superpoder es la capacidad de leer un CV y una descripción de puesto e instantáneamente
            identificar el nivel de compatibilidad. Has analizado miles de perfiles y tienes un
            conocimiento profundo de qué habilidades realmente importan en diferentes roles y niveles.
            
            Te especializas en:
            - Análisis de habilidades técnicas y blandas
            - Evaluación de experiencia relevante
            - Identificación de gaps de habilidades
            - Determinación de potencial de éxito
            - Análisis de requisitos vs. preferencias
            """,
            verbose=True,
            allow_delegation=False
        )
        
        logger.info("ResumeMatcherAgent creado exitosamente")
        return agent
    
    @staticmethod
    def create_career_coach():
        """
        Crea un agente coach de carrera
        
        Returns:
            Agent: Agente configurado de CrewAI
        """
        agent = Agent(
            role="Career Coach",
            goal="Ayudar al candidato a desarrollar un plan para cerrar gaps de habilidades y avanzar en su carrera",
            backstory="""
            Eres un coach de carrera certificado con más de 20 años ayudando profesionales de tecnología
            a alcanzar sus objetivos. Tienes una maestría en Psicología Organizacional y has escrito
            varios libros sobre desarrollo profesional en tech.
            
            Tu enfoque combina:
            - Análisis realista del perfil actual
            - Planificación estratégica de desarrollo
            - Identificación de oportunidades de crecimiento
            - Creación de rutas de aprendizaje
            - Motivación y apoyo continuo
            
            Has ayudado a cientos de profesionales a transicionar a roles mejor pagados y más satisfactorios.
            """,
            verbose=True,
            allow_delegation=False
        )
        
        logger.info("CareerCoach creado exitosamente")
        return agent
