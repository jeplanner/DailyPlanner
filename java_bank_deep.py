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


DEEP["ExecutorService — the four ways a thread pool bites you"] = [
"""1. THE GOAL IN PLAIN ENGLISH — why nobody writes `new Thread()` anymore

Creating a thread is a system call. The OS allocates a stack, registers a scheduling entity, and hands
it back. It costs on the order of a hundred microseconds and about a megabyte of reserved address
space. Do it per request and two things happen: you pay that cost on every request, and — far worse —
NOTHING BOUNDS HOW MANY EXIST. A traffic spike creates ten thousand threads, the machine spends all its
time context-switching, and the failure looks like the machine died rather than like you were busy.

    AN ExecutorService IS A FIXED CREW PLUS A QUEUE. You hand it tasks; a bounded set of threads takes
    them one at a time; and when they are all busy, the work WAITS instead of spawning more workers.

    THE QUEUE IS THE POINT, NOT THE THREADS. Reusing threads saves creation cost, which is nice. But
    the reason a pool exists is that it gives you a place to put excess work and a decision about what
    to do when that place is full. THAT DECISION IS YOUR OVERLOAD BEHAVIOUR, and most outages involving
    thread pools are really outages of that decision being made by default.

THE EVERYDAY VERSION: a coffee shop with four baristas. When fifty people arrive, you do not hire
forty-six baristas — you form a queue. And the interesting design question is not how fast the baristas
work; it is what happens when the queue reaches the door. Do you let it grow into the street? Turn
people away? Ask the person at the till to make their own coffee? EVERY ONE OF THOSE IS A CONFIGURED
POLICY, and picking none means picking one by accident.

TERMS AS THEY APPEAR:
- CORE POOL SIZE: threads kept alive even when idle.
- MAXIMUM POOL SIZE: the ceiling — but see section 2, because it does not mean what you think.
- WORK QUEUE: where tasks wait.
- REJECTION POLICY: what happens when the queue is full AND the pool is at maximum.
- `execute` vs `submit`: the difference decides whether your exceptions are visible or invisible.""",

"""2. THE INTUITION — the sizing rule that surprises everyone

`ThreadPoolExecutor` HAS SEVEN CONSTRUCTOR PARAMETERS, and the interaction between three of them is the
thing to actually understand:

    corePoolSize, maximumPoolSize, keepAliveTime, unit, workQueue, threadFactory, rejectionHandler

THE ALGORITHM WHEN A TASK ARRIVES, in this exact order:

    1. FEWER THAN corePoolSize THREADS?  → create a new thread. Even if others are idle.
    2. OTHERWISE, TRY TO QUEUE IT.        → if the queue accepts it, done.
    3. QUEUE FULL?                        → create a thread, up to maximumPoolSize.
    4. AT MAXIMUM TOO?                    → REJECT, via the rejection policy.

    NOW READ STEP 2 AND STEP 3 TOGETHER. THREADS BEYOND THE CORE ARE ONLY CREATED WHEN THE QUEUE IS
    FULL. Which means:

    WITH AN UNBOUNDED QUEUE, maximumPoolSize IS NEVER REACHED. Never. The queue never fills, so step 3
    never happens, so the pool never grows past core. You can set maximum to a thousand and it is
    decoration.

    THIS IS EXACTLY WHAT `Executors.newFixedThreadPool(n)` DOES. It uses a `LinkedBlockingQueue` with
    no capacity limit. So under sustained overload the pool does not grow, does not reject, and does
    not fail — IT QUEUES, FOREVER, until the heap is gone. The OutOfMemoryError names the queue, and
    the actual cause was that the system had no way to say "no".

    AND `Executors.newCachedThreadPool()` FAILS THE OPPOSITE WAY: a `SynchronousQueue`, which has zero
    capacity, so step 2 always fails and step 3 always fires — with a maximum of `Integer.MAX_VALUE`.
    Unbounded THREADS instead of an unbounded queue.

    BOTH CONVENIENCE FACTORIES ARE UNBOUNDED IN ONE DIRECTION. That is why serious codebases construct
    `ThreadPoolExecutor` explicitly, and why Google's Java style guide bans the `Executors` factories
    outright.

HOW MANY THREADS, then? Two regimes, and confusing them is the second most common mistake:

    CPU-BOUND WORK: threads ≈ number of cores. More threads do not create more cores; they add context
    switching and cache pressure to the same amount of work.
    I/O-BOUND WORK: threads ≈ cores × (1 + waitTime/computeTime). A task that waits 90% of the time
    supports about ten threads per core. THE RATIO IS THE THING TO MEASURE, and it is usually easier to
    measure than people expect: it is just the fraction of time the thread is not runnable.

AND THE REJECTION POLICY IS YOUR BACKPRESSURE DESIGN:

    AbortPolicy (default)  throws RejectedExecutionException. Honest, and requires the caller to cope.
    CallerRunsPolicy       THE CALLING THREAD RUNS THE TASK ITSELF. Which means the producer stops
                           producing while it does so. This is elegant: overload automatically slows
                           the source, with no signalling protocol at all.
    DiscardPolicy          silently drops. Right for metrics samples, catastrophic for orders.
    DiscardOldestPolicy    drops the oldest queued task. Right for "latest value wins" feeds.""",

"""3. THE MECHANISM — execute vs submit, shutdown, and the scheduled trap

THE EXCEPTION DIFFERENCE, which is the single most under-known thing here:

    execute(Runnable)          an uncaught exception KILLS THE THREAD, the pool quietly replaces it,
                               and the exception goes to the thread's UncaughtExceptionHandler — which
                               by default prints to stderr. VISIBLE, if anyone is reading stderr.
    submit(Runnable|Callable)  the exception is CAUGHT AND STORED IN THE Future. Nothing is printed.
                               Nothing is logged. The thread survives. IF YOU NEVER CALL `get()`, THE
                               EXCEPTION SIMPLY DOES NOT EXIST as far as your system is concerned.

    THAT IS WHY WORK "SILENTLY STOPS HAPPENING". Everyone writes `submit`, nobody keeps the Future, and
    every failure is swallowed by design. THE FIX IS A try/catch AROUND THE WHOLE TASK BODY, or a
    subclass overriding `afterExecute`, or `CompletableFuture` with `whenComplete`.

SHUTDOWN, and the three methods that get confused:

    shutdown()               stop accepting new tasks; finish everything already submitted. Returns
                             IMMEDIATELY — it does not wait.
    shutdownNow()            stop accepting, INTERRUPT running threads, and RETURN the queued tasks
                             that never started. Interruption only works if the task checks for it.
    awaitTermination(t, u)   the actual wait. Returns false on timeout.
    THE CORRECT SEQUENCE IS ALL THREE: shutdown, await, and if that times out, shutdownNow and await
    again.

    AND THE DEFAULT THREADS ARE NON-DAEMON, so a pool you forget to shut down KEEPS THE JVM ALIVE. The
    program finishes `main` and simply does not exit. On Java 19+, `ExecutorService` is `AutoCloseable`,
    so try-with-resources does the whole dance for you.

THE SCHEDULED-EXECUTOR TRAP, which deserves its own paragraph because it is silent and total:

    IF A TASK SUBMITTED TO `scheduleAtFixedRate` THROWS, THE SCHEDULE IS CANCELLED. Not skipped — 
    CANCELLED. It never runs again, for the life of the process, and nothing is logged. A health check,
    a cache refresh, a metrics flush: one transient exception at 3am and the job is dead until the next
    deploy. ALWAYS WRAP A SCHEDULED TASK BODY IN try/catch(Throwable).

    `scheduleAtFixedRate` vs `scheduleWithFixedDelay`: the first measures from START to start, so if a
    run takes longer than the period, runs bunch up back to back. The second measures from END to
    start, so there is always a real gap. FOR ANYTHING THAT TALKS TO A STRUGGLING DOWNSTREAM SERVICE,
    fixed DELAY is the safer default.

THREAD FACTORY. Default thread names are `pool-1-thread-3`, which tells you nothing in a thread dump at
2am. A three-line factory that names threads after their purpose is the cheapest observability
improvement available in Java.""",

"""4. EDGE CASES AND FAILURE MODES

CASE 1 — `newFixedThreadPool` UNDER SUSTAINED OVERLOAD. Unbounded queue, so it never rejects; the heap
fills with queued Runnables and the OOM names the queue rather than the cause.

CASE 2 — `newCachedThreadPool` UNDER SUSTAINED OVERLOAD. Unbounded threads. Same outcome by the
opposite route.

CASE 3 — MAXIMUM POOL SIZE THAT DOES NOTHING. Any unbounded queue makes it unreachable. People set it,
watch it never be used, and conclude the pool is broken.

CASE 4 — `submit` WITH AN IGNORED FUTURE. Every exception silently captured. The task stops working and
nothing anywhere records it.

CASE 5 — A THROWING TASK ON `scheduleAtFixedRate`. The schedule is cancelled permanently and silently.

CASE 6 — FORGETTING TO SHUT DOWN. Non-daemon threads keep the JVM alive; the process hangs after `main`
returns with no error at all.

CASE 7 — THREAD-POOL DEADLOCK. A task submits another task to the SAME bounded pool and blocks on its
`Future.get()`. With a single-threaded pool this deadlocks on the first try, guaranteed. With a
ten-thread pool it deadlocks under load, which is worse because it passes testing.

CASE 8 — BLOCKING WORK ON THE COMMON ForkJoinPool. Parallel streams and no-executor `CompletableFuture`
calls share `ForkJoinPool.commonPool()`, sized to cores minus one. One blocking call there stalls
unrelated code across the whole JVM.

CASE 9 — ThreadLocal LEAKS IN A POOLED THREAD. The thread never dies, so the value is never cleared,
and it holds whatever it references forever. Always `remove()` in a finally.

CASE 10 — INTERRUPTION SWALLOWED. `catch (InterruptedException e) { }` destroys the interrupt flag, so
`shutdownNow` cannot stop the task. Either rethrow, or restore with
`Thread.currentThread().interrupt()`.

CASE 11 — `invokeAll` BLOCKS UNTIL EVERY TASK COMPLETES, including the slow one. There is a timeout
overload and it is nearly always the one you want.

CASE 12 — DEFAULT THREAD NAMES. `pool-2-thread-7` in a thread dump identifies nothing.

CASE 13 — ONE POOL FOR EVERYTHING. Slow database calls and fast cache lookups sharing a pool means the
slow work starves the fast work. Separate pools are BULKHEADS, and they are how you stop one dependency
from taking down every endpoint.""",

"""5. THE ALTERNATIVES — and which pool for which job

CONSTRUCT `ThreadPoolExecutor` DIRECTLY. The recommended default, because it forces you to state the
queue bound and the rejection policy — which are the two decisions that matter and the two the
convenience factories make for you badly:

    new ThreadPoolExecutor(8, 8, 0L, MILLISECONDS,
        new ArrayBlockingQueue<>(1000),          // BOUNDED. This is the whole point.
        namedFactory("http-worker"),
        new ThreadPoolExecutor.CallerRunsPolicy())

`Executors` FACTORIES — know what each really is:
    newFixedThreadPool(n)          fixed threads, UNBOUNDED queue
    newCachedThreadPool()          UNBOUNDED threads, zero-capacity queue, 60s idle timeout
    newSingleThreadExecutor()      one thread, unbounded queue — genuinely useful for serialising
                                   access to something non-thread-safe
    newScheduledThreadPool(n)      timers, with the cancel-on-throw trap above
    newWorkStealingPool()          a ForkJoinPool. Good for recursive divide-and-conquer, not for
                                   independent blocking I/O
    newVirtualThreadPerTaskExecutor()  Java 21. Not a pool at all — see below.

VIRTUAL THREADS (Java 21) for I/O-BOUND work. They change the answer to this whole topic: threads
become cheap, so you stop pooling. BUT THE POOL WAS ALSO YOUR RATE LIMITER — that `ArrayBlockingQueue`
of 1000 and those 8 threads were bounding how much load reached your database. Replace them with
unbounded virtual threads and you must add a `Semaphore` explicitly, or the limit simply disappears.

`CompletableFuture` FOR COMPOSITION — chaining, combining, timeouts, error recovery. ALWAYS PASS AN
EXECUTOR; the no-executor overloads use the common pool.

FORKJOINPOOL for recursive splitting, where work-stealing genuinely helps. Not for independent blocking
tasks.

A MESSAGE QUEUE — Kafka, SQS, RabbitMQ — when the work must survive a restart. An in-memory queue is a
thread pool's queue; a broker's queue is durable, observable, and rate-limitable from outside the
process. THE MOMENT "we lost the queued work when the pod restarted" MATTERS, you wanted a broker.

A SEMAPHORE, when what you actually need is a CONCURRENCY LIMIT rather than a set of threads. Often
clearer than a pool, and it composes with virtual threads.

WHAT TO SAY: "I would construct ThreadPoolExecutor explicitly with a bounded queue and CallerRunsPolicy
so overload becomes backpressure rather than an OOM, size it from the wait-to-compute ratio, name the
threads, and use separate pools as bulkheads so a slow dependency cannot starve a fast one."

""",

"""6. HOW TO CONFIGURE A POOL — numbered steps

STEP 1 — CLASSIFY THE WORK. CPU-bound or I/O-bound? The sizing rules are completely different and
everything else follows from this.

STEP 2 — SIZE IT. CPU-bound: about the core count. I/O-bound: cores × (1 + wait/compute). Measure the
ratio rather than guessing it.

STEP 3 — BOUND THE QUEUE. Always. An unbounded queue converts overload into an OutOfMemoryError, and it
removes maximumPoolSize from the design at the same time.

STEP 4 — CHOOSE THE REJECTION POLICY DELIBERATELY. `CallerRunsPolicy` for natural backpressure,
`AbortPolicy` when the caller can shed load properly, `DiscardOldest` for latest-value-wins feeds.

STEP 5 — NAME THE THREADS. A three-line ThreadFactory, and every future thread dump becomes readable.

STEP 6 — WRAP EVERY TASK BODY IN try/catch(Throwable). Especially scheduled tasks, where an exception
cancels the schedule forever.

STEP 7 — DO NOT IGNORE FUTURES FROM `submit`. Either handle them, or use `execute`, or use
`CompletableFuture` with `whenComplete`.

STEP 8 — SHUT DOWN PROPERLY: `shutdown`, `awaitTermination`, then `shutdownNow` and await again. Or
try-with-resources on Java 19+.

STEP 9 — USE SEPARATE POOLS AS BULKHEADS. One per downstream dependency, so a slow one cannot starve
the rest.

STEP 10 — NEVER BLOCK ON A TASK IN THE SAME BOUNDED POOL. That is the thread-pool deadlock, and it
passes testing before it fails in production.

STEP 11 — CLEAR ThreadLocals IN A FINALLY. Pooled threads never die, so nothing else will.

STEP 12 — MONITOR QUEUE DEPTH, ACTIVE COUNT AND REJECTION COUNT. `ThreadPoolExecutor` exposes all
three. Queue depth trending upward is the earliest warning you will get, and it arrives long before
latency moves.""",

"""7. THE ANSWER IN PLAIN LANGUAGE — what you would say out loud

'Creating a thread is a syscall — about a megabyte of reserved stack and a hundred microseconds. Doing
it per request costs that every time, and worse, nothing bounds how many exist. A spike creates ten
thousand threads and the machine spends all its time context-switching, so the failure looks like the
box died rather than like you were busy.

A pool is a fixed crew plus a queue. But I'd say the QUEUE is the point, not the threads. Reusing
threads saves creation cost, which is nice. The reason a pool exists is that it gives you somewhere to
put excess work and a decision about what to do when that place is full — and that decision IS your
overload behaviour. Most thread-pool outages are really that decision being made by default.

The thing that surprises everyone is the sizing algorithm. When a task arrives: under core size, make
a thread. Otherwise try to QUEUE it. Only if the queue is FULL do you create threads up to the maximum.
Read those together and it follows that with an unbounded queue, maximumPoolSize is never reached. Ever.
You can set it to a thousand and it's decoration.

Which is exactly what newFixedThreadPool does — a LinkedBlockingQueue with no capacity. So under
sustained overload it doesn't grow, doesn't reject, doesn't fail. It queues until the heap is gone, and
the OOM names the queue while the actual cause was that the system had no way to say no. And
newCachedThreadPool fails the opposite way: a zero-capacity SynchronousQueue with a maximum of
Integer.MAX_VALUE, so unbounded THREADS instead of an unbounded queue. Both convenience factories are
unbounded in one direction, which is why I'd construct ThreadPoolExecutor explicitly.

For sizing: CPU-bound is roughly the core count — more threads don't create more cores. I/O-bound is
cores times one plus the wait-to-compute ratio, so a task waiting 90% of the time supports about ten
threads per core.

And the rejection policy is where the backpressure design lives. CallerRunsPolicy is the elegant one:
the CALLING thread runs the task itself, so the producer stops producing while it does. Overload
automatically slows the source with no signalling protocol at all.

Two things I'd flag that bite people constantly. First, submit versus execute: submit CAPTURES the
exception in the Future. Nothing is printed, nothing is logged, and if you never call get() the
exception effectively doesn't exist. That's why work "silently stops happening" — everyone writes
submit and nobody keeps the Future.

Second, scheduleAtFixedRate: if the task throws, the schedule is CANCELLED. Not skipped — cancelled
permanently, silently, for the life of the process. One transient exception at 3am and your cache
refresh is dead until the next deploy. Always wrap a scheduled body in catch Throwable.

Then: bound the queue, name the threads so a thread dump is readable, use separate pools as bulkheads
so a slow dependency can't starve a fast one, and never block on a Future from the same bounded pool —
that one deadlocks under load after passing every test.'""",

"""8. THE CODE, LINE BY LINE

    // ── WHY maximumPoolSize IS OFTEN DECORATION ─────────────────────────
    new ThreadPoolExecutor(2, 100, 60L, SECONDS, new LinkedBlockingQueue<>());
    //                        ^^^ NEVER REACHED. The queue is unbounded, so it always
    //   accepts, so the "queue is full" branch that creates threads 3..100 never runs.
    //   This is a 2-thread pool with a 100 written on it.

    Executors.newFixedThreadPool(8);
    // ^ EXACTLY THE ABOVE. LinkedBlockingQueue with no capacity. Under sustained
    //   overload: no growth, no rejection, no failure — it queues until the heap is
    //   gone, and the OOM stack trace names the queue rather than the cause.

    Executors.newCachedThreadPool();
    // ^ SynchronousQueue (capacity ZERO) + maximumPoolSize = Integer.MAX_VALUE.
    //   Every task fails to queue, so every task creates a thread. Unbounded THREADS.

    // ── THE POOL YOU SHOULD ACTUALLY WRITE ──────────────────────────────
    var pool = new ThreadPoolExecutor(
        8, 8,                              // core == max: predictable
        0L, TimeUnit.MILLISECONDS,
        new ArrayBlockingQueue<>(1000),    // ← BOUNDED. The single most important line.
        r -> { var t = new Thread(r, "http-worker"); t.setDaemon(true); return t; },
    //       ^^^^^^^^^^^^^^^^^^^^^^^^^ named threads. Three lines, and every future
    //       thread dump becomes readable at 2am.
        new ThreadPoolExecutor.CallerRunsPolicy());
    //      ^^^^^^^^^^^^^^^^^ THE CALLER RUNS IT. So the producer stops producing while
    //      it does. Overload throttles the source automatically — backpressure with no
    //      signalling protocol.

    // ── THE EXCEPTION THAT DOES NOT EXIST ───────────────────────────────
    pool.submit(() -> { throw new IllegalStateException("boom"); });
    //   ^^^^^^ CAUGHT AND STORED IN THE Future. Nothing printed, nothing logged, the
    //   thread survives. If nobody calls get(), this failure never happened.
    pool.execute(() -> { throw new IllegalStateException("boom"); });
    //   ^^^^^^^ goes to the thread's UncaughtExceptionHandler → stderr. VISIBLE.
    pool.submit(() -> { try { work(); } catch (Throwable t) { log.error("task", t); } });
    //                  ^^^ the actual fix: catch inside the task, always.

    // ── THE SCHEDULE THAT DIES SILENTLY ─────────────────────────────────
    sched.scheduleAtFixedRate(this::refreshCache, 0, 1, MINUTES);
    // ^ ONE exception → the schedule is CANCELLED. Permanently. Silently. The cache
    //   is stale until the next deploy and no log line marks the moment it stopped.
    sched.scheduleAtFixedRate(() -> {
        try { refreshCache(); } catch (Throwable t) { log.error("refresh", t); }
    }, 0, 1, MINUTES);                      // ← mandatory, not defensive

    // ── THE DEADLOCK THAT PASSES TESTING ────────────────────────────────
    var single = Executors.newSingleThreadExecutor();
    single.submit(() -> {
        var inner = single.submit(() -> 42);
        return inner.get();          // ← the only thread is BLOCKED waiting for a task
    });                              //   that needs the only thread. Deadlock, always.
    // With 10 threads this deadlocks only under load — which is worse, because it ships.

    // ── SHUTTING DOWN CORRECTLY ─────────────────────────────────────────
    pool.shutdown();                                   // stop accepting; returns at once
    if (!pool.awaitTermination(30, SECONDS)) {         // the actual wait
        pool.shutdownNow();                            // interrupt the stragglers
        pool.awaitTermination(10, SECONDS);
    }
    // Java 19+: try (var pool = Executors.newFixedThreadPool(8)) { ... }  does all of it.
    // Forget this and NON-DAEMON threads keep the JVM alive: main returns, nothing exits.""",

"""9. THE TRACE — one pool, four load levels

CONFIGURATION: core 4, max 8, `ArrayBlockingQueue(10)`, `CallerRunsPolicy`. Watch what each arriving
task does:

    task#  threads  queue  what happens                                  which rule fired
    ------------------------------------------------------------------------------------------
    1–4    0→4      0      a NEW THREAD each time — even though thread 1  rule 1: below core,
                           may already be idle                            always create
    5–14   4        0→10   QUEUED. No new threads, even though 4 more     rule 2: queue first
                           are permitted.                                 ← THE SURPRISING ONE
    15–18  4→8      10     queue is full → create threads 5..8            rule 3: only now
    19+    8        10     at max AND queue full → REJECTION POLICY →     rule 4
                           THE CALLING THREAD RUNS THE TASK ITSELF

    LOOK AT ROWS 5–14 AGAIN. Four threads are working, four more are ALLOWED, and ten tasks are sitting
    in a queue waiting. That is not a bug; it is the documented order. And it is why people report
    "my pool won't scale up" — it will, but only after the queue fills.

NOW REPLACE THE BOUNDED QUEUE WITH AN UNBOUNDED ONE — `newFixedThreadPool(4)`:

    task#      threads  queue      what happens
    ------------------------------------------------------------------------------------------
    1–4        0→4      0          create up to core
    5–1,000    4        →996       queued
    5–100,000  4        →99,996    STILL QUEUED. maximumPoolSize is unreachable.
    ...        4        growing    the heap fills with Runnables and their captured state
    eventually —        —          OutOfMemoryError, with a stack trace pointing at the queue

    NO REJECTION EVER HAPPENED. The system had no mechanism to say "no", so it said "yes" until it
    died. The pool behaved exactly as configured.

AND THE `CallerRunsPolicy` VERSION, which is the interesting one:

    time  producer thread                    pool                  effective rate
    ------------------------------------------------------------------------------------------
    t0    submitting 1000/sec                8 busy, queue 10      1000/sec accepted
    t1    submit REJECTED → CALLER RUNS IT   8 busy, queue 10      producer is now BUSY
    t2    producer still executing the task  8 busy, draining      producer submits NOTHING
    t3    producer finishes, submits again   queue has space       accepted
    ------------------------------------------------------------------------------------------
    THE PRODUCER THROTTLED ITSELF. No signal was sent, no rate limiter was configured, no exception was
    thrown. The system simply cannot outrun itself, because the thing generating work is the thing that
    absorbs the overflow. That is why this policy is worth knowing by name.

AND THE FAILURE THAT LOOKS LIKE NOTHING AT ALL:

    scheduleAtFixedRate(refresh, 0, 1, MINUTES)
    t=0min    runs, ok
    t=1min    runs, ok
    t=2min    THROWS — a transient network blip
    t=3min    ... nothing
    t=4min    ... nothing
    forever   ... nothing. No log line. No metric. The Future is cancelled and no one holds it.

    THE ONLY SYMPTOM IS DATA GETTING OLDER. Which is why the try/catch inside a scheduled task is not
    defensive programming; it is the difference between a job that exists and one that does not.""",

"""10. COMPLEXITY, THE MISTAKES, AND THE TAKEAWAY

    Thread creation: ~100 μs and ~1 MB reserved stack. Pool submission: sub-microsecond.
    Task arrival order: below core → CREATE; else → QUEUE; queue full → create up to max; else → REJECT.
    Unbounded queue ⇒ maximumPoolSize is unreachable, by construction.
    CPU-bound sizing ≈ cores. I/O-bound ≈ cores × (1 + wait/compute).
    `newFixedThreadPool`: unbounded QUEUE. `newCachedThreadPool`: unbounded THREADS.
    `submit` stores exceptions in the Future; `execute` routes them to the uncaught handler.
    A throwing `scheduleAtFixedRate` task cancels its schedule permanently.

THE #1 MISTAKE: an unbounded queue. Overload becomes an OutOfMemoryError instead of backpressure, and
maximumPoolSize silently stops meaning anything.

THE #2 MISTAKE: `submit` with an ignored Future. Every exception invisible; work stops and nothing
records it.

THE #3 MISTAKE: not wrapping scheduled tasks in try/catch. One throw cancels the schedule forever.

THE #4 MISTAKE: expecting maximumPoolSize to be reached with a `LinkedBlockingQueue`. It cannot be.

THE #5 MISTAKE: `newCachedThreadPool` for untrusted or bursty load. Unbounded thread creation.

THE #6 MISTAKE: blocking on a Future from the same bounded pool. Deadlock — guaranteed on a
single-thread pool, load-dependent on a larger one, which is worse because it ships.

THE #7 MISTAKE: forgetting to shut down. Non-daemon threads keep the JVM alive after `main` returns.

THE #8 MISTAKE: swallowing `InterruptedException`. Destroys the flag, so `shutdownNow` cannot stop the
task. Rethrow, or restore the flag.

THE #9 MISTAKE: default thread names. `pool-2-thread-7` identifies nothing in a thread dump.

THE #10 MISTAKE: ThreadLocals never removed. Pooled threads never die, so the values never go.

THE #11 MISTAKE: one pool for every kind of work. Slow calls starve fast ones; separate pools are
bulkheads.

THE #12 MISTAKE: blocking on `ForkJoinPool.commonPool()` via parallel streams or executor-less
`CompletableFuture`. It is shared by the entire JVM.

ONE-SENTENCE TAKEAWAY: a thread pool's threads are the boring half — the QUEUE and the REJECTION POLICY
are the design, because tasks only create threads beyond the core once the queue is FULL, which makes
`maximumPoolSize` unreachable behind an unbounded queue and turns `newFixedThreadPool` into a system
that queues until the heap is gone rather than ever saying no; construct `ThreadPoolExecutor` yourself
with a bounded queue and `CallerRunsPolicy` so overload throttles the producer, size from the
wait-to-compute ratio, name the threads, catch `Throwable` inside every task — especially scheduled
ones, where a single throw cancels the schedule permanently and silently — and never block on a Future
from the pool you are running in.""",
]


DEEP["Deadlock — the four conditions, and the one-line fix"] = [
"""1. THE GOAL IN PLAIN ENGLISH — two threads, each waiting for the other

Two threads need the same two locks. Thread A takes lock 1 and reaches for lock 2. Thread B, at the
same moment, holds lock 2 and reaches for lock 1. Neither will release what it holds until it gets what
it wants, and neither will ever get what it wants.

    THEY WAIT FOREVER. Not slowly — FOREVER. No exception, no timeout, no log line. The threads simply
    stop existing as far as your monitoring is concerned: CPU usage falls, memory sits still, and
    requests hang until the load balancer times them out.

    THE SYMPTOM IS SILENCE. Which is why deadlock is disproportionately painful for its frequency: a
    crash tells you where it happened, a slow query shows up in a profile, but a deadlock produces an
    application that looks healthy on every dashboard except the one nobody is watching.

    AND IT IS NOT A RACE CONDITION. That distinction matters. A race is non-deterministic in its
    OUTCOME — sometimes right, sometimes wrong. A deadlock is fully deterministic: given that exact
    interleaving, it happens 100% of the time. It is the INTERLEAVING that is rare. So it survives
    testing, survives staging, and appears at peak traffic — because peak traffic is simply more
    attempts at the rare ordering.

THE EVERYDAY VERSION: a narrow corridor, two people carrying a table each. One is halfway through
holding the left rail; the other is halfway through holding the right. Each needs the other's rail to
continue and neither will put theirs down. They will stand there indefinitely, and both are behaving
perfectly reasonably.

TERMS AS THEY APPEAR:
- LOCK / MONITOR: the thing only one thread may hold at a time.
- LOCK ORDERING: the discipline of always acquiring locks in the same global order.
- LIVELOCK: threads that are running and responding but making no progress.
- STARVATION: a thread that could progress but is never scheduled to.""",

"""2. THE INTUITION — the four conditions, and the fact that you only have to break one

COFFMAN'S FOUR CONDITIONS. Deadlock requires ALL FOUR simultaneously. That is the useful part: to make
deadlock impossible you only have to make ONE of them impossible.

    1. MUTUAL EXCLUSION — a resource can be held by only one thread at a time.
    2. HOLD AND WAIT — a thread holding one resource may request another.
    3. NO PREEMPTION — a resource cannot be forcibly taken from the thread holding it.
    4. CIRCULAR WAIT — there is a cycle of threads, each waiting on one held by the next.

NOW ASK WHICH ONE YOU CAN ACTUALLY BREAK IN JAVA:

    MUTUAL EXCLUSION — usually not. It is the point of the lock. Though sometimes you can: an immutable
    object, a copy-on-write structure, or a `ConcurrentHashMap` needs no exclusive lock at all, and
    "make it immutable" is a real and underused answer.

    HOLD AND WAIT — you can, by acquiring everything at once or nothing. Awkward, and it requires
    knowing the full set up front, which you often do not.

    NO PREEMPTION — you can, with `tryLock(timeout)`: if you cannot get the second lock, RELEASE THE
    FIRST, back off, and retry. This works, and it is essential when the ordering genuinely cannot be
    predetermined. But it needs a backoff or you get livelock, and it needs retry logic.

    CIRCULAR WAIT — THIS IS THE ONE. If every thread in the system acquires locks in the SAME GLOBAL
    ORDER, a cycle is arithmetically impossible: to have a cycle, some thread must hold a higher-ranked
    lock while waiting for a lower-ranked one, and the rule forbids that. NO COORDINATION, NO TIMEOUTS,
    NO RETRIES — just a rule everyone follows.

THE ONE-LINE FIX, THEREFORE, IS A CONSISTENT ORDER:

    IF THE OBJECTS HAVE A NATURAL ID — account number, user id, primary key — order by that. It is
    stable, meaningful, and readable.
    IF THEY DO NOT, ORDER BY `System.identityHashCode`. It is arbitrary but consistent within a run.
    AND HANDLE THE TIE: identity hash codes can collide, so take a third "tie-break" lock first in
    that rare case. Skipping the tie-break leaves a deadlock that fires roughly once in four billion
    pairs — which on a busy system is not never.

THE DEEPER LESSON, and the one worth saying in an interview: DEADLOCK IS A PROPERTY OF THE SYSTEM, NOT
OF A METHOD. Two methods that are each individually correct deadlock when combined. Which means you
cannot find it by reviewing a function; you find it by writing down the lock order for the whole
codebase and enforcing it.""",

"""3. THE MECHANISM — where deadlocks actually come from, and how to see one

THE TEXTBOOK EXAMPLE — two explicit locks in two orders — almost never appears in real code, because it
is too visible. THE REAL CAUSES ARE ALL FORMS OF "A LOCK YOU DID NOT KNOW YOU WERE HOLDING":

    THE ALIEN METHOD, the single biggest cause. You hold a lock and call code you do not control — a
    listener, a callback, an overridable method, a plugin. That code takes its own locks, in its own
    order, and you have just merged two lock hierarchies without meaning to. THE RULE THAT PREVENTS IT
    IS "OPEN CALLS": never hold a lock while calling something you do not own.

    LOCK ORDER DETERMINED BY ARGUMENTS. `transfer(from, to)` locks `from` then `to`. Perfectly
    reasonable, and the reversed call `transfer(b, a)` running concurrently is the deadlock. THE ORDER
    IS DATA-DEPENDENT, so no amount of reading the method reveals it.

    RE-ENTRANT-LOOKING CODE THAT IS NOT. `synchronized` is re-entrant on the SAME lock, so a recursive
    call is fine. Two DIFFERENT locks around the same logical operation are not.

    THE THREAD POOL. A task holds a lock and waits on a Future for another task that needs the same
    lock, in a pool with no free threads. The locks are fine; the RESOURCE is the thread.

    THE DATABASE, which is the same shape one level down. Two transactions updating the same rows in
    different orders deadlock in the engine — and unlike Java, the database DETECTS it, picks a victim,
    and throws. That is why the fix there is a retry loop, and why the underlying discipline is
    identical: update rows in a consistent order.

HOW TO SEE ONE — and this is the part that makes deadlock much less frightening than it sounds:

    `jstack <pid>` (or `jcmd <pid> Thread.print`) DETECTS JAVA DEADLOCKS AUTOMATICALLY. It prints
    "Found one Java-level deadlock:" followed by exactly which threads, which locks, and which lines.
    NOT AN INFERENCE — A DIAGNOSIS. It works for both `synchronized` monitors and
    `java.util.concurrent` locks.

    `ThreadMXBean.findDeadlockedThreads()` does the same programmatically, which lets a health check
    report it.

    WHAT NEITHER DETECTS: deadlocks that are not lock cycles. Waiting on a `CountDownLatch` nobody
    counts down, a `SynchronousQueue` handoff nobody takes, a `Future` that will never complete, a
    thread-pool exhaustion. Those look identical from the outside and require reading the thread dump
    yourself — every thread's stack, looking for what each is waiting on.

TWO PROPERTIES OF `synchronized` THAT MATTER HERE: it has NO TIMEOUT and it is NOT INTERRUPTIBLE. Once
a thread is blocked on a monitor there is no way to get it out, which is one of the strongest arguments
for `ReentrantLock` in code where deadlock is a real risk.""",

"""4. EDGE CASES AND FAILURE MODES

CASE 1 — DATA-DEPENDENT LOCK ORDER. `transfer(a, b)` and `transfer(b, a)`. The method is correct; the
PAIR is not. This is the canonical real deadlock.

CASE 2 — THE ALIEN METHOD. Holding a lock while calling a listener, callback, or overridable method.
You have merged an unknown lock hierarchy into yours.

CASE 3 — NESTED SYNCHRONIZED ACROSS LAYERS. A synchronized service method calls a synchronized
repository method which calls back into a synchronized cache. Nobody wrote a nested lock; the call
graph did.

CASE 4 — THREAD POOL DEADLOCK. Tasks waiting on other tasks in a bounded pool. Guaranteed on a
single-thread pool; load-dependent on a larger one, which is worse.

CASE 5 — IDENTITY HASH COLLISION IN AN ORDERING SCHEME. Two objects with the same
`System.identityHashCode` defeat the ordering. Rare, and requires an explicit tie-break lock.

CASE 6 — LIVELOCK. Both threads detect contention, both back off, both retry at the same interval,
forever. Running, responsive, making no progress. The fix is RANDOMISED backoff — deterministic backoff
reproduces the collision.

CASE 7 — LOCK-ORDER INVERSION VIA CLASS INITIALISATION. Class loading takes an internal lock. Two
classes whose static initialisers reference each other from different threads deadlock inside the JVM
itself, and the stack traces are baffling.

CASE 8 — DEADLOCK WITH A NON-LOCK. `CountDownLatch` never counted down, a `Future` never completed, a
`SynchronousQueue` handoff with no partner. `jstack` will NOT report these as deadlocks.

CASE 9 — `synchronized` ON A `String` OR A BOXED `Integer`. Interned literals and cached Integers are
SHARED GLOBALLY, so unrelated code can be holding "your" lock. Always lock a private final Object.

CASE 10 — LOCKING ON `this` IN A PUBLIC CLASS. Anyone can `synchronized (yourObject)` and participate
in your lock protocol without you knowing.

CASE 11 — RE-ENTRANCY ASSUMED ACROSS DIFFERENT LOCKS. `synchronized` is re-entrant on the SAME monitor
only.

CASE 12 — `tryLock` WITHOUT RELEASING WHAT YOU HOLD. If you fail to get the second lock and keep the
first while retrying, you have preserved hold-and-wait and gained nothing.

CASE 13 — DEADLOCK THAT ONLY APPEARS UNDER LOAD. It is not intermittent behaviour; it is a rare
interleaving. More traffic means more attempts, which is why it debuts at peak.""",

"""5. THE ALTERNATIVES — designing so the question does not arise

DO NOT SHARE MUTABLE STATE. The strongest fix, and it removes condition 1 entirely:
    IMMUTABLE OBJECTS need no locks at all. `record`, final fields, defensive copies.
    CONFINEMENT — give each thread its own copy and merge at the end. This is what a map-reduce does,
    and what a per-request object graph does.
    MESSAGE PASSING — an actor or a queue, where state is owned by one thread and others send
    requests. The lock discipline becomes structural rather than remembered.

USE A CONCURRENT COLLECTION INSTEAD OF LOCKING ONE. `ConcurrentHashMap.compute` performs a read-modify-
write atomically without you holding anything across the operation. `AtomicLong`, `LongAdder`,
`CopyOnWriteArrayList`. MOST "I NEED TWO LOCKS" SITUATIONS ARE ACTUALLY "I AM USING THE WRONG DATA
STRUCTURE".

`ReentrantLock` OVER `synchronized` WHERE DEADLOCK IS A REAL RISK, for three capabilities `synchronized`
does not have:
    `tryLock()` and `tryLock(timeout)` — breaks the no-preemption condition;
    `lockInterruptibly()` — lets you cancel a blocked thread;
    fairness, and multiple `Condition` objects per lock.
    The cost is that you must `unlock()` in a `finally`, every time, without exception.

A SINGLE COARSER LOCK. Genuinely underrated. Two fine-grained locks that deadlock are worse than one
coarse lock that serialises. MEASURE BEFORE ASSUMING THE COARSE LOCK IS TOO SLOW — most contention
concerns are imagined, and correctness is not.

STAMPEDLOCK for read-heavy structures — an optimistic read mode that takes no lock at all and validates
afterwards. Not re-entrant, which is a real trap.

DATABASE-LEVEL: consistent update order, short transactions, and a RETRY loop, because the engine
detects the deadlock and throws rather than hanging. `SELECT ... FOR UPDATE` in a defined order.

THE ONE-LINE FIX ITSELF — a global lock ordering. Not a library, not a framework: a rule, written down,
applied everywhere:

    Object first  = a.id() < b.id() ? a : b;
    Object second = a.id() < b.id() ? b : a;
    synchronized (first) { synchronized (second) { ... } }

WHAT TO SAY: "First I would try to remove the shared mutable state or use a concurrent collection so no
second lock exists. If two locks are genuinely needed, a global acquisition order breaks circular wait
with no coordination at all. And `tryLock` with a timeout and randomised backoff where the order
genuinely cannot be predetermined."

""",

"""6. HOW TO PREVENT AND DIAGNOSE — numbered steps

STEP 1 — TRY TO NEED ONLY ONE LOCK. Immutability, confinement, or a concurrent collection removes the
problem rather than managing it.

STEP 2 — WRITE DOWN A GLOBAL LOCK ORDER for the whole codebase, and put it somewhere people read.
Deadlock is a system property; it cannot be prevented one method at a time.

STEP 3 — WHEN LOCKING TWO OBJECTS OF THE SAME TYPE, ORDER BY A STABLE KEY. An id where one exists,
`System.identityHashCode` otherwise, plus a tie-break lock for the collision case.

STEP 4 — NEVER HOLD A LOCK WHILE CALLING CODE YOU DO NOT OWN. Callbacks, listeners, overridable
methods, plugins. Compute under the lock, release, then call out.

STEP 5 — PREFER `tryLock(timeout)` WHERE ORDERING IS IMPOSSIBLE, and RELEASE EVERYTHING on failure.
Keeping the first lock while retrying preserves hold-and-wait.

STEP 6 — RANDOMISE THE BACKOFF. Fixed backoff turns a deadlock into a livelock.

STEP 7 — LOCK PRIVATE FINAL OBJECTS. Never a `String`, never a boxed `Integer`, and never `this` in a
public class — all of those are locks other code can hold.

STEP 8 — KEEP CRITICAL SECTIONS SHORT AND FREE OF I/O. A lock held across a network call converts a
downstream slowdown into a total stall.

STEP 9 — WHEN IT HANGS, TAKE A THREAD DUMP FIRST. `jstack <pid>` or `jcmd <pid> Thread.print`. It
detects lock cycles automatically and names the threads, the locks and the lines.

STEP 10 — IF THE DUMP SHOWS NO DEADLOCK BUT NOTHING PROGRESSES, LOOK FOR THE NON-LOCK VERSIONS. A
latch, a Future, an empty pool. `jstack` cannot see those, so read every thread's WAITING state
yourself.

STEP 11 — ADD `ThreadMXBean.findDeadlockedThreads()` TO A HEALTH CHECK. Turning silence into an alert
is most of the battle.

STEP 12 — USE SEPARATE POOLS FOR DEPENDENT WORK, and never block on a Future from the pool you are
running in.""",

"""7. THE ANSWER IN PLAIN LANGUAGE — what you would say out loud

'Two threads need the same two locks in opposite orders. A takes lock 1 and reaches for 2; B holds 2
and reaches for 1. Neither releases what it has until it gets what it wants, so they wait forever.

And the symptom is SILENCE. No exception, no timeout, no log line. CPU drops, memory sits still,
requests hang until the load balancer gives up. Which is why it hurts more than its frequency suggests
— a crash tells you where it happened, a slow query shows up in a profile, but a deadlock leaves an
application that looks healthy on every dashboard.

The thing I'd separate out early: it's NOT a race condition. A race is non-deterministic in its
outcome. A deadlock is fully deterministic — given that interleaving it happens 100% of the time. It's
the INTERLEAVING that's rare. So it survives testing and staging and appears at peak traffic, because
peak traffic is just more attempts at the rare ordering.

The framework is Coffman's four conditions — mutual exclusion, hold and wait, no preemption, and
circular wait. You need all four simultaneously, which is the useful part: you only have to break ONE.

Mutual exclusion you usually can't break, though sometimes you can, and "make it immutable" is a real
answer people skip. Hold-and-wait means acquiring everything or nothing, which needs the full set up
front. No-preemption you break with tryLock and a timeout — release what you hold, back off, retry.
That works, but it needs retry logic and RANDOMISED backoff, because deterministic backoff turns the
deadlock into a livelock.

But the one to break is CIRCULAR WAIT, and that's the one-line fix. If everyone acquires locks in the
same global order, a cycle is arithmetically impossible — a cycle requires someone holding a
higher-ranked lock while waiting for a lower one, and the rule forbids it. No coordination, no
timeouts, no retries. Order by a natural id if there is one, System.identityHashCode if there isn't,
and take a third tie-break lock when the hashes collide — otherwise you've left a deadlock that fires
once in four billion pairs, which on a busy system isn't never.

Where they actually come from is worth saying, because the textbook two-locks-two-orders example almost
never appears in real code — it's too visible. The real cause is a lock you didn't know you were
holding. Number one is the ALIEN METHOD: you hold a lock and call a listener or an overridable method,
that code takes its own locks in its own order, and you've merged two lock hierarchies without meaning
to. The rule is open calls — never hold a lock while calling code you don't own. Number two is
data-dependent order: transfer(from, to) locks from then to, which is perfectly reasonable, and the
reversed call is the deadlock. Reading the method never reveals it.

And the encouraging part: jstack detects Java deadlocks automatically. It prints "Found one Java-level
deadlock" with the threads, the locks, and the lines. It's a diagnosis, not an inference. What it can't
see is deadlock that isn't a lock cycle — a latch nobody counts down, a Future that never completes, an
exhausted thread pool. Those look identical from outside and you have to read the dump yourself.

The framing I'd end on: deadlock is a property of the SYSTEM, not of a method. Two individually correct
methods deadlock when combined, so you can't find it in code review of a function — you find it by
writing down the lock order for the codebase and enforcing it.'""",

"""8. THE CODE, LINE BY LINE

    // ── THE REAL DEADLOCK: the order comes from the ARGUMENTS ───────────
    void transfer(Account from, Account to, long amount) {
        synchronized (from) {              // ← thread A: locks acct1
            synchronized (to) {            // ← thread A: wants acct2
                from.debit(amount); to.credit(amount);
            }
        }
    }
    // transfer(acct1, acct2) and transfer(acct2, acct1) running concurrently:
    //   A holds acct1, wants acct2   |   B holds acct2, wants acct1
    // THE METHOD IS CORRECT. THE PAIR IS NOT. Nothing you can see by reading it.

    // ── THE ONE-LINE FIX: break CIRCULAR WAIT with a global order ───────
    void transfer(Account from, Account to, long amount) {
        Account first  = from.id() < to.id() ? from : to;
        Account second = from.id() < to.id() ? to   : from;
    //  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ EVERY thread now acquires
    //  in ascending id order, so a cycle is arithmetically impossible: a cycle needs
    //  someone holding a higher lock while waiting for a lower one.
        synchronized (first) { synchronized (second) { ... } }
    }
    // No timeouts. No retries. No coordination. Just a rule everyone follows.

    // ── AND THE TIE-BREAK PEOPLE SKIP ───────────────────────────────────
    private static final Object TIE = new Object();
    int ha = System.identityHashCode(a), hb = System.identityHashCode(b);
    if (ha == hb) {                        // ← ~1 in 4 billion. Not never.
        synchronized (TIE) { synchronized (a) { synchronized (b) { ... } } }
    } else if (ha < hb) { synchronized (a) { synchronized (b) { ... } } }
    else                { synchronized (b) { synchronized (a) { ... } } }

    // ── BREAKING "NO PREEMPTION" INSTEAD, when order is impossible ──────
    while (true) {
        if (lockA.tryLock()) {
            try {
                if (lockB.tryLock(50, MILLISECONDS)) {
                    try { doWork(); return; } finally { lockB.unlock(); }
                }
            } finally { lockA.unlock(); }
    //                 ^^^^^^^^^^^^^^ RELEASE WHAT YOU HOLD. Retrying while still
    //                 holding lockA preserves hold-and-wait and fixes nothing.
        }
        Thread.sleep(ThreadLocalRandom.current().nextInt(1, 50));
    //                ^^^^^^^^^^^^^^^^^^ RANDOMISED. A fixed backoff makes both
    //                threads retry in lockstep forever — that is LIVELOCK.
    }

    // ── THE BIGGEST REAL CAUSE: the alien method ────────────────────────
    synchronized void addItem(Item i) {
        items.add(i);
        for (Listener l : listeners) l.onItemAdded(i);
    //                                ^^^^^^^^^^^^^^ CODE YOU DO NOT OWN, called
    //   while holding YOUR lock. It takes its own locks in its own order, and you
    //   have just merged two lock hierarchies without knowing it.
    }
    void addItem(Item i) {                     // ← the "open call" fix
        List<Listener> snapshot;
        synchronized (this) { items.add(i); snapshot = List.copyOf(listeners); }
        for (Listener l : snapshot) l.onItemAdded(i);   // OUTSIDE the lock
    }

    // ── LOCKS THAT ARE SECRETLY GLOBAL ──────────────────────────────────
    synchronized ("lock") { ... }     // interned literal — SHARED PROCESS-WIDE
    synchronized (Integer.valueOf(1)) { ... }  // cached box — SHARED
    private final Object lock = new Object();  // ← the only correct form

    // ── SEEING IT ───────────────────────────────────────────────────────
    // jstack <pid>   →   "Found one Java-level deadlock:"
    //                    "Thread-1 waiting to lock monitor 0x... which is held by Thread-0"
    //                    "Thread-0 waiting to lock monitor 0x... which is held by Thread-1"
    // A DIAGNOSIS, not an inference. Works for synchronized AND j.u.c locks.""",

"""9. THE TRACE — the interleaving, and why it passed every test

TWO THREADS, `transfer(acct1, acct2)` AND `transfer(acct2, acct1)`, starting at the same moment:

    time  Thread A                          Thread B                     state
    ------------------------------------------------------------------------------------
    t0    enters transfer(acct1, acct2)     enters transfer(acct2, acct1)  —
    t1    ACQUIRES acct1                    —                              A holds acct1
    t2    —                                 ACQUIRES acct2                 B holds acct2
    t3    requests acct2 → BLOCKED          —                              A waiting on B
    t4    —                                 requests acct1 → BLOCKED       B waiting on A
    t5    blocked                           blocked                        CYCLE. FOREVER.
    ------------------------------------------------------------------------------------
    NOTHING IS THROWN. Both threads are in state BLOCKED, which looks identical to "waiting for a busy
    lock". CPU usage falls to zero for these threads. The heap does not grow. Every health check that
    does not touch this code path passes.

WHY IT PASSED TESTING — the timing window, made explicit:

    A must acquire acct1 in the gap between B starting and B acquiring acct2. That window is on the
    order of NANOSECONDS. Run the pair a thousand times in a test and you may never hit it. Run it a
    million times a day in production and you hit it daily.

    THE DEADLOCK IS NOT INTERMITTENT. Given rows t1–t4 in that order, it happens every single time,
    deterministically. What is rare is the ORDER, not the outcome. Which is exactly why "we couldn't
    reproduce it" is the normal state of affairs and why the fix must be structural rather than
    empirical.

NOW THE ORDERED VERSION, with acct1.id = 100 and acct2.id = 200:

    time  Thread A                          Thread B                     state
    ------------------------------------------------------------------------------------
    t0    first=acct1(100), second=acct2    first=acct1(100), second=acct2  SAME ORDER
    t1    ACQUIRES acct1                    —                              A holds acct1
    t2    —                                 requests acct1 → BLOCKED       B waits (fine)
    t3    ACQUIRES acct2, does the work     —                              A holds both
    t4    releases both                     —                              —
    t5    —                                 ACQUIRES acct1, then acct2     B proceeds
    ------------------------------------------------------------------------------------
    B WAITED. That is not a deadlock, that is a lock doing its job. B blocked for microseconds and then
    made progress. NO CYCLE IS POSSIBLE, because both threads want the low id first, so whoever gets it
    can always complete.

AND THE LIVELOCK VERSION — what `tryLock` gives you if you forget to randomise:

    time   Thread A                      Thread B                    progress
    ------------------------------------------------------------------------------------
    t0     tryLock(A) ✓, tryLock(B) ✗    tryLock(B) ✓, tryLock(A) ✗   none
    t1     release, sleep 50ms           release, sleep 50ms          none
    t2     tryLock(A) ✓, tryLock(B) ✗    tryLock(B) ✓, tryLock(A) ✗   none
    ...    identical forever             identical forever            NONE
    ------------------------------------------------------------------------------------
    BOTH THREADS ARE RUNNING. CPU is busy. Thread dumps show RUNNABLE. Every health check passes and no
    work is done. A FIXED BACKOFF REPRODUCES THE COLLISION EXACTLY, every cycle; randomising it breaks
    the symmetry on the first or second attempt.

WHAT PRODUCED WHAT:
    CIRCULAR WAIT      produced trace 1, and removing it produced trace 2. That is the whole fix.
    THE NANOSECOND WINDOW  produced "it passed testing" — a statement about probability, not about
                       whether the bug exists.
    SYMMETRY           produced trace 3. Randomness is the cure for symmetry, which is why the sleep
                       is random and not tidy.""",

"""10. COMPLEXITY, THE MISTAKES, AND THE TAKEAWAY

    Deadlock needs ALL FOUR Coffman conditions; breaking any one makes it impossible.
    Global lock ordering breaks circular wait at ZERO runtime cost — no timeouts, retries, or
    coordination. It is the cheapest correct fix available.
    `tryLock(timeout)` breaks no-preemption, at the cost of retry logic and a randomised backoff.
    `synchronized`: no timeout, not interruptible, re-entrant on the same monitor.
    `ReentrantLock`: timeout, interruptible, fair mode, multiple conditions — and `unlock()` in a
    `finally` is mandatory.
    `jstack` / `jcmd Thread.print` detect lock-cycle deadlocks automatically and name the lines.
    They do NOT detect latch, Future, queue-handoff or pool-exhaustion hangs.

THE #1 MISTAKE: data-dependent lock order. `transfer(from, to)` is correct and the reversed pair is not.

THE #2 MISTAKE: holding a lock while calling code you do not own. The alien method merges lock
hierarchies invisibly. Make it an open call.

THE #3 MISTAKE: assuming testing would have caught it. The interleaving window is nanoseconds; the
deadlock itself is 100% deterministic once it occurs.

THE #4 MISTAKE: `tryLock` that keeps the first lock while retrying. Hold-and-wait preserved, nothing
fixed.

THE #5 MISTAKE: a fixed backoff. Converts deadlock into livelock, which looks healthier and is not.

THE #6 MISTAKE: ordering by identity hash with no tie-break. One in four billion is not never at scale.

THE #7 MISTAKE: `synchronized` on a String literal, a boxed Integer, or `this` in a public class. Those
locks are reachable — and holdable — by code you have never seen.

THE #8 MISTAKE: blocking on a Future from the pool you are running in. Thread-pool deadlock, guaranteed
on one thread and load-dependent on many.

THE #9 MISTAKE: holding a lock across I/O. A slow downstream call becomes a total stall.

THE #10 MISTAKE: expecting `jstack` to explain every hang. A latch nobody counts down produces the same
silence and is not a lock cycle.

THE #11 MISTAKE: fine-grained locks adopted for performance without measurement. Two locks that
deadlock are worse than one that serialises, and most contention worries are imagined.

ONE-SENTENCE TAKEAWAY: deadlock needs mutual exclusion, hold-and-wait, no preemption AND circular wait
all at once — so you only have to break one, and the cheapest is circular wait via a GLOBAL LOCK
ORDERING (by natural id, or `System.identityHashCode` with a tie-break lock), which costs nothing at
runtime; the real causes are almost never the textbook two-locks-two-orders but rather data-dependent
ordering and holding a lock while calling code you do not own, the symptom is total silence rather than
an error, and `jstack` will name the threads and lines for you — but only when the hang is an actual
lock cycle, not a latch, a Future, or an exhausted pool.""",
]


DEEP["Why == sometimes works on Strings, and why you must never rely on it"] = [
"""1. THE GOAL IN PLAIN ENGLISH — the comparison that works until it doesn't

    String a = "hello";
    String b = "hello";
    a == b                          →  true

    String c = new String("hello");
    a == c                          →  false

    String d = "hel";
    String e = d + "lo";
    a == e                          →  false

    THREE STRINGS THAT ALL CONTAIN "hello", AND `==` GIVES A DIFFERENT ANSWER EACH TIME.

`==` ON OBJECTS ASKS "ARE THESE THE SAME OBJECT?" — the same address, the same identity. It has never
asked about content. `equals` asks "do these hold the same characters?" and for a String that is
almost always the question you meant.

    SO WHY DOES THE FIRST ONE WORK? Because Java keeps a POOL of string literals. When the class is
    loaded, `"hello"` is placed in that pool once, and every literal `"hello"` anywhere in the program
    refers to THE SAME OBJECT. So `a == b` is true — not because the contents match, but because there
    is genuinely only one object.

    AND THAT IS EXACTLY WHY IT IS DANGEROUS. The comparison appears to work. It works in your unit
    test, where the strings are literals. It fails in production, where the string came from a request
    parameter, a database row, a JSON parser, or a concatenation — none of which are pooled. THE BUG IS
    INVISIBLE UNTIL THE DATA STOPS BEING A LITERAL, and by then the code has been reviewed and shipped.

THE EVERYDAY VERSION: two people both holding a copy of the same book. "Is it the same book?" and "does
it say the same thing?" are different questions. If the library only ever lends one physical copy, both
questions happen to give the same answer — and someone will conclude the first question is a fine way
to ask the second. Then a photocopier arrives.

TERMS AS THEY APPEAR:
- STRING POOL (string constant pool): a JVM-wide table of unique string instances.
- INTERNING: putting a string into that pool, or looking up the pooled instance.
- CONSTANT EXPRESSION: something javac can fully evaluate at compile time.
- IMMUTABLE: the contents can never change after construction — which is what makes all this safe.""",

"""2. THE INTUITION — why a pool exists at all, and what it buys

STRINGS ARE THE MOST COMMON OBJECT IN ALMOST EVERY JAVA PROGRAM. Class names, field names, map keys,
configuration values, log messages, HTTP headers. Heap dumps of real applications routinely show
strings and their backing arrays as 20–40% of live memory, and a large fraction of them are duplicates.

    SO THE JVM KEEPS A TABLE OF UNIQUE STRINGS. Every literal in every class file is interned when the
    class is loaded. Ten thousand classes containing the literal `"UTF-8"` share ONE object.

    THE SAVING IS REAL. And there is a second one people miss: comparing two pooled strings for
    equality can short-circuit on reference identity, so `equals` starts with `if (this == other)
    return true` and that check succeeds constantly on pooled data.

BUT THE POOL ONLY CONTAINS WHAT WAS PUT THERE:

    LITERALS IN SOURCE CODE                    → pooled, automatically
    COMPILE-TIME CONSTANT EXPRESSIONS          → FOLDED by javac into a literal, then pooled.
                                                 `"hel" + "lo"` becomes `"hello"` in the class file.
                                                 So does `"a" + FINAL_CONSTANT`, if the constant is a
                                                 `static final String` initialised with a literal.
    ANYTHING COMPUTED AT RUNTIME               → a NEW object, not pooled. Concatenation with a
                                                 variable, `substring`, `toUpperCase`, `split`,
                                                 `StringBuilder.toString`, a JSON parser, a JDBC driver.
    `new String("x")`                          → EXPLICITLY a new object, always. The literal is pooled;
                                                 the `new` makes a second, unpooled copy of it. This is
                                                 why the constructor is essentially never useful.
    `.intern()`                                → asks the pool for the canonical instance, adding it
                                                 if absent.

    NOW THE THREE RESULTS FROM SECTION 1 EXPLAIN THEMSELVES: `a == b` is true because both are the same
    pooled literal. `a == c` is false because `new` forced a second object. `a == e` is false because
    `d + "lo"` was computed at runtime from a VARIABLE, so the folding could not happen.

WHY THE POOL IS EVEN POSSIBLE — and this is the fact underneath the whole topic:

    STRINGS ARE IMMUTABLE. If one class could modify a shared `"hello"`, sharing it across ten thousand
    call sites would be catastrophic. IMMUTABILITY IS WHAT MAKES SHARING SAFE, and it is also what
    makes strings safe as HashMap keys, safe to pass between threads with no synchronisation, and safe
    to cache their hashCode — which `String` does, in a field, computing it once.

    IT IS ALSO A SECURITY PROPERTY. A `String` passed to a file-open or a SQL call cannot be changed by
    another thread between the security check and the use. That class of attack — time-of-check to
    time-of-use — is simply unavailable.""",

"""3. THE MECHANISM — where the pool lives, what a String is made of, and interning

WHERE THE POOL LIVES. Before Java 7 it was in PermGen, a fixed-size region, so aggressive `intern()`
could throw `OutOfMemoryError: PermGen space`. SINCE JAVA 7 IT IS IN THE NORMAL HEAP, so pooled strings
are garbage-collectable when nothing references them, and the size limit is the heap. The table itself
is a fixed-bucket hash table sized by `-XX:StringTableSize` (default 65536 in recent JDKs), and a
badly-oversubscribed table degrades `intern()` from constant time to a list walk.

WHAT A STRING IS MADE OF — and it changed in Java 9:

    BEFORE JAVA 9:   private final char[] value;      // 2 bytes per character, ALWAYS
    JAVA 9 ONWARDS:  private final byte[] value;
                     private final byte coder;        // LATIN1 or UTF16

    COMPACT STRINGS. If every character fits in one byte — which is true of essentially all ASCII text,
    so most identifiers, headers, JSON keys and English content — the string is stored one byte per
    character. THAT HALVED STRING MEMORY FOR MOST APPLICATIONS, and it was one of the largest
    across-the-board wins in a JDK release. It is invisible in the API and shows up only as a
    fifteen-percent heap reduction after upgrading.

    Also: `private int hash;` — the cached hashCode, computed on first use. A value of 0 means "not yet
    computed", so a string that genuinely hashes to 0 (including `""`) recomputed every time until
    Java 13 added a `hashIsZero` flag.

`intern()` — what it actually does and when it helps:

    Returns the canonical pooled instance, adding this string if the pool does not have it. The point
    is DEDUPLICATION: if you are parsing a million records with a hundred distinct category names, the
    naive result is a million String objects; interning gives you a hundred.
    THE COSTS ARE REAL: a native call, a hash-table lookup under contention, and pool growth you cannot
    easily observe. A `HashMap<String,String>` used as your own canonicalisation map is often faster
    and always more controllable.

`-XX:+UseStringDeduplication` — a G1 feature that does something related but different: a background GC
thread finds Strings with identical contents and points them at ONE SHARED BYTE ARRAY. The String
objects stay distinct — so `==` is unaffected and no semantics change — but the arrays, which are the
bulk of the memory, are shared. IT REQUIRES NO CODE CHANGES AT ALL, which makes it strictly easier than
interning for the memory problem.

`switch` ON A STRING, since Java 7, compiles to a `hashCode()` lookup followed by an `equals()` check —
never `==`. Which is why switching on a runtime-computed string works correctly and switching with `==`
would not.""",

"""4. EDGE CASES AND FAILURE MODES

CASE 1 — `==` THAT PASSES EVERY TEST. Literals in tests, runtime data in production. The classic shape:
`if (status == "ACTIVE")` works until the status arrives from JSON.

CASE 2 — `"hel" + "lo" == "hello"` IS TRUE. Both are compile-time constants, folded by javac into the
same literal. Which makes the rule look inconsistent and encourages exactly the wrong conclusion.

CASE 3 — `final String X = "hel"; X + "lo" == "hello"` IS ALSO TRUE, because a `final` local initialised
with a literal is a compile-time constant. Remove the `final` and it becomes false. A ONE-KEYWORD
CHANGE FLIPS THE RESULT.

CASE 4 — `new String("hello")` IS ALWAYS A DISTINCT OBJECT. There is no reason to write it except to
demonstrate this, or to force a copy of a substring in very old JDKs.

CASE 5 — `s1.equals(s2)` WITH `s1` NULL throws. `Objects.equals(s1, s2)` is null-safe both ways, and
`"literal".equals(variable)` is the Yoda form that avoids it.

CASE 6 — `equalsIgnoreCase` VS `toLowerCase().equals(...)`. The second allocates and is LOCALE
SENSITIVE — see the next case.

CASE 7 — THE TURKISH I. `"TITLE".toLowerCase()` in a Turkish default locale gives `"tıtle"` with a
dotless ı, so `"TITLE".toLowerCase().equals("title")` is FALSE on a machine in Istanbul. This has broken
real authentication and routing code. USE `toLowerCase(Locale.ROOT)` for anything that is a protocol
token rather than human text.

CASE 8 — SUBSTRING AND MEMORY, historically. Before Java 7u6, `substring` SHARED the backing array, so
a two-character substring of a ten-megabyte string retained all ten megabytes. Since 7u6 it copies —
O(n) instead of O(1), and no leak.

CASE 9 — `String.valueOf(null)` IS AMBIGUOUS. It binds to the `char[]` overload and throws NPE, while
`String.valueOf((Object) null)` returns `"null"`.

CASE 10 — `synchronized` ON A STRING LITERAL. Interned, therefore SHARED PROCESS-WIDE. Unrelated code
can hold "your" lock.

CASE 11 — PASSWORDS IN A `String`. Immutable, so you cannot zero it, and it may be interned, so it
lingers in the heap until collected — and shows up in a heap dump. `char[]` exists so you can wipe it.

CASE 12 — `split("")` AND TRAILING EMPTIES. `"a,b,,".split(",")` gives 2 elements, not 4; the trailing
empties are dropped unless you pass a negative limit.

CASE 13 — `==` ON A `Character` OR BOXED TYPE FOR THE SAME REASON. The Integer cache from −128 to 127
is the same phenomenon wearing a different hat.""",

"""5. THE ALTERNATIVES — comparing, canonicalising, and saving memory

FOR COMPARISON:
    `equals`                     content, exact. The default answer.
    `Objects.equals(a, b)`       null-safe on both sides. Use it whenever either might be null.
    `equalsIgnoreCase`           case-insensitive without allocating, and without the locale trap.
    `compareTo`                  lexicographic ordering by UTF-16 code unit — note that this is NOT
                                 alphabetical for non-English text.
    `Collator`                   locale-correct comparison and sorting for HUMAN-FACING text. "ö" sorts
                                 differently in German and Swedish, and `compareTo` knows nothing about
                                 that.
    `String.CASE_INSENSITIVE_ORDER`  a ready-made comparator.
    `contentEquals(CharSequence)`    compare a String to a StringBuilder without materialising it.

FOR CANONICALISATION — deduplicating repeated values:
    `intern()`                   simple, JVM-wide, but a native call with a shared table.
    YOUR OWN `HashMap<String,String>` or a Guava `Interner`. Usually faster, bounded, observable, and
    discardable when the parse finishes. THE PREFERRED ANSWER IN MOST REAL SYSTEMS.
    `-XX:+UseStringDeduplication` with G1. Shares the backing ARRAYS in the background with no code
    change at all. The right first move for a memory problem.
    AN ENUM. If the set of values is closed — statuses, types, currencies — then it was never really a
    string. `==` becomes correct, exhaustive `switch` becomes available, and typos become compile
    errors.

FOR BUILDING:
    `StringBuilder` for loops, `String.join` and `Collectors.joining` for delimited output,
    `StringJoiner` when you need a prefix and suffix, text blocks for multi-line literals, and
    `String.format` / `formatted` when readability matters more than the parsing cost.

FOR SECRETS: `char[]`, so it can be zeroed. A `String` cannot be cleared and may be interned.

FOR CASE AND NORMALISATION: `toLowerCase(Locale.ROOT)` for protocol tokens; `Normalizer.normalize(s,
Form.NFC)` before comparing user-entered text, because "é" has two distinct Unicode encodings that look
identical and are not `equals`.

WHAT TO SAY: "`equals` always, `Objects.equals` when null is possible, and an enum the moment the value
set is closed. `==` on strings is a bug that passes its own tests, so I would treat any instance of it
as a defect regardless of whether it currently works."

""",

"""6. HOW TO WORK WITH STRING EQUALITY — numbered steps

STEP 1 — USE `equals`, ALWAYS. There is no case where `==` on strings is the right expression of
intent, even when it happens to return the right answer.

STEP 2 — USE `Objects.equals(a, b)` WHEN EITHER SIDE MIGHT BE NULL. Null-safe in both directions.

STEP 3 — PUT THE LITERAL FIRST when you do use `equals` directly: `"ACTIVE".equals(status)` cannot NPE.

STEP 4 — IF THE VALUE SET IS CLOSED, USE AN ENUM. Statuses, types, currencies. It converts a runtime
string comparison into a compile-time check and makes `==` genuinely correct.

STEP 5 — TURN ON A STATIC ANALYSIS RULE FOR REFERENCE COMPARISON OF STRINGS. SpotBugs `ES_COMPARING_STRINGS_WITH_EQ`,
ErrorProne `ReferenceEquality`. This is a bug class a tool can eliminate entirely.

STEP 6 — USE `equalsIgnoreCase` RATHER THAN LOWERCASING BOTH SIDES. No allocation, no locale trap.

STEP 7 — WHEN YOU MUST CHANGE CASE FOR A PROTOCOL TOKEN, PASS `Locale.ROOT`. The Turkish dotless ı is a
real production bug, not a curiosity.

STEP 8 — NORMALISE USER-ENTERED TEXT BEFORE COMPARING. `Normalizer.normalize(s, Form.NFC)`; identical-
looking accented characters have multiple encodings.

STEP 9 — DO NOT REACH FOR `intern()` AS A MEMORY FIX. Try `-XX:+UseStringDeduplication` first — no code
change — and your own map if you need control.

STEP 10 — NEVER `synchronized` ON A STRING. Interned literals are shared process-wide.

STEP 11 — KEEP SECRETS IN `char[]`. A String cannot be wiped and may outlive its use in the pool and in
heap dumps.

STEP 12 — WHEN A COMPARISON "WORKS ON MY MACHINE", CHECK WHETHER BOTH SIDES ARE LITERALS. That is
almost always the explanation, and it is a warning rather than a result.""",

"""7. THE ANSWER IN PLAIN LANGUAGE — what you would say out loud

'`==` on objects asks "are these the same object" — same address, same identity. It has never asked
about content. `equals` asks about the characters, which is what you meant.

So why does it seem to work? Because Java keeps a POOL of string literals. Every literal in every class
file is interned when the class loads, so ten thousand classes containing "UTF-8" share one object.
Two literals with the same text ARE the same object, so `==` returns true — not because the contents
match, but because there genuinely is only one object.

And that's exactly what makes it dangerous. The comparison appears to work. It works in the unit test,
where the strings are literals. It fails in production, where the string came from a request parameter,
a database row, or a JSON parser — none of which are pooled. The bug is invisible until the data stops
being a literal, and by then it's been reviewed and shipped.

The pool only contains what was put there. Literals, and compile-time CONSTANT expressions, because
javac folds those — "hel" + "lo" is literally the string "hello" in the class file. Anything computed
at runtime is a fresh object: concatenation with a variable, substring, toUpperCase, a parser. And
`new String("hello")` is always a distinct object by definition, which is why that constructor is
essentially never useful.

There's a detail that shows how brittle this is. `final String x = "hel"; x + "lo" == "hello"` is TRUE,
because a final local initialised with a literal is a compile-time constant and gets folded. Drop the
`final` and it becomes false. A one-keyword change flips the result — which is a good argument that no
one should be reasoning about this at all.

The reason a pool is even possible is that strings are IMMUTABLE. If one class could modify a shared
"hello", sharing it across ten thousand call sites would be catastrophic. Immutability is what makes
sharing safe — and it's also what makes strings safe as HashMap keys, safe to pass between threads with
no synchronisation, and safe to cache the hashCode, which String does in a field.

Two things worth knowing beyond the basics. Java 9 changed the internal representation from char[] to
byte[] plus a coder flag — compact strings — so ASCII text is one byte per character instead of two.
That halved string memory for most applications and it's invisible in the API; it just shows up as a
heap reduction after upgrading. And if you have a duplicate-strings memory problem, the first move is
-XX:+UseStringDeduplication under G1, which shares the backing ARRAYS in the background with no code
change. Not intern(), which is a native call into a shared table.

Practically: equals always, Objects.equals when null is possible, literal first so it can't NPE, and an
ENUM the moment the value set is closed — statuses, types, currencies. If it's an enum, `==` becomes
correct, switch becomes exhaustive, and typos become compile errors. I'd treat any `==` on strings as a
defect even when it currently returns the right answer, because it's a bug that passes its own tests.'""",

"""8. THE CODE, LINE BY LINE

    // ── THE THREE ANSWERS ───────────────────────────────────────────────
    String a = "hello";                 // pooled at class load
    String b = "hello";                 // THE SAME OBJECT. Not a copy.
    System.out.println(a == b);         // true  ← identity, not content

    String c = new String("hello");     // the literal is pooled; `new` makes a
    System.out.println(a == c);         // false    SECOND, unpooled copy of it
    System.out.println(a.equals(c));    // true  ← the question you meant

    String d = "hel";
    String e = d + "lo";                // computed at RUNTIME from a variable
    System.out.println(a == e);         // false
    System.out.println(a == e.intern());// true  ← intern() returns the pooled one

    // ── THE ONE-KEYWORD FLIP ────────────────────────────────────────────
    final String F = "hel";
    System.out.println("hello" == F + "lo");   // TRUE
    //                            ^ a `final` local initialised with a literal is a
    //   COMPILE-TIME CONSTANT, so javac folds the whole expression into "hello".
    String G = "hel";                          // remove `final` ...
    System.out.println("hello" == G + "lo");   // FALSE
    //   ... and it is a runtime concatenation. SAME CODE, OPPOSITE ANSWER.

    // ── THE BUG THAT PASSES ITS OWN TESTS ───────────────────────────────
    if (status == "ACTIVE") { ... }
    // ^ In the unit test, `status` is the literal "ACTIVE" → the same pooled object
    //   → TRUE → the test passes. In production `status` came from Jackson, JDBC or
    //   a request parameter → a fresh object → FALSE → the branch never runs and
    //   nothing throws. The test suite actively certified the bug.
    if ("ACTIVE".equals(status)) { ... }       // correct, and null-safe
    if (status == Status.ACTIVE) { ... }       // better: it was never a string

    // ── THE LOCALE TRAP ─────────────────────────────────────────────────
    "TITLE".toLowerCase().equals("title")
    // ^ FALSE on a machine with a Turkish default locale: the uppercase I lowercases
    //   to a DOTLESS ı. This has broken real authentication code.
    "TITLE".toLowerCase(Locale.ROOT).equals("title")   // correct for protocol tokens
    "TITLE".equalsIgnoreCase("title")                  // better: no allocation either

    // ── WHAT A STRING IS, SINCE JAVA 9 ──────────────────────────────────
    private final byte[] value;        // was char[] — 2 bytes per char, ALWAYS
    private final byte coder;          // LATIN1 (1 byte/char) or UTF16
    private int hash;                  // cached. 0 means "not computed yet", which
    //                                    is why "" recomputed forever until Java 13
    //                                    added a hashIsZero flag.
    // COMPACT STRINGS halved string memory for most applications, invisibly.

    // ── DEDUPLICATION: three tools, different trade-offs ────────────────
    s.intern();                        // JVM-wide pool. Native call, shared table.
    myMap.computeIfAbsent(s, x -> x);  // your own canonical map: faster, bounded,
    //                                    observable, discardable. Usually better.
    // -XX:+UseStringDeduplication     // G1 shares the backing byte[] in the
    //                                    background. NO CODE CHANGE. `==` unaffected
    //                                    because the String objects stay distinct.

    // ── AND THE LOCK THAT IS SECRETLY GLOBAL ────────────────────────────
    synchronized ("lock") { ... }      // interned → SHARED PROCESS-WIDE → unrelated
    //                                    code can be holding it. Never do this.""",

"""9. THE TRACE — following four "hello"s through the JVM

CLASS LOAD. The class file's constant pool contains the literal `"hello"` once. On loading, the JVM
interns it:

    string pool:  { ... , "hello" @0x1000 }

RUNTIME, statement by statement:

    statement                    what is created                  reference     == a ?
    ------------------------------------------------------------------------------------
    String a = "hello";          nothing new — POOL LOOKUP        @0x1000       —
    String b = "hello";          nothing new — the same lookup    @0x1000       TRUE
    String c = new String("h..") pool lookup, THEN a new object   @0x2000       false
                                 copying its contents
    String d = "hel";            pool lookup                      @0x3000       —
    String e = d + "lo";         StringBuilder → new String       @0x4000       false
    e.intern()                   pool lookup: contents match      @0x1000       TRUE
                                 the existing entry, so the
                                 POOLED reference is returned
    ------------------------------------------------------------------------------------
    FOUR DISTINCT OBJECTS. All containing 'h','e','l','l','o'. `equals` is true for every pair;
    `==` is true for exactly two of them, for reasons that have nothing to do with the text.

WHAT javac DID BEFORE ANY OF THIS RAN — the compile-time half:

    source                       class file contains            why
    ------------------------------------------------------------------------------------
    "hel" + "lo"                 the single literal "hello"     both operands are
                                                                compile-time constants
    final String F = "hel";      the literal "hello"            a final local with a
    F + "lo"                                                    constant initialiser IS
                                                                a constant expression
    String G = "hel";            invokedynamic makeConcat...    G is a VARIABLE, so the
    G + "lo"                                                    value is unknown until
                                                                runtime
    ------------------------------------------------------------------------------------
    THE FOLDING IS WHY THE RULE LOOKS INCONSISTENT. Two expressions that are textually identical
    compile to completely different things, and the difference is one `final` keyword.

AND THE PRODUCTION TRACE — the same code in two environments:

    environment    where `status` came from             identity      `status == "ACTIVE"`
    ------------------------------------------------------------------------------------
    unit test      the literal "ACTIVE" in the test     pooled        TRUE  → test passes
    integration    an enum's name(), also folded        pooled        TRUE  → still passes
    production     Jackson parsed it from a byte[]      fresh object  FALSE → branch never
                                                                              runs, silently
    ------------------------------------------------------------------------------------
    THE TEST SUITE CERTIFIED THE BUG. Not by accident — by construction. Test data is written as
    literals, and literals are exactly the case where the broken comparison works. This is the reason
    the rule is "never use `==` on strings" rather than "understand when `==` is safe": the
    understanding does not survive contact with a different data source.

WHAT PRODUCED WHAT:
    THE POOL                produced `a == b`, and therefore produced the false confidence.
    CONSTANT FOLDING        produced the `final` flip — a compile-time decision showing up as a
                            runtime identity.
    RUNTIME CONCATENATION   produced every `false`, and it is what production data always is.
    IMMUTABILITY            is why the pool is safe to exist at all, and why none of these four
                            objects can be corrupted by sharing.""",

"""10. COMPLEXITY, THE MISTAKES, AND THE TAKEAWAY

    `==` is one reference comparison. `equals` is O(n) in the worst case, with a `this == other`
    fast path first — which succeeds constantly on pooled data.
    `hashCode` is O(n) once, then cached in a field.
    Literals and compile-time constant expressions: pooled. Everything computed at runtime: not.
    `intern()`: a native call plus a hash lookup on a shared table (`-XX:StringTableSize`, default
    65536).
    Compact strings (Java 9+): 1 byte per character for Latin-1 content, halving string memory for
    most applications.
    Since Java 7 the pool lives in the heap, so pooled strings can be collected.
    `substring` copies since Java 7u6: O(n) rather than O(1), and no retained-array leak.

THE #1 MISTAKE: `==` on strings. It passes its own tests, because test data is literals, and fails on
production data, which is not.

THE #2 MISTAKE: concluding from `"hel" + "lo" == "hello"` that concatenation is safe. That is constant
FOLDING, and adding or removing one `final` reverses it.

THE #3 MISTAKE: `new String("x")`. Always a distinct object; essentially never useful.

THE #4 MISTAKE: `variable.equals(literal)` when the variable can be null. Put the literal first, or use
`Objects.equals`.

THE #5 MISTAKE: `toLowerCase()` with no locale on a protocol token. The Turkish dotless ı breaks real
comparisons.

THE #6 MISTAKE: comparing user-entered text without Unicode normalisation. Identical-looking accented
characters have multiple encodings and are not `equals`.

THE #7 MISTAKE: `intern()` as the first response to a memory problem. `-XX:+UseStringDeduplication`
needs no code change and shares the arrays, which is where the memory actually is.

THE #8 MISTAKE: `synchronized` on a String. Interned literals are process-wide locks.

THE #9 MISTAKE: passwords in a `String`. Immutable, so unwipeable, and visible in a heap dump.

THE #10 MISTAKE: leaving a closed set of values as strings. An enum makes `==` correct, `switch`
exhaustive, and typos compile errors.

THE #11 MISTAKE: assuming `compareTo` sorts alphabetically. It orders by UTF-16 code unit; human
ordering needs a `Collator`.

ONE-SENTENCE TAKEAWAY: `==` asks whether two references point at the SAME OBJECT, and it returns true
for string literals only because the JVM interns every literal into a shared pool — a fact that has
nothing to do with the characters, that constant folding extends to expressions like `"hel" + "lo"` and
even to `final` locals, and that evaporates the moment the value is computed at runtime, which is what
all production data is; so the comparison passes every test written with literals and silently fails on
the first request parameter, and the rule is `equals` (or `Objects.equals`, or better an enum when the
value set is closed) with no exceptions, because the understanding of when `==` is safe does not survive
a change of data source.""",
]


DEEP["String concatenation in a loop — why it is O(n²) and what to use instead"] = [
"""1. THE GOAL IN PLAIN ENGLISH — the one-line change that is 10,000x

    String result = "";
    for (String row : rows) {
        result += row;        // ← this line
    }

That loop looks linear. It is quadratic, and at any real size it is catastrophic — not "a bit slow", but
minutes instead of milliseconds.

    THE REASON IS THAT STRINGS ARE IMMUTABLE. `result += row` cannot append to `result`, because
    nothing can modify a String. What it actually does is: ALLOCATE A NEW STRING BIG ENOUGH FOR BOTH,
    COPY EVERYTHING ALREADY IN `result` INTO IT, copy `row` on the end, and point `result` at the new
    object. The old one becomes garbage.

    SO EVERY ITERATION COPIES THE ENTIRE ACCUMULATED RESULT. Iteration 1 copies 10 characters,
    iteration 1,000 copies 10,000, iteration 100,000 copies a million. Add those up and you have copied
    roughly n²/2 characters to build a string of length n.

THE ARITHMETIC, because it is more persuasive than any adjective. Appending a 10-character row 100,000
times produces a 1,000,000-character string:

    `+=` in a loop        about 50,000,000,000 characters copied   (and that is the optimistic count)
    StringBuilder         about       2,000,000 characters copied
    ratio                 roughly 25,000 to 1

    THAT IS NOT AN OPTIMISATION. Changing one line takes an operation from "the request times out" to
    "the request completes", and it is probably the single most common genuine performance defect in
    production Java.

THE EVERYDAY VERSION: writing a shopping list where the pen cannot add to an existing sheet. To add one
item you must copy the whole list onto a fresh sheet and then write the new item. Ten items is fine.
Ten thousand items means you have written about fifty million lines to produce a list of ten thousand.

TERMS AS THEY APPEAR:
- IMMUTABLE: cannot be changed after creation. The property that causes all of this.
- StringBuilder: a MUTABLE character buffer. Appending writes into spare capacity in place.
- AMORTISED: the average cost per operation once you spread out the occasional expensive one.""",

"""2. THE INTUITION — why the compiler's help stops at the loop boundary

HERE IS THE PART THAT CONFUSES PEOPLE, AND IT IS WORTH GETTING EXACTLY RIGHT: `javac` DOES OPTIMISE
STRING CONCATENATION. It has since Java 1.0. `"a" + b + "c"` does not create two intermediate strings —
the compiler rewrites it into a single buffered build.

    ON JAVA 8 AND EARLIER it becomes `new StringBuilder().append("a").append(b).append("c").toString()`.
    ON JAVA 9 AND LATER it becomes a single `invokedynamic` to `StringConcatFactory`, which generates a
    method handle chain on first execution — one that can compute the exact final length up front and
    allocate the result array ONCE. For a fixed set of operands this often BEATS hand-written
    StringBuilder code.

    SO WHY IS THE LOOP STILL QUADRATIC? BECAUSE THE OPTIMISATION IS PER-EXPRESSION, AND THE EXPRESSION
    IS INSIDE THE LOOP.

    Each iteration is its own `result + row` expression, so each iteration gets its own fresh builder,
    which starts EMPTY, which means the entire accumulated `result` must be copied into it before `row`
    can be appended. Then `toString()` copies the whole thing out again into the new String.

    TWO FULL COPIES OF THE ACCUMULATED TEXT, PER ITERATION. The compiler cannot hoist the builder out
    of the loop, because between iterations `result` is an ordinary String that other code could
    legally read.

THE FIX IS THEREFORE STRUCTURAL, NOT A TRICK: HOIST THE BUFFER OUT OF THE LOOP YOURSELF.

    StringBuilder sb = new StringBuilder();
    for (String row : rows) sb.append(row);
    String result = sb.toString();

    NOW THERE IS ONE BUFFER FOR THE WHOLE LOOP. Appending writes into spare capacity in place — no copy
    at all in the common case. When capacity runs out the buffer GROWS by roughly doubling, which
    copies, but doubling means the total copying across all growths is O(n), not O(n²). One final copy
    in `toString()`.

WHY DOUBLING MAKES IT LINEAR — the argument worth being able to give:

    growing to 16, 34, 70, 142, ... each growth copies what is currently there. The total copied is
    16 + 34 + 70 + ... which is a geometric series summing to less than 2n. SO THE WHOLE BUILD COPIES
    UNDER 2n CHARACTERS regardless of how many appends there were. Geometric growth is the reason
    `ArrayList.add` is amortised O(1) too — it is the same trick.

AND THE ONE-LINE IMPROVEMENT ON TOP: `new StringBuilder(expectedSize)` removes every growth and every
copy but the final one. When you know the size, this is free.""",

"""3. THE MECHANISM — what StringBuilder is, and what indy concat does

StringBuilder IS A MUTABLE CHARACTER BUFFER — since Java 9 a `byte[]` plus a `coder` flag, exactly like
String, but with the array NOT final and a `count` of how much is used:

    byte[] value;      // the buffer, with SPARE CAPACITY at the end
    int count;         // how much is actually used
    byte coder;        // LATIN1 or UTF16

    append(x)          copies x's characters into value[count..], bumps count. NO other copying.
    ensureCapacity     when the buffer is full, allocate `value.length * 2 + 2` and copy once.
    toString()         ONE copy of the used region into a new String's array.

    NOTE THE `* 2 + 2`. The `+2` exists so that growth still works from a zero-length buffer. Default
    capacity is 16 characters, or 16 + the length of the string if you use the `StringBuilder(String)`
    constructor.

StringBuffer IS THE SAME CLASS WITH `synchronized` ON EVERY METHOD. It predates `StringBuilder`
(which arrived in Java 5) and it is essentially always the wrong choice: a builder is a local variable
in almost every program that exists, so the locking protects nothing. AND EVEN WHEN SHARED IT IS
USUALLY NOT ENOUGH — `sb.append(a).append(b)` is two separate locks, so another thread can interleave
between them. Per-method synchronisation rarely gives you the atomicity you actually wanted.

INVOKEDYNAMIC CONCATENATION (Java 9+), because it explains why the modern answer is subtler:

    `"user=" + name + " id=" + id` compiles to ONE `invokedynamic` instruction naming
    `StringConcatFactory.makeConcatWithConstants`. On first execution, that bootstrap builds a
    MethodHandle chain specialised to those exact operand types, and the JIT then inlines the whole
    thing.

    WHAT THAT BUYS: the length of every operand can be computed FIRST, so the result array is allocated
    exactly once at exactly the right size — no builder, no growth, no intermediate copy. For a fixed
    list of operands this beats writing StringBuilder by hand, which is why "always use StringBuilder"
    is outdated advice for straight-line code.

    WHAT IT CANNOT DO: span a loop. The instruction is inside the loop body, so it runs afresh every
    iteration on the whole accumulated string. THE QUADRATIC PROBLEM IS UNAFFECTED, and it is the only
    problem that matters.

`String.format` AND `formatted` PARSE THE FORMAT STRING ON EVERY CALL — a scan, a `Formatter` object,
and boxing of every argument. Roughly an order of magnitude slower than concatenation. That is
irrelevant in a log line and very relevant in a loop.

`String.concat(s)` is a plain two-way copy with no builder at all. Marginally faster than `+` for
exactly two strings on old JDKs, and it NPEs rather than printing "null".""",

"""4. EDGE CASES AND FAILURE MODES

CASE 1 — `+=` IN A LOOP. The headline. Quadratic, and it is usually written by someone who knows about
StringBuilder but did not notice the loop.

CASE 2 — CONCATENATION INSIDE `append`. `sb.append("a" + x + "b")` builds a temporary string and then
copies it in. Use three appends; the chained form allocates nothing extra.

CASE 3 — UNGUARDED CONCATENATION IN A LOG CALL. `log.debug("state " + expensive())` builds the string
and calls `expensive()` EVEN WHEN DEBUG IS OFF, because arguments are evaluated before the call. Use
parameterised logging: `log.debug("state {}", value)`. THIS IS A REAL HOT-PATH COST IN PRODUCTION
SYSTEMS and it hides behind a disabled log level.

CASE 4 — `String.format` IN A HOT LOOP. Parses the format string every call. Fine for messages, wrong
for bulk output.

CASE 5 — NOT PRE-SIZING WHEN THE SIZE IS KNOWN. Building a 1 MB string from the default 16-character
capacity performs about 17 growth-and-copy cycles.

CASE 6 — SHARING A `StringBuilder` ACROSS THREADS. Not thread-safe; you get interleaved or corrupted
output, or an `ArrayIndexOutOfBoundsException` from `count` and `value` disagreeing.

CASE 7 — `StringBuffer` "FOR SAFETY". Per-method locking that protects nothing in a local variable,
and does not give atomicity across chained appends even when shared.

CASE 8 — `sb.append(null)` APPENDS THE TEXT "null" — four characters — rather than throwing. So does
`+`. `String.concat(null)` throws instead. Three different behaviours for the same idea.

CASE 9 — `sb + ""` OR `"" + x` TO CONVERT TO A STRING. Works, allocates, and obscures intent.
`String.valueOf(x)` is clearer and handles null.

CASE 10 — REUSING A BUILDER WITH `setLength(0)` AND EXPECTING THE MEMORY BACK. The backing array stays
at its high-water mark. Usually that is what you want (no regrowth); occasionally it is a leak.

CASE 11 — BUILDING A DELIMITED LIST WITH A TRAILING-SEPARATOR FIX-UP. The `sb.setLength(sb.length()-1)`
pattern. `String.join` or `Collectors.joining` does it correctly and reads better.

CASE 12 — ASSUMING "ALWAYS USE StringBuilder". For straight-line concatenation on Java 9+, invokedynamic
concat is usually FASTER than a hand-written builder, because it can size the result exactly. The rule
is about LOOPS, not about `+`.

CASE 13 — CONCATENATING IN A `Stream.reduce`. `reduce("", String::concat)` is the same quadratic
behaviour wearing a functional hat. `Collectors.joining()` is linear.""",

"""5. THE ALTERNATIVES — pick by shape, not by habit

STRAIGHT-LINE CONCATENATION OF A FIXED SET OF OPERANDS — just use `+`. On Java 9+ it compiles to
invokedynamic and sizes the result exactly. It is the most readable option AND usually the fastest.
Writing StringBuilder by hand here makes the code worse for no gain.

A LOOP — `StringBuilder`, hoisted out of the loop, pre-sized when you know the size. This is the case
the whole entry exists for.

A DELIMITED LIST — never build it by hand:
    `String.join(", ", list)`                        simplest, for a collection of strings
    `list.stream().map(...).collect(joining(", "))`  when elements need transforming
    `new StringJoiner(", ", "[", "]")`               when you need a prefix, suffix, and an
                                                     "empty value" for the zero-element case
    ALL THREE HANDLE THE SEPARATOR CORRECTLY, which is where the hand-rolled version usually has a
    trailing-comma fix-up bug.

MULTI-LINE LITERAL TEXT — TEXT BLOCKS (Java 15+), delimited by three double-quotes, with the
    incidental indentation stripped for you.
Replaces the `"line\\n" + "line\\n"` pattern entirely, and `.formatted(...)` fills in placeholders.

STREAMING OUTPUT — if the result goes to a file, a socket, or an HTTP response, DO NOT BUILD THE STRING
AT ALL. Write to a `BufferedWriter` or an `OutputStream` as you go. A 500 MB report built in memory is
an OutOfMemoryError; the same report streamed is a constant-memory operation. THE BEST FIX FOR A LARGE
CONCATENATION IS OFTEN TO NOT CONCATENATE.

FORMATTING — `String.format` / `"...".formatted(...)` when readability matters, `MessageFormat` for
localised text with plurals and ordering, and PARAMETERISED LOGGING (`log.debug("x {}", v)`) always, so
disabled levels cost nothing.

CHARACTER-LEVEL WORK — `char[]` or a pre-sized `StringBuilder` with `setCharAt`, when you are doing
transformations rather than appends.

`StringBuffer` — legacy. If you genuinely need a shared mutable buffer you need external
synchronisation for atomicity anyway, so the per-method locking buys nothing.

WHAT TO SAY: "`+` for straight-line concatenation, because on Java 9+ invokedynamic sizes the result
exactly and beats a hand-written builder. StringBuilder the moment there is a LOOP, pre-sized when I
know the size. `String.join` or `Collectors.joining` for delimited output. And if the result is going
to a stream, I would not build the string at all."

""",

"""6. HOW TO GET THIS RIGHT — numbered steps

STEP 1 — LOOK FOR `+=` ON A STRING INSIDE A LOOP. That single pattern is the defect. Everything else in
this entry is refinement.

STEP 2 — HOIST A `StringBuilder` OUT OF THE LOOP. One buffer for the whole loop, `toString()` once at
the end.

STEP 3 — PRE-SIZE IT WHEN YOU KNOW ROUGHLY HOW BIG THE RESULT IS. `new StringBuilder(rows.size() * 40)`
removes every growth and copy but the last.

STEP 4 — DO NOT REWRITE STRAIGHT-LINE `+` INTO A BUILDER. On Java 9+ that makes it slower and less
readable. The rule is about loops.

STEP 5 — USE `String.join` OR `Collectors.joining` FOR DELIMITED OUTPUT. It removes the trailing-
separator bug class entirely.

STEP 6 — USE PARAMETERISED LOGGING, ALWAYS. `log.debug("x {}", v)` costs nothing when the level is off;
`log.debug("x " + v)` builds the string and evaluates the arguments regardless.

STEP 7 — CHAIN `append` CALLS INSTEAD OF CONCATENATING INSIDE ONE. `append(a).append(b)`, not
`append(a + b)`.

STEP 8 — KEEP `String.format` OUT OF HOT LOOPS. It parses the format string on every call.

STEP 9 — IF THE OUTPUT IS GOING SOMEWHERE, STREAM IT. A `BufferedWriter` turns an unbounded memory
requirement into a constant one.

STEP 10 — USE A TEXT BLOCK FOR MULTI-LINE LITERALS. It is both faster (one constant) and far more
readable than a chain of `+ "\n"`.

STEP 11 — NEVER SHARE A `StringBuilder` BETWEEN THREADS. And do not reach for `StringBuffer` as the
fix — it does not give you atomicity across chained calls anyway.

STEP 12 — IF YOU MEASURE, MEASURE AT A REALISTIC SIZE. At 100 iterations the quadratic version looks
fine; the whole problem is that the cost grows with the square, so small tests actively mislead.""",

"""7. THE ANSWER IN PLAIN LANGUAGE — what you would say out loud

'`result += row` in a loop looks linear and is quadratic. Strings are immutable, so `+=` cannot append
to the existing string — it allocates a new one big enough for both, copies everything already there
into it, copies the new piece on the end, and rebinds the variable.

So every iteration copies the whole accumulated result. Iteration one copies 10 characters, iteration
a thousand copies ten thousand, iteration a hundred thousand copies a million. Add those up and you've
copied about n²/2 characters to build a string of length n. Concretely: appending a 10-character row
100,000 times copies roughly fifty billion characters, where a StringBuilder copies about two million.
That's four orders of magnitude, and it turns a request that completes into a request that times out.

Now the part people get wrong in both directions. javac DOES optimise concatenation — it has since 1.0.
`"a" + b + "c"` doesn't build intermediates; on Java 8 it becomes a StringBuilder chain, and on Java 9+
it becomes a single invokedynamic into StringConcatFactory, which builds a method handle chain that
computes every operand's length FIRST and allocates the result array exactly once. For straight-line
concatenation that actually beats a hand-written StringBuilder, so "always use StringBuilder" is
outdated advice.

The reason the loop is still quadratic is that the optimisation is PER-EXPRESSION and the expression is
inside the loop. Each iteration gets its own fresh builder, starting empty, so the whole accumulated
result has to be copied into it before the new piece can be appended — and then toString copies it all
out again. Two full copies per iteration. And the compiler can't hoist the builder out, because between
iterations `result` is an ordinary String that other code could legally read.

Which makes the fix structural rather than a trick: hoist the buffer out yourself. Then there's one
buffer for the whole loop, appends write into spare capacity in place, and when it runs out it grows by
roughly doubling. Doubling is what makes it linear — the growths copy 16, then 34, then 70, a geometric
series that sums to under 2n. Same reason ArrayList.add is amortised O(1).

So my actual rule is: `+` for straight-line concatenation, because it's the most readable AND usually
the fastest on a modern JDK. StringBuilder the moment there's a loop, pre-sized if I know the size.
String.join or Collectors.joining for anything delimited, because the hand-rolled version always has
the trailing-comma fix-up. And parameterised logging always — `log.debug("x " + v)` builds the string
and evaluates the arguments even when debug is off, which is a real hot-path cost hiding behind a
disabled log level.

One more: if the result is going to a file or an HTTP response, I'd push back on building the string at
all. Streaming to a BufferedWriter turns an unbounded memory requirement into a constant one, and a
500 MB report built in memory is an OutOfMemoryError.'""",

"""8. THE CODE, LINE BY LINE

    // ── THE DEFECT ──────────────────────────────────────────────────────
    String result = "";
    for (String row : rows) {
        result += row;
    //  ^^^^^^^^^^^^^ Strings are IMMUTABLE, so this cannot append. It:
    //    1. allocates a StringBuilder (a fresh one, this iteration only)
    //    2. copies ALL of `result` into it              ← the whole accumulated text
    //    3. appends `row`
    //    4. toString() — copies it ALL out again        ← a second full copy
    //    5. the previous `result` becomes garbage
    //  TWO FULL COPIES PER ITERATION, of a string that grows every time.
    }

    // ── WHY THE COMPILER CANNOT SAVE YOU ────────────────────────────────
    // javac DOES optimise concatenation — this is not a naive compiler:
    //   Java 8:  new StringBuilder().append(a).append(b).toString()
    //   Java 9+: invokedynamic → StringConcatFactory.makeConcatWithConstants
    //            which sizes the result array EXACTLY and allocates once.
    // But the optimisation is PER EXPRESSION, and the expression is INSIDE the loop.
    // Between iterations `result` is an ordinary String other code could read, so
    // the builder cannot be hoisted. THE OPTIMISATION IS REAL AND IRRELEVANT HERE.

    // ── THE FIX: hoist the buffer yourself ──────────────────────────────
    StringBuilder sb = new StringBuilder(rows.size() * 40);
    //                                   ^^^^^^^^^^^^^^^^ pre-size when you can:
    //   removes every growth-and-copy but the final toString().
    for (String row : rows) sb.append(row);
    //                         ^^^^^^ writes into SPARE CAPACITY in place. No copy.
    String result = sb.toString();      // exactly ONE copy, at the end

    // ── WHY DOUBLING MAKES IT LINEAR ────────────────────────────────────
    // ensureCapacity: newLength = value.length * 2 + 2   (the +2 lets a 0-length
    //                                                     buffer still grow)
    // growths copy 16, then 34, then 70, then 142 ... a geometric series that sums
    // to UNDER 2n. So the whole build copies < 2n characters no matter how many
    // appends. Same trick as ArrayList.add being amortised O(1).

    // ── THE STRAIGHT-LINE CASE: do NOT "fix" this ───────────────────────
    String s = "user=" + name + " id=" + id;        // ← CORRECT and usually FASTEST
    // On Java 9+ this is one invokedynamic that computes every operand's length
    // first and allocates the result once. Rewriting it as a StringBuilder chain
    // makes it slower AND less readable. The rule is about LOOPS.

    // ── CONCATENATION INSIDE AN APPEND ──────────────────────────────────
    sb.append("name=" + n + ";");     // builds a TEMPORARY string, then copies it in
    sb.append("name=").append(n).append(';');   // ← nothing extra allocated
    //                                 ^^^ note the CHAR literal: append(char) skips
    //                                 the string-length-and-copy path entirely.

    // ── THE LOG LINE THAT COSTS YOU WHEN DEBUG IS OFF ───────────────────
    log.debug("state " + expensive());
    // ^ ARGUMENTS ARE EVALUATED BEFORE THE CALL. The concatenation runs and
    //   expensive() runs, then the method returns immediately because debug is
    //   disabled. A real hot-path cost hiding behind a disabled log level.
    log.debug("state {}", value);      // ← formats ONLY if the level is enabled

    // ── DELIMITED OUTPUT: never hand-roll it ────────────────────────────
    for (String x : list) { sb.append(x).append(", "); }
    sb.setLength(sb.length() - 2);     // ← and this throws on an EMPTY list
    String.join(", ", list);                                  // correct, one line
    list.stream().map(X::name).collect(Collectors.joining(", "));  // with transform
    new StringJoiner(", ", "[", "]").setEmptyValue("[]");     // prefix/suffix/empty

    // ── AND THE FIX THAT IS BETTER THAN ANY OF THEM ─────────────────────
    try (var out = new BufferedWriter(new FileWriter(f))) {
        for (String row : rows) out.write(row);
    }   // ^ CONSTANT MEMORY. A 500 MB report built in a String is an OOM; streamed,
        //   it is a non-event. The best fix for a big concatenation is not to do it.""",

"""9. THE TRACE — the same build, three ways

APPENDING A 10-CHARACTER ROW 100,000 TIMES, producing a 1,000,000-character string. Counting characters
copied, which is arithmetic rather than a measurement:

    `+=` IN A LOOP
    iteration   accumulated length   characters copied this iteration
    ---------------------------------------------------------------------------
    1           0                    10        (copy 0 in, append 10, copy 10 out)
    1,000       10,000               ~20,000
    10,000      100,000              ~200,000
    100,000     1,000,000            ~2,000,000
    ---------------------------------------------------------------------------
    TOTAL ≈ 2 × Σ(10i) for i = 1..100,000 ≈ 100,000,000,000 characters copied,
    plus ~200,000 objects allocated, to produce 1,000,000 characters of output.

    StringBuilder, PRE-SIZED
    ---------------------------------------------------------------------------
    100,000 appends, each writing 10 characters into spare capacity   1,000,000
    one toString() copy                                               1,000,000
    TOTAL = 2,000,000 characters copied. Two objects allocated.

    StringBuilder, DEFAULT CAPACITY
    ---------------------------------------------------------------------------
    the same 1,000,000 appended, plus growth copies of
    16 + 34 + 70 + 142 + ... + ~1,048,576                            ≈ 2,000,000
    one toString() copy                                               1,000,000
    TOTAL ≈ 4,000,000. Still linear — the geometric series sums to under 2n.

    THE RATIO BETWEEN ROW 1 AND ROW 2 IS ABOUT 50,000 TO 1. And notice the shape: the quadratic version
    is not "slower per character", it is doing a fundamentally different amount of work, and the gap
    WIDENS with n. At 1,000 iterations it is 500x; at 100,000 it is 50,000x. WHICH IS WHY A SMALL
    BENCHMARK ACTIVELY MISLEADS.

WHAT THE COMPILER PRODUCED, per Java version — the part that explains why the optimisation does not
help:

    source                     Java 8 bytecode              Java 9+ bytecode
    ---------------------------------------------------------------------------------
    "a" + b + "c"              ONE StringBuilder chain      ONE invokedynamic, exact
    (straight line)            for the whole expression     size, single allocation
    result += row              a NEW StringBuilder,         a NEW invokedynamic call,
    (inside a loop)            EVERY ITERATION              EVERY ITERATION
    ---------------------------------------------------------------------------------
    BOTH ROWS ARE THE SAME OPTIMISATION. It is scoped to an expression, and the loop creates a new
    expression evaluation each time round. Nothing in either compiler can carry the buffer across
    iterations, because `result` is observable between them.

AND THE MEMORY TRACE, which is the failure people actually hit:

    approach                    peak heap for a 500 MB report
    ---------------------------------------------------------------------------------
    `+=` in a loop              ~1 GB live at the end (old + new during the last copy),
                                plus ~500 GB of cumulative garbage churned through GC
    StringBuilder               ~1 GB (the buffer plus the toString copy)
    stream to a BufferedWriter  ~8 KB
    ---------------------------------------------------------------------------------
    THE THIRD ROW IS THE REAL ANSWER FOR LARGE OUTPUT. StringBuilder fixes the time complexity and
    leaves the space complexity at O(n); writing as you go fixes both. The best version of this
    optimisation is noticing that the string never needed to exist.

WHAT PRODUCED WHAT:
    IMMUTABILITY             produced the copy-per-iteration, and therefore the whole problem.
    PER-EXPRESSION SCOPING   produced "the compiler optimises this and it does not help".
    GEOMETRIC GROWTH         produced the linear total in rows 2 and 3 — the same reason
                             `ArrayList.add` is amortised O(1).""",

"""10. COMPLEXITY, THE MISTAKES, AND THE TAKEAWAY

    `+=` in a loop: O(n²) time in characters copied, O(n) garbage objects.
    `StringBuilder`: O(n) total, amortised O(1) per append; growth is `len * 2 + 2`, default
    capacity 16.
    Pre-sized `StringBuilder`: exactly one copy, in `toString()`.
    Straight-line `+` on Java 9+: one `invokedynamic`, result array sized exactly, one allocation —
    typically FASTER than a hand-written builder.
    `String.format`: parses the format string per call, roughly an order of magnitude slower than `+`.
    `String.join` / `Collectors.joining`: linear, and correct about separators.
    Streaming to a writer: O(1) space.

THE #1 MISTAKE: `+=` on a String inside a loop. Quadratic, and it is the most common genuine
performance defect in production Java.

THE #2 MISTAKE: concluding the compiler will fix it. It optimises the EXPRESSION, and the expression is
inside the loop.

THE #3 MISTAKE: over-correcting and rewriting straight-line `+` into StringBuilder. On Java 9+ that is
slower and less readable.

THE #4 MISTAKE: not pre-sizing when the size is known. About 17 growth cycles to reach a megabyte.

THE #5 MISTAKE: `sb.append(a + b)`. Builds a temporary and copies it in. Chain the appends.

THE #6 MISTAKE: unguarded concatenation in a log call. The string is built and the arguments evaluated
even when the level is disabled. Parameterised logging.

THE #7 MISTAKE: `String.format` in a hot loop.

THE #8 MISTAKE: hand-rolling delimited output and fixing up the trailing separator — which also throws
on an empty list. `String.join` or `Collectors.joining`.

THE #9 MISTAKE: `reduce("", String::concat)` in a stream. The same quadratic behaviour in functional
clothing. `Collectors.joining()`.

THE #10 MISTAKE: sharing a `StringBuilder` across threads, or reaching for `StringBuffer` as the fix —
per-method locking gives no atomicity across chained appends.

THE #11 MISTAKE: building a huge string in memory when it is going straight to a stream. Fixing the
time complexity while leaving the space complexity at O(n) is only half the fix.

THE #12 MISTAKE: benchmarking at a small n. The gap grows with n, so a small test says "it's fine" about
something that is not.

ONE-SENTENCE TAKEAWAY: strings are immutable, so `result += row` cannot append — it copies the entire
accumulated string into a fresh buffer and then out again, twice per iteration, making the loop O(n²)
and turning a hundred thousand appends into roughly a hundred billion character copies; the compiler's
concatenation optimisation is real (and on Java 9+ an `invokedynamic` that sizes the result exactly,
which is why straight-line `+` should be left alone) but it is scoped to an EXPRESSION and cannot cross
a loop boundary, so the fix is to hoist a `StringBuilder` out of the loop and pre-size it — or better,
for large output, to stream it to a writer and never build the string at all.""",
]
