"""Java bank — core language: control flow, OOP, collections, exceptions.

AN EXPANSION MODULE, not a second bank. java_bank.py owns the schema, the
categories and the checks; this file only supplies entries, through a build(Q)
function that receives the Q constructor so the required-field rules apply here
identically.

Split out at 14 entries rather than at 100, deliberately. The AI/SDE bank grew
to 200,000 lines in one file before it was split, and by then every edit was a
scroll hunt and every merge a conflict. The cost of establishing the pattern
early is one import; the cost of establishing it late is a refactor of
everything.
"""


def build(Q):
    return [

    # ══════════════════════════════════════════════════════════════════
    #  Control flow & methods
    # ══════════════════════════════════════════════════════════════════

    Q("flow",
      "Class initialization order — static blocks, instance blocks, constructors",
      "When Java builds an object there is a fixed order of events, and it is "
      "not the order the code appears in the file. Anything marked `static` runs "
      "ONCE, the very first time the class is used at all. Then, every time you "
      "make an object: the parent's setup runs before the child's, and within a "
      "class the field assignments and `{ }` blocks run in the order they are "
      "written, BEFORE the constructor body. Knowing that order is the whole "
      "answer to a large family of 'what does this print' questions.",
      "Order, exactly: (1) static fields and static initialiser blocks, in "
      "source order, ONCE, at class initialisation — triggered by first "
      "instantiation, first static member access, or Class.forName. (2) Then per "
      "instance: the superclass chain is fully initialised first; then instance "
      "field initialisers and instance blocks in source order; then the "
      "constructor BODY. The implicit `super()` is the first statement of every "
      "constructor unless you write `this(...)` or `super(...)` yourself.",
      ["initialization", "static", "constructor", "oop"],
      code="class Parent {\n    static { System.out.println(\"1 parent static\"); }\n    { System.out.println(\"3 parent instance block\"); }\n    Parent() { System.out.println(\"4 parent ctor\"); }\n}\n\nclass Child extends Parent {\n    static { System.out.println(\"2 child static\"); }\n    { System.out.println(\"5 child instance block\"); }\n    Child() {\n        // an implicit super() runs here, before anything else in this body\n        System.out.println(\"6 child ctor\");\n    }\n}\n\n// main:\nnew Child();\nSystem.out.println(\"---\");\nnew Child();          // statics do NOT run again",
      output="1 parent static\n2 child static\n3 parent instance block\n4 parent ctor\n5 child instance block\n6 child ctor\n---\n3 parent instance block\n4 parent ctor\n5 child instance block\n6 child ctor",
      gotcha="Q: a subclass constructor calls an overridden method — which fields does "
             "it see?  THE CHILD'S FIELDS ARE STILL AT THEIR DEFAULTS. The parent "
             "constructor runs BEFORE the child's field initialisers, so an "
             "overridden method called from a parent constructor sees null and 0 in "
             "the child, even for fields with an initialiser right there in the "
             "source. IT IS WHY 'NEVER CALL AN OVERRIDABLE METHOD FROM A "
             "CONSTRUCTOR' IS A RULE and not a style preference.",
      version="Unchanged since Java 1.0. Records (16) run their compact constructor "
              "before the implicit field assignment, which is the one place this "
              "order was extended.",
      quiz={
          "q": "class A { A(){ show(); } void show(){ System.out.println(\"A\"); } } "
               "class B extends A { String s = \"set\"; @Override void show(){ "
               "System.out.println(s); } }  —  new B();",
          "options": [
              "null — the parent constructor runs before B's field initialisers",
              "set — s is initialised at its declaration, before any constructor",
              "A — the parent's version runs, since B is not fully constructed",
              "It throws NullPointerException on the println",
          ],
          "answer": 0,
          "why": "Option A is right and it is the reason the rule exists: dispatch is "
                 "already dynamic during the parent constructor, so B's show() runs — "
                 "but B's field initialisers have not executed yet, so s is still "
                 "null. Option B is the intuitive reading and it inverts the order. "
                 "Option C assumes dispatch waits for construction to finish; it does "
                 "not, which is precisely what makes this dangerous. Option D is close "
                 "but wrong: println(null) prints \"null\", it does not throw — "
                 "String.valueOf handles it.",
      },
      pitfalls="A static initialiser that throws wraps the exception in "
               "ExceptionInInitializerError, and the class is then permanently marked "
               "erroneous — every later use throws NoClassDefFoundError with no "
               "mention of the original cause. It is one of the most confusing "
               "startup failures in Java.",
      followups="When exactly does a class initialise? On first instantiation, first "
                "access to a non-constant static member, or Class.forName. NOT on "
                "accessing a `static final` COMPILE-TIME CONSTANT — that is inlined by "
                "javac and never touches the class.",
      difficulty="Medium", frequency="Very common — a staple 'what does this print'",
      mnemonic="Static once, parent first, fields before constructor body."),

    Q("flow",
      "switch — fall-through, strings, and the expression form",
      "The old `switch` runs the matching branch AND EVERY BRANCH AFTER IT until "
      "it hits a `break`. That is called fall-through, it is almost never what "
      "you want, and forgetting one `break` is a classic bug. Modern Java added "
      "an arrow form that does not fall through at all and can produce a value "
      "directly, which removes the whole class of mistake.",
      "Classic `switch` uses colon labels and falls through — control continues "
      "into subsequent cases until `break`, `return` or the end. Java 7 allowed "
      "String (compiled as a hashCode switch plus an equals check). Java 14 "
      "finalised SWITCH EXPRESSIONS: the `->` form never falls through, may be "
      "used as an expression yielding a value, and is checked for EXHAUSTIVENESS "
      "when switching over an enum or sealed type — a missing case is a compile "
      "error rather than a silent null. `yield` returns a value from a multi-"
      "statement arrow block.",
      ["switch", "control-flow", "fall-through", "modern-java"],
      code="// CLASSIC — note the missing break on case 2\nint day = 2;\nswitch (day) {\n    case 1: System.out.println(\"Mon\"); break;\n    case 2: System.out.println(\"Tue\");        // no break!\n    case 3: System.out.println(\"Wed\"); break;\n    default: System.out.println(\"other\");\n}\n\n// ARROW FORM — no fall-through, and it is an EXPRESSION\nString name = switch (day) {\n    case 1 -> \"Monday\";\n    case 2, 3 -> \"Midweek\";          // multiple labels, one arm\n    default -> {\n        String s = \"day \" + day;\n        yield s;                      // yield, not return\n    }\n};\nSystem.out.println(name);",
      output="Tue\nWed\nMidweek",
      gotcha="Q: with `day = 2` and no `break` after case 2, what prints?  BOTH \"Tue\" "
             "AND \"Wed\". Control falls into case 3 and only stops at ITS break. "
             "Notice it does NOT print \"other\" — the break in case 3 caught it. So "
             "one missing break leaks exactly as far as the next one, which is why "
             "these bugs are so specific and so hard to spot by reading.",
      version="String switch: Java 7. Switch EXPRESSIONS with -> and yield: preview in "
              "12/13, final in Java 14. Pattern matching for switch: final in Java 21.",
      quiz={
          "q": "Why does the arrow form of switch remove a whole class of bug?",
          "options": [
              "It never falls through, so a missing break cannot leak into the next case",
              "It is faster — the compiler emits a jump table instead of comparisons",
              "It requires a default clause, so unhandled values cannot slip past",
              "It disallows multiple labels per case, forcing one branch per value",
          ],
          "answer": 0,
          "why": "Option A is right: fall-through is the bug, and the arrow form has "
                 "none. Option B confuses this with tableswitch vs lookupswitch, which "
                 "javac already chooses for both forms based on label density — the "
                 "arrow syntax changes semantics, not codegen. Option C is wrong in "
                 "general: default is only required when the switch is an EXPRESSION "
                 "and the cases are not exhaustive, and over a sealed type or enum you "
                 "can omit it entirely. Option D is backwards — the arrow form ADDED "
                 "multiple labels per arm, `case 2, 3 ->`.",
      },
      pitfalls="A switch on a String NPEs if the value is null — the classic form has "
               "no null label. Java 21 added `case null`. And a switch on a boxed "
               "Integer unboxes, so a null there throws too.",
      followups="Why was fall-through ever the default? Java inherited it from C, where "
                "it enables the Duff's-device style of shared tail code. It is "
                "genuinely useful perhaps one time in fifty and a bug the other "
                "forty-nine.",
      difficulty="Easy", frequency="Very common",
      mnemonic="Colon falls through. Arrow does not."),

    Q("flow",
      "Varargs — and the overload ambiguity it creates",
      "`String...` lets a method take any number of arguments and receive them "
      "as an array. It is convenient and it makes overload resolution harder, "
      "because the compiler now has a method that matches almost anything. Java "
      "resolves this by trying the ordinary methods first and only falling back "
      "to the varargs one if nothing else fits — which means adding a varargs "
      "overload can silently change which method an existing call goes to.",
      "A varargs parameter is compiled as an array parameter plus a flag; the "
      "call site allocates the array. Overload resolution runs in THREE PHASES: "
      "(1) match without boxing or varargs, (2) allow boxing/unboxing, (3) allow "
      "varargs. A candidate found in an earlier phase always wins, so varargs is "
      "the last resort. Passing an existing array to a varargs parameter passes "
      "it DIRECTLY rather than wrapping it, and passing `null` is ambiguous "
      "enough that javac warns.",
      ["varargs", "overloading", "methods"],
      code="static void f(int a, int b)   { System.out.println(\"two ints\"); }\nstatic void f(int... a)       { System.out.println(\"varargs, n=\" + a.length); }\nstatic void f(Integer a, Integer b) { System.out.println(\"two Integers\"); }\n\nf(1, 2);            // phase 1: exact match, no boxing, no varargs\nf(1, 2, 3);         // only varargs fits\nf();                // varargs with zero arguments\n\n// An ARRAY passed to varargs is used directly, not wrapped:\nint[] arr = {1, 2, 3};\nf(arr);\n\n// The classic surprise:\nSystem.out.println(java.util.Arrays.asList(1, 2, 3).size());\nint[] prims = {1, 2, 3};\nSystem.out.println(java.util.Arrays.asList(prims).size());",
      output="two ints\nvarargs, n=3\nvarargs, n=0\nvarargs, n=3\n3\n1",
      gotcha="Q: `Arrays.asList(intArray).size()` — 3 or 1?  ONE. asList is "
             "`<T> List<T> asList(T... a)` and T must be a reference type, so an "
             "`int[]` cannot be spread into T... — instead the WHOLE ARRAY becomes the "
             "single element, giving a List<int[]> of size 1. An `Integer[]` gives 3. "
             "THE SAME LINE MEANS TWO DIFFERENT THINGS DEPENDING ON WHETHER THE ARRAY "
             "IS PRIMITIVE, and the compiler is perfectly happy either way.",
      version="Varargs arrived in Java 5. Arrays.stream(int[]) and IntStream.of exist "
              "precisely because of the asList trap; List.of has the same primitive "
              "behaviour.",
      quiz={
          "q": "Given f(int,int) and f(int...), which does f(1,2) call, and why?",
          "options": [
              "f(int,int) — varargs is only considered in the last resolution phase",
              "f(int...) — it is more general, so it is preferred",
              "It is ambiguous and fails to compile",
              "f(int,int), but only because it is declared first in the file",
          ],
          "answer": 0,
          "why": "Option A is right, and the three-phase rule is worth knowing by name: "
                 "match without boxing or varargs, then with boxing, then with varargs. "
                 "Option B inverts it — generality LOSES, which is why adding a varargs "
                 "overload does not break existing calls. Option C assumes ambiguity, "
                 "but the phases make resolution deterministic. Option D invents "
                 "declaration order as a tiebreak; Java never uses source order for "
                 "overload resolution.",
      },
      pitfalls="`f(null)` on a varargs method passes a null ARRAY, not an array "
               "containing null — a.length then NPEs. Write `f((String) null)` for the "
               "latter. And a varargs parameter must be last; only one per method.",
      followups="Why does @SafeVarargs exist? A varargs parameter of a generic type "
                "creates an array of a generic type, which is unsound in general — the "
                "annotation is you asserting the method does not store anything into "
                "it.",
      difficulty="Medium", frequency="Common — the Arrays.asList form is a favourite",
      mnemonic="Varargs is the LAST candidate the compiler tries, never the first."),

    # ══════════════════════════════════════════════════════════════════
    #  OOP
    # ══════════════════════════════════════════════════════════════════

    Q("oop",
      "Abstract class vs interface — and what default methods changed",
      "An abstract class is a half-built class: it can hold state, have "
      "constructors, and you can only extend one of them. An interface is a "
      "contract: historically no state and no implementation, and a class can "
      "implement as many as it likes. Java 8 blurred the line by letting "
      "interfaces carry method BODIES (default methods), so the honest modern "
      "distinction is narrower than the textbook one: it is about STATE and "
      "SINGLE INHERITANCE, not about whether there is code.",
      "Abstract class: may have instance fields, constructors, any access "
      "modifier on members, and a class extends exactly one. Interface: fields "
      "are implicitly public static final (constants, not state), methods are "
      "public abstract unless marked `default`, `static` or `private`, and a "
      "class implements many. SINCE JAVA 8 the 'interfaces have no code' rule is "
      "gone — default methods exist so an interface can gain a method without "
      "breaking every implementor, which is exactly how Collection got stream() "
      "and forEach(). THE REMAINING REAL DIFFERENCES ARE INSTANCE STATE AND HOW "
      "MANY YOU CAN INHERIT.",
      ["oop", "interface", "abstract", "default-methods"],
      code="interface Greeter {\n    String name();                                  // abstract\n    default String greet() {                        // Java 8+: a body\n        return \"Hello, \" + name();\n    }\n    static Greeter of(String n) { return () -> n; } // Java 8+: static\n    // private String helper() { return \"\"; }      // Java 9+: private\n}\n\ninterface Loud {\n    default String greet() { return \"HELLO\"; }\n}\n\n// A class implementing BOTH must resolve the clash explicitly:\nclass Both implements Greeter, Loud {\n    public String name() { return \"Priya\"; }\n    @Override public String greet() {\n        return Greeter.super.greet() + \" / \" + Loud.super.greet();\n    }\n}\n\nSystem.out.println(Greeter.of(\"Anand\").greet());\nSystem.out.println(new Both().greet());",
      output="Hello, Anand\nHello, Priya / HELLO",
      gotcha="Q: two interfaces both provide a default greet() — does it compile?  NOT "
             "UNLESS YOU OVERRIDE IT. Java refuses to guess and the error is 'inherits "
             "unrelated defaults'. THIS IS JAVA'S ANSWER TO THE DIAMOND PROBLEM: it "
             "does not resolve the ambiguity for you, it makes you resolve it, and "
             "`Interface.super.method()` is the syntax for picking one. That is why "
             "default methods did not reintroduce multiple-inheritance chaos.",
      version="default and static interface methods: Java 8. private interface "
              "methods: Java 9. Sealed interfaces: Java 17.",
      quiz={
          "q": "Since interfaces can have method bodies, when do you still need an "
               "abstract class?",
          "options": [
              "When you need instance STATE or a constructor — interfaces have neither",
              "When you need a method body, which interfaces still cannot have",
              "When you need protected members, which interfaces support since Java 9",
              "Never — default methods made abstract classes redundant",
          ],
          "answer": 0,
          "why": "Option A is the real remaining distinction, and it is the whole "
                 "answer post-Java 8. Option B is the pre-2014 answer and has been "
                 "wrong for a decade. Option C is a plausible-sounding invention: Java "
                 "9 added PRIVATE interface methods, not protected, and interface "
                 "members are still implicitly public. Option D overcorrects — an "
                 "interface cannot hold a mutable field, so anything with per-instance "
                 "state still needs a class.",
      },
      pitfalls="Interface fields are `public static final` whether you write it or not "
               "— an 'interface constant' is shared and immutable, never per-instance "
               "state. And a default method cannot override anything from Object "
               "(equals, hashCode, toString); the compiler rejects it.",
      followups="Why were default methods added at all? To evolve interfaces without "
                "breaking implementors — Collection.stream() and Iterable.forEach() "
                "could not otherwise have been added in Java 8 without breaking every "
                "existing collection in the world.",
      difficulty="Medium", frequency="Extremely common — near-guaranteed",
      mnemonic="Interfaces got CODE in Java 8. They still have no STATE."),

    Q("oop",
      "Static nested vs inner class — and the memory leak the inner one causes",
      "A class declared inside another class comes in two kinds. Marked "
      "`static`, it is just a normal class that happens to live in another one's "
      "namespace. WITHOUT `static`, every instance secretly holds a reference "
      "back to the outer object that created it — which is convenient, and it "
      "means the outer object cannot be garbage collected while the inner one is "
      "alive. That hidden reference is a real and common source of memory leaks.",
      "A STATIC NESTED class has no implicit reference to an enclosing instance "
      "and is instantiated as `Outer.Nested n = new Outer.Nested()`. An INNER "
      "(non-static nested) class holds a synthetic `Outer.this` field, requires "
      "an enclosing instance — `outer.new Inner()` — and can read the outer "
      "object's fields directly. THE SYNTHETIC REFERENCE IS THE PROBLEM: a "
      "long-lived inner instance (a listener, a Runnable handed to an executor, "
      "a Handler) keeps its entire outer object reachable. Anonymous classes and "
      "non-static lambdas capturing `this` have the same property. MAKE NESTED "
      "CLASSES STATIC BY DEFAULT and add the outer reference only when you need "
      "it.",
      ["oop", "nested-class", "inner-class", "memory-leak"],
      code="class Outer {\n    private String secret = \"outer state\";\n\n    static class Nested {                 // no link to Outer\n        String describe() { return \"nested\"; }\n    }\n\n    class Inner {                         // holds Outer.this\n        String describe() { return \"inner sees: \" + secret; }\n    }\n\n    Runnable leaky() {\n        // anonymous inner class -> captures Outer.this implicitly\n        return new Runnable() {\n            public void run() { System.out.println(secret); }\n        };\n    }\n}\n\nOuter.Nested n = new Outer.Nested();        // no Outer instance needed\nSystem.out.println(n.describe());\n\nOuter o = new Outer();\nOuter.Inner i = o.new Inner();               // note the syntax\nSystem.out.println(i.describe());",
      output="nested\ninner sees: outer state",
      gotcha="Q: you register `new Runnable(){...}` from an Activity/Service/controller "
             "with a long-lived executor. What leaks?  THE ENTIRE OUTER OBJECT, and "
             "everything it references. The anonymous class holds Outer.this even if "
             "its body never touches an outer field — the reference is added by the "
             "compiler, not by usage. A STATIC nested class, or a lambda that captures "
             "no instance state, does not. This is the single most common Java memory "
             "leak and it is invisible in the source.",
      version="Local and anonymous classes could only capture effectively-final locals "
              "from Java 8 (before that you had to write `final` yourself). Lambdas "
              "(Java 8) capture `this` only if the body actually uses it, which makes "
              "them leak LESS than anonymous classes.",
      quiz={
          "q": "Which of these does NOT hold a hidden reference to the enclosing "
               "instance?",
          "options": [
              "A static nested class",
              "An anonymous inner class whose body never mentions an outer field",
              "A non-static inner class",
              "A local class declared inside an instance method",
          ],
          "answer": 0,
          "why": "Option A is the only one, and it is why 'make it static unless you "
                 "need the outer' is the rule. Option B is the trap and the reason the "
                 "leak is so hard to spot: the reference is added by the COMPILER "
                 "regardless of whether the body uses it. Options C and D both capture "
                 "the enclosing instance by definition — a local class in an instance "
                 "method is an inner class with a narrower scope.",
      },
      pitfalls="Serializing an inner class drags the outer object into the stream, and "
               "fails if the outer is not Serializable — a confusing "
               "NotSerializableException naming a class you never asked to serialize.",
      followups="How do you spot it in a heap dump? Look for `this$0` — that is the "
                "compiler-generated field holding the outer reference, and finding it "
                "on a retained object is the smoking gun.",
      difficulty="Medium", frequency="Common — and the leak half separates people",
      mnemonic="No `static` means a hidden `this$0` back to the outer object."),

    # ══════════════════════════════════════════════════════════════════
    #  Collections & generics
    # ══════════════════════════════════════════════════════════════════

    Q("collections",
      "How HashMap actually works — buckets, collisions, and treeification",
      "A HashMap stores entries in an array of slots. To find where a key goes "
      "it calls hashCode(), squeezes that number down to a slot index, and puts "
      "the entry there. Two different keys can land in the same slot — a "
      "collision — so each slot holds a small list, and lookup walks it comparing "
      "with equals(). If a slot gets too crowded Java converts that list into a "
      "balanced tree so lookup stays fast even under attack. And when the map "
      "gets too full overall it doubles the array and redistributes everything.",
      "Backing array of Node[] whose length is always a POWER OF TWO, so the "
      "index is `hash & (n-1)` — a mask rather than a modulo. The hash is "
      "SPREAD first: `h ^ (h >>> 16)`, mixing the high bits down, because the "
      "mask would otherwise discard them entirely and a hashCode differing only "
      "in its high bits would collide on every key. A bucket holds a linked list; "
      "at TREEIFY_THRESHOLD (8) entries in one bucket AND a table of at least 64, "
      "it becomes a red-black tree, taking worst-case lookup from O(n) to "
      "O(log n). Resize at LOAD_FACTOR 0.75 doubles the table and rehashes. "
      "Average get/put O(1); worst case O(log n) since Java 8, O(n) before.",
      ["hashmap", "collections", "hashing", "internals"],
      code="import java.util.*;\n\n// Everything about a HashMap follows from hashCode + equals:\nMap<String,Integer> m = new HashMap<>();\nm.put(\"a\", 1);\nm.put(\"a\", 2);                      // same key -> REPLACED, not added\nSystem.out.println(m);\n\n// Why the table length is a power of two: the index is a MASK.\nint tableSize = 16;\nint h = \"hello\".hashCode();\nint spread = h ^ (h >>> 16);         // exactly what HashMap does\nSystem.out.println(\"index = \" + (spread & (tableSize - 1)));\n\n// A deliberately terrible hashCode collapses every key into one bucket:\nclass Bad {\n    final int v;\n    Bad(int v) { this.v = v; }\n    @Override public int hashCode() { return 1; }        // ALWAYS 1\n    @Override public boolean equals(Object o) {\n        return o instanceof Bad && ((Bad) o).v == v;\n    }\n}\nMap<Bad,Integer> bad = new HashMap<>();\nfor (int i = 0; i < 5; i++) bad.put(new Bad(i), i);\nSystem.out.println(bad.size());      // still correct — just slow",
      output="{a=2}\nindex = 2\n5",
      gotcha="Q: is HashMap ordered?  NO, and the subtler point is that the order is "
             "not random either — it is an artefact of hash values and table size, so "
             "it is STABLE FOR A GIVEN SET OF KEYS AND THEN CHANGES THE MOMENT THE MAP "
             "RESIZES. Code that accidentally depends on iteration order passes every "
             "test with 10 keys and breaks in production with 13. Use LinkedHashMap for "
             "insertion order or TreeMap for sorted order.",
      version="Treeification and the h ^ (h >>> 16) spread arrived in Java 8. Before "
              "that a bucket was always a linked list, which made hash-collision "
              "denial-of-service a genuine attack on web frameworks parsing "
              "user-supplied form keys.",
      quiz={
          "q": "Why is a HashMap's table length always a power of two?",
          "options": [
              "So the bucket index can be hash & (n-1) — a bitmask instead of a modulo",
              "So the table can be doubled without rehashing any entries",
              "Because red-black trees require a power-of-two capacity",
              "To guarantee that distinct hashCodes map to distinct buckets",
          ],
          "answer": 0,
          "why": "Option A is right, and it is also WHY the spread function exists: a "
                 "mask keeps only the low bits, so the high bits would be thrown away "
                 "entirely without `h ^ (h >>> 16)`. Option B is wrong — a resize does "
                 "rehash, though the power-of-two size means each entry either stays at "
                 "index i or moves to i + oldCapacity, which is a real optimisation and "
                 "probably what this option is half-remembering. Option C is invented. "
                 "Option D is impossible for any finite table — collisions are "
                 "guaranteed by pigeonhole, which is the whole reason buckets hold "
                 "lists.",
      },
      complexity="get/put average O(1), worst case O(log n) since Java 8. A resize is "
                 "O(n) and amortized away by the doubling — the same geometric argument "
                 "as ArrayList. Memory: each entry is a Node object (~32-40 bytes) plus "
                 "the table slot, which is why a Map<Integer,Integer> costs far more "
                 "than two parallel int arrays.",
      pitfalls="MUTATING A KEY AFTER INSERTION puts it in the wrong bucket and it "
               "becomes unreachable — map.get(theVeryKey) returns null while the entry "
               "is still there and still counted in size(). Use immutable keys. And "
               "HashMap is not thread-safe: concurrent put during resize could produce "
               "an infinite loop before Java 8, and still corrupts state after.",
      followups="How does ConcurrentHashMap differ? Per-bin locking (CAS on an empty "
                "bin, synchronized on the head node otherwise) rather than one global "
                "lock, weakly-consistent iterators that never throw "
                "ConcurrentModificationException, and no null keys or values — because "
                "get() returning null would be ambiguous between 'absent' and 'mapped "
                "to null' with no atomic way to distinguish them.",
      difficulty="Medium", frequency="Extremely common — the #1 collections question",
      mnemonic="hashCode picks the bucket, equals picks the entry, 8-in-a-bucket becomes a tree."),

    Q("collections",
      "Generics and type erasure — what actually survives to runtime",
      "Generics are checked by the compiler and then thrown away. At runtime "
      "there is no such thing as a List<String> — there is only a List, and the "
      "compiler has inserted the casts for you. That is why you cannot ask an "
      "object what its generic type is, cannot create an array of a generic "
      "type, and why two methods differing only in their generic parameter will "
      "not compile as overloads.",
      "ERASURE: the compiler replaces each type parameter with its leftmost "
      "bound (Object for an unbounded T) and inserts checked casts at the call "
      "sites. Consequences: List<String> and List<Integer> are the SAME CLASS at "
      "runtime; you cannot write `new T[]` or `instanceof List<String>`; two "
      "methods whose signatures differ only after erasure clash; a static field "
      "cannot use the class's type parameter. Erasure was chosen for MIGRATION "
      "COMPATIBILITY — pre-generics code had to keep working and pre-generics "
      "class files had to keep loading — which is why Java has erasure where C# "
      "has reified generics.",
      ["generics", "erasure", "type-system"],
      code="import java.util.*;\n\nList<String> a = new ArrayList<>();\nList<Integer> b = new ArrayList<>();\nSystem.out.println(a.getClass() == b.getClass());   // same class at runtime\nSystem.out.println(a.getClass().getSimpleName());\n\n// Erasure lets you smuggle a wrong type in through a raw reference:\nList raw = a;                 // raw type — compiles with a warning\nraw.add(42);                  // no runtime check happens here\nSystem.out.println(a.size());\n// String s = a.get(0);       // ClassCastException at THIS line, not the add\n\n// Bounded type parameter — erased to Number, not Object:\nstatic <T extends Number> double sum(List<T> xs) {\n    double t = 0;\n    for (T x : xs) t += x.doubleValue();   // legal because of the bound\n    return t;\n}\nSystem.out.println(sum(List.of(1, 2, 3.5)));",
      output="true\nArrayList\n1\n6.5",
      gotcha="Q: `List<String> a` then `((List) a).add(42)` — where does it blow up?  "
             "NOT AT THE add. Erasure means the list has no idea it is supposed to hold "
             "Strings, so the add succeeds silently. The ClassCastException happens "
             "later, at the first `String s = a.get(0)` — a line that looks completely "
             "correct and is nowhere near the bug. THE CAST THE COMPILER INSERTED FOR "
             "YOU IS WHERE IT FAILS, which is why unchecked warnings are worth taking "
             "seriously.",
      version="Generics: Java 5. The diamond `<>`: Java 7. Diamond with anonymous "
              "classes: Java 9. `var` (10) infers the full generic type, so "
              "`var m = new HashMap<String,List<Integer>>()` keeps everything.",
      quiz={
          "q": "Why will `void f(List<String> x)` and `void f(List<Integer> x)` not "
               "compile in the same class?",
          "options": [
              "After erasure both are f(List), so they are the same method",
              "Java forbids overloading on any generic parameter, erased or not",
              "They would compile, but the call would be ambiguous at every call site",
              "Because List<String> and List<Integer> are unrelated types",
          ],
          "answer": 0,
          "why": "Option A is right and it is erasure in one sentence — the error is "
                 "literally 'have the same erasure'. Option B states a broader rule "
                 "that does not exist: `f(List<String>)` and `f(Set<String>)` overload "
                 "fine, because their erasures differ. Option C imagines a runtime "
                 "problem; this is rejected at COMPILE time, before any call site is "
                 "considered. Option D is true and irrelevant — being unrelated is "
                 "exactly why you would WANT the overload, and erasure is what "
                 "prevents it.",
      },
      pitfalls="`new T[10]` is illegal — use `(T[]) new Object[10]` and accept the "
               "unchecked warning, or better, an ArrayList. `instanceof List<String>` "
               "is illegal for the same reason; only `instanceof List<?>` compiles. And "
               "a static member cannot reference the class's type parameter, because "
               "there is one static field for all parameterisations.",
      followups="What survives erasure? Generic type information in the CLASS FILE's "
                "Signature attribute — which is why reflection can read the declared "
                "type of a FIELD or a method's parameters, even though an OBJECT cannot "
                "tell you its own. That gap is what the 'super type token' trick "
                "exploits.",
      difficulty="Medium", frequency="Very common",
      mnemonic="Generics are a compile-time promise. At runtime there is only List."),

    Q("collections",
      "Comparable vs Comparator — and the contract that silently breaks TreeMap",
      "Comparable is a class saying 'here is my natural order' — you implement "
      "compareTo inside the class itself, and there is only one. Comparator is a "
      "separate object saying 'here is AN order' — you can write as many as you "
      "like and pass whichever you want to a sort. Use Comparable when the type "
      "has one obvious ordering, Comparator when the ordering depends on what "
      "you are doing.",
      "Comparable<T>.compareTo(T) defines the NATURAL ORDER and is what "
      "Collections.sort, TreeMap and TreeSet use by default. Comparator<T> is an "
      "external strategy, composable since Java 8 with comparing / thenComparing "
      "/ reversed. THE CONTRACT MATTERS MORE THAN THE SYNTAX: the comparison must "
      "be antisymmetric, transitive, and consistent — and it SHOULD be consistent "
      "with equals, because TreeMap and TreeSet determine membership by "
      "compareTo() == 0 and NOT by equals(). A comparator that returns 0 for "
      "objects that are not equal makes a TreeSet silently drop them.",
      ["comparable", "comparator", "sorting", "contract"],
      code="import java.util.*;\n\nrecord Person(String name, int age) {}\n\nList<Person> people = new ArrayList<>(List.of(\n    new Person(\"Anand\", 30), new Person(\"Priya\", 25), new Person(\"Zoe\", 30)));\n\n// Composable comparators — read it left to right, like a SQL ORDER BY\npeople.sort(Comparator.comparingInt(Person::age)\n                      .thenComparing(Person::name));\nSystem.out.println(people);\n\npeople.sort(Comparator.comparing(Person::name).reversed());\nSystem.out.println(people);\n\n// THE TRAP: a TreeSet uses compareTo/compare, NEVER equals\nSet<Person> byAge = new TreeSet<>(Comparator.comparingInt(Person::age));\nbyAge.addAll(people);\nSystem.out.println(byAge.size());\n\nSet<Person> hash = new HashSet<>(people);\nSystem.out.println(hash.size());",
      output="[Person[name=Priya, age=25], Person[name=Anand, age=30], Person[name=Zoe, age=30]]\n[Person[name=Zoe, age=30], Person[name=Priya, age=25], Person[name=Anand, age=30]]\n2\n3",
      gotcha="Q: three distinct people, two of them aged 30, added to a "
             "`TreeSet<>(comparingInt(Person::age))` — what is size()?  TWO. A TreeSet "
             "decides membership by `compare(a,b) == 0`, NOT by equals, so Zoe and "
             "Anand are 'the same element' and one is silently discarded. The HashSet "
             "of the same list has 3. IT IS NOT A BUG IN TreeSet — it is documented — "
             "and it is why the Javadoc says the ordering should be CONSISTENT WITH "
             "EQUALS. A comparator on a non-unique field is a data-loss bug wearing a "
             "sorting bug's clothes.",
      version="Comparator.comparing / thenComparing / reversed / nullsFirst: Java 8. "
              "Before that you wrote anonymous Comparator classes and chained by hand.",
      quiz={
          "q": "You put 5 people into `new TreeSet<>(Comparator.comparing(Person::city))` "
               "and three share a city. What is size()?",
          "options": [
              "3 — a TreeSet treats compare()==0 as equal, so duplicates are dropped",
              "5 — the comparator only affects ORDER, not membership",
              "5 — but iteration order among the shared city is undefined",
              "It throws IllegalStateException on the duplicate insert",
          ],
          "answer": 0,
          "why": "Option A is right and it is the whole hazard: sorted collections "
                 "define equality by the comparator, not by equals. Option B is the "
                 "near-universal assumption and it is exactly backwards for TreeSet and "
                 "TreeMap. Option C gets the count wrong for the same reason. Option D "
                 "expects a failure; add() simply returns false and the element is "
                 "dropped SILENTLY, which is what makes this dangerous rather than "
                 "merely surprising.",
      },
      pitfalls="`(a, b) -> (int)(a.value() - b.value())` OVERFLOWS for large or "
               "opposite-signed values and returns the wrong sign — use "
               "Integer.compare / Long.compare / Comparator.comparingInt. And a "
               "comparator inconsistent with itself throws 'Comparison method violates "
               "its general contract!' from TimSort, usually only on larger inputs.",
      followups="Why does Collections.sort require a stable sort? So a two-pass sort — "
                "by name then by age — leaves equal-aged people in name order. TimSort "
                "is stable; Arrays.sort on PRIMITIVES uses a dual-pivot quicksort and "
                "is NOT stable, which is invisible until it matters.",
      difficulty="Medium", frequency="Very common",
      mnemonic="Comparable is the type's own order. Comparator is one of many. TreeSet believes the comparator, not equals."),

    # ══════════════════════════════════════════════════════════════════
    #  Exceptions
    # ══════════════════════════════════════════════════════════════════

    Q("exceptions",
      "Checked vs unchecked — and why the distinction is contested",
      "Java has two kinds of exception. CHECKED ones the compiler forces you to "
      "deal with: you either catch them or declare that your method throws them. "
      "UNCHECKED ones (anything extending RuntimeException) you may ignore "
      "entirely. The idea was that recoverable problems should be impossible to "
      "forget. In practice it produced a lot of code that catches an exception "
      "and does nothing, which is worse than not catching it — and no language "
      "designed since has copied the feature.",
      "Throwable splits into Error (JVM-level, do not catch: OutOfMemoryError, "
      "StackOverflowError) and Exception. Exception splits into "
      "RuntimeException (UNCHECKED) and everything else (CHECKED). Checked "
      "exceptions are part of a method's signature and are enforced at compile "
      "time; overriding a method may NARROW the throws clause but never widen "
      "it. THE DESIGN INTENT was that checked = a caller can plausibly recover, "
      "unchecked = a programming error. THE PRACTICAL CRITICISM is that it "
      "couples every caller in a chain to a low-level implementation detail, and "
      "that the common response — an empty catch block — destroys information "
      "rather than handling it.",
      ["exceptions", "checked", "unchecked", "design"],
      code="// CHECKED — the compiler will not let you ignore it\nstatic void readIt() throws java.io.IOException {\n    throw new java.io.IOException(\"disk gone\");\n}\n\n// UNCHECKED — no declaration required, no catch required\nstatic void bug() {\n    throw new IllegalStateException(\"programmer error\");\n}\n\ntry {\n    readIt();\n} catch (java.io.IOException e) {\n    // WRAP, do not swallow: keep the cause so the stack trace survives\n    throw new RuntimeException(\"could not read config\", e);\n}",
      output="Exception in thread \"main\" java.lang.RuntimeException: could not read config\n\tat Main.main(Main.java:12)\nCaused by: java.io.IOException: disk gone\n\tat Main.readIt(Main.java:3)\n\t... 1 more\n\n(the \"Caused by\" section is there ONLY because the cause was passed to the\n constructor — see the trap below)",
      gotcha="Q: `catch (IOException e) { throw new RuntimeException(\"failed\"); }` — "
             "what is lost?  EVERYTHING USEFUL. Without passing `e` as the cause there "
             "is no 'Caused by' section, so the stack trace points at your rethrow and "
             "the original file, line and message are gone forever. The one-character "
             "difference between `new RuntimeException(msg)` and `new "
             "RuntimeException(msg, e)` is the difference between a debuggable "
             "production incident and an unexplainable one.",
      version="try-with-resources: Java 7. Multi-catch `catch (A | B e)`: Java 7. "
              "More precise rethrow (declaring the specific types actually thrown "
              "rather than Exception): Java 7.",
      quiz={
          "q": "Which is the strongest practical argument AGAINST checked exceptions?",
          "options": [
              "They leak an implementation detail into every caller's signature, and the usual response is an empty catch that destroys information",
              "They are slower, because the JVM must track the throws clause at runtime",
              "They cannot carry a cause, so stack traces are lost",
              "They can only be thrown from methods that declare them, making refactoring impossible",
          ],
          "answer": 0,
          "why": "Option A is the real critique and the reason no language designed "
                 "since has adopted them. Option B invents a runtime cost — the throws "
                 "clause is purely compile-time and appears in the class file only as "
                 "metadata. Option C is false: every Throwable can carry a cause, "
                 "checked or not. Option D overstates it — you can always wrap in an "
                 "unchecked exception, which is exactly what most codebases end up "
                 "doing and is itself part of the argument.",
      },
      pitfalls="`catch (Exception e)` also catches RuntimeException, hiding programmer "
               "errors alongside recoverable ones. `catch (Throwable t)` additionally "
               "catches Error — including OutOfMemoryError, which you cannot meaningfully "
               "handle and should not swallow. Never catch and ignore; if you truly "
               "mean to, write a comment saying why.",
      followups="Should a library use checked or unchecked? The modern consensus is "
                "unchecked for almost everything, with a rich exception type so callers "
                "who WANT to handle it can. Spring, Hibernate and the java.time API all "
                "went that way.",
      difficulty="Medium", frequency="Very common",
      mnemonic="Checked = the compiler nags. Unchecked = your problem. Always pass the cause."),

    Q("exceptions",
      "finally, try-with-resources, and the return that eats an exception",
      "`finally` runs whether or not something went wrong, which makes it the "
      "place to close things. But it has a sharp edge: if the finally block "
      "itself returns or throws, it REPLACES whatever the try block was doing — "
      "including an exception in flight, which simply vanishes. "
      "try-with-resources was added to close things correctly without needing "
      "finally at all, and it gets the edge cases right in a way hand-written "
      "code usually does not.",
      "`finally` executes on normal completion, on exception, and on return — "
      "the return VALUE is computed first and then finally runs. A `return` "
      "inside finally DISCARDS a pending exception; a `throw` inside finally "
      "replaces it. try-with-resources closes every AutoCloseable in REVERSE "
      "order of declaration, closes them BEFORE any catch or finally block runs, "
      "and if both the body and close() throw, the body's exception wins and "
      "close()'s is attached as a SUPPRESSED exception (retrievable via "
      "getSuppressed) rather than lost. Hand-written finally-close gets that "
      "last case wrong essentially every time.",
      ["exceptions", "finally", "try-with-resources", "resources"],
      code="static int swallow() {\n    try {\n        throw new RuntimeException(\"the real problem\");\n    } finally {\n        return 42;              // DISCARDS the exception entirely\n    }\n}\n\nstatic int valueFirst() {\n    int x = 1;\n    try {\n        return x;               // the VALUE 1 is captured here...\n    } finally {\n        x = 99;                 // ...so this does not change what is returned\n    }\n}\n\nSystem.out.println(swallow());\nSystem.out.println(valueFirst());\n\n// try-with-resources: closed in REVERSE order, before catch/finally\nclass Res implements AutoCloseable {\n    final String n;\n    Res(String n) { this.n = n; System.out.println(\"open \" + n); }\n    public void close() { System.out.println(\"close \" + n); }\n}\ntry (Res a = new Res(\"A\"); Res b = new Res(\"B\")) {\n    System.out.println(\"body\");\n}",
      output="42\n1\nopen A\nopen B\nbody\nclose B\nclose A",
      gotcha="Q: a method throws inside try and returns inside finally — what does the "
             "caller see?  THE RETURN VALUE, AND NO EXCEPTION AT ALL. `return` in a "
             "finally block silently discards an in-flight exception, so a real failure "
             "becomes a normal-looking 42. Every static analyser flags this and javac "
             "does not, which is why it still appears in real code. NEVER RETURN OR "
             "THROW FROM finally.",
      version="try-with-resources: Java 7. Java 9 allowed an already-declared "
              "effectively-final variable in the resource list — "
              "`try (existingResource) { ... }` — without re-declaring it.",
      quiz={
          "q": "In try-with-resources, the body throws AND close() throws. What does "
               "the caller receive?",
          "options": [
              "The body's exception, with close()'s attached via getSuppressed()",
              "close()'s exception — it happened last, so it wins",
              "The body's exception; close()'s is discarded",
              "Both, wrapped in a single CompositeException",
          ],
          "answer": 0,
          "why": "Option A is right and it is the strongest argument for the construct: "
                 "hand-written finally-close gets exactly this wrong, because closing "
                 "inside finally lets close()'s exception REPLACE the real one. Option "
                 "B is what naive finally-close actually does, which is why it is the "
                 "tempting answer. Option C describes losing information the language "
                 "specifically preserved. Option D invents a type — Java has no "
                 "CompositeException.",
      },
      pitfalls="A resource declared in try-with-resources must be AutoCloseable and is "
               "implicitly final. Closing a resource whose constructor threw is not an "
               "issue — it was never assigned — but a resource you open INSIDE the body "
               "is not managed and must be handled separately.",
      followups="Does finally always run? Almost — not on System.exit(), not if the JVM "
                "crashes, and not if the thread is killed at the OS level. Those are the "
                "only exceptions, and none of them are situations you can code around.",
      difficulty="Medium", frequency="Common — the return-in-finally trap is a favourite",
      mnemonic="finally always runs. A return inside it eats your exception."),

    # ══════════════════════════════════════════════════════════════════
    #  Modern Java
    # ══════════════════════════════════════════════════════════════════

    Q("modern",
      "Streams — laziness, one-shot use, and when a loop is better",
      "A stream is a pipeline: you describe the steps (filter this, map that) "
      "and NOTHING RUNS until you ask for a result at the end. That end step is "
      "called a terminal operation, and until you write one the whole chain does "
      "nothing at all. A stream can also only be used once — consume it and it "
      "is spent, like a queue rather than a list.",
      "Intermediate operations (filter, map, sorted, distinct, peek) are LAZY "
      "and return a new stream; terminal operations (collect, forEach, reduce, "
      "count, anyMatch) trigger execution. Elements are pulled through the whole "
      "pipeline ONE AT A TIME rather than stage by stage, which is why "
      "short-circuiting terminals like findFirst and anyMatch can stop early and "
      "why an infinite stream plus limit() works. A stream is single-use: "
      "operating on a consumed stream throws IllegalStateException. Streams are "
      "for READABILITY over collections, not speed — for a simple loop over an "
      "int[] they are typically slower, and parallel() is only worth it for "
      "large, CPU-bound, independent work on a splittable source.",
      ["streams", "lazy", "functional", "modern-java"],
      code="import java.util.*;\nimport java.util.stream.*;\n\n// NOTHING PRINTS — there is no terminal operation\nStream.of(\"a\", \"b\", \"c\").filter(s -> {\n    System.out.println(\"filtering \" + s);\n    return true;\n});\nSystem.out.println(\"-- nothing above this line --\");\n\n// Elements flow through ONE AT A TIME, not stage by stage:\nList<String> out = Stream.of(\"a\", \"b\", \"c\")\n    .peek(s -> System.out.println(\"filter \" + s))\n    .map(s -> { System.out.println(\"  map \" + s); return s.toUpperCase(); })\n    .collect(Collectors.toList());\nSystem.out.println(out);\n\n// Short-circuiting: only the first element is ever processed\nOptional<String> first = Stream.of(\"x\", \"y\", \"z\")\n    .peek(s -> System.out.println(\"touched \" + s))\n    .findFirst();\nSystem.out.println(first.get());",
      output="-- nothing above this line --\nfilter a\n  map a\nfilter b\n  map b\nfilter c\n  map c\n[A, B, C]\ntouched x\nx",
      gotcha="Q: a stream chain with filter and map and no collect — what runs?  "
             "NOTHING. Intermediate operations are lazy, so a pipeline without a "
             "terminal operation is dead code that the compiler accepts happily. It "
             "usually shows up as 'my forEach isn't running' when someone has written "
             ".map(x -> doSideEffect(x)) and never terminated the chain. AND THE SECOND "
             "HALF: elements go through the WHOLE pipeline one at a time, so the output "
             "interleaves filter/map rather than doing all the filtering first.",
      version="Streams: Java 8. takeWhile/dropWhile and iterate with a predicate: Java "
              "9. toList() as a terminal shorthand for an unmodifiable list: Java 16. "
              "mapMulti: Java 16. Stream.toList() returns UNMODIFIABLE, unlike "
              "collect(toList()) — a real migration gotcha.",
      quiz={
          "q": "`stream.filter(...).map(...)` with no terminal operation. What happens?",
          "options": [
              "Nothing runs — intermediate operations are lazy and need a terminal to execute",
              "Both run eagerly; the result is simply discarded",
              "It throws IllegalStateException for an incomplete pipeline",
              "filter runs but map does not, since map needs a downstream consumer",
          ],
          "answer": 0,
          "why": "Option A is right, and it silently does nothing — the compiler will "
                 "not warn you. Option B is the intuition from collections, where every "
                 "call does its work immediately, and it is what makes this surprising. "
                 "Option C hopes for a runtime error; there is none. Option D invents a "
                 "partial evaluation rule — laziness applies to the WHOLE chain, not "
                 "per stage.",
      },
      complexity="Streams add allocation and virtual calls per element. For a simple "
                 "loop over primitives they are typically slower than a for loop; for "
                 "complex multi-stage transformations over objects the difference is "
                 "usually noise. USE THEM FOR CLARITY. parallel() needs large N, "
                 "CPU-bound work, no shared mutable state and a splittable source "
                 "(ArrayList/array yes, LinkedList/IO no) — and it shares one common "
                 "ForkJoinPool across the whole JVM, so a blocking task in a parallel "
                 "stream can stall unrelated code.",
      pitfalls="Reusing a consumed stream throws IllegalStateException. Modifying the "
               "source collection during a stream is undefined behaviour. peek() is for "
               "debugging only — the Javadoc says so, and implementations may skip it "
               "when the result is not needed. Collectors.toMap throws on duplicate keys "
               "unless you supply a merge function.",
      followups="Why does Optional exist alongside streams? findFirst and max cannot "
                "return a value that may be absent without either null or Optional, and "
                "Optional makes the absence part of the type — so the caller cannot "
                "forget it.",
      difficulty="Medium", frequency="Very common in modern interviews",
      mnemonic="No terminal, no work. One element at a time. One use only."),

    Q("modern",
      "var, records, sealed, text blocks — what Java 10-21 actually changed",
      "Four features that between them removed most of Java's reputation for "
      "ceremony. `var` lets the compiler work out a local variable's type. "
      "`record` writes a whole immutable data class for you in one line. "
      "`sealed` lets a type say exactly which classes may extend it. Text blocks "
      "let you write multi-line strings without escaping every quote. None of "
      "them change what Java can do; all of them change how much you have to "
      "type to do it.",
      "`var` (10): local variables only — not fields, not parameters, not return "
      "types — and it is STATIC typing with inference, not dynamic typing; the "
      "type is fixed at compile time. `record` (16): a transparent carrier for "
      "immutable data — generates a canonical constructor, accessors (named "
      "`name()` not `getName()`), equals, hashCode and toString; implicitly "
      "final; cannot extend a class. `sealed` (17): `sealed interface Shape "
      "permits Circle, Square` — the permitted set is closed, which lets a switch "
      "over it be checked for EXHAUSTIVENESS. TEXT BLOCKS (15): triple-quoted, "
      "with incidental leading whitespace stripped relative to the closing "
      "delimiter.",
      ["var", "records", "sealed", "text-blocks", "modern-java"],
      code="// var — inference, not dynamic typing\nvar list = new java.util.ArrayList<String>();   // ArrayList<String>\nvar n = 10;                                     // int\n// var x;            // ERROR: no initialiser, nothing to infer from\n// var y = null;     // ERROR: null has no useful type\n\n// record — a whole value class\nrecord Point(int x, int y) {\n    // compact constructor: validate before the fields are assigned\n    Point {\n        if (x < 0 || y < 0) throw new IllegalArgumentException(\"negative\");\n    }\n    double dist() { return Math.sqrt(x * x + y * y); }\n}\nvar p = new Point(3, 4);\nSystem.out.println(p);                 // generated toString\nSystem.out.println(p.x());             // accessor is x(), not getX()\nSystem.out.println(p.equals(new Point(3, 4)));\nSystem.out.println(p.dist());\n\n// text block — no escaping, no concatenation\nString json = \"\"\"\n    {\"name\": \"Priya\", \"age\": 25}\"\"\";\nSystem.out.println(json);",
      output="Point[x=3, y=4]\n3\ntrue\n5.0\n{\"name\": \"Priya\", \"age\": 25}",
      gotcha="Q: does `var` make Java dynamically typed?  NO, and this is the most "
             "common misunderstanding of it. The type is inferred once, at compile "
             "time, and is then completely fixed — `var n = 10; n = \"hi\";` does not "
             "compile. It is the same static type you would have written, with less "
             "typing. The real cost is READABILITY: `var x = getThing()` hides the type "
             "from a reader who does not have an IDE, which is why the style guidance "
             "is to use it where the right-hand side already names the type.",
      version="var: Java 10 (11 added it in lambda parameters). Text blocks: 15. "
              "Records: 16. Sealed types and pattern matching for instanceof: 17. "
              "Pattern matching for switch: 21. Virtual threads: 21.",
      quiz={
          "q": "What does `record Point(int x, int y) {}` generate for you?",
          "options": [
              "A canonical constructor, x() and y() accessors, equals, hashCode and toString",
              "Getters and setters, equals, hashCode and toString — a mutable data class",
              "Only a constructor and accessors; equals and hashCode still need writing",
              "The same as a class annotated @Data — including a no-arg constructor",
          ],
          "answer": 0,
          "why": "Option A is right, and the accessor NAMES are the detail people get "
                 "wrong: `x()`, not `getX()`. Option B is wrong on the central point — "
                 "records are IMMUTABLE, there are no setters and the fields are final. "
                 "Option C understates it; correct equals and hashCode are most of why "
                 "records exist. Option D imports Lombok's behaviour: records have no "
                 "no-arg constructor, because every component must be supplied.",
      },
      pitfalls="A record's fields are final but a MUTABLE FIELD INSIDE ONE IS STILL "
               "MUTABLE — `record Team(List<String> members)` hands out the same list "
               "every caller can modify. Defensive-copy in the compact constructor. And "
               "`var` in a for-each over a raw collection infers Object, silently losing "
               "type safety.",
      followups="When should a record NOT be used? When the type needs to hide its "
                "representation, needs mutability, or needs to extend a class — records "
                "are transparent carriers by design, and that transparency is the "
                "feature.",
      difficulty="Easy", frequency="Increasingly common — expected knowledge on Java 17+",
      mnemonic="var infers, record carries, sealed closes, \"\"\" quotes."),

    # ══════════════════════════════════════════════════════════════════
    #  Concurrency
    # ══════════════════════════════════════════════════════════════════

    Q("concurrency",
      "synchronized, volatile, and atomic — three different problems",
      "Three tools that people reach for interchangeably and that solve "
      "different things. `synchronized` stops two threads running the same block "
      "at once. `volatile` makes sure a change one thread makes is actually SEEN "
      "by another — but does nothing about two threads changing it at the same "
      "time. Atomic classes do read-modify-write as one indivisible step. "
      "Choosing the wrong one gives you code that works in testing and fails "
      "under load.",
      "There are TWO problems, not one. MUTUAL EXCLUSION: two threads must not "
      "interleave inside a critical section. VISIBILITY: a write by one thread "
      "must become visible to another, which is not automatic because each "
      "thread may cache values in registers and the compiler may reorder. "
      "`volatile` solves visibility and ordering ONLY — it guarantees reads see "
      "the latest write and establishes a happens-before edge, but `count++` on "
      "a volatile is still three operations and still races. `synchronized` "
      "solves both, at the cost of blocking. ATOMIC classes solve both for a "
      "single variable using a CAS loop, which is lock-free and usually faster "
      "under contention.",
      ["concurrency", "volatile", "synchronized", "atomic", "memory-model"],
      code="import java.util.concurrent.atomic.*;\n\n// WRONG: volatile gives visibility, not atomicity\nstatic volatile int broken = 0;\nstatic void incBroken() { broken++; }        // read, add, write — 3 steps\n\n// RIGHT for a counter: one indivisible operation\nstatic final AtomicInteger counter = new AtomicInteger();\nstatic void incAtomic() { counter.incrementAndGet(); }\n\n// RIGHT for a compound invariant spanning several fields\nstatic final Object lock = new Object();\nstatic int a = 0, b = 0;\nstatic void moveOne() {\n    synchronized (lock) { a--; b++; }        // a+b stays constant\n}\n\n// THE CLASSIC USE OF volatile — a stop flag, written once, read often\nstatic volatile boolean running = true;\nstatic void worker() {\n    while (running) { /* ... */ }             // without volatile this may\n}                                             // never observe the change",
      output="(no output — this entry is about what each construct guarantees;\n run 1,000 threads through incBroken() and the total is reliably\n LESS than 1,000, while incAtomic() is always exact)",
      gotcha="Q: `count` is volatile and ten threads run `count++` a thousand times "
             "each. Final value?  LESS THAN 10,000, and unpredictably so. `++` is read, "
             "add, write — three separate operations — and volatile makes each one "
             "visible without making the trio indivisible. Two threads can both read 5, "
             "both write 6, and one increment vanishes. VOLATILE IS ABOUT SEEING, NOT "
             "ABOUT WINNING, and that single sentence is the most useful thing to "
             "remember here.",
      version="The Java Memory Model was specified properly in Java 5 (JSR-133); "
              "volatile's ordering guarantees are unreliable folklore before that. "
              "VarHandle (9) replaced most legitimate uses of sun.misc.Unsafe. Virtual "
              "threads (21) make blocking cheap, which changes when you would reach for "
              "a lock-free design at all.",
      quiz={
          "q": "A boolean `stop` flag is set by one thread and polled in a loop by "
               "another. What is the minimum correct tool?",
          "options": [
              "volatile — this is a pure visibility problem with a single writer",
              "synchronized on every read and write, since volatile does not order anything",
              "AtomicBoolean — a plain volatile boolean can still tear",
              "Nothing; a write to a boolean is atomic, so it is already visible",
          ],
          "answer": 0,
          "why": "Option A is right and it is volatile's textbook use: one writer, many "
                 "readers, no compound update. Option B works and is heavier than "
                 "needed, and its premise is wrong — volatile does establish ordering. "
                 "Option C confuses atomicity with visibility: a boolean write cannot "
                 "tear (only long/double may, and only if non-volatile), so "
                 "AtomicBoolean buys nothing here. Option D is the dangerous one — the "
                 "write IS atomic and may still never be SEEN by the other thread, "
                 "which is exactly the bug volatile exists to prevent.",
      },
      pitfalls="`synchronized` on a method locks `this` (or the Class for a static "
               "method), so an unrelated caller synchronizing on your object can block "
               "you — prefer a private final lock object. Double-checked locking "
               "REQUIRES the field to be volatile; without it the reference can be "
               "published before the constructor finishes and another thread sees a "
               "half-built object. And `long`/`double` writes are not atomic unless "
               "volatile.",
      followups="What is happens-before? The ordering relation the memory model "
                "guarantees: unlocking a monitor happens-before locking it, a volatile "
                "write happens-before a subsequent read of it, and Thread.start() "
                "happens-before anything the thread does. EVERY correct concurrent "
                "program is built from those edges.",
      difficulty="Hard", frequency="Very common at mid/senior level",
      mnemonic="volatile = SEEING. synchronized = TAKING TURNS. atomic = ONE STEP."),

    # ══════════════════════════════════════════════════════════════════
    #  JVM & memory
    # ══════════════════════════════════════════════════════════════════

    Q("jvm",
      "Stack vs heap, and how a Java memory leak is even possible",
      "Java has two places to put things. The STACK holds each method call's "
      "local variables and disappears when the method returns — it is automatic "
      "and you never think about it. The HEAP holds every object, and it is "
      "cleaned by the garbage collector, which frees anything nothing can reach "
      "any more. People say Java cannot leak memory because of that. It can: if "
      "you accidentally KEEP a reference to something you are finished with, the "
      "collector correctly concludes it is still needed and keeps it forever.",
      "Each thread has its own STACK holding frames of local variables, "
      "parameters and return addresses — fixed size, freed on return, and "
      "exceeding it is StackOverflowError. The HEAP is shared and holds all "
      "objects; exhausting it is OutOfMemoryError. GC collects by REACHABILITY "
      "from GC roots (stack locals, static fields, JNI references), not by "
      "reference counting — so cycles are collected fine. A JAVA MEMORY LEAK IS "
      "AN UNINTENDED REACHABLE REFERENCE: a static collection that only ever "
      "grows, a listener never unregistered, a ThreadLocal on a pooled thread, "
      "an inner class holding its outer, or a cache with no eviction. The "
      "collector is behaving correctly in every case.",
      ["jvm", "memory", "gc", "leak", "stack", "heap"],
      code="import java.util.*;\n\n// THE MOST COMMON LEAK: a static collection that only grows\nclass Registry {\n    private static final List<Object> ALL = new ArrayList<>();\n    static void register(Object o) { ALL.add(o); }\n    // ...and nothing ever removes. ALL is a GC root, so every object\n    // ever registered stays reachable for the life of the JVM.\n}\n\n// A leak the collector cannot help with, in three lines:\nMap<String, byte[]> cache = new HashMap<>();\nfor (int i = 0; i < 3; i++) {\n    cache.put(\"key\" + i, new byte[1024 * 1024]);   // 1MB each, never evicted\n}\nSystem.out.println(\"cached: \" + cache.size());\n\n// Stack, not heap — recursion with no base case:\nstatic int depth(int n) { return depth(n + 1); }\ntry {\n    depth(0);\n} catch (StackOverflowError e) {\n    System.out.println(\"StackOverflowError — an ERROR, not an Exception\");\n}",
      output="cached: 3\nStackOverflowError — an ERROR, not an Exception",
      gotcha="Q: does setting a variable to null free the object?  NOT DIRECTLY — it "
             "only removes ONE reference. The object is collectable when NOTHING "
             "reachable points at it, so nulling a local that was about to go out of "
             "scope anyway does nothing at all. Nulling a field in a long-lived object "
             "genuinely can help. AND THE COROLLARY: System.gc() is a SUGGESTION the "
             "JVM may ignore, and calling it in production code is almost always a "
             "mistake.",
      version="PermGen was replaced by METASPACE in Java 8 — class metadata moved off "
              "the heap into native memory, so 'java.lang.OutOfMemoryError: PermGen "
              "space' no longer exists and the old -XX:MaxPermSize flag is gone. G1 "
              "became the default collector in Java 9; ZGC and Shenandoah are the "
              "low-pause options.",
      quiz={
          "q": "Which of these is a real Java memory leak?",
          "options": [
              "A static Map used as a cache with no eviction policy",
              "Two objects that reference each other and nothing else",
              "A large array allocated inside a method that has returned",
              "An object whose finalize() method was never called",
          ],
          "answer": 0,
          "why": "Option A is the classic: a static field is a GC root, so everything "
                 "in that map is permanently reachable and the collector is right to "
                 "keep it. Option B is the reference-counting intuition and Java does "
                 "not use reference counting — an unreachable CYCLE is collected "
                 "normally. Option C is collected as soon as the frame pops; the local "
                 "was the only reference. Option D confuses finalization with "
                 "reclamation, and finalize() is deprecated for removal precisely "
                 "because it was unreliable.",
      },
      complexity="Stack per thread defaults to around 512KB-1MB (-Xss), which is why "
                 "thousands of platform threads is expensive and why virtual threads "
                 "(21) matter. Heap is -Xmx. A typical object header is 12-16 bytes, so "
                 "an Integer costs ~16 bytes against an int's 4 — the ratio behind every "
                 "'use int[] not List<Integer>' recommendation.",
      pitfalls="A ThreadLocal on a POOLED thread is not cleaned when your task ends — "
               "the thread lives on and so does the value. Always remove() in a finally. "
               "Non-static inner classes hold their outer instance (see the nested-class "
               "entry). And an unbounded queue between a fast producer and a slow "
               "consumer is a leak with a different name.",
      followups="How would you actually find one? Take two heap dumps a few minutes "
                "apart under load, compare them, and look at what grew — then follow the "
                "RETAINED path back to a GC root. The growing class is rarely the "
                "problem; whatever is holding it is.",
      difficulty="Medium", frequency="Very common",
      mnemonic="GC frees the UNREACHABLE. A leak is something you are still holding."),

    ]
