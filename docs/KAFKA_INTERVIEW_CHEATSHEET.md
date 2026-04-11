# Kafka Interview Cheat Sheet — Senior Java/AWS

---

## 1. Fundamentos

| Concepto | Definicion |
|---|---|
| **Broker** | Servidor de Kafka. Almacena particiones, recibe y sirve mensajes |
| **Topic** | Canal logico de mensajes (como una tabla) |
| **Partition** | Unidad de paralelismo dentro de un topic. Log ordenado e inmutable |
| **Offset** | Numero secuencial de cada mensaje dentro de una particion |
| **Producer** | Publica mensajes a un topic |
| **Consumer** | Lee mensajes de particiones |
| **Consumer Group** | Grupo de consumers que se reparten particiones |
| **ZooKeeper/KRaft** | Metadata y leader election (KRaft reemplaza ZK desde Kafka 3.3+) |

### Kafka vs RabbitMQ

| | Kafka | RabbitMQ |
|---|---|---|
| Modelo | Log inmutable (mensajes persisten) | Cola (mensaje se borra al consumir) |
| Throughput | ~1M msgs/seg | ~50K msgs/seg |
| Replay | Si, desde cualquier offset | No, una vez consumido se fue |
| Multi-consumer | Si, cada consumer group lee todo | Competing consumers (1 msg → 1 consumer) |
| Usar cuando | Event streaming, alto volumen, multiples consumers | Tareas async simples, routing complejo |

---

## 2. Particiones y Ordering

- Orden garantizado **solo dentro de una particion**
- Sin key → round-robin entre particiones (orden NO garantizado)
- Con key → `hash(key) % particiones` → siempre la misma particion

```java
// MAL: sin key, orden perdido
kafka.send("orders", orderEvent);

// BIEN: key=userId, eventos del mismo user en orden
kafka.send("orders", userId, orderEvent);
```

### Consumer Group + Particiones

```
4 particiones, 2 consumers → cada consumer toma 2
4 particiones, 4 consumers → cada consumer toma 1
4 particiones, 6 consumers → 4 activos, 2 idle
```

- Regla: `consumers <= particiones`
- Redistribucion = **rebalanceo** (stop-the-world, 1-30 seg)
- Solucion: Cooperative Sticky Assignor (Kafka 2.4+)

---

## 3. Delivery Semantics

| Semantica | Commit del offset | Riesgo |
|---|---|---|
| **At-most-once** | ANTES de procesar | Pierdes mensajes |
| **At-least-once** | DESPUES de procesar | Duplicados |
| **Exactly-once** | Transaccion atomica | Ninguno, pero mas lento |

### At-least-once + Idempotencia (patron mas comun en produccion)

```sql
-- Consumer idempotente: ignora duplicados
INSERT INTO orders (order_id, amount, status)
VALUES (123, 500, 'PAID')
ON CONFLICT (order_id) DO NOTHING;
```

### Exactly-once (transacciones financieras)

```java
producer.initTransactions();
producer.beginTransaction();
producer.send(record);
producer.sendOffsetsToTransaction(offsets, groupId);
producer.commitTransaction();
```

---

## 4. Replication y Fault Tolerance

| Parametro | Valor seguro | Significado |
|---|---|---|
| `replication.factor` | 3 | 3 copias de cada particion en brokers distintos |
| `min.insync.replicas` | 2 | Minimo 2 brokers deben confirmar escritura |
| `acks` | all | Producer espera confirmacion de todos los ISR |

```
3 brokers, replication.factor=3, min.insync.replicas=2:
  → 1 broker cae: sigue funcionando (2 >= 2) ✅
  → 2 brokers caen: rechaza escrituras (1 < 2) ❌ pero no pierde datos
```

- **ISR** (In-Sync Replicas): replicas al dia con el lider
- Si el lider cae, un ISR es elegido nuevo lider
- Preferir no-disponibilidad a perdida de datos en sistemas financieros

---

## 5. Consumer Lag

**Definicion**: diferencia entre ultimo mensaje producido y ultimo consumido.

```
Offset producido: 10,000
Offset consumido:  7,000
Lag: 3,000 mensajes pendientes
```

### Causas comunes

| Causa | Solucion |
|---|---|
| Consumer lento (logica pesada) | Separar logica a otro topic (async) |
| Consumer caido/rebalanceo | Reiniciar, verificar health checks |
| Pocas particiones | Agregar particiones + consumers |

### Diagnostico

```bash
kafka-consumer-groups.sh --describe --group my-service
# Muestra: particion, offset actual, lag por particion
```

---

## 6. Retry + Dead Letter Topic (Spring Boot)

```java
@RetryableTopic(
    attempts = "4",             // 1 original + 3 retries
    backoff = @Backoff(delay = 1000, multiplier = 2.0)
)
@KafkaListener(topics = "payments", groupId = "payment-service")
public void process(PaymentEvent event) {
    paymentGateway.charge(event);  // si lanza excepcion, reintenta
}

@DltHandler
public void handleDlt(PaymentEvent event) {
    log.error("Fallo despues de 3 retries: {}", event);
    failedPaymentRepo.save(event);  // guardar para revision manual
}
```

```
payments → falla → payments-retry-0 → falla → payments-retry-1 → falla → payments-dlt
                   (1 seg)                     (2 seg)                     (revision manual)
```

- `@RetryableTopic`: retry en topics separados (no bloquea particion)
- `DefaultErrorHandler`: retry en memoria (bloquea particion durante retry)

---

## 7. Kafka Connect + CDC

Mover datos entre Kafka y sistemas externos **sin codigo**.

| Tipo | Direccion | Ejemplo |
|---|---|---|
| **Source** | DB → Kafka | Debezium (Postgres → Kafka) |
| **Sink** | Kafka → DB | Elasticsearch Sink (Kafka → Elastic) |

### Debezium CDC

Lee el WAL (Write-Ahead Log) de la DB y publica cada cambio como mensaje:

```
INSERT orders → {op: "c", id: 1, amount: 500}    ← create
UPDATE orders → {op: "u", id: 1, status: "PAID"}  ← update
DELETE orders → {op: "d", id: 1}                   ← delete
```

- No modifica la app, opera a nivel DB
- Configuracion via JSON (connector config)
- Patron estandar para sincronizar microservicios

---

## 8. Schema Registry

Valida que los mensajes tengan el formato correcto (Avro/JSON Schema/Protobuf).

### Problema que resuelve

```
Producer V1: {"orderId": 123, "amount": 500.00}
Producer V2: {"order_id": 123, "total": 500.00}  ← rompe consumers
```

### Como funciona

```
Producer → registra schema en Registry → si es compatible → envia mensaje
                                        → si NO es compatible → RECHAZA
```

### Compatibilidad

| Modo | Que permite | Que bloquea |
|---|---|---|
| BACKWARD | Borrar campos, agregar opcionales | Agregar campos requeridos |
| FORWARD | Agregar campos | Borrar campos |
| FULL | Agregar/borrar solo opcionales | Cambios breaking |

### Respuesta de entrevista

> "Uso Schema Registry con Avro y compatibilidad BACKWARD. El producer registra su schema antes de enviar. Si el cambio rompe compatibilidad con los consumers existentes, el Registry lo rechaza y el deploy falla antes de causar daño en produccion."

---

## 9. Kafka en AWS

| Servicio | Que es |
|---|---|
| **Amazon MSK** | Kafka managed (brokers, ZK gestionados por AWS) |
| **MSK Serverless** | Kafka sin provisionar brokers (pago por uso) |
| **MSK Connect** | Kafka Connect managed (conectores sin infra) |
| **SQS** | Cola simple, no es Kafka (no replay, no consumer groups) |
| **Kinesis** | Similar a Kafka pero propietario AWS, menos flexible |
| **EventBridge** | Event bus para integraciones AWS-to-AWS |

### MSK vs Kinesis

| | MSK | Kinesis |
|---|---|---|
| Protocolo | Kafka nativo | API propietaria AWS |
| Retencion | Ilimitada | 7 dias max (365 con long-term) |
| Tamaño msg | 1MB default (configurable) | 1MB fijo |
| Ecosistema | Kafka Connect, Schema Registry, ksqlDB | Limitado a AWS |
| Migracion | Facil desde Kafka on-prem | Lock-in AWS |

---

## 10. Patrones de Arquitectura (nivel Sr.)

### Event Sourcing

```
Topic: account-events
  {type: "CREATED", accountId: 123}
  {type: "DEPOSITED", amount: 500}
  {type: "WITHDRAWN", amount: 200}
  Estado actual = replay de todos los eventos
```

### CQRS

```
Write → API → Kafka → Consumer → Read DB (optimizada para queries)
Read  → API → Read DB directamente
```

### Saga Pattern

```
order-topic → payment-topic → inventory-topic → shipping-topic
         ← compensation events si algo falla ←
```

---

## Respuestas rapidas para entrevista

| Pregunta | Respuesta corta |
|---|---|
| ¿Como garantizas orden? | Message key → misma particion |
| ¿Como evitas duplicados? | Consumer idempotente (UPSERT/ON CONFLICT) |
| ¿Config para no perder datos? | replication.factor=3, min.insync.replicas=2, acks=all |
| ¿Consumer lag alto? | Verificar consumers vivos, escalar particiones+consumers, separar logica pesada |
| ¿Retry en Spring Boot? | @RetryableTopic + @DltHandler |
| ¿Sincronizar DB con Kafka? | Kafka Connect + Debezium CDC |
| ¿Prevenir schemas rotos? | Schema Registry con compatibilidad BACKWARD |
| ¿Kafka en AWS? | Amazon MSK (managed Kafka) |
| ¿Kafka vs RabbitMQ? | Kafka=streaming/replay/multi-consumer, Rabbit=tareas async simples |
| ¿Kafka vs Kinesis? | Kafka=open/portable, Kinesis=AWS-only/lock-in |
