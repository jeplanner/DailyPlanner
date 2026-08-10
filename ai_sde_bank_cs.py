"""CS fundamentals pack for the AI SDE bank (Section 3).

Operating systems, DBMS, computer networks and OOP concepts - the four
subjects a final-year student is examined on in college and then asked about
again, differently, in a Google or Amazon screen. The college version rewards
definitions; the interview version rewards a concrete example and knowing why
the idea exists. Every entry here leads with the plain-English picture, then
gives the precise version, then the example you can actually say out loud.

Imported by ai_sde_bank.py, which passes in its Q(...) constructor.
"""


def _c(s):
    return s.strip("\n")


def build(Q):
    entries = []

    # ── OOP concepts ──────────────────────────────────────────────────────
    entries += [
        Q("cs_fundamentals", "The four pillars of OOP, with one running example",
          "Almost every loop opens with this, and almost every candidate recites definitions. Use ONE example - a payment system - and show all four working together. ENCAPSULATION - bundle data with the code that changes it, and hide the internals. An Account exposes deposit() and withdraw() and keeps `_balance` private, so nobody can set a negative balance from outside; the class enforces its own invariants. The test of good encapsulation is that you can change how balance is stored (cents as an int, a Decimal, a running ledger) without any caller noticing. ABSTRACTION - expose WHAT something does and hide HOW. `processor.pay(amount)` tells you nothing about tokenisation, retries or currency conversion, and that is the point: callers depend on a small surface, so the implementation is free to change. Encapsulation hides DATA, abstraction hides COMPLEXITY - that distinction is the follow-up question. INHERITANCE - a subclass gets the parent's behaviour and can specialise it, expressing a genuine is-a relationship (a SavingsAccount IS an Account). Use it sparingly; prefer composition. POLYMORPHISM - one call, many behaviours: `for p in [CardPayment(), UpiPayment(), WalletPayment()]: p.pay(100)` runs three different implementations through one interface, and adding a fourth changes no existing code. Polymorphism is what makes the Open/Closed principle possible, so mention it as the pillar that pays for the others.",
          ["oop", "encapsulation", "abstraction", "inheritance", "polymorphism", "cs"],
          difficulty="Easy",
          frequency="Very commonly asked - the standard opening question of any OOP round, and universal in campus interviews.",
          mnemonic="A PIE: Abstraction, Polymorphism, Inheritance, Encapsulation. Encapsulation hides DATA; abstraction hides COMPLEXITY; inheritance shares a CONTRACT; polymorphism makes one call do many things.",
          code=_c('''
from abc import ABC, abstractmethod

# ENCAPSULATION: the data and the rules that guard it live together.
class Account:
    def __init__(self, owner, opening_cents=0):
        self.owner = owner
        self.__balance = opening_cents        # __ = name-mangled, "private"

    @property
    def balance(self):                        # read-only from outside
        return self.__balance

    def deposit(self, cents):
        if cents <= 0:
            raise ValueError("deposit must be positive")   # invariant enforced HERE
        self.__balance += cents

    def withdraw(self, cents):
        if cents > self.__balance:
            raise ValueError("insufficient funds")
        self.__balance -= cents

# ABSTRACTION: callers see pay(); they never see retries, tokens or gateways.
class PaymentMethod(ABC):
    @abstractmethod
    def pay(self, cents): ...

class CardPayment(PaymentMethod):
    def pay(self, cents): return f"charged {cents}c to a card"

class UpiPayment(PaymentMethod):
    def pay(self, cents): return f"collected {cents}c over UPI"

# INHERITANCE: a genuine is-a, adding behaviour rather than cancelling it.
class SavingsAccount(Account):
    def __init__(self, owner, opening_cents=0, rate=0.03):
        super().__init__(owner, opening_cents)
        self.rate = rate
    def add_interest(self):
        self.deposit(int(self.balance * self.rate))    # reuses the guarded method

# POLYMORPHISM: one loop, three behaviours, and a fourth costs no edits here.
def checkout(methods, cents):
    return [m.pay(cents) for m in methods]

checkout([CardPayment(), UpiPayment()], 2500)
'''),
          example="Polymorphism in one line you already use: `len(x)` works on a string, a list, a dict and your own class if it defines __len__. One call site, many implementations, chosen at runtime by the object's type.",
          examples=[
              "Encapsulation, and the test that proves you have it. Account keeps __balance private and exposes deposit/withdraw. Now change the internal representation from an integer of cents to a list of ledger entries with balance computed as their sum - and NOT ONE CALLER CHANGES. That is the real test of encapsulation: can you replace the internals without breaking anyone? If callers were reading account.balance and doing their own arithmetic, they would all break. Getters and setters that expose every field one-for-one are a public field with extra typing, not encapsulation.",
              "Abstraction versus encapsulation, which is the follow-up you will get. They are different levels. ABSTRACTION is a design decision about WHAT to expose: 'callers of PaymentMethod should see pay(amount) and nothing else - not the retry policy, not the tokenisation, not the currency conversion'. ENCAPSULATION is the MECHANISM that enforces it: private fields, name mangling, access modifiers. So abstraction is the plan and encapsulation is the enforcement. A useful one-liner: abstraction hides COMPLEXITY, encapsulation hides DATA.",
              "Polymorphism doing real work. `for method in [CardPayment(), UpiPayment(), WalletPayment()]: method.pay(2500)` runs three completely different implementations through one call site. Now add CryptoPayment: you write one class and change NOTHING in the loop, in the checkout service, or in the tests for the other three. That is the Open/Closed principle, and polymorphism is the mechanism that makes it possible - which is why it is the pillar that pays for the others.",
              "Inheritance used correctly, and the smell when it is not. SavingsAccount extends Account and ADDS add_interest() while reusing the guarded deposit() - a genuine is-a relationship where nothing is cancelled. Compare a common mistake: FixedDepositAccount extends Account and overrides withdraw() to `raise NotSupported`. That subclass cannot be used everywhere an Account can, so any code holding an Account will break on it. The moment a subclass cancels an inherited method, the inheritance is wrong and you wanted composition.",
              "Polymorphism you already use without noticing. `len(x)` works on a string, a list, a dict, a set and on your own class the moment it defines __len__. One call site, many implementations, chosen at runtime by the object's type. Same for `for x in thing` (__iter__), `a + b` (__add__) and `print(obj)` (__str__). Python's whole data model is polymorphism through protocols - and pointing at len() is a much better answer than a Shape hierarchy, because the interviewer knows you did not memorise it from a textbook.",
              "Putting all four in one sentence about the same system, which is what a strong answer sounds like: 'Account ENCAPSULATES its balance so no caller can make it negative; PaymentMethod is an ABSTRACTION so checkout never learns how a card is charged; SavingsAccount INHERITS Account because it genuinely is one and only adds interest; and the checkout loop is POLYMORPHIC, so adding a fourth payment type is a new file rather than an edit.' Four pillars, one example, thirty seconds - versus four memorised definitions, which is what they hear all day.",
          ],
          pitfalls="Reciting definitions with no example (the interviewer has heard it 300 times); calling getters and setters 'encapsulation' when they expose every field anyway - that is a public field with extra steps; claiming abstraction and encapsulation are the same thing; using inheritance where composition belongs.",
          followups="'Difference between abstraction and encapsulation?' Abstraction is a DESIGN decision about what to expose; encapsulation is the MECHANISM (access control) that enforces it. 'Which pillar would you give up?' Inheritance - composition covers most of its uses and none of its downsides."),

        Q("cs_fundamentals", "Abstract class vs interface - and which to reach for",
          "In plain words: an interface is a CONTRACT ('anything claiming to be a PaymentMethod must have pay()'); an abstract class is a PARTIALLY BUILT PARENT ('every report shares this loading and saving code, but each must supply its own render()'). The classic distinctions: an interface holds only method signatures (plus constants, and since Java 8 default methods), carries no state, and a class may implement MANY of them; an abstract class can hold fields, constructors and fully-implemented methods, and in single-inheritance languages a class may extend only ONE. THE DECISION RULE worth stating: if you are sharing a CAPABILITY across unrelated types, use an interface (a Bird and a Plane are both Flyable but share no ancestry); if you are sharing CODE and state across genuinely related types, use an abstract class. In Python the distinction blurs - abc.ABC gives you abstract methods and Python has multiple inheritance, so a pure-interface ABC and a mixin cover both cases - and modern Python adds Protocols for structural typing, where a class satisfies a protocol just by having the right methods, with no declaration at all. Saying that last part shows you understand the difference between nominal and structural typing.",
          ["oop", "interface", "abstract-class", "abc", "cs", "design"],
          difficulty="Easy",
          frequency="Very commonly asked in OOP rounds at Amazon and in every campus interview.",
          mnemonic="Interface = a CONTRACT (can-do, many per class, no state). Abstract class = a HALF-BUILT PARENT (is-a, one per class, has state and shared code). Sharing capability -> interface. Sharing code -> abstract class.",
          code=_c('''
from abc import ABC, abstractmethod
from typing import Protocol

# INTERFACE-style ABC: a pure contract, no state, no shared code.
class Serializable(ABC):
    @abstractmethod
    def to_dict(self) -> dict: ...

# ABSTRACT CLASS: shares real code and state, and demands one missing piece.
class Report(ABC):
    def __init__(self, title, rows):
        self.title, self.rows = title, rows        # STATE - an interface cannot

    def generate(self):                            # SHARED algorithm (Template Method)
        header = self._header()
        return header + self.render() + self._footer()

    def _header(self): return f"=== {self.title} ===\\n"   # concrete, inherited
    def _footer(self): return f"\\n({len(self.rows)} rows)"

    @abstractmethod
    def render(self) -> str: ...                   # each subclass MUST supply this

class CsvReport(Report, Serializable):             # one abstract parent, one interface
    def render(self):
        return "\\n".join(",".join(map(str, r)) for r in self.rows)
    def to_dict(self):
        return {"title": self.title, "rows": self.rows}

class HtmlReport(Report):
    def render(self):
        return "<table>" + "".join(f"<tr><td>{r}</td></tr>" for r in self.rows) + "</table>"

# Report() alone raises TypeError - you cannot instantiate an abstract class.

# PROTOCOL (structural typing): no inheritance at all. Any class with these
# methods satisfies it, which is how Python actually works day to day.
class SupportsClose(Protocol):
    def close(self) -> None: ...

def shutdown(resource: SupportsClose):     # a file, a socket, your own class -
    resource.close()                       # none of them ever heard of this type
'''),
          example="`Comparable` in Java or `__lt__` in Python is an interface-style capability: sorting works on anything that can compare itself, regardless of what else it is. `Report` above is an abstract class: every report shares the header/footer machinery and differs only in render().",
          examples=[
              "The decision, made concrete. A Bird and a Plane are both Flyable - they share a CAPABILITY but no ancestry whatsoever, so Flyable is an interface. CsvReport and HtmlReport share the header/footer machinery, the title and the rows - they share CODE and STATE, so Report is an abstract class. The rule that follows: if you find yourself wanting to put a field in it, you want an abstract class; if it is only method signatures, you want an interface.",
              "Why a class can implement many interfaces but extend one parent. Interfaces carry no state, so implementing five of them creates no ambiguity - there is nothing to collide. Two parent CLASSES could both define a `name` field or a half-implemented method, and the compiler would have no principled way to choose, which is the diamond problem. That is the whole reason Java allows unlimited `implements` and a single `extends`, and it is a much better answer than 'because Java says so'.",
              "The abstract class's real superpower: Template Method. Report.generate() implements the WHOLE algorithm - header, then render(), then footer - and leaves exactly one hole for subclasses. So the sequence is defined once and cannot be got wrong, while each format supplies only its own piece. An interface cannot do this, because it has no body to put the sequence in. Whenever several implementations share a fixed sequence with one varying step, that is the abstract-class case.",
              "The versioning cost, which is why Java 8 added default methods. Add a method to an interface that 200 classes implement and all 200 break at once - they no longer satisfy the contract. Add a CONCRETE method to an abstract class and every subclass inherits it silently, breaking nothing. Java's default methods exist precisely to let interfaces evolve without that mass breakage (it is how Collection gained stream() without breaking every collection ever written). Knowing this trade shows you have thought about libraries, not just classes.",
              "Python blurs the line, and you should say so. abc.ABC gives you abstract methods, and Python has multiple inheritance, so a pure-interface ABC and a stateful abstract base are the same construct with different content. What Python adds is PROTOCOLS: `class SupportsClose(Protocol): def close(self) -> None: ...` matches any object with a close() method - a file, a socket, your own class - with no inheritance and no declaration anywhere. That is STRUCTURAL typing (does it have the shape?) versus NOMINAL typing (did it declare the type?), and naming that distinction is a senior-sounding remark.",
              "The gotcha that bites in practice: `Report()` raises TypeError because it has an unimplemented abstract method - but only if the class actually inherits from ABC. Write `class Report:` with an @abstractmethod decorator and no ABC base, and Python happily instantiates it; the decorator alone does nothing. The metaclass supplied by ABC is what enforces the check. Forgetting the base class turns a compile-time-style guarantee into a runtime AttributeError deep in someone else's code.",
          ],
          pitfalls="Adding a method to a widely-implemented interface, which breaks every implementer at once (hence Java's default methods); using an abstract class purely to share a helper function - that is what a module-level function or a mixin is for; forgetting that Python lets you instantiate a class with unimplemented abstract methods if you forget to inherit from ABC.",
          followups="'Can an abstract class have a constructor?' Yes, and subclasses call it via super() - that is a main reason to prefer one when there is shared state. 'Interface with a default method vs abstract class?' Interfaces still hold no state, so the choice comes down to whether you need fields."),

        Q("cs_fundamentals", "Overloading vs overriding (compile-time vs runtime polymorphism)",
          "OVERLOADING is several methods with the SAME NAME but DIFFERENT PARAMETER LISTS in the same class - add(int, int) and add(double, double). The compiler picks one from the argument types at COMPILE time, which is why it is called static or compile-time polymorphism; it is really just a naming convenience. OVERRIDING is a subclass replacing a parent method with the SAME signature. Which one runs is decided at RUNTIME from the actual object's type - dynamic dispatch - and that is real polymorphism, the mechanism that makes `for shape in shapes: shape.area()` work. THE PYTHON TWIST, and this is what makes the question interesting for you specifically: Python does NOT support overloading. Defining `def add(self, a, b)` and then `def add(self, a, b, c)` simply replaces the first with the second, silently. Python covers the same ground with default arguments, *args/**kwargs, and functools.singledispatch for genuine type-based dispatch. Overriding, on the other hand, works exactly as expected, and super() lets you extend rather than replace. The rules that trip people up in Java-flavoured questions: you cannot overload on return type alone, static methods are HIDDEN not overridden, and an overriding method may not narrow the access modifier or add new checked exceptions.",
          ["oop", "polymorphism", "overloading", "overriding", "python", "cs"],
          difficulty="Easy",
          frequency="Very commonly asked, especially in campus and SDE-1 screens; the Python-has-no-overloading answer stands out.",
          mnemonic="OverLOADing = same name, different parameters, chosen by the COMPILER (static). OverRIDing = same signature, chosen by the OBJECT at RUNTIME (dynamic). Python has overriding but NOT overloading - the second definition just wins.",
          code=_c('''
# OVERRIDING - works exactly as expected, and is chosen by the real type.
class Animal:
    def speak(self): return "..."
    def describe(self): return f"This animal says {self.speak()}"   # dynamic dispatch

class Dog(Animal):
    def speak(self): return "Woof"          # replaces the parent's version

class Cat(Animal):
    def speak(self): return "Meow"

for a in (Dog(), Cat(), Animal()):
    print(a.describe())      # Animal.describe calls the SUBCLASS's speak()

# EXTENDING rather than replacing, with super():
class LoudDog(Dog):
    def speak(self): return super().speak().upper() + "!!!"


# OVERLOADING - Python does NOT have it. This is a common gotcha:
class Calc:
    def add(self, a, b):        return a + b
    def add(self, a, b, c):     return a + b + c     # <- SILENTLY replaces the first
# Calc().add(1, 2)  ->  TypeError: add() missing 1 required positional argument

# The three Pythonic replacements:
class Calc2:
    def add(self, a, b, c=0):       # 1. default arguments
        return a + b + c
    def add_all(self, *nums):       # 2. varargs
        return sum(nums)

from functools import singledispatchmethod
class Area:                          # 3. genuine dispatch ON TYPE
    @singledispatchmethod
    def of(self, shape): raise NotImplementedError
    @of.register
    def _(self, shape: int):   return shape * shape          # a square's side
    @of.register
    def _(self, shape: tuple): return shape[0] * shape[1]    # (w, h)
'''),
          example="`print()` looks overloaded because it accepts anything, but it is not - it calls str() on each argument, which is polymorphism through a common protocol. That is how dynamically typed languages get overloading's convenience without the feature.",
          examples=[
              "The Python gotcha, which is the highest-value thing in this entry. Define `def add(self, a, b)` and then `def add(self, a, b, c)` in the same class. The second definition simply REBINDS the name - the first is gone, with no error and no warning. Calling `Calc().add(1, 2)` then raises TypeError about a missing argument, which is a confusing error for something that looks like it should work. Java would have kept both and picked by argument count. Knowing this saves you from a genuinely puzzling bug and is a strong differentiator in a Python-flavoured screen.",
              "Overriding traced through dynamic dispatch. Animal.describe() calls self.speak(). When you call Dog().describe(), the describe() body is the PARENT's code, but self.speak() resolves to DOG's implementation, because the lookup happens at runtime against the actual object's type. That is why the base class can call a method it never implements and still get correct behaviour - and it is the mechanism behind the Template Method pattern. Being able to explain which method the parent's code ends up calling is what the question is really testing.",
              "The three Pythonic replacements for overloading, in the order you should reach for them. (1) DEFAULT ARGUMENTS: `def add(self, a, b, c=0)` handles both arities in one function - simplest, and right most of the time. (2) *args: `def add_all(self, *nums): return sum(nums)` when the count is genuinely variable. (3) functools.singledispatch when the behaviour depends on the TYPE, not the count - it registers a separate implementation per annotated type and dispatches at call time, which is the closest Python gets to real overloading.",
              "Method hiding, the classic Java trick question. A static method redeclared in a subclass is HIDDEN, not overridden: the call is resolved by the REFERENCE type at compile time, not by the object at runtime. So `Animal a = new Dog(); a.staticMethod();` runs ANIMAL's version, even though the object is a Dog. Instance methods do the opposite. Static dispatch versus dynamic dispatch in one example, and it is asked precisely because the two look identical in source.",
              "The rules an overriding method must respect, which get probed in Java-flavoured interviews. Same name and parameter list (a different list is an overload, not an override - hence @Override, which catches exactly that typo). The return type may be covariant (a subtype). The access modifier may only widen, never narrow - a public method cannot be overridden as protected, because callers holding the base type would suddenly lose access. And no new CHECKED exceptions may be added, for the same reason: callers were written against the parent's contract.",
              "Why overloading is only 'polymorphism' in a weak sense. The compiler picks the target from the static argument types and bakes it in - nothing varies at runtime, so it is really a naming convenience that saves you from writing addInt and addDouble. Overriding is the one that gives you the property that matters: a single call site whose behaviour depends on the object, which is what lets you write code today that works with classes written next year. If forced to pick which one 'real' polymorphism means, say overriding, and say why.",
          ],
          pitfalls="Claiming Python supports overloading; thinking overloading is polymorphism in the meaningful sense; overriding a method with a weaker signature; in Java, 'overriding' a static method (it is hidden, and the call is resolved by the reference type, not the object) or overriding equals() without also overriding hashCode().",
          followups="'What is method hiding?' A static method redeclared in a subclass - resolved by the reference type, so it is a common trick question. 'How does dynamic dispatch actually work?' A per-class table of function pointers (a vtable in C++/Java, the __dict__ / MRO lookup in Python) consulted at call time."),

        Q("cs_fundamentals", "Multiple inheritance, the diamond problem, and Python's MRO",
          "THE PROBLEM: if class D inherits from both B and C, and both inherit from A and both override greet(), which greet() does D get? That ambiguity is the diamond problem, and it is why Java refuses multiple class inheritance (allowing it only for interfaces, which carry no state). C++ allows it and hands you virtual inheritance to disambiguate. PYTHON ALLOWS IT and resolves the order deterministically with the C3 linearisation, exposed as `D.__mro__`. The rules the MRO guarantees: a class always precedes its parents, parents keep the order you listed them in, and each class appears exactly once. For the diamond, that gives D -> B -> C -> A -> object, so B wins - but crucially, A runs ONCE, not twice, which is the real payoff. THE PART CANDIDATES MISS: super() does not mean 'my parent', it means 'the next class in the MRO of the actual object', which is why every class in a cooperative hierarchy must call super().__init__() - if one link forgets, the chain silently stops and some ancestor never initialises. The practical guidance to give: use multiple inheritance for MIXINS - small, stateless, single-purpose classes like LoggingMixin or JsonSerializableMixin - and avoid deep diamonds of stateful classes, which are genuinely hard to reason about.",
          ["oop", "inheritance", "mro", "diamond-problem", "python", "cs"],
          difficulty="Medium",
          frequency="Commonly asked, and a favourite Python-specific follow-up to any inheritance question.",
          mnemonic="Diamond = D inherits B and C, both inherit A. Java bans it, C++ patches it, Python ORDERS it (C3 linearisation, D.__mro__). super() = 'next in the MRO', NOT 'my parent' - so every class must call super() or the chain breaks.",
          code=_c('''
class A:
    def __init__(self): print("A");
    def greet(self): return "A"

class B(A):
    def __init__(self): print("B"); super().__init__()
    def greet(self): return "B"

class C(A):
    def __init__(self): print("C"); super().__init__()
    def greet(self): return "C"

class D(B, C):                      # the diamond
    def __init__(self): print("D"); super().__init__()

D().greet()          # "B"  - B comes before C in the MRO
[c.__name__ for c in D.__mro__]     # ['D', 'B', 'C', 'A', 'object']

# D() prints D, B, C, A - note A runs ONCE even though two paths reach it.
# That only works because B and C both call super() rather than A.__init__().


# MIXINS - the good use of multiple inheritance: small, stateless, one job.
import json, logging

class JsonMixin:
    def to_json(self): return json.dumps(self.__dict__)

class TimestampMixin:
    def touch(self):
        import datetime as dt
        self.updated_at = dt.datetime.now()

class User(JsonMixin, TimestampMixin):      # composes two capabilities
    def __init__(self, name): self.name = name

u = User("asha"); u.touch(); u.to_json()


# The classic breakage: one class forgets super(), so the chain stops dead.
class Bad(A):
    def __init__(self): print("Bad")        # no super() call
class Broken(Bad, C): pass
# Broken() prints only "Bad" - C and A never initialise, and the bug shows up
# much later as a missing attribute.
'''),
          example="Python's own `class MyHandler(logging.Handler, ContextMixin)` style, or Django's class-based views, are built entirely on cooperative multiple inheritance - which is why every Django mixin's method ends with a super() call.",
          pitfalls="Calling ParentClass.__init__(self) directly instead of super().__init__(), which breaks the diamond and can double-initialise; assuming super() means the immediate parent; mixins that carry state and collide on attribute names; a hierarchy so deep that finding the running method needs the MRO printed out.",
          followups="'Why does Java forbid it?' To avoid ambiguous state; interfaces are safe because they hold none. 'What does C3 guarantee?' A consistent, monotonic order that respects local precedence - and Python raises a TypeError at class creation if no such order exists, which is better than a silent surprise."),

        Q("cs_fundamentals", "Shallow copy vs deep copy (and the aliasing bug behind it)",
          "In plain words: ASSIGNMENT copies nothing - both names point at the same object. A SHALLOW copy makes a new outer container whose slots still point at the SAME inner objects. A DEEP copy recursively rebuilds everything, so nothing is shared. The bug this causes is the single most common source of 'I changed one thing and something else changed too': `b = a` then `b.append(1)` also changes a; `b = a[:]` on a list of lists gives you a new outer list whose inner lists are still shared, so `b[0].append(1)` still mutates a[0]. THE COST is the reason shallow is the default: deep copying a large object graph is O(total nodes) in time and memory, and copy.deepcopy also has to track already-seen objects to survive cycles. THE PRACTICAL RULES to state: for flat containers of immutable values (ints, strings, tuples of those) shallow copying is completely safe and cheap; for nested mutable structures you need a deep copy or, far better, immutable data - if the inner objects cannot change, sharing them is free and correct. This connects directly to the Python interview classic about mutable default arguments, and to the LLD point about snapshotting a price onto an order line rather than referencing a live Product.",
          ["python", "copy", "aliasing", "memory", "cs", "oop"],
          difficulty="Easy",
          frequency="Very commonly asked in Python-flavoured screens and as a debugging question.",
          mnemonic="Assignment = same object, two names. Shallow = new box, same contents. Deep = new box, new contents, all the way down. If the contents are immutable, shallow is already safe.",
          code=_c('''
import copy

a = [[1, 2], [3, 4]]

b = a                       # NOT a copy: one list, two names
b.append([5, 6]); len(a)    # 3 - a changed too

c = a[:]                    # SHALLOW (also list(a), copy.copy(a))
c.append([7, 8]); len(a)    # unchanged - the OUTER list is new...
c[0].append(99); a[0]       # [1, 2, 99]  <- ...but the INNER lists are shared

d = copy.deepcopy(a)        # DEEP: everything rebuilt
d[0].append(1000); a[0]     # unchanged - nothing is shared


# The famous mutable-default-argument bug, which is the same aliasing idea:
def add_item(item, basket=[]):        # the [] is created ONCE, at def time
    basket.append(item)
    return basket

add_item("apple")     # ['apple']
add_item("pear")      # ['apple', 'pear']  <- the SAME list, still there

def add_item_fixed(item, basket=None):
    basket = [] if basket is None else basket    # a fresh list per call
    basket.append(item)
    return basket


# Custom deep-copy behaviour, and the cheap alternative: immutability.
from dataclasses import dataclass
@dataclass(frozen=True)               # cannot be mutated, so sharing is safe
class Money:
    cents: int
    currency: str = "EUR"
# Two orders can share the same Money instance with no risk at all.
'''),
          example="A Config object holding a dict of feature flags. Handing each request `copy.copy(config)` looks safe but every request still shares the same flags dict - one request toggling a flag changes it for everyone. Either deepcopy per request (expensive) or make the flags immutable (free).",
          examples=[
              "The three levels, traced on one object. a = [[1,2],[3,4]]. `b = a` is not a copy at all — one list, two names, so b.append changes a. `c = a[:]` is SHALLOW: the outer list is new, so c.append leaves a alone, but c[0].append(99) mutates a[0] too, because the inner lists are shared. `d = copy.deepcopy(a)` rebuilds everything, so d[0].append(1000) changes nothing in a. Three lines, three different behaviours — and the middle one is the one that surprises people because it LOOKS like a copy.",
              "The mutable default argument, which is the same bug wearing a different hat. `def add_item(item, basket=[])` creates that list ONCE, at function-definition time, not per call. So add_item('apple') returns ['apple'] and add_item('pear') returns ['apple','pear'] — the same list, still there from last time. The fix is `basket=None` plus `basket = [] if basket is None else basket`. This is probably the most-asked Python gotcha in interviews, and it is aliasing, not a special rule.",
              "A production-shaped version. A Config object holding a dict of feature flags, handed to each request as `copy.copy(config)`. It looks safe — each request gets its own Config — but every one still shares the same flags dict, so one request toggling a flag changes it for everyone concurrently. Either deepcopy per request (expensive on a hot path) or make the flags immutable. The second is almost always right, and it is the general lesson below.",
              "The cheapest fix is usually immutability, not copying. A frozen dataclass or a tuple cannot be mutated, so sharing it between threads, requests or objects is free and correct — no copy needed at all. That is why Money, Point and similar value objects are conventionally immutable, and it connects directly to the LLD rule about snapshotting a price onto an order line: an immutable snapshot cannot be changed out from under the order.",
              "Where deepcopy bites you. It recursively copies EVERYTHING reachable — so an object holding a database connection, a file handle, a socket or a thread lock will have those copied too, which is either an error or silently wrong. Define __deepcopy__ to control it, or restructure so those live outside the copied object. Also: deepcopy is O(total nodes) and quietly expensive in a loop, which is a real performance bug rather than a style one.",
              "How cycles are handled, since it is a natural follow-up. copy.deepcopy keeps a memo dict of already-copied objects keyed by id(), so a structure that references itself terminates instead of recursing forever — and the copy preserves the same sharing structure as the original, rather than duplicating a shared sub-object twice. That memo is also why deepcopy is not merely 'recursively copy': it has to preserve identity relationships.",
          ],
          pitfalls="Assuming list slicing deep-copies; deepcopy on an object holding a database connection or a file handle (it will try to copy those too - define __deepcopy__ or use __slots__ carefully); deepcopy in a hot loop, which is quietly O(n) per call; mutable class attributes shared by every instance, which is the same bug at class level.",
          followups="'How does deepcopy handle cycles?' It keeps a memo dict of already-copied objects keyed by id, so a self-referencing structure terminates. 'What is the cheapest fix in a design?' Make the shared data immutable - then no copy is needed at all."),

        Q("cs_fundamentals", "Python's GIL - what it actually stops, and what it does not",
          "Highly relevant to you because ML code is Python. THE FACT: CPython has one Global Interpreter Lock, so only ONE thread executes Python bytecode at a time within a process. THE CONSEQUENCE people state correctly: threads give you no speed-up for CPU-BOUND pure-Python work - four threads summing numbers take as long as one, plus switching overhead. THE CONSEQUENCE people miss: threads are still excellent for I/O-BOUND work, because the GIL is RELEASED during blocking I/O (a network read, a disk read, time.sleep), so 50 threads waiting on 50 HTTP requests genuinely overlap. It is also released by C extensions that opt in - which is why numpy, pandas, PyTorch and scikit-learn matrix operations DO use multiple cores despite the GIL: the heavy loop is running in C with the lock dropped. THE OPTIONS when you are actually CPU-bound: multiprocessing (separate processes, separate GILs, at the cost of IPC and memory), numpy/vectorisation (push the loop into C), Cython or a native extension, or Python 3.13+'s experimental free-threaded build. THE OTHER TRAP: the GIL does NOT make your code thread-safe. `counter += 1` is read-modify-write across several bytecodes and can still interleave, so you still need locks. That last sentence is the one interviewers are listening for.",
          ["python", "gil", "concurrency", "threads", "multiprocessing", "cs", "ml"],
          difficulty="Medium",
          frequency="Very commonly asked in Python and ML-engineering interviews.",
          mnemonic="One GIL = one thread running Python bytecode at a time. CPU-bound Python: threads do NOT help, use processes or numpy. I/O-bound: threads DO help, the GIL is released while waiting. And the GIL does NOT make += atomic.",
          code=_c('''
import threading, time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

def cpu_work(n):                       # pure Python arithmetic: GIL-bound
    return sum(i * i for i in range(n))

def io_work(url):                      # blocking wait: GIL is RELEASED here
    time.sleep(0.5); return url

# CPU-bound with THREADS -> no faster than serial (often slower).
with ThreadPoolExecutor(4) as ex:
    list(ex.map(cpu_work, [5_000_000] * 4))      # ~4x one call

# CPU-bound with PROCESSES -> genuinely parallel, 4 cores, 4 GILs.
if __name__ == "__main__":
    with ProcessPoolExecutor(4) as ex:
        list(ex.map(cpu_work, [5_000_000] * 4))  # ~1x one call

# I/O-bound with THREADS -> a real 4x win, GIL or not.
with ThreadPoolExecutor(4) as ex:
    list(ex.map(io_work, ["a", "b", "c", "d"]))  # ~0.5s total, not 2s


# The GIL does NOT give you atomicity. This really does lose increments:
counter = 0
def bump():
    global counter
    for _ in range(100_000):
        counter += 1          # LOAD, ADD, STORE - three steps, interruptible

ts = [threading.Thread(target=bump) for _ in range(4)]
[t.start() for t in ts]; [t.join() for t in ts]
print(counter)                # usually far less than 400,000

# Correct version:
lock = threading.Lock()
def bump_safe():
    global counter
    for _ in range(100_000):
        with lock:
            counter += 1
'''),
          example="Why numpy is the escape hatch: `arr.sum()` over ten million floats hands the whole array to compiled C that releases the GIL, so it runs at full speed and can even use several cores through BLAS. The same sum written as a Python for-loop is interpreted ten million times under the lock. Nothing about Python changed - the work left the interpreter.",
          examples=[
              "The two cases, with the numbers that make the rule stick. CPU-BOUND: four threads each summing 5 million squares take about as long as running them one after another, because only one holds the GIL at a time - you pay switching overhead for zero parallelism. Four PROCESSES finish in roughly the time of one, because each has its own interpreter and its own GIL. I/O-BOUND: four threads each sleeping 0.5s finish in ~0.5s total, not 2s, because the GIL is RELEASED while a thread waits on the OS. Same GIL, opposite conclusions - which is why 'threads are useless in Python' is wrong.",
              "Why numpy escapes it, which matters directly for ML work. `arr.sum()` over ten million floats hands the whole array to precompiled C that explicitly releases the GIL for the duration, so it runs at full speed and BLAS can even use several cores. The same sum written as a Python for-loop is interpreted ten million times while holding the lock. Nothing about Python got faster - the work left the interpreter. This is the entire architecture of the scientific Python stack, and the answer to 'isn't Python too slow for ML?'.",
              "The trap that catches people who think the GIL saves them: it does NOT make your code thread-safe. `counter += 1` compiles to LOAD, ADD, STORE - three bytecodes - and a thread can be descheduled between any two. Four threads each incrementing 100,000 times reliably produce far less than 400,000. The GIL guarantees one bytecode at a time, not one STATEMENT at a time, and that distinction is the single most valuable sentence in this entry.",
              "Picking the right tool, as a decision rule. Waiting on network, disk or a database -> threads or asyncio; the GIL is irrelevant because it is released during the wait. Crunching numbers in pure Python -> multiprocessing, or better, vectorise it into numpy so the loop leaves the interpreter entirely. Tens of thousands of concurrent connections -> asyncio, because one thread per socket is too heavy. The wrong pairing costs you: multiprocessing for I/O pays process spawn and pickling for nothing.",
              "The multiprocessing costs people forget. Arguments are PICKLED and copied to each worker, so passing a 2GB dataframe to four workers copies it four times and can cost more than the computation saves. Workers cannot share mutable state - you need a Queue, a Manager or shared memory. And on macOS and Windows the default start method is spawn, which re-imports your module in each child, so module-level code runs again and the `if __name__ == '__main__':` guard is mandatory rather than stylistic.",
              "Where this is going, so the answer is current. Python 3.13 ships an experimental free-threaded build (PEP 703) with the GIL removed, and 3.14 continues that work. Worth naming, with the honest caveat: removing the GIL converts easy correctness into hard correctness, because every shared data structure then needs its own locking, and single-threaded performance takes a hit from the finer-grained locking it replaces. It is not a free win, and saying that is more informed than either 'the GIL is being removed, problem solved' or not knowing it is happening.",
          ],
          pitfalls="Reaching for multiprocessing on I/O-bound work, paying process overhead for nothing; assuming the GIL makes shared state safe; forgetting that multiprocessing pickles arguments, so passing a huge dataframe to each worker can cost more than the computation; forgetting the `if __name__ == '__main__'` guard on Windows/macOS spawn.",
          followups="'When would you choose asyncio over threads?' For very high-concurrency I/O (thousands of sockets) where one thread per connection is too heavy - same GIL, far less overhead. 'Does removing the GIL fix everything?' No - it converts easy correctness into hard correctness, since every shared structure then needs its own locking."),
    ]

    # ── Operating systems ─────────────────────────────────────────────────
    entries += [
        Q("cs_fundamentals", "CPU scheduling algorithms (FCFS, SJF, SRTF, Round Robin, Priority)",
          "The scheduler decides which ready process gets the CPU next, and each algorithm optimises a different thing. FCFS (first come, first served) - a plain queue, non-preemptive, trivially fair in arrival order, but it suffers the CONVOY EFFECT: one 100-second job at the front makes every 1-second job behind it wait 100 seconds, wrecking average waiting time. SJF (shortest job first) - provably OPTIMAL for average waiting time, but it needs to know burst times in advance (in practice you estimate them with an exponential average of past bursts) and it STARVES long jobs when short ones keep arriving. SRTF is the preemptive version: a newly arrived shorter job kicks out the running one. ROUND ROBIN - each process gets a fixed time quantum then goes to the back of the queue; this is what interactive systems use because it bounds response time. The quantum is the whole design: too large and it degenerates into FCFS, too small and context-switch overhead dominates (a switch costs microseconds, so a quantum of 10-100ms keeps overhead near 1%). PRIORITY - highest priority first, which starves low-priority work unless you add AGING (raise a waiting process's priority over time). Real kernels blend these: Linux CFS gives each task a share of CPU time proportional to its weight and always runs the one with the least accumulated virtual runtime, which is round robin generalised to fractional shares.",
          ["os", "scheduling", "cpu", "round-robin", "cs"],
          difficulty="Medium",
          frequency="Frequently asked - a staple OS question in screens and campus interviews.",
          mnemonic="FCFS = fair but convoys. SJF = optimal average wait but starves and needs a crystal ball. RR = bounded response time, and the quantum is the whole trade. Priority = starvation unless you add aging.",
          code=_c('''
def fcfs(jobs):
    """jobs = [(name, arrival, burst)] -> completion/wait/turnaround per job."""
    t, out = 0, []
    for name, arrival, burst in sorted(jobs, key=lambda j: j[1]):
        start = max(t, arrival)          # CPU may idle waiting for an arrival
        finish = start + burst
        out.append((name, start - arrival, finish - arrival))   # wait, turnaround
        t = finish
    return out

def round_robin(jobs, quantum):
    """Preemptive: every job runs at most `quantum` before yielding."""
    from collections import deque
    jobs = sorted(jobs, key=lambda j: j[1])
    remaining = {n: b for n, _, b in jobs}
    arrivals, q, t, i, done = jobs, deque(), 0, 0, {}
    while i < len(arrivals) or q:
        while i < len(arrivals) and arrivals[i][1] <= t:
            q.append(arrivals[i][0]); i += 1          # admit new arrivals
        if not q:
            t = arrivals[i][1]; continue              # idle until the next arrival
        name = q.popleft()
        slice_ = min(quantum, remaining[name])
        t += slice_
        remaining[name] -= slice_
        while i < len(arrivals) and arrivals[i][1] <= t:
            q.append(arrivals[i][0]); i += 1          # admit BEFORE requeueing -
        if remaining[name] > 0:                       # this ordering detail is
            q.append(name)                            # where marks are lost
        else:
            done[name] = t
    return done

# Worked comparison - the convoy effect in numbers.
# jobs: A(arrive 0, burst 10), B(arrive 1, burst 1), C(arrive 2, burst 1)
#   FCFS order A,B,C  -> waits 0, 9, 9   -> average wait 6.0
#   SJF (preemptive)  -> waits 2, 0, 0   -> average wait 0.67
#   RR quantum 2      -> waits 4, 1, 2   -> average wait 2.33  (best RESPONSE time)
'''),
          example="Three jobs: A needs 10ms and arrives first, B and C need 1ms each. FCFS makes B and C wait 9ms each for a 1ms job - the user perceives a freeze. Round robin with a 2ms quantum gets both short jobs done within 5ms; total throughput is slightly worse because of the extra switches, and that is exactly the trade interactive systems choose.",
          pitfalls="Confusing waiting time (time in the ready queue) with turnaround time (completion minus arrival); forgetting the CPU can idle when nothing has arrived; in round robin, requeueing the preempted job BEFORE admitting new arrivals (a classic exam trap that changes the answer); claiming SJF is usable as-is when burst times are unknowable.",
          followups="'How does the OS estimate the next burst?' An exponential moving average of previous bursts. 'What is priority inversion?' A low-priority task holding a lock a high-priority task needs - fixed by priority inheritance, and the bug that famously nearly ended the Mars Pathfinder mission."),

        Q("cs_fundamentals", "Producer-consumer with a bounded buffer (and condition variables)",
          "The canonical synchronisation problem, and the one that shows whether you understand more than 'add a lock'. SETUP: producers add items to a fixed-size buffer, consumers remove them; a producer must WAIT when the buffer is full and a consumer must WAIT when it is empty, without either burning CPU. THE WRONG ANSWERS: a busy-wait loop (`while full: pass`) which spins a core doing nothing, and a plain mutex, which gives mutual exclusion but no way to WAIT FOR A CONDITION. THE CLASSIC SOLUTION uses three primitives - a mutex for the buffer itself, plus two counting semaphores: `empty` initialised to the buffer size and `full` initialised to 0. A producer does wait(empty), lock, insert, unlock, signal(full); a consumer mirrors it. THE ORDER MATTERS: taking the mutex before the semaphore deadlocks, because a blocked producer would hold the lock a consumer needs to make room. In modern code you would use a CONDITION VARIABLE instead: wait on it while the predicate is false, and notify after changing state. THE DETAIL INTERVIEWERS PROBE: always wait in a `while` loop, never an `if` - a thread can wake up and find the condition already false again because another thread got there first (a spurious or stolen wakeup), and the while loop is the only correct guard.",
          ["os", "concurrency", "producer-consumer", "semaphore", "condition-variable", "cs"],
          difficulty="Medium",
          frequency="Frequently asked - the standard OS concurrency question, and it maps onto real queue/worker code.",
          mnemonic="Two counting semaphores (empty starts at N, full starts at 0) plus one mutex. Take the SEMAPHORE first, the mutex second - reverse them and you deadlock. Always wait in a WHILE loop, never an if.",
          code=_c('''
import threading, collections

# Version 1: condition variable - what you would actually write today.
class BoundedBuffer:
    def __init__(self, capacity):
        self.capacity = capacity
        self.items = collections.deque()
        self.lock = threading.Lock()
        self.not_full  = threading.Condition(self.lock)   # both share ONE lock
        self.not_empty = threading.Condition(self.lock)

    def put(self, item):
        with self.not_full:
            while len(self.items) >= self.capacity:   # WHILE, not if: another
                self.not_full.wait()                  # producer may beat us
            self.items.append(item)
            self.not_empty.notify()                   # wake ONE consumer

    def get(self):
        with self.not_empty:
            while not self.items:
                self.not_empty.wait()                 # releases the lock while asleep
            item = self.items.popleft()
            self.not_full.notify()                    # wake ONE producer
            return item


# Version 2: the textbook semaphore solution - know the ORDER.
class SemaphoreBuffer:
    def __init__(self, capacity):
        self.buf = collections.deque()
        self.mutex = threading.Lock()
        self.empty = threading.Semaphore(capacity)    # free slots
        self.full  = threading.Semaphore(0)           # filled slots

    def put(self, item):
        self.empty.acquire()          # 1. wait for a free slot  <- semaphore FIRST
        with self.mutex:              # 2. then take the lock
            self.buf.append(item)
        self.full.release()           # 3. announce one more item

    def get(self):
        self.full.acquire()           # wait for an item
        with self.mutex:
            item = self.buf.popleft()
        self.empty.release()          # announce one more free slot
        return item

# DEADLOCK if you swap steps 1 and 2: a producer holding the mutex blocks on
# `empty`, and the consumer that would free a slot can never take the mutex.

# In practice: queue.Queue(maxsize=N) already implements all of this correctly.
'''),
          example="A web crawler: fetcher threads produce HTML into a bounded queue and parser threads consume it. The bound is the point - without it, fast fetchers and slow parsers grow the queue until the process runs out of memory. Backpressure is the buffer size.",
          pitfalls="`if` instead of `while` around wait(); notify() when several waiters need waking (use notify_all if the condition can satisfy more than one); using two separate locks for the two conditions; busy-waiting; forgetting that wait() must be called with the lock held and releases it while sleeping.",
          followups="'notify vs notify_all?' notify wakes one, which is enough when any single waiter can proceed; notify_all is needed when waiters are waiting on different predicates. 'How does this scale to multiple processes or machines?' The same shape, with the buffer in shared memory or a message broker like SQS/Kafka - and the queue depth becomes your backpressure signal."),

        Q("cs_fundamentals", "Page replacement: FIFO, LRU, Optimal - and Belady's anomaly",
          "When physical memory is full and a new page is needed, something must be evicted; the algorithm choosing the victim decides your page-fault rate. FIFO - evict the oldest-loaded page. Simple, and bad, because 'loaded long ago' has nothing to do with 'not needed now'; a heavily-used page loaded at start-up is a prime victim. FIFO also suffers BELADY'S ANOMALY: adding MORE frames can produce MORE page faults, which is deeply counter-intuitive and therefore a favourite exam question. OPTIMAL (Belady's OPT) - evict the page whose next use is furthest in the future. Provably minimal faults, and impossible to implement because it needs the future; its value is as a benchmark. LRU - evict the least recently used page, the practical approximation of OPT that works because of locality of reference. True LRU needs a timestamp or a linked-list move on EVERY access, which is too expensive in hardware, so real systems approximate: the CLOCK (second-chance) algorithm keeps pages in a ring with one reference bit, and the hand sweeps, clearing bits and evicting the first page whose bit is already 0. LRU has no Belady anomaly because it is a STACK algorithm - the pages held with n frames are always a subset of those held with n+1. That sentence is the crisp answer to 'why does LRU not suffer the anomaly?'.",
          ["os", "memory", "paging", "page-replacement", "lru", "cs"],
          difficulty="Medium",
          frequency="Frequently asked in OS screens; Belady's anomaly is a classic gotcha.",
          mnemonic="FIFO = oldest loaded (dumb, and can get WORSE with more frames - Belady). OPT = furthest future use (perfect, impossible). LRU = least recently used (locality makes it work). CLOCK = cheap LRU with one reference bit.",
          code=_c('''
from collections import OrderedDict, deque

def fifo_faults(pages, frames):
    mem, q, faults = set(), deque(), 0
    for p in pages:
        if p not in mem:
            faults += 1
            if len(mem) == frames:
                mem.discard(q.popleft())      # evict the OLDEST LOADED
            mem.add(p); q.append(p)
    return faults

def lru_faults(pages, frames):
    mem, faults = OrderedDict(), 0
    for p in pages:
        if p in mem:
            mem.move_to_end(p)                # a HIT still updates recency
        else:
            faults += 1
            if len(mem) == frames:
                mem.popitem(last=False)       # evict the LEAST RECENT
            mem[p] = True
    return faults

def optimal_faults(pages, frames):
    mem, faults = [], 0
    for i, p in enumerate(pages):
        if p in mem: continue
        faults += 1
        if len(mem) < frames:
            mem.append(p); continue
        # Evict whichever resident page is needed FURTHEST in the future.
        def next_use(x):
            try:    return pages.index(x, i + 1)
            except ValueError: return float("inf")     # never used again
        mem.remove(max(mem, key=next_use))
        mem.append(p)
    return faults

# BELADY'S ANOMALY, the standard reference string:
ref = [1,2,3,4,1,2,5,1,2,3,4,5]
fifo_faults(ref, 3)      # 9 faults
fifo_faults(ref, 4)      # 10 faults  <- MORE memory, MORE faults
lru_faults(ref, 3), lru_faults(ref, 4)   # 10, 8 - always monotone (stack algorithm)
'''),
          example="Why LRU works at all: locality of reference. A loop touching the same array repeatedly means the recently used pages are exactly the ones about to be used again - so 'least recently used' is a good guess at 'least likely to be needed'. Where that assumption fails (a single sequential scan of a huge file) LRU behaves terribly, which is why databases use scan-resistant policies like LRU-K or ARC.",
          pitfalls="Forgetting that a HIT must update recency in LRU (this is the most common implementation bug); thinking Belady's anomaly applies to LRU; running OPT and claiming it as a real policy; ignoring the dirty bit - evicting a modified page costs a disk write, so real systems prefer a clean victim.",
          followups="'Why does the hardware not implement true LRU?' It would need to update an ordering on every memory access; a single reference bit per page plus the clock hand is a cheap approximation. 'What is thrashing?' Working sets exceeding physical memory, so the system spends all its time paging - detected by the page-fault rate and fixed by reducing the multiprogramming level or adding RAM."),

        Q("cs_fundamentals", "fork(), exec(), and zombie vs orphan processes",
          "How a Unix process is actually created, and the two states that get asked about. fork() DUPLICATES the calling process: the child gets a copy of the address space (copy-on-write in practice, so nothing is physically copied until one side writes), and the call returns TWICE - 0 in the child, the child's pid in the parent. exec() REPLACES the current process image with a new program, keeping the same pid and open file descriptors. Together they explain how a shell runs a command: fork, then in the child exec the program, while the parent waits. The two states. A ZOMBIE is a process that has EXITED but whose parent has not yet called wait() to collect its exit status; the kernel keeps the process table entry alive precisely so the status can be read, so a zombie consumes no memory or CPU - only a table slot. Thousands of them mean a parent that forgets to reap, and they cannot be killed (they are already dead); you kill or fix the PARENT. An ORPHAN is the opposite: the parent died first, so the child is re-parented to init/systemd (pid 1), which reaps it automatically. Orphans are harmless; zombies are a leak. THE PRACTICAL POINT for you: this is why a container running your ML job should have a proper init as pid 1, and why `subprocess` code must wait() on its children.",
          ["os", "process", "fork", "exec", "zombie", "unix", "cs"],
          difficulty="Medium",
          frequency="Frequently asked in OS and systems screens; the zombie-vs-orphan distinction is a classic.",
          mnemonic="fork = copy (returns twice: 0 to the child, pid to the parent). exec = replace (same pid, new program). ZOMBIE = dead child, parent has not reaped it (a table-slot leak; fix the parent). ORPHAN = dead parent, child adopted by init (harmless).",
          code=_c('''
import os, sys, time

pid = os.fork()               # returns TWICE
if pid == 0:
    # ---- child ----
    print("child pid", os.getpid(), "parent", os.getppid())
    os.execvp("echo", ["echo", "replaced by a new program"])
    # Nothing after execvp runs: this process IS echo now (same pid).
else:
    # ---- parent ----
    print("parent pid", os.getpid(), "forked child", pid)
    finished_pid, status = os.wait()          # REAP the child -> no zombie
    print("reaped", finished_pid, "exit code", os.waitstatus_to_exitcode(status))


# Creating a zombie on purpose (what NOT to do):
#   pid = os.fork()
#   if pid == 0: sys._exit(0)       # child exits immediately
#   else: time.sleep(60)            # parent never calls wait()
#   -> `ps` shows the child as <defunct> for those 60 seconds

# Creating an orphan:
#   pid = os.fork()
#   if pid == 0: time.sleep(60)     # child outlives the parent
#   else: sys.exit(0)               # parent exits -> child re-parented to pid 1

# The everyday version - subprocess does fork+exec+wait for you:
import subprocess
result = subprocess.run(["echo", "hello"], capture_output=True, text=True)
# .run() waits internally. Popen() without .wait()/.communicate() leaks zombies.
'''),
          example="A long-running server that spawns a helper per request with Popen and never calls wait() accumulates one zombie per request. Memory looks fine, CPU looks fine, and then after a few days fork() starts failing with EAGAIN because the process table is full - a genuinely confusing production outage with a one-line fix.",
          pitfalls="Believing fork() copies memory eagerly (it is copy-on-write); expecting code after a successful exec() to run; trying to `kill -9` a zombie; forking a multi-threaded process (only the calling thread survives in the child, so a lock held by another thread stays locked forever - this is why fork-based multiprocessing after starting threads is dangerous).",
          followups="'How does copy-on-write work?' Parent and child share the same physical pages marked read-only; the first write traps and the kernel copies just that page. 'Why does Python's multiprocessing default to spawn on macOS and Windows?' Because fork in a threaded or Objective-C runtime is unsafe - spawn starts a fresh interpreter instead, at the cost of re-importing your module."),

        Q("cs_fundamentals", "Handling deadlock: prevention, avoidance, detection - and Banker's algorithm",
          "Given the four necessary conditions (mutual exclusion, hold-and-wait, no preemption, circular wait), there are exactly four strategies, and knowing which one real systems pick is the mark of a good answer. PREVENTION - structurally break one condition. The practical one is breaking CIRCULAR WAIT by imposing a global lock ORDER: everyone acquires locks in the same order (say by id), so a cycle is impossible. Breaking hold-and-wait means grabbing every lock up front (poor concurrency); breaking no-preemption means being able to snatch a resource back (fine for CPU or memory, impossible for a printer or a mutex); mutual exclusion usually cannot be removed at all. AVOIDANCE - allow the conditions but only grant a request if the system stays in a SAFE state, meaning some ordering exists in which every process can finish. That is BANKER'S ALGORITHM: each process declares its maximum need up front, and the banker grants a request only if, after granting, it can still find a sequence that satisfies everyone from the remaining pool. It is O(n^2 * m) per request and requires knowing maximum demands in advance, which is why no real OS uses it - say that explicitly. DETECTION AND RECOVERY - let deadlocks happen, run a wait-for-graph cycle check periodically, and recover by killing or rolling back a victim. This is what DATABASES actually do: a deadlock detector finds the cycle and aborts the cheapest transaction with a deadlock error, expecting the client to retry. THE OSTRICH ALGORITHM - ignore it, which is what general-purpose OS kernels do, because deadlocks are rare and a reboot is cheaper than the machinery.",
          ["os", "deadlock", "bankers-algorithm", "concurrency", "cs", "dbms"],
          difficulty="Hard",
          frequency="Frequently asked; Banker's algorithm is a campus-interview staple and the database-detection answer impresses in industry interviews.",
          mnemonic="Prevention = break a condition (in practice: a global LOCK ORDER). Avoidance = only enter SAFE states (Banker's - needs max demands, too costly, nobody uses it). Detection = find the cycle and kill a victim (what databases do). Ostrich = ignore it (what kernels do).",
          code=_c('''
def is_safe(available, maximum, allocated):
    """Banker's safety check. available: [m], maximum/allocated: [n][m]."""
    n, m = len(maximum), len(available)
    need = [[maximum[i][j] - allocated[i][j] for j in range(m)] for i in range(n)]
    work, finished, order = list(available), [False] * n, []
    progress = True
    while progress:
        progress = False
        for i in range(n):
            # Can process i finish with what is free right now?
            if not finished[i] and all(need[i][j] <= work[j] for j in range(m)):
                for j in range(m):
                    work[j] += allocated[i][j]      # assume it finishes and frees all
                finished[i] = True
                order.append(i)
                progress = True                     # try the others again
    return all(finished), order        # order = a safe execution sequence

def request_ok(available, maximum, allocated, pid, req):
    """Grant only if the system stays SAFE afterwards."""
    m = len(available)
    need = [maximum[pid][j] - allocated[pid][j] for j in range(m)]
    if any(req[j] > need[j] for j in range(m)):  raise ValueError("exceeds declared max")
    if any(req[j] > available[j] for j in range(m)): return False      # must wait
    # Tentatively grant, then test.
    avail2 = [available[j] - req[j] for j in range(m)]
    alloc2 = [row[:] for row in allocated]
    for j in range(m): alloc2[pid][j] += req[j]
    safe, _ = is_safe(avail2, maximum, alloc2)
    return safe                        # False -> roll back and make it wait

# The strategy that actually ships: a global lock ORDER.
def transfer(a, b, amount):
    first, second = (a, b) if a.id < b.id else (b, a)   # ALWAYS the same order
    with first.lock:
        with second.lock:
            a.balance -= amount; b.balance += amount
# Without the sort, transfer(X, Y) and transfer(Y, X) running at once deadlock.
'''),
          example="The bank-transfer deadlock is the one to have ready: thread 1 does transfer(A, B) and locks A then waits for B; thread 2 does transfer(B, A) and locks B then waits for A. Both wait forever. Sorting the two accounts by id before locking makes the cycle impossible, and the fix is one line - which is why lock ordering is the prevention technique that survives contact with real code.",
          pitfalls="Listing the four conditions but not knowing what to DO about them; presenting Banker's as practical; forgetting that detection needs a recovery policy (who gets killed, and does the client retry?); a lock order that is only followed in most places - one violation is enough.",
          followups="'How does a database detect deadlock?' It maintains a wait-for graph of transactions and runs cycle detection periodically (Postgres every deadlock_timeout, default 1s), then aborts the cheapest transaction with a retryable error. 'What is livelock?' Threads keep changing state politely and make no progress - two people stepping aside for each other in a corridor; fix it with randomised backoff."),

        Q("cs_fundamentals", "Paging vs segmentation, and internal vs external fragmentation",
          "Two ways to carve memory, and the fragmentation each causes. PAGING splits both the virtual address space and physical memory into FIXED-SIZE pages (typically 4KB), and a page table maps virtual page numbers to physical frames. Because every block is the same size, any free frame fits any page, so there is NO external fragmentation - but the last page of an allocation is usually partly empty, which is INTERNAL fragmentation (on average half a page wasted per allocation, so about 2KB per region - negligible). SEGMENTATION splits memory into VARIABLE-SIZE, logically meaningful pieces - code, data, stack, heap - which matches how programmers think and makes per-segment protection natural. But variable sizes mean free memory ends up as scattered unusable gaps: you have 100MB free in total but no single 20MB hole, which is EXTERNAL fragmentation, curable only by compaction (expensive) or careful allocation policies. THE MEMORISABLE PAIRING: fixed blocks -> internal fragmentation (waste INSIDE a block); variable blocks -> external fragmentation (waste BETWEEN blocks). Modern x86 uses paging, with segmentation reduced to a vestige. The related idea worth naming is the buddy allocator and slab allocator the kernel uses for its own objects, and the fact that huge pages (2MB) trade more internal fragmentation for far fewer TLB misses - which matters directly to large ML workloads.",
          ["os", "memory", "paging", "segmentation", "fragmentation", "cs"],
          difficulty="Medium",
          frequency="Frequently asked in OS screens and campus interviews.",
          mnemonic="FIXED-size blocks -> INTERNAL fragmentation (waste inside the block). VARIABLE-size blocks -> EXTERNAL fragmentation (unusable gaps between them). Paging = fixed; segmentation = variable. Modern systems page.",
          code=_c('''
PAGE = 4096

def pages_needed(n_bytes):
    return -(-n_bytes // PAGE)                  # ceiling division

def internal_waste(n_bytes):
    """Paging: the tail of the last page is wasted."""
    return pages_needed(n_bytes) * PAGE - n_bytes

internal_waste(1)        # 4095 bytes wasted for a 1-byte allocation
internal_waste(10_000)   # 3 pages = 12288, so 2288 bytes wasted
# On average PAGE/2 per allocation - about 2KB. Tiny, and bounded.


def external_fragmentation(holes, request):
    """Segmentation/variable allocation: plenty free, but no single hole fits."""
    total_free = sum(holes)
    largest = max(holes) if holes else 0
    return {"total_free": total_free, "largest_hole": largest,
            "can_serve": largest >= request, "wasted_by_scatter": total_free - largest}

external_fragmentation([8, 12, 6, 9], request=20)
# total_free 35 MB, largest hole 12 MB -> a 20 MB request FAILS despite 35 free.


# Address translation under paging, by hand (the exam question):
def translate(virtual_addr, page_table, page_size=PAGE):
    vpn, offset = divmod(virtual_addr, page_size)   # split into page # + offset
    frame = page_table[vpn]                          # look up the frame number
    return frame * page_size + offset                # rebuild the physical address

translate(9000, {0: 5, 1: 9, 2: 2})   # vpn 2, offset 808 -> frame 2 -> 8*1024+...
'''),
          example="A 10,000-byte allocation with 4KB pages takes 3 pages (12,288 bytes) and wastes 2,288 - internal fragmentation you can compute exactly. By contrast, a segmented system with free holes of 8, 12, 6 and 9 MB has 35 MB free and still cannot satisfy a 20 MB request - external fragmentation you cannot fix without moving things.",
          pitfalls="Swapping the two definitions (the single most common error); thinking paging eliminates all waste (the page TABLE itself costs memory, which is why multi-level and inverted page tables exist); forgetting that paging enables everything else - swapping, shared memory, copy-on-write, memory-mapped files.",
          followups="'What does the TLB do?' Caches recent virtual-to-physical translations, so a hit avoids walking a multi-level page table; a miss can cost several memory accesses. 'Why do huge pages help ML workloads?' A 2MB page covers 512 times the memory per TLB entry, so a large model's weights stop thrashing the TLB - at the cost of coarser allocation."),

        Q("cs_fundamentals", "Blocking vs non-blocking I/O, and how select/epoll enables 10,000 connections",
          "The question behind 'how does a web server handle many connections?'. BLOCKING I/O - `data = sock.recv(4096)` parks the thread until bytes arrive. Simple to reason about, and the reason the thread-per-connection model exists; the cost is roughly 1MB of stack per thread plus scheduler pressure, so 10,000 connections is 10GB of stacks and a context-switch storm. NON-BLOCKING I/O - the same call returns immediately with EWOULDBLOCK if nothing is ready, so one thread can service many sockets. But polling every socket in a loop is O(n) per pass and wastes CPU, which is where I/O MULTIPLEXING comes in: select/poll/epoll/kqueue let one thread ask the kernel 'which of these thousands of sockets are ready?' and sleep until at least one is. select() is O(n) per call and capped at 1024 descriptors; poll() removes the cap but stays O(n); EPOLL (Linux) and kqueue (BSD) are O(1) in the ready count because the interest set is registered once in the kernel and only ready descriptors are returned - that difference is literally the C10K problem's solution. THE FOURTH OPTION, asynchronous I/O, has the kernel complete the operation and then notify you (io_uring, IOCP). MAP IT TO WHAT YOU USE: Python's asyncio event loop is epoll underneath, node.js is libuv over epoll, and nginx's small fixed worker count beats Apache's thread-per-connection for exactly this reason.",
          ["os", "io", "epoll", "select", "async", "networking", "cs"],
          difficulty="Medium",
          frequency="Commonly asked in backend and systems interviews, and the natural follow-up to any 'how would you scale this server' question.",
          mnemonic="Blocking = one thread waits per connection (simple, heavy). Non-blocking + epoll = one thread watches thousands, kernel reports only the READY ones (O(1), not O(n) like select). asyncio/node/nginx are all this.",
          code=_c('''
import socket, selectors

# BLOCKING, thread-per-connection: fine for 100 clients, fatal at 100,000.
def blocking_server(port):
    import threading
    srv = socket.socket(); srv.bind(("", port)); srv.listen()
    def handle(conn):
        while True:
            data = conn.recv(4096)        # THREAD PARKS HERE until bytes arrive
            if not data: break
            conn.sendall(data)
        conn.close()
    while True:
        conn, _ = srv.accept()
        threading.Thread(target=handle, args=(conn,)).start()   # ~1MB stack each


# NON-BLOCKING + MULTIPLEXING: one thread, thousands of sockets.
# selectors picks the best backend available - epoll on Linux, kqueue on BSD.
def event_loop_server(port):
    sel = selectors.DefaultSelector()
    srv = socket.socket(); srv.bind(("", port)); srv.listen()
    srv.setblocking(False)                       # calls return instead of waiting
    sel.register(srv, selectors.EVENT_READ, data=None)

    while True:
        # ONE syscall returns only the sockets that are actually ready.
        for key, _ in sel.select(timeout=None):
            if key.data is None:                 # the listening socket
                conn, _ = key.fileobj.accept()
                conn.setblocking(False)
                sel.register(conn, selectors.EVENT_READ, data=b"")
            else:                                # a client socket with data
                conn = key.fileobj
                data = conn.recv(4096)           # guaranteed not to block
                if data:
                    conn.sendall(data)
                else:
                    sel.unregister(conn); conn.close()

# Cost comparison at 10,000 idle connections:
#   thread-per-connection : ~10,000 threads, ~10 GB of stacks, heavy switching
#   epoll event loop      : 1 thread, a few MB, the kernel wakes it only on work
'''),
          example="This is the C10K problem and its answer. Apache's classic thread-per-connection model falls over around ten thousand mostly-idle keep-alive connections; nginx handles them in a handful of worker processes because each worker is an epoll loop that is only woken for sockets with actual data.",
          pitfalls="Doing CPU-heavy work inside an event loop, which blocks every other connection (the cardinal asyncio sin - one slow synchronous call stalls thousands of users); assuming non-blocking means faster per request (it is the same speed, it just scales in connection count); forgetting that a non-blocking send can accept only part of your buffer, so you must track the remainder.",
          followups="'Why is asyncio not a magic speed-up?' It is still one thread and one GIL - it wins on concurrency, not on CPU throughput. 'What does io_uring add?' Batched submission and completion via shared ring buffers, so even the syscall overhead per operation largely disappears."),
    ]

    # ── DBMS ──────────────────────────────────────────────────────────────
    entries += [
        Q("cs_fundamentals", "Database keys: super, candidate, primary, composite, foreign, surrogate",
          "Definitions that sound interchangeable and are not. A SUPER KEY is any set of columns that uniquely identifies a row - including wasteful ones like (student_id, name, email). A CANDIDATE KEY is a MINIMAL super key: remove any column and uniqueness breaks. A table can have several candidate keys (student_id, and email, and PPS number). The PRIMARY KEY is the one candidate key you choose; it is unique, never NULL, and in most databases determines the physical clustering of the table. The others become ALTERNATE keys and should still get unique constraints - a very common omission. A COMPOSITE key is a key made of more than one column, e.g. (order_id, line_number) or the (student_id, course_id) pair on an enrolment table. A FOREIGN KEY is a column referencing another table's primary key, and it is what enforces referential integrity: you cannot insert an order for a customer who does not exist, and you must declare what happens on delete (CASCADE, SET NULL or RESTRICT). A SURROGATE key is a meaningless generated id (an auto-increment integer or a UUID) used instead of a NATURAL key made from real data. THE JUDGEMENT QUESTION - which to use - has a clear answer: prefer surrogate keys, because natural keys change (people change email addresses and surnames, and countries reissue identifiers) and a changing primary key has to cascade through every referencing row.",
          ["dbms", "sql", "keys", "primary-key", "foreign-key", "cs"],
          difficulty="Easy",
          frequency="Frequently asked - a guaranteed DBMS screening question and a campus-interview staple.",
          mnemonic="Super = unique (maybe bloated). Candidate = unique AND minimal. Primary = the candidate you picked (unique + NOT NULL). Composite = multi-column. Foreign = points at another table's primary key. Surrogate = a meaningless id, and usually the right choice.",
          code=_c('''
-- Candidate keys here: student_id (surrogate) AND email AND pps_number.
-- We pick one as PRIMARY and enforce the others with UNIQUE.
CREATE TABLE students (
    student_id  BIGSERIAL PRIMARY KEY,           -- surrogate: never changes
    email       TEXT NOT NULL UNIQUE,            -- alternate key
    pps_number  CHAR(9) NOT NULL UNIQUE,         -- alternate key
    full_name   TEXT NOT NULL
);

CREATE TABLE courses (
    course_id   BIGSERIAL PRIMARY KEY,
    code        TEXT NOT NULL UNIQUE,            -- natural key, kept as alternate
    title       TEXT NOT NULL
);

-- COMPOSITE primary key on the join table: a student enrols in a course once.
CREATE TABLE enrolments (
    student_id  BIGINT NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    course_id   BIGINT NOT NULL REFERENCES courses(course_id)  ON DELETE RESTRICT,
    enrolled_on DATE NOT NULL DEFAULT CURRENT_DATE,
    grade       TEXT,                            -- data ABOUT the relationship
    PRIMARY KEY (student_id, course_id)          -- composite, and it doubles as
);                                               -- the uniqueness rule

-- ON DELETE choices, and what they mean in practice:
--   CASCADE  : deleting a student deletes their enrolments (right here)
--   RESTRICT : refuse to delete a course that still has enrolments (right here)
--   SET NULL : keep the row, forget the parent (needs a nullable column)

-- Column ORDER in a composite key matters for the index it creates:
-- PRIMARY KEY (student_id, course_id) makes "all courses for a student" fast
-- and "all students on a course" slow - hence the extra index:
CREATE INDEX idx_enrolments_course ON enrolments(course_id);
'''),
          example="Why surrogate keys win: use email as the primary key of students and every enrolment, payment and log row stores that email. One student changes address and you must update every referencing row inside one transaction - or leave orphans. With a surrogate id, the email column changes in one place and nothing else notices.",
          pitfalls="Confusing candidate with super key (minimality is the whole distinction); forgetting UNIQUE on alternate keys, so duplicates creep in; nullable foreign keys with no ON DELETE policy, leaving orphan rows; assuming a composite primary key gives you a fast index in both directions - it does not, the leading column rules.",
          followups="'UUID or auto-increment?' Auto-increment is compact and index-friendly but leaks volume and needs a central sequence; UUIDv4 is distributable but random, which fragments B-tree inserts - UUIDv7 (time-ordered) is the modern compromise. 'Can a primary key be NULL?' No, by definition; a UNIQUE constraint, by contrast, generally permits NULLs."),

        Q("cs_fundamentals", "SQL JOINs - all of them, with one worked example",
          "Every join answers 'which rows do I keep when there is no match?'. Use one tiny example - employees and departments - and read off each result. INNER JOIN keeps only rows matching on BOTH sides: employees who have a department AND departments that have employees. LEFT (OUTER) JOIN keeps every row from the left table, filling the right side with NULLs when there is no match - this is how you find 'employees with no department', by adding `WHERE d.id IS NULL`. RIGHT JOIN is the mirror image and is rarely used, because you can always swap the tables and write a LEFT join, which reads better. FULL OUTER JOIN keeps unmatched rows from both sides. CROSS JOIN is every combination, n x m rows - occasionally what you want (generating a calendar grid), usually a bug caused by a missing join condition. SELF JOIN is a table joined to itself with aliases, the standard way to walk a hierarchy (employee to manager). THE TWO THINGS INTERVIEWERS TEST. First, the difference between a condition in ON and the same condition in WHERE for an OUTER join: `LEFT JOIN d ON e.dept = d.id AND d.active` keeps unmatched employees, while moving `d.active` to WHERE filters out the NULL rows and silently turns your outer join back into an inner one. Second, that a join between a 1,000-row and a 1,000,000-row table with no index on the join column means a scan per row - so always mention indexing the foreign key.",
          ["dbms", "sql", "joins", "query", "cs"],
          difficulty="Easy",
          frequency="Very commonly asked - SQL joins appear in almost every data-adjacent screen and in SQL live-coding rounds.",
          mnemonic="INNER = matches only. LEFT = all of the left, NULLs on the right. FULL = everything, NULLs both sides. CROSS = every combination. Anti-join = LEFT JOIN plus WHERE right.id IS NULL. In an OUTER join, a filter in WHERE kills the NULL rows - keep it in ON.",
          code=_c('''
-- employees                          departments
-- id | name  | dept_id               id | name
--  1 | Asha  | 10                    10 | Engineering
--  2 | Ben   | 20                    20 | Sales
--  3 | Cara  | NULL                  30 | Legal        (nobody in it)

-- INNER: only matched rows -> Asha/Engineering, Ben/Sales   (2 rows)
SELECT e.name, d.name
FROM employees e
JOIN departments d ON e.dept_id = d.id;

-- LEFT: every employee, NULL department for Cara           (3 rows)
SELECT e.name, d.name AS dept
FROM employees e
LEFT JOIN departments d ON e.dept_id = d.id;

-- ANTI-JOIN: employees with NO department -> Cara           (1 row)
SELECT e.name
FROM employees e
LEFT JOIN departments d ON e.dept_id = d.id
WHERE d.id IS NULL;                      -- the classic "find the orphans" pattern

-- FULL OUTER: everyone AND every department, including Legal (4 rows)
SELECT e.name, d.name
FROM employees e
FULL OUTER JOIN departments d ON e.dept_id = d.id;

-- SELF JOIN: each employee with their manager's name
SELECT e.name AS employee, m.name AS manager
FROM employees e
LEFT JOIN employees m ON e.manager_id = m.id;    -- LEFT so the CEO survives

-- THE TRAP: ON vs WHERE in an outer join.
SELECT e.name, d.name
FROM employees e
LEFT JOIN departments d ON e.dept_id = d.id AND d.active = true;   -- 3 rows
-- versus
SELECT e.name, d.name
FROM employees e
LEFT JOIN departments d ON e.dept_id = d.id
WHERE d.active = true;              -- 0-2 rows: NULL rows fail the WHERE, so
                                    -- this is an INNER join wearing a disguise

-- Always index the join column, or every left row triggers a scan:
CREATE INDEX idx_employees_dept ON employees(dept_id);
'''),
          example="Counting employees per department including empty ones needs `SELECT d.name, COUNT(e.id) FROM departments d LEFT JOIN employees e ON e.dept_id = d.id GROUP BY d.name`. Note COUNT(e.id) not COUNT(*) - COUNT(*) counts the NULL-filled row and reports Legal as having 1 employee, which is the single most common bug in this query.",
          examples=[
              "Row counts on the same tiny data, so the joins stop being abstract. Employees: Asha(dept 10), Ben(dept 20), Cara(dept NULL). Departments: 10 Engineering, 20 Sales, 30 Legal (empty). INNER gives 2 rows (Cara and Legal both vanish). LEFT gives 3 (Cara appears with a NULL department). RIGHT gives 3 (Legal appears with a NULL employee). FULL OUTER gives 4 (everyone and everything). CROSS gives 3 x 3 = 9. Quote those five numbers and you have answered the question completely.",
              "The COUNT(*) bug, which is the single most common LEFT JOIN mistake. `SELECT d.name, COUNT(*) FROM departments d LEFT JOIN employees e ON e.dept_id = d.id GROUP BY d.name` reports Legal as having 1 employee - because the NULL-filled row is still a row, and COUNT(*) counts rows. COUNT(e.id) counts non-NULL values of that column and correctly reports 0. The rule: with an outer join, always count a column from the OPTIONAL side, never *.",
              "ON versus WHERE, which silently converts your join. `LEFT JOIN departments d ON e.dept_id = d.id AND d.active = true` keeps all three employees, with d columns NULL where the department is inactive or missing. Move `d.active = true` into WHERE and the NULL rows fail the predicate (NULL = true is not true), so they are filtered out and you have an INNER join wearing a LEFT join's clothing. Same tables, same intent, different result - and no error to warn you.",
              "The anti-join, which is the pattern worth memorising. 'Find customers who have never ordered' is `LEFT JOIN orders o ON o.customer_id = c.id WHERE o.id IS NULL`: join everything, then keep only the rows where the right side failed to match. The tempting alternative `WHERE c.id NOT IN (SELECT customer_id FROM orders)` has a nasty trap - if that subquery returns even one NULL, the entire NOT IN evaluates to NULL and you get ZERO rows back, silently. Use NOT EXISTS or the LEFT JOIN form.",
              "Self join, and why it needs LEFT. 'Each employee with their manager's name' is the same table twice with aliases: `FROM employees e LEFT JOIN employees m ON e.manager_id = m.id`. Use an INNER join and the CEO - whose manager_id is NULL - disappears from the report entirely, which is the kind of bug that survives review because the output looks plausible. Any hierarchy walk (employee/manager, category/parent, comment/reply) is this shape.",
              "The cartesian explosion, quantified. Forget the ON clause between a 10,000-row and a 5,000-row table and you get 50 million rows - the query does not error, it just runs for minutes and may exhaust memory. Related and subtler: joining on a NON-UNIQUE column multiplies rows. If a customer has 3 orders and each order has 4 lines, joining customers to orders to lines gives 12 rows per customer, so SUM(customer.credit_limit) is now triple-counted. Aggregate before joining, or count DISTINCT.",
          ],
          pitfalls="COUNT(*) with a LEFT JOIN, which counts non-existent rows; putting the right table's filter in WHERE and unknowingly getting an inner join; a missing join condition producing a cartesian explosion; joining on a nullable column and being surprised that NULL never equals NULL.",
          followups="'How does the database actually execute a join?' Nested loop (good for small outer plus an index), hash join (good for big unsorted inputs, builds a hash table on the smaller side), or merge join (good when both inputs are already sorted). 'Why is my join slow?' Read the EXPLAIN plan - almost always a missing index on the join key, or a type mismatch preventing index use."),

        Q("cs_fundamentals", "Normalisation worked: taking one messy table to 3NF (and when to stop)",
          "Do not recite the forms - normalise a table live, which is what the interviewer actually asks for. START with an unnormalised orders table: order_id, customer_name, customer_email, product_ids ('P1,P2'), product_names, quantity, unit_price, supplier, supplier_phone. 1NF - no repeating groups, every cell atomic. The comma-separated product list must become one row per product, giving an order_lines table. 2NF - 1NF plus no PARTIAL dependency on part of a composite key. In order_lines the key is (order_id, product_id), but product_name depends only on product_id, so it moves to a products table. 3NF - 2NF plus no TRANSITIVE dependency: supplier_phone depends on supplier, which depends on product_id, so supplier moves to its own table. BCNF tightens 3NF for the rare case where a non-key column determines part of a key. THE ANSWER THAT SCORES, though, is knowing when to STOP. Normalisation removes update anomalies - with the supplier phone stored on every order line, changing it means updating a million rows and any one you miss is a contradiction - but it costs joins on every read. So you normalise the WRITE path (the source of truth) and deliberately denormalise the READ path: materialised views, a reporting star schema, a cached order_summary. Saying 'normalise until it hurts, denormalise until it works, and let the read path be a derived copy you can always rebuild' is the senior answer.",
          ["dbms", "normalization", "sql", "schema-design", "cs"],
          difficulty="Medium",
          frequency="Very commonly asked - normalisation is on every DBMS syllabus and every screening list.",
          mnemonic="1NF: atomic cells, no repeating groups. 2NF: no dependency on PART of a composite key. 3NF: no dependency on a NON-key column. In one line - every non-key column depends on the key, the whole key, and nothing but the key.",
          code=_c('''
-- ── BEFORE: one table, every anomaly ────────────────────────────────────
-- orders(order_id, customer_name, customer_email,
--        product_ids '"P1,P2"', product_names, qty, unit_price,
--        supplier, supplier_phone)
--
-- UPDATE anomaly : the supplier changes phone number -> update a million rows
-- INSERT anomaly : cannot record a new product until somebody orders it
-- DELETE anomaly : deleting the last order for a product erases the product

-- ── 1NF: atomic values, one row per product ─────────────────────────────
-- Split the comma-separated list into order_lines.

-- ── 2NF: remove partial dependencies on the composite key ───────────────
-- Key of order_lines is (order_id, product_id); product_name depends on
-- product_id ALONE, so it belongs in products.

-- ── 3NF: remove transitive dependencies ─────────────────────────────────
-- supplier_phone depends on supplier, not on the key -> its own table.

CREATE TABLE customers (
    customer_id BIGSERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    email       TEXT NOT NULL UNIQUE
);

CREATE TABLE suppliers (
    supplier_id BIGSERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    phone       TEXT                       -- lives in exactly ONE row now
);

CREATE TABLE products (
    product_id  BIGSERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    supplier_id BIGINT REFERENCES suppliers(supplier_id)
);

CREATE TABLE orders (
    order_id    BIGSERIAL PRIMARY KEY,
    customer_id BIGINT NOT NULL REFERENCES customers(customer_id),
    placed_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE order_lines (
    order_id    BIGINT NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    product_id  BIGINT NOT NULL REFERENCES products(product_id),
    qty         INT NOT NULL CHECK (qty > 0),
    unit_price  BIGINT NOT NULL,          -- SNAPSHOT in cents: history must not
    PRIMARY KEY (order_id, product_id)    -- change when the price changes
);

-- ── DELIBERATE denormalisation for the read path ────────────────────────
-- Five joins per dashboard load is fine at 1k orders and not at 100M. Keep a
-- derived copy that can always be rebuilt from the tables above.
CREATE MATERIALIZED VIEW order_summary AS
SELECT o.order_id, c.name AS customer,
       SUM(l.qty * l.unit_price) AS total_cents,
       COUNT(*) AS line_count
FROM orders o
JOIN customers c   ON c.customer_id = o.customer_id
JOIN order_lines l ON l.order_id = o.order_id
GROUP BY o.order_id, c.name;
'''),
          example="Note that unit_price stays on order_lines even though it looks like a duplicate of products.price. That is not a normalisation failure - the order line records what the customer ACTUALLY PAID, a historical fact, while products.price is the current price. Knowing which duplicates are redundancy and which are history is exactly the judgement being tested.",
          examples=[
              "The three anomalies, made concrete on the unnormalised table. UPDATE: the supplier changes phone number, and because it is repeated on every order line you must update a million rows - miss any and the database now contradicts itself about one supplier's number. INSERT: you cannot record a new product until somebody orders it, because the only place a product name lives is an order line. DELETE: cancelling the last order for a product erases the product from the database entirely. All three vanish once the fact lives in exactly one row, which is the whole point of normalisation.",
              "Walking 1NF live, which is what you will be asked to do. The column product_ids holding 'P1,P2' fails 1NF because the cell is not atomic - you cannot join on it, index it, or count products without string parsing. Splitting it gives one row per (order, product), which is the order_lines table. The tell that a table is not in 1NF: any column you would have to call split() on, any column named something_list, or a table with columns phone1, phone2, phone3.",
              "2NF, and why it only matters with a COMPOSITE key. The key of order_lines is (order_id, product_id). product_name depends on product_id ALONE - half the key - so it is a partial dependency and belongs in a products table. If your table has a single-column key, it is automatically in 2NF once it is in 1NF, which is worth saying because it shows you know what the rule is actually about rather than reciting it.",
              "3NF, with the transitive chain spelled out. order_line -> product_id -> supplier -> supplier_phone. supplier_phone does not depend on the key; it depends on supplier, which depends on the key. That indirection is the transitive dependency, and it is what forces the suppliers table. The memorable one-liner covering all three forms: every non-key column depends on the key, the whole key, and nothing but the key.",
              "The duplicate that is NOT a normalisation failure - which is the judgement half. order_lines keeps unit_price even though products.price exists. That looks like redundancy and is not: products.price is the CURRENT price, while order_lines.unit_price is what the customer actually paid, a historical fact that must never change when the price list does. Same for the shipping address copied onto the order rather than referenced from the customer. Knowing which duplicates are redundancy and which are history is exactly what separates a schema that survives an audit from one that quietly rewrites the past.",
              "When to stop, and the answer that reads as experience. Five joins to render a dashboard is fine at 1,000 orders and not at 100 million. So normalise the WRITE path - the source of truth, where integrity matters - and deliberately denormalise the READ path with a materialised view, a star schema or a cached summary table you can always rebuild from the normalised tables. 'Normalise until it hurts, denormalise until it works, and keep the read copy derivable' is the sentence to land, because it shows normalisation is a tool with a cost rather than a rule to obey.",
          ],
          pitfalls="Normalising away historical snapshots (prices, addresses, names on invoices); stopping at 1NF and calling it normalised; normalising an analytics warehouse, where a star schema with wide denormalised dimensions is correct; forgetting that every split adds a join, and joins are the cost you are buying integrity with.",
          followups="'What is denormalisation and when is it right?' Duplicating data to avoid joins, right when reads massively outnumber writes and you can rebuild the copy - counters, materialised views, search indexes. 'What is BCNF?' A stricter 3NF for tables with overlapping candidate keys; rare in practice, but know that 3NF does not always eliminate every anomaly."),

        Q("cs_fundamentals", "Transaction isolation levels and the anomalies they prevent",
          "Isolation is the I in ACID and it is a DIAL, not a switch: stronger isolation means fewer surprises and less concurrency. Learn the three anomalies first, because the levels are defined by which ones they allow. DIRTY READ - you read a row another transaction has modified but not committed; if it rolls back, you acted on data that never existed. NON-REPEATABLE READ - you read the same ROW twice in one transaction and get different values because someone committed in between. PHANTOM READ - you run the same QUERY twice and get different ROWS because someone inserted a row matching your WHERE clause. Now the levels. READ UNCOMMITTED allows all three (essentially unused). READ COMMITTED prevents dirty reads only - each statement sees a fresh snapshot of committed data; this is the default in Postgres and Oracle and is what most applications run on. REPEATABLE READ additionally prevents non-repeatable reads by pinning a snapshot for the whole transaction; MySQL's InnoDB default, and Postgres's implementation also prevents phantoms in practice. SERIALIZABLE behaves as if transactions ran one after another - no anomalies, at the cost of aborts or blocking. THE PRACTICAL POINT to raise: application code frequently has a LOST UPDATE bug that no isolation level below serializable prevents - read balance, compute new balance, write it, while someone else did the same. The fix is not a stronger level but an atomic statement (`UPDATE accounts SET balance = balance - 100 WHERE ...`), SELECT FOR UPDATE, or an optimistic version column.",
          ["dbms", "transactions", "isolation", "acid", "concurrency", "cs"],
          difficulty="Hard",
          frequency="Frequently asked in backend interviews; the lost-update follow-up separates strong candidates.",
          mnemonic="Dirty read = saw uncommitted data. Non-repeatable = same ROW changed. Phantom = new ROWS appeared. READ COMMITTED stops dirty; REPEATABLE READ stops non-repeatable; SERIALIZABLE stops phantoms too. Lost update needs an atomic UPDATE, not a stronger level.",
          code=_c('''
-- LOST UPDATE: the bug that survives READ COMMITTED and REPEATABLE READ.
-- Two transfers of 100 from an account holding 1000.

-- T1                                    T2
BEGIN;                                   BEGIN;
SELECT balance FROM accounts             SELECT balance FROM accounts
  WHERE id = 1;        -- 1000             WHERE id = 1;        -- 1000
                                         UPDATE accounts SET balance = 900
                                           WHERE id = 1;
                                         COMMIT;
UPDATE accounts SET balance = 900        -- T1 overwrites with its stale value
  WHERE id = 1;
COMMIT;
-- Result: 900. Two withdrawals of 100 from 1000 should leave 800. One is LOST.

-- FIX 1 - make it one atomic statement (best, no locks held by you):
UPDATE accounts SET balance = balance - 100
 WHERE id = 1 AND balance >= 100;        -- check the affected row count!

-- FIX 2 - pessimistic lock; other readers of this row block until you commit:
BEGIN;
SELECT balance FROM accounts WHERE id = 1 FOR UPDATE;
UPDATE accounts SET balance = 900 WHERE id = 1;
COMMIT;

-- FIX 3 - optimistic: a version column, and the loser retries.
UPDATE accounts SET balance = 900, version = version + 1
 WHERE id = 1 AND version = 7;           -- 0 rows updated => somebody beat us

-- PHANTOM READ, for contrast:
BEGIN;  -- REPEATABLE READ
SELECT COUNT(*) FROM orders WHERE total > 100;   -- 42
-- (another transaction INSERTs a matching order and commits)
SELECT COUNT(*) FROM orders WHERE total > 100;   -- 43 under some engines
COMMIT;
'''),
          example="A seat-booking check under READ COMMITTED: 'SELECT count of booked seats' says 99 of 100, so you insert a booking. Another transaction did exactly the same thing between your read and your write, and you have sold seat 101. No isolation level below serializable stops it - you need a unique constraint on (show_id, seat_id) so the database refuses the second insert, which is the real production answer.",
          pitfalls="Assuming SERIALIZABLE is free (it causes serialization failures your code must catch and retry); thinking a stronger level fixes lost updates; not knowing your engine's default (Postgres READ COMMITTED, MySQL REPEATABLE READ) - the same code behaves differently; holding a transaction open across a network call, so locks live for seconds.",
          followups="'How does MVCC avoid readers blocking writers?' Each transaction sees a snapshot built from row versions, so readers never take locks and writers never block them - the reason Postgres and InnoDB scale reads well. 'What must the application do under SERIALIZABLE?' Catch serialization failures and retry the whole transaction; it is the price of the guarantee."),

        Q("cs_fundamentals", "SQL: WHERE vs GROUP BY vs HAVING, and window functions",
          "The single most useful SQL fact is the LOGICAL ORDER OF EVALUATION, because it explains every confusing error message: FROM and JOIN first, then WHERE, then GROUP BY, then HAVING, then SELECT, then ORDER BY, then LIMIT. Two consequences you should say out loud. First, WHERE filters ROWS BEFORE grouping and cannot use an aggregate (the groups do not exist yet); HAVING filters GROUPS AFTER aggregation and is where `HAVING COUNT(*) > 5` belongs. Filter as much as possible in WHERE, because it shrinks the input to the grouping. Second, SELECT runs after GROUP BY, which is why you cannot reference a SELECT alias in WHERE, and why every non-aggregated selected column must appear in GROUP BY. WINDOW FUNCTIONS are the other half of this topic and are what a data-adjacent interview really probes: they compute across a set of rows RELATED to the current row while KEEPING every row, unlike GROUP BY which collapses them. `ROW_NUMBER() OVER (PARTITION BY dept ORDER BY salary DESC)` numbers employees within each department, so filtering to rn <= 3 gives the top 3 per group - a query that is genuinely awkward without windows. RANK skips numbers after ties, DENSE_RANK does not, and ROW_NUMBER never ties; that distinction is a favourite question. LAG/LEAD reach at the previous or next row, which is how you compute day-over-day change in one pass.",
          ["dbms", "sql", "group-by", "having", "window-functions", "cs"],
          difficulty="Medium",
          frequency="Very commonly asked - SQL rounds at Amazon and any data-facing team lean heavily on windows.",
          mnemonic="Order of evaluation: FROM -> WHERE -> GROUP BY -> HAVING -> SELECT -> ORDER BY -> LIMIT. WHERE filters ROWS before grouping; HAVING filters GROUPS after. Windows aggregate WITHOUT collapsing rows. ROW_NUMBER never ties, RANK skips, DENSE_RANK does not.",
          code=_c('''
-- WHERE vs HAVING: both appear, and each does its own job.
SELECT department, COUNT(*) AS headcount, AVG(salary) AS avg_salary
FROM employees
WHERE hired_on >= '2020-01-01'      -- filters ROWS first (cheap, shrinks input)
GROUP BY department
HAVING COUNT(*) > 5                 -- filters GROUPS after aggregation
ORDER BY avg_salary DESC;

-- This FAILS: aggregates do not exist yet when WHERE runs.
-- SELECT department FROM employees WHERE COUNT(*) > 5 GROUP BY department;

-- ── Window functions: aggregate WITHOUT collapsing rows ─────────────────

-- Every employee, with their department average alongside (rows preserved).
SELECT name, department, salary,
       AVG(salary) OVER (PARTITION BY department) AS dept_avg,
       salary - AVG(salary) OVER (PARTITION BY department) AS diff_from_avg
FROM employees;

-- TOP-N PER GROUP - the classic interview query.
SELECT * FROM (
    SELECT name, department, salary,
           ROW_NUMBER() OVER (PARTITION BY department
                              ORDER BY salary DESC) AS rn
    FROM employees
) t
WHERE rn <= 3;                      -- top 3 earners in each department

-- RANK vs DENSE_RANK vs ROW_NUMBER on salaries 100, 90, 90, 80:
--   ROW_NUMBER : 1, 2, 3, 4     (never ties)
--   RANK       : 1, 2, 2, 4     (ties share, then SKIP)
--   DENSE_RANK : 1, 2, 2, 3     (ties share, no gap)

-- LAG/LEAD: day-over-day change without a self-join.
SELECT day, revenue,
       LAG(revenue) OVER (ORDER BY day) AS prev_day,
       revenue - LAG(revenue) OVER (ORDER BY day) AS delta
FROM daily_sales;

-- Running total with an explicit frame.
SELECT day, revenue,
       SUM(revenue) OVER (ORDER BY day
                          ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running
FROM daily_sales;
'''),
          example="'Second highest salary per department' is the standard trap. With DENSE_RANK you get the second distinct salary level even when two people tie for first; with ROW_NUMBER you get whoever happens to be second in the ordering. Ask which the interviewer means - that clarification is itself part of the answer.",
          examples=[
              "The evaluation order explains every confusing error. FROM/JOIN -> WHERE -> GROUP BY -> HAVING -> SELECT -> ORDER BY -> LIMIT. So: `WHERE COUNT(*) > 5` fails because the groups do not exist yet when WHERE runs. `SELECT salary * 12 AS annual ... WHERE annual > 50000` fails because SELECT has not run when WHERE does (but `ORDER BY annual` works, because ORDER BY comes after SELECT). Memorise the order and you stop guessing at error messages.",
              "WHERE versus HAVING, both doing their own job in one query. `WHERE hired_on >= '2020-01-01'` drops rows BEFORE grouping - cheap, and it shrinks what has to be aggregated. `HAVING COUNT(*) > 5` drops whole GROUPS after aggregation. Both belong in the same query and they are not interchangeable: moving the date filter into HAVING would aggregate every row first and then discard, doing strictly more work for the same answer.",
              "What a window function buys you that GROUP BY cannot. `AVG(salary) OVER (PARTITION BY department)` puts the department average on EVERY employee row, so you can compute each person's difference from their department's mean in one pass. GROUP BY would collapse the rows and you would need a self-join to get back to per-employee detail. The one-line distinction: GROUP BY collapses, OVER does not.",
              "Top-N per group, the query worth memorising cold. Wrap ROW_NUMBER() OVER (PARTITION BY department ORDER BY salary DESC) in a subquery and filter rn <= 3. It must be a subquery because window functions run AFTER HAVING and cannot appear in WHERE - trying `WHERE ROW_NUMBER() OVER (...) <= 3` is a syntax error, and knowing why is the evaluation order again.",
              "RANK vs DENSE_RANK vs ROW_NUMBER on salaries 100, 90, 90, 80. ROW_NUMBER: 1,2,3,4 - never ties, so it picks an arbitrary winner between the two 90s. RANK: 1,2,2,4 - ties share, then SKIP. DENSE_RANK: 1,2,2,3 - ties share, no gap. For 'the second highest salary' this is the whole question: DENSE_RANK gives the second distinct salary LEVEL, ROW_NUMBER gives whoever happens to be second in the ordering. Ask the interviewer which they mean; the clarification is part of the answer.",
              "LAG and LEAD, which replace an awkward self-join. `revenue - LAG(revenue) OVER (ORDER BY day)` gives day-over-day change in one pass, with NULL on the first row (guard the percentage with NULLIF to avoid dividing by zero). The same idea powers running totals with an explicit frame - `SUM(revenue) OVER (ORDER BY day ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)` - and gaps-and-islands streak detection. Any question phrased as 'compared to the previous' is a LAG question.",
          ],
          pitfalls="Aggregates in WHERE; selecting a column that is neither grouped nor aggregated (MySQL historically allowed it and returned an arbitrary value - a genuine source of wrong reports); forgetting that COUNT(column) skips NULLs while COUNT(*) does not; omitting ORDER BY inside a window when the function needs one; assuming a window function can be used in WHERE - it cannot, wrap it in a subquery.",
          followups="'Solve top-N per group without window functions' - a correlated subquery counting how many rows in the same group score higher; correct, and much slower. 'Where do window functions run?' After HAVING and before ORDER BY, which is exactly why you must nest them in a subquery to filter on them."),

        Q("cs_fundamentals", "The SQL queries you will actually be asked to write",
          "A handful of patterns cover most live SQL rounds, and each has a trap. SECOND-HIGHEST SALARY - the naive `MAX(salary) WHERE salary < MAX(salary)` works but breaks on ties and does not generalise; DENSE_RANK is the answer that scales to Nth, and you must handle 'what if there is no second salary?' (return NULL, which `SELECT MAX(...)` does naturally and `LIMIT 1 OFFSET 1` does not - it returns no row). FIND DUPLICATES - GROUP BY the columns that should be unique and HAVING COUNT(*) > 1; the follow-up is DELETING duplicates while keeping one, which needs ROW_NUMBER over a partition. TOP-N PER GROUP - a window function, as above. RUNNING TOTAL - a window SUM with a frame. SELF-JOIN FOR HIERARCHY - employees to managers, with a LEFT join so the CEO survives. GAPS AND ISLANDS (consecutive days a user was active) - the classic trick of subtracting ROW_NUMBER from the date, which makes consecutive runs share a constant. PIVOT - conditional aggregation with `SUM(CASE WHEN ... THEN 1 ELSE 0 END)`, which is far more portable than any PIVOT syntax. Practise saying the plan before typing: 'group by the pair, keep groups with count above one' is what the interviewer wants to hear first.",
          ["dbms", "sql", "queries", "interview", "cs", "coding"],
          difficulty="Medium",
          frequency="Very commonly asked - Amazon and most data-adjacent teams run a live SQL round.",
          mnemonic="Duplicates = GROUP BY + HAVING COUNT(*) > 1. Nth highest = DENSE_RANK. Top-N per group = ROW_NUMBER in a subquery. Consecutive runs = date minus ROW_NUMBER is constant. Pivot = SUM(CASE WHEN ...).",
          code=_c('''
-- 1. Nth highest salary (handles ties, returns NULL when it does not exist)
SELECT MAX(salary) AS second_highest
FROM employees
WHERE salary < (SELECT MAX(salary) FROM employees);

-- generalised, and the version to prefer:
SELECT DISTINCT salary FROM (
    SELECT salary, DENSE_RANK() OVER (ORDER BY salary DESC) AS r
    FROM employees
) t WHERE r = 2;

-- 2. Find duplicate emails
SELECT email, COUNT(*) AS n
FROM users
GROUP BY email
HAVING COUNT(*) > 1;

-- 3. DELETE duplicates, keeping the earliest row per email
DELETE FROM users WHERE id IN (
    SELECT id FROM (
        SELECT id, ROW_NUMBER() OVER (PARTITION BY email ORDER BY id) AS rn
        FROM users
    ) t WHERE rn > 1                    -- keep rn = 1, delete the rest
);

-- 4. Customers who have never ordered (anti-join; NOT IN breaks on NULLs)
SELECT c.name
FROM customers c
LEFT JOIN orders o ON o.customer_id = c.id
WHERE o.id IS NULL;

-- 5. Running total and month-over-month growth
SELECT month, revenue,
       SUM(revenue) OVER (ORDER BY month) AS cumulative,
       ROUND(100.0 * (revenue - LAG(revenue) OVER (ORDER BY month))
             / NULLIF(LAG(revenue) OVER (ORDER BY month), 0), 1) AS pct_change
FROM monthly_revenue;                  -- NULLIF guards against divide-by-zero

-- 6. GAPS AND ISLANDS: longest streak of consecutive active days per user.
-- Trick: for consecutive dates, (date - row_number) is CONSTANT within a run.
WITH marked AS (
    SELECT user_id, day,
           day - (ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY day))::int
             AS streak_key
    FROM activity
)
SELECT user_id, COUNT(*) AS streak_length, MIN(day) AS started
FROM marked
GROUP BY user_id, streak_key
ORDER BY streak_length DESC;

-- 7. PIVOT by conditional aggregation (portable everywhere)
SELECT department,
       SUM(CASE WHEN status = 'active'  THEN 1 ELSE 0 END) AS active,
       SUM(CASE WHEN status = 'on_leave' THEN 1 ELSE 0 END) AS on_leave
FROM employees
GROUP BY department;
'''),
          example="The gaps-and-islands trick is worth internalising: for days 1,2,3 the row numbers are 1,2,3 so day - rn is 0,0,0; skip to day 7 and rn 4 gives 3. Every consecutive run shares one constant, so grouping by it groups the runs. It looks like magic and is two lines.",
          examples=[
              "Second-highest salary, and why the obvious version is fragile. `SELECT MAX(salary) WHERE salary < (SELECT MAX(salary))` works and returns NULL cleanly when there is no second salary - which is the required behaviour. `LIMIT 1 OFFSET 1` returns NO ROW instead of NULL, a different result the test suite will catch, and it also breaks on ties (two people on the top salary make the OFFSET land on the top salary again). DENSE_RANK generalises to Nth and handles ties correctly, so lead with the subquery for two and DENSE_RANK for N.",
              "The NOT IN trap, which is the nastiest bug in this set. `WHERE c.id NOT IN (SELECT customer_id FROM orders)` returns ZERO ROWS - not an error - if that subquery contains even one NULL, because `id NOT IN (1, 2, NULL)` evaluates to NULL rather than true. It silently returns nothing and looks like 'no customers match'. Use NOT EXISTS or the LEFT JOIN ... WHERE right.id IS NULL form, both of which handle NULLs correctly.",
              "Deleting duplicates while keeping one - the follow-up to finding them. Finding is GROUP BY email HAVING COUNT(*) > 1. Deleting needs ROW_NUMBER() OVER (PARTITION BY email ORDER BY id) in a subquery, then delete where rn > 1. The ORDER BY inside the window is doing real work: it decides WHICH copy survives (earliest id here). Omit it and the survivor is arbitrary, so re-running the query can delete a different row each time - non-deterministic destruction, which is the kind of thing that ends up in a post-mortem.",
              "Gaps and islands, which looks like magic and is two lines. For consecutive dates, (day - ROW_NUMBER() OVER (PARTITION BY user ORDER BY day)) is CONSTANT within a run: days 1,2,3 with row numbers 1,2,3 give 0,0,0; skip to day 7 with row number 4 gives 3. So grouping by that difference groups the streaks, and COUNT(*) per group is the streak length. Any 'longest consecutive' question - login streaks, consecutive wins, uninterrupted uptime - is this trick.",
              "Pivoting by conditional aggregation, which is portable everywhere. `SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) AS active` beats any vendor PIVOT syntax because it works on Postgres, MySQL, SQLite and BigQuery unchanged, and it extends to sums and averages, not just counts. It is also the standard way to build a cohort table, so it is worth having in your fingers.",
              "Two arithmetic traps that produce plausible wrong numbers. Integer division: `100 * count_a / count_b` in a database with integer division returns 0 for anything under 100% - write 100.0 to force float. And divide-by-zero on a percentage-change calculation kills the whole query, so wrap the denominator in NULLIF(x, 0), which turns the error into a NULL you can display as a dash. Both bugs return something rather than failing loudly, which is why they survive review.",
          ],
          pitfalls="`NOT IN (SELECT ...)` where the subquery can return NULL - the whole predicate becomes NULL and you get zero rows, a genuinely nasty bug; LIMIT 1 OFFSET 1 for second-highest, which returns no row instead of NULL and mishandles ties; deleting duplicates without a deterministic tie-break; integer division producing 0 for a percentage (multiply by 100.0).",
          followups="'Now do it without window functions' - correlated subqueries, and be ready to say why they are slower. 'How would you find the median?' PERCENTILE_CONT(0.5) where supported, otherwise ROW_NUMBER from both ends and average the middle one or two."),

        Q("cs_fundamentals", "Reading a query plan and fixing a slow query",
          "'This query is slow, what do you do?' is a real interview question and it has a method, not a guess. STEP 1 - measure, do not speculate: run EXPLAIN ANALYZE and read the plan bottom-up, because the leaves execute first. STEP 2 - find the expensive node. The numbers that matter are the estimated versus ACTUAL row counts (a large gap means stale statistics, so the planner chose a bad strategy - run ANALYZE), and the actual time on each node. STEP 3 - recognise the usual culprits. A SEQ SCAN on a big table filtered to a few rows means a missing index. A NESTED LOOP whose inner side runs a million times means the join column is unindexed or the estimate was wrong. A SORT that spills to disk means work_mem is too small or you are sorting more than you need. A FILTER applied after the scan rather than as an INDEX COND means your predicate is not sargable - wrapping a column in a function (`WHERE YEAR(created_at) = 2024`) disables the index, and rewriting it as a range (`created_at >= '2024-01-01' AND < '2025-01-01'`) restores it. STEP 4 - the fixes, in order of preference: add or fix an index (including a composite one in the right column order, and a covering index so the query never touches the table), rewrite the query (avoid SELECT *, push filters down, replace a correlated subquery with a join), then only afterwards consider denormalising or caching. THE N+1 PROBLEM deserves its own mention because ORMs cause it constantly: one query for the list, then one per row for a relation, so 1,000 rows means 1,001 round trips - fixed by eager loading or a single join.",
          ["dbms", "sql", "performance", "query-plan", "indexing", "cs"],
          difficulty="Medium",
          frequency="Commonly asked in backend and data-engineering interviews; the N+1 question is near-universal.",
          mnemonic="EXPLAIN ANALYZE, read bottom-up. Estimated vs actual rows way off -> stale stats. Seq scan on a big filtered table -> missing index. Function on the column -> index disabled. And check for N+1 before anything else.",
          code=_c('''
-- Suppose this takes 4 seconds:
EXPLAIN ANALYZE
SELECT o.id, o.total, c.name
FROM orders o
JOIN customers c ON c.id = o.customer_id
WHERE o.status = 'pending'
  AND o.created_at >= now() - interval '7 days'
ORDER BY o.created_at DESC
LIMIT 50;

-- A plan that tells you exactly what is wrong:
--  Limit  (actual time=3980..3980 rows=50)
--    ->  Sort  (actual rows=180000)  Sort Method: external merge  Disk: 24MB
--          ->  Hash Join  (actual rows=180000)
--                ->  Seq Scan on orders  (cost estimated rows=1200
--                                         ACTUAL rows=180000)      <-- both flags
--                      Filter: status = 'pending' AND created_at >= ...
--                      Rows Removed by Filter: 9,820,000            <-- reading 10M
--
-- Diagnosis: sequential scan over 10M rows, estimate off by 150x, sort spilling.

-- FIX 1: a composite index matching the filter AND the sort order.
CREATE INDEX idx_orders_status_created
    ON orders (status, created_at DESC);
-- Column order matters: equality columns first, then the range/sort column.
-- The planner can now seek to status='pending' and walk created_at backwards,
-- reading 50 rows and skipping the sort entirely.

-- FIX 2: covering index - answer the query from the index, never touch the heap.
CREATE INDEX idx_orders_covering
    ON orders (status, created_at DESC) INCLUDE (id, total, customer_id);

-- FIX 3: refresh the statistics that misled the planner.
ANALYZE orders;

-- ── NOT SARGABLE: these silently disable an index ───────────────────────
WHERE YEAR(created_at) = 2024                 -- function on the column: BAD
WHERE created_at >= '2024-01-01'
  AND created_at <  '2025-01-01'              -- range on the raw column: GOOD

WHERE customer_id::text = '42'                -- cast on the column: BAD
WHERE customer_id = 42                        -- GOOD

WHERE name LIKE '%smith'                      -- leading wildcard: no B-tree help
WHERE name LIKE 'smith%'                      -- prefix: index works

-- ── N+1, the ORM classic ────────────────────────────────────────────────
-- for order in Order.objects.all():        # 1 query
--     print(order.customer.name)           # + 1 query PER ORDER = 1001 queries
-- Fix: Order.objects.select_related("customer")   # ONE join, one round trip
'''),
          example="The composite index column order is the detail people miss: for `WHERE status = 'pending' ORDER BY created_at DESC`, an index on (status, created_at) lets the database seek to the status and read rows already in date order, so LIMIT 50 stops after 50 rows. An index on (created_at, status) cannot - it must scan dates and test status on each. Same two columns, completely different plan.",
          pitfalls="Adding an index per column instead of one composite index in the right order; indexing everything (every index slows writes and consumes memory); optimising without EXPLAIN; ignoring that a LIMIT with an ORDER BY still sorts everything unless the index provides the order; forgetting that an index on a low-cardinality column (a boolean) is rarely worth it.",
          followups="'When is a sequential scan the RIGHT plan?' When you are reading a large fraction of the table - random index lookups would be slower than a linear read. 'Why did adding an index not help?' Not sargable, stale statistics, low selectivity, or the planner correctly deciding the scan is cheaper."),

        Q("cs_fundamentals", "DELETE vs TRUNCATE vs DROP (and soft deletes)",
          "A small question that reveals whether you have operated a database. DELETE is DML: it removes rows one at a time, honours a WHERE clause, fires row triggers, writes every removal to the transaction log, can be rolled back, and does NOT reset an auto-increment sequence. Because it logs per row, deleting ten million rows is slow and bloats the log - and in MVCC engines like Postgres the space is not returned to the OS until VACUUM runs. TRUNCATE is DDL: it deallocates the table's pages wholesale, so it is dramatically faster, but it takes no WHERE clause, does not fire per-row triggers, usually resets identity sequences, and requires stronger locks; it is transactional in Postgres and implicitly commits in MySQL and Oracle - a difference worth flagging because it decides whether you can undo. DROP removes the table itself, along with its indexes, constraints and permissions. THE OPERATIONAL POINT, and the one that matters for real systems: deleting a large range in one statement holds a huge transaction and can block others, so you delete in BATCHES with a loop and a small commit each time. THE DESIGN POINT: most production systems do not hard-delete user data at all - they set a deleted_at timestamp and filter it out, so mistakes are recoverable, foreign keys do not break, and audit and analytics still work; the cost is that every query must remember the filter, so put it in a view or a repository method rather than trusting each caller.",
          ["dbms", "sql", "delete", "truncate", "operations", "cs"],
          difficulty="Easy",
          frequency="Commonly asked as a quick SQL discriminator in screens.",
          mnemonic="DELETE = rows, WHERE-able, logged, rollback-able, slow at scale. TRUNCATE = the whole table, fast, resets identity, DDL. DROP = the table is gone. In production, prefer a soft delete (deleted_at) and batch any real delete.",
          code=_c('''
-- DELETE: selective, logged per row, rollback-able, triggers fire.
BEGIN;
DELETE FROM sessions WHERE last_seen < now() - interval '30 days';
ROLLBACK;                     -- fully undone

-- TRUNCATE: whole table, near-instant, resets the identity sequence.
TRUNCATE TABLE staging_import RESTART IDENTITY;

-- DROP: the table, its indexes, constraints and grants all disappear.
DROP TABLE staging_import;

-- Deleting 50 million rows in ONE statement holds a giant transaction, bloats
-- the log and can block other writers. Batch it instead:
DO $$
DECLARE deleted INT;
BEGIN
  LOOP
    DELETE FROM events
     WHERE id IN (SELECT id FROM events
                   WHERE created_at < now() - interval '1 year'
                   LIMIT 10000);              -- small, bounded chunks
    GET DIAGNOSTICS deleted = ROW_COUNT;
    EXIT WHEN deleted = 0;
    COMMIT;                                   -- release locks between batches
  END LOOP;
END $$;

-- SOFT DELETE: what production systems actually do.
ALTER TABLE users ADD COLUMN deleted_at TIMESTAMPTZ;

UPDATE users SET deleted_at = now() WHERE id = 42;      -- "delete"

-- Every read must exclude them - so encode it ONCE, in a view:
CREATE VIEW active_users AS
SELECT * FROM users WHERE deleted_at IS NULL;

-- Partial index so the filter stays cheap on a large table:
CREATE INDEX idx_users_active ON users (id) WHERE deleted_at IS NULL;
'''),
          example="Truncating a partitioned table is how time-series data is really pruned: instead of `DELETE WHERE day < ...` scanning billions of rows, you DROP or TRUNCATE last month's partition, which is a metadata operation and takes milliseconds.",
          pitfalls="TRUNCATE inside a transaction assuming you can roll it back (engine-dependent - it implicitly commits in MySQL and Oracle); expecting DELETE to shrink the file on disk (it marks space reusable; you need VACUUM FULL or OPTIMIZE TABLE); forgetting that TRUNCATE skips triggers, so any audit or cascade logic in them never runs; a soft-delete filter forgotten in one query, so deleted users reappear on one screen.",
          followups="'How do you delete data for GDPR if you soft-delete?' A separate hard-erasure path with a documented retention window - soft delete is for accidents, erasure is a legal obligation. 'Why is DELETE slower than INSERT?' It must find the rows, write undo/redo, update every index, and in MVCC leaves dead tuples for the vacuum process to clean up."),
    ]

    # ── Computer networks ─────────────────────────────────────────────────
    entries += [
        Q("cs_fundamentals", "OSI and TCP/IP models - what each layer actually does",
          "Do not recite seven names; explain what problem each layer solves, using one HTTP request as the running example. PHYSICAL (1) - bits as voltages, light or radio. DATA LINK (2) - frames between two directly connected devices on the same network, addressed by MAC address; Ethernet and Wi-Fi live here, and so does the switch. NETWORK (3) - packets across networks, addressed by IP; this is where routing and the router live, and where the hop-by-hop journey is decided. TRANSPORT (4) - process-to-process delivery, addressed by PORT; TCP adds reliability, ordering and flow control, UDP adds essentially nothing. SESSION (5) and PRESENTATION (6) - in the OSI model these handle dialogue control and encoding/encryption; in practice they are folded into applications and libraries, and TLS is usually described as sitting here. APPLICATION (7) - HTTP, DNS, SMTP: what the user's program speaks. THE TCP/IP MODEL, which is what the internet actually implements, collapses this to four: Link, Internet, Transport, Application. THE UNIFYING IDEA IS ENCAPSULATION: your HTTP text gets a TCP header (ports, sequence numbers), then an IP header (source and destination IP), then an Ethernet header (source and destination MAC); each layer wraps the one above and strips its own header on the way up. THE ADDRESS DISTINCTION most people fumble: the MAC address changes at every hop while the IP address stays the same end to end - saying that sentence proves you understand layering rather than memorising it.",
          ["networks", "osi", "tcp-ip", "layers", "cs"],
          difficulty="Easy",
          frequency="Frequently asked - a guaranteed networking screening question, especially in campus interviews.",
          mnemonic="Please Do Not Throw Sausage Pizza Away: Physical, Data link, Network, Transport, Session, Presentation, Application. Layer 2 = MAC (changes every hop), layer 3 = IP (constant end to end), layer 4 = port (which program).",
          code=_c('''
# One HTTP request, wrapped layer by layer (encapsulation):
#
# APPLICATION  "GET /index.html HTTP/1.1\\r\\nHost: example.com\\r\\n\\r\\n"
#                     |
# TRANSPORT    [TCP hdr: src port 51234 -> dst port 443, seq, ack, flags][payload]
#                     |
# NETWORK      [IP hdr: 192.168.1.10 -> 93.184.216.34, TTL 64][TCP segment]
#                     |
# DATA LINK    [Eth hdr: aa:bb:.. -> your ROUTER's MAC][IP packet][CRC]
#                     |
# PHYSICAL     electrical / optical / radio signal
#
# At the next router: the Ethernet header is STRIPPED and REWRITTEN with new
# MAC addresses for the next hop, TTL is decremented, and the IP header's
# source and destination are UNCHANGED all the way to the server.

import socket

# The socket API is exactly the layer boundary you program against:
s = socket.socket(socket.AF_INET,        # layer 3 family: IPv4
                  socket.SOCK_STREAM)    # layer 4 protocol: TCP (SOCK_DGRAM=UDP)
s.connect(("example.com", 80))           # DNS (layer 7) -> IP, then TCP handshake
s.sendall(b"GET / HTTP/1.1\\r\\nHost: example.com\\r\\nConnection: close\\r\\n\\r\\n")
data = s.recv(4096)                      # TCP hands you an ordered BYTE STREAM
s.close()

# Which layer does each troubleshooting step test?
#   ping        -> layer 3 (ICMP: can packets reach the host at all?)
#   telnet host port / nc -> layer 4 (is a program listening on that port?)
#   curl -v     -> layer 7 (does the application respond correctly?)
#   arp -a      -> layer 2 (do we know the MAC for the next hop?)
'''),
          example="Why the layers earn their keep: TCP has no idea whether it is running over Ethernet, Wi-Fi or a satellite link, and HTTP has no idea whether it is running over TCP or QUIC. That independence is why the internet could add Wi-Fi and HTTP/3 without rewriting everything else.",
          pitfalls="Reciting the seven names with no function; claiming the internet implements OSI (it implements TCP/IP; OSI is a teaching model); putting TLS on a definite layer and arguing about it - say 'between transport and application' and move on; thinking a switch routes (a switch is layer 2 and uses MACs, a router is layer 3 and uses IPs).",
          followups="'Where does a load balancer sit?' L4 balancers forward TCP connections by IP and port; L7 balancers read HTTP and can route by path or header, at higher cost. 'What is MTU and why does it matter?' The largest frame a link accepts (typically 1500 bytes); exceeding it forces fragmentation or a Path MTU Discovery failure, which shows up as connections that hang on large payloads only."),

        Q("cs_fundamentals", "How a packet actually leaves your machine: ARP, DHCP, NAT and routing",
          "The question 'what happens when you type a URL' usually gets a DNS-and-HTTP answer; the layer-2 and layer-3 mechanics underneath are what separate a memorised answer from an understood one. THE SEQUENCE. (1) DHCP - on joining a network your machine broadcasts a DHCP DISCOVER; the server OFFERs an IP, you REQUEST it, it ACKs (the DORA sequence), and you also receive the subnet mask, the default gateway and DNS server addresses. (2) IS THE DESTINATION LOCAL? - AND your IP with the subnet mask and compare with the destination's network portion. Same subnet means you deliver directly; different subnet means you send it to the DEFAULT GATEWAY. (3) ARP - you have an IP for the next hop but Ethernet needs a MAC, so you broadcast 'who has 192.168.1.1?' and the router replies with its MAC, which you cache in the ARP table. (4) The frame goes out with the ROUTER's MAC as the destination but the SERVER's IP as the destination - the key layering fact. (5) NAT - your home router rewrites the source address from your private 192.168.x.x to its single public IP and records the mapping in a translation table, so replies can be sent back to the right internal machine; this is why private addresses (10.x, 172.16-31.x, 192.168.x) work at all and why IPv4 has survived address exhaustion. (6) ROUTING - each router looks up the longest matching prefix in its table and forwards; TTL decrements every hop and the packet dies at zero, which is what traceroute exploits.",
          ["networks", "arp", "dhcp", "nat", "routing", "ip", "cs"],
          difficulty="Medium",
          frequency="Commonly asked as the deeper half of 'what happens when you type a URL'.",
          mnemonic="DHCP gives you an address (DORA), the subnet mask says local-or-not, ARP turns the next-hop IP into a MAC, NAT rewrites your private source address, and each router forwards by LONGEST PREFIX MATCH while TTL counts down.",
          code=_c('''
import ipaddress

# STEP 2 - is the destination on my subnet? Pure bit arithmetic.
def is_local(my_ip, mask, dest_ip):
    net = ipaddress.ip_network(f"{my_ip}/{mask}", strict=False)
    return ipaddress.ip_address(dest_ip) in net

is_local("192.168.1.10", "255.255.255.0", "192.168.1.55")   # True  -> ARP directly
is_local("192.168.1.10", "255.255.255.0", "93.184.216.34")  # False -> via gateway

# STEP 6 - LONGEST PREFIX MATCH, the whole of routing in six lines.
ROUTES = {                                  # prefix -> next hop
    "0.0.0.0/0":        "isp-gateway",      # default: matches everything
    "10.0.0.0/8":       "corp-router",
    "10.1.2.0/24":      "branch-router",    # more specific than 10.0.0.0/8
}

def next_hop(dest):
    d = ipaddress.ip_address(dest)
    best, best_len = None, -1
    for prefix, hop in ROUTES.items():
        net = ipaddress.ip_network(prefix)
        if d in net and net.prefixlen > best_len:    # LONGEST prefix wins
            best, best_len = hop, net.prefixlen
    return best

next_hop("10.1.2.7")     # 'branch-router'  (/24 beats /8)
next_hop("10.9.9.9")     # 'corp-router'    (/8 beats the default /0)
next_hop("93.184.216.34")# 'isp-gateway'    (only the default matches)

# NAT table your home router keeps, conceptually:
#  internal 192.168.1.10:51234  <->  external 203.0.113.7:40001  -> 93.184.216.34:443
#  internal 192.168.1.11:51234  <->  external 203.0.113.7:40002  -> 93.184.216.34:443
#  Two machines can use the same internal PORT because the router remaps it.

# Shell commands that show each step:
#   ip addr / ipconfig      -> the address DHCP gave you
#   ip route / route print  -> your routing table and default gateway
#   arp -a                  -> the IP-to-MAC cache
#   traceroute example.com  -> sends TTL=1, 2, 3... and each router that drops
#                              the packet reveals itself with an ICMP reply
'''),
          example="Traceroute is the whole model in one tool: send a packet with TTL=1 and the first router decrements it to zero, discards it and replies with ICMP Time Exceeded - revealing hop 1. TTL=2 reveals hop 2, and so on. The path prints itself because of one field in the IP header.",
          pitfalls="Thinking ARP is used for remote hosts (you only ever ARP for something on your own subnet, usually the gateway); confusing a switch with a router; believing NAT is a security feature (it hides addresses as a side effect, it is not a firewall); forgetting that the destination MAC changes at every hop while the destination IP never does.",
          followups="'Why does IPv6 not need NAT?' The address space is large enough for every device to be publicly addressable, so the translation layer disappears - along with the difficulties it causes for peer-to-peer traffic. 'What is ARP spoofing?' Forging ARP replies so traffic for the gateway comes to you instead - a classic man-in-the-middle attack on a shared network, and the reason TLS matters even inside a LAN."),

        Q("cs_fundamentals", "HTTP in depth: methods, status codes, idempotency and REST",
          "The web protocol you will be asked about in every backend screen. METHODS and their two properties: SAFE means it does not change server state (GET, HEAD, OPTIONS); IDEMPOTENT means doing it N times has the same effect as doing it once (GET, PUT, DELETE, HEAD - and notably NOT POST). That distinction is not trivia: it decides whether a proxy, a browser or your own retry logic may safely repeat a request after a timeout. PUT replaces a resource at a known URL and is idempotent; POST creates a subordinate resource and is not, which is exactly why double-clicking Buy can create two orders and why real APIs accept an idempotency key. PATCH is a partial update and is not idempotent in general. STATUS CODES by family: 2xx success (200 OK, 201 Created with a Location header, 204 No Content), 3xx redirection (301 permanent and cacheable forever - dangerous to get wrong; 302/307 temporary; 304 Not Modified, the conditional-request win), 4xx client error (400 malformed, 401 unauthenticated, 403 authenticated but not allowed, 404 missing, 409 conflict, 422 validation failed, 429 rate limited), 5xx server error (500 unhandled, 502 bad upstream, 503 unavailable, 504 upstream timeout). The 401-vs-403 and 502-vs-504 pairs are the ones interviewers probe. REST as a set of constraints worth naming: resources identified by URLs, a uniform interface of standard methods, STATELESSNESS (every request carries its own auth and context, which is what lets you put ten identical servers behind a load balancer), and cacheability.",
          ["networks", "http", "rest", "api", "idempotency", "status-codes", "cs"],
          difficulty="Easy",
          frequency="Very commonly asked in backend and full-stack screens; the idempotency question comes up constantly.",
          mnemonic="SAFE = no change (GET). IDEMPOTENT = repeat safely (GET, PUT, DELETE - not POST). 401 = who are you; 403 = I know you and no. 502 = bad upstream reply; 504 = upstream never replied. Stateless is what makes horizontal scaling possible.",
          code=_c('''
# ── Method semantics, as an API you would actually design ────────────────
# GET    /orders/42          -> 200 + body        (safe, idempotent, cacheable)
# POST   /orders             -> 201 + Location: /orders/43   (NOT idempotent)
# PUT    /orders/42          -> 200/204   full replace       (idempotent)
# PATCH  /orders/42          -> 200       partial update
# DELETE /orders/42          -> 204; deleting again -> 204 or 404 (idempotent:
#                               the STATE is the same either way)

# ── The idempotency key: how real APIs make POST safe to retry ───────────
from flask import request, jsonify

processed = {}          # key -> response (in production: Redis with a TTL)

def create_order():
    key = request.headers.get("Idempotency-Key")
    if key and key in processed:
        return processed[key], 200          # replay the ORIGINAL response
    order = do_create(request.json)         # the real work, exactly once
    response = jsonify(order)
    if key:
        processed[key] = response
    return response, 201

# Without this, a client that times out and retries creates TWO orders - the
# request may well have succeeded and only the RESPONSE was lost.

# ── Conditional requests: 304 saves the whole body ───────────────────────
# Client: GET /avatar.png    If-None-Match: "abc123"
# Server: 304 Not Modified   (no body at all - just headers)

# ── Status codes that get confused, and the rule for each ────────────────
# 401 Unauthorized  -> you are not authenticated. Send credentials.
# 403 Forbidden     -> you ARE authenticated and still may not. Do not retry.
# 404 vs 403        -> returning 404 for a resource you may not see avoids
#                      leaking its existence; a deliberate security choice.
# 429 Too Many      -> include a Retry-After header so clients back off politely
# 502 Bad Gateway   -> the upstream replied with garbage
# 503 Unavailable   -> we are overloaded or in maintenance; usually retryable
# 504 Gateway Timeout -> the upstream never replied in time

# ── Statelessness, and why it matters for scaling ────────────────────────
# BAD : the server keeps session state in local memory -> the user must return
#       to the SAME server (sticky sessions), and a restart logs everyone out.
# GOOD: the request carries a signed token, or session state lives in Redis ->
#       any of ten servers can serve any request, and scaling is just "add one".
'''),
          example="Why DELETE counts as idempotent even though the second call 404s: idempotency is about the resulting STATE, not the response code. After one DELETE or five, the resource is gone. A client may therefore safely retry a DELETE that timed out - which is precisely the property retry logic depends on.",
          examples=[
              "Why idempotency is not trivia. A client POSTs an order, the payment succeeds, and the response is lost to a network blip. The client's retry logic fires and POSTs again - two orders, two charges. This is not a rare edge case; it is the normal behaviour of any network under load. The fix is an Idempotency-Key header: the server stores the key with the result of the first attempt and REPLAYS that stored response on any retry carrying the same key. Stripe, Square and every serious payments API work exactly this way.",
              "Why DELETE counts as idempotent even though the second call 404s. Idempotency is a property of the resulting STATE, not of the response code. After one DELETE the resource is gone; after five, it is still gone. So a client whose DELETE timed out may safely retry - which is precisely the property retry logic depends on. Contrast POST /orders, where each call creates a NEW resource, so the state after five calls differs from the state after one. That is the distinction, and candidates who answer 'because it returns 404' have it backwards.",
              "401 versus 403, which is asked constantly. 401 Unauthorized actually means UNAUTHENTICATED: 'I do not know who you are - send credentials', and it should carry a WWW-Authenticate header. 403 Forbidden means 'I know exactly who you are, and you still may not' - retrying with the same credentials is pointless. A related design choice worth raising: returning 404 instead of 403 for a resource the user may not see avoids leaking that it exists at all, which is a deliberate security trade some APIs make.",
              "502 versus 503 versus 504, from the perspective of a gateway. Your load balancer sits in front of an app server. 502 Bad Gateway: the app replied, but with garbage the gateway could not parse (often a crashed worker mid-response). 503 Service Unavailable: nothing is available to ask - all workers busy, or the service is deliberately in maintenance; usually retryable and often paired with Retry-After. 504 Gateway Timeout: the app was asked and never answered within the deadline, which points at a slow query or a deadlock downstream. Three different investigations, so the code you return matters operationally.",
              "Statelessness, and the concrete consequence. Store the session in the app server's memory and a user must keep returning to that same server - so you need sticky sessions, a restart logs everyone out, and you cannot scale by simply adding a machine. Move the session into a signed token the client carries, or into Redis, and any of ten servers can serve any request. This is why REST lists statelessness as a constraint: it is not purity, it is what makes horizontal scaling and zero-downtime deploys possible.",
              "Conditional requests, which are free performance. Client sends `If-None-Match: \"abc123\"`; if the resource is unchanged the server replies 304 Not Modified with NO body at all - just headers. For a 500KB avatar or a large JSON list that changes rarely, that is a 500KB saving per request across every user. The same mechanism with If-Modified-Since works on timestamps, and ETags additionally enable optimistic concurrency on writes via If-Match, which turns a lost-update race into a 412 Precondition Failed.",
          ],
          pitfalls="Using GET for anything that changes state (crawlers and prefetchers will trigger it); returning 200 with an error message in the body, which breaks every client's error handling; using 301 during an experiment (browsers cache it aggressively and users get stuck); assuming POST retries are safe; putting a session in server memory and then wondering why scaling out logs people out.",
          followups="'How would you make a payment endpoint safe against retries?' An idempotency key stored with the result, plus a unique constraint in the database as the last line of defence. 'What changed in HTTP/2 and HTTP/3?' HTTP/2 multiplexes many streams over one TCP connection (killing head-of-line blocking at the HTTP layer but not at TCP); HTTP/3 moves to QUIC over UDP, which removes it at the transport layer too and survives a network change without a new handshake."),

        Q("cs_fundamentals", "TCP flow control vs congestion control (and why your download speeds up gradually)",
          "Two different problems that both throttle a TCP sender, and mixing them up is the standard mistake. FLOW CONTROL protects the RECEIVER: it stops a fast sender overwhelming a slow receiver's buffer. The mechanism is the RECEIVE WINDOW advertised in every ACK - 'I have room for 64KB more' - and the sender may never have more than that unacknowledged. A window of zero halts the sender until a window update arrives. CONGESTION CONTROL protects the NETWORK: it stops all senders collectively overwhelming the routers in between, which nobody advertises because no router tells you it is full - you must INFER congestion from packet loss or rising delay. The mechanism is a second, sender-side congestion window, and the sender may transmit at most min(receive window, congestion window). THE ALGORITHM, which explains a familiar experience: SLOW START begins with a couple of segments and DOUBLES the window every round trip (exponential, despite the name) until it hits a threshold or loses a packet; then CONGESTION AVOIDANCE grows it by roughly one segment per round trip (linear, the additive-increase phase); a triple duplicate ACK signals mild loss so FAST RECOVERY halves the window (multiplicative decrease); a full timeout is treated as severe, collapsing the window back to the start. That AIMD sawtooth is why a big download ramps up over a few seconds rather than starting at full speed, and why a lossy Wi-Fi link is slow even when bandwidth is plentiful - TCP interprets radio loss as congestion. Modern alternatives (CUBIC, and BBR which models bandwidth and round-trip time instead of reacting to loss) are worth naming.",
          ["networks", "tcp", "congestion-control", "flow-control", "cs"],
          difficulty="Medium",
          frequency="Commonly asked in networking-heavy screens and as a follow-up to TCP vs UDP.",
          mnemonic="FLOW control protects the RECEIVER (advertised window, explicit). CONGESTION control protects the NETWORK (inferred from loss, sender-side). Send min(rwnd, cwnd). Slow start doubles, avoidance adds one, loss halves - AIMD's sawtooth.",
          code=_c('''
def simulate_tcp(rounds=14, ssthresh=16, loss_at=None):
    """The classic cwnd sawtooth, in round-trip times."""
    cwnd, phase, history = 1, "slow-start", []
    for rtt in range(1, rounds + 1):
        history.append((rtt, cwnd, phase))
        if loss_at and rtt == loss_at:            # triple duplicate ACK
            ssthresh = max(2, cwnd // 2)
            cwnd = ssthresh                       # multiplicative DECREASE
            phase = "congestion-avoidance"
            continue
        if phase == "slow-start":
            cwnd *= 2                             # EXPONENTIAL growth
            if cwnd >= ssthresh:
                phase = "congestion-avoidance"
        else:
            cwnd += 1                             # additive INCREASE (linear)
    return history

for rtt, cwnd, phase in simulate_tcp(loss_at=8):
    print(f"RTT {rtt:2}  cwnd {cwnd:3}  {phase}")
# 1,2,4,8,16 (slow start) then 17,18,19 (avoidance) then loss -> 9, then 10,11...

# What the SENDER may actually have in flight:
def in_flight_limit(receive_window, congestion_window, mss=1460):
    return min(receive_window, congestion_window * mss)

# Bandwidth-delay product: how big the window must be to fill a fast, long link.
def bdp_bytes(bandwidth_mbps, rtt_ms):
    return bandwidth_mbps * 1_000_000 / 8 * (rtt_ms / 1000)

bdp_bytes(1000, 100)      # 12.5 MB needed to saturate 1 Gbps at 100ms RTT
# The original 16-bit window field caps at 64KB - hence the window scaling
# option, without which a fast intercontinental link is stuck at ~5 Mbps.
'''),
          example="Why a video call over patchy Wi-Fi degrades so badly on TCP: a lost frame from radio interference is not congestion, but TCP cannot tell the difference and halves its window anyway. That is precisely why real-time media uses UDP and handles loss itself, and why QUIC (over UDP) can implement smarter loss handling than TCP allows.",
          pitfalls="Saying slow start is slow (it is exponential; it merely STARTS small); attributing the receive window to congestion control; forgetting the sender is limited by the MINIMUM of the two windows; ignoring bandwidth-delay product, which is why a long fat link needs window scaling to go fast.",
          followups="'What does BBR do differently?' It estimates the bottleneck bandwidth and minimum RTT and paces to that, rather than growing until something breaks - much better on lossy or buffer-bloated paths. 'What is head-of-line blocking in TCP?' One lost segment stalls delivery of everything behind it even if it has arrived, which HTTP/2 could not fix and HTTP/3 over QUIC does by giving each stream independent ordering."),

        Q("cs_fundamentals", "Real-time on the web: polling vs long polling vs SSE vs WebSockets",
          "'How would you build live updates?' has four answers and each is right somewhere. SHORT POLLING - the client asks every N seconds. Trivial to build on plain HTTP, works through every proxy, and wastes a request per interval per user; latency averages half the interval. Fine for a dashboard refreshing every 30 seconds. LONG POLLING - the client asks and the server HOLDS the request open until it has news (or times out), then the client immediately asks again. Near-real-time on ordinary HTTP, at the cost of a held connection per user and awkward timeout handling; it was how chat worked before WebSockets. SERVER-SENT EVENTS - one long-lived HTTP response over which the server streams text events; ONE-DIRECTIONAL (server to client), built into browsers as EventSource, and it reconnects automatically with a Last-Event-ID so you can resume. Perfect for notifications, live scores, progress bars and streaming LLM tokens - which is exactly what ChatGPT-style token streaming uses. WEBSOCKETS - a real bidirectional connection created by an HTTP Upgrade handshake, then a persistent frame-based channel in both directions with low per-message overhead. The right choice for chat, multiplayer games and collaborative editing; the cost is that it is no longer HTTP, so load balancers, proxies and auth need explicit support and you must handle reconnection and heartbeats yourself. THE DECISION RULE to state: if only the server has news, SSE; if both sides talk constantly, WebSockets; if updates are rare and latency does not matter, polling - and do not build a WebSocket layer for a page that refreshes every minute.",
          ["networks", "websockets", "sse", "polling", "realtime", "http", "cs"],
          difficulty="Medium",
          frequency="Commonly asked in web and system-design rounds; SSE is increasingly asked because of LLM token streaming.",
          mnemonic="Polling = ask repeatedly (simple, wasteful). Long polling = ask and wait. SSE = server streams one way, auto-reconnects, plain HTTP. WebSockets = both ways, persistent, needs infra support. Server-only news -> SSE. Two-way chat -> WebSockets.",
          code=_c('''
# ── SSE: one-way server -> client, plain HTTP, auto-reconnect built in ───
from flask import Response
import json, time

def sse_stream():
    def gen():
        event_id = 0
        while True:
            event_id += 1
            payload = json.dumps({"progress": event_id * 10})
            # The wire format is literally these lines plus a blank line:
            yield f"id: {event_id}\\ndata: {payload}\\n\\n"
            time.sleep(1)
    return Response(gen(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache",
                             "X-Accel-Buffering": "no"})   # stop nginx buffering

# Browser side - three lines, and it reconnects on its own:
#   const es = new EventSource("/stream");
#   es.onmessage = e => console.log(JSON.parse(e.data));
#   // on reconnect the browser sends Last-Event-ID so you can resume

# ── WebSockets: bidirectional, after an HTTP Upgrade handshake ───────────
# Client request:            Server response:
#   GET /ws HTTP/1.1           HTTP/1.1 101 Switching Protocols
#   Upgrade: websocket         Upgrade: websocket
#   Connection: Upgrade        Connection: Upgrade
#   Sec-WebSocket-Key: ...     Sec-WebSocket-Accept: <hash of the key>
# After 101 the TCP connection is no longer HTTP - it carries WS frames.

import asyncio, websockets                      # server sketch

CLIENTS = set()

async def handler(ws):
    CLIENTS.add(ws)                             # track for broadcast
    try:
        async for message in ws:                # receive
            await asyncio.gather(*[c.send(message) for c in CLIENTS])  # fan out
    finally:
        CLIENTS.discard(ws)                     # ALWAYS clean up, or you leak

# Production concerns people forget:
#  - heartbeats (ping/pong) to detect a dead peer; NAT drops idle connections
#  - exponential backoff on reconnect, or a server restart causes a stampede
#  - authenticate at the handshake; you cannot rely on per-message auth headers
#  - a sticky routing or a shared pub/sub bus, because a connection lives on ONE
#    server and the message it must deliver may arrive at another
'''),
          example="LLM token streaming is the SSE case exactly: the server has a stream of tokens, the client has nothing to say back mid-generation, and SSE gives you reconnect and resume for free over ordinary HTTP. Choosing WebSockets there adds infrastructure complexity for a channel you would use in one direction.",
          pitfalls="Reaching for WebSockets by default; forgetting nginx or a CDN will buffer an SSE stream unless told not to, so nothing appears until the end; no heartbeat, so half-open connections pile up; no reconnect backoff, so a restart brings a thundering herd; assuming a WebSocket connection can move between servers - it cannot, which is why you need a shared pub/sub layer to broadcast.",
          followups="'How do you scale WebSockets to a million connections?' Many stateless gateway processes each holding connections, with Redis or Kafka pub/sub fanning messages between them, and an epoll-based server so idle connections are nearly free. 'What happens through a corporate proxy?' SSE is ordinary HTTP and usually survives; WebSocket upgrades are sometimes blocked, which is why libraries like Socket.IO fall back to long polling."),
    ]

    return entries
