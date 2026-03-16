from crewai import Agent
from src.tools import LinkedInMCPTool
from src.utils.llm_factory import get_llm_for_agent
from loguru import logger


class JobSearchAgent:
    """Agente especializado en búsqueda de empleos en LinkedIn"""

    @staticmethod
    def create():
        """
        Crea un agente de búsqueda de empleo

        Returns:
            Agent: Agente configurado de CrewAI
        """
        linkedin_tool = LinkedInMCPTool()

        agent = Agent(
            role="Job Search Specialist",
            llm=get_llm_for_agent("job_searcher"),
            goal="Encontrar las mejores oportunidades de empleo en LinkedIn que coincidan con el perfil del candidato",
            backstory="""
            Eres un experto en búsqueda de empleo con más de 10 años de experiencia en reclutamiento
            y análisis de mercado laboral. Conoces profundamente LinkedIn y sus algoritmos de búsqueda.
            Tu habilidad para encontrar oportunidades ocultas y analizar la calidad de los puestos es legendaria.
            Has ayudado a cientos de profesionales a encontrar su trabajo ideal.
            
            Te especializas en:
            - Búsqueda avanzada en LinkedIn
            - Análisis de descripciones de puestos
            - Identificación de oportunidades de alta calidad
            - Evaluación de requisitos vs. realidad
            - Determinación de salary ranges y beneficios
            """,
            verbose=True,
            allow_delegation=False,
            tools=[
                linkedin_tool.search_jobs,
                linkedin_tool.get_job_details,
                linkedin_tool.get_company_info,
            ],
        )

        logger.info("JobSearchAgent creado exitosamente")
        return agent

    @staticmethod
    def create_researcher():
        """
        Crea un agente investigador de mercado laboral

        Returns:
            Agent: Agente configurado de CrewAI
        """
        linkedin_tool = LinkedInMCPTool()

        agent = Agent(
            role="Labor Market Researcher",
            llm=get_llm_for_agent("job_searcher"),
            goal="Investigar tendencias del mercado laboral y análisis de empresas para informar la estrategia de búsqueda",
            backstory="""
            Eres un analista de mercado laboral especializado en tendencias de la industria tecnológica.
            Tienes un MBA con especialización en análisis de recursos humanos y has trabajado para 
            empresas como LinkedIn, Glassdoor y empresas de headhunting top-tier.
            
            Tu expertise incluye:
            - Análisis de tendencias salariales
            - Evaluación de cultura empresarial
            - Investigación de crecimiento de empresas
            - Análisis de estabilidad financiera
            - Identificación de mercados emergentes
            """,
            verbose=True,
            allow_delegation=False,
            tools=[
                linkedin_tool.search_profiles,
                linkedin_tool.get_company_info,
                linkedin_tool.get_profile_details,
            ],
        )

        logger.info("LaborMarketResearcher creado exitosamente")
        return agent
