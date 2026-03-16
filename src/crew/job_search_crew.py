from crewai import Crew, Process
from loguru import logger
from src.agents import (
    JobSearchAgent, 
    ResumeMatcherAgent, 
    ApplicationStrategyAgent,
    InterviewPrepAgent
)
from src.tasks import (
    JobSearchTask,
    ResumeMatcherTask,
    ApplicationStrategyTask,
    InterviewPrepTask
)
from config import settings


class JobSearchCrew:
    """Crew principal para orquestar el proceso de búsqueda de empleo"""
    
    def __init__(self):
        self.crew = None
        self.agents = {}
        self.tasks = {}
        
    def initialize(self):
        """Inicializa los agentes y el crew"""
        logger.info("Inicializando JobSearchCrew...")
        
        # Crear agentes
        self.agents = {
            "job_searcher": JobSearchAgent.create(),
            "resume_matcher": ResumeMatcherAgent.create(),
            "application_strategist": ApplicationStrategyAgent.create(),
            "interview_prepper": InterviewPrepAgent.create()
        }
        
        logger.info("Agentes creados exitosamente")
    
    def create_job_search_crew(
        self,
        search_params: dict,
        resume_data: dict
    ):
        """
        Crea un crew para búsqueda de empleo
        
        Args:
            search_params: Parámetros de búsqueda
            resume_data: Datos del CV del usuario
            
        Returns:
            Crew: Crew configurado de CrewAI
        """
        logger.info("Creando crew de búsqueda de empleo...")
        
        # Crear tareas
        tasks = [
            JobSearchTask.create(search_params),
            ResumeMatcherTask.create(resume_data, search_params)
        ]
        
        # Crear crew
        self.crew = Crew(
            agents=[
                self.agents["job_searcher"],
                self.agents["resume_matcher"]
            ],
            tasks=tasks,
            process=Process.hierarchical,
            verbose=True,
            memory=settings.crewai_memory_enabled,
            cache=settings.crewai_cache_enabled
        )
        
        logger.info("Crew de búsqueda de empleo creado")
        return self.crew
    
    def create_full_analysis_crew(
        self,
        search_params: dict,
        resume_data: dict,
        job_details: dict,
        matching_score: int
    ):
        """
        Crea un crew para análisis completo
        
        Args:
            search_params: Parámetros de búsqueda
            resume_data: Datos del CV del usuario
            job_details: Detalles del puesto
            matching_score: Score de matching
            
        Returns:
            Crew: Crew configurado de CrewAI
        """
        logger.info("Creando crew de análisis completo...")
        
        # Crear tareas
        tasks = [
            JobSearchTask.create(search_params),
            ResumeMatcherTask.create(resume_data, job_details),
            ApplicationStrategyTask.create(resume_data, job_details, matching_score),
            InterviewPrepTask.create(job_details)
        ]
        
        # Crear crew
        self.crew = Crew(
            agents=[
                self.agents["job_searcher"],
                self.agents["resume_matcher"],
                self.agents["application_strategist"],
                self.agents["interview_prepper"]
            ],
            tasks=tasks,
            process=Process.hierarchical,
            verbose=True,
            memory=settings.crewai_memory_enabled,
            cache=settings.crewai_cache_enabled
        )
        
        logger.info("Crew de análisis completo creado")
        return self.crew
    
    def create_career_development_crew(
        self,
        resume_data: dict,
        target_role: str
    ):
        """
        Crea un crew para desarrollo de carrera
        
        Args:
            resume_data: Datos del CV del usuario
            target_role: Rol objetivo
            
        Returns:
            Crew: Crew configurado de CrewAI
        """
        logger.info("Creando crew de desarrollo de carrera...")
        
        # Crear agentes específicos
        career_coach = ResumeMatcherAgent.create_career_coach()
        cv_writer = ApplicationStrategyAgent.create_cv_writer()
        
        # Crear tareas
        tasks = [
            ResumeMatcherTask.create_gap_analysis(resume_data, target_role),
            ApplicationStrategyTask.create_resume_optimization(resume_data, [])
        ]
        
        # Crear crew
        self.crew = Crew(
            agents=[
                career_coach,
                cv_writer
            ],
            tasks=tasks,
            process=Process.sequential,
            verbose=True,
            memory=settings.crewai_memory_enabled,
            cache=settings.crewai_cache_enabled
        )
        
        logger.info("Crew de desarrollo de carrera creado")
        return self.crew
    
    def create_interview_prep_crew(
        self,
        job_details: dict,
        user_skills: list,
        user_experience: str
    ):
        """
        Crea un crew para preparación de entrevistas
        
        Args:
            job_details: Detalles del puesto
            user_skills: Lista de habilidades del usuario
            user_experience: Experiencia del usuario
            
        Returns:
            Crew: Crew configurado de CrewAI
        """
        logger.info("Creando crew de preparación de entrevistas...")
        
        # Crear agentes específicos
        technical_interviewer = InterviewPrepAgent.create_technical_interviewer()
        behavioral_coach = InterviewPrepAgent.create_behavioral_coach()
        
        # Crear tareas
        tasks = [
            InterviewPrepTask.create(job_details),
            InterviewPrepTask.create_technical_prep(job_details, user_skills),
            InterviewPrepTask.create_behavioral_prep(user_experience)
        ]
        
        # Crear crew
        self.crew = Crew(
            agents=[
                technical_interviewer,
                behavioral_coach
            ],
            tasks=tasks,
            process=Process.sequential,
            verbose=True,
            memory=settings.crewai_memory_enabled,
            cache=settings.crewai_cache_enabled
        )
        
        logger.info("Crew de preparación de entrevistas creado")
        return self.crew
    
    async def kickoff(self, inputs: dict = None):
        """
        Ejecuta el crew
        
        Args:
            inputs: Inputs para el crew
            
        Returns:
            Resultado de la ejecución del crew
        """
        if not self.crew:
            raise ValueError("El crew no ha sido creado. Llama a uno de los métodos create_* primero.")
        
        logger.info("Iniciando ejecución del crew...")
        result = await self.crew.kickoff(inputs=inputs)
        logger.info("Crew ejecutado exitosamente")
        
        return result
