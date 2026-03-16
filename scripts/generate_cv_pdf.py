"""
Generate ATS-friendly CV PDFs from resume.json data.
Produces English and Spanish versions.
"""
import json
from fpdf import FPDF

class CVPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=20)

    def header_section(self, name, title, contact_info):
        """Name + title + contact line."""
        self.set_font("Helvetica", "B", 18)
        self.cell(0, 10, name, new_x="LMARGIN", new_y="NEXT", align="C")
        self.set_font("Helvetica", "", 12)
        self.cell(0, 6, title, new_x="LMARGIN", new_y="NEXT", align="C")
        self.ln(2)
        self.set_font("Helvetica", "", 9)
        self.cell(0, 5, contact_info, new_x="LMARGIN", new_y="NEXT", align="C")
        self.ln(1)
        # Line separator
        self.set_draw_color(100, 100, 100)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def section_title(self, title):
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(30, 80, 160)
        self.cell(0, 8, title.upper(), new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)
        self.ln(1)

    def subsection(self, text, right_text=""):
        self.set_font("Helvetica", "B", 10)
        if right_text:
            w = self.get_string_width(text)
            self.cell(w + 2, 6, text)
            self.set_font("Helvetica", "", 9)
            self.cell(0, 6, right_text, new_x="LMARGIN", new_y="NEXT", align="R")
        else:
            self.cell(0, 6, text, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def bullet(self, text, indent=10):
        self.set_font("Helvetica", "", 9)
        x = self.get_x()
        self.set_x(x + indent)
        self.cell(4, 5, "-")
        self.multi_cell(170 - indent, 5, text)
        self.ln(0.5)

    def sub_bullet(self, text, indent=16):
        self.set_font("Helvetica", "", 9)
        x = self.get_x()
        self.set_x(x + indent)
        self.cell(4, 5, "-")
        self.multi_cell(164 - indent, 5, text)
        self.ln(0.5)

    def skills_line(self, category, skills):
        self.set_font("Helvetica", "B", 9)
        w = self.get_string_width(category + ": ")
        self.set_x(self.get_x() + 10)
        self.cell(w + 2, 5, category + ": ")
        self.set_font("Helvetica", "", 9)
        self.multi_cell(170 - w, 5, skills)
        self.ln(0.5)


def generate_english_cv():
    pdf = CVPDF()
    pdf.add_page()

    pdf.header_section(
        "Alejandro Hernandez Loza",
        "SR. Software Engineer | Full Stack Developer",
        "alejandrohloza@gmail.com | +52 56 4144 6948 | linkedin.com/in/alejandro-hernandez-loza | github.com/alejandro-loza"
    )

    # Summary
    pdf.section_title("Professional Summary")
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(0, 5,
        "Senior Software Engineer with 12+ years of experience designing, developing, and deploying "
        "innovative, scalable solutions using microservices (Spring Boot), cloud platforms (AWS, GCP), "
        "and agile methodologies. Proven track record in migrating legacy systems, building real-time data "
        "pipelines, and developing AI-powered productivity tools. Passionate about clean code principles "
        "and continuous improvement. Open to remote roles."
    )
    pdf.ln(3)

    # Technical Skills
    pdf.section_title("Technical Skills")
    pdf.skills_line("Languages", "Java (Core), Groovy, Kotlin, JavaScript/TypeScript (Node.js), Python, Go, Ruby, Scala")
    pdf.skills_line("Frameworks", "Spring Boot, Micronaut, Grails, Angular, Ember, React, Vue")
    pdf.skills_line("Cloud & DevOps", "AWS (Lambda, S3, RDS, DynamoDB, Aurora, SES, SNS), GCP (Cloud Functions, Cloud SQL, Firestore, Cloud Spanner), Docker, Kubernetes, CI/CD, Jenkins")
    pdf.skills_line("Data & Messaging", "Confluent Kafka, RabbitMQ, SAP CPI, Event-Driven Architecture")
    pdf.skills_line("Databases", "MySQL, PostgreSQL, MongoDB, Redis, Oracle")
    pdf.skills_line("Architecture", "Microservices, Clean Architecture, Hexagonal Architecture, REST/SOAP APIs")
    pdf.skills_line("Testing", "JUnit, Spock, Jest, Nightwatch.js")
    pdf.skills_line("AI & Tools", "Claude Code, GitHub Copilot, Gradle, Maven, Git, Jira, Confluence")
    pdf.ln(3)

    # Work Experience
    pdf.section_title("Work Experience")

    # Thomson Reuters
    pdf.subsection("Sr. Backend Developer | Thomson Reuters", "Mexico City, Mexico | 2024 - 2025")
    pdf.bullet("Led migration of critical legacy applications from Grails to Java/Spring Boot, ensuring functional parity and improved maintainability.")
    pdf.bullet("Developed AI agents using Claude Code for advanced productivity tooling:")
    pdf.sub_bullet("Automated code review, formatting, and quality standards enforcement.")
    pdf.sub_bullet("Built auto-migration tools to accelerate legacy code conversion.")
    pdf.sub_bullet("Created PR management agents for automated code fixes and review comment resolution.")
    pdf.sub_bullet("Implemented E2E test generation from legacy code behavior for migration validation.")
    pdf.ln(2)

    # Globant
    pdf.subsection("Full Stack Developer | Globant", "Mexico City, Mexico | 2022 - 2024")
    pdf.bullet("Taulia Inc.: Maintained and enhanced Spring Boot/Groovy microservices. Integrated SAP CPI for enterprise system communication. Comprehensive testing with Spock and JUnit.")
    pdf.bullet("Flow (WeWork): Designed real-time data pipelines using Confluent Kafka with Event-Driven Architecture. Developed scalable cloud functions in Kotlin. Maintained legacy Go/Python systems.")
    pdf.ln(2)

    # Finerio Connect
    pdf.subsection("Java Developer | Finerio Connect", "Mexico City, Mexico | 2020 - 2021")
    pdf.bullet("Integrated Finerio with Actinver (leading LATAM financial data provider), increasing PFM feature adoption by 20%.")
    pdf.bullet("Built RESTful APIs with Spring Boot, Gradle, and Groovy. Deployed microservices with Docker and Kubernetes.")
    pdf.ln(2)

    # Kubo Financiero
    pdf.subsection("Java Developer | Kubo Financiero", "Mexico City, Mexico | 2018 - 2020")
    pdf.bullet("Led microservices migration from monolith using Micronaut and Spring Boot: 20% scalability increase, 15% latency reduction.")
    pdf.bullet("Built GCP serverless applications (Cloud Functions, Cloud SQL, Firestore). Implemented SOAP & REST APIs.")
    pdf.ln(2)

    # gob.mx
    pdf.subsection("Full Stack Developer | gob.mx (Mexican Government)", "Mexico City, Mexico | 2015 - 2018")
    pdf.bullet("Modernized government IT infrastructure including the nationally impactful gob.mx/ActaNacimiento project.")
    pdf.bullet("Developed DynForms plugin (Node.js) used in Acta Nacimiento and Fuerza Mexico (critical tool during 2017 earthquake).")
    pdf.bullet("Tech stack: Ember, Angular, Node.js, Ruby, PostgreSQL, MongoDB, Akamai, NGINX.")
    pdf.ln(2)

    # Clickonero
    pdf.subsection("Java Developer | Clickonero", "Mexico City, Mexico | 2013 - 2015")
    pdf.bullet("Designed middleware for e-commerce platform communication. Built scalable microservices with Grails and Dropwizard.")
    pdf.bullet("Implemented RabbitMQ for async messaging and Redis for caching. Jenkins for CI/CD automation.")
    pdf.ln(2)

    # Vinco Orbis
    pdf.subsection("Java Developer | Vinco Orbis", "Mexico City, Mexico | 2013")
    pdf.bullet("Club Premier Aeromexico: API integration and frontend enhancement (Backbone.js).")
    pdf.ln(3)

    # Education
    pdf.section_title("Education")
    pdf.subsection("B.S. Computer Systems Engineering | UAEH", "2007 - 2012")
    pdf.bullet("Universidad Autonoma del Estado de Hidalgo")

    pdf.output("data/cv_alejandro_en.pdf")
    print("Generated: data/cv_alejandro_en.pdf")


def generate_spanish_cv():
    pdf = CVPDF()
    pdf.add_page()

    pdf.header_section(
        "Alejandro Hernandez Loza",
        "SR. Full Stack Developer | Ingeniero de Software Senior",
        "alejandrohloza@gmail.com | +52 56 4144 6948 | linkedin.com/in/alejandro-hernandez-loza | github.com/alejandro-loza"
    )

    # Perfil
    pdf.section_title("Perfil Profesional")
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(0, 5,
        "Desarrollador de Software Senior con mas de 12 anos de experiencia disenando, desarrollando e "
        "implementando soluciones innovadoras y escalables utilizando microservicios (Spring Boot), "
        "plataformas en la nube (AWS, GCP) y metodologias agiles (Scrum, TDD). Experiencia comprobada "
        "en migracion de sistemas legados, construccion de pipelines de datos en tiempo real, y desarrollo "
        "de herramientas de productividad con IA. Apasionado por los principios de codigo limpio y la "
        "mejora continua. Abierto a posiciones remotas."
    )
    pdf.ln(3)

    # Habilidades
    pdf.section_title("Habilidades Tecnicas")
    pdf.skills_line("Lenguajes", "Java (Core), Groovy, Kotlin, JavaScript/TypeScript (Node.js), Python, Go, Ruby, Scala")
    pdf.skills_line("Frameworks", "Spring Boot, Micronaut, Grails, Angular, Ember, React, Vue")
    pdf.skills_line("Cloud & DevOps", "AWS (Lambda, S3, RDS, DynamoDB, Aurora, SES, SNS), GCP (Cloud Functions, Cloud SQL, Firestore, Cloud Spanner), Docker, Kubernetes, CI/CD, Jenkins")
    pdf.skills_line("Datos & Mensajeria", "Confluent Kafka, RabbitMQ, SAP CPI, Arquitectura Orientada a Eventos")
    pdf.skills_line("Bases de Datos", "MySQL, PostgreSQL, MongoDB, Redis, Oracle")
    pdf.skills_line("Arquitectura", "Microservicios, Clean Architecture, Hexagonal Architecture, APIs REST/SOAP")
    pdf.skills_line("Testing", "JUnit, Spock, Jest, Nightwatch.js")
    pdf.skills_line("IA & Herramientas", "Claude Code, GitHub Copilot, Gradle, Maven, Git, Jira, Confluence")
    pdf.ln(3)

    # Experiencia
    pdf.section_title("Experiencia Profesional")

    # Thomson Reuters
    pdf.subsection("Sr. Backend Developer | Thomson Reuters", "Ciudad de Mexico | 2024 - 2025")
    pdf.bullet("Lidere la migracion de aplicativos legados criticos de Grails a Java/Spring Boot, garantizando paridad funcional.")
    pdf.bullet("Desarrolle agentes de IA con Claude Code para herramientas de productividad:")
    pdf.sub_bullet("Automatizacion de revision de codigo y estandares de calidad.")
    pdf.sub_bullet("Herramientas de auto-migracion para acelerar conversion de codigo legado.")
    pdf.sub_bullet("Agentes de gestion de PRs para correccion automatica de codigo.")
    pdf.sub_bullet("Generacion automatica de pruebas E2E basadas en comportamiento del codigo legado.")
    pdf.ln(2)

    # Globant
    pdf.subsection("Full Stack Developer | Globant", "Ciudad de Mexico | 2022 - 2024")
    pdf.bullet("Taulia Inc.: Mantenimiento y mejora de microservicios Spring Boot/Groovy. Integracion SAP CPI. Pruebas con Spock y JUnit.")
    pdf.bullet("Flow (WeWork): Pipelines de datos en tiempo real con Confluent Kafka y Arquitectura Orientada a Eventos. Cloud functions escalables en Kotlin. Mantenimiento de sistemas legados Go/Python.")
    pdf.ln(2)

    # Finerio Connect
    pdf.subsection("Java Developer | Finerio Connect", "Ciudad de Mexico | 2020 - 2021")
    pdf.bullet("Integracion exitosa Finerio-Actinver, aumentando adopcion de PFM en un 20%.")
    pdf.bullet("APIs RESTful con Spring Boot, Gradle y Groovy. Despliegue con Docker y Kubernetes.")
    pdf.ln(2)

    # Kubo Financiero
    pdf.subsection("Java Developer | Kubo Financiero", "Ciudad de Mexico | 2018 - 2020")
    pdf.bullet("Migracion de monolito a microservicios con Micronaut y Spring Boot: 20% mejora en escalabilidad, 15% reduccion en latencia.")
    pdf.bullet("Aplicaciones serverless en GCP (Cloud Functions, Cloud SQL, Firestore). APIs SOAP y REST.")
    pdf.ln(2)

    # gob.mx
    pdf.subsection("Full Stack Developer | gob.mx (Gobierno de Mexico)", "Ciudad de Mexico | 2015 - 2018")
    pdf.bullet("Modernizacion de infraestructura TI gubernamental incluyendo gob.mx/ActaNacimiento.")
    pdf.bullet("Plugin DynForms (Node.js) usado en Acta Nacimiento y Fuerza Mexico (herramienta critica durante sismo 2017).")
    pdf.bullet("Stack: Ember, Angular, Node.js, Ruby, PostgreSQL, MongoDB, Akamai, NGINX.")
    pdf.ln(2)

    # Clickonero
    pdf.subsection("Java Developer | Clickonero", "Ciudad de Mexico | 2013 - 2015")
    pdf.bullet("Middleware para plataformas de e-commerce. Microservicios con Grails y Dropwizard.")
    pdf.bullet("RabbitMQ para mensajeria asincrona, Redis para cache. Jenkins para CI/CD.")
    pdf.ln(2)

    # Vinco Orbis
    pdf.subsection("Java Developer | Vinco Orbis", "Ciudad de Mexico | 2013")
    pdf.bullet("Proyecto Club Premier Aeromexico: Integracion de APIs y mejora de frontend (Backbone.js).")
    pdf.ln(3)

    # Educacion
    pdf.section_title("Educacion")
    pdf.subsection("Ing. en Sistemas Computacionales | UAEH", "2007 - 2012")
    pdf.bullet("Universidad Autonoma del Estado de Hidalgo, Pachuca, Hidalgo")

    pdf.output("data/cv_alejandro_es.pdf")
    print("Generated: data/cv_alejandro_es.pdf")


if __name__ == "__main__":
    generate_english_cv()
    generate_spanish_cv()
