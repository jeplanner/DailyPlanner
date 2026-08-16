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
