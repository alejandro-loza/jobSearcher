import pytest
import sys
from pathlib import Path

# Agregar el directorio src al path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestLinkedInMCPTool:
    """Tests para LinkedInMCPTool"""
    
    @pytest.mark.asyncio
    async def test_search_jobs_disabled(self):
        """Test que busca empleos con MCP deshabilitado"""
        from src.tools.linkedin_mcp import LinkedInMCPTool
        
        tool = LinkedInMCPTool()
        tool.enabled = False
        
        result = await tool.search_jobs(
            keywords="python",
            location="remote",
            limit=5
        )
        
        assert result == []
    
    @pytest.mark.asyncio
    async def test_get_job_details_disabled(self):
        """Test que obtiene detalles de job con MCP deshabilitado"""
        from src.tools.linkedin_mcp import LinkedInMCPTool
        
        tool = LinkedInMCPTool()
        tool.enabled = False
        
        result = await tool.get_job_details("test_job_id")
        
        assert "error" in result or result == {}


class TestDataStorage:
    """Tests para DataStorage"""
    
    def test_save_and_load_resume(self, tmp_path):
        """Test guardar y cargar CV"""
        from src.utils.storage import DataStorage
        
        storage = DataStorage(data_dir=str(tmp_path))
        
        resume_data = {
            "user_id": "test_user",
            "full_name": "Test User",
            "email": "test@email.com",
            "technical_skills": ["Python", "Django"]
        }
        
        # Guardar
        filepath = storage.save_resume(resume_data, "test_resume.json")
        assert Path(filepath).exists()
        
        # Cargar
        loaded = storage.load_resume("test_resume.json")
        assert loaded["user_id"] == "test_user"
        assert loaded["technical_skills"] == ["Python", "Django"]
    
    def test_save_and_load_jobs(self, tmp_path):
        """Test guardar y cargar empleos"""
        from src.utils.storage import DataStorage
        
        storage = DataStorage(data_dir=str(tmp_path))
        
        jobs = [
            {
                "job_id": "job_1",
                "title": "Python Developer",
                "company": "Tech Corp",
                "location": "Remote"
            },
            {
                "job_id": "job_2",
                "title": "Senior Engineer",
                "company": "Startup Inc",
                "location": "Madrid"
            }
        ]
        
        # Guardar
        filepath = storage.save_jobs(jobs, "test_jobs.json")
        assert Path(filepath).exists()
        
        # Cargar
        loaded = storage.load_jobs("test_jobs.json")
        assert len(loaded) == 2
        assert loaded[0]["title"] == "Python Developer"
    
    def test_load_nonexistent_resume(self, tmp_path):
        """Test cargar CV que no existe"""
        from src.utils.storage import DataStorage
        import pytest
        
        storage = DataStorage(data_dir=str(tmp_path))
        
        with pytest.raises(FileNotFoundError):
            storage.load_resume("nonexistent.json")
    
    def test_load_empty_jobs(self, tmp_path):
        """Test cargar empleos cuando no hay archivo"""
        from src.utils.storage import DataStorage
        
        storage = DataStorage(data_dir=str(tmp_path))
        
        loaded = storage.load_jobs("nonexistent.json")
        assert loaded == []


class TestReportGenerator:
    """Tests para ReportGenerator"""
    
    def test_generate_job_search_report(self):
        """Test generar reporte de búsqueda"""
        from src.utils.storage import ReportGenerator
        
        search_params = {
            "keywords": "python",
            "location": "remote",
            "job_type": "full-time"
        }
        
        jobs = [
            {
                "job_id": "job_1",
                "title": "Python Developer",
                "company": "Tech Corp"
            }
        ]
        
        matching_results = [
            {
                "job_title": "Python Developer",
                "company": "Tech Corp",
                "matching_score": 85.0,
                "recommendation": "approve"
            }
        ]
        
        report = ReportGenerator.generate_job_search_report(
            search_params=search_params,
            jobs=jobs,
            matching_results=matching_results
        )
        
        assert "REPORTE DE BÚSQUEDA DE EMPLEO" in report
        assert "python" in report
        assert "remote" in report
        assert "TOP MATCHES" in report
        assert "85.0%" in report
    
    def test_generate_matching_report(self):
        """Test generar reporte de matching"""
        from src.utils.storage import ReportGenerator
        
        matching_result = {
            "job_title": "Python Developer",
            "company": "Tech Corp",
            "matching_score": 85.0,
            "recommendation": "approve",
            "matched_skills": ["Python", "Django"],
            "missing_skills": ["React"],
            "strengths": ["Good experience"],
            "improvements": ["Learn React"],
            "justification": "Good match overall"
        }
        
        report = ReportGenerator.generate_matching_report(matching_result)
        
        assert "REPORTE DE MATCHING" in report
        assert "85.0%" in report
        assert "APPROVE" in report
        assert "HABILIDADES QUE COINCIDEN" in report
        assert "HABILIDADES FALTANTES" in report
        assert "Python" in report
        assert "React" in report


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
