# 🎧 Plan de Estudio Completo - Audible Interview

**Objetivo**: Preparación integral para entrevistas técnicas + behaviorales de Audible
**Duración**: 4 semanas (28 días)
**Fecha inicio**: 2026-04-07
**Entrevista target**: 2026-05-07

---

## 📋 Estructura del Proceso

### Formato
- **Duración**: 30 minutos por sesión
- **Contenido**: Competencia técnica + Principios Audible + Diseño de sistemas

### Entrevistadores

| Entrevistador | Temas | Principios Audible |
|----------------|--------|-------------------|
| Matt Love & Kshitij Shah | Coding (DSA) | Articulate The Possible + Move Fast |
| Alfonso López López | Coding (Problem Solving) | Be Customer Obsessed |
| Chaitra Ramdas | System Design | Study/Culture/Tech + Activate Caring |
| Poorva Karunakaran | Coding (Logical & Maintainable) | Imagine and Invent Before They Ask |

---

## 🎯 Principios de Evaluación

1. **Resolver el problema correctamente** → Solución funcional
2. **Compensaciones** → Justificar trade-offs de arquitectura/diseño
3. **Determinar por qué una solución es mejor que otra** → Análisis comparativo

---

## 📅 Semana 1: STAR Stories & DSA Fundamentals

### Objetivo
- Preparar historias STAR para 6 principios (18 historias)
- Fundamentos de estructuras de datos

### Lunes-Domingo: STAR Framework

#### 📝 Articulate The Possible + Move Fast To Make It Real

**Pregunta 1**: Tell me about a time you needed to quickly get your team up to speed on new information, and how you rallied them around a near-term goal or plan of action.

**STAR Template**:
- **S**ituation: Contexto (cuándo, dónde, quién)
- **T**ask: Tu responsabilidad específica
- **A**ction: Qué hiciste TÚ específicamente
- **R**esult: Resultado medible

**Ejemplo para tu perfil**:
```
S: En Globant (2023), migrando código legacy a Spring Boot en un proyecto de Taulia.
T: Necesitaba que el equipo entendiera el nuevo arquitectura en 2 semanas antes de milestone.
A: 1) Creé documento de arquitectura con diagramas 2) Sesiones de pair programming daily 3) Code reviews intensivos 4) Demo del progreso cada 2 días.
R: Equipo productivo en 10 días (vs 14 esperados), 20% más rápido, 0 bugs críticos en milestone.
```

**Pregunta 2**: Give me an example of when you solicited a set of ideas from your team and used those to come to a better solution than one you'd have developed yourself.

**Ejemplo**:
```
S: En Kubo Financiero (2019), optimizando latencia de microservicios.
T: Tenía una solución propia para cache en Redis, pero no estaba seguro de abordaje óptimo.
A: Organicé brainstorming con 3 devs. Ideas: 1) Redis (mi propuesta) 2) Edge caching 3) Lazy loading 4) Híbrido.
   Combinamos lazy loading + Redis local. Implementamos en 2 días con pruebas A/B.
R: 15% reducción de latencia vs mi solución original (era 8%).
```

**Pregunta 3**: Give me an example of a time when you were able to leverage – and activate – your internal network to deliver a better, faster result or outcome.

**Ejemplo**:
```
S: En Thomson Reuters (2024), migrando Grails a Spring Boot.
T: Estancados en integración de sistema legacy con nuevo Spring Boot, delay de 2 semanas.
A: Contacté ex-colega de Globant experto en Spring Boot legacy. 30-min call → patrón Adapter + Spring Data JPA.
   Compartí código con equipo, implementamos en 3 días.
R: Reducción de delay de 14 días a 3 días (78% más rápido).
```

---

#### 📝 Study and Draw Inspiration From Culture and Technology

**Pregunta 1**: Tell me about a time when you consumed new information (i.e., read a book, attended a conference, etc.) seemingly not relevant to your field, and extracted something new and interesting that influenced your work.

**Ejemplo**:
```
S: En 2023, leí "The Design of Everyday Things" (diseño industrial).
T: Buscando inspiración fuera de tecnología para mejorar UX de API.
A: Apliqué concepto de "affordances" a diseño de REST APIs - endpoints más intuitivos basados en intención del usuario.
   Implementé guía de affordances en 3 servicios: GET /books/{id}/cover (no /getBookCover).
R: Adopción por otros equipos (5 servicios más), reducción de tickets de soporte 30%.
```

**Pregunta 2**: Tell me about a time you learned something new – from anywhere in life – and adapted and applied it to create value at work.

**Ejemplo**:
```
S: En 2022, aprendí sobre "batch cooking" (cocinar en batch para la semana).
T: Noté patrón: preparar todo en batch más eficiente que proceso único.
A: Apliqué a CI/CD: build Docker images en batch nightly en lugar de on-demand.
   Implementé caching de layers, pre-warming de DB.
R: Tiempo de deployment de 8min a 2min (75% reducción), costos AWS 40% menor.
```

**Pregunta 3**: Tell me about a time you intentionally brought a "non-expert" into a conversation to bring a different perspective to the table.

**Ejemplo**:
```
S: En Finerio Connect (2020), diseñando UX de onboarding de bancos.
T: Stuck en diseño técnico de integración, 3 días sin progreso.
A: Invité a PM de producto (no técnico) a sesión. Preguntó: "¿Bancos realmente usan esto o es tu asunción?"
   Investigamos → 70% bancos usaban API diferente. Cambiamos estrategia.
R: Rediseño completo en 5 días (vs 15 días de implementación original), integración 3 bancos adicionales.
```

---

#### 📝 Activate Caring

**Pregunta 1**: Tell me about a time you had to balance your goal with a teammate's and ensure you both succeeded.

**Ejemplo**:
```
S: En Globant (2023), trabajaba con junior dev en tarea crítica.
T: Mi meta: entregar en 3 días. Su meta: aprender microservicios.
A: 1) Rediseñé tarea: él hizo módulo simple, yo módulo complejo 2) Daily syncs de 30min para enseñar 3) Code review detallado.
R: Entregamos en 3 días + junior hizo PR solo al siguiente módulo (meta cumplida para ambos).
```

**Pregunta 2**: Tell me about a time you offered your voice in support of someone else's idea that was unpopular or misunderstood, but that you believed was the right idea.

**Ejemplo**:
```
S: En Kubo Financiero (2019), tech lead proponía monolith vs mi preferencia de microservicios.
T: Todos apoyaban monolith por "simplicidad", yo era único a favor de microservicios.
A: Defendí microservicios con datos: 1) Escalabilidad 2) Team autonomy 3) Future-proofing.
   Propusimos POC de microservicios con 1 servicio. 2 semanas demo → éxito.
R: Empresa adoptó microservicios, hoy tienen 15+. Yo gané respeto técnico.
```

**Pregunta 3**: Tell me about a time you collaborated on a piece of work you could have done faster on your own, but which yielded a stronger outcome for partnership.

**Ejemplo**:
```
S: En Thomson Reuters (2024), desarrollando AI agent para code review.
T: Podía hacer solo en 3 días, pero involucré a 2 devs de QA.
A: 1) Invité a diseño del agent desde inicio 2) Testing early con casos reales 3) Feedback loop diario.
R: Producto final mejor (95% accuracy vs 80% estimado), team adoption 100% vs resistencia prevista.
```

---

### Tareas de la Semana 1

- [ ] Lunes: Escribir 3 historias STAR para "Articulate The Possible"
- [ ] Martes: Escribir 3 historias STAR para "Study and Draw Inspiration"
- [ ] Miércoles: Escribir 3 historias STAR para "Activate Caring"
- [ ] Jueves: Practicar recitar STAR stories aloud (cada una <2 min)
- [ ] Viernes: Revisar y pulir historias con feedback
- [ ] Sábado: DSA Practice - Arrays, Hash Maps, Trees
- [ ] Domingo: Mock interview STAR + DSA básico

---

## 📅 Semana 2: DSA Profundo & Be Customer Obsessed

### Objetivo
- Dominar estructuras de datos para problemas de coding
- Preparar STAR stories para "Be Customer Obsessed"

### Lunes-Miércoles: DSA Practice

#### 1. First Non-Repeating Character in Stream

**Problema**: Dado un stream de caracteres, retornar el primer caracter que no repite.

**Solución 1: Brute Force** (O(n²))
```python
def first_unique_brute(s: str) -> str:
    for i, ch in enumerate(s):
        if ch not in s[i+1:] and ch not in s[:i]:
            return ch
    return None  # No unique char
```
- **Time**: O(n²) - Para cada char, busca en resto del string
- **Space**: O(1) - No usa estructura extra
- **Uso**: Solo para strings muy pequeños (<100 chars)

**Solución 2: Frequency Array** (O(n))
```java
// La solución dada en el problema
public static char findFirstUniqueCharacter(String inputString) throws Exception {
    if (inputString == null || inputString.length() == 0) {
        throw new Exception("Unexpected input: inputString is null or empty");
    }

    int[] charFrequency = new int[CHAR_SET_LENGTH];

    for (int i = 0; i < inputString.length(); i++) {
        char ch = inputString.charAt(i);
        charFrequency[ch - 'a']++;
    }

    for (int i = 0; i < inputString.length(); i++) {
        if (charFrequency[inputString.charAt(i) - 'a'] == 1)
            return inputString.charAt(i);
    }

    throw new Exception("Unexpected input: inputString does not have a unique character");
}
```
- **Time**: O(n) - 2 pasadas
- **Space**: O(1) - Array fijo de 26 chars
- **Limitación**: Solo funciona para lowercase a-z (extendible a 256 chars para ASCII)
- **Por qué es mejor**: O(n) vs O(n²), space O(1) aceptable

**Solución 3: LinkedHashMap** (O(n)) - Mantiene orden de inserción
```python
from collections import OrderedDict

def first_unique_linked(s: str) -> str:
    seen = {}
    for ch in s:
        if ch in seen:
            del seen[ch]  # Remover si ya existe
        else:
            seen[ch] = True  # Marcar como visto una vez
    return next(iter(seen.keys())) if seen else None
```
- **Time**: O(n) - LinkedHashMap es O(1) para insert/delete
- **Space**: O(n) - En peor caso todos chars únicos
- **Por qué usar**: Mantiene orden de primera aparición, funciona para cualquier char (Unicode)

**Edge Cases**:
- String vacío → Throw exception
- No char único → Throw exception
- Todos chars repetidos → Throw exception
- Case sensitivity → Decidir si 'A' == 'a' (normalmente no)
- Unicode → LinkedHashMap mejor que array fijo

**Trade-offs**:
| Solución | Time | Space | When to use |
|----------|-------|--------|-------------|
| Brute Force | O(n²) | O(1) | Strings <100 chars, memoria crítica |
| Frequency Array | O(n) | O(1) | Alphabets pequeños (a-z), ASCII |
| LinkedHashMap | O(n) | O(n) | Unicode, caracteres arbitrarios, balance |

---

#### 2. Smallest K Numbers in File

**Solución 1: Sort** (O(n log n))
```java
private static int[] smallestValueListV1(int[] input, int k) {
    // avoid side effects. optional
    int[] sortedInput = Arrays.copyOf(input, input.length);

    Arrays.sort(sortedInput);

    return Arrays.copyOf(sortedInput, Math.min(k, input.length));
}
```
- **Time**: O(n log n) - Sorting
- **Space**: O(n) - Copia del array
- **Uso**: Simple, legible, n pequeño (<1M)

**Solución 2: Max Heap** (O(n log k))
```python
import heapq

def smallest_k_heap(input: list, k: int) -> list:
    # Mantener heap de tamaño k con los k más pequeños
    # Usamos max heap negativo (Python tiene min heap)
    max_heap = [-x for x in input[:k]] if k < len(input) else input[:]
    heapq.heapify(max_heap)

    for num in input[k:]:
        # Si num es menor que el máximo en heap, reemplazar
        if num < -max_heap[0]:
            heapq.heappop(max_heap)
            heapq.heappush(max_heap, -num)

    # Heap contiene negativos, convertir a positivos
    return sorted([-x for x in max_heap])
```
- **Time**: O(n log k) - n iteraciones, heap size k
- **Space**: O(k) - Solo almacenamos k elementos
- **Ventaja vs sort**: k << n (ej: n=1B, k=10 → mucho más eficiente)
- **Por qué es mejor**: O(n log k) vs O(n log n) cuando k << n

**Solución 3: Quickselect** (O(n) average)
```python
import random

def smallest_k_quickselect(input: list, k: int) -> list:
    def partition(arr, left, right, pivot_index):
        pivot = arr[pivot_index]
        arr[pivot_index], arr[right] = arr[right], arr[pivot_index]
        store = left
        for i in range(left, right):
            if arr[i] < pivot:
                arr[store], arr[i] = arr[i], arr[store]
                store += 1
        arr[right], arr[store] = arr[store], arr[right]
        return store

    def select(arr, left, right, k_smallest):
        if left == right:
            return arr[:k_smallest]

        pivot_index = random.randint(left, right)
        pivot_index = partition(arr, left, right, pivot_index)

        if k_smallest == pivot_index:
            return arr[:k_smallest]
        elif k_smallest < pivot_index:
            return select(arr, left, pivot_index - 1, k_smallest)
        else:
            return select(arr, pivot_index + 1, right, k_smallest)

    return select(input[:], 0, len(input) - 1, k)
```
- **Time**: O(n) average, O(n²) worst case (raro con random pivot)
- **Space**: O(1) in-place (o O(k) si copias)
- **Ventaja**: No requiere heap sort, más rápido para grandes datasets
- **Riesgo**: Worst case O(n²) (raro con random)

**Trade-offs**:
| Solución | Time | Space | When to use |
|----------|-------|--------|-------------|
| Sort | O(n log n) | O(n) | n pequeño (<1M), simplicidad |
| Max Heap | O(n log k) | O(k) | k << n, memoria limitada |
| Quickselect | O(n) avg | O(1) | n grande, k grande |

**File Input Considerations**:
```python
def smallest_k_in_file(file_path: str, k: int) -> list:
    heap = []
    heapq.heapify(heap)  # Min heap

    with open(file_path, 'r') as f:
        for line in f:
            num = int(line.strip())
            if len(heap) < k:
                heapq.heappush(heap, -num)  # Push negativo
            elif num < -heap[0]:  # Si num es menor que el mayor en heap
                heapq.heapreplace(heap, -num)  # Reemplazar

    return sorted([-x for x in heap])
```
- **Streaming**: No cargar todo en memoria, procesar línea por línea
- **Memory**: O(k) vs O(n) - Crítico para archivos gigantes

---

#### 3. File Search with Rules (OOP Design)

**Solución dada**:
```java
// Interface para abstracción
public interface FileRule {
    boolean match(File f);
}

// AND rule
public class FileRuleAnd implements FileRule {
    private final List<FileRule> andRules;

    public FileRuleAnd(FileRule ... andRules) {
        this.andRules = Arrays.asList(andRules);
    }

    @Override
    public boolean match(File f) {
        for (FileRule rule : andRules) {
            if (!rule.match(f)) {
                return false;
            }
        }
        return true;
    }
}

// OR rule
public class FileRuleOr implements FileRule {
    private final List<FileRule> orRules;

    public FileRuleOr(FileRule ... orRules) {
        this.orRules = Arrays.asList(orRules);
    }

    @Override
    public boolean match(File f) {
        for (FileRule rule : orRules) {
            if (rule.match(f)) {
                return true;
            }
        }
        return false;
    }
}

// Extension rule
public class FileRuleExtension implements FileRule {
    private final String extension;

    public FileRuleExtension(String extension) {
        this.extension = extension.toLowerCase();
    }

    @Override
    public boolean match(File f) {
        return f.getName().toLowerCase().endsWith("." + extension);
    }
}

// Size rule
public class FileRuleSize implements FileRule {
    public enum FileRuleSizeOp { EQUAL, GREATER_THAN, LESS_THAN }

    private final long sizeInBytes;
    private final FileRuleSizeOp op;

    public FileRuleSize(long sizeInBytes, FileRuleSizeOp op) {
        this.sizeInBytes = sizeInBytes;
        this.op = op;
    }

    @Override
    public boolean match(File f) {
        switch (op) {
            case EQUAL: return f.length() == sizeInBytes;
            case GREATER_THAN: return f.length() > sizeInBytes;
            case LESS_THAN: return f.length() < sizeInBytes;
            default: return false;
        }
    }
}

// Finder
public class FindFile {
    public static void find(String dir, FileRule rule) {
        File baseDir = new File(dir);
        if (baseDir.isDirectory()) {
            for (File f : baseDir.listFiles()) {
                if (rule.match(f)) {
                    System.out.println(f.getName());
                }
            }
        }
    }

    public static void main(String[] args) {
        // Encuentra archivos .java O (archivos .zip de tamaño exacto 5711472 bytes)
        FileRule rule = new FileRuleOr(
            new FileRuleExtension("java"),
            new FileRuleAnd(
                new FileRuleExtension("zip"),
                new FileRuleSize(5711472, FileRuleSize.FileRuleSizeOp.EQUAL)
            )
        );

        find("/home/local/ANT/lestrozi", rule);
    }
}
```

**Análisis del diseño**:

1. **Open/Closed Principle**: ✅ Abierto a extensión (nuevas rules), cerrado a modificación
2. **Single Responsibility**: ✅ Cada rule tiene una responsabilidad única
3. **Composite Pattern**: ✅ `FileRuleAnd` y `FileRuleOr` componen rules
4. **Interface Segregation**: ✅ `FileRule` es minimalista
5. **Dependency Inversion**: ❌ `FindFile` depende de concreto `FileRule` (OK para este caso)

**Mejoras**:
- Agregar manejo de symbolic links (recursión infinita)
- Soporte para búsqueda recursiva en subdirectorios
- Parallel processing para directorios grandes
- Caching de reglas si se reusan

**Extensiones**:
```java
// Name pattern rule
public class FileRuleName implements FileRule {
    private final String pattern;

    public FileRuleName(String pattern) {
        this.pattern = pattern;
    }

    @Override
    public boolean match(File f) {
        return f.getName().matches(pattern);
    }
}

// Modified after date rule
public class FileRuleModifiedAfter implements FileRule {
    private final Date date;

    public FileRuleModifiedAfter(Date date) {
        this.date = date;
    }

    @Override
    public boolean match(File f) {
        return new Date(f.lastModified()).after(date);
    }
}

// Uso combinado
FileRule complexRule = new FileRuleAnd(
    new FileRuleExtension("java"),
    new FileRuleName(".*Service\\.java"),
    new FileRuleModifiedAfter(new Date(System.currentTimeMillis() - 86400000))  // Últimas 24h
);
```

---

### Jueves: Be Customer Obsessed - STAR Stories

**Pregunta 1**: Tell me about a time you dove into learning about customer perspective or experience which then influenced a business decision you made.

**Ejemplo**:
```
S: En Finerio Connect (2020), integrando con Actinver (banco grande).
T: Integración API compleja, 2 meses de desarrollo, bugs constantes.
A: Solicité shadowing con operador bancario que usa API. Observé que ellos no usaban endpoint que causaba 80% de nuestros bugs.
   Rediseñamos integración eliminando endpoint problemático.
R: Integración exitosa, adopción +20% por parte de Actinver (era el principal pain point).
```

**Pregunta 2**: Tell me about a time when you gained an important customer insight using your product/service. What was the key insight? How did it influence your next steps?

**Ejemplo**:
```
S: En Kubo Financiero (2019), app de microservicios para préstamos.
T: Usuarios abandonaban en 70% en paso de "verificar ingresos".
A: Analicé logs + entrevisté 5 usuarios → Insight: "Verificar ingresos" pedía subir foto de nómina pero 60% usuarios no tenían nómina digital.
   Implementé opción de "validar manualmente" con llamada telefónica + selfie.
R: Abandono bajó de 70% a 30%, conversión +133%.
```

**Pregunta 3**: Tell me about a time that you championed for a customer to make a change within a business.

**Ejemplo**:
```
S: En Globant (2022), cliente Taulia requería feature X.
T: Feature X compleja, estimado 4 semanas, conflicto con roadmap.
A: Defendí prioridad: 1) Cliente perdiendo $10k/día sin feature 2) Feature X desbloqueaba 2 proyectos más.
   Negocié con PM: retrasar feature Y (internal tool) por feature X.
R: Feature X entregada en 3 semanas, cliente expandió contrato +30%, equipo ganó reputación.
```

---

### Viernes-Domingo: Imagine and Invent Before They Ask

**Pregunta 1**: Tell me about a time you were able to "see around the corner" to meet a customer need, or provide delight, with a solution or product they hadn't yet requested.

**Ejemplo**:
```
S: En gob.mx (2017), plataforma de trámites digitales.
T: Usuarios solicitando certificados de nacimiento → 2 días de proceso, muchos quejas.
A: Noté patrón: 90% certificados de 2010-2017 (nada digital). Implementé: 1) OCR de certificados físicos 2) Auto-poblado de campos 3) Búsqueda avanzada por folio.
   Feature no solicitada, pero anticipé necesidad.
R: Usuarios redujeron tiempo de 2 días a 5 min, quejas -85%, feature destacada en comunicado presidencial.
```

**Pregunta 2**: Tell me about a time you took something that was working "just fine" and you still found a way to improve upon it.

**Ejemplo**:
```
S: En Kubo Financiero (2018), servicio de pagos funcionaba "fine".
T: 500ms de latencia, 99.9% uptime, no complaints.
A: Decidí optimizar aunque nadie lo pidió. Implementé: 1) Redis local cache 2) Lazy loading 3) Async processing.
R: Latencia bajó de 500ms a 425ms (15%), costos AWS -40% por menos DB hits.
   CEO reconoció iniciativa en company-wide meeting.
```

**Pregunta 3**: Tell me about a time you delivered an outcome that "failed" but you deemed the experience a success due to a critical learning that emerged.

**Ejemplo**:
```
S: En Thomson Reuters (2024), desarrollé AI agent para generar tests E2E automáticamente.
T: Objetivo: generar 100 tests, 90% coverage.
A: Implementé con Claude Code + custom pipeline. Resultado: 30 tests, 60% coverage (failed KPI).
   Pero aprendí: 1) Agentes generan tests pero no ejecutan (falta infra) 2) Need domain knowledge injection.
R: Failed en objetivo, pero éxito en aprendizaje: V2 con infra completa alcanzó 95% coverage en 1 semana.
   Documenté learning, hoy lo usan otros 3 equipos.
```

---

### Tareas de la Semana 2

- [ ] Lunes: Practicar First Non-Repeating Character (3 soluciones)
- [ ] Martes: Practicar Smallest K Numbers (3 soluciones)
- [ ] Miércoles: Practicar File Search + OOP design
- [ ] Jueves: Escribir 3 historias STAR para "Be Customer Obsessed"
- [ ] Viernes: Escribir 3 historias STAR para "Imagine and Invent"
- [ ] Sábado: DSA Challenge - 10 problemas en LeetCode (Arrays, Hash Maps)
- [ ] Domingo: Mock interview completa (STAR + Coding 45 min)

---

## 📅 Semana 3: Problem Solving & System Design

### Objetivo
- Dominar problemas de problem solving (Amazon Locker)
- Preparar System Design (Locker system)

### Lunes-Miércoles: Amazon Locker Problem

**Problema**: Find optimal locker for a given package

**Análisis**:

1. **Input**:
   - Package dimensions (width, height, depth)
   - Available lockers (with sizes: S, M, L, XL)

2. **Constraints**:
   - Package debe caber físicamente
   - NO usar solo volumen (W × H × D)
   - Considerar dimensiones individuales + 6 permutaciones
   - Buscar el locker más pequeño que ajuste (optimización)

3. **Common Pitfall**: Calcular solo volumen y asumir que cabe

**Solución 1: Brute Force - Check All Lockers**
```python
def find_locker_brute(package_dims: tuple, available_lockers: list) -> str:
    """
    package_dims: (width, height, depth)
    available_lockers: [{'id': 'L1', 'size': 'L', 'dims': (w, h, d)}, ...]
    """
    pw, ph, pd = package_dims

    for locker in sorted(available_lockers, key=lambda l: l['size']):
        lw, lh, ld = locker['dims']

        # Check 6 permutations
        fits = any([
            pw <= lw and ph <= lh and pd <= ld,  # Original
            pw <= lw and pd <= lh and ph <= ld,  # Flip height/depth
            ph <= lw and pw <= lh and pd <= ld,  # Flip width/height
            ph <= lw and pd <= lh and pw <= ld,  # Rotate 180
            pd <= lw and pw <= lh and ph <= ld,  # Rotate depth/width
            pd <= lw and ph <= lh and pw <= ld,  # Rotate all
        ])

        if fits:
            return locker['id']

    return None  # No locker fits
```
- **Time**: O(n × 6) = O(n) - n lockers
- **Space**: O(1)
- **Cuándo usar**: Simple, pocos lockers (<100)

**Solución 2: Precompute Locker Sizes + Binary Search**
```python
def find_locker_optimized(package_dims: tuple, locker_config: dict) -> str:
    """
    locker_config: {
        'S': {'dims': (w, h, d), 'count': 10},
        'M': {'dims': (w, h, d), 'count': 5},
        'L': {'dims': (w, h, d), 'count': 3},
        'XL': {'dims': (w, h, d), 'count': 1}
    }
    """
    pw, ph, pd = package_dims
    size_order = ['S', 'M', 'L', 'XL']  # Smallest to largest

    for size in size_order:
        config = locker_config[size]
        if config['count'] == 0:
            continue  # No lockers available of this size

        lw, lh, ld = config['dims']

        # Check if fits with permutation
        fits = check_fits((pw, ph, pd), (lw, lh, ld))
        if fits:
            # Decrement count (simulate reservation)
            config['count'] -= 1
            return f"{size}-{config['count'] + 1}"  # Return specific locker ID

    return None

def check_fits(package: tuple, locker: tuple) -> bool:
    pw, ph, pd = package
    lw, lh, ld = locker

    # Check if any permutation fits
    return any([
        pw <= lw and ph <= lh and pd <= ld,
        pw <= lw and pd <= lh and ph <= ld,
        ph <= lw and pw <= lh and pd <= ld,
        ph <= lw and pd <= lh and pw <= ld,
        pd <= lw and pw <= lh and ph <= ld,
        pd <= lw and ph <= lh and pw <= ld,
    ])
```
- **Time**: O(1) - Máximo 4 tamaños × 6 permutaciones = 24 checks
- **Space**: O(1)
- **Ventaja vs brute force**: No depende de número de lockers, solo de tipos (4)
- **Optimización**: Si S no cabe, no check M/L/XL individualmente, buscar siguiente tamaño

**Solución 3: Caching de Package Dimensions**
```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def find_locker_cached(package_dims: tuple, locker_config_hash: int) -> str:
    # locker_config_hash puede ser hash del config actual
    # Cache basado en dimensiones de paquete
    return find_locker_optimized(package_dims, locker_config)

# Uso:
package_dims = (20, 15, 10)  # 20x15x10 cm
locker_id = find_locker_cached(package_dims, config_hash)
```
- **Time**: O(1) después de primer lookup (cache hit)
- **Space**: O(m) - m = número de paquetes únicos (1000 en cache)
- **Ventaja**: Misma dimensión de paquete → respuesta instantánea
- **Trade-off**: Si config cambia (se reservan lockers), invalidar cache

**Trade-offs**:
| Solución | Time | Space | Complexity | When to use |
|----------|-------|--------|-------------|
| Brute Force | O(n) | O(1) | Simple, pocos lockers |
| Size Types | O(1) | O(1) | Config predefinida (S/M/L/XL) |
| Cached | O(1) | O(m) | Alta frecuencia de mismos paquetes |

**Edge Cases**:
- Package más grande que XL → Return None
- Todos lockers ocupados → Return None + sugerir locker más cercano
- Package dims = 0 (invalid input) → Throw exception
- Dimensiones con decimales → Round o handle como float

**Implementación Completa**:
```python
class LockerSystem:
    def __init__(self):
        self.lockers = {
            'S': [Locker(f'S-{i}', (30, 30, 30)) for i in range(10)],
            'M': [Locker(f'M-{i}', (60, 60, 60)) for i in range(5)],
            'L': [Locker(f'L-{i}', (90, 90, 90)) for i in range(3)],
            'XL': [Locker(f'XL-{i}', (120, 120, 120)) for i in range(1)],
        }
        self.reservations = {}  # package_id -> locker_id

    def find_locker(self, package_dims: tuple) -> str:
        for size in ['S', 'M', 'L', 'XL']:
            for locker in self.lockers[size]:
                if not locker.is_reserved() and self._fits(package_dims, locker.dims):
                    locker.reserve()
                    return locker.id
        return None

    def _fits(self, package: tuple, locker: tuple) -> bool:
        pw, ph, pd = package
        lw, lh, ld = locker
        return any([
            pw <= lw and ph <= lh and pd <= ld,
            pw <= lw and pd <= lh and ph <= ld,
            ph <= lw and pw <= lh and pd <= ld,
            ph <= lw and pd <= lh and pw <= ld,
            pd <= lw and pw <= lh and ph <= ld,
            pd <= lw and ph <= lh and pw <= ld,
        ])

class Locker:
    def __init__(self, locker_id: str, dims: tuple):
        self.id = locker_id
        self.dims = dims  # (width, height, depth)
        self.reserved = False

    def is_reserved(self) -> bool:
        return self.reserved

    def reserve(self):
        self.reserved = True
```

---

### Jueves-Viernes: System Design - Amazon Locker System

**Requisitos Funcionales**:
1. Customers pueden elegir locker location para delivery
2. Customers pueden devolver items a locker
3. Access code non-renewable para reservación
4. Amazon Delivery personnel puede acceder a lockers

**Requisitos No-Funcionales**:
1. Customer promised locker - no se puede revocar
2. Escalable basado en demanda
3. Access codes no fácilmente adivinables
4. Optimizar idle time cuando hay reservaciones pendientes

**Requisitos Adicionales**:
1. Track packages (ordered/returned)
2. Reservaciones pueden expirar (no-show)
3. Reservaciones para mañana aunque hoy esté reservado con expiración

---

### Arquitectura Propuesta

```
┌─────────────────────────────────────────────────────────────┐
│                     Customer (Web/Mobile)                │
└─────────────────────────┬───────────────────────────────────┘
                      │ HTTPS
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   API Gateway (Amazon)                  │
│  - Authentication (Cognito)                            │
│  - Rate limiting                                       │
│  - Request routing                                     │
└──────────┬────────────────────────┬───────────────────────┘
           │                        │
           ▼                        ▼
┌─────────────────────┐  ┌─────────────────────┐
│  Locker Service    │  │  Order Service     │
│  - Find locker     │  │  - Order status   │
│  - Reserve locker  │  │  - Package info   │
│  - Release locker  │  └─────────────────────┘
│  - Access codes   │
└─────────┬─────────┘
          │
    ┌─────┴─────┬─────────────┐
    │             │             │
    ▼             ▼             ▼
┌──────────┐ ┌──────────┐ ┌──────────┐
│  Locker  │ │  Locker  │ │  Locker  │
│   Pod 1  │ │   Pod 2  │ │   Pod N  │
│  IoT HW  │ │  IoT HW  │ │  IoT HW  │
└──────────┘ └──────────┘ └──────────┘
     │             │             │
     ▼             ▼             ▼
┌──────────────────────────────────────────────┐
│           Database (RDS PostgreSQL)         │
│  - lockers (id, location, size, state)  │
│  - reservations (id, locker_id, user_id, │
│                   code, expiry)           │
│  - packages (id, tracking, locker_id)   │
└──────────────────────────────────────────────┘
          │
          ▼
┌──────────────────────────────────────────────┐
│      Notification Service (SNS)          │
│  - Email notifications                   │
│  - SMS notifications                   │
│  - Push notifications                  │
└──────────────────────────────────────────────┘
```

---

### Componentes del Sistema

#### 1. Locker Service (Core)

**API Endpoints**:
```
POST   /api/v1/lockers/search
       Body: {location: "Mexico City", dimensions: {w,h,d}}
       Response: {available_lockers: [{id, distance}]}
       Returns lockers disponibles ordenados por ubicación

POST   /api/v1/lockers/reserve
       Body: {locker_id, user_id, package_id}
       Response: {reservation_id, access_code, expiry}
       Two-phase commit: Pre-reserva → Confirmación

POST   /api/v1/lockers/release
       Body: {reservation_id, code}
       Response: {status: "released"}
       Libera locker después de pickup

GET    /api/v1/lockers/{id}/status
       Response: {state: "available|reserved|occupied"}
       Estado actual del locker
```

**Locker States**:
```
AVAILABLE → RESERVED (customer reserved) → OCCUPIED (package dropped off)
                                                ↓
                                         RELEASED (customer picked up)
                                                ↓
                                           AVAILABLE
```

#### 2. Database Schema

```sql
CREATE TABLE lockers (
    id VARCHAR(36) PRIMARY KEY,
    location_id VARCHAR(36) REFERENCES locations(id),
    size VARCHAR(10) CHECK (size IN ('S', 'M', 'L', 'XL')),
    state VARCHAR(20) CHECK (state IN ('AVAILABLE', 'RESERVED', 'OCCUPIED', 'MAINTENANCE')),
    dimensions JSONB, -- {width, height, depth}
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_lockers_location ON lockers(location_id);
CREATE INDEX idx_lockers_state ON lockers(state);

CREATE TABLE reservations (
    id VARCHAR(36) PRIMARY KEY,
    locker_id VARCHAR(36) REFERENCES lockers(id),
    user_id VARCHAR(36) REFERENCES users(id),
    package_id VARCHAR(36) REFERENCES packages(id),
    access_code VARCHAR(10) UNIQUE, -- Random alphanumeric
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expiry TIMESTAMP NOT NULL,
    status VARCHAR(20) CHECK (status IN ('ACTIVE', 'COMPLETED', 'EXPIRED'))
);

CREATE INDEX idx_reservations_locker ON reservations(locker_id);
CREATE INDEX idx_reservations_expiry ON reservations(expiry);
CREATE INDEX idx_reservations_user ON reservations(user_id);

CREATE TABLE packages (
    id VARCHAR(36) PRIMARY KEY,
    tracking_number VARCHAR(50) UNIQUE,
    locker_id VARCHAR(36) REFERENCES lockers(id),
    status VARCHAR(20) CHECK (status IN ('DELIVERING', 'DELIVERED', 'PICKED_UP')),
    dimensions JSONB,
    weight NUMERIC,
    delivered_at TIMESTAMP
);
```

#### 3. Access Code Generation

**Requisito**: No fácilmente adivinables

**Algoritmo**:
```python
import secrets
import string

def generate_access_code() -> str:
    # 8 caracteres alfanuméricos
    # Entropy: 62^8 = 218 trillion combinaciones
    alphabet = string.ascii_uppercase + string.digits
    code = ''.join(secrets.choice(alphabet) for _ in range(8))

    # Validar que no exista en DB
    if code_exists_in_db(code):
        return generate_access_code()  # Retry

    return code
```

- **Entropy**: 62^8 = 2.18 × 10^14 combinaciones
- **Seguridad**: 1 en 218 trillones de adivinar
- **Expire**: 24 horas después de generar

#### 4. Reservation Flow (Two-Phase Commit)

**Fase 1: Pre-reserva** (Customer al hacer pedido)
```
POST /api/v1/lockers/reserve

Request:
{
  "locker_id": "L-123",
  "user_id": "user-456",
  "package_id": "pkg-789",
  "duration_hours": 24
}

Response:
{
  "reservation_id": "res-001",
  "status": "PENDING",
  "expires_at": "2026-04-08T09:00:00Z"
}

DB:
  reservations.status = "PENDING"
  reservations.expiry = now() + 24 hours
```

**Fase 2: Confirmación** (Amazon entrega paquete)
```
POST /api/v1/lockers/confirm

Request:
{
  "reservation_id": "res-001",
  "driver_id": "driver-123"
}

Response:
{
  "access_code": "A7X3K2M9",
  "locker_id": "L-123",
  "expiry": "2026-04-09T09:00:00Z"
}

DB:
  reservations.status = "ACTIVE"
  reservations.access_code = "A7X3K2M9"
  lockers.state = "OCCUPIED"
```

**Fase 3: Pickup** (Customer recibe paquete)
```
POST /api/v1/lockers/release

Request:
{
  "reservation_id": "res-001",
  "access_code": "A7X3K2M9"
}

Response:
{
  "status": "RELEASED",
  "locker_id": "L-123"
}

DB:
  reservations.status = "COMPLETED"
  lockers.state = "AVAILABLE"
```

---

### Manejo de Contención (Contention)

**Problema**: Múltiples customers intentan reservar mismo locker

**Solución**: Distributed Lock con Redis
```python
import redis
import json

redis_client = redis.Redis(host='localhost', port=6379)

def reserve_locker(locker_id: str, user_id: str) -> dict:
    # Intentar adquirir lock con TTL de 5 segundos
    lock_key = f"lock:locker:{locker_id}"
    acquired = redis_client.set(lock_key, user_id, nx=True, ex=5)

    if not acquired:
        return {"status": "CONFLICT", "message": "Locker being reserved by another user"}

    # Check si está disponible
    locker_state = get_locker_state(locker_id)
    if locker_state != "AVAILABLE":
        redis_client.delete(lock_key)  # Release lock
        return {"status": "NOT_AVAILABLE", "message": "Locker not available"}

    # Reservar
    create_reservation(locker_id, user_id)
    redis_client.delete(lock_key)  # Release lock

    return {"status": "SUCCESS", "reservation_id": generate_id()}
```

**Alternativa**: Two-Phase Lock (2PL) en DB
```sql
BEGIN;

-- Fase 1: Lock
SELECT id, state FROM lockers WHERE id = 'L-123' FOR UPDATE;

-- Check si está AVAILABLE
-- Si no, ROLLBACK y retornar error

-- Fase 2: Reserve
INSERT INTO reservations (locker_id, user_id, ...) VALUES ('L-123', 'user-456', ...);
UPDATE lockers SET state = 'RESERVED' WHERE id = 'L-123';

COMMIT;
```

---

### Optimización de Idle Time

**Problema**: Lockers idle mientras hay demandas pendientes

**Estrategias**:

1. **Shorter reservation durations**
   - Default: 24 horas
   - Si hay demanda: 12 horas
   - Configurable por location (urban = 12h, rural = 48h)

2. **No-show release**
   - Si customer no pickup en 24h → auto-release
   - Notificación 2h antes de expiración
   - Notificación en expiración

3. **Dynamic sizing**
   - Monitorear demanda por location
   - Si 80% lockers occupied → Agregar lockers temporales (trailers)
   - Si 30% lockers occupied → Reducir tamaño

4. **Predictive allocation**
   - ML para predecir demanda por hora/día
   - Pre-reservar lockers para slots de alta demanda
   - Liberar lockers en baja demanda

---

### Escalabilidad

**Nivel 1: Single Region (CDMX)**
- 100 lockers pods
- 1 DB (RDS Multi-AZ)
- 1 API Gateway

**Nivel 2: Multiple Regions**
- 100 lockers por region (CDMX, MTY, GDL)
- Regional APIs (latency <50ms)
- Global API Gateway con geo-routing

**Nivel 3: Hyper-scale (US-wide)**
- Sharding por region
- Read replicas por alta demanda
- CDN para assets de locker locations

**Scaling Strategies**:

| Componente | Estrategia | Scaling Trigger |
|-------------|-------------|------------------|
| API Gateway | Auto-scaling group | CPU >70% por 5 min |
| Locker Service | Horizontal scaling | Requests/sec >1000 |
| Database | Read replicas + sharding | Connections >1000 |
| Locker Pods | Manual (physical) | Demand forecast |

---

### APIs Principales

#### Locker Service

```
# Buscar lockers disponibles
GET /api/v1/lockers/available?location=CDMX&lat=19.43&lng=-99.13&package_id=pkg-123
Response:
{
  "lockers": [
    {
      "id": "L-001",
      "location": "Polanco",
      "distance_km": 2.3,
      "size": "L",
      "dimensions": {"width": 90, "height": 90, "depth": 90},
      "available_until": "2026-04-08T18:00:00Z"
    }
  ]
}

# Reservar locker
POST /api/v1/lockers/reserve
Request:
{
  "locker_id": "L-001",
  "user_id": "user-456",
  "package_id": "pkg-789",
  "duration_hours": 24
}
Response:
{
  "reservation_id": "res-001",
  "access_code": "A7X3K2M9",
  "expiry": "2026-04-09T09:00:00Z",
  "qr_code": "data:image/png;base64,..."
}

# Confirmar reservación (Amazon driver)
POST /api/v1/lockers/confirm
Request:
{
  "reservation_id": "res-001",
  "driver_id": "driver-123"
}

# Pickup (customer)
POST /api/v1/lockers/release
Request:
{
  "reservation_id": "res-001",
  "access_code": "A7X3K2M9"
}
Response:
{
  "status": "SUCCESS",
  "message": "Locker L-001 opened"
}
```

#### Order Service

```
# Crear orden con locker delivery
POST /api/v1/orders
Request:
{
  "user_id": "user-456",
  "items": [...],
  "delivery_method": "LOCKER",
  "locker_id": "L-001"
}
Response:
{
  "order_id": "ord-123",
  "status": "PROCESSING",
  "delivery_estimated": "2026-04-08T14:00:00Z"
}

# Obtener access code (para customer)
GET /api/v1/orders/{order_id}/access
Response:
{
  "access_code": "A7X3K2M9",
  "locker_id": "L-001",
  "location": "Polanco",
  "expiry": "2026-04-09T09:00:00Z"
}
```

---

### Trade-offs a Mencionar

| Decisión | Opción A | Opción B | Trade-off |
|-----------|-----------|-----------|------------|
| DB | SQL (PostgreSQL) | NoSQL (DynamoDB) | SQL = ACID, joins / NoSQL = scale, eventual consistency |
| Auth | Locks (2PL) | Redis | Locks = fuerte / Redis = rápido pero eventual consistency |
| Delivery | Push (fan-out) | Pull | Push = reads rápidas / Pull = escalable para celebrities |
| Reservation | Two-phase | Directo | Two-phase = fuerte / Directo = simple pero race conditions |
| No-show | Auto-release | Manual | Auto = optimiza lockers / Manual = customer control |

---

### Tareas de la Semana 3

- [ ] Lunes: Implementar Amazon Locker (3 soluciones)
- [ ] Martes: Diseñar arquitectura de Locker System
- [ ] Miércoles: Diseñar DB schema + APIs
- [ ] Jueves: Implementar manejo de contención + locks
- [ ] Viernes: Documentar trade-offs + escalabilidad
- [ ] Sábado: Mock System Design (whiteboard 30 min)
- [ ] Domingo: Review + memorizar diagramas

---

## 📅 Semana 4: Logical Coding & Final Prep

### Objetivo
- Dominar coding lógico y mantenible
- Revisión final + practice intensiva

### Lunes-Miércoles: Logical & Maintainable Coding

**Principios**:
1. **Code readability** > Cleverness
2. **Error handling** explícito
3. **Single responsibility**
4. **DRY** (Don't Repeat Yourself)
5. **SOLID principles**

**Ejemplo: Employee Directory Tree Filter**
(De guía original - ya cubierto)

**Code Review Checklist**:
- [ ] Nombres descriptivos de variables y funciones
- [ ] Funciones pequeñas (<20 líneas)
- [ ] Error handling específico (no try/except genérico)
- [ ] Comments solo para "por qué", no "qué"
- [ ] Type hints (si aplica)
- [ ] Unit tests para edge cases

---

### Jueves-Domingo: Final Prep

**Jueves**: Mock Interview Completa
- 30 min: STAR stories (randomly seleccionadas)
- 30 min: Coding (problema sorpresa)
- Feedback recording + areas de mejora

**Viernes**: Weak Areas Focus
- Identificar 3 áreas débiles
- Practice intensiva (4 horas)
- Ej: Si weak en trees → 10 problemas de trees en LeetCode

**Sábado**: Full Simulation
- Simular día de entrevista completa:
  - 9:00 AM: Interview 1 (Matt/Kshitij) - DSA + Articulate
  - 10:30 AM: Interview 2 (Alfonso) - Problem Solving + Customer Obsessed
  - 12:00 PM: Lunch break
  - 1:00 PM: Interview 3 (Chaitra) - System Design + Culture/Caring
  - 2:30 PM: Interview 4 (Poorva) - Logical + Imagine
- Grabar simulación
- Self-evaluation

**Domingo**: Rest + Light Review
- Revisar STAR stories (all 18)
- Revisar soluciones de coding (all 5 problems)
- Visualizar éxito en entrevista
- Early sleep (rested mind)

---

## 🎯 Tips de Entrevista

### Antes de la Entrevista

**1. Research**:
- Audible products (audiobooks, podcasts, original content)
- Audible tech stack (AWS, Java, microservices, data-driven)
- Interviewers (LinkedIn) - backgrounds, interests

**2. Prepare STAR Stories**:
- 18 historias memorizadas (3 por principio)
- Practicar aloud (cada <2 min)
- Grabar y escuchar (ajustar timing)

**3. Coding Practice**:
- 50 problems en LeetCode (Arrays, Hash Maps, Trees, Heaps)
- Implementar soluciones sin IDE (paper + whiteboard)
- Timeboxed practice (30 min/problem)

**4. System Design**:
- Memorizar diagramas (Locker, Feed, etc.)
- Practice whiteboard (drawing + explaining)
- Focus en trade-offs y scalability

---

### Durante la Entrevista

**Behaviorals (STAR)**:

1. **Clarify question first**
   - "Can you give me an example of X?"
   - "Let me make sure I understand: you're asking about..."

2. **Structure response (STAR)**
   - S: "In my role at [Company] in [Year]..."
   - T: "I was responsible for..."
   - A: "I specifically did: 1)... 2)... 3)..."
   - R: "The result was: [metric]"

3. **Be specific**
   - Instead of "improved performance", say "reduced latency by 15%"
   - Instead of "team liked it", say "team adopted in 3 other services"

4. **Own the outcome**
   - Use "I did" instead of "we did" (for YOUR actions)
   - "I led", "I implemented", "I drove"

**Coding**:

1. **Clarify constraints first**
   - "Can I assume input is always valid?"
   - "Should I handle edge cases like empty input?"
   - "Time and space constraints?"

2. **State approach before coding**
   - "I'll use a HashMap for O(n) time complexity"
   - "Brute force would be O(n²), but I can optimize with..."

3. **Write clean code**
   - Meaningful variable names (not `i`, `j`, `k` unless loops)
   - Functions with single responsibility
   - Error handling explicit

4. **Talk while coding**
   - "I'm iterating through the array to build frequency count"
   - "Now I'll find the first character with count = 1"

5. **Test with example**
   - Walk through code with sample input
   - "For input 'aabcc', this gives us..."

6. **Proactively mention trade-offs**
   - "HashMap gives O(n) time but O(n) space"
   - "For small inputs, brute force might be simpler"

**System Design**:

1. **Clarify requirements first**
   - "Is this for a single region or global?"
   - "What's the expected scale? 100 users or 1 million?"
   - "What are the key constraints? Latency, consistency, availability?"

2. **Draw high-level architecture**
   - Boxes for services (API, Database, Cache)
   - Arrows for data flow
   - Labels for technologies (PostgreSQL, Redis, Kafka)

3. **Deep dive into critical components**
   - Pick 2-3 components to explain in detail
   - Database schema, API design, caching strategy

4. **Address trade-offs**
   - "SQL gives ACID but NoSQL scales better"
   - "Push model gives fast reads but expensive for celebrities"
   - "Here I chose SQL for strong consistency requirements"

5. **Talk about scalability**
   - "With 1000 users, this works fine. At 1M, we'd need..."
   - "We can shard by region to reduce contention"
   - "Read replicas would help with read-heavy workloads"

---

### Después de la Entrevista

**1. Send thank you email** (dentro de 24 horas)
```
Subject: Thank you - [Position Name] Interview

Dear [Interviewer Name],

Thank you for the opportunity to interview for [Position].
I enjoyed our discussion about [specific topic discussed].

I'm particularly excited about [specific aspect of role/team/company]
and believe my experience with [relevant skill] would allow me to contribute.

I look forward to hearing about next steps.

Best regards,
Alejandro Hernandez Loza
alejandrohloza@gmail.com
LinkedIn: https://www.linkedin.com/in/alejandro-hernandez-loza/
```

**2. Reflection** (mismo día)
- Qué preguntas respondí bien? (STAR stories que fluideron)
- Qué preguntas me costaron? (Practice más)
- Qué problemas de coding fallé? (Implementar de nuevo)
- Qué conceptos de system design no cubrí? (Read + practice)

**3. Follow-up** (si no respuesta en 7 días)
```
Subject: Follow-up - [Position Name] Interview

Hi [Interviewer Name],

I hope you're doing well.

I wanted to follow up on my interview for [Position] last week.
I'm still very interested in the opportunity and excited about [specific aspect].

Please let me know if you need any additional information.

Best regards,
Alejandro
```

---

## 📚 Recursos de Estudio

### Coding Practice

**LeetCode** (Problemas específicos):
1. **Arrays + Hash Maps**
   - Two Sum
   - First Unique Character in Stream
   - Top K Frequent Elements
   - Group Anagrams

2. **Heaps**
   - Kth Largest Element
   - Merge K Sorted Lists
   - Find Median from Data Stream

3. **Trees**
   - Binary Tree Inorder Traversal
   - Validate BST
   - Lowest Common Ancestor

**Practice Schedule**:
- 5 problemas/día (30 min cada uno)
- Total: 140 problemas en 4 semanas
- Focus: Arrays, Hash Maps, Heaps, Trees

### System Design Resources

**Books**:
- "Designing Data-Intensive Applications" (Martin Kleppmann)
- "System Design Interview" (Alex Xu)

**Videos**:
- System Design Primer (YouTube - TechLead)
- Scalability lectures (YouTube - Gaurav Sen)

**Practice**:
- Design 2 systems/semana desde cero
- Practice whiteboard drawing + explaining
- Focus: Trade-offs + Scalability

### Behavioral Resources

**Amazon Leadership Principles**:
- Read all 16 principles
- Prepare 2-3 stories per principle
- Practice aloud with timer

**STAR Framework**:
- Situation → Context (quándo, dónde, quién)
- Task → Tu responsabilidad específica
- Action → Qué hiciste TÚ (no "we did")
- Result → Resultado medible (números, %)

---

## 📊 Checklist de Preparación

### Semana 1
- [ ] 3 STAR stories - Articulate The Possible
- [ ] 3 STAR stories - Study and Draw Inspiration
- [ ] 3 STAR stories - Activate Caring
- [ ] Practice STAR aloud (all 9 stories)
- [ ] DSA basics: Arrays, Hash Maps, Trees
- [ ] 10 LeetCode problems

### Semana 2
- [ ] Practice: First Non-Repeating Character (3 solutions)
- [ ] Practice: Smallest K Numbers (3 solutions)
- [ ] Practice: File Search (OOP design)
- [ ] 3 STAR stories - Be Customer Obsessed
- [ ] 3 STAR stories - Imagine and Invent
- [ ] 15 LeetCode problems
- [ ] Mock interview (45 min)

### Semana 3
- [ ] Practice: Amazon Locker (3 solutions)
- [ ] Design: Locker System (architecture + DB + APIs)
- [ ] Document trade-offs + scalability
- [ ] Practice whiteboard drawing
- [ ] 10 LeetCode problems
- [ ] Mock System Design (30 min)

### Semana 4
- [ ] Review coding principles (SOLID, DRY, Clean Code)
- [ ] Mock full interview (4 sessions)
- [ ] Weak areas focus (4 hours practice)
- [ ] Full simulation (day-long)
- [ ] Final review (STAR stories + coding solutions)

### Día Antes de Entrevista
- [ ] Research Audible products + tech stack
- [ ] Research interviewers (LinkedIn)
- [ ] Restful sleep (8+ hours)
- [ ] Early arrival (15 min before)
- [ ] Have water, notebook, pen ready
- [ ] STAR stories memorized (all 18)
- [ ] Coding solutions reviewed (all 5 problems)
- [ ] System design diagrams memorized

---

## 🎓 Notas de Entrevistadores

| Entrevistador | Empresa Background | Tips |
|---------------|-------------------|-------|
| Matt Love & Kshitij Shah | Amazon/Audible Technical | Expect DSA depth, articulate clearly |
| Alfonso López López | Amazon/Audible Engineering | Problem solving, customer focus |
| Chaitra Ramdas | Amazon/Audible Product/Tech | System design + culture fit |
| Poorva Karunakaran | Amazon/Audible Leadership | Logical thinking, innovation |

---

## 🚨 Common Pitfalls to Avoid

### Behaviorals
1. **Being vague** → Instead of "improved performance", say "reduced latency by 15%"
2. **Using "we" instead of "I"** → Own YOUR specific actions
3. **Too long** → Keep stories <2 min each
4. **No result** → Always end with measurable outcome

### Coding
1. **Jumping to code without clarifying** → Ask constraints first
2. **Not stating approach** → Explain complexity before coding
3. **Silent coding** → Talk through your thought process
4. **Ignoring edge cases** → Handle empty input, nulls, boundaries
5. **No testing** → Walk through example with your code

### System Design
1. **Not clarifying requirements** → Ask scale, constraints, features
2. **Over-complicating** → Start simple, add complexity as needed
3. **Ignoring trade-offs** → Always discuss pros/cons
4. **Not addressing scalability** → Mention how it scales from 100 to 1M users
5. **Poor drawing** → Clear boxes, labels, arrows

---

## 💪 Mindset Preparation

### Positivity
- "I prepared thoroughly. I'm ready to show my best."
- "Even if I make a mistake, I learn and recover."
- "This is a conversation, not an interrogation."

### Confidence
- "I have 12+ years of experience solving complex problems."
- "I've delivered results at Thomson Reuters, Globant, Kubo."
- "I can explain my decisions clearly and stand by them."

### Resilience
- "If I get stuck, I'll ask clarifying questions."
- "If I can't solve a coding problem, I'll explain my thinking."
- "If I don't know something, I'll say 'I'm not sure, but here's my approach'."

---

## 🎯 Success Criteria

**Interview exit criteria** (self-assessment):
- [ ] All STAR stories delivered clearly, concisely (<2 min each)
- [ ] All coding problems solved with O(n) or O(n log n) optimal solution
- [ ] System design explained with trade-offs + scalability
- [ ] Asked clarifying questions before answering
- [ ] Stated approach/time complexity before coding
- [ ] Tested code with example input
- [ ] Proactively mentioned trade-offs

**Post-interview criteria**:
- [ ] Sent thank you email within 24 hours
- [ ] Reflected on what went well/poorly
- [ ] Practiced weak areas immediately
- [ ] Followed up after 7 days if no response

---

**Plan creado**: 2026-04-07
**Autor**: Alejandro Hernandez Loza
**Estado**: Ready to execute

**¡Buena suerte en la entrevista! 🎧🚀**
