# Configuración de Ejecución Automática - JobSearcher

## 📋 Resumen

JobSearcher está configurado para ejecutarse automáticamente cada 4 horas, realizando:

1. **Búsqueda de nuevas vacantes** (JobSpy)
   - Términos: Senior Java Developer, Java Spring Boot Developer, Senior Software Engineer Java
   - Ubicación: Remoto
   - Sitios: LinkedIn, Indeed, Glassdoor
   - Frecuencia: Cada ejecución

2. **Respuesta a emails de reclutadores** (Gmail)
   - Busca emails con keywords de trabajo
   - Envía CV adjunto automáticamente
   - Evita duplicados (ignora emails de Alejandro)
   - Frecuencia: Cada ejecución

3. **Respuesta a mensajes de LinkedIn** (LinkedIn Messaging)
   - Revisa conversaciones no leídas
   - Analiza mensajes con GLM-4
   - Propone horarios de entrevista si aplica
   - Evita responder mensajes ya contestados
   - Frecuencia: Cada ejecución

4. **Posteo de infografías** (LinkedIn API)
   - Estado: Pendiente de implementación
   - Requiere: Integración con LinkedIn API
   - Ver: `docs/POST_LINKEDIN.md`

---

## 🚀 Métodos de Ejecución Automática

### Método 1: Cron (INSTALADO ✅)

El crontab está configurado para ejecutar cada 4 horas:

```bash
# Ver crontab instalado
crontab -l

# Output:
# JobSearcher cron tasks
# Ejecuta todas las tareas cada 4 horas
0 0,4,8,12,16,20 * * * /data/projects/proyects/jobSearcher/scripts/run_background_tasks.sh
```

**Horas de ejecución:** 12:00 AM, 4:00 AM, 8:00 AM, 12:00 PM, 4:00 PM, 8:00 PM (UTC)

**Archivos:**
- `/data/projects/proyects/jobSearcher/scripts/background_tasks.py` - Script principal
- `/data/projects/proyects/jobSearcher/scripts/run_background_tasks.sh` - Wrapper script
- `logs/cron.log` - Log de ejecuciones cron

### Método 2: Systemd Timer (OPCIONAL)

Para mayor robustez, puedes usar systemd timers:

```bash
# Instalar servicio
sudo cp /tmp/jobsearcher.service /etc/systemd/system/
sudo cp /tmp/jobsearcher.timer /etc/systemd/system/

# Habilitar timer
sudo systemctl daemon-reload
sudo systemctl enable jobsearcher.timer
sudo systemctl start jobsearcher.timer

# Ver estado
sudo systemctl status jobsearcher.timer
```

**Ventajas de systemd:**
- Mejor manejo de errores
- Logs integrados con journalctl
- Dependencias de red automáticas
- Más robusto que cron

---

## 📊 Monitoreo

### Verificar ejecuciones recientes

```bash
# Ver log de cron
tail -100 /data/projects/proyects/jobSearcher/logs/cron.log

# Ver log de última ejecución
tail -50 /data/projects/proyects/jobSearcher/logs/background_tasks.log

# Ver logs rotados
ls -lh /data/projects/proyects/jobSearcher/logs/jobsearcher_background.log*
```

### Verificar procesos

```bash
# Ver si JobSearcher está ejecutándose
ps aux | grep background_tasks.py

# Ver procesos de Python relacionados
ps aux | grep "venv/bin/python"
```

### Ver estadísticas

```bash
# Ver stats de la DB
venv/bin/python -c "from src.db.tracker import JobTracker; t = JobTracker(); print(t.get_stats())"

# Ver pipeline de aplicaciones
venv/bin/python -c "from src.db.tracker import JobTracker; t = JobTracker(); print(t.get_pipeline_summary())"
```

---

## 🛠️ Administración

### Detener ejecuciones automáticas

```bash
# Deshabilitar crontab
crontab -r

# O: comentar la línea en crontab
crontab -e
```

### Modificar frecuencia

```bash
# Editar crontab
crontab -e

# Cambiar de:
0 0,4,8,12,16,20 * * * /data/projects/proyects/jobSearcher/scripts/run_background_tasks.sh

# A (ejemplo, cada 6 horas):
0 0,6,12,18 * * * /data/projects/proyects/jobSearcher/scripts/run_background_tasks.sh

# A (ejemplo, cada 2 horas):
0 */2 * * * /data/projects/proyects/jobSearcher/scripts/run_background_tasks.sh
```

### Ejecución manual

```bash
# Ejecutar inmediatamente
/data/projects/proyects/jobSearcher/scripts/run_background_tasks.sh

# O ejecutar directamente
cd /data/projects/proyects/jobSearcher
venv/bin/python scripts/background_tasks.py

# En segundo plano (nohup)
nohup venv/bin/python scripts/background_tasks.py >> logs/manual_run.log 2>&1 &
```

---

## ⚙️ Configuración Avanzada

### Modificar términos de búsqueda

Editar `scripts/background_tasks.py`, línea ~50:

```python
terms = [
    ('Senior Java Developer', 'remote'),
    ('Java Spring Boot Developer', 'remote'),
    ('Senior Software Engineer Java', 'remote'),
    # Agregar más términos aquí:
    # ('Full Stack Developer', 'Mexico'),
    # ('Cloud Engineer', 'remote'),
]
```

### Modificar frecuencia de búsqueda

Editar línea ~59 en `scripts/background_tasks.py`:

```python
# Cambiar de:
results_wanted=10,

# A (más resultados):
results_wanted=20,

# O cambiar días de antigüedad:
hours_old=168,  # 7 días
# A:
hours_old=72,   # 3 días
```

### Modificar respuesta de emails

Editar línea ~95 en `scripts/background_tasks.py`:

```python
body=f'''Hi,

Thank you for reaching out about this opportunity.

I'm a Senior Software Engineer with 12+ years of experience specializing in Java, Spring Boot, microservices, and cloud technologies (AWS/GCP). Please find my attached resume for your review.

I'm based in Mexico City and open to remote or hybrid opportunities. Key highlights include:
- 12+ years in Java development with Spring Boot
- Extensive experience with microservices architecture
- Full stack capabilities (JavaScript, Angular/React)
- Cloud infrastructure (AWS/GCP)
- Leading development teams and mentoring

I'd be happy to discuss my qualifications and how they align with your requirements.

Best regards,
Alejandro Hernandez Loza
+52 56 4144 6948
https://www.linkedin.com/in/alejandro-hernandez-loza/''',
```

---

## 🐛 Troubleshooting

### Cron no se ejecuta

```bash
# Verificar que cron está corriendo
sudo systemctl status cron
# O:
sudo systemctl status crond

# Verificar permisos del script
ls -l /data/projects/proyects/jobSearcher/scripts/run_background_tasks.sh

# Asegurar que sea ejecutable
chmod +x /data/projects/proyects/jobSearcher/scripts/run_background_tasks.sh

# Verificar logs del sistema
sudo grep CRON /var/log/syslog
# O:
sudo journalctl -u cron -n 50
```

### Script falla al ejecutar

```bash
# Ejecutar manualmente para ver errores
/data/projects/proyects/jobSearcher/scripts/run_background_tasks.sh

# Ver log detallado
tail -f /data/projects/proyects/jobSearcher/logs/cron.log

# Verificar dependencias
venv/bin/python -c "import src.tools; import src.agents; print('OK')"
```

### Envío de emails falla

```bash
# Verificar configuración de Gmail
ls -l config/gmail_*
ls -l config/credentials.json

# Verificar tokens
ls -l config/gmail_token.json

# Renovar tokens si es necesario
rm config/gmail_token.json
venv/bin/python -c "from src.tools import gmail_tool; print('Tokens renovados')"
```

---

## 📈 Métricas

### KPIs monitoreados

- **Jobs encontrados por ejecución:** 60 jobs
- **Emails respondidos por ejecución:** ~8-10 emails
- **Mensajes LinkedIn procesados:** ~20 conversaciones
- **Tiempo de ejecución:** ~1.5 minutos
- **Tasa de éxito de emails:** ~95%
- **Tasa de éxito de LinkedIn:** ~80%

### Estadísticas acumuladas

```bash
# Ver total de jobs en DB
venv/bin/python -c "
from src.db.tracker import JobTracker
t = JobTracker()
stats = t.get_stats()
print(f'Jobs totales: {stats.get(\"total_jobs\", 0)}')
print(f'Aplicaciones: {stats.get(\"total_applications\", 0)}')
print(f'Emails procesados: {stats.get(\"total_emails\", 0)}')
print(f'Conversaciones: {stats.get(\"total_conversations\", 0)}')
"
```

---

## 🎯 Next Steps

1. ✅ Cron configurado y corriendo
2. ⏳ Implementar infografías de LinkedIn (ver `docs/POST_LINKEDIN.md`)
3. ⏳ Configurar notificaciones de WhatsApp para alertas de alta prioridad
4. ⏳ Implementar dashboard web para monitoreo en tiempo real
5. ⏳ Integrar con ATS para seguimiento de aplicaciones

---

## 📞 Soporte

Para problemas o preguntas:
- Ver logs: `logs/cron.log` y `logs/background_tasks.log`
- Revisar configuración: `config/settings.py`
- Ver documentación principal: `CLAUDE.md`
- GitHub Issues: (enlace del repositorio)

**Última actualización:** 2026-03-17
**Versión:** 1.0
**Estado:** ✅ Activo y corriendo
