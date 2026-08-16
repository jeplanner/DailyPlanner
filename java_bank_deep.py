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
