# 🎧 Audible Interview Cheatsheet — Viernes 10 Abril

## 📅 Schedule
- **Zoom:** https://amazon.zoom.us/j/92735802948?pwd=4mVtbQTJwGTwpxUBNmjjqKKf8ybou1.1
- **Meeting ID:** 9273 580 2948 | **Password:** 12618815

| Hora (CDMX) | Entrevistador | Tema |
|---|---|---|
| 9:30-9:45am | David Han — Recruiting Coordinator | Intro / bienvenida |
| 9:45-10:00am | — | BREAK |
| 10:00-11:00am | Kshitij Shah + Matt Love — SDE II | Coding: DSA + Articulate The Possible |
| 11:00-12:00pm | Alfonso Lopez Lopez — SDM | Coding: Problem Solving + Be Customer Obsessed |
| 12:00-1:00pm | Chaitra Ramdas — SDE II | System Design + Activate Caring + Study & Draw |
| 1:00-2:00pm | Poorva Karunakaran — SDE II | Coding: Logical & Maintainable + Imagine & Invent |
| 2:00-2:15pm | Nathan Shen — Recruiter | Cierre |

---

## 🧠 Audible People Principles — Resumen

1. **Activate Caring** — Trabaja hombro a hombro, no egos, altos estándares con amabilidad
2. **Articulate The Possible & Move Fast** — Cristaliza la visión, muévete con misión y propósito
3. **Imagine & Invent Before They Ask** — Abraza ambigüedad, simplifica antes de que te lo pidan
4. **Be Customer Obsessed** — Escucha activa al cliente, su dependencia en nosotros es un honor
5. **Study & Draw Inspiration From Culture and Technology** — Opera en la vanguardia de artes y ciencias

---

## 💻 Coding Problems — Los Reales de Esta Entrevista

---

### 🔵 Interview 1: Audiobook Trip Recommendation (Two Sum variant)
**Entrevistador: Matt Love & Kshitij Shah**

> Imagina una app que recomienda audiobooks para un viaje. Tienes la duración del viaje y las duraciones de los libros. Diseña una función que recomiende libros cuya duración sume exactamente la duración del viaje.
>
> Flight Duration: 2.5h | Book A: 1h, Book B: 5h, Book C: 1.5h, Book D: 2h
> → Recommendation: [Book A, Book C]

**Approach — Two Sum con HashMap:**
```java
public List<String> recommendBooks(double tripDuration, Map<String, Double> books) {
    // target = tripDuration, buscar dos libros que sumen exactamente
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

**Complejidades:**
- HashMap approach: **O(n) time, O(n) space**
- Brute force (nested loops): O(n²) time, O(1) space → mencionar como punto de partida

**Edge cases a mencionar:**
- Ningún libro suma exactamente → retornar vacío o excepción
- Un libro con duración exacta → ¿cuenta solo? (clarificar con entrevistador)
- Duraciones con punto flotante → comparación con epsilon, no `==`
- Múltiples combinaciones posibles → ¿retornar todas o la primera?

**Trade-offs a articular:**
- Sort + two pointers: O(n log n) pero O(1) espacio
- HashMap: O(n) más rápido pero usa memoria
- Para n grande → HashMap gana; para memoria limitada → two pointers

**Extensión posible:** ¿Qué si quieres k libros (no solo 2)? → Backtracking/recursión

---

### 🟢 Interview 2: Audible Credit Management System (FIFO + Expiration)
**Entrevistador: Alfonso Lopez Lopez**

> Build a system to track user credit balance with expiration policy.
> Credits expire after 1 year. Consumed in FIFO order (earliest expiring first).
> Input: List of transactions (date, amount) + query date
> Output: Valid credit balance at query date

**Approach — Queue de créditos por expiración:**
```java
class CreditManager {
    // Cada crédito: {amount, expirationDate}
    // Queue ordenada por expiración (FIFO = primero el que expira antes)
    private Deque<double[]> credits = new ArrayDeque<>(); // [amount, expiryTimestamp]
    
    public void addCredit(LocalDate date, double amount) {
        LocalDate expiry = date.plusYears(1);
        credits.addLast(new double[]{amount, expiry.toEpochDay()});
    }
    
    public double getBalance(LocalDate queryDate) {
        double balance = 0;
        long queryEpoch = queryDate.toEpochDay();
        
        for (double[] credit : credits) {
            // Solo cuenta si no ha expirado en queryDate
            if (credit[1] >= queryEpoch) {
                balance += credit[0];
            }
        }
        return balance;
    }
    
    public void consumeCredits(LocalDate date, double amount) {
        // Consume FIFO: primero el que expira antes
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

**Edge cases:**
- Crédito expirado exactamente en queryDate → ¿cuenta? (clarificar: expira DESPUÉS de 1 año)
- Balance negativo → no permitido, lanzar excepción
- Transacciones desordenadas por fecha → ordenar primero o usar PriorityQueue
- Consumir más de lo que hay → excepción o retornar -1

**Trade-offs:**
- `ArrayDeque`: O(1) add/remove extremos, O(n) balance query
- `PriorityQueue` por expiry: útil si transacciones llegan desordenadas

---

### 🟡 Interview 3: Audible Social Site — System Design
**Entrevistadora: Chaitra Ramdas**

> Design a simple version of Audible Social Site to increase engagement: users can share their current listen, recently completed book, or any message.
>
> **Two use cases:**
> 1. Submit a new post
> 2. Social feed — time-ordered list of your posts + posts from people you follow

#### Clarifying Questions — POR QUÉ PREGUNTAR CADA UNA

1. *"How many daily active users are we designing for?"*
   → **Escala**: 10k usuarios = 1 DB aguanta. 10M = necesitas cache, CDN, múltiples servidores.

2. *"Is the feed real-time or is eventual consistency acceptable?"*
   → **Arquitectura**: Real-time = WebSockets/SSE. Eventual = Kafka fan-out simple. Cambia todo el diseño.

3. *"Can posts include media like audio clips or images, or text only?"*
   → **Storage**: Con media necesitas S3 + CDN. Solo texto = mucho más simple.

4. *"Do we need to support search on posts, or just the feed?"*
   → **Índices**: Búsqueda = Elasticsearch. Sin búsqueda = no lo incluyes, menos complejidad.

**Asunciones para esta entrevista:** 10M DAU, eventual consistency OK, texto only, sin búsqueda.

#### High-Level Design

```
[Web/Mobile Client]
       │
       │ POST /posts
       ▼
[Post Service] ──→ [Posts DB (DynamoDB)]
       │                    
       │ publish event      
       ▼                    
[Message Queue (SQS/Kafka)]
       │
       ▼
[Fan-out Service] ──→ [Feed Cache (Redis)]
                              │
                              │ GET /feed
                              ▼
                       [Feed Service] ──→ [Client]
```

#### Feed Strategies (Trade-off central)

| Approach | Pros | Contras |
|---|---|---|
| **Push (fan-out on write)** | Feed pre-computed, reads O(1) | Costoso para usuarios con muchos followers |
| **Pull (fan-out on read)** | Simple, no duplicación | Lento para usuarios con muchos follows |
| **Híbrido** | Pull para celebridades, Push para usuarios normales | Complejidad adicional |

**Recomendar: Híbrido** — usuarios con >10k followers → pull; resto → push a Redis feed list.

#### FUQ: New Post Flow (lo que preguntarán primero)
1. Cliente hace `POST /posts` con texto + timestamp
2. **Post Service** valida + escribe en **DynamoDB** (partition key: userId, sort key: timestamp)
3. Publica evento a **Kafka** topic `new-posts`
4. **Fan-out Service** consume el evento → busca followers del usuario → escribe post_id en el feed list de cada follower en **Redis** (`LPUSH feed:{userId} post_id`)
5. Feed list en Redis tiene TTL de 7 días, máximo 1000 posts (trim con `LTRIM`)

#### Non-functional
- **Scale**: 10M DAU × 10 posts/día read = 100M reads/día → ~1,200 RPS → Redis aguanta fácil
- **Fault tolerance**: Kafka garantiza at-least-once delivery; Fan-out idempotente (check si post_id ya existe)
- **Monitoring**: lag en Kafka fan-out, cache hit rate en Redis

---

### 🔴 Interview 4: GetCommunity — Tree Traversal con Filtro
**Entrevistadora: Poorva Karunakaran**

> Employee directory como árbol. Cada nodo tiene propiedades (Location, Country, Music genre, etc.).
> `GetCommunity("Music genre", "Rock")` → extraer jerarquía de empleados que comparten esa propiedad.
> Nodos que no hacen match → saltar, pero conectar sus hijos matching con el ancestro matching más cercano.

**Ejemplo:**
```
         a*
/     /     \     \
b     c*     d*     e
|   / | \   /  \   / \
f* g  h* i j*   k l  m

→ resultado:
  a
/ | \
f  c  d
   |  |
   h  j

Si a* no hace match → lista: [f, c, d] con sus hijos
```

**Solución — DFS recursivo:**
```java
class Employee {
    String name;
    Map<String, String> properties; // "Music genre" → "Rock"
    List<Employee> children;
}

class ResultNode {
    Employee employee;
    List<ResultNode> children = new ArrayList<>();
}

// Retorna lista de ResultNodes que hacen match (con sus sub-árboles filtrados)
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

// Entry point: si la raíz hace match → árbol; si no → lista
public Object getResult(Employee root, String property, String value) {
    List<ResultNode> nodes = getCommunity(root, property, value);
    if (nodes.size() == 1 && nodes.get(0).employee == root) {
        return nodes.get(0); // árbol con raíz
    }
    return nodes; // lista de sub-árboles
}
```

**Complejidades:** O(n) time, O(n) space (peor caso: todos hacen match)

**Edge cases:**
- Árbol vacío / null → return empty list
- Ningún nodo hace match → return empty list
- Todos hacen match → árbol completo original
- Hoja que hace match → nodo sin hijos
- Propiedad que no existe en algún nodo → tratarlo como no-match

**Lo que buscan (Logical & Maintainable):**
- Interfaz limpia (`getCommunity` bien nombrado, responsabilidades claras)
- Sin duplicación de lógica
- Código extensible: ¿qué si quiero filtrar por múltiples propiedades? → pasar `Predicate<Employee>`

---

## 📖 STAR Stories por Entrevistador

---

### 🔵 Matt Love & Kshitij Shah (10-11am)
**Principio: Articulate The Possible & Move Fast**

**Preguntas reales:**
- *"Give me an example of when you solicited a set of ideas from your team and used those to come to a better solution than one you'd have developed yourself."*
- *"Tell me about a time you rolled up your sleeves to get something done, even if it wasn't technically your piece of work to do."*

#### Historia 1 — Migración de archivos en Kubo Financiero
**Para:** *"Solicited ideas from team → better solution"*

> "At Kubo Financiero, we had a monolithic application on a local server crashing frequently due to disk space issues from storing too many files.
>
> My task was to solve this with my team. During our discussion, one teammate proposed migrating the files to GCP and serving them directly to the frontend. It was a good idea, but it required building a Node.js library to integrate with our JSP-based monolith — that would have taken weeks.
>
> I took that idea as inspiration but proposed a different approach: migrate the files to GCP, but map the cloud paths to the same local paths the system already expected. Files would download on-demand transparently — zero changes to the monolith's frontend code.
>
> We solved the crashes with minimal code changes, reduced server resource usage significantly, and shipped much faster than the original proposal would have allowed."

#### Historia 2 — Clickonero Hot Sale
**Para:** *"Rolled up your sleeves, not technically your work"*

> "At Clickonero, during a Hot Sale event — one of the busiest days of the year — our system went down. Our architect was traveling abroad and unreachable.
>
> My team was assigned to find and fix the issue. I reached out to our former tech lead who had moved to another company. Even though he no longer worked with us, he jumped on a quick call and helped us identify the root cause much faster than we would have on our own.
>
> We resolved the incident in half a day. Without that call it could have taken the full day — which during Hot Sale would have meant significant additional losses."

---

### 🟢 Alfonso Lopez Lopez (11am-12pm)
**Principio: Be Customer Obsessed**

**Preguntas reales:**
- *"Give me an example of when you had to change your course of action given a new insight or idea from a customer."*
- *"Tell me about a time you went above and beyond to ensure a customer was delighted."*

#### Historia Principal — CMS de Encuestas (Presidencia)
**Para:** *"Changed course given customer insight"* o *"went above and beyond"*

> "At Mexico's Presidential Office, the citizen attention team needed to publish polls regularly on the government website. The process was fully manual — they had to request the development team to write and deploy HTML every single time. They were frustrated and dependent on us for something that should have been simple.
>
> Initially we were going to build a simple form submission tool. But after sitting with the team and listening to their actual workflow, I realized they needed full autonomy — not just a form, but a complete self-service CMS.
>
> We built a CMS that allowed the citizen attention team to create and publish polls themselves — no code, no developer involvement.
>
> The team went from waiting days for each poll to publishing in minutes on their own. They were happy, more productive, and we freed up developer time for higher-impact work."

#### 🌟 Historia Comodín — Terremoto CDMX
> "I was working at Mexico's Presidential Office when a major earthquake hit Mexico City. Within a few hours, a small group of us decided to act — we built and published an emergency form on gob.mx where citizens could report their location, describe the damage, and share GPS coordinates.
>
> We skipped security reviews, QA, load testing. The only goal was to get it live so rescue teams could have a real-time map of where people needed help.
>
> The system went live the same day. Rescue teams used it to prioritize locations. We didn't measure success in uptime or code quality that day — we measured it in lives."

---

### 🟡 Chaitra Ramdas (12-1pm)
**Principios: Activate Caring + Study and Draw Inspiration**

**Preguntas reales:**
- *"Tell me about an experience you had in dedicating your time, energy, and/or expertise to help others."* (Activate Caring)
- *"Tell me about a time you used new information or insight to improve a product or process that was working well."* (Study & Draw)
- *"Tell me about the most interesting thing you've learned in the past month, and what insight you've extracted from it."* (Study & Draw)
- *"Tell me about a time you spent time getting to know a colleague better and why."* (Activate Caring)

#### Historia 1 — Mentorship Jr Developer (Thomson Reuters)
**Para:** *"Dedicated your time to help others"*

> "At Thomson Reuters, I noticed a junior developer on another team was struggling. He had no one to turn to — his team wasn't supporting him and he was blocked.
>
> I had no obligation to help — it wasn't my project. But I sat down with him, explored the project together, debugged it, and we eventually found the solution.
>
> After that he started coming to me whenever he was blocked. That turned into an informal mentorship — I started sharing clean code principles, best practices, code review techniques.
>
> For me it wasn't extra work — it was just the right thing to do. Seeing him grow and become more confident was the real result."

#### Historia 2 — AI Code Review Agent (Thomson Reuters)
**Para:** *"New information to improve a process that was working well"* o *"most interesting thing learned"*

> "At Thomson Reuters, I started experimenting with Claude Code — an AI coding assistant. What fascinated me was how it reasons about patterns across large code corpora.
>
> Our code review process was already working — reviews happened, PRs got merged. But I noticed the reviews were inconsistent and junior developers got different feedback depending on who reviewed them.
>
> I applied what I learned about AI pattern recognition: I built a custom AI code review agent that analyzed our past PR comments, extracted the patterns that mattered to us as a team, and automatically checked new PRs against those rules before any human reviewer touched the code.
>
> The result was faster, more consistent reviews and junior developers got instant feedback. The team spent less time on repetitive comments and more on meaningful architectural discussions."

#### Historia 3 — Code Review que me cambió
**Para:** *"Getting to know a colleague better"* — adaptar para mostrar relación/crecimiento

> "Early in my career, I submitted a pull request I was proud of — it worked. But the code review was brutal. Completely rejected — no clean code, no design patterns, no tests.
>
> Instead of getting defensive, I used it as a signal. I sought out the senior developer who rejected it, asked him to walk me through his reasoning. That conversation turned into a mentorship.
>
> I started studying seriously — Clean Code, design patterns, TDD. Over time my code went from rejections to being used as examples for junior developers. That relationship changed my trajectory."

---

### 🔴 Poorva Karunakaran (1-2pm)
**Principio: Imagine & Invent Before They Ask**

**Pregunta real:**
- *"Tell me about a time you took something that was working 'just fine' and you still found a way to improve upon it."*

#### Historia Principal — AI Code Review Agent (Thomson Reuters)
**Para:** *"Took something working and improved it anyway"*

> "At Thomson Reuters, we started a new project and immediately had friction — code reviews were taking too long because there were no clear acceptance criteria.
>
> Nobody asked me to fix this. I just saw the problem and decided to act. First, I ran polls with my teammates to understand their pain points. Then I used Claude Code to analyze all our past PR comments and extract patterns.
>
> From that data I drafted our acceptance criteria. But then I went further — I built a custom AI code review agent that automatically checked new PRs against those rules before any human reviewer touched the code.
>
> Code reviews became faster and more consistent. Junior developers got instant feedback. The team spent less time on repetitive comments and more on meaningful architectural discussions."

---

## ⚡ Tips Generales

- **Máximo 2 minutos por historia** — no te extiendas
- **En coding:** *"Let me think through this out loud"* — nunca silencio
- **Empieza con brute force**, luego optimiza — explica el trade-off
- **Para float comparisons:** menciona epsilon, no `==` directo
- **Al final de cada entrevista:** *"What does success look like in the first 90 days?"*
- **Keycloak** (no keycloack), **Prometheus** (no prometeus)

## 🔗 Links útiles
- Amazon SDE Interview Prep: https://amazonsdeinterviewprep.splashthat.com/
- Audible People Principles: https://www.audible.com/about/people-principles
