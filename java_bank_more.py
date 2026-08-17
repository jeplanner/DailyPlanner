"""Java bank — strings, collections and primitives.

The first of two modules filling out the thin rungs. The bank had two
string entries and five collection entries, which is not enough for
either: strings are where the == trap lives and collections are where
half of every Java interview is spent.

NO JDK ON THE BUILD MACHINE, so unlike sql_bank these outputs cannot be
machine-verified. Every one here is behaviour specified in the JLS or in
the class's own contract, and where a result depends on the VM (identity
hash codes, HashMap iteration order, string interning of computed values)
the entry says so rather than printing a number that would be a lie on
another machine.
"""


def build(Q):
    return [

    # ══════════════════ STRINGS ══════════════════

    Q("strings", "== compares references; .equals compares characters",
      "Two strings that read the same are not necessarily the same object. "
      "== asks 'are these the same object in memory'. .equals asks 'do these "
      "hold the same characters'. For text you almost always mean the second.",
      "String literals are INTERNED: the compiler puts identical literals in a "
      "shared pool, so `\"hi\" == \"hi\"` is true. `new String(\"hi\")` "
      "explicitly allocates a fresh object, so it is == to nothing but itself. "
      "Anything computed at RUNTIME — concatenation of variables, substring, "
      "reading input — produces a new object that is not in the pool unless you "
      "call .intern() yourself.",
      ["strings", "equality", "string-pool"],
      code='String a = "hello";\n'
           'String b = "hello";                 // same literal -> same pooled object\n'
           'String c = new String("hello");     // explicitly a new object\n'
           'String d = "hel" + "lo";            // folded by the COMPILER -> pooled\n'
           'String part = "hel";\n'
           'String e = part + "lo";             // computed at RUNTIME -> new object\n'
           '\n'
           'System.out.println(a == b);\n'
           'System.out.println(a == c);\n'
           'System.out.println(a == d);\n'
           'System.out.println(a == e);\n'
           'System.out.println(a.equals(e));\n'
           'System.out.println(a == e.intern());',
      output="true\nfalse\ntrue\nfalse\ntrue\ntrue",
      gotcha="Line 4 is the one that catches people. `\"hel\" + \"lo\"` is TRUE because "
             "both halves are compile-time constants, so javac folds them into a single "
             "literal before the pool ever sees them. Make one half a variable and the "
             "concatenation happens at runtime, producing a new object — same characters, "
             "different answer.",
      quiz={
        "q": "Given `String s1 = \"java\"; final String p = \"ja\"; String s2 = p + \"va\";` "
             "what does `s1 == s2` print?",
        "options": [
          "true — p is final, so the expression is a compile-time constant and gets folded",
          "false — any concatenation happens at runtime",
          "It does not compile — you cannot concatenate a final variable",
          "true, but only because both strings have the same hash code",
        ],
        "answer": 0,
        "why": "Option A is right, and it is the subtle case: a `final` local initialised "
               "with a constant IS a compile-time constant, so javac folds `p + \"va\"` "
               "into the literal \"java\" and it comes from the pool. Option B is the "
               "answer for a NON-final variable, which is why removing `final` flips this "
               "to false — that difference is the whole question. Option C invents a rule; "
               "final variables concatenate like any other. Option D confuses == with "
               "hashing: equal hash codes do not imply identity, and == never consults a "
               "hash code.",
      },
      pitfalls="`==` on boxed Integers has the same shape of bug for a different reason "
               "(the -128..127 cache). The rule that covers both: use == for primitives "
               "and .equals for objects, every time, and let the one case where == would "
               "have worked cost you nothing.",
      followups="Why does the pool exist at all? Strings are immutable and enormously "
                "common, so sharing identical literals saves real memory. Since Java 7 "
                "the pool lives on the heap rather than in PermGen, which is why "
                "intern()-heavy code stopped causing PermGen OOMs.",
      difficulty="Easy", frequency="Asked in almost every Java interview",
      mnemonic="Literals are shared. Anything computed at runtime is new. Use .equals."),

    Q("strings", "Strings are immutable, and why that makes += in a loop O(n²)",
      "A String never changes. Every operation that looks like it modifies one "
      "actually builds a new one and throws the old away. In a loop that means "
      "copying everything you have so far, on every single iteration.",
      "String is immutable, so `s += x` compiles to building a new String whose "
      "contents are the old one plus x. Doing that n times copies 1 + 2 + 3 + ... "
      "+ n characters, which is O(n²). StringBuilder keeps a growable char array "
      "and appends in amortised O(1), making the same loop O(n). Javac optimises "
      "concatenation in a SINGLE expression into one StringBuilder — but it "
      "cannot do that across loop iterations, which is exactly where it matters.",
      ["strings", "immutability", "stringbuilder", "performance"],
      code='String s = "";\n'
           'for (int i = 0; i < 5; i++) {\n'
           '    s += i;                      // a NEW String each time\n'
           '}\n'
           'System.out.println(s);\n'
           '\n'
           'StringBuilder sb = new StringBuilder();\n'
           'for (int i = 0; i < 5; i++) {\n'
           '    sb.append(i);                // mutates one buffer\n'
           '}\n'
           'System.out.println(sb.toString());\n'
           '\n'
           'String t = "a";\n'
           't.concat("b");                   // return value DISCARDED\n'
           'System.out.println(t);',
      output="01234\n01234\na",
      gotcha="The last three lines are the immutability trap in its purest form. "
             "`t.concat(\"b\")` computes \"ab\" and RETURNS it — it cannot change t, "
             "because nothing can change a String. The result is dropped on the floor "
             "and t is still \"a\". Every String method behaves this way: "
             "toUpperCase, trim, replace, substring. If you did not assign the result, "
             "nothing happened.",
      quiz={
        "q": "Why is `s += x` in a loop O(n²) when javac is known to optimise string "
             "concatenation into StringBuilder?",
        "options": [
          "The optimisation applies within one expression; each iteration is a separate "
          "expression, so a new builder is created and discarded every time",
          "Javac does not optimise concatenation at all — that is a myth",
          "Because String.concat is synchronized and the lock dominates",
          "Because the string pool must be searched on every concatenation",
        ],
        "answer": 0,
        "why": "Option A is right: javac rewrites `a + b + c` in ONE expression into a "
               "single builder, but a loop body is re-entered each iteration, so it "
               "builds, appends, and calls toString() every time — and toString copies "
               "the whole accumulated array. Option B is wrong; the single-expression "
               "optimisation is real and is why `\"a\" + b + \"c\"` is not slow. Option C "
               "invents a lock: String.concat is not synchronized, and it is StringBuffer "
               "(not StringBuilder) that is. Option D confuses interning with "
               "concatenation — the pool is only consulted for literals and explicit "
               "intern() calls.",
      },
      pitfalls="StringBuilder is NOT thread-safe; StringBuffer is, and pays a lock per "
               "call for it. A builder is almost always a local variable, so almost "
               "always the right choice — reaching for StringBuffer 'to be safe' is "
               "paying for synchronisation nobody contends.",
      followups="Since Java 9, `+` on strings compiles to an invokedynamic call handled "
                "by StringConcatFactory rather than to explicit StringBuilder code, which "
                "lets the JVM pick a strategy at runtime. It does not change the loop "
                "problem: the concatenation is still per-iteration.",
      difficulty="Easy", frequency="Very common, often as 'optimise this loop'",
      mnemonic="Every String method RETURNS a new string. If you did not assign it, "
               "nothing happened."),

    Q("strings", "split() drops trailing empty strings unless you ask it not to",
      "Splitting \"a,b,,\" on a comma gives you two pieces, not four. The empty "
      "pieces at the END are thrown away by default, which quietly changes the "
      "length of your array.",
      "`split(regex)` is `split(regex, 0)`, and a limit of 0 means 'apply the "
      "pattern as many times as possible AND discard trailing empty strings'. A "
      "NEGATIVE limit applies the pattern as many times as possible and keeps "
      "them. A POSITIVE limit n applies the pattern at most n-1 times, so the "
      "last element holds the entire remainder including any delimiters.",
      ["strings", "split", "regex"],
      code='String csv = "a,b,,,";\n'
           'System.out.println(csv.split(",").length);      // trailing empties dropped\n'
           'System.out.println(csv.split(",", -1).length);  // kept\n'
           'System.out.println(csv.split(",", 2).length);   // at most 1 split\n'
           'System.out.println(csv.split(",", 2)[1]);       // the whole remainder\n'
           '\n'
           'System.out.println(",a".split(",").length);     // LEADING empty is kept\n'
           'System.out.println("a.b".split(".").length);    // "." is a regex!\n'
           'System.out.println("a.b".split("\\\\.").length);',
      output="2\n5\n2\nb,,,\n2\n0\n2",
      gotcha="Two separate traps in one entry. The trailing empties vanish but the "
             "LEADING one does not — `\",a\".split(\",\")` gives [\"\", \"a\"], length 2. "
             "And `split(\".\")` returns an EMPTY ARRAY, because the argument is a REGEX "
             "and `.` matches every character, so every piece is an empty trailing string "
             "and all of them are discarded. Parsing a version number or a filename with "
             "split(\".\") is a classic and it fails silently by returning nothing.",
      quiz={
        "q": "What is the length of `\"a.b.c\".split(\".\")`?",
        "options": [
          "0 — '.' is a regex matching any character, so every piece is empty and all "
          "trailing empties are discarded",
          "3 — it splits on the literal dots",
          "5 — it splits between every character",
          "It throws PatternSyntaxException",
        ],
        "answer": 0,
        "why": "Option A is right and it is why this is a trap rather than a detail: the "
               "argument is a regular expression, `.` matches everything, so the result "
               "is five empty strings — all of them trailing — and the default limit of 0 "
               "discards the lot. Option B is what everyone expects and requires escaping "
               "to `\\\\.` to get. Option C describes what would happen if empties were "
               "kept, i.e. with a negative limit. Option D is wrong: `.` is a perfectly "
               "valid pattern, which is exactly the problem — nothing errors.",
      },
      pitfalls="For a fixed single character, `String.split` still compiles a Pattern "
               "unless the JDK's fast path applies (a one-char non-metacharacter). "
               "Splitting in a hot loop on a metacharacter is worth hoisting into a "
               "precompiled `Pattern` and calling `pattern.split`.",
      followups="What does an empty input give? `\"\".split(\",\")` returns an array of "
                "ONE empty string, not an empty array — the special case that catches "
                "code counting fields.",
      difficulty="Medium", frequency="Common, and a real source of production bugs",
      mnemonic="split takes a REGEX and drops trailing empties. Use -1 to keep them, "
               "and escape your dots."),

    Q("strings", "StringBuilder vs StringBuffer vs String.join",
      "Three ways to build a string. One is for a single thread and is what you "
      "want; one adds locking you almost never need; one is for the common case "
      "of joining a list with a separator and is a single call.",
      "StringBuilder is the unsynchronized, faster builder — introduced in Java 5 "
      "precisely because StringBuffer's synchronisation was almost always "
      "uncontended overhead. StringBuffer is identical but every method is "
      "synchronized. String.join and Collectors.joining handle the "
      "separator-between-elements case without the off-by-one that hand-rolled "
      "loops produce. All three build the same result; the choice is about "
      "threading and about how much fencepost logic you want to write.",
      ["strings", "stringbuilder", "join"],
      code='StringBuilder sb = new StringBuilder();\n'
           'sb.append("a").append(1).append(true).append(\'x\');\n'
           'System.out.println(sb);\n'
           'System.out.println(sb.reverse());        // MUTATES, then returns this\n'
           'System.out.println(sb);\n'
           '\n'
           'System.out.println(String.join("-", "a", "b", "c"));\n'
           'System.out.println(String.join(",", java.util.List.of()));\n'
           '\n'
           'StringBuilder n = new StringBuilder();\n'
           'n.append((String) null);                  // the null-append trap\n'
           'System.out.println(n.length());',
      output="a1truex\nxeurt1a\nxeurt1a\na-b-c\n\n4",
      gotcha="Two things. `reverse()` MUTATES the builder and also returns it, so the "
             "third println shows the reversed value — the builder was changed by a call "
             "that looks like it returns a copy. And `append(null)` appends the four "
             "characters \"null\" rather than throwing or appending nothing, so a null "
             "field silently becomes the text 'null' in your output.",
      quiz={
        "q": "`sb.append(x)` where x is a null String reference. What happens?",
        "options": [
          "The four characters n-u-l-l are appended",
          "NullPointerException",
          "Nothing is appended and the builder is unchanged",
          "An empty string is appended, so the length is unchanged",
        ],
        "answer": 0,
        "why": "Option A is right: append is specified to append the string \"null\" for "
               "a null argument, which is why user-facing output sometimes contains the "
               "literal word null. Option B is what most people guess, and it is what "
               "`sb.append(x.trim())` would throw — the NPE comes from touching the "
               "reference, not from appending it. Options C and D describe the same "
               "wrong behaviour two ways; both would leave length at 0, and it is 4.",
      },
      pitfalls="Pre-size the builder when you know roughly how big the result will be: "
               "`new StringBuilder(1024)` avoids the repeated array copies that growing "
               "from the default 16 causes. Only worth it in a hot path.",
      followups="Why is StringBuffer still in the JDK? Backwards compatibility — it "
                "shipped in 1.0. There is no case where new code should prefer it: if "
                "two threads share a builder you have a design problem that a lock per "
                "append does not solve.",
      difficulty="Easy", frequency="Common",
      mnemonic="StringBuilder unless two threads share it, which they should not. "
               "String.join for separators."),

    Q("strings", "substring() and the memory leak that used to be",
      "Taking a small piece of a huge string used to keep the huge string alive "
      "in memory. It was fixed in Java 7, and it is still asked about because "
      "the fix has its own cost.",
      "Before Java 7u6, String held (char[] value, int offset, int count) and "
      "substring() returned a new String SHARING the original array — O(1), and "
      "a 10-character substring of a 100 MB string kept all 100 MB reachable. "
      "Since 7u6, substring COPIES the characters: the leak is gone and "
      "substring became O(n) instead of O(1). Code written for the old behaviour "
      "that took thousands of substrings in a loop got measurably slower.",
      ["strings", "substring", "memory", "history"],
      code='String big = "abcdefghij";\n'
           'String small = big.substring(2, 5);\n'
           'System.out.println(small);\n'
           'System.out.println(small.length());\n'
           '\n'
           '// endIndex is EXCLUSIVE, and equal indices are legal\n'
           'System.out.println("[" + big.substring(3, 3) + "]");\n'
           'System.out.println(big.substring(10).isEmpty());   // start == length is legal\n'
           '\n'
           'try {\n'
           '    big.substring(11);\n'
           '} catch (StringIndexOutOfBoundsException e) {\n'
           '    System.out.println("caught");\n'
           '}',
      output="cde\n3\n[]\ntrue\ncaught",
      gotcha="`substring(10)` on a 10-character string is LEGAL and returns \"\" — "
             "start == length is the one out-of-range-looking index that is allowed, "
             "because it means 'everything from the end', which is nothing. "
             "`substring(11)` throws. Off-by-one code that guards with `< length` "
             "instead of `<= length` rejects a valid empty result.",
      quiz={
        "q": "What changed about String.substring in Java 7u6?",
        "options": [
          "It began COPYING the characters instead of sharing the original array — "
          "fixing a memory leak and making it O(n) rather than O(1)",
          "It began sharing the original array to make it O(1)",
          "It started throwing on a negative index, which previously wrapped",
          "Nothing changed; the leak was in StringBuilder",
        ],
        "answer": 0,
        "why": "Option A is right, and the trade is the point: the leak went away and the "
               "operation got asymptotically slower. Option B has the direction backwards "
               "— sharing is what the OLD implementation did and what caused the leak. "
               "Option C invents a change; a negative index has always thrown "
               "StringIndexOutOfBoundsException. Option D misattributes it: StringBuilder "
               "never shared its array with a String, because toString() has always "
               "copied.",
      },
      pitfalls="If you genuinely need many substrings of one large string and the memory "
               "is fine, keep indices rather than Strings — a (start, end) pair into the "
               "original costs 8 bytes where a copied substring costs its own characters.",
      difficulty="Medium", frequency="A history question, but a common one",
      mnemonic="Old: shared the array, leaked, O(1). New: copies, safe, O(n)."),

    # ══════════════════ COLLECTIONS ══════════════════

    Q("collections", "ArrayList vs LinkedList — the answer is almost always ArrayList",
      "One stores items in a single block of memory; the other stores each item "
      "separately with pointers between them. The textbook says the second is "
      "faster for inserting in the middle. In practice the first wins nearly "
      "always, and the reason is not in the big-O.",
      "ArrayList is a growable array: O(1) indexed access, O(n) insert or remove "
      "in the middle (it shifts), amortised O(1) append. LinkedList is a doubly "
      "linked list: O(1) insert or remove GIVEN A NODE, O(n) to find that node, "
      "and O(n) indexed access. The catch is that LinkedList's O(1) insert "
      "requires you to already be at the position, which for anything except an "
      "explicit ListIterator means walking there first — and each node is a "
      "separate heap object, so traversal misses the CPU cache on every step "
      "while an array walk is a linear prefetch.",
      ["collections", "list", "performance", "data-structures"],
      code='java.util.List<Integer> a = new java.util.ArrayList<>();\n'
           'java.util.List<Integer> l = new java.util.LinkedList<>();\n'
           'for (int i = 0; i < 5; i++) { a.add(i); l.add(i); }\n'
           '\n'
           'System.out.println(a.get(3) + " " + l.get(3));   // same answer\n'
           'System.out.println(a);\n'
           '\n'
           'a.add(2, 99);          // shifts everything after index 2\n'
           'System.out.println(a);\n'
           '\n'
           'System.out.println(a.remove(Integer.valueOf(99)));  // by VALUE\n'
           'System.out.println(a.remove(0));                    // by INDEX\n'
           'System.out.println(a);',
      output="3 3\n[0, 1, 2, 3, 4]\n[0, 1, 99, 2, 3, 4]\ntrue\n0\n[1, 2, 3, 4]",
      gotcha="`remove(int)` removes by INDEX and `remove(Object)` removes by VALUE, and "
             "for a `List<Integer>` both overloads apply. `list.remove(2)` removes the "
             "element AT index 2; `list.remove(Integer.valueOf(2))` removes the element "
             "EQUAL to 2. The compiler picks by static type with no warning, and on a "
             "list of integers the two do completely different things.",
      quiz={
        "q": "On a `List<Integer>` containing [10, 20, 30], what does `list.remove(1)` "
             "leave behind?",
        "options": [
          "[10, 30] — the int overload is preferred, so it removes by INDEX",
          "[10, 20, 30] — there is no element equal to 1, so nothing is removed",
          "[20, 30] — it removes the first element",
          "It does not compile — the call is ambiguous",
        ],
        "answer": 0,
        "why": "Option A is right: `remove(int)` is an exact match for the literal 1 and "
               "Java prefers it over boxing to `remove(Object)`, so index 1 (the value "
               "20) goes. Option B is what `remove(Integer.valueOf(1))` would do and is "
               "the behaviour people expect. Option C is what index 0 would remove. "
               "Option D is wrong and it is the interesting part — the call is NOT "
               "ambiguous, javac resolves it silently in favour of the primitive, which "
               "is why the bug is invisible at the call site.",
      },
      pitfalls="LinkedList's genuine niche is a Deque used as a queue, and even there "
               "ArrayDeque beats it on both memory and speed. If you find yourself "
               "reaching for LinkedList, the question to ask is whether you actually want "
               "an ArrayDeque.",
      followups="When does the middle-insert argument hold? When you already hold a "
                "ListIterator at the position and are inserting many times — a rope or "
                "an LRU implementation. That is a narrow enough case that the JDK's own "
                "LinkedHashMap uses a linked list only for iteration order, not for "
                "lookup.",
      difficulty="Easy", frequency="Extremely common",
      mnemonic="ArrayList unless proven otherwise. LinkedList's O(1) insert needs a node "
               "you do not have."),

    Q("collections", "The hashCode / equals contract, and what breaks when you break it",
      "If two objects are equal they must return the same hash code. Override "
      "one without the other and your object works everywhere except inside a "
      "HashMap or HashSet, where it silently disappears.",
      "The contract: equal objects must have equal hash codes; unequal objects "
      "MAY share one (a collision). A HashMap finds a key by hashing to a bucket "
      "and then calling equals within it, so an object whose hashCode was not "
      "overridden hashes to a bucket derived from its identity — a fresh, equal "
      "object hashes elsewhere and the lookup misses. Overriding hashCode "
      "without equals is the reverse: two equal-hashing objects land in the same "
      "bucket and are then compared by identity, so they are treated as "
      "different keys.",
      ["collections", "hashmap", "equals", "hashcode"],
      code='class P {\n'
           '    final String n;\n'
           '    P(String n) { this.n = n; }\n'
           '    @Override public boolean equals(Object o) {\n'
           '        return o instanceof P && ((P) o).n.equals(n);\n'
           '    }\n'
           '    // hashCode DELIBERATELY not overridden\n'
           '}\n'
           '\n'
           'java.util.Set<P> set = new java.util.HashSet<>();\n'
           'set.add(new P("ana"));\n'
           'System.out.println(set.contains(new P("ana")));\n'
           'System.out.println(new P("ana").equals(new P("ana")));\n'
           'set.add(new P("ana"));\n'
           'System.out.println(set.size());',
      output="false\ntrue\n2",
      gotcha="The two objects ARE equal — the second line proves it — and the set "
             "contains neither of the other. Worse, adding the second one succeeds, so a "
             "Set that is supposed to hold unique elements now holds two things that are "
             "equal to each other. Nothing throws, nothing warns, and the bug surfaces as "
             "a duplicate in a report months later.",
      quiz={
        "q": "A class overrides hashCode() to `return 1` for every instance but "
             "implements equals() correctly. What is the consequence?",
        "options": [
          "It is CORRECT but degenerate — every key lands in one bucket, so HashMap "
          "lookups degrade toward O(n)",
          "It is incorrect — the contract requires distinct objects to have distinct "
          "hash codes",
          "HashMap will throw IllegalStateException on the second insert",
          "Lookups will silently miss, the same as not overriding hashCode at all",
        ],
        "answer": 0,
        "why": "Option A is right: the contract only says EQUAL objects must hash "
               "equally, so a constant is legal and merely terrible — everything "
               "collides. (Since Java 8 an over-full bucket treeifies, so it degrades "
               "toward O(log n) rather than O(n) for Comparable keys.) Option B states "
               "the contract backwards; collisions are explicitly permitted. Option C "
               "invents an exception. Option D describes the OPPOSITE failure — that is "
               "what happens when hashCode is not overridden and equals is, which is the "
               "code in this entry.",
      },
      pitfalls="Both methods must use the same fields, and those fields should be "
               "effectively immutable. Mutating a field that hashCode reads AFTER the "
               "object is a key in a map moves it to a bucket the map will never look in "
               "— it is present, and unreachable.",
      followups="Records generate both from the components automatically, which removes "
                "this entire class of bug for value types and is a real reason to prefer "
                "them.",
      difficulty="Medium", frequency="Very common",
      mnemonic="Override one, override both, from the same immutable fields."),

    Q("collections", "Arrays.asList, List.of and the three kinds of unmodifiable",
      "There are several ways to make a list from a few values, and they behave "
      "differently when you try to change them. One is fixed-size but writable, "
      "one is fully immutable and rejects nulls, and one is a copy.",
      "`Arrays.asList(...)` returns a FIXED-SIZE view backed by the array: set() "
      "works and writes through to the array, add() and remove() throw "
      "UnsupportedOperationException. `List.of(...)` (Java 9+) is genuinely "
      "immutable, rejects null elements with NullPointerException, and rejects "
      "null lookups too. `new ArrayList<>(Arrays.asList(...))` is an independent, "
      "fully mutable copy.",
      ["collections", "list", "immutability", "arrays"],
      code='Integer[] arr = {1, 2, 3};\n'
           'java.util.List<Integer> view = java.util.Arrays.asList(arr);\n'
           '\n'
           'view.set(0, 99);                 // allowed - writes THROUGH\n'
           'System.out.println(arr[0]);\n'
           '\n'
           'try { view.add(4); }\n'
           'catch (UnsupportedOperationException e) { System.out.println("cannot add"); }\n'
           '\n'
           'java.util.List<Integer> imm = java.util.List.of(1, 2, 3);\n'
           'try { imm.set(0, 99); }\n'
           'catch (UnsupportedOperationException e) { System.out.println("cannot set"); }\n'
           '\n'
           'java.util.List<Integer> copy = new java.util.ArrayList<>(view);\n'
           'copy.add(4);\n'
           'System.out.println(copy.size() + " " + view.size());',
      output="99\ncannot add\ncannot set\n4 3",
      gotcha="`view.set(0, 99)` changes the underlying ARRAY — the first println shows "
             "99, not 1. Arrays.asList is a two-way view, not a snapshot, so handing it "
             "to a method that sorts it reorders the caller's array. And "
             "`Arrays.asList(intArray)` on a `int[]` (not `Integer[]`) gives you a "
             "`List<int[]>` OF SIZE ONE, because varargs sees a single object.",
      quiz={
        "q": "`List<Integer> l = Arrays.asList(1, 2, 3); l.set(1, 9); l.add(4);` — what "
             "happens?",
        "options": [
          "set succeeds, add throws UnsupportedOperationException",
          "Both succeed; Arrays.asList returns an ordinary ArrayList",
          "Both throw; the returned list is immutable",
          "set throws and add succeeds",
        ],
        "answer": 0,
        "why": "Option A is right: it is FIXED-SIZE, not immutable — the distinction the "
               "question exists to test. Option B is the common misreading; the returned "
               "type is Arrays$ArrayList, a different class from java.util.ArrayList that "
               "happens to share the name. Option C is what List.of would do, and mixing "
               "the two up is why code migrated from Arrays.asList to List.of sometimes "
               "starts throwing on a set() that used to work. Option D has the two "
               "backwards.",
      },
      pitfalls="`List.of()` rejects nulls — including `list.contains(null)`, which throws "
               "rather than returning false. Code that defensively checks for a null "
               "element breaks when the list is switched to List.of.",
      followups="What about `Collections.unmodifiableList(x)`? It is an unmodifiable VIEW "
                "of x — if someone still holds x and mutates it, the 'unmodifiable' list "
                "changes underneath you. List.copyOf gives an unmodifiable snapshot.",
      difficulty="Medium", frequency="Common",
      mnemonic="Arrays.asList is fixed-size and writes through. List.of is immutable and "
               "hates null."),

    Q("collections", "Removing while iterating — the ConcurrentModificationException",
      "Change a collection while a for-each loop is walking it and it throws, "
      "usually. Sometimes it does not throw and silently skips an element, which "
      "is worse.",
      "A for-each over a Collection uses an Iterator, which records the "
      "collection's modCount when created and checks it on every next(). Any "
      "structural change through the collection (not through the iterator) bumps "
      "modCount and the next call throws ConcurrentModificationException. The "
      "check is best-effort, not a guarantee: removing the SECOND-TO-LAST element "
      "makes hasNext() return false before the check runs, so the loop exits "
      "quietly having skipped the last element.",
      ["collections", "iterator", "concurrent-modification"],
      code='java.util.List<String> l = new java.util.ArrayList<>(\n'
           '        java.util.List.of("a", "b", "c", "d"));\n'
           'try {\n'
           '    for (String s : l) if (s.equals("b")) l.remove(s);\n'
           '} catch (java.util.ConcurrentModificationException e) {\n'
           '    System.out.println("CME");\n'
           '}\n'
           '\n'
           '// the SILENT case: removing the second-to-last element\n'
           'java.util.List<String> m = new java.util.ArrayList<>(\n'
           '        java.util.List.of("a", "b", "c"));\n'
           'for (String s : m) if (s.equals("b")) m.remove(s);\n'
           'System.out.println(m);\n'
           '\n'
           '// the two correct ways\n'
           'java.util.List<String> n = new java.util.ArrayList<>(\n'
           '        java.util.List.of("a", "b", "c", "d"));\n'
           'n.removeIf(s -> s.equals("b"));\n'
           'System.out.println(n);',
      output="CME\n[a, c]\n[a, c, d]",
      gotcha="The middle case does NOT throw. Removing \"b\" from [a, b, c] leaves size 2 "
             "with the cursor at 2, so hasNext() returns false, the loop ends, and \"c\" "
             "was never visited — no exception, and an element silently skipped. THE "
             "EXCEPTION IS THE LUCKY OUTCOME; the quiet one is the bug you ship.",
      quiz={
        "q": "Why does removing the second-to-last element during a for-each NOT throw?",
        "options": [
          "hasNext() compares cursor to size and returns false before next() can run its "
          "modCount check, so the loop exits before noticing",
          "ArrayList exempts the last two positions from the modification check",
          "It does throw; the behaviour is simply timing-dependent",
          "Because remove(Object) does not increment modCount, only remove(int) does",
        ],
        "answer": 0,
        "why": "Option A is right, and it is why the JDK documents this check as "
               "best-effort rather than a guarantee: hasNext() is `cursor != size` with "
               "no modCount check, and after one removal those are equal. Option B "
               "invents an exemption. Option C claims non-determinism where the behaviour "
               "is entirely deterministic on a single thread — it reliably does not "
               "throw. Option D is wrong; both removal overloads bump modCount, which is "
               "exactly why the first loop in the example throws.",
      },
      pitfalls="`removeIf` is the clear answer for a predicate. When you need the "
               "iterator's own remove, write the loop explicitly: `Iterator<T> it = "
               "l.iterator(); while (it.hasNext()) { if (...) it.remove(); }` — "
               "`it.remove()` updates the iterator's expectation and is safe.",
      followups="CopyOnWriteArrayList never throws CME because its iterator walks a "
                "snapshot — at the cost of copying the whole array on every write. Right "
                "for a listener list read constantly and written rarely; wrong for "
                "anything else.",
      difficulty="Medium", frequency="Very common",
      mnemonic="Use removeIf, or the iterator's own remove. The exception is the good "
               "outcome."),

    Q("collections", "HashMap, LinkedHashMap, TreeMap — order is the whole difference",
      "Three maps with the same interface and three different iteration orders: "
      "unspecified, insertion order, and sorted. Choosing the first and then "
      "relying on the order you happened to see is a bug waiting for a rehash.",
      "HashMap makes NO order guarantee and the order changes when the map "
      "resizes. LinkedHashMap maintains a doubly linked list through the entries "
      "giving insertion order (or access order, which is how you build an LRU "
      "cache in about ten lines). TreeMap is a red-black tree ordered by the "
      "key's natural ordering or a supplied Comparator, giving O(log n) "
      "operations instead of O(1) and adding navigation methods — floorKey, "
      "ceilingKey, subMap — that the hash maps cannot offer.",
      ["collections", "map", "ordering"],
      code='var h = new java.util.HashMap<String,Integer>();\n'
           'var l = new java.util.LinkedHashMap<String,Integer>();\n'
           'var t = new java.util.TreeMap<String,Integer>();\n'
           'for (var m : java.util.List.of(h, l, t)) {\n'
           '    m.put("pear", 1); m.put("apple", 2); m.put("fig", 3);\n'
           '}\n'
           'System.out.println(l.keySet());\n'
           'System.out.println(t.keySet());\n'
           'System.out.println(t.firstKey() + " " + t.lastKey());\n'
           'System.out.println(t.headMap("fig"));\n'
           '\n'
           'System.out.println(h.getOrDefault("plum", 0));\n'
           'h.merge("pear", 10, Integer::sum);\n'
           'System.out.println(h.get("pear"));',
      output="[pear, apple, fig]\n[apple, fig, pear]\napple pear\n{apple=2}\n0\n11",
      gotcha="HashMap's key order is deliberately not printed here, because it is not "
             "specified and printing one would teach a number that is not a fact. It "
             "happens to be stable for a given JDK and set of keys, which is precisely "
             "what makes depending on it dangerous — the code works until the map grows "
             "past its load factor and rehashes.",
      quiz={
        "q": "Which map do you reach for to implement an LRU cache?",
        "options": [
          "LinkedHashMap with accessOrder=true and an overridden removeEldestEntry",
          "TreeMap, ordering by last-access timestamp",
          "HashMap — its iteration order is already least-recently-used",
          "ConcurrentHashMap, which evicts automatically under memory pressure",
        ],
        "answer": 0,
        "why": "Option A is right, and it is a genuinely useful thing to know: the "
               "three-argument constructor takes accessOrder, and overriding "
               "removeEldestEntry gives a bounded LRU in a handful of lines. Option B "
               "fails because updating a timestamp key means removing and reinserting, "
               "and the key would no longer be the thing you look up by. Option C is "
               "false — HashMap has no order guarantee at all. Option D invents "
               "behaviour; ConcurrentHashMap never evicts, and nothing in the JDK evicts "
               "under memory pressure except SoftReference-based caches.",
      },
      pitfalls="TreeMap uses compareTo, NOT equals, to decide key identity. A Comparator "
               "that is inconsistent with equals gives a map where two keys that are "
               "equal() occupy separate entries, or where one shadows the other.",
      followups="Since Java 8 a HashMap bucket with more than 8 entries converts to a "
                "red-black tree, so a hash-collision attack degrades lookups to O(log n) "
                "rather than O(n). It requires the keys to be Comparable to do so.",
      difficulty="Medium", frequency="Very common",
      mnemonic="HashMap: no order. LinkedHashMap: the order you put them in. TreeMap: "
               "sorted, O(log n), navigable."),

    # ══════════════════ BASICS ══════════════════

    Q("basics", "Autoboxing and the Integer cache",
      "Small Integer objects are shared from a cache, so == accidentally works "
      "for them. Go past 127 and the same comparison starts returning false, "
      "with no change to your code.",
      "Java caches boxed Integer instances for values -128 to 127 inclusive, so "
      "`Integer.valueOf(100) == Integer.valueOf(100)` is true — they are the same "
      "object. Outside that range each boxing creates a new object and == "
      "compares references, giving false. Autoboxing calls valueOf, so the cache "
      "applies to `Integer a = 100` too. The upper bound is tunable with "
      "-XX:AutoBoxCacheMax, which means the exact threshold is not even a "
      "language constant.",
      ["basics", "autoboxing", "equality", "integer-cache"],
      code='Integer a = 127, b = 127;\n'
           'Integer c = 128, d = 128;\n'
           'System.out.println(a == b);\n'
           'System.out.println(c == d);\n'
           'System.out.println(c.equals(d));\n'
           '\n'
           'int prim = 128;\n'
           'System.out.println(c == prim);      // one side unboxes\n'
           '\n'
           'Long e = 127L;\n'
           'System.out.println(e.equals(127));  // Long vs Integer',
      output="true\nfalse\ntrue\ntrue\nfalse",
      gotcha="Two separate surprises after the famous one. `c == prim` is TRUE even "
             "though `c == d` is false: comparing a boxed value with a PRIMITIVE unboxes "
             "the object and compares numerically, so the reference question never "
             "arises. And `e.equals(127)` is FALSE — equals takes an Object, the literal "
             "boxes to Integer, and Long.equals returns false for anything that is not a "
             "Long. The values are both 127.",
      quiz={
        "q": "`Integer a = 1000, b = 1000; System.out.println(a == b);` prints false. "
             "What single change makes it print true without changing the values?",
        "options": [
          "Run with -XX:AutoBoxCacheMax=1000, which extends the cache to cover them",
          "Nothing — 1000 can never be cached",
          "Declare them as `int` instead, which is a change of values",
          "Call a.intern() first",
        ],
        "answer": 0,
        "why": "Option A is right and is the reason this behaviour must never be relied "
               "on in either direction: the upper bound of the cache is a VM flag, so the "
               "same source can print true on one machine and false on another. Option B "
               "is the common belief and is wrong for that reason. Option C would work "
               "but changes the types, which the question excludes — and it is the "
               "correct real-world fix. Option D applies intern() to Strings; Integer has "
               "no such method.",
      },
      pitfalls="`Map<String, Integer> m; if (m.get(k) > 0)` throws NullPointerException "
               "when the key is absent, because the null Integer is unboxed to compare. "
               "This is the most common autoboxing NPE and it has no visible cast.",
      followups="Boolean caches both values, Character caches 0-127, Byte/Short/Long all "
                "cache -128..127. Float and Double cache NOTHING, so == on boxed "
                "floating-point values is always a reference comparison.",
      difficulty="Medium", frequency="A classic — asked constantly",
      mnemonic="-128..127 is shared. Outside it, new objects. Never == on boxed types."),

    Q("basics", "Floating point cannot represent 0.1, and what to use instead",
      "0.1 + 0.2 does not equal 0.3. It is not a Java bug — binary fractions "
      "cannot represent tenths exactly, the same way decimal cannot represent a "
      "third exactly.",
      "double and float are IEEE 754 binary floating point. 0.1 in binary is a "
      "repeating fraction, so it is stored as the nearest representable value and "
      "the tiny error compounds through arithmetic. For MONEY use BigDecimal "
      "constructed from a STRING — `new BigDecimal(0.1)` captures the error you "
      "were trying to avoid — or use a long of minor units. For comparison, "
      "never ==; compare against a tolerance.",
      ["basics", "floating-point", "bigdecimal", "ieee754"],
      code='System.out.println(0.1 + 0.2);\n'
           'System.out.println(0.1 + 0.2 == 0.3);\n'
           'System.out.println(1.0 / 0);\n'
           'System.out.println(0.0 / 0);\n'
           'System.out.println(Double.NaN == Double.NaN);\n'
           '\n'
           'System.out.println(new java.math.BigDecimal("0.1")\n'
           '        .add(new java.math.BigDecimal("0.2")));\n'
           'System.out.println(new java.math.BigDecimal("1.0")\n'
           '        .equals(new java.math.BigDecimal("1.00")));',
      output="0.30000000000000004\nfalse\nInfinity\nNaN\nfalse\n0.3\nfalse",
      gotcha="Two beyond the famous one. `1.0 / 0` does NOT throw — floating-point "
             "division by zero gives Infinity, while INTEGER division by zero throws "
             "ArithmeticException. And BigDecimal's equals compares SCALE as well as "
             "value, so 1.0 and 1.00 are not equal; use compareTo() == 0 for numeric "
             "equality, which is a bug people ship in money code specifically.",
      quiz={
        "q": "Why does `new BigDecimal(0.1)` not give exactly 0.1?",
        "options": [
          "The double 0.1 is already inexact before BigDecimal sees it, and the "
          "constructor faithfully captures that inexact value",
          "BigDecimal rounds to 16 significant digits by default",
          "It does give exactly 0.1; the string constructor is only a convenience",
          "Because no MathContext was supplied, so precision is unlimited and it "
          "overflows",
        ],
        "answer": 0,
        "why": "Option A is right, and it is why the string constructor exists: by the "
               "time the literal `0.1` is a double it is already 0.1000000000000000055..., "
               "and BigDecimal records that exactly. Option B invents a default rounding; "
               "the double constructor is documented as exact and therefore unpredictable. "
               "Option C is simply false and is the belief that causes the bug. Option D "
               "gets it backwards — unlimited precision is what makes it show all the "
               "error digits rather than hiding them.",
      },
      pitfalls="`Math.round(2.5)` is 3 and `Math.round(-2.5)` is -2, because it rounds "
               "half UP toward positive infinity rather than half away from zero. "
               "BigDecimal lets you name the rounding mode, which for money you should.",
      followups="Is float ever the right choice over double? For large arrays where "
                "memory bandwidth dominates and precision genuinely does not matter — "
                "graphics, ML weights. For anything else double costs the same per "
                "operation on modern hardware.",
      difficulty="Easy", frequency="Very common",
      mnemonic="Binary cannot do tenths. Money is BigDecimal-from-a-String, or a long of "
               "pennies."),

    Q("basics", "char is a number, and arithmetic on it widens to int",
      "A char holds a character, and it is also a 16-bit unsigned number. Do "
      "arithmetic on one and the result is an int, so 'a' + 1 prints 98 rather "
      "than 'b'.",
      "char is an unsigned 16-bit integral type. Any arithmetic operator promotes "
      "its operands to at least int (binary numeric promotion), so char + char, "
      "char + int and even +char all produce an int. To get a char back you must "
      "cast. The compound assignment operators contain an IMPLICIT cast, which is "
      "why `c += 1` compiles where `c = c + 1` does not.",
      ["basics", "char", "promotion", "types"],
      code="char c = 'a';\n"
           "System.out.println(c + 1);\n"
           "System.out.println((char) (c + 1));\n"
           "\n"
           "c += 1;                       // compound assignment casts implicitly\n"
           "System.out.println(c);\n"
           "\n"
           "System.out.println('b' - 'a');\n"
           "System.out.println((int) 'A');\n"
           "\n"
           "char d = 'x';\n"
           "System.out.println(\"\" + c + d);   // string context, no arithmetic\n"
           "System.out.println(c + d);         // arithmetic!",
      output="98\nb\nb\n1\n65\nbx\n218",
      gotcha="The last two lines are the trap. `\"\" + c + d` concatenates left to right "
             "and gives \"bx\"; `c + d` with no string in front is ARITHMETIC and gives "
             "218 (98 + 120). Building output with `+` and forgetting to start from a "
             "string turns your characters into a sum, and it compiles perfectly.",
      quiz={
        "q": "Why does `char c = 'a'; c = c + 1;` fail to compile while `c += 1;` "
             "succeeds?",
        "options": [
          "c + 1 is an int and there is no implicit narrowing to char; compound "
          "assignment contains an implicit cast",
          "c + 1 overflows the char range",
          "+= is overloaded for char and + is not",
          "Because 1 is an int literal; using the char literal '\\u0001' would fix the "
          "first form",
        ],
        "answer": 0,
        "why": "Option A is right: E1 op= E2 is defined as E1 = (T)(E1 op E2), so the "
               "cast is part of the operator's specification. Option B is wrong — 'b' is "
               "well inside the range; the failure is a type error, not an overflow. "
               "Option C invents operator overloading, which Java does not have for user "
               "or primitive types beyond String +. Option D would still produce an int, "
               "because BOTH operands promote — the literal's type is not the problem.",
      },
      pitfalls="char is UNSIGNED, uniquely among Java's integral types. So `(char) -1` is "
               "65535, and a char can never be negative — which is why a loop written "
               "`for (char i = 0; i >= 0; i++)` never terminates.",
      followups="A char is a UTF-16 code unit, not a character. Anything outside the "
                "Basic Multilingual Plane — most emoji — is a surrogate PAIR, so "
                "`\"emoji\".length()` is 2 and charAt(0) gives you half a character. Use "
                "codePointAt for correctness.",
      difficulty="Medium", frequency="Common in 'what does this print' questions",
      mnemonic="Arithmetic on char gives int. Start a concatenation with a String or you "
               "get a sum."),

    ]
