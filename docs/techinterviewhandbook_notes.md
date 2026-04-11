# Tech Interview Handbook — Notas para Audible Interview

Fuente: https://www.techinterviewhandbook.org
Aplicado a los 4 problemas del 10 de abril.

---

## 1. Arrays — Interview 1: Audiobook Two Sum (Matt & Kshitij)

### Técnicas clave (del handbook)
- **Two pointers**: útil cuando el array está ordenado o puedes ordenarlo
- **HashMap/HashSet**: trade-off espacio por velocidad — O(n) time, O(n) space
- **Sliding window**: para subarrays contiguos (no aplica directamente aquí)
- **Sorting primero**: a veces simplifica — mencionar explícitamente el trade-off

### Para el problema de audiobooks (Two Sum variant)
- Brute force: nested loops O(n²) → mencionarlo como punto de partida
- Óptimo: HashMap complement → O(n) time, O(n) space
- Si duraciones son floats: **no uses `==`**, usa epsilon comparison
- Edge cases del handbook: duplicates, empty array, single element, no solution

### Corner cases a verificar siempre
- Empty input → return empty
- Array de 1-2 elementos
- Valores duplicados (¿dos libros con misma duración cuentan como par?)
- Sin solución → return empty list, no exception (clarificar con entrevistador)
- Múltiples soluciones posibles → ¿retornar todas o la primera?

### Lo que mide el rubric de Audible
- Justificar por qué usas HashMap vs sorting+pointers
- Calcular time/space complexity en voz alta
- Identificar trade-offs explícitamente

---

## 2. Queue + Hash Table — Interview 2: Credit Management (Alfonso)

### Técnicas clave (del handbook)
- **Queue/Deque**: FIFO = ArrayDeque en Java, O(1) para add/remove en extremos
- **HashMap**: lookup O(1), útil para tracking por fecha
- **Precomputation**: prefix sums para balance acumulado

### Para el Credit Management System
- Estructura: `Deque<CreditEntry>` donde cada entry tiene `{amount, expiryDate}`
- FIFO = consume primero el que expira antes → mantener ordenado por fecha de adición
- Si transactions llegan desordenadas → `PriorityQueue` ordenada por expiryDate
- Balance query: iterar queue, sumar solo los no expirados en queryDate

### Corner cases
- Query date antes de cualquier transacción → balance 0
- Todos los créditos expirados → balance 0
- Consumir más de lo disponible → excepción o retornar saldo restante (clarificar)
- Crédito que expira exactamente en queryDate → ¿expira O no? (clarificar con entrevistador)
- Transacciones desordenadas cronológicamente

### Trade-offs a mencionar
| Estructura | Time add | Time query | Space |
|---|---|---|---|
| ArrayDeque (ordenado por inserción) | O(1) | O(n) | O(n) |
| PriorityQueue (ordenado por expiry) | O(log n) | O(n) | O(n) |
| Sorted list | O(n) | O(n) | O(n) |

---

## 3. Trees — Interview 4: GetCommunity (Poorva)

### Técnicas clave (del handbook)
- **Recursion es el approach por defecto para trees** — el handbook lo enfatiza explícitamente
- **Post-order traversal**: procesa hijos antes que el padre — ideal para GetCommunity
- **Retornar dos valores** desde recursión: a veces necesario (aquí: lista de matching children)
- **Base case**: siempre verificar node == null primero

### Para GetCommunity
- DFS post-order: primero procesa todos los hijos, luego decide qué hacer con el nodo actual
- Si el nodo hace match → crea ResultNode con los hijos que hicieron match
- Si NO hace match → "sé transparente", propaga la lista de hijos hacia arriba
- Si root no hace match → resultado es lista (no árbol)

### Corner cases (del handbook adaptados)
- Empty tree / null root → return empty list
- Single node que hace match → return [node] sin hijos
- Single node que no hace match → return []
- Árbol completo hace match → retornar árbol original
- Ningún nodo hace match → return []
- Propiedad no existe en el nodo → tratarlo como no-match

### Extensión que pueden pedir (Logical & Maintainable)
- Múltiples propiedades → cambiar `String property, String value` a `Predicate<Employee>`
- Esto demuestra código mantenible y extensible

### Lo que busca Poorva específicamente
- Abstracción limpia: interface bien definida, responsabilidades claras
- Código extensible sin duplicación
- Nombrar bien: `getCommunity`, `ResultNode`, no nombres genéricos

---

## 4. System Design — Interview 3: Audible Social Site (Chaitra)

### Framework del handbook para System Design

**Paso a paso (45-60 min):**
1. **Clarify requirements** (5 min) — funcionales y no-funcionales
2. **Capacity estimation** (5 min) — DAU, storage, bandwidth
3. **High-level design** (10-15 min) — diagrama general
4. **Deep dive en componentes críticos** (20 min) — el entrevistador guía
5. **Trade-offs y alternativas** (5 min)

### Para Audible Social Site (Twitter/news feed pattern)

**Clarifying questions primero:**
- How many DAU? (asume 10M)
- Read-heavy or write-heavy? (muy read-heavy: 100:1 ratio)
- Is feed real-time or eventual consistency OK?
- Max post length? Media supported?
- Do we need search on posts?

**Capacity estimation:**
- 10M DAU × 5 posts/día = 50M writes/día = ~580 writes/s
- 10M DAU × 100 reads/día = 1B reads/día = ~11,500 reads/s → necesita cache agresivo

**Componentes core:**
- Post Service → DynamoDB (partition: userId, sort: timestamp)
- Fan-out Service → consume Kafka → escribe en Redis feed list por follower
- Feed Service → lee Redis → retorna al cliente
- CDN para assets (si hay fotos/audio)

**Trade-off central — Fan-out strategy:**
- Push (write): pre-computa feed → reads O(1) pero costoso para usuarios con muchos followers
- Pull (read): simple pero lento para usuarios que siguen a muchos
- **Híbrido (recomendado)**: Push para usuarios normales, Pull para celebridades/influencers

**Base de datos:**
- Posts: NoSQL (DynamoDB) — no necesita joins, escala horizontal
- Follows graph: NoSQL o grafo DB
- Feed cache: Redis `LPUSH feed:{userId} post_id`, `LTRIM` a últimos 1000

**Fault tolerance:**
- Kafka garantiza at-least-once delivery
- Fan-out debe ser idempotente
- Redis con réplicas para HA

### Lo que mide el rubric de Audible (System Design)
1. Identifica todos los requirements y clarifica
2. Identifica key technical decisions
3. Solución meets requirements y usa recursos eficientemente
4. Considera fault-tolerance y monitoring
5. Solución es extensible (más carga, nuevas features)
6. **Articula trade-offs explícitamente** — esto es crítico

---

## Tips Generales del Handbook (aplicados a Audible)

### En coding interviews
1. **Clarify antes de codear** — nunca asumas, siempre pregunta
2. **Brute force primero** — menciona O(n²) aunque no lo implementes
3. **Explica mientras escribes** — no silencio
4. **Escribe tests mentales** con los ejemplos dados
5. **Verifica edge cases** antes de decir "done"

### Señales positivas (lo que quieren ver)
- "Let me think about the trade-offs here..."
- "What if I sort first? That gives me O(n log n) but O(1) space..."
- "Edge case: what if the input is empty?"
- "I'd want to add monitoring on X because..."
