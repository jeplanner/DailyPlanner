"""Java bank — ten-section deep dives, keyed by entry title.

WHY A PATCH DICT RATHER THAN A FIELD ON THE ENTRY. A deep dive is 12,000
characters; an entry is 3,000. Inlining them would make the entry modules
unreadable — you would scroll past three screens of prose to find the next
title — and the ratio only gets worse. Keeping them keyed by TITLE means the
entry modules stay browsable and a deep dive can be added to any entry later
without touching it.

Keyed by title rather than by index for the same reason progress is: inserting
an entry in the middle of a module must not silently re-point every deep dive
at the wrong topic. A title that matches nothing is a self-check failure, not
a silent no-op.

THE TEN SECTIONS are fixed and ordered as pedagogy, not preference:
    1  the goal, in plain English
    2  the intuition — why the rule exists at all
    3  the mechanism, in detail
    4  edge cases and failure modes
    5  the alternatives, and what each costs
    6  numbered how-to steps
    7  the answer in plain language — spoken register, for saying out loud
    8  the code, line by line
    9  a full trace
   10  complexity, numbered mistakes, one-sentence takeaway
"""

DEEP = {}


DEEP["equals and hashCode — the contract, and what breaks when you ignore it"] = [
"""1. THE GOAL IN PLAIN ENGLISH — teaching Java when two different objects count as the same thing

By default, Java thinks two objects are "equal" only if they are literally the SAME OBJECT — the same
thing in memory. That is almost never what you want for a value. Two `Point` objects both holding
(1, 2) are different objects and are obviously the same point, and you have to say so.

Saying so takes TWO methods, not one, and that is the entire source of the trouble.

    equals(Object)  — "do these two hold the same values?"
    hashCode()      — "give me a number summarising this object's values"

WHY TWO? Because a HashSet does not compare you against every element it holds — that would be O(n)
and would defeat the point of a hash set. It uses hashCode() to jump STRAIGHT to one small bucket, and
only compares with equals() against the handful of things already in that bucket.

    SO IF TWO EQUAL OBJECTS RETURN DIFFERENT HASH CODES, THEY GO TO DIFFERENT BUCKETS AND ARE NEVER
    COMPARED. The set contains one of them and cannot find the other. Nothing errors. `contains`
    simply returns false for an object the set demonstrably equals.

THE EVERYDAY VERSION: a library filing books by the first letter of the author's surname. equals is
"is this the same book?" and hashCode is "which shelf?". Get the shelf wrong and the book is still in
the library, and nobody will ever find it — because the search only ever looks on one shelf.

TERMS AS THEY APPEAR:
- CONTRACT: the rules the two methods must jointly satisfy, documented on java.lang.Object.
- BUCKET / BIN: one slot of a hash table's internal array.
- COLLISION: two unequal objects landing in the same bucket. Normal, expected, and handled.""",

"""2. THE INTUITION — the contract has one direction, and only one

The rule is stated as an implication, and the direction matters enormously:

    IF a.equals(b) THEN a.hashCode() == b.hashCode()          ← REQUIRED
    IF a.hashCode() == b.hashCode() THEN a.equals(b)          ← NOT required, and impossible anyway

THE SECOND DIRECTION CANNOT BE REQUIRED. A hashCode returns an int — about 4.3 billion possible values
— and there are infinitely many possible Strings. By the pigeonhole principle, distinct objects MUST
share hash codes eventually. A collision is not a bug; a hash table is built to handle them.

SO THE ONE-WAY CONTRACT IS EXACTLY AS STRONG AS IT CAN BE. Equal things must agree on their hash;
unequal things are free to agree or not.

WHICH IMMEDIATELY TELLS YOU THE TWO WAYS TO BREAK IT:

    OVERRIDE equals AND NOT hashCode — the common one. Two objects are now equal with different hash
    codes, which violates the contract directly. HashSet accumulates duplicates; HashMap loses keys.

    OVERRIDE hashCode AND NOT equals — rarer, and it does NOT violate the contract. Equal objects
    (identical references) still share a hash. But it is useless: the objects collide into one bucket,
    Object.equals compares references, and they are all kept as distinct entries. You have made the
    hash table slower without making it more correct.

    THAT ASYMMETRY IS WORTH INTERNALISING. Forgetting hashCode is a CORRECTNESS bug. Forgetting equals
    is a PERFORMANCE bug that behaves exactly as if you had overridden neither.

AND A LEGAL-BUT-TERRIBLE IMPLEMENTATION EXISTS: `return 1;`. Every object shares a hash code, the
contract holds perfectly, and every entry lands in one bucket. Since Java 8 that bucket becomes a
red-black tree at eight entries, so lookup degrades to O(log n) rather than the O(n) it would have
been before. STILL WRONG, and now wrong more slowly.""",

"""3. THE MECHANISM — what HashSet.contains actually does, step by step

    set.contains(new Point(1, 2))

    STEP 1. Call hashCode() on the argument.                     → say 994
    STEP 2. SPREAD it: h ^ (h >>> 16), mixing high bits down.
    STEP 3. Mask to an index: spread & (tableLength - 1).        → say bucket 2
    STEP 4. Walk bucket 2 — a linked list, or a tree if it grew past 8.
    STEP 5. For each entry: first `==` (a cheap identity check), then equals().
    STEP 6. Return true on the first match; false if the bucket runs out.

    NOTICE WHAT NEVER HAPPENS: NO OTHER BUCKET IS EVER EXAMINED. That is the whole performance
    argument for a hash table, and it is exactly why a wrong hashCode is fatal rather than merely
    inefficient. The object may be sitting in bucket 7; contains() will never look there.

THE FIVE FORMAL REQUIREMENTS ON equals, from the Object javadoc:

    REFLEXIVE     x.equals(x) is true.
    SYMMETRIC     x.equals(y) implies y.equals(x).
    TRANSITIVE    x.equals(y) and y.equals(z) implies x.equals(z).
    CONSISTENT    repeated calls give the same answer, if nothing changed.
    NULL          x.equals(null) is false — never throws.

SYMMETRY IS THE ONE PEOPLE BREAK, and they break it with subclasses. If `Point.equals` uses
`instanceof Point` and `ColourPoint extends Point` adds a colour to its comparison, then
`point.equals(colourPoint)` is TRUE (the point sees a Point with matching coordinates) while
`colourPoint.equals(point)` is FALSE (the colour point sees no colour). Asymmetric, and a collection
containing both behaves differently depending on iteration order.

    THE TWO WAYS OUT, AND NEITHER IS FREE:
    `getClass() != o.getClass()` — symmetric, and it means a subclass instance is never equal to a
    superclass instance, which breaks Liskov substitutability.
    `instanceof` plus a `canEqual` method — symmetric and correct, and it is machinery.
    THE PRACTICAL ANSWER: make value classes FINAL, or use a `record`, and the question does not
    arise.

CONSISTENCY IS THE OTHER SILENT ONE. Nothing stops you computing a hash from a mutable field. Mutate
it after inserting into a set and the object is now in the WRONG BUCKET — set.contains(thatVeryObject)
returns false, and it will still be there in the iteration, and in size().""",

"""4. EDGE CASES AND FAILURE MODES

CASE 1 — equals WITHOUT hashCode. The default hashCode is identity-based, so two equal objects almost
certainly differ. HashSet holds duplicates; HashMap.get returns null for a key it contains; and every
direct `a.equals(b)` test you write passes, which is why this survives review. THE BUG IS INVISIBLE
UNTIL THE OBJECT MEETS A HASH-BASED COLLECTION.

CASE 2 — hashCode WITHOUT equals. Contract intact, behaviour unchanged from overriding neither, and
now everything collides. A pure performance loss.

CASE 3 — A MUTABLE FIELD IN THE HASH. Insert, mutate, and the object is unreachable in a collection
that still contains it. THE FIX IS NOT A BETTER hashCode — it is immutable fields.

CASE 4 — ASYMMETRY VIA A SUBCLASS. See section 3. Prefer final classes or records.

CASE 5 — `equals(MyType other)` INSTEAD OF `equals(Object)`. This is an OVERLOAD, not an override, so
collections keep calling Object.equals and your method is never invoked. `@Override` turns this into a
compile error instantly, which is the entire argument for always writing it.

CASE 6 — FLOATING-POINT FIELDS. `==` on a double says NaN != NaN, so an object holding NaN would not
equal itself and REFLEXIVITY breaks. Use Double.compare or Objects.equals on the boxed values —
Double.equals is defined to treat NaN as equal to itself precisely so this works.

CASE 7 — ARRAY FIELDS. `Objects.hash(arr)` hashes the array REFERENCE, not its contents, so two
objects with identical arrays get different hashes. Use Arrays.hashCode, or Arrays.deepHashCode for
nested arrays.

CASE 8 — INHERITING equals FROM A PARENT WITH EXTRA FIELDS. A subclass adding state must include it,
and then section 3's symmetry problem arrives.

CASE 9 — `return 1;` as a hashCode. Legal, contract-compliant, and it turns your HashMap into a
treeified list.

CASE 10 — RELYING ON hashCode ACROSS JVM RUNS. String.hashCode is specified and stable; almost
nothing else is. Object.hashCode varies per run. NEVER PERSIST A hashCode or use it as a database key.""",

"""5. THE ALTERNATIVES — and what each costs

WRITE IT BY HAND.
    Full control, and it is the version an interview asks for. The canonical shape is in section 8.
    COST: it is boilerplate, and every field added later must be added to both methods — which is
    exactly the maintenance failure that produces a class whose equals is quietly out of date.

LET THE IDE GENERATE IT.
    Correct, instantly, and regenerable when fields change. THE DEFAULT ANSWER FOR A REAL CODEBASE.
    COST: it does not regenerate itself, so the same drift is possible, just less likely.

`Objects.hash(a, b, c)` (Java 7+).
    One line and correct. COST: it ALLOCATES A VARARGS ARRAY on every call and boxes every primitive.
    For an object used as a hot-loop map key that is measurable, and the hand-written
    `31 * result + field` form avoids it. Measure before caring.

A `record` (Java 16+).
    Generates a correct equals, hashCode and toString from the components, and cannot drift because
    there is nothing to keep in sync. IT IS THE RIGHT ANSWER FOR A VALUE CLASS IN MODERN JAVA, and it
    also sidesteps the subclass-symmetry problem entirely by being implicitly final.
    COST: no inheritance, no mutability, and the representation is public by design.

LOMBOK'S @EqualsAndHashCode.
    Generates both at compile time. COST: an annotation processor in the build, and its default of
    including every field is frequently wrong — a cache or a back-reference should not be in equals.

APACHE COMMONS EqualsBuilder / HashCodeBuilder.
    Readable and reflective variants exist that are convenient and slow. Largely superseded by
    Objects.hash and records.

WHAT TO ACTUALLY SAY IN AN INTERVIEW: "For a value class I'd use a record. If it has to be a class,
I'd let the IDE generate them from the identity fields, keep those fields final, and write @Override
on both so an accidental overload is a compile error."
""",

"""6. HOW TO WRITE IT — numbered steps

STEP 1 — ASK WHICH FIELDS DEFINE IDENTITY. Not all of them: a cached value, a lazily-computed field,
a back-reference to a parent, a timestamp of last access — none of those make two objects different
things.

STEP 2 — MAKE THOSE FIELDS FINAL. It is the only real protection against the mutable-key failure, and
it is cheaper than any amount of documentation.

STEP 3 — WRITE @Override ON BOTH. It converts `equals(MyType)` — an overload that will never be
called — from a silent bug into a compile error.

STEP 4 — START equals WITH THE IDENTITY FAST PATH. `if (this == o) return true;` It is one comparison
and it short-circuits the common case of comparing an object with itself.

STEP 5 — USE `instanceof`, WHICH HANDLES null FOR FREE. `if (!(o instanceof Point p)) return false;`
— and since Java 16 that pattern also binds the cast variable, removing the separate cast line.

STEP 6 — COMPARE FIELD BY FIELD, CHEAPEST FIRST. Primitives with `==`, doubles with Double.compare,
objects with Objects.equals (null-safe), arrays with Arrays.equals.

STEP 7 — USE THE SAME FIELDS IN hashCode, IN THE SAME ORDER. `Objects.hash(x, y)` unless it is a hot
path.

STEP 8 — DO NOT INCLUDE A MUTABLE FIELD. If you must, document loudly that the object cannot be used
as a key after mutation — and then reconsider making it immutable.

STEP 9 — TEST THE FIVE PROPERTIES. Reflexive, symmetric, transitive, consistent, null-safe. And test
the one that actually matters: put two equal objects in a HashSet and assert the size is 1.

STEP 10 — OR SKIP ALL OF IT AND WRITE A RECORD.""",

"""7. THE ANSWER IN PLAIN LANGUAGE — what you would say out loud

'By default Java treats two objects as equal only if they're the same object in memory, which is
almost never what you want for a value. So you override equals to say what "the same" means — and you
have to override hashCode at the same time, because of how hash-based collections work.

A HashSet doesn't compare your object against everything it holds; that would be linear and would
defeat the point. It calls hashCode to jump straight to one bucket, and only calls equals against the
handful of things already in that bucket. So if two equal objects return different hash codes they
land in different buckets and are NEVER COMPARED. The set contains one and can't find the other.
Nothing throws — contains just returns false for an object the set demonstrably equals.

The contract runs in exactly one direction: equal objects MUST have equal hash codes, and the reverse
is not required and couldn't be. A hashCode is an int — about four billion values — and there are
infinitely many Strings, so by pigeonhole distinct objects must share hashes eventually. A collision
isn't a bug; the table is built to handle them.

That one-way rule also tells you which mistake is which. Overriding equals and forgetting hashCode is
a CORRECTNESS bug — the collection loses things. Overriding hashCode and forgetting equals doesn't
violate the contract at all; it just makes everything collide into one bucket while Object.equals
still compares references, so you've made the table slower without making it more correct.

For the implementation: I'd start with the identity fast path, `this == o`. Then `instanceof`, which
handles null for free — and since Java 16 the pattern form binds the cast variable too, so you don't
need a separate cast line. Then compare the identity fields, cheapest first. And use exactly those
same fields in hashCode.

Two things I'd flag. Use IMMUTABLE fields — if a field in the hash changes after the object is in a
set, the object is now in the wrong bucket and contains(thatVeryObject) returns false while it's still
sitting in the iteration and still counted in size(). And always write @Override, because
`equals(MyType other)` is an OVERLOAD rather than an override, so collections keep calling
Object.equals and your method is never invoked. @Override turns that from a silent bug into a compile
error.

Symmetry is the subtle one. If a subclass adds a field to the comparison, the parent thinks they're
equal and the child doesn't, so equals is asymmetric and a collection holding both behaves differently
depending on iteration order. The practical fix is to make value classes final — or just use a record,
which generates all of this correctly, can't drift when you add a field, and is implicitly final so
the symmetry question never arises.'""",

"""8. THE CODE, LINE BY LINE

    public final class Point {
    //     ^^^^^ FINAL. It removes the subclass-symmetry problem entirely rather
    //     than solving it, and for a value class there is no cost.

        private final int x, y;
        //      ^^^^^ FINAL FIELDS. The only real protection against the
        //      mutable-key failure — an object whose hash changes after
        //      insertion is unreachable in a collection that still holds it.

        @Override
        //  ^^^^^^^^^ NOT DECORATION. Without it, `equals(Point o)` compiles
        //  happily as an OVERLOAD, collections keep calling Object.equals, and
        //  your method is never invoked. With it, that is a compile error.
        public boolean equals(Object o) {
        //             ^^^^^^^ the parameter MUST be Object to override.

            if (this == o) return true;
            // ^ identity fast path. One comparison, and it short-circuits the
            //   extremely common case of an object compared with itself —
            //   which happens on every set.contains(x) that finds x.

            if (!(o instanceof Point p)) return false;
            //    ^^^^^^^^^^^^^^^^^^^^^ instanceof is FALSE for null, so this
            //    single line covers the null check too — no separate `o == null`.
            //    ^ the `p` binding is Java 16+ pattern matching: it replaces the
            //    `Point p = (Point) o;` line the old form needed.

            return x == p.x && y == p.y;
            //     ^ primitives compare with ==. For OBJECT fields use
            //       Objects.equals(a, b) — null-safe both ways. For DOUBLES use
            //       Double.compare, because == says NaN != NaN and an object
            //       holding NaN would then not equal ITSELF, breaking reflexivity.
            //       For ARRAYS use Arrays.equals — == compares references.
        }

        @Override
        public int hashCode() {
            return Objects.hash(x, y);
            //     ^ THE SAME FIELDS as equals, always. Adding a field to one and
            //       not the other is the drift that breaks the contract months
            //       after the class was written.
            //     ^ COST: allocates a varargs array and boxes both ints. Fine
            //       almost everywhere; for a hot-loop map key write the manual
            //       form below instead.
        }
    }

THE MANUAL hashCode, for when allocation matters:

    int result = Integer.hashCode(x);
    result = 31 * result + Integer.hashCode(y);
    return result;
    // ^ 31 is odd and prime, and 31*i compiles to (i << 5) - i, which mattered
    //   more in 1995 than now. ANY odd multiplier works; the primality is
    //   folklore rather than requirement. The MULTIPLY-AND-ADD is the part that
    //   matters — it makes the result depend on field ORDER, so (1,2) and (2,1)
    //   get different hashes where a plain sum would not.

OR, IN MODERN JAVA, THE WHOLE THING:

    public record Point(int x, int y) {}
    // equals, hashCode and toString generated from the components, implicitly
    // final, and it CANNOT drift when a component is added.""",

"""9. THE TRACE — watch the object become unfindable

TWO CLASSES, IDENTICAL EXCEPT FOR ONE OVERRIDE.

    class Good { int x; equals→compares x; hashCode→Objects.hash(x); }
    class Bad  { int x; equals→compares x; NO hashCode override; }

    Set<?> set = new HashSet<>();  table length 16.

GOOD:

    step                                  value           result
    ---------------------------------------------------------------------------
    set.add(new Good(5))
      hashCode() of Good(5)                 1029          → bucket 5
      bucket 5 is empty                                   → INSERTED
    set.contains(new Good(5))
      hashCode() of the NEW Good(5)         1029          → bucket 5   (same!)
      walk bucket 5, call equals            true          → TRUE
    set.size()                                            → 1

BAD:

    step                                  value           result
    ---------------------------------------------------------------------------
    set.add(new Bad(5))
      Object.hashCode() — identity      1698156408        → bucket 8
      bucket 8 is empty                                   → INSERTED
    set.contains(new Bad(5))
      Object.hashCode() of the NEW one   712345678        → bucket 14  (DIFFERENT)
      walk bucket 14 — EMPTY                              → FALSE
      equals() IS NEVER CALLED AT ALL
    set.add(new Bad(5))  again                            → INSERTED, bucket 3
    set.size()                                            → 2

    THE LINE THAT MATTERS IS "equals() IS NEVER CALLED AT ALL". The two objects are equal by every
    definition the class gives, `a.equals(b)` returns true if you test it directly, and the set never
    asks — because it looked in one bucket and they were not in the same one.

    AND NOTE THE SIZE. The set now contains two objects that are equal to each other. Every invariant
    a Set is supposed to provide is broken, silently, with no exception anywhere.

THE MUTATION FAILURE, traced:

    Good g = new Good(5);
    set.add(g);                    hashCode 1029 → bucket 5, inserted
    g.x = 6;                       (only possible if x is not final)
    set.contains(g)                hashCode is now 1060 → bucket 4
                                   bucket 4 is empty → FALSE
    set.size()                     → 1
    for (Good o : set) ...         → yields g

    THE SET CONTAINS AN OBJECT IT CANNOT FIND. contains(g) is false, size() is 1, and iterating
    produces g. That is why the fields must be final, and it is why the fix is immutability rather
    than a cleverer hash function.

WHICH LINE CAUSED WHICH ROW:

    `Objects.hash(x)` in Good     produced the SAME hash for two distinct objects, which is the entire
                                 requirement. Delete it and every row of the BAD table follows.
    Object's identity hashCode   produced 1698156408 and 712345678 — arbitrary, different every run,
                                 and different for every instance. That is correct behaviour for
                                 Object and catastrophic as a value's hash.
    `g.x = 6`                    produced the unfindable-object trace. Making x final makes that line
                                 a compile error, which is the whole point.""",

"""10. COMPLEXITY, THE MISTAKES, AND THE TAKEAWAY

    HashSet.contains / HashMap.get: O(1) average, O(log n) worst case since Java 8 (treeified bins),
    O(n) before that.
    A CORRECT hashCode is what makes the average case average. A constant hashCode is contract-
    compliant and turns every operation into the worst case.
    Objects.hash allocates a varargs array and boxes primitives — irrelevant almost everywhere,
    measurable for a hot-loop map key.

    THE CONTRACT, in one line: a.equals(b) IMPLIES a.hashCode() == b.hashCode(). One direction only,
    and the reverse is impossible to require.

THE #1 MISTAKE: overriding equals and not hashCode. Every direct test passes; the collection loses
things. It is a correctness bug that is invisible until the object meets a HashMap.

THE #2 MISTAKE: a mutable field in the hash. Insert, mutate, and the object is unreachable in a
collection that still contains it and still counts it in size().

THE #3 MISTAKE: `public boolean equals(MyType o)`. An overload, never called by any collection.
@Override catches it at compile time, which is the entire reason to write @Override.

THE #4 MISTAKE: asymmetric equals via a subclass. Make value classes final, or use a record.

THE #5 MISTAKE: `==` on double fields. NaN != NaN breaks reflexivity — an object would not equal
itself. Use Double.compare.

THE #6 MISTAKE: `Objects.hash(someArray)`. That hashes the array REFERENCE. Use Arrays.hashCode.

THE #7 MISTAKE: different fields in equals and hashCode. Usually drift — a field added to one and not
the other, six months later.

THE #8 MISTAKE: persisting a hashCode, or using it as a database key. Only String's is specified and
stable; Object's varies per JVM run.

THE #9 MISTAKE: `return 1;`. Contract-compliant, and it turns your hash table into one treeified
bucket.

THE #10 MISTAKE: writing all of this by hand in 2026 for a plain value class. A record generates it
correctly, cannot drift, and is implicitly final.

ONE-SENTENCE TAKEAWAY: hashCode picks the BUCKET and equals decides membership INSIDE it, so two equal
objects with different hash codes land in different buckets and are never compared — the set contains
one and returns false for the other with no exception anywhere — which is why the contract runs one
way (equal implies same hash, never the reverse), why the fields must be immutable, why @Override is
not decoration, and why a `record` is the right answer whenever the class is just a value.""",
]


DEEP["How HashMap actually works — buckets, collisions, and treeification"] = [
"""1. THE GOAL IN PLAIN ENGLISH — finding something without looking through everything

A HashMap answers "what value is stored under this key?" in roughly constant time, no matter how many
entries it holds. A million entries and a hundred entries cost the same to look up. That is a strange
promise and it is worth understanding how it is kept.

THE IDEA: keep an ARRAY of slots. To find where a key belongs, turn the key into a number — that is
hashCode() — and use that number to pick a slot. Now a lookup is arithmetic plus one array access,
which does not care how big the array is.

    THE PROBLEM THAT IMMEDIATELY FOLLOWS: two different keys can produce the same slot. That is a
    COLLISION and it is not rare — it is guaranteed, because there are more possible keys than slots.

    THE ANSWER: each slot holds a small LIST rather than a single entry. A lookup jumps to the slot
    and then walks that short list comparing with equals(). As long as the lists stay short, the walk
    is a handful of comparisons and the whole thing is still effectively constant.

    THE PROBLEM AFTER THAT: what if the lists do not stay short? Since Java 8, a slot that grows past
    eight entries is converted into a BALANCED TREE, so even a pathological case degrades to O(log n)
    rather than O(n).

    AND THE LAST PIECE: as entries accumulate the lists lengthen everywhere. So when the table is 75%
    full, HashMap DOUBLES the array and redistributes everything, keeping the lists short again.

TERMS AS THEY APPEAR:
- BUCKET / BIN: one slot of the array.
- LOAD FACTOR: how full the table is allowed to get before it doubles. Default 0.75.
- TREEIFY: converting an over-long bucket into a red-black tree.""",

"""2. THE INTUITION — three design choices, each forced by the one before it

CHOICE 1: THE TABLE LENGTH IS ALWAYS A POWER OF TWO.

    The obvious way to turn a hash into an index is `hash % length`. A modulo is a division, and
    division is one of the slowest integer instructions on any CPU. But if the length is a power of
    two, `hash % length` is exactly `hash & (length - 1)` — a single AND against a mask of low bits.

    SO THE POWER-OF-TWO CHOICE BUYS A DIVISION-FREE INDEX, on the hottest path in the class.

CHOICE 2: THE HASH IS SPREAD BEFORE MASKING — h ^ (h >>> 16).

    This is FORCED BY CHOICE 1 and it is the part people miss. A mask keeps only the LOW bits and
    throws the high ones away entirely. So two keys differing only in their high bits collide on
    every single lookup, forever.

    Consider a key type whose hashCode is `id * 65536` — perfectly reasonable-looking. Every such
    hash has sixteen zero low bits, so with a table of 16 they ALL map to bucket 0.

    THE FIX IS ONE LINE: XOR the top 16 bits down into the bottom 16. Now a difference anywhere in
    the int influences the low bits, and the mask sees it. It is deliberately cheap — one shift and
    one XOR — because it runs on every operation, and it is a mitigation rather than a real hash
    function: it makes a mediocre hashCode survivable, not good.

CHOICE 3: OVER-LONG BUCKETS BECOME TREES.

    Before Java 8, a bucket was always a linked list. That made worst-case lookup O(n) — and it was
    ATTACKABLE. A web framework parsing user-supplied form parameters into a HashMap could be sent
    thousands of keys engineered to share one bucket, turning an O(n) parse into O(n²) and taking the
    server down with a single small request. That was a real, published denial-of-service class
    affecting most languages of the era, not a theoretical one.

    TREEIFICATION BOUNDS THE DAMAGE. At 8 entries in one bucket — and only if the table is at least
    64 long, because otherwise resizing is the better response — the bucket becomes a red-black tree
    and lookup within it is O(log n). The attack goes from quadratic to n log n, which is survivable.

    NOTE THE TWO THRESHOLDS. Eight is chosen because with a decent hash the probability of eight
    entries in one bucket is vanishingly small (Poisson, roughly 6 in 100 million), so a bucket that
    long means the hash is bad or hostile. Sixty-four exists so that a small, dense table resizes
    instead of building trees it will immediately have to take apart.""",

"""3. THE MECHANISM — put and get, in detail

    map.put(key, value)

    1. h = key.hashCode()
    2. h = h ^ (h >>> 16)                     the spread
    3. i = h & (table.length - 1)             the index
    4. if table[i] is empty → place a new Node there. Done.
    5. else walk the bucket:
         for each node, if node.hash == h AND (node.key == key || node.key.equals(key))
             → REPLACE its value, return the old one
       (the `node.hash == h` check first is an optimisation: comparing two ints is far cheaper than
        calling equals, and if the hashes differ the keys cannot be equal)
    6. not found → append a new node. If the bucket now has ≥ 8 entries AND the table is ≥ 64 long,
       TREEIFY the bucket.
    7. if ++size > threshold (capacity × 0.75) → RESIZE.

    map.get(key) is steps 1-3 and 5, with no mutation.

THE RESIZE, AND THE PROPERTY THAT MAKES IT CHEAP:

    The table doubles, from n to 2n. Because n is a power of two, the mask gains exactly ONE BIT. So
    for any entry, its new index is determined by that single new bit:

        the bit is 0 → the entry stays at index i
        the bit is 1 → the entry moves to index i + oldCapacity

    NO ENTRY GOES ANYWHERE ELSE. So a resize splits each bucket into exactly two, in one pass, with no
    rehashing and no comparisons — Java 8 exploits this to split a bucket into a "low" list and a
    "high" list and attach them at i and i + n. That is a direct consequence of choice 1 in section 2.

    THE COST IS O(n) and it is amortized away by the doubling — the same geometric-series argument as
    ArrayList's growth. TOTAL work across n insertions is O(n); a SINGLE insertion can be O(n).

WHY ITERATION ORDER IS WHAT IT IS:

    Iteration walks the table from index 0, and each bucket in list order. So the order is a
    deterministic function of the hash values and the table length. It is NOT random — it is stable
    for a fixed set of keys — AND IT CHANGES THE MOMENT THE TABLE RESIZES.

    That is the worst possible combination for a bug: code accidentally depending on order passes
    every test with ten keys and breaks in production at thirteen.""",

"""4. EDGE CASES AND FAILURE MODES

CASE 1 — A MUTABLE KEY. Insert, then change a field that hashCode reads. The entry is now in the
wrong bucket: map.get(thatVeryKey) returns null, the entry is still in entrySet(), and size() still
counts it. USE IMMUTABLE KEYS. This is the single most common HashMap bug.

CASE 2 — A KEY WITH equals BUT NO hashCode. Covered fully in the equals/hashCode entry: different
buckets, never compared, entries lost.

CASE 3 — null. HashMap ALLOWS one null key (special-cased to bucket 0) and any number of null values.
ConcurrentHashMap allows NEITHER, because `get(k) == null` would be ambiguous between "absent" and
"mapped to null" with no atomic way to disambiguate.

CASE 4 — CONCURRENT MODIFICATION. HashMap is not thread-safe. Before Java 8, a concurrent put during
a resize could produce a CIRCULAR LINKED LIST in a bucket, and a subsequent get would spin forever at
100% CPU — a genuinely famous production failure. Java 8's resize does not reverse the list order, so
that specific infinite loop is gone; the map is still corruptible and still must not be shared.

CASE 5 — RELYING ON ITERATION ORDER. Deterministic, and it changes on resize. Use LinkedHashMap for
insertion order or TreeMap for sorted order.

CASE 6 — A TERRIBLE hashCode. `return 1;` is contract-compliant and puts everything in one bucket,
which since Java 8 is one tree — O(log n) instead of O(1), plus the memory of tree nodes.

CASE 7 — TREEIFICATION NEEDS COMPARABLE KEYS TO BE EFFICIENT. If the keys do not implement Comparable,
the tree falls back to comparing identity hashes to establish an order, which works and is a weaker
guarantee.

CASE 8 — NOT PRE-SIZING A KNOWN-LARGE MAP. Building a map of a million entries from the default
capacity of 16 performs about 17 resizes and copies. `new HashMap<>(expectedSize / 0.75f + 1)` skips
them. The division by the load factor is the part people forget — passing the expected size directly
still resizes once.

CASE 9 — computeIfAbsent MODIFYING THE SAME MAP inside its mapping function. Undefined behaviour on
HashMap and explicitly forbidden on ConcurrentHashMap.

CASE 10 — MEMORY. Every entry is a Node object — roughly 32-40 bytes — plus the table slot. A
Map<Integer,Integer> of a million entries costs tens of megabytes where two int arrays would cost
eight.""",

"""5. THE ALTERNATIVES — and when each is right

HashMap. O(1) average, no ordering, one null key, not thread-safe. THE DEFAULT.

LinkedHashMap. A HashMap plus a doubly-linked list threading every entry in INSERTION order (or, with
one constructor flag, ACCESS order). Iteration is predictable, and the access-order mode plus an
overridden removeEldestEntry gives you an LRU CACHE IN ABOUT FIVE LINES — which is the reason to know
it exists. Costs two extra references per entry.

TreeMap. A red-black tree, O(log n), SORTED by natural order or a comparator, and it offers the
navigation methods a hash map cannot — firstKey, floorKey, ceilingKey, headMap, subMap. Use it when
you need order or range queries. AND REMEMBER IT DEFINES EQUALITY BY compareTo() == 0, NOT equals —
which silently drops entries whose comparator says they tie.

ConcurrentHashMap. Per-bin locking, weakly-consistent iterators that never throw, atomic compound
operations (putIfAbsent, merge, compute), and no nulls. THE ANSWER FOR SHARED MUTABLE MAPS.

EnumMap. Backed by a plain array indexed by the enum's ordinal. Faster and far smaller than a HashMap,
with no hashing at all. ALWAYS PREFER IT FOR ENUM KEYS.

IdentityHashMap. Uses == instead of equals. A specialist tool for object-graph traversal and
serialization, and a trap if reached for by accident.

Map.of / Map.copyOf (Java 9+). Small, immutable, and null-hostile. Ideal for constants. Note the
iteration order of Map.of is deliberately RANDOMISED PER JVM RUN to stop anyone depending on it —
which is the standard library making section 3's point for you.

WHAT TO SAY: "HashMap unless I need ordering, sorting, thread-safety, or enum keys — and for enum keys
it's always EnumMap."
""",

"""6. HOW TO USE IT WELL — numbered steps

STEP 1 — MAKE KEYS IMMUTABLE. Final fields, or a record. It eliminates the most common HashMap bug
outright rather than documenting around it.

STEP 2 — OVERRIDE equals AND hashCode TOGETHER, from the same fields.

STEP 3 — PRE-SIZE WHEN YOU KNOW THE SIZE. `new HashMap<>((int)(n / 0.75f) + 1)`. Dividing by the load
factor is the part people omit, and without it you still resize once at the end.

STEP 4 — USE EnumMap FOR ENUM KEYS. It is an array lookup with no hashing.

STEP 5 — USE getOrDefault, computeIfAbsent AND merge instead of hand-rolled check-then-act. They are
shorter, and on ConcurrentHashMap they are also atomic where the hand-rolled version is not.

STEP 6 — NEVER DEPEND ON ITERATION ORDER. If you need it, say so with the type: LinkedHashMap or
TreeMap.

STEP 7 — DO NOT SHARE A HashMap ACROSS THREADS. ConcurrentHashMap, or confine it to one thread.

STEP 8 — WATCH MEMORY FOR PRIMITIVE-KEYED MAPS. A Map<Integer,Integer> of a million entries is tens of
megabytes; consider a primitive-specialised map or parallel arrays if it matters.

STEP 9 — IF LOOKUPS ARE SLOW, LOOK AT hashCode BEFORE ANYTHING ELSE. A bad hash is the only way a
HashMap becomes slow, and it usually means the key's identity fields were chosen badly.

STEP 10 — FOR AN LRU CACHE, USE LinkedHashMap IN ACCESS ORDER with removeEldestEntry. It is five lines
and it is correct.""",

"""7. THE ANSWER IN PLAIN LANGUAGE — what you would say out loud

'A HashMap keeps an array of buckets. To find where a key goes it calls hashCode, squeezes that into a
bucket index, and looks in that one bucket. Two keys can land in the same bucket — a collision — so
each bucket holds a short list, and lookup walks it comparing with equals. As long as the lists stay
short, a lookup is arithmetic plus a couple of comparisons regardless of how many entries the map
holds.

There are three design choices worth knowing and each one forces the next.

The table length is always a POWER OF TWO, so the index is `hash & (length - 1)` — a bitmask instead
of a modulo, and a division is one of the slowest integer instructions there is.

But a mask keeps only the LOW bits and throws the high ones away, so two keys differing only in their
high bits would collide on every lookup forever. Which is why HashMap SPREADS the hash first — `h xor
(h >>> 16)`, XORing the top sixteen bits down into the bottom. One shift and one XOR, deliberately
cheap because it runs on every operation. It doesn't make a bad hashCode good; it makes it survivable.

Third, since Java 8 a bucket that grows past eight entries becomes a RED-BLACK TREE, so worst-case
lookup is O(log n) instead of O(n). That wasn't a performance nicety — before Java 8 you could send a
web framework thousands of form parameters engineered to share one bucket and turn an O(n) parse into
O(n squared). It was a real denial-of-service class across most languages of that era.

The resize is the nicest consequence of the power-of-two choice. The table doubles, so the mask gains
exactly ONE BIT, which means every entry either stays at index i or moves to i plus the old capacity —
nowhere else. So a resize splits each bucket into two in a single pass with no rehashing at all.

Two things I'd flag as the real-world bugs. Keys must be IMMUTABLE: if you mutate a field that hashCode
reads after inserting, the entry is in the wrong bucket and map.get of that very key returns null while
the entry is still in entrySet and still counted in size. And iteration order is NOT random — it's a
deterministic function of the hashes and the table length, which means it's stable for a given set of
keys and CHANGES the moment the map resizes. That's the worst combination: code that accidentally
depends on it passes every test with ten keys and breaks in production at thirteen.'""",

"""8. THE CODE, LINE BY LINE — the parts of HashMap that matter

    // The spread. This is HashMap.hash(), essentially verbatim.
    static int hash(Object key) {
        int h;
        return (key == null) ? 0 : (h = key.hashCode()) ^ (h >>> 16);
        //     ^^^^^^^^^^^^^^^^^ A NULL KEY HASHES TO 0, so it always lands in
        //     bucket 0. That is the whole of HashMap's null-key support.
        //                          ^^^^^^^^^^^^^^^^^^^^^^^ XOR the top 16 bits
        //     down into the bottom 16. FORCED BY THE MASK: without it, two keys
        //     differing only above bit 16 collide on every lookup, forever.
        //     >>> is the UNSIGNED shift — with >> the sign bit would smear.
    }

    // The index. One AND. No division anywhere.
    int i = hash & (table.length - 1);
    //              ^^^^^^^^^^^^^^^^^ length is a power of two, so length-1 is a
    //              mask of low bits and this is exactly hash % length — at a
    //              fraction of the cost.

    // The bucket walk, with the cheap check first.
    for (Node<K,V> e = table[i]; e != null; e = e.next) {
        if (e.hash == hash && (e.key == key || key.equals(e.key))) return e.value;
        //  ^^^^^^^^^^^^^^ COMPARE THE STORED HASH FIRST. Two ints, one
        //  comparison — and if they differ the keys cannot be equal, so equals()
        //  is skipped entirely. On a bucket full of collisions this is most of
        //  the saving.
        //                   ^^^^^^^^^^^^^^ then identity, which is free and true
        //                   surprisingly often (interned strings, cached boxes).
        //                                    ^^^^^^^^^^^^^^^^^ only then equals.
    }

    // Treeify — the thresholds, and why there are two.
    if (binCount >= TREEIFY_THRESHOLD - 1) {            // 8
        if (table.length < MIN_TREEIFY_CAPACITY)        // 64
            resize();          // a SMALL dense table should GROW, not build trees
        else
            treeifyBin(table, hash);
    }
    // ^ 8 because with a decent hash the chance of eight in one bucket is about
    //   6 in 100 million (Poisson, load factor 0.75) — so a bucket that long
    //   means the hash is bad or hostile, not unlucky.
    // ^ 64 so a 16-slot table that is merely crowded resizes instead of building
    //   trees it would immediately have to dismantle.

    // The resize split — the payoff from the power-of-two choice.
    // Old capacity n, new capacity 2n. The mask gains exactly one bit, so:
    if ((e.hash & oldCap) == 0)  → goes in the LOW list, stays at index i
    else                         → goes in the HIGH list, moves to i + oldCap
    // ^ NO REHASHING AND NO COMPARISONS. One pass, each bucket splits in two,
    //   and no entry can go anywhere else. That is a direct consequence of the
    //   table length being a power of two.""",

"""9. THE TRACE — one put, one collision, one resize

TABLE LENGTH 16, so the mask is 0b1111. Three keys.

    key      hashCode()    h ^ (h>>>16)     & 15     bucket
    -------------------------------------------------------------
    "Aa"          2112              2112        0          0
    "BB"          2112              2112        0          0      ← COLLISION
    "Cc"          2143              2143       15         15

    "Aa" AND "BB" HAVE THE SAME hashCode — this is the famous String collision pair, and it is real:
    'A'*31 + 'a' = 2015 + 97 and 'B'*31 + 'B' = 2046 + 66 both equal 2112. So they must share a
    bucket, and no spread function can separate them, because the collision is in the hashCode itself.

    put("Aa", 1)   bucket 0 empty            → Node("Aa",1)
    put("BB", 2)   bucket 0 occupied         → walk: hash 2112 == 2112, so equals IS called
                                               "Aa".equals("BB") is false
                                             → append: bucket 0 = Node("Aa") → Node("BB")
    get("BB")      bucket 0                  → first node: hash matches, equals false, next
                                             → second node: hash matches, equals TRUE → 2

    NOTE THAT equals WAS CALLED TWICE for that get, and would have been called ZERO times if the
    hashes had differed — the `e.hash == hash` check is what makes a collision cheap when the hashes
    merely happen to mask to the same bucket, and expensive only when the hashes are genuinely equal.

THE SPREAD, MADE VISIBLE. A key type whose hashCode is `id << 16`:

    id    hashCode      binary (high|low)        & 15 WITHOUT spread   with spread
    -----------------------------------------------------------------------------
    1        65536      0000 0001 | 0000 0000            0                  1
    2       131072      0000 0010 | 0000 0000            0                  2
    3       196608      0000 0011 | 0000 0000            0                  3

    WITHOUT THE SPREAD, EVERY KEY GOES TO BUCKET 0 — a perfectly reasonable-looking hashCode reduced
    to a linked list. The XOR pulls the distinguishing bits down where the mask can see them. THAT IS
    THE WHOLE JUSTIFICATION FOR THAT ONE LINE.

THE RESIZE SPLIT, from 16 to 32. The mask goes from 0b01111 to 0b11111 — one new bit, value 16:

    entry     hash    hash & 16      old index    new index
    ------------------------------------------------------------
    A          33            0             1          1          (stays)
    B          17           16             1          17         (i + oldCap)
    C          49           16             1          17         (i + oldCap)
    D           1            0             1          1          (stays)

    ONE BUCKET BECAME TWO, decided by a single bit test, with no key comparisons and no calls to
    hashCode. Every entry that was at index 1 is now at 1 or 17 and nowhere else.

WHICH DESIGN CHOICE PRODUCED WHICH ROW:

    POWER-OF-TWO LENGTH    produced the `& 15` mask, and produced the one-bit resize split.
    THE SPREAD             produced the third table — delete it and those three keys collide forever.
    `e.hash == hash` FIRST produced "equals was called twice, and would have been zero times" —
                           the cheap guard that makes ordinary collisions nearly free.
    THE "Aa"/"BB" PAIR     is the case NO spread can fix, because the collision is in hashCode itself.
                           It is why treeification exists: some collisions cannot be hashed away.""",

"""10. COMPLEXITY, THE MISTAKES, AND THE TAKEAWAY

    get / put / containsKey:  O(1) average, O(log n) worst case since Java 8, O(n) before.
    resize:                   O(n), amortized to O(1) per insertion by doubling.
    iteration:                O(capacity + size) — a large, sparse map is slow to iterate.
    memory:                   ~32-40 bytes per Node plus the table slot. A Map<Integer,Integer> of a
                              million entries is tens of MB against 8MB for two int arrays.

    DEFAULTS: initial capacity 16, load factor 0.75, treeify at 8 entries with a table of at least 64,
    untreeify back to a list at 6.

THE #1 MISTAKE: a mutable key. Insert, mutate, and get(thatVeryKey) returns null while the entry sits
in entrySet() and counts toward size().

THE #2 MISTAKE: equals without hashCode. Different buckets, never compared, entries lost.

THE #3 MISTAKE: depending on iteration order. Deterministic, and it changes on resize — so it passes
with ten keys and fails with thirteen.

THE #4 MISTAKE: sharing a HashMap across threads. Use ConcurrentHashMap; before Java 8 a concurrent
resize could build a circular list and spin a core forever.

THE #5 MISTAKE: not pre-sizing a known-large map, and then pre-sizing it wrong — the argument must be
expectedSize / 0.75, not expectedSize.

THE #6 MISTAKE: HashMap for enum keys. EnumMap is an array indexed by ordinal, with no hashing at all.

THE #7 MISTAKE: a constant or near-constant hashCode. Contract-compliant, and it turns the map into
one tree.

THE #8 MISTAKE: assuming a collision means something is wrong. Collisions are guaranteed by pigeonhole
and the table is built for them; only LONG buckets indicate a problem.

THE #9 MISTAKE: modifying the map inside computeIfAbsent's mapping function. Undefined on HashMap,
forbidden on ConcurrentHashMap.

THE #10 MISTAKE: reaching for a "faster map" before checking the hashCode. A bad hash is essentially
the only way a HashMap becomes slow.

ONE-SENTENCE TAKEAWAY: a HashMap is an array of buckets indexed by `hash & (length-1)` — a mask rather
than a modulo, which is why the length is a power of two, which in turn is why the hash must be SPREAD
with `h ^ (h >>> 16)` before masking or high-bit differences would be discarded entirely — with each
bucket a short list that becomes a red-black tree past eight entries (a denial-of-service fix, not a
performance one) and a resize that splits every bucket in two on a single bit test with no rehashing;
so the failures that matter are all about the KEY: mutate one and the entry becomes unreachable,
override equals without hashCode and it is lost, and depend on iteration order and it breaks the day
the table doubles.""",
]


def apply(entries):
    """Attach the deep dives, and fail loudly on a title that matches nothing.

    A silent no-op here would mean renaming an entry quietly detaches its deep
    dive, and nobody would notice until the card was opened months later.
    """
    by_title = {e["title"]: e for e in entries}
    missing = [t for t in DEEP if t not in by_title]
    if missing:
        raise KeyError("deep dive has no matching entry: " + "; ".join(missing))
    for title, sections in DEEP.items():
        if len(sections) != 10:
            raise ValueError(f"{title!r}: deep dive must be 10 sections, "
                             f"got {len(sections)}")
        by_title[title]["examples"] = list(sections)
    return entries


DEEP["synchronized, volatile, and atomic — three different problems"] = [
"""1. THE GOAL IN PLAIN ENGLISH — two problems that look like one

When two threads touch the same data, two completely different things can go wrong, and almost every
concurrency bug comes from fixing one of them and assuming you fixed both.

    PROBLEM ONE — TAKING TURNS. Two threads run the same few lines at the same time and interleave.
    `count++` is really three steps: read the value, add one, write it back. Two threads can both read
    5, both compute 6, and both write 6. One increment simply vanishes. Nothing is corrupted, nothing
    throws — the number is just quietly wrong.

    PROBLEM TWO — SEEING. A thread writes a value and another thread never notices. Not "notices
    late" — never. The writing thread may keep the value in a CPU register, or the compiler may have
    decided the reading thread's loop can never change and hoisted the read out of it. Both are legal.

    THESE ARE INDEPENDENT. You can fix taking turns and still have an invisible write. You can fix
    seeing and still lose increments.

THE THREE TOOLS MAP ONTO THEM UNEVENLY, which is the source of the confusion:

    volatile     fixes SEEING only.               One variable.
    synchronized fixes BOTH.                      A block, at the cost of blocking.
    Atomic*      fixes BOTH.                      One variable, without blocking.

    SO `volatile int count; count++;` IS BROKEN, and it is broken in the exact way that survives every
    test you will write on your laptop and fails under load in production.

THE EVERYDAY VERSION: two people editing a shared shopping list. Taking turns is making sure you are
not both writing on the same line at once. Seeing is making sure the list you are looking at is the
current one, and not a photocopy you took ten minutes ago.

TERMS AS THEY APPEAR:
- VISIBILITY: whether one thread's write becomes observable to another.
- ATOMICITY: whether an operation happens all at once, with no other thread able to interleave.
- HAPPENS-BEFORE: the ordering guarantee the memory model actually gives you.""",

"""2. THE INTUITION — why "seeing" is even a problem

The natural assumption is that when a thread writes to a field, the value goes into memory and any
other thread reading that field gets it. That assumption is wrong on every modern machine, and it is
wrong for THREE separate reasons stacked on top of each other.

    1. THE COMPILER REORDERS. javac and, far more aggressively, the JIT may reorder any two operations
       whose order is not observable WITHIN A SINGLE THREAD. `a = 1; b = 2;` may become `b = 2; a = 1;`
       because no single-threaded program can tell. Another thread absolutely can.

    2. THE CPU REORDERS. Store buffers, out-of-order execution, speculative loads. A write may sit in
       a core's store buffer for a while before any other core can see it.

    3. THE CACHES ARE PER-CORE. A value read into a register or an L1 cache line may be re-read from
       there indefinitely. The classic symptom is a `while (!stopFlag)` loop that never exits, because
       the JIT hoisted the read out of the loop entirely — which it is entitled to do, since within
       that one thread nothing writes to stopFlag.

    NONE OF THIS IS A BUG. Every one of those transformations makes single-threaded code faster and is
    permitted by the specification. THE JAVA MEMORY MODEL EXISTS TO SAY EXACTLY WHEN YOU ARE ALLOWED
    TO ASSUME OTHERWISE.

AND THE MODEL'S ANSWER IS A SINGLE RELATION: HAPPENS-BEFORE.

    If action A happens-before action B, then everything A did is visible to B. If there is NO
    happens-before edge between two actions in different threads, YOU ARE GUARANTEED NOTHING — not
    "probably fine", not "eventually consistent", nothing.

THE EDGES YOU GET FOR FREE — and this list is short enough to memorise, which is the point:

    PROGRAM ORDER      within one thread, earlier statements happen-before later ones.
    MONITOR            unlocking a monitor happens-before any later lock of that same monitor.
    VOLATILE           a write to a volatile happens-before any later read of it.
    THREAD START       Thread.start() happens-before anything the new thread does.
    THREAD JOIN        everything a thread does happens-before join() returns.
    FINAL FIELDS       a correctly-constructed object's final fields are visible without any
                       synchronisation at all.

    EVERY CORRECT CONCURRENT PROGRAM IS BUILT OUT OF THOSE EDGES. If you cannot point at one, you do
    not have a guarantee.""",

"""3. THE MECHANISM — what each tool actually does

VOLATILE. A read of a volatile is guaranteed to see the most recent write, and reads and writes cannot
be reordered across it. Concretely the JIT emits memory barriers: a write is followed by a store
barrier, a read preceded by a load barrier.

    THE PART PEOPLE MISS: a volatile write also publishes EVERYTHING THE THREAD WROTE BEFORE IT. That
    is why volatile is useful for more than the one variable — writing a volatile flag after filling a
    data structure makes the whole structure visible to any thread that reads the flag.

    WHAT IT DOES NOT DO: make a read-modify-write atomic. `count++` on a volatile is still three
    operations with a gap in the middle.

SYNCHRONIZED. Acquiring a monitor blocks until it is free; releasing it flushes everything the thread
wrote. So it gives mutual exclusion AND the same visibility guarantee as volatile, over a whole block
rather than one variable.

    THE COST is blocking: a thread that cannot acquire the lock parks, and parking and unparking is a
    trip through the OS scheduler. Modern JVMs mitigate with BIASED and THIN locks so an uncontended
    lock is nearly free — the expense is contention, not the keyword.

ATOMIC CLASSES. AtomicInteger and friends are built on COMPARE-AND-SWAP, a single CPU instruction that
says "if this memory location still holds X, replace it with Y, and tell me whether you did".

    incrementAndGet is a LOOP:
        read the current value v
        compute v + 1
        compareAndSet(v, v + 1)
        if it failed, somebody else got there first — go round again

    NO THREAD EVER BLOCKS. A thread that loses the race retries immediately. That is LOCK-FREE: the
    system as a whole always makes progress, even though an individual thread might retry several
    times. Under moderate contention it beats a lock comfortably; under EXTREME contention the retries
    themselves become the bottleneck, which is why LongAdder exists — it spreads the count across
    several cells and sums them only when you ask.

    THE LIMIT: CAS works on ONE variable. An invariant spanning two fields — "a + b must stay
    constant" — cannot be maintained by two atomics, no matter how atomic each one is. That needs a
    lock, or a single immutable object holding both swapped atomically.""",

"""4. EDGE CASES AND FAILURE MODES

CASE 1 — `volatile` ON A COUNTER. The canonical mistake. Visibility without atomicity: ten threads
incrementing a volatile int a thousand times each reliably total LESS than 10,000.

CASE 2 — DOUBLE-CHECKED LOCKING WITHOUT `volatile`. The famous one:

        if (instance == null) { synchronized (lock) { if (instance == null) instance = new Thing(); } }

    Without a volatile field this is BROKEN, and subtly. `instance = new Thing()` is really: allocate,
    run the constructor, assign the reference. The JIT may reorder the last two, so another thread can
    see a NON-NULL reference to a HALF-CONSTRUCTED object, skip the synchronized block entirely, and
    use it. Making the field volatile forbids that reordering and fixes it. USE A STATIC HOLDER CLASS
    INSTEAD and the problem does not arise — class initialisation is already thread-safe.

CASE 3 — `synchronized` ON A METHOD locks `this`. Any unrelated caller who synchronizes on your object
now blocks you, and they may not know they are doing it. USE A PRIVATE FINAL LOCK OBJECT.

CASE 4 — SYNCHRONIZING ON SOMETHING MUTABLE OR SHARED. Locking on a String literal or a boxed Integer
means locking on an interned, JVM-wide object — anyone else with the same literal shares your lock.
Locking on a field you then reassign means two threads lock different objects and neither excludes the
other.

CASE 5 — NON-ATOMIC `long` AND `double`. The spec permits a 64-bit non-volatile write to be split into
two 32-bit halves, so another thread can observe a value that was never written. Rare on 64-bit JVMs
and permitted, so declare shared longs volatile.

CASE 6 — TWO ATOMICS, ONE INVARIANT. Each operation is atomic and the PAIR is not. If a + b must stay
constant, atomics cannot do it.

CASE 7 — CHECK-THEN-ACT ON A CONCURRENT COLLECTION. `if (!map.containsKey(k)) map.put(k, v)` races
even on a ConcurrentHashMap. Each call is atomic; a sequence of calls is not. Use putIfAbsent.

CASE 8 — THE ABA PROBLEM. CAS checks the VALUE, not the history. A value that changed from A to B and
back to A passes compareAndSet as though nothing happened. Usually harmless for counters, fatal for
lock-free stacks — AtomicStampedReference adds a version counter for exactly this.

CASE 9 — SWALLOWING InterruptedException. Catching it CLEARS the interrupt flag, so every caller above
you loses the cancellation signal. Restore it: `Thread.currentThread().interrupt()`.

CASE 10 — TESTING FOR CORRECTNESS. You cannot. A race that never appears in a million runs on your
laptop appears in the first hour on a machine with a different core count. REASON ABOUT THE
HAPPENS-BEFORE EDGES; the test can only ever find a bug, never establish its absence.""",

"""5. THE ALTERNATIVES — and what each costs

DON'T SHARE STATE AT ALL. Immutable objects, thread confinement, message passing, a copy per thread.
NO SYNCHRONISATION IS NEEDED FOR DATA NOBODY ELSE CAN SEE OR CHANGE, and this remains the best answer
by a wide margin. Most concurrency bugs are the punishment for sharing something that did not need to
be shared.

IMMUTABLE OBJECTS. All fields final, no setters, defensive copies of mutable components. The memory
model's FINAL FIELD guarantee means a correctly-constructed immutable object is safe to publish
anywhere with no synchronisation at all. Update by replacing the whole object, via an
AtomicReference if it must be shared.

volatile. One variable, visibility only, and free on reads. RIGHT FOR: a flag written by one thread and
polled by others; a reference published after being fully built. WRONG FOR: anything read-modify-write.

Atomic*. One variable, lock-free, and it scales better than a lock under moderate contention. Under
severe contention use LongAdder for counters — it spreads writes across cells and only sums on read.

synchronized. Both problems, any number of variables, arbitrary blocks. THE DEFAULT WHEN AN INVARIANT
SPANS MORE THAN ONE FIELD. Uncontended it is nearly free; the cost is contention.

ReentrantLock. Everything synchronized does, plus tryLock with a timeout, interruptible acquisition,
fairness, and multiple Conditions. THE COST is that you must unlock in a finally block — the language
does it for you with synchronized and will not here. ALSO: it does NOT pin a virtual thread where
synchronized does, which makes it the preferred choice on Java 21.

CONCURRENT COLLECTIONS. ConcurrentHashMap, BlockingQueue, CopyOnWriteArrayList. Almost always better
than a lock you wrote around a plain collection, because the locking is finer-grained than you would
bother to make it.

HIGHER-LEVEL COORDINATION. CountDownLatch (wait for N events, once), CyclicBarrier (N threads meet
repeatedly), Semaphore (N permits), Phaser. PREFER THESE TO wait/notify, which is error-prone —
notify() wakes an arbitrary waiter and a wait() must always sit in a loop because of spurious wakeups.""",

"""6. HOW TO GET IT RIGHT — numbered steps

STEP 1 — TRY NOT TO SHARE. Confine the data to one thread, or make it immutable. Everything below is
the price of failing this step.

STEP 2 — IF IT IS SHARED AND NEVER CHANGES, MAKE IT `final`. The final-field guarantee means it needs
no synchronisation at all.

STEP 3 — IDENTIFY WHICH PROBLEM YOU HAVE. Only visibility, with a single writer? volatile. A
read-modify-write on one variable? Atomic. An invariant across several fields? A lock.

STEP 4 — NEVER USE `volatile` FOR A COUNTER. `++` is three operations regardless of the modifier.

STEP 5 — LOCK ON A PRIVATE FINAL OBJECT, not on `this` and not on a class you do not own. `private
final Object lock = new Object();`

STEP 6 — HOLD THE LOCK FOR THE WHOLE INVARIANT AND NOT ONE INSTRUCTION LONGER. Never call unknown code
— a listener, a callback, an overridable method — while holding a lock; that is how deadlocks form
between your code and code you have never read.

STEP 7 — IF YOU NEED TWO LOCKS, ORDER THEM GLOBALLY. Same locks, same order, no cycle, no deadlock.

STEP 8 — PREFER THE CONCURRENT COLLECTION TO A LOCK YOU WROTE. It is finer-grained than yours.

STEP 9 — DOCUMENT THE POLICY. "All access to `balance` is guarded by `lock`" as a comment or a
@GuardedBy annotation. A concurrency policy that lives only in one person's head is not a policy.

STEP 10 — REASON, DO NOT TEST. Point at the happens-before edge. A passing test proves nothing about a
race, and the absence of a failure on your machine is not evidence.""",

"""7. THE ANSWER IN PLAIN LANGUAGE — what you would say out loud

'There are two problems here, not one, and most concurrency bugs come from fixing one and assuming you
fixed both.

The first is TAKING TURNS. `count++` is really read, add, write — three steps — so two threads can
both read 5, both compute 6, and both write 6. One increment vanishes silently.

The second is SEEING. A thread writes a value and another thread never observes it. Not late — never.
And there are three independent reasons: the compiler can reorder anything whose order isn't
observable within a single thread; the CPU reorders too, with store buffers and out-of-order
execution; and caches are per-core, so a value read into a register can be re-read from there forever.
The classic symptom is a `while (!stopFlag)` loop that never exits because the JIT hoisted the read
out — which it's entitled to do, since nothing in THAT thread writes to the flag.

None of that is a bug. Every one of those transformations makes single-threaded code faster and is
permitted. The Java Memory Model exists to say exactly when you're allowed to assume otherwise, and
its answer is one relation: HAPPENS-BEFORE. If A happens-before B, everything A did is visible to B.
If there's no edge between two actions in different threads, you're guaranteed NOTHING — not
"probably fine", nothing.

The edges you get for free are a short list worth memorising: program order within a thread; unlocking
a monitor before any later lock of it; a volatile write before any later read of it; Thread.start
before anything the thread does; everything a thread does before join returns; and final fields of a
correctly-constructed object, which are visible with no synchronisation at all.

So the three tools map onto the two problems unevenly. VOLATILE fixes seeing only — one variable, and
a volatile write also publishes everything the thread wrote BEFORE it, which is why it's useful for
more than the one field. SYNCHRONIZED fixes both, over a whole block, at the cost of blocking. And the
ATOMIC classes fix both for a single variable without blocking, using compare-and-swap in a retry
loop — no thread ever parks, so under moderate contention they beat a lock.

The headline mistake is `volatile int count; count++;`. Visibility without atomicity, and it's broken
in exactly the way that survives every test on your laptop and fails under load.

The second one I'd raise is DOUBLE-CHECKED LOCKING without a volatile field. `instance = new Thing()`
is allocate, construct, assign — and the JIT may reorder the last two, so another thread sees a
non-null reference to a HALF-CONSTRUCTED object, skips the synchronized block, and uses it. volatile
forbids the reordering. Though I'd use a static holder class instead, because class initialisation is
already thread-safe and the problem never arises.

And the thing I'd want to land: YOU CANNOT TEST FOR THIS. A race that never appears in a million runs
on your machine appears in the first hour on one with a different core count. You have to point at the
happens-before edge; a test can find a bug but never establish its absence.'""",

"""8. THE CODE, LINE BY LINE

    // ── WRONG. The single most common concurrency mistake in Java. ──────
    static volatile int broken = 0;
    static void incBroken() { broken++; }
    //                        ^^^^^^^^ THREE operations: read broken, add 1,
    //   write broken. `volatile` guarantees each of those three SEES the
    //   latest value and does nothing whatever about the GAPS between them.
    //   Two threads read 5, both write 6, one increment is gone.
    //   VOLATILE IS ABOUT SEEING, NOT ABOUT WINNING.

    // ── RIGHT for a single counter: one indivisible operation. ──────────
    static final AtomicInteger counter = new AtomicInteger();
    static void incAtomic() { counter.incrementAndGet(); }
    //                                ^^^^^^^^^^^^^^^^ internally a CAS LOOP:
    //   read v; compute v+1; compareAndSet(v, v+1); if it failed, retry.
    //   NO THREAD EVER BLOCKS — a loser retries immediately. Lock-free.
    //   Under EXTREME contention the retries themselves cost; that is what
    //   LongAdder is for.

    // ── RIGHT for an invariant spanning several fields. ─────────────────
    private static final Object lock = new Object();
    //      ^^^^^^^ PRIVATE and FINAL. Synchronizing on `this` lets any
    //      unrelated caller who locks your object block you, possibly without
    //      knowing they are doing it. Private means only your code can lock it.
    static int a = 0, b = 0;
    static void moveOne() {
        synchronized (lock) { a--; b++; }
        //                    ^^^^^^^^^ a + b stays constant. TWO ATOMICS
        //   COULD NOT DO THIS — each operation would be atomic and the PAIR
        //   would not, so another thread could observe the moment between them.
    }

    // ── THE CLASSIC volatile: a flag, one writer, many readers. ─────────
    static volatile boolean running = true;
    static void worker() {
        while (running) { /* ... */ }
        //     ^^^^^^^ WITHOUT volatile the JIT may hoist this read out of the
        //     loop entirely — nothing in THIS thread writes to it — and the
        //     loop never terminates. With it, the read is guaranteed fresh.
    }

    // ── DOUBLE-CHECKED LOCKING. The volatile is not optional. ───────────
    private static volatile Thing instance;
    //             ^^^^^^^^ REMOVE THIS AND THE CODE IS BROKEN. `new Thing()`
    //   is allocate, construct, assign — and the last two may be REORDERED, so
    //   another thread can see a non-null reference to a half-built object,
    //   skip the synchronized block, and use it.
    static Thing get() {
        if (instance == null) {                    // cheap, unsynchronised
            synchronized (lock) {
                if (instance == null)              // re-check under the lock
                    instance = new Thing();
            }
        }
        return instance;
    }

    // ── BETTER: the holder idiom. No locks, no volatile, no reasoning. ──
    private static class Holder { static final Thing INSTANCE = new Thing(); }
    static Thing getBetter() { return Holder.INSTANCE; }
    //  ^ Class initialisation is ALREADY thread-safe and lazy — the JVM
    //    guarantees it runs exactly once, on first use. The whole problem
    //    above simply does not arise.""",

"""9. THE TRACE — the increment that vanishes, and the edge that saves it

TWO THREADS, ONE `volatile int count = 0`, one increment each.

    time   thread A                     thread B                     count in memory
    ---------------------------------------------------------------------------------
    t1     read count → 0                                                   0
    t2                                  read count → 0                      0
    t3     compute 0 + 1 = 1                                                0
    t4                                  compute 0 + 1 = 1                   0
    t5     write 1                                                          1
    t6                                  write 1                             1

    TWO INCREMENTS, FINAL VALUE 1. And `volatile` did its job perfectly at every step — both reads saw
    the true current value of 0, and both writes were immediately visible. THE PROBLEM IS THE GAP
    BETWEEN t1 AND t5, which no amount of visibility can close.

THE SAME SEQUENCE WITH AtomicInteger:

    time   thread A                              thread B                       count
    ---------------------------------------------------------------------------------
    t1     read 0, compute 1                                                       0
    t2                                           read 0, compute 1                 0
    t3     compareAndSet(0, 1) → SUCCESS                                           1
    t4                                           compareAndSet(0, 1) → FAILS       1
    t5                                           (it saw 0, memory holds 1)
    t6                                           RETRY: read 1, compute 2          1
    t7                                           compareAndSet(1, 2) → SUCCESS     2

    THE FAILED CAS AT t4 IS THE WHOLE MECHANISM. Thread B's assumption ("count is still 0") was
    checked at the instant of the write and found to be stale, so the write did not happen and B went
    round again. Nobody blocked; B simply did the work twice.

THE VISIBILITY FAILURE, which is a different shape entirely:

    boolean running = true;      // NOT volatile

    thread A                                thread B
    -----------------------------------------------------------------------
    while (running) { ... }                 running = false;
      ^ the JIT observes that nothing in
        THIS thread writes to `running`,
        hoists the read out of the loop,
        and compiles it to `while (true)`
                                            ^ the write happens, and lands in
                                              B's store buffer or B's cache

    THREAD A NEVER STOPS. Not "stops late" — never. And the program is correct on every JVM that
    happens not to make that optimisation, which is why this reliably works in development and hangs
    in production.

    THE FIX IS ONE KEYWORD, and what it buys is precisely a happens-before edge: B's volatile WRITE
    happens-before A's subsequent volatile READ, so the read cannot be hoisted and cannot be stale.

WHICH LINE PRODUCED WHICH ROW:

    `volatile` ON THE COUNTER      produced correct reads at t1 and t2 and did nothing about the gap.
                                   Visibility was never the problem in that table.
    THE THREE-STEP `++`            produced the lost update. Any read-modify-write has this shape,
                                   including `x = x + 1`, `list.size()` then `list.add()`, and
                                   check-then-act on a map.
    `compareAndSet`                produced the FAILURE at t4, which is the only reason the final
                                   value is 2. A CAS that could not fail would be a plain write.
    THE ABSENCE OF `volatile` on the flag
                                   produced the infinite loop — and note the loop is not "slow to
                                   notice", it is compiled to never check again.""",
"""10. COMPLEXITY, THE MISTAKES, AND THE TAKEAWAY

    volatile      read is free (a plain load plus a barrier); write costs a store barrier. VISIBILITY
                  AND ORDERING ONLY — no atomicity, ever.
    synchronized  uncontended is nearly free on a modern JVM (thin locks); CONTENDED costs a park and
                  unpark through the OS scheduler, which is microseconds. Both problems solved.
    Atomic*       lock-free CAS retry loop. Beats a lock under moderate contention, degrades under
                  extreme contention as retries pile up — use LongAdder for hot counters.
    final fields  free. A correctly-constructed object's final fields are visible with NO
                  synchronisation at all, which is why immutability is the cheapest concurrency
                  strategy there is.

    THE MODEL IN ONE SENTENCE: without a happens-before edge between two actions in different threads,
    you are guaranteed nothing.

THE #1 MISTAKE: `volatile` on a counter. Visibility without atomicity — `++` is three operations, and
ten threads incrementing a thousand times each reliably total less than 10,000.

THE #2 MISTAKE: double-checked locking without a volatile field. The construction can be reordered
past the assignment, publishing a half-built object. Use a static holder class instead.

THE #3 MISTAKE: `synchronized` on a method, which locks `this`. Any unrelated caller locking your
object blocks you. Use a private final lock.

THE #4 MISTAKE: locking on a String literal, a boxed Integer, or a field you reassign. The first two
are JVM-wide interned objects; the third means two threads lock different objects and neither excludes
the other.

THE #5 MISTAKE: two atomics guarding one invariant. Each operation is atomic and the PAIR is not.

THE #6 MISTAKE: check-then-act on a concurrent collection. Every individual call is atomic; a sequence
of them is not. That is what putIfAbsent, merge and compute exist for.

THE #7 MISTAKE: assuming a 64-bit `long` write is atomic. The spec permits it to be split in two, so a
shared long should be volatile.

THE #8 MISTAKE: swallowing InterruptedException. Catching it CLEARS the flag, destroying the
cancellation signal for every caller above you. Restore it.

THE #9 MISTAKE: calling unknown code — a listener, a callback, an overridable method — while holding a
lock. That is how a deadlock forms with code you have never read.

THE #10 MISTAKE: believing a passing test. A race that never appears in a million runs on your laptop
appears in the first hour on a machine with a different core count.

ONE-SENTENCE TAKEAWAY: there are TWO problems and three tools that cover them unevenly — `volatile`
fixes SEEING only, `synchronized` fixes seeing and TAKING TURNS at the cost of blocking, and the atomic
classes fix both for a single variable with a lock-free CAS retry loop — so `volatile int count;
count++;` is broken in exactly the way that passes every test on your laptop; and the only real tool
for reasoning about any of it is HAPPENS-BEFORE, because without an edge between two actions in
different threads the specification guarantees you nothing at all.""",
]


DEEP["Generics and type erasure — what actually survives to runtime"] = [
"""1. THE GOAL IN PLAIN ENGLISH — a promise the compiler keeps and then forgets

`List<String>` tells the compiler "this list holds Strings". The compiler checks every add and every
get against that promise, and then — this is the part that surprises people — IT THROWS THE PROMISE
AWAY. The class file contains a plain `List`. At runtime there is no such thing as a List of Strings;
there is a List, and a set of casts the compiler quietly inserted wherever you read from it.

    List<String> names = new ArrayList<>();
    names.add("hi");
    String s = names.get(0);

    ...compiles to roughly:

    List names = new ArrayList();
    names.add("hi");
    String s = (String) names.get(0);
                ^^^^^^^^ YOU DID NOT WRITE THIS CAST. The compiler did, because it knows the promise
                and the runtime does not.

THAT IS ERASURE, and almost every strange rule about Java generics is a direct consequence of it. You
cannot make an array of a type parameter. You cannot ask an object what its generic type is. Two
methods differing only in their generic parameter will not compile. None of those are arbitrary —
they all reduce to "there is nothing there at runtime to check".

THE EVERYDAY VERSION: a customs form declaring the contents of a box. The inspector checks the form
against the contents at the border, stamps it, and then removes the form. Downstream, the box is just
a box — and anyone who tears the form off before the border can put anything they like inside.

TERMS AS THEY APPEAR:
- ERASURE: replacing a type parameter with its bound and inserting casts.
- RAW TYPE: `List` with no parameter — the pre-generics form, still legal for compatibility.
- HEAP POLLUTION: a variable of a parameterised type referring to an object that is not of that type.""",

"""2. THE INTUITION — why Java chose erasure, when C# chose otherwise

Generics arrived in Java 5, nine years after the language. By then there were millions of lines of
`List` and `Map` in production and, more importantly, millions of COMPILED CLASS FILES in jars nobody
was going to rebuild.

    THE CONSTRAINT WAS MIGRATION COMPATIBILITY, and it was absolute:
    * new code using `List<String>` had to work with old libraries expecting `List`;
    * old compiled code had to keep running on the new JVM unchanged;
    * a library could add generics to its signatures WITHOUT breaking its existing callers.

    ERASURE SATISFIES ALL THREE FOR FREE, because after erasure the new code IS the old code. A
    `List<String>` and a raw `List` are byte-for-byte the same type to the JVM, so they interoperate
    perfectly and no bytecode had to change.

    C# MADE THE OPPOSITE CHOICE two years later and REIFIED its generics — the runtime genuinely knows
    a `List<string>` from a `List<int>`. It could, because .NET was young enough that breaking the
    ecosystem was affordable, and because they changed the runtime itself. Java could not change the
    JVM without invalidating every class file in existence.

    SO THE TRADE IS EXPLICIT: C# gets `new T[]`, `typeof(T)`, `List<int>` without boxing, and paid for
    it with a runtime change. Java got a smooth migration and pays for it in every restriction below.

    THAT IS THE ANSWER TO "WHY IS JAVA'S GENERICS SYSTEM LIKE THIS" — not an oversight, a deliberate
    purchase. And Project Valhalla is the long-running attempt to buy back the specialisation without
    breaking anything, which is why it has been in progress for over a decade.

WHAT ERASURE ACTUALLY DOES, precisely:

    <T>                    becomes Object
    <T extends Number>     becomes Number          ← the LEFTMOST BOUND, not Object
    <T extends A & B>      becomes A
    List<String>           becomes List
    T[]                    becomes Object[]

    ...and the compiler inserts a checked cast at every point where a value of type T is read out.""",

"""3. THE MECHANISM — casts, bridge methods, and where the exception lands

THE CASTS ARE THE VISIBLE HALF. Every read of a generic value gets a compiler-inserted cast, which is
why a mistake surfaces AT THE READ rather than at the write:

    List<String> a = new ArrayList<>();
    List raw = a;                 // legal, with an unchecked warning
    raw.add(42);                  // NO CHECK HAPPENS HERE. The list has no idea.
    String s = a.get(0);          // ClassCastException HERE — at a line that looks correct

    THE EXCEPTION LANDS AT A CAST YOU DID NOT WRITE, IN A LINE THAT HAS NOTHING WRONG WITH IT. That
    displacement is the practical cost of erasure and it is why unchecked warnings are worth taking
    seriously — they mark the place where the compiler stopped being able to help.

BRIDGE METHODS ARE THE INVISIBLE HALF, and they are the part that most people have never heard of.

    Consider `class StringBox implements Comparable<StringBox>` with
    `public int compareTo(StringBox other)`.

    After erasure, `Comparable`'s method is `compareTo(Object)`. But StringBox declares
    `compareTo(StringBox)` — a DIFFERENT SIGNATURE, so by the JVM's rules it does not override
    anything, and polymorphism would break: `Comparable c = new StringBox(); c.compareTo(x)` would
    find no implementation.

    SO javac GENERATES A THIRD METHOD you never wrote:

        public int compareTo(Object o) { return compareTo((StringBox) o); }   // synthetic, bridge

    That bridge restores the override relationship and inserts the cast. It is why passing the wrong
    type through a raw reference throws ClassCastException inside a method whose source contains no
    cast at all — the cast is in the bridge.

WHAT SURVIVES ERASURE, which is the detail that makes reflection possible at all:

    The class file keeps a SIGNATURE ATTRIBUTE recording the generic type of FIELDS, of METHOD
    PARAMETERS AND RETURN TYPES, and of CLASS AND INTERFACE DECLARATIONS.

    So reflection CAN tell you that a field is declared `List<String>`, or that a method returns
    `Map<String, List<Integer>>`. What it CANNOT tell you is the type argument of an OBJECT — because
    the object genuinely does not carry one.

    THAT GAP IS EXACTLY WHAT THE SUPER TYPE TOKEN TRICK EXPLOITS. `new TypeReference<List<String>>(){}`
    creates an anonymous SUBCLASS, and a subclass's generic superclass IS recorded in the Signature
    attribute — so the type argument can be recovered by reflection. It is how Jackson and Gson accept
    a generic target type, and it works only because of what the class file kept.""",

"""4. EDGE CASES AND FAILURE MODES

CASE 1 — `new T[10]` IS ILLEGAL. There is no T at runtime, so the array has no element type to check
stores against. The workaround is `(T[]) new Object[10]` plus an unchecked warning — and it can throw
ClassCastException later at a compiler-inserted cast somewhere else entirely. ArrayList does exactly
this internally, and keeps the array `Object[]` privately to contain the damage.

CASE 2 — `instanceof List<String>` IS ILLEGAL. Nothing to test. Only `instanceof List<?>` compiles.

CASE 3 — TWO METHODS WITH THE SAME ERASURE CLASH. `f(List<String>)` and `f(List<Integer>)` both erase
to `f(List)` and the error says so literally: "have the same erasure". Note `f(List<String>)` and
`f(Set<String>)` are fine — their erasures differ.

CASE 4 — A STATIC MEMBER CANNOT USE THE CLASS'S TYPE PARAMETER. There is ONE static field for all
parameterisations, so `static T instance;` has no coherent meaning.

CASE 5 — YOU CANNOT CATCH A GENERIC EXCEPTION. `catch (T e)` is illegal, because catch matching is a
runtime type test.

CASE 6 — HEAP POLLUTION VIA VARARGS. `static <T> void f(T... args)` creates a `T[]`, which erases to
`Object[]`, which can be assigned anything. That is why javac warns and why @SafeVarargs exists — the
annotation is YOU ASSERTING the method never stores into the array.

CASE 7 — OVERLOADING ON A BOUND. `<T extends Number>` erases to Number, so a method taking it clashes
with one taking Number.

CASE 8 — A GENERIC ARRAY CREATION EXPRESSION. `new List<String>[10]` is illegal for the same reason as
case 1, and the workaround has the same caveat.

CASE 9 — RAW TYPES DISABLE GENERICS ENTIRELY, not just for the raw variable. Using a raw `List`
suppresses type checking on OTHER generic methods of the same class, which is a deliberately blunt
rule from the migration era and a good reason never to use raw types in new code.

CASE 10 — `List<Object>` IS NOT A SUPERTYPE OF `List<String>`. Generics are INVARIANT, and this is the
restriction people resent most — it exists because arrays made the other choice and pay for it with a
runtime check on every store.""",

"""5. THE ALTERNATIVES — living with erasure

WILDCARDS, which recover most of the flexibility invariance takes away.

    `List<? extends Number>` — a PRODUCER. You may READ Numbers from it; you may not add, because the
    actual list might be a List<Double>.
    `List<? super Integer>` — a CONSUMER. You may ADD Integers; you may only read Objects, because the
    actual list might be a List<Object>.
    PECS: Producer Extends, Consumer Super. It is the single most useful mnemonic in Java generics and
    Collections.copy(dest, src) is the canonical signature carrying both.

CLASS TOKENS, when you genuinely need the type at runtime.

    `<T> T read(Class<T> type, String json)` — pass the Class object explicitly, and use
    `type.cast(x)` for a checked cast. It is what erasure forces and it is honest about it.

SUPER TYPE TOKENS, for generic targets a Class cannot express.

    `new TypeReference<List<String>>(){}` — an anonymous subclass, whose generic superclass IS in the
    Signature attribute and IS readable by reflection. Jackson's TypeReference and Guava's TypeToken.

MAKE THE ARRAY AN ArrayList. Most `new T[]` problems evaporate: an ArrayList has none of the
restrictions and is what you wanted anyway.

REIFIED GENERICS, for comparison and not as an option. C#, and Kotlin's `inline fun <reified T>` which
achieves it by INLINING the function at each call site so the compiler can substitute the concrete
type. Java's Project Valhalla is the long-running effort to get specialisation without breaking the
existing model.

WHAT TO SAY IN AN INTERVIEW: "Generics are compile-time only — erased to their bound with casts
inserted. If I need the type at runtime I pass a Class token, or a TypeReference for a parameterised
target. And I'd never use a raw type in new code, because it disables type checking more broadly than
people expect."

""",

"""6. HOW TO WORK WITH IT — numbered steps

STEP 1 — TREAT UNCHECKED WARNINGS AS ERRORS. Each one marks a place the compiler stopped being able to
help, and where a ClassCastException may later surface somewhere unrelated.

STEP 2 — NEVER USE A RAW TYPE IN NEW CODE. It disables generic checking beyond the one variable, and
it is only legal at all for the sake of 2004.

STEP 3 — PREFER A List TO AN ARRAY when a type parameter is involved. It sidesteps the array
restrictions entirely.

STEP 4 — USE WILDCARDS ON PARAMETERS, PECS. A method that only reads takes `? extends T`; one that only
writes takes `? super T`. It widens what callers can pass at no cost to you.

STEP 5 — PASS A `Class<T>` TOKEN when you genuinely need the runtime type — for a cast, a reflective
instantiation or a deserialisation target.

STEP 6 — USE A SUPER TYPE TOKEN for a parameterised target, and know WHY it works: a subclass's generic
superclass survives in the Signature attribute where an object's own type argument does not.

STEP 7 — CONFINE ANY UNCHECKED CAST TO ONE PRIVATE PLACE, annotate it @SuppressWarnings("unchecked")
narrowly, and comment why it is safe. A suppression on a whole class hides the next one.

STEP 8 — USE @SafeVarargs ONLY WHEN IT IS TRUE — the method must never store into the varargs array nor
let it escape.

STEP 9 — REMEMBER STATIC MEMBERS CANNOT USE THE CLASS'S PARAMETER. Make the METHOD generic instead:
`static <T> Box<T> empty()`.

STEP 10 — WHEN AN OVERLOAD WILL NOT COMPILE, CHECK THE ERASURES. "Have the same erasure" means the two
signatures are identical after type parameters are stripped, and the fix is different names.""",

"""7. THE ANSWER IN PLAIN LANGUAGE — what you would say out loud

'Generics in Java are a COMPILE-TIME feature. The compiler checks every use against the declared type
and then erases it — the class file just contains `List`, and the compiler has inserted casts wherever
you read from it. So at runtime there's no such thing as a List of Strings; a List<String> and a
List<Integer> are the same class, and `getClass()` on both returns ArrayList.

The reason is MIGRATION COMPATIBILITY, and it was an absolute constraint rather than an oversight.
Generics arrived nine years into Java's life, when there were millions of compiled class files nobody
was going to rebuild. Erasure means new generic code IS old raw code after compilation, so they
interoperate perfectly and no bytecode had to change. C# made the opposite call two years later and
reified its generics — it could, because .NET was young enough to break its ecosystem and because they
changed the runtime. Java couldn't change the JVM without invalidating every jar in existence.

So the trade was bought deliberately: C# gets `new T[]`, `typeof(T)` and `List<int>` without boxing;
Java got a smooth migration and pays for it in every restriction. That's the honest answer to "why is
Java's generics system like this".

What erasure does precisely: an unbounded T becomes Object, a bounded `T extends Number` becomes
NUMBER — the leftmost bound, not Object — and casts go in at every read.

The consequence people hit first is that the exception lands in the wrong place. If you smuggle a
wrong value in through a raw reference, the add succeeds silently — the list has no idea what it's
supposed to hold — and the ClassCastException fires later at `String s = list.get(0)`, a line that
looks completely correct. The cast that fails is one you never wrote.

The half most people haven't heard of is BRIDGE METHODS. If you implement `Comparable<StringBox>`, you
write `compareTo(StringBox)` — but after erasure the interface's method is `compareTo(Object)`, a
different signature, so by the JVM's rules yours doesn't override anything and polymorphism would
break. So javac generates a synthetic bridge, `compareTo(Object)`, that casts and delegates. That's
why the ClassCastException can appear inside a method whose source contains no cast — it's in the
bridge.

And the thing worth knowing about what SURVIVES: the class file keeps a Signature attribute recording
the generic types of fields, method signatures and class declarations. So reflection CAN tell you a
field is declared List<String>. What it can't tell you is an OBJECT's type argument, because the
object genuinely doesn't carry one. That gap is exactly what the super-type-token trick exploits —
`new TypeReference<List<String>>(){}` creates an anonymous SUBCLASS, and a subclass's generic
superclass IS in the Signature attribute. It's how Jackson accepts a generic target type.

Practically: never use raw types in new code, treat unchecked warnings as errors, use wildcards on
parameters — PECS, producer extends, consumer super — and pass a Class token when you genuinely need
the type at runtime.'""",

"""8. THE CODE, LINE BY LINE

    List<String> a = new ArrayList<>();
    List<Integer> b = new ArrayList<>();
    System.out.println(a.getClass() == b.getClass());     // true
    //                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^ THE SAME CLASS OBJECT. There is
    //   one ArrayList class and it has no idea what it was declared to hold.
    //   This single line is erasure in its entirety.

    // ── SMUGGLING A WRONG VALUE IN, AND WHERE IT SURFACES ───────────────
    List raw = a;
    //   ^^^ A RAW TYPE. Legal, with an unchecked warning — and legal only because
    //   pre-2004 code had to keep compiling. Never write this deliberately.
    raw.add(42);
    //  ^^^^^^^ NO CHECK OCCURS. The ArrayList has no element type at runtime, so
    //  there is nothing to check against. The list now genuinely holds an Integer
    //  in a variable the compiler believes holds Strings — HEAP POLLUTION.
    // String s = a.get(0);
    //            ^^^^^^^^^ ClassCastException HERE, at a compiler-inserted
    //  (String) cast, on a line containing no visible cast and no visible fault.
    //  THE DISPLACEMENT BETWEEN THE BUG AND THE CRASH IS THE COST OF ERASURE.

    // ── A BOUNDED PARAMETER ERASES TO THE BOUND, NOT TO OBJECT ──────────
    static <T extends Number> double sum(List<T> xs) {
        //   ^^^^^^^^^^^^^^^ erases to Number. Which is exactly why the next line
        //   compiles — the erased parameter type has doubleValue(). An unbounded
        //   <T> would erase to Object and this would not compile.
        double t = 0;
        for (T x : xs) t += x.doubleValue();
        return t;
    }

    // ── THE BRIDGE METHOD YOU NEVER WROTE ───────────────────────────────
    class StringBox implements Comparable<StringBox> {
        public int compareTo(StringBox other) { return 0; }
        //         ^^^^^^^^^^^^^^^^^^^^^^^^^ after erasure the INTERFACE declares
        //   compareTo(Object), so this signature overrides NOTHING and
        //   polymorphism through a Comparable reference would break.
        //
        //   So javac synthesises this, which is in the class file and not in
        //   your source:
        //
        //       public int compareTo(Object o) {
        //           return compareTo((StringBox) o);      // <- THE CAST LIVES HERE
        //       }
        //
        //   Pass the wrong type through a raw Comparable and the
        //   ClassCastException is thrown inside a method you did not write.
    }

    // ── WHAT SURVIVES, AND THE TRICK THAT EXPLOITS IT ───────────────────
    class Holder { List<String> names; }
    // reflection CAN read this:
    //   Holder.class.getDeclaredField("names").getGenericType()
    //     -> java.util.List<java.lang.String>
    // ...because the class file's SIGNATURE ATTRIBUTE records a FIELD's generic
    // type. It cannot do the same for an OBJECT, which carries nothing.
    //
    // Hence the super type token — an anonymous SUBCLASS, whose generic
    // superclass IS recorded:
    //   new TypeReference<List<String>>() {}
    //   ((ParameterizedType) getClass().getGenericSuperclass())
    //       .getActualTypeArguments()[0]     -> List<String>""",

"""9. THE TRACE — the same program, before and after the compiler

SOURCE:

    class Box<T extends Number> {
        private T value;
        void set(T v)      { this.value = v; }
        T get()            { return value; }
        double doubled()   { return value.doubleValue() * 2; }
    }

    Box<Integer> b = new Box<>();
    b.set(21);
    int x = b.get();

AFTER ERASURE — what the class file effectively contains:

    class Box {
        private Number value;              // T ERASED TO ITS BOUND, not to Object
        void set(Number v)   { this.value = v; }
        Number get()         { return value; }
        double doubled()     { return value.doubleValue() * 2; }
        //                            ^^^^^^^^^^^^^^^ compiles because the erased
        //   field type is Number. With an UNBOUNDED <T> the field would be Object
        //   and this line would not compile — which is what a bound is FOR.
    }

    Box b = new Box();
    b.set(Integer.valueOf(21));            // autoboxing, then a widening reference
    int x = ((Integer) b.get()).intValue();
    //       ^^^^^^^^^ THE COMPILER PUT THIS HERE. Every read of a generic value
    //       carries one, and it is where a violated promise turns into an exception.

THE FAILURE, step by step:

    step                                    what the compiler knows   what the JVM knows
    -------------------------------------------------------------------------------------
    List<String> a = new ArrayList<>();     a holds Strings           a holds Objects
    List raw = a;                           unchecked — warning       identical reference
    raw.add(42);                            nothing (raw type)        add an Object. FINE.
    ...
    String s = a.get(0);                    inserts (String)          CAST FAILS → CCE

    THE TWO COLUMNS DIVERGE AT ROW 2 AND THE PROGRAM CRASHES AT ROW 4. Everything between is correct
    by both sets of rules, which is precisely why the stack trace points somewhere useless.

WHAT ERASURE DOES TO EACH FORM:

    declared                    erased to        why it matters
    ---------------------------------------------------------------------------------
    <T>                         Object           you lose every method but Object's
    <T extends Number>          Number           you keep Number's methods — USE BOUNDS
    <T extends A & B>           A                the LEFTMOST bound wins
    List<String>                List             same class as List<Integer>
    T[]                         Object[]         which is why new T[] is illegal
    void f(List<String>)        void f(List)     which is why the overload clashes

WHICH RULE PRODUCED WHICH ROW:

    "REPLACE T WITH ITS BOUND"        produced `private Number value`, and therefore produced the fact
                                      that `doubled()` compiles at all. An unbounded T would erase to
                                      Object and the method would be rejected.
    "INSERT A CAST AT EVERY READ"     produced `((Integer) b.get())`, and produced the crash site in
                                      the failure table — at a line the programmer did not write.
    "ERASE THE PARAMETER FROM THE
     SIGNATURE"                       produced `void f(List)`, and therefore the "have the same
                                      erasure" compile error for two overloads that look distinct.
    "KEEP THE SIGNATURE ATTRIBUTE"    is why the FIELD's declared type is still recoverable by
                                      reflection even though the OBJECT's is not — the one thing
                                      erasure did not take.""",

"""10. COMPLEXITY, THE MISTAKES, AND THE TAKEAWAY

    ERASURE COSTS NOTHING AT RUNTIME — generics are entirely a compile-time construct, so a generic
    method is exactly as fast as the raw equivalent. The costs are all in EXPRESSIVENESS.
    THE ONE PERFORMANCE COST IS INDIRECT: no reified primitives, so a List<Integer> boxes every value.
    An int[] of a million entries is 4MB; a List<Integer> of distinct values is roughly 20MB. That
    ratio is why IntStream and int[] exist alongside Stream<Integer>.

    WHAT ERASURE REMOVES: `new T[]`, `instanceof List<String>`, `catch (T e)`, `static T field`,
    overloads differing only by type argument, and an object's knowledge of its own type argument.
    WHAT IT KEEPS: the Signature attribute — the generic types of FIELDS, METHOD SIGNATURES and CLASS
    DECLARATIONS — which is what makes reflection and super type tokens possible at all.

THE #1 MISTAKE: ignoring an unchecked warning. Each one marks the point where the compiler stopped
being able to help, and where a ClassCastException may later appear somewhere unrelated.

THE #2 MISTAKE: using a raw type in new code. It disables generic checking more broadly than the one
variable, and it exists only for 2004's sake.

THE #3 MISTAKE: expecting the exception where the bug is. A wrong value goes in silently and the crash
happens at a compiler-inserted cast on a later, innocent-looking line.

THE #4 MISTAKE: `new T[10]`. Use a List, or `(T[]) new Object[10]` confined to one private field.

THE #5 MISTAKE: overloading on the type argument. Both erase to the same signature and the compiler
says so literally.

THE #6 MISTAKE: an unbounded `<T>` where a bound was wanted. `<T extends Number>` erases to Number and
keeps its methods; `<T>` erases to Object and keeps nothing.

THE #7 MISTAKE: a static field of type T. There is one static field across all parameterisations, so
it has no coherent meaning. Make the method generic instead.

THE #8 MISTAKE: @SafeVarargs on a method that stores into the array or lets it escape. The annotation
is an assertion, and an untrue one is worse than the warning.

THE #9 MISTAKE: a blanket @SuppressWarnings("unchecked") on a class or method. It hides the NEXT
unchecked operation, which nobody reviewed. Put it on the narrowest declaration possible.

THE #10 MISTAKE: believing invariance is arbitrary. Arrays made the other choice and pay for it with a
type check on every single store, plus a runtime ArrayStoreException. The restriction IS the fix.

ONE-SENTENCE TAKEAWAY: generics are checked at compile time and then ERASED — a type parameter becomes
its leftmost bound and casts are inserted at every read — so List<String> and List<Integer> are the
same class at runtime, which is why you cannot write `new T[]` or `instanceof List<String>` or two
overloads differing only by type argument; the choice was bought deliberately for MIGRATION
COMPATIBILITY when generics arrived nine years late and millions of class files could not be rebuilt;
and the practical consequences are that a violated promise surfaces as a ClassCastException at a cast
you never wrote, sometimes inside a synthetic BRIDGE METHOD, while the Signature attribute keeps just
enough for reflection to read a FIELD's generic type even though an OBJECT can never report its own.""",
]


DEEP["Streams — laziness, one-shot use, and when a loop is better"] = [
"""1. THE GOAL IN PLAIN ENGLISH — describing the work, then doing it once

A stream is not a collection. It holds no data. It is a DESCRIPTION of a pipeline — filter these, map
those, collect the rest — and writing that description does nothing at all. The work only starts when
you ask for a result at the end, and then all the steps happen together, one element at a time.

    THE TWO CONSEQUENCES THAT SURPRISE PEOPLE:

    A PIPELINE WITH NO ENDING DOES NOTHING. `list.stream().map(x -> save(x))` looks like it saves
    everything and saves nothing. There is no terminal operation, so the description was built and
    thrown away. The compiler does not warn.

    THE ELEMENTS DO NOT GO THROUGH STAGE BY STAGE. It is not "filter everything, then map everything".
    Each element is pulled through the WHOLE pipeline before the next one starts. Which is why a
    stream over an infinite source plus `limit(5)` terminates, and why `findFirst` on a million
    elements can touch exactly one.

THE EVERYDAY VERSION: a recipe versus cooking. Writing "chop the onions, fry them, add stock" produces
no dinner. And when you do cook, you do not chop every vegetable in the kitchen before frying anything
— you take one thing through the steps that apply to it.

    A STREAM IS ALSO SINGLE-USE. Once consumed it is spent, like a queue rather than a list. Operating
    on it again throws IllegalStateException, which is the API refusing to pretend it can rewind.

TERMS AS THEY APPEAR:
- INTERMEDIATE operation: returns another stream. Lazy. filter, map, sorted, distinct, limit, peek.
- TERMINAL operation: produces a result or a side effect, and TRIGGERS EVERYTHING. collect, forEach,
  reduce, count, anyMatch, findFirst.
- SHORT-CIRCUITING: a terminal that may finish without consuming the whole source.""",

"""2. THE INTUITION — the pull model, and what laziness buys

The natural mental model is that each stage runs to completion and hands a collection to the next.
That would be a PUSH model, it would allocate an intermediate collection per stage, and it could never
handle an infinite source.

    STREAMS ARE A PULL MODEL INSTEAD. The terminal operation asks for one element; the request travels
    UP the pipeline to the source; the element comes back down through every stage in turn; and only
    then is the next one requested.

    THAT SINGLE DESIGN DECISION BUYS FOUR THINGS AT ONCE:

    NO INTERMEDIATE COLLECTIONS. A filter-map-collect over a million elements allocates one result,
    not three million-element lists. This is called STAGE FUSION, and it is why a long pipeline is not
    proportionally slower than a short one.

    SHORT-CIRCUITING BECOMES POSSIBLE. `findFirst` stops asking after the first match; `anyMatch`
    after the first true; `limit(5)` after five. On a million-element source that can be a million-fold
    saving, and it is impossible in a push model because the earlier stages have already run.

    INFINITE SOURCES BECOME USABLE. `Stream.iterate(1, n -> n * 2).limit(10)` is fine, because nothing
    is produced until something asks.

    AND THE ORDER OF OPERATIONS STARTS TO MATTER. `filter(...).map(expensive)` maps only what survives
    the filter; `map(expensive).filter(...)` maps everything. Identical results, and one may be ten
    times the work — which is a real optimisation you can perform by reading, without measuring.

THE ONE PLACE LAZINESS BREAKS DOWN — and it is the detail worth knowing:

    STATEFUL INTERMEDIATE OPERATIONS. `sorted()` cannot emit its first element until it has seen the
    LAST one, so it is a full barrier: everything upstream runs to completion, is buffered, and only
    then does anything downstream begin. `distinct()` must remember everything seen so far.

    WHICH MEANS `sorted().limit(3)` STILL SORTS EVERYTHING. The limit cannot short-circuit through the
    sort. If you want the three smallest of a million elements, a bounded priority queue is O(n log 3)
    and the sort is O(n log n) — the stream reads better and does far more work.""",

"""3. THE MECHANISM — Spliterator, fusion, and what parallel actually does

UNDERNEATH EVERY STREAM IS A SPLITERATOR, which is an iterator that can also split itself:

    tryAdvance(action)   process one element. The pull.
    trySplit()           hand back a Spliterator covering roughly half, keeping the rest. The parallel.
    estimateSize()       how many are left, for deciding whether splitting is worth it.
    characteristics()    SIZED, ORDERED, DISTINCT, SORTED, IMMUTABLE, NONNULL, CONCURRENT.

    THE CHARACTERISTICS ARE NOT DECORATION — the pipeline reads them and skips work. A stream already
    marked DISTINCT skips `distinct()` entirely. A SIZED stream can pre-allocate the result array. A
    stream that is not ORDERED may let `findFirst` behave like `findAny`.

    AND trySplit IS WHY SOME SOURCES PARALLELISE AND OTHERS DO NOT. An ArrayList or an array splits in
    O(1) into two exact halves, because it knows its size and can index. A LinkedList must WALK to
    find its middle, and a stream from a BufferedReader or an Iterator cannot split meaningfully at
    all — it hands back null and the "parallel" stream runs on one thread with extra overhead.

STAGE FUSION. The intermediate operations are composed into a single chain of Consumers before
anything runs, so `filter(p).map(f).forEach(c)` becomes roughly one nested call per element rather than
three passes over three collections.

PARALLEL STREAMS. `.parallel()` splits the source recursively via trySplit, processes the pieces on the
COMMON ForkJoinPool, and combines the results.

    THREE THINGS ARE WORTH KNOWING AND ARE ROUTINELY MISSED:

    THE POOL IS SHARED BY THE ENTIRE JVM. ForkJoinPool.commonPool() is sized to availableProcessors()
    MINUS ONE, and every parallel stream, every CompletableFuture that omitted an executor, and every
    library doing the same all use it. A blocking operation inside a parallel stream stalls unrelated
    code elsewhere in the process.

    THE COMBINE STEP IS REAL WORK. Splitting is cheap; merging results is not always. Collecting into
    a HashMap in parallel merges maps, which can cost more than the parallelism saved.

    ORDER SURVIVES BUT COSTS. `forEachOrdered` preserves encounter order and serialises the tail of the
    pipeline; `forEach` does not and is faster. `findFirst` must respect order, `findAny` need not —
    which is precisely why both exist.""",

"""4. EDGE CASES AND FAILURE MODES

CASE 1 — NO TERMINAL OPERATION. The pipeline is built and discarded. Nothing runs, nothing warns, and
the symptom is "my forEach isn't executing" from someone who wrote `.map(x -> sideEffect(x))` and
never terminated the chain.

CASE 2 — REUSING A CONSUMED STREAM. IllegalStateException: "stream has already been operated upon or
closed". Assign the SOURCE to a variable, not the stream.

CASE 3 — `sorted().limit(n)` EXPECTING A SHORT-CIRCUIT. Sorting is a full barrier; limit cannot reach
through it. For the top-n of a large source use a bounded priority queue.

CASE 4 — MODIFYING THE SOURCE DURING THE STREAM. Explicitly undefined behaviour, and it usually
manifests as ConcurrentModificationException from the terminal operation — a stack trace pointing at
`collect` rather than at the mutation.

CASE 5 — `Collectors.toMap` ON DUPLICATE KEYS. Throws IllegalStateException rather than overwriting.
Supply a merge function: `toMap(k, v, (a, b) -> b)`. AND toMap THROWS ON A NULL VALUE, where a HashMap
would accept one — a real difference when replacing a loop with a stream.

CASE 6 — `peek()` FOR ANYTHING BUT DEBUGGING. The Javadoc says debugging only, and implementations may
SKIP it when the result is not needed — a `count()` on a SIZED stream may not traverse at all, so the
peek never fires.

CASE 7 — SIDE EFFECTS IN A LAMBDA. `stream.forEach(x -> list.add(x))` is not thread-safe in parallel
and defeats the point in serial. Use a collector.

CASE 8 — PARALLEL ON A SOURCE THAT WILL NOT SPLIT. A LinkedList, an Iterator, a BufferedReader: you
pay the coordination cost and get one thread's throughput.

CASE 9 — PARALLEL WITH A SMALL N. The fork/join overhead dominates below roughly ten thousand elements
of real work, and often far above that.

CASE 10 — `Stream.toList()` vs `collect(Collectors.toList())`. Java 16's `toList()` returns an
UNMODIFIABLE list; the collector traditionally returns an ArrayList. Swapping one for the other turns
a later `.add()` into an UnsupportedOperationException, and it is a genuine migration hazard.

CASE 11 — BOXING. `list.stream().map(x -> x.getCount()).reduce(0, Integer::sum)` boxes every value.
`mapToInt(...).sum()` does not, and the difference is large on a hot path.""",

"""5. THE ALTERNATIVES — and when a loop is simply better

A PLAIN for LOOP. Faster on primitives, debuggable with a breakpoint on any line, and it can `break`,
`continue`, and `return` from the middle. A STREAM CANNOT RETURN FROM THE ENCLOSING METHOD, cannot
carry a checked exception out of a lambda, and produces stack traces full of internal frames.

    USE A LOOP WHEN: the body is imperative, you need early return, you are working on primitives in a
    hot path, or the pipeline would need more than about three stages to express.

AN ENHANCED for OVER A COLLECTION. The same, with less index arithmetic.

`Collection.removeIf(predicate)`. One pass, no iterator management, and on an ArrayList it COMPACTS in
a single pass rather than shifting per removal — so it beats both a stream and a manual loop.

PRIMITIVE STREAMS — IntStream, LongStream, DoubleStream. All the readability with no boxing.
`mapToInt`, `sum`, `average`, `summaryStatistics`. USE THESE WHENEVER THE VALUES ARE PRIMITIVES; the
difference against `Stream<Integer>` is not marginal.

COLLECTORS, which are the part of the API worth learning properly. A Collector is four functions:

    supplier      make a new empty container
    accumulator   fold one element into a container
    combiner      merge two containers  ← ONLY used in parallel, and the usual source of bugs
    finisher      convert the container to the final result

    groupingBy, partitioningBy, joining, counting, summingInt, mapping, teeing (Java 12), and
    groupingBy with a DOWNSTREAM collector, which is where the real expressiveness lives:
    `groupingBy(Person::dept, counting())`.

PARALLEL STREAMS. Worth it only when ALL of: the source splits well, N is large, the per-element work
is CPU-bound and substantial, there is no shared mutable state, and you have measured it. THAT IS FIVE
CONDITIONS, and failing any one usually makes it slower.

WHAT TO SAY: "Streams for readability on collection transformations, primitive streams whenever the
values are primitives, a loop when the body is imperative or needs early exit, and parallel only after
measuring."

""",

"""6. HOW TO USE THEM WELL — numbered steps

STEP 1 — END EVERY PIPELINE WITH A TERMINAL OPERATION. If nothing happened, this is why.

STEP 2 — PUT `filter` BEFORE `map`. Mapping only what survives is free to arrange and can be an
order-of-magnitude difference.

STEP 3 — USE PRIMITIVE STREAMS FOR PRIMITIVES. `mapToInt(...).sum()` rather than
`map(...).reduce(0, Integer::sum)`.

STEP 4 — DO NOT PUT SIDE EFFECTS IN LAMBDAS. Collect a result instead; a stream that mutates external
state is a loop wearing a costume.

STEP 5 — REMEMBER `sorted()` AND `distinct()` ARE BARRIERS. Nothing downstream starts until everything
upstream finishes, so `sorted().limit(3)` sorts the whole source.

STEP 6 — SUPPLY A MERGE FUNCTION TO `toMap`. It throws on duplicate keys, and it throws on null
values, where the equivalent loop with a HashMap would not.

STEP 7 — LEARN `groupingBy` WITH A DOWNSTREAM COLLECTOR. It is where most of the expressiveness is,
and it replaces the most tedious loops you write.

STEP 8 — TREAT `peek` AS DEBUG-ONLY. It may legitimately never run.

STEP 9 — BEFORE `parallel()`, CHECK ALL FIVE CONDITIONS: splittable source, large N, CPU-bound work,
no shared state, and a measurement. And remember the common pool is shared with the whole JVM.

STEP 10 — WHEN A PIPELINE PASSES ABOUT THREE STAGES OR NEEDS A COMMENT TO EXPLAIN IT, WRITE THE LOOP.
Readability was the reason to use a stream; past a point it stops being the readable option.""",

"""7. THE ANSWER IN PLAIN LANGUAGE — what you would say out loud

'A stream isn't a collection — it holds no data. It's a DESCRIPTION of a pipeline, and building that
description does nothing. The work only starts when you write a terminal operation at the end.

Which means a pipeline with no terminal operation does NOTHING AT ALL, silently. That usually shows up
as "my forEach isn't running" from someone who wrote map with a side effect and never ended the chain,
and the compiler won't warn you.

The second surprise is that elements don't go through stage by stage. It's not "filter everything then
map everything" — each element is pulled through the WHOLE pipeline before the next one starts. It's a
PULL model: the terminal asks for an element, the request travels up to the source, and the element
comes back down through every stage.

That one decision buys four things. No intermediate collections — a filter-map-collect over a million
elements allocates one result, not three million-element lists. Short-circuiting becomes possible, so
findFirst can touch exactly one element out of a million. Infinite sources become usable, because
nothing is produced until something asks. And the ORDER of your operations starts to matter:
filter-then-map maps only what survives, map-then-filter maps everything. Same result, potentially ten
times the work, and you can fix it by reading rather than measuring.

The place laziness breaks down is STATEFUL operations. `sorted()` can't emit its first element until
it's seen the LAST one, so it's a full barrier — everything upstream runs to completion and is
buffered. Which means `sorted().limit(3)` still sorts everything. If you want the three smallest of a
million, a bounded priority queue is O(n log 3) and the sort is O(n log n) — the stream reads better
and does far more work.

Underneath it all is a SPLITERATOR — an iterator that can also split itself in half. That's what makes
parallel possible, and it's also why some sources parallelise and others don't: an ArrayList or array
splits in constant time into exact halves, while a LinkedList has to walk to find its middle and an
Iterator or a BufferedReader can't split at all. Those hand back null and your "parallel" stream runs
on one thread with extra overhead.

On parallel generally — I'd want five conditions before reaching for it: the source splits well, N is
large, the work is CPU-bound and substantial, there's no shared mutable state, and I've measured it.
And the pool is ForkJoinPool.commonPool, sized to cores minus one and shared by the WHOLE JVM, so
anything blocking inside a parallel stream stalls unrelated code.

Two practical things. Use primitive streams whenever the values are primitives — mapToInt then sum,
rather than map then reduce with Integer::sum, which boxes every value. And Collectors.toMap throws on
duplicate keys AND on null values, where the equivalent loop with a HashMap would happily accept both
— which catches people converting a loop to a stream.

And I'd say plainly: streams are for READABILITY, not speed. On a simple loop over primitives they're
slower. When a pipeline passes about three stages or needs a comment, the loop was the readable
option.'""",

"""8. THE CODE, LINE BY LINE

    // ── NOTHING HAPPENS HERE. No terminal operation. ────────────────────
    Stream.of("a", "b", "c").filter(s -> {
        System.out.println("filtering " + s);
        return true;
    });
    // ^ The pipeline is CONSTRUCTED and discarded. The println never runs, the
    //   compiler does not warn, and the symptom is "my code isn't executing".

    // ── ONE ELEMENT AT A TIME, THROUGH THE WHOLE CHAIN ──────────────────
    List<String> out = Stream.of("a", "b", "c")
        .peek(s  -> System.out.println("filter " + s))
        .map (s  -> { System.out.println("  map " + s); return s.toUpperCase(); })
        .collect(Collectors.toList());
    //   ^^^^^^^ THE TERMINAL. Everything above ran because of this line.
    //
    //   The output INTERLEAVES — filter a, map a, filter b, map b — because the
    //   stages are FUSED into one chain of Consumers and each element is pulled
    //   all the way through before the next is requested. A push model would
    //   print all three filters and then all three maps.

    // ── SHORT-CIRCUITING: one element out of three is touched ───────────
    Stream.of("x", "y", "z")
        .peek(s -> System.out.println("touched " + s))
        .findFirst();
    // ^ prints "touched x" and stops. On a million-element source this is a
    //   million-fold saving, and it is IMPOSSIBLE in a push model because the
    //   earlier stage would already have run to completion.

    // ── ORDER MATTERS, AND IT IS FREE TO FIX ────────────────────────────
    people.stream().filter(p -> p.age() > 60).map(Person::expensiveReport)
    // ^ maps only the survivors.
    people.stream().map(Person::expensiveReport).filter(r -> r.age() > 60)
    // ^ maps EVERYONE. Same result. Potentially ten times the work.

    // ── THE BARRIER. limit cannot reach through sorted. ─────────────────
    million.stream().sorted().limit(3).toList();
    //                ^^^^^^^^ CANNOT emit anything until it has seen the LAST
    //   element, so the entire source is buffered and sorted — O(n log n) —
    //   and only then does limit take three. A bounded PriorityQueue is
    //   O(n log 3). The stream reads better and does far more work.

    // ── PRIMITIVE STREAMS: the boxing difference ────────────────────────
    int total = items.stream().mapToInt(Item::count).sum();
    //                         ^^^^^^^^^ IntStream — no Integer objects at all.
    // int total = items.stream().map(Item::count).reduce(0, Integer::sum);
    //                            ^^^ boxes EVERY value. Same answer, and on a
    //   hot path the difference is not marginal.

    // ── toMap's TWO SURPRISES ───────────────────────────────────────────
    // .collect(Collectors.toMap(Person::name, Person::age))
    //   ^ throws IllegalStateException on a DUPLICATE KEY (a HashMap would
    //     overwrite) AND NullPointerException on a null VALUE (a HashMap would
    //     accept it). Both bite when converting a loop to a stream.
    .collect(Collectors.toMap(Person::name, Person::age, (a, b) -> b));
    //                                                   ^^^^^^^^^^ the merge
    //   function. Supply it unless you genuinely want the exception.""",

"""9. THE TRACE — pull, fuse, short-circuit

THE PIPELINE:

    Stream.of("a", "b", "c")
          .peek(s -> print("filter " + s))
          .map (s -> { print("  map " + s); return s.toUpperCase(); })
          .collect(toList());

WHAT A PUSH MODEL WOULD PRINT — stage by stage, and this is what people expect:

    filter a
    filter b
    filter c
      map a
      map b
      map c

WHAT ACTUALLY PRINTS — element by element, because the stages are FUSED:

    filter a
      map a
    filter b
      map b
    filter c
      map c

    THE DIFFERENCE IS NOT COSMETIC. In the push model, stage one has fully materialised a collection
    before stage two begins — so an intermediate list exists, an infinite source hangs, and
    short-circuiting is impossible because the work is already done.

THE SHORT-CIRCUIT, traced:

    step   what the terminal asks           what the source does        printed
    ---------------------------------------------------------------------------------
    1      findFirst: "give me one"         emits "x"                   touched x
    2      an element arrived → DONE        never asked again           —

    TWO ELEMENTS NEVER TOUCHED. The pull direction is what makes this possible: the terminal controls
    how many requests are made, so it can simply stop asking.

THE BARRIER, traced — `sorted().limit(3)` over a million elements:

    stage         behaviour                                   elements processed
    -------------------------------------------------------------------------------
    source        emits                                       1,000,000
    sorted        BUFFERS EVERYTHING, cannot emit until the    1,000,000 buffered
                  last element has arrived                     + O(n log n) compares
    limit(3)      takes 3 and stops asking                     3
    toList        collects                                     3

    LIMIT SHORT-CIRCUITS AND IT SHORT-CIRCUITS TOO LATE. It stops the stage ABOVE it from being asked
    for a fourth element — and that stage is `sorted`, which has already done all the work. The
    laziness is real and it cannot reach past a stateful operation.

PARALLEL SPLITTING, and why the source decides:

    source            trySplit()                        result
    -------------------------------------------------------------------------------
    ArrayList         O(1), exact halves, SIZED         splits cleanly, scales
    int[]             O(1), exact halves, SIZED         the best case
    HashMap.keySet    splits by table range             reasonable
    LinkedList        must WALK to find the middle      splits poorly
    BufferedReader    returns null                      NO SPLIT — one thread,
                                                        plus fork/join overhead

WHICH DESIGN DECISION PRODUCED WHICH ROW:

    THE PULL MODEL             produced the interleaved output, the short-circuit, and the ability to
                               consume an infinite source. All three are the same fact.
    STAGE FUSION               produced "one result allocated, not three collections" — the reason a
                               five-stage pipeline is not five passes.
    STATEFULNESS OF `sorted`   produced the barrier table. It is a property of the OPERATION, not of
                               streams — `distinct` and `limit`-after-`sorted` behave the same way.
    Spliterator.trySplit       produced the parallel table. Parallelism is a property of the SOURCE
                               first and of your code second.""",

"""10. COMPLEXITY, THE MISTAKES, AND THE TAKEAWAY

    A stream adds allocation and a virtual call per element per stage. For a simple loop over
    primitives it is typically SLOWER than a for loop; for multi-stage transformations over objects
    the difference is usually noise. USE THEM FOR CLARITY.
    Stage fusion means an n-stage pipeline is ONE pass, not n passes.
    Short-circuiting terminals can turn O(n) into O(1) on the lucky element.
    `sorted()` is O(n log n) and a FULL BARRIER; `distinct()` is O(n) time and O(n) space.
    Primitive streams remove boxing entirely — the largest single win available in stream code.
    Parallel needs a splittable source, large N, CPU-bound work, no shared state, and a measurement.

THE #1 MISTAKE: no terminal operation. The pipeline is built and discarded, silently, with no warning.

THE #2 MISTAKE: expecting stage-by-stage execution. Elements go through the whole chain one at a time,
which is why short-circuiting and infinite sources work at all.

THE #3 MISTAKE: `sorted().limit(n)` for a top-n. The sort is a barrier and limit cannot reach through
it. Use a bounded priority queue.

THE #4 MISTAKE: `map` before `filter`. Free to fix by reading, and potentially an order of magnitude.

THE #5 MISTAKE: `Stream<Integer>` where `IntStream` belongs. Every value boxed.

THE #6 MISTAKE: `Collectors.toMap` without a merge function. It throws on duplicate keys and on null
values, unlike the HashMap loop it replaced.

THE #7 MISTAKE: side effects in lambdas. Not thread-safe in parallel, and pointless in serial.

THE #8 MISTAKE: `peek` for anything real. Debug-only by specification, and it may never run.

THE #9 MISTAKE: `parallel()` as a performance button. Five conditions must hold, the pool is shared
with the entire JVM, and a blocking call inside one stalls unrelated code.

THE #10 MISTAKE: reusing a consumed stream. Keep a reference to the SOURCE, not to the stream.

THE #11 MISTAKE: assuming `Stream.toList()` and `collect(toList())` are interchangeable. The first is
UNMODIFIABLE since Java 16, and a later `.add()` throws.

ONE-SENTENCE TAKEAWAY: a stream is a lazily-evaluated DESCRIPTION of a pipeline that does nothing until
a terminal operation pulls elements through the whole fused chain ONE AT A TIME — which is what makes
short-circuiting, infinite sources and single-pass execution possible, and what makes `filter` before
`map` a free optimisation — with the laziness breaking down at stateful operations like `sorted()`,
which buffers everything and means `sorted().limit(3)` still sorts a million elements; use primitive
streams for primitives, reach for a loop when the body is imperative or needs an early exit, and treat
`parallel()` as five conditions to verify rather than a button to press.""",
]


DEEP["The JIT — why your first benchmark is always wrong"] = [
"""1. THE GOAL IN PLAIN ENGLISH — code that gets faster while it runs

Java starts by INTERPRETING your program — reading each instruction and doing what it says, one at a
time, which is slow. While it does that it also WATCHES: which methods run often, which branches are
taken, which actual types show up at each call. Once a method looks hot, a compiler translates it to
machine code, using everything that was observed to make choices it could never make ahead of time.

    SO THE SAME METHOD RUNS AT SEVERAL DIFFERENT SPEEDS DURING ONE PROGRAM. The first few hundred calls
    are interpreted. Later calls run compiled but conservatively. Later still they run through an
    aggressive compiler that has a behavioural profile to work from. Speedups of ten to a hundred times
    between the first call and the steady state are ordinary, not exotic.

    WHICH IS WHY YOUR FIRST BENCHMARK IS ALWAYS WRONG. If you time a method the first time it runs,
    you have measured the interpreter. If you time it in a loop with no warm-up, you have measured a
    blend of interpreter, half-optimised and optimised code, weighted by whichever phase happened to
    take longest. Neither number describes the code that will run in production.

THE EVERYDAY VERSION: a new employee reading the manual for every task, while a supervisor takes notes.
After a week the supervisor writes a one-page cheat sheet based on what this person ACTUALLY does —
"you always get the blue form, so here it is pre-filled" — and the job gets much faster. Time them on
day one and you have measured the manual, not the job.

TERMS AS THEY APPEAR:
- JIT: just-in-time compiler. Compiles at RUN time, from observed behaviour.
- AOT: ahead-of-time. Compiles before the program runs, from source alone.
- PROFILE: the counters and type records collected while interpreting.
- SPECULATION: compiling on an assumption the profile supports but cannot prove.
- DEOPTIMISATION: throwing away compiled code when a speculation turns out to be false.
- WARM-UP: running code enough times to reach its steady state before you measure it.""",

"""2. THE INTUITION — why running late beats running early

An ahead-of-time compiler must produce code that is CORRECT FOR EVERY POSSIBLE EXECUTION. It sees a
call through an interface and must emit a dynamic dispatch, because any implementation might arrive.
It sees a branch and must compile both sides. It sees a field read and must actually read it.

    A JIT KNOWS WHAT ACTUALLY HAPPENED. Not what could happen — what did. And in real programs the gap
    between those is enormous:

    THE CALL THAT LOOKS POLYMORPHIC IS USUALLY MONOMORPHIC. A `List` variable in a real application is
    an ArrayList at 99% of call sites, every single time. The JIT observes one type, INLINES that
    implementation directly, and leaves a cheap class check in front of it. AOT cannot do this
    honestly, because the code must survive the case it never sees.

    HALF THE BRANCHES ARE NEVER TAKEN. Null checks that never fire, error paths, feature flags that
    are off. The JIT compiles the taken path densely and replaces the untaken side with a TRAP — an
    instruction that means "if control ever arrives here, abandon this compiled code and fall back to
    the interpreter". Zero cost while the assumption holds.

    INLINING IS THE ENABLER, NOT AN OPTIMISATION. On its own, inlining just removes a call. But once
    the callee's body sits inside the caller, every other optimisation can see across the old boundary:
    constants fold through it, redundant null checks collapse, and the escape analyser can finally
    prove that an object never leaves. MOST OF WHAT THE JIT WINS IS DOWNSTREAM OF INLINING — which is
    why a method too large to inline is a performance cliff, not a gentle slope.

THE PRICE, and it is the honest half of the story:

    COMPILATION COSTS TIME AND IT COSTS IT AT RUN TIME. A JVM spends its first seconds slow, competing
    with your application for CPU while it compiles. Startup is worse than a native binary and always
    will be. A short-lived process — a CLI tool, a lambda invocation — may EXIT before it ever reaches
    the fast code it paid for.

    AND EVERY SPECULATION IS A DEBT. Load a second implementation of that interface and the inlined
    call is invalidated, the compiled method is discarded, execution falls back to the interpreter, and
    the whole thing recompiles more conservatively. Normally invisible. Occasionally the cause of a
    latency spike nobody can explain.""",

"""3. THE MECHANISM — tiers, inlining, escape analysis, and deoptimisation

TIERED COMPILATION, which is the default and explains the shape of every warm-up curve:

    TIER 0   the INTERPRETER. Slow, but it collects the profile.
    TIER 1   C1, no profiling. For trivial methods that will never benefit from more.
    TIER 2   C1, limited profiling. A short-lived stage used when the C2 queue is backed up.
    TIER 3   C1, FULL profiling. Fast-ish code that still counts branches and records types.
             This is where most hot code lives on its way up, and it is deliberately slower than
             tier 1 because it is carrying instrumentation.
    TIER 4   C2. The aggressive optimiser. No profiling — it CONSUMES the profile instead.

    THE USUAL PATH IS 0 → 3 → 4. Roughly a couple of hundred invocations to leave the interpreter and
    on the order of ten thousand to reach C2, though the thresholds are adaptive and depend on how
    busy the compiler queues are. Two runs of the same program can compile at different points.

ON-STACK REPLACEMENT (OSR). A method called ONCE that contains a million-iteration loop would never
reach the invocation threshold. So loop back-edges are counted too, and when the count trips, the JVM
compiles the method and SWAPS THE RUNNING FRAME for the compiled version mid-loop. This is why `main`
with one big loop still gets fast, and why OSR code is often slightly worse than normally-compiled code
— it had to be entered at an awkward point.

INLINING, with the two thresholds that decide it:
    a small method (roughly ≤ 35 bytes of bytecode) is inlined almost anywhere;
    a HOT method gets a much larger budget (roughly ≤ 325 bytes);
    a huge method is never inlined, and everything downstream of that decision is lost.
    -XX:+UnlockDiagnosticVMOptions -XX:+PrintInlining tells you which, and why not.

INLINE CACHES — how a virtual call gets inlined at all:
    MONOMORPHIC   one type ever seen → inline it behind a single class-pointer compare. Nearly free.
    BIMORPHIC     two types → inline both behind a two-way check. Still good.
    MEGAMORPHIC   three or more → give up, fall back to a vtable/itable lookup, INLINING IS LOST,
                  and with it every optimisation that depended on it.
    THAT CLIFF IS THE REASON A CALL SITE'S HISTORY MATTERS. The same code is fast in a service that
    only ever passes one implementation and slow in one that passes four.

ESCAPE ANALYSIS. If the JIT can prove an object never leaves the compiled region, it can SCALAR
REPLACE it — the object is never allocated at all, its fields become registers. This is why "avoid
allocation" advice is often obsolete: the allocation may not exist. Inlining is what makes the proof
possible, which is the dependency again.

DEOPTIMISATION. Every speculation is guarded. When a guard fails — a second implementation is loaded,
a never-taken branch is taken, a null finally arrives — the compiled method is marked NOT ENTRANT, the
running frame is rebuilt as an interpreter frame, and execution continues correctly, slowly, until a
new compilation arrives. Correctness is never at risk. Predictable timing is.""",

"""4. EDGE CASES AND FAILURE MODES

CASE 1 — DEAD CODE ELIMINATION EATS THE BENCHMARK. If the result is never used, C2 can prove the whole
computation is unobservable and delete it. The loop becomes nothing. The classic tell is a number that
is PHYSICALLY IMPOSSIBLE — a fraction of a nanosecond per operation, faster than one memory access.

CASE 2 — CONSTANT FOLDING. If the inputs are `static final` or otherwise compile-time constants, the
answer is computed once at compile time and the "loop" returns a literal. You measured a return.

CASE 3 — LOOP HOISTING. A computation that does not depend on the loop variable is moved OUT of the
loop and done once, so a million iterations become one.

CASE 4 — NO WARM-UP AT ALL. The whole measurement is interpreter time. Typically ten to a hundred
times slower than the truth, which is why microbenchmarks so often "prove" the wrong option wins.

CASE 5 — MEASURING DURING THE CLIMB. A loop that runs long enough to trip compilation MID-MEASUREMENT
gives you a weighted average of three different implementations, and the weights depend on the machine.

CASE 6 — PROFILE POLLUTION, the subtlest of all. Running two implementations of the same interface in
ONE JVM makes the shared call site BIMORPHIC or MEGAMORPHIC, so both are measured worse than either
would be alone — and the one measured second may inherit the first one's profile. This is precisely
why JMH forks a fresh JVM per benchmark by default.

CASE 7 — A DEOPTIMISATION STORM. Code compiled on an assumption that keeps breaking recompiles
repeatedly. Symptom: throughput that oscillates rather than settling.

CASE 8 — CLASS LOADING INVALIDATES INLINING LATE. A method inlined because it had exactly one
implementation is discarded the moment a second is loaded — potentially hours in, when a plugin, a
lazily-initialised path, or a proxy first appears.

CASE 9 — SHORT-LIVED PROCESSES NEVER GET THERE. CLI tools, serverless invocations, tests. They pay the
compilation cost and exit before collecting.

CASE 10 — THE CODE CACHE FILLS UP. Compiled code lives in a fixed-size region. When it fills, the JVM
prints a warning and STOPS COMPILING ENTIRELY — the application quietly reverts toward interpreted
speed and stays there.

CASE 11 — TIMING WITH `System.currentTimeMillis()`. It is wall-clock, subject to NTP adjustment, and
its granularity can be milliseconds. Use `System.nanoTime()`, which is monotonic — and even then only
for durations, never as a timestamp.

CASE 12 — ONE MEASUREMENT. GC, the OS scheduler, another tenant on the box, CPU frequency scaling.
A single number carries no information about its own variance.""",

"""5. THE ALTERNATIVES — and what to reach for instead of a hand-rolled timer

JMH (Java Microbenchmark Harness), written by the people who wrote the JIT, and the only honest answer
for anything at method scale. What it does that your loop does not:

    RETURNING THE VALUE, or handing it to a Blackhole, so dead code elimination cannot fire.
    @State OBJECTS the compiler cannot fold to constants.
    @Fork — a FRESH JVM per benchmark, which is the fix for profile pollution.
    @Warmup ITERATIONS run and DISCARDED, so you measure the steady state.
    Many measurement iterations, reported with a confidence interval rather than one number.
    It also warns you when your benchmark looks suspicious.

ASYNC-PROFILER or JFR for anything at APPLICATION scale. A microbenchmark answers "which of these two
methods is faster"; a profiler answers "does this method matter at all", which is almost always the
question you actually had. MOST MICROBENCHMARKS OPTIMISE SOMETHING THAT IS 0.3% OF THE PROFILE.

-XX:+PrintCompilation — a live log of what is being compiled, at which tier, and what is being thrown
away. `%` marks OSR, `s` synchronized, `!` an exception handler, and `made not entrant` is a
deoptimisation. Reading this once teaches more about warm-up than any article.

-XX:+UnlockDiagnosticVMOptions -XX:+PrintInlining — why a method was or was not inlined. "too big",
"hot method too big", "callee is too large". This is the flag for the "why is this slow when the
identical smaller version is fast" question.

-Xint (interpreter only) and -XX:-TieredCompilation (C2 only) — as EXPERIMENTS, to see how much of a
result is compilation.

GraalVM NATIVE IMAGE — AOT compilation to a native binary. Millisecond startup, low memory, no warm-up
— and a LOWER PEAK than a warmed JIT, because it never sees the profile. It also requires a closed
world: reflection and dynamic loading must be declared. THE TRADE IS EXPLICIT: it is the right choice
for short-lived processes and the wrong one for a long-running server.

CLASS DATA SHARING and the JVM's profile-replay options reduce startup without giving up peak.

WHAT TO SAY: "For method-scale questions, JMH — nothing hand-rolled is trustworthy. For real
performance questions, a profiler first, because the method I was about to micro-optimise is usually
not in the top twenty."

""",

"""6. HOW TO BENCHMARK WITHOUT LYING TO YOURSELF — numbered steps

STEP 1 — ASK WHETHER IT MATTERS. Profile the application first. A microbenchmark of a method that is
0.3% of the profile is a correct answer to a question nobody asked.

STEP 2 — USE JMH. Not a loop with nanoTime. Every failure mode in section 4 is one it already handles.

STEP 3 — CONSUME THE RESULT. Return it from the benchmark method or pass it to a Blackhole, or dead
code elimination will delete the thing you are measuring.

STEP 4 — KEEP THE INPUTS OUT OF REACH OF CONSTANT FOLDING. Put them in an @State object; never in a
`static final`.

STEP 5 — WARM UP AND DISCARD. Several seconds of iterations, thrown away, before anything counts.

STEP 6 — FORK A FRESH JVM PER BENCHMARK. This is the profile-pollution fix, and it is the one that
looks unnecessary until it silently reverses a result.

STEP 7 — REPORT VARIANCE, NOT A NUMBER. If the intervals overlap, you have not shown a difference.

STEP 8 — WHEN THE RESULT LOOKS TOO GOOD, DISBELIEVE IT. Under about a nanosecond per operation, assume
the loop was eliminated until you have proved otherwise.

STEP 9 — READ -XX:+PrintCompilation ONCE ON YOUR ACTUAL WORKLOAD. Watch the tiers climb and watch
`made not entrant` scroll past. It makes warm-up concrete in a way no description does.

STEP 10 — IF SOMETHING IS INEXPLICABLY SLOW, CHECK INLINING. -XX:+PrintInlining, and look for "too
big" and for a call site that has gone megamorphic.

STEP 11 — FOR SERVICES, WARM UP IN PRODUCTION TOO. Send synthetic traffic before taking a new instance
into the load balancer, or the first real users pay for your compilation.

STEP 12 — MEASURE ON THE HARDWARE THAT WILL RUN IT. Core count, cache sizes and frequency scaling all
move these numbers.""",

"""7. THE ANSWER IN PLAIN LANGUAGE — what you would say out loud

'Java starts by INTERPRETING — reading each instruction and doing what it says. While it does that it's
also watching: which methods run often, which branches get taken, which actual types show up at each
call. Once a method looks hot, it gets compiled to machine code using everything that was observed.

So the same method runs at several different speeds during one program. First few hundred calls,
interpreted. Then compiled but conservatively, with instrumentation still attached. Then compiled
aggressively by C2 with a real behavioural profile. Ten to a hundred times between the first call and
the steady state is ordinary.

Which is why the first benchmark is always wrong. Time it once and you measured the interpreter. Time
it in a loop with no warm-up and you measured a blend of three different implementations, weighted by
whichever phase happened to take longest on that machine. Neither number describes production.

The reason a JIT can beat ahead-of-time compilation at all is that it knows what ACTUALLY happened, not
what could. A List variable is an ArrayList at basically every call site, every time — so the JIT
inlines that implementation directly behind a cheap class check. An AOT compiler can't do that
honestly, because its code has to survive the case it never sees.

And inlining is the ENABLER, not the optimisation. On its own it just removes a call. But once the
callee's body is inside the caller, everything else can see across the old boundary — constants fold
through, null checks collapse, and escape analysis can finally prove an object never leaves, so it's
never allocated at all. Most of what the JIT wins is downstream of inlining, which is why a method too
big to inline is a cliff rather than a slope.

The cost is that every speculation is a debt. If a second implementation of that interface gets loaded,
the inlined call is invalidated — the compiled code is marked not entrant, the running frame is rebuilt
as an interpreter frame, and it recompiles more conservatively. Correctness is never at risk. Predictable
timing is. And that can happen hours in, when some plugin or lazy path first loads a class.

The failure mode I'd watch for most in a hand-rolled benchmark is DEAD CODE ELIMINATION. If nothing
uses the result, C2 proves the computation is unobservable and deletes it. The tell is a number that's
physically impossible — a fraction of a nanosecond per operation, faster than a single memory access.
The subtler one is PROFILE POLLUTION: measuring two implementations of the same interface in one JVM
makes the shared call site megamorphic, so both look worse than either would alone. That's exactly why
JMH forks a fresh JVM per benchmark by default.

So: JMH for anything at method scale, nothing hand-rolled. Consume the result, keep the inputs in a
@State object so they can't fold to constants, warm up and discard, fork per benchmark, and report a
confidence interval rather than a number. And honestly — profile the application first, because the
method I was about to micro-optimise is usually not in the top twenty.'""",

"""8. THE CODE, LINE BY LINE — a benchmark that measures nothing

    // ── THE VERSION EVERYONE WRITES FIRST ───────────────────────────────
    long start = System.currentTimeMillis();
    //           ^^^^^^^^^^^^^^^^^^^^^^^^ WALL CLOCK. Subject to NTP stepping,
    //           and its granularity can be milliseconds. nanoTime is monotonic.
    for (int i = 0; i < 1_000_000; i++) {
        expensiveCalculation(i);
    //  ^ THE RESULT IS DISCARDED. C2 can prove the call has no observable
    //    effect and delete the entire loop. Not "optimise" — DELETE.
    }
    System.out.println(System.currentTimeMillis() - start + " ms");
    // ^ Prints 0. Which is not a fast result; it is the absence of a result.
    //   And even if the loop survived, the first ~10,000 iterations were
    //   INTERPRETED, so the average is mostly warm-up.

    // ── THE THREE WAYS THE COMPILER CAN CHEAT ───────────────────────────
    static final int N = 1000;              // ← CONSTANT FOLDING: the compiler
    int r = 0;                              //   knows N, so the whole sum can be
    for (int i = 0; i < N; i++) r += i;     //   computed at compile time and
    // the loop becomes `r = 499500;`       //   replaced with a literal.

    for (int i = 0; i < n; i++) sum += list.size() * factor;
    //                                ^^^^^^^^^^^^^^^^^^^^ LOOP HOISTING: nothing
    //   here depends on i, so it is computed ONCE and the loop just adds.

    for (int i = 0; i < n; i++) hash(data);
    //                          ^^^^^^^^^^ DEAD CODE ELIMINATION: unused result,
    //   no side effect, no loop.

    // ── THE HONEST VERSION ──────────────────────────────────────────────
    @State(Scope.Benchmark)                 // ← inputs live in an object the
    public static class Input {             //   compiler cannot fold to constants
        int[] data = randomArray(10_000);
    }

    @Benchmark
    @Fork(value = 3)                        // ← THREE FRESH JVMs. This is the
    //                                          profile-pollution fix: measuring
    //                                          two impls in ONE JVM makes the
    //                                          shared call site megamorphic and
    //                                          slows BOTH.
    @Warmup(iterations = 5, time = 1)       // ← run and DISCARD. You are waiting
    //                                          for tier 4, not measuring tier 0.
    @Measurement(iterations = 10, time = 1)
    public int sum(Input in) {
        int s = 0;
        for (int v : in.data) s += v;
        return s;
    //  ^^^^^^^^ RETURNING IT is what stops dead code elimination. JMH consumes
    //  the return value; for multiple results, Blackhole.consume(x).
    }

    // ── THE FLAGS THAT SHOW YOU WHAT HAPPENED ───────────────────────────
    // -XX:+PrintCompilation
    //     3    java.lang.String::hashCode (55 bytes)      ← tier 3, C1+profiling
    //     4 %  Main::sum @ 12 (43 bytes)                  ← % means OSR
    //     3    Main::sum   made not entrant               ← A DEOPTIMISATION.
    // -XX:+UnlockDiagnosticVMOptions -XX:+PrintInlining
    //     @ 7  Main::helper (312 bytes)  hot method too big  ← the cliff, named.""",

"""9. THE TRACE — one method, four speeds

THE SAME METHOD, timed at four points in one JVM's life. Numbers are ILLUSTRATIVE SHAPES, not measured
constants — the ratios are what matters, and they are the ratios people actually observe:

    invocation      what is executing                              relative time
    ---------------------------------------------------------------------------------
    1               tier 0, INTERPRETER. Every bytecode dispatched  ~100x
                    through a switch. The profile starts filling.
    ~500            tier 3, C1 WITH FULL PROFILING. Real machine    ~8x
                    code, but carrying counters — deliberately
                    slower than tier 1, because it is paying to
                    learn.
    ~12,000         tier 4, C2. Profile consumed. The hot path      ~1x
                    inlined, the untaken branches replaced by
                    traps, the escaping-nowhere object never
                    allocated at all.
    later           a second implementation is loaded → the guard   ~100x briefly,
                    fails → MADE NOT ENTRANT → back to the           then ~1.4x
                    interpreter → recompile, this time with a
                    bimorphic call and no scalar replacement.

    THE LAST ROW IS THE ONE THAT SURPRISES PEOPLE. Nothing was wrong, nothing was misconfigured, and no
    code changed. A class was loaded, an assumption became false, and the JVM did the only correct
    thing — which cost a latency spike and a permanently slightly-slower steady state.

WHY EACH DROP HAPPENED — mapping the row to the mechanism:

    100x → 8x       LEAVING THE INTERPRETER. Bytecode dispatch removed. This is the largest single
                    step and it is why an unwarmed measurement is not off by a bit, it is off by
                    two orders of magnitude.
    8x → 1x         INLINING, and everything downstream of it: constant folding across the old call
                    boundary, dead branch removal via uncommon traps, and scalar replacement removing
                    the allocation entirely.
    1x → 1.4x       THE CALL SITE WENT BIMORPHIC. Inlining survived but with a two-way guard, and
                    escape analysis could no longer prove the object was confined.

NOW THE NAIVE BENCHMARK, traced against that table:

    what you wrote                          what you measured
    ---------------------------------------------------------------------------------
    time one call                           the interpreter. ~100x too slow.
    loop 1,000 times, no warm-up            mostly interpreter, some tier 3. ~30x too slow.
    loop 1,000,000, no warm-up              a weighted average that DEPENDS ON THE MACHINE,
                                            because the thresholds are adaptive.
    result unused                           0 ms. The loop does not exist.
    inputs are `static final`               0 ms. The answer is a literal in the class file.
    two impls, one JVM, no fork             both slower than either alone, and possibly REVERSED
                                            in ranking. This is the one that survives review.

    THE SHAPE OF THE WHOLE THING: every single row above is a case of the measurement disturbing what
    it measures. The JIT optimises for what it observes, and a benchmark is a strange, unrepresentative
    thing to observe. JMH's entire design is a list of defences against exactly this table.""",

"""10. COMPLEXITY, THE MISTAKES, AND THE TAKEAWAY

    Interpreted → C2 steady state is commonly 10–100x. This is the number that makes unwarmed
    measurements worthless rather than merely imprecise.
    Roughly a couple of hundred invocations to leave the interpreter; on the order of ten thousand to
    reach C2 — ADAPTIVE, so two runs of the same program compile at different points.
    Inlining budget: about 35 bytes of bytecode cold, about 325 hot. Past that, a cliff.
    Inline caches: 1 type is nearly free, 2 is fine, 3+ loses inlining and everything downstream.
    Deoptimisation is correct, cheap in aggregate, and occasionally the unexplained latency spike.
    Compilation competes with your application for CPU during startup — this is real, and it is why a
    native image starts in milliseconds and a JVM does not.

THE #1 MISTAKE: no warm-up. You measured the interpreter, and it is not close.

THE #2 MISTAKE: discarding the result. Dead code elimination deletes the loop; the tell is a time that
is physically impossible.

THE #3 MISTAKE: `static final` inputs. Constant-folded to a literal at compile time.

THE #4 MISTAKE: measuring two implementations in one JVM. Profile pollution can slow both and REVERSE
the ranking. Fork per benchmark.

THE #5 MISTAKE: `System.currentTimeMillis()`. Wall clock, NTP-adjustable, coarse. Use `nanoTime`, and
only for durations.

THE #6 MISTAKE: one measurement, no variance. Overlapping intervals are not a result.

THE #7 MISTAKE: microbenchmarking before profiling. The method usually is not in the top twenty.

THE #8 MISTAKE: believing a suspiciously good number. Under a nanosecond per operation, assume the work
was eliminated.

THE #9 MISTAKE: expecting a short-lived process to reach peak. CLI tools and serverless invocations pay
for compilation and exit before collecting; that is a native-image case, not a tuning case.

THE #10 MISTAKE: forgetting the code cache can fill. When it does, the JVM stops compiling and quietly
drifts back toward interpreted speed — with a warning nobody reads.

THE #11 MISTAKE: assuming allocation costs what it used to. Escape analysis may have removed the object
entirely — but only if the enclosing method was inlined, which is why the advice is conditional.

ONE-SENTENCE TAKEAWAY: the JVM interprets first while PROFILING, then compiles hot code using what it
actually observed — inlining monomorphic calls, replacing never-taken branches with traps, and removing
allocations it can prove never escape — so the same method runs 10–100x apart between its first call
and its steady state, every one of those optimisations is a SPECULATION that can be deoptimised when a
class loads or a branch finally fires, and consequently any benchmark without warm-up, without
consuming its result, without non-constant inputs, and without a forked JVM is measuring the harness
rather than the code.""",
]


DEEP["Garbage collection — the generational hypothesis, and which collector to pick"] = [
"""1. THE GOAL IN PLAIN ENGLISH — why nobody frees memory in Java

In C you ask for memory and you give it back. Forget to give it back and the program grows until it
dies; give it back twice, or use it after giving it back, and the program corrupts itself in a way that
shows up somewhere else entirely, hours later. Those two bug classes have caused an enormous share of
the security vulnerabilities of the last forty years.

    JAVA REMOVES THE QUESTION. You never free anything. Periodically the JVM works out which objects
    are still REACHABLE — meaning there is some chain of references from a running thread, a static
    field, or a local variable to that object — and everything else is, by definition, garbage that no
    code could ever look at again.

    THE KEY WORD IS REACHABLE, NOT USED. The collector cannot tell whether you are FINISHED with an
    object. It can only tell whether you can still GET to it. Which is why Java still has memory leaks:
    a cache, a static list or a listener registry that holds a reference forever keeps the object alive
    forever, and the collector is doing exactly its job while your heap fills.

THE EVERYDAY VERSION: a library that never asks you to return books, but every night walks the building
and removes any book that nobody has a note pointing to. If you leave a note in a drawer you forgot
about, the book stays. That is a Java memory leak, and no amount of tuning fixes it.

    THE SECOND SURPRISE IS THAT COLLECTION IS CHEAP IN PROPORTION TO WHAT SURVIVES, NOT TO WHAT DIED.
    A young-generation collection copies the survivors elsewhere and then declares the entire region
    empty in one step. Ten thousand dead objects cost NOTHING. This inverts the usual instinct:
    creating short-lived garbage is close to free, and it is long-lived objects that are expensive.

TERMS AS THEY APPEAR:
- HEAP: where objects live. STACK: where local variables and frames live, per thread.
- ROOT: a starting point for reachability — a thread's stack, a static field, a JNI reference.
- STOP THE WORLD (STW): a pause where application threads are frozen so the collector can work.
- MINOR / YOUNG GC: collects the young generation only. Frequent, short.
- FULL GC: collects everything, usually with a long pause. Something has gone wrong if these are
  frequent.""",

"""2. THE INTUITION — the weak generational hypothesis, and what it buys

One observation drives almost every collector ever shipped:

    THE WEAK GENERATIONAL HYPOTHESIS: MOST OBJECTS DIE YOUNG.

    It is not a theory, it is a measurement, and it holds across wildly different programs. The string
    you built to log a line, the iterator, the boxed Integer, the intermediate list — the overwhelming
    majority of allocations are dead within milliseconds. A smaller set — caches, connection pools,
    the object graph of a long-lived session — lives essentially forever. VERY LITTLE LIVES A MEDIUM
    AMOUNT OF TIME.

IF THAT IS TRUE, TWO DESIGN DECISIONS FOLLOW IMMEDIATELY:

    SEPARATE THE YOUNG FROM THE OLD, and collect the young region far more often. You spend your effort
    where the garbage is, and you almost never touch the region where nothing is dying.

    COLLECT THE YOUNG REGION BY COPYING, NOT BY SWEEPING. Walk the roots, copy every live object out to
    another space, then mark the whole original region free in a single operation. THE COST IS
    PROPORTIONAL TO THE SURVIVORS. If 98% of the region is dead — which the hypothesis says it will be
    — you did 2% of the work of examining it object by object.

    AND COPYING COMPACTS FOR FREE. Because survivors are copied out one after another, the space left
    behind has no holes. Which means ALLOCATION becomes a pointer bump: to allocate, add the object's
    size to a pointer. That is a handful of instructions, and it is why "object allocation is slow in
    Java" has been wrong for about twenty years.

THE MECHANISM THAT MAKES THE POINTER BUMP THREAD-SAFE WITHOUT A LOCK is worth naming: each thread gets
its own THREAD-LOCAL ALLOCATION BUFFER (TLAB), a private slice of Eden. Allocating inside your own TLAB
needs no synchronisation at all. Only refilling it does.

THE PRICE OF THE SPLIT, and it is the part that is easy to forget: if the collector only walks the
young region, it must still find references INTO the young region FROM the old one. It cannot scan the
whole old generation — that would defeat the purpose. So the JVM tracks those references as they are
created, using a WRITE BARRIER on every reference store into an old object, recording the location in a
CARD TABLE. Every reference assignment in your program pays a tiny tax so that young collections can
stay short. THAT TRADE — a small constant cost everywhere to buy a large saving at collection time — is
the shape of nearly every choice in this area.""",

"""3. THE MECHANISM — Eden, survivors, promotion, and what each collector does differently

THE CLASSIC LAYOUT:

    ┌───────────────── YOUNG ─────────────────┐  ┌──────── OLD (Tenured) ────────┐
    │   Eden (large)   │  S0  │  S1  │           │    long-lived objects         │
    └──────────────────┴──────┴──────┘           └───────────────────────────────┘

    ALLOCATION goes into Eden, by pointer bump inside a TLAB.
    WHEN EDEN FILLS → a MINOR GC. Live objects in Eden and in the occupied survivor space are copied
    into the OTHER survivor space; Eden and the vacated survivor are then wholesale empty.
    EACH SURVIVAL INCREMENTS AN AGE COUNTER in the object header. Past the TENURING THRESHOLD the
    object is PROMOTED to the old generation instead.
    THE OLD GENERATION is collected rarely and expensively.

    NOTE WHAT THIS IMPLIES: AN OBJECT'S ADDRESS CHANGES. Repeatedly. Which is why Java has no
    meaningful pointer arithmetic, why `identityHashCode` has to be stored once computed, and why a
    native library holding a raw address must pin the object.

THE COLLECTORS, and the ONE trade-off that distinguishes them — you may have low pause time, high
throughput, or small footprint, and no collector gives all three:

    SERIAL       one thread, stop-the-world. Small heaps, containers with one CPU. Genuinely the
                 fastest choice below a few hundred MB, because it has no coordination cost.
    PARALLEL     multiple threads, still fully stop-the-world. THE HIGHEST THROUGHPUT of any collector.
                 Correct for batch jobs where a two-second pause costs nothing.
    G1           the default since Java 9. Splits the heap into REGIONS (1–32 MB) rather than
                 contiguous generations, and each region is designated Eden, Survivor or Old
                 DYNAMICALLY. Marks concurrently, then evacuates the regions with the most garbage
                 first — "garbage first" — so it can aim at a PAUSE TARGET (default 200 ms) by simply
                 collecting fewer regions per cycle.
    ZGC          concurrent almost everywhere, sub-millisecond pauses that are INDEPENDENT OF HEAP
                 SIZE — the same pause at 4 GB and 4 TB. Uses coloured pointers and LOAD BARRIERS: the
                 barrier fixes up a reference as it is read, so objects can be relocated while the
                 application runs. Generational since Java 21. Costs some throughput and footprint.
    SHENANDOAH   the same goal by a different route, concurrent evacuation with a forwarding pointer.

TWO G1 DETAILS THAT CAUSE REAL INCIDENTS:

    HUMONGOUS OBJECTS — anything larger than half a region is allocated directly into contiguous Old
    regions and is handled poorly. A steady stream of large arrays can fragment the heap and trigger
    full GCs on a heap that looks nowhere near full.
    EVACUATION FAILURE — if there is no free region to copy survivors into, G1 falls back to a FULL,
    single-threaded, compacting collection. That is the multi-second pause in the log.""",

"""4. EDGE CASES AND FAILURE MODES

CASE 1 — THE STATIC COLLECTION THAT ONLY GROWS. A `static Map` used as a cache with no eviction. Every
entry is reachable, so nothing is collectable, and the leak is in your code, not the collector.

CASE 2 — THE UNREGISTERED LISTENER. An object registers a callback and is never removed. The registry
holds it, so it and everything it references live forever. THE MOST COMMON LEAK IN LONG-RUNNING JAVA
APPLICATIONS.

CASE 3 — THE INNER CLASS THAT OUTLIVES ITS OUTER. A non-static inner class holds an implicit reference
to the enclosing instance. Hand one to a long-lived executor and the enclosing object cannot die.

CASE 4 — ThreadLocal IN A POOLED THREAD. The thread is never destroyed, so the value is never cleared.
Classic in servlet containers. Always `remove()` in a finally.

CASE 5 — PROMOTION OF THINGS THAT SHOULD HAVE DIED. If the survivor spaces are too small, objects are
promoted to the old generation prematurely, the old generation fills, and full GCs begin. THE SYMPTOM
IS OLD-GEN GROWTH IN AN APPLICATION THAT ALLOCATES NOTHING LONG-LIVED.

CASE 6 — ALLOCATION RATE AS THE REAL DIAL. If the application allocates faster than the collector can
keep up, no tuning flag saves it. GC time is a symptom; allocation rate is usually the cause.

CASE 7 — HUMONGOUS ALLOCATION UNDER G1. Large arrays fragment the region layout and force full GCs.

CASE 8 — CALLING `System.gc()`. A hint, not a command. Under some collectors it forces a full
stop-the-world collection you did not want. Production code should essentially never call it, and
`-XX:+DisableExplicitGC` exists because libraries do.

CASE 9 — FINALIZERS. Deprecated, and rightly: they run on an unspecified thread at an unspecified time,
can resurrect the object, and DELAY collection by at least one extra cycle. Use try-with-resources for
resources and `Cleaner` if you truly need a native-memory hook.

CASE 10 — HEAP TOO LARGE. Above about 32 GB the JVM can no longer use COMPRESSED ORDINARY OBJECT
POINTERS (4-byte references instead of 8), so every reference doubles in size and effective capacity
can go DOWN as you raise -Xmx. A 31 GB heap can hold more objects than a 33 GB one.

CASE 11 — CONTAINER MEMORY LIMITS. A JVM that does not see the cgroup limit sizes its heap from the
HOST's memory and is killed by the OOM killer with no Java-level error at all. Modern JVMs are
container-aware; older ones need -XX:MaxRAMPercentage.

CASE 12 — MEASURING GC BY PAUSE COUNT. What matters is the percentage of wall time spent paused and
the tail of the pause distribution, not how many collections happened.""",

"""5. THE ALTERNATIVES — how to choose, and what to reach for instead of a flag

CHOOSING A COLLECTOR is mostly one question: WHAT DOES A PAUSE COST YOU?

    A BATCH JOB, A BUILD, AN ETL PIPELINE. Nothing is waiting. Use PARALLEL — it has the highest
    throughput of anything available, precisely because it does not do concurrent work.
    A WEB SERVICE WITH ORDINARY LATENCY GOALS. G1, the default. Set a pause target and leave it.
    A LATENCY-CRITICAL SERVICE, OR A VERY LARGE HEAP. ZGC or Shenandoah. Pauses stay sub-millisecond
    at any heap size, and you pay in throughput and footprint.
    A SMALL CONTAINER, ONE OR TWO CPUS. SERIAL. Concurrent collectors need spare cores; without them
    they steal from the application.
    A PROCESS THAT EXITS BEFORE IT COLLECTS. EPSILON — a no-op collector. Genuinely useful for
    short-lived tools and for proving how much memory a benchmark really allocates.

BEFORE TUNING ANYTHING, REDUCE ALLOCATION. It is usually the larger win and it is always the more
durable one:
    primitive collections or arrays instead of `List<Integer>`;
    `StringBuilder` rather than concatenation in a loop;
    `mapToInt` rather than `Stream<Integer>`;
    reusing buffers on genuinely hot paths.
    AND MEASURE FIRST — escape analysis may already have removed the allocation you are worried about.

REFERENCE TYPES, for the cases where you want the collector to help you:
    SOFT       cleared only when memory is tight. A memory-sensitive cache — though in practice a
               bounded LRU cache is easier to reason about and behaves better.
    WEAK       cleared as soon as nothing strong points at it. This is what WeakHashMap uses, and it
               is the right tool for keying metadata by an object you do not own.
    PHANTOM    for cleanup after collection, via a reference queue. What `Cleaner` is built on.

OFF-HEAP AND ALTERNATIVES:
    ByteBuffer.allocateDirect and the Java 21+ Foreign Function & Memory API move data outside the
    heap, so the collector never walks it. Right for very large caches and for I/O buffers; wrong
    almost everywhere else, because you have reintroduced manual lifetime management.

WHAT TO LOOK AT INSTEAD OF GUESSING:
    -Xlog:gc* (Java 9+) for the log. A heap dump plus Eclipse MAT for a leak — its dominator tree
    answers "what is keeping this alive", which is the only question that matters. JFR for allocation
    profiling by call site.

WHAT TO SAY: "Default to G1, use Parallel for batch and ZGC for latency-critical or very large heaps.
But almost every GC problem I have actually seen was an allocation-rate problem or a retention bug, and
neither is fixed with a flag."

""",

"""6. HOW TO DIAGNOSE A GC PROBLEM — numbered steps

STEP 1 — ESTABLISH WHICH PROBLEM YOU HAVE. Long pauses, or growth? They have almost nothing in common.
Pauses are a tuning and collector question; growth is a retention bug in your code.

STEP 2 — TURN ON THE LOG. `-Xlog:gc*:file=gc.log:time,uptime,level,tags`. It costs almost nothing and
you cannot reason without it.

STEP 3 — READ THE PERCENTAGE, NOT THE COUNT. Time paused as a fraction of wall time, plus the p99 pause.
Thousands of 1 ms pauses are healthy; three 4-second pauses are not.

STEP 4 — CHECK WHETHER THE OLD GENERATION IS GROWING ACROSS FULL GCs. Old-gen occupancy that is higher
after every full collection than after the last one is a LEAK, and no flag will help.

STEP 5 — FOR A LEAK, TAKE A HEAP DUMP AND OPEN THE DOMINATOR TREE. `jcmd <pid> GC.heap_dump`. Ask what
is retaining the largest object, not what is largest.

STEP 6 — FOR PAUSES, LOOK AT THE ALLOCATION RATE FIRST. MB/s promoted and MB/s allocated. High
allocation is fixed in code and only mitigated by flags.

STEP 7 — CHECK FOR PREMATURE PROMOTION. Objects reaching the old generation at a low age means the
young generation or survivor spaces are too small for the workload.

STEP 8 — LOOK FOR FULL GCs AND NAME THE CAUSE. Evacuation failure, humongous allocation, metaspace, or
an explicit `System.gc()`. Each has a different fix.

STEP 9 — SET -Xms EQUAL TO -Xmx for a server. Heap resizing causes full collections, and a server will
reach its maximum anyway.

STEP 10 — CHANGE ONE FLAG AT A TIME AND MEASURE. GC tuning is where cargo-culted flag lists go to
accumulate; most inherited flag sets contain options that are obsolete, contradictory, or no longer
exist.

STEP 11 — IN A CONTAINER, VERIFY THE JVM SEES THE LIMIT. `-XX:MaxRAMPercentage` and check the resolved
heap size, or the OOM killer will end the process with no Java-level error.

STEP 12 — BEFORE ANY OF THIS, CONSIDER ALLOCATING LESS. It is the fix that keeps working after the
next JVM upgrade changes all the defaults.""",

"""7. THE ANSWER IN PLAIN LANGUAGE — what you would say out loud

'The collector works out which objects are still REACHABLE — meaning there's a chain of references from
a running thread, a static field or a local variable — and everything else is garbage by definition,
because no code could ever look at it again.

The key word is reachable, not used. The collector can't tell whether you're FINISHED with an object,
only whether you can still get to it. That's why Java still has memory leaks: a static cache, a
listener registry, a ThreadLocal in a pooled thread. The collector is doing its job exactly right while
the heap fills.

The design is built on one measurement, the weak generational hypothesis: most objects die young. It's
not a theory, it holds across wildly different programs. So you split the heap, collect the young part
constantly, and collect the young part BY COPYING — walk the roots, copy the survivors out, then mark
the whole region free in one step. The cost is proportional to what SURVIVED, not to what died. If 98%
of the region is garbage you did 2% of the work.

That inverts the usual instinct. Creating short-lived garbage is nearly free. And because copying
leaves no holes, allocation becomes a pointer bump — a handful of instructions in a thread-local buffer
with no synchronisation at all. "Allocation is slow in Java" has been wrong for about twenty years.

The price is that if you only collect the young region, you still have to find references INTO it from
the old one — and you can't scan the old generation, that would defeat the point. So there's a write
barrier on every reference store into an old object, recording it in a card table. Your program pays a
tiny tax on every reference assignment to keep young collections short. That trade — a small cost
everywhere to buy a big saving at collection — is the shape of nearly every decision in this area.

On collectors: there's one trade-off, and you get two of three. Throughput, pause time, footprint.
Parallel is the highest throughput and fully stop-the-world, so it's right for batch. G1 is the default
— region-based, marks concurrently, evacuates the regions with the most garbage first, which is how it
can aim at a pause target: collect fewer regions. ZGC gives sub-millisecond pauses INDEPENDENT of heap
size, same pause at 4 GB and 4 TB, using load barriers that fix up references as they're read so
objects can move while the application runs. Costs throughput. And Serial genuinely wins on a
one-CPU container, because concurrent collectors need spare cores to be concurrent in.

But honestly — almost every GC problem I've actually seen was either an allocation-rate problem or a
retention bug, and neither is fixed with a flag. So I'd separate the two questions first: long pauses,
or growth? If old-gen occupancy is higher after every full GC than after the last one, that's a leak,
take a heap dump and read the dominator tree. If it's pauses, look at allocation rate before touching
any option.'""",

"""8. THE CODE, LINE BY LINE — a leak, and why it is not the collector's fault

    // ── THE LEAK EVERY LONG-RUNNING SERVICE HAS HAD ─────────────────────
    public class EventBus {
        private static final List<Listener> LISTENERS = new ArrayList<>();
        //                   ^^^^^^ STATIC. A GC ROOT. Everything in this list is
        //                   reachable from a root forever, by definition.

        public static void register(Listener l) { LISTENERS.add(l); }
        // ^ and no unregister. Every listener ever added lives until the JVM exits,
        //   ALONG WITH EVERYTHING IT REFERENCES — which for an inner class is the
        //   entire enclosing object graph.
    }

    class Session {                          // 50 MB of cached user state
        void start() {
            EventBus.register(e -> handle(e));
    //                        ^^^^^^^^^^^^^ this lambda captures `this`, because
    //      handle() is an instance method. The Session — and its 50 MB — is now
    //      reachable from a static field. Ten thousand sessions later, OutOfMemory.
        }
    }
    // THE COLLECTOR IS CORRECT AT EVERY STEP. Reachable is not the same as needed.

    // ── THE OTHER CLASSIC: ThreadLocal IN A POOLED THREAD ───────────────
    static final ThreadLocal<Context> CTX = new ThreadLocal<>();
    void handleRequest(Request r) {
        CTX.set(new Context(r));             // ← the POOL thread never dies, so
        process();                           //   this value is never cleared, and
    }                                        //   it holds the request alive.
    // FIX: try { ... } finally { CTX.remove(); }

    // ── WHY ALLOCATION IS NOT THE THING TO WORRY ABOUT ──────────────────
    for (int i = 0; i < 1_000_000; i++) {
        String s = "row " + i;                // a million short-lived objects
        process(s);
    }
    // ^ These die in Eden. A minor GC copies only the SURVIVORS — near zero — and
    //   declares the whole region empty. The million dead objects cost NOTHING.
    //   Each allocation was a pointer bump inside this thread's own TLAB: no lock,
    //   no free list, a handful of instructions. And escape analysis may have
    //   removed some of them entirely.

    // ── THE ALLOCATION THAT ACTUALLY HURTS ──────────────────────────────
    cache.put(key, new byte[8 * 1024 * 1024]);
    //             ^^^^^^^^^^^^^^^^^^^^^^^^^ larger than half a G1 region, so it is
    //   a HUMONGOUS object: allocated straight into contiguous Old regions, never
    //   young-collected, and a steady stream of them fragments the heap into full
    //   GCs while the heap looks far from full.

    // ── WHAT TO RUN, NOT WHAT TO GUESS ──────────────────────────────────
    // -Xlog:gc*:file=gc.log:time,uptime,level,tags   the log
    // jcmd <pid> GC.heap_info                        live occupancy
    // jcmd <pid> GC.heap_dump /tmp/h.hprof           then MAT's dominator tree
    // System.gc();  ← a HINT, and under some collectors a full STW pause you did
    //                 not ask for. Production code should never call it.""",

"""9. THE TRACE — one minor GC, and the cost that is not where you expect

STARTING STATE. Eden 512 MB, survivors 64 MB each, old 2 GB. The application has just allocated a
million short-lived strings and holds onto three of them.

    step  what happens                                          cost
    -----------------------------------------------------------------------------------
    1     Eden fills. An allocation cannot bump the pointer.      —
    2     Threads roll forward to a SAFEPOINT and stop.           the pause begins here,
          Not instantly — a thread in a long counted loop can     and "time to safepoint"
          take a while to reach one.                              is its own metric
    3     Roots are scanned: every thread stack, every static
          field, JNI references.                                  proportional to ROOTS
    4     The CARD TABLE is consulted for old→young references.   proportional to DIRTY
          This is why the write barrier existed.                  CARDS, not to old size
    5     Live objects are COPIED to the empty survivor space,
          ages incremented, anything past the tenuring
          threshold promoted to Old.                              PROPORTIONAL TO SURVIVORS
    6     Eden and the old survivor space are declared empty
          wholesale. No per-object work.                          O(1)
    7     Threads resume.                                         pause ends

    THE MILLION DEAD OBJECTS APPEAR NOWHERE IN THIS TABLE. That is the whole point. Step 5 touched
    three objects. Step 6 reclaimed 512 MB in a single operation.

NOW THE SAME TRACE WITH A CACHE THAT RETAINS 400 MB OF WHAT WAS ALLOCATED:

    step 5     400 MB must be COPIED, then promoted           the pause grows by orders
    step 6     unchanged                                      of magnitude
    old gen    grows by 400 MB every cycle                    → old fills → FULL GC

    SAME ALLOCATION RATE. SAME COLLECTOR. SAME FLAGS. The difference is entirely SURVIVAL RATE, which
    is a property of your code. This is the single most useful thing to know about GC: you tune the
    collector, but you control the survival rate, and the survival rate is what the cost is
    proportional to.

READING THE LOG — what each line is telling you:

    [gc] Pause Young (Normal) 512M->8M(2G) 4.2ms
          ^ healthy. 512 MB in, 8 MB survived, 4 ms. Survival rate 1.5%.

    [gc] Pause Young (Normal) 512M->480M(2G) 210ms
          ^ 94% SURVIVED. Either a leak, or the young generation is too small for the
            workload so objects that would have died are being caught mid-life.

    [gc] Pause Full (G1 Evacuation Pause) 1.9G->1.8G(2G) 3400ms
          ^ THE INCIDENT. A full, compacting collection that freed almost nothing.
            G1 had no free region to evacuate into. The next one will be worse.

    [gc] Pause Young (Concurrent Start) (G1 Humongous Allocation)
          ^ an object larger than half a region. A steady stream of these fragments
            the heap, and the heap will not look full when it fails.

    THE DIAGNOSTIC RULE THAT COVERS MOST CASES: compare the number AFTER the arrow across successive
    FULL collections. If it climbs every time, you have a retention bug and no flag will help. If it
    returns to the same floor, the heap is behaving and the question is pauses, not growth.""",

"""10. COMPLEXITY, THE MISTAKES, AND THE TAKEAWAY

    Allocation is a pointer bump in a thread-local buffer — a handful of instructions, no lock.
    A young collection costs O(survivors), NOT O(allocated). Dead objects are free.
    A full collection costs O(live heap) and is the pause that shows up in incident reviews.
    The write barrier taxes every reference store into an old object; that is what buys short young
    pauses.
    G1 pause target: default 200 ms, achieved by collecting FEWER REGIONS, not by working faster.
    ZGC pauses are sub-millisecond and INDEPENDENT of heap size — 4 GB and 4 TB alike.
    Above ~32 GB compressed oops are lost and every reference doubles in size.

THE #1 MISTAKE: believing Java cannot leak. Reachable is not the same as needed, and unbounded caches,
listener registries and ThreadLocals in pooled threads leak exactly as reliably as `malloc` without
`free`.

THE #2 MISTAKE: tuning flags for a retention bug. If old-gen occupancy after each full GC keeps
climbing, no option helps. Take a heap dump.

THE #3 MISTAKE: optimising away short-lived allocation. It is nearly free, and escape analysis may have
removed it already. Optimise SURVIVAL, not allocation.

THE #4 MISTAKE: calling `System.gc()`. A hint that can become a full stop-the-world pause you did not
want.

THE #5 MISTAKE: raising -Xmx past 32 GB without realising compressed oops are lost, so effective
capacity can fall as the number rises.

THE #6 MISTAKE: using a concurrent collector on one or two cores. It needs spare CPU to be concurrent
in; without it, it steals from the application. Serial is genuinely correct there.

THE #7 MISTAKE: judging GC health by collection count. Percentage of wall time paused and the p99
pause are the numbers.

THE #8 MISTAKE: relying on finalizers. Unspecified thread, unspecified time, and they DELAY collection
by an extra cycle. try-with-resources, or `Cleaner`.

THE #9 MISTAKE: leaving -Xms below -Xmx on a server. Heap growth triggers full collections on the way
to a maximum the server will reach anyway.

THE #10 MISTAKE: ignoring humongous allocations under G1. Large arrays fragment the region layout and
force full GCs on a heap that looks half empty.

THE #11 MISTAKE: copying an inherited flag list. Most contain options that are obsolete, mutually
contradictory, or removed in the JVM actually running.

ONE-SENTENCE TAKEAWAY: garbage collection reclaims what is UNREACHABLE — not what is unused, which is
why Java leaks — and it is built on the measurement that most objects die young, so the heap is split
and the young region collected by COPYING SURVIVORS OUT and freeing the rest wholesale, making the cost
proportional to what lived rather than what died and making allocation a lock-free pointer bump; choose
Parallel for throughput, G1 by default, ZGC when pauses matter at any heap size, and Serial on one
core — but diagnose growth and pauses as separate problems first, because almost every real GC incident
is a retention bug or an allocation rate, and neither is fixed with a flag.""",
]


DEEP["Virtual threads (Java 21) — what actually changed"] = [
"""1. THE GOAL IN PLAIN ENGLISH — getting blocking code back

For twenty-five years a Java thread was an OPERATING SYSTEM thread. One-to-one. The OS reserved about a
megabyte of stack for each one, switching between them meant a trip through the kernel, and the
practical ceiling was a few thousand per process — not because Java said so, but because the OS did.

    THAT CEILING SHAPED HOW EVERYONE WROTE SERVERS. The natural design — one thread per request, write
    plain blocking code, let the thread wait — stopped working the moment you needed ten thousand
    concurrent requests. So the industry moved to callbacks, then futures, then reactive streams: every
    blocking call rewritten as "start this, and here is what to do when it finishes".

    THE COST OF THAT MOVE WAS ENORMOUS AND MOSTLY UNCOUNTED. Stack traces became useless, because the
    stack no longer contains the logical caller. Breakpoints stopped meaning anything. try/catch and
    try-with-resources no longer spanned the operation. ThreadLocal stopped working. And the code
    inverted: the sequence you wanted to express was scattered across a dozen callbacks.

    VIRTUAL THREADS REMOVE THE CEILING, SO THE ORIGINAL DESIGN WORKS AGAIN. A virtual thread is
    scheduled by the JVM, not the OS. It costs a few hundred bytes, not a megabyte. You can have
    millions. So you go back to writing `var response = http.send(request)` on one line, blocking, in a
    thread of its own — and your stack traces, debugger, and exception handling all work again.

    THE HEADLINE IS NOT SPEED. A virtual thread does not make one request faster. It makes it cheap to
    have a million requests in flight, WITHOUT giving up the programming model. THAT is the change.

THE EVERYDAY VERSION: a restaurant where each waiter can serve exactly one table and must stand there
while the kitchen cooks. With ten waiters you seat ten tables. The old fix was to make every waiter
juggle twenty tables with a clipboard of half-finished orders — more throughput, far more mistakes, and
nobody can tell you what is happening at table six. Virtual threads make waiters nearly free instead:
one per table again, and each one can simply stand and wait.

TERMS AS THEY APPEAR:
- PLATFORM THREAD: the old kind. One OS thread each.
- CARRIER THREAD: a platform thread that a virtual thread is currently running on.
- MOUNT / UNMOUNT: a virtual thread being placed on, or lifted off, a carrier.
- PINNING: a virtual thread that cannot unmount, so it holds its carrier while blocked.""",

"""2. THE INTUITION — why blocking became cheap

WHEN A PLATFORM THREAD BLOCKS ON I/O, the OS parks it. Its stack — up to a megabyte of reserved address
space — sits idle, and the kernel must be involved to switch to something else. Ten thousand of those
is ten gigabytes of reserved stack and a scheduler with ten thousand entries to manage.

    A VIRTUAL THREAD'S STACK LIVES ON THE JAVA HEAP. That single fact is the whole design.

    When a virtual thread blocks, the JVM COPIES ITS STACK FRAMES TO THE HEAP, lifts it off the carrier,
    and runs a different virtual thread on that same carrier. When the I/O completes, the frames are
    copied back onto a carrier — not necessarily the same one — and it continues from exactly where it
    was. The Java code never notices. It called `read()`, and `read()` returned.

    SO "BLOCKING" NO LONGER MEANS "OCCUPYING AN OS THREAD". It means "parking a small heap object". A
    blocked virtual thread costs roughly what its live stack costs, which starts in the hundreds of
    bytes and grows only as deep as the call chain actually goes.

    AND THE SWITCH NEVER ENTERS THE KERNEL. The JVM schedules virtual threads itself, onto a small
    ForkJoinPool of carriers sized by default to the number of processors. Switching is a user-space
    operation, roughly the cost of a method call plus some copying, rather than a kernel context
    switch.

WHICH GIVES THE COMPARISON THAT MATTERS:

                             platform thread          virtual thread
    ---------------------------------------------------------------------
    cost to create           OS syscall, ~1 MB        heap object, ~hundreds of bytes
    practical count          a few thousand           millions
    blocking costs           an OS thread             a parked heap object
    context switch           kernel                   user space
    scheduled by             the OS                   the JVM
    CPU-BOUND THROUGHPUT     THE SAME                 THE SAME

    THAT LAST ROW IS THE ONE PEOPLE MISS, AND IT IS THE MOST IMPORTANT. If your task is computing
    rather than waiting, virtual threads do nothing whatsoever. You still have the same number of cores.
    Virtual threads solve WAITING, and only waiting. A CPU-bound workload wants a bounded pool sized to
    the cores, exactly as before.

THE DEEPER POINT: the reason we pooled threads was that threads were expensive. POOLING WAS NEVER THE
GOAL — it was a workaround. Remove the expense and the workaround becomes an anti-pattern, which is why
the recommended usage is one virtual thread per task, created and discarded, with no pool at all.""",

"""3. THE MECHANISM — continuations, carriers, and pinning

UNDERNEATH A VIRTUAL THREAD IS A CONTINUATION — an object that can capture the current call stack, be
put aside, and later be resumed. `Continuation.yield()` copies the frames from the carrier's stack onto
the heap; `Continuation.run()` copies them back and jumps to where it left off.

    EVERY BLOCKING OPERATION IN THE JDK WAS REWRITTEN TO YIELD INSTEAD OF BLOCK. Socket reads, file
    channel operations, `Thread.sleep`, `BlockingQueue.take`, lock acquisition, `Future.get`. When a
    virtual thread calls one, the JDK registers interest in the event, yields, and the carrier
    immediately picks up another virtual thread.

    THIS IS WHY IT ONLY WORKS FOR JDK BLOCKING. A blocking call inside a NATIVE library — a JNI
    method, or an old driver doing its own socket I/O — cannot yield, because the JVM cannot copy a
    native frame to the heap and put it back. It blocks the carrier.

THE CARRIER POOL. A dedicated ForkJoinPool, in FIFO mode, with parallelism defaulting to
`availableProcessors()`. It is NOT the common pool. Its size caps how many virtual threads can be
RUNNING at once, which is exactly right — that number should equal your cores. What is uncapped is how
many can be WAITING.

PINNING — the one failure mode you must know:

    A virtual thread CANNOT unmount while it is inside a `synchronized` block or method, or while it
    has native frames on its stack. In those states, blocking blocks the CARRIER.

    THE SYMPTOM IS A THROUGHPUT CLIFF, NOT AN ERROR. If every request holds a `synchronized` lock
    across its database call, then on an 8-core machine you have 8 carriers, all pinned, and your
    million virtual threads run 8 at a time. Nothing throws. The application is simply and
    inexplicably serialised. In the worst case it DEADLOCKS: every carrier pinned, waiting on work that
    needs a carrier to proceed.

    THIS IS WHY THE STANDARD ADVICE WAS TO REPLACE `synchronized` WITH `ReentrantLock`, which is
    virtual-thread aware and unmounts correctly. JEP 491 in JDK 24 removed the `synchronized`
    limitation, so on a modern JDK it is largely historical — but native frames still pin, and a great
    deal of production code still runs on 21.

    DETECTING IT: the JFR event `jdk.VirtualThreadPinned`, or `-Djdk.tracePinnedThreads=full` on 21.

OTHER PROPERTIES WORTH KNOWING: virtual threads are ALWAYS daemon threads, so they do not keep the JVM
alive. Priorities are ignored. Thread groups are vestigial. And `jcmd <pid> Thread.dump_to_file
-format=json` gives you a dump of a million of them, grouped, which is the observability story that
callbacks never had.""",

"""4. EDGE CASES AND FAILURE MODES

CASE 1 — POOLING VIRTUAL THREADS. `Executors.newFixedThreadPool` of virtual threads reintroduces the
exact limit they exist to remove. Use `newVirtualThreadPerTaskExecutor()`. THE POOL WAS THE WORKAROUND,
NOT THE GOAL.

CASE 2 — PINNING ON `synchronized` (JDK 21–23). A lock held across a blocking call pins the carrier;
throughput collapses to the carrier count, silently. `ReentrantLock` instead, or JDK 24+.

CASE 3 — PINNING ON NATIVE FRAMES. A JNI-based driver or a native crypto call cannot unmount. Still
true on every JDK version.

CASE 4 — EXPECTING CPU-BOUND WORK TO GET FASTER. It will not. You have the same cores. Virtual threads
address waiting only.

CASE 5 — THE LIMITER MOVED, AND NOBODY NOTICED. A 200-thread pool was silently rate-limiting your
database to 200 concurrent queries. Replace it with unbounded virtual threads and the database receives
ten thousand, and falls over. THE THREAD POOL WAS LOAD-SHEDDING INFRASTRUCTURE THAT NOBODY DOCUMENTED.
Use a `Semaphore` to bound the resource explicitly, which is the honest version of what the pool was
doing.

CASE 6 — CONNECTION POOL EXHAUSTION AS THE NEW BOTTLENECK. Ten thousand virtual threads queueing for
twenty connections is not progress; it is the same queue in a different place, now with ten thousand
objects waiting in it.

CASE 7 — ThreadLocal AT SCALE. It still works, but a ThreadLocal holding 1 KB across a million virtual
threads is a gigabyte. `ScopedValue` is the designed replacement: immutable, bounded to a syntactic
scope, and inherited by child threads cheaply.

CASE 8 — LONG CPU-BOUND SECTIONS INSIDE A VIRTUAL THREAD. Nothing preempts them. A virtual thread only
yields at a blocking point, so a tight computational loop monopolises its carrier.

CASE 9 — `Thread.currentThread()` IDENTITY AS A KEY. With a thread per task, identity-keyed caches now
have a million entries instead of two hundred.

CASE 10 — MONITORING THAT COUNTS THREADS. Dashboards, alerts and thread-count-based autoscaling all
become meaningless. Count in-flight TASKS instead.

CASE 11 — STACK DEPTH. Deep recursion in a virtual thread grows a heap-allocated stack; it is not free,
and the failure mode is memory pressure rather than a neat StackOverflowError at a familiar depth.

CASE 12 — ASSUMING FRAMEWORK SUPPORT MEANS FRAMEWORK READINESS. A framework may run your handler on a
virtual thread while its own internals still hold `synchronized` locks across I/O, giving you all of
the migration and none of the benefit.""",

"""5. THE ALTERNATIVES — and what virtual threads replaced

PLATFORM THREADS WITH A BOUNDED POOL. Still exactly right for CPU-BOUND work: you want as many runnable
tasks as cores and no more. `Executors.newFixedThreadPool(cores)` is not obsolete; it was never about
I/O in the first place.

REACTIVE — Reactor, RxJava, Mutiny. What virtual threads are largely displacing for the ordinary case:
    THEY DELIVERED the same scalability, years earlier, on Java 8.
    THEY COST stack traces that do not show your caller, debuggers that cannot step, exceptions that
    escape into an error channel, ThreadLocal-based context that has to be reimplemented, and the
    "coloured function" problem where one async call forces every caller to become async.
    THEY STILL WIN when you genuinely need STREAM SEMANTICS — backpressure, windowing, merging, and
    operators over an unbounded flow. Virtual threads give you cheap concurrency, not a dataflow
    algebra. Do not rewrite a real streaming pipeline into blocking calls.

ASYNCHRONOUS NIO AND CompletableFuture BY HAND. Same trade as reactive, less machinery, more
boilerplate. `CompletableFuture` remains the right tool for COMPOSING independent operations and for
timeouts; it is no longer needed merely to avoid blocking a thread.

KOTLIN COROUTINES. The same idea — suspending instead of blocking — implemented in the compiler rather
than the runtime, with the `suspend` keyword making the colouring explicit. Virtual threads put it in
the JVM instead, so it works for every language and every existing library without recompilation.

STRUCTURED CONCURRENCY (`StructuredTaskScope`), which is the piece that makes virtual threads a
programming model rather than just a cheap thread:
    tasks forked in a block CANNOT OUTLIVE the block;
    a failure in one can cancel its siblings automatically;
    the parent's stack trace contains the child's, so an error is traceable to its origin;
    cancellation propagates down the tree instead of leaking.
    It restores to concurrency what `try`/`finally` did to resources: a lifetime bounded by syntax.

WHAT TO SAY: "Virtual threads for I/O-bound concurrency and thread-per-request, a bounded platform pool
for CPU-bound work, and reactive only where I genuinely need streaming semantics rather than just
scalability. And a Semaphore wherever the old thread pool was quietly limiting a downstream resource."

""",

"""6. HOW TO ADOPT THEM — numbered steps

STEP 1 — CONFIRM YOUR WORKLOAD IS I/O-BOUND. If threads are computing rather than waiting, virtual
threads change nothing and you should stop here.

STEP 2 — USE `Executors.newVirtualThreadPerTaskExecutor()`. One thread per task, created and discarded.
Do not pool them; that is the thing being removed.

STEP 3 — FIND EVERY `synchronized` BLOCK THAT SPANS A BLOCKING CALL. On JDK 21–23 these pin the carrier
and silently cap you at the core count. Convert to `ReentrantLock`, or move to JDK 24+.

STEP 4 — AUDIT NATIVE CALLS. JNI-based drivers and native crypto still pin on every version.

STEP 5 — REPLACE THE POOL'S IMPLICIT RATE LIMIT WITH AN EXPLICIT ONE. A `Semaphore` around the database,
the downstream service, the disk. THIS IS THE STEP MOST MIGRATIONS SKIP, and it is what turns "we
enabled virtual threads" into "we took down the database".

STEP 6 — SIZE THE CONNECTION POOL FOR THE NEW CONCURRENCY. Ten thousand threads and twenty connections
is the same queue, relocated.

STEP 7 — REVIEW ThreadLocal USAGE. Multiply its size by the number of concurrent tasks. Move context to
`ScopedValue` where you can.

STEP 8 — TURN ON PINNING DETECTION BEFORE YOU BELIEVE IT WORKS. JFR's `jdk.VirtualThreadPinned`, or
`-Djdk.tracePinnedThreads=full`. A pinning problem produces no error at all — only a number that is
lower than you expected.

STEP 9 — FIX YOUR MONITORING. Thread count is no longer a signal. Alert on in-flight tasks, queue depth
at the real bottleneck, and latency.

STEP 10 — USE `StructuredTaskScope` FOR FAN-OUT. Bounded lifetimes, automatic sibling cancellation, and
child stack traces attached to the parent.

STEP 11 — LOAD TEST WITH THE REAL DOWNSTREAM. The failure mode of this migration is never the JVM; it
is whatever the JVM is now allowed to hit ten thousand times at once.

STEP 12 — LEAVE CPU-BOUND WORK ON A BOUNDED PLATFORM POOL. Mixing the two is fine and expected; the
distinction is the point.""",

"""7. THE ANSWER IN PLAIN LANGUAGE — what you would say out loud

'For twenty-five years a Java thread was an OS thread, one to one. About a megabyte of reserved stack
each, switching went through the kernel, and you got a few thousand per process. That ceiling is why
everyone abandoned thread-per-request and moved to callbacks and reactive.

And that move cost a lot that nobody counted. Stack traces stopped containing your caller. Breakpoints
stopped meaning anything. try-with-resources no longer spanned the operation. ThreadLocal broke. And
one async call forces every caller to become async — the coloured function problem.

A virtual thread is scheduled by the JVM instead of the OS, and its stack lives on the HEAP. That one
fact is the whole design. When it blocks, the JVM copies its frames to the heap, lifts it off the
carrier thread, and runs something else there. When the I/O completes the frames get copied back — not
necessarily onto the same carrier — and it continues. The Java code never notices; it called read(),
and read() returned.

So blocking no longer means occupying an OS thread. It means parking a small heap object, a few hundred
bytes, and the switch never enters the kernel. You can have millions.

The thing people get wrong is thinking this is about speed. It is not. CPU-bound throughput is
IDENTICAL — you still have the same cores. Virtual threads solve WAITING, and only waiting. CPU-bound
work still wants a bounded pool sized to the cores.

And the second thing: don't pool them. We pooled threads because threads were expensive. Pooling was
never the goal, it was a workaround, so a pool of virtual threads reintroduces exactly the limit they
remove. It's newVirtualThreadPerTaskExecutor, one per task, created and thrown away.

The failure mode to know is PINNING. A virtual thread can't unmount while it's inside a synchronized
block or has native frames on its stack — so blocking there blocks the CARRIER. And the symptom is a
throughput cliff with no error at all: eight cores, eight carriers, all pinned, and your million
virtual threads run eight at a time. In the worst case it deadlocks. That's why the advice on 21 was
ReentrantLock instead of synchronized; JEP 491 in JDK 24 fixed the synchronized case, but native frames
still pin.

The operational trap I'd flag hardest, though, is that THE LIMITER MOVED. That 200-thread pool was
silently rate-limiting your database to 200 concurrent queries — it was load-shedding infrastructure
nobody documented. Swap in unbounded virtual threads and the database gets ten thousand and falls over.
So you replace the pool's implicit limit with an explicit Semaphore around each downstream resource.
That's the step migrations skip.

And the piece that makes it a programming model rather than just cheap threads is structured
concurrency — StructuredTaskScope. Forked tasks can't outlive the block, a failure cancels its
siblings, and the child's stack trace is attached to the parent's. It does for concurrency what
try/finally did for resources: a lifetime bounded by syntax.'""",

"""8. THE CODE, LINE BY LINE

    // ── THE OLD CEILING, MADE CONCRETE ──────────────────────────────────
    var pool = Executors.newFixedThreadPool(200);
    //                                      ^^^ 200 OS threads, ~200 MB of reserved
    //   stack, and a HARD CAP OF 200 CONCURRENT REQUESTS — not because 200 is
    //   right, but because 10,000 OS threads is not affordable.

    // ── THE NEW VERSION. Note what is NOT here: a size. ─────────────────
    try (var exec = Executors.newVirtualThreadPerTaskExecutor()) {
    //               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ONE VIRTUAL THREAD PER TASK.
    //   Not a pool. Creating and discarding a virtual thread is the intended usage;
    //   pooling them reintroduces the exact limit they exist to remove.
        for (var req : requests) {
            exec.submit(() -> handle(req));      // a million of these is fine
        }
    }   // close() waits for all tasks — the executor is an AutoCloseable barrier

    String handle(Request r) {
        var user = db.findUser(r.userId());      // BLOCKS. The virtual thread's
        //                                          frames are copied to the heap and
        //                                          the carrier immediately runs
        //                                          another virtual thread.
        var prefs = prefsService.fetch(user);    // BLOCKS again. Same story.
        return render(user, prefs);
    }
    // ^ Plain, sequential, blocking code. The stack trace of any exception in here
    //   contains handle() and its caller. A breakpoint works. try/catch spans the
    //   whole operation. THAT is what was given up for scalability, and given back.

    // ── PINNING: the bug with no error message ──────────────────────────
    synchronized (lock) {                 // ← the carrier CANNOT be released while
        var row = db.query(sql);          //   this frame is on the stack (JDK 21-23)
    }
    // ^ 8 cores → 8 carriers → all 8 pinned → your million virtual threads run
    //   EIGHT AT A TIME. Nothing throws. Throughput is just inexplicably flat.
    private final ReentrantLock lock = new ReentrantLock();
    lock.lock();
    try { var row = db.query(sql); } finally { lock.unlock(); }
    // ^ virtual-thread aware: unmounts correctly. (JEP 491 in JDK 24 fixes the
    //   synchronized case too — but NATIVE frames still pin on every version.)

    // ── THE LIMITER MOVED. The step migrations skip. ────────────────────
    private final Semaphore dbLimit = new Semaphore(200);
    //                                              ^^^ the 200 that used to be the
    //   POOL SIZE. It was rate-limiting the database all along, and nobody wrote
    //   that down. Remove the pool without this and the database receives 10,000
    //   concurrent queries.
    dbLimit.acquire();
    try { return db.query(sql); } finally { dbLimit.release(); }

    // ── STRUCTURED CONCURRENCY: lifetimes bounded by syntax ─────────────
    try (var scope = new StructuredTaskScope.ShutdownOnFailure()) {
        var user  = scope.fork(() -> userService.find(id));
        var order = scope.fork(() -> orderService.recent(id));
        scope.join().throwIfFailed();
    //  ^ NEITHER TASK CAN OUTLIVE THIS BLOCK. If one fails, the other is cancelled
    //    automatically, and the child's stack trace is attached to this one's.
        return new Page(user.get(), order.get());
    }

    // ── WHAT DOES NOT CHANGE ────────────────────────────────────────────
    var cpu = Executors.newFixedThreadPool(Runtime.getRuntime().availableProcessors());
    // ^ CPU-bound work. Same cores, same answer as before virtual threads existed.""",

"""9. THE TRACE — one carrier, three virtual threads, and then a pin

EIGHT CARRIERS ON AN 8-CORE MACHINE. Follow ONE of them while three virtual threads run on it:

    time  carrier-1 is running   what happened                          carrier state
    ------------------------------------------------------------------------------------
    t0    VT-1                   calls db.query()                       —
    t1    —                      VT-1's frames COPIED TO THE HEAP,      FREE, instantly
                                 unmounted, socket read registered
    t2    VT-2                   mounted on carrier-1, starts running   busy
    t3    —                      VT-2 calls http.send(), unmounts       FREE
    t4    VT-3                   mounted, runs, computes for 2 ms       busy
    t5    VT-1                   DB responded → frames copied BACK,     busy
                                 possibly onto a DIFFERENT carrier,
                                 and `query()` simply returns
    ------------------------------------------------------------------------------------
    ONE OS THREAD SERVED THREE REQUESTS AND WAS NEVER IDLE. No callbacks were written. VT-1's stack at
    t5 still contains `handle()` and everything that called it, because those frames were preserved
    verbatim — that is what makes the debugger and the stack trace work.

NOW THE SAME TRACE WITH `synchronized` AROUND THE QUERY (JDK 21):

    t0    VT-1                   enters synchronized, calls db.query()  —
    t1    VT-1 (BLOCKED)         CANNOT UNMOUNT — a monitor is held.    PINNED, 40 ms
                                 The carrier is stuck waiting on I/O.
    t2    VT-1 (BLOCKED)         VT-2 and VT-3 are runnable and CANNOT  still pinned
                                 be scheduled here.
    ------------------------------------------------------------------------------------
    MULTIPLY BY 8 CARRIERS: your concurrency is 8, not a million. NOTHING THROWS. No warning, no
    exception, no log line — only a throughput number that is lower than expected and a profile that
    shows everything waiting. This is the single most common disappointment in a virtual-thread
    migration, and it is invisible unless you enable `jdk.VirtualThreadPinned`.

AND THE THIRD TRACE — the one that takes down the database:

    before                                    after
    ------------------------------------------------------------------------------------
    200-thread pool                           unbounded virtual threads
    → at most 200 concurrent DB queries       → 10,000 concurrent DB queries
    → the pool was LOAD SHEDDING              → nothing is shedding load
    → excess requests queued in the pool      → excess requests hit the database
    → latency rose, the system survived       → connections exhausted, timeouts,
                                                 cascading failure upstream

    NOTHING IN THE JVM WENT WRONG. The application did exactly what it was now permitted to do. The
    200 was never a thread-count decision; it was a concurrency budget for a downstream resource,
    expressed in the only unit the old model had. THE FIX IS TO SAY IT OUT LOUD — a Semaphore of 200
    around the database — which is both the correct behaviour and the first time it has ever been
    written down.

WHAT EACH TRACE PROVED:
    TRACE 1   the stack-on-heap mechanism, and why blocking code keeps its stack trace.
    TRACE 2   pinning: a correctness-preserving, silent, order-of-magnitude throughput loss.
    TRACE 3   that a thread pool is TWO things — a resource pool and a rate limiter — and virtual
              threads remove the first while leaving you responsible for the second.""",

"""10. COMPLEXITY, THE MISTAKES, AND THE TAKEAWAY

    Platform thread: ~1 MB reserved stack, an OS scheduling entity, a few thousand per process.
    Virtual thread: hundreds of bytes initially, growing with real stack depth; millions per process.
    Mount/unmount: user-space, roughly a method call plus stack copying. No kernel transition.
    Carrier pool: a dedicated ForkJoinPool, parallelism = availableProcessors by default. It caps how
    many run AT ONCE, which is correct; what is uncapped is how many WAIT.
    CPU-bound throughput: UNCHANGED. Identical core count, identical result.
    Pinned carrier: concurrency silently drops to the carrier count, with no error of any kind.

THE #1 MISTAKE: pooling virtual threads. The pool was the workaround for expensive threads; keeping it
keeps the limit. `newVirtualThreadPerTaskExecutor()`.

THE #2 MISTAKE: expecting CPU-bound work to speed up. Same cores. Virtual threads address waiting only.

THE #3 MISTAKE: `synchronized` across a blocking call on JDK 21–23. Pins the carrier, silently.
`ReentrantLock`, or JDK 24+.

THE #4 MISTAKE: forgetting native frames still pin, on every version.

THE #5 MISTAKE — AND THE ONE THAT CAUSES OUTAGES: removing the pool without replacing the rate limit it
was silently providing. Put a `Semaphore` around every downstream resource.

THE #6 MISTAKE: leaving the connection pool at twenty. Ten thousand threads queueing for twenty
connections is the same queue, relocated and larger.

THE #7 MISTAKE: ThreadLocal at a million-thread scale. Multiply its size by the concurrency.
`ScopedValue` instead.

THE #8 MISTAKE: long CPU-bound sections inside a virtual thread. Nothing preempts them; a virtual
thread yields only at a blocking point.

THE #9 MISTAKE: monitoring thread count. It is no longer a signal. Count in-flight tasks.

THE #10 MISTAKE: believing they replace reactive entirely. They replace it for SCALABILITY; reactive
still wins where you need real stream semantics — backpressure, windowing, merging.

THE #11 MISTAKE: assuming a framework running handlers on virtual threads is ready. Its internals may
still hold monitors across I/O, giving you the migration and none of the benefit.

ONE-SENTENCE TAKEAWAY: a virtual thread is scheduled by the JVM with its stack on the HEAP, so blocking
means copying frames aside and freeing the carrier rather than occupying an OS thread — which makes
millions of concurrent waiting tasks affordable and hands back plain blocking code with working stack
traces, debuggers and try/finally, at the cost of exactly zero improvement to CPU-bound work; do not
pool them, watch for pinning on `synchronized` (pre-JDK 24) and native frames where throughput
collapses to the carrier count with no error at all, and above all replace the rate limit your old
thread pool was silently enforcing on every downstream resource, because that limit is the reason the
database survived.""",
]


DEEP["ArrayList vs LinkedList — and why the textbook answer is usually wrong"] = [
"""1. THE GOAL IN PLAIN ENGLISH — the answer everyone gives, and why it is wrong

THE TEXTBOOK ANSWER: an ArrayList is an array, so reading by index is instant but inserting in the
middle means shifting everything after it. A LinkedList is a chain of nodes each pointing at the next,
so inserting is just rewiring two pointers, but reading the thousandth element means walking a
thousand links. Therefore: ArrayList for reading, LinkedList for inserting.

    THAT ANSWER IS ALGORITHMICALLY CORRECT AND PRACTICALLY WRONG. On real hardware, for essentially
    every workload you will meet, ArrayList wins — INCLUDING at inserting and removing in the middle,
    which is precisely the case LinkedList is supposed to own.

    THE REASON IS NOT IN THE BIG-O. Big-O counts OPERATIONS and assumes every memory access costs the
    same. On a modern CPU that assumption is false by a factor of about a hundred: a value already in
    cache arrives in roughly a nanosecond, and one that must come from main memory takes closer to a
    hundred. An algorithm that touches memory PREDICTABLY beats one that touches less memory
    UNPREDICTABLY, and it beats it by more than the operation count suggests.

THE EVERYDAY VERSION: two ways to store a hundred documents. One is a single stack on your desk — to
insert in the middle you lift half the stack, which is real work, but it is one smooth motion. The
other scatters the hundred documents across a hundred rooms in a building, each with a note saying
which room the next one is in. Inserting is trivial: change two notes. Getting to document fifty means
walking to fifty rooms. AND THE WALKING IS THE ENTIRE COST — the fact that you did less "work" at the
insertion point is irrelevant next to it.

TERMS AS THEY APPEAR:
- CACHE LINE: memory is fetched in blocks, typically 64 bytes. Reading one byte fetches all 64.
- LOCALITY: whether the things you access next are near the things you accessed last.
- PREFETCHER: hardware that notices sequential access and fetches ahead of you, for free.
- POINTER CHASING: following a reference to find the address of the next reference. Unpredictable
  by construction, so the prefetcher cannot help.""",

"""2. THE INTUITION — why contiguity beats operation count

AN ARRAYLIST IS ONE CONTIGUOUS ARRAY OF REFERENCES. Walking it, the CPU reads 64 bytes at a time and
gets sixteen references per fetch (with compressed pointers). The prefetcher sees the pattern
immediately and loads the NEXT block while you are still using this one. In steady state you wait for
memory almost never.

A LINKEDLIST IS N SEPARATE NODE OBJECTS, each holding a previous pointer, a next pointer, and the item.
They are allocated at different times and land at different addresses.

    TO REACH THE NEXT ELEMENT YOU MUST FIRST READ THE CURRENT NODE — because the address of the next
    one IS THE DATA IN THIS ONE. The CPU cannot fetch ahead, because it does not know where ahead is
    until the current fetch returns. THAT IS A SERIALISED DEPENDENCY CHAIN OF MEMORY LOADS, and it is
    the worst pattern modern hardware has.

NOW COUNT THE MEMORY, which is the second half of the story:

    ARRAYLIST, per element: one 4-byte reference, plus up to 50% slack capacity. Call it 4–6 bytes.
    LINKEDLIST, per element: a Node object — 12-byte header, prev, next, item = 24 bytes, plus the
    element itself. Call it 24 bytes.

    THAT IS ROUGHLY FIVE TIMES THE MEMORY, and memory bandwidth is the scarce resource. A list that
    fits in L2 cache as an ArrayList may not fit as a LinkedList, and the difference between "in cache"
    and "not in cache" is the hundred-fold one.

AND THE INSERT CASE — the one LinkedList is supposed to win — has a hidden step:

    `list.add(5000, x)` ON A LINKEDLIST IS NOT O(1). The rewiring is O(1); FINDING position 5000 is
    O(n), and it is O(n) of the worst possible kind — five thousand dependent cache misses. The O(1)
    only exists if you ALREADY HOLD the node, and Java's `List` interface never gives you one.

    `list.add(5000, x)` ON AN ARRAYLIST IS O(n) SHIFTING — via `System.arraycopy`, which is a JVM
    INTRINSIC compiled to a vectorised block move. It moves many bytes per instruction, sequentially,
    at memory bandwidth. Moving ten thousand references costs a few microseconds.

    SO THE COMPARISON IS: a vectorised sequential block move, versus five thousand serialised pointer
    dereferences. The one with the better Big-O loses, and it loses badly.

THE HONEST SUMMARY, which is what makes this a good interview answer: LINKEDLIST'S ADVANTAGE IS REAL
ONLY WHEN YOU ALREADY HAVE A REFERENCE TO THE POSITION — which in Java means you are iterating and
using `Iterator.remove()`. Every other case, ArrayList.""",

"""3. THE MECHANISM — growth, arraycopy, and what each class actually is

ARRAYLIST INTERNALS:

    Object[] elementData;   // the backing array. Note: Object[], because of erasure.
    int size;               // how many are USED. capacity is elementData.length.

    GROWTH. When full, a new array of `oldCapacity + (oldCapacity >> 1)` — 1.5x — is allocated and the
    contents copied. The default starting capacity is 10, and it is allocated LAZILY on first add.
    Growth is O(n) but AMORTISED O(1): doubling-ish growth means the total copying across n additions
    is O(n), so each addition averages constant.
    `ensureCapacity(n)` up front skips all of it, and matters when n is large and known.

    add(i, x)        System.arraycopy shifts [i, size) right by one, then writes. O(n) but VECTORISED.
    remove(i)        System.arraycopy shifts left, then nulls the last slot (so it can be collected).
    get(i)           one bounds check, one array read. Genuinely O(1).

    THE SLACK IS A REAL COST. After growth an ArrayList can be up to 50% empty, and `trimToSize()`
    exists for the case where that matters. `remove` never shrinks the array.

LINKEDLIST INTERNALS: a doubly-linked list with head and tail pointers.

    private static class Node<E> { E item; Node<E> next; Node<E> prev; }

    get(i)           walks from the NEARER END — so index 0 and index size-1 are fast, and the middle
                     is the worst case at n/2 dependent loads. Still O(n).
    add(i, x)        walks to i, then rewires. O(n) walk + O(1) rewire.
    addFirst/addLast O(1) genuinely, and this is the only operation where it is competitive.
    Iterator.remove  O(1) genuinely, because the iterator holds the node.

    IT ALSO IMPLEMENTS Deque. Which is the source of most remaining uses — and `ArrayDeque` does the
    same job on a circular array, with better locality and less memory, so it wins there too.

THE OPERATION THAT DECIDES MOST REAL CODE — removing while iterating:

    ARRAYLIST + Iterator.remove()   O(n) per removal, because it still arraycopies the tail.
                                    Removing k elements one at a time is O(nk).
    ARRAYLIST + removeIf(pred)      ONE PASS. It marks survivors in a bitset and compacts once. O(n)
                                    TOTAL regardless of how many are removed. This is the fastest
                                    option available and most people do not know it exists.
    LINKEDLIST + Iterator.remove()  O(1) per removal, O(n) total — algorithmically the best, and
                                    still typically slower in wall clock because the WALK is the
                                    dominant cost, not the removals.""",

"""4. EDGE CASES AND FAILURE MODES

CASE 1 — `list.remove(0)` IN A LOOP TO DRAIN AN ARRAYLIST. Each removal shifts everything left, so
draining n elements is O(n²). Iterate forwards and clear, iterate BACKWARDS removing from the end, or
use `ArrayDeque` if it is really a queue.

CASE 2 — `list.remove(1)` MEANING TWO DIFFERENT THINGS. On a `List<Integer>`, `remove(int)` removes by
INDEX and `remove(Object)` removes by VALUE. `remove(1)` picks the index overload. `remove(Integer.valueOf(1))`
removes the value. The compiler chooses silently and both compile.

CASE 3 — USING LINKEDLIST AS A QUEUE. `ArrayDeque` does it with better locality, less memory, and no
per-element node allocation. LinkedList's Deque implementation is essentially legacy.

CASE 4 — GROWTH THRASH ON A KNOWN SIZE. Building a 100,000-element ArrayList from the default capacity
performs about 25 reallocations and copies. `new ArrayList<>(100_000)` performs none.

CASE 5 — MEMORY AFTER A LARGE LIST SHRINKS. `remove` never shrinks the backing array, so a list that
held a million elements still holds a million-slot array. `trimToSize()`.

CASE 6 — `Arrays.asList(...)` IS FIXED-SIZE. It is a VIEW over the array: `set` works and writes
through to the array, `add` and `remove` throw UnsupportedOperationException.

CASE 7 — `List.of(...)` IS FULLY IMMUTABLE AND REJECTS NULLS. Different failure from `Arrays.asList`,
which permits nulls.

CASE 8 — `subList` IS A VIEW, NOT A COPY. Structurally modifying the backing list invalidates it —
ConcurrentModificationException on next use — and modifying the sublist writes through to the parent.

CASE 9 — MEASURING WITH A LIST THAT FITS IN CACHE. A thousand-element benchmark shows LinkedList
looking respectable, because everything is in L1 and locality is free. At a million the gap becomes
enormous. THE SIZE AT WHICH YOU BENCHMARK DETERMINES THE ANSWER YOU GET.

CASE 10 — ASSUMING `contains` IS CHEAP. O(n) on both, with an `equals` call per element. If you are
calling it in a loop you wanted a `HashSet` and the whole comparison is beside the point.

CASE 11 — THREAD SAFETY ON NEITHER. `Collections.synchronizedList` locks every method but not
iteration; `CopyOnWriteArrayList` is right for read-mostly with rare writes.

CASE 12 — NULLS. Both permit them, so `list.get(i) == null` is ambiguous between "absent" and "stored
null" in exactly the way `Map.get` is.""",

"""5. THE ALTERNATIVES — what to reach for instead of either

ARRAYLIST is the default, and should be. Contiguous, cache-friendly, minimal per-element overhead,
`System.arraycopy` for the shifting. Reach for it unless you can name why not.

ARRAYDEQUE for anything queue- or stack-shaped. A circular array: O(1) at both ends with no node
allocation and good locality. IT BEATS BOTH `LinkedList` AND `Stack` AT THEIR OWN JOBS, and the
Javadoc says so explicitly.

HASHSET / LINKEDHASHSET the moment membership is the question. If you are calling `list.contains` in a
loop, this is the real fix and the ArrayList-versus-LinkedList question was never the bottleneck.

TREEMAP / PRIORITYQUEUE when you need ordering or a repeatedly-extracted minimum. A sorted ArrayList
that you re-sort is usually the wrong shape.

PRIMITIVE COLLECTIONS — Eclipse Collections, fastutil, HPPC — when the elements are primitives.
`ArrayList<Integer>` stores a reference to a boxed object per element: roughly 20 bytes and a pointer
dereference each, against 4 bytes contiguous for an `int[]`. FOR LARGE NUMERIC DATA THIS IS A BIGGER
WIN THAN ANY LIST CHOICE.

`int[]` OR `long[]` DIRECTLY when the size is fixed. No abstraction, no boxing, perfect locality.

COPYONWRITEARRAYLIST for read-mostly concurrent access — listener registries, configuration snapshots.
Every write copies the whole array, so it is wrong for anything write-heavy and perfect for the case
where writes are rare and iteration must never block.

`removeIf` INSTEAD OF AN ITERATOR LOOP. One compacting pass on an ArrayList, regardless of how many
elements match.

WHEN IS LINKEDLIST ACTUALLY RIGHT? Honestly: almost never in Java. The case it wins — O(1) insertion at
a position you already hold — requires node access the `List` interface does not expose, so the only
realisation is `Iterator.remove()` during a walk, and even there `removeIf` on an ArrayList usually
wins in wall-clock time. Java's own collections author has said publicly that he wrote it and does not
use it.

WHAT TO SAY: "ArrayList by default; ArrayDeque for queues and stacks; a Set if the question is
membership; primitive arrays or a primitive collection library if the elements are numbers. I would
want a measured reason to choose LinkedList, and I have not had one."

""",

"""6. HOW TO CHOOSE — numbered steps

STEP 1 — ASK WHAT THE ACCESS PATTERN ACTUALLY IS, not what the operation is called. "Insert in the
middle" via an index is a WALK plus an insert, and the walk dominates.

STEP 2 — DEFAULT TO ARRAYLIST. It is right often enough that the burden of proof is on the alternative.

STEP 3 — IF IT IS A QUEUE OR A STACK, USE ARRAYDEQUE. Not LinkedList, not `Stack`.

STEP 4 — IF THE QUESTION IS MEMBERSHIP, USE A SET. `list.contains` in a loop is O(n²) and no list
choice fixes it.

STEP 5 — IF THE ELEMENTS ARE PRIMITIVES AND THERE ARE MANY, USE AN ARRAY OR A PRIMITIVE COLLECTION.
Boxing costs more than the list structure ever will.

STEP 6 — PRE-SIZE WHEN YOU KNOW THE SIZE. `new ArrayList<>(n)` removes every reallocation and copy.

STEP 7 — USE `removeIf` FOR BULK REMOVAL. One compacting pass; an iterator loop is O(nk).

STEP 8 — NEVER `remove(0)` IN A LOOP. That is an accidental O(n²), and it is a common one.

STEP 9 — BE CAREFUL WITH `remove` ON A `List<Integer>`. Index or value, chosen silently by overload
resolution.

STEP 10 — IF YOU BENCHMARK, USE A REALISTIC SIZE. A thousand elements fit in cache and hide the entire
effect you are trying to measure.

STEP 11 — TREAT `subList` AND `Arrays.asList` AS VIEWS. They alias, and they throw on operations that
look ordinary.

STEP 12 — FOR CONCURRENT READ-MOSTLY, USE `CopyOnWriteArrayList`; otherwise a proper concurrent
structure. `Collections.synchronizedList` does not make ITERATION safe.""",

"""7. THE ANSWER IN PLAIN LANGUAGE — what you would say out loud

'The textbook answer is ArrayList for reading, LinkedList for inserting — O(1) index access versus O(1)
insertion. That's algorithmically correct and practically wrong. On real hardware ArrayList wins
essentially everywhere, including at the middle-insertion case LinkedList is supposed to own.

The reason isn't in the Big-O. Big-O counts operations and assumes every memory access costs the same.
That assumption is off by about a hundred: something in cache arrives in a nanosecond, something from
main memory takes closer to a hundred. So an algorithm that touches memory PREDICTABLY beats one that
touches less memory unpredictably.

An ArrayList is one contiguous array of references. Walking it, the CPU fetches 64 bytes at a time and
gets sixteen references, and the prefetcher sees the pattern and loads the next block while you're
still using this one. You almost never wait.

A LinkedList is n separate node objects at scattered addresses, and to reach the next element you have
to read the current node FIRST — because the address of the next one is the data in this one. The CPU
can't fetch ahead because it doesn't know where ahead is until the current load returns. That's a
serialised chain of dependent cache misses, which is the worst pattern this hardware has.

Then count the memory. ArrayList: about 4 bytes per element plus some slack. LinkedList: a node object
per element — 12-byte header plus prev, next and item — call it 24 bytes. Five times the memory, and
memory bandwidth is the scarce thing.

And the insert case has a hidden step people skip. `list.add(5000, x)` on a LinkedList is NOT O(1). The
rewiring is O(1); FINDING position 5000 is O(n), and it's the worst kind of O(n) — five thousand
dependent cache misses. The O(1) only exists if you already hold the node, and Java's List interface
never gives you one. Meanwhile the ArrayList version is System.arraycopy, which is a JVM intrinsic
compiled to a vectorised block move — many bytes per instruction, sequential, at memory bandwidth.
Shifting ten thousand references takes microseconds.

So the real comparison is a vectorised block move versus five thousand serialised pointer
dereferences. The one with the better Big-O loses, badly.

Where LinkedList's advantage is genuinely real is when you ALREADY have a reference to the position —
which in Java means Iterator.remove during a walk. And even there, removeIf on an ArrayList usually
wins in wall clock, because it does one compacting pass regardless of how many you remove.

Practically: ArrayList by default, ArrayDeque for anything queue- or stack-shaped, a Set the moment the
question is membership, and a primitive array if the elements are numbers — because boxing costs more
than the list structure ever will. I'd want a measured reason to pick LinkedList, and I've never had
one.'""",

"""8. THE CODE, LINE BY LINE

    // ── WHAT AN ARRAYLIST IS ────────────────────────────────────────────
    transient Object[] elementData;   // ONE contiguous array. 16 references per
    //                                   64-byte cache line with compressed oops.
    private int size;                 // used slots; capacity is elementData.length

    public void add(int index, E element) {
        System.arraycopy(elementData, index, elementData, index + 1, size - index);
    //  ^^^^^^^^^^^^^^^^ A JVM INTRINSIC. Not a loop — a vectorised block move, at
    //  memory bandwidth. Shifting 10,000 references is a few MICROSECONDS.
        elementData[index] = element;
        size++;
    }

    private Object[] grow(int minCapacity) {
        int newCapacity = oldCapacity + (oldCapacity >> 1);   // ← 1.5x
    //                                   ^^^^^^^^^^^^^^^^^ geometric growth is what
    //  makes add() AMORTISED O(1): total copying across n adds is O(n).
        return elementData = Arrays.copyOf(elementData, newCapacity);
    }

    // ── WHAT A LINKEDLIST IS ────────────────────────────────────────────
    private static class Node<E> { E item; Node<E> next; Node<E> prev; }
    //                             ^ 12-byte header + 3 refs = 24 bytes PER ELEMENT,
    //   allocated separately, at whatever address was free at the time.

    Node<E> node(int index) {
        if (index < (size >> 1)) {              // ← walks from the NEARER end
            Node<E> x = first;
            for (int i = 0; i < index; i++) x = x.next;
    //                                       ^^^^^^^^^^ EACH ITERATION MUST WAIT for
    //      the previous load: the address of x.next IS the data in x. The prefetcher
    //      cannot help. This is a serialised chain of cache misses.
            return x;
        } ...
    }

    // ── THE "O(1) INSERT" THAT ISN'T ────────────────────────────────────
    linked.add(5000, x);
    //         ^^^^ node(5000) walks 5,000 links FIRST. O(n) of the worst kind.
    //   Then the rewiring is genuinely O(1) — and irrelevant.
    array.add(5000, x);
    //         ^^^^ one arraycopy of the tail. O(n) that runs at memory bandwidth.

    // ── THE ACCIDENTAL O(n²) ────────────────────────────────────────────
    while (!list.isEmpty()) list.remove(0);
    //                           ^^^^^^^^^ shifts EVERYTHING left, every time.
    //   Draining 100,000 elements does ~5 billion element moves. Use clear(),
    //   iterate backwards, or use an ArrayDeque if it is really a queue.

    // ── THE BULK REMOVAL NOBODY USES ────────────────────────────────────
    list.removeIf(x -> x.isExpired());
    //   ^^^^^^^^ ONE compacting pass — it marks survivors and moves them once,
    //   O(n) TOTAL no matter how many match. An iterator loop calling remove() is
    //   O(n) PER REMOVAL, so O(nk). This is the fastest option available.

    // ── THE OVERLOAD THAT PICKS SILENTLY ────────────────────────────────
    List<Integer> l = new ArrayList<>(List.of(10, 20, 30));
    l.remove(1);                      // remove(int INDEX)  → removes 20
    l.remove(Integer.valueOf(10));    // remove(Object)     → removes the VALUE 10
    // ^ Both compile. The compiler prefers the primitive overload without warning.""",

"""9. THE TRACE — the same operation, two data structures, one cache

WALKING 1,000,000 ELEMENTS. Counting cache behaviour rather than operations:

    ARRAYLIST
    step  what the CPU does                                    memory stalls
    ---------------------------------------------------------------------------------
    1     fetch cache line at elementData[0]                    ONE miss
    2     elements 0..15 are already in that line               ZERO
    3     the prefetcher, having seen the pattern, has          ZERO — the line was
          ALREADY loaded the next line                          fetched during step 2
    ...   repeat
    ---------------------------------------------------------------------------------
    TOTAL ≈ 1,000,000 / 16 = 62,500 line fetches, nearly all PREFETCHED, so nearly
    all free. The loop runs at the speed of the ALU, not of memory.

    LINKEDLIST
    step  what the CPU does                                    memory stalls
    ---------------------------------------------------------------------------------
    1     fetch node[0]                                         ONE miss
    2     read node[0].next → now we know where node[1] is      —
    3     fetch node[1] — AND WE COULD NOT HAVE STARTED THIS     ONE miss, SERIALISED
          UNTIL STEP 2 RETURNED                                 behind step 1
    ...   repeat
    ---------------------------------------------------------------------------------
    TOTAL ≈ 1,000,000 dependent misses. Not "more work" — the SAME number of
    logical steps, each one waiting on the last, at ~100x the latency.

    SAME O(n). ONE RUNS AT MEMORY BANDWIDTH, THE OTHER AT MEMORY LATENCY. That distinction is invisible
    in Big-O and is the entire answer.

NOW THE INSERT AT THE MIDDLE — the case the textbook says LinkedList wins:

    operation                        LinkedList                   ArrayList
    ---------------------------------------------------------------------------------
    find position 500,000            500,000 DEPENDENT misses     0 — it is an index
    perform the insertion            rewire 2 pointers: O(1)      arraycopy 500,000
                                                                  refs: vectorised,
                                                                  sequential
    dominant cost                    THE WALK                     the copy
    which is faster in practice      —                            ARRAYLIST, by a lot
    ---------------------------------------------------------------------------------
    The O(1) that LinkedList is famous for is real. It is just attached to the half of the operation
    that costs nothing, while the half that costs everything is O(n) in the worst possible currency.

AND THE ONE CASE WHERE IT GOES THE OTHER WAY:

    removing 500,000 elements while iterating
    LinkedList + Iterator.remove()   O(1) each, O(n) total     ← algorithmically best
    ArrayList  + Iterator.remove()   O(n) each, O(nk) total    ← genuinely bad, avoid
    ArrayList  + removeIf(pred)      ONE compacting pass       ← usually fastest of all

    THE MIDDLE ROW IS THE REAL TRAP. It is the one people write, it is quadratic, and it is why
    "ArrayList is always faster" is not quite the right lesson. The right lesson is: match the API to
    the access pattern, and on an ArrayList that means `removeIf`.

WHAT PRODUCED WHAT:
    CONTIGUITY          produced the prefetching in trace 1 and the vectorised copy in trace 2.
    POINTER CHASING     produced the serialised miss chain — the single fact behind every row.
    THE List INTERFACE  produced "the O(1) you cannot reach", because it exposes indices, not nodes.""",

"""10. COMPLEXITY, THE MISTAKES, AND THE TAKEAWAY

                          ArrayList              LinkedList
    get(i)                O(1)                   O(n), from the nearer end
    add(x) at the end     amortised O(1)         O(1)
    add(i, x)             O(n) VECTORISED copy   O(n) WALK + O(1) rewire
    remove(i)             O(n) vectorised copy   O(n) walk + O(1) rewire
    Iterator.remove()     O(n) each              O(1) each
    removeIf(pred)        O(n) TOTAL, one pass   O(n)
    contains(x)           O(n)                   O(n)
    memory per element    ~4 bytes + ≤50% slack  ~24 bytes (a Node object)
    locality              contiguous, prefetched pointer chasing, unpredictable

THE #1 MISTAKE: choosing from the Big-O alone. It counts operations and assumes uniform memory cost;
the real spread between cache and main memory is about a hundred to one.

THE #2 MISTAKE: believing LinkedList's middle insert is O(1). Only the rewiring is; finding the
position is O(n) of dependent cache misses, and the List interface gives you no way to skip it.

THE #3 MISTAKE: `remove(0)` in a loop. Accidental O(n²) and very common.

THE #4 MISTAKE: an iterator-remove loop on an ArrayList. O(n) per removal. Use `removeIf`.

THE #5 MISTAKE: LinkedList as a queue. `ArrayDeque` is better on every axis.

THE #6 MISTAKE: not pre-sizing a list whose size you know. About 25 reallocations to reach 100,000.

THE #7 MISTAKE: `ArrayList<Integer>` for large numeric data. A boxed object and a pointer dereference
per element — a bigger cost than the list choice.

THE #8 MISTAKE: `list.contains` in a loop. You wanted a `HashSet`, and no list choice will save it.

THE #9 MISTAKE: benchmarking at a thousand elements. Everything fits in cache and the effect you are
measuring does not exist yet.

THE #10 MISTAKE: treating `Arrays.asList` and `subList` as copies. They are VIEWS that alias the
original and throw on structural modification.

THE #11 MISTAKE: assuming a large list frees memory when emptied. `remove` never shrinks the array;
`trimToSize()` does.

ONE-SENTENCE TAKEAWAY: the textbook comparison is algorithmically correct and practically wrong,
because an ArrayList is ONE CONTIGUOUS BLOCK that the prefetcher can run ahead of and that
`System.arraycopy` shifts as a vectorised block move, while a LinkedList is a chain of 24-byte nodes
whose next address IS the data in the current one — a serialised chain of dependent cache misses at
roughly a hundred times the latency — so even the middle-insertion case LinkedList supposedly owns is
an O(n) walk in the worst currency attached to an O(1) rewire that costs nothing; default to
ArrayList, use ArrayDeque for queues, `removeIf` for bulk removal, a Set for membership and a primitive
array for numbers, and require a measured reason before choosing LinkedList.""",
]


DEEP["0.1 + 0.2 != 0.3 — floating point, and when to use BigDecimal"] = [
"""1. THE GOAL IN PLAIN ENGLISH — why the computer gets simple arithmetic wrong

    System.out.println(0.1 + 0.2);   →   0.30000000000000004

This is not a bug in Java. Every language using standard hardware floating point prints the same thing:
Python, JavaScript, C, Go, Rust. It is not imprecision in the addition either. THE ADDITION IS EXACTLY
CORRECT — it is the two inputs that are not the numbers you wrote.

    A `double` STORES A NUMBER IN BINARY, as a sum of halves, quarters, eighths, sixteenths. Some
    decimal fractions simply do not fit that form, no matter how many bits you allow.

    0.1 IS ONE TENTH. Ten is 2 × 5. The 5 is the problem: binary can only build fractions out of powers
    of two, so one fifth — and therefore one tenth — is a REPEATING binary fraction, exactly as one
    third is a repeating decimal fraction.

    SO WHEN YOU WRITE `0.1`, JAVA STORES THE NEAREST DOUBLE, which is
    0.1000000000000000055511151231257827021181583404541015625 — close, and not equal. Same for 0.2.
    Add those two exact values and you get something that is not the nearest double to 0.3. The result
    prints its true value, and it looks absurd.

    AND HERE IS WHY IT AMBUSHES PEOPLE RATHER THAN BEING OBVIOUS: `System.out.println(0.1)` prints
    "0.1". Java prints the SHORTEST decimal that would round-trip back to the same double. So the error
    is invisible in every single value, and becomes visible only when two of them are combined. The
    representation was wrong from the moment you typed the literal; the arithmetic just revealed it.

THE EVERYDAY VERSION: you write one third as 0.333. Correct to three places. Add three of them and you
get 0.999, not 1. Nothing went wrong in the addition — the *writing down* was lossy, and adding made
the loss visible. Binary has the same problem, just with a different set of unlucky fractions, and one
tenth happens to be one of them.

TERMS AS THEY APPEAR:
- IEEE 754: the standard every CPU implements for floating point.
- MANTISSA (significand): the digits. EXPONENT: where the point goes.
- PRECISION: how many significant digits survive. For a double, about 15–17 decimal digits.
- ULP: "unit in the last place" — the gap between one representable double and the next.""",

"""2. THE INTUITION — a sliding window of significant digits

A `double` IS 64 BITS: 1 sign, 11 exponent, 52 mantissa. Read it as scientific notation in base two —
a fixed number of significant BINARY digits, times two to some power.

    THE CONSEQUENCE THAT EXPLAINS EVERYTHING ELSE: YOU ALWAYS HAVE ABOUT 15–17 SIGNIFICANT DECIMAL
    DIGITS, AND THEY SLIDE. Near 1.0 the gap between representable values is about 2.2e-16. Near
    1,000,000 it is about 1.2e-10. Near 1e17 the gap is larger than 1, so CONSECUTIVE INTEGERS STOP
    BEING REPRESENTABLE.

    THAT LAST POINT IS A REAL PRODUCTION BUG AND NOT A CURIOSITY. Above 2^53 (about 9.007e15) a double
    cannot represent every integer. Put a 19-digit database ID or a nanosecond timestamp through a
    double — which happens the moment JSON is parsed by JavaScript, where every number IS a double —
    and it comes back changed. Two distinct IDs can become equal.

WHICH FRACTIONS ARE EXACT? Exactly those whose denominator is a power of two. 0.5, 0.25, 0.75, 0.125.
Everything else — 0.1, 0.2, 0.3, 1/3 — is stored as the nearest representable neighbour.

    SO SOME "IMPOSSIBLE" RESULTS ARE ACTUALLY CORRECT: `0.5 + 0.25 == 0.75` is true, exactly, always.
    The rule is not "floating point is random". It is "the inputs were rounded on the way in".

THE THREE WAYS ERROR ACTUALLY HURTS, in increasing order of nastiness:

    ROUNDING, once. Half an ulp per operation. Almost always harmless.

    ACCUMULATION. Add 0.1 to a running total ten million times and the errors compound. The result
    drifts visibly — this is the one that turns up in financial batch jobs and in physics simulations.

    CATASTROPHIC CANCELLATION, the dangerous one. Subtract two nearly-equal numbers and the leading
    digits — the ones that were CORRECT — cancel out, promoting the trailing error digits to the front.
    1.0000000001 minus 1.0 keeps almost no significant digits at all. A calculation that was accurate
    to fifteen digits can become accurate to two in a single subtraction, and NOTHING SIGNALS IT.

AND THE PROPERTY YOU LOSE THAT MATTERS MOST TO PROGRAMMERS: FLOATING-POINT ADDITION IS NOT ASSOCIATIVE.
`(a + b) + c` and `a + (b + c)` can differ. Which is why summing an array in parallel gives a different
answer from summing it sequentially, and why a "flaky" test comparing sums may be reporting something
real.""",

"""3. THE MECHANISM — the bits, the special values, and BigDecimal

THE LAYOUT of a double:

    ┌─┬───────────┬────────────────────────────────────────────────────┐
    │S│  exponent │                  mantissa (52 bits)                │
    └─┴───────────┴────────────────────────────────────────────────────┘
     1     11                            52

    value = (-1)^S × 1.mantissa × 2^(exponent - 1023)

    THE LEADING 1 IS IMPLIED and not stored, which buys one free bit of precision — and it is why
    zero, which has no leading 1, needs a special encoding, and why there are TWO of them.

THE SPECIAL VALUES, all of which are representable and none of which behave normally:

    +0.0 and -0.0   Equal by `==`, and DISTINGUISHABLE: 1/0.0 is +Infinity, 1/-0.0 is -Infinity.
                    `Double.compare(-0.0, 0.0)` is -1 while `-0.0 == 0.0` is true. This split is
                    why a TreeMap and a HashMap can disagree about a key.
    Infinity        Overflow does not throw; it saturates. `1.0/0.0` is Infinity, not an exception.
                    Integer division by zero throws; floating point does not.
    NaN             `0.0/0.0`. NOT EQUAL TO ITSELF: `Double.NaN == Double.NaN` is FALSE. But
                    `Double.valueOf(NaN).equals(Double.valueOf(NaN))` is TRUE, and
                    `Double.compare(NaN, NaN)` is 0 — because collections need a total order.
                    THREE DIFFERENT ANSWERS TO "ARE THESE EQUAL", all deliberate.
    SUBNORMALS      Very small values near zero, with reduced precision, and on some hardware
                    dramatically slower to compute with.

`float` IS 32 BITS — 24 bits of significand, about 7 decimal digits. It is almost never the right
choice on a modern CPU: doubles are the same speed, and float's precision runs out fast. Use it for
memory-bound bulk data (graphics, ML tensors), not for scalar arithmetic.

BIGDECIMAL is a completely different machine: an arbitrary-precision INTEGER (`unscaledValue`) plus an
`int scale`, where the value is unscaledValue × 10^-scale.

    IT IS BASE TEN, so 0.1 is exact. It has no fixed precision, so it grows as needed. And it is
    roughly a hundred times slower than a double, with an object allocation per operation.

    THREE THINGS ABOUT IT THAT CATCH EVERYONE:

    `new BigDecimal(0.1)` IS WRONG. It faithfully converts the ALREADY-WRONG double, giving
    0.1000000000000000055511151231257827021181583404541015625. Use `new BigDecimal("0.1")` or
    `BigDecimal.valueOf(0.1)` (which routes through `Double.toString`).

    `equals` COMPARES SCALE. `new BigDecimal("2.0").equals(new BigDecimal("2.00"))` is FALSE. Use
    `compareTo(...) == 0`. This breaks HashSet and HashMap membership in a way that looks insane.

    DIVISION CAN THROW. `ONE.divide(new BigDecimal("3"))` throws ArithmeticException, because the exact
    result is non-terminating. You MUST supply a scale and a RoundingMode.""",

"""4. EDGE CASES AND FAILURE MODES

CASE 1 — `if (a == b)` ON DOUBLES. Almost always wrong. Two paths to the same mathematical value can
produce different doubles.

CASE 2 — A FIXED EPSILON. `Math.abs(a - b) < 0.0001` is fine near 1.0 and meaningless near 1e12, where
the gap between ADJACENT doubles already exceeds it. Comparison must be RELATIVE to magnitude, or in
ulps.

CASE 3 — MONEY IN A DOUBLE. The single most expensive instance of this whole topic. 0.1 is not
representable, so cents drift, and a reconciliation report is off by a few pennies across a million
rows with no single wrong transaction to point at.

CASE 4 — ACCUMULATING IN A LOOP. Summing 0.1 ten million times drifts measurably. Kahan (compensated)
summation recovers most of it by tracking the lost low-order part explicitly.

CASE 5 — CATASTROPHIC CANCELLATION. Subtracting nearly-equal values destroys significant digits
silently. The classic instance is the naive variance formula `E[x²] - E[x]²`, which can even return a
NEGATIVE variance; use Welford's algorithm.

CASE 6 — INTEGERS ABOVE 2^53. Not all representable. IDs, nanosecond timestamps, and anything that
passed through JSON parsed by JavaScript. Two distinct IDs can compare equal.

CASE 7 — `NaN` IN A SORT. `NaN == NaN` is false, so a comparator written with `<` and `>` violates
its own contract and `Arrays.sort` can throw "Comparison method violates its general contract" — or
silently produce garbage. `Double.compare` handles it.

CASE 8 — `NaN` IN A COLLECTION. `list.contains(Double.NaN)` is TRUE, because `contains` uses `equals`,
not `==`. The opposite of the `==` result, and both are correct.

CASE 9 — `-0.0` AS A KEY. `HashMap` distinguishes it from `0.0` (different bits, different hash);
`==` does not. Two structures, two answers.

CASE 10 — OVERFLOW TO INFINITY, SILENTLY. No exception, and `Infinity - Infinity` is NaN, which then
propagates through every subsequent operation and poisons the whole result.

CASE 11 — `new BigDecimal(double)`. Preserves the error you switched to BigDecimal to escape.

CASE 12 — `BigDecimal.equals` VS `compareTo`. 2.0 and 2.00 are not `equals`. Sets and map keys behave
bizarrely as a result.

CASE 13 — `float` FOR ACCUMULATION. About 7 digits. A float running total is visibly wrong after a few
million additions.

CASE 14 — ASSUMING ASSOCIATIVITY. `(a+b)+c != a+(b+c)`, so a parallel sum and a sequential sum legally
differ. Reordering an expression can change the result.""",

"""5. THE ALTERNATIVES — pick by domain, not by taste

FOR MONEY, TWO CORRECT ANSWERS AND ONE WRONG ONE:

    `long` OF MINOR UNITS — cents, or hundredths of a cent. Exact, fast, and it is what most payment
    systems actually do. The costs are that you must track the currency's scale yourself and watch for
    overflow, and that division still needs an explicit rounding decision.
    `BigDecimal` with an EXPLICIT scale and RoundingMode. Exact in base ten, handles arbitrary
    precision, self-documenting. About 100x slower, which is irrelevant for transactions and relevant
    for a billion-row aggregation.
    `double` — WRONG. Not "risky": wrong. The values you need are not representable.

FOR SCIENTIFIC AND STATISTICAL WORK, `double` is right, and the discipline is in the algorithms:
    KAHAN / NEUMAIER SUMMATION for long sums.
    WELFORD'S ALGORITHM for variance, instead of `E[x²] - E[x]²`.
    `Math.fma(a, b, c)` — a fused multiply-add, computed with a single rounding instead of two.
    `Math.hypot(x, y)` instead of `sqrt(x*x + y*y)`, which overflows for large inputs.
    `Math.log1p(x)` and `Math.expm1(x)` near zero, where `log(1+x)` loses everything to cancellation.
    REORDER SUMS SMALLEST-FIRST when you can; it materially reduces accumulated error.

FOR COMPARISON:
    `Double.compare(a, b)` for a total order that handles NaN and -0.0 correctly. Use it in every
    comparator, always.
    RELATIVE tolerance: `Math.abs(a-b) <= eps * Math.max(Math.abs(a), Math.abs(b))`.
    ULP-based: `Math.ulp(x)` for a tolerance expressed in representable steps.

FOR EXACT RATIONALS — `BigInteger` numerator and denominator, or `BigFraction` from Apache Commons
Numbers. Exact for everything expressible as a ratio, and the denominators grow without bound.

FOR REPRODUCIBILITY ACROSS PLATFORMS — `strictfp`, which forced strict IEEE semantics. As of Java 17 it
is the DEFAULT and the keyword is a no-op, because the x87 hardware quirk it existed for is gone.

WHAT TO SAY: "Doubles for measurement, `long` of minor units or BigDecimal for money, and `Double.compare`
in every comparator. And I would ask what the number MEANS before choosing — 'money' and 'a sensor
reading' want opposite answers, and the mistake is treating them the same."

""",

"""6. HOW TO WORK WITH FLOATING POINT — numbered steps

STEP 1 — ASK WHAT THE NUMBER IS. A measurement, or a COUNT of exact units? Money, invoice quantities
and share counts are counts and belong in `long` or BigDecimal. Temperatures, weights and durations are
measurements and belong in `double`.

STEP 2 — NEVER USE `==` ON DOUBLES. Compare with a tolerance, and make the tolerance RELATIVE to
magnitude.

STEP 3 — USE `Double.compare` IN EVERY COMPARATOR. It gives a total order over NaN and -0.0; hand-rolled
`<`/`>` comparators violate their contract and `Arrays.sort` will eventually tell you so.

STEP 4 — FOR MONEY, DECIDE THE UNIT ONCE AND WRITE IT DOWN. Minor units in a `long`, or BigDecimal with
a fixed scale. Never mix representations across a boundary.

STEP 5 — CONSTRUCT BIGDECIMAL FROM A STRING. `new BigDecimal("0.1")`, or `BigDecimal.valueOf(x)`. Never
`new BigDecimal(0.1)`.

STEP 6 — ALWAYS GIVE `divide` A SCALE AND A RoundingMode. Otherwise it throws on any non-terminating
result, usually in production, usually on a divide by three.

STEP 7 — COMPARE BIGDECIMALS WITH `compareTo(...) == 0`. `equals` includes the scale, so 2.0 and 2.00
are not equal and set membership behaves absurdly.

STEP 8 — FOR LONG SUMS, USE COMPENSATED SUMMATION or sum smallest-first. Naive accumulation drifts.

STEP 9 — WATCH FOR SUBTRACTION OF NEARLY-EQUAL VALUES. That is where accuracy dies, and nothing warns.
Look for a mathematically equivalent formula that avoids it.

STEP 10 — CHECK FOR OVERFLOW AND NaN AT BOUNDARIES. They propagate silently through everything
downstream. `Double.isFinite` at the edges of a computation.

STEP 11 — KEEP LARGE IDS OUT OF DOUBLES. Above 2^53 not every integer exists. Serialise them as
strings, especially across JSON.

STEP 12 — WHEN A TEST IS FLAKY ON A SUM, SUSPECT ORDERING BEFORE SUSPECTING THE TEST. Addition is not
associative; a parallel sum legitimately differs from a sequential one.""",

"""7. THE ANSWER IN PLAIN LANGUAGE — what you would say out loud

'0.1 + 0.2 gives 0.30000000000000004, and it's not a Java bug — every language on standard hardware
prints that. And the addition isn't imprecise either. The addition is exactly correct. It's the two
INPUTS that aren't the numbers I wrote.

A double stores a number in binary — as a sum of halves, quarters, eighths. One tenth is 1/10, and 10
is 2 times 5. The 5 is the problem: binary can only build fractions from powers of two, so one tenth is
a repeating binary fraction, exactly the way one third is a repeating decimal. So when I write 0.1,
what gets stored is the nearest double, which is 0.1000000000000000055 and change.

The reason it ambushes people rather than being obvious is that println(0.1) prints "0.1". Java prints
the shortest decimal that round-trips back to the same double, so the error is invisible in every
individual value and only shows up when you combine two. The representation was already wrong when I
typed the literal — the arithmetic just revealed it.

The way I'd frame the whole topic: a double gives you about 15 to 17 significant decimal digits, and
they SLIDE with magnitude. Near 1.0 the gap between representable values is about 2e-16. Near 1e17 the
gap is bigger than 1 — so consecutive integers stop existing. That's a real production bug, not a
curiosity: above 2^53 you can't represent every integer, so a 19-digit database ID or a nanosecond
timestamp through a double comes back changed. Two distinct IDs can become equal. It happens every time
JSON gets parsed by JavaScript, where every number IS a double.

Error hurts in three escalating ways. Rounding once, half an ulp, harmless. Accumulation — add 0.1 ten
million times and it visibly drifts. And the dangerous one, catastrophic cancellation: subtract two
nearly-equal numbers and the leading digits, the CORRECT ones, cancel, which promotes the trailing
error digits to the front. A calculation accurate to fifteen digits can drop to two in one subtraction,
and nothing signals it. The classic case is the naive variance formula, E[x²] minus E[x]², which can
return a negative variance.

Also worth knowing: floating-point addition is not ASSOCIATIVE. (a+b)+c can differ from a+(b+c). Which
is why a parallel sum and a sequential sum legitimately disagree, and why a flaky test on a sum might
be telling you something real.

Practically, I'd decide by asking what the number IS. A measurement, or a count of exact units? Money
is a count — it belongs in a long of minor units, or BigDecimal with an explicit scale and RoundingMode.
Not a double; that's not risky, it's wrong, because the values aren't representable. Measurements
belong in doubles, and then the discipline is in the algorithms — Kahan summation, Welford for
variance, hypot instead of sqrt of squares.

And two BigDecimal traps: `new BigDecimal(0.1)` faithfully preserves the wrong double, so always
construct from a string. And `equals` compares SCALE, so 2.0 and 2.00 aren't equal and set membership
goes strange — use compareTo == 0.'""",

"""8. THE CODE, LINE BY LINE

    // ── WHAT IS ACTUALLY STORED ─────────────────────────────────────────
    System.out.println(0.1);
    // prints: 0.1
    // ^ A LIE OF OMISSION. Java prints the SHORTEST decimal that round-trips
    //   back to this double, which is why the error is invisible per-value.
    System.out.println(new BigDecimal(0.1));
    // prints: 0.1000000000000000055511151231257827021181583404541015625
    // ^ THE TRUTH. new BigDecimal(double) converts the double faithfully, so it
    //   is the wrong constructor for input AND the perfect one for inspection.

    System.out.println(0.1 + 0.2);        // 0.30000000000000004
    System.out.println(0.1 + 0.2 == 0.3); // false
    System.out.println(0.5 + 0.25 == 0.75); // TRUE — denominators are powers of 2

    // ── THE COMPARISON THAT IS ALSO WRONG ───────────────────────────────
    if (Math.abs(a - b) < 0.0001) { ... }
    //                     ^^^^^^ fine near 1.0. MEANINGLESS near 1e12, where the
    //   gap between ADJACENT doubles already exceeds it — so this is always true.
    if (Math.abs(a - b) <= 1e-9 * Math.max(Math.abs(a), Math.abs(b))) { ... }
    //                           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ RELATIVE to
    //   magnitude. Scales correctly across the whole range.

    // ── ABOVE 2^53, INTEGERS STOP EXISTING ──────────────────────────────
    long id = 9007199254740993L;          // 2^53 + 1
    System.out.println((long)(double) id);// 9007199254740992  ← CHANGED
    // ^ The double simply has no bit pattern for that integer. This is why IDs
    //   must be serialised as STRINGS in JSON: JavaScript numbers ARE doubles.

    // ── CATASTROPHIC CANCELLATION: 15 digits down to 2 ──────────────────
    double a = 1.0000000001, b = 1.0;
    System.out.println(a - b);            // 1.000000082740371E-10
    // ^ The correct answer is 1e-10. We kept about TWO significant digits, because
    //   the leading digits — the accurate ones — cancelled, promoting the error.
    //   Nothing warned. This is how a good calculation quietly becomes a bad one.

    // ── ACCUMULATION, AND THE FIX ───────────────────────────────────────
    double sum = 0;
    for (int i = 0; i < 10_000_000; i++) sum += 0.1;
    // sum ≈ 999999.9998389754, not 1000000.0
    double s = 0, c = 0;                  // Kahan: track the lost low-order part
    for (int i = 0; i < 10_000_000; i++) {
        double y = 0.1 - c, t = s + y;
        c = (t - s) - y;                  // ← what the addition DROPPED
        s = t;
    }                                     // s is correct to the last digit

    // ── NaN: THREE ANSWERS TO ONE QUESTION, ALL CORRECT ─────────────────
    double n = 0.0 / 0.0;
    System.out.println(n == n);                       // false — IEEE 754 says so
    System.out.println(Double.valueOf(n).equals(n));  // true  — collections need
    System.out.println(Double.compare(n, n));         // 0     — a total order
    System.out.println(List.of(n).contains(n));       // TRUE — contains uses equals

    // ── MONEY ───────────────────────────────────────────────────────────
    // double  total = 0.1 + 0.2;                     ← WRONG. Not risky. Wrong.
    long cents = 10 + 20;                             // exact, fast, what payment
    //                                                   systems actually do
    var big = new BigDecimal("0.1").add(new BigDecimal("0.2"));  // exactly 0.3
    // new BigDecimal(0.1)  ← keeps the error you switched to BigDecimal to escape
    new BigDecimal("2.0").equals(new BigDecimal("2.00"));   // FALSE — scale differs
    new BigDecimal("2.0").compareTo(new BigDecimal("2.00")); // 0 — use THIS
    BigDecimal.ONE.divide(new BigDecimal("3"));       // THROWS ArithmeticException
    BigDecimal.ONE.divide(new BigDecimal("3"), 10, RoundingMode.HALF_UP);  // fine""",

"""9. THE TRACE — following 0.1 + 0.2 through the hardware

STEP 1 — THE LITERAL `0.1` IS PARSED. The compiler finds the nearest double to one tenth:

    exact value wanted:  0.1
    nearest double:      0.1000000000000000055511151231257827021181583404541015625
    error introduced:    +5.55e-18            ← ALREADY WRONG, BEFORE ANY ARITHMETIC

STEP 2 — THE LITERAL `0.2` IS PARSED:

    nearest double:      0.200000000000000011102230246251565404236316680908203125
    error introduced:    +1.11e-17

STEP 3 — THE ADDITION. The CPU adds the two stored values EXACTLY, then rounds the exact sum to the
nearest double:

    exact sum of the two stored values:  0.3000000000000000166533453693773481063544750213623046875
    nearest double to that:              0.3000000000000000444089209850062616169452667236328125
    the double nearest to 0.3:           0.299999999999999988897769753748434595763683319091796875

    THE TWO ARE DIFFERENT DOUBLES. So `==` is false, correctly.

STEP 4 — PRINTING. `Double.toString` emits the shortest decimal that round-trips:

    for 0.1 alone       → "0.1"                    ← the error is HIDDEN
    for the sum         → "0.30000000000000004"    ← the error is now large enough
                                                      that "0.3" would round-trip to
                                                      a DIFFERENT double, so it must
                                                      be shown

    THAT IS THE WHOLE MYSTERY. Nothing changed about how wrong the values were. The printer simply
    stopped being able to hide it. Every double you have ever printed had this error; you only see it
    when it crosses the round-trip threshold.

NOW ACCUMULATION — adding 0.1 ten million times:

    additions        running sum                     absolute error
    ---------------------------------------------------------------------------------
    10               0.9999999999999999              1.1e-16
    1,000            99.9999999999986                1.4e-12
    1,000,000        100000.00000133288              1.3e-6
    10,000,000       999999.9998389754               1.6e-4      ← visible in a report

    THE ERROR GROWS FASTER THAN THE NUMBER OF ADDITIONS, because each partial sum is larger, so each
    rounding is coarser — an ulp near 100,000 is much bigger than an ulp near 1. Kahan summation
    tracks the dropped low-order part explicitly and recovers essentially all of it.

AND CANCELLATION — the failure that produces no symptom at all:

    operation                        significant digits remaining
    ---------------------------------------------------------------------------------
    a = 1.0000000001                 ~16, correct
    b = 1.0                          exact
    a - b                            ~2 correct digits out of 16
    (a - b) * 1e10                   still ~2 — the loss is PERMANENT

    NOTHING THREW. NOTHING WARNED. The subtraction was performed exactly as specified; it is the
    INFORMATION that was lost, and no runtime check can detect that. This is the reason numerical code
    is rewritten around cancellation — `log1p`, `expm1`, `hypot`, Welford — rather than checked for it.

WHAT PRODUCED WHAT:
    BINARY FRACTIONS         produced steps 1 and 2 — the error exists before any arithmetic runs.
    ROUND-TO-NEAREST         produced step 3, which is the only step that is genuinely "the hardware".
    SHORTEST ROUND-TRIP      produced step 4, and therefore produced the surprise.
    SLIDING PRECISION        produced the accumulation table: the same operation costs more as the
                             magnitude grows.""",

"""10. COMPLEXITY, THE MISTAKES, AND THE TAKEAWAY

    double: 64 bits, 52-bit mantissa, ~15–17 significant decimal digits, range ~±1.8e308.
    float:  32 bits, 23-bit mantissa, ~7 digits. Rarely the right scalar choice.
    Exactly representable: fractions whose denominator is a power of two. 0.5, 0.25, 0.125.
    Every integer up to 2^53 (~9.007e15) is exact; above that, they are not.
    ULP near 1.0: ~2.2e-16. Near 1e6: ~1.2e-10. Near 1e17: greater than 1.
    BigDecimal: exact in base ten, arbitrary precision, roughly 100x slower with an allocation per
    operation.
    Arithmetic is COMMUTATIVE but NOT ASSOCIATIVE and NOT DISTRIBUTIVE.

THE #1 MISTAKE: `==` on doubles. Use a RELATIVE tolerance, or `Double.compare` for ordering.

THE #2 MISTAKE: money in a double. Not risky — wrong. `long` of minor units, or BigDecimal.

THE #3 MISTAKE: a FIXED epsilon. Meaningless once the magnitude exceeds it; comparison must scale.

THE #4 MISTAKE: `new BigDecimal(0.1)`. Faithfully preserves the error you were escaping. Use the String
constructor or `BigDecimal.valueOf`.

THE #5 MISTAKE: `BigDecimal.equals` for value comparison. It includes SCALE, so 2.0 and 2.00 differ and
set membership behaves absurdly. `compareTo(...) == 0`.

THE #6 MISTAKE: `divide` with no scale and RoundingMode. Throws on any non-terminating result.

THE #7 MISTAKE: hand-rolled `<`/`>` comparators on doubles. They violate the comparator contract on
NaN, and `Arrays.sort` will eventually say so out loud.

THE #8 MISTAKE: large IDs through a double. Above 2^53 not every integer exists; two distinct IDs can
become equal. Serialise as strings.

THE #9 MISTAKE: naive accumulation over millions of values. Use compensated summation, or sum
smallest-first.

THE #10 MISTAKE: subtracting nearly-equal values without noticing. Catastrophic cancellation destroys
significant digits with no signal whatsoever.

THE #11 MISTAKE: assuming overflow throws. It saturates to Infinity, `Infinity - Infinity` is NaN, and
the NaN then poisons everything downstream in silence.

THE #12 MISTAKE: assuming associativity. A parallel sum and a sequential sum legally differ, so this
can present as a flaky test that is actually reporting something true.

ONE-SENTENCE TAKEAWAY: a double stores binary fractions, so any decimal whose denominator is not a
power of two — 0.1 included — is rounded THE MOMENT YOU TYPE THE LITERAL, and `Double.toString` hides
that by printing the shortest round-tripping decimal until an addition makes it too large to hide;
the practical consequences are that `==` is unusable, that a fixed epsilon is wrong at scale, that
integers above 2^53 do not all exist, that long accumulations drift and near-equal subtractions destroy
accuracy with no signal at all, and that money — being a COUNT of exact units rather than a measurement
— belongs in a `long` of minor units or a BigDecimal built from a String and compared with `compareTo`,
never in a double.""",
]
