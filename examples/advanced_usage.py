"""
Ejemplos avanzados de uso de JobSearcher

Este archivo muestra casos de uso más avanzados y complejos.
"""

import asyncio
from src.crew import JobSearchCrew
from src.utils.storage import DataStorage, ReportGenerator


async def example_multi_stage_workflow():
    """Ejemplo de workflow multi-etapa completo"""

    print("=" * 60)
    print("WORKFLOW MULTI-ETAPA COMPLETO")
    print("=" * 60)

    # Inicializar
    storage = DataStorage()
    crew_manager = JobSearchCrew()
    crew_manager.initialize()

    # Cargar CV
    try:
        resume_data = storage.load_resume("resume_example.json")
    except FileNotFoundError:
        print("Error: No se encontró CV de ejemplo")
        return

    # ETAPA 1: Búsqueda de empleos
    print("\n--- ETAPA 1: BÚSQUEDA DE EMPLEOS ---")
    search_params = {
        "keywords": "senior python developer",
        "location": "remote",
        "job_type": "full-time",
        "limit": 10,
    }

    crew = crew_manager.create_job_search_crew(
        search_params=search_params, resume_data=resume_data
    )

    search_result = await crew.kickoff()
    print(search_result)

    # Cargar jobs encontrados
    jobs = storage.load_jobs()

    if not jobs:
        print("No se encontraron empleos")
        return

    # ETAPA 2: Análisis de matching para top 5
    print("\n--- ETAPA 2: ANÁLISIS DE MATCHING ---")
    matching_results = []

    for job in jobs[:5]:
        print(f"\nAnalizando: {job.get('title', 'N/A')} en {job.get('company', 'N/A')}")

        # Crear crew de matching
        crew = crew_manager.create_full_analysis_crew(
            search_params={},
            resume_data=resume_data,
            job_details=job,
            matching_score=0,  # Se calculará
        )

        result = await crew.kickoff()
        matching_results.append(result)

    # Guardar resultados de matching
    storage.save_matching_results(matching_results)

    # ETAPA 3: Generar estrategia para el mejor match
    print("\n--- ETAPA 3: ESTRATEGIA DE APLICACIÓN ---")

    # Seleccionar el mejor match (simulado)
    if matching_results:
        best_job = jobs[0]
        best_score = 85  # Simulado

        crew = crew_manager.create_full_analysis_crew(
            search_params={},
            resume_data=resume_data,
            job_details=best_job,
            matching_score=best_score,
        )

        strategy_result = await crew.kickoff()
        print(strategy_result)

    # ETAPA 4: Preparación de entrevista
    print("\n--- ETAPA 4: PREPARACIÓN DE ENTREVISTA ---")

    crew = crew_manager.create_interview_prep_crew(
        job_details=jobs[0],
        user_skills=resume_data["technical_skills"],
        user_experience=resume_data["experience_summary"],
    )

    interview_result = await crew.kickoff()
    print(interview_result)

    print("\n" + "=" * 60)
    print("WORKFLOW COMPLETADO")
    print("=" * 60)


async def example_career_development():
    """Ejemplo de análisis de desarrollo de carrera"""

    print("=" * 60)
    print("ANÁLISIS DE DESARROLLO DE CARRERA")
    print("=" * 60)

    # Inicializar
    storage = DataStorage()
    crew_manager = JobSearchCrew()
    crew_manager.initialize()

    # Cargar CV
    try:
        resume_data = storage.load_resume("resume_example.json")
    except FileNotFoundError:
        print("Error: No se encontró CV de ejemplo")
        return

    # Definir rol objetivo
    target_role = "Staff Software Engineer"

    # Crear crew de desarrollo de carrera
    crew = crew_manager.create_career_development_crew(
        resume_data=resume_data, target_role=target_role
    )

    print(f"\nAnalizando camino hacia: {target_role}")

    result = await crew.kickoff()

    print("\n" + "=" * 60)
    print("RESULTADO DEL ANÁLISIS")
    print("=" * 60)
    print(result)


async def example_company_research():
    """Ejemplo de investigación de compañías"""

    print("=" * 60)
    print("INVESTIGACIÓN DE COMPAÑÍAS")
    print("=" * 60)

    # Compañías a investigar
    companies = ["Google", "Amazon", "Netflix"]

    # Inicializar
    crew_manager = JobSearchCrew()
    crew_manager.initialize()

    for company in companies:
        print(f"\nInvestigando: {company}")

        # Crear tarea de análisis de compañía
        from src.tasks import JobSearchTask

        task = JobSearchTask.create_company_analysis(company)

        # Ejecutar (en producción se usaría el crew completo)
        print(f"Tarea creada para {company}")
        print("- Investigación de tamaño y cultura")
        print("- Análisis de stack tecnológico")
        print("- Evaluación de oportunidades")
        print("- Pros y contras como empleador")


async def example_batch_analysis():
    """Ejemplo de análisis por lotes de múltiples empleos"""

    print("=" * 60)
    print("ANÁLISIS POR LOTES")
    print("=" * 60)

    # Inicializar
    storage = DataStorage()
    crew_manager = JobSearchCrew()
    crew_manager.initialize()

    # Cargar datos
    try:
        resume_data = storage.load_resume("resume_example.json")
        jobs = storage.load_jobs()
    except FileNotFoundError:
        print("Error: No se encontraron datos")
        return

    if not jobs:
        print("No hay empleos para analizar")
        return

    # Procesar en lotes de 3
    batch_size = 3
    total_jobs = len(jobs)

    print(f"\nAnalizando {total_jobs} empleos en lotes de {batch_size}")

    for i in range(0, total_jobs, batch_size):
        batch = jobs[i : i + batch_size]
        print(f"\nProcesando lote {i // batch_size + 1} ({len(batch)} empleos)...")

        for job in batch:
            # Aquí se ejecutaría el análisis
            print(f"  - {job.get('title', 'N/A')} en {job.get('company', 'N/A')}")

            # Simulación de análisis
            crew = crew_manager.create_job_search_crew(
                search_params={}, resume_data=resume_data
            )

            # En producción: await crew.kickoff()


async def example_continuous_monitoring():
    """Ejemplo de monitoreo continuo de nuevas ofertas"""

    print("=" * 60)
    print("MONITOREO CONTINUO DE OFERTAS")
    print("=" * 60)

    # Inicializar
    storage = DataStorage()
    crew_manager = JobSearchCrew()
    crew_manager.initialize()

    # Cargar CV
    try:
        resume_data = storage.load_resume("resume_example.json")
    except FileNotFoundError:
        print("Error: No se encontró CV de ejemplo")
        return

    # Parámetros de búsqueda
    search_params = {
        "keywords": "python developer",
        "location": "remote",
        "job_type": "full-time",
        "limit": 20,
    }

    # Simular monitoreo continuo (3 ciclos)
    cycles = 3

    for cycle in range(1, cycles + 1):
        print(f"\n--- CICLO {cycle} ---")
        print(f"Búsqueda activa: {search_params['keywords']}")

        # Buscar empleos
        crew = crew_manager.create_job_search_crew(
            search_params=search_params, resume_data=resume_data
        )

        # En producción: await crew.kickoff()

        # Simular nuevos jobs encontrados
        new_jobs = cycle * 5
        print(f"✓ {new_jobs} nuevos empleos encontrados")
        print(f"  - {new_jobs * 0.6:.0f} con alto match")
        print(f"  - {new_jobs * 0.4:.0f} con match medio")

        # Simular espera entre ciclos
        if cycle < cycles:
            print(f"\nEsperando 30 segundos antes del siguiente ciclo...")
            # En producción: await asyncio.sleep(30)


async def main():
    """Ejecuta los ejemplos avanzados"""

    print("=== JOBSSEARCHER - EJEMPLOS AVANZADOS ===\n")

    # Ejemplo 1: Workflow completo
    await example_multi_stage_workflow()

    print("\n\n")

    # Ejemplo 2: Desarrollo de carrera
    await example_career_development()

    print("\n\n")

    # Ejemplo 3: Investigación de compañías
    await example_company_research()

    print("\n\n")

    # Ejemplo 4: Análisis por lotes
    await example_batch_analysis()

    print("\n\n")

    # Ejemplo 5: Monitoreo continuo
    await example_continuous_monitoring()


if __name__ == "__main__":
    asyncio.run(main())
