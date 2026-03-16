from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class JobPosting(BaseModel):
    """Modelo para representar una oferta de empleo"""
    
    job_id: str = Field(..., description="ID único del empleo")
    title: str = Field(..., description="Título del puesto")
    company: str = Field(..., description="Nombre de la empresa")
    location: str = Field(..., description="Ubicación del puesto")
    job_type: str = Field(default="full-time", description="Tipo de trabajo")
    description: str = Field(..., description="Descripción del puesto")
    requirements: List[str] = Field(default_factory=list, description="Requisitos del puesto")
    responsibilities: List[str] = Field(default_factory=list, description="Responsabilidades")
    salary_range: Optional[str] = Field(None, description="Rango salarial")
    url: str = Field(..., description="URL de la oferta")
    posted_date: Optional[datetime] = Field(None, description="Fecha de publicación")
    applications: Optional[int] = Field(None, description="Número de aplicaciones")
    relevance_score: float = Field(default=0.0, description="Score de relevancia (0-10)")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class Resume(BaseModel):
    """Modelo para representar el CV del usuario"""
    
    user_id: str = Field(..., description="ID único del usuario")
    full_name: str = Field(..., description="Nombre completo")
    email: str = Field(..., description="Email de contacto")
    phone: Optional[str] = Field(None, description="Teléfono")
    location: Optional[str] = Field(None, description="Ubicación")
    
    # Información profesional
    professional_title: str = Field(..., description="Título profesional")
    summary: str = Field(..., description="Resumen profesional")
    
    # Experiencia
    experience_summary: str = Field(..., description="Resumen de experiencia")
    years_of_experience: int = Field(default=0, description="Años de experiencia")
    
    # Habilidades
    technical_skills: List[str] = Field(default_factory=list, description="Habilidades técnicas")
    soft_skills: List[str] = Field(default_factory=list, description="Habilidades blandas")
    
    # Educación
    education: str = Field(..., description="Educación")
    
    # Otros
    certifications: List[str] = Field(default_factory=list, description="Certificaciones")
    achievements: List[str] = Field(default_factory=list, description="Logros destacados")
    linkedin_url: Optional[str] = Field(None, description="URL de LinkedIn")
    github_url: Optional[str] = Field(None, description="URL de GitHub")
    portfolio_url: Optional[str] = Field(None, description="URL de portafolio")


class MatchingResult(BaseModel):
    """Modelo para representar el resultado de matching"""
    
    job_id: str = Field(..., description="ID del puesto")
    job_title: str = Field(..., description="Título del puesto")
    company: str = Field(..., description="Nombre de la empresa")
    matching_score: float = Field(..., description="Score de matching (0-100)")
    
    # Detalles del matching
    matched_skills: List[str] = Field(default_factory=list, description="Habilidades que coinciden")
    missing_skills: List[str] = Field(default_factory=list, description="Habilidades faltantes")
    
    # Análisis
    experience_match: str = Field(..., description="Análisis de experiencia")
    strengths: List[str] = Field(default_factory=list, description="Fortalezas del candidato")
    improvements: List[str] = Field(default_factory=list, description="Áreas de mejora")
    
    # Recomendación
    recommendation: str = Field(..., description="Recomendación: approve, review, reject")
    justification: str = Field(..., description="Justificación de la recomendación")


class ApplicationStrategy(BaseModel):
    """Modelo para representar una estrategia de postulación"""
    
    job_id: str = Field(..., description="ID del puesto")
    company_analysis: str = Field(..., description="Análisis de la empresa")
    
    # CV
    cv_recommendations: List[str] = Field(default_factory=list, description="Recomendaciones para el CV")
    keywords_to_include: List[str] = Field(default_factory=list, description="Keywords importantes")
    
    # Cover Letter
    cover_letter: str = Field(..., description="Cover Letter personalizada")
    
    # Networking
    connection_message: str = Field(..., description="Mensaje para conectar con reclutadores")
    
    # Timing y enfoque
    timing: str = Field(..., description="Cuándo aplicar")
    positioning: str = Field(..., description="Cómo posicionarse")
    
    # Checklist
    pre_application_checklist: List[str] = Field(default_factory=list, description="Checklist antes de aplicar")
    post_application_plan: str = Field(..., description="Plan después de aplicar")


class InterviewPrep(BaseModel):
    """Modelo para representar la preparación de entrevista"""
    
    job_id: str = Field(..., description="ID del puesto")
    job_title: str = Field(..., description="Título del puesto")
    company: str = Field(..., description="Nombre de la empresa")
    
    # Preguntas
    technical_questions: List[Dict[str, str]] = Field(default_factory=list, description="Preguntas técnicas")
    behavioral_questions: List[Dict[str, str]] = Field(default_factory=list, description="Preguntas comportamentales")
    questions_to_ask: List[str] = Field(default_factory=list, description="Preguntas para hacer al entrevistador")
    
    # Prep adicional
    company_research: str = Field(..., description="Investigación de la empresa")
    interview_format: str = Field(..., description="Formato de la entrevista")
    success_tips: List[str] = Field(default_factory=list, description="Tips de éxito")
    
    # Preparación específica
    code_exercises: List[Dict[str, Any]] = Field(default_factory=list, description="Ejercicios de código")
    star_stories: List[Dict[str, str]] = Field(default_factory=list, description="Historias STAR")


class JobSearchResult(BaseModel):
    """Modelo para representar el resultado de una búsqueda"""
    
    search_params: Dict[str, Any] = Field(..., description="Parámetros de búsqueda")
    total_results: int = Field(..., description="Total de resultados")
    jobs: List[JobPosting] = Field(default_factory=list, description="Lista de empleos encontrados")
    
    # Análisis
    summary: str = Field(..., description="Resumen de la búsqueda")
    top_recommendations: List[JobPosting] = Field(default_factory=list, description="Empleos recomendados")
    
    # Metadata
    search_date: datetime = Field(default_factory=datetime.now, description="Fecha de búsqueda")
