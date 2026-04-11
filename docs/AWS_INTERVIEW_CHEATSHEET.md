# AWS Interview Cheat Sheet — Senior Java/Spring Boot

---

## 1. Compute — Donde corre tu codigo

| Servicio | Que es | Cuando usarlo |
|---|---|---|
| **EC2** | Maquina virtual (tu la administras) | Control total, apps legacy, DBs custom |
| **ECS Fargate** | Containers sin administrar servidores | Microservicios en Docker (el mas comun hoy) |
| **EKS** | Kubernetes managed | Si ya usas Kubernetes |
| **Lambda** | Funcion que se ejecuta por evento | Trafico variable, funciones cortas (<15 min) |

### ECS Fargate vs Lambda

| | ECS Fargate | Lambda |
|---|---|---|
| Modelo | Container siempre corriendo | Se ejecuta solo cuando hay evento |
| Costo | Pagas 24/7 (aunque no haya trafico) | Pagas solo por ejecucion |
| Cold start | No (container ya esta listo) | Si (~1-3 seg en Java) |
| Duracion max | Sin limite | 15 minutos |
| Memoria max | 30 GB | 10 GB |
| Usar cuando | APIs con trafico constante | Eventos esporadicos, procesamiento corto |

### Lambda — respuesta de entrevista

> "Elijo Lambda para un servicio de notificaciones con trafico de 0-500/min porque: (1) solo pago cuando hay eventos, (2) escala automaticamente a miles de invocaciones concurrentes, (3) la logica es simple (enviar email + guardar log, <1 seg). La desventaja es el cold start de Java (~1-3 seg en primera invocacion), que mitigo con SnapStart o Provisioned Concurrency."

---

## 2. Networking y Seguridad

### VPC (Virtual Private Cloud)

Tu red privada en AWS. Todo vive dentro de una VPC.

```
Internet
    ↓
┌─────────────────────────────────────────┐
│  VPC (10.0.0.0/16)                      │
│                                         │
│  Subnet PUBLICA      Subnet PRIVADA     │
│  (ALB, bastion)      (ECS, RDS)         │
│       ↑                                 │
│  Internet Gateway     NAT Gateway       │
│  (entrada)            (salida a inet)   │
└─────────────────────────────────────────┘
```

| Concepto | Que es |
|---|---|
| **Subnet publica** | Tiene Internet Gateway, accesible desde internet |
| **Subnet privada** | Sin acceso directo desde internet |
| **Internet Gateway** | Puerta de entrada a internet |
| **NAT Gateway** | Permite que subnets privadas SALGAN a internet (updates, APIs) sin ser accesibles |
| **Availability Zone** | Data center fisico separado (multi-AZ = alta disponibilidad) |

### Security Groups (firewall)

Reglas de trafico por servicio. Se encadenan:

```
alb-sg:  entrada puerto 443 desde 0.0.0.0/0 (internet)
app-sg:  entrada puerto 8080 SOLO desde alb-sg
db-sg:   entrada puerto 5432 SOLO desde app-sg

Internet → ALB → App → DB  ✅
Internet → DB              ❌ bloqueado
Internet → App             ❌ bloqueado
```

### Respuesta de entrevista (VPC)

> "Creo una VPC con subnets publicas y privadas en 2+ AZs. ALB en subnet publica como unico punto de entrada. ECS y RDS en subnets privadas. Security Groups encadenados: ALB acepta HTTPS, app acepta solo trafico del ALB, DB acepta solo conexiones de la app. Multi-AZ para tolerancia a fallos."

---

## 3. IAM — Permisos

### IAM User vs IAM Role

| | IAM User | IAM Role |
|---|---|---|
| Para | **Personas** (developer, admin) | **Servicios** (ECS, Lambda, EC2) |
| Credenciales | Access keys permanentes | Temporales, rotan automaticamente |
| Riesgo | Keys se filtran en git/logs | Sin keys que filtrar |
| Usar cuando | Acceso a consola/CLI personal | Apps que acceden a S3, SQS, etc. |

### NUNCA access keys en servicios

```
MAL:  IAM User → access keys → variables de entorno en container
      → keys permanentes, se filtran, dificil rotar

BIEN: IAM Role → asignar al ECS Task Definition
      → credenciales temporales, rotan cada hora, SDK las detecta automaticamente
```

### Principle of Least Privilege

Solo permisos minimos necesarios, en recursos especificos:

```json
{
  "Effect": "Allow",
  "Action": "s3:GetObject",
  "Resource": "arn:aws:s3:::my-bucket/pdfs/*"
}
```

Nunca `"Action": "*"` ni `"Resource": "*"` en produccion.

### Respuesta de entrevista (IAM)

> "Uso IAM Roles para servicios, nunca Users con access keys. El Role se asigna al Task Definition de ECS con permisos minimos (least privilege). AWS inyecta credenciales temporales que rotan cada hora. El SDK las detecta automaticamente — el codigo no maneja keys."

---

## 4. Almacenamiento

### S3 (Simple Storage Service)

Almacenamiento de archivos ilimitado y barato.

| Clase | Costo | Cuando |
|---|---|---|
| **S3 Standard** | $$$ | Acceso frecuente (imagenes, PDFs activos) |
| **S3 Infrequent Access** | $$ | Acceso raro (backups mensuales) |
| **S3 Glacier** | $ | Archivo (datos legales, anos) |

### Pre-signed URLs

Link temporal para que alguien sin cuenta AWS descargue/suba archivos:

```java
S3Presigner presigner = S3Presigner.create();
PresignedGetObjectRequest presigned = presigner.presignGetObject(req ->
    req.getObjectRequest(b -> b.bucket("my-bucket").key("report.pdf"))
       .signatureDuration(Duration.ofHours(1))  // expira en 1 hora
);
String url = presigned.url().toString();
// Envias esta URL al cliente → descarga sin cuenta AWS
```

### Respuesta de entrevista (S3)

> "Para dar acceso temporal a archivos sin hacer el bucket publico, uso pre-signed URLs con expiracion. El backend genera la URL firmada y la envia al cliente. No necesita cuenta AWS. El bucket sigue privado."

---

## 5. Bases de datos

| Servicio | Tipo | Cuando usarlo |
|---|---|---|
| **RDS** | SQL managed (Postgres, MySQL) | Relacional, el mas comun |
| **Aurora** | SQL premium (3-5x mas rapido) | Alto rendimiento, alta disponibilidad |
| **DynamoDB** | NoSQL key-value | Alta escala, baja latencia, schema flexible |
| **ElastiCache** | Redis/Memcached | Cache (sesiones, datos frecuentes) |

### RDS Multi-AZ

```
AZ-a: RDS Primary (lectura + escritura)
         ↓ replicacion sincrona
AZ-b: RDS Standby (replica)

Primary cae → failover automatico a Standby (~30-60 seg)
```

### Read Replicas (escalar lecturas)

```
Escrituras → Primary
Lecturas   → Read Replica 1, 2, 3... (hasta 15 en Aurora)
```

---

## 6. Mensajeria y Eventos

| Servicio | Modelo | Cuando |
|---|---|---|
| **SQS** | Cola (1 mensaje → 1 consumer) | Tareas async, desacoplamiento simple |
| **SNS** | Pub/Sub (1 mensaje → N suscriptores) | Notificaciones, fan-out |
| **MSK** | Kafka managed | Event streaming, replay, multi-consumer |
| **EventBridge** | Event bus | Integracion entre servicios AWS |

### SQS + SNS (fan-out pattern)

```
Evento "orden creada"
    ↓
  SNS Topic
  ↙    ↓     ↘
SQS   SQS    SQS
billing inventory email
```

Un evento, multiples procesadores independientes.

### SQS vs Kafka (MSK)

| | SQS | MSK (Kafka) |
|---|---|---|
| Replay | No (mensaje se borra al consumir) | Si (log inmutable) |
| Consumer groups | No (competing consumers) | Si (cada grupo lee todo) |
| Throughput | Miles/seg | Millones/seg |
| Complejidad | Nula (managed, sin config) | Media (brokers, particiones) |
| Usar cuando | Tareas simples, fire-and-forget | Event streaming, multiples consumers |

---

## 7. Auto Scaling

### Tipos

| Tipo | Como funciona | Cuando |
|---|---|---|
| **Target Tracking** | "Mantener CPU al 60%" — AWS sube/baja automaticamente | Mayoria de casos |
| **Step Scaling** | Reglas: CPU 60%→+2, CPU 80%→+5, CPU 90%→+10 | Necesitas control granular |
| **Scheduled Scaling** | Cron: "viernes quincena 10am → min 15 containers" | Patrones predecibles |

### Mejor estrategia: combinar

```
Scheduled  → pre-calienta ANTES del pico conocido
    +
Target Tracking → ajusta dinamicamente si el pico es diferente
```

### Cooldown

Espera entre acciones de scaling para evitar oscilaciones (default ~300 seg).

### Escalar la DB tambien

```
20 containers → sin pooling → 2,000 conexiones → DB se cae 💥
20 containers → con pooling → 200 conexiones  → DB feliz ✅
```

Usar connection pooling (HikariCP en Spring Boot) + Aurora Read Replicas.

### Respuesta de entrevista (Scaling)

> "Combino Scheduled Scaling para picos predecibles con Target Tracking en CPU 60% para ajuste dinamico. ALB distribuye trafico. Para la DB, Aurora con read replicas y connection pooling para no saturar conexiones."

---

## 8. Monitoreo y Observabilidad

| Servicio | Para que |
|---|---|
| **CloudWatch** | Metricas, alarmas, logs (el basico) |
| **X-Ray** | Tracing distribuido (seguir un request entre microservicios) |
| **CloudTrail** | Audit log (quien hizo que en tu cuenta AWS) |

### CloudWatch Alarms

```
Metrica: CPUUtilization > 80% por 5 minutos
  → Accion: SNS notification → email/Slack al equipo
  → Accion: Auto Scaling → agregar containers
```

---

## 9. CI/CD en AWS

| Servicio | Que hace |
|---|---|
| **CodePipeline** | Orquesta el pipeline (source → build → deploy) |
| **CodeBuild** | Compila, corre tests, crea Docker image |
| **CodeDeploy** | Despliega a ECS/EC2 (blue-green, rolling) |
| **ECR** | Registry de Docker images (como Docker Hub privado) |

### Pipeline tipico

```
GitHub push → CodePipeline → CodeBuild (mvn test, docker build)
    → push image a ECR → CodeDeploy → ECS Fargate (rolling update)
```

### Deployment strategies

| Estrategia | Como | Riesgo |
|---|---|---|
| **Rolling** | Reemplaza containers uno a uno | Bajo, lento |
| **Blue-Green** | Crea set nuevo, switch de golpe | Rollback instantaneo, doble costo temporal |
| **Canary** | 10% trafico a version nueva, luego 100% | Minimo riesgo, mas complejo |

---

## 10. Arquitectura tipica de microservicios en AWS

```
Internet
    ↓
Route 53 (DNS)
    ↓
CloudFront (CDN, cache estatico)
    ↓
ALB (Load Balancer, subnet publica)
    ↓
┌────────────────────────────────────────┐
│  ECS Fargate (subnet privada)          │
│  [Order Service] [Payment] [Notif]     │
│       ↓              ↓         ↓       │
│  Aurora DB        SQS/SNS   Lambda     │
│  (subnet priv)   (async)   (email)     │
└────────────────────────────────────────┘
    ↓                              ↓
S3 (archivos)              CloudWatch (logs/alarmas)
Secrets Manager (keys)     X-Ray (tracing)
```

---

## 11. Servicios que debes conocer (resumen rapido)

| Servicio | Una linea |
|---|---|
| **EC2** | Maquina virtual |
| **ECS/Fargate** | Containers managed |
| **Lambda** | Funciones serverless |
| **RDS/Aurora** | Base de datos SQL managed |
| **DynamoDB** | NoSQL key-value, alta escala |
| **S3** | Almacenamiento de archivos |
| **SQS** | Cola de mensajes |
| **SNS** | Pub/Sub notificaciones |
| **MSK** | Kafka managed |
| **ALB** | Load balancer HTTP |
| **Route 53** | DNS |
| **CloudFront** | CDN |
| **IAM** | Permisos (Users, Roles, Policies) |
| **VPC** | Red privada virtual |
| **CloudWatch** | Metricas, logs, alarmas |
| **X-Ray** | Tracing distribuido |
| **Secrets Manager** | Guardar API keys, passwords |
| **ECR** | Registry de Docker images |
| **CodePipeline** | CI/CD orquestacion |
| **ElastiCache** | Redis/Memcached managed |
| **KMS** | Encriptacion de datos |

---

## 12. Respuestas rapidas para entrevista

| Pregunta | Respuesta corta |
|---|---|
| ¿Donde desplegar microservicios? | ECS Fargate con ALB enfrente |
| ¿Como proteger la DB? | Subnet privada + Security Group solo acepta trafico de la app |
| ¿Como dar permisos a un servicio? | IAM Role asignado al Task Definition, nunca access keys |
| ¿Como compartir archivo sin hacer publico? | Pre-signed URL de S3 con expiracion |
| ¿Como escalar con picos? | Target Tracking + Scheduled Scaling |
| ¿Lambda o Fargate? | Lambda si trafico variable y funciones cortas; Fargate si trafico constante |
| ¿Como manejar secretos? | Secrets Manager, el servicio los lee con IAM Role |
| ¿Deployment seguro? | Blue-green o canary via CodeDeploy |
| ¿SQL o NoSQL? | RDS/Aurora para relacional; DynamoDB para key-value alta escala |
| ¿Como comunicar microservicios? | Sincrono: HTTP/gRPC via ALB. Asincrono: SQS/SNS/Kafka |
| ¿Monitoreo? | CloudWatch metricas/logs + X-Ray tracing + alarmas a SNS |
| ¿CI/CD? | CodePipeline → CodeBuild → ECR → CodeDeploy → ECS |

---

## 13. Pregunta pendiente — Lambda vs Fargate

**Escenario**: Servicio de notificaciones, 0-500 eventos/min, picos impredecibles, envia email + guarda log.

**Respuesta**:

> "Lambda. Razones: (1) trafico de 0-500/min con picos impredecibles — Lambda escala a miles sin config, Fargate necesitaria Auto Scaling policies. (2) Logica simple (<1 seg por invocacion) — no necesita container. (3) Costo — con 0 eventos, pago $0; Fargate cobra 24/7. Desventaja: cold start de Java (~1-3 seg primera invocacion). Mitigo con SnapStart (Lambda pre-inicializa el runtime) o Provisioned Concurrency (containers Lambda pre-calentados)."
