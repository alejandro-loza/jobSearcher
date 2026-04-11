# 🎧 AUDIBLE CHEATSHEET - FINAL

**Objetivo**: Referencia rápida para entrevistas de Audible (Amazon)
**Fecha**: 10 de abril 2026
**Duración por sesión**: 30 minutos (coding + behavioral)

---

## 📅 Schedule

| Hora (CDMX) | Entrevistador | Tema | Principios Audible |
|---------------|--------------|-------|-------------------|
| 9:30-9:45am | David Han | Introducción/bienvenida | - |
| 9:45-10:00am | Break | - | - |
| 10:00-11:00am | Matt Love & Kshitij Shah | Coding: DSA + Articulate The Possible | Articulate The Possible, Move Fast To Make It Real |
| 11:00-12:00pm | Alfonso Lopez Lopez | Coding: Problem Solving + Be Customer Obsessed | Be Customer Obsessed |
| 12:00-1:00pm | Chaitra Ramdas | System Design + Activate Caring + Study & Draw | Activate Caring, Study and Draw Inspiration From Culture and Technology |
| 1:00-2:00pm | Poorva Karunakaran | Coding: Logical & Maintainable + Imagine and Invent | Imagine and Invent Before They Ask |

---

## 🎯 Audible Leadership Principles / Principios de Liderazgo

### 1. **Activate Caring** / **Activa el Cuidado**
> *"People will invariably forget things you say, but they will rarely forget how you make them feel."*
> *"La gente siempre olvidará lo que dices, pero raramente olvidará cómo les hiciste sentir."*

**Español**: Trabaja humano a humano, no egos, altos estándares con amabilidad
**English**: Work human-to-human, no egos, high standards with kindness

---

### 2. **Articulate The Possible & Move Fast To Make It Real** / **Articula Lo Posible y Muévete Rápido Para Hacerlo Real**
> *"The best visions of possible are intellectual hypotheses made even better when data and research inform them."*
> *"Las mejores visiones de lo posible son hipótesis intelectuales que se vuelven mejores cuando datos e investigación las informan."*

**Español**: Cristaliza la visión, muévete con misión y propósito
**English**: Crystallize the vision, move with mission and purpose

---

### 3. **Imagine and Invent Before They Ask** / **Imagina e Inventa Antes de Que Te Pidan**
> *"We embrace ambiguity and tolerate and demystify complexity."*
> *"Abrazamos la ambigüedad y toleramos y desmitificamos la complejidad."*

**Español**: Abraza ambigüedad, simplifica antes de que te lo pidan
**English**: Embrace ambiguity, simplify before they ask

---

### 4. **Be Customer Obsessed** / **Está Obsesionado con el Cliente**
> *"That our customers depend on us is an honor."*
> *"Que nuestros clientes dependan de nosotros es un honor."*

**Español**: Escucha activa al cliente, su dependencia en nosotros es un honor
**English**: Actively listen to customer, their dependency on us is an honor

---

### 5. **Study and Draw Inspiration From Culture and Technology** / **Estudia y Obtén Inspiración de la Cultura y la Tecnología**
> *"Leaders who stand out operate at the cutting edge of arts and sciences."*
> *"Los líderes que destacan operan en la vanguardia de las artes y las ciencias."*

**Español**: Opera en la vanguardia de artes y ciencias
**English**: Operate at the cutting edge of arts and sciences

---

## 📋 STAR Stories Framework / Marco STAR

### English Structure
- **S**ituation — Set context
- **T**ask — Your responsibility
- **A**ction — What YOU specifically did
- **R**esult — Measurable outcome

### Estructura en Español
- **S**ituación — Contexto (cuándo, dónde, quién)
- **T**area — Tu responsabilidad específica
- **A**cción — Qué hiciste TÚ específicamente
- **R**esultado — Resultado medible

---

## 💻 Coding Problems - STAR Stories

### Interview 1: Matt Love & Kshitij Shah (10:00-11:00am)
**Principio**: Articulate The Possible + Move Fast

#### STAR Story 1 - Migration de archivos en Kubo Financiero
**Español**:
```
SITUACIÓN: En Kubo Financiero (2023), teníamos una aplicación monolítica en servidor local que fallaba frecuentemente por espacio en disco al almacenar demasiados archivos.

TAREA: Necesitaba solucionar el problema de estabilidad del servidor antes del milestone en 2 semanas.

ACCIÓN: Organicé un brainstorming con mi equipo. Un compañero propuso migrar archivos a GCP y servirlos directamente al frontend. Era una buena idea, pero requería construir una librería Node.js para integrar con nuestro monolito en JSP — esto habría tomado semanas. Tomé esa idea como inspiración pero propuse un enfoque diferente: migrar archivos a GCP, pero mapear paths en la nube a los mismos paths locales que el sistema ya esperaba. Los archivos se descargarían bajo demanda, de forma transparente — sin cambios al código del monolito.

RESULTADO: Resolvimos los crashes de servidor con cambios mínimos de código, redujimos el uso de recursos significativamente, y enviamos mucho más rápido de lo que la propuesta original habría permitido.
```

**English**:
```
SITUATION: At Kubo Financiero (2023), we had a monolithic application on a local server crashing frequently due to disk space issues from storing too many files.

TASK: I needed to solve the server stability issue before the 2-week milestone.

ACTION: I brainstormed with my team. One teammate proposed migrating files to GCP and serving them directly to the frontend. It was a good idea, but it required building a Node.js library to integrate with our JSP-based monolith — that would have taken weeks. I took that idea as inspiration but proposed a different approach: migrate files to GCP, but map cloud paths to the same local paths the system already expected. Files would download on-demand, transparently — with no changes to the monolith's frontend code.

RESULT: We solved the server crashes with minimal code changes, significantly reduced server resource usage, and shipped much faster than the original proposal would have allowed.
```

---

#### STAR Story 2 - Clickonero Hot Sale
**Español**:
```
SITUACIÓN: En Clickonero, durante un evento Hot Sale (uno de los días más ocupados del año), nuestro sistema se cayó.

TAREA: Mi equipo fue asignado a encontrar y solucionar el problema y restaurar el servicio.

ACCIÓN: Me comuniqué con mi ex-tech lead, quien se había mudado a otra empresa. Aunque ya no trabajaba con nosotros, respondió a una llamada rápida y nos ayudó a identificar la causa raíz mucho más rápido de lo que habríamos logrado por nuestra cuenta.

RESULTADO: Resolvimos el incidente en medio día. Sin esa llamada, podría haber tomado un día completo — lo cual durante Hot Sale habría significado pérdidas financieras significativas.
```

**English**:
```
SITUATION: At Clickonero, during a Hot Sale event (one of the busiest days of the year), our system went down.

TASK: My team was assigned to find and fix the issue and restore the service.

ACTION: I reached out to our former tech lead who had moved to another company. Even though he no longer worked with us, he jumped on a quick call and helped us identify the root cause much faster than we would have on our own.

RESULT: We resolved the incident in half a day. Without that call it could have taken a full day — which during Hot Sale would have meant significant additional losses.
```

---

### Interview 2: Alfonso Lopez Lopez (11:00am-12:00pm)
**Principio**: Be Customer Obsessed

#### STAR Story Principal - CMS de Encuestas (Presidencia)
**Español**:
```
SITUACIÓN: En la Oficina Presidencial de México, el equipo de atención al ciudadano necesitaba publicar encuestas regularmente en el sitio web del gobierno. El proceso era completamente manual — tenían que solicitar al equipo de desarrollo que escribiera y desplegara HTML cada vez.

TAREA: Automatizar el proceso de publicación de encuestas para eliminar la dependencia del equipo en el equipo de desarrollo.

ACCIÓN: Inicialmente íbamos a construir una herramienta simple de envío de formularios. Pero después de trabajar con el equipo y escuchar su flujo de trabajo real, me di cuenta de que necesitaban autonomía completa — no solo un formulario, sino un CMS auto-servicio completo. Construimos un CMS que permitía al equipo de atención al ciudadano crear y publicar encuestas por su cuenta — sin intervención del equipo de desarrollo.

RESULTADO: El equipo pasó de esperar días por cada encuesta a publicarlas en minutos por su cuenta. Estaban felices, más productivos, y liberamos tiempo del equipo de desarrollo para trabajo de mayor impacto.
```

**English**:
```
SITUATION: At Mexico's Presidential Office, the citizen attention team needed to publish polls regularly on the government website. The process was fully manual — they had to request the development team to write and deploy HTML every single time.

TASK: Automate the poll publishing process to eliminate the development team's dependency on the citizen attention team.

ACTION: Initially we were going to build a simple form submission tool. But after working with the team and listening to their actual workflow, I realized they needed full autonomy — not just a form, but a complete self-service CMS. We built a CMS that allowed the citizen attention team to create and publish polls on their own — with no developer involvement.

RESULT: The team went from waiting days for each poll to publishing them in minutes on their own. They were happy, more productive, and we freed up developer time for higher-impact work.
```

---

#### STAR Story Comodín - Terremoto CDMX
**Español**:
```
SITUACIÓN: Estaba trabajando en la Oficina Presidencial de México cuando un terremoto fuerte impactó la Ciudad de México. En pocas horas, un pequeño grupo de nosotros decidimos actuar.

TAREA: Ayudar a los equipos de rescate proporcionando información sobre personas afectadas y ubicaciones dañadas.

ACCIÓN: Construimos y publicamos un formulario de emergencia en gob.mx donde los ciudadanos podrían reportar su ubicación, describir daños y compartir coordenadas GPS. Nos saltamos revisiones de seguridad, pruebas de carga y pruebas de rendimiento. El único objetivo era ponerlo en vivo para que los equipos de rescate tuvieran un mapa en tiempo real de dónde necesitaban ayuda.

RESULTADO: El sistema se puso en vivo el mismo día. Los equipos de rescate lo usaron para priorizar ubicaciones. No medimos el éxito ese día en uptime o calidad de código — lo medimos en vidas.
```

**English**:
```
SITUATION: I was working at Mexico's Presidential Office when a major earthquake hit Mexico City. Within a few hours, a small group of us decided to act.

TASK: Help rescue teams by providing information about affected people and damaged locations.

ACTION: We built and published an emergency form on gob.mx where citizens could report their location, describe damage, and share GPS coordinates. We skipped security reviews, QA, load testing. The only goal was to get it live so rescue teams could have a real-time map of where people needed help.

RESULT: The system went live the same day. Rescue teams used it to prioritize locations. We didn't measure success that day in uptime or code quality — we measured it in lives.
```

---

### Interview 3: Chaitra Ramdas (12:00-1:00pm)
**Principio**: Activate Caring + Study and Draw Inspiration

#### STAR Story 1 - Mentorship Jr Developer (Thomson Reuters)
**Español**:
```
SITUACIÓN: En Thomson Reuters, noté que un desarrollador junior de otro equipo estaba luchando. No tenía a quien recurrir — su equipo no lo apoyaba y estaba bloqueado.

TAREA: Ayudar al desarrollador junior a desbloquearse y progresar.

ACCIÓN: No tenía obligación de ayudar — no era mi proyecto. Pero me senté con él, exploramos el proyecto juntos, depuramos el problema, y eventualmente encontramos la solución. Después de eso, empezó a venir a mí cada vez que estaba bloqueado. Eso se convirtió en una mentoría informal — empecé a compartir principios de código limpio, mejores prácticas y técnicas de code review.

RESULTADO: Para mí no fue trabajo extra — fue simplemente lo correcto que había que hacer. Verlo crecer y ganar confianza fue el resultado real. Esa relación cambió mi trayectoria.
```

**English**:
```
SITUATION: At Thomson Reuters, I noticed a junior developer on another team was struggling. He had no one to turn to — his team wasn't supporting him and he was blocked.

TASK: Help the junior developer unblock and progress.

ACTION: I sat down with him, explored the project together, debugged it, and we eventually found the solution. After that he started coming to me whenever he was blocked. That turned into an informal mentorship — I started sharing clean code principles, best practices, and code review techniques.

RESULT:: For me it wasn't extra work — it was just the right thing to do. Seeing him grow and become more confident was the real result. That relationship changed my trajectory.
```

---

#### STAR Story 2 - AI Code Review Agent (Thomson Reuters)
**Español**:
```
SITUACIÓN: En Thomson Reuters, empecé a experimentar con Claude Code — un asistente de codificación con IA. Lo que me fascinó fue cómo razonaba sobre patrones a través de grandes corpus de código.

TAREA: Mejorar el proceso de code review aprovechando el razonamiento de patrones de IA.

ACCIÓN: Nuestro proceso de code review ya funcionaba — las revisiones ocurrían, los PR se mergearon. Pero noté que las revisiones eran inconsistentes y los desarrolladores junior recibían diferentes retroalimentaciones dependiendo de quién revisaba su código. Apliqué lo que aprendí sobre reconocimiento de patrones de IA: Analicé nuestros comentarios de PR anteriores, extraje los patrones que importaban para nosotros como equipo, y construí un agente personalizado que verificaba automáticamente los nuevos PRs contra esas reglas antes de que ningún revisor humano tocara el código.

RESULTADO: Las revisiones de código se volvieron más rápidas y consistentes. Los desarrolladores junior recibieron retroalimentación instantánea. El equipo gastó menos tiempo en comentarios repetitivos y más tiempo en discusiones arquitectónicas significativas.
```

**English**:
```
SITUATION: At Thomson Reuters, I started experimenting with Claude Code — an AI coding assistant. What fascinated me was how it reasoned about patterns across large code corpora.

TASK: Improve the code review process by leveraging AI pattern recognition.

ACTION: Our code review process was already working — reviews happened, PRs got merged. But I noticed that reviews were inconsistent and junior developers got different feedback depending on who reviewed their code. I applied what I learned about AI pattern recognition: I analyzed our past PR comments, extracted patterns that mattered to us as a team, and built a custom AI code review agent that automatically checked new PRs against those rules before any human reviewer touched the code.

RESULT: Code reviews became faster and more consistent. Junior developers got instant feedback. The team spent less time on repetitive comments and more on meaningful architectural discussions.
```

---

#### STAR Story 3 - Code Review que me cambió
**Español**:
```
SITUACIÓN: Al principio de mi carrera, envié un pull request del que estaba orgulloso — funcionaba. Pero el code review fue brutal. Completamente rechazado — sin código limpio, sin patrones de diseño, sin pruebas.

TAREA: Entender por qué mi código fue rechazado y mejorar.

ACCIÓN: En lugar de ponerme a la defensiva, usé el rechazo como señal. Busqué al desarrollador senior que lo rechazó y le pedí que me explicara su razonamiento. Esa conversación se convirtió en una mentoría. Empecé a estudiar seriamente — Clean Code, patrones de diseño, TDD. Con el tiempo, mi código pasó de rechazos a ser usado como ejemplos para desarrolladores junior.

RESULTADO: Esa relación cambió mi trayectoria. Dejé de ser el junior defensivo a ser alguien al que los junior consultaban por código limpio y mejores prácticas.
```

**English**:
```
SITUATION: Early in my career, I submitted a pull request I was proud of — it worked. But the code review was brutal. Completely rejected — no clean code, no design patterns, no tests.

TASK: Understand why my code was rejected and improve.

ACTION: Instead of getting defensive, I used the rejection as a signal. I sought out the senior developer who rejected it and asked him to walk me through his reasoning. That conversation turned into a mentorship. I started studying seriously — Clean Code, design patterns, TDD. Over time my code went from rejections to being used as examples for junior developers.

RESULT: That relationship changed my trajectory. I stopped being the defensive junior and became someone junior developers consulted for clean code and best practices.
```

---

### Interview 4: Poorva Karunakaran (1:00-2:00pm)
**Principio**: Imagine and Invent Before They Ask

#### STAR Story Principal - AI Code Review Agent (Thomson Reuters)
**Español**:
```
SITUACIÓN: En Thomson Reuters, iniciamos un proyecto nuevo e inmediatamente tuvimos fricción — las revisiones de código tomaban demasiado tiempo porque no había criterios de aceptación claros.

TAREA: Reducir el tiempo de code review y hacerlo más eficiente.

ACCIÓN: Nadie me pidió que arreglara esto. Simplemente vi el problema y decidí actuar. Primero, hice encuestas con mis compañeros de equipo para entender sus puntos de dolor. Luego, usé Claude Code para analizar todos nuestros comentarios de PR anteriores y extraer patrones. A partir de esos datos, redacté nuestros criterios de aceptación. Pero fui más allá — construí un agente personalizado de code review con IA que automáticamente verificaba los nuevos PRs contra esas reglas antes de que ningún revisor humano tocara el código.

RESULTADO: Las revisiones de código se volvieron más rápidas y consistentes. Los desarrolladores junior recibieron retroalimentación instantánea. El equipo gastó menos tiempo en comentarios repetitivos y más tiempo en discusiones arquitectónicas significativas.
```

**English**:
```
SITUATION: At Thomson Reuters, we started a new project and immediately had friction — code reviews were taking too long because there were no clear acceptance criteria.

TASK: Reduce code review time and make it more efficient.

ACTION: No one asked me to fix this. I just saw the problem and decided to act. First, I ran polls with my teammates to understand their pain points. Then I used Claude Code to analyze all our past PR comments and extract patterns. From that data I drafted our acceptance criteria. But I went further — I built a custom AI code review agent that automatically checked new PRs against those rules before any human reviewer touched the code.

RESULT: Code reviews became faster and more consistent. Junior developers got instant feedback. The team spent less time on repetitive comments and more on meaningful architectural discussions.
```

---

## � System Design - Amazon Locker System

### Arquitectura Propuesta
```
┌─────────────────────────────────────────────────────────────┐
│                     Customer (Web/Mobile)                │
└─────────────────────────┬───────────────────────────────────┘
                      │ HTTPS
                      ▼
┌─────────────────────────┐
│   API Gateway (Amazon)│
│   - Authentication (Cognito)                            │
│   - Rate limiting                                       │
│   - Request routing                                     │
└──────────┬────────────────────────┬───────────────────────┘
           │                        │
           ▼                        ▼
┌─────────────────────┐   ┌─────────────────────┐
│  Locker Service    │   │ Order Service     │
│   - Find locker     │   │ - Order status   │
│   - Reserve locker  │   │ - Package info   │
└───────┬───────────────┘   └─────────────────────┘
        │
        │
        ▼
┌─────────────────────┐
│ Database (RDS PostgreSQL)│
│   - lockers (id, location, size, state)│
│   - reservations (id, locker_id, user_id, code, expiry)│
│   - packages (id, tracking, locker_id)   │
└─────────────────────┘
```

### Preguntas de Clarificación (CLARIFYING QUESTIONS)

1. **"How many daily active users are we designing for?"**
   - **Respuesta**: 10k usuarios = 1 DB aguanta. 10M = necesitas cache, CDN, múltiples servidores.
   - **Por qué pregunta**: Determina escala de arquitectura

2. **"Is feed real-time or is eventual consistency acceptable?"**
   - **Respuesta**: Real-time = WebSockets/SSE. Eventual = Kafka fan-out simple. Cambia todo el diseño.
   - **Por qué pregunta**: Determina si necesitamos WebSockets o basta con pub/sub

3. **"Can posts include media like audio clips or images, or text only?"**
   - **Respuesta**: Con media necesitas S3 + CDN. Solo texto = mucho más simple.
   - **Por qué pregunta**: Determina complejidad de storage

4. **"Do we need to support search on posts, or just feed?"**
   - **Respuesta**: Búsqueda = Elasticsearch. Sin búsqueda = no lo incluyes, menos complejidad.
   - **Por qué pregunta**: Determina si necesitamos Elasticsearch

### Trade-offs Principales

| Decisión | Opción A | Opción B | Trade-off |
|----------|-----------|-----------|-----------|
| **Feed** | Push (fan-out on write) | Pull (fan-out on read) | Push = reads rápidos, caro para usuarios con muchos followers / Pull = simple, lento para usuarios con muchos follows |
| **DB** | SQL (PostgreSQL) | NoSQL (DynamoDB) | SQL = ACID, joins / NoSQL = scale, eventual consistency |
| **Auth** | Locks (2PL) | Redis | Locks = fuerte / Redis = rápido pero eventual consistency |

### Escalabilidad

**Nivel 1: Single Region (CDMX)**
- 100 lockers
- 1 DB (RDS Multi-AZ)
- 1 API Gateway

**Nivel 2: Multiple Regions**
- 100 lockers por región (CDMX, MTY, GDL)
- Regional APIs (latencia <50ms)
- Global API Gateway con geo-routing

**Nivel 3: Hyper-scale (US-wide)**
- Sharding por región
- Read replicas por alta demanda
- CDN para assets de locker locations

---

## 📊 Coding Problems Reference

### 1. Audiobook Trip Recommender (Two Sum)
**Pregunta**: Dada duración de viaje y lista de libros con duraciones, encontrar par cuyo total sea exactamente la duración del viaje.

**Solución óptima - HashMap (O(n))**:
```java
public static List<String> recommendBooks(double tripDuration, Map<String, Double> books) {
    Map<Double, String> seen = new HashMap<>();
    
    for (Map.Entry<String, Double> entry : books.entrySet()) {
        double complement = tripDuration - entry.getValue();
        if (seen.containsKey(complement)) {
            return Arrays.asList(seen.get(complement), entry.getKey());
        }
        seen.put(entry.getValue(), entry.getKey());
    }
    return Collections.emptyList(); // no match
}
```

| Metric | Value |
|--------|-------|
| Time | O(n) |
| Space | O(n) |
| Why HashMap? | Lookup O(1) instead of O(n) nested loop |

**Edge cases**: Ningún libro suma exactamente → vacío; Un libro con duración exacta → ¿cuenta solo?; Duraciones flotantes → usar epsilon.

---

### 2. Credit Management System (FIFO + Expiration)
**Pregunta**: Sistema de créditos con expiración de 1 año, consumo en orden FIFO (primero en expirar primero).

**Solución - Queue de créditos por expiración**:
```java
class CreditManager {
    private Deque<double[]> credits = new ArrayDeque<>(); // [amount, expiryTimestamp]
    
    public void addCredit(LocalDate date, double amount) {
        LocalDate expiry = date.plusYears(1);
        credits.addLast(new double[]{amount, expiry.toEpochDay()});
    }
    
    public double getBalance(LocalDate queryDate) {
        double balance = 0;
        long queryEpoch = queryDate.toEpochDay();
        
        for (double[] credit : credits) {
            if (credit[1] >= queryEpoch) { // Solo cuenta si no expiró
                balance += credit[0];
            }
        }
        return balance;
    }
    
    public void consumeCredits(LocalDate date, double amount) {
        double remaining = amount;
        while (remaining > 0 && !credits.isEmpty()) {
            double[] oldest = credits.peekFirst();
            if (oldest[0] <= remaining) {
                remaining -= oldest[0];
                credits.pollFirst();
            } else {
                oldest[0] -= remaining;
                remaining = 0;
            }
        }
    }
}
```

| Metric | Value |
|--------|-------|
| Time | O(n log n) para sort, O(n) overall |
| Space | O(n) |
| Why Deque? | O(1) append/pop desde ambos extremos — perfecto para FIFO |

**Edge cases**: Crédito expirado exactamente en queryDate → ¿cuenta?; Transacciones desordenadas → ordenar primero o usar PriorityQueue.

---

### 3. Employee Directory - GetCommunity (Tree Traversal)
**Pregunta**: Directorio de empleados como árbol. Extraer sub-árbol de empleados que comparten propiedad (ej: "Music genre" = "Rock"). Nodos que no hacen match → saltar pero conectar sus hijos matching con ancestro matching más cercano.

**Solución - DFS recursivo**:
```java
public List<ResultNode> getCommunity(Employee root, String property, String value) {
    List<ResultNode> result = new ArrayList<>();
    boolean matches = value.equals(root.properties.get(property));
    
    // Recolectar hijos que hacen match (recursivamente)
    List<ResultNode> matchingChildren = new ArrayList<>();
    for (Employee child : root.children) {
        matchingChildren.addAll(getCommunity(child, property, value));
    }
    
    if (matches) {
        ResultNode node = new ResultNode();
        node.employee = root;
        node.children = matchingChildren; // adopta todos los hijos matching
        result.add(node);
    } else {
        // No hace match → "transparente", propaga sus hijos hacia arriba
        result.addAll(matchingChildren);
    }
    
    return result;
}
```

| Metric | Value |
|--------|-------|
| Time | O(n) — visita cada nodo una vez |
| Space | O(h) — pila de recursión (altura del árbol) |
| Why DFS? | Natural para árboles; permite reconexión bottom-up de hijos |

**Edge cases**: Árbol vacío; Ningún nodo hace match → vacío; Todos hacen match → árbol original; Hoja que hace match → nodo sin hijos.

---

## ⚡ Tips de Entrevista

### Antes de la entrevista
- [x] Revisar todas las STAR stories (mínimo 3 por principio)
- [x] Practicar recitar STAR stories aloud (cada <2 min)
- [x] Revisar todas las soluciones de coding (3 soluciones por problema)
- [x] Practicar código sin IDE (papel + whiteboard)
- [x] Memorizar arquitectura de Amazon Locker System

### Durante la entrevista - Behavioral
- [x] Clarificar pregunta antes de responder
- [x] "Let me think through this out loud" — nunca silencio
- [x] Máximo 2 minutos por historia STAR
- [x] SER específico: "I did", "I led", "I implemented" (no "we did")
- [x] Resultados medibles: números, %, tiempo reducido
- [x] Conectar historia a principios Audible

### Durante la entrevista - Coding
- [x] Clarificar constraints y edge cases primero
- [x] State approach + complexity **ANTES** de codificar
- [x] Escribir código limpio con nombres significativos
- [x] Walk through example manualmente con input de muestra
- [x] Proactivamente mencionar trade-offs y alternativas
- [x] Para floats: mencionar epsilon, no `==` directo
- [x] Error handling explícito (no try/catch genérico)

### Durante la entrevista - System Design
- [x] Clarificar requerimientos (escala, consistency, latencia)
- [x] Dibujar boxes para servicios (API, Database, Cache)
- [x] Usar flechas para flujo de datos
- [x] Mencionar tecnologías específicas (PostgreSQL, Redis, Kafka, etc.)
- [x] Deep dive en 2-3 componentes críticos
- [x] Address trade-offs explícitamente (Push vs Pull, SQL vs NoSQL)
- [x] Mencionar escalabilidad (3 niveles)

### Al final de cada entrevista
- [x] Preguntar sobre próximos pasos
- [x] "What does success look like in the first 90 days?"
- [x] Agradecer al entrevistador

---

## 🔗 Links Útiles

- [ ] Amazon SDE Interview Prep: https://amzonsdeinterviewprep.splashthat.com/
- [ ] Audible People Principles: https://www.audible.com/about/people-principles
- [ ] Tech Interview Handbook: https://www.techinterviewhandbook.org/

---

## 📝 Checklist Final

- [ ] 18 STAR stories memorizadas (3 por principio × 6)
- [ ] 3 soluciones de coding memorizadas (3 problemas)
- [ ] Arquitectura de Amazon Locker memorizada
- [ ] 5 problemas de LeetCode practicados por semana (140 en 4 semanas)
- [ ] System design 2 sistemas/semana (8 en 4 semanas)
- [ ] Mock interviews (2 sesiones completas)
- [ ] Resto + agua listo el día anterior
- [ ] LinkedIn actualizado con experiencia más reciente
- [ ] CV actualizado con proyectos de AI/LLM

---

## 🎯 Principios Audible - Resumen Rápido

| Inglés | Español | Key Concept |
|----------|-----------|-------------|
| **Activate Caring** | Activa el Cuidado | Empatía, amabilidad, apoyo |
| **Articulate The Possible** | Articula Lo Posible | Visión clara, misión, propósito |
| **Imagine and Invent** | Imagina e Inventa | Anticiparse a problemas, simplificar |
| **Be Customer Obsessed** | Esté Obsesionado con el Cliente | Escucha activa, dependencia es honor |
| **Study and Draw Inspiration** | Estudia e Inspírate | Vanguardia, tecnología, innovación |

---

**¡Buena suerte, Alejandro! 🍀**
