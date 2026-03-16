# Contributing to JobSearcher

¡Gracias por tu interés en contribuir a JobSearcher! Este documento te guiará a través del proceso de contribución.

## Código de Conducta

Al participar en este proyecto, te comprometes a mantener un ambiente inclusivo y respetuoso. Trata a todos con respeto y consideración.

## ¿Cómo Contribuir?

### Reportar Bugs

Si encuentras un bug:

1. Busca si ya existe un issue abierto
2. Si no existe, crea un nuevo issue con:
   - Título descriptivo
   - Pasos para reproducir
   - Comportamiento esperado vs. actual
   - Versión de Python y del sistema operativo
   - Logs relevantes (si aplica)

### Sugerir Features

Para sugerir nuevas funcionalidades:

1. Busca issues similares
2. Crea un issue con:
   - Título claro
   - Descripción detallada de la feature
   - Casos de uso
   - Posibles soluciones propuestas
   - Implementaciones de referencia (si existen)

### Enviar Pull Requests

#### 1. Fork y Clona

```bash
git clone https://github.com/tu-usuario/jobsearcher.git
cd jobsearcher
```

#### 2. Crea una Rama

```bash
git checkout -b feature/tu-feature-o-bugfix
```

Nombres de rama recomendados:
- `feature/nombre-feature` para nuevas funcionalidades
- `fix/nombre-bug` para correcciones
- `docs/nombre-documentacion` para documentación

#### 3. Haz tus Cambios

- Sigue los estándares de código del proyecto
- Escribe tests para tu código
- Actualiza la documentación si es necesario
- Asegúrate de que los tests pasen:
  ```bash
  make test
  ```

#### 4. Commite tus Cambios

```bash
git add .
git commit -m "tipo: descripción breve"
```

Tipos de commits:
- `feat`: nueva funcionalidad
- `fix`: corrección de bug
- `docs`: cambios en documentación
- `style`: cambios en formato (sin lógica)
- `refactor`: refactorización
- `test`: agregar tests
- `chore`: tareas de mantenimiento

Ejemplos:
```
feat: agregar soporte para búsqueda por compañía
fix: corregir error en parsing de salary ranges
docs: actualizar README con nuevas instrucciones
```

#### 5. Push y Pull Request

```bash
git push origin feature/tu-feature-o-bugfix
```

Luego crea un Pull Request desde GitHub con:
- Título descriptivo
- Descripción de los cambios
- Referencias a issues relacionados (usando `#numero`)
- Capturas de pantalla si aplica

## Estándares de Código

### Python

- Usa PEP 8 como guía de estilo
- Usa type hints cuando sea apropiado
- Docstrings estilo Google o NumPy
- Máxima longitud de línea: 100 caracteres

```python
def calculate_matching_score(
    resume: Resume,
    job: JobPosting
) -> float:
    """
    Calcula el score de matching entre un CV y un puesto.
    
    Args:
        resume: CV del candidato.
        job: Oferta de empleo.
        
    Returns:
        Score de matching entre 0 y 100.
    """
    pass
```

### Organización de Archivos

```
src/
├── agents/          # Agentes de CrewAI
├── tasks/           # Tareas de CrewAI
├── tools/           # Herramientas externas
├── crew/            # Configuración de crews
├── models/          # Modelos de datos
├── utils/           # Utilidades
└── cli.py           # Interfaz de línea de comandos
```

### Tests

- Escribe tests para nuevas funcionalidades
- Usa `pytest` como framework
- Mock de servicios externos (APIs, DB)
- Tests deben ser independientes y reproducibles

```python
def test_search_jobs():
    """Test de búsqueda de empleos."""
    result = await search_jobs(keywords="python")
    assert len(result) > 0
```

## Proceso de Revisión

1. **Automated Checks**: CI ejecuta tests, linting, etc.
2. **Code Review**: Al menos 1 mantenedor debe aprobar
3. **Tests**: Todos los tests deben pasar
4. **Merge**: Mantenedor hace merge a main

## Estilo de Commit

Usa [Conventional Commits](https://www.conventionalcommits.org/):

```
<tipo>(<alcance>): <descripción>

[opcional cuerpo]

[opcional pie]
```

## Documentación

Si cambias la API o funcionalidades principales:
- Actualiza README.md
- Actualiza docs/ARCHITECTURE.md
- Agrega ejemplos en examples/
- Actualiza type hints

## Development Setup

1. Fork el repositorio
2. Clona tu fork
3. Crea entorno virtual:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # o
   venv\Scripts\activate  # Windows
   ```
4. Instala dependencias:
   ```bash
   pip install -r requirements.txt
   pip install -e .
   ```
5. Copia .env.example a .env y configura tus API keys
6. Ejecuta tests:
   ```bash
   make test
   ```

## Preguntas Frecuentes

**¿Puedo contribuir sin experiencia?**
¡Sí! Empieza con documentación, tests, o issues marcados como "good first issue".

**¿Cuánto tiempo tomará revisar mi PR?**
Generalmente revisamos PRs en 1-3 días. Si no recibes respuesta, haz un ping amable.

**¿Puedo trabajar en cualquier issue?**
Sí, pero issues con etiquetas "help wanted" o "good first issue" son buenos puntos de partida.

**¿Necesito firmar un CLA?**
No, actualmente no requerimos CLA. Tus contribuciones se licencian bajo MIT.

## Contacto

- Issues: https://github.com/tu-usuario/jobsearcher/issues
- Discussions: https://github.com/tu-usuario/jobsearcher/discussions
- Email: contact@jobsearcher.dev

## Licencia

Al contribuir, acuerdas que tus contribuciones se licenciarán bajo la Licencia MIT.

## Reconocimientos

¡Gracias a todos los contribuidores! Tu trabajo hace que JobSearcher sea mejor para todos.
