"""Java bank — concurrency and the JVM.

The two rungs that were one entry each. Both are where a mid-level interview
separates from a junior one, and both are full of behaviour that is documented,
surprising, and silent when you get it wrong — which is exactly the shape this
bank's `gotcha` field exists for.

Same contract as java_bank_core.py: build(Q) receives the constructor, so the
required-field rules apply here identically.
"""


def build(Q):
    return [

    # ══════════════════════════════════════════════════════════════════
    #  Concurrency
    # ══════════════════════════════════════════════════════════════════

    Q("concurrency",
      "ExecutorService — the four ways a thread pool bites you",
      "Creating a thread by hand for every job is expensive and unbounded: a "
      "thousand jobs means a thousand threads and the machine falls over. A "
      "thread pool keeps a small fixed set of workers and feeds them jobs from "
      "a queue. That is almost always what you want, and the standard factory "
      "methods hide four decisions that matter enormously — how many threads, "
      "how big the queue, what happens when it is full, and what happens to an "
      "exception.",
      "ThreadPoolExecutor has a core size, a max size, a keep-alive, a QUEUE and "
      "a REJECTION POLICY. The Executors factory methods pick these for you and "
      "the defaults are dangerous: newFixedThreadPool uses an UNBOUNDED "
      "LinkedBlockingQueue, so under overload the queue grows until the heap "
      "does not; newCachedThreadPool has an unbounded THREAD count instead. "
      "SIZING: roughly N cores for CPU-bound work, and far higher for IO-bound, "
      "since threads spend most of their time blocked. LIFECYCLE: pool threads "
      "are non-daemon by default, so an executor you never shut down KEEPS THE "
      "JVM ALIVE after main returns.",
      ["concurrency", "executor", "thread-pool", "sizing"],
      code="import java.util.concurrent.*;\n\n// The convenient factory — and its unbounded queue\nExecutorService lazy = Executors.newFixedThreadPool(4);\n\n// What you should usually write instead: every decision made on purpose\nExecutorService pool = new ThreadPoolExecutor(\n    4, 4,                                   // core, max\n    60L, TimeUnit.SECONDS,                  // keep-alive for extra threads\n    new ArrayBlockingQueue<>(1000),         // BOUNDED — back-pressure, not OOM\n    new ThreadPoolExecutor.CallerRunsPolicy() // full? the submitter does the work\n);\n\n// THE EXCEPTION TRAP — submit() vs execute()\npool.submit(() -> { throw new RuntimeException(\"vanishes\"); });\npool.execute(() -> { throw new RuntimeException(\"reaches the handler\"); });\n\n// Shutdown is TWO steps, and the second is the one people omit\npool.shutdown();                            // stop accepting; finish the queue\ntry {\n    if (!pool.awaitTermination(30, TimeUnit.SECONDS)) {\n        pool.shutdownNow();                 // interrupt what is still running\n    }\n} catch (InterruptedException e) {\n    pool.shutdownNow();\n    Thread.currentThread().interrupt();     // RESTORE the flag — see the trap\n}",
      output="(the execute() task prints a stack trace to stderr via the thread's\n uncaught-exception handler; the submit() task prints NOTHING AT ALL —\n its exception is captured in the returned Future and is only seen if\n someone calls get() on it)",
      gotcha="Q: a task submitted with submit() throws. Where does the exception go?  "
             "NOWHERE VISIBLE. submit() wraps the task in a FutureTask, which CATCHES "
             "the throwable and stores it in the Future to be rethrown from get(). If "
             "you ignore the returned Future — and everyone ignores it for "
             "fire-and-forget work — the exception is silently swallowed and the task "
             "just appears not to have run. execute() has no Future, so the exception "
             "reaches the thread's uncaught handler and gets logged. THE SAME TASK, "
             "SUBMITTED TWO WAYS, FAILS LOUDLY OR SILENTLY.",
      version="ExecutorService: Java 5. CompletableFuture: 8. Executors."
              "newVirtualThreadPerTaskExecutor(): Java 21 — with virtual threads the "
              "pool-sizing question largely disappears for IO-bound work, because "
              "blocking is no longer expensive.",
      quiz={
          "q": "Why is Executors.newFixedThreadPool(4) risky under sustained overload?",
          "options": [
              "Its queue is unbounded, so tasks pile up until the heap is exhausted",
              "It creates unbounded threads, so the OS runs out of native threads",
              "It rejects tasks silently once four are running",
              "It is not risky — four threads is a hard cap on all resource use",
          ],
          "answer": 0,
          "why": "Option A is right: the THREADS are capped and the QUEUE is not, so "
                 "back-pressure never reaches the producer and memory grows instead. "
                 "Option B describes newCachedThreadPool, which has the opposite "
                 "failure — unbounded threads with a zero-capacity handoff queue — and "
                 "confusing the two is the common mistake. Option C invents silent "
                 "rejection; the default policy throws RejectedExecutionException, and "
                 "only once the queue is full, which here it never is. Option D is the "
                 "reasoning that causes the outage: capping threads does not cap "
                 "memory.",
      },
      complexity="CPU-bound: threads ≈ cores (Runtime.availableProcessors()). IO-bound: "
                 "cores × (1 + wait/compute), which is often 50-200 — measure rather "
                 "than guess. Each PLATFORM thread costs ~512KB-1MB of stack, which is "
                 "why 10,000 of them is not an option and why virtual threads exist.",
      pitfalls="Swallowing InterruptedException without restoring the flag "
               "(`Thread.currentThread().interrupt()`) breaks cancellation for every "
               "caller above you — the exception CLEARS the interrupt status, so not "
               "restoring it destroys the signal. And submitting a task that itself "
               "waits on another task in the SAME single-threaded pool deadlocks "
               "instantly.",
      followups="What does CallerRunsPolicy actually buy? Back-pressure. The submitting "
                "thread executes the task itself, so it stops submitting while it is "
                "busy — which slows the producer down instead of dropping work or "
                "growing the queue. It is the most useful of the four built-in "
                "policies.",
      difficulty="Medium", frequency="Very common at mid level",
      mnemonic="Fixed pool = bounded threads, UNBOUNDED queue. submit() hides exceptions."),

    Q("concurrency",
      "Deadlock — the four conditions, and the one-line fix",
      "A deadlock is two threads each holding something the other needs, so "
      "neither can move. Thread A holds lock 1 and wants lock 2; thread B holds "
      "lock 2 and wants lock 1. Both wait forever, the program does not crash, "
      "and nothing appears in the logs — it simply stops. The standard fix is "
      "boringly simple: make every thread take the locks in the SAME ORDER, and "
      "the cycle becomes impossible.",
      "Four conditions must ALL hold: mutual exclusion, hold-and-wait, no "
      "preemption, and CIRCULAR WAIT. Break any one and deadlock cannot occur — "
      "and circular wait is the cheapest to break, by imposing a GLOBAL LOCK "
      "ORDERING (by identity hash, by ID, by any total order) so no cycle can "
      "form. Alternatives: acquire with tryLock and a timeout so a thread can "
      "back off and retry; reduce the lock's scope so nothing is held while "
      "another is taken; or remove the shared mutable state entirely. Java "
      "detects nothing at runtime — a jstack thread dump WILL identify it, and "
      "it is the first thing to run against a hung JVM.",
      ["concurrency", "deadlock", "locks", "debugging"],
      code="// GUARANTEED deadlock: two accounts, two threads, opposite order\nclass Account {\n    final int id;\n    double balance;\n    Account(int id, double b) { this.id = id; this.balance = b; }\n}\n\n// WRONG — the order depends on the arguments\nstatic void transferBad(Account from, Account to, double amt) {\n    synchronized (from) {\n        synchronized (to) { from.balance -= amt; to.balance += amt; }\n    }\n}\n// transferBad(a, b) and transferBad(b, a) running at once = deadlock\n\n// RIGHT — a TOTAL ORDER, so no cycle can form\nstatic void transferGood(Account from, Account to, double amt) {\n    Account first  = from.id < to.id ? from : to;\n    Account second = from.id < to.id ? to   : from;\n    synchronized (first) {\n        synchronized (second) { from.balance -= amt; to.balance += amt; }\n    }\n}\n\n// The other approach: back off instead of blocking\nimport java.util.concurrent.locks.*;\nstatic boolean transferTry(ReentrantLock a, ReentrantLock b) throws Exception {\n    if (a.tryLock(50, java.util.concurrent.TimeUnit.MILLISECONDS)) {\n        try {\n            if (b.tryLock(50, java.util.concurrent.TimeUnit.MILLISECONDS)) {\n                try { return true; } finally { b.unlock(); }\n            }\n        } finally { a.unlock(); }\n    }\n    return false;                    // caller retries, possibly with a jitter\n}",
      output="(transferBad deadlocks: both threads block forever, CPU at zero, no\n exception, no log line. `jstack <pid>` prints \"Found one Java-level\n deadlock\" and names both threads and both monitors. transferGood and\n transferTry always complete.)",
      gotcha="Q: what does a deadlocked Java program look like from outside?  PERFECTLY "
             "HEALTHY AND COMPLETELY STOPPED. No exception, no error, no log line, and "
             "CPU usage at ZERO rather than pegged — which is the opposite of what "
             "people look for. An infinite loop burns a core and is obvious; a deadlock "
             "burns nothing. If a JVM has gone quiet and idle, run `jstack` before "
             "anything else: it detects Java-level deadlocks explicitly and names the "
             "threads and monitors involved.",
      version="ReentrantLock and tryLock: Java 5. Virtual threads (21) do not change "
              "any of this — a deadlock between virtual threads deadlocks identically, "
              "and `synchronized` can additionally PIN a virtual thread to its carrier.",
      quiz={
          "q": "Which single change makes deadlock IMPOSSIBLE in the transfer example?",
          "options": [
              "Always acquire the two locks in a globally consistent order",
              "Make the balance field volatile so no lock is needed",
              "Synchronize the whole method instead of the two objects",
              "Use a ConcurrentHashMap to hold the accounts",
          ],
          "answer": 0,
          "why": "Option A breaks CIRCULAR WAIT, and with any one of the four "
                 "conditions gone deadlock cannot occur. Option B confuses visibility "
                 "with atomicity — a volatile double still cannot be read-modify-"
                 "written atomically, so it removes the deadlock by introducing a race. "
                 "Option C would work by accident (one global lock, no second lock to "
                 "wait for) at the cost of serialising every transfer in the system, "
                 "which is why nobody does it. Option D changes where the accounts are "
                 "STORED and nothing about how they are locked.",
      },
      pitfalls="LIVELOCK is deadlock's cousin: threads keep responding to each other "
               "and make no progress — two people stepping aside in a corridor. "
               "tryLock-and-retry without a RANDOMISED backoff produces exactly that. "
               "And nested synchronized blocks in library code you do not control can "
               "form a cycle with yours that neither side can see.",
      followups="Can you deadlock with one lock? Yes — a thread waiting on a condition "
                "that only it could signal, or a single-threaded executor whose task "
                "waits on another task submitted to the same executor. Deadlock needs a "
                "cycle in the WAIT-FOR graph, and that graph includes more than "
                "monitors.",
      difficulty="Medium", frequency="Very common",
      mnemonic="Same locks, SAME ORDER, no cycle. Quiet and idle means jstack."),

    Q("concurrency",
      "ConcurrentHashMap and friends — and why null is forbidden",
      "A HashMap breaks under concurrent use, and wrapping it in "
      "Collections.synchronizedMap makes every operation take one global lock, "
      "which is correct and slow. ConcurrentHashMap locks per BIN instead, so "
      "threads touching different keys never wait for each other. It also "
      "refuses to store null — which looks arbitrary until you see why it is "
      "forced by the concurrency, not a style choice.",
      "ConcurrentHashMap locks per bin: a CAS to install the first node in an "
      "empty bin, and `synchronized` on the head node otherwise, so contention "
      "is proportional to collisions rather than to traffic. Iterators are "
      "WEAKLY CONSISTENT — they never throw ConcurrentModificationException and "
      "may or may not reflect concurrent updates. size() is an estimate. NULL "
      "KEYS AND VALUES ARE FORBIDDEN because `get(k) == null` would be ambiguous "
      "between 'absent' and 'mapped to null', and in a concurrent map there is "
      "no way to disambiguate with containsKey without a race in between. "
      "CopyOnWriteArrayList copies the whole array on every write — right for "
      "listener lists, catastrophic for anything write-heavy. BlockingQueue is "
      "the producer-consumer primitive and gives you back-pressure for free.",
      ["concurrency", "concurrenthashmap", "collections", "null"],
      code="import java.util.concurrent.*;\nimport java.util.*;\n\nConcurrentHashMap<String,Integer> m = new ConcurrentHashMap<>();\n\n// m.put(\"k\", null);        // NullPointerException — see the trap\n// m.put(null, 1);          // NullPointerException\n\n// ATOMIC compound operations — the reason to use it over a lock\nm.putIfAbsent(\"a\", 1);\nm.merge(\"a\", 10, Integer::sum);          // read-modify-write, atomically\nm.compute(\"a\", (k, v) -> v == null ? 1 : v * 2);\nSystem.out.println(m);\n\n// THIS IS NOT ATOMIC — two threads can both see absent and both put\nif (!m.containsKey(\"b\")) m.put(\"b\", 1);   // check-then-act: a race\nm.putIfAbsent(\"b\", 1);                    // the atomic equivalent\n\n// Right tool for a listener list: many reads, almost no writes\nList<String> listeners = new CopyOnWriteArrayList<>();\nlisteners.add(\"one\");\nfor (String s : listeners) listeners.add(\"safe — the iterator sees a snapshot\");\nSystem.out.println(listeners.size());\n\n// Producer-consumer with back-pressure built in\nBlockingQueue<String> q = new ArrayBlockingQueue<>(100);\nq.offer(\"job\");\nSystem.out.println(q.poll());",
      output="{a=22}\n2\njob",
      gotcha="Q: why does ConcurrentHashMap forbid null values when HashMap allows "
             "them?  BECAUSE `get(k) == null` WOULD BE UNANSWERABLE. In a HashMap you "
             "disambiguate with containsKey(k), and that works because nothing changes "
             "in between. In a CONCURRENT map another thread can insert or remove "
             "between your get and your containsKey, so the two answers need not agree "
             "and there is no atomic way to ask both. Doug Lea's stated reason is that "
             "the ambiguity cannot be resolved, so the map refuses to create it. "
             "IT IS A CONSEQUENCE OF CONCURRENCY, NOT A PREFERENCE.",
      version="ConcurrentHashMap rewritten in Java 8 — segment locking replaced by "
              "per-bin CAS plus synchronized, and merge/compute/forEach/reduce added. "
              "ConcurrentHashMap.newKeySet() gives the concurrent Set that Java "
              "otherwise lacks.",
      quiz={
          "q": "Two threads run `if (!map.containsKey(k)) map.put(k, v);` on a "
               "ConcurrentHashMap. What can go wrong?",
          "options": [
              "Both can see the key absent and both put — check-then-act is not atomic, even on a concurrent map",
              "Nothing — ConcurrentHashMap makes every sequence of calls atomic",
              "It throws ConcurrentModificationException",
              "One thread blocks until the other finishes the whole if-statement",
          ],
          "answer": 0,
          "why": "Option A is right and it is the most important thing to understand "
                 "about concurrent collections: each INDIVIDUAL call is atomic, and a "
                 "SEQUENCE of them is not. putIfAbsent exists precisely for this. "
                 "Option B is the assumption that causes the bug — 'concurrent' in the "
                 "class name does not extend across statements. Option C is what a "
                 "plain HashMap's iterator would do; CHM's iterators are weakly "
                 "consistent and never throw it. Option D imagines a lock spanning the "
                 "caller's code, which no collection can provide.",
      },
      complexity="CHM get is lock-free; put contends only with other threads hitting "
                 "the SAME bin. CopyOnWriteArrayList: reads are free and lock-free, "
                 "every write is O(n) — so it is right for a listener list read "
                 "constantly and written at startup, and disastrous for anything else.",
      pitfalls="computeIfAbsent's mapping function MUST NOT modify the same map — it "
               "runs while the bin is locked and doing so can deadlock or corrupt the "
               "table, and the Javadoc forbids it explicitly. size() and isEmpty() are "
               "estimates under concurrent modification; do not use them for control "
               "flow.",
      followups="When is Collections.synchronizedMap still right? When you need to hold "
                "the lock ACROSS several operations — you can synchronize on the "
                "returned map yourself, which CHM gives you no way to do. That is the "
                "one thing the old wrapper can do and the concurrent map cannot.",
      difficulty="Medium", frequency="Very common",
      mnemonic="Each call atomic, sequences not. No nulls, because get()==null would be ambiguous."),

    Q("concurrency",
      "CompletableFuture — composing async work without blocking",
      "A plain Future can only be asked 'are you done yet', which means someone "
      "has to sit and wait. CompletableFuture lets you say what should happen "
      "AFTER a result arrives, and chain those steps together, so no thread is "
      "parked doing nothing. The catch is that the callbacks run on a shared "
      "pool by default, and if you put blocking work there you starve everything "
      "else in the JVM that uses it.",
      "CompletableFuture is a Future plus a completion callback API: thenApply "
      "(transform), thenCompose (flatMap — chain another future), thenCombine "
      "(join two), allOf/anyOf (fan-in). WITHOUT AN EXPLICIT EXECUTOR the async "
      "variants run on ForkJoinPool.commonPool(), which is sized to cores − 1 "
      "and is SHARED WITH PARALLEL STREAMS AND THE REST OF THE JVM — blocking "
      "there starves unrelated code. EXCEPTIONS travel down the chain: a failure "
      "skips every thenApply and lands at the first exceptionally/handle. join() "
      "throws unchecked CompletionException; get() throws checked "
      "ExecutionException, which is why join() is usually the one you want in a "
      "lambda.",
      ["concurrency", "completablefuture", "async", "forkjoin"],
      code="import java.util.concurrent.*;\n\nExecutorService io = Executors.newFixedThreadPool(8);\n\n// ALWAYS pass your own executor for blocking work — see the trap\nCompletableFuture<String> a = CompletableFuture.supplyAsync(() -> \"user\", io);\nCompletableFuture<String> b = CompletableFuture.supplyAsync(() -> \"orders\", io);\n\nCompletableFuture<String> both = a.thenCombine(b, (x, y) -> x + \"+\" + y);\n\nCompletableFuture<String> chained = both\n    .thenApply(String::toUpperCase)                  // transform\n    .thenCompose(s -> CompletableFuture.supplyAsync(() -> s + \"!\", io))\n    .exceptionally(ex -> \"fallback: \" + ex.getMessage());\n\nSystem.out.println(chained.join());\n\n// A failure SKIPS every thenApply and lands at the handler\nCompletableFuture<String> failed = CompletableFuture\n    .<String>supplyAsync(() -> { throw new IllegalStateException(\"boom\"); }, io)\n    .thenApply(s -> { System.out.println(\"never runs\"); return s; })\n    .exceptionally(ex -> \"recovered from \" + ex.getCause().getMessage());\nSystem.out.println(failed.join());\n\nio.shutdown();",
      output="USER+ORDERS!\nrecovered from boom",
      gotcha="Q: `CompletableFuture.supplyAsync(() -> blockingHttpCall())` with no "
             "executor — what is the risk?  IT RUNS ON ForkJoinPool.commonPool(), WHICH "
             "IS SHARED BY THE WHOLE JVM — every parallel stream, every other "
             "CompletableFuture that also omitted an executor, and any library doing "
             "the same. The pool is sized to CORES MINUS ONE, so on a 4-core box that "
             "is three threads: three concurrent blocking calls and everything else in "
             "the process stops. ALWAYS PASS AN EXECUTOR FOR ANYTHING THAT BLOCKS, and "
             "the common pool is for short CPU-bound work only.",
      version="CompletableFuture: Java 8. orTimeout / completeOnTimeout: Java 9. With "
              "virtual threads (21) the calculus changes — "
              "Executors.newVirtualThreadPerTaskExecutor() makes blocking cheap, and "
              "structured concurrency (preview) is the intended successor for fan-out.",
      quiz={
          "q": "What is the difference between thenApply and thenCompose?",
          "options": [
              "thenApply maps the value; thenCompose chains another CompletableFuture and flattens it",
              "thenApply is synchronous and thenCompose is asynchronous",
              "thenCompose runs on the common pool; thenApply runs on the calling thread",
              "They are aliases — thenCompose is the older name kept for compatibility",
          ],
          "answer": 0,
          "why": "Option A is right: it is map versus flatMap. Using thenApply where "
                 "the function itself returns a future gives you a "
                 "CompletableFuture<CompletableFuture<T>>, which is the usual symptom "
                 "of picking the wrong one. Option B confuses the pair with their "
                 "…Async suffixed variants — that is what the suffix controls, not the "
                 "name. Option C invents a per-method pool rule; both run on whichever "
                 "thread completed the previous stage unless you use the Async form. "
                 "Option D is invented.",
      },
      pitfalls="A CompletableFuture is NOT cancelled by cancel() the way a Future on an "
               "executor is — cancel() completes it exceptionally but does not interrupt "
               "the running task. And a chain with no terminal join/get and no side "
               "effect can complete after your method returns, so exceptions surface "
               "in a log at an unrelated moment.",
      followups="Why join() rather than get()? join() throws the unchecked "
                "CompletionException, so it can be used inside a lambda without a "
                "try/catch; get() throws checked ExecutionException and "
                "InterruptedException, which a functional interface cannot declare.",
      difficulty="Hard", frequency="Common at mid/senior level",
      mnemonic="thenApply = map, thenCompose = flatMap. Never block on the common pool."),

    Q("concurrency",
      "Virtual threads (Java 21) — what actually changed",
      "Until Java 21, every Java thread was an operating-system thread: about a "
      "megabyte of stack, expensive to create, and blocking one wasted it "
      "entirely. That is why servers used thread pools and why 'never block' "
      "became a rule. A virtual thread is managed by the JVM instead of the OS "
      "— you can have millions, and when one blocks the JVM parks it and reuses "
      "the underlying OS thread for something else. Blocking stopped being "
      "expensive, which undoes the reason most async code was written.",
      "A virtual thread is a Thread whose stack lives on the HEAP and which is "
      "MOUNTED onto a carrier (platform) thread only while running. On a "
      "blocking call the JVM UNMOUNTS it, copies its stack out, and frees the "
      "carrier — so blocking costs memory rather than a thread. Creation is "
      "microseconds and a few hundred bytes against ~1MB and milliseconds. THE "
      "PROGRAMMING MODEL RETURNS TO thread-per-request with ordinary blocking "
      "code, which is readable and debuggable in a way callback chains are not. "
      "THE LIMITS: a virtual thread is PINNED to its carrier inside a "
      "`synchronized` block or a native call, so a blocking call there does "
      "consume a carrier — use ReentrantLock instead. And thread POOLS become "
      "pointless: create one virtual thread per task.",
      ["concurrency", "virtual-threads", "loom", "modern-java"],
      code="import java.util.concurrent.*;\nimport java.time.*;\n\n// One virtual thread per task — pooling them defeats the point\ntry (var exec = Executors.newVirtualThreadPerTaskExecutor()) {\n    for (int i = 0; i < 10_000; i++) {\n        exec.submit(() -> {\n            Thread.sleep(Duration.ofSeconds(1));   // blocking is FINE now\n            return null;\n        });\n    }\n}   // close() waits for all of them — try-with-resources on an ExecutorService\n    // is itself a Java 19+ addition\n\n// Directly:\nThread v = Thread.ofVirtual().name(\"worker\").start(() ->\n    System.out.println(Thread.currentThread()));\nv.join();\n\n// PINNING: inside synchronized, a blocking call holds the carrier\nfinal Object lock = new Object();\nRunnable pinned = () -> {\n    synchronized (lock) {\n        try { Thread.sleep(1000); } catch (InterruptedException e) {}\n    }\n};\n// ReentrantLock does NOT pin — prefer it in virtual-thread code",
      output="VirtualThread[#21,worker]/runnable@ForkJoinPool-1-worker-1\n\n(10,000 virtual threads each sleeping a second complete in a little over\n one second. Ten thousand PLATFORM threads would need ~10GB of stack and\n would not start.)",
      gotcha="Q: virtual threads are cheap, so should you pool them?  NO — and this is "
             "the single most common mistake when adopting them. A pool exists to reuse "
             "something EXPENSIVE to create; a virtual thread costs microseconds and a "
             "few hundred bytes. Pooling them reintroduces the exact bottleneck they "
             "removed: the pool size caps concurrency again. Create one per task. "
             "`Executors.newVirtualThreadPerTaskExecutor()` is named the way it is on "
             "purpose — it is not a pool, it is a factory that happens to implement "
             "ExecutorService.",
      version="Preview in 19 and 20, FINAL IN JAVA 21. Structured concurrency and "
              "scoped values are the companion features and are still preview as of 21. "
              "Java 24 (JEP 491) removes most `synchronized` pinning, which is the main "
              "remaining sharp edge.",
      quiz={
          "q": "Which of these still blocks a CARRIER thread when a virtual thread "
               "waits?",
          "options": [
              "Blocking inside a synchronized block — the virtual thread is pinned",
              "Any call to Thread.sleep",
              "Reading from a socket via the standard java.net APIs",
              "Waiting on a ReentrantLock",
          ],
          "answer": 0,
          "why": "Option A is the remaining sharp edge, and the reason ReentrantLock is "
                 "preferred over synchronized in virtual-thread code. Options B and C "
                 "were both retrofitted to unmount the virtual thread — that "
                 "retrofitting of the entire JDK's blocking APIs was most of the work "
                 "in Project Loom, and it is why existing blocking code just works. "
                 "Option D also unmounts correctly; java.util.concurrent locks were "
                 "made virtual-thread-aware from the start.",
      },
      complexity="Platform thread: ~1MB stack, ~1ms to create, tens of thousands is the "
                 "practical ceiling. Virtual thread: a few hundred bytes growing on "
                 "demand, ~1µs to create, MILLIONS are fine. Throughput on CPU-bound "
                 "work is UNCHANGED — you still only have as many cores as you have. "
                 "The win is entirely on blocking, IO-bound workloads.",
      pitfalls="ThreadLocal on millions of virtual threads is a memory problem that did "
               "not exist when threads were scarce — scoped values are the replacement. "
               "And code that assumed `Thread.currentThread()` identified a pooled "
               "worker (for logging, for caching) now sees a different thread every "
               "request.",
      followups="Does this make reactive programming obsolete? For the common case of "
                "'handle many concurrent IO-bound requests', largely yes — that was "
                "reactive's main selling point and it came at a heavy cost in "
                "readability and debuggability. Reactive still wins where you genuinely "
                "need streaming back-pressure over an unbounded source.",
      difficulty="Medium", frequency="Increasingly common — expected on Java 21",
      mnemonic="Blocking got cheap. So stop pooling, and stop using synchronized."),

    # ══════════════════════════════════════════════════════════════════
    #  JVM, memory & performance
    # ══════════════════════════════════════════════════════════════════

    Q("jvm",
      "Garbage collection — the generational hypothesis, and which collector to pick",
      "Most objects die almost immediately: a temporary string, a loop "
      "variable, an object built and discarded inside one method call. Java's "
      "collectors are built entirely around that observation. New objects go "
      "into a small nursery which is collected very often and very cheaply, "
      "because nearly everything in it is already garbage. The few that survive "
      "get promoted to a larger area collected rarely. That split is why Java's "
      "allocation is fast despite the collector.",
      "THE WEAK GENERATIONAL HYPOTHESIS: most objects die young, and few "
      "references point from old objects to young ones. So the heap splits into "
      "a YOUNG generation (Eden plus two survivor spaces) and an OLD generation. "
      "A MINOR GC copies the few live objects out of Eden — cost is proportional "
      "to what SURVIVES, not to what was allocated, which is why allocating "
      "short-lived garbage is nearly free. Surviving several minor GCs promotes "
      "an object to old. A MAJOR/FULL GC collects old and is far more expensive. "
      "COLLECTORS: G1 (default since 9) balances throughput and pause, targeting "
      "a pause goal; PARALLEL maximises throughput and does not care about "
      "pauses; ZGC and SHENANDOAH are mostly-concurrent with sub-millisecond "
      "pauses that scale independently of heap size; SERIAL is for tiny heaps "
      "and containers.",
      ["jvm", "gc", "memory", "tuning"],
      code="// Nothing here is a Java API — GC is configured with FLAGS, and\n// knowing the flags is most of the practical knowledge.\n\n//   -XX:+UseG1GC              default since Java 9\n//   -XX:MaxGCPauseMillis=200  G1's pause GOAL, not a guarantee\n//   -XX:+UseZGC               sub-millisecond pauses, larger footprint\n//   -XX:+UseParallelGC        best raw throughput, longest pauses\n//   -Xmx4g -Xms4g             SET THEM EQUAL in a container: resizing the\n//                             heap at runtime is pure jitter\n//   -Xlog:gc*                 Java 9+ unified logging (was -XX:+PrintGCDetails)\n\n// Allocation is a POINTER BUMP in a thread-local buffer, which is why this\n// costs far less than the equivalent in a reference-counted language:\nfor (int i = 0; i < 1_000_000; i++) {\n    String tmp = \"item \" + i;      // allocated, dead by the next iteration\n}\n// A minor GC copies only the SURVIVORS, so a loop producing pure garbage\n// costs close to nothing to collect.\n\n// The one thing you should almost never write:\n// System.gc();   // a SUGGESTION the JVM may ignore, and a full GC if honoured",
      output="(no output — this entry is about behaviour and flags. Run with\n -Xlog:gc and the million-iteration loop above prints several\n \"Pause Young (Normal)\" lines of a millisecond or two each, and no\n full GC at all.)",
      gotcha="Q: does allocating a million short-lived objects hurt?  ALMOST NOT AT "
             "ALL, and the reason is counter-intuitive: minor GC cost is proportional "
             "to what SURVIVES, not to what was allocated. A loop producing pure "
             "garbage leaves nothing to copy, so the collection is nearly free and "
             "allocation itself is a pointer bump in a thread-local buffer. THE "
             "EXPENSIVE OBJECT IS THE ONE THAT SURVIVES LONG ENOUGH TO BE PROMOTED — "
             "which is why a badly-sized cache hurts far more than a hot loop full of "
             "temporaries.",
      version="G1 default since Java 9 (Parallel before). ZGC production-ready in 15, "
              "generational ZGC in 21. CMS removed in 14. Metaspace replaced PermGen in "
              "8. Java 10+ is container-aware: it reads cgroup limits rather than the "
              "host's memory, which is why an old JVM in Docker used to OOM the "
              "container.",
      quiz={
          "q": "Why is a minor GC usually cheap even after allocating millions of "
               "objects?",
          "options": [
              "Its cost is proportional to the objects that SURVIVE, not the ones allocated",
              "It runs concurrently with the application, so it never pauses",
              "Young-generation objects are freed individually as they go out of scope",
              "The JVM reference-counts young objects and frees them immediately",
          ],
          "answer": 0,
          "why": "Option A is the generational hypothesis paying off: a copying "
                 "collector touches only the live set, so pure garbage is free to "
                 "collect. Option B is wrong for young collections in G1 and Parallel — "
                 "they are stop-the-world, just very short. Option C describes "
                 "scope-based destruction, which is C++, not Java; going out of scope "
                 "makes an object unreachable, and nothing happens until a GC runs. "
                 "Option D is the reference-counting model Java deliberately does not "
                 "use, which is also why unreachable CYCLES are collected fine.",
      },
      complexity="Rule of thumb: G1 young pauses in the single-digit milliseconds, full "
                 "GC in hundreds of ms to seconds on a large heap. ZGC keeps pauses "
                 "under a millisecond REGARDLESS of heap size, paying with ~10-15% "
                 "throughput and more memory. Choose by whether your SLA is about "
                 "throughput or about tail latency.",
      pitfalls="Do not tune GC before measuring — most 'GC problems' are allocation "
               "problems or a memory leak, and no collector fixes those. Never call "
               "System.gc() in application code. And a heap far larger than the live "
               "set wastes memory and lengthens full GCs, so bigger is not safer.",
      followups="What is a STOP-THE-WORLD pause? Every application thread is halted at "
                "a safepoint while the collector works. Even 'concurrent' collectors "
                "have short STW phases for root scanning. It is why a 32GB heap on a "
                "throughput collector can pause for seconds, and why ZGC exists.",
      difficulty="Medium", frequency="Very common at mid/senior level",
      mnemonic="Most objects die young. Minor GC pays for SURVIVORS, not allocations."),

    Q("jvm",
      "The JIT — why your first benchmark is always wrong",
      "Java starts by reading your compiled program one instruction at a time "
      "and doing what each says, which is slow. While it runs it counts how "
      "often each method is called, and once something is clearly popular it "
      "translates that method into real machine code — often FASTER code than a "
      "compiler could have produced up front, because it can use facts that are "
      "only true while the program is actually running. The consequence for "
      "measuring anything is severe: the first thousand runs of your code are "
      "not the code you shipped, so a benchmark that does not warm up first is "
      "timing the slow version.",
      "TIERED COMPILATION: the interpreter gathers profile data, C1 compiles "
      "quickly with light optimisation, and C2 recompiles the hottest methods "
      "with aggressive ones. THE OPTIMISATIONS THAT MATTER: inlining (the "
      "enabler for everything else), escape analysis (an object that never "
      "leaves a method may be scalarised and never allocated at all), loop "
      "unrolling, and MONOMORPHIC INLINE CACHES — if a call site has only ever "
      "seen one implementing class, C2 inlines it and guards with a cheap type "
      "check. That last one is why an interface call is usually free in practice "
      "and why adding a second implementation can measurably slow a hot loop. "
      "DEOPTIMISATION undoes a speculation when it turns out to be wrong.",
      ["jvm", "jit", "performance", "benchmarking"],
      code="// A benchmark that measures nothing useful:\nlong t0 = System.nanoTime();\nfor (int i = 0; i < 1000; i++) work();\nSystem.out.println((System.nanoTime() - t0) / 1000 + \" ns/op\");\n// ^ 1,000 iterations is INSIDE the interpreter and C1. The number you get\n//   can be 10-100x worse than steady state.\n\n// And this one measures nothing AT ALL:\nlong t1 = System.nanoTime();\nfor (int i = 0; i < 100_000_000; i++) {\n    Math.sqrt(i);          // result unused -> DEAD CODE ELIMINATION\n}\nSystem.out.println(System.nanoTime() - t1);\n// ^ C2 proves the loop has no effect and deletes it. Near-zero, always.\n\n// The only correct answer is JMH, which handles warmup, dead-code\n// elimination (Blackhole), constant folding and fork isolation for you:\n//\n//   @Benchmark public double sqrt(Blackhole bh) { return Math.sqrt(x); }\n//\n// Useful flags while investigating:\n//   -XX:+PrintCompilation      what got compiled, and when\n//   -XX:+UnlockDiagnosticVMOptions -XX:+PrintInlining\n//   -Xint                      interpret only, to see the floor",
      output="(the first loop prints a number typically 10-100x the steady-state\n cost; the second prints something near zero, because the loop was\n deleted entirely)",
      gotcha="Q: your microbenchmark says a method takes 0.3 nanoseconds. What "
             "happened?  IT WAS DELETED. 0.3ns is well under a single memory access, so "
             "no real work occurred — C2 proved the result was unused and removed the "
             "whole loop by DEAD CODE ELIMINATION. A suspiciously fast result in a "
             "hand-rolled benchmark almost always means the compiler outsmarted the "
             "benchmark rather than the code being fast. USE JMH, whose Blackhole "
             "exists specifically to consume a value in a way C2 cannot see through.",
      version="Tiered compilation on by default since Java 8. GraalVM's JIT is an "
              "alternative C2. AOT compilation via native-image trades peak throughput "
              "for near-zero startup — the opposite trade to the JIT, and why it suits "
              "short-lived CLI tools and serverless.",
      quiz={
          "q": "Why can a JIT produce faster code than an ahead-of-time compiler?",
          "options": [
              "It can speculate on facts only observable at runtime — like a call site having only ever seen one class",
              "It has more time to optimise, since compilation happens in the background",
              "It targets the exact CPU model, which an AOT compiler cannot",
              "It compiles to assembly directly, while AOT compilers go through C",
          ],
          "answer": 0,
          "why": "Option A is the real asymmetry: profile-guided speculation with a "
                 "cheap guard and deoptimisation if it turns out wrong. An AOT compiler "
                 "must be correct for every possible execution and cannot make that "
                 "bet. Option B has it backwards — the JIT is under TIME PRESSURE and "
                 "must share the CPU with the application, which is why C1 exists. "
                 "Option C is true and minor, and an AOT compiler can also be told the "
                 "target CPU. Option D describes neither.",
      },
      pitfalls="JVM warmup is why a service is slow for its first few seconds and why "
               "load balancers should ramp new instances in. It is also why a "
               "single-shot latency measurement of a cold path is meaningless, and why "
               "the p99 of a low-traffic endpoint stays bad — it never gets hot enough "
               "to compile.",
      followups="Why does adding a second implementation of an interface slow a hot "
                "loop? The call site goes from MONOMORPHIC — one type seen, inlined "
                "with a guard — to bimorphic or megamorphic, where the JIT can no "
                "longer inline and must do a virtual dispatch. It is a real effect, and "
                "it is also a terrible reason to avoid interfaces.",
      difficulty="Medium", frequency="Common at senior level",
      mnemonic="Warm it up or you are timing the interpreter. Suspiciously fast means deleted."),

    Q("jvm",
      "OutOfMemoryError — five different messages, five different causes",
      "OutOfMemoryError does not mean one thing. The message after the colon "
      "tells you which pool ran out, and each one points at a completely "
      "different problem with a completely different fix. Reading the message is "
      "most of the diagnosis, and increasing -Xmx is the right answer for "
      "exactly one of them.",
      "'Java heap space' — the object heap is full: a leak, an undersized heap, "
      "or a genuinely large working set. 'GC overhead limit exceeded' — the JVM "
      "spent over 98% of its time in GC recovering under 2% of the heap; the "
      "same causes, caught earlier. 'Metaspace' — class metadata exhausted, "
      "which means a CLASSLOADER LEAK (repeated redeploys in an app server, or "
      "runtime proxy generation) rather than an object leak; -Xmx does nothing. "
      "'unable to create new native thread' — the OS refused, so it is a THREAD "
      "leak or a ulimit, and paradoxically a SMALLER heap can help by leaving "
      "room for thread stacks. 'Direct buffer memory' — off-heap NIO buffers, "
      "bounded by -XX:MaxDirectMemorySize and freed only when their Java wrapper "
      "is collected. NOTE THAT AN OutOfMemoryError IS AN Error, NOT AN EXCEPTION "
      "— catching it is almost always wrong, because the JVM may already be in "
      "an unrecoverable state.",
      ["jvm", "oom", "memory", "debugging"],
      code="// The flags that matter BEFORE you have a problem, because a dump\n// taken after the fact is the only thing that answers the question:\n//\n//   -XX:+HeapDumpOnOutOfMemoryError\n//   -XX:HeapDumpPath=/var/log/app/\n//   -Xlog:gc*:file=/var/log/app/gc.log\n\n// 1. Java heap space — a leak, or a genuinely large live set\n//    -> heap dump, compare two, follow the RETAINED path to a GC root\n\n// 2. GC overhead limit exceeded — the same, caught earlier\n//    -> the JVM is thrashing: >98% of time in GC, <2% reclaimed\n\n// 3. Metaspace — a CLASSLOADER leak, not an object leak\n//    -> -Xmx does nothing. Look for repeated redeploys or generated proxies.\n\n// 4. unable to create new native thread — a THREAD leak or a ulimit\n//    -> jstack and count. A SMALLER -Xmx can help: stacks live outside it.\n\n// 5. Direct buffer memory — off-heap NIO\n//    -> -XX:MaxDirectMemorySize, and check for unreleased ByteBuffers\n\n// Catching it is almost always wrong:\ntry {\n    byte[] huge = new byte[Integer.MAX_VALUE];\n} catch (OutOfMemoryError e) {\n    // The allocation failed, so this frame is fine — but any OTHER thread\n    // may have died mid-operation and left shared state inconsistent.\n    System.out.println(\"caught: \" + e.getMessage());\n}",
      output="caught: Requested array size exceeds VM limit\n\n(that particular message is its own case: the array is larger than the\n JVM can index, not larger than the heap — you get it even with an\n enormous -Xmx)",
      gotcha="Q: 'OutOfMemoryError: Metaspace' — do you raise -Xmx?  NO, AND IT WILL "
             "NOT HELP AT ALL. Metaspace holds CLASS METADATA and lives in native "
             "memory, entirely outside the -Xmx heap. Running out of it means "
             "classloaders are not being collected — the classic cause is repeated "
             "redeployment in an app server, where each deploy creates a new "
             "classloader and something holds a reference to the old one. THE MESSAGE "
             "AFTER THE COLON IS THE DIAGNOSIS, and treating every OOM as 'needs a "
             "bigger heap' is how a Metaspace leak survives three rounds of tuning.",
      version="PermGen became Metaspace in Java 8, moving class metadata off-heap and "
              "making -XX:MaxPermSize obsolete. Java 10+ reads container cgroup limits, "
              "so a JVM in Docker no longer sizes its heap from the HOST's memory and "
              "then gets OOM-killed by the kernel.",
      quiz={
          "q": "A service throws 'OutOfMemoryError: unable to create new native "
               "thread'. Which action is most likely to help?",
          "options": [
              "Find the thread leak — and consider a SMALLER heap, since stacks live outside it",
              "Increase -Xmx, since the JVM has run out of memory",
              "Increase -XX:MaxMetaspaceSize",
              "Call System.gc() more often to reclaim dead threads",
          ],
          "answer": 0,
          "why": "Option A is right and the smaller-heap part is the genuinely "
                 "counter-intuitive bit: thread stacks are allocated in native memory "
                 "OUTSIDE the heap, so a large -Xmx can leave too little address space "
                 "or RAM for them. Option B is the reflex answer and makes this "
                 "particular failure WORSE. Option C addresses class metadata, which is "
                 "unrelated. Option D misunderstands the mechanism entirely — a running "
                 "thread is a GC root and cannot be collected; the fix is to stop "
                 "creating them.",
      },
      pitfalls="Catching OutOfMemoryError to 'recover' is almost always wrong: your "
               "frame survived because ITS allocation failed, while another thread may "
               "have died halfway through updating shared state. The one defensible "
               "use is a controlled shutdown. And OOM in a container is often the "
               "KERNEL's OOM-killer, not the JVM's — the process vanishes with no stack "
               "trace and exit code 137.",
      followups="How do you actually find a heap leak? Two heap dumps a few minutes "
                "apart under load, compared. Look at what GREW, then follow the RETAINED "
                "path back to a GC root — the growing class is rarely the problem, "
                "whatever is holding it is.",
      difficulty="Medium", frequency="Very common at senior level",
      mnemonic="Read the words after the colon. Only ONE of the five wants a bigger -Xmx."),

    Q("jvm",
      "Class loading and the parent-delegation model",
      "Java loads a class the first moment it is genuinely needed, not when the "
      "program starts. When it does, the loader does not look for the class "
      "itself first — it asks its PARENT loader, which asks its own parent, all "
      "the way to the top. Only if nobody above can find it does the loader try. "
      "That upward-first order is what stops anyone replacing java.lang.String "
      "with their own version by putting a class file earlier on the classpath.",
      "Three built-in loaders: BOOTSTRAP (the JDK's own classes), PLATFORM, and "
      "APPLICATION (your classpath). PARENT DELEGATION: a request goes UP before "
      "any loader searches, so a class already loaded higher up always wins. "
      "That gives two guarantees — the core library cannot be shadowed, and a "
      "class is loaded once per loader. A CLASS'S IDENTITY IS (name, "
      "classloader): the same bytes loaded by two different loaders are two "
      "different classes, and casting between them throws ClassCastException "
      "with a message naming what looks like the same type twice. LOADING is "
      "separate from INITIALISATION: loading reads the bytes and verifies them; "
      "initialisation runs the static blocks, and is triggered lazily by first "
      "instantiation, first non-constant static access, or Class.forName.",
      ["jvm", "classloader", "delegation", "initialization"],
      code="// The identity of a class is (name, loader) — not the name alone.\nClassLoader app = Main.class.getClassLoader();\nSystem.out.println(app);\nSystem.out.println(app.getParent());              // platform\nSystem.out.println(app.getParent().getParent());  // null = bootstrap\n\n// Loaded vs INITIALISED — the static block runs at initialisation, not load\nclass Lazy {\n    static { System.out.println(\"Lazy initialised\"); }\n    static final String CONST = \"compile-time constant\";\n    static String runtime = compute();\n    static String compute() { return \"runtime\"; }\n}\n\nSystem.out.println(Lazy.CONST);      // does NOT initialise Lazy — inlined!\nSystem.out.println(\"---\");\nSystem.out.println(Lazy.runtime);    // DOES initialise it",
      output="jdk.internal.loader.ClassLoaders$AppClassLoader@...\njdk.internal.loader.ClassLoaders$PlatformClassLoader@...\nnull\ncompile-time constant\n---\nLazy initialised\nruntime",
      gotcha="Q: `System.out.println(Lazy.CONST)` where CONST is `static final String "
             "CONST = \"...\"` — does the static block run?  NO. A `static final` field "
             "initialised with a COMPILE-TIME CONSTANT is INLINED BY javac into the "
             "calling class file, so the reference to Lazy disappears entirely and the "
             "class is never even loaded. Change it to a value computed at runtime and "
             "the static block suddenly fires. THE SAME LINE OF SOURCE HAS TWO "
             "COMPLETELY DIFFERENT BEHAVIOURS depending on whether the initialiser is "
             "constant — and it is also why changing a public constant in a library "
             "requires recompiling every caller, not just redeploying the jar.",
      version="Java 9's module system replaced the old extension classloader with the "
              "PLATFORM loader and made the bootstrap loader's contents smaller. "
              "Class.forName and Thread.getContextClassLoader remain the escape hatches "
              "frameworks use to break delegation deliberately.",
      quiz={
          "q": "Why does parent delegation search UPWARDS before a loader tries itself?",
          "options": [
              "So core classes cannot be shadowed — nobody can substitute their own java.lang.String",
              "Because the parent loader is faster, having already cached most classes",
              "To guarantee classes are loaded in alphabetical order across the hierarchy",
              "Because child loaders can only load classes their parent has already seen",
          ],
          "answer": 0,
          "why": "Option A is the security and consistency guarantee delegation exists "
                 "for. Option B invents a performance rationale; delegation is about "
                 "correctness and it costs a walk up the chain on every miss. Option C "
                 "is meaningless — there is no ordering property. Option D inverts the "
                 "relationship: a child can load classes its parent cannot see, which "
                 "is exactly how an app server isolates two deployed applications.",
      },
      pitfalls="Two versions of the same library on the classpath: the FIRST one found "
               "wins for every class, and you can end up with a mix — jar hell. In an "
               "app server, holding a static reference to a class from a redeployed "
               "application pins its whole classloader and leaks Metaspace. And "
               "'ClassCastException: com.x.Foo cannot be cast to com.x.Foo' is not a "
               "typo — it is two loaders.",
      followups="How do frameworks break delegation on purpose? Servlet containers "
                "invert it — the web application's loader tries ITSELF first for most "
                "packages, so an app can bundle its own version of a library without "
                "the container's copy winning. That is why WEB-INF/lib behaves "
                "differently from the classpath you are used to.",
      difficulty="Medium", frequency="Common at senior level",
      mnemonic="Ask upwards first. A class is (name + loader). Constants get inlined away."),

    ]
