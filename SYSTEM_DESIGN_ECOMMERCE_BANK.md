# 🏗️ System Design Question Bank — E-commerce Edition

A working reference for system-design interviews and real e-commerce architecture, organized so you can **reason from first principles** rather than memorize. Every entry follows the same schema:

> **Problem it solves · How it works (answer) · Real implementation example · Use cases · Architecture (ASCII) · Disadvantages · Competing technologies**

### An honest note on scope
Interview mastery comes from **~40–60 designs you deeply understand**, not thousands of shallow ones. This bank covers **all the core building blocks and all the major e-commerce scenarios** at real depth. Section D lists the long tail of variations to expand into — a menu you (or I, in batches) can keep growing. Depth first, then breadth.

### How to use it
1. Learn **Part A (building blocks)** first — every scenario is assembled from these.
2. For each **Part B scenario**, practice the flow out loud: *requirements → API → data model → high-level architecture → deep-dive on the hard part → bottlenecks & scale → trade-offs.*
3. Always state **trade-offs** — interviewers score judgment, not buzzwords.

---

## The universal framework (say this in every design round)

1. **Clarify requirements** — functional (what it does) + non-functional (scale: QPS, users, data size, latency, availability, consistency).
2. **Estimate scale** — back-of-envelope: reads/writes per second, storage/year, bandwidth.
3. **API design** — the key endpoints.
4. **Data model** — entities, SQL vs NoSQL, access patterns.
5. **High-level architecture** — draw the boxes and arrows.
6. **Deep dive** — the interviewer picks the hardest component; go deep.
7. **Bottlenecks & scale** — caching, sharding, replication, queues, CDN.
8. **Trade-offs** — consistency vs availability, cost vs latency, build vs buy.

> *"Make it work, make it right, make it fast."* — Kent Beck. In interviews: correct → then scalable → then optimized.

---

# PART A — Core Building Blocks

## A1. Load Balancing
- **Problem it solves:** A single server can't handle all traffic and is a single point of failure.
- **How it works:** A load balancer distributes incoming requests across a pool of servers using an algorithm (Round Robin, Least Connections, IP Hash, Weighted). Layer 4 (TCP) balances on IP/port; Layer 7 (HTTP) balances on content (path, headers, cookies). Health checks remove dead servers.
- **Real example:** AWS ALB fronts a fleet of catalog service instances; sticky sessions route a user to the same node when needed.
- **Use cases:** Horizontal scaling, high availability, zero-downtime deploys (drain + rotate).
- **Architecture:**
```
        ┌──────────┐   ┌── App Server 1
Client ─┤   Load   ├───┼── App Server 2
        │ Balancer │   └── App Server 3
        └──────────┘        (health-checked pool)
```
- **Disadvantages:** Itself a potential SPOF (needs redundancy/failover); adds a hop of latency; L7 inspection costs CPU.
- **Competing tech:** NGINX, HAProxy, AWS ELB/ALB/NLB, Envoy, Google Cloud Load Balancing; DNS round-robin (crude alternative).

## A2. Caching
- **Problem it solves:** Repeatedly recomputing or re-fetching the same data is slow and overloads the database.
- **How it works:** Store hot data in fast memory (RAM). Patterns: **cache-aside** (app checks cache, on miss reads DB and populates), **read-through/write-through** (cache sits in front of DB), **write-back** (write to cache, async to DB). Eviction: LRU/LFU/TTL. Key challenge: **invalidation** (keep cache consistent with source).
- **Real example:** Product detail pages cache the product JSON in Redis with a 5-min TTL; on price update, the service invalidates the key.
- **Use cases:** Product catalog, sessions, computed feeds, rate-limit counters, hot inventory reads.
- **Architecture:**
```
Client → App → [Redis cache] --hit--> return
                    │miss
                    ▼
                 Database → populate cache → return
```
- **Disadvantages:** Stale data risk; cache invalidation is famously hard; cold-start/thundering-herd on expiry; extra infra cost.
- **Competing tech:** Redis, Memcached, in-process caches (Caffeine/Guava), CDN edge caches, Hazelcast.

## A3. CDN (Content Delivery Network)
- **Problem it solves:** Serving static/media content from one origin is slow for far-away users and hammers the origin.
- **How it works:** Geographically distributed edge servers cache content close to users; requests hit the nearest PoP. Pull (lazy) or push (pre-load) models.
- **Real example:** Product images, CSS/JS, and videos served from CloudFront edges; origin (S3) is hit only on cache miss.
- **Use cases:** Images, static assets, video, even cacheable API responses.
- **Architecture:**
```
User(IN) → Edge(Mumbai) ─miss→ Origin(S3)
User(US) → Edge(Virginia)┘  (cached copies at each edge)
```
- **Disadvantages:** Cost; invalidation lag for updated assets; not for personalized/dynamic content.
- **Competing tech:** CloudFront, Akamai, Cloudflare, Fastly, Google Cloud CDN.

## A4. Database Indexing
- **Problem it solves:** Full-table scans are O(n) and slow for lookups/filters.
- **How it works:** An index (usually a B-tree, or hash for equality) is a sorted structure mapping column values to row locations, turning lookups into O(log n). Composite indexes support multi-column queries; covering indexes serve a query entirely from the index.
- **Real example:** Index on `orders(user_id, created_at)` makes "my recent orders" instant.
- **Use cases:** Any frequent WHERE/JOIN/ORDER BY column, foreign keys, uniqueness.
- **Disadvantages:** Slows writes (index must update); uses storage; too many indexes hurt; unused indexes are pure cost.
- **Competing tech:** B-tree (default), Hash, GiST/GIN (Postgres full-text/geo), LSM-trees (write-heavy stores), inverted index (search engines).

## A5. SQL vs NoSQL
- **Problem it solves:** Choosing storage for a given data shape, scale, and consistency need.
- **How it works:** **SQL** = structured schema, relations/joins, **ACID**, strong consistency, vertical scale (Postgres, MySQL). **NoSQL** = flexible schema, horizontal scale, often eventual consistency; families: key-value (Redis/DynamoDB), document (MongoDB), wide-column (Cassandra), graph (Neo4j).
- **Real example:** Orders/payments in Postgres (need ACID); product catalog + cart in DynamoDB/Mongo (flexible, huge scale); recommendations graph in Neo4j.
- **Use cases:** SQL for transactions & complex queries; NoSQL for massive scale, high write throughput, flexible/denormalized data.
- **Disadvantages:** SQL harder to scale horizontally; NoSQL sacrifices joins/consistency and pushes complexity into the app.
- **Competing tech:** Postgres, MySQL, Aurora / DynamoDB, Cassandra, MongoDB, HBase, Spanner (NewSQL bridges both).

## A6. Database Sharding / Partitioning
- **Problem it solves:** A single DB can't hold all the data or serve all the traffic.
- **How it works:** Split data across nodes by a **shard key**. Strategies: **hash-based** (even spread, but range queries hard), **range-based** (good for ranges, risk of hotspots), **directory-based** (lookup service). Consistent hashing minimizes reshuffling when nodes change.
- **Real example:** Shard `orders` by `hash(user_id)` so each user's orders live on one shard.
- **Use cases:** Very large tables (orders, events, catalog at marketplace scale).
- **Architecture:**
```
                ┌── Shard 1 (user_id % 3 == 0)
Router/hash ────┼── Shard 2 (user_id % 3 == 1)
                └── Shard 3 (user_id % 3 == 2)
```
- **Disadvantages:** Cross-shard joins/transactions are hard; rebalancing is painful; hotspots if key is skewed; operational complexity.
- **Competing tech:** Native sharding (Mongo, Cassandra), Vitess (MySQL), Citus (Postgres), app-level sharding.

## A7. Replication
- **Problem it solves:** Availability, read scaling, and durability if a node dies.
- **How it works:** Copy data to multiple nodes. **Leader-follower (primary-replica):** writes to leader, reads from followers (async or sync). **Multi-leader/leaderless** (Dynamo-style quorum: W+R>N) for write availability.
- **Real example:** Postgres primary handles writes; 3 read replicas serve catalog reads; failover promotes a replica.
- **Use cases:** Read-heavy workloads, HA, geo-distribution, backups.
- **Disadvantages:** **Replication lag** → stale reads (read-your-writes issues); sync replication adds latency; conflict resolution in multi-leader.
- **Competing tech:** Postgres/MySQL replication, MongoDB replica sets, Cassandra tunable quorums, DynamoDB global tables.

## A8. Message Queues / Async Processing
- **Problem it solves:** Slow or spiky work shouldn't block the user request; services shouldn't be tightly coupled.
- **How it works:** Producers push messages to a queue; consumers process asynchronously at their own pace. Decouples, buffers spikes, enables retries. Delivery: at-least-once (common, needs idempotency), at-most-once, exactly-once (hard).
- **Real example:** On checkout, publish an `OrderPlaced` message; email, inventory, and analytics consumers process independently.
- **Use cases:** Emails/notifications, order pipelines, image processing, decoupling microservices, load leveling.
- **Architecture:**
```
Checkout ──▶ [Queue] ──▶ Email Worker
                   ├────▶ Inventory Worker
                   └────▶ Analytics Worker
```
- **Disadvantages:** Eventual consistency; ordering & duplicate handling; another system to run; debugging async flows is harder.
- **Competing tech:** Kafka (log/stream), RabbitMQ, AWS SQS/SNS, Google Pub/Sub, ActiveMQ, Redis Streams.

## A9. Event-Driven Architecture / Pub-Sub
- **Problem it solves:** Many services need to react to the same event without the producer knowing about them.
- **How it works:** Producers emit events to topics; any number of subscribers consume independently (fan-out). Event log (Kafka) also enables replay and event sourcing.
- **Real example:** `OrderPlaced` event fans out to inventory, loyalty points, recommendation retraining, and the seller dashboard.
- **Use cases:** Microservice choreography, real-time analytics, CDC (change data capture), audit logs.
- **Disadvantages:** Hard to trace end-to-end; eventual consistency; event schema evolution; "event soup" if overused.
- **Competing tech:** Kafka, AWS SNS+SQS, Google Pub/Sub, NATS, EventBridge.

## A10. Rate Limiting
- **Problem it solves:** Protect services from abuse, bots, and traffic spikes; enforce quotas/fairness.
- **How it works:** Algorithms: **Token Bucket** (tokens refill over time, allows bursts), **Leaky Bucket** (constant drain), **Fixed/Sliding Window** counters. Usually a Redis counter keyed by user/IP/API-key.
- **Real example:** "Add to cart" limited to N req/sec per user in Redis to blunt bots during a flash sale.
- **Use cases:** API gateways, login/OTP endpoints, scraping/bot defense, flash-sale fairness.
- **Disadvantages:** Distributed counting is tricky (clock skew, race conditions); false positives block real users behind shared NAT.
- **Competing tech:** Redis-based limiters, API Gateway (Kong/AWS), Envoy, Cloudflare rate limiting.

## A11. API Gateway
- **Problem it solves:** Clients shouldn't call dozens of microservices directly; cross-cutting concerns repeat everywhere.
- **How it works:** A single entry point that routes to backend services and handles auth, rate limiting, SSL termination, request aggregation, and versioning.
- **Real example:** Mobile app → API Gateway → routes to catalog, cart, order services; gateway validates JWT and rate-limits.
- **Use cases:** Microservice front door, BFF (backend-for-frontend), auth centralization.
- **Disadvantages:** Potential bottleneck/SPOF; extra latency; can become a "god" component.
- **Competing tech:** Kong, AWS API Gateway, Apigee, NGINX, Envoy, Zuul/Spring Cloud Gateway.

## A12. Microservices vs Monolith
- **Problem it solves:** Scaling teams and components independently as a system grows.
- **How it works:** **Monolith** = one deployable; simple to build/test, but scales as a unit and couples teams. **Microservices** = many small independently deployable services owning their data, communicating via API/events; independent scaling & deploys.
- **Real example:** Split an e-commerce monolith into catalog, cart, order, payment, inventory, and search services.
- **Use cases:** Large orgs, differing scale profiles, independent release cadences.
- **Disadvantages:** Distributed-system complexity (network, partial failure, data consistency), ops overhead, harder debugging. Start monolith, split when justified.
- **Competing tech:** Modular monolith, SOA, serverless functions.

## A13. CAP Theorem & Consistency Models
- **Problem it solves:** Reasoning about trade-offs in distributed data stores during network partitions.
- **How it works:** Under a network **P**artition you must choose **C**onsistency (reject/stale-block to stay correct) or **A**vailability (serve possibly-stale data). Models: strong, eventual, causal, read-your-writes. PACELC extends it (else, latency vs consistency).
- **Real example:** Payments choose CP (correctness over availability); product catalog/reviews choose AP (always available, eventually consistent).
- **Use cases:** Picking/tuning databases per workload.
- **Disadvantages:** No free lunch — every choice sacrifices something; "eventual" surprises users (stale carts).
- **Competing tech:** CP stores (HBase, Spanner, Zookeeper), AP stores (Cassandra, Dynamo), tunable (Cassandra quorums).

## A14. Idempotency
- **Problem it solves:** Retries and at-least-once delivery can process the same request twice (double charge, double order).
- **How it works:** Client sends an **idempotency key**; server records it and returns the same result for repeats instead of re-executing. Or design naturally idempotent operations (upserts, set-state).
- **Real example:** "Place order" carries an idempotency key; a retried checkout returns the existing order rather than creating a duplicate.
- **Use cases:** Payments, order creation, any retried/queued write.
- **Disadvantages:** Must store keys (TTL/cleanup); careful with concurrent duplicates (need a unique constraint/lock).
- **Competing tech:** Stripe-style idempotency keys, DB unique constraints, dedup tables, exactly-once frameworks.

## A15. CQRS (Command Query Responsibility Segregation)
- **Problem it solves:** Read and write workloads have very different shapes and scale needs.
- **How it works:** Separate the write model (commands, normalized, transactional) from the read model (denormalized, optimized for queries), kept in sync via events.
- **Real example:** Orders written to Postgres; a denormalized read view of "order history" projected into Elasticsearch for fast queries.
- **Use cases:** High-read systems, complex reporting, event-sourced systems.
- **Disadvantages:** Complexity, eventual consistency between write and read models, more moving parts.
- **Competing tech:** Plain CRUD (simpler), materialized views, read replicas.

## A16. Saga Pattern (Distributed Transactions)
- **Problem it solves:** No ACID transaction spans microservices, but a business flow (checkout) touches many services.
- **How it works:** A sequence of local transactions; each publishes an event triggering the next. On failure, run **compensating transactions** to undo prior steps. **Choreography** (events) or **orchestration** (a coordinator).
- **Real example:** Checkout saga: reserve inventory → charge payment → create order → on payment failure, release inventory (compensate).
- **Architecture:**
```
Order → reserve stock → charge → confirm
   ▲__________compensate on failure_________│
```
- **Use cases:** Order fulfillment, booking systems, any multi-service transaction.
- **Disadvantages:** Complex to design/debug; eventual consistency; compensations aren't always clean (money already moved).
- **Competing tech:** 2-phase commit (2PC, blocking/rarely used), Temporal/Camunda orchestration, outbox pattern.

## A17. Consistent Hashing
- **Problem it solves:** Adding/removing cache or DB nodes shouldn't remap almost all keys.
- **How it works:** Map nodes and keys onto a hash ring; a key belongs to the next node clockwise. Adding/removing a node only moves the keys between adjacent points. Virtual nodes even out distribution.
- **Real example:** Distributing cache keys across a Redis cluster; DynamoDB/Cassandra partitioning.
- **Use cases:** Distributed caches, sharded databases, load balancers.
- **Disadvantages:** Uneven load without virtual nodes; still some remapping; more complex than modulo.
- **Competing tech:** Modulo hashing (simple, bad on resize), rendezvous hashing, range partitioning.

## A18. Search — Inverted Index / Elasticsearch
- **Problem it solves:** `LIKE '%query%'` on a SQL DB is slow and can't do relevance/typos/facets.
- **How it works:** An **inverted index** maps each term → list of documents containing it. Add tokenization, stemming, TF-IDF/BM25 relevance ranking, fuzzy matching, and facets/aggregations.
- **Real example:** Product search indexed in Elasticsearch; supports typo tolerance, filters (brand, price), and relevance ranking.
- **Use cases:** Product search, logs, autocomplete, analytics.
- **Disadvantages:** Eventually consistent with the source DB; operationally heavy; not the system of record.
- **Competing tech:** Elasticsearch/OpenSearch, Apache Solr, Algolia, Typesense, Postgres full-text (small scale).

## A19. Object / Blob Storage
- **Problem it solves:** Databases are wrong for large binary files (images, videos, invoices).
- **How it works:** Store files as objects with metadata in a flat namespace, accessed via HTTP; virtually unlimited, cheap, durable. Often fronted by a CDN; uploads via pre-signed URLs.
- **Real example:** Product images and invoices in S3; the DB stores only the URL/key.
- **Use cases:** Media, backups, static sites, data lake.
- **Disadvantages:** Higher latency than block storage; eventual consistency (historically); not for frequent small updates.
- **Competing tech:** AWS S3, Google Cloud Storage, Azure Blob, MinIO, Ceph.

## A20. Observability (Logging, Metrics, Tracing)
- **Problem it solves:** You can't fix or scale what you can't see, especially across microservices.
- **How it works:** **Logs** (events), **metrics** (numeric time series: latency, QPS, error rate), **distributed tracing** (a request's path across services via a trace ID). Alerting on SLOs.
- **Real example:** A slow checkout is traced across cart→payment→inventory to find the bottleneck service.
- **Use cases:** Debugging, capacity planning, SLA/SLO monitoring, incident response.
- **Disadvantages:** Cost/volume of telemetry; cardinality explosions; noise vs signal.
- **Competing tech:** Prometheus+Grafana, ELK/OpenSearch, Datadog, Jaeger/Zipkin, OpenTelemetry, Honeycomb.

---

# PART B — E-commerce Scenario Designs

## B1. Design a Product Catalog Service
- **Problem it solves:** Store and serve millions of products with fast, flexible reads at massive scale.
- **Answer / approach:** Read-heavy (100:1). Use a document store for flexible attributes; aggressively cache; serve images via CDN. Denormalize for the product-detail page. Separate write path (seller updates) from read path (CQRS-lite).
- **Real example:** Amazon-style catalog: product docs in DynamoDB/Mongo, Redis cache for hot items, images in S3+CloudFront, changes streamed to search index.
- **Use cases:** Product detail page, listing pages, category browse.
- **Architecture:**
```
                    ┌─ Redis (hot products)
Client → CDN → API ─┼─ Catalog DB (DynamoDB/Mongo)
        (images)    └─ (CDC)→ Search index (ES)
```
- **Disadvantages:** Cache invalidation on price/stock changes; eventual consistency to search; denormalization duplication.
- **Competing tech:** DynamoDB vs MongoDB vs Postgres+JSONB; Redis vs Memcached.

## B2. Design Product Search & Autocomplete
- **Problem it solves:** Fast, relevant, typo-tolerant search over the whole catalog with filters/facets.
- **Answer / approach:** Index products in Elasticsearch (inverted index + BM25). Autocomplete via a prefix index (edge n-grams) or a Trie in Redis. Sync from catalog via change-data-capture. Rank by relevance + business signals (popularity, margin, availability).
- **Real example:** Search service consuming `ProductUpdated` events into ES; autocomplete served from a Redis-backed Trie of top queries.
- **Use cases:** Search bar, autocomplete, faceted filtering, "did you mean".
- **Architecture:**
```
Catalog → (events) → Indexer → [Elasticsearch]
Search bar → API → ES (results) + Redis Trie (suggest)
```
- **Disadvantages:** Index lag (eventual consistency); relevance tuning is ongoing; ES ops cost.
- **Competing tech:** Elasticsearch/OpenSearch, Algolia, Solr, Typesense.

## B3. Design a Shopping Cart
- **Problem it solves:** Persist a user's selected items across sessions/devices with low latency and high availability (must never be "down").
- **Answer / approach:** Favor **availability (AP)**. Store cart as a key-value doc keyed by user/session in a fast store (Redis or DynamoDB) with TTL for guests. Merge guest cart into user cart on login. Validate price/stock at checkout, not on every add.
- **Real example:** Cart in DynamoDB (`user_id` → items[]), Redis cache in front; guest carts by session cookie with 30-day TTL.
- **Use cases:** Add/remove/update items, cross-device cart, save-for-later.
- **Architecture:**
```
Client → Cart API → Redis (hot) → DynamoDB (durable)
              └─ on checkout → validate price/stock
```
- **Disadvantages:** Stale prices/stock until checkout; merge conflicts (guest→user); eventual consistency across regions.
- **Competing tech:** Redis, DynamoDB, MongoDB; session store vs persistent store.

## B4. Design Checkout & Order Placement
- **Problem it solves:** Turn a cart into a paid order reliably across inventory, payment, and order services — without double-charging or overselling.
- **Answer / approach:** Orchestrate a **Saga**: reserve inventory → charge payment → create order → send confirmation; compensate on failure. Use an **idempotency key** so retries don't duplicate orders. Use the **outbox pattern** to reliably publish events with the DB write.
- **Real example:** Checkout orchestrator calls inventory (reserve), payment (charge), order (persist); on payment failure, releases the reservation.
- **Use cases:** The core buy flow.
- **Architecture:**
```
Cart → Checkout Orchestrator
        1) Inventory: reserve
        2) Payment: charge (idempotency key)
        3) Order: create (outbox → event)
        ✗ any step fails → compensate previous
```
- **Disadvantages:** Distributed-transaction complexity; partial failures; eventual consistency; compensations for money are delicate.
- **Competing tech:** Orchestration (Temporal/Step Functions) vs choreography (events); 2PC (avoided).

## B5. Design Payment Processing
- **Problem it solves:** Charge customers correctly, securely, and exactly once, integrating external gateways.
- **Answer / approach:** Never store raw card data (PCI-DSS) — tokenize via the gateway. Idempotency keys prevent double charges. Persist a payment state machine (initiated→authorized→captured→refunded). Handle async gateway **webhooks** for final status; reconcile daily.
- **Real example:** Integrate Stripe/Razorpay: create PaymentIntent with idempotency key; confirm via webhook; store only tokens.
- **Use cases:** Card/UPI/wallet payments, refunds, subscriptions.
- **Architecture:**
```
Checkout → Payment Svc → Gateway (Stripe)
                ▲            │ webhook (async result)
                └── state machine + idempotency + reconciliation
```
- **Disadvantages:** External dependency/latency; webhook reliability; fraud/chargebacks; strict compliance.
- **Competing tech:** Stripe, Razorpay, Braintree, Adyen, PayPal, in-house (rarely).

## B6. Design Inventory Management (avoid overselling)
- **Problem it solves:** Under high concurrency, two buyers must not both buy the last unit.
- **Answer / approach:** The **last-item problem** needs strong consistency on the stock counter. Options: (1) atomic conditional DB update `UPDATE ... SET qty=qty-1 WHERE qty>0` (transactional); (2) reserve-on-add-to-cart with TTL; (3) Redis atomic `DECR` with a reconciliation to the DB for extreme scale (flash sales).
- **Real example:** Reserve stock at checkout via a row-level lock / conditional update; release if payment fails or reservation times out.
- **Use cases:** Stock display, reservations, flash sales, multi-warehouse.
- **Architecture:**
```
Checkout → Inventory Svc:
  atomic: UPDATE stock SET qty=qty-1 WHERE sku=? AND qty>0
  success → reserve (TTL); fail → "out of stock"
```
- **Disadvantages:** Strong consistency limits throughput (hotspots on popular SKUs); reservation cleanup; multi-warehouse allocation complexity.
- **Competing tech:** SQL transactions/row locks, Redis atomic ops, distributed locks (Redlock), event-sourced stock.

## B7. Design Order Management & Fulfillment
- **Problem it solves:** Track an order through its lifecycle (placed→paid→packed→shipped→delivered→returned) across many services.
- **Answer / approach:** Model an explicit **state machine**; drive transitions with events. Store orders in an ACID DB (source of truth); project a read model for order history/tracking. Emit events for warehouse, shipping, notifications, analytics.
- **Real example:** Order service persists state; each fulfillment step emits an event updating status and notifying the customer.
- **Use cases:** Order tracking, returns, customer support, seller dashboards.
- **Architecture:**
```
Order (Postgres, source of truth)
   └ events → Warehouse / Shipping / Notify / Analytics
   └ projection → Order-history read model (ES)
```
- **Disadvantages:** Many states/edge cases (partial shipments, cancellations); consistency across services; audit needs.
- **Competing tech:** Event sourcing vs CRUD state machine; Temporal for long-running workflows.

## B8. Design a Recommendation System
- **Problem it solves:** Surface relevant products to increase engagement and revenue.
- **Answer / approach:** Two-stage funnel. **Candidate generation** (collaborative filtering / two-tower embeddings → ANN lookup over millions of items, fast, recall-oriented). **Ranking** (a model scoring hundreds of candidates on rich features, precision-oriented). Add business re-ranking (margin, stock, diversity). Batch-train offline, serve online; evaluate with A/B tests.
- **Real example:** "Customers who bought X also bought Y" via item-item collaborative filtering; personalized homepage via embeddings + a ranking model.
- **Use cases:** Homepage, PDP "related", cart cross-sell, email.
- **Architecture:**
```
Events → Feature store + model training (offline)
Request → Candidate gen (ANN) → Ranker → Re-rank → results
```
- **Disadvantages:** Cold start (new users/items); feedback loops (popularity bias); heavy infra; needs experimentation.
- **Competing tech:** Collaborative filtering, content-based, matrix factorization, deep two-tower; tools: TensorFlow Recommenders, FAISS, AWS Personalize.

## B9. Design Pricing, Promotions & Coupons
- **Problem it solves:** Apply dynamic prices, discounts, and coupon rules correctly and fast, with abuse protection.
- **Answer / approach:** A **rules engine** evaluates promotions (percentage/BOGO/threshold) at cart time. Coupons validated for eligibility, usage limits (atomic counter to prevent over-redemption), and stacking rules. Cache computed prices; recompute on cart change.
- **Real example:** Cart service calls a promotions engine returning line-item and order-level discounts; coupon redemption count decremented atomically in Redis.
- **Use cases:** Sales, coupons, loyalty, dynamic/personalized pricing.
- **Architecture:**
```
Cart → Pricing Engine (rules) → discounts
Coupon → validate + atomic redeem-count (Redis/DB)
```
- **Disadvantages:** Rule complexity/conflicts; abuse (coupon farming); consistency of usage limits under concurrency.
- **Competing tech:** Rules engines (Drools), custom services, feature-flag/experiment platforms.

## B10. Design Reviews & Ratings
- **Problem it solves:** Collect and display product reviews/ratings at read-heavy scale with aggregation.
- **Answer / approach:** Store reviews in a scalable store; precompute aggregates (avg rating, count, histogram) incrementally on new reviews rather than on read. Moderate (spam/abuse) async. Serve via cache/CDN. Eventual consistency is fine.
- **Real example:** Review written → event → update product's rolling average and count → invalidate product cache.
- **Use cases:** PDP ratings, review lists, sorting/filtering by rating.
- **Architecture:**
```
Write review → Reviews DB → event → update aggregates → cache
Read → cached aggregate + paginated reviews
```
- **Disadvantages:** Fake-review/spam detection; aggregate consistency; moderation cost.
- **Competing tech:** SQL vs NoSQL for reviews; batch vs streaming aggregation.

## B11. Design a Notification System (email/SMS/push)
- **Problem it solves:** Send billions of transactional and marketing messages reliably across channels.
- **Answer / approach:** Async via queues. A notification service consumes events (`OrderShipped`), renders templates, and dispatches to channel providers with retries and rate limits. Respect user preferences/opt-outs; dedupe; track delivery. Priority queues separate transactional from marketing.
- **Real example:** `OrderShipped` → queue → worker renders email → SES/Twilio/FCM; failures retried with backoff.
- **Use cases:** Order updates, OTP, price-drop alerts, marketing campaigns.
- **Architecture:**
```
Events → [Queue] → Notification Workers → Email/SMS/Push providers
                         └ prefs, templates, retry, dedupe, tracking
```
- **Disadvantages:** Provider limits/failures; deliverability/spam; ordering; cost at scale.
- **Competing tech:** SES/SNS, Twilio, FCM/APNs, SendGrid; Kafka/SQS as backbone.

## B12. Design Fraud Detection
- **Problem it solves:** Block fraudulent orders/payments in near-real-time without blocking good customers.
- **Answer / approach:** Real-time scoring pipeline: extract features (velocity, device fingerprint, geo mismatch, amount anomalies) → ML model + rules → score → allow/review/deny. Async deep analysis feeds back into training. Low-latency budget (<100ms) in the payment path.
- **Real example:** At checkout, a fraud service scores the transaction; high-risk goes to manual review, clear-fraud is blocked.
- **Use cases:** Payment fraud, account takeover, promo abuse, fake reviews.
- **Architecture:**
```
Checkout → Fraud Svc (features + model + rules) → allow/review/deny
        events → offline training → model updates
```
- **Disadvantages:** False positives lose sales; adversarial/evolving fraud; latency budget; label lag.
- **Competing tech:** Rules engines, ML (gradient boosting), graph analysis; AWS Fraud Detector, Sift, Signifyd.

## B13. Design a Flash Sale / High-Contention Drop
- **Problem it solves:** Millions rush a few thousand units in seconds — extreme spike + the last-item problem.
- **Answer / approach:** Protect the system: **waiting room/queue** to admit users gradually; pre-warm caches; decrement stock atomically in Redis (`DECR`, stop at 0) to avoid DB hotspots, reconcile to DB async; aggressive rate limiting + bot detection; make add-to-cart/checkout idempotent; degrade gracefully (static pages).
- **Real example:** Xiaomi/limited-drop style: virtual queue → token to buy → Redis atomic stock counter → async order persistence.
- **Use cases:** Flash sales, ticket/limited drops, Black Friday doorbusters.
- **Architecture:**
```
Users → CDN/waiting-room → rate limiter → Redis stock (atomic DECR)
     token → checkout (idempotent) → async order write → DB
```
- **Disadvantages:** Redis-DB reconciliation; fairness vs bots; huge transient load; cost of over-provisioning.
- **Competing tech:** Redis atomic ops/Lua, queue-based admission, CDN edge logic.

## B14. Design Delivery Tracking / Logistics
- **Problem it solves:** Show real-time shipment status and location to customers across carriers.
- **Answer / approach:** Ingest carrier webhooks/GPS pings into a stream; update a shipment state store; push live updates to clients via WebSockets/polling; geospatial index for ETA. Read model optimized for "where's my order".
- **Real example:** Carrier events → Kafka → tracking service updates status → customer app gets push + live map.
- **Use cases:** Order tracking page, delivery ETA, driver apps.
- **Architecture:**
```
Carrier/GPS → [Kafka] → Tracking Svc → state store (+ geo index)
Customer app ← WebSocket/poll ← Tracking Svc
```
- **Disadvantages:** High-frequency location writes; carrier data inconsistency; real-time push at scale.
- **Competing tech:** Kafka + geospatial DB (PostGIS, Redis Geo), WebSockets, MQTT for devices.

## B15. Design a Clickstream / Analytics Pipeline
- **Problem it solves:** Capture billions of user events (views, clicks, add-to-cart) for analytics, personalization, and BI.
- **Answer / approach:** Client/edge emits events → ingestion (Kafka) → stream processing (real-time aggregates) + sink to a data lake/warehouse (batch). Lambda/Kappa architecture. Downstream: dashboards, ML features, funnels.
- **Real example:** Events → Kafka → Flink (real-time metrics) + S3 → Spark/warehouse (batch) → BI + feature store.
- **Use cases:** Funnels, A/B analysis, recommendation features, real-time dashboards.
- **Architecture:**
```
Client → Collector → [Kafka] ─┬→ Stream proc (Flink) → real-time metrics
                              └→ Data lake (S3) → Warehouse → BI/ML
```
- **Disadvantages:** Data volume/cost; exactly-once vs at-least-once; schema evolution; late/out-of-order events.
- **Competing tech:** Kafka/Kinesis, Flink/Spark Streaming, Snowflake/BigQuery/Redshift, dbt.

---

# PART C — Rapid-Fire Conceptual Q&A

Short answers to drill (each is a mini design prompt — expand out loud):

1. **Strong vs eventual consistency — pick for cart vs payment?** Cart: eventual (AP, always available). Payment/inventory: strong (correctness).
2. **How to prevent double order submission?** Idempotency key + unique constraint on (user, idempotency_key).
3. **Read-heavy catalog scaling?** CDN + Redis cache + read replicas + denormalized docs.
4. **Handle a hot key (celebrity product)?** Local cache + request coalescing + replicate the key across cache nodes.
5. **Sync catalog DB → search index?** Change Data Capture (Debezium) → Kafka → indexer (eventual consistency).
6. **Guarantee message processed once?** At-least-once delivery + idempotent consumers (true exactly-once is rare/expensive).
7. **Store product images?** Object storage (S3) + CDN; DB holds only URLs.
8. **Session storage across servers?** Externalize to Redis (stateless app servers).
9. **Rate-limit per user across a cluster?** Central Redis counter (token bucket) keyed by user.
10. **Multi-region availability?** Geo-DNS + regional replicas + async cross-region replication; conflict strategy for writes.
11. **Reduce checkout latency?** Async the non-critical work (email, analytics) via queue; only inventory+payment synchronous.
12. **Prevent oversell at scale?** Atomic conditional decrement + reservation with TTL.
13. **Search relevance signals?** Text match (BM25) + popularity + conversion rate + availability + margin.
14. **Cache invalidation strategy?** TTL + event-driven invalidation on writes; version keys.
15. **Outbox pattern — why?** Atomically persist state and the event to publish, avoiding dual-write inconsistency.

---

# PART D — The Long Tail (topics to expand into)

To grow this bank toward broad coverage, each of these becomes a full entry (same schema). This is the menu:

- **More building blocks:** distributed locks (Redlock), leader election (Zookeeper/Raft), gossip protocols, vector clocks, Merkle trees, write-ahead logs, LSM vs B-tree, backpressure, bulkheads, service mesh (Istio), feature flags, blue-green/canary deploys, DB connection pooling, read/write splitting, materialized views, time-series DBs, geospatial indexing, full-text ranking (BM25 deep dive), ANN indexes (HNSW/FAISS), data lake vs lakehouse, CDC internals, schema registry, dead-letter queues, exactly-once semantics, quorum tuning (R/W/N).
- **More e-commerce scenarios:** wishlist/save-for-later, buy-now-pay-later, subscriptions/recurring billing, gift cards & store credit, tax & currency (multi-region), address/geocoding service, seller/marketplace onboarding & payouts, returns/RMA & refunds, loyalty/points, abandoned-cart recovery, price-drop alerts, stock notifications ("notify me"), product Q&A, image similarity search ("shop the look"), size/fit recommendation, dynamic pricing engine, ad/sponsored-listings ranking, warehouse/WMS allocation, last-mile routing optimization, customer support/ticketing, chat/live support, A/B testing platform, feature store, GDPR/data-deletion pipeline, audit logging, multi-tenant seller isolation, catalog ingestion/bulk import, deduplication of listings, counterfeit detection.
- **Per-scenario variations:** each design at 3 scales (startup / mid / hyperscale), each with a cost lens, a failure-mode lens, and a "what breaks first" lens. This is how one design becomes ten meaningful questions.

---

## How to scale this bank (practically)

- **Batch expansion:** I can add ~30–50 fully-written entries per pass from the Part D menu — tell me which section to prioritize (building blocks vs scenarios) and I'll keep going.
- **In-app track:** I can wire this into the DailyPlanner Interview Prep page as a browsable, filterable, **editable** "System Design" track (like the behavioral bank) so you study and track progress in the app.
- **The honest math:** 45 core designs × (3 scales × 3 lenses) already yields ~400 genuinely distinct, high-value questions. That — not 5,000 stubs — is what actually gets you the offer.

> *"Simplicity is the ultimate sophistication."* Master these building blocks and you can design anything they throw at you.

---

# PART E — Databases, Data Platforms & Analytics at Scale

> The whole of this Part (plus Parts A–B) is also available as a **browsable, searchable, editable in-app track** on the DailyPlanner Interview Prep page. This section adds elaborate depth on the specifically-requested topics.

## E1. TiDB — Distributed NewSQL / HTAP (elaborate)
- **Problem it solves:** You've outgrown a single MySQL — you need horizontal write scale and ACID transactions, *and* you want fresh analytics on the same data without exporting to a separate warehouse. Traditional options force a choice: shard MySQL (app complexity, no cross-shard transactions) or bolt on a warehouse (stale, ETL-heavy).
- **How it works (architecture):** TiDB uses a **disaggregated, layered** design:
  - **TiDB (SQL layer):** stateless MySQL-compatible query nodes — parse, optimize, and route. Scale by adding nodes.
  - **TiKV (storage layer):** a distributed, transactional, **row-based** key-value store. Data is range-partitioned into **Regions** (~96MB), each **Raft-replicated** across 3+ nodes for strong consistency and auto-failover. Transactions use a **Percolator-style** two-phase commit with a global timestamp.
  - **TiFlash (columnar engine):** a **columnar** replica of TiKV data, kept in sync as a **Raft learner**. This is what makes it **HTAP** — the optimizer routes OLTP to TiKV (row) and OLAP scans to TiFlash (column), consistently, on live data.
  - **PD (Placement Driver):** the brain — stores metadata, hands out globally-ordered timestamps (**TSO**), and auto-rebalances Regions as load/data shifts.
- **Example (how it's implemented):** A payments/orders platform migrates from sharded MySQL: the app keeps speaking the MySQL protocol (minimal rewrite), transactions scale out on TiKV, and the analytics team runs revenue dashboards directly on TiFlash — **no nightly ETL, sub-second-fresh analytics.**
- **Use cases:** Scale-out OLTP beyond one MySQL, real-time HTAP, multi-region strong consistency, MySQL migrations without re-architecting.
- **Architecture:**
```
   App ──(MySQL protocol)──▶ [ TiDB SQL nodes (stateless) ]
                                    │            │
                          ┌─────────┘            └──────────┐
                          ▼                                 ▼
                  [ TiKV: row store ]  ──Raft learner──▶ [ TiFlash: columnar ]
                  (Regions, Raft x3, OLTP)                 (OLAP scans)
                          ▲
                   [ PD: metadata, TSO (timestamps), auto-rebalance ]
```
- **Disadvantages:** Many moving parts (heavier ops than one MySQL); distributed-transaction latency vs a local commit; TiFlash adds storage/compute; overkill for small workloads; a few MySQL features unsupported.
- **Competing technologies:** **CockroachDB, Google Spanner, YugabyteDB** (distributed SQL); **Vitess** (sharded MySQL, no HTAP); **SingleStore** (HTAP); **Snowflake / ClickHouse** for pure OLAP; **Aurora** for managed scale-up.

## E2. Aerospike — Real-time NoSQL at Scale (elaborate)
- **Problem it solves:** Serve **terabytes-to-petabytes** with **sub-millisecond** reads/writes at **very high throughput** (100k → millions ops/sec), reliably and cheaply — where Redis (RAM-bound) gets too expensive and disk databases are too slow.
- **How it works:** A distributed key-value/row store built around a **Hybrid Memory Architecture**: the **primary index lives in RAM** (fast lookups) while **data lives on SSD**, accessed **directly** (bypassing the filesystem/page cache) for near-in-memory latency at SSD cost/capacity. A **smart client** holds the cluster's **partition map** and talks **directly** to the owning node (no proxy hop). Data is sharded by consistent hashing, **synchronously replicated**, self-healing on node loss, and offers **strong-consistency** or high-availability modes. **Cross-Datacenter Replication (XDR)** gives global low latency.
- **Example:** A **real-time bidding** (ad-tech) service reads a user profile in **<1 ms** during the ad auction; or a **fraud/feature store** serving models at request time under a tight latency budget.
- **Use cases:** Real-time bidding, fraud detection, recommendation/feature stores, large session stores, any huge low-latency KV workload.
- **Architecture:**
```
  Smart client ──(partition map, direct)──▶ [ Aerospike node ]
                                              RAM: primary index
                                              SSD: record data (direct I/O)
                                              ── sync replica ──▶ peer node
                                              ── XDR ──▶ another datacenter
```
- **Disadvantages:** KV/row data model (limited joins/rich queries); specialized ops knowledge; enterprise features are licensed; overkill for small/low-QPS apps.
- **Competing technologies:** **Redis** (in-memory, smaller data), **DynamoDB**, **Cassandra/ScyllaDB**, **Couchbase**, **Memcached**.

## E3. Data Platforms at Scale (the big picture)
- **Problem it solves:** As data grows across many sources and teams, you need a platform that lands, stores, transforms, governs, and serves data for BI **and** ML — reliably, cheaply, and at scale.
- **The reference architecture (assemble the building blocks):**
```
  SOURCES            INGESTION          STORAGE (Lakehouse)        SERVE
  ┌────────┐   CDC   ┌────────┐   ┌───────────────────────────┐  ┌──────────┐
  │ OLTP DB│──────▶ │ Kafka /│──▶│ Bronze(raw)→Silver(clean)  │─▶│ Warehouse│▶ BI/dashboards
  │ Events │  events │ Kinesis│   │ →Gold(marts)  [Iceberg/    │  │  (OLAP)  │
  │ SaaS   │──batch─▶│ Airbyte│   │  Delta on S3/object store] │  ├──────────┤
  │ Logs   │         └────────┘   └───────────────────────────┘  │ Feature  │▶ ML models
  └────────┘              │   ┌──────────┐          ▲             │  store   │
                          └──▶│ Flink    │─realtime─┘             ├──────────┤
                              │ (stream) │                         │ Reverse  │▶ back to apps
                              └──────────┘                         │  ETL     │
        Orchestration: Airflow/Dagster · Transform: dbt/Spark · Governance/Catalog: Unity/DataHub
```
- **The layers explained:**
  - **Ingestion:** batch (Airbyte/Fivetran) + streaming (**Kafka**) + **CDC** (Debezium) from OLTP.
  - **Storage — the Lakehouse:** cheap object storage + a **table format (Iceberg/Delta/Hudi)** giving ACID, schema evolution, time travel. Layered **Bronze → Silver → Gold** (medallion).
  - **Processing:** **batch** (Spark) for heavy transforms, **stream** (Flink) for real-time; orchestrated by **Airflow/Dagster**, modeled with **dbt**.
  - **Serving:** **warehouse/OLAP** (Snowflake/BigQuery/ClickHouse) for BI; **feature store** for ML; **reverse-ETL** to push insights back to apps.
  - **Governance:** catalog, lineage, access control (Unity Catalog, DataHub, Amundsen).
- **Architectural styles:** **Lambda** (batch + speed layers) vs **Kappa** (one streaming path); **centralized platform** vs **Data Mesh** (domain-owned data products).
- **Disadvantages:** Real complexity and cost; many tools to integrate/operate; governance and data quality are ongoing battles; skills-intensive.
- **Competing technologies:** **Databricks** (lakehouse), **Snowflake** (warehouse-first), **BigQuery/Redshift/Synapse**, **open stack** (Iceberg + Spark/Trino + Kafka + Airflow + dbt).

## E4. Data Analytics — the landscape
- **Problem it solves:** Turning raw data into decisions — dashboards, ad-hoc analysis, real-time signals, and experiments — without hammering production systems.
- **The spectrum:**
  - **OLTP vs OLAP:** transactions (row store, current data) vs analytics (**columnar, MPP**, history). Separate them; move data via ETL/CDC.
  - **Batch analytics:** scheduled transforms over big datasets → **warehouse** → **BI dashboards** (Tableau/Looker/Power BI/Superset) over a **semantic layer** (consistent metric definitions).
  - **Real-time/streaming analytics:** **Kafka → Flink → real-time OLAP (Druid/Pinot/ClickHouse) → live dashboards**, with windowing and watermarks for late events.
  - **Product analytics:** clickstream funnels, retention, cohorts (Amplitude/Segment).
  - **Experimentation:** **A/B testing platforms** with proper randomization, guardrails, and statistics.
  - **ETL vs ELT:** transform-before-load vs load-raw-then-transform-in-warehouse (**ELT** is the modern default via dbt).
- **Example:** During a sale, a **real-time GMV + 'trending now'** dashboard is computed by Flink from the clickstream (seconds-fresh), while **cohort/retention** reports run as nightly dbt models in Snowflake (batch).
- **Architecture:**
```
  Events ─▶ Kafka ─┬─▶ Flink ─▶ real-time OLAP (Druid) ─▶ live dashboards
                   └─▶ Lake ─▶ warehouse (dbt models) ─▶ BI + experiments
```
- **Disadvantages:** Two paths (batch+stream) to maintain; metric governance (everyone must agree what "active user" means); streaming state/exactly-once complexity; cost at volume.
- **Competing technologies:** Snowflake/BigQuery/Redshift/ClickHouse; Flink/Spark/Materialize; Druid/Pinot; Looker/Tableau/Power BI/Superset; dbt; Optimizely/Statsig.

## E5. Common Data Model (Canonical Data Model) — elaborate
- **Problem it solves:** In a big enterprise, every system defines core entities differently — CRM's "Customer" ≠ billing's "Account" ≠ the webshop's "User". Integrating **N systems point-to-point** needs **N×(N−1) mappings**, analytics can't join across systems, and every new integration is bespoke pain.
- **How it works:** Define a **single shared, standardized schema** for core business entities (Customer, Product, Order, Address...) that **every system maps to once**. Integrations translate **to/from the canonical model**, turning **N-to-N mappings into N-to-1**. It's a design pattern (canonical model in an ESB/iPaaS or MDM), and there are ready-made industry CDMs:
  - **Microsoft Common Data Model / Dataverse** — standardized entities for business apps (Power Platform, Dynamics).
  - **OMOP** (health data), **FHIR** (healthcare interop), **ARTS/ARTS ODM** (retail), **ACORD** (insurance).
- **Example:** An enterprise defines a canonical **Customer**; CRM, billing, support, and the webshop each write one mapping to it. Now a **Customer-360** view and cross-system analytics "just work," and adding a new SaaS tool means writing **one** mapping, not integrating with everything.
- **Use cases:** Enterprise application integration (canonical model in the message bus), **Master Data Management (MDM)**, data-warehouse conformance (conformed dimensions), partner/EDI exchange, unifying microservice data for a single analytical view.
- **Architecture:**
```
  CRM ──map──┐                      ┌──map── Billing
             ▼                      ▼
        [  CANONICAL DATA MODEL (Customer, Order, Product) ]
             ▲                      ▲
  Webshop ─map┘                     └─map── Support
        (each system maps ONCE → N-to-1, not N-to-N)
```
- **Disadvantages:** Significant upfront design + ongoing **governance**; a rigid canonical model can lag fast-changing business needs; risk of over-generalizing (a "Customer" that fits everything fits nothing well); needs a clear owner.
- **Competing technologies:** **Point-to-point mapping** (simple, doesn't scale); **Microsoft CDM/Dataverse**; industry standards (OMOP/FHIR/ARTS/ACORD); **MDM tools** (Informatica, Reltio); **data-contract / semantic-layer** approaches (a more modern, decentralized take).

## E6. Data Modeling — quick reference
- **Dimensional modeling (Kimball):** facts (measurable events) + dimensions (context) in **star/snowflake** schemas — the BI workhorse.
- **Normalization vs denormalization:** integrity/write-efficiency (OLTP) vs read speed (OLAP/NoSQL); choose by read/write ratio.
- **Slowly Changing Dimensions (SCD):** Type 1 (overwrite), **Type 2** (new row + effective dates = full history), Type 3 (previous-value column). Type 2 is standard for point-in-time analytics.
- **Data Vault:** hubs/links/satellites — auditable, flexible enterprise warehouse modeling.
- **3NF (Inmon)** vs **star (Kimball)** vs **One Big Table** — pick per query patterns and governance needs.

> *"Data is a precious thing and will last longer than the systems themselves."* — Tim Berners-Lee. Model it well and everything downstream gets easier.
