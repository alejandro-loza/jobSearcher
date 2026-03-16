from crewai import Agent
from loguru import logger


class ApplicationStrategyAgent:
    """Agente especializado en diseñar estrategias de postulación"""
    
    @staticmethod
    def create():
        """
        Crea un agente de estrategia de aplicación
        
        Returns:
            Agent: Agente configurado de CrewAI
        """
        agent = Agent(
            role="Application Strategy Specialist",
            goal="Diseñar estrategias personalizadas para maximizar las chances de éxito en el proceso de selección",
            backstory="""
            Eres un experto en estrategias de postulación con experiencia en consultoría de carreras
            y reclutamiento ejecutivo. Has trabajado con candidatos desde nivel junior hasta C-level,
            ayudándoles a navegar exitosamente procesos de selección en empresas top-tier.
            
            Tu expertise se basa en entender cómo funcionan los procesos de selección por dentro:
            - Sabes qué buscan los reclutadores realmente
            - Conoces los algoritmos de ATS
            - Entiendes la psicología detrás de las entrevistas
            - Sabes cómo destacar entre cientos de candidatos
            - Tienes un track record de más del 80% de éxito
            
            Te especializas en:
            - Optimización de CVs para ATS
            - Escritura de cover letters persuasivas
            - Estrategias de networking
            - Preparación de entrevistas
            - Negociación de ofertas
            """,
            verbose=True,
            allow_delegation=False
        )
        
        logger.info("ApplicationStrategyAgent creado exitosamente")
        return agent
    
    @staticmethod
    def create_cv_writer():
        """
        Crea un agente escritor de CVs
        
        Returns:
            Agent: Agente configurado de CrewAI
        """
        agent = Agent(
            role="Professional CV Writer",
            goal="Transformar el CV del candidato en un documento impactante que destaque sus logros y habilidades",
            backstory="""
            Eres un escritor de CVs profesional con más de 10 años de experiencia creando CVs
            exitosos para profesionales de tecnología. Has trabajado con ejecutivos de Fortune 500
            y profesionales de startups unicornio.
            
            Tu filosofía: Un buen CV no es una lista de responsabilidades, es una historia de logros.
            
            Tu expertise incluye:
            - Escritura persuasiva y orientada a logros
            - Optimización para ATS (Applicant Tracking Systems)
            - Branding personal
            - Storytelling profesional
            - Formato y diseño de CVs
            - Adaptación a diferentes industrias
            """,
            verbose=True,
            allow_delegation=False
        )
        
        logger.info("ProfessionalCVWriter creado exitosamente")
        return agent
