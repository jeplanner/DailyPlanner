"""Java core interview bank — a study bank for someone learning Java properly,
not skimming it.

WHY THIS IS SHAPED DIFFERENTLY FROM ai_sde_bank.py
--------------------------------------------------
The AI/SDE bank answers CONCEPTUAL questions, so a long `answer` field is the
right container. Java is a LANGUAGE. In a Java interview the question is very
often "what does this print, and why", and the answer is a five-line snippet
plus one sentence about the JLS. A prose blob is the wrong container for that.

So this bank adds four fields the other one does not have, and each exists
because of a specific failure of the other format:

    plain    - the answer with NO jargon, written first and read first. The
               other bank bolted this on later after "explain, don't assert"
               feedback; here it is a required field, so an entry cannot be
               written jargon-first.
    output   - EXACTLY what `code` prints. Java's whole interview genre is
               "predict the output", and an entry whose code has no stated
               output cannot be self-tested.
    gotcha   - the trap, stated as a question, with WHY the wrong answer is
               the intuitive one. Not "here is a pitfall" but "here is what
               you will guess, and here is why you will guess it".
    version  - which Java release introduced or changed this. Java 8, 11, 17
               and 21 differ enough that undated advice is often wrong, and
               almost every bank omits this.

And one that changes how the quiz works:

    quiz     - a HAND-WRITTEN multiple choice question whose distractors are
               the actual misconceptions. The AI/SDE quiz builds options by
               sampling other entries' titles, which produces obviously-wrong
               options and therefore tests recognition of the topic rather
               than understanding of it. A distractor is only useful if a
               person who half-knows the material would pick it.

EVERYTHING ELSE MATCHES ai_sde_bank.py DELIBERATELY - same Q() call shape,
same `examples` ten-section deep-dive list, same tags/difficulty/frequency -
so the existing routes, PDF export, progress tracking and card renderer work
against this bank with no changes beyond a registration.

A NOTE ON HOW THE OUTPUTS WERE PRODUCED. There is no JVM on the machine this
was written on, so no snippet here was executed. Every `output` was derived by
hand from the Java Language Specification and is marked as such rather than
presented as a measured run. Where a claim depends on an implementation detail
rather than the spec (HashMap iteration order, GC timing, Integer cache upper
bound), the entry says so explicitly instead of stating a number that happens
to be true on one JVM.
"""

import re

CATEGORIES = {
    "setup":       "Getting Started — JVM, JDK, compiling",
    "basics":      "Syntax & Primitives",
    "strings":     "Strings",
    "flow":        "Control Flow & Methods",
    "oop":         "Objects & OOP",
    "collections": "Collections & Generics",
    "exceptions":  "Exceptions & Resources",
    "modern":      "Modern Java (8 → 21)",
    "concurrency": "Threads & Concurrency",
    "jvm":         "Memory, GC & Performance",
    "traps":       "Classic Traps (what does this print?)",
}

#: Order matters — this is the teaching ladder, not an alphabetical list.
CATEGORY_ORDER = list(CATEGORIES)

_CATEGORY_TAGS = {
    "setup": ["setup", "jvm"], "basics": ["basics", "syntax"],
    "strings": ["string"], "flow": ["control-flow", "methods"],
    "oop": ["oop"], "collections": ["collections", "generics"],
    "exceptions": ["exceptions"], "modern": ["modern-java"],
    "concurrency": ["concurrency", "threads"], "jvm": ["jvm", "memory"],
    "traps": ["trap", "gotcha"],
}


def Q(cat, title, plain, answer, tags,
      code="", output="", gotcha="", version="", bytecode="",
      quiz=None, example="", complexity="", pitfalls="", followups="",
      difficulty="", frequency="", mnemonic="", diagram="", examples=None):
    """One bank entry.

    REQUIRED, and required on purpose:
        plain  - no jargon. If you cannot write it, you do not understand it.
        answer - the technical statement, free to use the vocabulary `plain`
                 just defined.

    `quiz` is {"q":..., "options":[4 strings], "answer": index, "why": ...}
    where `why` explains each wrong option, not just the right one.
    """
    if not plain.strip():
        raise ValueError(f"entry {title!r} has no plain-English answer")
    if code and not output.strip():
        raise ValueError(f"entry {title!r} has code but no stated output")
    return {
        "cat": cat, "title": title, "plain": plain, "answer": answer,
        "code": code, "output": output, "gotcha": gotcha, "version": version,
        "bytecode": bytecode, "quiz": quiz, "example": example,
        "complexity": complexity, "pitfalls": pitfalls, "followups": followups,
        "tags": tags, "difficulty": difficulty, "frequency": frequency,
        "mnemonic": mnemonic, "diagram": diagram, "examples": list(examples or []),
    }


ENTRIES = [

    # ══════════════════════════════════════════════════════════════════
    #  Getting Started
    # ══════════════════════════════════════════════════════════════════

    Q("setup",
      "What actually happens when you run a Java program?",
      "You write a .java text file. A program called the compiler turns it into "
      "a .class file — that file is NOT machine code for your laptop, it is "
      "instructions for an imaginary computer called the Java Virtual Machine. "
      "When you run the program, a real JVM for your actual laptop reads those "
      "instructions and carries them out. That extra layer is the whole trick: "
      "the same .class file works on Windows, Mac and Linux, because each of "
      "them has its own JVM that speaks the same instruction set.",
      "javac compiles .java source to .class files containing BYTECODE — a "
      "platform-independent instruction set for the JVM. At runtime the JVM "
      "loads, verifies and links those classes, then interprets the bytecode. "
      "Hot methods are then compiled to native machine code by the JIT "
      "(just-in-time) compiler, which is why long-running Java is fast while "
      "short programs feel slow to start. 'Write once, run anywhere' is a "
      "property of the bytecode, not of the source.",
      ["jvm", "bytecode", "jit", "compilation"],
      code="// File: Hello.java   —   the file name must match the public class name.\npublic class Hello {\n    // The JVM looks for exactly this signature to start the program.\n    public static void main(String[] args) {\n        System.out.println(\"Hello, \" + (args.length > 0 ? args[0] : \"world\"));\n    }\n}\n\n// Terminal:\n//   javac Hello.java      -> produces Hello.class (bytecode)\n//   java Hello Priya      -> the JVM runs it",
      output="Hello, Priya\n\n(and with no argument:  Hello, world)",
      version="The single-file launch `java Hello.java` — compile and run in one "
              "step, no .class file left behind — is Java 11+. Before that you "
              "always ran javac first.",
      gotcha="Q: is Java compiled or interpreted?  Almost everyone answers one or "
             "the other and both are half right. It is compiled to BYTECODE ahead "
             "of time, then that bytecode is interpreted AND selectively compiled "
             "to native code at runtime by the JIT. Saying 'both, and here is the "
             "boundary' is the answer.",
      quiz={
          "q": "You compile Foo.java on a Mac and copy Foo.class to a Linux server. "
               "What happens when you run it there?",
          "options": [
              "It runs — the .class file contains bytecode, and the Linux JVM executes it",
              "It fails — .class files contain native machine code for the machine that compiled them",
              "It runs, but only if the Linux machine has the same CPU architecture",
              "It must be recompiled, because javac targets the host operating system",
          ],
          "answer": 0,
          "why": "Option A is right and it is the entire point of the JVM. Option B "
                 "describes C, not Java, and it is the intuition people bring from "
                 "other languages. Option C confuses the JVM's job with the JIT's — "
                 "the JIT does produce CPU-specific code, but at RUNTIME, from the "
                 "portable bytecode. Option D mixes up javac's --release flag "
                 "(which targets a Java VERSION) with targeting an OS, which javac "
                 "never does.",
      },
      complexity="Startup cost is real: JVM boot plus class loading is tens to "
                 "hundreds of milliseconds, which is why Java lost ground to Go for "
                 "CLI tools and why GraalVM native-image exists.",
      pitfalls="File name must match the public class name exactly, including case. "
               "`main` must be public static void with a String[] parameter — "
               "`String... args` also works (it is the same type after compilation), "
               "but `int[] args` or a non-static main compiles fine and then fails "
               "at launch with 'Main method not found'.",
      followups="What is the difference between JDK, JRE and JVM? JDK = the tools "
                "(javac, jar, javadoc) + JRE. JRE = the JVM + the standard library. "
                "JVM = the thing that executes bytecode. Since Java 11 there is no "
                "separately distributed JRE — you ship a trimmed runtime with jlink.",
      difficulty="Easy", frequency="Very common — a standard opener",
      mnemonic="SOURCE → BYTECODE → JVM → (JIT) → machine code. Two compilers, not one.",
      diagram=(
          "  Hello.java                                                      \n"
          "      |  javac  (ahead-of-time, ONCE)                             \n"
          "      v                                                           \n"
          "  Hello.class   <-- BYTECODE. Portable. This is what you ship.     \n"
          "      |                                                           \n"
          "      |  java Hello                                               \n"
          "      v                                                           \n"
          "  +---------------------------------------------------+           \n"
          "  |                      JVM                          |           \n"
          "  |  class loader -> verifier -> interpreter          |           \n"
          "  |                        |                          |           \n"
          "  |                        | method called a lot?     |           \n"
          "  |                        v                          |           \n"
          "  |                  JIT COMPILER  --> native code    |           \n"
          "  +---------------------------------------------------+           \n"
          "  A DIFFERENT JVM ON EACH PLATFORM. Same .class file for all.      "
      )),

    Q("setup",
      "JDK vs JRE vs JVM — and which one do you install?",
      "Three names for three nested things. The JVM is the engine that runs the "
      "program. The JRE is the engine plus the standard library — everything "
      "needed to RUN Java but not to write it. The JDK is the JRE plus the tools "
      "you need to BUILD Java: the compiler, the debugger, the jar packager. "
      "If you are writing code you install the JDK, and it contains the other two.",
      "JVM: the specification and its implementations (HotSpot, OpenJ9, GraalVM) "
      "— loads, verifies and executes bytecode. JRE: JVM + the class library "
      "(java.lang, java.util, ...). JDK: JRE + javac, javadoc, jar, jshell, "
      "jlink, jdeps, and the debugging/profiling tools. Since Java 11 Oracle no "
      "longer ships a standalone JRE; you produce a minimal runtime for your "
      "application with jlink instead, which is smaller than a full JRE because "
      "it includes only the modules you actually use.",
      ["jdk", "jre", "jvm", "tooling"],
      version="Java 11 removed the separately downloadable JRE and Java Web Start. "
              "jlink (Java 9+) replaced it. If a tutorial tells you to 'download "
              "the JRE', it predates 2018.",
      quiz={
          "q": "Your production server only needs to RUN a Java application, never "
               "compile one. On Java 17, what do you install?",
          "options": [
              "A jlink-produced runtime image containing only the modules the app needs",
              "The JRE, which is the runtime-only distribution",
              "The full JDK — there is no other option on modern Java",
              "The JVM on its own, downloaded separately from the class library",
          ],
          "answer": 0,
          "why": "Option A is the modern answer and it is why jlink exists — a "
                 "trimmed image is often 40-60MB against a JDK's 300MB. Option B is "
                 "the answer everyone gives and it has been wrong since Java 11, "
                 "when the standalone JRE was discontinued. Option C is what people "
                 "fall back to and it works while shipping a compiler you do not "
                 "need. Option D is not a thing — the JVM is not distributed "
                 "without a class library, because it cannot run anything without "
                 "java.lang.",
      },
      mnemonic="JDK ⊃ JRE ⊃ JVM. Outermost is for writing, innermost is for running.",
      difficulty="Easy", frequency="Very common — usually the second question asked",
      followups="Which JDK build? OpenJDK is the reference implementation; Temurin, "
                "Corretto, Zulu and Liberica are free certified builds of it. Oracle "
                "JDK is the same code with a different licence. For almost every "
                "purpose they are interchangeable."),

    # ══════════════════════════════════════════════════════════════════
    #  Syntax & Primitives
    # ══════════════════════════════════════════════════════════════════

    Q("basics",
      "Primitives vs objects — the split that explains half of Java",
      "Java has two completely different kinds of value. A PRIMITIVE (int, "
      "double, boolean, char and four others) is the actual number, stored "
      "directly in the variable, like writing 5 on a sticky note. An OBJECT is "
      "stored somewhere else in memory and the variable holds only its address, "
      "like writing down the address of a house rather than the house. That one "
      "difference explains why == means different things for the two, why one "
      "can be null and the other cannot, and why collections cannot hold ints.",
      "Eight primitives: byte(8), short(16), int(32), long(64), float(32), "
      "double(64), char(16, unsigned), boolean(unspecified size). They are "
      "value types — assignment copies the value, == compares the value, they "
      "have a default (0 / 0.0 / '\\u0000' / false) and can never be null. "
      "Everything else is a reference type: the variable holds a reference, "
      "assignment copies the reference (not the object), == compares references, "
      "the default is null. Each primitive has a wrapper class (Integer, Double, "
      "...) so it can be used where an object is required — generics, "
      "collections, Optional — and the compiler inserts the conversions "
      "automatically, which is where the traps come from.",
      ["primitives", "references", "memory", "wrappers"],
      code="int a = 5;\nint b = a;          // COPIES the value 5\nb = 99;\nSystem.out.println(a);          // a is untouched\n\nint[] x = {1, 2, 3};\nint[] y = x;        // COPIES THE REFERENCE — both names, one array\ny[0] = 99;\nSystem.out.println(x[0]);       // x sees the change\n\nInteger boxed = null;           // legal: Integer is an object\n// int prim = null;             // COMPILE ERROR: int cannot be null\nSystem.out.println(boxed);",
      output="5\n99\nnull",
      gotcha="Q: does Java pass by value or by reference?  ALWAYS BY VALUE — with no "
             "exceptions. The confusion is that for an object the VALUE BEING "
             "PASSED IS THE REFERENCE. So a method can mutate the object you handed "
             "it (same house) and cannot make your variable point at a different "
             "object (it got a copy of the address). People say 'pass by reference' "
             "because the first half feels like it; the second half is the test.",
      quiz={
          "q": "void f(int[] a) { a[0] = 9; a = new int[]{7}; }  — called as "
               "int[] arr = {1}; f(arr); System.out.println(arr[0]);",
          "options": [
              "9 — the element write is visible, the reassignment is not",
              "7 — the method replaced the array",
              "1 — Java passes by value, so the method cannot affect the caller at all",
              "It does not compile — you cannot reassign a parameter",
          ],
          "answer": 0,
          "why": "Option A is right and it is the whole pass-by-value story in one "
                 "line: `a` is a COPY of the reference, so writing THROUGH it "
                 "reaches the caller's array, and reassigning it only changes the "
                 "copy. Option B is what 'pass by reference' would give, which is "
                 "why it is the popular wrong answer. Option C over-corrects — it "
                 "hears 'pass by value' and concludes nothing can be mutated. "
                 "Option D is a guess; parameters are ordinary local variables and "
                 "are reassignable unless declared final.",
      },
      complexity="A primitive int is 4 bytes. An Integer is an object: header plus "
                 "the field, typically 16 bytes, plus 4-8 bytes for the reference "
                 "pointing at it. An int[1_000_000] is ~4MB; an Integer[1_000_000] "
                 "with distinct values is roughly 20MB. THAT RATIO IS WHY IntStream "
                 "AND int[] EXIST ALONGSIDE Stream<Integer> AND List<Integer>.",
      pitfalls="`==` on wrappers compares references, not values — see the Integer "
               "cache entry. Unboxing a null wrapper throws NullPointerException at "
               "a line that contains no visible method call.",
      followups="Why does `List<int>` not compile? Generics erase to Object, and "
                "Object cannot hold a primitive. Project Valhalla is the long-running "
                "effort to fix exactly this.",
      difficulty="Easy", frequency="Fundamental — assumed, then tested via traps",
      mnemonic="Primitive = the value on the note. Object = the address on the note.",
      diagram=(
          "  PRIMITIVE                      REFERENCE                        \n"
          "  int a = 5;                     int[] x = {1,2,3};               \n"
          "                                                                  \n"
          "  stack                          stack            heap            \n"
          "  +-------+                      +-------+       +-----------+    \n"
          "  | a | 5 |                      | x |  --------->| 1 | 2 | 3 |   \n"
          "  +-------+                      +-------+       +-----------+    \n"
          "                                     ^                            \n"
          "  int b = a;  copies the 5       int[] y = x;  copies the ARROW    \n"
          "  +-------+                      +-------+                        \n"
          "  | b | 5 |   independent        | y |  ---------^  SAME array     \n"
          "  +-------+                      +-------+                        "
      )),

    Q("basics",
      "Integer overflow — Java wraps around silently",
      "An int can hold values from about minus two billion to plus two billion. "
      "If a calculation goes past the top it does not stop or complain — it "
      "wraps around to the very bottom, like a car odometer rolling over. Your "
      "program carries on with a large negative number where you expected a "
      "large positive one, and nothing anywhere reports a problem.",
      "int is a 32-bit two's-complement signed value: MIN_VALUE = -2^31 = "
      "-2,147,483,648 and MAX_VALUE = 2^31 - 1 = 2,147,483,647. Arithmetic "
      "overflow is DEFINED to wrap (unlike C, where signed overflow is undefined "
      "behaviour) and is never reported. The range is asymmetric — one more "
      "negative value than positive — so Math.abs(Integer.MIN_VALUE) returns "
      "Integer.MIN_VALUE, still negative. Use Math.addExact / multiplyExact to "
      "get an ArithmeticException instead of silence, long for a wider range, or "
      "BigInteger for unbounded.",
      ["overflow", "int", "arithmetic", "twos-complement"],
      code="System.out.println(Integer.MAX_VALUE);          // the ceiling\nSystem.out.println(Integer.MAX_VALUE + 1);      // wraps to the floor\nSystem.out.println(Math.abs(Integer.MIN_VALUE)); // still negative!\n\n// The classic binary-search bug, present in the JDK itself until 2006:\nint low = 1_500_000_000, high = 2_000_000_000;\nSystem.out.println((low + high) / 2);           // overflows -> negative\nSystem.out.println(low + (high - low) / 2);     // safe form\n\n// Ask for an exception instead of silence:\ntry {\n    Math.addExact(Integer.MAX_VALUE, 1);\n} catch (ArithmeticException e) {\n    System.out.println(\"caught: \" + e.getMessage());\n}",
      output="2147483647\n-2147483648\n-2147483648\n-397483648\n1750000000\ncaught: integer overflow",
      gotcha="Q: what is Math.abs(Integer.MIN_VALUE)?  Everyone says 2147483648, "
             "and that value DOES NOT EXIST in an int — the range is asymmetric, "
             "so the only thing abs can return is MIN_VALUE itself, unchanged and "
             "negative. It is the single most surprising line in the Math class, "
             "and it is documented behaviour, not a bug.",
      version="Math.addExact / subtractExact / multiplyExact / toIntExact arrived "
              "in Java 8. Before that you hand-rolled the check.",
      quiz={
          "q": "Why is `low + (high - low) / 2` preferred over `(low + high) / 2` in "
               "a binary search?",
          "options": [
              "`low + high` can overflow int and become negative, indexing out of bounds",
              "It is faster — one fewer addition on most CPUs",
              "It rounds toward low instead of away from it, which matters for correctness",
              "It avoids a division by zero when low equals high",
          ],
          "answer": 0,
          "why": "Option A is right and this exact bug lived in java.util.Arrays."
                 "binarySearch for nine years. Option B is backwards — the safe form "
                 "does MORE arithmetic; it is chosen for correctness, not speed. "
                 "Option C sounds plausible because rounding does matter in binary "
                 "search, but both forms truncate identically for non-negative "
                 "inputs. Option D is invented; neither form can divide by zero.",
      },
      pitfalls="`int seconds = days * 24 * 60 * 60;` overflows at about 24,855 days. "
               "Multiplying two ints and assigning to a long does NOT help — the "
               "multiplication happens in int first and the overflow has already "
               "occurred. Cast one operand: `(long) a * b`.",
      followups="Does long overflow too? Yes, at ~9.2 x 10^18. System.nanoTime() is "
                "documented as only meaningful for DIFFERENCES precisely because its "
                "absolute value can overflow.",
      difficulty="Easy", frequency="Very common — the binary-search version is a classic",
      mnemonic="int is an odometer: it rolls over, it never errors.",
      examples=[
"""1. THE GOAL IN PLAIN ENGLISH — a fixed number of bits, and what happens when you run out

An `int` in Java is exactly 32 bits. Thirty-two binary digits can represent 2^32 = 4,294,967,296
distinct patterns, and Java spends them on the range −2,147,483,648 to +2,147,483,647.

WHEN A CALCULATION PRODUCES A RESULT OUTSIDE THAT RANGE, JAVA DOES NOT STOP, WARN, OR THROW. It keeps
the low 32 bits of the true answer and discards the rest, which — because of how two's complement works
— means the value WRAPS AROUND from the top to the bottom.

    2,147,483,647 + 1  =  −2,147,483,648

THE EVERYDAY VERSION: a car odometer with five digits. At 99,999 miles the next mile shows 00,000. The
car did not travel backwards; the display simply has nowhere else to go.

WHY THIS IS WORTH A WHOLE ENTRY: the failure is SILENT. A crash tells you where the bug is. A wrong
number does not, and it will flow through the rest of your program, into a database, into a report,
looking exactly like a real value.

TERMS AS THEY APPEAR:
- TWO'S COMPLEMENT: the standard binary encoding for signed integers. The top bit means "negative".
- OVERFLOW: a result too large for the type.
- DEFINED BEHAVIOUR: the spec says exactly what happens. Java's overflow is defined; C's is not.""",

"""2. THE INTUITION — why it wraps to NEGATIVE, specifically

The surprising part is not that it wraps. It is that it wraps to a large NEGATIVE number, and that
falls straight out of two's complement.

In 32 bits, the value is interpreted as: the top bit contributes −2^31 and the remaining 31 bits
contribute their usual positive amounts.

    0111 1111 ... 1111   =  +2,147,483,647   (MAX_VALUE — every bit but the top one is set)
    add 1
    1000 0000 ... 0000   =  −2,147,483,648   (MIN_VALUE — only the top bit is set)

    THE ADDITION IS COMPLETELY ORDINARY BINARY ARITHMETIC. Adding 1 to a run of 31 ones carries all the
    way up and sets the 32nd bit. What changed is the INTERPRETATION: that bit means −2^31.

SO THE HARDWARE DID NOTHING SPECIAL AND NOTHING WENT WRONG AT THE BIT LEVEL. The bits are exactly what
you would get on paper; only the sign convention makes them read as negative.

AND THIS IS WHY THE RANGE IS ASYMMETRIC. There is exactly one pattern with only the top bit set, and it
means −2^31. There is no pattern that means +2^31, because that would need a 33rd bit. SO THE NEGATIVE
SIDE GOES ONE FURTHER THAN THE POSITIVE SIDE, and section 3 is about the consequences of that.""",

"""3. THE CONSEQUENCE PEOPLE NEVER PREDICT — Math.abs(Integer.MIN_VALUE)

    System.out.println(Math.abs(Integer.MIN_VALUE));   →   -2147483648

    THE ABSOLUTE VALUE FUNCTION RETURNED A NEGATIVE NUMBER.

It is not a bug and it is documented in the Javadoc. The reason is the asymmetry from section 2:

    |−2,147,483,648| = 2,147,483,648
    Integer.MAX_VALUE = 2,147,483,647

    THE CORRECT ANSWER IS ONE LARGER THAN THE LARGEST INT. It cannot be represented, so `abs` returns
    its argument unchanged.

WHERE THIS ACTUALLY BITES, and it is a real class of security bug:

    if (Math.abs(userSuppliedIndex) < array.length) { use(array[userSuppliedIndex]); }

    Pass Integer.MIN_VALUE and `Math.abs` returns a large NEGATIVE number, which IS less than
    array.length, so the guard passes and the array access throws — or worse, in a language without
    bounds checking, reads memory it should not.

THE SAME ASYMMETRY PRODUCES TWO MORE SURPRISES:

    Integer.MIN_VALUE / -1   →   throws? No — it overflows to Integer.MIN_VALUE. (The only division
                                 that overflows. Note `Integer.MIN_VALUE % -1` is 0, correctly.)
    -Integer.MIN_VALUE       →   Integer.MIN_VALUE. Negation cannot escape it either.

    THE RULE TO REMEMBER: ANY OPERATION THAT NEGATES OR TAKES A MAGNITUDE HAS A SPECIAL CASE AT
    MIN_VALUE. If your code does either on untrusted input, handle it explicitly.""",

"""4. EDGE CASES AND WHERE OVERFLOW HIDES

CASE 1 — THE BINARY SEARCH MIDPOINT. `(low + high) / 2` overflows once low + high exceeds MAX_VALUE.
This bug was present in java.util.Arrays.binarySearch from 1997 until 2006 and in most textbooks for
longer. THE FIX IS `low + (high - low) / 2`, which never forms the large sum. It is the canonical
example precisely because the buggy version is more readable.

CASE 2 — MULTIPLYING THEN WIDENING. `long ms = hours * 60 * 60 * 1000;` where hours is an int.
THE MULTIPLICATION HAPPENS IN INT AND OVERFLOWS BEFORE THE ASSIGNMENT WIDENS IT. Assigning to a long
does not retroactively fix it. The fix is to widen one operand first: `(long) hours * 60 * 60 * 1000`.

CASE 3 — ACCUMULATING IN A LOOP. Summing a million values that average 5,000 exceeds MAX_VALUE. The sum
silently goes negative and any later `if (sum > threshold)` behaves absurdly.

CASE 4 — hashCode ARITHMETIC. String.hashCode multiplies by 31 repeatedly and overflows constantly by
design. THAT IS FINE — hash codes only need to be consistent, not meaningful — and it is worth knowing
so that a negative hashCode does not look like a bug. But `Math.abs(hashCode()) % buckets` is a real
bug for exactly the reason in section 3.

CASE 5 — TIME AND DATE ARITHMETIC IN MILLISECONDS. An int holds about 24.8 days of milliseconds. Any
duration arithmetic in int milliseconds has a bug waiting at day 25.

CASE 6 — char AND short PROMOTE TO int BEFORE ARITHMETIC. `short a = 30000, b = 30000; short c = (short)(a+b);`
— the addition is done in int (60000, no overflow) and then the CAST truncates to −5536.

CASE 7 — long IS NOT SAFE, ONLY WIDER. It overflows at ±9.22 x 10^18. Nanosecond arithmetic overflows a
long after about 292 years, which is why System.nanoTime() is documented as valid only for differences.""",

"""5. THE ALTERNATIVES — and what each costs

`long` — 64 bits, range ±9.22 x 10^18.
    THE USUAL FIX, and it only moves the cliff. Free in speed on a 64-bit CPU; doubles the memory of
    large arrays.

`Math.addExact`, `subtractExact`, `multiplyExact`, `negateExact`, `toIntExact` (Java 8+) — the same
arithmetic, but THEY THROW ArithmeticException INSTEAD OF WRAPPING.
    THIS IS THE RIGHT DEFAULT FOR FINANCIAL AND ACCOUNTING CODE, where a silently wrong total is far
    worse than a crash. The cost is a branch per operation, which the JIT handles well.

`BigInteger` — arbitrary precision, no overflow ever possible.
    THE COST IS LARGE: every value is an object, every operation allocates, and it is roughly two
    orders of magnitude slower than primitive arithmetic. Correct for cryptography and for exact
    factorials; wrong for a loop counter.

`Math.floorDiv` / `Math.floorMod` — not about overflow, but they fix the OTHER integer surprise:
    -7 / 2 == -3 (truncates toward zero) and -7 % 2 == -1 (the sign follows the DIVIDEND).
    Math.floorMod(-7, 2) == 1, which is what modular arithmetic actually means and what you want for
    wrapping an index around an array.

`Integer.parseUnsignedInt` and `Integer.toUnsignedLong` (Java 8+) — treat the 32 bits as unsigned when
you genuinely need 0 to 4.29 billion. Java has no unsigned int type; these are the workaround.

WHAT TO ACTUALLY DO: use `long` by default for anything counting real-world quantities, use the `Exact`
methods anywhere a wrong answer costs money, and write the binary-search midpoint the safe way out of
habit rather than after checking whether it can overflow.""",

"""6. HOW TO AVOID IT — numbered steps

STEP 1 — KNOW THE TWO NUMBERS. Integer.MAX_VALUE ≈ 2.1 billion, Long.MAX_VALUE ≈ 9.2 x 10^18. Most
overflow bugs are written by someone who has never compared their data's scale to the first number.

STEP 2 — ASK "CAN THIS EXCEED TWO BILLION?" of every int that holds a count, a sum, a duration in
milliseconds, or a product of two other ints.

STEP 3 — WIDEN THE OPERAND, NOT THE RESULT. `(long) a * b`, never `long c = a * b`.

STEP 4 — WRITE THE MIDPOINT AS `low + (high - low) / 2` ALWAYS, even when you have convinced yourself
it is safe.

STEP 5 — USE Math.addExact AND FRIENDS WHERE A WRONG NUMBER IS EXPENSIVE. A thrown exception is a bug
report; a wrapped value is a mystery.

STEP 6 — HANDLE MIN_VALUE EXPLICITLY WHEREVER YOU NEGATE OR TAKE AN ABSOLUTE VALUE OF UNTRUSTED INPUT.
Math.abs, unary minus and division by −1 all fail there.

STEP 7 — DO NOT USE Math.abs(hashCode()) % n. Use `(hashCode() & 0x7fffffff) % n` or
Math.floorMod(hashCode(), n), both of which are correct at MIN_VALUE.

STEP 8 — PREFER java.time OVER MILLISECOND ARITHMETIC. Duration and Instant carry longs internally and
have overflow-checked arithmetic.

STEP 9 — TEST WITH THE BOUNDARIES. MIN_VALUE, MAX_VALUE, 0, −1 and 1 catch more integer bugs than any
number of random values.""",

"""7. THE ANSWER IN PLAIN LANGUAGE — what you would say out loud

'An int in Java is exactly 32 bits, holding roughly minus two billion to plus two billion. When a
calculation goes outside that, Java DOES NOT throw or warn — it keeps the low 32 bits and the value
wraps around from the top to the bottom. MAX_VALUE plus one is MIN_VALUE.

And it is worth being clear that this is DEFINED behaviour, not undefined. In C, signed overflow is
undefined and the compiler is allowed to do anything, including deleting your overflow check. In Java
the spec says exactly what happens, which makes it predictable and, if anything, more dangerous —
because it will never crash and tell you.

The reason it wraps to a negative number falls out of two's complement. MAX_VALUE is a zero followed by
thirty-one ones; adding one carries all the way up and sets the top bit, and the top bit means minus
two-to-the-thirty-one. The hardware did completely ordinary arithmetic — only the interpretation of
that top bit makes it read as negative.

That also explains the asymmetry: there is exactly one bit pattern with only the top bit set, and it
means MIN_VALUE, but there is no pattern meaning positive two-to-the-thirty-one. So the negative side
goes one further. Which gives you the most surprising line in the Math class: MATH.ABS OF
INTEGER.MIN_VALUE RETURNS INTEGER.MIN_VALUE, still negative — because the correct answer is one larger
than the largest int and simply cannot be represented. That is a real source of security bugs in
bounds checks written as "if abs of index is less than length".

The classic example is the binary search midpoint. `(low + high) / 2` overflows once the sum passes
two billion, and the midpoint goes negative and indexes out of bounds. That bug lived in the JDK's own
Arrays.binarySearch for nine years. The fix is `low + (high - low) / 2`, which never forms the large
sum — and I would write it that way by habit rather than after deciding it is needed.

Two other places it hides. Multiplying then widening: `long ms = hours * 60 * 60 * 1000` does the
multiplication in INT and overflows BEFORE the assignment widens it, so you cast one operand first. And
milliseconds in an int overflow after about twenty-five days, which catches out a lot of duration code.

For prevention: use long by default for anything counting real-world quantities, and use Math.addExact
and friends anywhere a wrong number costs money — they throw ArithmeticException instead of wrapping,
and a thrown exception is a bug report while a wrapped value is a mystery.'""",

"""8. THE CODE, LINE BY LINE

    System.out.println(Integer.MAX_VALUE);
    // 2147483647 = 2^31 - 1. Binary: 0111 1111 ... 1111 — every bit set EXCEPT the
    // top one, which is the sign bit.

    System.out.println(Integer.MAX_VALUE + 1);
    // -2147483648. Adding 1 carries through all thirty-one 1s and sets the top bit:
    // 1000 0000 ... 0000. THE ARITHMETIC IS ORDINARY; only the INTERPRETATION of the
    // top bit (worth -2^31) makes the result negative. No exception, no warning.

    System.out.println(Math.abs(Integer.MIN_VALUE));
    // -2147483648. The true answer, 2147483648, is ONE MORE than MAX_VALUE and has no
    // int representation — so abs returns its argument unchanged. DOCUMENTED, not a bug.

    int low = 1_500_000_000, high = 2_000_000_000;
    //  ^ underscores in numeric literals are legal since Java 7 and are purely visual.

    System.out.println((low + high) / 2);
    // -397483648. low + high = 3,500,000,000 which exceeds MAX_VALUE by 1,352,516,353,
    // so it wraps to -794,967,296, and halving THAT gives -397,483,648.
    // THIS IS THE JDK's OWN BINARY SEARCH BUG, shipped from 1997 to 2006.

    System.out.println(low + (high - low) / 2);
    // 1750000000. high - low = 500,000,000 — well within range — so the halving and
    // the addition both stay in bounds. SAME MATHEMATICAL RESULT, DIFFERENT
    // INTERMEDIATE VALUES. That is the entire trick.

    try {
        Math.addExact(Integer.MAX_VALUE, 1);
    } catch (ArithmeticException e) {
        System.out.println("caught: " + e.getMessage());
    }
    // caught: integer overflow
    // ^ Java 8+. Identical arithmetic, and it CHECKS the result and throws instead of
    //   wrapping. This is what you want anywhere a silently wrong number is expensive.

THE SAFE PATTERNS, side by side:

    (low + high) / 2                  // WRONG — forms a sum that can overflow
    low + (high - low) / 2            // right — forms only a difference
    (low + high) >>> 1                // also right — unsigned shift treats the
                                      //   overflowed sum's bits as unsigned, and for
                                      //   non-negative low and high this recovers the
                                      //   correct midpoint. Clever, and less readable.

    long ms = hours * 3600_000;       // WRONG — multiplies in int, then widens
    long ms = (long) hours * 3600_000; // right — widens first, multiplies in long

    Math.abs(h) % n                   // WRONG — negative at MIN_VALUE
    (h & 0x7fffffff) % n              // right — masks off the sign bit
    Math.floorMod(h, n)               // right, and clearer (Java 8+)""",

"""9. THE TRACE — the bits, step by step

`Integer.MAX_VALUE + 1`, in 32 bits:

    step                      binary (grouped)                              decimal
    -----------------------------------------------------------------------------------
    Integer.MAX_VALUE         0111 1111 1111 1111 1111 1111 1111 1111    2,147,483,647
    + 1                       0000 0000 0000 0000 0000 0000 0000 0001                1
    ordinary binary addition:
      the low 31 ones all carry, the carry lands in bit 31
    result                    1000 0000 0000 0000 0000 0000 0000 0000   −2,147,483,648

    READ THE RESULT ROW TWICE. As an UNSIGNED pattern it is 2,147,483,648 — exactly the right answer.
    As a SIGNED int the top bit is worth −2^31 and every other bit is 0, so it is −2,147,483,648.
    THE BITS ARE CORRECT. THE INTERPRETATION IS WHAT FLIPS.

`(low + high) / 2` with low = 1,500,000,000 and high = 2,000,000,000:

    quantity                   true value          as a 32-bit int         why
    ---------------------------------------------------------------------------------------
    low + high              3,500,000,000            −794,967,296     3.5e9 − 2^32 = −794,967,296
    (low + high) / 2        1,750,000,000            −397,483,648     halving a negative
    high − low                500,000,000             500,000,000     comfortably in range
    (high − low) / 2          250,000,000             250,000,000     still fine
    low + (…)               1,750,000,000           1,750,000,000     CORRECT

    THE TWO FORMS ARE ALGEBRAICALLY IDENTICAL AND DIFFER ONLY IN THE SIZE OF THE INTERMEDIATE VALUE.
    That is the general lesson: in fixed-width arithmetic, ALGEBRAIC EQUIVALENCE DOES NOT IMPLY
    COMPUTATIONAL EQUIVALENCE, and rearranging an expression to keep intermediates small is a real
    technique rather than a stylistic choice.

`Math.abs(Integer.MIN_VALUE)`:

    MIN_VALUE               1000 0000 … 0000                −2,147,483,648
    abs negates it: two's complement negation is "invert all bits, add 1"
    invert                  0111 1111 … 1111                 2,147,483,647
    add 1                   1000 0000 … 0000                −2,147,483,648   ← back where it started

    NEGATION IS ITS OWN INVERSE HERE. MIN_VALUE is the unique fixed point of two's complement negation,
    which is exactly why abs, unary minus, and division by −1 all fail on it and only on it.

WHICH LINE PRODUCED WHICH BEHAVIOUR:

    THE 32-BIT WIDTH produced every number in this entry. On a hypothetical 64-bit `int` none of these
    examples would overflow, and all of the same failures would reappear at 9.2 x 10^18.
    THE TWO'S COMPLEMENT ENCODING produced the WRAP TO NEGATIVE rather than to zero. A sign-magnitude
    encoding would wrap differently and would have two zeros.
    THE ASYMMETRIC RANGE — one extra negative value — produced the Math.abs surprise, the
    MIN_VALUE / −1 surprise, and the negation fixed point. ALL THREE ARE THE SAME FACT.
    JAVA DEFINING OVERFLOW rather than leaving it undefined is why these results are reproducible on
    every JVM. In C the equivalent program is allowed to do anything at all.""",

"""10. COMPLEXITY, THE MISTAKES, AND THE TAKEAWAY

    int:      32 bits, −2,147,483,648 to 2,147,483,647
    long:     64 bits, ±9.22 x 10^18
    OVERFLOW IS DEFINED TO WRAP and is NEVER reported. No exception, no warning, no compiler flag.
    THE RANGE IS ASYMMETRIC: exactly one more negative value than positive.

THE #1 MISTAKE: `(low + high) / 2`. The sum overflows and the midpoint goes negative. It shipped in the
JDK's own binary search for nine years.

THE #2 MISTAKE: `long x = intA * intB;`. The multiplication happens in int and overflows before the
widening. Cast one operand: `(long) intA * intB`.

THE #3 MISTAKE: assuming Math.abs always returns a non-negative number. At MIN_VALUE it does not, and
`Math.abs(hash) % n` is a real bug.

THE #4 MISTAKE: durations in int milliseconds. They overflow after about 24.8 days.

THE #5 MISTAKE: expecting an exception. Java will not give you one unless you ask with the Exact
methods.

THE #6 MISTAKE: thinking `%` gives a mathematical modulus. −7 % 2 is −1 in Java, because the sign
follows the dividend. Math.floorMod gives 1.

THE #7 MISTAKE: casting after arithmetic on short or char. `(short)(a + b)` promotes to int, adds
correctly, then TRUNCATES — so the overflow happens in the cast, not the addition.

THE #8 MISTAKE: reaching for BigInteger by default. It is roughly two orders of magnitude slower and
allocates on every operation; long is almost always the right answer.

ONE-SENTENCE TAKEAWAY: an int is 32 two's-complement bits, so arithmetic past ±2.1 billion WRAPS
SILENTLY to the other end rather than throwing — MAX_VALUE + 1 is MIN_VALUE — and because the range is
asymmetric by exactly one value, Math.abs(Integer.MIN_VALUE) is itself, still negative; so write
`low + (high - low) / 2` by habit, cast before multiplying rather than after, and use Math.addExact
anywhere a silently wrong number would cost money.""",
      ]),

    Q("basics",
      "0.1 + 0.2 != 0.3 — floating point, and when to use BigDecimal",
      "Computers store fractions in binary, and some perfectly ordinary decimal "
      "numbers have no exact binary form — 0.1 is one of them, the same way 1/3 "
      "has no exact decimal form. So 0.1 is stored as something very slightly "
      "off, and when you add three slightly-off numbers the error shows. This "
      "has nothing to do with Java; it is how every language using standard "
      "floating point behaves.",
      "double and float are IEEE 754 binary floating point. A finite binary "
      "fraction can only represent numbers of the form m/2^k, and 0.1 is not one "
      "— it is stored as the nearest representable double, which is "
      "0.1000000000000000055511151231257827. Errors accumulate under addition. "
      "NEVER USE double FOR MONEY. Use BigDecimal (constructed from a STRING, "
      "not a double) for exact decimal arithmetic, or store whole pence/cents in "
      "a long. For comparisons, never use == on doubles; compare "
      "Math.abs(a - b) < epsilon with an epsilon appropriate to your scale.",
      ["floating-point", "double", "bigdecimal", "money", "ieee754"],
      code="System.out.println(0.1 + 0.2);\nSystem.out.println(0.1 + 0.2 == 0.3);\nSystem.out.printf(\"%.20f%n\", 0.1);\n\n// Money the wrong way:\ndouble total = 0.0;\nfor (int i = 0; i < 10; i++) total += 0.1;\nSystem.out.println(total);\n\n// Money the right way — note the STRING constructor:\n// (java.math.BigDecimal imported at the top of the file)\nBigDecimal a = new BigDecimal(\"0.1\");\nSystem.out.println(a.add(new BigDecimal(\"0.2\")));\n\n// The trap inside the fix:\nSystem.out.println(new BigDecimal(0.1));",
      output="0.30000000000000004\nfalse\n0.10000000000000000555\n0.9999999999999999\n0.3\n0.1000000000000000055511151231257827021181583404541015625",
      gotcha="Q: BigDecimal fixes floating point, so `new BigDecimal(0.1)` is exact?  "
             "NO — and this is the trap inside the fix. That constructor takes a "
             "DOUBLE, which is already wrong before BigDecimal ever sees it, and it "
             "then faithfully preserves all 55 digits of the error. ALWAYS USE THE "
             "STRING CONSTRUCTOR, `new BigDecimal(\"0.1\")`, or BigDecimal.valueOf("
             "0.1) which routes through Double.toString.",
      version="BigDecimal has been there since Java 1.1. `strictfp` became the "
              "default and the keyword became a no-op in Java 17.",
      quiz={
          "q": "You are storing a price. Which is correct?",
          "options": [
              "long pence, or BigDecimal built from a String",
              "double, rounded to 2 decimal places when displayed",
              "float, because prices need less precision than scientific values",
              "BigDecimal built from a double, which is exact by definition",
          ],
          "answer": 0,
          "why": "Option A is the two acceptable answers. Option B is the most common "
                 "production bug in this area — rounding at DISPLAY time hides the "
                 "error while the stored total continues to drift, and it reconciles "
                 "wrong. Option C is worse than option 2: float has ~7 significant "
                 "digits, so it cannot even represent £99,999.99 exactly. Option D "
                 "is the trap in the gotcha above — the double is already wrong "
                 "before BigDecimal receives it.",
      },
      pitfalls="`==` on doubles is almost always a bug. BigDecimal.equals compares "
               "SCALE as well as value, so `new BigDecimal(\"1.0\").equals(new "
               "BigDecimal(\"1.00\"))` is FALSE — use compareTo() == 0 instead. "
               "BigDecimal division can throw ArithmeticException for a non-"
               "terminating result unless you supply a scale and RoundingMode.",
      followups="Why 0.30000000000000004 specifically? Because the two stored values "
                "are each slightly above 0.1 and 0.2, and their exact sum rounds to "
                "the double just above 0.3. What about 0.5 or 0.25? Exact — they are "
                "1/2 and 1/4, both powers of two.",
      difficulty="Easy", frequency="Very common — asked in almost every junior interview",
      mnemonic="Binary cannot write 0.1, the way decimal cannot write 1/3."),

    # ══════════════════════════════════════════════════════════════════
    #  Strings
    # ══════════════════════════════════════════════════════════════════

    Q("strings",
      "Why == sometimes works on Strings, and why you must never rely on it",
      "Two Strings that look the same might be two separate objects in memory or "
      "the very same object. `==` asks 'are these the same object?' and .equals() "
      "asks 'do these have the same characters?'. Java keeps a shared pool of "
      "strings written directly in your code, so two identical literals really "
      "are the same object and == happens to work. Build the same text any other "
      "way — from input, from concatenation at runtime, with `new` — and you get "
      "a different object, so == is false even though the text matches.",
      "String literals are INTERNED: the compiler places them in the runtime "
      "constant pool and identical literals resolve to one instance. `new "
      "String(\"a\")` explicitly creates a second object. Compile-time constant "
      "expressions (final variables, literal concatenation) are folded by javac "
      "and interned too; anything computed at runtime is not. `.intern()` returns "
      "the pooled instance. THE ONLY CORRECT COMPARISON IS .equals(), and "
      "Objects.equals(a, b) if either may be null.",
      ["string", "equals", "interning", "string-pool"],
      code="String a = \"hello\";\nString b = \"hello\";\nString c = new String(\"hello\");\nString d = \"hel\" + \"lo\";          // folded by the COMPILER — a constant\nString part = \"hel\";\nString e = part + \"lo\";             // built at RUNTIME — a new object\n\nSystem.out.println(a == b);         // same pooled literal\nSystem.out.println(a == c);         // new String() forced a second object\nSystem.out.println(a == d);         // constant-folded to the same literal\nSystem.out.println(a == e);         // runtime concatenation -> different object\nSystem.out.println(a.equals(e));    // the only question worth asking\nSystem.out.println(a == e.intern());// intern() returns the pooled instance",
      output="true\nfalse\ntrue\nfalse\ntrue\ntrue",
      gotcha="Q: `a == d` where d is \"hel\" + \"lo\" — different from `a == e` where "
             "e is part + \"lo\"?  Yes, and the difference is WHO does the "
             "concatenation. Both operands of d are compile-time constants, so javac "
             "folds them into the literal \"hello\" and it lands in the pool. `part` "
             "is a variable, so e is built at runtime with a StringBuilder and is a "
             "fresh object. MAKE `part` FINAL AND `a == e` BECOMES TRUE — the same "
             "source line changes meaning based on a modifier three lines up. That "
             "is precisely why nobody should depend on ==.",
      version="String was char[]-backed until Java 8; since Java 9 it is byte[] plus "
              "a coder field (COMPACT STRINGS), which halves memory for Latin-1 text. "
              "The string pool moved from PermGen to the heap in Java 7.",
      quiz={
          "q": "String s1 = \"java\"; String s2 = new String(\"java\").intern(); "
               "What are s1 == s2 and s1.equals(s2)?",
          "options": [
              "true and true — intern() returns the pooled instance",
              "false and true — new String() always produces a distinct object",
              "true and false — intern() changes identity but not content",
              "false and false — the two were created by different mechanisms",
          ],
          "answer": 0,
          "why": "Option A is right: `new String(\"java\")` does create a distinct "
                 "object, but `.intern()` then RETURNS the pooled one and that is "
                 "what s2 holds. Option B is the popular answer because it stops "
                 "reading at `new String` and never accounts for the intern() call. "
                 "Option C has it backwards — equals() compares characters and is "
                 "true regardless. Option D ignores that equals() does not care how "
                 "an object was made.",
      },
      pitfalls="Interning at scale is a memory leak risk — the pool is a fixed-size "
               "hash table and interning millions of unique strings degrades it. "
               "Comparing with == passes your tests (small literals) and fails in "
               "production (strings from a database or a request body).",
      followups="Why is String immutable at all? Safe sharing across threads, safe "
                "use as a HashMap key (the hash cannot change under you), the "
                "security of not being able to mutate a validated file path or class "
                "name after the check, and hashCode caching.",
      difficulty="Easy", frequency="Extremely common — the #1 Java string question",
      mnemonic="== asks 'same house?'. equals asks 'same contents?'. Always ask contents.",
      diagram=(
          "  STRING POOL (in the heap since Java 7)                      \n"
          "  +---------------------+                                     \n"
          "  |  \"hello\"  <--------+---------- a                         \n"
          "  |                     |<--------- b   (same literal)         \n"
          "  |                     |<--------- d   (constant-folded)      \n"
          "  +---------------------+                                     \n"
          "                                                              \n"
          "  ORDINARY HEAP                                               \n"
          "  +---------------------+                                     \n"
          "  |  \"hello\"  <--------+---------- c   (new String)          \n"
          "  +---------------------+                                     \n"
          "  |  \"hello\"  <--------+---------- e   (runtime concat)      \n"
          "  +---------------------+                                     \n"
          "                                                              \n"
          "  a == b  TRUE     a == c  FALSE     a == e  FALSE            \n"
          "  a.equals(c)  TRUE  —  contents are contents                 "
      )),

    Q("strings",
      "String concatenation in a loop — why it is O(n²) and what to use instead",
      "A String cannot be changed once it is made. So `s = s + x` does not add to "
      "s — it builds a brand new String containing everything s had plus x, and "
      "points s at that. Inside a loop, that means copying the whole accumulated "
      "text on every single pass. Ten items is fine; ten thousand means copying "
      "roughly fifty million characters. StringBuilder keeps one growable buffer "
      "and appends into it, so nothing is copied repeatedly.",
      "String is immutable, so `+=` in a loop allocates a new String and copies "
      "the full accumulated length each iteration: 1 + 2 + ... + n = n(n+1)/2 "
      "character copies, i.e. O(n²) time and O(n²) allocation churn. StringBuilder "
      "maintains a resizable byte[] and appends in amortized O(1), doubling "
      "capacity when full — the same geometric-growth argument as ArrayList. "
      "javac DOES optimise a single concatenation expression into a StringBuilder "
      "(or, since Java 9, an invokedynamic call to StringConcatFactory), BUT IT "
      "CANNOT HOIST THAT OUT OF A LOOP, because each iteration is a separate "
      "expression. That is the whole reason the loop case is different.",
      ["string", "stringbuilder", "performance", "immutability"],
      code="// O(n^2) — a new String and a full copy every iteration\nString slow = \"\";\nfor (int i = 0; i < 5; i++) {\n    slow += i;              // javac makes a StringBuilder HERE, then throws it away\n}\nSystem.out.println(slow);\n\n// O(n) — one buffer, appended into\nStringBuilder sb = new StringBuilder();\nfor (int i = 0; i < 5; i++) {\n    sb.append(i);\n}\nSystem.out.println(sb.toString());\n\n// A SINGLE expression is fine — javac optimises it:\nString name = \"a\", tail = \"b\";\nString ok = \"x\" + name + \"y\" + tail;   // one StringBuilder, one pass\nSystem.out.println(ok);\n\nSystem.out.println(String.join(\"-\", \"a\", \"b\", \"c\"));",
      output="01234\n01234\nxayb\na-b-c",
      gotcha="Q: is `\"a\" + b + \"c\" + d` slow?  NO — a single concatenation "
             "EXPRESSION is compiled into one StringBuilder (Java 8) or one "
             "invokedynamic bootstrap (Java 9+), so it is already O(total length). "
             "THE LOOP IS THE PROBLEM, not the plus sign, because each iteration is "
             "its own expression and the compiler cannot see across iterations. "
             "People over-apply the rule and write StringBuilder for a two-part "
             "concatenation, which is slower AND uglier.",
      version="Java 9 replaced javac's StringBuilder desugaring with invokedynamic "
              "against StringConcatFactory, which lets the JVM pick a strategy at "
              "runtime and is typically faster. The n² loop behaviour is unchanged.",
      quiz={
          "q": "Building a 100,000-line report. Which is right?",
          "options": [
              "StringBuilder, or a Stream with Collectors.joining",
              "String += in a loop — javac optimises it into a StringBuilder anyway",
              "String.concat in a loop, which avoids the + operator's overhead",
              "An ArrayList<String> and then String.valueOf on the list",
          ],
          "answer": 0,
          "why": "Option A is right. Option B is the widespread half-truth — javac "
                 "does create a StringBuilder, but a NEW ONE PER ITERATION, which it "
                 "then discards, so the quadratic copying is untouched. Option C is "
                 "worse: String.concat allocates a new String every call with no "
                 "buffer at all. Option D produces the list's toString, "
                 "'[a, b, c]' — a real bug people ship, and the fix is "
                 "String.join or Collectors.joining.",
      },
      complexity="`+=` in a loop: O(n²) time. StringBuilder: amortized O(1) per "
                 "append, O(n) total, with the same doubling-growth argument as "
                 "ArrayList. At 10,000 appends that is ~50 million character copies "
                 "against ~20,000.",
      pitfalls="StringBuilder is NOT thread-safe; StringBuffer is the synchronised "
               "version and is essentially never what you want, because a builder is "
               "almost always a local variable. Pre-size it with `new "
               "StringBuilder(expectedLength)` when you know the size — it removes "
               "the resize copies entirely.",
      followups="What about String.format in a loop? Worse than both — it parses the "
                "format string every call. For structured output use a StringBuilder "
                "with append, or a single String.format outside the loop.",
      difficulty="Easy", frequency="Very common — and the loop-vs-expression nuance separates people",
      mnemonic="The + is fine. The LOOP around it is not."),

    # ══════════════════════════════════════════════════════════════════
    #  Classic traps
    # ══════════════════════════════════════════════════════════════════

    Q("traps",
      "Integer caching — why 127 == 127 but 128 != 128",
      "Java keeps a ready-made set of Integer objects for the small numbers "
      "everybody uses, from −128 to 127. When you write `Integer a = 127`, Java "
      "hands you the shared one from that set — so two variables holding 127 are "
      "literally the same object and == says true. Write 128 and there is no "
      "ready-made one, so Java builds a fresh object each time and == says false. "
      "The values are equal either way; the OBJECTS are not.",
      "Integer.valueOf(int) — which autoboxing compiles to — returns a cached "
      "instance for values in [−128, 127]. The lower bound is fixed by the JLS; "
      "THE UPPER BOUND IS A MINIMUM, not a maximum, and is configurable with "
      "-XX:AutoBoxCacheMax. The same caching exists for Byte, Short, Long, "
      "Character (0–127) and Boolean; Float and Double are NEVER cached. `new "
      "Integer(5)` always allocates and bypasses the cache — which is why it was "
      "deprecated in Java 9. The rule that follows: never use == on boxed types.",
      ["autoboxing", "integer-cache", "equals", "trap"],
      code="Integer a = 127, b = 127;\nInteger c = 128, d = 128;\nSystem.out.println(a == b);        // both from the cache\nSystem.out.println(c == d);        // two fresh objects\nSystem.out.println(c.equals(d));   // values are equal\n\nInteger e = 128;\nint f = 128;\nSystem.out.println(e == f);        // MIXED types -> e is UNBOXED, values compared\n\nLong g = 127L;\n// System.out.println(g.equals(127));  // false! Integer 127 != Long 127\nSystem.out.println(g.equals(127L));\n\nDouble h = 1.0, i = 1.0;\nSystem.out.println(h == i);        // Double is never cached",
      output="true\nfalse\ntrue\ntrue\ntrue\nfalse",
      gotcha="Q: `Integer e = 128; int f = 128; e == f`?  TRUE — and it looks like it "
             "contradicts `c == d` being false two lines earlier. The rule is that "
             "when ONE operand of == is a primitive, the other is UNBOXED and the "
             "comparison becomes numeric. Both-boxed compares references; "
             "mixed compares values. SO THE SAME OPERATOR MEANS TWO DIFFERENT THINGS "
             "DEPENDING ON THE STATIC TYPES, which is why == on wrappers is banned "
             "in most style guides rather than merely discouraged.",
      version="`new Integer(int)` deprecated in Java 9, marked for removal in Java "
              "16. Use Integer.valueOf or plain autoboxing.",
      quiz={
          "q": "Map<Integer,String> m; you put key 1000 and then look up with a "
               "different Integer holding 1000. What happens?",
          "options": [
              "It is found — HashMap uses hashCode and equals, not ==",
              "It is not found — 1000 is outside the Integer cache so the objects differ",
              "It is found only if you called intern() on the key",
              "It throws — Integer keys outside the cache are not permitted",
          ],
          "answer": 0,
          "why": "Option A is right and it is the important reassurance: HashMap "
                 "never uses ==, so the cache is irrelevant to map lookups. Option B "
                 "is the trap for someone who has just learned about the cache and "
                 "over-applies it — the cache only affects ==, nothing else. "
                 "Option C confuses String interning with Integer caching. Option D "
                 "is invented.",
      },
      pitfalls="`Long.equals(Integer)` is always false — equals checks the class "
               "first, so 127L does not equal 127. A `Map<Long,?>` looked up with an "
               "int literal silently misses every time, and this is one of the "
               "hardest bugs in this list to spot by reading.",
      followups="Why cache at all? Small integers dominate real programs (loop "
                "counters, flags, sizes), so caching them avoids enormous allocation "
                "churn. Why is the upper bound tunable? Because an application "
                "boxing a known small range benefits from a larger cache.",
      difficulty="Medium", frequency="Extremely common — the single most-asked Java trap",
      mnemonic="−128 to 127 is cached. Outside that, new objects. So never == a wrapper."),

    Q("traps",
      "The ternary operator can throw a NullPointerException on a line with no method call",
      "The `? :` operator has to decide on one type for its result. If one branch "
      "gives an object like Integer and the other gives a plain int, Java decides "
      "the whole thing is a plain int — and then, if the object branch is chosen "
      "and it happens to be null, Java has to convert null into a plain int, "
      "which is impossible. It throws, on a line where you can see no method being "
      "called and no obvious unboxing.",
      "Under JLS §15.25 the conditional operator computes a single result type "
      "from both branches. When one branch is a wrapper and the other a primitive, "
      "BINARY NUMERIC PROMOTION applies and the result type is the primitive — so "
      "the wrapper branch is unboxed even when it is the branch taken. A null "
      "wrapper therefore throws NullPointerException at the ternary itself. The "
      "same promotion silently widens types: a ternary mixing Integer and Double "
      "produces a Double, so a branch returning Integer 1 comes out as 1.0.",
      ["ternary", "autoboxing", "npe", "trap", "jls"],
      code="Integer maybeNull = null;\nboolean flag = true;\n\n// Looks safe. Is not.\n// Integer x = flag ? maybeNull : 0;    // throws NPE — the 0 forces int\n\n// Safe: BOTH branches are Integer, so no unboxing happens\nInteger y = flag ? maybeNull : Integer.valueOf(0);\nSystem.out.println(y);\n\n// Silent type promotion, no exception, wrong-looking output:\nObject z = true ? Integer.valueOf(1) : Double.valueOf(2.0);\nSystem.out.println(z);\n\n// And the same promotion in a Map.get:\njava.util.Map<String,Integer> m = new java.util.HashMap<>();\n// int v = m.containsKey(\"k\") ? m.get(\"k\") : 0;   // fine\n// int w = m.get(\"missing\") != null ? m.get(\"missing\") : 0;  // fine\nSystem.out.println(m.getOrDefault(\"missing\", 0));   // the clean way",
      output="null\n1.0\n0",
      gotcha="Q: `Integer x = flag ? maybeNull : 0;` with flag true and maybeNull "
             "null — does it assign null or throw?  IT THROWS. The `0` makes the "
             "result type `int`, so the chosen branch is unboxed on its way out and "
             "unboxing null is an NPE. Change the `0` to `Integer.valueOf(0)` and it "
             "assigns null happily. A ONE-CHARACTER DIFFERENCE CHANGES WHETHER THE "
             "LINE THROWS, and the stack trace points at a line containing no method "
             "call, which is why this one is genuinely hard to debug.",
      version="Behaviour is unchanged since autoboxing arrived in Java 5. Modern IDEs "
              "warn about it; javac does not.",
      quiz={
          "q": "`Object o = true ? Integer.valueOf(1) : Double.valueOf(2.0); "
               "System.out.println(o);`",
          "options": [
              "1.0 — both branches are promoted to double before the result is boxed",
              "1 — the true branch is taken, so the Integer is used unchanged",
              "It does not compile — the branches have incompatible types",
              "1 — but the static type is Number, so it prints via Integer.toString",
          ],
          "answer": 0,
          "why": "Option A is right: binary numeric promotion unifies Integer and "
                 "Double to double, so the taken branch is unboxed to 1, widened to "
                 "1.0, and re-boxed as a Double. Option B is what everyone expects "
                 "and it ignores that the ternary has ONE result type computed from "
                 "BOTH branches regardless of which is taken. Option C assumes the "
                 "compiler rejects mixed branches; it does not, it promotes. "
                 "Option D gets the reasoning half right and the output wrong.",
      },
      pitfalls="The safe habits: make both branches the same reference type, or use "
               "Optional / getOrDefault / Objects.requireNonNullElse instead of a "
               "ternary over a possibly-null wrapper.",
      followups="Where else does hidden unboxing throw? `map.get(k) > 0` when the key "
                "is absent; `list.remove(someInteger)` picks the INDEX overload if the "
                "argument is an int; and any arithmetic on a wrapper field that has "
                "not been initialised.",
      difficulty="Hard", frequency="Common at senior level — a favourite 'what does this print'",
      mnemonic="One ternary, one result type — computed from BOTH branches, even the untaken one."),

    Q("traps",
      "list.remove(1) — the overload that removes the wrong thing",
      "`List` has two remove methods: one takes a position and one takes the "
      "object to delete. If you write remove(1) with a plain number, Java picks "
      "the position version and deletes whatever is at index 1 — not the value 1. "
      "To delete the value you must hand it an Integer object. Two lines that "
      "look almost identical do completely different things.",
      "List<E> declares both `E remove(int index)` (from List) and `boolean "
      "remove(Object o)` (from Collection). Overload resolution happens at COMPILE "
      "TIME on static types, and Java prefers a match requiring no boxing over one "
      "requiring boxing — so remove(1) binds to remove(int) even on a "
      "List<Integer>. To remove by value you must pass a reference type: "
      "remove(Integer.valueOf(1)) or remove((Integer) 1).",
      ["collections", "overloading", "autoboxing", "trap"],
      code="import java.util.*;\n\nList<Integer> list = new ArrayList<>(List.of(10, 20, 30));\n\nlist.remove(1);                      // index 1 -> removes the value 20\nSystem.out.println(list);\n\nlist.add(1, 99);                     // add(index, element) — same shape\nSystem.out.println(list);\n\nList<Integer> other = new ArrayList<>(List.of(10, 20, 30));\nother.remove(Integer.valueOf(20));   // BY VALUE\nSystem.out.println(other);\n\nother.remove(Integer.valueOf(99));   // absent -> no exception, returns false\nSystem.out.println(other);",
      output="[10, 30]\n[10, 99, 30]\n[10, 30]\n[10, 30]",
      gotcha="Q: on a List<Integer>, does remove(1) remove the element 1 or index 1?  "
             "INDEX 1 — because overload resolution prefers the exact primitive match "
             "and never considers boxing when an unboxed candidate exists. THE "
             "GENERIC TYPE IS IRRELEVANT: erasure means the compiler sees "
             "remove(Object) and remove(int), and `1` is an int. The failure mode is "
             "the worst kind: no exception, plausible-looking output, wrong element "
             "gone.",
      version="Present since generics arrived in Java 5. Set and Map do not have this "
              "problem, because they have no index-based overload.",
      quiz={
          "q": "List<Integer> l = new ArrayList<>(List.of(5, 10, 15)); "
               "l.remove(2); System.out.println(l);",
          "options": [
              "[5, 10] — index 2 was removed",
              "[5, 10, 15] — the value 2 is absent, so nothing happens",
              "[5, 15] — the value 10 at index 1 is removed",
              "It does not compile — remove is ambiguous on a List<Integer>",
          ],
          "answer": 0,
          "why": "Option A is right: remove(int) wins, index 2 holds 15, and it goes. "
                 "Option B is what you get if you assume the generic type steers the "
                 "overload — the single most common wrong model here. Option C is a "
                 "guess at an off-by-one. Option D assumes ambiguity, but the "
                 "resolution rules are deterministic and prefer the primitive.",
      },
      pitfalls="The same shape appears in `add(int index, E element)` vs `add(E)`, "
               "and in any API that overloads an int position against an Object "
               "value. When you see both, pass an explicit wrapper.",
      followups="How would you design this API to avoid the trap? Distinct names — "
                "removeAt(int) and removeValue(E) — which is exactly what several "
                "later languages did after watching Java get this wrong.",
      difficulty="Medium", frequency="Very common — a staple 'what does this print'",
      mnemonic="remove(int) is a POSITION. remove(Object) is a VALUE. A bare 1 is a position."),

    # ══════════════════════════════════════════════════════════════════
    #  OOP
    # ══════════════════════════════════════════════════════════════════

    Q("oop",
      "equals and hashCode — the contract, and what breaks when you ignore it",
      "If you want two different objects to count as 'the same' — two Point "
      "objects both at (1,2), say — you write an equals method saying so. But "
      "HashMap and HashSet do not call equals first: they use hashCode to decide "
      "which bucket to look in, and only compare with equals inside that bucket. "
      "So if two equal objects return different hash codes they land in different "
      "buckets and never meet, and your map loses things. THE RULE: whenever you "
      "override equals, override hashCode too.",
      "The contract: (1) if a.equals(b) then a.hashCode() == b.hashCode(); "
      "(2) the reverse is NOT required — unequal objects may share a hash code "
      "(a collision), which is fine; (3) equals must be reflexive, symmetric, "
      "transitive, consistent, and false for null. Hash-based collections rely on "
      "(1) absolutely. THE OTHER HALF OF THE RULE: fields used in equals/hashCode "
      "should be effectively immutable, because mutating one after insertion "
      "changes the object's bucket and it becomes unreachable in a set that still "
      "contains it.",
      ["equals", "hashcode", "collections", "contract"],
      code="import java.util.*;\n\nfinal class Point {\n    private final int x, y;\n    Point(int x, int y) { this.x = x; this.y = y; }\n\n    @Override public boolean equals(Object o) {\n        if (this == o) return true;                  // cheap identity fast path\n        if (!(o instanceof Point)) return false;     // handles null too\n        Point p = (Point) o;\n        return x == p.x && y == p.y;\n    }\n    @Override public int hashCode() { return Objects.hash(x, y); }\n    @Override public String toString() { return \"(\" + x + \",\" + y + \")\"; }\n}\n\nSet<Point> set = new HashSet<>();\nset.add(new Point(1, 2));\nSystem.out.println(set.contains(new Point(1, 2)));\nSystem.out.println(set.size());\nset.add(new Point(1, 2));            // equal -> not added again\nSystem.out.println(set.size());",
      output="true\n1\n1\n\n(Delete the hashCode override and the first line prints false\n and the last prints 2 — the set silently holds duplicates.)",
      gotcha="Q: you override equals but not hashCode. What breaks?  NOT equals — "
             "a.equals(b) still returns true, and every direct test you write passes. "
             "What breaks is every HASH-BASED collection: contains returns false for "
             "an object the set demonstrably equals, and a HashSet accumulates "
             "duplicates. THE BUG IS INVISIBLE UNTIL THE OBJECT MEETS A HashMap, "
             "which is why it survives code review so often.",
      version="Objects.hash and Objects.equals arrived in Java 7. `record` (Java 16) "
              "generates a correct equals, hashCode and toString for you, and is the "
              "right answer for a value class in modern Java. Pattern matching for "
              "instanceof (Java 16) removes the cast: "
              "`if (!(o instanceof Point p)) return false;`",
      quiz={
          "q": "A class overrides hashCode but NOT equals. What is the consequence?",
          "options": [
              "Equal-looking objects are still distinct — equals defaults to ==, so a HashSet holds duplicates",
              "Nothing — hashCode alone is enough for HashSet to deduplicate",
              "It fails to compile — the two must be overridden together",
              "HashMap lookups throw, because the hash matches but equals does not",
          ],
          "answer": 0,
          "why": "Option A is right: they collide into the SAME bucket, then "
                 "Object.equals compares references and says no, so both are kept. "
                 "Option B is the mirror-image misconception to the usual one — "
                 "hashCode selects the bucket, equals decides membership, and you "
                 "need both. Option C is wrong; javac has no such rule, which is "
                 "exactly why this bug exists. Option D invents an exception — "
                 "nothing throws, it just answers wrongly.",
      },
      pitfalls="Using a MUTABLE field in hashCode and then mutating it after adding "
               "the object to a set — the object is now in the wrong bucket and "
               "set.contains(thatVeryObject) returns false. Using `getClass() != "
               "o.getClass()` versus `instanceof` changes behaviour for subclasses "
               "and breaks symmetry in one direction; pick deliberately.",
      followups="Why 31 in the classic hashCode? It is odd and prime, and 31*i "
                "compiles to (i << 5) - i, which used to matter. Any odd multiplier "
                "works; the primality is folklore more than requirement.",
      difficulty="Medium", frequency="Extremely common — near-guaranteed in any Java interview",
      mnemonic="hashCode picks the BUCKET. equals decides INSIDE it. Break one, lose both.",
      diagram=(
          "  HashSet.contains(new Point(1,2))                            \n"
          "                                                              \n"
          "   1. hashCode()  ->  which bucket?                           \n"
          "         |                                                    \n"
          "         v                                                    \n"
          "   +----+----+----+----+----+----+----+----+                   \n"
          "   | 0  | 1  | 2  | 3  | 4  | 5  | 6  | 7  |   buckets         \n"
          "   +----+----+----+----+----+----+----+----+                   \n"
          "               |                                              \n"
          "               v                                              \n"
          "   2. equals()  ->  is it actually in there?                   \n"
          "                                                              \n"
          "  WRONG hashCode -> WRONG BUCKET -> equals is NEVER CALLED     \n"
          "  and the object is 'not present' despite being equal.         "
      )),

    Q("oop",
      "Overriding vs overloading — and why static methods are not polymorphic",
      "OVERRIDING is a child class replacing a method its parent already has; "
      "which one runs is decided when the program runs, from the object's real "
      "type. OVERLOADING is two methods in the same class with the same name but "
      "different parameters; which one runs is decided by the COMPILER, from the "
      "declared types it can see. The two words look alike and the timing is the "
      "whole difference — and it is why a static method looks like it overrides "
      "and does not.",
      "OVERRIDING: same name, same parameter types, in a subclass. Dispatched "
      "DYNAMICALLY at runtime on the object's actual class (virtual dispatch, "
      "invokevirtual). OVERLOADING: same name, different parameter list, resolved "
      "STATICALLY at compile time from the declared types of the arguments. "
      "STATIC METHODS ARE NOT OVERRIDDEN, THEY ARE HIDDEN: a static method in a "
      "subclass with the same signature shadows the parent's, and which one runs "
      "depends on the REFERENCE type, not the object. Fields behave the same way "
      "— they are hidden, never overridden.",
      ["oop", "polymorphism", "overriding", "overloading", "dispatch"],
      code="class Animal {\n    String name() { return \"animal\"; }               // instance -> OVERRIDDEN\n    static String kind() { return \"Animal.kind\"; }   // static   -> HIDDEN\n    String label = \"animal-label\";                    // field    -> HIDDEN\n}\nclass Dog extends Animal {\n    @Override String name() { return \"dog\"; }\n    static String kind() { return \"Dog.kind\"; }\n    String label = \"dog-label\";\n}\n\nAnimal a = new Dog();          // declared Animal, actually a Dog\n\nSystem.out.println(a.name());   // instance method: RUNTIME type wins\nSystem.out.println(a.kind());   // static: COMPILE-TIME type wins\nSystem.out.println(a.label);    // field: COMPILE-TIME type wins\nSystem.out.println(((Dog) a).label);",
      output="dog\nAnimal.kind\nanimal-label\ndog-label",
      gotcha="Q: `Animal a = new Dog(); a.kind();` — which static runs?  "
             "Animal.kind, because static dispatch uses the DECLARED type. And "
             "`a.label` prints animal-label for the same reason. SO THE ONLY THING "
             "THAT ACTUALLY OBEYS THE OBJECT'S REAL TYPE IS AN INSTANCE METHOD. "
             "Calling a static through an instance reference is legal and misleading "
             "enough that most linters forbid it — write Animal.kind().",
      version="@Override has been available since Java 5 and is checked by javac; use "
              "it always, because it turns a silent 'you accidentally overloaded "
              "instead of overrode' into a compile error.",
      quiz={
          "q": "class P { void f(Object o){System.out.print(\"O\");} } "
               "class C extends P { void f(String s){System.out.print(\"S\");} } "
               "P p = new C(); p.f(\"hi\");",
          "options": [
              "O — f(String) is an OVERLOAD, and P has no such method, so f(Object) is chosen at compile time",
              "S — the object is a C, so its more specific method runs",
              "S — String is more specific than Object, so overload resolution prefers it",
              "It does not compile — C must override f(Object)",
          ],
          "answer": 0,
          "why": "Option A is right and it is the crux: f(String) does not OVERRIDE "
                 "f(Object), it OVERLOADS it — different parameter type. The "
                 "compiler resolves against the DECLARED type P, which only has "
                 "f(Object). Options B and C both assume runtime dispatch picks the "
                 "more specific method; overload selection happens at COMPILE time "
                 "and dynamic dispatch only chooses among genuine overrides. "
                 "Option D invents a rule — a subclass may add whatever methods it "
                 "likes.",
      },
      pitfalls="`public boolean equals(MyType other)` is an OVERLOAD of "
               "equals(Object), not an override — so collections keep calling "
               "Object.equals and your method is never invoked. @Override catches "
               "this instantly and is the reason to always write it.",
      followups="Can you override a private method? No — it is not visible, so a "
                "same-named method in the subclass is simply a new method. Can you "
                "widen the return type? Yes, COVARIANT returns are allowed since "
                "Java 5. Can you narrow the visibility? No — you may only widen it.",
      difficulty="Medium", frequency="Extremely common",
      mnemonic="OverRIDE = Runtime, real type. OverLOAD = Lexical, declared type."),

    # ══════════════════════════════════════════════════════════════════
    #  Collections
    # ══════════════════════════════════════════════════════════════════

    Q("collections",
      "ArrayList vs LinkedList — and why the textbook answer is usually wrong",
      "An ArrayList keeps everything in one continuous block, like a row of "
      "numbered lockers — jumping straight to number 500 is instant, but inserting "
      "in the middle means shifting everything after it. A LinkedList is a chain "
      "where each item holds the address of the next — inserting is just "
      "re-pointing two arrows, but reaching item 500 means walking from the start. "
      "The textbook says use LinkedList for lots of insertions. IN PRACTICE "
      "ARRAYLIST ALMOST ALWAYS WINS ANYWAY, and the reason is worth understanding.",
      "ArrayList: a backing Object[] with amortized O(1) append (doubling growth), "
      "O(1) random access, O(n) insert/remove in the middle. LinkedList: a doubly-"
      "linked list with O(1) insert/remove GIVEN A NODE REFERENCE, O(n) access, "
      "and O(n) to FIND the position — so add(i, x) is O(n) too. THE REASON "
      "ARRAYLIST WINS IN PRACTICE IS MEMORY LOCALITY: its elements are contiguous "
      "and prefetch into cache, while LinkedList nodes are scattered and each "
      "carries ~24 bytes of overhead plus two pointers, causing a cache miss per "
      "step. A shift of 1,000 contiguous elements is often faster than 1,000 "
      "pointer chases. USE ArrayList BY DEFAULT; use ArrayDeque, not LinkedList, "
      "when you need a queue or stack.",
      ["collections", "arraylist", "linkedlist", "performance", "cache"],
      code="import java.util.*;\n\nList<Integer> al = new ArrayList<>();\nList<Integer> ll = new LinkedList<>();\nfor (int i = 0; i < 5; i++) { al.add(i); ll.add(i); }\n\nSystem.out.println(al.get(3));      // O(1) index into an array\nSystem.out.println(ll.get(3));      // O(n) walk from an end\n\nal.add(2, 99);                      // shifts the tail right\nSystem.out.println(al);\n\n// The right tool for a queue or stack — NOT LinkedList, NOT Stack:\nDeque<Integer> stack = new ArrayDeque<>();\nstack.push(1); stack.push(2);\nSystem.out.println(stack.pop());\n\nDeque<Integer> queue = new ArrayDeque<>();\nqueue.offer(1); queue.offer(2);\nSystem.out.println(queue.poll());",
      output="3\n3\n[0, 1, 99, 2, 3, 4]\n2\n1",
      gotcha="Q: you need a stack. Use java.util.Stack?  NO. Stack extends Vector, "
             "so every operation is synchronized (a cost you are not using) and it "
             "iterates BOTTOM-TO-TOP, which is the opposite of stack order and has "
             "surprised people for twenty-five years. USE ArrayDeque. The Javadoc for "
             "Stack itself recommends Deque instead.",
      version="ArrayDeque arrived in Java 6. List.of / Set.of / Map.of (Java 9) "
              "return IMMUTABLE collections — `List.of(1,2).add(3)` throws "
              "UnsupportedOperationException, which surprises people migrating from "
              "Arrays.asList (which is fixed-size but allows set()).",
      quiz={
          "q": "You will append a million elements and then read them by index. Which?",
          "options": [
              "ArrayList, ideally pre-sized with new ArrayList<>(1_000_000)",
              "LinkedList — appending is O(1) and there is no resize copying",
              "Vector, because it is the thread-safe version of ArrayList",
              "Either — both are O(1) append and O(1) get, so it makes no difference",
          ],
          "answer": 0,
          "why": "Option A is right, and pre-sizing removes the ~20 resize copies "
                 "entirely. Option B is the textbook trap: LinkedList's append IS "
                 "O(1), and then every get(i) is O(n), which destroys the read phase "
                 "— plus it allocates a node object per element. Option C picks up "
                 "an unused lock on every call and is legacy. Option D is wrong on "
                 "the second half: LinkedList.get(i) is O(n), not O(1).",
      },
      complexity="ArrayList: get O(1), add-at-end amortized O(1), add/remove at i "
                 "O(n). LinkedList: get O(n), add-at-end O(1), add/remove at a KNOWN "
                 "NODE O(1) but add(i,x) O(n). Memory: ArrayList ~4-8 bytes per "
                 "reference plus slack; LinkedList ~40 bytes of node overhead per "
                 "element.",
      pitfalls="Iterating a LinkedList with `for (int i = 0; i < list.size(); i++) "
               "list.get(i)` is O(n²) — use the for-each loop, which uses an iterator "
               "and is O(n). Arrays.asList returns a FIXED-SIZE view backed by the "
               "array: set() works, add() throws.",
      followups="When does LinkedList genuinely win? When you hold an Iterator and "
                "call iterator.remove() repeatedly while traversing — that is O(1) "
                "per removal against ArrayList's O(n). It is a narrow case, and "
                "ArrayList's removeIf covers most of it in one pass.",
      difficulty="Medium", frequency="Extremely common — and the cache-locality answer stands out",
      mnemonic="ArrayList by default. ArrayDeque for queue/stack. LinkedList almost never."),

    Q("collections",
      "ConcurrentModificationException — why removing inside a for-each throws",
      "While you are walking through a collection with a for-each loop, the "
      "collection is not allowed to change underneath you. If you add or remove "
      "during the walk, Java notices on the next step and throws, rather than "
      "letting you carry on with a walker that no longer matches reality. The fix "
      "is to remove THROUGH the walker itself, or to use removeIf, which does the "
      "whole thing safely in one pass.",
      "ArrayList and friends keep a `modCount` incremented by every structural "
      "modification. The iterator records it at creation and compares on every "
      "next(), throwing ConcurrentModificationException on mismatch — this is "
      "FAIL-FAST behaviour. It is a BEST-EFFORT BUG DETECTOR, not a guarantee: "
      "the check is unsynchronised and can miss, and removing the SECOND-TO-LAST "
      "element famously does not throw at all, because hasNext() then returns "
      "false and next() is never called again. The correct fixes are "
      "Iterator.remove(), Collection.removeIf(predicate), collecting into a new "
      "list, or a concurrent collection.",
      ["collections", "iterator", "concurrentmodification", "fail-fast"],
      code="import java.util.*;\n\nList<String> l = new ArrayList<>(List.of(\"a\", \"b\", \"c\", \"d\"));\n\n// 1. THROWS on the next iteration after the removal\ntry {\n    for (String s : l) { if (s.equals(\"b\")) l.remove(s); }\n} catch (ConcurrentModificationException e) {\n    System.out.println(\"CME as expected\");\n}\n\n// 2. Correct: remove THROUGH the iterator\nList<String> m = new ArrayList<>(List.of(\"a\", \"b\", \"c\", \"d\"));\nfor (Iterator<String> it = m.iterator(); it.hasNext(); ) {\n    if (it.next().equals(\"b\")) it.remove();\n}\nSystem.out.println(m);\n\n// 3. Cleanest: removeIf (Java 8+)\nList<String> n = new ArrayList<>(List.of(\"a\", \"b\", \"c\", \"d\"));\nn.removeIf(s -> s.equals(\"b\"));\nSystem.out.println(n);\n\n// 4. THE ONE THAT DOES NOT THROW — and is still a bug\nList<String> p = new ArrayList<>(List.of(\"a\", \"b\", \"c\"));\nfor (String s : p) { if (s.equals(\"b\")) p.remove(s); }\nSystem.out.println(p);",
      output="CME as expected\n[a, c, d]\n[a, c, d]\n[a, c]",
      gotcha="Q: does removing during a for-each ALWAYS throw?  NO, and that is worse "
             "than if it did. Remove the SECOND-TO-LAST element and the size drops so "
             "that hasNext() returns false immediately — next() is never called, the "
             "modCount check never runs, and the loop exits silently having skipped "
             "the final element. Case 4 above prints [a, c] and never visits \"c\". "
             "A DETECTOR THAT USUALLY FIRES IS MORE DANGEROUS THAN ONE THAT NEVER "
             "DOES, because you learn to trust it.",
      version="removeIf arrived in Java 8 and is the right answer for almost every "
              "case. ConcurrentHashMap and CopyOnWriteArrayList are WEAKLY CONSISTENT "
              "instead of fail-fast — they never throw and may or may not reflect "
              "concurrent updates.",
      quiz={
          "q": "Which of these safely removes every element matching a predicate from "
               "an ArrayList?",
          "options": [
              "list.removeIf(pred) — one pass, no iterator management, no CME",
              "for (T t : list) if (pred.test(t)) list.remove(t);",
              "for (int i = 0; i < list.size(); i++) if (pred.test(list.get(i))) list.remove(i);",
              "list.stream().filter(pred).forEach(list::remove);",
          ],
          "answer": 0,
          "why": "Option A is right and it is also the fastest, because ArrayList's "
                 "removeIf compacts in a single pass rather than shifting per "
                 "removal. Option B is the CME case. Option C does not throw and "
                 "SKIPS ELEMENTS — after removing index i everything shifts left and "
                 "i++ steps over the next one; iterating BACKWARDS fixes it, which "
                 "is why that idiom exists. Option D mutates the source of a live "
                 "stream, which is explicitly undefined behaviour and typically "
                 "throws CME.",
      },
      pitfalls="The backwards loop `for (int i = list.size()-1; i >= 0; i--)` is the "
               "index-based idiom that works, because removals only shift elements "
               "you have already passed. Modifying a map while iterating its keySet "
               "has the same fail-fast behaviour.",
      followups="Why not just make collections thread-safe? Because fail-fast is "
                "about SINGLE-THREADED bugs too — the exception name is misleading, "
                "as the common cause is one thread modifying while iterating, not a "
                "race.",
      difficulty="Medium", frequency="Very common — and the 'does not always throw' half is the differentiator",
      mnemonic="Remove THROUGH the iterator, or use removeIf. Never remove from the collection you are in."),
]


# ─────────────────────────────────────────────────────────────────────
#  Derived quiz + recall, and a self-check
# ─────────────────────────────────────────────────────────────────────

def entries_by_category():
    """Entries grouped in TEACHING order, not alphabetical."""
    out = {}
    for key in CATEGORY_ORDER:
        rows = [e for e in ENTRIES if e["cat"] == key]
        if rows:
            out[key] = rows
    return out


def presented_quiz(entry):
    """A quiz with its options SHUFFLED, and the explanation relabelled to match.

    WHY THIS EXISTS. Every quiz in this file is authored with the correct
    option FIRST, because that is far easier to write and to review — you can
    see at a glance whether the distractors are really wrong. Presenting them
    in that order would teach one thing only: pick A.

    So the options are rotated by a per-entry amount derived from the title,
    which makes the position stable across sessions (she is not re-learning a
    shuffled layout every reload) and unpredictable across entries. The `why`
    text refers to options by LETTER, so those letters are remapped too —
    otherwise the explanation would point at the wrong option, which is worse
    than not explaining at all.
    """
    q = entry.get("quiz")
    if not q:
        return None
    opts = list(q["options"])
    n = len(opts)
    shift = sum(ord(c) for c in entry["title"]) % n
    # rotate: presented position p holds the authored option (p - shift) mod n
    order = [(p - shift) % n for p in range(n)]
    shown = [opts[j] for j in order]
    new_index = order.index(q["answer"])
    # authored letter -> presented letter
    remap = {chr(65 + j): chr(65 + p) for p, j in enumerate(order)}
    why = _relabel(q["why"], remap)
    return {"q": q["q"], "options": shown, "answer": new_index, "why": why}


def _relabel(text, remap):
    import re
    return re.sub(r"Option ([A-D])", lambda m: "Option " + remap[m.group(1)],
                  re.sub(r"Options ([A-D]) and ([A-D])",
                         lambda m: f"Options {remap[m.group(1)]} and {remap[m.group(2)]}",
                         text))


def quiz_items():
    """The hand-written multiple-choice questions, ready to present.

    Deliberately NOT generated. A distractor is only worth anything if
    someone who half-knows the topic would pick it, and that judgement
    cannot be sampled from other entries' titles.
    """
    items = []
    for i, e in enumerate(ENTRIES):
        q = presented_quiz(e)
        if not q:
            continue
        items.append({
            "id": f"jq{i}", "cat": e["cat"], "topic": e["title"],
            "question": q["q"], "options": q["options"],
            "answer": q["answer"], "why": q["why"],
            "difficulty": e.get("difficulty", ""),
        })
    return items


#: Recall prompts, in the order they should be attempted. Predict-the-output
#: comes FIRST for a language bank — it is the closest thing to the interview,
#: and it is the only prompt that cannot be answered by recognition.
_RECALL_FORMS = [
    ("output", "Read the code for this topic and predict EXACTLY what it prints, "
               "line by line, before you look.", "output"),
    ("plain", "Explain this topic to someone who has never written Java, using no "
              "jargon at all.", "plain"),
    ("code", "From a blank editor, write the snippet that demonstrates this.", "code"),
    ("gotcha", "What is the trap here, and why is the wrong answer the intuitive "
               "one?", "gotcha"),
    ("pitfalls", "Name the ways this goes wrong in real code.", "pitfalls"),
    ("version", "Which Java version introduced or changed this, and what did people "
                "do before?", "version"),
]

MAX_RECALL_ITEMS = 5


def recall_for(entry):
    """Retrieval-practice prompts DERIVED from the entry's own fields.

    Same principle as ai_sde_recall.py — nothing here invents prose, so a
    prompt can never drift from the topic — with one change: `output` leads,
    because for a language bank predicting the output is the question that
    most resembles the interview and least resembles re-reading.
    """
    items = []
    for kind, prompt, field in _RECALL_FORMS:
        value = (entry.get(field) or "").strip()
        if not value:
            continue
        items.append({"kind": kind, "prompt": prompt, "answer": value})
        if len(items) >= MAX_RECALL_ITEMS:
            break
    return items


def self_check():
    """Structural checks. Run as a script; also called from tests/.

    These are the invariants that make the format worth having — an entry
    that violates one is not merely untidy, it is unusable for the drill it
    was written for.
    """
    problems = []
    seen = set()
    for e in ENTRIES:
        t = e["title"]
        if t in seen:
            problems.append(f"duplicate title: {t!r}")
        seen.add(t)
        if e["cat"] not in CATEGORIES:
            problems.append(f"{t!r}: unknown category {e['cat']!r}")
        if e["code"] and not e["output"]:
            problems.append(f"{t!r}: code with no stated output")
        q = e.get("quiz")
        if q:
            if len(q["options"]) != 4:
                problems.append(f"{t!r}: quiz needs exactly 4 options")
            if not 0 <= q["answer"] < len(q["options"]):
                problems.append(f"{t!r}: quiz answer index out of range")
            if len(q.get("why", "")) < 120:
                problems.append(f"{t!r}: quiz 'why' must explain the WRONG options too")
            if re.search(r"Option \d", q.get("why", "")):
                problems.append(f"{t!r}: quiz 'why' must label options by LETTER, "
                                f"not by number (the renderer shows A-D)")
            letters = set(re.findall(r"Options? ([A-D])(?: and ([A-D]))?",
                                     q.get("why", "")))
            letters = {x for pair in letters for x in pair if x}
            if len(letters) < 3:
                problems.append(f"{t!r}: quiz 'why' names only {len(letters)} option(s) "
                                f"- it must say why the DISTRACTORS are wrong")
            if q["answer"] != 0:
                problems.append(f"{t!r}: author the correct option FIRST; the "
                                f"presenter shuffles it (see presented_quiz)")
        if e["examples"] and len(e["examples"]) != 10:
            problems.append(f"{t!r}: examples must be the full 10 sections, got "
                            f"{len(e['examples'])}")
        for i, sec in enumerate(e["examples"]):
            if not sec.lstrip().startswith(f"{i+1}."):
                problems.append(f"{t!r}: example section {i+1} is misnumbered")
    return problems


def stats():
    by_cat = {k: len(v) for k, v in entries_by_category().items()}
    return {
        "entries": len(ENTRIES),
        "categories": by_cat,
        "with_code": sum(1 for e in ENTRIES if e["code"]),
        "with_quiz": sum(1 for e in ENTRIES if e.get("quiz")),
        "with_gotcha": sum(1 for e in ENTRIES if e["gotcha"]),
        "with_deep_dive": sum(1 for e in ENTRIES if e["examples"]),
        "quiz_questions": len(quiz_items()),
    }


def render(entry, width=78, deep=False):
    """One entry as plain text, in the order it should be READ.

    plain -> answer -> code -> output -> gotcha -> version -> the rest.
    The plain-English paragraph is first because that is the order the
    entry was required to be written in, and reading it any other way
    lets you skip the part that proves you understood it.
    """
    rule = "═" * width
    thin = "─" * width
    out = [rule, entry["title"], rule]

    meta = [b for b in (entry.get("difficulty"), entry.get("frequency"),
                        CATEGORIES.get(entry["cat"], entry["cat"])) if b]
    if meta:
        out.append("  ·  ".join(meta))
        out.append("")

    def block(label, text, mono=False):
        if not (text or "").strip():
            return
        out.append(thin)
        out.append(label)
        out.append(thin)
        if mono:
            out.extend("    " + ln for ln in text.splitlines())
        else:
            out.append(_wrap(text, width))
        out.append("")

    block("IN PLAIN ENGLISH", entry["plain"])
    block("THE TECHNICAL ANSWER", entry["answer"])
    block("CODE", entry["code"], mono=True)
    block("OUTPUT  (derived from the JLS — not executed; see module docstring)",
          entry["output"], mono=True)
    block("THE TRAP", entry["gotcha"])
    block("VERSION NOTES", entry["version"])
    block("DIAGRAM", entry["diagram"], mono=True)
    block("COMPLEXITY / COST", entry["complexity"])
    block("PITFALLS", entry["pitfalls"])
    block("FOLLOW-UPS", entry["followups"])
    if entry.get("mnemonic"):
        block("REMEMBER IT AS", entry["mnemonic"])

    q = presented_quiz(entry)
    if q:
        out.append(thin)
        out.append("QUIZ  (hand-written distractors — each is a real misconception)")
        out.append(thin)
        out.append(_wrap(q["q"], width))
        out.append("")
        for i, opt in enumerate(q["options"]):
            out.append(_wrap(f"  {chr(65+i)}) {opt}", width, hang=5))
        out.append("")
        out.append(f"  ANSWER: {chr(65 + q['answer'])}")
        out.append(_wrap("  " + q["why"], width, hang=2))
        out.append("")

    items = recall_for(entry)
    if items:
        out.append(thin)
        out.append("RECALL DRILL  (attempt from a blank page, then reveal)")
        out.append(thin)
        for i, it in enumerate(items, 1):
            out.append(_wrap(f"  {i}. {it['prompt']}", width, hang=5))
        out.append("")

    if deep and entry["examples"]:
        out.append(rule)
        out.append(f"DEEP DIVE — {len(entry['examples'])} sections")
        out.append(rule)
        for sec in entry["examples"]:
            out.append(sec)
            out.append("")
    elif entry["examples"]:
        out.append(f"  [deep dive available: {len(entry['examples'])} sections "
                   f"— pass --deep to print]")
        out.append("")
    return "\n".join(out)


def _wrap(text, width, hang=0):
    import textwrap
    pad = " " * hang
    paras = []
    for para in text.split("\n"):
        if not para.strip():
            paras.append("")
            continue
        paras.append(textwrap.fill(para, width=width,
                                   subsequent_indent=pad))
    return "\n".join(paras)


def find(needle):
    needle = needle.lower()
    exact = [e for e in ENTRIES if e["title"].lower() == needle]
    if exact:
        return exact[0]
    part = [e for e in ENTRIES if needle in e["title"].lower()]
    return part[0] if part else None


if __name__ == "__main__":
    import sys
    if "--show" in sys.argv:
        i = sys.argv.index("--show")
        entry = find(sys.argv[i + 1]) if len(sys.argv) > i + 1 else ENTRIES[0]
        if entry is None:
            print("no entry matched"); sys.exit(1)
        print(render(entry, deep="--deep" in sys.argv))
        sys.exit(0)
    if "--list" in sys.argv:
        for key in CATEGORY_ORDER:
            rows = [e for e in ENTRIES if e["cat"] == key]
            if not rows:
                continue
            print(f"\n{CATEGORIES[key]}")
            for e in rows:
                marks = ("C" if e["code"] else " ") + ("Q" if e["quiz"] else " ") \
                        + ("T" if e["gotcha"] else " ") + ("D" if e["examples"] else " ")
                print(f"  [{marks}]  {e['title']}")
        sys.exit(0)
    bad = self_check()
    if bad:
        print("SELF-CHECK FAILED:")
        for b in bad:
            print("  -", b)
        sys.exit(1)
    s = stats()
    print(f"java_bank: {s['entries']} entries, self-check clean")
    for k, v in s["categories"].items():
        print(f"  {k:<12} {v:>3}  {CATEGORIES[k]}")
    print(f"  code {s['with_code']} | quiz {s['with_quiz']} | "
          f"gotcha {s['with_gotcha']} | deep-dive {s['with_deep_dive']}")
