import argparse
import sys
from pathlib import Path
from loguru import logger
from config import settings
from src.crew import JobSearchCrew
from src.utils.storage import DataStorage, ReportGenerator


def setup_logging():
    """Configura el logging"""
    logger.remove()
    logger.add(
        sys.stdout,
        level=settings.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>"
    )
    logger.add(
        f"{settings.log_dir}/jobsearcher.log",
        rotation="10 MB",
        level=settings.log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
    )


def cmd_search(args):
    """Comando para buscar empleos"""
    logger.info("Iniciando búsqueda de empleos...")
    
    # Parámetros de búsqueda
    search_params = {
        "keywords": args.keywords,
        "location": args.location,
        "job_type": args.job_type,
        "limit": args.limit
    }
    
    # Cargar CV si existe
    storage = DataStorage()
    try:
        resume_data = storage.load_resume()
        logger.info("CV cargado exitosamente")
    except FileNotFoundError:
        logger.warning("No se encontró CV. Por favor, carga tu CV primero.")
        logger.info("Usa: python -m src.main upload-resume")
        return
    
    # Crear crew y ejecutar
    crew_manager = JobSearchCrew()
    crew_manager.initialize()
    
    crew = crew_manager.create_job_search_crew(
        search_params=search_params,
        resume_data=resume_data
    )
    
    logger.info("Ejecutando búsqueda...")
    result = crew.kickoff()
    
    # Guardar resultados
    jobs = []  # Sería extraído del resultado
    storage.save_jobs(jobs)
    
    print("\n" + "="*60)
    print("BÚSQUEDA COMPLETADA")
    print("="*60)
    print(result)
    
    # Generar reporte
    report = ReportGenerator.generate_job_search_report(
        search_params=search_params,
        jobs=jobs,
        matching_results=[]
    )
    print(report)


def cmd_full_analysis(args):
    """Comando para análisis completo"""
    logger.info("Iniciando análisis completo...")
    
    # Cargar datos
    storage = DataStorage()
    try:
        resume_data = storage.load_resume()
        jobs = storage.load_jobs()
    except FileNotFoundError as e:
        logger.error(f"No se encontraron datos: {e}")
        return
    
    if not jobs:
        logger.warning("No hay empleos guardados. Primero ejecuta una búsqueda.")
        return
    
    # Seleccionar el primer job para análisis
    job_details = jobs[0]
    
    # Crear crew y ejecutar
    crew_manager = JobSearchCrew()
    crew_manager.initialize()
    
    crew = crew_manager.create_full_analysis_crew(
        search_params={},
        resume_data=resume_data,
        job_details=job_details,
        matching_score=70
    )
    
    logger.info("Ejecutando análisis completo...")
    result = crew.kickoff()
    
    print("\n" + "="*60)
    print("ANÁLISIS COMPLETO")
    print("="*60)
    print(result)


def cmd_match(args):
    """Comando para hacer matching entre CV y un puesto"""
    logger.info("Iniciando análisis de matching...")
    
    # Cargar datos
    storage = DataStorage()
    try:
        resume_data = storage.load_resume()
        jobs = storage.load_jobs()
    except FileNotFoundError as e:
        logger.error(f"No se encontraron datos: {e}")
        return
    
    if not jobs:
        logger.warning("No hay empleos guardados. Primero ejecuta una búsqueda.")
        return
    
    # Analizar matching para cada puesto
    crew_manager = JobSearchCrew()
    crew_manager.initialize()
    
    matching_results = []
    
    for job in jobs[:args.limit]:
        # Aquí se ejecutaría el matching
        # matching_result = ...
        # matching_results.append(matching_result)
        logger.info(f"Analizando: {job.get('title', 'N/A')}")
    
    # Generar reporte
    if matching_results:
        report = ReportGenerator.generate_job_search_report(
            search_params={},
            jobs=jobs,
            matching_results=matching_results
        )
        print(report)


def cmd_strategy(args):
    """Comando para generar estrategia de aplicación"""
    logger.info("Generando estrategia de aplicación...")
    
    # Cargar datos
    storage = DataStorage()
    try:
        resume_data = storage.load_resume()
        jobs = storage.load_jobs()
    except FileNotFoundError as e:
        logger.error(f"No se encontraron datos: {e}")
        return
    
    if not jobs:
        logger.warning("No hay empleos guardados. Primero ejecuta una búsqueda.")
        return
    
    # Seleccionar el puesto especificado o el primero
    job_id = args.job_id if args.job_id else jobs[0].get('job_id')
    
    # Crear crew y ejecutar
    crew_manager = JobSearchCrew()
    crew_manager.initialize()
    
    crew = crew_manager.create_full_analysis_crew(
        search_params={},
        resume_data=resume_data,
        job_details=jobs[0],
        matching_score=75
    )
    
    logger.info("Generando estrategia...")
    result = crew.kickoff()
    
    print("\n" + "="*60)
    print("ESTRATEGIA DE APLICACIÓN")
    print("="*60)
    print(result)


def cmd_interview_prep(args):
    """Comando para preparación de entrevista"""
    logger.info("Generando preparación de entrevista...")
    
    # Cargar datos
    storage = DataStorage()
    try:
        resume_data = storage.load_resume()
        jobs = storage.load_jobs()
    except FileNotFoundError as e:
        logger.error(f"No se encontraron datos: {e}")
        return
    
    if not jobs:
        logger.warning("No hay empleos guardados. Primero ejecuta una búsqueda.")
        return
    
    # Seleccionar el puesto
    job_id = args.job_id if args.job_id else jobs[0].get('job_id')
    
    # Crear crew y ejecutar
    crew_manager = JobSearchCrew()
    crew_manager.initialize()
    
    crew = crew_manager.create_interview_prep_crew(
        job_details=jobs[0],
        user_skills=resume_data.get('technical_skills', []),
        user_experience=resume_data.get('experience_summary', '')
    )
    
    logger.info("Generando preparación...")
    result = crew.kickoff()
    
    print("\n" + "="*60)
    print("PREPARACIÓN DE ENTREVISTA")
    print("="*60)
    print(result)


def main():
    """Función principal"""
    parser = argparse.ArgumentParser(
        description="JobSearcher - Sistema de búsqueda de empleo con IA",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Comandos disponibles")
    
    # Comando search
    search_parser = subparsers.add_parser("search", help="Buscar empleos en LinkedIn")
    search_parser.add_argument("--keywords", "-k", required=True, help="Palabras clave de búsqueda")
    search_parser.add_argument("--location", "-l", default="remote", help="Ubicación (default: remote)")
    search_parser.add_argument("--job-type", "-t", default="full-time", help="Tipo de trabajo")
    search_parser.add_argument("--limit", "-n", type=int, default=10, help="Número de resultados")
    
    # Comando analyze
    analyze_parser = subparsers.add_parser("analyze", help="Análisis completo de un puesto")
    analyze_parser.add_argument("--job-id", "-j", help="ID del puesto a analizar")
    
    # Comando match
    match_parser = subparsers.add_parser("match", help="Analizar matching entre CV y empleos")
    match_parser.add_argument("--limit", "-n", type=int, default=5, help="Número de empleos a analizar")
    
    # Comando strategy
    strategy_parser = subparsers.add_parser("strategy", help="Generar estrategia de aplicación")
    strategy_parser.add_argument("--job-id", "-j", help="ID del puesto")
    
    # Comando interview
    interview_parser = subparsers.add_parser("interview", help="Preparación para entrevista")
    interview_parser.add_argument("--job-id", "-j", help="ID del puesto")
    
    # Comando interactive
    subparsers.add_parser("interactive", help="Modo interactivo")
    
    args = parser.parse_args()
    
    # Configurar logging
    setup_logging()
    
    # Ejecutar comando
    if args.command == "search":
        cmd_search(args)
    elif args.command == "analyze":
        cmd_full_analysis(args)
    elif args.command == "match":
        cmd_match(args)
    elif args.command == "strategy":
        cmd_strategy(args)
    elif args.command == "interview":
        cmd_interview_prep(args)
    elif args.command == "interactive":
        logger.info("Modo interactivo (próximamente)")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
