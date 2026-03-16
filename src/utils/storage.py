import json
import os
from typing import Dict, Any, List
from pathlib import Path
from loguru import logger


class DataStorage:
    """Clase para manejo de almacenamiento de datos"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def save_resume(self, resume_data: Dict[str, Any], filename: str = "resume.json") -> str:
        """Guarda el CV del usuario en un archivo JSON"""
        filepath = self.data_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(resume_data, f, indent=2, ensure_ascii=False)
        logger.info(f"CV guardado en {filepath}")
        return str(filepath)
    
    def load_resume(self, filename: str = "resume.json") -> Dict[str, Any]:
        """Carga el CV del usuario desde un archivo JSON"""
        filepath = self.data_dir / filename
        if not filepath.exists():
            raise FileNotFoundError(f"No se encontró el CV en {filepath}")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"CV cargado desde {filepath}")
        return data
    
    def save_jobs(self, jobs: List[Dict[str, Any]], filename: str = "jobs.json") -> str:
        """Guarda los empleos encontrados en un archivo JSON"""
        filepath = self.data_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(jobs, f, indent=2, ensure_ascii=False, default=str)
        logger.info(f"{len(jobs)} empleos guardados en {filepath}")
        return str(filepath)
    
    def load_jobs(self, filename: str = "jobs.json") -> List[Dict[str, Any]]:
        """Carga los empleos desde un archivo JSON"""
        filepath = self.data_dir / filename
        if not filepath.exists():
            return []
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"{len(data)} empleos cargados desde {filepath}")
        return data
    
    def save_matching_results(
        self, 
        results: List[Dict[str, Any]], 
        filename: str = "matching_results.json"
    ) -> str:
        """Guarda los resultados de matching"""
        filepath = self.data_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        logger.info(f"{len(results)} resultados de matching guardados en {filepath}")
        return str(filepath)
    
    def save_application_strategy(
        self, 
        strategy: Dict[str, Any], 
        job_id: str
    ) -> str:
        """Guarda la estrategia de aplicación para un puesto específico"""
        strategies_dir = self.data_dir / "strategies"
        strategies_dir.mkdir(exist_ok=True)
        
        filepath = strategies_dir / f"strategy_{job_id}.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(strategy, f, indent=2, ensure_ascii=False)
        logger.info(f"Estrategia guardada en {filepath}")
        return str(filepath)
    
    def save_interview_prep(
        self, 
        prep: Dict[str, Any], 
        job_id: str
    ) -> str:
        """Guarda la preparación de entrevista para un puesto específico"""
        preps_dir = self.data_dir / "interview_preps"
        preps_dir.mkdir(exist_ok=True)
        
        filepath = preps_dir / f"prep_{job_id}.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(prep, f, indent=2, ensure_ascii=False)
        logger.info(f"Preparación de entrevista guardada en {filepath}")
        return str(filepath)


class ReportGenerator:
    """Clase para generar reportes"""
    
    @staticmethod
    def generate_job_search_report(
        search_params: Dict[str, Any],
        jobs: List[Dict[str, Any]],
        matching_results: List[Dict[str, Any]]
    ) -> str:
        """Genera un reporte en texto de la búsqueda de empleo"""
        report = []
        report.append("=" * 60)
        report.append("REPORTE DE BÚSQUEDA DE EMPLEO")
        report.append("=" * 60)
        report.append(f"\nFecha: {search_params.get('date', 'N/A')}")
        report.append(f"Keywords: {search_params.get('keywords', 'N/A')}")
        report.append(f"Ubicación: {search_params.get('location', 'N/A')}")
        report.append(f"Tipo de trabajo: {search_params.get('job_type', 'N/A')}")
        report.append(f"\nTotal de resultados: {len(jobs)}")
        
        if matching_results:
            report.append("\n" + "-" * 60)
            report.append("TOP MATCHES")
            report.append("-" * 60)
            
            # Ordenar por score descendente
            sorted_results = sorted(
                matching_results, 
                key=lambda x: x.get('matching_score', 0), 
                reverse=True
            )[:5]
            
            for i, result in enumerate(sorted_results, 1):
                report.append(f"\n{i}. {result.get('job_title', 'N/A')} en {result.get('company', 'N/A')}")
                report.append(f"   Score: {result.get('matching_score', 0):.1f}%")
                report.append(f"   Recomendación: {result.get('recommendation', 'N/A')}")
        
        report.append("\n" + "=" * 60)
        
        return "\n".join(report)
    
    @staticmethod
    def generate_matching_report(matching_result: Dict[str, Any]) -> str:
        """Genera un reporte detallado de matching"""
        report = []
        report.append("=" * 60)
        report.append("REPORTE DE MATCHING")
        report.append("=" * 60)
        report.append(f"\nPuesto: {matching_result.get('job_title', 'N/A')}")
        report.append(f"Empresa: {matching_result.get('company', 'N/A')}")
        report.append(f"Score de Matching: {matching_result.get('matching_score', 0):.1f}%")
        report.append(f"Recomendación: {matching_result.get('recommendation', 'N/A').upper()}")
        
        report.append("\n" + "-" * 60)
        report.append("HABILIDADES QUE COINCIDEN")
        report.append("-" * 60)
        for skill in matching_result.get('matched_skills', []):
            report.append(f"✓ {skill}")
        
        report.append("\n" + "-" * 60)
        report.append("HABILIDADES FALTANTES")
        report.append("-" * 60)
        for skill in matching_result.get('missing_skills', []):
            report.append(f"✗ {skill}")
        
        report.append("\n" + "-" * 60)
        report.append("FORTALEZAS")
        report.append("-" * 60)
        for strength in matching_result.get('strengths', []):
            report.append(f"• {strength}")
        
        report.append("\n" + "-" * 60)
        report.append("ÁREAS DE MEJORA")
        report.append("-" * 60)
        for improvement in matching_result.get('improvements', []):
            report.append(f"• {improvement}")
        
        report.append("\n" + "-" * 60)
        report.append("JUSTIFICACIÓN")
        report.append("-" * 60)
        report.append(matching_result.get('justification', 'N/A'))
        
        report.append("\n" + "=" * 60)
        
        return "\n".join(report)
