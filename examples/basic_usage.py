"""
Ejemplo de uso básico de JobSearcher

Este ejemplo muestra cómo:
1. Configurar el crew
2. Buscar empleos
3. Analizar matching con el CV
"""

import asyncio
from src.crew import JobSearchCrew
from src.utils.storage import DataStorage, ReportGenerator


async def example_basic_search():
    """Ejemplo básico de búsqueda de empleo"""
    
    # Inicializar storage
    storage = DataStorage()
    
    # Cargar CV de ejemplo
    try:
        resume_data = storage.load_resume("resume_example.json")
        print("CV cargado exitosamente")
    except FileNotFoundError:
        print("Error: No se encontró el CV de ejemplo")
        return
    
    # Configurar crew
    crew_manager = JobSearchCrew()
    crew_manager.initialize()
    
    # Parámetros de búsqueda
    search_params = {
        "keywords": "python developer senior",
        "location": "remote",
        "job_type": "full-time",
        "limit": 5
    }
    
    # Crear crew de búsqueda
    crew = crew_manager.create_job_search_crew(
        search_params=search_params,
        resume_data=resume_data
    )
    
    # Ejecutar búsqueda
    print("\n" + "="*60)
    print("INICIANDO BÚSQUEDA DE EMPLEOS")
    print("="*60)
    result = await crew.kickoff()
    
    print("\n" + "="*60)
    print("RESULTADO")
    print("="*60)
    print(result)


async def example_full_analysis():
    """Ejemplo de análisis completo de un puesto"""
    
    # Inicializar storage
    storage = DataStorage()
    
    # Cargar datos
    try:
        resume_data = storage.load_resume("resume_example.json")
        jobs = storage.load_jobs()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return
    
    if not jobs:
        print("No hay empleos guardados. Ejecuta primero example_basic_search")
        return
    
    # Seleccionar el primer job
    job_details = jobs[0]
    
    # Configurar crew
    crew_manager = JobSearchCrew()
    crew_manager.initialize()
    
    # Crear crew de análisis completo
    crew = crew_manager.create_full_analysis_crew(
        search_params={},
        resume_data=resume_data,
        job_details=job_details,
        matching_score=75
    )
    
    # Ejecutar análisis
    print("\n" + "="*60)
    print("INICIANDO ANÁLISIS COMPLETO")
    print("="*60)
    result = await crew.kickoff()
    
    print("\n" + "="*60)
    print("RESULTADO DEL ANÁLISIS")
    print("="*60)
    print(result)


async def example_interview_prep():
    """Ejemplo de preparación para entrevista"""
    
    # Inicializar storage
    storage = DataStorage()
    
    # Cargar datos
    try:
        resume_data = storage.load_resume("resume_example.json")
        jobs = storage.load_jobs()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return
    
    if not jobs:
        print("No hay empleos guardados. Ejecuta primero example_basic_search")
        return
    
    # Seleccionar el primer job
    job_details = jobs[0]
    
    # Configurar crew
    crew_manager = JobSearchCrew()
    crew_manager.initialize()
    
    # Crear crew de preparación de entrevista
    crew = crew_manager.create_interview_prep_crew(
        job_details=job_details,
        user_skills=resume_data['technical_skills'],
        user_experience=resume_data['experience_summary']
    )
    
    # Ejecutar preparación
    print("\n" + "="*60)
    print("INICIANDO PREPARACIÓN DE ENTREVISTA")
    print("="*60)
    result = await crew.kickoff()
    
    print("\n" + "="*60)
    print("RESULTADO DE PREPARACIÓN")
    print("="*60)
    print(result)


async def main():
    """Ejecuta los ejemplos"""
    print("=== JOBSEARCHER - EJEMPLOS DE USO ===\n")
    
    # Ejemplo 1: Búsqueda básica
    print("EJEMPLO 1: Búsqueda básica de empleos")
    print("-" * 60)
    await example_basic_search()
    
    # Ejemplo 2: Análisis completo
    print("\n\nEJEMPLO 2: Análisis completo de un puesto")
    print("-" * 60)
    await example_full_analysis()
    
    # Ejemplo 3: Preparación de entrevista
    print("\n\nEJEMPLO 3: Preparación de entrevista")
    print("-" * 60)
    await example_interview_prep()


if __name__ == "__main__":
    asyncio.run(main())
