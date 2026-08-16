"""Java bank — the "what does this print" genre.

A large share of a Java interview is a five-line snippet and one question. The
answer is rarely difficult once you know the rule; the difficulty is entirely
that the INTUITIVE answer is wrong and feels right. So every entry here is
built around a specific wrong answer somebody would confidently give.

None of these are obscure. All of them are documented, all are consequences of
rules that made sense when they were chosen, and all of them show up in real
code — which is why they are worth the space.

Same build(Q) contract as the other modules.
"""


def build(Q):
    return [

    Q("traps",
      "NaN, -0.0, and the three different meanings of 'equal' for a double",
      "Floating point has two values that break the ordinary rules. NaN — 'not "
      "a number', what you get from 0.0/0.0 — is NOT EQUAL TO ITSELF, so "
      "`x == x` is false for it. And there are two zeros, positive and "
      "negative, which `==` says are the same and which behave differently "
      "everywhere else. Java then gives you three ways to compare doubles — "
      "`==`, `.equals()` and `Double.compare()` — and they disagree with each "
      "other on exactly these two values.",
      "IEEE 754 defines NaN as unordered: every comparison with it is false, "
      "INCLUDING `NaN == NaN`. Java's `Double.equals` and `Double.compare` "
      "deliberately DIVERGE from `==` so that collections behave sensibly: "
      "equals treats NaN as equal to itself (otherwise a HashSet could never "
      "find a NaN it contains) and treats +0.0 and -0.0 as DIFFERENT (otherwise "
      "the equals/compareTo contract would break). compare orders "
      "-0.0 < 0.0 and puts NaN above everything. So: `==` follows IEEE 754, "
      "while equals and compare follow the COLLECTIONS contract, and the two "
      "goals are irreconcilable on precisely these values.",
      ["floating-point", "nan", "equals", "trap"],
      code="double nan = 0.0 / 0.0;\n\nSystem.out.println(nan == nan);                                 // IEEE 754\nSystem.out.println(Double.valueOf(nan).equals(Double.valueOf(nan)));\nSystem.out.println(Double.compare(nan, nan));\n\nSystem.out.println(0.0 == -0.0);                                // IEEE 754\nSystem.out.println(Double.valueOf(0.0).equals(Double.valueOf(-0.0)));\nSystem.out.println(Double.compare(0.0, -0.0));\n\n// Why the divergence exists — collections would be broken otherwise:\nimport java.util.*;\nSet<Double> s = new HashSet<>();\ns.add(Double.NaN);\nSystem.out.println(s.contains(Double.NaN));\n\n// The practical detection idiom, because x != x reads as nonsense:\nSystem.out.println(Double.isNaN(nan));",
      output="false\ntrue\n0\ntrue\nfalse\n1\ntrue\ntrue",
      gotcha="Q: `nan == nan` is false but `Double.valueOf(nan).equals(...)` is TRUE — "
             "which one is broken?  NEITHER. `==` obeys IEEE 754, where NaN is "
             "unordered and every comparison against it is false. equals obeys the "
             "COLLECTIONS contract, and it has to disagree: if equals returned false "
             "for NaN, a HashSet could contain a NaN it could never find again. THE TWO "
             "RULES CANNOT BOTH BE SATISFIED, so Java satisfies each in its own "
             "context. And the same conflict runs the other way for zero — `==` says "
             "0.0 and -0.0 are the same, equals says they are not.",
      version="Unchanged since Java 1.0; it is IEEE 754 behaviour, not a Java choice. "
              "`strictfp` became the default and the keyword a no-op in Java 17.",
      quiz={
          "q": "`double d = 0.0/0.0; System.out.println(d == d);`",
          "options": [
              "false — NaN is unordered, so every comparison against it is false",
              "true — any value equals itself",
              "It throws ArithmeticException on the division",
              "It prints NaN",
          ],
          "answer": 0,
          "why": "Option A is right and it is the one rule to carry away: NaN is not "
                 "equal to anything, including itself. Option B is the reflex, and it "
                 "is the reason `x != x` is the classic (if unreadable) NaN test. "
                 "Option C confuses floating-point division with INTEGER division — "
                 "`0/0` on ints throws, `0.0/0.0` on doubles quietly yields NaN, which "
                 "is itself worth knowing. Option D answers a different question; the "
                 "expression is a boolean comparison, not the value.",
      },
      pitfalls="`Math.min(0.0, -0.0)` returns -0.0 and `Math.max` returns 0.0, but "
               "`0.0 > -0.0` is false — so a hand-rolled min/max using `>` gives a "
               "different answer from Math's. And a comparator written as "
               "`(a,b) -> a < b ? -1 : a > b ? 1 : 0` returns 0 for NaN pairs and "
               "violates the comparator contract, which TimSort will eventually "
               "detect and throw over.",
      followups="Where does -0.0 actually come from? Any negative value that underflows "
                "to zero, and `-1.0 * 0.0`. It matters in `1/x`: `1/0.0` is +Infinity "
                "and `1/-0.0` is -Infinity, so the sign of a zero can flip the sign of "
                "a downstream result.",
      difficulty="Hard", frequency="Common — a favourite for senior candidates",
      mnemonic="== is IEEE. equals and compare are for COLLECTIONS. They disagree on NaN and -0.0."),

    Q("traps",
      "replace vs replaceAll — one takes a regex and one does not",
      "Two methods on String that look like the same thing with different "
      "scope. They are not: `replace` treats its argument as literal text, and "
      "`replaceAll` treats it as a REGULAR EXPRESSION. Both replace every "
      "occurrence, so the name suggests the difference is 'one vs all' and the "
      "actual difference is 'literal vs pattern'. A dot means 'any character' "
      "to one of them and 'a dot' to the other.",
      "`replace(CharSequence, CharSequence)` is literal. "
      "`replaceAll(String regex, String replacement)` compiles the first "
      "argument as a Pattern AND treats the replacement specially — `$1` is a "
      "group reference and `\\` is an escape, so a replacement containing either "
      "must go through Matcher.quoteReplacement. `replaceFirst` is the same with "
      "a limit of one. THE NAMES ARE THE PROBLEM: both replace every match, and "
      "the 'All' refers to nothing that distinguishes them. `split` is regex "
      "too, which is why splitting on '|' or '.' or '+' does not do what people "
      "expect.",
      ["string", "regex", "replace", "trap"],
      code="String s = \"a.b.c\";\n\nSystem.out.println(s.replace(\".\", \"-\"));       // LITERAL dot\nSystem.out.println(s.replaceAll(\".\", \"-\"));    // REGEX: . means any char\nSystem.out.println(s.replaceAll(\"\\\\.\", \"-\"));  // escaped: a literal dot\n\n// split is regex too:\nSystem.out.println(java.util.Arrays.toString(\"a.b.c\".split(\"\\\\.\")));\n\n// And a regex metacharacter that is not even valid on its own:\ntry {\n    \"1+2\".split(\"+\");\n} catch (java.util.regex.PatternSyntaxException e) {\n    System.out.println(\"PatternSyntaxException: \" + e.getDescription());\n}\n\n// The replacement string is special too — $ and \\ are not literal:\ntry {\n    System.out.println(\"cost\".replaceAll(\"cost\", \"$5\"));\n} catch (Exception e) {\n    System.out.println(e.getClass().getSimpleName());\n}",
      output="a-b-c\n-----\na-b-c\n[a, b, c]\nPatternSyntaxException: Dangling meta character '+'\nIndexOutOfBoundsException",
      gotcha="Q: `\"a.b.c\".replaceAll(\".\", \"-\")` — what prints?  FIVE DASHES, not "
             "`a-b-c`. In a regex `.` means ANY CHARACTER, so every one of the five "
             "characters is replaced. `replace` would give `a-b-c` because it is "
             "literal. AND THE REPLACEMENT SIDE IS SPECIAL TOO: replacing with `$5` "
             "throws IndexOutOfBoundsException, because `$5` is a reference to capture "
             "group 5 which does not exist — a bug that only appears when a user types "
             "a currency amount into your search-and-replace.",
      version="replace(CharSequence,CharSequence) arrived in Java 5; before that "
              "`replace` only took chars, which is why the confusing pair exists at "
              "all. Matcher.quoteReplacement and Pattern.quote are the escape hatches.",
      quiz={
          "q": "`\"1.2.3\".split(\".\")` returns an array of what length?",
          "options": [
              "0 — '.' is a regex meaning any character, so every character is a delimiter and all the pieces are empty and trailing-trimmed away",
              "3 — it splits on the dots, like split(\"\\\\.\")",
              "5 — one element per character",
              "1 — the string does not contain a literal dot delimiter",
          ],
          "answer": 0,
          "why": "Option A is right and it is the most confusing result in the family: "
                 "every character matches, producing only empty strings, and split's "
                 "default limit of 0 removes trailing empties — all of them — leaving "
                 "an EMPTY array. Option B is what everyone expects and needs "
                 "split(\"\\\\.\"). Option C would be the answer if the empties were "
                 "kept, i.e. with an explicit negative limit. Option D assumes a "
                 "literal match like replace's.",
      },
      pitfalls="`split(\"|\")` splits on every character, because `|` is regex "
               "alternation with two empty branches. `split(\"$\")`, `split(\"^\")` and "
               "`split(\"*\")` are all surprises or errors. WHEN THE DELIMITER COMES "
               "FROM DATA rather than a literal, wrap it: `split(Pattern.quote(d))`.",
      followups="When should you use replaceAll at all? When you genuinely want a "
                "pattern. For a literal swap, `replace` is both correct and faster — it "
                "skips regex compilation entirely, which matters in a loop.",
      difficulty="Medium", frequency="Very common — and a real production bug, not just an interview one",
      mnemonic="replace = literal. replaceAll and split = REGEX. The 'All' is a lie."),

    Q("traps",
      "split() silently drops trailing empty strings",
      "Splitting `\"a,b,,\"` on a comma gives you TWO elements, not four. Java "
      "throws away empty pieces at the END of the result — but keeps them at the "
      "start and in the middle. So a CSV line ending in blank fields loses them, "
      "and the row you parse has fewer columns than the header, on exactly the "
      "rows where the last few values happened to be empty.",
      "`split(regex)` is `split(regex, 0)`, and a limit of ZERO means 'apply the "
      "pattern as many times as possible AND DISCARD TRAILING EMPTY STRINGS'. A "
      "NEGATIVE limit applies the pattern as many times as possible and KEEPS "
      "them. A positive limit applies the pattern at most limit-1 times. Leading "
      "and interior empties are always kept — only the tail is trimmed. And "
      "`\"\".split(\",\")` returns an array of length ONE containing the empty "
      "string, not an empty array, because no match occurred at all.",
      ["string", "split", "csv", "trap"],
      code="System.out.println(\"a,b,,\".split(\",\").length);       // trailing dropped\nSystem.out.println(\"a,b,,\".split(\",\", -1).length);   // kept\nSystem.out.println(\",a,b\".split(\",\").length);        // LEADING is kept\nSystem.out.println(\"a,,b\".split(\",\").length);        // INTERIOR is kept\nSystem.out.println(\"\".split(\",\").length);            // not zero!\nSystem.out.println(\",,,\".split(\",\").length);         // all trailing\n\nSystem.out.println(java.util.Arrays.toString(\",a,b,,\".split(\",\")));\nSystem.out.println(java.util.Arrays.toString(\",a,b,,\".split(\",\", -1)));",
      output="2\n4\n3\n3\n1\n0\n[, a, b]\n[, a, b, , ]",
      gotcha="Q: `\"a,b,,\".split(\",\").length` — 4 or 2?  TWO. The default limit of 0 "
             "discards TRAILING empty strings, and it discards ALL of them, so "
             "`\",,,\"` splits to an array of length ZERO. But leading and interior "
             "empties survive: `\",a,b\"` gives 3. THE ASYMMETRY IS THE TRAP — the same "
             "empty string is kept or dropped depending on where it sits — and it "
             "surfaces as a CSV parser whose column count varies by row.",
      version="Java 8 changed one related detail: a zero-width match at the START of "
              "the input no longer produces a leading empty string, so "
              "`\"abc\".split(\"\")` gives 3 elements on Java 8+ and 4 on Java 7. Code "
              "that split on the empty string changed behaviour across that upgrade.",
      quiz={
          "q": "You are parsing CSV rows with `line.split(\",\")`. Which rows break?",
          "options": [
              "Rows whose LAST fields are empty — those columns vanish and the row is short",
              "Rows whose FIRST field is empty — leading empties are dropped",
              "Rows containing any empty field anywhere",
              "None — split preserves every field; only quoting is a problem",
          ],
          "answer": 0,
          "why": "Option A is right, and it is nasty because it is data-dependent: most "
                 "rows parse fine and only the ones ending in blanks come out short. "
                 "Option B has the asymmetry backwards — leading empties are KEPT. "
                 "Option C over-generalises; interior empties are kept too. Option D is "
                 "the assumption that lets this ship — quoting IS also a problem, and "
                 "it is a separate one.",
      },
      pitfalls="`\"\".split(\",\")` returns `[\"\"]` of length 1, so a loop over the "
               "result of splitting an empty line processes one empty field rather than "
               "none. USE A REAL CSV LIBRARY for real CSV — split cannot handle quoted "
               "fields containing the delimiter, and no limit argument fixes that.",
      followups="What does a positive limit do? `split(\",\", 2)` splits at most once, "
                "giving 'first field' and 'everything else' — which is genuinely useful "
                "for parsing `key=value` where the value may contain an equals sign.",
      difficulty="Medium", frequency="Very common — and a real data bug",
      mnemonic="Trailing empties are dropped. Leading and interior are kept. Use -1 to keep them all."),

    Q("traps",
      "Array covariance — the assignment that compiles and throws",
      "In Java, a `String[]` is allowed where an `Object[]` is expected. That "
      "sounds harmless and it means the compiler will let you put an Integer "
      "into an array that is really an array of Strings. It cannot catch it, so "
      "the JVM checks at runtime instead and throws. Generics deliberately do "
      "NOT work this way, which is why `List<String>` is not a `List<Object>` — "
      "the restriction people find annoying exists precisely because arrays "
      "showed what happens without it.",
      "Java arrays are COVARIANT: if S is a subtype of T then S[] is a subtype "
      "of T[]. That is unsound for writing, so every array store carries a "
      "RUNTIME type check and a bad one throws ArrayStoreException. Generics "
      "are INVARIANT — List<String> is unrelated to List<Object> — which is "
      "sound at compile time and needs no runtime check, and is possible only "
      "because erasure means there is nothing to check anyway. Wildcards "
      "recover the flexibility safely: `List<? extends T>` may be READ from and "
      "not written to; `List<? super T>` may be written to and not usefully "
      "read. PECS: Producer Extends, Consumer Super.",
      ["arrays", "generics", "variance", "trap"],
      code="// Legal. Arrays are covariant.\nObject[] objs = new String[2];\nobjs[0] = \"fine\";\ntry {\n    objs[1] = 42;               // compiles — throws at RUNTIME\n} catch (ArrayStoreException e) {\n    System.out.println(\"ArrayStoreException: \" + e.getMessage());\n}\n\n// The generic equivalent does NOT compile — the error moves to compile time:\n// List<Object> l = new ArrayList<String>();   // incompatible types\n\n// Wildcards recover the flexibility, safely. PECS:\nimport java.util.*;\nstatic double sum(List<? extends Number> src) {    // PRODUCER — read only\n    double t = 0;\n    for (Number n : src) t += n.doubleValue();\n    // src.add(1);            // correctly rejected: the list might be List<Double>\n    return t;\n}\nstatic void fill(List<? super Integer> dst) {      // CONSUMER — write only\n    dst.add(1);\n    // Integer i = dst.get(0);   // rejected: it might be a List<Object>\n}\n\nSystem.out.println(sum(List.of(1, 2.5, 3L)));\nList<Number> nums = new ArrayList<>();\nfill(nums);\nSystem.out.println(nums);",
      output="ArrayStoreException: java.lang.Integer\n6.5\n[1]",
      gotcha="Q: `Object[] o = new String[1]; o[0] = 42;` — compile error or runtime "
             "error?  RUNTIME. Array covariance makes the assignment type-check, so "
             "javac is satisfied and the JVM catches it with an ArrayStoreException on "
             "the store. THAT COST — a type check on EVERY array write, forever, in "
             "every Java program — is what generics were designed to avoid, and it is "
             "the real answer to 'why can't I assign a List<String> to a "
             "List<Object>?'. The annoyance is the fix.",
      version="Arrays have been covariant since Java 1.0, chosen before generics "
              "existed so that a method like Arrays.sort(Object[]) could be written at "
              "all. Generics (5) made the other choice with the benefit of hindsight.",
      quiz={
          "q": "Why are generics INVARIANT when arrays are covariant?",
          "options": [
              "Covariance is unsound for writing; arrays pay for it with a runtime check on every store, and generics avoid the cost by rejecting it at compile time",
              "Because erasure makes a runtime check impossible, so the compiler must be conservative",
              "Because generics came later and the designers preferred stricter typing on principle",
              "They are not — List<String> IS assignable to List<Object> since Java 8",
          ],
          "answer": 0,
          "why": "Option A is the actual reasoning, and the array case is the evidence "
                 "for it. Option B is a real fact used as the wrong explanation — "
                 "erasure does prevent a runtime check, which is why invariance is "
                 "NECESSARY rather than merely preferable, but the motivation is "
                 "soundness, not the mechanism. Option C reduces a specific technical "
                 "argument to taste. Option D is simply false, and is what someone "
                 "half-remembering wildcards would say.",
      },
      pitfalls="A generic array is doubly awkward: `new T[10]` is illegal and "
               "`(T[]) new Object[10]` compiles with an unchecked warning and can throw "
               "ClassCastException later, at a cast the compiler inserted somewhere "
               "else. Prefer an ArrayList.",
      followups="Which way round is PECS? A `List<? extends T>` PRODUCES T values for "
                "you to read and cannot be added to; a `List<? super T>` CONSUMES the T "
                "values you write and cannot be usefully read. Collections.copy(dest, "
                "src) is the canonical signature with both.",
      difficulty="Hard", frequency="Common at senior level",
      mnemonic="Arrays lie at compile time and check at runtime. Generics refuse up front."),

    Q("traps",
      "char arithmetic, and the cast that compound assignment hides",
      "A `char` is a number. Add 1 to `'a'` and Java quietly promotes both to "
      "`int`, so the result is 98 rather than the letter b — and printing it "
      "shows a number. But writing `c += 1` on a char compiles perfectly and "
      "gives you `b`, because compound assignment inserts a cast back to char "
      "that plain assignment does not. That hidden cast is convenient and it "
      "also silently truncates, which is where the real bug is.",
      "BINARY NUMERIC PROMOTION: byte, short and char are promoted to int "
      "before any arithmetic, so `'a' + 1` has type int. Assigning that back "
      "requires an explicit cast — `c = c + 1` is a compile error. COMPOUND "
      "ASSIGNMENT (`+=`, `-=`, `*=`…) is defined by JLS 15.26.2 to include an "
      "IMPLICIT CAST to the left-hand type, so `c += 1` compiles and so does "
      "`byte b = 10; b += 300;` — which silently truncates rather than "
      "overflowing. And `+` with a String on either side is CONCATENATION, so "
      "`\"\" + 'a' + 'b'` is \"ab\" while `'a' + 'b'` is 195.",
      ["char", "arithmetic", "promotion", "trap"],
      code="System.out.println('a' + 1);            // int arithmetic\nSystem.out.println((char) ('a' + 1));    // cast back to see the letter\nSystem.out.println('a' + 'b');           // 97 + 98\nSystem.out.println(\"\" + 'a' + 'b');      // String on the left -> concat\n\nchar c = 'a';\nc += 1;                                  // legal: implicit cast to char\nSystem.out.println(c);\n// c = c + 1;                            // COMPILE ERROR: int -> char\n\nbyte b = 10;\nb += 300;                                // legal, and it TRUNCATES\nSystem.out.println(b);\n\n// The idiom that depends on all of this:\nfor (char ch = 'a'; ch <= 'e'; ch++) System.out.print(ch);\nSystem.out.println();\nSystem.out.println('9' - '0');            // the digit-to-int trick",
      output="98\nb\n195\nab\nb\n54\nabcde\n9",
      gotcha="Q: `byte b = 10; b += 300;` — compile error, exception, or a value?  A "
             "VALUE, AND THE WRONG ONE: 54. Compound assignment inserts an implicit "
             "narrowing cast, so `b += 300` means `b = (byte)(b + 300)` — the addition "
             "happens in int, giving 310, and the cast keeps only the low byte. Writing "
             "`b = b + 300` instead is a COMPILE ERROR, which is strictly better "
             "behaviour. THE SHORTER FORM IS THE DANGEROUS ONE, which is the opposite "
             "of how these things usually go.",
      version="Unchanged since Java 1.0. `char` being 16-bit UTF-16 means a char cannot "
              "hold every Unicode code point — anything above U+FFFF needs a surrogate "
              "PAIR, which is why String.length() counts UTF-16 units and "
              "codePointCount exists.",
      quiz={
          "q": "`System.out.println('a' + 'b');`",
          "options": [
              "195 — both chars are promoted to int and added",
              "ab — the + operator concatenates characters",
              "It does not compile — chars cannot be added",
              "c — 'a' plus 'b' as an offset from the start of the alphabet",
          ],
          "answer": 0,
          "why": "Option A is right: 97 + 98, printed via println(int). Option B is the "
                 "intuition from `\"\" + 'a' + 'b'`, which DOES give \"ab\" — the "
                 "difference is whether a String is involved, and that one detail flips "
                 "the meaning of the same operator. Option C assumes chars are not "
                 "numeric; they are. Option D invents alphabet arithmetic.",
      },
      pitfalls="`char` is UNSIGNED 16-bit, so `(char) -1` is 65535 and a char can never "
               "be negative — which breaks the common `int idx = str.indexOf(c)` style "
               "loops that expect a -1 sentinel to fit. And iterating a String by char "
               "breaks emoji and other supplementary characters, which occupy two chars "
               "each.",
      followups="Why does `'9' - '0'` give 9? Because the ASCII/Unicode digits are "
                "consecutive, so subtracting the code point of '0' converts a digit "
                "character to its value. It is the standard idiom and it silently "
                "produces nonsense for non-ASCII digit characters, of which Unicode has "
                "many.",
      difficulty="Medium", frequency="Very common",
      mnemonic="char + int = int. `+=` hides a cast that plain `=` refuses."),

    Q("traps",
      "i = i++ — evaluation order, and why the increment vanishes",
      "`i = i++` leaves i unchanged. Not incremented, not doubled — exactly "
      "where it started. The reason is the order Java does things: it takes a "
      "copy of i's current value to be the result of the expression, THEN "
      "increments i, THEN assigns the saved copy back over the top. The "
      "increment happened and was immediately overwritten.",
      "Java's evaluation order is fully specified — unlike C, where this is "
      "undefined behaviour and different compilers genuinely differ. For "
      "`i = i++`: the right-hand side is evaluated first, `i++` yields the OLD "
      "value and stores the incremented one in i, and then the assignment writes "
      "the yielded old value back into i. Net effect: nothing. `i = ++i` yields "
      "the NEW value, so it works. Operands are evaluated STRICTLY LEFT TO "
      "RIGHT, which makes even `k = k++ + ++k` deterministic and identical on "
      "every conforming JVM.",
      ["operators", "evaluation-order", "increment", "trap"],
      code="int i = 0;\ni = i++;\nSystem.out.println(i);         // the increment is overwritten\n\nint j = 0;\nj = ++j;\nSystem.out.println(j);         // pre-increment yields the NEW value\n\nint k = 0;\nk = k++ + ++k;                 // left to right: 0 + 2\nSystem.out.println(k);\n\n// Left-to-right evaluation, made visible:\nint n = 1;\nSystem.out.println(n + \" \" + n++ + \" \" + n);\n\n// The same reasoning in an array index — a real bug, not a puzzle:\nint[] a = new int[3];\nint idx = 0;\na[idx++] = idx;                // the INDEX is taken before idx changes\nSystem.out.println(java.util.Arrays.toString(a));",
      output="0\n1\n2\n1 1 2\n[1, 0, 0]",
      gotcha="Q: `int i = 0; i = i++;` — what is i?  ZERO. The `i++` evaluates to the "
             "OLD value (0) while storing 1 into i, and then the assignment writes that "
             "saved 0 straight back over it. The increment genuinely happened and was "
             "then destroyed by the assignment. AND UNLIKE C, THIS IS FULLY DEFINED IN "
             "JAVA — the JLS fixes evaluation order, so every JVM gives 0, whereas the "
             "equivalent C program is undefined behaviour and compilers disagree.",
      version="Specified since Java 1.0 and never changed. It is one of the few places "
              "Java deliberately tightened something C left loose, precisely so "
              "programs behave identically everywhere.",
      quiz={
          "q": "`int k = 0; k = k++ + ++k; System.out.println(k);`",
          "options": [
              "2 — left to right: k++ yields 0 leaving k=1, then ++k makes k=2 and yields 2, so 0+2",
              "1 — the two increments cancel with the assignment",
              "3 — k++ yields 0 and ++k yields 2, but k is already 2 before the add",
              "Undefined — the order of evaluation is unspecified",
          ],
          "answer": 0,
          "why": "Option A traces it correctly, and the tracing is the whole skill: "
                 "operands are evaluated strictly left to right. Option B guesses at "
                 "cancellation. Option C double-counts by adding the final value of k "
                 "to the sum rather than the operand values. Option D is TRUE OF C AND "
                 "FALSE OF JAVA — the JLS pins the order down, which is why this "
                 "question has an answer at all.",
      },
      pitfalls="`a[i++] = i;` and `a[i] = i++;` do different things, and both are legal. "
               "Any expression using a variable more than once where one use has a side "
               "effect is a puzzle rather than code — split it into two statements.",
      followups="Would a compiler warn? Most static analysers flag a self-assigning "
                "increment; javac does not. And in C or C++ this same line is UNDEFINED "
                "BEHAVIOUR — the compiler may do anything at all — which is the "
                "difference between 'surprising' and 'unpredictable'.",
      difficulty="Medium", frequency="Very common — the classic puzzle question",
      mnemonic="i++ yields the OLD value. The assignment writes it back and eats the increment."),

    Q("traps",
      "Integer division and % with negatives — Java truncates toward zero",
      "`-7 / 2` is `-3`, not `-4`. And `-7 % 2` is `-1`, not `1`. Java's "
      "division throws away the fractional part by moving TOWARD ZERO rather "
      "than downward, and the remainder takes the sign of the LEFT operand. "
      "That means `%` is not the modulo of mathematics, and using it to wrap an "
      "index around an array produces a negative index the moment the input goes "
      "negative.",
      "Integer division truncates toward zero, so `-7/2 == -3` while "
      "`Math.floorDiv(-7,2) == -4`. The `%` operator is a REMAINDER, defined so "
      "that `(a/b)*b + a%b == a`, which forces its sign to follow the DIVIDEND: "
      "`-7 % 2 == -1` and `7 % -2 == 1`. Mathematical modulo always returns a "
      "value with the sign of the divisor, and that is `Math.floorMod`. USE "
      "floorMod FOR WRAPPING — array indices, circular buffers, hash bucketing "
      "— and `%` only when you genuinely want a remainder.",
      ["arithmetic", "modulo", "division", "trap"],
      code="System.out.println(-7 / 2);                 // truncates TOWARD ZERO\nSystem.out.println(-7 % 2);                 // sign follows the DIVIDEND\nSystem.out.println(7 % -2);                 // still positive\n\nSystem.out.println(Math.floorDiv(-7, 2));   // rounds DOWN\nSystem.out.println(Math.floorMod(-7, 2));   // sign follows the DIVISOR\n\n// Why it matters — wrapping an index:\nint[] ring = {10, 20, 30};\nint i = -1;\n// System.out.println(ring[i % ring.length]);        // -1 -> ArrayIndexOOB\nSystem.out.println(ring[Math.floorMod(i, ring.length)]);\n\n// And the hash-bucket version of the same bug.\n// NOTE 7, not 8: MIN_VALUE is divisible by 8, so a power-of-two bucket\n// count HIDES the bug entirely. It only appears on some divisors.\nint h = Integer.MIN_VALUE;\nSystem.out.println(Math.abs(h) % 7);         // NEGATIVE — abs cannot help\nSystem.out.println(Math.floorMod(h, 7));    // correct\nSystem.out.println((h & 0x7fffffff) % 7);   // also correct, different value",
      output="-3\n-1\n1\n-4\n1\n30\n-2\n5\n0",
      gotcha="Q: `Math.abs(hashCode()) % buckets` — what is wrong with it?  IT CAN "
             "RETURN A NEGATIVE BUCKET. If hashCode() happens to be Integer.MIN_VALUE, "
             "`Math.abs` returns MIN_VALUE unchanged — the positive counterpart does "
             "not exist in an int — and `%` then keeps that negative sign. It is the "
             "integer-overflow asymmetry and the remainder-sign rule combining into one "
             "line that is correct for 4,294,967,295 of the 4,294,967,296 possible hash "
             "values. USE Math.floorMod OR MASK THE SIGN BIT.\n\nAND THE REASON THIS "
             "SURVIVES CODE REVIEW: with a POWER-OF-TWO bucket count the bug does not "
             "appear at all, because MIN_VALUE is divisible by every power of two. "
             "`abs(MIN_VALUE) % 8` is a perfectly innocent 0. Change the bucket count "
             "to 7 and the same line returns -2. A bug that depends on a CONFIGURATION "
             "VALUE being non-power-of-two is not one you will find by testing.",
      version="Math.floorDiv and Math.floorMod arrived in Java 8. Before that everyone "
              "wrote `((x % n) + n) % n`, which is correct and is why that idiom is all "
              "over older code.",
      quiz={
          "q": "`System.out.println(-7 % 2);`",
          "options": [
              "-1 — the remainder takes the sign of the dividend",
              "1 — modulo always returns a non-negative result",
              "-3 — % is integer division for negative operands",
              "It throws, since a negative modulus is undefined",
          ],
          "answer": 0,
          "why": "Option A is right and it follows from `(a/b)*b + a%b == a`, which is "
                 "the identity Java's operator is defined to preserve. Option B "
                 "describes MATHEMATICAL modulo — which is Math.floorMod, not `%` — and "
                 "is the assumption behind most index-wrapping bugs. Option C confuses "
                 "the operator with `/`. Option D invents an error; the only "
                 "ArithmeticException here is division by zero.",
      },
      pitfalls="`Integer.MIN_VALUE / -1` OVERFLOWS to Integer.MIN_VALUE and is the only "
               "division that can — while `Integer.MIN_VALUE % -1` is correctly 0. And "
               "`%` on doubles keeps the dividend's sign too, so `-7.5 % 2` is -1.5.",
      example="Note that the two CORRECT forms disagree: floorMod(MIN_VALUE, 7) is 5 "
              "and (MIN_VALUE & 0x7fffffff) % 7 is 0. Both are valid bucket indices and "
              "neither is wrong — masking discards the sign BIT while floorMod wraps the "
              "VALUE, so they land in different buckets. Pick one and use it "
              "consistently, because mixing them across a codebase means two components "
              "disagree about which bucket a key belongs in.",
      followups="Why did Java choose truncation? It matches C and the underlying "
                "hardware instruction, which was the pragmatic choice in 1995. Python "
                "chose floor division instead, which is why `-7 // 2` is -4 there and "
                "`-7 % 2` is 1 — the same expressions, different answers, in two "
                "languages people routinely switch between.",
      difficulty="Medium", frequency="Common — and a real source of index bugs",
      mnemonic="/ truncates toward zero. % follows the DIVIDEND. floorMod for wrapping."),

    Q("traps",
      "Calling a static method through a null reference works",
      "`Foo f = null; f.hello();` throws no NullPointerException if `hello` is "
      "static. The reference is not actually used — the compiler already knows "
      "which class the method belongs to from the DECLARED TYPE of the variable, "
      "so it emits a call to that class and discards the reference entirely. It "
      "looks exactly like a method call on an object and it is nothing of the "
      "sort.",
      "A static method is resolved at COMPILE TIME from the static type of the "
      "expression, and javac emits `invokestatic` on that class. The instance "
      "expression is still EVALUATED — side effects happen — and its value is "
      "then discarded, so a null reference is never dereferenced and no NPE "
      "occurs. THE SAME MECHANISM IS WHY STATIC METHODS ARE NOT POLYMORPHIC: "
      "`Animal a = new Dog(); a.staticMethod()` calls Animal's version. Every "
      "linter forbids calling a static through an instance for exactly this "
      "reason — it reads as dynamic dispatch and is not.",
      ["static", "dispatch", "null", "trap"],
      code="class Util {\n    static String hello() { return \"static hello\"; }\n    String instance() { return \"instance\"; }\n}\n\nUtil u = null;\nSystem.out.println(u.hello());          // NO NullPointerException\n// System.out.println(u.instance());     // this one DOES throw\n\n// The reference IS evaluated — side effects still happen:\nstatic Util sideEffect() {\n    System.out.println(\"evaluated\");\n    return null;\n}\nSystem.out.println(sideEffect().hello());\n\n// The same rule, seen from the other side — statics are not polymorphic:\nclass Parent { static String who() { return \"Parent\"; } }\nclass Child extends Parent { static String who() { return \"Child\"; } }\nParent p = new Child();\nSystem.out.println(p.who());            // the DECLARED type decides",
      output="static hello\nevaluated\nstatic hello\nParent",
      gotcha="Q: `Util u = null; u.hello();` where hello is static — NPE or not?  NO "
             "NPE, and it prints normally. javac resolves the method from the DECLARED "
             "TYPE and emits invokestatic on Util; the null reference is evaluated and "
             "thrown away without ever being dereferenced. Change `hello` to an "
             "instance method and the identical-looking line throws. THE LINE'S "
             "BEHAVIOUR DEPENDS ENTIRELY ON A MODIFIER YOU CANNOT SEE FROM THE CALL "
             "SITE, which is exactly why every style guide says to write `Util.hello()`.",
      version="Unchanged since Java 1.0. Java 14's helpful NullPointerException messages "
              "make the CONTRAST much clearer when it does throw — the message names "
              "the exact expression that was null.",
      quiz={
          "q": "`Parent p = new Child(); System.out.println(p.who());` where who() is "
               "static in both classes.",
          "options": [
              "Parent — statics are resolved from the DECLARED type at compile time",
              "Child — the object is a Child, so its version runs",
              "It does not compile — a subclass cannot redeclare a static method",
              "Child, but only because Child was instantiated most recently",
          ],
          "answer": 0,
          "why": "Option A is right: this is HIDING, not overriding, and the declared "
                 "type decides. Option B applies virtual dispatch, which is precisely "
                 "what static methods do not have — and it is the reason the linters "
                 "ban this syntax. Option C invents a rule; a subclass may hide a "
                 "static freely and @Override on it is a compile error, which is the "
                 "hint. Option D invents runtime bookkeeping that does not exist.",
      },
      pitfalls="The same applies to FIELDS: `p.field` reads the declared type's field, "
               "so a subclass field with the same name hides rather than overrides. And "
               "a static method cannot be made abstract, cannot use `this`, and cannot "
               "be overridden — three consequences of one rule.",
      followups="Why does the language allow it at all? Historical permissiveness — it "
                "was legal in 1995 and removing it would break existing code. Every "
                "modern linter and IDE flags it, and `@Override` on a static is a "
                "compile error precisely because the language wants you to know these "
                "are different mechanisms.",
      difficulty="Medium", frequency="Common — a favourite 'does this throw' question",
      mnemonic="Static calls use the DECLARED type. The reference is evaluated and thrown away."),

    ]
