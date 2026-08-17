"""Java bank — modern Java, exceptions and OOP.

The second fill-out module. `modern` had two entries for everything from
Java 8 to 21, `exceptions` had two, and `oop` had four — which for the
three areas an interview spends most of its time on is not a bank, it is
a gesture.

NO JDK ON THE BUILD MACHINE. Every output here is behaviour specified in
the JLS or in the class's own contract; nothing depends on a VM detail,
and where version matters the entry names the version.
"""


def build(Q):
    return [

    # ══════════════════ MODERN ══════════════════

    Q("modern", "Optional is a return type, not a field type",
      "A box that either holds a value or is empty, so a method can say 'there "
      "might be nothing here' in its signature instead of returning null and "
      "hoping the caller checks.",
      "Optional<T> exists to make absence part of the TYPE of a return value. It "
      "was deliberately not made Serializable and the designers said explicitly "
      "it was not intended for fields or parameters: as a field it adds an object "
      "per instance and still permits null; as a parameter it forces every caller "
      "to wrap. Its value is entirely at the boundary of a method that may find "
      "nothing.",
      ["modern", "optional", "null", "api-design"],
      code='import java.util.Optional;\n'
           '\n'
           'Optional<String> some = Optional.of("hi");\n'
           'Optional<String> none = Optional.empty();\n'
           '\n'
           'System.out.println(some.map(String::toUpperCase).orElse("?"));\n'
           'System.out.println(none.map(String::toUpperCase).orElse("?"));\n'
           'System.out.println(none.isPresent());\n'
           '\n'
           'System.out.println(Optional.ofNullable(null).isEmpty());\n'
           '\n'
           'try { Optional.of(null); }\n'
           'catch (NullPointerException e) { System.out.println("of(null) throws"); }\n'
           '\n'
           'System.out.println(some.orElseGet(() -> expensive()));\n'
           'static String expensive() { System.out.println("computed"); return "x"; }',
      output="HI\n?\nfalse\ntrue\nof(null) throws\nhi",
      gotcha="The last line prints \"hi\" and NOT \"computed\" — orElseGet takes a "
             "supplier and only calls it when the Optional is empty. `orElse(expensive())` "
             "would evaluate the argument ALWAYS, because arguments are evaluated before "
             "the call, so a default that costs a database round trip is paid on every "
             "invocation including the ones that did not need it.",
      quiz={
        "q": "What is the difference between `orElse(x)` and `orElseGet(() -> x)`?",
        "options": [
          "orElse evaluates its argument unconditionally; orElseGet only calls the "
          "supplier when the Optional is empty",
          "They are identical; orElseGet is a convenience overload",
          "orElse throws if the Optional is empty; orElseGet returns the default",
          "orElseGet caches the result and orElse does not",
        ],
        "answer": 0,
        "why": "Option A is right, and it is the whole reason both exist: `orElse` takes "
               "a VALUE, so the expression is evaluated at the call site whatever the "
               "Optional holds. Option B is the assumption that makes people write "
               "`orElse(fetchFromDb())` and wonder why the database is hit on every "
               "request. Option C describes `orElseThrow`, which is the third method and "
               "the one that does throw. Option D invents caching that neither performs.",
      },
      pitfalls="`Optional.get()` without checking is exactly as unsafe as dereferencing a "
               "null, and it is why the method was effectively deprecated in favour of "
               "`orElseThrow()` — same behaviour, a name that admits what it does.",
      followups="Why not use Optional for fields? Serialization, an extra object per "
                "instance, and the fact that the field can still be null — giving you two "
                "kinds of absent to check instead of one.",
      difficulty="Medium", frequency="Very common in modern-Java questions",
      mnemonic="Optional at a method's exit. orElseGet for anything expensive."),

    Q("modern", "Records — the compiler writes equals, hashCode and toString",
      "A short way to declare a class whose only job is to hold a few values. "
      "You write the components; the compiler writes the constructor, the "
      "accessors, equals, hashCode and toString.",
      "`record Point(int x, int y) {}` generates a canonical constructor, "
      "accessors named `x()` and `y()` (not getX), and value-based equals, "
      "hashCode and toString from all components. Records are implicitly final, "
      "cannot extend a class, and their fields are final — so they are shallowly "
      "immutable. A COMPACT CONSTRUCTOR lets you validate or normalise without "
      "restating the assignments.",
      ["modern", "records", "immutability", "java16"],
      code='record Point(int x, int y) {\n'
           '    Point {                       // compact constructor\n'
           '        if (x < 0 || y < 0) throw new IllegalArgumentException("negative");\n'
           '    }\n'
           '    int sum() { return x + y; }   // extra methods are allowed\n'
           '}\n'
           '\n'
           'Point a = new Point(1, 2);\n'
           'Point b = new Point(1, 2);\n'
           'System.out.println(a);\n'
           'System.out.println(a.equals(b));\n'
           'System.out.println(a.x() + " " + a.sum());\n'
           'System.out.println(a.hashCode() == b.hashCode());\n'
           '\n'
           'try { new Point(-1, 0); }\n'
           'catch (IllegalArgumentException e) { System.out.println("rejected"); }',
      output="Point[x=1, y=2]\ntrue\n1 3\ntrue\nrejected",
      gotcha="Records are only SHALLOWLY immutable. `record Team(String name, List<String> "
             "members)` has a final reference to a mutable list — the caller can still "
             "add to it after construction, and equals will then report two records equal "
             "that hold different contents at different times. Defensive-copy in the "
             "compact constructor if the component is mutable.",
      quiz={
        "q": "What does the accessor for a record component named `value` get called?",
        "options": [
          "value() — records do not use the get prefix",
          "getValue() — it follows the JavaBeans convention",
          "Both are generated, for compatibility",
          "There is no accessor; the field is public",
        ],
        "answer": 0,
        "why": "Option A is right, and it matters because frameworks expecting JavaBeans "
               "naming needed updating to support records. Option B is the convention "
               "records deliberately broke — the component name IS the method name. "
               "Option C invents a second method that would double the API. Option D is "
               "wrong: the field is private final, and the accessor is what makes it "
               "readable.",
      },
      pitfalls="A record cannot extend anything (it already extends java.lang.Record), so "
               "you cannot use one to add fields to an existing class. It CAN implement "
               "interfaces, which is how records participate in sealed hierarchies.",
      followups="Records pair with sealed interfaces and pattern matching to give Java "
                "algebraic data types: a sealed interface with record implementations, "
                "matched exhaustively in a switch, with the compiler checking you handled "
                "every case.",
      difficulty="Easy", frequency="Common — expected knowledge on Java 17+",
      mnemonic="Components in, equals/hashCode/toString out. Shallowly immutable, so "
               "copy mutable components."),

    Q("modern", "Sealed types and pattern matching for switch",
      "You can tell the compiler that a type has exactly these subtypes and no "
      "others. Then a switch over it can be checked for completeness — miss a "
      "case and it will not compile.",
      "`sealed interface Shape permits Circle, Square` restricts implementation "
      "to the named types, which must each be final, sealed or non-sealed. "
      "Because the compiler knows the full set, a switch covering all of them is "
      "EXHAUSTIVE and needs no default. Adding a new permitted subtype then "
      "breaks every switch that does not handle it — which is the point: the "
      "compiler finds the places you must update.",
      ["modern", "sealed", "pattern-matching", "switch", "java21"],
      code='sealed interface Shape permits Circle, Square {}\n'
           'record Circle(double r) implements Shape {}\n'
           'record Square(double side) implements Shape {}\n'
           '\n'
           'static String describe(Shape s) {\n'
           '    return switch (s) {                 // no default needed\n'
           '        case Circle c when c.r() > 10 -> "big circle";\n'
           '        case Circle c                 -> "circle r=" + c.r();\n'
           '        case Square q                 -> "square " + q.side();\n'
           '    };\n'
           '}\n'
           '\n'
           'System.out.println(describe(new Circle(2)));\n'
           'System.out.println(describe(new Circle(20)));\n'
           'System.out.println(describe(new Square(3)));',
      output="circle r=2.0\nbig circle\nsquare 3.0",
      gotcha="ORDER MATTERS with guarded patterns. The guarded `case Circle c when r > 10` "
             "must come BEFORE the unguarded `case Circle c`, because the unguarded one "
             "matches every Circle and would DOMINATE the guarded case — and javac "
             "rejects that as a compile error rather than silently picking the first. "
             "Putting the general case first is a compile failure, which is the language "
             "protecting you from an unreachable branch.",
      quiz={
        "q": "Why does a switch over a sealed interface not need a `default` branch?",
        "options": [
          "The compiler knows the complete set of permitted subtypes, so covering all of "
          "them is provably exhaustive",
          "switch expressions never require default",
          "Because records implement Shape, and records are always exhaustive",
          "It does need one; omitting it is a runtime MatchException",
        ],
        "answer": 0,
        "why": "Option A is right, and the payoff is that ADDING a subtype turns every "
               "incomplete switch into a compile error rather than a silent fallthrough — "
               "which is exactly the behaviour a default branch would have destroyed. "
               "Option B is wrong: a switch EXPRESSION must be exhaustive, and over an "
               "unsealed type that means a default. Option C confuses records with "
               "sealing; records are just final classes here. Option D describes what "
               "happens when a sealed hierarchy is recompiled inconsistently, which is a "
               "real but different failure.",
      },
      pitfalls="Adding a default to an exhaustive sealed switch is legal and throws away "
               "the guarantee — the compiler can no longer tell you about a new subtype, "
               "because the default silently absorbs it.",
      followups="Record patterns (Java 21) go further: "
                "`case Circle(double r) when r > 10` destructures in the pattern itself, "
                "so there is no local to name and no accessor call to write.",
      difficulty="Medium", frequency="Increasingly common on Java 21 roles",
      mnemonic="sealed = the compiler knows every subtype = the switch is checked for you."),

    Q("modern", "var infers the type; it does not make Java dynamic",
      "`var` lets you skip writing the type of a local variable when the "
      "right-hand side already says it. The variable still has one fixed type, "
      "decided at compile time, and it can never change.",
      "var is LOCAL VARIABLE TYPE INFERENCE (Java 10). It works only for locals "
      "with an initialiser, for-loop variables, and try-with-resources — never "
      "for fields, parameters or return types, because those are API and "
      "inference would make the API depend on an implementation. The inferred "
      "type is the STATIC type of the initialiser, which is sometimes narrower "
      "than you intended.",
      ["modern", "var", "type-inference", "java10"],
      code='var list = new java.util.ArrayList<String>();   // ArrayList<String>\n'
           'list.add("a");\n'
           'System.out.println(list.getClass().getSimpleName());\n'
           '\n'
           'var n = 1;                    // int, not Integer, not long\n'
           'System.out.println(((Object) n).getClass().getSimpleName());\n'
           '\n'
           'var d = 1.0;                  // double\n'
           'System.out.println(((Object) d).getClass().getSimpleName());\n'
           '\n'
           'for (var s : list) System.out.println(s.length());\n'
           '\n'
           'var arr = new int[]{1, 2, 3};\n'
           'System.out.println(arr.length);',
      output="ArrayList\nInteger\nDouble\n1\n3",
      gotcha="`var list = new ArrayList<String>()` infers the CONCRETE type ArrayList, "
             "not the interface List. That is usually harmless for a local, and it is why "
             "`var` is a poor habit in code you intend to refactor: the declaration no "
             "longer expresses the contract, so changing the implementation type silently "
             "changes what methods are available at the call site.",
      quiz={
        "q": "Which of these is a legal use of `var`?",
        "options": [
          "A local variable in a method, with an initialiser",
          "A field of a class",
          "A method parameter",
          "A method return type",
        ],
        "answer": 0,
        "why": "Option A is the only one that compiles — var is specified for LOCAL "
               "variables only. Option B is rejected because a field is part of a class's "
               "shape and inferring it would make that shape depend on an initialiser "
               "expression. Option C is rejected because a parameter type is the "
               "method's contract with every caller. Option D is rejected for the "
               "sharpest version of the same reason: a return type inferred from the "
               "method body would change whenever the body did, silently breaking "
               "callers. (Lambda parameters are the one near-exception, where `var` is "
               "permitted purely so annotations can be attached.)",
      },
      pitfalls="`var x = null;` does not compile — there is nothing to infer from. "
               "Neither does a bare `var x;` with the assignment on the next line, even "
               "though a human can see the type: inference reads the initialiser and "
               "there isn't one.",
      followups="`var` and the diamond together are a trap: `var list = new ArrayList<>();` "
                "infers `ArrayList<Object>`, because there is no target type to guide the "
                "diamond. Every subsequent add compiles and every read gives you Object.",
      difficulty="Easy", frequency="Common",
      mnemonic="Locals only, initialiser required, static type inferred. Not dynamic."),

    Q("modern", "Streams are lazy, single-use, and not automatically faster",
      "A pipeline over a collection that reads like a description of what you "
      "want rather than a loop. Nothing happens until you ask for the result, "
      "and you cannot ask twice.",
      "Intermediate operations (map, filter, sorted) are LAZY — they build a "
      "pipeline and do no work. A terminal operation (collect, forEach, count) "
      "runs it, and afterwards the stream is CONSUMED: reusing it throws "
      "IllegalStateException. Laziness enables short-circuiting, so findFirst on "
      "an infinite stream terminates. parallelStream() is not free: it costs "
      "fork-join overhead and is a loss below tens of thousands of elements or "
      "for any cheap per-element operation.",
      ["modern", "streams", "lazy", "java8"],
      code='var names = java.util.List.of("ana", "bo", "cy", "di");\n'
           '\n'
           'var s = names.stream().filter(n -> n.length() == 2);\n'
           'System.out.println(s.count());\n'
           'try { s.count(); }\n'
           'catch (IllegalStateException e) { System.out.println("already consumed"); }\n'
           '\n'
           '// nothing is printed: no terminal operation\n'
           'names.stream().map(n -> { System.out.println("mapping " + n); return n; });\n'
           'System.out.println("still here");\n'
           '\n'
           'System.out.println(java.util.stream.Stream.iterate(1, i -> i + 1)\n'
           '        .filter(i -> i % 7 == 0).findFirst().get());',
      output="3\nalready consumed\nstill here\n7",
      gotcha="The map() call prints NOTHING. There is no terminal operation, so the "
             "pipeline is never run and the side effect inside the lambda never happens. "
             "Code that does its work in a map() and forgets to collect looks correct, "
             "compiles, runs, and does nothing at all — with no warning.",
      quiz={
        "q": "`Stream.iterate(1, i -> i + 1).filter(i -> i % 7 == 0).findFirst()` on an "
             "INFINITE stream — what happens?",
        "options": [
          "It returns 7; laziness means only as many elements are generated as findFirst "
          "needs",
          "It hangs, because the stream is infinite",
          "It throws OutOfMemoryError building the stream",
          "It returns an empty Optional, because an infinite stream has no first element",
        ],
        "answer": 0,
        "why": "Option A is right and it is the practical payoff of laziness: elements are "
               "pulled one at a time and findFirst short-circuits after the seventh. "
               "Option B is what an EAGER implementation would do and is the intuition "
               "laziness overturns. Option C would follow from materialising the stream, "
               "which never happens. Option D confuses an infinite stream with an empty "
               "one — and note that `.sorted()` in this pipeline WOULD hang, because "
               "sorting cannot short-circuit.",
      },
      pitfalls="`peek` is documented for debugging and may be skipped entirely: since "
               "Java 9 the JDK can elide a peek whose result is not needed, so relying on "
               "it for side effects gives behaviour that changes between versions.",
      followups="When does parallelStream() actually pay? Large N, a genuinely expensive "
                "per-element operation, a splittable source (ArrayList yes, LinkedList "
                "no), and no shared mutable state. Miss any of those and it is slower.",
      difficulty="Medium", frequency="Very common",
      mnemonic="No terminal operation, no work. One terminal operation, then it is spent."),

    # ══════════════════ EXCEPTIONS ══════════════════

    Q("exceptions", "Checked vs unchecked, and where the line actually is",
      "Some exceptions the compiler forces you to handle or declare; others it "
      "does not. The rule is about the class you extend, and the choice is about "
      "whether a caller can reasonably do anything about it.",
      "Throwable splits into Error (do not catch: OutOfMemoryError, "
      "StackOverflowError), RuntimeException and its subclasses (UNCHECKED), and "
      "everything else under Exception (CHECKED). Checked exceptions must be "
      "caught or declared. The intent was that recoverable conditions are checked "
      "and programming errors are unchecked — a file that might not exist versus "
      "an index you got wrong. In practice most modern APIs favour unchecked, "
      "because a checked exception propagates up every signature it passes "
      "through.",
      ["exceptions", "checked", "unchecked", "hierarchy"],
      code='try {\n'
           '    throw new IllegalStateException("unchecked");\n'
           '} catch (RuntimeException e) {\n'
           '    System.out.println("caught " + e.getMessage());\n'
           '}\n'
           '\n'
           'try {\n'
           '    Object o = "text";\n'
           '    Integer i = (Integer) o;      // unchecked: ClassCastException\n'
           '} catch (ClassCastException e) {\n'
           '    System.out.println("CCE");\n'
           '}\n'
           '\n'
           'try {\n'
           '    int[] a = new int[1];\n'
           '    a[2] = 0;\n'
           '} catch (RuntimeException e) {\n'
           '    System.out.println(e.getClass().getSimpleName());\n'
           '}\n'
           '\n'
           'try { throw new Exception("checked"); }\n'
           'catch (Exception e) { System.out.println("checked caught"); }',
      output="caught unchecked\nCCE\nArrayIndexOutOfBoundsException\nchecked caught",
      gotcha="`catch (Exception e)` catches checked AND unchecked, because "
             "RuntimeException extends Exception. It does NOT catch Error. So the "
             "commonly-written `catch (Exception e)` silently swallows every bug in the "
             "block — a null dereference, a bad cast, an off-by-one — alongside the "
             "IOException you meant to handle.",
      quiz={
        "q": "Which of these is a CHECKED exception?",
        "options": [
          "java.io.IOException",
          "NullPointerException",
          "IllegalArgumentException",
          "ArrayIndexOutOfBoundsException",
        ],
        "answer": 0,
        "why": "Option A is right: IOException extends Exception directly, not "
               "RuntimeException, so the compiler demands it be caught or declared. "
               "Option B is unchecked — a null dereference is a bug, not a condition to "
               "recover from. Option C is unchecked for the same reason: passing a bad "
               "argument is the caller's error. Option D is unchecked and completes the "
               "pattern worth naming — every one of the three indicates a PROGRAMMING "
               "error the caller could have prevented, which is exactly the line the "
               "designers drew.",
      },
      pitfalls="Never `catch (Throwable t)` in application code. It catches "
               "OutOfMemoryError and StackOverflowError, from which continuing is not "
               "meaningful, and it catches ThreadDeath.",
      followups="Why do lambdas make checked exceptions painful? The functional "
                "interfaces in java.util.function declare no checked exceptions, so a "
                "method that throws one cannot be used as a Function without wrapping — "
                "which is a large part of why modern APIs avoid them.",
      difficulty="Easy", frequency="Universal",
      mnemonic="RuntimeException and below: unchecked. Everything else under Exception: "
               "checked. Error: not yours."),

    Q("exceptions", "try-with-resources closes in reverse, and suppresses",
      "Declare a resource in the try and it is closed automatically, even if "
      "something throws. Multiple resources close in reverse order, and if "
      "closing ALSO throws, that second exception is attached to the first "
      "rather than replacing it.",
      "Any AutoCloseable declared in the try(...) header is closed when the block "
      "exits, in REVERSE declaration order — so a resource that depends on an "
      "earlier one is still valid while it closes. If the body throws and close() "
      "also throws, the close exception is SUPPRESSED: attached to the primary "
      "exception and retrievable with getSuppressed(). The old try/finally idiom "
      "lost the original exception entirely in that case, which is the bug this "
      "syntax exists to fix.",
      ["exceptions", "try-with-resources", "autocloseable", "java7"],
      code='class R implements AutoCloseable {\n'
           '    final String n;\n'
           '    R(String n) { this.n = n; System.out.println("open " + n); }\n'
           '    public void close() { System.out.println("close " + n); }\n'
           '}\n'
           '\n'
           'try (R a = new R("a"); R b = new R("b")) {\n'
           '    System.out.println("body");\n'
           '}\n'
           '\n'
           'class Bad implements AutoCloseable {\n'
           '    public void close() { throw new IllegalStateException("close failed"); }\n'
           '}\n'
           'try (Bad x = new Bad()) {\n'
           '    throw new RuntimeException("body failed");\n'
           '} catch (Exception e) {\n'
           '    System.out.println(e.getMessage());\n'
           '    System.out.println(e.getSuppressed()[0].getMessage());\n'
           '}',
      output="open a\nopen b\nbody\nclose b\nclose a\nbody failed\nclose failed",
      gotcha="The PRIMARY exception is the one from the body, and the close failure is "
             "suppressed onto it. Written the old way — try/finally with close() in the "
             "finally — the close exception would propagate and the body's exception "
             "would be LOST, so you would debug 'close failed' while the actual failure "
             "was invisible. That silent replacement is what try-with-resources fixed.",
      quiz={
        "q": "Two resources are declared in one try-with-resources. In what order are "
             "they closed?",
        "options": [
          "Reverse of declaration — the last declared closes first",
          "Declaration order — first declared closes first",
          "Unspecified; it depends on the JVM",
          "Only the first is closed automatically",
        ],
        "answer": 0,
        "why": "Option A is right, and the reason is worth knowing rather than "
               "memorising: a later resource is often built FROM an earlier one (a "
               "BufferedReader wrapping a FileReader), so it must close while its "
               "dependency is still open. Option B would close the file out from under "
               "the buffer. Option C is wrong — the order is specified by the JLS. "
               "Option D describes no version of the feature; every declared resource is "
               "closed.",
      },
      pitfalls="Before Java 9 the resource had to be declared IN the header. Since 9 an "
               "effectively-final existing variable can be named directly: "
               "`try (existingReader) { ... }`.",
      followups="What if close() throws and the body did NOT? Then there is no primary "
                "exception to suppress onto, and the close exception propagates normally "
                "— which is why a close() that can fail meaningfully still deserves "
                "thought.",
      difficulty="Medium", frequency="Common",
      mnemonic="Reverse order, and close-failures attach to the real exception instead of "
               "hiding it."),

    Q("exceptions", "A return in finally swallows the exception",
      "Whatever finally does wins. Return from it and the exception that was "
      "propagating simply disappears — no stack trace, no log, nothing to "
      "indicate anything went wrong.",
      "finally always runs, and a `return`, `break` or `continue` in it "
      "ABRUPTLY COMPLETES the block, discarding any exception or return value "
      "still in flight. A return in finally therefore overrides a return in try "
      "AND cancels an exception being thrown. Every static analyser flags it; it "
      "is legal Java and it is never what anyone means.",
      ["exceptions", "finally", "control-flow", "traps"],
      code='static int swallow() {\n'
           '    try {\n'
           '        throw new RuntimeException("boom");\n'
           '    } finally {\n'
           '        return 1;             // the exception vanishes\n'
           '    }\n'
           '}\n'
           '\n'
           'static int override() {\n'
           '    try { return 1; }\n'
           '    finally { return 2; }\n'
           '}\n'
           '\n'
           'static int mutate() {\n'
           '    int x = 1;\n'
           '    try { return x; }\n'
           '    finally { x = 99; }       // too late: the value was already captured\n'
           '}\n'
           '\n'
           'System.out.println(swallow());\n'
           'System.out.println(override());\n'
           'System.out.println(mutate());',
      output="1\n2\n1",
      gotcha="`mutate()` returns 1, not 99. The return VALUE is evaluated and stored "
             "before finally runs, so assigning to the local afterwards changes the "
             "variable and not the pending return. But `return x;` where x is a mutable "
             "OBJECT and finally mutates its contents DOES show the change — the "
             "reference was captured, not the object.",
      quiz={
        "q": "A method throws inside try and returns 1 inside finally. What does the "
             "caller see?",
        "options": [
          "1, and the exception is silently discarded",
          "The exception propagates; the return is unreachable",
          "It does not compile — a return in finally is an error",
          "Both: the exception is thrown after the value is returned",
        ],
        "answer": 0,
        "why": "Option A is right and it is why every linter bans this: the finally block "
               "completes abruptly with a return, which discards the pending throw "
               "entirely. Option B is what people expect and would be the safe design. "
               "Option C is wrong — it compiles without so much as a warning from javac, "
               "which is what makes it dangerous. Option D is not possible; a method "
               "either returns or throws.",
      },
      pitfalls="The same abrupt-completion rule applies to `break` and `continue` inside "
               "a finally within a loop, with the same silent swallowing.",
      followups="Does finally always run? Almost: not if the JVM exits (System.exit), not "
                "if the thread is killed at the OS level, and not if the try block loops "
                "forever. Otherwise yes, including on return and on throw.",
      difficulty="Medium", frequency="A classic 'what does this print'",
      mnemonic="finally wins. Return from it and the exception never happened."),

    # ══════════════════ OOP ══════════════════

    Q("oop", "equals must be reflexive, symmetric, transitive — and subclasses break it",
      "The equals contract has four rules, and the one that catches people is "
      "symmetry: if a.equals(b) then b.equals(a) must also be true. Add a field "
      "in a subclass and it stops being true.",
      "equals must be reflexive (a.equals(a)), symmetric, transitive, consistent, "
      "and false for null. A superclass whose equals uses `instanceof` will "
      "consider a subclass instance equal to a superclass one, while the "
      "subclass's own equals — comparing the extra field — will not. That "
      "asymmetry breaks collections in ways that depend on which object you ask. "
      "Using `getClass() !=` instead of instanceof restores symmetry and breaks "
      "the Liskov substitution principle; there is no way to have both, which is "
      "why composition is preferred over extending a value class.",
      ["oop", "equals", "contract", "inheritance"],
      code='class Point {\n'
           '    final int x, y;\n'
           '    Point(int x, int y) { this.x = x; this.y = y; }\n'
           '    @Override public boolean equals(Object o) {\n'
           '        if (!(o instanceof Point)) return false;\n'
           '        Point p = (Point) o;\n'
           '        return p.x == x && p.y == y;\n'
           '    }\n'
           '    @Override public int hashCode() { return x * 31 + y; }\n'
           '}\n'
           'class Coloured extends Point {\n'
           '    final String c;\n'
           '    Coloured(int x, int y, String c) { super(x, y); this.c = c; }\n'
           '    @Override public boolean equals(Object o) {\n'
           '        if (!(o instanceof Coloured)) return false;\n'
           '        return super.equals(o) && ((Coloured) o).c.equals(c);\n'
           '    }\n'
           '}\n'
           '\n'
           'Point p = new Point(1, 2);\n'
           'Coloured c = new Coloured(1, 2, "red");\n'
           'System.out.println(p.equals(c));\n'
           'System.out.println(c.equals(p));',
      output="true\nfalse",
      gotcha="p.equals(c) is true and c.equals(p) is false — the SAME PAIR, two answers. "
             "Put both in a HashSet and whether the set contains one of them depends on "
             "which was inserted first and which you ask about. Nothing throws; the set "
             "is simply wrong in a way that is order-dependent.",
      quiz={
        "q": "How do you make equals symmetric across a class and its subclass that adds "
             "a field?",
        "options": [
          "You cannot have both symmetry and substitutability — use composition instead "
          "of inheritance for value types",
          "Use getClass() != o.getClass() in both, which fixes it completely",
          "Make the subclass's equals call super.equals only",
          "Mark the subclass final",
        ],
        "answer": 0,
        "why": "Option A is right and it is the honest answer: this is a genuine "
               "limitation, and it is why Effective Java recommends composition for value "
               "classes. Option B restores symmetry and breaks substitutability — a "
               "subclass instance is then never equal to a superclass one even when it "
               "should be, which violates Liskov. Option C makes the subclass ignore its "
               "own field, so two differently-coloured points are equal. Option D "
               "prevents FURTHER subclasses but does nothing about the pair that already "
               "exists.",
      },
      pitfalls="`equals(Object)` — if you write `equals(MyType)` you have OVERLOADED it, "
               "not overridden it. Collections call the Object version and never see "
               "yours. @Override on the method is what catches this at compile time.",
      followups="Records sidestep the whole problem: they are implicitly final and cannot "
                "be extended, so the asymmetric case cannot arise.",
      difficulty="Hard", frequency="A senior question",
      mnemonic="instanceof breaks symmetry, getClass breaks substitutability. Prefer "
               "composition."),

    Q("oop", "Initialisation order: fields, blocks, constructors, and the super call",
      "When you create an object, several things run in a fixed order that is not "
      "the order they appear in the file. A field initialised after the "
      "constructor's line still runs before the constructor's body.",
      "Order for `new Child()`: (1) static initialisers of the whole hierarchy, "
      "once, top-down, on first use; (2) the implicit or explicit super() call, "
      "so the PARENT is fully constructed first; (3) the child's instance field "
      "initialisers and instance blocks, in SOURCE ORDER, interleaved; (4) the "
      "child's constructor body. The consequence that bites: a parent "
      "constructor calling an overridable method runs the CHILD's override "
      "before the child's fields have been initialised.",
      ["oop", "initialisation", "constructor", "inheritance"],
      code='class Parent {\n'
           '    Parent() {\n'
           '        System.out.println("parent ctor");\n'
           '        show();                       // calls the OVERRIDE\n'
           '    }\n'
           '    void show() { System.out.println("parent show"); }\n'
           '}\n'
           'class Child extends Parent {\n'
           '    String name = "set";\n'
           '    { System.out.println("child block"); }\n'
           '    Child() { System.out.println("child ctor, name=" + name); }\n'
           '    @Override void show() { System.out.println("child show, name=" + name); }\n'
           '}\n'
           '\n'
           'new Child();',
      output="parent ctor\nchild show, name=null\nchild block\nchild ctor, name=set",
      gotcha="`child show, name=null`. The parent's constructor runs FIRST and calls the "
             "override, but the child's field initialisers have not run yet — so `name` "
             "is still the default null. A field declared `final` behaves the same way. "
             "THIS IS WHY YOU NEVER CALL AN OVERRIDABLE METHOD FROM A CONSTRUCTOR: the "
             "subclass sees itself half-built.",
      quiz={
        "q": "A parent constructor calls an overridable method. What does the child's "
             "override see?",
        "options": [
          "The child's fields at their DEFAULT values — null/0/false — because the "
          "child's initialisers have not run yet",
          "The child's fields fully initialised, since the object exists",
          "The parent's version runs, because the object is still a Parent at that point",
          "A NullPointerException, because the child object does not exist yet",
        ],
        "answer": 0,
        "why": "Option A is right and it is the most surprising consequence of the "
               "ordering: dynamic dispatch is live from the start, but the child's field "
               "initialisers run AFTER super(). Option B is the intuition that makes the "
               "bug. Option C is wrong — virtual dispatch does not wait for the "
               "constructor to finish, which is exactly the problem. Option D confuses "
               "the object not existing with its fields being unset; the object exists "
               "and its fields hold defaults.",
      },
      pitfalls="Make the method `final`, `private` or `static` if a constructor must call "
               "it — all three prevent overriding, which removes the hazard entirely.",
      followups="Static initialisers run once, on first ACTIVE use of the class — which "
                "does not include reading a compile-time constant `static final int`, "
                "because that is inlined by the compiler and the class is never loaded.",
      difficulty="Hard", frequency="A favourite 'what does this print'",
      mnemonic="super() first, then fields in source order, then the constructor body. "
               "Never call an overridable from a constructor."),

    Q("oop", "Default methods and the diamond the compiler makes you resolve",
      "Interfaces can carry method bodies. Implement two interfaces that both "
      "provide the same default and the compiler refuses to guess — you must say "
      "which one you meant.",
      "Default methods (Java 8) let an interface evolve without breaking "
      "implementers — which is how Collection gained stream() and removeIf. "
      "Resolution order when a method could come from several places: a CLASS "
      "always beats an interface; a more specific interface beats a less specific "
      "one; and if two unrelated interfaces both provide it, that is an ambiguity "
      "the compiler reports rather than resolves. You disambiguate with "
      "`Interface.super.method()`.",
      ["oop", "interface", "default-method", "diamond", "java8"],
      code='interface A { default String who() { return "A"; } }\n'
           'interface B { default String who() { return "B"; } }\n'
           '\n'
           'class C implements A, B {\n'
           '    @Override public String who() {\n'
           '        return A.super.who() + B.super.who();   // must choose explicitly\n'
           '    }\n'
           '}\n'
           '\n'
           'class Base { public String who() { return "Base"; } }\n'
           'class D extends Base implements A { }             // no override needed\n'
           '\n'
           'System.out.println(new C().who());\n'
           'System.out.println(new D().who());',
      output="AB\nBase",
      gotcha="`D` compiles with NO override and prints \"Base\", not \"A\". The rule is "
             "'the class wins': an inherited concrete method from a superclass silently "
             "beats an interface default, with no warning. So adding a default method to "
             "an interface can be completely invisible to a class that happens to inherit "
             "the same signature from elsewhere.",
      quiz={
        "q": "`class C implements A, B` where both A and B define `default String who()`. "
             "What happens if C does not override it?",
        "options": [
          "Compile error — the inheritance is ambiguous and must be resolved explicitly",
          "A's version wins, by declaration order in the implements clause",
          "B's version wins, as the last one declared",
          "It compiles and throws IncompatibleClassChangeError at runtime",
        ],
        "answer": 0,
        "why": "Option A is right: the compiler will not pick for you, which is the safe "
               "design — either candidate could be wrong and silently choosing one would "
               "hide it. Options B and C both invent an ordering rule; the order of the "
               "implements clause has no meaning in Java. Option D describes a real error "
               "that arises from inconsistent RECOMPILATION, not from this source, which "
               "does not compile at all.",
      },
      pitfalls="Interfaces still cannot hold instance STATE. A default method can only "
               "use other interface methods and its arguments, which is what keeps them "
               "from being multiple inheritance of state — the thing Java has always "
               "refused.",
      followups="Why not just add abstract methods to Collection? Because every existing "
                "implementation in the world would fail to compile. Default methods "
                "exist so that stream() could be added to an interface implemented by "
                "code the JDK authors had never seen.",
      difficulty="Medium", frequency="Common on Java 8+ questions",
      mnemonic="Class beats interface. Two interfaces tie, and the compiler makes you "
               "choose with X.super.m()."),

    ]
