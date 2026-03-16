from loguru import logger
from src.crew import JobSearchCrew
from config import settings


def main():
    """Función principal de la aplicación"""
    
    # Configurar logging
    logger.add(
        f"{settings.log_dir}/jobsearcher.log",
        rotation="10 MB",
        level=settings.log_level
    )
    
    logger.info("=== JobSearcher - AI-Powered Job Search ===")
    
    # Inicializar el crew
    crew_manager = JobSearchCrew()
    crew_manager.initialize()
    
    # Ejemplo de uso: búsqueda de empleos
    search_params = {
        "keywords": "python developer",
        "location": "remote",
        "job_type": "full-time",
        "limit": 10
    }
    
    # Ejemplo de CV (en producción esto vendría de un archivo o input)
    resume_data = {
        "current_role": "Python Developer",
        "years_of_experience": 3,
        "technical_skills": [
            "Python", "Django", "FastAPI", "PostgreSQL", 
            "Docker", "AWS", "Git", "REST APIs"
        ],
        "soft_skills": [
            "Teamwork", "Problem Solving", "Communication", 
            "Adaptability", "Leadership"
        ],
        "experience_summary": """
        Desarrollador Python con 3 años de experiencia construyendo
        aplicaciones web y APIs escalables. Experiencia en microservicios,
        arquitectura cloud y metodologías ágiles.
        """,
        "education": "Ingeniería de Sistemas, Universidad XYZ",
        "certifications": ["AWS Certified Developer"],
        "achievements": [
            "Redució tiempo de carga de APIs en 40%",
            "Lideró equipo de 4 desarrolladores",
            "Implementó CI/CD pipeline"
        ]
    }
    
    # Crear y ejecutar crew de búsqueda
    try:
        crew = crew_manager.create_job_search_crew(
            search_params=search_params,
            resume_data=resume_data
        )
        
        logger.info("Ejecutando búsqueda de empleos...")
        result = crew.kickoff()
        
        logger.success("Búsqueda completada exitosamente")
        print("\n" + "="*50)
        print("RESULTADO:")
        print("="*50)
        print(result)
        
    except Exception as e:
        logger.error(f"Error durante la ejecución: {e}")
        raise


if __name__ == "__main__":
    main()
