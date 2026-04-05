# 🎧 Audible Interview Study Guide

---

## Interview 1 — Articulate The Possible + Coding (DSA)

### 🧠 Behavioral: Articulate The Possible and Move Fast To Make It Real

> *"The best visions of the possible are intellectual hypotheses made even better when data and research inform them."*

**Core message:** Think clearly, communicate concisely, inspire others to act, then move decisively.

**Behavioral Questions (STAR format):**
- *Give me an example of when you solicited ideas from your team and reached a better solution than you would alone.*
- *Tell me about a time you rolled up your sleeves to get something done, even if it wasn't your piece of work.*

---

### 💻 Coding: Audiobook Trip Recommender (Two Sum Variant)

**Problem:** Given a trip duration and a list of audiobooks with durations, find a pair of books whose total duration exactly matches the trip.

```
Trip: 2.5h | Books: A=1h, B=5h, C=1.5h, D=2h
→ [Book A, Book C]  (1 + 1.5 = 2.5)
```

**Optimal Approach — HashMap (Two-Sum style):**

```python
def recommend_books(trip_duration: float, books: dict) -> list:
    seen = {}  # duration -> book_name
    for book, duration in books.items():
        complement = trip_duration - duration
        if complement in seen:
            return [seen[complement], book]
        seen[duration] = book
    return []

books = {"Book A": 1.0, "Book B": 5.0, "Book C": 1.5, "Book D": 2.0}
print(recommend_books(2.5, books))  # ['Book A', 'Book C']
```

| Metric | Value |
|--------|-------|
| **Time** | O(n) |
| **Space** | O(n) |
| **Why HashMap?** | Look up complement in O(1) instead of O(n) nested loop |

> **Trade-off:** Brute force is O(n²) time, O(1) space. HashMap is O(n) time, O(n) space. For large catalogs, time efficiency wins.

**Edge cases to mention:** empty catalog, no valid pair, floating-point precision (convert to int cents/tenths).

---

## Interview 2 — Be Customer Obsessed + Coding (Problem Solving)

### 🧠 Behavioral: Be Customer Obsessed

> *"That our customers depend on us is an honor."*

**Behavioral Questions:**
- *Give me an example of when you had to change your course of action given a new insight or idea from a customer.*
- *Tell me about a time you went above and beyond to ensure a customer was delighted.*

---

### 💻 Coding: Audible Credit Management System (FIFO + Expiration)

**Problem:** Track credit balance with 1-year expiration. Credits consumed in FIFO order (earliest-expiring first). Given a list of `(date, amount)` transactions and a `query_date`, return the valid balance.

```python
from collections import deque
from datetime import date, timedelta

def get_credit_balance(transactions: list, query_date: date) -> float:
    # Each entry: (expiration_date, amount)
    credit_queue = deque()

    for tx_date, amount in sorted(transactions, key=lambda x: x[0]):
        if tx_date > query_date:
            break
        expiry = tx_date + timedelta(days=365)
        if amount > 0:
            credit_queue.append((expiry, amount))
        else:  # consumption
            to_consume = abs(amount)
            while to_consume > 0 and credit_queue:
                exp, credits = credit_queue.popleft()
                if credits <= to_consume:
                    to_consume -= credits
                else:
                    credit_queue.appendleft((exp, credits - to_consume))
                    to_consume = 0

    # Sum only non-expired credits at query_date
    return sum(amt for exp, amt in credit_queue if exp > query_date)
```

| Metric | Value |
|--------|-------|
| **Time** | O(n log n) for sort, O(n) overall |
| **Space** | O(n) |
| **Why Deque?** | O(1) append/pop from both ends — perfect for FIFO |

**Edge cases:** credits added after query_date (ignore), all credits expired, partial consumption.

---

## Interview 3 — Activate Caring + Culture/Technology + System Design

### 🧠 Behavioral: Activate Caring

> *"People will invariably forget things you say, but they will rarely forget how you make them feel."*

**Question:** *Tell me about an experience dedicating your time/energy/expertise to help others.*

---

### 🧠 Behavioral: Study and Draw Inspiration From Culture and Technology

> *"Leaders who stand out operate at the cutting edge of the arts and sciences."*

**Questions:**
- *Tell me about a time you used new information to improve a product or process that was working well.*
- *Tell me about the most interesting thing you've learned in the past month.*
- *Tell me about a time you spent time getting to know a colleague better and why.*

---

### 🏗️ System Design: Audible Social Site

**Use Cases:**
1. Customer submits a new post (current listen, completed book, or message)
2. Social feed — time-ordered list of own posts + followed users' posts

**[FUQ] The customer pressed 'Send'. What would you build to accept and store posts at scale?**

#### High-Level Architecture

```
Client → API Gateway → Post Service → Message Queue (SQS/Kafka)
                                              ↓
                                      Fan-out Worker
                                     /              \
                             User's Post DB       Followers' Feed Cache (Redis)
                                     ↓
                              NoSQL (DynamoDB): PostsTable
```

#### Key Components

| Component | Choice | Reason |
|-----------|--------|--------|
| **Post storage** | DynamoDB | Flexible schema, horizontal scale |
| **Feed delivery** | Redis sorted set | O(log n) insert, time-ordered range queries |
| **Async fan-out** | Kafka/SQS | Decouples write from distribution |
| **API** | REST / GraphQL | GraphQL ideal for feed composition |

#### Trade-offs to Articulate
- **Push vs Pull:** Push (fan-out on write) = fast reads, expensive for users with millions of followers.
- **Hybrid approach:** Push to active followers, pull for celebrity/inactive accounts.
- **Fault-tolerance:** Retries, idempotency keys, dead-letter queues.

---

## Interview 4 — Imagine and Invent Before They Ask + Coding (Logical & Maintainable)

### 🧠 Behavioral: Imagine and Invent Before They Ask

> *"We embrace ambiguity and tolerate and demystify complexity."*

**Question:** *Tell me about a time you took something working "just fine" and still improved upon it.*

---

### 💻 Coding: Employee Directory — Filter Tree by Property (DFS)

**Problem:** Given an org-chart tree where each node has properties, extract a filtered subtree keeping only nodes that match a given property=value. Skip non-matching nodes but reconnect matching descendants to the nearest matching ancestor.

```python
class Employee:
    def __init__(self, name, properties, children=None):
        self.name = name
        self.properties = properties  # e.g. {"Music genre": "Rock"}
        self.children = children or []

def get_community(root: Employee, prop: str, value: str) -> list:
    """Returns list of root nodes of filtered trees."""
    results = []
    _filter(root, prop, value, results)
    return results

def _filter(node: Employee, prop: str, value: str, result_roots: list) -> list:
    """Returns matching subtree roots from this node's subtree."""
    matching_children = []
    for child in node.children:
        matching_children.extend(_filter(child, prop, value, result_roots))

    if node.properties.get(prop) == value:
        node.children = matching_children  # reconnect matching descendants
        return [node]
    else:
        return matching_children  # skip node, bubble children up
```

**Example:**
```
Input (★ = matches):        Output:
       a★                      a★
   /  |  \  \                /  |  \
  b  c★  d★  e             f★  c★  d★
  |  /|\  /\  /\                |    |
 f★ g h★ i j★ k l m            h★   j★
```

| Metric | Value |
|--------|-------|
| **Time** | O(n) — visits every node once |
| **Space** | O(h) — recursion stack (tree height) |
| **Why DFS?** | Natural for trees; enables bottom-up child reconnection |

> **Edge case:** If root doesn't match, return a **list** of top-level matching subtrees — not a single tree.

**Design points to mention:**
- Prefer returning a new tree (immutability) over mutating the original
- `GetCommunity` is a public API — design for extensibility (multiple values, multiple properties)
- Consider caching if called frequently with identical queries

---

## 📋 Quick Reference

| Interview | Behavioral Principle | Coding Topic |
|-----------|---------------------|--------------|
| 1 | Articulate The Possible + Move Fast | Two-Sum / Book Recommender → HashMap O(n) |
| 2 | Be Customer Obsessed | Credit Management FIFO → Deque O(n) |
| 3 | Activate Caring + Culture/Tech | System Design → Social Feed (Kafka + Redis) |
| 4 | Imagine and Invent Before They Ask | Tree Filter DFS → Employee Directory O(n) |

### STAR Framework
- **S**ituation — set the context
- **T**ask — your responsibility  
- **A**ction — what **you** specifically did
- **R**esult — measurable outcome

### Coding Interview Checklist
1. Clarify constraints and edge cases first
2. State approach + complexity **before** coding
3. Write clean code with meaningful names
4. Walk through an example manually
5. Proactively mention trade-offs and alternatives
